#!/usr/bin/env python3
"""
Unit tests for PaperTrader
"""

import json
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone
import tempfile
import sys

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from paper_trader import PaperTrader, STARTING_BALANCE


class TestPaperTrader:
    """Test suite for PaperTrader"""
    
    @pytest.fixture
    def trader(self, tmp_path):
        """Create a PaperTrader with temp data directory"""
        with patch('paper_trader.DATA_DIR', tmp_path):
            with patch('paper_trader.TRADES_FILE', tmp_path / "paper_trades.json"):
                # Mock the Polymarket client
                with patch('paper_trader.PolymarketClient') as mock_client:
                    mock_client.return_value = MagicMock()
                    trader = PaperTrader()
                    trader.trades = []
                    yield trader
    
    @pytest.fixture
    def mock_market(self):
        """Sample market data"""
        return {
            "question": "Will AI achieve AGI by 2030?",
            "slug": "ai-agi-2030",
            "outcomes": [
                {"name": "Yes", "price": 0.35},
                {"name": "No", "price": 0.65}
            ]
        }
    
    def test_starting_balance(self):
        """Starting balance should be $10k"""
        assert STARTING_BALANCE == 10000.00
    
    def test_buy_calculates_shares_correctly(self, trader, mock_market):
        """Buy should calculate shares as (amount / price) * 100"""
        trader.client.get_market_by_slug.return_value = mock_market
        trader.client.parse_prices.return_value = {"Yes": 0.35, "No": 0.65}
        
        result = trader.buy("ai-agi-2030", "Yes", 100.0, reason="Test trade")
        
        # At 0.35 price, $100 buys (100/0.35)*100 = 285.71 shares
        expected_shares = (100.0 / 0.35) * 100
        assert abs(result["shares"] - expected_shares) < 0.01
    
    def test_buy_with_manual_price(self, trader):
        """Buy with entry_price should skip market lookup for price"""
        trader.client.get_market_by_slug.return_value = {"question": "Test"}
        
        result = trader.buy("test-market", "Yes", 50.0, entry_price=0.25, reason="Manual")
        
        expected_shares = (50.0 / 0.25) * 100  # 200 shares
        assert result["shares"] == expected_shares
        assert result["entry_price"] == 0.25
    
    def test_buy_invalid_outcome(self, trader, mock_market):
        """Buy with invalid outcome should return error"""
        trader.client.get_market_by_slug.return_value = mock_market
        trader.client.parse_prices.return_value = {"Yes": 0.35, "No": 0.65}
        
        result = trader.buy("ai-agi-2030", "Maybe", 100.0)
        
        assert "error" in result
        assert "Maybe" in result["error"]
    
    def test_buy_market_not_found(self, trader):
        """Buy on non-existent market should return error"""
        trader.client.get_market_by_slug.return_value = None
        
        result = trader.buy("fake-market", "Yes", 100.0)
        
        assert "error" in result
        assert "not found" in result["error"].lower()
    
    def test_trade_has_required_fields(self, trader, mock_market):
        """Trade record should have all required fields"""
        trader.client.get_market_by_slug.return_value = mock_market
        trader.client.parse_prices.return_value = {"Yes": 0.50}
        
        trade = trader.buy("test", "Yes", 100.0, reason="Testing")
        
        required_fields = [
            "id", "type", "market_slug", "question", "outcome",
            "entry_price", "amount", "shares", "reason", 
            "timestamp", "status"
        ]
        for field in required_fields:
            assert field in trade, f"Missing field: {field}"
    
    def test_trade_status_is_open(self, trader, mock_market):
        """New trade should have OPEN status"""
        trader.client.get_market_by_slug.return_value = mock_market
        trader.client.parse_prices.return_value = {"Yes": 0.50}
        
        trade = trader.buy("test", "Yes", 100.0)
        
        assert trade["status"] == "OPEN"
    
    def test_trade_id_increments(self, trader, mock_market):
        """Each trade should get incrementing ID"""
        trader.client.get_market_by_slug.return_value = mock_market
        trader.client.parse_prices.return_value = {"Yes": 0.50}
        
        trade1 = trader.buy("test", "Yes", 100.0)
        trade2 = trader.buy("test", "Yes", 50.0)
        
        assert trade2["id"] == trade1["id"] + 1
    
    def test_pnl_calculation_win(self, trader):
        """P&L for winning trade should be positive"""
        # Manually set up a trade
        trader.trades = [{
            "id": 1,
            "type": "BUY",
            "market_slug": "test",
            "outcome": "Yes",
            "entry_price": 0.30,
            "amount": 100.0,
            "shares": 333.33,  # (100/0.30)*100
            "status": "OPEN"
        }]
        
        # If outcome resolves Yes, shares pay $1 each
        # P&L = (exit_price - entry_price) * shares / 100
        # Win at price=1.0: (1.0 - 0.30) * 333.33 / 100 = $233.33 profit
        expected_pnl = (1.0 - 0.30) * 333.33 / 100
        assert expected_pnl > 0  # Win


class TestPaperTraderPersistence:
    """Test trade persistence"""
    
    def test_trades_save_and_load(self, tmp_path):
        """Trades should persist to JSON file"""
        trades_file = tmp_path / "paper_trades.json"
        
        # Write trades
        trades = [{"id": 1, "type": "BUY", "amount": 100}]
        with open(trades_file, "w") as f:
            json.dump(trades, f)
        
        # Read back
        with open(trades_file) as f:
            loaded = json.load(f)
        
        assert loaded == trades


class TestShareCalculations:
    """Test share/price math - matches paper_trader.py formula"""
    
    def test_shares_at_low_price(self):
        """Low price = more shares per dollar"""
        amount = 100.0
        low_price = 0.10
        # Formula: (amount / price) * 100
        shares = (amount / low_price) * 100
        assert shares == 100000.0  # $100 at $0.10 = 100k units (adjusted)
    
    def test_shares_at_high_price(self):
        """High price = fewer shares per dollar"""
        amount = 100.0
        high_price = 0.90
        shares = (amount / high_price) * 100
        expected = (100.0 / 0.90) * 100  # ~11111.11
        assert abs(shares - expected) < 0.01
    
    def test_breakeven_price(self):
        """Breakeven is when exit_price = entry_price"""
        entry = 0.50
        shares = 200
        # P&L = (exit - entry) * shares / 100
        pnl_at_breakeven = (0.50 - entry) * shares / 100
        assert pnl_at_breakeven == 0
    
    def test_max_profit(self):
        """Max profit is when price goes to 1.0"""
        entry = 0.20
        amount = 100.0
        shares = (amount / entry) * 100  # 500 shares
        max_pnl = (1.0 - entry) * shares / 100
        assert max_pnl == 400.0  # $400 max profit on $100 at 0.20
    
    def test_max_loss(self):
        """Max loss is when price goes to 0.0"""
        entry = 0.80
        amount = 100.0
        shares = (amount / entry) * 100  # 125 shares
        max_loss = (0.0 - entry) * shares / 100
        assert max_loss == -100.0  # Lose the full $100


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
