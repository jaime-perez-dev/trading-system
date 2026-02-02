#!/usr/bin/env python3
"""
Trading System Dashboard
One-command view of portfolio, markets, and opportunities

Usage:
  python dashboard.py           # Full dashboard with pretty output
  python dashboard.py --json    # JSON output for automation
  python dashboard.py --quiet   # Compact summary (for cron/logs)
"""

import argparse
import json
from datetime import datetime
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent))

from polymarket.client import PolymarketClient
from paper_trader import PaperTrader, STARTING_BALANCE

DATA_DIR = Path(__file__).parent / "data"


def get_live_prices(client: PolymarketClient, slugs: list) -> dict:
    """Get live prices for a list of market slugs"""
    prices = {}
    for slug in slugs:
        market = client.get_market_by_slug(slug)
        if market:
            parsed = client.parse_prices(market)
            prices[slug] = {
                "yes": parsed.get("Yes", 0),
                "no": parsed.get("No", 0),
                "market": market
            }
    return prices


def calculate_unrealized_pnl(trades: list, prices: dict) -> list:
    """Calculate unrealized P&L for open positions"""
    results = []
    for t in trades:
        if t["status"] != "OPEN":
            continue
        
        slug = t["market_slug"]
        if slug not in prices:
            continue
        
        current_price = prices[slug]["yes"] if t["outcome"] == "Yes" else prices[slug]["no"]
        entry_price = t["entry_price"]
        shares = t["shares"]
        
        # P&L = price change * shares
        price_change = current_price - entry_price
        unrealized_pnl = (price_change / 100) * shares
        pnl_pct = (unrealized_pnl / t["amount"]) * 100 if t["amount"] > 0 else 0
        
        results.append({
            **t,
            "current_price": current_price,
            "unrealized_pnl": unrealized_pnl,
            "unrealized_pnl_pct": pnl_pct,
        })
    
    return results


def print_header(title: str):
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print(f"{'=' * 60}")


def get_dashboard_data() -> dict:
    """Get all dashboard data as a dictionary (for JSON output)"""
    client = PolymarketClient()
    trader = PaperTrader()
    
    open_trades = [t for t in trader.trades if t["status"] == "OPEN"]
    closed_trades = [t for t in trader.trades if t["status"] in ["CLOSED", "RESOLVED"]]
    
    position_slugs = list(set(t["market_slug"] for t in open_trades))
    live_prices = get_live_prices(client, position_slugs)
    positions_with_pnl = calculate_unrealized_pnl(open_trades, live_prices)
    
    total_unrealized = sum(p["unrealized_pnl"] for p in positions_with_pnl)
    total_realized = sum(t.get("pnl", 0) for t in closed_trades)
    total_invested = sum(t["amount"] for t in open_trades)
    
    markets = client.get_tracked_ai_markets()
    markets.sort(key=lambda x: float(x.get("volume", 0)), reverse=True)
    
    # Last scan info
    last_scan_file = DATA_DIR / "last_scan.json"
    last_scan = {}
    if last_scan_file.exists():
        with open(last_scan_file) as f:
            last_scan = json.load(f)
    
    return {
        "timestamp": datetime.now().isoformat(),
        "portfolio": {
            "starting_balance": STARTING_BALANCE,
            "realized_pnl": round(total_realized, 2),
            "unrealized_pnl": round(total_unrealized, 2),
            "total_pnl": round(total_realized + total_unrealized, 2),
            "total_invested": round(total_invested, 2),
            "available": round(STARTING_BALANCE + total_realized - total_invested, 2),
        },
        "positions": {
            "open_count": len(open_trades),
            "closed_count": len(closed_trades),
            "open": [
                {
                    "id": p["id"],
                    "market": p["question"][:50],
                    "entry_price": p["entry_price"],
                    "current_price": p["current_price"],
                    "amount": p["amount"],
                    "unrealized_pnl": round(p["unrealized_pnl"], 2),
                }
                for p in positions_with_pnl
            ],
        },
        "markets": {
            "ai_markets_count": len(markets),
            "top_by_volume": [
                {
                    "question": m["question"][:60],
                    "yes_price": client.parse_prices(m).get("Yes", 0),
                    "volume": float(m.get("volume", 0)),
                }
                for m in markets[:10]
            ],
        },
        "system": {
            "last_scan": last_scan.get("timestamp"),
            "new_articles": last_scan.get("new_articles", 0),
            "opportunities": last_scan.get("opportunities", 0),
        },
    }


def print_quiet(data: dict):
    """Print compact one-liner for cron/logs"""
    p = data["portfolio"]
    pnl_emoji = "🟢" if p["total_pnl"] >= 0 else "🔴"
    print(f"[{data['timestamp'][:19]}] {pnl_emoji} P&L: ${p['total_pnl']:+.2f} | Open: {data['positions']['open_count']} | Markets: {data['markets']['ai_markets_count']}")


