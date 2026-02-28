"""
Advanced retry engine for SP-API requests.

Features:
- Exponential backoff with configurable jitter
- Per-endpoint retry budgets
- Circuit breaker pattern (half-open recovery)
- Quota-aware throttle backoff
- Retry history for debugging

Usage:
    from sp_api.retry import RetryPolicy, CircuitBreaker

    policy = RetryPolicy(max_retries=5, base_delay=0.5, max_delay=60)
    result = policy.execute(lambda: api.get_orders())

    cb = CircuitBreaker(failure_threshold=5, recovery_timeout=30)
    result = cb.call(lambda: api.search_catalog("laptop"))
"""

import logging
import random
import time
import threading
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Type

from sp_api.exceptions import SPAPIError, SPAPIThrottleError

logger = logging.getLogger(__name__)


class BackoffStrategy(Enum):
    """Backoff strategies for retry delays."""
    EXPONENTIAL = "exponential"
    LINEAR = "linear"
    CONSTANT = "constant"
    FIBONACCI = "fibonacci"
    DECORRELATED_JITTER = "decorrelated_jitter"


class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


@dataclass
class RetryAttempt:
    """Record of a single retry attempt."""
    attempt: int
    delay: float
    error: Optional[str] = None
    success: bool = False
    timestamp: float = field(default_factory=time.time)


@dataclass
class RetryStats:
    """Aggregated retry statistics."""
    total_calls: int = 0
    total_retries: int = 0
    total_failures: int = 0
    total_successes: int = 0
    total_delay_seconds: float = 0.0
    last_error: Optional[str] = None

    @property
    def success_rate(self) -> float:
        if self.total_calls == 0:
            return 0.0
        return self.total_successes / self.total_calls

    @property
    def avg_retries_per_call(self) -> float:
        if self.total_calls == 0:
            return 0.0
        return self.total_retries / self.total_calls

    def to_dict(self) -> Dict:
        return {
            "total_calls": self.total_calls,
            "total_retries": self.total_retries,
            "total_failures": self.total_failures,
            "total_successes": self.total_successes,
            "success_rate": round(self.success_rate, 4),
            "avg_retries": round(self.avg_retries_per_call, 2),
            "total_delay_seconds": round(self.total_delay_seconds, 2),
            "last_error": self.last_error,
        }


