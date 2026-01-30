#!/usr/bin/env python3
"""
Edge Validation Tracker
Tracks news events and corresponding market movements to validate the lag hypothesis.
"""
import json
import os
from datetime import datetime, timedelta
from pathlib import Path

DATA_DIR = Path("/home/rafa/clawd/trading-system/data")
DATA_DIR.mkdir(parents=True, exist_ok=True)

EDGE_LOG = DATA_DIR / "edge_events.json"

def load_events():
    if EDGE_LOG.exists():
        with open(EDGE_LOG) as f:
            return json.load(f)
    return {"events": [], "stats": {}}

def save_events(data):
    with open(EDGE_LOG, 'w') as f:
        json.dump(data, f, indent=2)

def log_news_event(headline: str, source: str, market_slug: str = None):
    """Log a news event when detected."""
    data = load_events()
    event = {
        "id": len(data["events"]) + 1,
        "type": "news",
        "headline": headline,
        "source": source,
        "market_slug": market_slug,
        "news_time": datetime.now().isoformat(),
        "market_price_at_news": None,  # Fill in manually or via API
        "market_price_1h_later": None,
        "market_price_24h_later": None,
        "final_resolution": None,  # "yes" or "no"
        "notes": ""
    }
    data["events"].append(event)
    save_events(data)
    print(f"Logged event #{event['id']}: {headline[:50]}...")
    return event["id"]

def update_event(event_id: int, **kwargs):
    """Update an event with new data."""
    data = load_events()
    for event in data["events"]:
        if event["id"] == event_id:
            event.update(kwargs)
            save_events(data)
            print(f"Updated event #{event_id}")
            return
    print(f"Event #{event_id} not found")

def calculate_stats():
    """Calculate edge statistics."""
    data = load_events()
    events = data["events"]
    
    if not events:
        print("No events logged yet")
        return
    
    total = len(events)
    with_prices = [e for e in events if e.get("market_price_at_news") and e.get("market_price_1h_later")]
    resolved = [e for e in events if e.get("final_resolution")]
    
    print(f"\n=== Edge Tracking Stats ===")
    print(f"Total events: {total}")
    print(f"With price data: {len(with_prices)}")
    print(f"Resolved: {len(resolved)}")
    
    if with_prices:
        # Calculate average price movement
        movements = []
        for e in with_prices:
            p0 = float(e["market_price_at_news"])
            p1 = float(e["market_price_1h_later"])
            if p0 > 0:
                movements.append((p1 - p0) / p0 * 100)
        
        if movements:
            avg_move = sum(movements) / len(movements)
            print(f"Avg 1h price move: {avg_move:+.1f}%")
    
    if resolved:
        # Calculate win rate
        wins = len([e for e in resolved if e.get("trade_result") == "win"])
        print(f"Win rate: {wins}/{len(resolved)} ({wins/len(resolved)*100:.0f}%)")

def show_events(n: int = 10):
    """Show recent events."""
    data = load_events()
    events = data["events"][-n:]
    
    print(f"\n=== Recent {len(events)} Events ===\n")
    for e in events:
        status = "✓" if e.get("final_resolution") else "⏳"
        print(f"{status} #{e['id']}: {e['headline'][:60]}")
        print(f"   Time: {e['news_time']}")
        if e.get("market_price_at_news"):
            print(f"   Price @ news: {e['market_price_at_news']}%")
        if e.get("market_price_1h_later"):
            print(f"   Price @ +1h: {e['market_price_1h_later']}%")
        print()

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage:")
        print("  edge_tracker.py log <headline> <source> [market_slug]")
        print("  edge_tracker.py update <id> <field>=<value>")
        print("  edge_tracker.py show [n]")
        print("  edge_tracker.py stats")
        sys.exit(0)
    
    cmd = sys.argv[1]
    
    if cmd == "log":
        headline = sys.argv[2] if len(sys.argv) > 2 else "Unknown"
        source = sys.argv[3] if len(sys.argv) > 3 else "Unknown"
        slug = sys.argv[4] if len(sys.argv) > 4 else None
        log_news_event(headline, source, slug)
    
    elif cmd == "update":
        event_id = int(sys.argv[2])
        updates = {}
        for arg in sys.argv[3:]:
            k, v = arg.split("=", 1)
            updates[k] = v
        update_event(event_id, **updates)
    
    elif cmd == "show":
        n = int(sys.argv[2]) if len(sys.argv) > 2 else 10
        show_events(n)
    
    elif cmd == "stats":
        calculate_stats()
