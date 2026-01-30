#!/usr/bin/env python3
"""
Position Monitor - Tracks open positions and alerts on significant price movements
"""

import sys
import json
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from polymarket.client import PolymarketClient
from alerts.telegram_notifier import TelegramNotifier


class PositionMonitor:
    """
    Monitors open paper trading positions for price movements.
    Sends alerts when prices move significantly.
    """
    
    def __init__(self, alert_threshold: float = 5.0, notify: bool = True):
        """
        Args:
            alert_threshold: Percentage point change to trigger alert (default 5pp)
            notify: Whether to send Telegram notifications
        """
        self.threshold = alert_threshold
        self.polymarket = PolymarketClient()
        self.notifier = TelegramNotifier() if notify else None
        self.data_dir = Path(__file__).parent.parent / "data"
        self.state_file = self.data_dir / "position_prices.json"
    
    def load_positions(self) -> list:
        """Load open positions from paper trades."""
        trades_file = self.data_dir / "paper_trades.json"
        if not trades_file.exists():
            return []
        
        with open(trades_file, "r") as f:
            trades = json.load(f)
        
        return [t for t in trades if t.get("status") == "OPEN"]
    
    def load_last_prices(self) -> dict:
        """Load last known prices for positions."""
        if not self.state_file.exists():
            return {}
        with open(self.state_file, "r") as f:
            return json.load(f)
    
    def save_prices(self, prices: dict):
        """Save current prices for next comparison."""
        with open(self.state_file, "w") as f:
            json.dump(prices, f, indent=2)
    
    def get_current_price(self, market_slug: str) -> float | None:
        """Fetch current price for a market by slug."""
        try:
            # Use direct API call with slug parameter
            import requests
            url = f"https://gamma-api.polymarket.com/markets?slug={market_slug}"
            response = requests.get(url, timeout=10)
            if response.ok:
                data = response.json()
                if data and len(data) > 0:
                    market = data[0]
                    prices = market.get("outcomePrices", "[]")
                    if isinstance(prices, str):
                        prices = json.loads(prices)
                    if prices:
                        return float(prices[0]) * 100  # Convert to percentage
        except Exception as e:
            print(f"Error fetching price for {market_slug}: {e}")
        return None
    
    def check_positions(self) -> list:
        """
        Check all open positions for significant price movements.
        Returns list of alerts triggered.
        """
        positions = self.load_positions()
        if not positions:
            print("No open positions to monitor.")
            return []
        
        last_prices = self.load_last_prices()
        current_prices = {}
        alerts = []
        
        print(f"Checking {len(positions)} open position(s)...\n")
        
        for pos in positions:
            slug = pos.get("market_slug")
            question = pos.get("question", slug)
            entry_price = pos.get("entry_price", 0)
            
            current = self.get_current_price(slug)
            if current is None:
                print(f"⚠️ Could not fetch price for: {question[:50]}")
                continue
            
            current_prices[slug] = current
            last = last_prices.get(slug, entry_price)
            change = current - last
            
            print(f"📊 {question[:50]}...")
            print(f"   Entry: {entry_price:.2f}% | Last: {last:.2f}% | Now: {current:.2f}%")
            print(f"   Change: {change:+.2f}pp")
            
            # Check if threshold exceeded
            if abs(change) >= self.threshold:
                direction = "up" if change > 0 else "down"
                alert = {
                    "market": question,
                    "slug": slug,
                    "entry": entry_price,
                    "last": last,
                    "current": current,
                    "change": change,
                    "direction": direction
                }
                alerts.append(alert)
                
                print(f"   🚨 ALERT: Price moved {change:+.2f}pp!")
                
                if self.notifier:
                    self.notifier.alert_price_move(
                        market=question,
                        old_price=last,
                        new_price=current,
                        direction=direction
                    )
                    print(f"   📱 Telegram alert sent!")
            print()
        
        # Save current prices for next run
        self.save_prices(current_prices)
        
        return alerts
    
    def summary(self) -> dict:
        """Get portfolio summary with current prices."""
        positions = self.load_positions()
        
        total_invested = 0
        total_unrealized = 0
        position_data = []
        
        for pos in positions:
            slug = pos.get("market_slug")
            entry = pos.get("entry_price", 0)
            amount = pos.get("amount", 0)
            shares = pos.get("shares", 0)
            
            current = self.get_current_price(slug) or entry
            pnl = (current - entry) * shares / 100
            
            total_invested += amount
            total_unrealized += pnl
            
            position_data.append({
                "question": pos.get("question"),
                "entry": entry,
                "current": current,
                "amount": amount,
                "pnl": pnl
            })
        
        return {
            "positions": position_data,
            "total_invested": total_invested,
            "unrealized_pnl": total_unrealized,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Monitor open positions")
    parser.add_argument("--threshold", "-t", type=float, default=5.0,
                       help="Alert threshold in percentage points (default: 5)")
    parser.add_argument("--no-notify", action="store_true",
                       help="Disable Telegram notifications")
    parser.add_argument("--summary", "-s", action="store_true",
                       help="Just show portfolio summary")
    args = parser.parse_args()
    
    monitor = PositionMonitor(
        alert_threshold=args.threshold,
        notify=not args.no_notify
    )
    
    if args.summary:
        summary = monitor.summary()
        print("\n📊 PORTFOLIO SUMMARY")
        print("=" * 50)
        for p in summary["positions"]:
            emoji = "🟢" if p["pnl"] >= 0 else "🔴"
            print(f"{emoji} {p['question'][:40]}...")
            print(f"   Entry: {p['entry']:.2f}% → Now: {p['current']:.2f}%")
            print(f"   P&L: ${p['pnl']:+.2f}")
        print("-" * 50)
        print(f"Total Invested: ${summary['total_invested']:.2f}")
        print(f"Unrealized P&L: ${summary['unrealized_pnl']:+.2f}")
    else:
        alerts = monitor.check_positions()
        print(f"\n{'=' * 50}")
        print(f"Alerts triggered: {len(alerts)}")
        print(f"{'=' * 50}")


if __name__ == "__main__":
    main()
