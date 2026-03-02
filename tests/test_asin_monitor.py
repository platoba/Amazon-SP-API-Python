"""
Tests for ASIN Monitor module
"""
import pytest
from datetime import datetime
from pathlib import Path
import tempfile
from unittest.mock import Mock

from sp_api.asin_monitor import ASINMonitor, ASINSnapshot
from sp_api.client import SPAPIClient


@pytest.fixture
def temp_storage():
    """Create temporary storage directory"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def mock_client():
    """Mock SP-API client"""
    client = Mock(spec=SPAPIClient)
    
    # Mock pricing response
    client.get_competitive_pricing.return_value = {
        "B08N5WRWNW": {
            "Product": {
                "CompetitivePricing": {
                    "CompetitivePrices": [{
                        "Price": {
                            "LandedPrice": {
                                "Amount": 29.99,
                                "CurrencyCode": "USD"
                            }
                        }
                    }]
                },
                "Offers": [{
                    "IsFulfilledByAmazon": True,
                    "IsBuyBoxWinner": True,
                    "SellerId": "SELLER123"
                }]
            }
        }
    }
    
    # Mock catalog response
    client.get_catalog_item.return_value = {
        "summaries": [{
            "customerReviewsRating": 4.5,
            "customerReviewsCount": 1234
        }]
    }
    
    return client


def test_capture_snapshot(mock_client, temp_storage):
    """Test capturing ASIN snapshots"""
    monitor = ASINMonitor(mock_client, storage_path=temp_storage)
    
    snapshots = monitor.capture_snapshot(["B08N5WRWNW"])
    
    assert len(snapshots) == 1
    snapshot = snapshots[0]
    assert snapshot.asin == "B08N5WRWNW"
    assert snapshot.price == 29.99
    assert snapshot.currency == "USD"
    assert snapshot.availability == "FBA"
    assert snapshot.rating == 4.5
    assert snapshot.review_count == 1234
    assert snapshot.buybox_winner == "SELLER123"


def test_save_and_load_snapshots(mock_client, temp_storage):
    """Test saving and loading snapshots"""
    monitor = ASINMonitor(mock_client, storage_path=temp_storage)
    
    # Capture and save
    snapshots = monitor.capture_snapshot(["B08N5WRWNW"])
    monitor.save_snapshots(snapshots)
    
    # Verify file exists
    date_str = datetime.utcnow().strftime("%Y-%m-%d")
    file_path = Path(temp_storage) / f"snapshots_{date_str}.jsonl"
    assert file_path.exists()
    
    # Load back
    loaded = monitor.load_snapshots("B08N5WRWNW", days=1)
    assert len(loaded) >= 1
    assert loaded[0].asin == "B08N5WRWNW"


def test_detect_price_change(mock_client, temp_storage):
    """Test price change detection"""
    monitor = ASINMonitor(mock_client, storage_path=temp_storage)
    
    # Create two snapshots with price change
    snapshot1 = ASINSnapshot(
        asin="B08N5WRWNW",
        timestamp=datetime.utcnow().isoformat(),
        price=29.99,
        currency="USD",
        availability="FBA",
        rating=4.5,
        review_count=1234,
        buybox_winner="SELLER123"
    )
    
    snapshot2 = ASINSnapshot(
        asin="B08N5WRWNW",
        timestamp=datetime.utcnow().isoformat(),
        price=24.99,  # 16.7% decrease
        currency="USD",
        availability="FBA",
        rating=4.5,
        review_count=1234,
        buybox_winner="SELLER123"
    )
    
    monitor.save_snapshots([snapshot1, snapshot2])
    
    # Detect changes
    changes = monitor.detect_changes("B08N5WRWNW", threshold_pct=5.0)
    
    assert len(changes["changes"]) == 1
    price_change = changes["changes"][0]
    assert price_change["type"] == "price"
    assert price_change["from"] == 29.99
    assert price_change["to"] == 24.99
    assert price_change["change_pct"] < 0  # Negative = price drop


def test_detect_availability_change(mock_client, temp_storage):
    """Test availability change detection"""
    monitor = ASINMonitor(mock_client, storage_path=temp_storage)
    
    snapshot1 = ASINSnapshot(
        asin="B08N5WRWNW",
        timestamp=datetime.utcnow().isoformat(),
        price=29.99,
        currency="USD",
        availability="FBA",
        rating=4.5,
        review_count=1234,
        buybox_winner="SELLER123"
    )
    
    snapshot2 = ASINSnapshot(
        asin="B08N5WRWNW",
        timestamp=datetime.utcnow().isoformat(),
        price=29.99,
        currency="USD",
        availability="FBM",  # Changed
        rating=4.5,
        review_count=1234,
        buybox_winner="SELLER123"
    )
    
    monitor.save_snapshots([snapshot1, snapshot2])
    changes = monitor.detect_changes("B08N5WRWNW")
    
    availability_changes = [c for c in changes["changes"] if c["type"] == "availability"]
    assert len(availability_changes) == 1
    assert availability_changes[0]["from"] == "FBA"
    assert availability_changes[0]["to"] == "FBM"
