"""
ASIN Monitor - Track price, inventory, and rating changes for multiple ASINs
"""
import time
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Set
from dataclasses import dataclass, asdict
import json
from pathlib import Path

from .client import SPAPIClient
from .exceptions import SPAPIError


@dataclass
class ASINSnapshot:
    """Single ASIN snapshot at a point in time"""
    asin: str
    timestamp: str
    price: Optional[float]
    currency: str
    availability: str
    rating: Optional[float]
    review_count: Optional[int]
    buybox_winner: Optional[str]
    
    def to_dict(self):
        return asdict(self)


class ASINMonitor:
    """Monitor multiple ASINs for price/inventory/rating changes"""
    
    def __init__(self, client: SPAPIClient, storage_path: Optional[str] = None):
        self.client = client
        self.storage_path = Path(storage_path or "./asin_monitor_data")
        self.storage_path.mkdir(exist_ok=True)
        
    def capture_snapshot(self, asins: List[str]) -> List[ASINSnapshot]:
        """Capture current state of multiple ASINs"""
        snapshots = []
        
        # Batch pricing
        pricing_data = self.client.get_competitive_pricing(asins)
        
        # Batch catalog data
        catalog_data = {}
        for asin in asins:
            try:
                item = self.client.get_catalog_item(asin)
                catalog_data[asin] = item
            except SPAPIError:
                catalog_data[asin] = None
                
        timestamp = datetime.utcnow().isoformat()
        
        for asin in asins:
            pricing = pricing_data.get(asin, {})
            catalog = catalog_data.get(asin, {})
            
            # Extract price
            price = None
            currency = "USD"
            if pricing and "Product" in pricing:
                competitive_pricing = pricing["Product"].get("CompetitivePricing", {})
                price_list = competitive_pricing.get("CompetitivePrices", [])
                if price_list:
                    landed_price = price_list[0].get("Price", {}).get("LandedPrice", {})
                    price = float(landed_price.get("Amount", 0))
                    currency = landed_price.get("CurrencyCode", "USD")
            
            # Extract availability
            availability = "unknown"
            if pricing and "Product" in pricing:
                offers = pricing["Product"].get("Offers", [])
                if offers:
                    availability = offers[0].get("IsFulfilledByAmazon", False) and "FBA" or "FBM"
            
            # Extract rating/reviews
            rating = None
            review_count = None
            if catalog and "summaries" in catalog:
                summaries = catalog["summaries"]
                if summaries:
                    rating = summaries[0].get("customerReviewsRating")
                    review_count = summaries[0].get("customerReviewsCount")
            
            # Buybox winner
            buybox_winner = None
            if pricing and "Product" in pricing:
                offers = pricing["Product"].get("Offers", [])
                if offers and offers[0].get("IsBuyBoxWinner"):
                    buybox_winner = offers[0].get("SellerId")
            
            snapshot = ASINSnapshot(
                asin=asin,
                timestamp=timestamp,
                price=price,
                currency=currency,
                availability=availability,
                rating=rating,
                review_count=review_count,
                buybox_winner=buybox_winner
            )
            snapshots.append(snapshot)
        
        return snapshots
    
    def save_snapshots(self, snapshots: List[ASINSnapshot]):
        """Save snapshots to JSONL file"""
        date_str = datetime.utcnow().strftime("%Y-%m-%d")
        file_path = self.storage_path / f"snapshots_{date_str}.jsonl"
        
        with open(file_path, "a") as f:
            for snapshot in snapshots:
                f.write(json.dumps(snapshot.to_dict()) + "\n")
    
    def load_snapshots(self, asin: str, days: int = 7) -> List[ASINSnapshot]:
        """Load historical snapshots for an ASIN"""
        snapshots = []
        start_date = datetime.utcnow() - timedelta(days=days)
        
        for day_offset in range(days + 1):
            date = start_date + timedelta(days=day_offset)
            date_str = date.strftime("%Y-%m-%d")
            file_path = self.storage_path / f"snapshots_{date_str}.jsonl"
            
            if not file_path.exists():
                continue
                
            with open(file_path) as f:
                for line in f:
                    data = json.loads(line)
                    if data["asin"] == asin:
                        snapshots.append(ASINSnapshot(**data))
        
        return sorted(snapshots, key=lambda s: s.timestamp)
    
    def detect_changes(self, asin: str, threshold_pct: float = 5.0) -> Dict:
        """Detect significant changes in last 24h"""
        snapshots = self.load_snapshots(asin, days=1)
        
        if len(snapshots) < 2:
            return {"asin": asin, "changes": []}
        
        latest = snapshots[-1]
        previous = snapshots[-2]
        changes = []
        
        # Price change
        if latest.price and previous.price:
            pct_change = ((latest.price - previous.price) / previous.price) * 100
            if abs(pct_change) >= threshold_pct:
                changes.append({
                    "type": "price",
                    "from": previous.price,
                    "to": latest.price,
                    "change_pct": round(pct_change, 2)
                })
        
        # Availability change
        if latest.availability != previous.availability:
            changes.append({
                "type": "availability",
                "from": previous.availability,
                "to": latest.availability
            })
        
        # Rating change
        if latest.rating and previous.rating:
            rating_diff = latest.rating - previous.rating
            if abs(rating_diff) >= 0.1:
                changes.append({
                    "type": "rating",
                    "from": previous.rating,
                    "to": latest.rating,
                    "change": round(rating_diff, 2)
                })
        
        # Buybox change
        if latest.buybox_winner != previous.buybox_winner:
            changes.append({
                "type": "buybox",
                "from": previous.buybox_winner,
                "to": latest.buybox_winner
            })
        
        return {
            "asin": asin,
            "timestamp": latest.timestamp,
            "changes": changes
        }
    
    def monitor_loop(self, asins: List[str], interval_minutes: int = 60, duration_hours: Optional[int] = None):
        """Run continuous monitoring loop"""
        start_time = time.time()
        iteration = 0
        
        while True:
            iteration += 1
            print(f"[{datetime.utcnow().isoformat()}] Monitoring iteration {iteration}")
            
            try:
                snapshots = self.capture_snapshot(asins)
                self.save_snapshots(snapshots)
                print(f"  Captured {len(snapshots)} snapshots")
                
                # Detect changes
                for asin in asins:
                    changes = self.detect_changes(asin)
                    if changes["changes"]:
                        print(f"  ⚠️  {asin}: {len(changes['changes'])} changes detected")
                        for change in changes["changes"]:
                            print(f"      {change}")
            
            except Exception as e:
                print(f"  ❌ Error: {e}")
            
            # Check duration limit
            if duration_hours:
                elapsed_hours = (time.time() - start_time) / 3600
                if elapsed_hours >= duration_hours:
                    print(f"Duration limit reached ({duration_hours}h)")
                    break
            
            # Sleep
            print(f"  Sleeping {interval_minutes} minutes...")
            time.sleep(interval_minutes * 60)
