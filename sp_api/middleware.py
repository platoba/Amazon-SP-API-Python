"""
Request/Response middleware pipeline with circuit breaker.

Middleware functions hook into the request lifecycle:
    - before_request(method, path, params, body) → may modify or reject
    - after_response(method, path, response) → may transform
    - on_error(method, path, error) → may recover or re-raise

Built-in middleware:
    - LoggingMiddleware: structured request/response logging
    - CircuitBreaker: fail-fast when error rate exceeds threshold
    - MetricsMiddleware: request timing and counters
    - RetryBudgetMiddleware: global retry budget per time window

Usage:
    from sp_api.middleware import MiddlewarePipeline, LoggingMiddleware, CircuitBreaker

    pipeline = MiddlewarePipeline()
    pipeline.add(LoggingMiddleware(level="INFO"))
    pipeline.add(CircuitBreaker(threshold=5, reset_timeout=60))

    # Attach to client
    api = SPAPI(refresh_token=..., client_id=..., client_secret=..., middleware=pipeline)
"""

import time
import logging
import threading
from collections import deque
from typing import Any, Callable, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class Middleware:
    """Base middleware class. Override hooks as needed."""

    def before_request(
        self, method: str, path: str, params: Optional[Dict], body: Optional[Dict]
    ) -> Optional[Tuple[str, str, Optional[Dict], Optional[Dict]]]:
        """
        Called before each request.
        Return None to proceed unchanged, or (method, path, params, body) to modify.
        Raise SPAPIError to reject the request.
        """
        return None

    def after_response(
        self, method: str, path: str, response: Dict, elapsed_ms: float
    ) -> Optional[Dict]:
        """
        Called after a successful response.
        Return None to pass through, or a modified response dict.
        """
        return None

    def on_error(
        self, method: str, path: str, error: Exception, elapsed_ms: float
    ) -> Optional[Dict]:
        """
        Called on request error.
        Return None to propagate the error, or a fallback response dict.
        """
        return None


class MiddlewarePipeline:
    """Ordered pipeline of middleware hooks."""

    def __init__(self):
        self._middleware: List[Middleware] = []

    def add(self, mw: Middleware) -> "MiddlewarePipeline":
        self._middleware.append(mw)
        return self

    def remove(self, mw_type: type) -> "MiddlewarePipeline":
        self._middleware = [m for m in self._middleware if not isinstance(m, mw_type)]
        return self

    def run_before(self, method, path, params, body):
        for mw in self._middleware:
            result = mw.before_request(method, path, params, body)
            if result is not None:
                method, path, params, body = result
        return method, path, params, body

    def run_after(self, method, path, response, elapsed_ms):
        for mw in self._middleware:
            result = mw.after_response(method, path, response, elapsed_ms)
            if result is not None:
                response = result
        return response

    def run_error(self, method, path, error, elapsed_ms):
        for mw in self._middleware:
            result = mw.on_error(method, path, error, elapsed_ms)
            if result is not None:
                return result
        return None

    def __len__(self):
        return len(self._middleware)


# ── Built-in Middleware ───────────────────────────────────


class LoggingMiddleware(Middleware):
    """
    Structured request/response logging.

    Logs request method, path, timing, and status.
    Configurable log level and optional body logging.
    """

    def __init__(self, level: str = "INFO", log_body: bool = False,
                 log_params: bool = False):
        self.level = getattr(logging, level.upper(), logging.INFO)
        self.log_body = log_body
        self.log_params = log_params

    def before_request(self, method, path, params, body):
        parts = [f"→ {method} {path}"]
        if self.log_params and params:
            parts.append(f"params={params}")
        if self.log_body and body:
            parts.append(f"body_keys={list(body.keys())}")
        logger.log(self.level, " ".join(parts))
        return None

    def after_response(self, method, path, response, elapsed_ms):
        logger.log(
            self.level,
            "← %s %s [%.0fms] keys=%s",
            method, path, elapsed_ms,
            list(response.keys()) if isinstance(response, dict) else type(response).__name__,
        )
        return None

    def on_error(self, method, path, error, elapsed_ms):
        logger.error(
            "✗ %s %s [%.0fms] %s: %s",
            method, path, elapsed_ms, type(error).__name__, error,
        )
        return None


