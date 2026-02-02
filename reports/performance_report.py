#!/usr/bin/env python3
"""
Performance Report Generator
Generates markdown reports from trading data for marketing and transparency.
"""

import json
import os
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass
from typing import List, Dict, Any, Optional
from collections import defaultdict

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data')
TRADES_FILE = os.path.join(DATA_DIR, 'paper_trades.json')
REPORTS_DIR = os.path.join(os.path.dirname(__file__), 'generated')


@dataclass
class TradeStats:
    """Aggregated trading statistics"""
    total_trades: int
    real_trades: int  # Excludes test trades
    open_trades: int
    closed_trades: int
    resolved_trades: int
    
    total_invested: float
    total_pnl: float
    total_pnl_pct: float
    
    wins: int
    losses: int
    win_rate: float
    
    avg_hold_days: float
    avg_pnl_per_trade: float
    best_trade_pnl: float
    worst_trade_pnl: float
    
    by_status: Dict[str, int]
    by_month: Dict[str, Dict[str, Any]]


def load_trades() -> List[Dict[str, Any]]:
    """Load trades from paper_trades.json"""
    if not os.path.exists(TRADES_FILE):
        return []
    with open(TRADES_FILE, 'r') as f:
        return json.load(f)


def is_test_trade(trade: Dict[str, Any]) -> bool:
    """Check if a trade is a test trade"""
    slug = trade.get('market_slug', '')
    question = trade.get('question', '')
    return slug.startswith('test') or 'test' in question.lower()


def calculate_hold_days(trade: Dict[str, Any]) -> float:
    """Calculate how long a position was held"""
    entry_str = trade.get('timestamp', '')
    if not entry_str:
        return 0.0
    
    entry = datetime.fromisoformat(entry_str.replace('Z', '+00:00'))
    
    # Use closed_at, resolved_at, or now
    if trade.get('closed_at'):
        exit_time = datetime.fromisoformat(trade['closed_at'].replace('Z', '+00:00'))
    elif trade.get('resolved_at'):
        exit_time = datetime.fromisoformat(trade['resolved_at'].replace('Z', '+00:00'))
    else:
        exit_time = datetime.now(timezone.utc)
    
    return (exit_time - entry).total_seconds() / 86400


def get_trade_month(trade: Dict[str, Any]) -> str:
    """Get YYYY-MM for a trade"""
    ts = trade.get('timestamp', '')
    if not ts:
        return 'Unknown'
    try:
        dt = datetime.fromisoformat(ts.replace('Z', '+00:00'))
        return dt.strftime('%Y-%m')
    except:
        return 'Unknown'


def calculate_stats(trades: List[Dict[str, Any]], include_test: bool = False) -> TradeStats:
    """Calculate aggregate statistics from trades"""
    if not include_test:
        trades = [t for t in trades if not is_test_trade(t)]
    
    by_status = defaultdict(int)
    by_month = defaultdict(lambda: {'trades': 0, 'pnl': 0.0, 'invested': 0.0})
    
    total_invested = 0.0
    total_pnl = 0.0
    wins = 0
    losses = 0
    hold_days = []
    pnls = []
    
    open_count = 0
    closed_count = 0
    resolved_count = 0
    
    for trade in trades:
        status = trade.get('status', 'UNKNOWN')
        by_status[status] += 1
        
        month = get_trade_month(trade)
        by_month[month]['trades'] += 1
        
        amount = trade.get('amount', 0) or 0
        pnl = trade.get('pnl') or 0
        
        total_invested += amount
        by_month[month]['invested'] += amount
        
        if status == 'OPEN':
            open_count += 1
        elif status == 'CLOSED':
            closed_count += 1
            total_pnl += pnl
            pnls.append(pnl)
            by_month[month]['pnl'] += pnl
            if pnl >= 0:
                wins += 1
            else:
                losses += 1
            hold_days.append(calculate_hold_days(trade))
        elif status == 'RESOLVED':
            resolved_count += 1
            total_pnl += pnl
            pnls.append(pnl)
            by_month[month]['pnl'] += pnl
            if trade.get('won', False):
                wins += 1
            else:
                losses += 1
            hold_days.append(calculate_hold_days(trade))
    
    completed = wins + losses
    win_rate = (wins / completed * 100) if completed > 0 else 0.0
    avg_hold = sum(hold_days) / len(hold_days) if hold_days else 0.0
    avg_pnl = total_pnl / completed if completed > 0 else 0.0
    pnl_pct = (total_pnl / total_invested * 100) if total_invested > 0 else 0.0
    
    return TradeStats(
        total_trades=len(trades),
        real_trades=len([t for t in trades if not is_test_trade(t)]),
        open_trades=open_count,
        closed_trades=closed_count,
        resolved_trades=resolved_count,
        total_invested=total_invested,
        total_pnl=total_pnl,
        total_pnl_pct=pnl_pct,
        wins=wins,
        losses=losses,
        win_rate=win_rate,
        avg_hold_days=avg_hold,
        avg_pnl_per_trade=avg_pnl,
        best_trade_pnl=max(pnls) if pnls else 0.0,
        worst_trade_pnl=min(pnls) if pnls else 0.0,
        by_status=dict(by_status),
        by_month=dict(by_month)
    )


def format_currency(amount: float) -> str:
    """Format as USD currency"""
    if amount >= 0:
        return f"${amount:,.2f}"
    return f"-${abs(amount):,.2f}"


def format_percent(pct: float) -> str:
    """Format as percentage"""
    sign = "+" if pct >= 0 else ""
    return f"{sign}{pct:.1f}%"


