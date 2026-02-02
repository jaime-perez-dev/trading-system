#!/usr/bin/env python3
"""Unit tests for trade_analyzer.py"""

import pytest
from datetime import datetime, timedelta, timezone

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from trade_analyzer import (
    calculate_hold_time,
    categorize_failure,
    generate_lessons,
    analyze_trade,
    calculate_aggregate_stats,
    extract_key_lessons,
    get_closed_trades,
    TradeAnalysis
)


class TestCalculateHoldTime:
    """Tests for hold time calculation"""
    
    def test_resolved_trade(self):
        """Resolved trade should calculate hold time correctly"""
        trade = {
            'timestamp': '2026-01-28T12:00:00+00:00',
            'resolved_at': '2026-01-30T12:00:00+00:00'
        }
        assert calculate_hold_time(trade) == 2.0
    
    def test_closed_trade(self):
        """Closed trade should use closed_at timestamp"""
        trade = {
            'timestamp': '2026-01-28T12:00:00+00:00',
            'closed_at': '2026-01-29T12:00:00+00:00'
        }
        assert calculate_hold_time(trade) == 1.0
    
    def test_no_exit_time(self):
        """Trade without exit time returns 0"""
        trade = {
            'timestamp': '2026-01-28T12:00:00+00:00'
        }
        assert calculate_hold_time(trade) == 0.0
    
    def test_partial_day_hold(self):
        """Partial day hold time calculated correctly"""
        trade = {
            'timestamp': '2026-01-28T00:00:00+00:00',
            'resolved_at': '2026-01-28T12:00:00+00:00'
        }
        assert calculate_hold_time(trade) == 0.5


class TestCategorizeFailure:
    """Tests for failure categorization"""
    
    def test_winner_returns_none(self):
        """Winning trades have no failure category"""
        trade = {'won': True, 'pnl_pct': 50}
        assert categorize_failure(trade) is None
    
    def test_total_loss_with_timing_keywords(self):
        """Total loss with timing keywords = timing_aggressive"""
        trade = {
            'won': False,
            'pnl_pct': -100,
            'reason': 'Announcement said coming weeks',
            'timestamp': '2026-01-28T00:00:00+00:00',
            'resolved_at': '2026-01-30T00:00:00+00:00'
        }
        assert categorize_failure(trade) == 'timing_aggressive'
    
    def test_total_loss_binary_wrong(self):
        """Total loss without timing = binary_wrong"""
        trade = {
            'won': False,
            'pnl_pct': -100,
            'reason': 'Market analysis suggested yes',
            'timestamp': '2026-01-28T00:00:00+00:00',
            'resolved_at': '2026-01-30T00:00:00+00:00'
        }
        assert categorize_failure(trade) == 'binary_wrong'
    
    def test_small_loss_closed_early(self):
        """Small loss on closed trade = early_exit"""
        trade = {
            'won': False,
            'pnl_pct': -10,
            'status': 'CLOSED',
            'entry_price': 50,
            'reason': 'Cut losses',
            'timestamp': '2026-01-28T00:00:00+00:00',
            'closed_at': '2026-01-30T00:00:00+00:00'
        }
        assert categorize_failure(trade) == 'early_exit'
    
    def test_high_entry_price(self):
        """Loss on high entry price = overconfidence"""
        trade = {
            'won': False,
            'pnl_pct': -50,
            'entry_price': 85,
            'reason': 'Seemed like a sure thing',
            'timestamp': '2026-01-28T00:00:00+00:00',
            'resolved_at': '2026-01-30T00:00:00+00:00'
        }
        assert categorize_failure(trade) == 'overconfidence_high_price'
    
    def test_news_misread(self):
        """Loss with announcement keywords = news_misread"""
        trade = {
            'won': False,
            'pnl_pct': -50,
            'entry_price': 50,
            'reason': 'Company announced the product',
            'timestamp': '2026-01-28T00:00:00+00:00',
            'resolved_at': '2026-01-30T00:00:00+00:00'
        }
        assert categorize_failure(trade) == 'news_misread'


class TestGenerateLessons:
    """Tests for lesson generation"""
    
    def test_timing_aggressive_lessons(self):
        """Timing aggressive failures generate timing lessons"""
        trade = {
            'entry_price': 50, 
            'pnl_pct': -100,
            'timestamp': '2026-01-28T00:00:00+00:00',
            'resolved_at': '2026-01-30T00:00:00+00:00'
        }
        lessons = generate_lessons(trade, 'timing_aggressive')
        assert any('timeline' in l.lower() for l in lessons)
    
    def test_high_entry_price_lesson(self):
        """High entry price generates upside warning"""
        trade = {
            'entry_price': 95, 
            'pnl_pct': -50,
            'timestamp': '2026-01-28T00:00:00+00:00',
            'resolved_at': '2026-01-30T00:00:00+00:00'
        }
        lessons = generate_lessons(trade, 'overconfidence_high_price')
        assert any('upside' in l.lower() for l in lessons)
    
    def test_early_exit_lessons(self):
        """Early exit generates exit criteria lessons"""
        trade = {
            'entry_price': 50, 
            'pnl_pct': -10,
            'timestamp': '2026-01-28T00:00:00+00:00',
            'closed_at': '2026-01-30T00:00:00+00:00'
        }
        lessons = generate_lessons(trade, 'early_exit')
        assert any('exit' in l.lower() for l in lessons)
    
    def test_stop_loss_suggestion_for_long_holds(self):
        """Long losing holds suggest stop-loss"""
        trade = {'entry_price': 50, 'pnl_pct': -60, 'timestamp': '2026-01-01T00:00:00+00:00', 'resolved_at': '2026-01-15T00:00:00+00:00'}
        lessons = generate_lessons(trade, 'market_moved_against')
        assert any('stop-loss' in l.lower() for l in lessons)


