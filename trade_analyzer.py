#!/usr/bin/env python3
"""
Trade Post-Mortem Analyzer
Analyzes closed trades to understand what went wrong and identify patterns.
"""

import json
import os
from datetime import datetime, timedelta
from dataclasses import dataclass
from typing import List, Optional, Dict, Any

DATA_DIR = os.path.join(os.path.dirname(__file__), 'data')
TRADES_FILE = os.path.join(DATA_DIR, 'paper_trades.json')
ANALYSIS_FILE = os.path.join(DATA_DIR, 'trade_analysis.json')


@dataclass
class TradeAnalysis:
    """Analysis of a single trade"""
    trade_id: int
    question: str
    outcome: str
    entry_price: float
    exit_price: float
    pnl: float
    pnl_pct: float
    won: bool
    reason: str
    hold_time_days: float
    failure_category: Optional[str]  # timing, overconfidence, news_misread, market_moved, etc.
    lessons: List[str]


def load_trades() -> List[Dict[str, Any]]:
    """Load all trades from paper_trades.json"""
    if not os.path.exists(TRADES_FILE):
        return []
    with open(TRADES_FILE, 'r') as f:
        return json.load(f)


def get_closed_trades(trades: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Get trades that have resolved or been closed"""
    return [t for t in trades if t.get('status') in ['RESOLVED', 'CLOSED'] 
            and not t.get('market_slug', '').startswith('test')]


def calculate_hold_time(trade: Dict[str, Any]) -> float:
    """Calculate how long a position was held in days"""
    entry = datetime.fromisoformat(trade['timestamp'].replace('Z', '+00:00'))
    
    if trade.get('resolved_at'):
        exit_time = datetime.fromisoformat(trade['resolved_at'].replace('Z', '+00:00'))
    elif trade.get('closed_at'):
        exit_time = datetime.fromisoformat(trade['closed_at'].replace('Z', '+00:00'))
    else:
        return 0.0
    
    return (exit_time - entry).total_seconds() / 86400


def categorize_failure(trade: Dict[str, Any]) -> Optional[str]:
    """Categorize why a trade failed"""
    if trade.get('won', False):
        return None
    
    pnl_pct = trade.get('pnl_pct', 0)
    entry_price = trade.get('entry_price', 0)
    reason = trade.get('reason', '').lower()
    hold_time = calculate_hold_time(trade)
    
    # Total loss on binary outcome
    if pnl_pct <= -95:
        if 'weeks' in reason or 'days' in reason or 'soon' in reason:
            return 'timing_aggressive'
        return 'binary_wrong'
    
    # Small loss from early exit
    if pnl_pct > -20 and trade.get('status') == 'CLOSED':
        return 'early_exit'
    
    # High entry price that didn't work out
    if entry_price > 80:
        return 'overconfidence_high_price'
    
    # News interpretation was wrong
    if 'announced' in reason or 'confirmed' in reason:
        return 'news_misread'
    
    return 'market_moved_against'


def generate_lessons(trade: Dict[str, Any], category: Optional[str]) -> List[str]:
    """Generate lessons learned from a trade"""
    lessons = []
    
    if category == 'timing_aggressive':
        lessons.append("Don't bet on tight timelines from vague announcements")
        lessons.append("'Coming soon' rarely means 'next week'")
        
    if category == 'binary_wrong':
        lessons.append("Binary outcomes are high-risk - size positions accordingly")
        lessons.append("Consider partial positions or hedging")
        
    if category == 'early_exit':
        lessons.append("Review exit criteria - was the thesis still valid?")
        lessons.append("Consider using stop-losses with trailing profit")
        
    if category == 'overconfidence_high_price':
        lessons.append("High prices (>80%) mean little upside, lots of downside")
        lessons.append("Look for mispriced markets, not confirming bets")
        
    if category == 'news_misread':
        lessons.append("Verify news interpretation - what exactly was announced?")
        lessons.append("Distinguish between 'testing', 'planning', and 'launching'")
    
    # General lessons based on trade characteristics
    entry_price = trade.get('entry_price', 0)
    if entry_price > 90:
        lessons.append(f"Entry at {entry_price}% - only 10% upside, 100% downside")
    
    hold_time = calculate_hold_time(trade)
    if hold_time > 7 and trade.get('pnl_pct', 0) < -50:
        lessons.append("Consider stop-loss orders for extended holds")
    
    return lessons


def analyze_trade(trade: Dict[str, Any]) -> TradeAnalysis:
    """Analyze a single trade"""
    category = categorize_failure(trade)
    lessons = generate_lessons(trade, category)
    
    return TradeAnalysis(
        trade_id=trade.get('id', 0),
        question=trade.get('question', ''),
        outcome=trade.get('outcome', ''),
        entry_price=trade.get('entry_price', 0),
        exit_price=trade.get('exit_price', 0),
        pnl=trade.get('pnl', 0),
        pnl_pct=trade.get('pnl_pct', 0),
        won=trade.get('won', False),
        reason=trade.get('reason', ''),
        hold_time_days=calculate_hold_time(trade),
        failure_category=category,
        lessons=lessons
    )


def calculate_aggregate_stats(analyses: List[TradeAnalysis]) -> Dict[str, Any]:
    """Calculate aggregate statistics from all analyses"""
    if not analyses:
        return {}
    
    total_trades = len(analyses)
    winners = [a for a in analyses if a.won]
    losers = [a for a in analyses if not a.won]
    
    total_pnl = sum(a.pnl for a in analyses)
    avg_pnl = total_pnl / total_trades if total_trades > 0 else 0
    
    win_rate = len(winners) / total_trades * 100 if total_trades > 0 else 0
    
    # Failure category breakdown
    category_counts = {}
    for a in losers:
        cat = a.failure_category or 'unknown'
        category_counts[cat] = category_counts.get(cat, 0) + 1
    
    # Average hold time
    avg_hold_time = sum(a.hold_time_days for a in analyses) / total_trades if total_trades > 0 else 0
    
    return {
        'total_trades': total_trades,
        'winners': len(winners),
        'losers': len(losers),
        'win_rate_pct': round(win_rate, 1),
        'total_pnl': round(total_pnl, 2),
        'avg_pnl': round(avg_pnl, 2),
        'avg_hold_time_days': round(avg_hold_time, 1),
        'failure_categories': category_counts
    }


def extract_key_lessons(analyses: List[TradeAnalysis]) -> List[str]:
    """Extract most important lessons from all analyses"""
    all_lessons = []
    for a in analyses:
        all_lessons.extend(a.lessons)
    
    # Deduplicate and prioritize
    lesson_counts = {}
    for lesson in all_lessons:
        lesson_counts[lesson] = lesson_counts.get(lesson, 0) + 1
    
    # Sort by frequency
    sorted_lessons = sorted(lesson_counts.items(), key=lambda x: x[1], reverse=True)
    return [lesson for lesson, count in sorted_lessons[:10]]


def print_analysis_report(analyses: List[TradeAnalysis], stats: Dict[str, Any], key_lessons: List[str]):
    """Print a formatted analysis report"""
    print("\n" + "=" * 70)
    print("  📊 TRADE POST-MORTEM ANALYSIS")
    print("=" * 70)
    
    print(f"\n  📈 Overall Stats")
    print("  " + "-" * 40)
    print(f"  Total Trades:     {stats.get('total_trades', 0)}")
    print(f"  Winners:          {stats.get('winners', 0)}")
    print(f"  Losers:           {stats.get('losers', 0)}")
    print(f"  Win Rate:         {stats.get('win_rate_pct', 0)}%")
    print(f"  Total P&L:        ${stats.get('total_pnl', 0):,.2f}")
    print(f"  Avg P&L/Trade:    ${stats.get('avg_pnl', 0):,.2f}")
    print(f"  Avg Hold Time:    {stats.get('avg_hold_time_days', 0):.1f} days")
    
    if stats.get('failure_categories'):
        print(f"\n  🔴 Failure Categories")
        print("  " + "-" * 40)
        for cat, count in sorted(stats['failure_categories'].items(), key=lambda x: x[1], reverse=True):
            cat_display = cat.replace('_', ' ').title()
            print(f"  {cat_display}: {count}")
    
    print(f"\n  📝 Individual Trade Analysis")
    print("  " + "-" * 40)
    
    for a in analyses:
        status = "✅ WON" if a.won else "❌ LOST"
        print(f"\n  Trade #{a.trade_id}: {a.question[:45]}...")
        print(f"    Status: {status}")
        print(f"    Entry: {a.entry_price}% → Exit: {a.exit_price}%")
        print(f"    P&L: ${a.pnl:,.2f} ({a.pnl_pct:+.1f}%)")
        print(f"    Hold Time: {a.hold_time_days:.1f} days")
        print(f"    Original Reason: {a.reason[:60]}...")
        
        if a.failure_category:
            print(f"    Failure Type: {a.failure_category.replace('_', ' ').title()}")
        
        if a.lessons:
            print(f"    Lessons:")
            for lesson in a.lessons[:3]:
                print(f"      • {lesson}")
    
    if key_lessons:
        print(f"\n  🎯 KEY LESSONS LEARNED")
        print("  " + "-" * 40)
        for i, lesson in enumerate(key_lessons, 1):
            print(f"  {i}. {lesson}")
    
    print("\n" + "=" * 70)


def save_analysis(analyses: List[TradeAnalysis], stats: Dict[str, Any], key_lessons: List[str]):
    """Save analysis to JSON file"""
    data = {
        'generated_at': datetime.now().isoformat(),
        'stats': stats,
        'key_lessons': key_lessons,
        'trade_analyses': [
            {
                'trade_id': a.trade_id,
                'question': a.question,
                'outcome': a.outcome,
                'entry_price': a.entry_price,
                'exit_price': a.exit_price,
                'pnl': a.pnl,
                'pnl_pct': a.pnl_pct,
                'won': a.won,
                'reason': a.reason,
                'hold_time_days': a.hold_time_days,
                'failure_category': a.failure_category,
                'lessons': a.lessons
            }
            for a in analyses
        ]
    }
    
    with open(ANALYSIS_FILE, 'w') as f:
        json.dump(data, f, indent=2)
    
    print(f"\n  💾 Analysis saved to {ANALYSIS_FILE}")


def main():
    """Main entry point"""
    trades = load_trades()
    closed_trades = get_closed_trades(trades)
    
    if not closed_trades:
        print("\n  No closed/resolved trades to analyze yet.")
        return
    
    analyses = [analyze_trade(t) for t in closed_trades]
    stats = calculate_aggregate_stats(analyses)
    key_lessons = extract_key_lessons(analyses)
    
    print_analysis_report(analyses, stats, key_lessons)
    save_analysis(analyses, stats, key_lessons)


if __name__ == '__main__':
    main()
