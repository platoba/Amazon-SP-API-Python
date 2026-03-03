"""Tests for retry engine — policies, circuit breaker, endpoint manager."""

import time
import pytest

from sp_api.retry import (
    BackoffStrategy,
    CircuitBreaker,
    CircuitState,
    EndpointRetryManager,
    RetryAttempt,
    RetryPolicy,
    RetryStats,
)
from sp_api.exceptions import SPAPIError, SPAPIThrottleError


class TestRetryStats:
    def test_initial_stats(self):
        stats = RetryStats()
        assert stats.total_calls == 0
        assert stats.success_rate == 0.0
        assert stats.avg_retries_per_call == 0.0

    def test_success_rate(self):
        stats = RetryStats(total_calls=10, total_successes=8, total_failures=2)
        assert stats.success_rate == 0.8

    def test_avg_retries(self):
        stats = RetryStats(total_calls=10, total_retries=30)
        assert stats.avg_retries_per_call == 3.0

    def test_to_dict(self):
        stats = RetryStats(total_calls=5, total_successes=4, total_failures=1, total_retries=3)
        d = stats.to_dict()
        assert d["total_calls"] == 5
        assert d["success_rate"] == 0.8
        assert d["avg_retries"] == 0.6


class TestRetryAttempt:
    def test_create(self):
        attempt = RetryAttempt(attempt=1, delay=0.5, error="timeout")
        assert attempt.attempt == 1
        assert attempt.delay == 0.5
        assert not attempt.success

    def test_success(self):
        attempt = RetryAttempt(attempt=0, delay=0, success=True)
        assert attempt.success


class TestRetryPolicy:
    def test_execute_success_first_try(self):
        policy = RetryPolicy(max_retries=3)
        result = policy.execute(lambda: "ok")
        assert result == "ok"
        assert policy.stats.total_successes == 1
        assert policy.stats.total_retries == 0

    def test_execute_success_after_retries(self):
        call_count = {"n": 0}
        def flaky():
            call_count["n"] += 1
            if call_count["n"] < 3:
                raise ConnectionError("fail")
            return "recovered"

        policy = RetryPolicy(max_retries=5, base_delay=0.01)
        result = policy.execute(flaky)
        assert result == "recovered"
        assert policy.stats.total_retries == 2

    def test_execute_exhausted(self):
        policy = RetryPolicy(max_retries=2, base_delay=0.01)
        with pytest.raises(ConnectionError):
            policy.execute(lambda: (_ for _ in ()).throw(ConnectionError("always fail")))
        assert policy.stats.total_failures == 1

    def test_non_retryable_error_raises_immediately(self):
        policy = RetryPolicy(max_retries=5, base_delay=0.01)
        with pytest.raises(ValueError):
            policy.execute(lambda: (_ for _ in ()).throw(ValueError("bad input")))
        assert policy.stats.total_retries == 0

    def test_exponential_backoff(self):
        policy = RetryPolicy(strategy=BackoffStrategy.EXPONENTIAL, base_delay=1.0, jitter=0)
        assert policy._compute_delay(1) == 1.0
        assert policy._compute_delay(2) == 2.0
        assert policy._compute_delay(3) == 4.0

    def test_linear_backoff(self):
        policy = RetryPolicy(strategy=BackoffStrategy.LINEAR, base_delay=1.0, jitter=0)
        assert policy._compute_delay(1) == 1.0
        assert policy._compute_delay(2) == 2.0
        assert policy._compute_delay(3) == 3.0

    def test_constant_backoff(self):
        policy = RetryPolicy(strategy=BackoffStrategy.CONSTANT, base_delay=2.0, jitter=0)
        assert policy._compute_delay(1) == 2.0
        assert policy._compute_delay(5) == 2.0

    def test_fibonacci_backoff(self):
        policy = RetryPolicy(strategy=BackoffStrategy.FIBONACCI, base_delay=1.0, jitter=0)
        assert policy._compute_delay(1) == 1.0   # fib(1) = 1
        assert policy._compute_delay(2) == 1.0   # fib(2) = 1
        assert policy._compute_delay(3) == 2.0   # fib(3) = 2
        assert policy._compute_delay(4) == 3.0   # fib(4) = 3
        assert policy._compute_delay(5) == 5.0   # fib(5) = 5

    def test_max_delay_cap(self):
        policy = RetryPolicy(base_delay=1.0, max_delay=10.0, jitter=0)
        # 2^20 would be huge, but capped
        assert policy._compute_delay(20) == 10.0

    def test_jitter_adds_variation(self):
        policy = RetryPolicy(base_delay=1.0, jitter=0.5)
        delays = {policy._compute_delay(3) for _ in range(20)}
        # With jitter, should not all be identical
        assert len(delays) > 1

    def test_throttle_error_is_retryable(self):
        policy = RetryPolicy()
        assert policy._is_retryable(SPAPIThrottleError("429"))
        assert policy._is_retryable(ConnectionError("conn refused"))
        assert not policy._is_retryable(ValueError("bad"))

    def test_history_tracking(self):
        call_count = {"n": 0}
        def flaky():
            call_count["n"] += 1
            if call_count["n"] == 1:
                raise ConnectionError("fail")
            return "ok"

        policy = RetryPolicy(max_retries=3, base_delay=0.01)
        policy.execute(flaky)
        assert len(policy.history) == 2  # 1 failure + 1 success
        assert not policy.history[0].success
        assert policy.history[1].success

    def test_reset_stats(self):
        policy = RetryPolicy()
        policy.execute(lambda: "ok")
        policy.reset_stats()
        assert policy.stats.total_calls == 0
        assert len(policy.history) == 0

    def test_decorrelated_jitter(self):
        policy = RetryPolicy(
            strategy=BackoffStrategy.DECORRELATED_JITTER,
            base_delay=1.0,
        )
        delay = policy._compute_delay(1)
        assert delay >= 1.0  # At least base_delay


