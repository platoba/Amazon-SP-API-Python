"""Tests for metrics module — collector, endpoint stats, reports."""

import json
import os
import time
import tempfile
import pytest

from sp_api.metrics import (
    EndpointStats,
    MetricsCollector,
    MetricsReport,
    RequestRecord,
    _RequestTracker,
)


class TestRequestRecord:
    def test_create(self):
        rec = RequestRecord(
            endpoint="/orders",
            method="GET",
            status_code=200,
            latency_ms=150.5,
            timestamp=time.time(),
        )
        assert rec.endpoint == "/orders"
        assert rec.status_code == 200
        assert not rec.throttled

    def test_error_record(self):
        rec = RequestRecord(
            endpoint="/orders",
            method="GET",
            status_code=500,
            latency_ms=50.0,
            timestamp=time.time(),
            error="Internal Server Error",
        )
        assert rec.error is not None

    def test_throttled_record(self):
        rec = RequestRecord(
            endpoint="/catalog",
            method="GET",
            status_code=429,
            latency_ms=10.0,
            timestamp=time.time(),
            throttled=True,
        )
        assert rec.throttled


class TestEndpointStats:
    def test_initial(self):
        stats = EndpointStats(endpoint="/test")
        assert stats.total_requests == 0
        assert stats.avg_latency_ms == 0.0
        assert stats.success_rate == 0.0

    def test_record_success(self):
        stats = EndpointStats(endpoint="/orders")
        rec = RequestRecord("/orders", "GET", 200, 100.0, time.time())
        stats.record(rec)
        assert stats.total_requests == 1
        assert stats.success_count == 1
        assert stats.success_rate == 1.0

    def test_record_error(self):
        stats = EndpointStats(endpoint="/orders")
        rec = RequestRecord("/orders", "GET", 500, 50.0, time.time(), error="fail")
        stats.record(rec)
        assert stats.error_count == 1
        assert stats.errors_by_code[500] == 1
        assert stats.success_rate == 0.0

    def test_record_throttle(self):
        stats = EndpointStats(endpoint="/orders")
        rec = RequestRecord("/orders", "GET", 429, 10.0, time.time(), throttled=True)
        stats.record(rec)
        assert stats.throttle_count == 1
        assert stats.throttle_rate == 1.0

    def test_record_cache_hit(self):
        stats = EndpointStats(endpoint="/orders")
        rec = RequestRecord("/orders", "GET", 200, 1.0, time.time(), from_cache=True)
        stats.record(rec)
        assert stats.cache_hits == 1
        assert stats.cache_hit_rate == 1.0

    def test_latency_tracking(self):
        stats = EndpointStats(endpoint="/orders")
        for ms in [100, 200, 300, 400, 500]:
            rec = RequestRecord("/orders", "GET", 200, ms, time.time())
            stats.record(rec)
        assert stats.min_latency_ms == 100
        assert stats.max_latency_ms == 500
        assert stats.avg_latency_ms == 300.0

    def test_percentiles(self):
        stats = EndpointStats(endpoint="/orders")
        for ms in range(1, 101):
            rec = RequestRecord("/orders", "GET", 200, float(ms), time.time())
            stats.record(rec)
        assert stats.p50 == pytest.approx(50, abs=2)
        assert stats.p95 == pytest.approx(95, abs=2)
        assert stats.p99 == pytest.approx(99, abs=2)

    def test_empty_percentile(self):
        stats = EndpointStats(endpoint="/orders")
        assert stats.p50 == 0.0

    def test_rps(self):
        stats = EndpointStats(endpoint="/orders")
        t = time.time()
        for i in range(10):
            rec = RequestRecord("/orders", "GET", 200, 10.0, t + i)
            stats.record(rec)
        assert stats.rps > 0

    def test_rps_single_request(self):
        stats = EndpointStats(endpoint="/orders")
        rec = RequestRecord("/orders", "GET", 200, 10.0, time.time())
        stats.record(rec)
        assert stats.rps == 0.0

    def test_to_dict(self):
        stats = EndpointStats(endpoint="/orders")
        rec = RequestRecord("/orders", "GET", 200, 100.0, time.time())
        stats.record(rec)
        d = stats.to_dict()
        assert d["endpoint"] == "/orders"
        assert d["total_requests"] == 1
        assert "latency" in d
        assert "avg_ms" in d["latency"]

    def test_latency_window(self):
        """Ensures latencies list doesn't grow unbounded."""
        stats = EndpointStats(endpoint="/orders")
        for i in range(1500):
            rec = RequestRecord("/orders", "GET", 200, float(i), time.time())
            stats.record(rec)
        assert len(stats.latencies) <= 1000


