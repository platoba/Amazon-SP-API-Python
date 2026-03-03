"""
Request metrics and monitoring for SP-API calls.

Tracks latency, throughput, error rates, and quota usage per endpoint.
Provides real-time dashboards and exportable reports.

Usage:
    from sp_api.metrics import MetricsCollector, MetricsReport

    metrics = MetricsCollector()

    # Record a request
    with metrics.track("/orders/v0/orders"):
        response = api.get_orders()

    # Get report
    report = MetricsReport(metrics)
    print(report.summary())
    report.export_json("metrics.json")
"""

import json
import logging
import threading
import time
from collections import defaultdict
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class RequestRecord:
    """Single request record."""
    endpoint: str
    method: str
    status_code: int
    latency_ms: float
    timestamp: float
    error: Optional[str] = None
    throttled: bool = False
    from_cache: bool = False
    request_size: int = 0
    response_size: int = 0


@dataclass
class EndpointStats:
    """Aggregated statistics for a single endpoint."""
    endpoint: str
    total_requests: int = 0
    success_count: int = 0
    error_count: int = 0
    throttle_count: int = 0
    cache_hits: int = 0
    total_latency_ms: float = 0.0
    min_latency_ms: float = float('inf')
    max_latency_ms: float = 0.0
    latencies: list = field(default_factory=list)
    errors_by_code: Dict[int, int] = field(default_factory=lambda: defaultdict(int))
    first_request: float = 0.0
    last_request: float = 0.0

    def record(self, rec: RequestRecord):
        """Add a request record."""
        self.total_requests += 1
        self.total_latency_ms += rec.latency_ms
        self.latencies.append(rec.latency_ms)

        # Keep only last 1000 latencies for percentile calculation
        if len(self.latencies) > 1000:
            self.latencies = self.latencies[-1000:]

        if rec.latency_ms < self.min_latency_ms:
            self.min_latency_ms = rec.latency_ms
        if rec.latency_ms > self.max_latency_ms:
            self.max_latency_ms = rec.latency_ms

        if not self.first_request:
            self.first_request = rec.timestamp
        self.last_request = rec.timestamp

        if rec.error:
            self.error_count += 1
            self.errors_by_code[rec.status_code] += 1
        else:
            self.success_count += 1

        if rec.throttled:
            self.throttle_count += 1
        if rec.from_cache:
            self.cache_hits += 1

    @property
    def avg_latency_ms(self) -> float:
        if self.total_requests == 0:
            return 0.0
        return self.total_latency_ms / self.total_requests

    @property
    def success_rate(self) -> float:
        if self.total_requests == 0:
            return 0.0
        return self.success_count / self.total_requests

    @property
    def throttle_rate(self) -> float:
        if self.total_requests == 0:
            return 0.0
        return self.throttle_count / self.total_requests

    @property
    def cache_hit_rate(self) -> float:
        if self.total_requests == 0:
            return 0.0
        return self.cache_hits / self.total_requests

    def percentile(self, p: float) -> float:
        """Calculate latency percentile (0-100)."""
        if not self.latencies:
            return 0.0
        sorted_lat = sorted(self.latencies)
        idx = int(len(sorted_lat) * p / 100)
        idx = min(idx, len(sorted_lat) - 1)
        return sorted_lat[idx]

    @property
    def p50(self) -> float:
        return self.percentile(50)

    @property
    def p95(self) -> float:
        return self.percentile(95)

    @property
    def p99(self) -> float:
        return self.percentile(99)

    @property
    def rps(self) -> float:
        """Requests per second."""
        if self.total_requests < 2:
            return 0.0
        duration = self.last_request - self.first_request
        if duration <= 0:
            return 0.0
        return self.total_requests / duration

    def to_dict(self) -> Dict:
        return {
            "endpoint": self.endpoint,
            "total_requests": self.total_requests,
            "success_count": self.success_count,
            "error_count": self.error_count,
            "throttle_count": self.throttle_count,
            "cache_hits": self.cache_hits,
            "success_rate": round(self.success_rate, 4),
            "throttle_rate": round(self.throttle_rate, 4),
            "cache_hit_rate": round(self.cache_hit_rate, 4),
            "latency": {
                "avg_ms": round(self.avg_latency_ms, 2),
                "min_ms": round(self.min_latency_ms, 2) if self.min_latency_ms != float('inf') else 0,
                "max_ms": round(self.max_latency_ms, 2),
                "p50_ms": round(self.p50, 2),
                "p95_ms": round(self.p95, 2),
                "p99_ms": round(self.p99, 2),
            },
            "rps": round(self.rps, 2),
            "errors_by_code": dict(self.errors_by_code),
        }


