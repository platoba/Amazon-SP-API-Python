"""
Shipping API module — SP-API Shipping v2.
Manage shipping labels, rates, and tracking.
"""

from sp_api.base import BaseAPI


class ShippingAPI(BaseAPI):
    """Amazon SP-API Shipping v2 endpoints."""

    SHIPPING_VERSION = "v2"

    def get_rates(self, ship_from, ship_to, packages, service_type=None, **kwargs):
        """
        Get shipping rates for a shipment.

        Args:
            ship_from: dict with address fields (name, addressLine1, city,
                       stateOrRegion, postalCode, countryCode).
            ship_to: dict with address fields.
            packages: list of package dicts (dimensions, weight, etc.).
            service_type: Optional service type filter.

        Returns:
            Shipping rates response.
        """
        body = {
            "shipFrom": ship_from,
            "shipTo": ship_to,
            "packages": packages,
        }
        if service_type:
            body["serviceType"] = service_type
        body.update(kwargs)
        return self.post(f"/shipping/{self.SHIPPING_VERSION}/shipments/rates", body=body)

    def purchase_shipment(self, request_token, rate_id, **kwargs):
        """
        Purchase a shipping label for a shipment.

        Args:
            request_token: Token from get_rates response.
            rate_id: Selected rate ID.

        Returns:
            Purchased shipment with label info.
        """
        body = {
            "requestToken": request_token,
            "rateId": rate_id,
        }
        body.update(kwargs)
        return self.post(f"/shipping/{self.SHIPPING_VERSION}/shipments", body=body)

    def get_shipment(self, shipment_id):
        """
        Get shipment details.

        Args:
            shipment_id: The shipment identifier.

        Returns:
            Shipment details including tracking.
        """
        return self.get(f"/shipping/{self.SHIPPING_VERSION}/shipments/{shipment_id}")

    def cancel_shipment(self, shipment_id):
        """
        Cancel a shipment.

        Args:
            shipment_id: The shipment to cancel.

        Returns:
            Cancellation confirmation.
        """
        return self.put(f"/shipping/{self.SHIPPING_VERSION}/shipments/{shipment_id}/cancel")

    def get_tracking(self, tracking_id, carrier_id):
        """
        Get tracking information.

        Args:
            tracking_id: Tracking number.
            carrier_id: Carrier identifier (e.g., "AMZN_US").

        Returns:
            Tracking details with events.
        """
        params = {
            "trackingId": tracking_id,
            "carrierId": carrier_id,
        }
        return self.get(f"/shipping/{self.SHIPPING_VERSION}/tracking", params)

    def get_access_points(self, access_point_types, country_code, postal_code=None):
        """
        Get available access points (pickup locations).

        Args:
            access_point_types: List of types (e.g., ["HELIX", "CAMPUS_LOCKER"]).
            country_code: Two-letter country code.
            postal_code: Optional postal code filter.

        Returns:
            List of access points.
        """
        params = {
            "accessPointTypes": ",".join(access_point_types),
            "countryCode": country_code,
        }
        if postal_code:
            params["postalCode"] = postal_code
        return self.get(f"/shipping/{self.SHIPPING_VERSION}/accessPoints", params)

    def get_additional_inputs(self, request_token, rate_id):
        """
        Get additional inputs required for shipment purchase.

        Args:
            request_token: Token from get_rates.
            rate_id: Selected rate ID.

        Returns:
            Required additional input fields.
        """
        params = {
            "requestToken": request_token,
            "rateId": rate_id,
        }
        return self.get(
            f"/shipping/{self.SHIPPING_VERSION}/shipments/additionalInputs/schema",
            params,
        )
