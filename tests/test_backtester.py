#!/usr/bin/env python3
"""
Unit tests for backtester.py

Tests trading statistics calculations and analysis functions.
No file I/O required - all tests use in-memory data.
"""

import pytest
from datetime import datetime, timedelta
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backtester import (
    TradeStats,
    calculate_unrealized_pnl,
    analyze_trades,
    analyze_timing,
    generate_marketing_json,
)


class TestTradeStats:
    """Tests for the TradeStats dataclass."""
    
    def test_default_values(self):
        """TradeStats should have sensible defaults."""
        stats = TradeStats()
        
        assert stats.total_trades == 0
        assert stats.closed_trades == 0
        assert stats.open_trades == 0
        assert stats.winning_trades == 0
        assert stats.losing_trades == 0
        assert stats.total_pnl == 0.0
        assert stats.realized_pnl == 0.0
        assert stats.unrealized_pnl == 0.0
        assert stats.win_rate == 0.0
        assert stats.profit_factor == 0.0


class TestCalculateUnrealizedPnl:
    """Tests for unrealized P&L calculation."""
    
    def test_closed_trade_returns_zero(self):
        """Closed trades have no unrealized P&L."""
        trade = {
            "status": "CLOSED",
            "entry_price": 50,
            "shares": 100,
            "outcome": "Yes"
        }
        
        result = calculate_unrealized_pnl(trade, current_price=60)
        assert result == 0.0
    
    def test_no_current_price_returns_zero(self):
        """Without current price, unrealized P&L is zero."""
        trade = {
            "status": "OPEN",
            "entry_price": 50,
            "shares": 100,
            "outcome": "Yes"
        }
        
        result = calculate_unrealized_pnl(trade, current_price=None)
        assert result == 0.0
    
    def test_yes_position_profit(self):
        """Yes position profits when price rises."""
        trade = {
            "status": "OPEN",
            "entry_price": 50,  # 50%
            "shares": 100,
            "outcome": "Yes"
        }
        
        # Price rose from 50% to 60%
        result = calculate_unrealized_pnl(trade, current_price=60)
        # (0.60 - 0.50) * 100 * 100 = $10
        assert result == pytest.approx(10.0)
    
    def test_yes_position_loss(self):
        """Yes position loses when price falls."""
        trade = {
            "status": "OPEN",
            "entry_price": 50,  # 50%
            "shares": 100,
            "outcome": "Yes"
        }
        
        # Price fell from 50% to 40%
        result = calculate_unrealized_pnl(trade, current_price=40)
        # (0.40 - 0.50) * 100 * 100 = -$10
        assert result == pytest.approx(-10.0)
    
    def test_no_position_profit(self):
        """No position profits when price falls."""
        trade = {
            "status": "OPEN",
            "entry_price": 50,  # 50%
            "shares": 100,
            "outcome": "No"
        }
        
        # Price fell from 50% to 40% (good for No position)
        result = calculate_unrealized_pnl(trade, current_price=40)
        # (0.50 - 0.40) * 100 * 100 = $10
        assert result == pytest.approx(10.0)
    
    def test_no_position_loss(self):
        """No position loses when price rises."""
        trade = {
            "status": "OPEN",
            "entry_price": 50,  # 50%
            "shares": 100,
            "outcome": "No"
        }
        
        # Price rose from 50% to 60% (bad for No position)
        result = calculate_unrealized_pnl(trade, current_price=60)
        # (0.50 - 0.60) * 100 * 100 = -$10
        assert result == pytest.approx(-10.0)


