"""
SP-API Authentication Manager.
Handles OAuth2 token lifecycle with automatic refresh.
"""

import time
import threading
import logging
import requests
from sp_api.exceptions import SPAPIAuthError

logger = logging.getLogger(__name__)

TOKEN_URL = "https://api.amazon.com/auth/o2/token"


class AuthManager:
    """
    Manages SP-API OAuth2 access tokens with auto-refresh.

    Features:
        - Thread-safe token caching
        - Automatic refresh before expiry (60s buffer)
        - Configurable refresh callback
    """

    def __init__(self, refresh_token, client_id, client_secret,
                 token_url=TOKEN_URL, refresh_buffer=60):
        self.refresh_token = refresh_token
        self.client_id = client_id
        self.client_secret = client_secret
        self.token_url = token_url
        self.refresh_buffer = refresh_buffer

        self._access_token = None
        self._token_expires = 0.0
        self._lock = threading.Lock()
        self._on_refresh = None

    @property
    def access_token(self):
        """Get a valid access token, refreshing if needed."""
        if self._is_token_valid():
            return self._access_token
        return self._refresh()

    def _is_token_valid(self):
        return (
            self._access_token is not None
            and time.time() < self._token_expires - self.refresh_buffer
        )

    def _refresh(self):
        with self._lock:
            # Double-check after acquiring lock
            if self._is_token_valid():
                return self._access_token

            logger.debug("Refreshing SP-API access token...")
            try:
                resp = requests.post(self.token_url, data={
                    "grant_type": "refresh_token",
                    "refresh_token": self.refresh_token,
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                }, timeout=15)
                resp.raise_for_status()
            except requests.RequestException as e:
                raise SPAPIAuthError(f"Token refresh failed: {e}") from e

            data = resp.json()
            if "access_token" not in data:
                raise SPAPIAuthError(f"Invalid token response: {data}")

            self._access_token = data["access_token"]
            self._token_expires = time.time() + data.get("expires_in", 3600)
            logger.debug("Token refreshed, expires in %ds", data.get("expires_in", 3600))

            if self._on_refresh:
                self._on_refresh(self._access_token)

            return self._access_token

    def force_refresh(self):
        """Force an immediate token refresh."""
        self._access_token = None
        self._token_expires = 0.0
        return self._refresh()

    def on_refresh(self, callback):
        """Register a callback invoked after each token refresh."""
        self._on_refresh = callback
        return self

    def invalidate(self):
        """Invalidate the current token."""
        with self._lock:
            self._access_token = None
            self._token_expires = 0.0
