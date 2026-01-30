#!/usr/bin/env python3
"""
Backtesting Module for AI Trading System

Features:
- Performance analysis of paper/real trades
- Win rate calculation
- Timing analysis (price movement after news)
- Historical edge validation
- Metrics for marketing/credibility
"""

import json
import argparse
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional
from dataclasses import dataclass

DATA_DIR = Path(__file__).parent / "data"
PAPER_TRADES_FILE = DATA_DIR / "paper_trades.json"
EDGE_EVENTS_FILE = DATA_DIR / "edge_events.json"


@dataclass
class TradeStats:
    """Aggregate trading statistics"""
    total_trades: int = 0
    closed_trades: int = 0
    open_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    total_pnl: float = 0.0
    realized_pnl: float = 0.0
    unrealized_pnl: float = 0.0
    total_invested: float = 0.0
    win_rate: float = 0.0
    avg_win: float = 0.0
    avg_loss: float = 0.0
    profit_factor: float = 0.0
    largest_win: float = 0.0
    largest_loss: float = 0.0
    avg_hold_time_hours: float = 0.0


def load_trades() -> list:
    """Load paper trades from JSON file"""
    if not PAPER_TRADES_FILE.exists():
        return []
    with open(PAPER_TRADES_FILE) as f:
        return json.load(f)


def load_edge_events() -> dict:
    """Load edge events for timing analysis"""
    if not EDGE_EVENTS_FILE.exists():
        return {"events": [], "stats": {}}
    with open(EDGE_EVENTS_FILE) as f:
        return json.load(f)


def calculate_unrealized_pnl(trade: dict, current_price: Optional[float] = None) -> float:
    """Calculate unrealized P&L for an open position"""
    if trade.get("status") != "OPEN":
        return 0.0
    
    if current_price is None:
        # If no current price provided, use entry (no change)
        return 0.0
    
    entry_price = trade["entry_price"] / 100  # Convert from percentage
    current = current_price / 100
    shares = trade["shares"]
    
    # For Yes positions: profit if price goes up
    if trade.get("outcome", "Yes") == "Yes":
        return (current - entry_price) * shares * 100
    else:
        # For No positions: profit if price goes down
        return (entry_price - current) * shares * 100


def analyze_trades(trades: list, current_prices: Optional[dict] = None) -> TradeStats:
    """Analyze trading performance"""
    stats = TradeStats()
    
    if not trades:
        return stats
    
    wins = []
    losses = []
    hold_times = []
    
    for trade in trades:
        stats.total_trades += 1
        stats.total_invested += trade.get("amount", 0)
        
        if trade.get("status") == "CLOSED":
            stats.closed_trades += 1
            pnl = trade.get("pnl", 0) or 0
            stats.realized_pnl += pnl
            
            if pnl > 0:
                stats.winning_trades += 1
                wins.append(pnl)
            elif pnl < 0:
                stats.losing_trades += 1
                losses.append(abs(pnl))
            
            # Calculate hold time if we have exit timestamp
            if trade.get("exit_timestamp") and trade.get("timestamp"):
                try:
                    entry = datetime.fromisoformat(trade["timestamp"].replace("Z", "+00:00"))
                    exit_t = datetime.fromisoformat(trade["exit_timestamp"].replace("Z", "+00:00"))
                    hold_hours = (exit_t - entry).total_seconds() / 3600
                    hold_times.append(hold_hours)
                except:
                    pass
        else:
            stats.open_trades += 1
            # Calculate unrealized P&L
            slug = trade.get("market_slug", "")
            current = current_prices.get(slug) if current_prices else None
            stats.unrealized_pnl += calculate_unrealized_pnl(trade, current)
    
    # Calculate derived stats
    stats.total_pnl = stats.realized_pnl + stats.unrealized_pnl
    
    if stats.closed_trades > 0:
        stats.win_rate = (stats.winning_trades / stats.closed_trades) * 100
    
    if wins:
        stats.avg_win = sum(wins) / len(wins)
        stats.largest_win = max(wins)
    
    if losses:
        stats.avg_loss = sum(losses) / len(losses)
        stats.largest_loss = max(losses)
    
    # Profit factor = gross wins / gross losses
    total_wins = sum(wins) if wins else 0
    total_losses = sum(losses) if losses else 1  # Avoid div by zero
    stats.profit_factor = total_wins / total_losses if total_losses > 0 else float('inf')
    
    if hold_times:
        stats.avg_hold_time_hours = sum(hold_times) / len(hold_times)
    
    return stats


def analyze_timing(events: list) -> dict:
    """Analyze timing between news and price movement"""
    timing_stats = {
        "events_analyzed": 0,
        "avg_price_move_1h": 0.0,
        "avg_price_move_24h": 0.0,
        "fastest_move_pct": 0.0,
        "events": []
    }
    
    if not events:
        return timing_stats
    
    moves_1h = []
    moves_24h = []
    
    for event in events:
        price_at_news = float(event.get("market_price_at_news", 0) or 0)
        price_1h = event.get("market_price_1h_later")
        price_24h = event.get("market_price_24h_later")
        
        if price_1h:
            move_1h = abs(float(price_1h) - price_at_news)
            moves_1h.append(move_1h)
        
        if price_24h:
            move_24h = abs(float(price_24h) - price_at_news)
            moves_24h.append(move_24h)
        
        timing_stats["events"].append({
            "headline": event.get("headline", "")[:60],
            "source": event.get("source", ""),
            "price_at_news": price_at_news,
            "move_1h": move_1h if price_1h else None
        })
    
    timing_stats["events_analyzed"] = len(events)
    
    if moves_1h:
        timing_stats["avg_price_move_1h"] = sum(moves_1h) / len(moves_1h)
        timing_stats["fastest_move_pct"] = max(moves_1h)
    
    if moves_24h:
        timing_stats["avg_price_move_24h"] = sum(moves_24h) / len(moves_24h)
    
    return timing_stats


