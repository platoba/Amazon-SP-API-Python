"""
Base API module mixin.
All API modules inherit from this to get _get/_post/_put/_delete.
"""


class BaseAPI:
    """
    Mixin for SP-API modules.
    Expects the host class to have: get(), post(), put(), delete(), marketplace_id.
    """

    def _ensure_marketplace(self, params, key="marketplaceIds"):
        if key not in params and "MarketplaceIds" not in params:
            params[key] = self.marketplace_id
        return params
