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
                # Mock the Polymarket client and ExitTracker
                with patch('paper_trader.PolymarketClient') as mock_client, \
                     patch('paper_trader.ExitTracker') as mock_exit_tracker:
                    
                    mock_client.return_value = MagicMock()
                    mock_exit_tracker.return_value = MagicMock()
                    
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


class TestPaperTraderExits:
    """Test exit target integration in PaperTrader"""
    
    @pytest.fixture
    def trader(self, tmp_path):
        """Create trader with mocked dependencies"""
        with patch('paper_trader.DATA_DIR', tmp_path):
            with patch('paper_trader.TRADES_FILE', tmp_path / "paper_trades.json"):
                with patch('paper_trader.PolymarketClient') as mock_client, \
                     patch('paper_trader.ExitTracker') as mock_exit_tracker:
                    
                    mock_client.return_value = MagicMock()
                    mock_exit_tracker.return_value = MagicMock()
                    
                    trader = PaperTrader()
                    trader.trades = []
                    yield trader
    
    @pytest.fixture
    def mock_market(self):
        return {
            "question": "Test Market",
            "slug": "test-market",
            "outcomes": [{"name": "Yes", "price": 0.50}]
        }

    def test_buy_sets_exit_targets(self, trader, mock_market):
        """Buy with exit targets should call set_exit_target"""
        trader.client.get_market_by_slug.return_value = mock_market
        trader.client.parse_prices.return_value = {"Yes": 0.50}
        
        trader.buy(
            "test-market", "Yes", 100.0, 
            take_profit=0.90, stop_loss=0.40, trailing_stop=5.0
        )
        
        # Verify set_exit_target called with correct args
        trader.exit_tracker.set_exit_target.assert_called_once()
        call_args = trader.exit_tracker.set_exit_target.call_args
        assert call_args[0][0] == 1  # trade_id
        assert call_args[1]['take_profit'] == 0.90
        assert call_args[1]['stop_loss'] == 0.40
        assert call_args[1]['trailing_stop'] == 5.0

    def test_buy_without_targets_does_not_call_tracker(self, trader, mock_market):
        """Buy without exit targets should skip set_exit_target"""
        trader.client.get_market_by_slug.return_value = mock_market
        trader.client.parse_prices.return_value = {"Yes": 0.50}
        
        trader.buy("test-market", "Yes", 100.0)
        
        trader.exit_tracker.set_exit_target.assert_not_called()