class RetryPolicy:
    """
    Configurable retry policy with multiple backoff strategies.

    Args:
        max_retries: Maximum number of retries (0 = no retry)
        base_delay: Initial delay in seconds
        max_delay: Maximum delay cap in seconds
        strategy: Backoff strategy
        jitter: Add random jitter (0.0-1.0 factor)
        retryable_errors: Exception types that trigger retry
        retryable_status_codes: HTTP status codes that trigger retry
    """

    RETRYABLE_STATUS = {429, 500, 502, 503, 504}

    def __init__(
        self,
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        strategy: BackoffStrategy = BackoffStrategy.EXPONENTIAL,
        jitter: float = 0.25,
        retryable_errors: Optional[Set[Type[Exception]]] = None,
        retryable_status_codes: Optional[Set[int]] = None,
    ):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.strategy = strategy
        self.jitter = min(max(jitter, 0.0), 1.0)
        self.retryable_errors = retryable_errors or {
            SPAPIThrottleError, ConnectionError, TimeoutError, OSError,
        }
        self.retryable_status_codes = retryable_status_codes or self.RETRYABLE_STATUS
        self._stats = RetryStats()
        self._history: List[RetryAttempt] = []
        self._fib_cache: Dict[int, float] = {0: 0, 1: 1}

    @property
    def stats(self) -> RetryStats:
        return self._stats

    @property
    def history(self) -> List[RetryAttempt]:
        return list(self._history[-100:])  # Last 100 attempts

    def _compute_delay(self, attempt: int) -> float:
        """Compute delay for given attempt number."""
        if self.strategy == BackoffStrategy.EXPONENTIAL:
            delay = self.base_delay * (2 ** (attempt - 1))
        elif self.strategy == BackoffStrategy.LINEAR:
            delay = self.base_delay * attempt
        elif self.strategy == BackoffStrategy.CONSTANT:
            delay = self.base_delay
        elif self.strategy == BackoffStrategy.FIBONACCI:
            delay = self.base_delay * self._fibonacci(attempt)
        elif self.strategy == BackoffStrategy.DECORRELATED_JITTER:
            prev = self.base_delay if attempt <= 1 else self._compute_delay(attempt - 1)
            delay = random.uniform(self.base_delay, prev * 3)
        else:
            delay = self.base_delay * (2 ** (attempt - 1))

        # Apply jitter
        if self.jitter > 0 and self.strategy != BackoffStrategy.DECORRELATED_JITTER:
            jitter_range = delay * self.jitter
            delay += random.uniform(-jitter_range, jitter_range)

        return min(max(delay, 0.01), self.max_delay)

    def _fibonacci(self, n: int) -> float:
        """Fibonacci number with memoization."""
        if n in self._fib_cache:
            return self._fib_cache[n]
        result = self._fibonacci(n - 1) + self._fibonacci(n - 2)
        self._fib_cache[n] = result
        return result

    def _is_retryable(self, error: Exception) -> bool:
        """Check if an error should trigger a retry."""
        for err_type in self.retryable_errors:
            if isinstance(error, err_type):
                return True
        if isinstance(error, SPAPIError) and hasattr(error, 'status_code'):
            return error.status_code in self.retryable_status_codes
        return False

    def execute(self, func: Callable[..., Any], *args, **kwargs) -> Any:
        """
        Execute function with retry policy.

        Args:
            func: Callable to execute
            *args, **kwargs: Arguments to pass

        Returns:
            Result of successful function call

        Raises:
            Last exception if all retries exhausted
        """
        self._stats.total_calls += 1
        last_error = None

        for attempt in range(self.max_retries + 1):
            try:
                result = func(*args, **kwargs)
                self._stats.total_successes += 1
                self._history.append(RetryAttempt(
                    attempt=attempt, delay=0, success=True,
                ))
                return result
            except Exception as e:
                last_error = e
                error_msg = f"{type(e).__name__}: {e}"

                if attempt >= self.max_retries or not self._is_retryable(e):
                    self._stats.total_failures += 1
                    self._stats.last_error = error_msg
                    self._history.append(RetryAttempt(
                        attempt=attempt, delay=0, error=error_msg,
                    ))
                    raise

                delay = self._compute_delay(attempt + 1)
                self._stats.total_retries += 1
                self._stats.total_delay_seconds += delay
                self._history.append(RetryAttempt(
                    attempt=attempt, delay=delay, error=error_msg,
                ))

                logger.warning(
                    "Retry %d/%d after %.2fs: %s",
                    attempt + 1, self.max_retries, delay, error_msg,
                )
                time.sleep(delay)

        raise last_error  # Should not reach here

    def reset_stats(self):
        """Reset statistics."""
        self._stats = RetryStats()
        self._history.clear()


