"""
Amazon Advertising API module — Sponsored Products, Brands, Display.

Amazon Ads API uses a separate endpoint from SP-API but shares
credentials. This module provides campaign management, ad group
operations, keyword targeting, bid optimization, and reporting.

Endpoint: https://advertising-api.amazon.com (NA)
           https://advertising-api-eu.amazon.com (EU)
           https://advertising-api-fe.amazon.com (FE)
"""

import time
import logging
from datetime import datetime, timezone, timedelta
from sp_api.base import BaseAPI

logger = logging.getLogger(__name__)

ADS_ENDPOINTS = {
    "NA": "https://advertising-api.amazon.com",
    "EU": "https://advertising-api-eu.amazon.com",
    "FE": "https://advertising-api-fe.amazon.com",
}

CAMPAIGN_TYPES = {
    "sp": "sponsoredProducts",
    "sb": "sponsoredBrands",
    "sd": "sponsoredDisplay",
}

TARGETING_TYPES = ["manual", "auto"]
BID_STRATEGIES = ["legacyForSales", "autoForSales", "manual"]
MATCH_TYPES = ["exact", "phrase", "broad"]

SP_METRICS = [
    "impressions", "clicks", "cost", "attributedSales7d",
    "attributedConversions7d", "attributedUnitsOrdered7d",
]

SB_METRICS = [
    "impressions", "clicks", "cost", "attributedSales14d",
    "attributedConversions14d", "dpv14d", "attributedOrdersNewToBrand14d",
]