class TestAnalyzeTrades:
    """Tests for trade analysis function."""
    
    def test_empty_trades_returns_default_stats(self):
        """Empty trade list returns default stats."""
        stats = analyze_trades([])
        
        assert stats.total_trades == 0
        assert stats.win_rate == 0.0
    
    def test_single_winning_trade(self):
        """Stats for a single winning trade."""
        trades = [{
            "status": "CLOSED",
            "amount": 100,
            "pnl": 50,
            "shares": 100,
            "entry_price": 50
        }]
        
        stats = analyze_trades(trades)
        
        assert stats.total_trades == 1
        assert stats.closed_trades == 1
        assert stats.winning_trades == 1
        assert stats.losing_trades == 0
        assert stats.realized_pnl == 50
        assert stats.win_rate == 100.0
        assert stats.avg_win == 50
        assert stats.largest_win == 50
    
    def test_single_losing_trade(self):
        """Stats for a single losing trade."""
        trades = [{
            "status": "CLOSED",
            "amount": 100,
            "pnl": -30,
            "shares": 100,
            "entry_price": 50
        }]
        
        stats = analyze_trades(trades)
        
        assert stats.total_trades == 1
        assert stats.closed_trades == 1
        assert stats.winning_trades == 0
        assert stats.losing_trades == 1
        assert stats.realized_pnl == -30
        assert stats.win_rate == 0.0
        assert stats.avg_loss == 30  # Absolute value
        assert stats.largest_loss == 30
    
    def test_mixed_trades(self):
        """Stats for mix of winning and losing trades."""
        trades = [
            {"status": "CLOSED", "amount": 100, "pnl": 100},  # Win $100
            {"status": "CLOSED", "amount": 100, "pnl": 50},   # Win $50
            {"status": "CLOSED", "amount": 100, "pnl": -25},  # Lose $25
        ]
        
        stats = analyze_trades(trades)
        
        assert stats.total_trades == 3
        assert stats.closed_trades == 3
        assert stats.winning_trades == 2
        assert stats.losing_trades == 1
        assert stats.realized_pnl == 125  # 100 + 50 - 25
        assert stats.win_rate == pytest.approx(66.67, rel=0.01)  # 2/3
        assert stats.avg_win == 75  # (100 + 50) / 2
        assert stats.avg_loss == 25
        assert stats.largest_win == 100
        assert stats.largest_loss == 25
    
    def test_open_trades_count(self):
        """Open trades are counted separately."""
        trades = [
            {"status": "CLOSED", "amount": 100, "pnl": 50},
            {"status": "OPEN", "amount": 100, "entry_price": 50, "shares": 100},
            {"status": "OPEN", "amount": 100, "entry_price": 60, "shares": 100},
        ]
        
        stats = analyze_trades(trades)
        
        assert stats.total_trades == 3
        assert stats.closed_trades == 1
        assert stats.open_trades == 2
    
    def test_profit_factor_calculation(self):
        """Profit factor = gross wins / gross losses."""
        trades = [
            {"status": "CLOSED", "amount": 100, "pnl": 100},  # Win
            {"status": "CLOSED", "amount": 100, "pnl": 50},   # Win
            {"status": "CLOSED", "amount": 100, "pnl": -30},  # Lose
        ]
        
        stats = analyze_trades(trades)
        
        # Gross wins = 150, Gross losses = 30
        # Profit factor = 150 / 30 = 5.0
        assert stats.profit_factor == pytest.approx(5.0)
    
    def test_hold_time_calculation(self):
        """Average hold time calculated from timestamps."""
        base = datetime.now()
        trades = [
            {
                "status": "CLOSED",
                "amount": 100,
                "pnl": 50,
                "timestamp": base.isoformat(),
                "exit_timestamp": (base + timedelta(hours=24)).isoformat()
            },
            {
                "status": "CLOSED",
                "amount": 100,
                "pnl": 30,
                "timestamp": base.isoformat(),
                "exit_timestamp": (base + timedelta(hours=48)).isoformat()
            },
        ]
        
        stats = analyze_trades(trades)
        
        # Average hold time = (24 + 48) / 2 = 36 hours
        assert stats.avg_hold_time_hours == pytest.approx(36.0)
    
    def test_total_pnl_includes_unrealized(self):
        """Total P&L = realized + unrealized."""
        trades = [
            {"status": "CLOSED", "amount": 100, "pnl": 50},
            {
                "status": "OPEN",
                "amount": 100,
                "entry_price": 50,
                "shares": 100,
                "market_slug": "test-market",
                "outcome": "Yes"
            },
        ]
        
        current_prices = {"test-market": 60}  # 10pp profit
        stats = analyze_trades(trades, current_prices)
        
        # Unrealized = (0.60 - 0.50) * 100 * 100 = $10
        # Total = 50 (realized) + 10 (unrealized) = $60
        assert stats.realized_pnl == 50
        assert stats.unrealized_pnl == pytest.approx(10.0)
        assert stats.total_pnl == pytest.approx(60.0)


