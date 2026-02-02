#!/usr/bin/env python3
"""
Market Watchlist

Track markets you're interested in before entering positions.
Get alerts when prices move significantly or when conditions are favorable.

Usage:
    # Add market to watchlist
    python market_watchlist.py add <slug> [--target 0.30] [--note "Waiting for news"]
    
    # Remove from watchlist
    python market_watchlist.py remove <slug>
    
    # Check all watched markets
    python market_watchlist.py check [--notify]
    
    # List watchlist
    python market_watchlist.py list
    
    # Clear watchlist
    python market_watchlist.py clear
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict

# Add parent dir for imports
sys.path.insert(0, str(Path(__file__).parent))

from polymarket.client import PolymarketClient

DATA_DIR = Path(__file__).parent / "data"
WATCHLIST_FILE = DATA_DIR / "watchlist.json"


@dataclass
class WatchedMarket:
    """A market being watched"""
    slug: str
    question: str
    added_at: str
    target_price: Optional[float] = None  # Alert when price crosses this
    alert_on_move: float = 0.05  # Alert on 5% move by default
    last_price: Optional[float] = None
    last_check: Optional[str] = None
    note: Optional[str] = None
    alerts_triggered: int = 0


def load_watchlist() -> Dict[str, Dict]:
    """Load watchlist from file"""
    if not WATCHLIST_FILE.exists():
        return {}
    try:
        with open(WATCHLIST_FILE) as f:
            return json.load(f)
    except:
        return {}


def save_watchlist(watchlist: Dict[str, Dict]):
    """Save watchlist to file"""
    DATA_DIR.mkdir(exist_ok=True)
    with open(WATCHLIST_FILE, "w") as f:
        json.dump(watchlist, f, indent=2)


def add_market(slug: str, target: Optional[float] = None, note: Optional[str] = None, 
               alert_on_move: float = 0.05) -> WatchedMarket:
    """Add a market to the watchlist"""
    client = PolymarketClient()
    
    # Get current market info
    market = client.get_market_by_slug(slug)
    if not market:
        raise ValueError(f"Market not found: {slug}")
    
    question = market.get("question", slug)
    
    # Parse current price
    current_price = None
    try:
        outcomes = market.get("outcomePrices", "[]")
        if isinstance(outcomes, str):
            outcomes = json.loads(outcomes)
        if outcomes and len(outcomes) > 0:
            current_price = float(outcomes[0])
    except:
        pass
    
    watched = WatchedMarket(
        slug=slug,
        question=question,
        added_at=datetime.now(timezone.utc).isoformat(),
        target_price=target,
        alert_on_move=alert_on_move,
        last_price=current_price,
        last_check=datetime.now(timezone.utc).isoformat(),
        note=note
    )
    
    watchlist = load_watchlist()
    watchlist[slug] = asdict(watched)
    save_watchlist(watchlist)
    
    print(f"✅ Added to watchlist: {question[:60]}")
    print(f"   Current price: {current_price:.1%}" if current_price else "   Price: Unknown")
    if target:
        print(f"   Target alert: {target:.1%}")
    if note:
        print(f"   Note: {note}")
    
    return watched


def remove_market(slug: str) -> bool:
    """Remove a market from the watchlist"""
    watchlist = load_watchlist()
    if slug not in watchlist:
        print(f"❌ Market not in watchlist: {slug}")
        return False
    
    question = watchlist[slug].get("question", slug)
    del watchlist[slug]
    save_watchlist(watchlist)
    print(f"✅ Removed from watchlist: {question[:60]}")
    return True


def check_watchlist(notify: bool = False) -> List[Dict]:
    """Check all watched markets for price changes"""
    watchlist = load_watchlist()
    if not watchlist:
        print("📋 Watchlist is empty")
        return []
    
    client = PolymarketClient()
    alerts = []
    
    # Set up notifier if requested
    notifier = None
    if notify:
        try:
            from alerts.telegram_notifier import TelegramNotifier
            notifier = TelegramNotifier()
        except Exception as e:
            print(f"⚠️  Notifications disabled: {e}")
    
    print(f"🔍 Checking {len(watchlist)} watched markets...\n")
    
    for slug, data in watchlist.items():
        try:
            market = client.get_market_by_slug(slug)
            if not market:
                print(f"⚠️  Market not found: {slug}")
                continue
            
            # Get current price
            current_price = None
            try:
                outcomes = market.get("outcomePrices", "[]")
                if isinstance(outcomes, str):
                    outcomes = json.loads(outcomes)
                if outcomes and len(outcomes) > 0:
                    current_price = float(outcomes[0])
            except:
                pass
            
            last_price = data.get("last_price")
            target = data.get("target_price")
            alert_threshold = data.get("alert_on_move", 0.05)
            question = data.get("question", slug)[:50]
            
            # Calculate move
            price_change = None
            alert_reason = None
            
            if current_price and last_price:
                price_change = current_price - last_price
                change_pct = abs(price_change / last_price) if last_price > 0 else 0
                
                # Check for significant move
                if change_pct >= alert_threshold:
                    direction = "📈" if price_change > 0 else "📉"
                    alert_reason = f"{direction} Moved {price_change:+.1%} (was {last_price:.1%})"
                    alerts.append({
                        "slug": slug,
                        "question": question,
                        "reason": alert_reason,
                        "old_price": last_price,
                        "new_price": current_price,
                        "change": price_change
                    })
            
            # Check target price
            if current_price and target:
                if (last_price and last_price < target <= current_price) or \
                   (last_price and last_price > target >= current_price):
                    alert_reason = f"🎯 Hit target {target:.1%} (now {current_price:.1%})"
                    alerts.append({
                        "slug": slug,
                        "question": question,
                        "reason": alert_reason,
                        "target": target,
                        "new_price": current_price
                    })
            
            # Print status
            price_str = f"{current_price:.1%}" if current_price else "?"
            change_str = ""
            if price_change:
                direction = "↑" if price_change > 0 else "↓"
                change_str = f" ({direction}{abs(price_change):.1%})"
            
            status = "📋"
            if alert_reason:
                status = "🚨"
            
            print(f"{status} {question}...")
            print(f"   Price: {price_str}{change_str}")
            if target:
                print(f"   Target: {target:.1%}")
            if data.get("note"):
                print(f"   Note: {data['note']}")
            print()
            
            # Update last check
            data["last_price"] = current_price
            data["last_check"] = datetime.now(timezone.utc).isoformat()
            if alert_reason:
                data["alerts_triggered"] = data.get("alerts_triggered", 0) + 1
            
        except Exception as e:
            print(f"⚠️  Error checking {slug}: {e}")
    
    # Save updated watchlist
    save_watchlist(watchlist)
    
    # Send notifications
    if alerts and notifier:
        for alert in alerts:
            msg = f"📊 Watchlist Alert\n\n{alert['question']}\n{alert['reason']}"
            notifier.send_alert(msg, "watchlist_alert")
    
    # Summary
    if alerts:
        print(f"\n🚨 {len(alerts)} alert(s) triggered!")
    else:
        print(f"✅ No alerts. All {len(watchlist)} markets stable.")
    
    return alerts


def list_watchlist() -> List[Dict]:
    """List all watched markets"""
    watchlist = load_watchlist()
    if not watchlist:
        print("📋 Watchlist is empty")
        print("   Use: python market_watchlist.py add <slug>")
        return []
    
    print(f"📋 Watchlist ({len(watchlist)} markets)\n")
    
    markets = []
    for slug, data in watchlist.items():
        question = data.get("question", slug)[:50]
        price = data.get("last_price")
        target = data.get("target_price")
        note = data.get("note")
        added = data.get("added_at", "")[:10]
        
        print(f"• {question}...")
        print(f"  Slug: {slug}")
        if price:
            print(f"  Last price: {price:.1%}")
        if target:
            print(f"  Target: {target:.1%}")
        if note:
            print(f"  Note: {note}")
        print(f"  Added: {added}")
        print()
        
        markets.append(data)
    
    return markets


def clear_watchlist() -> int:
    """Clear all watched markets"""
    watchlist = load_watchlist()
    count = len(watchlist)
    save_watchlist({})
    print(f"✅ Cleared {count} markets from watchlist")
    return count


def main():
    parser = argparse.ArgumentParser(description="Market Watchlist - Track markets before trading")
    subparsers = parser.add_subparsers(dest="command", required=True)
    
    # Add command
    add_parser = subparsers.add_parser("add", help="Add market to watchlist")
    add_parser.add_argument("slug", help="Market slug")
    add_parser.add_argument("--target", type=float, help="Alert when price crosses this (0.0-1.0)")
    add_parser.add_argument("--note", help="Note about why you're watching")
    add_parser.add_argument("--move", type=float, default=0.05, help="Alert on this % move (default: 0.05)")
    
    # Remove command
    remove_parser = subparsers.add_parser("remove", help="Remove market from watchlist")
    remove_parser.add_argument("slug", help="Market slug")
    
    # Check command
    check_parser = subparsers.add_parser("check", help="Check all watched markets")
    check_parser.add_argument("--notify", action="store_true", help="Send Telegram alerts")
    
    # List command
    subparsers.add_parser("list", help="List all watched markets")
    
    # Clear command
    subparsers.add_parser("clear", help="Clear watchlist")
    
    args = parser.parse_args()
    
    if args.command == "add":
        add_market(args.slug, target=args.target, note=args.note, alert_on_move=args.move)
    elif args.command == "remove":
        remove_market(args.slug)
    elif args.command == "check":
        check_watchlist(notify=args.notify)
    elif args.command == "list":
        list_watchlist()
    elif args.command == "clear":
        clear_watchlist()


if __name__ == "__main__":
    main()
