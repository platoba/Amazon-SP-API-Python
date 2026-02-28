"""
SP-API Client — main entry point.
Composes all API modules into a single client.
"""

import time
import logging
import requests

from sp_api.auth import AuthManager
from sp_api.rate_limiter import RateLimiter
from sp_api.marketplaces import ENDPOINTS, MARKETPLACES, REGION_MAP
from sp_api.exceptions import (
    SPAPIError,
    SPAPIThrottleError,
    SPAPINotFoundError,
    SPAPIValidationError,
)
from sp_api.orders import OrdersAPI
from sp_api.catalog import CatalogAPI
from sp_api.inventory import InventoryAPI
from sp_api.reports import ReportsAPI
from sp_api.finances import FinancesAPI
from sp_api.listings import ListingsAPI
from sp_api.pricing import PricingAPI
from sp_api.feeds import FeedsAPI
from sp_api.fulfillment import FulfillmentAPI
from sp_api.notifications import NotificationsAPI

logger = logging.getLogger(__name__)


class SPAPIClient(
    OrdersAPI,
    CatalogAPI,
    InventoryAPI,
    ReportsAPI,
    FinancesAPI,
    ListingsAPI,
    PricingAPI,
    FeedsAPI,
    FulfillmentAPI,
    NotificationsAPI,
):
    """
    Amazon Selling Partner API client.

    Unified access to all SP-API endpoints:
        - Catalog Items (search, details)
        - Orders (list, get, items, address, buyer info)
        - Product Pricing (competitive pricing, offers, batch)
        - Reports (create, poll, download)
        - Feeds (submit, upload, poll)
        - FBA Inventory (summaries, by-SKU)
        - Finances (events, groups, by-order)
        - Listings Items (CRUD)
        - Fulfillment Outbound / MCF (preview, create, track, returns)
        - Notifications (subscriptions, destinations)

    Usage:
        client = SPAPIClient(
            refresh_token="...",
            client_id="...",
            client_secret="...",
            marketplace="US",
        )
        orders = client.get_orders()
    """

    VERSION = "3.0.0"

    def __init__(
        self,
        refresh_token,
        client_id,
        client_secret,
        marketplace="US",
        max_retries=3,
        timeout=30,
        rate_limiter=None,
        user_agent=None,
    ):
        if marketplace not in MARKETPLACES:
            raise ValueError(
                f"Unknown marketplace: {marketplace}. "
                f"Available: {sorted(MARKETPLACES.keys())}"
            )

        self.marketplace_id, region = MARKETPLACES[marketplace]
        self.marketplace = marketplace
        self.endpoint = ENDPOINTS[region]
        self.region = REGION_MAP[region]
        self.max_retries = max_retries
        self.timeout = timeout

        # Auth
        self.auth = AuthManager(refresh_token, client_id, client_secret)

        # Rate limiter
        self.rate_limiter = rate_limiter or RateLimiter()

        # HTTP session
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": user_agent or f"Amazon-SP-API-Python/{self.VERSION}",
            "Content-Type": "application/json",
        })

        # Request stats
        self._request_count = 0
        self._error_count = 0

    # ── Core HTTP ─────────────────────────────────────────

    def _request(self, method, path, params=None, body=None, **kwargs):
        url = self.endpoint + path
        self.rate_limiter.acquire(path)
        self._request_count += 1

        headers = {"x-amz-access-token": self.auth.access_token}

        for attempt in range(1, self.max_retries + 1):
            try:
                resp = self.session.request(
                    method,
                    url,
                    params=params,
                    json=body,
                    headers=headers,
                    timeout=self.timeout,
                    **kwargs,
                )
            except requests.RequestException as e:
                self._error_count += 1
                if attempt == self.max_retries:
                    raise SPAPIError(f"Request failed after {self.max_retries} retries: {e}") from e
                wait = 2 ** attempt
                logger.warning("Request error (attempt %d/%d), retrying in %ds: %s",
                               attempt, self.max_retries, wait, e)
                time.sleep(wait)
                continue

            if resp.status_code == 429:
                retry_after = float(resp.headers.get("Retry-After", 2 ** attempt))
                if attempt == self.max_retries:
                    self._error_count += 1
                    raise SPAPIThrottleError(
                        f"Rate limited after {self.max_retries} retries",
                        retry_after=retry_after,
                        status_code=429,
                        response=resp,
                    )
                logger.warning("Throttled (429), retry in %.1fs (attempt %d/%d)",
                               retry_after, attempt, self.max_retries)
                time.sleep(retry_after)
                headers["x-amz-access-token"] = self.auth.access_token
                continue

            if resp.status_code == 401:
                # Token may have expired mid-flight
                self.auth.force_refresh()
                headers["x-amz-access-token"] = self.auth.access_token
                if attempt < self.max_retries:
                    continue

            if resp.status_code == 404:
                self._error_count += 1
                raise SPAPINotFoundError(
                    f"Not found: {path}",
                    status_code=404,
                    response=resp,
                )

            if resp.status_code == 400:
                self._error_count += 1
                raise SPAPIValidationError(
                    f"Validation error: {resp.text[:500]}",
                    status_code=400,
                    response=resp,
                )

            if resp.status_code >= 400:
                self._error_count += 1
                raise SPAPIError(
                    f"SP-API {resp.status_code}: {resp.text[:500]}",
                    status_code=resp.status_code,
                    response=resp,
                )

            return resp.json() if resp.text.strip() else {}

        raise SPAPIError("Max retries exhausted")

    def get(self, path, params=None):
        return self._request("GET", path, params=params)

    def post(self, path, body=None, params=None):
        return self._request("POST", path, params=params, body=body)

    def put(self, path, body=None, params=None):
        return self._request("PUT", path, params=params, body=body)

    def delete(self, path, params=None):
        return self._request("DELETE", path, params=params)

    # ── Stats / Info ──────────────────────────────────────

    @property
    def stats(self):
        """Return request statistics."""
        return {
            "total_requests": self._request_count,
            "total_errors": self._error_count,
            "marketplace": self.marketplace,
            "endpoint": self.endpoint,
        }

    def __repr__(self):
        return (
            f"SPAPIClient(marketplace={self.marketplace!r}, "
            f"endpoint={self.endpoint!r}, "
            f"requests={self._request_count})"
        )