class TestCircuitBreaker:
    def test_initial_state(self):
        cb = CircuitBreaker()
        assert cb.state == CircuitState.CLOSED

    def test_call_success(self):
        cb = CircuitBreaker()
        result = cb.call(lambda: "ok")
        assert result == "ok"

    def test_trips_after_threshold(self):
        cb = CircuitBreaker(failure_threshold=3)
        for _ in range(3):
            with pytest.raises(ValueError):
                cb.call(lambda: (_ for _ in ()).throw(ValueError("fail")))
        assert cb.state == CircuitState.OPEN

    def test_open_rejects_immediately(self):
        cb = CircuitBreaker(failure_threshold=1)
        with pytest.raises(ValueError):
            cb.call(lambda: (_ for _ in ()).throw(ValueError("fail")))
        assert cb.state == CircuitState.OPEN
        with pytest.raises(SPAPIError, match="OPEN"):
            cb.call(lambda: "should not run")

    def test_half_open_after_recovery_timeout(self):
        cb = CircuitBreaker(failure_threshold=1, recovery_timeout=0.05)
        with pytest.raises(ValueError):
            cb.call(lambda: (_ for _ in ()).throw(ValueError("fail")))
        assert cb.state == CircuitState.OPEN
        time.sleep(0.06)
        assert cb.state == CircuitState.HALF_OPEN

    def test_half_open_recovers_to_closed(self):
        cb = CircuitBreaker(failure_threshold=1, recovery_timeout=0.05, success_threshold=2)
        with pytest.raises(ValueError):
            cb.call(lambda: (_ for _ in ()).throw(ValueError("fail")))
        time.sleep(0.06)
        cb.call(lambda: "ok")
        cb.call(lambda: "ok")
        assert cb.state == CircuitState.CLOSED

    def test_half_open_failure_reopens(self):
        cb = CircuitBreaker(failure_threshold=1, recovery_timeout=0.05)
        with pytest.raises(ValueError):
            cb.call(lambda: (_ for _ in ()).throw(ValueError("fail")))
        time.sleep(0.06)
        assert cb.state == CircuitState.HALF_OPEN
        with pytest.raises(ValueError):
            cb.call(lambda: (_ for _ in ()).throw(ValueError("fail again")))
        assert cb.state == CircuitState.OPEN

    def test_reset(self):
        cb = CircuitBreaker(failure_threshold=1)
        with pytest.raises(ValueError):
            cb.call(lambda: (_ for _ in ()).throw(ValueError("fail")))
        cb.reset()
        assert cb.state == CircuitState.CLOSED

    def test_stats(self):
        cb = CircuitBreaker(failure_threshold=2, name="test-ep")
        cb.call(lambda: "ok")
        stats = cb.stats
        assert stats["name"] == "test-ep"
        assert stats["state"] == "closed"


class TestEndpointRetryManager:
    def test_default_policy(self):
        mgr = EndpointRetryManager()
        policy = mgr.get_policy("/orders")
        assert policy is not None

    def test_custom_policy(self):
        mgr = EndpointRetryManager()
        custom = RetryPolicy(max_retries=10)
        mgr.set_policy("/orders", custom)
        assert mgr.get_policy("/orders").max_retries == 10

    def test_execute_success(self):
        mgr = EndpointRetryManager(RetryPolicy(base_delay=0.01))
        result = mgr.execute("/orders", lambda: "ok")
        assert result == "ok"

    def test_circuit_breaker_per_endpoint(self):
        mgr = EndpointRetryManager()
        cb1 = mgr.get_circuit_breaker("/orders")
        cb2 = mgr.get_circuit_breaker("/catalog")
        assert cb1 is not cb2
        assert mgr.get_circuit_breaker("/orders") is cb1

    def test_health_report(self):
        mgr = EndpointRetryManager(RetryPolicy(base_delay=0.01))
        mgr.execute("/orders", lambda: "ok")
        report = mgr.health_report()
        assert "/orders" in report
        assert "circuit" in report["/orders"]
        assert "retry_stats" in report["/orders"]

    def test_reset_all(self):
        mgr = EndpointRetryManager(RetryPolicy(base_delay=0.01))
        mgr.execute("/orders", lambda: "ok")
        mgr.reset_all()
        report = mgr.health_report()
        for ep in report.values():
            assert ep["circuit"]["state"] == "closed"