def main():
    parser = argparse.ArgumentParser(description="Trading System Dashboard")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument("--quiet", "-q", action="store_true", help="Compact one-liner (for cron/logs)")
    args = parser.parse_args()
    
    data = get_dashboard_data()
    
    if args.json:
        print(json.dumps(data, indent=2))
        return
    
    if args.quiet:
        print_quiet(data)
        return
    
    # Full pretty output
    print(f"""
╔══════════════════════════════════════════════════════════════╗
║          AI TRADING SYSTEM DASHBOARD                        ║
║          {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}                               ║
╚══════════════════════════════════════════════════════════════╝
""")
    
    client = PolymarketClient()
    trader = PaperTrader()
    
    # Get open positions
    open_trades = [t for t in trader.trades if t["status"] == "OPEN"]
    closed_trades = [t for t in trader.trades if t["status"] in ["CLOSED", "RESOLVED"]]
    
    # Get live prices for positions
    position_slugs = list(set(t["market_slug"] for t in open_trades))
    live_prices = get_live_prices(client, position_slugs)
    
    # Calculate P&L
    positions_with_pnl = calculate_unrealized_pnl(open_trades, live_prices)
    
    total_unrealized = sum(p["unrealized_pnl"] for p in positions_with_pnl)
    total_realized = sum(t.get("pnl", 0) for t in closed_trades)
    total_invested = sum(t["amount"] for t in open_trades)
    
    # Portfolio Summary
    print_header("📊 PORTFOLIO SUMMARY")
    print(f"""
  💰 Starting Balance:   ${STARTING_BALANCE:>10,.2f}
  📈 Realized P&L:       ${total_realized:>+10,.2f}
  📊 Unrealized P&L:     ${total_unrealized:>+10,.2f}
  💵 Total P&L:          ${(total_realized + total_unrealized):>+10,.2f}
  ─────────────────────────────────────
  💼 Total Invested:     ${total_invested:>10,.2f}
  🎯 Available:          ${(STARTING_BALANCE + total_realized - total_invested):>10,.2f}
""")
    
    # Open Positions
    print_header("📂 OPEN POSITIONS")
    if positions_with_pnl:
        print(f"\n  {'#':<3} {'Market':<35} {'Entry':>7} {'Now':>7} {'P&L':>10}")
        print(f"  {'-'*3} {'-'*35} {'-'*7} {'-'*7} {'-'*10}")
        for p in positions_with_pnl:
            emoji = "🟢" if p["unrealized_pnl"] >= 0 else "🔴"
            print(f"  {p['id']:<3} {p['question'][:35]:<35} {p['entry_price']:>6.1f}% {p['current_price']:>6.1f}% {emoji}${p['unrealized_pnl']:>+8.2f}")
    else:
        print("\n  No open positions")
    
    # Trade History
    print_header("📜 RECENT TRADES")
    if closed_trades:
        for t in closed_trades[-5:]:
            emoji = "🏆" if t.get("pnl", 0) > 0 else "💀"
            print(f"  {emoji} #{t['id']} {t['question'][:40]}... P&L: ${t.get('pnl', 0):+.2f}")
    else:
        print("\n  No closed trades yet")
    
    # AI Markets Overview
    print_header("🎯 AI MARKETS OVERVIEW")
    markets = client.get_tracked_ai_markets()
    markets.sort(key=lambda x: float(x.get("volume", 0)), reverse=True)
    
    print(f"\n  Found {len(markets)} active AI markets\n")
    print(f"  {'Market':<45} {'Yes':>7} {'Volume':>12}")
    print(f"  {'-'*45} {'-'*7} {'-'*12}")
    for m in markets[:15]:
        prices = client.parse_prices(m)
        vol = float(m.get("volume", 0))
        print(f"  {m['question'][:45]:<45} {prices.get('Yes', 0):>6.1f}% ${vol:>10,.0f}")
    
    # System Status
    print_header("⚙️ SYSTEM STATUS")
    last_scan_file = DATA_DIR / "last_scan.json"
    if last_scan_file.exists():
        with open(last_scan_file) as f:
            scan = json.load(f)
        print(f"""
  📡 Last Scan:        {scan.get('timestamp', 'Unknown')[:19]}
  📰 New Articles:     {scan.get('new_articles', 0)}
  🎯 Opportunities:    {scan.get('opportunities', 0)}
""")
    else:
        print("\n  ⚠️ No scan data found - run scanner.py")
    
    print("\n" + "=" * 60)
    print("  Run: python scanner.py      # Find opportunities")
    print("  Run: python paper_trader.py # Manage trades")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
