"""
Sellers API module — SP-API Sellers v1.
Marketplace participations and account info.
"""

from sp_api.base import BaseAPI


class SellersAPI(BaseAPI):
    """Amazon SP-API Sellers endpoints."""

    def get_marketplace_participations(self):
        """
        Get a list of marketplaces the seller participates in,
        along with information about the seller's participation in each.

        Returns:
            dict with 'payload' containing list of marketplace participations.
        """
        return self.get("/sellers/v1/marketplaceParticipations")

    def get_account_info(self):
        """
        Convenience: extract seller account info from marketplace participations.

        Returns:
            dict with marketplace_id → {marketplace, participation} mapping.
        """
        result = self.get_marketplace_participations()
        payload = result.get("payload", [])
        info = {}
        for entry in payload:
            mp = entry.get("marketplace", {})
            mp_id = mp.get("id", "unknown")
            info[mp_id] = {
                "name": mp.get("name"),
                "country_code": mp.get("countryCode"),
                "default_currency": mp.get("defaultCurrencyCode"),
                "default_language": mp.get("defaultLanguageCode"),
                "domain": mp.get("domainName"),
                "is_participating": entry.get("participation", {}).get(
                    "isParticipating", False
                ),
                "has_suspended_listings": entry.get("participation", {}).get(
                    "hasSuspendedListings", False
                ),
            }
        return info

    def get_active_marketplaces(self):
        """
        Get only marketplaces where the seller is actively participating.

        Returns:
            list of marketplace info dicts.
        """
        all_info = self.get_account_info()
        return [
            {"marketplace_id": mp_id, **info}
            for mp_id, info in all_info.items()
            if info.get("is_participating")
        ]
