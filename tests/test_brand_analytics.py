"""Tests for Brand Analytics API module."""

import pytest
from sp_api.brand_analytics import (
    BrandAnalyticsAPI, BRAND_ANALYTICS_REPORTS, REPORTING_PERIODS,
)


class MockClient(BrandAnalyticsAPI):
    """Mock client for testing BrandAnalyticsAPI mixin."""

    def __init__(self):
        self.marketplace_id = "ATVPDKIKX0DER"
        self._calls = []

    def get(self, path, params=None):
        self._calls.append(("GET", path, params))
        return {"mock": True, "path": path}

    def post(self, path, body=None, params=None):
        self._calls.append(("POST", path, body))
        return {"mock": True, "path": path, "body": body}


@pytest.fixture
def client():
    return MockClient()


# ── Constants ─────────────────────────────────────────────

class TestConstants:
    def test_report_types(self):
        assert "search_terms" in BRAND_ANALYTICS_REPORTS
        assert "market_basket" in BRAND_ANALYTICS_REPORTS
        assert "demographics" in BRAND_ANALYTICS_REPORTS
        assert "repeat_purchase" in BRAND_ANALYTICS_REPORTS
        assert "item_comparison" in BRAND_ANALYTICS_REPORTS

    def test_reporting_periods(self):
        assert "DAY" in REPORTING_PERIODS
        assert "WEEK" in REPORTING_PERIODS
        assert "MONTH" in REPORTING_PERIODS
        assert "QUARTER" in REPORTING_PERIODS


# ── Search Terms ──────────────────────────────────────────

class TestSearchTerms:
    def test_get_search_terms(self, client):
        result = client.get_search_terms()
        assert "searchTerms" in result["path"]

    def test_get_search_terms_with_params(self, client):
        client.get_search_terms(
            report_date="2024-01-15",
            reporting_period="MONTH",
            asin="B001TEST",
            search_term="wireless",
        )
        _, _, body = client._calls[-1]
        assert body["reportDate"] == "2024-01-15"
        assert body["reportingPeriod"] == "MONTH"
        assert body["asin"] == "B001TEST"
        assert body["searchTerm"] == "wireless"

    def test_get_search_terms_invalid_period(self, client):
        with pytest.raises(ValueError, match="reporting_period"):
            client.get_search_terms(reporting_period="INVALID")

    def test_get_search_terms_pagination(self, client):
        client.get_search_terms(next_token="abc123", max_results=50)
        _, _, body = client._calls[-1]
        assert body["nextToken"] == "abc123"
        assert body["maxResults"] == 50

    def test_get_top_search_terms(self, client):
        # Mock response with search terms
        client.post = lambda path, body=None: {
            "searchTerms": [
                {"searchTerm": "a", "searchFrequencyRank": 3},
                {"searchTerm": "b", "searchFrequencyRank": 1},
                {"searchTerm": "c", "searchFrequencyRank": 2},
            ]
        }
        result = client.get_top_search_terms(count=2)
        assert len(result) == 2
        assert result[0]["searchFrequencyRank"] == 1

    def test_get_asin_search_terms(self, client):
        client.get_asin_search_terms("B001TEST")
        _, _, body = client._calls[-1]
        assert body["asin"] == "B001TEST"


# ── Market Basket ─────────────────────────────────────────

class TestMarketBasket:
    def test_get_market_basket(self, client):
        result = client.get_market_basket("B001TEST")
        assert "marketBasket" in result["path"]

    def test_get_market_basket_params(self, client):
        client.get_market_basket(
            "B001TEST",
            report_date="2024-01-15",
            reporting_period="MONTH",
        )
        _, _, body = client._calls[-1]
        assert body["asin"] == "B001TEST"
        assert body["reportingPeriod"] == "MONTH"

    def test_get_cross_sell_asins(self, client):
        client.post = lambda path, body=None: {
            "basketItems": [
                {"asin": "B001", "combinationPct": 15.0},
                {"asin": "B002", "combinationPct": 3.0},
                {"asin": "B003", "combinationPct": 8.0},
            ]
        }
        result = client.get_cross_sell_asins("B000", min_combo_pct=5.0)
        assert len(result) == 2
        assert result[0]["asin"] == "B001"


# ── Repeat Purchase ───────────────────────────────────────

