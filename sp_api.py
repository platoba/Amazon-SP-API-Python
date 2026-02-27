"""
Amazon SP-API Python SDK
轻量级Amazon Selling Partner API客户端
"""

import time
import json
import hashlib
import hmac
import datetime
import requests
from urllib.parse import quote, urlencode


class SPAPIError(Exception):
    def __init__(self, message, status_code=None, response=None):
        super().__init__(message)
        self.status_code = status_code
        self.response = response


class SPAPI:
    """Amazon Selling Partner API Client"""

    ENDPOINTS = {
        "NA": "https://sellingpartnerapi-na.amazon.com",
        "EU": "https://sellingpartnerapi-eu.amazon.com",
        "FE": "https://sellingpartnerapi-fe.amazon.com",
    }

    MARKETPLACES = {
        "US": ("ATVPDKIKX0DER", "NA"), "CA": ("A2EUQ1WTGCTBG2", "NA"),
        "MX": ("A1AM78C64UM0Y8", "NA"), "BR": ("A2Q3Y263D00KWC", "NA"),
        "UK": ("A1F83G8C2ARO7P", "EU"), "DE": ("A1PA6795UKMFR9", "EU"),
        "FR": ("A13V1IB3VIYZZH", "EU"), "IT": ("APJ6JRA9NG5V4", "EU"),
        "ES": ("A1RKKUPIHCS9HS", "EU"), "NL": ("A1805IZSGTT6HS", "EU"),
        "SE": ("A2NODRKZP88ZB9", "EU"), "PL": ("A1C3SOZRARQ6R3", "EU"),
        "TR": ("A33AVAJ2PDY3EV", "EU"), "AE": ("A2VIGQ35RCS4UG", "EU"),
        "SA": ("A17E79C6D8DWNP", "EU"), "IN": ("A21TJRUUN4KGV", "EU"),
        "EG": ("ARBP9OOSHTCHU", "EU"), "JP": ("A1VC38T7YXB528", "FE"),
        "AU": ("A39IBJ37TRP1C6", "FE"), "SG": ("A19VAU5U5O7RUS", "FE"),
    }

    def __init__(self, refresh_token, client_id, client_secret,
                 aws_access_key=None, aws_secret_key=None, role_arn=None,
                 marketplace="US"):
        self.refresh_token = refresh_token
        self.client_id = client_id
        self.client_secret = client_secret
        self.aws_access_key = aws_access_key
        self.aws_secret_key = aws_secret_key
        self.role_arn = role_arn

        if marketplace not in self.MARKETPLACES:
            raise ValueError(f"Unknown marketplace: {marketplace}. Use: {list(self.MARKETPLACES.keys())}")

        self.marketplace_id, region = self.MARKETPLACES[marketplace]
        self.endpoint = self.ENDPOINTS[region]
        self.region = {"NA": "us-east-1", "EU": "eu-west-1", "FE": "us-west-2"}[region]

        self._access_token = None
        self._token_expires = 0
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "SP-API-Python/1.0"})

    # ── Auth ──────────────────────────────────────────────
    def _get_access_token(self):
        now = time.time()
        if self._access_token and now < self._token_expires - 60:
            return self._access_token

        r = requests.post("https://api.amazon.com/auth/o2/token", data={
            "grant_type": "refresh_token",
            "refresh_token": self.refresh_token,
            "client_id": self.client_id,
            "client_secret": self.client_secret,
        })
        r.raise_for_status()
        data = r.json()
        self._access_token = data["access_token"]
        self._token_expires = now + data.get("expires_in", 3600)
        return self._access_token

    # ── Request ───────────────────────────────────────────
    def _request(self, method, path, params=None, body=None, **kwargs):
        url = self.endpoint + path
        token = self._get_access_token()

        headers = {
            "x-amz-access-token": token,
            "Content-Type": "application/json",
        }

        r = self.session.request(
            method, url, params=params,
            json=body if body else None,
            headers=headers, timeout=30, **kwargs
        )

        if r.status_code == 429:
            retry_after = int(r.headers.get("Retry-After", 2))
            time.sleep(retry_after)
            return self._request(method, path, params, body, **kwargs)

        if r.status_code >= 400:
            raise SPAPIError(
                f"SP-API {r.status_code}: {r.text[:500]}",
                status_code=r.status_code, response=r
            )
        return r.json() if r.text else {}

    def get(self, path, params=None):
        return self._request("GET", path, params=params)

    def post(self, path, body=None, params=None):
        return self._request("POST", path, params=params, body=body)

    def put(self, path, body=None, params=None):
        return self._request("PUT", path, params=params, body=body)

    def delete(self, path, params=None):
        return self._request("DELETE", path, params=params)

    # ── Catalog Items ─────────────────────────────────────
    def search_catalog(self, keywords, **kwargs):
        params = {
            "marketplaceIds": self.marketplace_id,
            "keywords": keywords,
            "includedData": kwargs.get("included_data", "summaries,images,salesRanks"),
            "pageSize": kwargs.get("page_size", 20),
        }
        return self.get("/catalog/2022-04-01/items", params)

    def get_catalog_item(self, asin, **kwargs):
        params = {
            "marketplaceIds": self.marketplace_id,
            "includedData": kwargs.get("included_data", "summaries,images,salesRanks,attributes"),
        }
        return self.get(f"/catalog/2022-04-01/items/{asin}", params)

    # ── Orders ────────────────────────────────────────────
    def get_orders(self, created_after=None, **kwargs):
        if not created_after:
            created_after = (datetime.datetime.utcnow() - datetime.timedelta(days=7)).strftime("%Y-%m-%dT%H:%M:%SZ")
        params = {
            "MarketplaceIds": self.marketplace_id,
            "CreatedAfter": created_after,
            "MaxResultsPerPage": kwargs.get("max_results", 100),
        }
        if kwargs.get("order_statuses"):
            params["OrderStatuses"] = ",".join(kwargs["order_statuses"])
        return self.get("/orders/v0/orders", params)

    def get_order(self, order_id):
        return self.get(f"/orders/v0/orders/{order_id}")

    def get_order_items(self, order_id):
        return self.get(f"/orders/v0/orders/{order_id}/orderItems")

    # ── Product Pricing ───────────────────────────────────
    def get_competitive_pricing(self, asins):
        if isinstance(asins, str):
            asins = [asins]
        params = {
            "MarketplaceId": self.marketplace_id,
            "ItemType": "Asin",
            "Asins": ",".join(asins),
        }
        return self.get("/products/pricing/v0/competitivePrice", params)

    def get_item_offers(self, asin, item_condition="New"):
        params = {
            "MarketplaceId": self.marketplace_id,
            "ItemCondition": item_condition,
        }
        return self.get(f"/products/pricing/v0/items/{asin}/offers", params)

    # ── Reports ───────────────────────────────────────────
    def create_report(self, report_type, start_date=None, end_date=None, **kwargs):
        body = {
            "reportType": report_type,
            "marketplaceIds": [self.marketplace_id],
        }
        if start_date:
            body["dataStartTime"] = start_date
        if end_date:
            body["dataEndTime"] = end_date
        return self.post("/reports/2021-06-30/reports", body)

    def get_report(self, report_id):
        return self.get(f"/reports/2021-06-30/reports/{report_id}")

    def get_report_document(self, document_id):
        return self.get(f"/reports/2021-06-30/documents/{document_id}")

    # ── FBA Inventory ─────────────────────────────────────
    def get_inventory_summaries(self, **kwargs):
        params = {
            "granularityType": "Marketplace",
            "granularityId": self.marketplace_id,
            "marketplaceIds": self.marketplace_id,
        }
        return self.get("/fba/inventory/v1/summaries", params)

    # ── Listings ──────────────────────────────────────────
    def get_listings_item(self, seller_id, sku, **kwargs):
        params = {
            "marketplaceIds": self.marketplace_id,
            "includedData": kwargs.get("included_data", "summaries,attributes,issues"),
        }
        return self.get(f"/listings/2021-08-01/items/{seller_id}/{quote(sku)}", params)

    def put_listings_item(self, seller_id, sku, body):
        return self.put(f"/listings/2021-08-01/items/{seller_id}/{quote(sku)}", body)

    # ── Feeds ─────────────────────────────────────────────
    def create_feed(self, feed_type, document_id, **kwargs):
        body = {
            "feedType": feed_type,
            "marketplaceIds": [self.marketplace_id],
            "inputFeedDocumentId": document_id,
        }
        return self.post("/feeds/2021-06-30/feeds", body)

    def get_feed(self, feed_id):
        return self.get(f"/feeds/2021-06-30/feeds/{feed_id}")

    # ── Notifications ─────────────────────────────────────
    def get_subscription(self, notification_type):
        return self.get(f"/notifications/v1/subscriptions/{notification_type}")

    def create_subscription(self, notification_type, destination_id):
        body = {"destinationId": destination_id}
        return self.post(f"/notifications/v1/subscriptions/{notification_type}", body)