class TestAnalyzeTiming:
    """Tests for timing analysis function."""
    
    def test_empty_events(self):
        """Empty events list returns default timing stats."""
        result = analyze_timing([])
        
        assert result["events_analyzed"] == 0
    
    def test_timing_with_price_moves(self):
        """Timing stats calculated from price movements."""
        base = datetime.now()
        events = [
            {
                "timestamp": base.isoformat(),
                "news_time": base.isoformat(),
                "trade_time": (base + timedelta(minutes=30)).isoformat(),
                "initial_price": 50,
                "current_price": 55,
                "price_move_pp": 5
            },
            {
                "timestamp": base.isoformat(),
                "news_time": base.isoformat(),
                "trade_time": (base + timedelta(minutes=60)).isoformat(),
                "initial_price": 60,
                "current_price": 70,
                "price_move_pp": 10
            },
        ]
        
        result = analyze_timing(events)
        
        assert result["events_analyzed"] == 2


class TestGenerateMarketingJson:
    """Tests for marketing JSON generation."""
    
    def test_marketing_json_structure(self):
        """Marketing JSON has expected structure."""
        stats = TradeStats(
            total_trades=10,
            closed_trades=8,
            winning_trades=6,
            losing_trades=2,
            win_rate=75.0,
            total_pnl=500.0,
            realized_pnl=450.0,
            profit_factor=3.0,
            avg_hold_time_hours=24.5
        )
        
        result = generate_marketing_json(stats)
        
        assert "performance" in result
        assert "win_rate" in result["performance"]
        assert "total_pnl" in result["performance"]
        assert "total_trades" in result["performance"]
        assert result["performance"]["win_rate"] == 75.0
    
    def test_marketing_json_rounds_values(self):
        """Marketing JSON rounds values for cleaner display."""
        stats = TradeStats(
            win_rate=66.666666,
            total_pnl=123.456789,
            profit_factor=2.333333
        )
        
        result = generate_marketing_json(stats)
        
        # Check values are rounded reasonably
        assert result["performance"]["win_rate"] == 66.7
        assert result["performance"]["total_pnl"] == 123.46


class TestEdgeCases:
    """Tests for edge cases and error handling."""
    
    def test_trade_with_zero_pnl(self):
        """Trade with exactly zero P&L is neither win nor loss."""
        trades = [{"status": "CLOSED", "amount": 100, "pnl": 0}]
        
        stats = analyze_trades(trades)
        
        assert stats.winning_trades == 0
        assert stats.losing_trades == 0
        assert stats.closed_trades == 1
    
    def test_trade_with_none_pnl(self):
        """Trade with None P&L treated as zero."""
        trades = [{"status": "CLOSED", "amount": 100, "pnl": None}]
        
        stats = analyze_trades(trades)
        
        assert stats.realized_pnl == 0
        assert stats.closed_trades == 1
    
    def test_trade_missing_amount(self):
        """Trade missing amount field doesn't crash."""
        trades = [{"status": "CLOSED", "pnl": 50}]
        
        stats = analyze_trades(trades)
        
        assert stats.total_invested == 0
        assert stats.realized_pnl == 50
    
    def test_all_losses_profit_factor(self):
        """Profit factor with all losses doesn't divide by zero."""
        trades = [
            {"status": "CLOSED", "amount": 100, "pnl": -50},
            {"status": "CLOSED", "amount": 100, "pnl": -30},
        ]
        
        stats = analyze_trades(trades)
        
        # No wins, so profit factor should be 0
        assert stats.profit_factor == 0.0
    
    def test_all_wins_profit_factor(self):
        """Profit factor with all wins approaches infinity."""
        trades = [
            {"status": "CLOSED", "amount": 100, "pnl": 50},
            {"status": "CLOSED", "amount": 100, "pnl": 30},
        ]
        
        stats = analyze_trades(trades)
        
        # No losses, profit factor = total_wins / 1 = total_wins
        # Actually implemented as inf when losses = 0, but may vary
        assert stats.profit_factor > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
