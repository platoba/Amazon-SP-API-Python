"""
Async SP-API Client — aiohttp-based for high-performance concurrent operations.

Usage:
    async with AsyncSPAPI(refresh_token=..., client_id=..., client_secret=...) as api:
        orders = await api.get_orders()
        items = await api.search_catalog("wireless earbuds")
        results = await api.gather(
            api.get_orders(),
            api.search_catalog("laptop stand"),
            api.get_inventory_summaries(),
        )
"""

import asyncio
import time
import logging
from typing import Any, Dict, List, Optional

try:
    import aiohttp
except ImportError:
    aiohttp = None  # Deferred import error

from sp_api.marketplaces import ENDPOINTS, MARKETPLACES, REGION_MAP
from sp_api.exceptions import (
    SPAPIError,
    SPAPIAuthError,
    SPAPIThrottleError,
    SPAPINotFoundError,
    SPAPIValidationError,
)

logger = logging.getLogger(__name__)


class AsyncAuthManager:
    """Async-compatible OAuth2 token manager."""

    TOKEN_URL = "https://api.amazon.com/auth/o2/token"

    def __init__(self, refresh_token: str, client_id: str, client_secret: str,
                 refresh_buffer: int = 60):
        self.refresh_token = refresh_token
        self.client_id = client_id
        self.client_secret = client_secret
        self.refresh_buffer = refresh_buffer
        self._access_token: Optional[str] = None
        self._token_expires: float = 0.0
        self._lock = asyncio.Lock()

    @property
    def is_valid(self) -> bool:
        return (
            self._access_token is not None
            and time.time() < self._token_expires - self.refresh_buffer
        )

    async def get_token(self, session: "aiohttp.ClientSession") -> str:
        if self.is_valid:
            return self._access_token
        return await self._refresh(session)

    async def _refresh(self, session: "aiohttp.ClientSession") -> str:
        async with self._lock:
            if self.is_valid:
                return self._access_token

            logger.debug("Async: Refreshing SP-API access token...")
            try:
                async with session.post(self.TOKEN_URL, data={
                    "grant_type": "refresh_token",
                    "refresh_token": self.refresh_token,
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                }, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                    resp.raise_for_status()
                    data = await resp.json()
            except Exception as e:
                raise SPAPIAuthError(f"Async token refresh failed: {e}") from e

            if "access_token" not in data:
                raise SPAPIAuthError(f"Invalid token response: {data}")

            self._access_token = data["access_token"]
            self._token_expires = time.time() + data.get("expires_in", 3600)
            return self._access_token

    async def force_refresh(self, session: "aiohttp.ClientSession") -> str:
        self._access_token = None
        self._token_expires = 0.0
        return await self._refresh(session)


class AsyncSPAPI:
    """
    Async Amazon SP-API client.

    Use as async context manager:
        async with AsyncSPAPI(...) as api:
            orders = await api.get_orders()

    Supports concurrent requests via gather():
        results = await api.gather(api.get_orders(), api.search_catalog("books"))
    """

    VERSION = "5.0.0"

    def __init__(
        self,
        refresh_token: str,
        client_id: str,
        client_secret: str,
        marketplace: str = "US",
        max_retries: int = 3,
        timeout: int = 30,
        max_concurrent: int = 10,
        user_agent: Optional[str] = None,
    ):
        if aiohttp is None:
            raise ImportError(
                "aiohttp is required for AsyncSPAPI. Install with: pip install aiohttp"
            )

        if marketplace not in MARKETPLACES:
            raise ValueError(f"Unknown marketplace: {marketplace}")

        self.marketplace_id, region = MARKETPLACES[marketplace]
        self.marketplace = marketplace
        self.endpoint = ENDPOINTS[region]
        self.region = REGION_MAP[region]
        self.max_retries = max_retries
        self.timeout = timeout
        self.max_concurrent = max_concurrent
        self._user_agent = user_agent or f"Amazon-SP-API-Python-Async/{self.VERSION}"

        self.auth = AsyncAuthManager(refresh_token, client_id, client_secret)
        self._session: Optional[aiohttp.ClientSession] = None
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._request_count = 0
        self._error_count = 0

    async def __aenter__(self):
        self._session = aiohttp.ClientSession(
            headers={
                "User-Agent": self._user_agent,
                "Content-Type": "application/json",
            },
            timeout=aiohttp.ClientTimeout(total=self.timeout),
        )
        return self

    async def __aexit__(self, *exc):
        if self._session:
            await self._session.close()
            self._session = None

    # ── Core HTTP ─────────────────────────────────────────

    async def _request(
        self,
        method: str,
        path: str,
        params: Optional[Dict] = None,
        body: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        if not self._session:
            raise RuntimeError("Use 'async with AsyncSPAPI(...) as api:' context manager")

        url = self.endpoint + path
        self._request_count += 1

        async with self._semaphore:
            for attempt in range(1, self.max_retries + 1):
                token = await self.auth.get_token(self._session)
                headers = {"x-amz-access-token": token}

                try:
                    async with self._session.request(
                        method, url, params=params, json=body, headers=headers
                    ) as resp:
                        if resp.status == 429:
                            retry_after = float(
                                resp.headers.get("Retry-After", 2 ** attempt)
                            )
                            if attempt == self.max_retries:
                                self._error_count += 1
                                raise SPAPIThrottleError(
                                    f"Rate limited after {self.max_retries} retries",
                                    retry_after=retry_after,
                                    status_code=429,
                                )
                            logger.warning(
                                "Async throttled (429), retry in %.1fs (%d/%d)",
                                retry_after, attempt, self.max_retries,
                            )
                            await asyncio.sleep(retry_after)
                            continue

                        if resp.status == 401:
                            await self.auth.force_refresh(self._session)
                            if attempt < self.max_retries:
                                continue

                        if resp.status == 404:
                            self._error_count += 1
                            raise SPAPINotFoundError(
                                f"Not found: {path}", status_code=404
                            )

                        if resp.status == 400:
                            text = await resp.text()
                            self._error_count += 1
                            raise SPAPIValidationError(
                                f"Validation error: {text[:500]}", status_code=400
                            )

                        if resp.status >= 400:
                            text = await resp.text()
                            self._error_count += 1
                            raise SPAPIError(
                                f"SP-API {resp.status}: {text[:500]}",
                                status_code=resp.status,
                            )

                        text = await resp.text()
                        if text.strip():
                            return await resp.json() if hasattr(resp, '_body') else __import__('json').loads(text)
                        return {}

                except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                    self._error_count += 1
                    if attempt == self.max_retries:
                        raise SPAPIError(
                            f"Request failed after {self.max_retries} retries: {e}"
                        ) from e
                    wait = 2 ** attempt
                    logger.warning(
                        "Async request error (%d/%d), retrying in %ds: %s",
                        attempt, self.max_retries, wait, e,
                    )
                    await asyncio.sleep(wait)

        raise SPAPIError("Max retries exhausted")

    async def get(self, path: str, params: Optional[Dict] = None) -> Dict:
        return await self._request("GET", path, params=params)

    async def post(self, path: str, body: Optional[Dict] = None,
                   params: Optional[Dict] = None) -> Dict:
        return await self._request("POST", path, params=params, body=body)

    async def put(self, path: str, body: Optional[Dict] = None,
                  params: Optional[Dict] = None) -> Dict:
        return await self._request("PUT", path, params=params, body=body)

    async def delete(self, path: str, params: Optional[Dict] = None) -> Dict:
        return await self._request("DELETE", path, params=params)

    # ── Concurrency Helper ────────────────────────────────

    @staticmethod
    async def gather(*coroutines) -> List[Any]:
        """Run multiple API calls concurrently."""
        return await asyncio.gather(*coroutines, return_exceptions=True)

    # ── Orders ────────────────────────────────────────────

    async def get_orders(self, created_after=None, order_statuses=None,
                         max_results=100, next_token=None, **kwargs):
        import datetime
        if not created_after:
            created_after = (
                datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=7)
            ).strftime("%Y-%m-%dT%H:%M:%SZ")
        params = {
            "MarketplaceIds": self.marketplace_id,
            "CreatedAfter": created_after,
            "MaxResultsPerPage": min(max_results, 100),
        }
        if order_statuses:
            params["OrderStatuses"] = ",".join(order_statuses)
        if next_token:
            params["NextToken"] = next_token
        params.update(kwargs)
        return await self.get("/orders/v0/orders", params)

    async def get_order(self, order_id: str):
        return await self.get(f"/orders/v0/orders/{order_id}")

    async def get_order_items(self, order_id: str, next_token=None):
        params = {}
        if next_token:
            params["NextToken"] = next_token
        return await self.get(f"/orders/v0/orders/{order_id}/orderItems", params or None)

    # ── Catalog ───────────────────────────────────────────

    async def search_catalog(self, keywords: str, included_data=None,
                             page_size=20, **kwargs):
        params = {
            "marketplaceIds": self.marketplace_id,
            "keywords": keywords,
            "includedData": included_data or "summaries,images,salesRanks",
            "pageSize": min(page_size, 20),
        }
        params.update(kwargs)
        return await self.get("/catalog/2022-04-01/items", params)

    async def get_catalog_item(self, asin: str, included_data=None, **kwargs):
        params = {
            "marketplaceIds": self.marketplace_id,
            "includedData": included_data or "summaries,images,salesRanks,attributes",
        }
        params.update(kwargs)
        return await self.get(f"/catalog/2022-04-01/items/{asin}", params)

    # ── Inventory ─────────────────────────────────────────

    async def get_inventory_summaries(self, granularity_type="Marketplace",
                                      next_token=None, seller_skus=None, **kwargs):
        params = {
            "granularityType": granularity_type,
            "granularityId": self.marketplace_id,
            "marketplaceIds": self.marketplace_id,
        }
        if next_token:
            params["nextToken"] = next_token
        if seller_skus:
            params["sellerSkus"] = ",".join(seller_skus) if isinstance(seller_skus, list) else seller_skus
        params.update(kwargs)
        return await self.get("/fba/inventory/v1/summaries", params)

    # ── Pricing ───────────────────────────────────────────

    async def get_competitive_pricing(self, asins=None, skus=None):
        params = {"MarketplaceId": self.marketplace_id, "ItemType": "Asin"}
        if asins:
            params["Asins"] = ",".join(asins) if isinstance(asins, list) else asins
        elif skus:
            params["ItemType"] = "Sku"
            params["SellerSKUs"] = ",".join(skus) if isinstance(skus, list) else skus
        return await self.get("/products/pricing/v0/competitivePrice", params)

    async def get_item_offers(self, asin: str, item_condition="New"):
        params = {
            "MarketplaceId": self.marketplace_id,
            "ItemCondition": item_condition,
        }
        return await self.get(f"/products/pricing/v0/items/{asin}/offers", params)

    # ── Reports ───────────────────────────────────────────

    async def create_report(self, report_type: str, marketplace_ids=None,
                            data_start=None, data_end=None):
        body = {
            "reportType": report_type,
            "marketplaceIds": marketplace_ids or [self.marketplace_id],
        }
        if data_start:
            body["dataStartTime"] = data_start
        if data_end:
            body["dataEndTime"] = data_end
        return await self.post("/reports/2021-06-30/reports", body=body)

    async def get_report(self, report_id: str):
        return await self.get(f"/reports/2021-06-30/reports/{report_id}")

    # ── Sellers ───────────────────────────────────────────

    async def get_marketplace_participations(self):
        return await self.get("/sellers/v1/marketplaceParticipations")

    # ── Finances ──────────────────────────────────────────

    async def list_financial_events(self, posted_after=None, posted_before=None,
                                    next_token=None, max_results=100):
        params = {"MaxResultsPerPage": min(max_results, 100)}
        if posted_after:
            params["PostedAfter"] = posted_after
        if posted_before:
            params["PostedBefore"] = posted_before
        if next_token:
            params["NextToken"] = next_token
        return await self.get("/finances/v0/financialEvents", params)

    # ── Stats ─────────────────────────────────────────────

    @property
    def stats(self) -> Dict:
        return {
            "total_requests": self._request_count,
            "total_errors": self._error_count,
            "marketplace": self.marketplace,
            "endpoint": self.endpoint,
            "max_concurrent": self.max_concurrent,
        }

    def __repr__(self):
        return (
            f"AsyncSPAPI(marketplace={self.marketplace!r}, "
            f"requests={self._request_count}, concurrent={self.max_concurrent})"
        )
