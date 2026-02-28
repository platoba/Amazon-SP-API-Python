"""
Catalog Items API module — SP-API Catalog Items 2022-04-01.
"""

from sp_api.base import BaseAPI


class CatalogAPI(BaseAPI):
    """Amazon SP-API Catalog Items endpoints."""

    CATALOG_VERSION = "2022-04-01"

    def search_catalog(self, keywords, included_data=None, page_size=20,
                       identifiers=None, identifiers_type=None, **kwargs):
        """
        Search the Amazon catalog.

        Args:
            keywords: Search keywords string.
            included_data: Comma-separated data types (summaries,images,salesRanks,...).
            page_size: Results per page (1-20).
            identifiers: List of identifiers (ASINs, UPCs, etc.).
            identifiers_type: Type of identifiers (ASIN, UPC, EAN, ISBN).
        """
        params = {
            "marketplaceIds": self.marketplace_id,
            "keywords": keywords,
            "includedData": included_data or "summaries,images,salesRanks",
            "pageSize": min(page_size, 20),
        }
        if identifiers:
            params["identifiers"] = ",".join(identifiers) if isinstance(identifiers, list) else identifiers
        if identifiers_type:
            params["identifiersType"] = identifiers_type
        params.update(kwargs)
        return self.get(f"/catalog/{self.CATALOG_VERSION}/items", params)

    def get_catalog_item(self, asin, included_data=None, **kwargs):
        """
        Get detailed info for a single catalog item.

        Args:
            asin: Amazon Standard Identification Number.
            included_data: Data to include in response.
        """
        params = {
            "marketplaceIds": self.marketplace_id,
            "includedData": included_data or "summaries,images,salesRanks,attributes",
        }
        params.update(kwargs)
        return self.get(f"/catalog/{self.CATALOG_VERSION}/items/{asin}", params)

    def search_catalog_by_identifier(self, identifiers, identifiers_type="ASIN",
                                     included_data=None, **kwargs):
        """
        Search catalog by identifiers (ASIN, UPC, EAN, ISBN).

        Args:
            identifiers: List of identifiers.
            identifiers_type: ASIN, UPC, EAN, or ISBN.
            included_data: Data to include.
        """
        id_str = ",".join(identifiers) if isinstance(identifiers, list) else identifiers
        params = {
            "marketplaceIds": self.marketplace_id,
            "identifiers": id_str,
            "identifiersType": identifiers_type,
            "includedData": included_data or "summaries",
        }
        params.update(kwargs)
        return self.get(f"/catalog/{self.CATALOG_VERSION}/items", params)