class CircuitBreaker(Middleware):
    """
    Circuit breaker pattern — fail fast when error rate is too high.

    States:
        CLOSED → normal operation, errors counted
        OPEN → all requests fail immediately
        HALF_OPEN → one test request allowed

    Usage:
        cb = CircuitBreaker(threshold=5, reset_timeout=60)
        pipeline.add(cb)
    """

    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"

    def __init__(self, threshold: int = 5, reset_timeout: float = 60.0,
                 half_open_max: int = 1):
        self.threshold = threshold
        self.reset_timeout = reset_timeout
        self.half_open_max = half_open_max

        self._state = self.CLOSED
        self._failure_count = 0
        self._last_failure_time = 0.0
        self._half_open_count = 0
        self._lock = threading.Lock()

    @property
    def state(self) -> str:
        with self._lock:
            if self._state == self.OPEN:
                if time.time() - self._last_failure_time >= self.reset_timeout:
                    self._state = self.HALF_OPEN
                    self._half_open_count = 0
            return self._state

    def before_request(self, method, path, params, body):
        state = self.state
        if state == self.OPEN:
            from sp_api.exceptions import SPAPIError
            raise SPAPIError(
                f"Circuit breaker OPEN — requests blocked for {path}. "
                f"Resets in {self.reset_timeout - (time.time() - self._last_failure_time):.0f}s"
            )
        if state == self.HALF_OPEN:
            with self._lock:
                if self._half_open_count >= self.half_open_max:
                    from sp_api.exceptions import SPAPIError
                    raise SPAPIError(
                        f"Circuit breaker HALF_OPEN — max test requests reached for {path}"
                    )
                self._half_open_count += 1
        return None

    def after_response(self, method, path, response, elapsed_ms):
        with self._lock:
            if self._state == self.HALF_OPEN:
                # Success in half-open → close
                self._state = self.CLOSED
                self._failure_count = 0
                logger.info("Circuit breaker: HALF_OPEN → CLOSED (success)")
            elif self._state == self.CLOSED:
                self._failure_count = 0
        return None

    def on_error(self, method, path, error, elapsed_ms):
        with self._lock:
            self._failure_count += 1
            self._last_failure_time = time.time()

            if self._state == self.HALF_OPEN:
                self._state = self.OPEN
                logger.warning("Circuit breaker: HALF_OPEN → OPEN (test failed)")
            elif self._failure_count >= self.threshold:
                self._state = self.OPEN
                logger.warning(
                    "Circuit breaker: CLOSED → OPEN (%d failures)",
                    self._failure_count,
                )
        return None

    def reset(self):
        """Manually reset the circuit breaker."""
        with self._lock:
            self._state = self.CLOSED
            self._failure_count = 0
            self._half_open_count = 0

    @property
    def stats(self) -> Dict:
        return {
            "state": self.state,
            "failure_count": self._failure_count,
            "threshold": self.threshold,
            "reset_timeout": self.reset_timeout,
        }


class MetricsMiddleware(Middleware):
    """
    Request metrics collector.

    Tracks per-endpoint timing, counts, and error rates.

    Usage:
        metrics = MetricsMiddleware()
        pipeline.add(metrics)
        # Later:
        print(metrics.summary())
    """

    def __init__(self, window_size: int = 1000):
        self._window_size = window_size
        self._timings: Dict[str, deque] = {}
        self._counts: Dict[str, int] = {}
        self._errors: Dict[str, int] = {}
        self._lock = threading.Lock()

    def after_response(self, method, path, response, elapsed_ms):
        key = f"{method} {path}"
        with self._lock:
            self._counts[key] = self._counts.get(key, 0) + 1
            if key not in self._timings:
                self._timings[key] = deque(maxlen=self._window_size)
            self._timings[key].append(elapsed_ms)
        return None

    def on_error(self, method, path, error, elapsed_ms):
        key = f"{method} {path}"
        with self._lock:
            self._errors[key] = self._errors.get(key, 0) + 1
            self._counts[key] = self._counts.get(key, 0) + 1
        return None

    def summary(self) -> Dict[str, Dict]:
        """Get metrics summary per endpoint."""
        result = {}
        with self._lock:
            for key in self._counts:
                timings = list(self._timings.get(key, []))
                count = self._counts[key]
                errors = self._errors.get(key, 0)
                result[key] = {
                    "total_requests": count,
                    "total_errors": errors,
                    "error_rate": f"{(errors / count * 100):.1f}%" if count else "0%",
                    "avg_ms": round(sum(timings) / len(timings), 1) if timings else 0,
                    "min_ms": round(min(timings), 1) if timings else 0,
                    "max_ms": round(max(timings), 1) if timings else 0,
                    "p95_ms": round(
                        sorted(timings)[int(len(timings) * 0.95)] if timings else 0, 1
                    ),
                }
        return result

    def reset(self):
        with self._lock:
            self._timings.clear()
            self._counts.clear()
            self._errors.clear()


class RetryBudgetMiddleware(Middleware):
    """
    Global retry budget — limits total retries in a time window.

    Prevents retry storms during widespread outages.

    Usage:
        budget = RetryBudgetMiddleware(max_retries=20, window_seconds=60)
        pipeline.add(budget)
    """

    def __init__(self, max_retries: int = 20, window_seconds: float = 60.0):
        self.max_retries = max_retries
        self.window_seconds = window_seconds
        self._retry_times: deque = deque()
        self._lock = threading.Lock()

    def _prune(self):
        cutoff = time.time() - self.window_seconds
        while self._retry_times and self._retry_times[0] < cutoff:
            self._retry_times.popleft()

    def on_error(self, method, path, error, elapsed_ms):
        with self._lock:
            self._prune()
            if len(self._retry_times) >= self.max_retries:
                from sp_api.exceptions import SPAPIError
                raise SPAPIError(
                    f"Retry budget exhausted: {self.max_retries} retries "
                    f"in {self.window_seconds}s window"
                )
            self._retry_times.append(time.time())
        return None

    @property
    def remaining(self) -> int:
        with self._lock:
            self._prune()
            return max(0, self.max_retries - len(self._retry_times))

    @property
    def stats(self) -> Dict:
        return {
            "remaining": self.remaining,
            "max_retries": self.max_retries,
            "window_seconds": self.window_seconds,
        }