class TestRepeatPurchase:
    def test_get_repeat_purchase(self, client):
        result = client.get_repeat_purchase()
        assert "repeatPurchase" in result["path"]

    def test_get_repeat_purchase_with_asin(self, client):
        client.get_repeat_purchase(asin="B001TEST")
        _, _, body = client._calls[-1]
        assert body["asin"] == "B001TEST"

    def test_get_loyalty_score(self, client):
        client.post = lambda path, body=None: {
            "repeatPurchaseItems": [
                {
                    "asin": "B001",
                    "repeatCustomersPct": 25.0,
                    "ordersPerCustomer": 3.5,
                }
            ]
        }
        result = client.get_loyalty_score("B001")
        assert result["asin"] == "B001"
        assert result["repeat_rate"] == 25.0
        assert result["loyalty_score"] > 0
        assert result["loyalty_score"] <= 100

    def test_get_loyalty_score_no_data(self, client):
        client.post = lambda path, body=None: {"repeatPurchaseItems": []}
        result = client.get_loyalty_score("B001")
        assert result["loyalty_score"] == 0


# ── Demographics ──────────────────────────────────────────

class TestDemographics:
    def test_get_demographics(self, client):
        result = client.get_demographics()
        assert "demographics" in result["path"]

    def test_get_demographics_with_asin(self, client):
        client.get_demographics(asin="B001TEST")
        _, _, body = client._calls[-1]
        assert body["asin"] == "B001TEST"

    def test_get_customer_profile(self, client):
        client.post = lambda path, body=None: {
            "demographics": {
                "ageRange": [
                    {"label": "25-34", "pct": 35.0},
                    {"label": "35-44", "pct": 28.0},
                ],
                "gender": [
                    {"label": "Male", "pct": 60.0},
                    {"label": "Female", "pct": 40.0},
                ],
            }
        }
        result = client.get_customer_profile("B001")
        assert result["asin"] == "B001"
        assert result["ageRange"]["dominant"] == "25-34"
        assert result["gender"]["dominant"] == "Male"


# ── Item Comparison ───────────────────────────────────────

class TestItemComparison:
    def test_get_item_comparison(self, client):
        result = client.get_item_comparison("B001TEST")
        assert "itemComparison" in result["path"]

    def test_get_competitors(self, client):
        client.post = lambda path, body=None: {
            "alternateItems": [
                {"asin": "B100", "comparisonPct": 20.0},
                {"asin": "B200", "comparisonPct": 2.0},
                {"asin": "B300", "comparisonPct": 10.0},
            ]
        }
        result = client.get_competitors("B001", min_comparison_pct=5.0)
        assert len(result) == 2
        assert result[0]["comparisonPct"] == 20.0  # sorted descending

    def test_get_competitors_empty(self, client):
        client.post = lambda path, body=None: {"alternateItems": []}
        result = client.get_competitors("B001")
        assert result == []


# ── Search Catalog ────────────────────────────────────────

class TestSearchCatalog:
    def test_search_catalog_analytics(self, client):
        client.search_catalog_analytics("wireless headphones")
        _, _, body = client._calls[-1]
        assert body["searchTerm"] == "wireless headphones"
        assert body["marketplaceId"] == "ATVPDKIKX0DER"


# ── Competitive Landscape ─────────────────────────────────

class TestCompetitiveLandscape:
    def test_competitive_landscape(self, client):
        # Mock all sub-methods
        client.get_asin_search_terms = lambda asin, **kw: {"searchTerms": [{"term": "a"}]}
        client.get_competitors = lambda asin, **kw: [{"asin": "B100"}]
        client.get_cross_sell_asins = lambda asin, **kw: [{"asin": "B200"}]

        result = client.competitive_landscape("B001")
        assert result["asin"] == "B001"
        assert result["summary"]["search_term_count"] == 1
        assert result["summary"]["competitor_count"] == 1
        assert result["summary"]["cross_sell_count"] == 1

    def test_competitive_landscape_errors(self, client):
        # Mock methods that raise errors
        client.get_asin_search_terms = lambda asin, **kw: (_ for _ in ()).throw(Exception("API Error"))
        client.get_competitors = lambda asin, **kw: (_ for _ in ()).throw(Exception("API Error"))
        client.get_cross_sell_asins = lambda asin, **kw: []

        result = client.competitive_landscape("B001")
        assert "search_terms_error" in result
        assert "competitors_error" in result