def generate_summary_report(stats: TradeStats) -> str:
    """Generate a summary markdown report"""
    now = datetime.now(timezone.utc)
    
    # Determine PnL emoji
    pnl_emoji = "🟢" if stats.total_pnl >= 0 else "🔴"
    
    report = f"""# EdgeSignals Performance Report
*Generated: {now.strftime('%Y-%m-%d %H:%M UTC')}*

## 📊 Overview

| Metric | Value |
|--------|-------|
| Total Trades | {stats.total_trades} |
| Real Trades | {stats.real_trades} |
| Open Positions | {stats.open_trades} |
| Completed Trades | {stats.closed_trades + stats.resolved_trades} |

## 💰 Financial Performance

| Metric | Value |
|--------|-------|
| Total Invested | {format_currency(stats.total_invested)} |
| Net P&L | {pnl_emoji} {format_currency(stats.total_pnl)} |
| Return | {format_percent(stats.total_pnl_pct)} |
| Avg P&L per Trade | {format_currency(stats.avg_pnl_per_trade)} |

## 🎯 Win/Loss

| Metric | Value |
|--------|-------|
| Wins | {stats.wins} |
| Losses | {stats.losses} |
| Win Rate | {stats.win_rate:.1f}% |

## ⏱️ Timing

| Metric | Value |
|--------|-------|
| Avg Hold Time | {stats.avg_hold_days:.1f} days |
| Best Trade | {format_currency(stats.best_trade_pnl)} |
| Worst Trade | {format_currency(stats.worst_trade_pnl)} |

"""
    
    # Monthly breakdown
    if stats.by_month:
        report += "## 📅 Monthly Breakdown\n\n"
        report += "| Month | Trades | Invested | P&L |\n"
        report += "|-------|--------|----------|-----|\n"
        
        for month in sorted(stats.by_month.keys(), reverse=True):
            data = stats.by_month[month]
            pnl_str = format_currency(data['pnl'])
            invested_str = format_currency(data['invested'])
            report += f"| {month} | {data['trades']} | {invested_str} | {pnl_str} |\n"
    
    report += """
---

*This report is for informational purposes only. Past performance does not guarantee future results.*
"""
    
    return report


def generate_trade_log(trades: List[Dict[str, Any]], limit: int = 20) -> str:
    """Generate a detailed trade log"""
    trades = [t for t in trades if not is_test_trade(t)]
    trades = sorted(trades, key=lambda t: t.get('timestamp', ''), reverse=True)[:limit]
    
    report = "# Trade Log\n\n"
    report += "| # | Date | Market | Entry | Status | P&L |\n"
    report += "|---|------|--------|-------|--------|-----|\n"
    
    for trade in trades:
        ts = trade.get('timestamp', '')
        try:
            date = datetime.fromisoformat(ts.replace('Z', '+00:00')).strftime('%m/%d')
        except:
            date = 'N/A'
        
        question = trade.get('question', 'Unknown')[:30]
        entry = trade.get('entry_price', 0)
        status = trade.get('status', 'UNKNOWN')
        pnl = trade.get('pnl')
        
        if pnl is not None:
            pnl_str = format_currency(pnl)
        else:
            pnl_str = "-"
        
        status_emoji = {
            'OPEN': '🟡',
            'CLOSED': '✅',
            'RESOLVED': '🏁'
        }.get(status, '❓')
        
        report += f"| {trade.get('id', '?')} | {date} | {question}... | {entry:.1f}¢ | {status_emoji} | {pnl_str} |\n"
    
    return report


def generate_marketing_snippet(stats: TradeStats) -> str:
    """Generate a short marketing-friendly snippet"""
    pnl_emoji = "📈" if stats.total_pnl >= 0 else "📉"
    
    return f"""🎯 **EdgeSignals Track Record**

{pnl_emoji} {format_currency(stats.total_pnl)} ({format_percent(stats.total_pnl_pct)})
📊 {stats.total_trades} trades | {stats.win_rate:.0f}% win rate
⏱️ Avg hold: {stats.avg_hold_days:.1f} days

*Full transparency. Real results.*
"""


def save_report(content: str, filename: str) -> str:
    """Save report to file"""
    os.makedirs(REPORTS_DIR, exist_ok=True)
    filepath = os.path.join(REPORTS_DIR, filename)
    with open(filepath, 'w') as f:
        f.write(content)
    return filepath


def main():
    """CLI entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Generate performance reports')
    parser.add_argument('--type', choices=['summary', 'log', 'snippet', 'all'], 
                        default='summary', help='Report type')
    parser.add_argument('--include-test', action='store_true', 
                        help='Include test trades')
    parser.add_argument('--save', action='store_true', help='Save to file')
    parser.add_argument('--limit', type=int, default=20, help='Trade log limit')
    args = parser.parse_args()
    
    trades = load_trades()
    stats = calculate_stats(trades, include_test=args.include_test)
    
    if args.type == 'summary' or args.type == 'all':
        report = generate_summary_report(stats)
        print(report)
        if args.save:
            path = save_report(report, f"summary_{datetime.now().strftime('%Y%m%d')}.md")
            print(f"\n✅ Saved to {path}")
    
    if args.type == 'log' or args.type == 'all':
        log = generate_trade_log(trades, limit=args.limit)
        print(log)
        if args.save:
            path = save_report(log, f"trades_{datetime.now().strftime('%Y%m%d')}.md")
            print(f"\n✅ Saved to {path}")
    
    if args.type == 'snippet' or args.type == 'all':
        snippet = generate_marketing_snippet(stats)
        print(snippet)


if __name__ == '__main__':
    main()