class MetricsCollector:
    """
    Thread-safe metrics collector for SP-API requests.

    Tracks per-endpoint and global request statistics including
    latency percentiles, error rates, throttle counts, and throughput.
    """

    def __init__(self, max_history: int = 10000):
        self._lock = threading.Lock()
        self._endpoints: Dict[str, EndpointStats] = {}
        self._history: List[RequestRecord] = []
        self._max_history = max_history
        self._start_time = time.time()
        self._global_stats = EndpointStats(endpoint="__global__")

    @contextmanager
    def track(
        self,
        endpoint: str,
        method: str = "GET",
        request_size: int = 0,
    ):
        """
        Context manager to track a request.

        Usage:
            with metrics.track("/orders/v0/orders") as tracker:
                response = make_request()
                tracker.set_status(200)
                tracker.set_response_size(len(response))
        """
        tracker = _RequestTracker(endpoint, method, request_size)
        try:
            yield tracker
        except Exception as e:
            tracker.set_error(e)
            raise
        finally:
            record = tracker.finalize()
            self._record(record)

    def record_request(
        self,
        endpoint: str,
        method: str = "GET",
        status_code: int = 200,
        latency_ms: float = 0.0,
        error: Optional[str] = None,
        throttled: bool = False,
        from_cache: bool = False,
        request_size: int = 0,
        response_size: int = 0,
    ):
        """Directly record a request (alternative to context manager)."""
        record = RequestRecord(
            endpoint=endpoint,
            method=method,
            status_code=status_code,
            latency_ms=latency_ms,
            timestamp=time.time(),
            error=error,
            throttled=throttled,
            from_cache=from_cache,
            request_size=request_size,
            response_size=response_size,
        )
        self._record(record)

    def _record(self, record: RequestRecord):
        """Thread-safe recording."""
        with self._lock:
            # Per-endpoint stats
            if record.endpoint not in self._endpoints:
                self._endpoints[record.endpoint] = EndpointStats(endpoint=record.endpoint)
            self._endpoints[record.endpoint].record(record)

            # Global stats
            self._global_stats.record(record)

            # History
            self._history.append(record)
            if len(self._history) > self._max_history:
                self._history = self._history[-self._max_history:]

    def get_endpoint_stats(self, endpoint: str) -> Optional[EndpointStats]:
        """Get stats for a specific endpoint."""
        with self._lock:
            return self._endpoints.get(endpoint)

    @property
    def global_stats(self) -> EndpointStats:
        """Get global aggregate stats."""
        return self._global_stats

    @property
    def endpoints(self) -> Dict[str, EndpointStats]:
        """Get all endpoint stats."""
        with self._lock:
            return dict(self._endpoints)

    @property
    def uptime_seconds(self) -> float:
        return time.time() - self._start_time

    def summary(self) -> Dict:
        """Get a summary of all metrics."""
        with self._lock:
            return {
                "uptime_seconds": round(self.uptime_seconds, 1),
                "global": self._global_stats.to_dict(),
                "endpoints": {
                    name: stats.to_dict()
                    for name, stats in sorted(self._endpoints.items())
                },
                "top_errors": self._top_errors(5),
                "slowest_endpoints": self._slowest_endpoints(5),
            }

    def _top_errors(self, n: int) -> List[Dict]:
        """Get endpoints with most errors."""
        endpoints = sorted(
            self._endpoints.values(),
            key=lambda s: s.error_count,
            reverse=True,
        )
        return [
            {"endpoint": e.endpoint, "errors": e.error_count, "rate": round(1 - e.success_rate, 4)}
            for e in endpoints[:n] if e.error_count > 0
        ]

    def _slowest_endpoints(self, n: int) -> List[Dict]:
        """Get slowest endpoints by p95 latency."""
        endpoints = sorted(
            self._endpoints.values(),
            key=lambda s: s.p95,
            reverse=True,
        )
        return [
            {"endpoint": e.endpoint, "p95_ms": round(e.p95, 2), "avg_ms": round(e.avg_latency_ms, 2)}
            for e in endpoints[:n] if e.total_requests > 0
        ]

    def reset(self):
        """Reset all metrics."""
        with self._lock:
            self._endpoints.clear()
            self._history.clear()
            self._global_stats = EndpointStats(endpoint="__global__")
            self._start_time = time.time()


