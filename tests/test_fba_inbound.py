"""Tests for FBA Inbound Shipments API module."""

import pytest
from sp_api.fba_inbound import (
    FBAInboundAPI, LABEL_PREP_TYPES, SHIPMENT_STATUSES,
    CONDITION_TYPES,
)


class MockClient(FBAInboundAPI):
    """Mock client for testing FBAInboundAPI mixin."""

    def __init__(self):
        self.marketplace_id = "ATVPDKIKX0DER"
        self._calls = []

    def get(self, path, params=None):
        self._calls.append(("GET", path, params))
        return {"mock": True, "path": path}

    def post(self, path, body=None, params=None):
        self._calls.append(("POST", path, body))
        return {"mock": True, "path": path}

    def put(self, path, body=None, params=None):
        self._calls.append(("PUT", path, body))
        return {"mock": True, "path": path}

    def delete(self, path, params=None):
        self._calls.append(("DELETE", path, params))
        return {"mock": True, "path": path}


@pytest.fixture
def client():
    return MockClient()


@pytest.fixture
def ship_from():
    return {
        "Name": "Test Seller",
        "AddressLine1": "123 Main St",
        "City": "Seattle",
        "StateOrProvinceCode": "WA",
        "PostalCode": "98101",
        "CountryCode": "US",
    }


# ── Constants ─────────────────────────────────────────────

class TestConstants:
    def test_label_prep_types(self):
        assert "SELLER_LABEL" in LABEL_PREP_TYPES
        assert "AMAZON_LABEL_ONLY" in LABEL_PREP_TYPES

    def test_shipment_statuses(self):
        assert "WORKING" in SHIPMENT_STATUSES
        assert "SHIPPED" in SHIPMENT_STATUSES
        assert "RECEIVING" in SHIPMENT_STATUSES

    def test_condition_types(self):
        assert "NewItem" in CONDITION_TYPES
        assert "UsedLikeNew" in CONDITION_TYPES


# ── Shipment Plans ────────────────────────────────────────

class TestShipmentPlans:
    def test_create_inbound_shipment_plan(self, client, ship_from):
        items = [
            {"SellerSKU": "SKU-001", "Quantity": 10},
            {"SellerSKU": "SKU-002", "Quantity": 20, "ASIN": "B001TEST"},
        ]
        client.create_inbound_shipment_plan(items, ship_from)
        _, path, body = client._calls[-1]
        assert "plans" in path
        assert len(body["InboundShipmentPlanRequestItems"]) == 2
        assert body["InboundShipmentPlanRequestItems"][0]["SellerSKU"] == "SKU-001"
        assert body["LabelPrepPreference"] == "SELLER_LABEL"

    def test_create_plan_invalid_label_prep(self, client, ship_from):
        with pytest.raises(ValueError, match="label_prep"):
            client.create_inbound_shipment_plan(
                [{"SellerSKU": "A", "Quantity": 1}],
                ship_from,
                label_prep="INVALID",
            )

    def test_create_plan_with_condition(self, client, ship_from):
        items = [{"SellerSKU": "SKU-001", "Quantity": 5, "Condition": "UsedLikeNew"}]
        client.create_inbound_shipment_plan(items, ship_from)
        _, _, body = client._calls[-1]
        assert body["InboundShipmentPlanRequestItems"][0]["Condition"] == "UsedLikeNew"

    def test_create_plan_with_case_qty(self, client, ship_from):
        items = [{"SellerSKU": "SKU-001", "Quantity": 24, "QuantityInCase": 6}]
        client.create_inbound_shipment_plan(items, ship_from)
        _, _, body = client._calls[-1]
        assert body["InboundShipmentPlanRequestItems"][0]["QuantityInCase"] == 6


# ── Shipment CRUD ─────────────────────────────────────────

class TestShipmentCRUD:
    def test_create_inbound_shipment(self, client, ship_from):
        items = [{"SellerSKU": "SKU-001", "QuantityShipped": 10}]
        client.create_inbound_shipment(
            "SHP-001", "My Shipment", items, "PHX7", ship_from,
        )
        _, path, body = client._calls[-1]
        assert "SHP-001" in path
        assert body["InboundShipmentHeader"]["ShipmentName"] == "My Shipment"
        assert body["InboundShipmentHeader"]["DestinationFulfillmentCenterId"] == "PHX7"

    def test_update_inbound_shipment(self, client):
        client.update_inbound_shipment("SHP-001", status="SHIPPED")
        _, path, body = client._calls[-1]
        assert "SHP-001" in path
        assert body["InboundShipmentHeader"]["ShipmentStatus"] == "SHIPPED"

    def test_update_shipment_items(self, client):
        items = [{"SellerSKU": "SKU-001", "QuantityShipped": 15}]
        client.update_inbound_shipment("SHP-001", items=items)
        _, _, body = client._calls[-1]
        assert len(body["InboundShipmentItems"]) == 1


# ── Shipment Queries ──────────────────────────────────────

