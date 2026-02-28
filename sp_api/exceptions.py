"""SP-API Exception classes."""


class SPAPIError(Exception):
    """Base exception for SP-API errors."""

    def __init__(self, message, status_code=None, response=None, error_code=None):
        super().__init__(message)
        self.status_code = status_code
        self.response = response
        self.error_code = error_code

    def __repr__(self):
        return f"SPAPIError(status={self.status_code}, message={str(self)})"


class SPAPIAuthError(SPAPIError):
    """Authentication/token refresh failure."""
    pass


class SPAPIThrottleError(SPAPIError):
    """Rate limit exceeded (HTTP 429)."""

    def __init__(self, message, retry_after=None, **kwargs):
        super().__init__(message, **kwargs)
        self.retry_after = retry_after


class SPAPINotFoundError(SPAPIError):
    """Resource not found (HTTP 404)."""
    pass


class SPAPIValidationError(SPAPIError):
    """Request validation error (HTTP 400)."""
    pass