class TestAnalyzeTrade:
    """Tests for full trade analysis"""
    
    def test_analyze_losing_trade(self):
        """Analyze a complete losing trade"""
        trade = {
            'id': 1,
            'question': 'Test market?',
            'outcome': 'Yes',
            'entry_price': 90,
            'exit_price': 0,
            'pnl': -100,
            'pnl_pct': -100,
            'won': False,
            'reason': 'Test reason',
            'timestamp': '2026-01-28T00:00:00+00:00',
            'resolved_at': '2026-01-30T00:00:00+00:00'
        }
        analysis = analyze_trade(trade)
        assert isinstance(analysis, TradeAnalysis)
        assert analysis.trade_id == 1
        assert analysis.pnl == -100
        assert not analysis.won
        assert analysis.hold_time_days == 2.0
    
    def test_analyze_winning_trade(self):
        """Winning trade has no failure category"""
        trade = {
            'id': 2,
            'question': 'Good bet?',
            'outcome': 'Yes',
            'entry_price': 50,
            'exit_price': 100,
            'pnl': 100,
            'pnl_pct': 100,
            'won': True,
            'reason': 'Good analysis',
            'timestamp': '2026-01-28T00:00:00+00:00',
            'resolved_at': '2026-01-30T00:00:00+00:00'
        }
        analysis = analyze_trade(trade)
        assert analysis.won
        assert analysis.failure_category is None


class TestCalculateAggregateStats:
    """Tests for aggregate statistics"""
    
    def test_empty_analyses(self):
        """Empty list returns empty dict"""
        assert calculate_aggregate_stats([]) == {}
    
    def test_all_losers(self):
        """All losing trades stats"""
        analyses = [
            TradeAnalysis(1, 'Q1', 'Yes', 50, 0, -100, -100, False, 'R1', 1.0, 'binary_wrong', []),
            TradeAnalysis(2, 'Q2', 'Yes', 60, 0, -50, -83, False, 'R2', 2.0, 'timing_aggressive', [])
        ]
        stats = calculate_aggregate_stats(analyses)
        assert stats['total_trades'] == 2
        assert stats['winners'] == 0
        assert stats['losers'] == 2
        assert stats['win_rate_pct'] == 0.0
        assert stats['total_pnl'] == -150
    
    def test_mixed_results(self):
        """Mixed win/loss stats"""
        analyses = [
            TradeAnalysis(1, 'Q1', 'Yes', 50, 100, 100, 100, True, 'R1', 1.0, None, []),
            TradeAnalysis(2, 'Q2', 'Yes', 60, 0, -50, -83, False, 'R2', 2.0, 'binary_wrong', [])
        ]
        stats = calculate_aggregate_stats(analyses)
        assert stats['winners'] == 1
        assert stats['losers'] == 1
        assert stats['win_rate_pct'] == 50.0
        assert stats['total_pnl'] == 50


class TestExtractKeyLessons:
    """Tests for key lesson extraction"""
    
    def test_deduplicates_lessons(self):
        """Duplicate lessons are deduplicated"""
        analyses = [
            TradeAnalysis(1, 'Q1', 'Yes', 50, 0, -100, -100, False, 'R1', 1.0, 'timing_aggressive', ['Lesson A', 'Lesson B']),
            TradeAnalysis(2, 'Q2', 'Yes', 60, 0, -50, -83, False, 'R2', 2.0, 'timing_aggressive', ['Lesson A', 'Lesson C'])
        ]
        lessons = extract_key_lessons(analyses)
        # Lesson A appears twice, should be first
        assert lessons[0] == 'Lesson A'
        assert len(lessons) == 3  # A, B, C
    
    def test_limits_to_ten_lessons(self):
        """Maximum 10 lessons returned"""
        many_lessons = [f'Lesson {i}' for i in range(20)]
        analyses = [
            TradeAnalysis(1, 'Q1', 'Yes', 50, 0, -100, -100, False, 'R1', 1.0, 'binary_wrong', many_lessons)
        ]
        lessons = extract_key_lessons(analyses)
        assert len(lessons) <= 10


class TestGetClosedTrades:
    """Tests for filtering closed trades"""
    
    def test_filters_resolved(self):
        """Returns RESOLVED trades"""
        trades = [
            {'status': 'RESOLVED', 'market_slug': 'real-market'},
            {'status': 'OPEN', 'market_slug': 'open-market'}
        ]
        closed = get_closed_trades(trades)
        assert len(closed) == 1
        assert closed[0]['status'] == 'RESOLVED'
    
    def test_filters_closed(self):
        """Returns CLOSED trades"""
        trades = [
            {'status': 'CLOSED', 'market_slug': 'closed-market'},
            {'status': 'OPEN', 'market_slug': 'open-market'}
        ]
        closed = get_closed_trades(trades)
        assert len(closed) == 1
    
    def test_excludes_test_markets(self):
        """Excludes test-* markets"""
        trades = [
            {'status': 'RESOLVED', 'market_slug': 'test-market'},
            {'status': 'RESOLVED', 'market_slug': 'real-market'}
        ]
        closed = get_closed_trades(trades)
        assert len(closed) == 1
        assert closed[0]['market_slug'] == 'real-market'


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
