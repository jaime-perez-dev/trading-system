#!/usr/bin/env python3
"""
Automated News + Market Monitor
Runs periodically to detect news and track market movements.
"""
import json
import os
import sys
from datetime import datetime
from pathlib import Path

# Add parent dir for imports
sys.path.insert(0, str(Path(__file__).parent))

from polymarket.client import PolymarketClient
from edge_tracker import log_news_event, update_event, load_events

DATA_DIR = Path("/home/rafa/clawd/trading-system/data")
TAVILY_KEY = "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"

# Keywords that indicate tradeable AI news
AI_KEYWORDS = [
    "openai", "chatgpt", "gpt-5", "gpt-4", "claude", "anthropic",
    "google ai", "gemini", "deepmind", "meta ai", "llama",
    "ai regulation", "ai safety", "agi"
]

# Markets we're tracking
TRACKED_MARKETS = {
    "gpt-ads-by-january-31-329-775": "GPT ads by Jan 31",
    "gpt-ads-by-march-31-269-364-978": "GPT ads by Mar 31",
}

def search_news():
    """Search for recent AI news."""
    import subprocess
    
    query = "OpenAI OR ChatGPT OR Anthropic Claude announcement release"
    cmd = f'''curl -s -X POST "https://api.tavily.com/search" \
      -H "Content-Type: application/json" \
      -d '{{"api_key": "{TAVILY_KEY}", "query": "{query}", "max_results": 5, "search_depth": "basic"}}' '''
    
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    
    try:
        data = json.loads(result.stdout)
        return data.get("results", [])
    except:
        return []

def get_market_prices():
    """Get current prices for tracked markets."""
    client = PolymarketClient()
    prices = {}
    
    for slug, name in TRACKED_MARKETS.items():
        try:
            # Use gamma API directly
            import subprocess
            result = subprocess.run(
                f'curl -s "https://gamma-api.polymarket.com/markets?slug={slug}"',
                shell=True, capture_output=True, text=True
            )
            data = json.loads(result.stdout)
            if data and len(data) > 0:
                market = data[0]
                outcome_prices = json.loads(market.get("outcomePrices", "[]"))
                if outcome_prices:
                    prices[slug] = {
                        "yes": float(outcome_prices[0]) * 100,
                        "name": name
                    }
        except Exception as e:
            print(f"Error getting {slug}: {e}")
    
    return prices

def check_pending_events():
    """Check price updates for events logged in the last 24h."""
    data = load_events()
    prices = get_market_prices()
    
    now = datetime.now()
    
    for event in data["events"]:
        if event.get("market_price_1h_later"):
            continue  # Already has update
        
        # Check if 1+ hour has passed
        news_time = datetime.fromisoformat(event["news_time"])
        hours_passed = (now - news_time).total_seconds() / 3600
        
        if hours_passed >= 1:
            slug = event.get("market_slug")
            if slug and slug in prices:
                update_event(event["id"], 
                    market_price_1h_later=f"{prices[slug]['yes']:.1f}")
                print(f"Updated event #{event['id']} with 1h price: {prices[slug]['yes']:.1f}%")

def run_monitor():
    """Main monitoring loop."""
    print(f"\n=== Monitor Run: {datetime.now().strftime('%Y-%m-%d %H:%M')} ===\n")
    
    # 1. Check current market prices
    print("Checking market prices...")
    prices = get_market_prices()
    for slug, info in prices.items():
        print(f"  {info['name']}: {info['yes']:.1f}% Yes")
    
    # 2. Search for news
    print("\nSearching for AI news...")
    news = search_news()
    
    # Save seen headlines to avoid duplicates
    seen_file = DATA_DIR / "seen_headlines.json"
    seen = set()
    if seen_file.exists():
        with open(seen_file) as f:
            seen = set(json.load(f))
    
    new_items = []
    for item in news:
        title = item.get("title", "")
        if title and title not in seen:
            # Check if it's relevant
            title_lower = title.lower()
            if any(kw in title_lower for kw in AI_KEYWORDS):
                new_items.append(item)
                seen.add(title)
    
    with open(seen_file, 'w') as f:
        json.dump(list(seen)[-100:], f)  # Keep last 100
    
    if new_items:
        print(f"\nFound {len(new_items)} new relevant headlines:")
        for item in new_items:
            print(f"  📰 {item['title'][:60]}...")
    else:
        print("  No new relevant news")
    
    # 3. Update pending events
    print("\nChecking pending events...")
    check_pending_events()
    
    print("\n✓ Monitor complete")

if __name__ == "__main__":
    run_monitor()