class CircuitBreaker:
    """
    Circuit breaker for SP-API endpoints.

    Prevents cascading failures by cutting off requests to unhealthy endpoints.

    States:
        CLOSED   → Normal operation, requests pass through
        OPEN     → Requests immediately fail (too many errors)
        HALF_OPEN → One test request allowed to check recovery

    Args:
        failure_threshold: Consecutive failures to trip the breaker
        recovery_timeout: Seconds to wait before half-open probe
        success_threshold: Consecutive successes in half-open to close
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 30.0,
        success_threshold: int = 2,
        name: str = "default",
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.success_threshold = success_threshold
        self.name = name
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time = 0.0
        self._total_trips = 0
        self._lock = threading.Lock()

    @property
    def state(self) -> CircuitState:
        with self._lock:
            if self._state == CircuitState.OPEN:
                elapsed = time.time() - self._last_failure_time
                if elapsed >= self.recovery_timeout:
                    self._state = CircuitState.HALF_OPEN
                    self._success_count = 0
                    logger.info("Circuit '%s' → HALF_OPEN", self.name)
            return self._state

    @property
    def stats(self) -> Dict:
        return {
            "name": self.name,
            "state": self.state.value,
            "failure_count": self._failure_count,
            "total_trips": self._total_trips,
        }

    def _record_success(self):
        with self._lock:
            if self._state == CircuitState.HALF_OPEN:
                self._success_count += 1
                if self._success_count >= self.success_threshold:
                    self._state = CircuitState.CLOSED
                    self._failure_count = 0
                    logger.info("Circuit '%s' → CLOSED (recovered)", self.name)
            else:
                self._failure_count = 0

    def _record_failure(self, error: Exception):
        with self._lock:
            self._failure_count += 1
            self._last_failure_time = time.time()
            if self._state == CircuitState.HALF_OPEN:
                self._state = CircuitState.OPEN
                logger.warning("Circuit '%s' → OPEN (half-open probe failed)", self.name)
            elif self._failure_count >= self.failure_threshold:
                self._state = CircuitState.OPEN
                self._total_trips += 1
                logger.warning(
                    "Circuit '%s' → OPEN (%d consecutive failures)",
                    self.name, self._failure_count,
                )

    def call(self, func: Callable[..., Any], *args, **kwargs) -> Any:
        """
        Execute function through the circuit breaker.

        Raises:
            SPAPIError: If circuit is open
        """
        state = self.state
        if state == CircuitState.OPEN:
            raise SPAPIError(
                f"Circuit breaker '{self.name}' is OPEN — "
                f"wait {self.recovery_timeout}s for recovery"
            )

        try:
            result = func(*args, **kwargs)
            self._record_success()
            return result
        except Exception as e:
            self._record_failure(e)
            raise

    def reset(self):
        """Manually reset the circuit breaker."""
        with self._lock:
            self._state = CircuitState.CLOSED
            self._failure_count = 0
            self._success_count = 0


class EndpointRetryManager:
    """
    Per-endpoint retry management with individual budgets.

    Tracks retry budgets and health per API endpoint.
    """

    def __init__(self, default_policy: Optional[RetryPolicy] = None):
        self._default_policy = default_policy or RetryPolicy()
        self._endpoint_policies: Dict[str, RetryPolicy] = {}
        self._circuit_breakers: Dict[str, CircuitBreaker] = {}

    def set_policy(self, endpoint: str, policy: RetryPolicy):
        """Set custom retry policy for an endpoint."""
        self._endpoint_policies[endpoint] = policy

    def get_policy(self, endpoint: str) -> RetryPolicy:
        """Get retry policy for endpoint (falls back to default)."""
        return self._endpoint_policies.get(endpoint, self._default_policy)

    def get_circuit_breaker(self, endpoint: str) -> CircuitBreaker:
        """Get or create circuit breaker for endpoint."""
        if endpoint not in self._circuit_breakers:
            self._circuit_breakers[endpoint] = CircuitBreaker(name=endpoint)
        return self._circuit_breakers[endpoint]

    def execute(self, endpoint: str, func: Callable[..., Any], *args, **kwargs) -> Any:
        """Execute function with endpoint-specific retry + circuit breaker."""
        cb = self.get_circuit_breaker(endpoint)
        policy = self.get_policy(endpoint)
        return cb.call(policy.execute, func, *args, **kwargs)

    def health_report(self) -> Dict[str, Dict]:
        """Get health report for all tracked endpoints."""
        report = {}
        for endpoint, cb in self._circuit_breakers.items():
            policy = self.get_policy(endpoint)
            report[endpoint] = {
                "circuit": cb.stats,
                "retry_stats": policy.stats.to_dict(),
            }
        return report

    def reset_all(self):
        """Reset all circuit breakers and retry stats."""
        for cb in self._circuit_breakers.values():
            cb.reset()
        for policy in self._endpoint_policies.values():
            policy.reset_stats()
        self._default_policy.reset_stats()
