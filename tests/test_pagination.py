"""Tests for pagination module."""

import pytest
from sp_api.pagination import (
    Paginator,
    AsyncPaginator,
    paginate,
    async_paginate,
    _find_next_token,
    _find_items,
)


class TestFindNextToken:
    """Tests for _find_next_token extraction."""

    def test_direct_next_token(self):
        assert _find_next_token({"NextToken": "abc"}) == "abc"

    def test_direct_lowercase(self):
        assert _find_next_token({"nextToken": "xyz"}) == "xyz"

    def test_in_payload(self):
        assert _find_next_token({"payload": {"NextToken": "tok1"}}) == "tok1"

    def test_in_pagination(self):
        assert _find_next_token({"pagination": {"nextToken": "tok2"}}) == "tok2"

    def test_in_payload_pagination(self):
        resp = {"payload": {"pagination": {"nextToken": "tok3"}}}
        assert _find_next_token(resp) == "tok3"

    def test_no_token(self):
        assert _find_next_token({"data": "value"}) is None

    def test_empty_response(self):
        assert _find_next_token({}) is None


class TestFindItems:
    """Tests for _find_items extraction."""

    def test_explicit_key(self):
        resp = {"Orders": [1, 2, 3], "other": "data"}
        assert _find_items(resp, "Orders") == [1, 2, 3]

    def test_in_payload(self):
        resp = {"payload": {"Orders": [1, 2]}}
        assert _find_items(resp, "Orders") == [1, 2]

    def test_auto_detect_list(self):
        resp = {"payload": {"someKey": "val", "results": [4, 5, 6]}}
        assert _find_items(resp) == [4, 5, 6]

    def test_items_key(self):
        resp = {"items": [7, 8, 9]}
        assert _find_items(resp) == [7, 8, 9]

    def test_orders_key(self):
        resp = {"payload": {"orders": [10, 11]}}
        assert _find_items(resp) == [10, 11]

    def test_inventory_summaries(self):
        resp = {"payload": {"inventorySummaries": [{"sku": "A"}]}}
        assert _find_items(resp) == [{"sku": "A"}]

    def test_empty_response(self):
        assert _find_items({}) == []

    def test_list_response(self):
        assert _find_items([1, 2, 3]) == [1, 2, 3]


class TestPaginator:
    """Tests for sync Paginator."""

    def _make_mock_method(self, pages):
        """Create a mock paginated method."""
        call_count = 0
        def method(**kwargs):
            nonlocal call_count
            next_token = kwargs.get("next_token")
            idx = call_count if not next_token else int(next_token.split("_")[1])
            call_count += 1
            page_data = pages[idx]
            return page_data
        return method

    def test_single_page(self):
        def method(**kwargs):
            return {"items": [1, 2, 3]}

        result = list(Paginator(method))
        assert result == [1, 2, 3]

    def test_multi_page(self):
        pages = [
            {"items": [1, 2], "nextToken": "page_1"},
            {"items": [3, 4], "nextToken": "page_2"},
            {"items": [5]},
        ]
        method = self._make_mock_method(pages)
        result = list(Paginator(method))
        assert result == [1, 2, 3, 4, 5]

    def test_max_items(self):
        def method(**kwargs):
            return {"items": list(range(100))}

        result = list(Paginator(method, max_items=5))
        assert len(result) == 5

    def test_max_pages(self):
        page_count = 0
        def method(**kwargs):
            nonlocal page_count
            page_count += 1
            return {"items": [page_count], "nextToken": f"page_{page_count}"}

        result = list(Paginator(method, max_pages=3))
        assert len(result) == 3

    def test_stats(self):
        def method(**kwargs):
            return {"items": [1, 2, 3]}

        pager = Paginator(method)
        list(pager)
        assert pager.stats["pages_fetched"] == 1
        assert pager.stats["total_items"] == 3

    def test_custom_item_key(self):
        def method(**kwargs):
            return {"payload": {"Orders": [{"id": 1}, {"id": 2}]}}

        result = list(Paginator(method, item_key="Orders"))
        assert len(result) == 2

    def test_empty_response(self):
        def method(**kwargs):
            return {"items": []}

        result = list(Paginator(method))
        assert result == []


class TestPaginateFunction:
    """Tests for paginate() convenience function."""

    def test_returns_paginator(self):
        def method(**kwargs):
            return {"items": []}
        result = paginate(method)
        assert isinstance(result, Paginator)

    def test_iteration(self):
        def method(**kwargs):
            return {"items": [1, 2, 3]}
        result = list(paginate(method))
        assert result == [1, 2, 3]


class TestAsyncPaginator:
    """Tests for AsyncPaginator."""

    def test_init(self):
        async def method(**kwargs):
            return {"items": []}
        pager = AsyncPaginator(method, max_items=10)
        assert pager._max_items == 10

    def test_async_paginate_function(self):
        async def method(**kwargs):
            return {"items": []}
        result = async_paginate(method)
        assert isinstance(result, AsyncPaginator)

    def test_stats_initial(self):
        async def method(**kwargs):
            return {"items": []}
        pager = AsyncPaginator(method)
        assert pager.stats["pages_fetched"] == 0
        assert pager.stats["total_items"] == 0
