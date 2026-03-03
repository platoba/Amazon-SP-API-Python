"""Tests for middleware module."""

import time
import pytest

from sp_api.middleware import (
    Middleware,
    MiddlewarePipeline,
    LoggingMiddleware,
    CircuitBreaker,
    MetricsMiddleware,
    RetryBudgetMiddleware,
)


class TestMiddleware:
    """Tests for base Middleware class."""

    def test_before_request_returns_none(self):
        mw = Middleware()
        assert mw.before_request("GET", "/test", None, None) is None

    def test_after_response_returns_none(self):
        mw = Middleware()
        assert mw.after_response("GET", "/test", {}, 100) is None

    def test_on_error_returns_none(self):
        mw = Middleware()
        assert mw.on_error("GET", "/test", Exception("x"), 100) is None


class TestMiddlewarePipeline:
    """Tests for MiddlewarePipeline."""

    def test_add(self):
        pipeline = MiddlewarePipeline()
        mw = Middleware()
        pipeline.add(mw)
        assert len(pipeline) == 1

    def test_remove(self):
        pipeline = MiddlewarePipeline()
        pipeline.add(LoggingMiddleware())
        pipeline.add(CircuitBreaker())
        pipeline.remove(LoggingMiddleware)
        assert len(pipeline) == 1

    def test_run_before(self):
        pipeline = MiddlewarePipeline()
        pipeline.add(Middleware())
        result = pipeline.run_before("GET", "/test", None, None)
        assert result == ("GET", "/test", None, None)

    def test_run_before_modifies(self):
        class ModifyMiddleware(Middleware):
            def before_request(self, method, path, params, body):
                return ("POST", "/modified", {"key": "val"}, None)

        pipeline = MiddlewarePipeline()
        pipeline.add(ModifyMiddleware())
        result = pipeline.run_before("GET", "/test", None, None)
        assert result == ("POST", "/modified", {"key": "val"}, None)

    def test_run_after(self):
        pipeline = MiddlewarePipeline()
        pipeline.add(Middleware())
        result = pipeline.run_after("GET", "/test", {"data": 1}, 50.0)
        assert result == {"data": 1}

    def test_run_error_returns_none(self):
        pipeline = MiddlewarePipeline()
        pipeline.add(Middleware())
        result = pipeline.run_error("GET", "/test", Exception("e"), 100)
        assert result is None

    def test_run_error_with_fallback(self):
        class RecoverMiddleware(Middleware):
            def on_error(self, method, path, error, elapsed_ms):
                return {"fallback": True}

        pipeline = MiddlewarePipeline()
        pipeline.add(RecoverMiddleware())
        result = pipeline.run_error("GET", "/test", Exception("e"), 100)
        assert result == {"fallback": True}


class TestLoggingMiddleware:
    """Tests for LoggingMiddleware."""

    def test_init_default(self):
        mw = LoggingMiddleware()
        assert mw.log_body is False
        assert mw.log_params is False

    def test_init_custom(self):
        mw = LoggingMiddleware(level="DEBUG", log_body=True, log_params=True)
        assert mw.log_body is True
        assert mw.log_params is True

    def test_before_request_returns_none(self):
        mw = LoggingMiddleware()
        assert mw.before_request("GET", "/test", None, None) is None

    def test_after_response_returns_none(self):
        mw = LoggingMiddleware()
        assert mw.after_response("GET", "/test", {"key": "val"}, 50) is None

    def test_on_error_returns_none(self):
        mw = LoggingMiddleware()
        assert mw.on_error("GET", "/test", Exception("err"), 100) is None