def print_report(stats: TradeStats, timing: dict):
    """Print formatted backtest report"""
    print("\n" + "=" * 60)
    print("  📊 BACKTESTING REPORT - AI TRADING SYSTEM")
    print("  " + datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    print("=" * 60)
    
    # Performance Summary
    print("\n┌─────────────────────────────────────────────────────────┐")
    print("│  💰 PERFORMANCE SUMMARY                                  │")
    print("├─────────────────────────────────────────────────────────┤")
    print(f"│  Total Trades:        {stats.total_trades:>6}                           │")
    print(f"│  Closed Trades:       {stats.closed_trades:>6}                           │")
    print(f"│  Open Positions:      {stats.open_trades:>6}                           │")
    print("├─────────────────────────────────────────────────────────┤")
    pnl_color = "🟢" if stats.total_pnl >= 0 else "🔴"
    print(f"│  {pnl_color} Total P&L:        ${stats.total_pnl:>10.2f}                     │")
    print(f"│     Realized:        ${stats.realized_pnl:>10.2f}                     │")
    print(f"│     Unrealized:      ${stats.unrealized_pnl:>10.2f}                     │")
    print("└─────────────────────────────────────────────────────────┘")
    
    # Win/Loss Stats
    if stats.closed_trades > 0:
        print("\n┌─────────────────────────────────────────────────────────┐")
        print("│  🎯 WIN/LOSS ANALYSIS                                    │")
        print("├─────────────────────────────────────────────────────────┤")
        print(f"│  Win Rate:           {stats.win_rate:>6.1f}%                          │")
        print(f"│  Winning Trades:     {stats.winning_trades:>6}                           │")
        print(f"│  Losing Trades:      {stats.losing_trades:>6}                           │")
        print("├─────────────────────────────────────────────────────────┤")
        print(f"│  Avg Win:            ${stats.avg_win:>10.2f}                     │")
        print(f"│  Avg Loss:           ${stats.avg_loss:>10.2f}                     │")
        print(f"│  Largest Win:        ${stats.largest_win:>10.2f}                     │")
        print(f"│  Largest Loss:       ${stats.largest_loss:>10.2f}                     │")
        print(f"│  Profit Factor:      {stats.profit_factor:>10.2f}x                    │")
        print("└─────────────────────────────────────────────────────────┘")
    
    # Timing Analysis
    if timing.get("events_analyzed", 0) > 0:
        print("\n┌─────────────────────────────────────────────────────────┐")
        print("│  ⏱️  TIMING ANALYSIS                                      │")
        print("├─────────────────────────────────────────────────────────┤")
        print(f"│  Events Tracked:     {timing['events_analyzed']:>6}                           │")
        print(f"│  Avg 1h Move:        {timing['avg_price_move_1h']:>6.1f}pp                         │")
        print(f"│  Fastest Move:       {timing['fastest_move_pct']:>6.1f}pp                         │")
        print("└─────────────────────────────────────────────────────────┘")
    
    # Marketing Stats (for website/social)
    print("\n┌─────────────────────────────────────────────────────────┐")
    print("│  📣 MARKETING READY STATS                                │")
    print("├─────────────────────────────────────────────────────────┤")
    print(f"│  \"Win Rate: {stats.win_rate:.0f}%\"                                     │")
    print(f"│  \"Profit Factor: {stats.profit_factor:.1f}x\"                               │")
    print(f"│  \"Total Returns: ${stats.total_pnl:.2f}\"                          │")
    if stats.closed_trades > 0:
        roi = (stats.realized_pnl / stats.total_invested * 100) if stats.total_invested > 0 else 0
        print(f"│  \"ROI: {roi:.1f}% on ${stats.total_invested:.0f} invested\"                       │")
    print("└─────────────────────────────────────────────────────────┘")
    
    print()


def generate_marketing_json(stats: TradeStats) -> dict:
    """Generate stats JSON for website/API"""
    return {
        "generated_at": datetime.now().isoformat(),
        "performance": {
            "total_trades": stats.total_trades,
            "win_rate": round(stats.win_rate, 1),
            "profit_factor": round(stats.profit_factor, 2),
            "total_pnl": round(stats.total_pnl, 2),
            "realized_pnl": round(stats.realized_pnl, 2)
        },
        "marketing_copy": {
            "win_rate_display": f"{stats.win_rate:.0f}%",
            "pnl_display": f"${stats.total_pnl:,.2f}",
            "trade_count": f"{stats.closed_trades} trades"
        }
    }


def main():
    parser = argparse.ArgumentParser(description="Backtest AI Trading System")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument("--marketing", action="store_true", help="Output marketing stats only")
    parser.add_argument("--save", action="store_true", help="Save stats to data/backtest_stats.json")
    args = parser.parse_args()
    
    # Load data
    trades = load_trades()
    edge_data = load_edge_events()
    
    # Analyze
    stats = analyze_trades(trades)
    timing = analyze_timing(edge_data.get("events", []))
    
    if args.json or args.marketing:
        marketing = generate_marketing_json(stats)
        print(json.dumps(marketing, indent=2))
    else:
        print_report(stats, timing)
    
    if args.save:
        output = generate_marketing_json(stats)
        output["timing"] = timing
        output_file = DATA_DIR / "backtest_stats.json"
        with open(output_file, "w") as f:
            json.dump(output, f, indent=2)
        print(f"✅ Stats saved to {output_file}")


if __name__ == "__main__":
    main()
