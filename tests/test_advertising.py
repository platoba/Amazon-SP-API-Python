"""Tests for Advertising API module."""

import pytest
from unittest.mock import MagicMock, patch
from sp_api.advertising import (
    AdvertisingAPI, ADS_ENDPOINTS, CAMPAIGN_TYPES,
    TARGETING_TYPES, BID_STRATEGIES, MATCH_TYPES,
    SP_METRICS, SB_METRICS,
)


class MockClient(AdvertisingAPI):
    """Mock client for testing AdvertisingAPI mixin."""

    def __init__(self):
        self.endpoint = "https://sellingpartnerapi-na.amazon.com"
        self.marketplace_id = "ATVPDKIKX0DER"
        self._calls = []

    def get(self, path, params=None):
        self._calls.append(("GET", path, params))
        return {"mock": True, "path": path}

    def post(self, path, body=None, params=None):
        self._calls.append(("POST", path, body))
        return {"mock": True, "path": path}

    def put(self, path, body=None, params=None):
        self._calls.append(("PUT", path, body))
        return {"mock": True, "path": path}

    def delete(self, path, params=None):
        self._calls.append(("DELETE", path, params))
        return {"mock": True, "path": path}


@pytest.fixture
def client():
    return MockClient()


# ── Constants ─────────────────────────────────────────────

class TestConstants:
    def test_ads_endpoints(self):
        assert "NA" in ADS_ENDPOINTS
        assert "EU" in ADS_ENDPOINTS
        assert "FE" in ADS_ENDPOINTS

    def test_campaign_types(self):
        assert "sp" in CAMPAIGN_TYPES
        assert "sb" in CAMPAIGN_TYPES
        assert "sd" in CAMPAIGN_TYPES

    def test_targeting_types(self):
        assert "manual" in TARGETING_TYPES
        assert "auto" in TARGETING_TYPES

    def test_bid_strategies(self):
        assert len(BID_STRATEGIES) == 3

    def test_match_types(self):
        assert "exact" in MATCH_TYPES
        assert "phrase" in MATCH_TYPES
        assert "broad" in MATCH_TYPES

    def test_metrics(self):
        assert "impressions" in SP_METRICS
        assert "clicks" in SP_METRICS
        assert len(SB_METRICS) > 0


# ── Profiles ──────────────────────────────────────────────

class TestProfiles:
    def test_list_ad_profiles(self, client):
        result = client.list_ad_profiles()
        assert result["path"] == "/v2/profiles"

    def test_get_ad_profile(self, client):
        result = client.get_ad_profile("12345")
        assert result["path"] == "/v2/profiles/12345"


# ── Campaigns ─────────────────────────────────────────────

class TestCampaigns:
    def test_list_campaigns(self, client):
        result = client.list_campaigns()
        assert "sponsoredProducts/campaigns" in result["path"]

    def test_list_campaigns_with_filters(self, client):
        result = client.list_campaigns(
            campaign_type="sb", state_filter="enabled", name_filter="test"
        )
        _, path, params = client._calls[-1]
        assert "sponsoredBrands" in path
        assert params["stateFilter"] == "enabled"
        assert params["name"] == "test"

    def test_get_campaign(self, client):
        result = client.get_campaign("999")
        assert "999" in result["path"]

    def test_create_campaign(self, client):
        result = client.create_campaign(
            name="Test Campaign",
            daily_budget=50.0,
            targeting_type="manual",
        )
        _, path, body = client._calls[-1]
        assert "campaigns" in path
        assert body[0]["name"] == "Test Campaign"
        assert body[0]["dailyBudget"] == 50.0
        assert body[0]["targetingType"] == "manual"

    def test_create_campaign_invalid_targeting(self, client):
        with pytest.raises(ValueError, match="targeting_type"):
            client.create_campaign("Test", 50, targeting_type="invalid")

    def test_create_campaign_invalid_bid_strategy(self, client):
        with pytest.raises(ValueError, match="bid_strategy"):
            client.create_campaign("Test", 50, bid_strategy="invalid")

    def test_create_campaign_with_all_options(self, client):
        result = client.create_campaign(
            name="Full Campaign",
            daily_budget=100,
            targeting_type="auto",
            campaign_type="sd",
            start_date="20240101",
            end_date="20240131",
            bid_strategy="autoForSales",
            state="paused",
            portfolio_id="555",
        )
        _, path, body = client._calls[-1]
        assert "sponsoredDisplay" in path
        assert body[0]["state"] == "paused"
        assert body[0]["startDate"] == "20240101"
        assert body[0]["endDate"] == "20240131"
        assert body[0]["portfolioId"] == 555

    def test_update_campaign(self, client):
        client.update_campaign("123", state="paused")
        _, path, body = client._calls[-1]
        assert body[0]["campaignId"] == 123
        assert body[0]["state"] == "paused"

    def test_archive_campaign(self, client):
        client.archive_campaign("123")
        method, path, _ = client._calls[-1]
        assert method == "DELETE"
        assert "123" in path


# ── Ad Groups ─────────────────────────────────────────────

class TestAdGroups:
    def test_list_ad_groups(self, client):
        result = client.list_ad_groups()
        assert "adGroups" in result["path"]

    def test_list_ad_groups_filtered(self, client):
        client.list_ad_groups(campaign_id="999", state_filter="enabled")
        _, _, params = client._calls[-1]
        assert params["campaignIdFilter"] == "999"

    def test_get_ad_group(self, client):
        result = client.get_ad_group("456")
        assert "456" in result["path"]

    def test_create_ad_group(self, client):
        client.create_ad_group("999", "My Group", 1.5)
        _, _, body = client._calls[-1]
        assert body[0]["campaignId"] == 999
        assert body[0]["name"] == "My Group"
        assert body[0]["defaultBid"] == 1.5

    def test_update_ad_group(self, client):
        client.update_ad_group("456", defaultBid=2.0)
        _, _, body = client._calls[-1]
        assert body[0]["adGroupId"] == 456

    def test_archive_ad_group(self, client):
        client.archive_ad_group("456")
        method, _, _ = client._calls[-1]
        assert method == "DELETE"