class TestCircuitBreaker:
    """Tests for CircuitBreaker."""

    def test_init_closed(self):
        cb = CircuitBreaker(threshold=5, reset_timeout=60)
        assert cb.state == "closed"

    def test_closed_allows_requests(self):
        cb = CircuitBreaker(threshold=3)
        assert cb.before_request("GET", "/test", None, None) is None

    def test_opens_after_threshold(self):
        cb = CircuitBreaker(threshold=3, reset_timeout=60)
        for _ in range(3):
            cb.on_error("GET", "/test", Exception("err"), 100)
        assert cb.state == "open"

    def test_open_blocks_requests(self):
        from sp_api.exceptions import SPAPIError
        cb = CircuitBreaker(threshold=1, reset_timeout=60)
        cb.on_error("GET", "/test", Exception("err"), 100)
        with pytest.raises(SPAPIError, match="Circuit breaker OPEN"):
            cb.before_request("GET", "/test", None, None)

    def test_half_open_after_timeout(self):
        cb = CircuitBreaker(threshold=1, reset_timeout=0.01)
        cb.on_error("GET", "/test", Exception("err"), 100)
        assert cb.state == "open"
        time.sleep(0.02)
        assert cb.state == "half_open"

    def test_success_closes_from_half_open(self):
        cb = CircuitBreaker(threshold=1, reset_timeout=0.01)
        cb.on_error("GET", "/test", Exception("err"), 100)
        time.sleep(0.02)
        # Half open — allow one request
        cb.before_request("GET", "/test", None, None)
        # Success closes it
        cb.after_response("GET", "/test", {}, 50)
        assert cb.state == "closed"

    def test_failure_in_half_open_reopens(self):
        cb = CircuitBreaker(threshold=1, reset_timeout=0.01)
        cb.on_error("GET", "/test", Exception("err"), 100)
        time.sleep(0.02)
        cb.before_request("GET", "/test", None, None)
        cb.on_error("GET", "/test", Exception("again"), 100)
        assert cb.state == "open"

    def test_reset(self):
        cb = CircuitBreaker(threshold=1)
        cb.on_error("GET", "/test", Exception("err"), 100)
        assert cb.state == "open"
        cb.reset()
        assert cb.state == "closed"

    def test_stats(self):
        cb = CircuitBreaker(threshold=5, reset_timeout=60)
        stats = cb.stats
        assert stats["state"] == "closed"
        assert stats["threshold"] == 5
        assert stats["failure_count"] == 0

    def test_success_resets_count(self):
        cb = CircuitBreaker(threshold=5)
        cb.on_error("GET", "/test", Exception("err"), 100)
        cb.on_error("GET", "/test", Exception("err"), 100)
        assert cb._failure_count == 2
        cb.after_response("GET", "/test", {}, 50)
        assert cb._failure_count == 0


class TestMetricsMiddleware:
    """Tests for MetricsMiddleware."""

    def test_init(self):
        m = MetricsMiddleware()
        assert m.summary() == {}

    def test_tracks_response(self):
        m = MetricsMiddleware()
        m.after_response("GET", "/orders", {}, 150.0)
        m.after_response("GET", "/orders", {}, 200.0)
        summary = m.summary()
        assert "GET /orders" in summary
        assert summary["GET /orders"]["total_requests"] == 2
        assert summary["GET /orders"]["avg_ms"] == 175.0

    def test_tracks_errors(self):
        m = MetricsMiddleware()
        m.after_response("GET", "/test", {}, 50)
        m.on_error("GET", "/test", Exception("err"), 100)
        summary = m.summary()
        assert summary["GET /test"]["total_errors"] == 1
        assert summary["GET /test"]["total_requests"] == 2

    def test_p95(self):
        m = MetricsMiddleware()
        for i in range(100):
            m.after_response("GET", "/p95", {}, float(i))
        summary = m.summary()
        assert summary["GET /p95"]["p95_ms"] >= 90

    def test_reset(self):
        m = MetricsMiddleware()
        m.after_response("GET", "/test", {}, 50)
        m.reset()
        assert m.summary() == {}

    def test_error_rate(self):
        m = MetricsMiddleware()
        m.after_response("GET", "/api", {}, 50)
        m.on_error("GET", "/api", Exception("e"), 100)
        summary = m.summary()
        assert summary["GET /api"]["error_rate"] == "50.0%"


class TestRetryBudgetMiddleware:
    """Tests for RetryBudgetMiddleware."""

    def test_init(self):
        rb = RetryBudgetMiddleware(max_retries=10, window_seconds=60)
        assert rb.remaining == 10

    def test_consumes_budget(self):
        rb = RetryBudgetMiddleware(max_retries=3, window_seconds=60)
        rb.on_error("GET", "/test", Exception("err"), 100)
        assert rb.remaining == 2

    def test_exhausts_budget(self):
        from sp_api.exceptions import SPAPIError
        rb = RetryBudgetMiddleware(max_retries=2, window_seconds=60)
        rb.on_error("GET", "/test", Exception("err"), 100)
        rb.on_error("GET", "/test", Exception("err"), 100)
        with pytest.raises(SPAPIError, match="Retry budget exhausted"):
            rb.on_error("GET", "/test", Exception("err"), 100)

    def test_budget_recovers_after_window(self):
        rb = RetryBudgetMiddleware(max_retries=1, window_seconds=0.01)
        rb.on_error("GET", "/test", Exception("err"), 100)
        assert rb.remaining == 0
        time.sleep(0.02)
        assert rb.remaining == 1

    def test_stats(self):
        rb = RetryBudgetMiddleware(max_retries=10, window_seconds=30)
        stats = rb.stats
        assert stats["remaining"] == 10
        assert stats["max_retries"] == 10
        assert stats["window_seconds"] == 30