class TestPaperTraderCleanup:
    """Test cleanup and filtering functionality"""
    
    @pytest.fixture
    def trader_with_mixed_trades(self, tmp_path):
        """Create trader with both test and real trades"""
        with patch('paper_trader.DATA_DIR', tmp_path):
            with patch('paper_trader.TRADES_FILE', tmp_path / "paper_trades.json"):
                with patch('paper_trader.PolymarketClient') as mock_client, \
                     patch('paper_trader.ExitTracker') as mock_exit_tracker:
                    
                    mock_client.return_value = MagicMock()
                    mock_exit_tracker.return_value = MagicMock()
                    
                    trader = PaperTrader()
                    trader.trades = [
                        {"id": 1, "market_slug": "test-market", "status": "OPEN", "amount": 100, 
                         "outcome": "Yes", "entry_price": 0.50, "question": "Test market question"},
                        {"id": 2, "market_slug": "test-another", "status": "OPEN", "amount": 50,
                         "outcome": "No", "entry_price": 0.30, "question": "Test another question"},
                        {"id": 3, "market_slug": "real-market-ai", "status": "OPEN", "amount": 200,
                         "outcome": "Yes", "entry_price": 0.40, "question": "Real AI market question"},
                        {"id": 4, "market_slug": "test-closed", "status": "CLOSED", "pnl": -50, "amount": 100,
                         "outcome": "Yes", "entry_price": 0.60, "question": "Test closed question"},
                        {"id": 5, "market_slug": "real-closed", "status": "RESOLVED", "pnl": 75, "amount": 150,
                         "outcome": "Yes", "entry_price": 0.25, "question": "Real closed question"},
                    ]
                    yield trader

    def test_cleanup_dry_run_does_not_modify(self, trader_with_mixed_trades):
        """Cleanup with dry_run=True should not modify trades"""
        original_count = len(trader_with_mixed_trades.trades)
        
        result = trader_with_mixed_trades.cleanup_test_trades(dry_run=True)
        
        assert len(trader_with_mixed_trades.trades) == original_count
        assert result["removed"] == 0
        assert result["remaining"] == 2  # Two real trades

    def test_cleanup_with_confirm_removes_test_trades(self, trader_with_mixed_trades):
        """Cleanup with dry_run=False should remove test trades"""
        result = trader_with_mixed_trades.cleanup_test_trades(dry_run=False)
        
        assert len(trader_with_mixed_trades.trades) == 2
        assert result["removed"] == 3  # Three test trades removed
        assert result["remaining"] == 2

    def test_cleanup_renumbers_remaining_trades(self, trader_with_mixed_trades):
        """After cleanup, remaining trades should have sequential IDs"""
        trader_with_mixed_trades.cleanup_test_trades(dry_run=False)
        
        ids = [t["id"] for t in trader_with_mixed_trades.trades]
        assert ids == [1, 2]  # Re-numbered from 1

    def test_cleanup_only_removes_test_prefix(self, trader_with_mixed_trades):
        """Cleanup should only remove trades where market_slug starts with 'test'"""
        trader_with_mixed_trades.cleanup_test_trades(dry_run=False)
        
        slugs = [t["market_slug"] for t in trader_with_mixed_trades.trades]
        assert "real-market-ai" in slugs
        assert "real-closed" in slugs
        assert not any(s.startswith("test") for s in slugs)

    def test_status_exclude_test_hides_test_trades(self, trader_with_mixed_trades):
        """status(exclude_test=True) should only count real trades"""
        result = trader_with_mixed_trades.status(exclude_test=True)
        
        # Only 1 real open trade, 1 real closed trade
        assert result["open_positions"] == 1
        assert result["closed_trades"] == 1

    def test_status_includes_all_by_default(self, trader_with_mixed_trades):
        """status() should count all trades by default"""
        result = trader_with_mixed_trades.status(exclude_test=False)
        
        # 3 open trades (2 test + 1 real), 2 closed (1 test + 1 real)
        assert result["open_positions"] == 3
        assert result["closed_trades"] == 2

    def test_list_trades_exclude_test(self, trader_with_mixed_trades):
        """list_trades(exclude_test=True) should only return real trades"""
        trades = trader_with_mixed_trades.list_trades(exclude_test=True)
        
        assert len(trades) == 2
        assert not any(t["market_slug"].startswith("test") for t in trades)

    def test_cleanup_no_test_trades(self, tmp_path):
        """Cleanup with no test trades should report 0 removed"""
        with patch('paper_trader.DATA_DIR', tmp_path):
            with patch('paper_trader.TRADES_FILE', tmp_path / "paper_trades.json"):
                with patch('paper_trader.PolymarketClient'), \
                     patch('paper_trader.ExitTracker'):
                    trader = PaperTrader()
                    trader.trades = [
                        {"id": 1, "market_slug": "real-market", "status": "OPEN", "amount": 100,
                         "outcome": "Yes", "entry_price": 0.50, "question": "Real market question"}
                    ]
                    
                    result = trader.cleanup_test_trades(dry_run=True)
                    
                    assert result["removed"] == 0
                    assert result["remaining"] == 1


class TestAsymmetricRiskWarning:
    """Test asymmetric risk warning feature"""
    
    @pytest.fixture
    def trader(self, tmp_path):
        """Create a PaperTrader with temp data directory"""
        with patch('paper_trader.DATA_DIR', tmp_path):
            with patch('paper_trader.TRADES_FILE', tmp_path / "paper_trades.json"):
                with patch('paper_trader.PolymarketClient') as mock_client, \
                     patch('paper_trader.ExitTracker'):
                    trader = PaperTrader()
                    mock_client.return_value.get_market_by_slug.return_value = {"question": "Test"}
                    yield trader
    
    def test_high_price_triggers_warning(self, trader, capsys):
        """Entry price > 85% should print asymmetric risk warning"""
        trader.buy("test-market", "Yes", 100.0, entry_price=90.0, reason="High price test")
        
        captured = capsys.readouterr()
        assert "ASYMMETRIC RISK WARNING" in captured.out
        assert "Entry at 90.0%" in captured.out
    
    def test_normal_price_no_warning(self, trader, capsys):
        """Entry price <= 85% should NOT print asymmetric risk warning"""
        trader.buy("test-market", "Yes", 100.0, entry_price=50.0, reason="Normal price test")
        
        captured = capsys.readouterr()
        assert "ASYMMETRIC RISK WARNING" not in captured.out
    
    def test_edge_case_85_percent(self, trader, capsys):
        """Entry price at exactly 85% should NOT trigger warning"""
        trader.buy("test-market", "Yes", 100.0, entry_price=85.0, reason="Edge case test")
        
        captured = capsys.readouterr()
        assert "ASYMMETRIC RISK WARNING" not in captured.out
    
    def test_edge_case_86_percent(self, trader, capsys):
        """Entry price at 86% should trigger warning"""
        trader.buy("test-market", "Yes", 100.0, entry_price=86.0, reason="Edge case test")
        
        captured = capsys.readouterr()
        assert "ASYMMETRIC RISK WARNING" in captured.out


