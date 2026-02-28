"""
Auto-pagination iterators for SP-API responses.

Handles NextToken-based pagination across all endpoints:

    # Sync iteration
    for order in paginate(api, api.get_orders):
        print(order)

    # Async iteration
    async for item in async_paginate(api, api.get_inventory_summaries):
        print(item)

    # Collect all pages
    all_orders = list(paginate(api, api.get_orders))

    # With limit
    first_500 = list(paginate(api, api.get_orders, max_items=500))
"""

import logging
from typing import Any, Callable, Dict, Iterator, List, Optional

logger = logging.getLogger(__name__)


# ── Token extraction strategies ──────────────────────────

def _find_next_token(response: Dict) -> Optional[str]:
    """Extract NextToken from various SP-API response structures."""
    # Direct NextToken
    if "NextToken" in response:
        return response["NextToken"]
    if "nextToken" in response:
        return response["nextToken"]

    # Nested in payload
    payload = response.get("payload", {})
    if isinstance(payload, dict):
        if "NextToken" in payload:
            return payload["NextToken"]
        if "nextToken" in payload:
            return payload["nextToken"]

    # Nested in pagination
    pagination = (
        response.get("pagination", {})
        or payload.get("pagination", {})
        or {}
    )
    if isinstance(pagination, dict):
        if "nextToken" in pagination:
            return pagination["nextToken"]
        if "NextToken" in pagination:
            return pagination["NextToken"]

    return None


def _find_items(response: Dict, item_key: Optional[str] = None) -> List[Any]:
    """Extract the list of items from an SP-API response."""
    # If response is already a list, return it directly
    if isinstance(response, list):
        return response

    # Explicit key
    if item_key and isinstance(response, dict) and item_key in response:
        return response[item_key]

    payload = response.get("payload", response) if isinstance(response, dict) else response
    if isinstance(payload, dict):
        if item_key and item_key in payload:
            return payload[item_key]
        # Auto-detect: find the first list value
        for key, value in payload.items():
            if isinstance(value, list):
                return value

    # Items / items
    for key in ("items", "Items", "orders", "Orders", "inventorySummaries",
                "orderItems", "OrderItems", "reports", "financialEvents"):
        if key in response:
            return response[key]
        if isinstance(payload, dict) and key in payload:
            return payload[key]

    return []


# ── Sync Paginator ────────────────────────────────────────

class Paginator:
    """
    Sync auto-pagination iterator.

    Usage:
        for order in Paginator(api.get_orders):
            process(order)

        # With parameters
        for item in Paginator(api.search_catalog, keywords="laptop"):
            process(item)

        # With max items
        pager = Paginator(api.get_orders, max_items=200)
        orders = list(pager)
    """

    def __init__(
        self,
        method: Callable,
        *args,
        item_key: Optional[str] = None,
        max_items: Optional[int] = None,
        max_pages: Optional[int] = None,
        **kwargs,
    ):
        self._method = method
        self._args = args
        self._kwargs = kwargs
        self._item_key = item_key
        self._max_items = max_items
        self._max_pages = max_pages
        self._pages_fetched = 0
        self._items_yielded = 0
        self._total_items = 0

    def __iter__(self) -> Iterator[Any]:
        next_token = None
        page = 0

        while True:
            if self._max_pages and page >= self._max_pages:
                break

            kwargs = dict(self._kwargs)
            if next_token:
                kwargs["next_token"] = next_token

            response = self._method(*self._args, **kwargs)
            page += 1
            self._pages_fetched = page

            items = _find_items(response, self._item_key)
            for item in items:
                if self._max_items and self._items_yielded >= self._max_items:
                    return
                yield item
                self._items_yielded += 1
                self._total_items += 1

            next_token = _find_next_token(response)
            if not next_token:
                break

            logger.debug(
                "Paginator: page %d complete, %d items so far, fetching next...",
                page, self._total_items,
            )

    @property
    def stats(self) -> Dict:
        return {
            "pages_fetched": self._pages_fetched,
            "total_items": self._total_items,
        }


class AsyncPaginator:
    """
    Async auto-pagination iterator.

    Usage:
        async for item in AsyncPaginator(async_api.get_orders):
            process(item)
    """

    def __init__(
        self,
        method: Callable,
        *args,
        item_key: Optional[str] = None,
        max_items: Optional[int] = None,
        max_pages: Optional[int] = None,
        **kwargs,
    ):
        self._method = method
        self._args = args
        self._kwargs = kwargs
        self._item_key = item_key
        self._max_items = max_items
        self._max_pages = max_pages
        self._pages_fetched = 0
        self._items_yielded = 0

    def __aiter__(self):
        return self._iterate()

    async def _iterate(self):
        next_token = None
        page = 0

        while True:
            if self._max_pages and page >= self._max_pages:
                break

            kwargs = dict(self._kwargs)
            if next_token:
                kwargs["next_token"] = next_token

            response = await self._method(*self._args, **kwargs)
            page += 1
            self._pages_fetched = page

            items = _find_items(response, self._item_key)
            for item in items:
                if self._max_items and self._items_yielded >= self._max_items:
                    return
                yield item
                self._items_yielded += 1

            next_token = _find_next_token(response)
            if not next_token:
                break

    @property
    def stats(self) -> Dict:
        return {
            "pages_fetched": self._pages_fetched,
            "total_items": self._items_yielded,
        }


# ── Convenience functions ─────────────────────────────────

def paginate(method: Callable, *args, **kwargs) -> Paginator:
    """
    Create a sync paginator.

    Usage:
        for order in paginate(api.get_orders):
            print(order)

        for item in paginate(api.search_catalog, keywords="laptop", max_items=100):
            print(item)
    """
    return Paginator(method, *args, **kwargs)


def async_paginate(method: Callable, *args, **kwargs) -> AsyncPaginator:
    """
    Create an async paginator.

    Usage:
        async for item in async_paginate(api.get_orders):
            print(item)
    """
    return AsyncPaginator(method, *args, **kwargs)
