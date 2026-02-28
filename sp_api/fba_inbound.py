"""
FBA Inbound Shipments API module — SP-API Fulfillment Inbound.

Manage FBA inbound shipments: create shipment plans, add items,
generate labels, manage transport, and track shipment status.
"""

from datetime import datetime, timezone
from sp_api.base import BaseAPI


# Label prep preferences
LABEL_PREP_TYPES = ["SELLER_LABEL", "AMAZON_LABEL_ONLY", "AMAZON_LABEL_PREFERRED"]

# Shipment statuses
SHIPMENT_STATUSES = [
    "WORKING", "READY_TO_SHIP", "SHIPPED", "RECEIVING",
    "CANCELLED", "DELETED", "CLOSED", "ERROR", "IN_TRANSIT", "DELIVERED",
    "CHECKED_IN",
]

# Condition types
CONDITION_TYPES = [
    "NewItem", "NewWithWarranty", "NewOEM", "NewOpenBox",
    "UsedLikeNew", "UsedVeryGood", "UsedGood", "UsedAcceptable",
    "Refurbished", "CollectibleLikeNew", "CollectibleVeryGood",
    "CollectibleGood", "CollectibleAcceptable",
]


class FBAInboundAPI(BaseAPI):
    """
    FBA Inbound Shipments API.

    Create and manage inbound shipments to Amazon fulfillment centers.
    Handles shipment plans, item labeling, box content, transport,
    and shipment tracking.
    """

    # ── Shipment Plans ────────────────────────────────────

    def create_inbound_shipment_plan(self, items, ship_from_address,
                                     label_prep="SELLER_LABEL"):
        """
        Create an inbound shipment plan.

        Amazon will suggest how to split items across fulfillment centers.

        Args:
            items: List of dicts with:
                - SellerSKU: str
                - ASIN: str (optional)
                - Quantity: int
                - QuantityInCase: int (optional)
                - Condition: str (default 'NewItem')
            ship_from_address: Dict with Name, AddressLine1, City,
                              StateOrProvinceCode, PostalCode, CountryCode
            label_prep: Label prep preference
        """
        if label_prep not in LABEL_PREP_TYPES:
            raise ValueError(f"label_prep must be one of {LABEL_PREP_TYPES}")

        inbound_items = []
        for item in items:
            entry = {
                "SellerSKU": item["SellerSKU"],
                "Quantity": int(item["Quantity"]),
                "Condition": item.get("Condition", "NewItem"),
            }
            if "ASIN" in item:
                entry["ASIN"] = item["ASIN"]
            if "QuantityInCase" in item:
                entry["QuantityInCase"] = int(item["QuantityInCase"])
            if "PrepDetailsList" in item:
                entry["PrepDetailsList"] = item["PrepDetailsList"]
            inbound_items.append(entry)

        body = {
            "ShipFromAddress": ship_from_address,
            "InboundShipmentPlanRequestItems": inbound_items,
            "LabelPrepPreference": label_prep,
        }
        return self.post(
            "/fba/inbound/v0/plans", body=body
        )

    # ── Shipment CRUD ─────────────────────────────────────

    def create_inbound_shipment(self, shipment_id, shipment_name, items,
                                destination_fc, ship_from_address,
                                label_prep="SELLER_LABEL",
                                status="WORKING"):
        """
        Create an inbound shipment (after plan creation).

        Args:
            shipment_id: Shipment ID from the plan
            shipment_name: Human-readable name
            items: List of dicts with SellerSKU, QuantityShipped
            destination_fc: Destination fulfillment center ID
            ship_from_address: Ship-from address dict
            label_prep: Label prep preference
            status: Initial status (WORKING or SHIPPED)
        """
        inbound_items = [
            {
                "SellerSKU": item["SellerSKU"],
                "QuantityShipped": int(item["QuantityShipped"]),
                "QuantityInCase": int(item.get("QuantityInCase", 0)) or None,
            }
            for item in items
        ]
        # Remove None values
        for item in inbound_items:
            item = {k: v for k, v in item.items() if v is not None}

        body = {
            "InboundShipmentHeader": {
                "ShipmentName": shipment_name,
                "ShipFromAddress": ship_from_address,
                "DestinationFulfillmentCenterId": destination_fc,
                "LabelPrepPreference": label_prep,
                "ShipmentStatus": status,
            },
            "InboundShipmentItems": inbound_items,
            "MarketplaceId": self.marketplace_id,
        }
        return self.post(
            f"/fba/inbound/v0/shipments/{shipment_id}", body=body
        )

    def update_inbound_shipment(self, shipment_id, items=None,
                                shipment_name=None, status=None,
                                ship_from_address=None):
        """
        Update an existing inbound shipment.

        Args:
            shipment_id: Shipment to update
            items: Updated items list (optional)
            shipment_name: New name (optional)
            status: New status (optional)
            ship_from_address: Updated address (optional)
        """
        body = {"MarketplaceId": self.marketplace_id}
        header = {}

        if shipment_name:
            header["ShipmentName"] = shipment_name
        if status:
            header["ShipmentStatus"] = status
        if ship_from_address:
            header["ShipFromAddress"] = ship_from_address

        if header:
            body["InboundShipmentHeader"] = header

        if items:
            body["InboundShipmentItems"] = [
                {
                    "SellerSKU": item["SellerSKU"],
                    "QuantityShipped": int(item["QuantityShipped"]),
                }
                for item in items
            ]

        return self.put(
            f"/fba/inbound/v0/shipments/{shipment_id}", body=body
        )

    # ── Shipment Queries ──────────────────────────────────

    def get_shipments(self, shipment_status_list=None, shipment_id_list=None,
                      last_updated_after=None, last_updated_before=None,
                      next_token=None):
        """
        List inbound shipments.

        Args:
            shipment_status_list: Filter by statuses
            shipment_id_list: Filter by shipment IDs
            last_updated_after: ISO datetime
            last_updated_before: ISO datetime
            next_token: Pagination token
        """
        params = {"MarketplaceId": self.marketplace_id, "QueryType": "SHIPMENT"}

        if shipment_status_list:
            params["ShipmentStatusList"] = ",".join(shipment_status_list)
            params["QueryType"] = "SHIPMENT"
        if shipment_id_list:
            params["ShipmentIdList"] = ",".join(shipment_id_list)
            params["QueryType"] = "SHIPMENT"
        if last_updated_after:
            params["LastUpdatedAfter"] = last_updated_after
            params["QueryType"] = "DATE_RANGE"
        if last_updated_before:
            params["LastUpdatedBefore"] = last_updated_before
        if next_token:
            params["NextToken"] = next_token

        return self.get("/fba/inbound/v0/shipments", params)

    def get_shipment_items(self, shipment_id, next_token=None):
        """Get items in a specific shipment."""
        params = {"MarketplaceId": self.marketplace_id}
        if next_token:
            params["NextToken"] = next_token
        return self.get(
            f"/fba/inbound/v0/shipments/{shipment_id}/items", params
        )

    def get_shipment_items_by_seller(self, last_updated_after=None,
                                     last_updated_before=None,
                                     next_token=None):
        """Get all shipment items across all shipments."""
        params = {"MarketplaceId": self.marketplace_id, "QueryType": "DATE_RANGE"}
        if last_updated_after:
            params["LastUpdatedAfter"] = last_updated_after
        if last_updated_before:
            params["LastUpdatedBefore"] = last_updated_before
        if next_token:
            params["NextToken"] = next_token
        return self.get("/fba/inbound/v0/shipmentItems", params)

    # ── Labels ────────────────────────────────────────────

    def get_labels(self, shipment_id, page_type="PackageLabel_Letter_2",
                   label_type="UNIQUE", number_of_packages=None,
                   package_labels_to_print=None, number_of_pallets=None):
        """
        Get package/pallet labels for a shipment.

        Args:
            shipment_id: Shipment ID
            page_type: Label page format
            label_type: UNIQUE, SELLER_LABEL, or BARCODE_2D
            number_of_packages: Number of packages (for UNIQUE labels)
            package_labels_to_print: Specific labels to print
            number_of_pallets: For pallet shipments
        """
        params = {
            "PageType": page_type,
            "LabelType": label_type,
            "MarketplaceId": self.marketplace_id,
        }
        if number_of_packages:
            params["NumberOfPackages"] = number_of_packages
        if package_labels_to_print:
            params["PackageLabelsToPrint"] = ",".join(package_labels_to_print)
        if number_of_pallets:
            params["NumberOfPallets"] = number_of_pallets

        return self.get(
            f"/fba/inbound/v0/shipments/{shipment_id}/labels", params
        )

    def get_item_labels(self, shipment_id, seller_sku, quantity,
                        page_type="PackageLabel_Letter_2"):
        """Get FNSKU labels for items in a shipment."""
        params = {
            "SellerSKU": seller_sku,
            "Quantity": quantity,
            "PageType": page_type,
            "MarketplaceId": self.marketplace_id,
        }
        return self.get(
            f"/fba/inbound/v0/shipments/{shipment_id}/items/labels", params
        )

    # ── Prep Instructions ─────────────────────────────────

    def get_prep_instructions(self, seller_skus=None, asin_list=None):
        """
        Get prep instructions for items.

        Args:
            seller_skus: List of seller SKUs
            asin_list: List of ASINs
        """
        params = {"ShipToCountryCode": "US", "MarketplaceId": self.marketplace_id}
        if seller_skus:
            params["SellerSKUList"] = ",".join(seller_skus)
        if asin_list:
            params["ASINList"] = ",".join(asin_list)
        return self.get("/fba/inbound/v0/prepInstructions", params)

    # ── Transport ─────────────────────────────────────────

    def put_transport_details(self, shipment_id, is_partnered,
                              shipment_type, transport_details):
        """
        Submit transport details for a shipment.

        Args:
            shipment_id: Shipment ID
            is_partnered: True for Amazon-partnered carrier
            shipment_type: 'SP' (small parcel) or 'LTL' (less than truckload)
            transport_details: Carrier/tracking details dict
        """
        body = {
            "IsPartnered": is_partnered,
            "ShipmentType": shipment_type,
            "TransportDetails": transport_details,
        }
        return self.put(
            f"/fba/inbound/v0/shipments/{shipment_id}/transport", body=body
        )

    def get_transport_details(self, shipment_id):
        """Get transport details for a shipment."""
        return self.get(
            f"/fba/inbound/v0/shipments/{shipment_id}/transport"
        )

    def estimate_transport(self, shipment_id):
        """Estimate shipping cost for a partnered shipment."""
        return self.post(
            f"/fba/inbound/v0/shipments/{shipment_id}/transport/estimate"
        )

    def confirm_transport(self, shipment_id):
        """Confirm transport details (triggers label generation for partnered)."""
        return self.post(
            f"/fba/inbound/v0/shipments/{shipment_id}/transport/confirm"
        )

    def void_transport(self, shipment_id):
        """Void a confirmed transport (before shipping)."""
        return self.post(
            f"/fba/inbound/v0/shipments/{shipment_id}/transport/void"
        )

    # ── Box Content ───────────────────────────────────────

    def get_box_content(self, shipment_id):
        """Get box content information for a shipment."""
        return self.get(
            f"/fba/inbound/v0/shipments/{shipment_id}/boxContent"
        )

    def put_box_content(self, shipment_id, boxes):
        """
        Submit box content information.

        Args:
            boxes: List of box dicts with items and dimensions
        """
        body = {"Boxes": boxes}
        return self.put(
            f"/fba/inbound/v0/shipments/{shipment_id}/boxContent", body=body
        )

    # ── Convenience ───────────────────────────────────────

    def get_active_shipments(self):
        """Get all active (non-closed) shipments."""
        active_statuses = [
            "WORKING", "READY_TO_SHIP", "SHIPPED",
            "IN_TRANSIT", "RECEIVING", "CHECKED_IN",
        ]
        return self.get_shipments(shipment_status_list=active_statuses)

    def mark_shipped(self, shipment_id):
        """Mark a shipment as shipped."""
        return self.update_inbound_shipment(shipment_id, status="SHIPPED")

    def cancel_shipment(self, shipment_id):
        """Cancel a shipment (only if status is WORKING)."""
        return self.update_inbound_shipment(shipment_id, status="CANCELLED")

    def quick_ship(self, sku_quantities, ship_from_address,
                   shipment_name=None):
        """
        Quick shipment creation: plan → create in one call.

        Args:
            sku_quantities: Dict of {SellerSKU: quantity}
            ship_from_address: Ship-from address
            shipment_name: Optional name (auto-generated if None)

        Returns:
            List of created shipment IDs
        """
        items = [
            {"SellerSKU": sku, "Quantity": qty}
            for sku, qty in sku_quantities.items()
        ]

        # Step 1: Create plan
        plan_result = self.create_inbound_shipment_plan(items, ship_from_address)
        plans = plan_result.get("payload", {}).get(
            "InboundShipmentPlans", plan_result.get("InboundShipmentPlans", [])
        )

        created = []
        for i, plan in enumerate(plans):
            sid = plan.get("ShipmentId", "")
            fc = plan.get("DestinationFulfillmentCenterId", "")
            plan_items = plan.get("Items", [])

            name = shipment_name or f"Quick-Ship-{datetime.now(timezone.utc).strftime('%Y%m%d')}-{i+1}"

            ship_items = [
                {"SellerSKU": item["SellerSKU"], "QuantityShipped": item["Quantity"]}
                for item in plan_items
            ]

            self.create_inbound_shipment(
                sid, name, ship_items, fc, ship_from_address
            )
            created.append({"shipment_id": sid, "fc": fc, "items": len(ship_items)})

        return created