class AdvertisingAPI(BaseAPI):
    """
    Amazon Advertising API — Sponsored Products, Brands, Display.

    Provides campaign lifecycle, keyword targeting, bid optimization,
    budget management, and performance reporting.
    """

    @property
    def _ads_endpoint(self):
        region = "NA"
        endpoint = getattr(self, "endpoint", "")
        if "eu" in endpoint:
            region = "EU"
        elif "fe" in endpoint:
            region = "FE"
        return ADS_ENDPOINTS.get(region, ADS_ENDPOINTS["NA"])

    # ── Profiles ──────────────────────────────────────────

    def list_ad_profiles(self):
        """List advertising profiles associated with the account."""
        return self.get("/v2/profiles")

    def get_ad_profile(self, profile_id):
        """Get a single advertising profile."""
        return self.get(f"/v2/profiles/{profile_id}")

    # ── Campaigns ─────────────────────────────────────────

    def list_campaigns(self, campaign_type="sp", state_filter=None,
                       name_filter=None, max_results=100, next_token=None):
        """
        List advertising campaigns.

        Args:
            campaign_type: 'sp', 'sb', or 'sd'
            state_filter: 'enabled', 'paused', 'archived'
            name_filter: Filter by name (contains)
            max_results: Max results per page
            next_token: Pagination token
        """
        params = {"maxResults": min(max_results, 100)}
        if state_filter:
            params["stateFilter"] = state_filter
        if name_filter:
            params["name"] = name_filter
        if next_token:
            params["nextToken"] = next_token
        ad_type = CAMPAIGN_TYPES.get(campaign_type, "sponsoredProducts")
        return self.get(f"/v2/{ad_type}/campaigns", params)

    def get_campaign(self, campaign_id, campaign_type="sp"):
        """Get a single campaign by ID."""
        ad_type = CAMPAIGN_TYPES.get(campaign_type, "sponsoredProducts")
        return self.get(f"/v2/{ad_type}/campaigns/{campaign_id}")

    def create_campaign(self, name, daily_budget, targeting_type="manual",
                        campaign_type="sp", start_date=None, end_date=None,
                        bid_strategy="legacyForSales", state="enabled",
                        portfolio_id=None):
        """
        Create a new advertising campaign.

        Args:
            name: Campaign name
            daily_budget: Daily budget in currency units
            targeting_type: 'manual' or 'auto'
            campaign_type: 'sp', 'sb', or 'sd'
            start_date: YYYYMMDD, defaults to today
            end_date: YYYYMMDD, optional
            bid_strategy: Bidding strategy
            state: 'enabled' or 'paused'
            portfolio_id: Optional portfolio ID
        """
        if targeting_type not in TARGETING_TYPES:
            raise ValueError(f"targeting_type must be one of {TARGETING_TYPES}")
        if bid_strategy not in BID_STRATEGIES:
            raise ValueError(f"bid_strategy must be one of {BID_STRATEGIES}")

        if not start_date:
            start_date = datetime.now(timezone.utc).strftime("%Y%m%d")

        campaign = {
            "name": name,
            "campaignType": "sponsoredProducts",
            "targetingType": targeting_type,
            "state": state,
            "dailyBudget": float(daily_budget),
            "startDate": start_date,
            "bidding": {"strategy": bid_strategy},
        }
        if end_date:
            campaign["endDate"] = end_date
        if portfolio_id:
            campaign["portfolioId"] = int(portfolio_id)

        ad_type = CAMPAIGN_TYPES.get(campaign_type, "sponsoredProducts")
        return self.post(f"/v2/{ad_type}/campaigns", body=[campaign])

    def update_campaign(self, campaign_id, campaign_type="sp", **updates):
        """Update campaign settings (name, state, dailyBudget, etc.)."""
        body = {"campaignId": int(campaign_id)}
        body.update(updates)
        ad_type = CAMPAIGN_TYPES.get(campaign_type, "sponsoredProducts")
        return self.put(f"/v2/{ad_type}/campaigns", body=[body])

    def archive_campaign(self, campaign_id, campaign_type="sp"):
        """Archive (soft-delete) a campaign."""
        ad_type = CAMPAIGN_TYPES.get(campaign_type, "sponsoredProducts")
        return self.delete(f"/v2/{ad_type}/campaigns/{campaign_id}")

    # ── Ad Groups ─────────────────────────────────────────

    def list_ad_groups(self, campaign_id=None, campaign_type="sp",
                       state_filter=None, max_results=100, next_token=None):
        """List ad groups, optionally filtered by campaign."""
        params = {"maxResults": min(max_results, 100)}
        if campaign_id:
            params["campaignIdFilter"] = campaign_id
        if state_filter:
            params["stateFilter"] = state_filter
        if next_token:
            params["nextToken"] = next_token
        ad_type = CAMPAIGN_TYPES.get(campaign_type, "sponsoredProducts")
        return self.get(f"/v2/{ad_type}/adGroups", params)

    def get_ad_group(self, ad_group_id, campaign_type="sp"):
        """Get a single ad group."""
        ad_type = CAMPAIGN_TYPES.get(campaign_type, "sponsoredProducts")
        return self.get(f"/v2/{ad_type}/adGroups/{ad_group_id}")

    def create_ad_group(self, campaign_id, name, default_bid,
                        campaign_type="sp", state="enabled"):
        """
        Create an ad group within a campaign.

        Args:
            campaign_id: Parent campaign ID
            name: Ad group name
            default_bid: Default bid amount
            state: 'enabled' or 'paused'
        """
        body = {
            "campaignId": int(campaign_id),
            "name": name,
            "defaultBid": float(default_bid),
            "state": state,
        }
        ad_type = CAMPAIGN_TYPES.get(campaign_type, "sponsoredProducts")
        return self.post(f"/v2/{ad_type}/adGroups", body=[body])

    def update_ad_group(self, ad_group_id, campaign_type="sp", **updates):
        """Update ad group settings."""
        body = {"adGroupId": int(ad_group_id)}
        body.update(updates)
        ad_type = CAMPAIGN_TYPES.get(campaign_type, "sponsoredProducts")
        return self.put(f"/v2/{ad_type}/adGroups", body=[body])

    def archive_ad_group(self, ad_group_id, campaign_type="sp"):
        """Archive an ad group."""
        ad_type = CAMPAIGN_TYPES.get(campaign_type, "sponsoredProducts")
        return self.delete(f"/v2/{ad_type}/adGroups/{ad_group_id}")

    # ── Keywords / Targeting ──────────────────────────────

    def list_keywords(self, campaign_id=None, ad_group_id=None,
                      campaign_type="sp", state_filter=None,
                      max_results=100, next_token=None):
        """List keywords for targeting."""
        params = {"maxResults": min(max_results, 100)}
        if campaign_id:
            params["campaignIdFilter"] = campaign_id
        if ad_group_id:
            params["adGroupIdFilter"] = ad_group_id
        if state_filter:
            params["stateFilter"] = state_filter
        if next_token:
            params["nextToken"] = next_token
        ad_type = CAMPAIGN_TYPES.get(campaign_type, "sponsoredProducts")
        return self.get(f"/v2/{ad_type}/keywords", params)

    def create_keywords(self, ad_group_id, campaign_id, keywords,
                        campaign_type="sp"):
        """
        Add keywords to an ad group.

        Args:
            ad_group_id: Target ad group
            campaign_id: Parent campaign
            keywords: List of dicts with 'keyword', 'matchType', 'bid'
                      matchType: 'exact', 'phrase', or 'broad'
        """
        body = []
        for kw in keywords:
            match_type = kw.get("matchType", "broad")
            if match_type not in MATCH_TYPES:
                raise ValueError(f"matchType must be one of {MATCH_TYPES}")
            body.append({
                "campaignId": int(campaign_id),
                "adGroupId": int(ad_group_id),
                "keywordText": kw["keyword"],
                "matchType": match_type,
                "bid": float(kw.get("bid", 1.0)),
                "state": kw.get("state", "enabled"),
            })
        ad_type = CAMPAIGN_TYPES.get(campaign_type, "sponsoredProducts")
        return self.post(f"/v2/{ad_type}/keywords", body=body)

    def update_keyword(self, keyword_id, campaign_type="sp", **updates):
        """Update a keyword (bid, state)."""
        body = {"keywordId": int(keyword_id)}
        body.update(updates)
        ad_type = CAMPAIGN_TYPES.get(campaign_type, "sponsoredProducts")
        return self.put(f"/v2/{ad_type}/keywords", body=[body])

    def archive_keyword(self, keyword_id, campaign_type="sp"):
        """Archive a keyword."""
        ad_type = CAMPAIGN_TYPES.get(campaign_type, "sponsoredProducts")
        return self.delete(f"/v2/{ad_type}/keywords/{keyword_id}")

    def list_negative_keywords(self, campaign_id=None, ad_group_id=None,
                               campaign_type="sp"):
        """List negative keywords."""
        params = {}
        if campaign_id:
            params["campaignIdFilter"] = campaign_id
        if ad_group_id:
            params["adGroupIdFilter"] = ad_group_id
        ad_type = CAMPAIGN_TYPES.get(campaign_type, "sponsoredProducts")
        return self.get(f"/v2/{ad_type}/negativeKeywords", params or None)

    def create_negative_keywords(self, ad_group_id, campaign_id, keywords,
                                 campaign_type="sp"):
        """
        Add negative keywords.

        Args:
            keywords: List of dicts with 'keyword' and 'matchType'
                      matchType: 'negativeExact' or 'negativePhrase'
        """
        body = []
        for kw in keywords:
            body.append({
                "campaignId": int(campaign_id),
                "adGroupId": int(ad_group_id),
                "keywordText": kw["keyword"],
                "matchType": kw.get("matchType", "negativeExact"),
                "state": "enabled",
            })
        ad_type = CAMPAIGN_TYPES.get(campaign_type, "sponsoredProducts")
        return self.post(f"/v2/{ad_type}/negativeKeywords", body=body)

    # ── Product Ads ───────────────────────────────────────

    def list_product_ads(self, campaign_id=None, ad_group_id=None,
                         campaign_type="sp", state_filter=None):
        """List product ads."""
        params = {}
        if campaign_id:
            params["campaignIdFilter"] = campaign_id
        if ad_group_id:
            params["adGroupIdFilter"] = ad_group_id
        if state_filter:
            params["stateFilter"] = state_filter
        ad_type = CAMPAIGN_TYPES.get(campaign_type, "sponsoredProducts")
        return self.get(f"/v2/{ad_type}/productAds", params or None)

    def create_product_ads(self, ad_group_id, campaign_id, asins,
                           campaign_type="sp"):
        """
        Create product ads for ASINs.

        Args:
            asins: List of ASINs or list of dicts with 'asin' and optional 'sku'
        """
        body = []
        for item in asins:
            if isinstance(item, str):
                item = {"asin": item}
            body.append({
                "campaignId": int(campaign_id),
                "adGroupId": int(ad_group_id),
                "asin": item["asin"],
                "sku": item.get("sku", ""),
                "state": "enabled",
            })
        ad_type = CAMPAIGN_TYPES.get(campaign_type, "sponsoredProducts")
        return self.post(f"/v2/{ad_type}/productAds", body=body)

    # ── Bid Recommendations ───────────────────────────────

    def get_bid_recommendations(self, ad_group_id, campaign_type="sp"):
        """Get suggested bids for an ad group."""
        ad_type = CAMPAIGN_TYPES.get(campaign_type, "sponsoredProducts")
        return self.get(f"/v2/{ad_type}/adGroups/{ad_group_id}/bidRecommendations")

    def get_keyword_bid_recommendations(self, keyword_id, campaign_type="sp"):
        """Get suggested bid for a specific keyword."""
        ad_type = CAMPAIGN_TYPES.get(campaign_type, "sponsoredProducts")
        return self.get(f"/v2/{ad_type}/keywords/{keyword_id}/bidRecommendations")

    # ── Suggested Keywords ────────────────────────────────

    def get_suggested_keywords(self, ad_group_id, max_suggestions=100,
                               campaign_type="sp"):
        """Get keyword suggestions for an ad group."""
        params = {"maxNumSuggestions": min(max_suggestions, 1000)}
        ad_type = CAMPAIGN_TYPES.get(campaign_type, "sponsoredProducts")
        return self.get(
            f"/v2/{ad_type}/adGroups/{ad_group_id}/suggested/keywords",
            params,
        )

    def get_asin_suggested_keywords(self, asin, max_suggestions=100):
        """Get keyword suggestions for a specific ASIN."""
        params = {"maxNumSuggestions": min(max_suggestions, 1000)}
        return self.get(
            f"/v2/sp/targets/keywords/recommendations",
            {"asins": [asin], **params},
        )

    # ── Portfolios ────────────────────────────────────────

    def list_portfolios(self, state_filter=None):
        """List advertising portfolios."""
        params = {}
        if state_filter:
            params["portfolioStateFilter"] = state_filter
        return self.get("/v2/portfolios", params or None)

    def create_portfolio(self, name, budget=None, state="enabled"):
        """Create a portfolio for organizing campaigns."""
        body = {"name": name, "state": state}
        if budget:
            body["budget"] = {
                "amount": float(budget),
                "policy": "dateRange",
            }
        return self.post("/v2/portfolios", body=[body])

    # ── Reports ───────────────────────────────────────────

    def request_report(self, record_type, campaign_type="sp",
                       report_date=None, metrics=None):
        """
        Request an advertising report.

        Args:
            record_type: 'campaigns', 'adGroups', 'keywords', 'productAds', 'targets'
            campaign_type: 'sp', 'sb', or 'sd'
            report_date: YYYYMMDD, defaults to yesterday
            metrics: List of metrics to include
        """
        if not report_date:
            report_date = (
                datetime.now(timezone.utc) - timedelta(days=1)
            ).strftime("%Y%m%d")

        if not metrics:
            metrics = SP_METRICS if campaign_type == "sp" else SB_METRICS

        body = {
            "reportDate": report_date,
            "metrics": ",".join(metrics),
        }
        ad_type = CAMPAIGN_TYPES.get(campaign_type, "sponsoredProducts")
        return self.post(f"/v2/{ad_type}/{record_type}/report", body=body)

    def get_report(self, report_id):
        """Get report status and download URL."""
        return self.get(f"/v2/reports/{report_id}")

    def download_report(self, report_id, max_wait=120, poll_interval=5):
        """
        Wait for report to complete and return download URL.

        Args:
            report_id: Report ID from request_report
            max_wait: Maximum wait time in seconds
            poll_interval: Polling interval in seconds

        Returns:
            dict with 'url' for download and 'status'
        """
        start = time.time()
        while time.time() - start < max_wait:
            result = self.get_report(report_id)
            status = result.get("status", "")
            if status == "SUCCESS":
                return result
            if status == "FAILURE":
                raise ValueError(f"Report {report_id} failed: {result}")
            logger.debug("Report %s status: %s, waiting...", report_id, status)
            time.sleep(poll_interval)
        raise TimeoutError(f"Report {report_id} not ready after {max_wait}s")

    # ── Budget Rules ──────────────────────────────────────

    def get_campaign_budget(self, campaign_id, campaign_type="sp"):
        """Get budget details for a campaign."""
        ad_type = CAMPAIGN_TYPES.get(campaign_type, "sponsoredProducts")
        return self.get(f"/v2/{ad_type}/campaigns/{campaign_id}/budget")

    # ── History ───────────────────────────────────────────

    def get_campaign_history(self, campaign_id, campaign_type="sp",
                             from_date=None, to_date=None):
        """
        Get change history for a campaign.

        Args:
            from_date: Start date (YYYYMMDD)
            to_date: End date (YYYYMMDD)
        """
        params = {}
        if from_date:
            params["fromDate"] = from_date
        if to_date:
            params["toDate"] = to_date
        ad_type = CAMPAIGN_TYPES.get(campaign_type, "sponsoredProducts")
        return self.get(
            f"/v2/{ad_type}/campaigns/{campaign_id}/history",
            params or None,
        )

    # ── Convenience / Batch ───────────────────────────────

    def pause_campaign(self, campaign_id, campaign_type="sp"):
        """Pause a campaign."""
        return self.update_campaign(campaign_id, campaign_type, state="paused")

    def enable_campaign(self, campaign_id, campaign_type="sp"):
        """Enable a paused campaign."""
        return self.update_campaign(campaign_id, campaign_type, state="enabled")

    def set_campaign_budget(self, campaign_id, daily_budget, campaign_type="sp"):
        """Set daily budget for a campaign."""
        return self.update_campaign(
            campaign_id, campaign_type, dailyBudget=float(daily_budget)
        )

    def bulk_update_bids(self, keyword_updates, campaign_type="sp"):
        """
        Bulk update keyword bids.

        Args:
            keyword_updates: List of dicts with 'keywordId' and 'bid'
        """
        body = [
            {"keywordId": int(kw["keywordId"]), "bid": float(kw["bid"])}
            for kw in keyword_updates
        ]
        ad_type = CAMPAIGN_TYPES.get(campaign_type, "sponsoredProducts")
        return self.put(f"/v2/{ad_type}/keywords", body=body)

    def get_campaign_summary(self, campaign_id, campaign_type="sp",
                             report_date=None):
        """
        Get a quick summary report for a campaign.
        Returns metrics dict with impressions, clicks, cost, sales.
        """
        result = self.request_report(
            "campaigns", campaign_type, report_date,
            metrics=["impressions", "clicks", "cost", "attributedSales7d"],
        )
        report_id = result.get("reportId")
        if not report_id:
            return result
        return self.download_report(report_id)