# ── Keywords ──────────────────────────────────────────────

class TestKeywords:
    def test_list_keywords(self, client):
        result = client.list_keywords()
        assert "keywords" in result["path"]

    def test_create_keywords(self, client):
        keywords = [
            {"keyword": "wireless headphones", "matchType": "exact", "bid": 1.5},
            {"keyword": "bluetooth earbuds", "matchType": "broad"},
        ]
        client.create_keywords("456", "999", keywords)
        _, _, body = client._calls[-1]
        assert len(body) == 2
        assert body[0]["keywordText"] == "wireless headphones"
        assert body[0]["matchType"] == "exact"
        assert body[1]["bid"] == 1.0  # default bid

    def test_create_keywords_invalid_match(self, client):
        with pytest.raises(ValueError, match="matchType"):
            client.create_keywords("456", "999", [
                {"keyword": "test", "matchType": "invalid"}
            ])

    def test_update_keyword(self, client):
        client.update_keyword("789", bid=2.0)
        _, _, body = client._calls[-1]
        assert body[0]["keywordId"] == 789

    def test_archive_keyword(self, client):
        client.archive_keyword("789")
        method, _, _ = client._calls[-1]
        assert method == "DELETE"

    def test_list_negative_keywords(self, client):
        result = client.list_negative_keywords(campaign_id="999")
        assert "negativeKeywords" in result["path"]

    def test_create_negative_keywords(self, client):
        keywords = [{"keyword": "cheap", "matchType": "negativeExact"}]
        client.create_negative_keywords("456", "999", keywords)
        _, _, body = client._calls[-1]
        assert body[0]["keywordText"] == "cheap"


# ── Product Ads ───────────────────────────────────────────

class TestProductAds:
    def test_list_product_ads(self, client):
        result = client.list_product_ads()
        assert "productAds" in result["path"]

    def test_create_product_ads_strings(self, client):
        client.create_product_ads("456", "999", ["B001", "B002"])
        _, _, body = client._calls[-1]
        assert len(body) == 2
        assert body[0]["asin"] == "B001"

    def test_create_product_ads_dicts(self, client):
        asins = [{"asin": "B001", "sku": "SKU-001"}]
        client.create_product_ads("456", "999", asins)
        _, _, body = client._calls[-1]
        assert body[0]["sku"] == "SKU-001"


# ── Bid Recommendations ──────────────────────────────────

class TestBidRecommendations:
    def test_get_bid_recommendations(self, client):
        result = client.get_bid_recommendations("456")
        assert "bidRecommendations" in result["path"]

    def test_get_keyword_bid_recommendations(self, client):
        result = client.get_keyword_bid_recommendations("789")
        assert "789" in result["path"]


# ── Suggested Keywords ────────────────────────────────────

class TestSuggestedKeywords:
    def test_get_suggested_keywords(self, client):
        result = client.get_suggested_keywords("456")
        assert "suggested" in result["path"]

    def test_get_asin_suggested_keywords(self, client):
        result = client.get_asin_suggested_keywords("B001")
        assert result["mock"] is True


# ── Portfolios ────────────────────────────────────────────

class TestPortfolios:
    def test_list_portfolios(self, client):
        result = client.list_portfolios()
        assert "portfolios" in result["path"]

    def test_create_portfolio(self, client):
        client.create_portfolio("My Portfolio", budget=1000)
        _, _, body = client._calls[-1]
        assert body[0]["name"] == "My Portfolio"
        assert body[0]["budget"]["amount"] == 1000.0


# ── Reports ───────────────────────────────────────────────

class TestReports:
    def test_request_report(self, client):
        result = client.request_report("campaigns")
        _, _, body = client._calls[-1]
        assert "metrics" in body

    def test_request_report_custom_metrics(self, client):
        client.request_report("keywords", metrics=["impressions", "clicks"])
        _, _, body = client._calls[-1]
        assert body["metrics"] == "impressions,clicks"

    def test_get_report(self, client):
        result = client.get_report("report-123")
        assert "report-123" in result["path"]


# ── Convenience ───────────────────────────────────────────

class TestConvenience:
    def test_pause_campaign(self, client):
        client.pause_campaign("123")
        _, _, body = client._calls[-1]
        assert body[0]["state"] == "paused"

    def test_enable_campaign(self, client):
        client.enable_campaign("123")
        _, _, body = client._calls[-1]
        assert body[0]["state"] == "enabled"

    def test_set_campaign_budget(self, client):
        client.set_campaign_budget("123", 75.0)
        _, _, body = client._calls[-1]
        assert body[0]["dailyBudget"] == 75.0

    def test_bulk_update_bids(self, client):
        updates = [
            {"keywordId": "1", "bid": 1.5},
            {"keywordId": "2", "bid": 2.0},
        ]
        client.bulk_update_bids(updates)
        _, _, body = client._calls[-1]
        assert len(body) == 2
        assert body[0]["bid"] == 1.5

    def test_ads_endpoint_na(self, client):
        assert "advertising-api.amazon.com" in client._ads_endpoint

    def test_ads_endpoint_eu(self, client):
        client.endpoint = "https://sellingpartnerapi-eu.amazon.com"
        assert "eu" in client._ads_endpoint

    def test_ads_endpoint_fe(self, client):
        client.endpoint = "https://sellingpartnerapi-fe.amazon.com"
        assert "fe" in client._ads_endpoint
