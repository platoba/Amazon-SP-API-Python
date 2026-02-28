"""
Brand Analytics API module — Amazon Brand Analytics.

Provides access to Search Terms, Market Basket Analysis,
Repeat Purchase Behavior, Demographics, and Item Comparison.
Available only to brand-registered sellers.
"""

from datetime import datetime, timezone, timedelta
from sp_api.base import BaseAPI


# Report types
BRAND_ANALYTICS_REPORTS = {
    "search_terms": "GET_BRAND_ANALYTICS_SEARCH_TERMS_REPORT",
    "market_basket": "GET_BRAND_ANALYTICS_MARKET_BASKET_REPORT",
    "repeat_purchase": "GET_BRAND_ANALYTICS_REPEAT_PURCHASE_REPORT",
    "demographics": "GET_BRAND_ANALYTICS_DEMOGRAPHICS_REPORT",
    "item_comparison": "GET_BRAND_ANALYTICS_ALTERNATE_ITEM_REPORT",
    "search_catalog": "GET_BRAND_ANALYTICS_SEARCH_CATALOG_REPORT",
}

# Reporting periods
REPORTING_PERIODS = ["DAY", "WEEK", "MONTH", "QUARTER"]


class BrandAnalyticsAPI(BaseAPI):
    """
    Amazon Brand Analytics API.

    Access search term performance, market basket analysis,
    repeat purchase behavior, demographics, and competitive insights.
    Requires Brand Registry enrollment.
    """

    # ── Search Terms ──────────────────────────────────────

    def get_search_terms(self, report_date=None, reporting_period="WEEK",
                         asin=None, search_term=None, max_results=100,
                         next_token=None):
        """
        Get Brand Analytics search terms report.

        Shows top search terms, click share, conversion share per ASIN.

        Args:
            report_date: Date for the report (YYYY-MM-DD), defaults to last week
            reporting_period: DAY, WEEK, MONTH, or QUARTER
            asin: Filter by specific ASIN
            search_term: Filter by search term
            max_results: Max results per page
            next_token: Pagination token
        """
        if reporting_period not in REPORTING_PERIODS:
            raise ValueError(f"reporting_period must be one of {REPORTING_PERIODS}")

        if not report_date:
            report_date = (
                datetime.now(timezone.utc) - timedelta(days=7)
            ).strftime("%Y-%m-%d")

        body = {
            "reportDate": report_date,
            "reportingPeriod": reporting_period,
            "marketplaceId": self.marketplace_id,
            "maxResults": min(max_results, 500),
        }
        if asin:
            body["asin"] = asin
        if search_term:
            body["searchTerm"] = search_term
        if next_token:
            body["nextToken"] = next_token

        return self.post("/analytics/brandAnalytics/v1/searchTerms", body=body)

    def get_top_search_terms(self, count=25, report_date=None,
                             reporting_period="WEEK"):
        """
        Get top N search terms by search frequency rank.

        Args:
            count: Number of top terms to return
            report_date: Report date
            reporting_period: Reporting period
        """
        result = self.get_search_terms(
            report_date=report_date,
            reporting_period=reporting_period,
            max_results=min(count, 500),
        )
        terms = result.get("searchTerms", result.get("payload", []))
        if isinstance(terms, list):
            terms.sort(key=lambda x: x.get("searchFrequencyRank", 9999))
            return terms[:count]
        return terms

    def get_asin_search_terms(self, asin, report_date=None,
                              reporting_period="WEEK"):
        """Get search terms driving traffic to a specific ASIN."""
        return self.get_search_terms(
            report_date=report_date,
            reporting_period=reporting_period,
            asin=asin,
        )

    # ── Market Basket Analysis ────────────────────────────

    def get_market_basket(self, asin, report_date=None,
                          reporting_period="WEEK", max_results=100,
                          next_token=None):
        """
        Get market basket analysis for an ASIN.

        Shows products frequently purchased together with the given ASIN.

        Args:
            asin: Target ASIN
            report_date: Report date
            reporting_period: Reporting period
            max_results: Max results
            next_token: Pagination token
        """
        if not report_date:
            report_date = (
                datetime.now(timezone.utc) - timedelta(days=7)
            ).strftime("%Y-%m-%d")

        body = {
            "reportDate": report_date,
            "reportingPeriod": reporting_period,
            "marketplaceId": self.marketplace_id,
            "asin": asin,
            "maxResults": min(max_results, 500),
        }
        if next_token:
            body["nextToken"] = next_token

        return self.post("/analytics/brandAnalytics/v1/marketBasket", body=body)

    def get_cross_sell_asins(self, asin, min_combo_pct=5.0, report_date=None):
        """
        Find ASINs commonly purchased with a given ASIN.

        Args:
            asin: Target ASIN
            min_combo_pct: Minimum combination percentage threshold
            report_date: Report date

        Returns:
            List of related ASINs sorted by combination percentage
        """
        result = self.get_market_basket(asin, report_date=report_date)
        items = result.get("basketItems", result.get("payload", []))
        if isinstance(items, list):
            return [
                item for item in items
                if item.get("combinationPct", 0) >= min_combo_pct
            ]
        return items

    # ── Repeat Purchase Behavior ──────────────────────────

    def get_repeat_purchase(self, asin=None, report_date=None,
                            reporting_period="MONTH", max_results=100,
                            next_token=None):
        """
        Get repeat purchase behavior report.

        Shows repeat purchase rates and customer loyalty metrics.

        Args:
            asin: Optional ASIN filter
            report_date: Report date
            reporting_period: Reporting period (MONTH or QUARTER recommended)
            max_results: Max results
            next_token: Pagination token
        """
        if not report_date:
            report_date = (
                datetime.now(timezone.utc) - timedelta(days=30)
            ).strftime("%Y-%m-%d")

        body = {
            "reportDate": report_date,
            "reportingPeriod": reporting_period,
            "marketplaceId": self.marketplace_id,
            "maxResults": min(max_results, 500),
        }
        if asin:
            body["asin"] = asin
        if next_token:
            body["nextToken"] = next_token

        return self.post(
            "/analytics/brandAnalytics/v1/repeatPurchase", body=body
        )

    def get_loyalty_score(self, asin, report_date=None):
        """
        Calculate a loyalty score for an ASIN based on repeat purchases.

        Returns:
            dict with repeat_rate, loyalty_score (0-100), and raw data
        """
        result = self.get_repeat_purchase(asin=asin, report_date=report_date)
        items = result.get("repeatPurchaseItems", result.get("payload", []))

        if not items:
            return {"asin": asin, "repeat_rate": 0, "loyalty_score": 0}

        item = items[0] if isinstance(items, list) else items
        repeat_rate = item.get("repeatCustomersPct", 0)
        orders_per_customer = item.get("ordersPerCustomer", 1)

        # Score: weighted combination of repeat rate and order frequency
        score = min(100, repeat_rate * 0.6 + min(orders_per_customer * 10, 40))

        return {
            "asin": asin,
            "repeat_rate": repeat_rate,
            "orders_per_customer": orders_per_customer,
            "loyalty_score": round(score, 1),
            "raw": item,
        }

    # ── Demographics ──────────────────────────────────────

    def get_demographics(self, asin=None, report_date=None,
                         reporting_period="MONTH", max_results=100,
                         next_token=None):
        """
        Get customer demographics report.

        Shows age, gender, income, education, and marital status
        distribution of customers.

        Args:
            asin: Optional ASIN filter
            report_date: Report date
            reporting_period: Reporting period
            max_results: Max results
            next_token: Pagination token
        """
        if not report_date:
            report_date = (
                datetime.now(timezone.utc) - timedelta(days=30)
            ).strftime("%Y-%m-%d")

        body = {
            "reportDate": report_date,
            "reportingPeriod": reporting_period,
            "marketplaceId": self.marketplace_id,
            "maxResults": min(max_results, 500),
        }
        if asin:
            body["asin"] = asin
        if next_token:
            body["nextToken"] = next_token

        return self.post(
            "/analytics/brandAnalytics/v1/demographics", body=body
        )

    def get_customer_profile(self, asin, report_date=None):
        """
        Build a customer profile for an ASIN.

        Returns aggregated demographics: dominant age group, gender split,
        income bracket, and education level.
        """
        result = self.get_demographics(asin=asin, report_date=report_date)
        data = result.get("demographics", result.get("payload", {}))

        profile = {"asin": asin}

        if isinstance(data, dict):
            # Extract dominant segments
            for dim in ["ageRange", "gender", "income", "education", "maritalStatus"]:
                segments = data.get(dim, [])
                if segments and isinstance(segments, list):
                    dominant = max(segments, key=lambda x: x.get("pct", 0))
                    profile[dim] = {
                        "dominant": dominant.get("label", "unknown"),
                        "pct": dominant.get("pct", 0),
                        "segments": segments,
                    }

        return profile

    # ── Item Comparison / Alternate Items ─────────────────

    def get_item_comparison(self, asin, report_date=None,
                            reporting_period="WEEK", max_results=100,
                            next_token=None):
        """
        Get item comparison report (alternate items).

        Shows products customers viewed/purchased instead of the given ASIN.

        Args:
            asin: Target ASIN
            report_date: Report date
            reporting_period: Reporting period
            max_results: Max results
            next_token: Pagination token
        """
        if not report_date:
            report_date = (
                datetime.now(timezone.utc) - timedelta(days=7)
            ).strftime("%Y-%m-%d")

        body = {
            "reportDate": report_date,
            "reportingPeriod": reporting_period,
            "marketplaceId": self.marketplace_id,
            "asin": asin,
            "maxResults": min(max_results, 500),
        }
        if next_token:
            body["nextToken"] = next_token

        return self.post(
            "/analytics/brandAnalytics/v1/itemComparison", body=body
        )

    def get_competitors(self, asin, report_date=None, min_comparison_pct=3.0):
        """
        Find competitor ASINs for a given product.

        Args:
            asin: Target ASIN
            report_date: Report date
            min_comparison_pct: Minimum comparison percentage

        Returns:
            List of competitor ASINs sorted by comparison percentage
        """
        result = self.get_item_comparison(asin, report_date=report_date)
        items = result.get("alternateItems", result.get("payload", []))
        if isinstance(items, list):
            competitors = [
                item for item in items
                if item.get("comparisonPct", 0) >= min_comparison_pct
            ]
            competitors.sort(
                key=lambda x: x.get("comparisonPct", 0), reverse=True
            )
            return competitors
        return items

    # ── Search Catalog ────────────────────────────────────

    def search_catalog_analytics(self, search_term, report_date=None,
                                 reporting_period="WEEK", max_results=100):
        """
        Search catalog with analytics context.

        Shows how a search term maps to ASINs with click/conversion shares.

        Args:
            search_term: Search query
            report_date: Report date
            reporting_period: Reporting period
            max_results: Max results
        """
        if not report_date:
            report_date = (
                datetime.now(timezone.utc) - timedelta(days=7)
            ).strftime("%Y-%m-%d")

        body = {
            "reportDate": report_date,
            "reportingPeriod": reporting_period,
            "marketplaceId": self.marketplace_id,
            "searchTerm": search_term,
            "maxResults": min(max_results, 500),
        }

        return self.post(
            "/analytics/brandAnalytics/v1/searchCatalog", body=body
        )

    # ── Convenience ───────────────────────────────────────

    def competitive_landscape(self, asin, report_date=None):
        """
        Build a comprehensive competitive landscape for an ASIN.

        Combines search terms, item comparison, and market basket
        into a single competitive analysis.

        Returns:
            dict with search_terms, competitors, cross_sell, and summary
        """
        landscape = {"asin": asin}

        # Search terms driving traffic
        try:
            terms = self.get_asin_search_terms(asin, report_date=report_date)
            landscape["search_terms"] = terms.get(
                "searchTerms", terms.get("payload", [])
            )
        except Exception as e:
            landscape["search_terms"] = []
            landscape["search_terms_error"] = str(e)

        # Competitor products
        try:
            landscape["competitors"] = self.get_competitors(
                asin, report_date=report_date
            )
        except Exception as e:
            landscape["competitors"] = []
            landscape["competitors_error"] = str(e)

        # Cross-sell opportunities
        try:
            landscape["cross_sell"] = self.get_cross_sell_asins(
                asin, report_date=report_date
            )
        except Exception as e:
            landscape["cross_sell"] = []
            landscape["cross_sell_error"] = str(e)

        # Summary
        landscape["summary"] = {
            "search_term_count": len(landscape["search_terms"]),
            "competitor_count": len(landscape["competitors"]),
            "cross_sell_count": len(landscape["cross_sell"]),
        }

        return landscape