class TestMetricsCollector:
    def test_record_request(self):
        mc = MetricsCollector()
        mc.record_request("/orders", latency_ms=100)
        assert mc.global_stats.total_requests == 1

    def test_per_endpoint(self):
        mc = MetricsCollector()
        mc.record_request("/orders", latency_ms=100)
        mc.record_request("/catalog", latency_ms=200)
        assert len(mc.endpoints) == 2
        assert mc.get_endpoint_stats("/orders").total_requests == 1
        assert mc.get_endpoint_stats("/catalog").total_requests == 1

    def test_unknown_endpoint(self):
        mc = MetricsCollector()
        assert mc.get_endpoint_stats("/nonexistent") is None

    def test_context_manager_success(self):
        mc = MetricsCollector()
        with mc.track("/orders") as tracker:
            time.sleep(0.01)
            tracker.set_status(200)
        stats = mc.get_endpoint_stats("/orders")
        assert stats.total_requests == 1
        assert stats.success_count == 1

    def test_context_manager_error(self):
        mc = MetricsCollector()
        with pytest.raises(ValueError):
            with mc.track("/orders") as tracker:
                raise ValueError("test error")
        stats = mc.get_endpoint_stats("/orders")
        assert stats.error_count == 1

    def test_summary(self):
        mc = MetricsCollector()
        mc.record_request("/orders", latency_ms=100)
        mc.record_request("/orders", latency_ms=200, error="fail", status_code=500)
        mc.record_request("/catalog", latency_ms=50)
        summary = mc.summary()
        assert summary["global"]["total_requests"] == 3
        assert len(summary["endpoints"]) == 2
        assert "top_errors" in summary
        assert "slowest_endpoints" in summary

    def test_uptime(self):
        mc = MetricsCollector()
        time.sleep(0.05)
        assert mc.uptime_seconds >= 0.05

    def test_reset(self):
        mc = MetricsCollector()
        mc.record_request("/orders", latency_ms=100)
        mc.reset()
        assert mc.global_stats.total_requests == 0
        assert len(mc.endpoints) == 0

    def test_history_limit(self):
        mc = MetricsCollector(max_history=100)
        for i in range(200):
            mc.record_request("/orders", latency_ms=float(i))
        assert len(mc._history) <= 100

    def test_mixed_endpoints_summary(self):
        mc = MetricsCollector()
        for _ in range(5):
            mc.record_request("/orders", latency_ms=100)
        for _ in range(3):
            mc.record_request("/catalog", latency_ms=200, error="fail", status_code=500)
        summary = mc.summary()
        top_err = summary["top_errors"]
        assert len(top_err) > 0
        assert top_err[0]["endpoint"] == "/catalog"


class TestRequestTracker:
    def test_set_status(self):
        t = _RequestTracker("/orders", "GET", 0)
        t.set_status(429)
        assert t._throttled

    def test_set_error(self):
        t = _RequestTracker("/orders", "GET", 0)
        t.set_error(ValueError("bad"))
        assert "ValueError" in t._error

    def test_set_cached(self):
        t = _RequestTracker("/orders", "GET", 0)
        t.set_cached(True)
        assert t._from_cache

    def test_finalize(self):
        t = _RequestTracker("/orders", "GET", 100)
        time.sleep(0.01)
        rec = t.finalize()
        assert rec.endpoint == "/orders"
        assert rec.latency_ms >= 10
        assert rec.request_size == 100


class TestMetricsReport:
    def test_text_summary(self):
        mc = MetricsCollector()
        mc.record_request("/orders", latency_ms=100)
        mc.record_request("/orders", latency_ms=200, error="fail", status_code=500)
        report = MetricsReport(mc)
        text = report.text_summary()
        assert "SP-API Metrics Report" in text
        assert "/orders" in text
        assert "Total requests" in text

    def test_export_json(self):
        mc = MetricsCollector()
        mc.record_request("/orders", latency_ms=100)
        report = MetricsReport(mc)
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = f.name
        try:
            report.export_json(path)
            with open(path) as f:
                data = json.load(f)
            assert data["global"]["total_requests"] == 1
        finally:
            os.unlink(path)

    def test_export_csv(self):
        mc = MetricsCollector()
        mc.record_request("/orders", latency_ms=100)
        mc.record_request("/catalog", latency_ms=200)
        report = MetricsReport(mc)
        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as f:
            path = f.name
        try:
            report.export_csv(path)
            with open(path) as f:
                lines = f.readlines()
            assert len(lines) == 3  # header + 2 endpoints
            assert "endpoint" in lines[0]
        finally:
            os.unlink(path)