class _RequestTracker:
    """Helper for context-managed request tracking."""

    def __init__(self, endpoint: str, method: str, request_size: int):
        self.endpoint = endpoint
        self.method = method
        self.request_size = request_size
        self._start = time.time()
        self._status_code = 200
        self._error: Optional[str] = None
        self._throttled = False
        self._from_cache = False
        self._response_size = 0

    def set_status(self, code: int):
        self._status_code = code
        if code == 429:
            self._throttled = True

    def set_error(self, error: Exception):
        self._error = f"{type(error).__name__}: {error}"
        if "throttl" in str(error).lower() or "429" in str(error):
            self._throttled = True
        if not hasattr(self, '_status_code_set'):
            self._status_code = getattr(error, 'status_code', 500)

    def set_response_size(self, size: int):
        self._response_size = size

    def set_cached(self, cached: bool = True):
        self._from_cache = cached

    def finalize(self) -> RequestRecord:
        elapsed_ms = (time.time() - self._start) * 1000
        return RequestRecord(
            endpoint=self.endpoint,
            method=self.method,
            status_code=self._status_code,
            latency_ms=elapsed_ms,
            timestamp=self._start,
            error=self._error,
            throttled=self._throttled,
            from_cache=self._from_cache,
            request_size=self.request_size,
            response_size=self._response_size,
        )


class MetricsReport:
    """
    Generate human-readable or exportable metrics reports.

    Args:
        collector: MetricsCollector instance
    """

    def __init__(self, collector: MetricsCollector):
        self.collector = collector

    def text_summary(self) -> str:
        """Generate a human-readable text report."""
        data = self.collector.summary()
        g = data["global"]
        lines = [
            "═══════════════════════════════════════════",
            "  SP-API Metrics Report",
            f"  Uptime: {data['uptime_seconds']}s",
            "═══════════════════════════════════════════",
            "",
            f"  Total requests:  {g['total_requests']}",
            f"  Success rate:    {g['success_rate']:.1%}",
            f"  Throttle rate:   {g['throttle_rate']:.1%}",
            f"  Cache hit rate:  {g['cache_hit_rate']:.1%}",
            f"  Avg latency:     {g['latency']['avg_ms']:.1f}ms",
            f"  P50 latency:     {g['latency']['p50_ms']:.1f}ms",
            f"  P95 latency:     {g['latency']['p95_ms']:.1f}ms",
            f"  P99 latency:     {g['latency']['p99_ms']:.1f}ms",
            f"  RPS:             {g['rps']:.2f}",
            "",
        ]

        if data["endpoints"]:
            lines.append("  Per-Endpoint Breakdown:")
            lines.append("  " + "─" * 41)
            for name, stats in data["endpoints"].items():
                lines.append(f"  {name}")
                lines.append(
                    f"    {stats['total_requests']} reqs | "
                    f"{stats['success_rate']:.0%} ok | "
                    f"p95={stats['latency']['p95_ms']:.0f}ms"
                )

        if data["top_errors"]:
            lines.append("")
            lines.append("  Top Error Endpoints:")
            for e in data["top_errors"]:
                lines.append(f"    {e['endpoint']}: {e['errors']} errors ({e['rate']:.1%})")

        lines.append("═══════════════════════════════════════════")
        return "\n".join(lines)

    def export_json(self, filepath: str):
        """Export metrics to JSON file."""
        data = self.collector.summary()
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
        logger.info("Metrics exported to %s", filepath)

    def export_csv(self, filepath: str):
        """Export per-endpoint metrics to CSV."""
        data = self.collector.summary()
        lines = [
            "endpoint,requests,success_rate,throttle_rate,avg_ms,p50_ms,p95_ms,p99_ms,errors,rps"
        ]
        for name, stats in data["endpoints"].items():
            lat = stats["latency"]
            lines.append(
                f"{name},{stats['total_requests']},{stats['success_rate']},"
                f"{stats['throttle_rate']},{lat['avg_ms']},{lat['p50_ms']},"
                f"{lat['p95_ms']},{lat['p99_ms']},{stats['error_count']},{stats['rps']}"
            )
        with open(filepath, 'w') as f:
            f.write("\n".join(lines))
        logger.info("Metrics CSV exported to %s", filepath)
