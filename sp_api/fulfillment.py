"""
Fulfillment Outbound API module — SP-API Fulfillment Outbound 2020-07-01.
Multi-Channel Fulfillment (MCF) for FBA inventory.
"""

from sp_api.base import BaseAPI


class FulfillmentAPI(BaseAPI):
    """Amazon SP-API Fulfillment Outbound (MCF) endpoints."""

    FO_VERSION = "2020-07-01"

    def get_fulfillment_preview(self, address, items, shipping_speed_categories=None,
                                include_cod=False, include_delivery_windows=False, **kwargs):
        """
        Get fulfillment preview (shipping options + estimated delivery).

        Args:
            address: Dict with name, line1, city, stateOrRegion, postalCode, countryCode.
            items: List of dicts with sellerSku, quantity, sellerFulfillmentOrderItemId.
            shipping_speed_categories: List of speed categories (Standard, Expedited, Priority).
            include_cod: Include COD pricing.
            include_delivery_windows: Include delivery window info.
        """
        body = {
            "marketplaceId": self.marketplace_id,
            "address": address,
            "items": items,
        }
        if shipping_speed_categories:
            body["shippingSpeedCategories"] = shipping_speed_categories
        if include_cod:
            body["includeCODFulfillmentPreview"] = True
        if include_delivery_windows:
            body["includeDeliveryWindows"] = True
        body.update(kwargs)
        return self.post(f"/fba/outbound/fulfillmentOrders/{self.FO_VERSION}/previews", body)

    def create_fulfillment_order(self, seller_fulfillment_order_id, displayable_order_id,
                                  displayable_order_date, displayable_order_comment,
                                  shipping_speed_category, destination_address,
                                  items, **kwargs):
        """
        Create a Multi-Channel Fulfillment order.

        Args:
            seller_fulfillment_order_id: Unique order ID.
            displayable_order_id: Customer-facing order ID.
            displayable_order_date: ISO 8601 datetime.
            displayable_order_comment: Comment shown on packing slip.
            shipping_speed_category: Standard, Expedited, or Priority.
            destination_address: Shipping address dict.
            items: List of items with sellerSku, quantity, etc.
        """
        body = {
            "marketplaceId": self.marketplace_id,
            "sellerFulfillmentOrderId": seller_fulfillment_order_id,
            "displayableOrderId": displayable_order_id,
            "displayableOrderDate": displayable_order_date,
            "displayableOrderComment": displayable_order_comment,
            "shippingSpeedCategory": shipping_speed_category,
            "destinationAddress": destination_address,
            "items": items,
        }
        body.update(kwargs)
        return self.post(f"/fba/outbound/fulfillmentOrders/{self.FO_VERSION}", body)

    def get_fulfillment_order(self, seller_fulfillment_order_id):
        """Get a fulfillment order by ID."""
        return self.get(
            f"/fba/outbound/fulfillmentOrders/{self.FO_VERSION}/{seller_fulfillment_order_id}"
        )

    def list_all_fulfillment_orders(self, query_start_date=None, next_token=None, **kwargs):
        """
        List fulfillment orders.

        Args:
            query_start_date: ISO 8601 datetime.
            next_token: Pagination token.
        """
        params = {}
        if query_start_date:
            params["queryStartDate"] = query_start_date
        if next_token:
            params["nextToken"] = next_token
        params.update(kwargs)
        return self.get(f"/fba/outbound/fulfillmentOrders/{self.FO_VERSION}", params)

    def cancel_fulfillment_order(self, seller_fulfillment_order_id):
        """Cancel a fulfillment order."""
        return self.put(
            f"/fba/outbound/fulfillmentOrders/{self.FO_VERSION}/{seller_fulfillment_order_id}/cancel"
        )

    def get_package_tracking_details(self, package_number):
        """
        Get tracking details for a package.

        Args:
            package_number: Package number from the fulfillment order.
        """
        params = {"packageNumber": package_number}
        return self.get(f"/fba/outbound/fulfillmentOrders/{self.FO_VERSION}/tracking", params)

    def list_return_reason_codes(self, seller_sku, language="en_US",
                                  marketplace_id=None, **kwargs):
        """
        Get return reason codes for a SKU.

        Args:
            seller_sku: Seller SKU.
            language: Language code.
            marketplace_id: Override marketplace.
        """
        params = {
            "sellerSku": seller_sku,
            "language": language,
        }
        if marketplace_id:
            params["marketplaceId"] = marketplace_id
        params.update(kwargs)
        return self.get(
            f"/fba/outbound/fulfillmentOrders/{self.FO_VERSION}/returnReasonCodes",
            params,
        )

    def create_fulfillment_return(self, seller_fulfillment_order_id, items):
        """
        Create a return for a fulfillment order.

        Args:
            seller_fulfillment_order_id: Order ID.
            items: List of return item dicts (sellerReturnItemId, sellerFulfillmentOrderItemId,
                   amazonShipmentId, returnReasonCode, returnComment).
        """
        body = {"items": items}
        return self.put(
            f"/fba/outbound/fulfillmentOrders/{self.FO_VERSION}/{seller_fulfillment_order_id}/return",
            body,
        )

    def get_features(self):
        """Get available fulfillment features for the seller."""
        params = {"marketplaceId": self.marketplace_id}
        return self.get(f"/fba/outbound/fulfillmentOrders/{self.FO_VERSION}/features", params)

    def get_feature_inventory(self, feature_name, next_token=None, **kwargs):
        """
        Get inventory eligible for a specific feature.

        Args:
            feature_name: Feature name (e.g., "BLANK_BOX").
            next_token: Pagination token.
        """
        params = {"marketplaceId": self.marketplace_id}
        if next_token:
            params["nextToken"] = next_token
        params.update(kwargs)
        return self.get(
            f"/fba/outbound/fulfillmentOrders/{self.FO_VERSION}/features/inventory/{feature_name}",
            params,
        )

    def get_feature_sku(self, feature_name, seller_sku):
        """
        Check if a SKU is eligible for a feature.

        Args:
            feature_name: Feature name.
            seller_sku: Seller SKU.
        """
        params = {"marketplaceId": self.marketplace_id}
        return self.get(
            f"/fba/outbound/fulfillmentOrders/{self.FO_VERSION}/features/inventory/{feature_name}/{seller_sku}",
            params,
        )