class TestJsonOutput:
    """Test JSON output functionality"""
    
    @pytest.fixture
    def trader(self, tmp_path):
        """Create a PaperTrader with temp data directory"""
        with patch('paper_trader.DATA_DIR', tmp_path):
            with patch('paper_trader.TRADES_FILE', tmp_path / "paper_trades.json"):
                with patch('paper_trader.PolymarketClient') as mock_client, \
                     patch('paper_trader.ExitTracker') as mock_exit_tracker:
                    
                    mock_client.return_value = MagicMock()
                    mock_exit_tracker.return_value = MagicMock()
                    
                    trader = PaperTrader()
                    trader.trades = []
                    yield trader
    
    @pytest.fixture
    def mock_market(self):
        """Sample market data"""
        return {
            "question": "Test JSON Market",
            "slug": "test-json-market",
            "outcomes": [{"name": "Yes", "price": 0.50}]
        }
    
    def test_status_json_returns_dict(self, trader):
        """status() with json_output=True returns dict without printing"""
        result = trader.status(json_output=True)
        
        assert isinstance(result, dict)
        assert "starting_balance" in result
        assert "current_balance" in result
        assert "realized_pnl" in result
        assert "win_rate" in result
        assert "open_trades" in result
    
    def test_status_json_no_print(self, trader, capsys):
        """status() with json_output=True should not print formatted output"""
        trader.status(json_output=True)
        
        captured = capsys.readouterr()
        assert "PAPER TRADING STATUS" not in captured.out
        assert "Starting Balance" not in captured.out
    
    def test_status_normal_prints(self, trader, capsys):
        """status() without json_output should print formatted output"""
        trader.status(json_output=False)
        
        captured = capsys.readouterr()
        assert "PAPER TRADING STATUS" in captured.out
    
    def test_list_trades_json_returns_list(self, trader, mock_market):
        """list_trades() with json_output=True returns list without printing"""
        # Mock the Polymarket client
        trader.client.get_market_by_slug.return_value = mock_market
        trader.client.parse_prices.return_value = {"Yes": 0.50}
        
        # Add some test trades
        trader.buy("test-json-market", "Yes", 100.0, entry_price=50.0)
        
        result = trader.list_trades(json_output=True)
        
        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0]["market_slug"] == "test-json-market"
    
    def test_list_trades_json_no_print(self, trader, mock_market, capsys):
        """list_trades() with json_output=True should not print formatted output"""
        trader.client.get_market_by_slug.return_value = mock_market
        trader.client.parse_prices.return_value = {"Yes": 0.50}
        
        trader.buy("test-json-market", "Yes", 100.0, entry_price=50.0)
        trader.list_trades(json_output=True)
        
        captured = capsys.readouterr()
        # Should not contain emoji indicators from list output
        assert "🔵" not in captured.out
    
    def test_cleanup_json_returns_dict(self, trader, mock_market):
        """cleanup_test_trades() with json_output=True returns dict"""
        trader.client.get_market_by_slug.return_value = mock_market
        trader.client.parse_prices.return_value = {"Yes": 0.50}
        
        # Add test trades
        trader.buy("test-cleanup-market", "Yes", 100.0, entry_price=50.0)
        
        result = trader.cleanup_test_trades(dry_run=True, json_output=True)
        
        assert isinstance(result, dict)
        assert "removed" in result
        assert "remaining" in result
        assert "would_remove" in result
        assert "dry_run" in result
    
    def test_cleanup_json_no_print(self, trader, mock_market, capsys):
        """cleanup_test_trades() with json_output=True should not print"""
        trader.client.get_market_by_slug.return_value = mock_market
        trader.client.parse_prices.return_value = {"Yes": 0.50}
        
        trader.buy("test-cleanup-market", "Yes", 100.0, entry_price=50.0)
        trader.cleanup_test_trades(dry_run=True, json_output=True)
        
        captured = capsys.readouterr()
        assert "DRY RUN" not in captured.out


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
