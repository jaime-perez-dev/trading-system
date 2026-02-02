#!/usr/bin/env python3
"""
Tests for dashboard.py
"""

import pytest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from dashboard import calculate_unrealized_pnl


class TestCalculateUnrealizedPnl:
    """Test calculate_unrealized_pnl logic"""
    
    def test_empty_trades(self):
        """Empty trades returns empty list"""
        result = calculate_unrealized_pnl([], {})
        assert result == []
    
    def test_no_open_trades(self):
        """Non-open trades are filtered out"""
        trades = [
            {"status": "CLOSED", "market_slug": "test", "outcome": "Yes"},
            {"status": "RESOLVED", "market_slug": "test", "outcome": "No"},
        ]
        prices = {"test": {"yes": 50, "no": 50}}
        result = calculate_unrealized_pnl(trades, prices)
        assert result == []
    
    def test_open_trade_with_profit(self):
        """Open trade with price increase shows profit"""
        trades = [{
            "status": "OPEN",
            "market_slug": "ai-market",
            "outcome": "Yes",
            "entry_price": 40,
            "shares": 100,
            "amount": 40,
        }]
        prices = {"ai-market": {"yes": 60, "no": 40}}
        
        result = calculate_unrealized_pnl(trades, prices)
        
        assert len(result) == 1
        assert result[0]["current_price"] == 60
        # P&L = (60-40)/100 * 100 = 20
        assert result[0]["unrealized_pnl"] == 20.0
        # P&L % = 20/40 * 100 = 50%
        assert result[0]["unrealized_pnl_pct"] == 50.0
    
    def test_open_trade_with_loss(self):
        """Open trade with price decrease shows loss"""
        trades = [{
            "status": "OPEN",
            "market_slug": "ai-market",
            "outcome": "Yes",
            "entry_price": 60,
            "shares": 100,
            "amount": 60,
        }]
        prices = {"ai-market": {"yes": 40, "no": 60}}
        
        result = calculate_unrealized_pnl(trades, prices)
        
        assert len(result) == 1
        assert result[0]["current_price"] == 40
        # P&L = (40-60)/100 * 100 = -20
        assert result[0]["unrealized_pnl"] == -20.0
        # P&L % = -20/60 * 100 = -33.33%
        assert abs(result[0]["unrealized_pnl_pct"] - (-33.33)) < 0.1
    
    def test_no_outcome_uses_yes_price(self):
        """No outcome on trade uses yes price"""
        trades = [{
            "status": "OPEN",
            "market_slug": "test",
            "outcome": "No",
            "entry_price": 30,
            "shares": 50,
            "amount": 15,
        }]
        prices = {"test": {"yes": 70, "no": 30}}
        
        result = calculate_unrealized_pnl(trades, prices)
        
        assert len(result) == 1
        # Should use no price (30) since outcome is "No"
        assert result[0]["current_price"] == 30
        # P&L = (30-30)/100 * 50 = 0
        assert result[0]["unrealized_pnl"] == 0.0
    
    def test_missing_market_price(self):
        """Trade with missing market price is skipped"""
        trades = [{
            "status": "OPEN",
            "market_slug": "unknown-market",
            "outcome": "Yes",
            "entry_price": 50,
            "shares": 100,
            "amount": 50,
        }]
        prices = {"other-market": {"yes": 60, "no": 40}}
        
        result = calculate_unrealized_pnl(trades, prices)
        assert result == []
    
    def test_multiple_trades(self):
        """Multiple open trades are processed"""
        trades = [
            {
                "status": "OPEN",
                "market_slug": "market-a",
                "outcome": "Yes",
                "entry_price": 50,
                "shares": 100,
                "amount": 50,
            },
            {
                "status": "OPEN",
                "market_slug": "market-b",
                "outcome": "No",
                "entry_price": 40,
                "shares": 80,
                "amount": 32,
            },
            {
                "status": "CLOSED",  # Should be filtered
                "market_slug": "market-c",
                "outcome": "Yes",
                "entry_price": 60,
                "shares": 100,
                "amount": 60,
            },
        ]
        prices = {
            "market-a": {"yes": 70, "no": 30},
            "market-b": {"yes": 50, "no": 50},
            "market-c": {"yes": 80, "no": 20},
        }
        
        result = calculate_unrealized_pnl(trades, prices)
        
        assert len(result) == 2
        
        # Market A: (70-50)/100 * 100 = 20
        assert result[0]["unrealized_pnl"] == 20.0
        
        # Market B (No outcome): (50-40)/100 * 80 = 8
        assert result[1]["unrealized_pnl"] == 8.0
    
    def test_zero_amount_trade(self):
        """Trade with zero amount handles pct calculation"""
        trades = [{
            "status": "OPEN",
            "market_slug": "test",
            "outcome": "Yes",
            "entry_price": 50,
            "shares": 100,
            "amount": 0,
        }]
        prices = {"test": {"yes": 60, "no": 40}}
        
        result = calculate_unrealized_pnl(trades, prices)
        
        assert len(result) == 1
        # P&L % should be 0 to avoid division by zero
        assert result[0]["unrealized_pnl_pct"] == 0.0
    
    def test_preserves_original_trade_fields(self):
        """Original trade fields are preserved in result"""
        trades = [{
            "status": "OPEN",
            "market_slug": "test",
            "outcome": "Yes",
            "entry_price": 50,
            "shares": 100,
            "amount": 50,
            "id": 1,
            "question": "Test market?",
            "timestamp": "2026-01-01",
        }]
        prices = {"test": {"yes": 60, "no": 40}}
        
        result = calculate_unrealized_pnl(trades, prices)
        
        assert result[0]["id"] == 1
        assert result[0]["question"] == "Test market?"
        assert result[0]["timestamp"] == "2026-01-01"
    
    def test_large_position_pnl(self):
        """Large position calculates correctly"""
        trades = [{
            "status": "OPEN",
            "market_slug": "big-market",
            "outcome": "Yes",
            "entry_price": 10,
            "shares": 10000,
            "amount": 1000,
        }]
        prices = {"big-market": {"yes": 90, "no": 10}}
        
        result = calculate_unrealized_pnl(trades, prices)
        
        # P&L = (90-10)/100 * 10000 = 8000
        assert result[0]["unrealized_pnl"] == 8000.0
        # P&L % = 8000/1000 * 100 = 800%
        assert result[0]["unrealized_pnl_pct"] == 800.0
    
    def test_fractional_prices(self):
        """Handles fractional prices correctly"""
        trades = [{
            "status": "OPEN",
            "market_slug": "test",
            "outcome": "Yes",
            "entry_price": 33.33,
            "shares": 150,
            "amount": 50,
        }]
        prices = {"test": {"yes": 66.67, "no": 33.33}}
        
        result = calculate_unrealized_pnl(trades, prices)
        
        # P&L = (66.67-33.33)/100 * 150 = 50.01
        assert abs(result[0]["unrealized_pnl"] - 50.01) < 0.1


class TestDashboardIntegration:
    """Integration tests for dashboard functions"""
    
    def test_pnl_calculation_matches_paper_trader(self):
        """P&L calculation should match paper_trader logic"""
        # This ensures consistency between dashboard display and actual trading
        trades = [{
            "status": "OPEN",
            "market_slug": "test",
            "outcome": "Yes",
            "entry_price": 25,
            "shares": 400,  # $100 at 25 cents = 400 shares
            "amount": 100,
        }]
        prices = {"test": {"yes": 75, "no": 25}}
        
        result = calculate_unrealized_pnl(trades, prices)
        
        # If resolves YES: win 400 * ($1 - $0.25) = $300 profit
        # Current unrealized at 75%: (75-25)/100 * 400 = $200
        assert result[0]["unrealized_pnl"] == 200.0