class TestShipmentQueries:
    def test_get_shipments_by_status(self, client):
        client.get_shipments(shipment_status_list=["WORKING", "SHIPPED"])
        _, _, params = client._calls[-1]
        assert "WORKING,SHIPPED" in params["ShipmentStatusList"]

    def test_get_shipments_by_id(self, client):
        client.get_shipments(shipment_id_list=["SHP-001", "SHP-002"])
        _, _, params = client._calls[-1]
        assert "SHP-001" in params["ShipmentIdList"]

    def test_get_shipments_by_date(self, client):
        client.get_shipments(last_updated_after="2024-01-01T00:00:00Z")
        _, _, params = client._calls[-1]
        assert params["QueryType"] == "DATE_RANGE"

    def test_get_shipment_items(self, client):
        result = client.get_shipment_items("SHP-001")
        assert "SHP-001" in result["path"]

    def test_get_shipment_items_pagination(self, client):
        client.get_shipment_items("SHP-001", next_token="token123")
        _, _, params = client._calls[-1]
        assert params["NextToken"] == "token123"

    def test_get_shipment_items_by_seller(self, client):
        result = client.get_shipment_items_by_seller(
            last_updated_after="2024-01-01"
        )
        assert result["mock"] is True


# ── Labels ────────────────────────────────────────────────

class TestLabels:
    def test_get_labels(self, client):
        result = client.get_labels("SHP-001")
        assert "labels" in result["path"]

    def test_get_labels_with_options(self, client):
        client.get_labels(
            "SHP-001",
            page_type="PackageLabel_A4_4",
            number_of_packages=10,
        )
        _, _, params = client._calls[-1]
        assert params["PageType"] == "PackageLabel_A4_4"
        assert params["NumberOfPackages"] == 10

    def test_get_item_labels(self, client):
        client.get_item_labels("SHP-001", "SKU-001", 50)
        _, _, params = client._calls[-1]
        assert params["SellerSKU"] == "SKU-001"
        assert params["Quantity"] == 50


# ── Prep Instructions ─────────────────────────────────────

class TestPrepInstructions:
    def test_get_prep_instructions_by_sku(self, client):
        client.get_prep_instructions(seller_skus=["SKU-001", "SKU-002"])
        _, _, params = client._calls[-1]
        assert "SKU-001" in params["SellerSKUList"]

    def test_get_prep_instructions_by_asin(self, client):
        client.get_prep_instructions(asin_list=["B001", "B002"])
        _, _, params = client._calls[-1]
        assert "B001" in params["ASINList"]


# ── Transport ─────────────────────────────────────────────

class TestTransport:
    def test_put_transport_details(self, client):
        transport = {"CarrierName": "UPS", "TrackingId": "1Z999"}
        client.put_transport_details("SHP-001", True, "SP", transport)
        _, path, body = client._calls[-1]
        assert "transport" in path
        assert body["IsPartnered"] is True
        assert body["ShipmentType"] == "SP"

    def test_get_transport_details(self, client):
        result = client.get_transport_details("SHP-001")
        assert "transport" in result["path"]

    def test_estimate_transport(self, client):
        client.estimate_transport("SHP-001")
        method, path, _ = client._calls[-1]
        assert method == "POST"
        assert "estimate" in path

    def test_confirm_transport(self, client):
        client.confirm_transport("SHP-001")
        method, path, _ = client._calls[-1]
        assert method == "POST"
        assert "confirm" in path

    def test_void_transport(self, client):
        client.void_transport("SHP-001")
        method, path, _ = client._calls[-1]
        assert method == "POST"
        assert "void" in path


# ── Box Content ───────────────────────────────────────────

class TestBoxContent:
    def test_get_box_content(self, client):
        result = client.get_box_content("SHP-001")
        assert "boxContent" in result["path"]

    def test_put_box_content(self, client):
        boxes = [{"BoxNumber": 1, "Items": [{"SKU": "SKU-001", "Qty": 5}]}]
        client.put_box_content("SHP-001", boxes)
        method, _, body = client._calls[-1]
        assert method == "PUT"
        assert body["Boxes"] == boxes


# ── Convenience ───────────────────────────────────────────

class TestConvenience:
    def test_get_active_shipments(self, client):
        client.get_active_shipments()
        _, _, params = client._calls[-1]
        assert "WORKING" in params["ShipmentStatusList"]
        assert "SHIPPED" in params["ShipmentStatusList"]

    def test_mark_shipped(self, client):
        client.mark_shipped("SHP-001")
        _, _, body = client._calls[-1]
        assert body["InboundShipmentHeader"]["ShipmentStatus"] == "SHIPPED"

    def test_cancel_shipment(self, client):
        client.cancel_shipment("SHP-001")
        _, _, body = client._calls[-1]
        assert body["InboundShipmentHeader"]["ShipmentStatus"] == "CANCELLED"

    def test_quick_ship(self, client, ship_from):
        # Mock plan creation response
        original_post = client.post
        call_count = [0]

        def mock_post(path, body=None, params=None):
            call_count[0] += 1
            if "plans" in path:
                return {
                    "payload": {
                        "InboundShipmentPlans": [
                            {
                                "ShipmentId": "SHP-AUTO-001",
                                "DestinationFulfillmentCenterId": "PHX7",
                                "Items": [
                                    {"SellerSKU": "SKU-001", "Quantity": 10}
                                ],
                            }
                        ]
                    }
                }
            client._calls.append(("POST", path, body))
            return {"mock": True}

        client.post = mock_post

        result = client.quick_ship({"SKU-001": 10}, ship_from)
        assert len(result) == 1
        assert result[0]["shipment_id"] == "SHP-AUTO-001"
        assert result[0]["fc"] == "PHX7"
