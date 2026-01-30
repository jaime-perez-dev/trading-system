#!/usr/bin/env python3
"""
Exit Tracker - Monitors positions for exit targets and stop-losses

Features:
- Define take-profit and stop-loss levels per position
- Real-time P&L tracking with unrealized gains
- Alerts when exit targets are hit
- Automatic exit suggestions based on conditions
"""

import sys
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, List, Dict, Any

sys.path.insert(0, str(Path(__file__).parent.parent))

from polymarket.client import PolymarketClient
from alerts.telegram_notifier import TelegramNotifier


class ExitTracker:
    """
    Advanced position tracking with exit targets.
    """
    
    def __init__(self, notify: bool = True):
        self.polymarket = PolymarketClient()
        self.notifier = TelegramNotifier() if notify else None
        self.data_dir = Path(__file__).parent.parent / "data"
        self.targets_file = self.data_dir / "exit_targets.json"
        self.trades_file = self.data_dir / "paper_trades.json"
    
    def load_positions(self) -> List[Dict]:
        """Load open positions from paper trades."""
        if not self.trades_file.exists():
            return []
        with open(self.trades_file, "r") as f:
            trades = json.load(f)
        return [t for t in trades if t.get("status") == "OPEN"]
    
    def load_targets(self) -> Dict[str, Dict]:
        """Load exit targets for positions."""
        if not self.targets_file.exists():
            return {}
        with open(self.targets_file, "r") as f:
            return json.load(f)
    
    def save_targets(self, targets: Dict):
        """Save exit targets."""
        with open(self.targets_file, "w") as f:
            json.dump(targets, f, indent=2)
    
    def set_exit_target(self, 
                        position_id: int,
                        take_profit: Optional[float] = None,
                        stop_loss: Optional[float] = None,
                        trailing_stop: Optional[float] = None):
        """
        Set exit targets for a position.
        
        Args:
            position_id: Trade ID
            take_profit: Price to take profit (e.g., 98.0 for 98%)
            stop_loss: Price to stop loss (e.g., 90.0 for 90%)
            trailing_stop: Trailing stop distance in pp (e.g., 5.0 for 5pp below peak)
        """
        targets = self.load_targets()
        
        targets[str(position_id)] = {
            "take_profit": take_profit,
            "stop_loss": stop_loss,
            "trailing_stop": trailing_stop,
            "peak_price": None,  # For trailing stops
            "set_at": datetime.now(timezone.utc).isoformat()
        }
        
        self.save_targets(targets)
        print(f"✅ Exit targets set for position #{position_id}")
        if take_profit:
            print(f"   Take profit: {take_profit:.1f}%")
        if stop_loss:
            print(f"   Stop loss: {stop_loss:.1f}%")
        if trailing_stop:
            print(f"   Trailing stop: {trailing_stop:.1f}pp")
    
    def get_current_price(self, market_slug: str) -> Optional[float]:
        """Fetch current price for a market."""
        try:
            import requests
            url = f"https://gamma-api.polymarket.com/markets?slug={market_slug}"
            response = requests.get(url, timeout=10)
            if response.ok:
                data = response.json()
                if data and len(data) > 0:
                    prices = data[0].get("outcomePrices", "[]")
                    if isinstance(prices, str):
                        prices = json.loads(prices)
                    if prices:
                        return float(prices[0]) * 100
        except Exception as e:
            print(f"Error fetching price: {e}")
        return None
    
    def check_exits(self) -> List[Dict]:
        """
        Check all positions against their exit targets.
        Returns list of triggered exits.
        """
        positions = self.load_positions()
        targets = self.load_targets()
        
        if not positions:
            print("No open positions to track.")
            return []
        
        triggered = []
        updated_targets = targets.copy()
        
        print(f"🎯 Checking exit targets for {len(positions)} position(s)...\n")
        
        for pos in positions:
            pos_id = str(pos.get("id"))
            slug = pos.get("market_slug")
            question = pos.get("question", slug)
            entry = pos.get("entry_price", 0)
            amount = pos.get("amount", 0)
            shares = pos.get("shares", 0)
            outcome = pos.get("outcome", "Yes")
            
            current = self.get_current_price(slug)
            if current is None:
                print(f"⚠️ Could not fetch: {question[:40]}...")
                continue
            
            # Calculate P&L
            if outcome == "Yes":
                pnl = (current - entry) * shares / 100
            else:
                pnl = (entry - current) * shares / 100
            
            pnl_pct = (pnl / amount) * 100 if amount > 0 else 0
            
            print(f"📊 #{pos_id}: {question[:40]}...")
            print(f"   Entry: {entry:.1f}% → Current: {current:.1f}%")
            print(f"   P&L: ${pnl:+.2f} ({pnl_pct:+.1f}%)")
            
            # Check targets if they exist
            if pos_id in targets:
                target = targets[pos_id]
                tp = target.get("take_profit")
                sl = target.get("stop_loss")
                ts = target.get("trailing_stop")
                peak = target.get("peak_price")
                
                # Update peak for trailing stop
                if ts is not None:
                    if peak is None or current > peak:
                        updated_targets[pos_id]["peak_price"] = current
                        peak = current
                    
                    # Calculate trailing stop level
                    ts_level = peak - ts
                    print(f"   Trailing stop: {ts_level:.1f}% (peak: {peak:.1f}%)")
                    
                    if current <= ts_level:
                        print(f"   🚨 TRAILING STOP HIT!")
                        self._send_exit_alert(pos, current, "trailing_stop", ts_level)
                        triggered.append({
                            "position_id": pos_id,
                            "type": "trailing_stop",
                            "trigger_price": ts_level,
                            "current_price": current,
                            "pnl": pnl
                        })
                
                # Check take profit
                if tp is not None:
                    print(f"   Take profit target: {tp:.1f}%")
                    if current >= tp:
                        print(f"   🎉 TAKE PROFIT HIT!")
                        self._send_exit_alert(pos, current, "take_profit", tp)
                        triggered.append({
                            "position_id": pos_id,
                            "type": "take_profit",
                            "trigger_price": tp,
                            "current_price": current,
                            "pnl": pnl
                        })
                
                # Check stop loss
                if sl is not None:
                    print(f"   Stop loss: {sl:.1f}%")
                    if current <= sl:
                        print(f"   🛑 STOP LOSS HIT!")
                        self._send_exit_alert(pos, current, "stop_loss", sl)
                        triggered.append({
                            "position_id": pos_id,
                            "type": "stop_loss",
                            "trigger_price": sl,
                            "current_price": current,
                            "pnl": pnl
                        })
            else:
                print(f"   (No exit targets set)")
            
            print()
        
        # Save updated targets (for trailing stop peaks)
        self.save_targets(updated_targets)
        
        return triggered
    
    def _send_exit_alert(self, position: Dict, current: float, exit_type: str, target: float):
        """Send Telegram alert for exit trigger."""
        if not self.notifier:
            return
        
        emoji = {
            "take_profit": "🎉",
            "stop_loss": "🛑",
            "trailing_stop": "📉"
        }.get(exit_type, "🔔")
        
        label = {
            "take_profit": "TAKE PROFIT",
            "stop_loss": "STOP LOSS",
            "trailing_stop": "TRAILING STOP"
        }.get(exit_type, "EXIT")
        
        message = f"""{emoji} **{label} TRIGGERED**

**Market:** {position.get('question', 'Unknown')[:50]}
**Position:** #{position.get('id')} ({position.get('outcome')})
**Entry:** {position.get('entry_price', 0):.1f}%
**Target:** {target:.1f}%
**Current:** {current:.1f}%
**Amount:** ${position.get('amount', 0):.0f}

Consider closing this position."""
        
        self.notifier.send_message(message)
    
    def portfolio_summary(self) -> Dict:
        """Get full portfolio summary with real-time P&L."""
        positions = self.load_positions()
        
        summary = {
            "positions": [],
            "total_invested": 0,
            "total_unrealized_pnl": 0,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        for pos in positions:
            slug = pos.get("market_slug")
            entry = pos.get("entry_price", 0)
            amount = pos.get("amount", 0)
            shares = pos.get("shares", 0)
            outcome = pos.get("outcome", "Yes")
            
            current = self.get_current_price(slug) or entry
            
            if outcome == "Yes":
                pnl = (current - entry) * shares / 100
            else:
                pnl = (entry - current) * shares / 100
            
            summary["positions"].append({
                "id": pos.get("id"),
                "market": pos.get("question"),
                "outcome": outcome,
                "entry": entry,
                "current": current,
                "amount": amount,
                "pnl": pnl,
                "pnl_pct": (pnl / amount * 100) if amount > 0 else 0
            })
            
            summary["total_invested"] += amount
            summary["total_unrealized_pnl"] += pnl
        
        return summary


def main():
    """Run exit tracker from command line."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Exit Tracker for positions")
    parser.add_argument("--check", action="store_true", help="Check all exit targets")
    parser.add_argument("--summary", action="store_true", help="Show portfolio summary")
    parser.add_argument("--set", type=int, help="Set target for position ID")
    parser.add_argument("--tp", type=float, help="Take profit price")
    parser.add_argument("--sl", type=float, help="Stop loss price")
    parser.add_argument("--ts", type=float, help="Trailing stop distance (pp)")
    parser.add_argument("--no-notify", action="store_true", help="Disable notifications")
    
    args = parser.parse_args()
    
    tracker = ExitTracker(notify=not args.no_notify)
    
    if args.set:
        tracker.set_exit_target(args.set, args.tp, args.sl, args.ts)
    elif args.summary:
        summary = tracker.portfolio_summary()
        print("\n📈 Portfolio Summary")
        print("=" * 50)
        for p in summary["positions"]:
            print(f"\n#{p['id']}: {p['market'][:40]}...")
            print(f"   {p['outcome']} @ {p['entry']:.1f}% → {p['current']:.1f}%")
            print(f"   Amount: ${p['amount']:.0f} | P&L: ${p['pnl']:+.2f} ({p['pnl_pct']:+.1f}%)")
        
        print("\n" + "=" * 50)
        print(f"Total Invested: ${summary['total_invested']:.0f}")
        print(f"Unrealized P&L: ${summary['total_unrealized_pnl']:+.2f}")
    else:
        # Default: check exits
        triggered = tracker.check_exits()
        if triggered:
            print(f"\n⚠️ {len(triggered)} exit(s) triggered!")
        else:
            print("\n✅ No exits triggered.")


if __name__ == "__main__":
    main()
