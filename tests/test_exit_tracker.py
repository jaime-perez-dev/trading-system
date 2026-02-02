#!/usr/bin/env python3
"""Unit tests for ExitTracker."""

import json
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from alerts.exit_tracker import ExitTracker


@pytest.fixture
def temp_data_dir():
    """Create temporary data directory for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def tracker(temp_data_dir):
    """Create ExitTracker with mocked paths."""
    with patch.object(ExitTracker, '__init__', lambda self, notify=True: None):
        t = ExitTracker()
        t.polymarket = MagicMock()
        t.notifier = MagicMock()
        t.data_dir = temp_data_dir
        t.targets_file = temp_data_dir / "exit_targets.json"
        t.trades_file = temp_data_dir / "paper_trades.json"
        return t


class TestLoadPositions:
    """Tests for load_positions."""
    
    def test_no_file_returns_empty(self, tracker):
        """Return empty list when trades file doesn't exist."""
        result = tracker.load_positions()
        assert result == []
    
    def test_loads_open_positions_only(self, tracker):
        """Only return positions with status OPEN."""
        trades = [
            {"id": 1, "status": "OPEN", "market_slug": "test-1"},
            {"id": 2, "status": "CLOSED", "market_slug": "test-2"},
            {"id": 3, "status": "OPEN", "market_slug": "test-3"},
        ]
        with open(tracker.trades_file, "w") as f:
            json.dump(trades, f)
        
        result = tracker.load_positions()
        assert len(result) == 2
        assert result[0]["id"] == 1
        assert result[1]["id"] == 3
    
    def test_filters_by_status(self, tracker):
        """Filter out positions without OPEN status."""
        trades = [
            {"id": 1, "status": "PENDING"},
            {"id": 2, "status": "CLOSED"},
            {"id": 3},  # No status
        ]
        with open(tracker.trades_file, "w") as f:
            json.dump(trades, f)
        
        result = tracker.load_positions()
        assert result == []


class TestLoadAndSaveTargets:
    """Tests for load_targets and save_targets."""
    
    def test_no_file_returns_empty_dict(self, tracker):
        """Return empty dict when targets file doesn't exist."""
        result = tracker.load_targets()
        assert result == {}
    
    def test_loads_existing_targets(self, tracker):
        """Load targets from file."""
        targets = {
            "1": {"take_profit": 95.0, "stop_loss": 80.0},
            "2": {"trailing_stop": 5.0, "peak_price": 90.0}
        }
        with open(tracker.targets_file, "w") as f:
            json.dump(targets, f)
        
        result = tracker.load_targets()
        assert result["1"]["take_profit"] == 95.0
        assert result["2"]["trailing_stop"] == 5.0
    
    def test_save_and_reload(self, tracker):
        """Save targets and reload them."""
        targets = {
            "42": {"take_profit": 98.0, "stop_loss": 85.0, "trailing_stop": None}
        }
        tracker.save_targets(targets)
        
        result = tracker.load_targets()
        assert result == targets


class TestSetExitTarget:
    """Tests for set_exit_target."""
    
    def test_sets_take_profit(self, tracker, capsys):
        """Set take profit target."""
        tracker.set_exit_target(1, take_profit=95.0)
        
        targets = tracker.load_targets()
        assert "1" in targets
        assert targets["1"]["take_profit"] == 95.0
        assert targets["1"]["stop_loss"] is None
        assert targets["1"]["trailing_stop"] is None
        assert "set_at" in targets["1"]
        
        captured = capsys.readouterr()
        assert "Exit targets set" in captured.out
        assert "95.0%" in captured.out
    
    def test_sets_stop_loss(self, tracker, capsys):
        """Set stop loss target."""
        tracker.set_exit_target(2, stop_loss=80.0)
        
        targets = tracker.load_targets()
        assert targets["2"]["stop_loss"] == 80.0
        
        captured = capsys.readouterr()
        assert "80.0%" in captured.out
    
    def test_sets_trailing_stop(self, tracker, capsys):
        """Set trailing stop target."""
        tracker.set_exit_target(3, trailing_stop=5.0)
        
        targets = tracker.load_targets()
        assert targets["3"]["trailing_stop"] == 5.0
        assert targets["3"]["peak_price"] is None  # Peak set on first check
        
        captured = capsys.readouterr()
        assert "5.0pp" in captured.out
    
    def test_sets_multiple_targets(self, tracker):
        """Set all target types at once."""
        tracker.set_exit_target(4, take_profit=98.0, stop_loss=85.0, trailing_stop=3.0)
        
        targets = tracker.load_targets()
        assert targets["4"]["take_profit"] == 98.0
        assert targets["4"]["stop_loss"] == 85.0
        assert targets["4"]["trailing_stop"] == 3.0
    
    def test_overwrites_existing_target(self, tracker):
        """Overwrite existing target for same position."""
        tracker.set_exit_target(5, take_profit=90.0)
        tracker.set_exit_target(5, take_profit=95.0, stop_loss=80.0)
        
        targets = tracker.load_targets()
        assert targets["5"]["take_profit"] == 95.0
        assert targets["5"]["stop_loss"] == 80.0


class TestGetCurrentPrice:
    """Tests for get_current_price."""
    
    def test_fetches_price_success(self, tracker):
        """Fetch and parse price from API."""
        mock_response = MagicMock()
        mock_response.ok = True
        mock_response.json.return_value = [{"outcomePrices": "[0.85, 0.15]"}]
        
        with patch("requests.get", return_value=mock_response):
            price = tracker.get_current_price("test-market")
        
        assert price == 85.0
    
    def test_handles_list_prices(self, tracker):
        """Handle outcomePrices as list instead of string."""
        mock_response = MagicMock()
        mock_response.ok = True
        mock_response.json.return_value = [{"outcomePrices": [0.72, 0.28]}]
        
        with patch("requests.get", return_value=mock_response):
            price = tracker.get_current_price("test-market")
        
        assert price == 72.0
    
    def test_returns_none_on_error(self, tracker):
        """Return None when API fails."""
        with patch("requests.get", side_effect=Exception("Network error")):
            price = tracker.get_current_price("test-market")
        
        assert price is None
    
    def test_returns_none_on_empty_response(self, tracker):
        """Return None when API returns empty data."""
        mock_response = MagicMock()
        mock_response.ok = True
        mock_response.json.return_value = []
        
        with patch("requests.get", return_value=mock_response):
            price = tracker.get_current_price("test-market")
        
        assert price is None
    
    def test_returns_none_on_bad_response(self, tracker):
        """Return None when response is not ok."""
        mock_response = MagicMock()
        mock_response.ok = False
        
        with patch("requests.get", return_value=mock_response):
            price = tracker.get_current_price("test-market")
        
        assert price is None


class TestCheckExits:
    """Tests for check_exits."""
    
    def test_no_positions(self, tracker, capsys):
        """Handle no open positions."""
        result = tracker.check_exits()
        
        assert result == []
        captured = capsys.readouterr()
        assert "No open positions" in captured.out
    
    def test_take_profit_triggered(self, tracker):
        """Trigger take profit when price exceeds target."""
        # Setup position
        trades = [{
            "id": 1,
            "status": "OPEN",
            "market_slug": "test-market",
            "question": "Test Question",
            "entry_price": 80.0,
            "amount": 100,
            "shares": 125,
            "outcome": "Yes"
        }]
        with open(tracker.trades_file, "w") as f:
            json.dump(trades, f)
        
        # Setup target
        tracker.set_exit_target(1, take_profit=95.0)
        
        # Mock price at 96% (above TP)
        with patch.object(tracker, "get_current_price", return_value=96.0):
            triggered = tracker.check_exits()
        
        assert len(triggered) == 1
        assert triggered[0]["type"] == "take_profit"
        assert triggered[0]["current_price"] == 96.0
        assert triggered[0]["trigger_price"] == 95.0
    
    def test_stop_loss_triggered(self, tracker):
        """Trigger stop loss when price falls below target."""
        trades = [{
            "id": 2,
            "status": "OPEN",
            "market_slug": "test-market",
            "question": "Test Question",
            "entry_price": 80.0,
            "amount": 100,
            "shares": 125,
            "outcome": "Yes"
        }]
        with open(tracker.trades_file, "w") as f:
            json.dump(trades, f)
        
        tracker.set_exit_target(2, stop_loss=70.0)
        
        with patch.object(tracker, "get_current_price", return_value=65.0):
            triggered = tracker.check_exits()
        
        assert len(triggered) == 1
        assert triggered[0]["type"] == "stop_loss"
        assert triggered[0]["current_price"] == 65.0
    
    def test_trailing_stop_updates_peak(self, tracker):
        """Update peak price for trailing stop."""
        trades = [{
            "id": 3,
            "status": "OPEN",
            "market_slug": "test-market",
            "question": "Test Question",
            "entry_price": 80.0,
            "amount": 100,
            "shares": 125,
            "outcome": "Yes"
        }]
        with open(tracker.trades_file, "w") as f:
            json.dump(trades, f)
        
        tracker.set_exit_target(3, trailing_stop=5.0)
        
        # Price at 90 - should set peak
        with patch.object(tracker, "get_current_price", return_value=90.0):
            triggered = tracker.check_exits()
        
        targets = tracker.load_targets()
        assert targets["3"]["peak_price"] == 90.0
        assert len(triggered) == 0  # Not triggered yet
    
    def test_trailing_stop_triggered(self, tracker):
        """Trigger trailing stop when price drops below peak - distance."""
        trades = [{
            "id": 4,
            "status": "OPEN",
            "market_slug": "test-market",
            "question": "Test Question",
            "entry_price": 80.0,
            "amount": 100,
            "shares": 125,
            "outcome": "Yes"
        }]
        with open(tracker.trades_file, "w") as f:
            json.dump(trades, f)
        
        # Set trailing stop with peak already at 95
        targets = {
            "4": {
                "take_profit": None,
                "stop_loss": None,
                "trailing_stop": 5.0,
                "peak_price": 95.0,
                "set_at": "2026-02-01T00:00:00Z"
            }
        }
        tracker.save_targets(targets)
        
        # Price drops to 89 (below 95-5=90)
        with patch.object(tracker, "get_current_price", return_value=89.0):
            triggered = tracker.check_exits()
        
        assert len(triggered) == 1
        assert triggered[0]["type"] == "trailing_stop"
        assert triggered[0]["trigger_price"] == 90.0
    
    def test_no_trigger_within_targets(self, tracker):
        """No trigger when price is within bounds."""
        trades = [{
            "id": 5,
            "status": "OPEN",
            "market_slug": "test-market",
            "question": "Test Question",
            "entry_price": 80.0,
            "amount": 100,
            "shares": 125,
            "outcome": "Yes"
        }]
        with open(tracker.trades_file, "w") as f:
            json.dump(trades, f)
        
        tracker.set_exit_target(5, take_profit=95.0, stop_loss=70.0)
        
        # Price at 85 - within bounds
        with patch.object(tracker, "get_current_price", return_value=85.0):
            triggered = tracker.check_exits()
        
        assert len(triggered) == 0
    
    def test_handles_price_fetch_failure(self, tracker, capsys):
        """Continue checking when price fetch fails for one position."""
        trades = [
            {"id": 6, "status": "OPEN", "market_slug": "fail-market", "question": "Fail"},
            {"id": 7, "status": "OPEN", "market_slug": "ok-market", "question": "OK",
             "entry_price": 80.0, "amount": 100, "shares": 125, "outcome": "Yes"},
        ]
        with open(tracker.trades_file, "w") as f:
            json.dump(trades, f)
        
        def mock_price(slug):
            if slug == "fail-market":
                return None
            return 85.0
        
        with patch.object(tracker, "get_current_price", side_effect=mock_price):
            tracker.check_exits()
        
        captured = capsys.readouterr()
        assert "Could not fetch" in captured.out
    
    def test_pnl_calculation_yes_outcome(self, tracker):
        """Calculate P&L for Yes outcome correctly."""
        trades = [{
            "id": 8,
            "status": "OPEN",
            "market_slug": "test",
            "question": "Test",
            "entry_price": 50.0,  # Bought at 50%
            "amount": 100,
            "shares": 200,  # $100 / 0.50 = 200 shares
            "outcome": "Yes"
        }]
        with open(tracker.trades_file, "w") as f:
            json.dump(trades, f)
        
        tracker.set_exit_target(8, take_profit=80.0)
        
        # Price went to 80% - P&L should be (80-50)*200/100 = $60
        with patch.object(tracker, "get_current_price", return_value=80.0):
            triggered = tracker.check_exits()
        
        assert triggered[0]["pnl"] == 60.0
    
    def test_pnl_calculation_no_outcome(self, tracker):
        """Calculate P&L for No outcome (inverted)."""
        trades = [{
            "id": 9,
            "status": "OPEN",
            "market_slug": "test",
            "question": "Test",
            "entry_price": 50.0,  # No at 50% (Yes at 50%)
            "amount": 100,
            "shares": 200,
            "outcome": "No"
        }]
        with open(tracker.trades_file, "w") as f:
            json.dump(trades, f)
        
        tracker.set_exit_target(9, take_profit=30.0)  # Profit if Yes drops
        
        # Yes price dropped to 30% - our No went up
        # P&L = (entry - current) * shares / 100 = (50-30)*200/100 = $40
        with patch.object(tracker, "get_current_price", return_value=30.0):
            triggered = tracker.check_exits()
        
        assert triggered[0]["pnl"] == 40.0


class TestSendExitAlert:
    """Tests for _send_exit_alert."""
    
    def test_sends_take_profit_alert(self, tracker):
        """Send formatted take profit alert."""
        position = {
            "id": 1,
            "question": "Test Market Question",
            "outcome": "Yes",
            "entry_price": 80.0,
            "amount": 100
        }
        
        tracker._send_exit_alert(position, 96.0, "take_profit", 95.0)
        
        tracker.notifier.send_message.assert_called_once()
        message = tracker.notifier.send_message.call_args[0][0]
        assert "TAKE PROFIT" in message
        assert "🎉" in message
        assert "Test Market Question" in message
    
    def test_sends_stop_loss_alert(self, tracker):
        """Send formatted stop loss alert."""
        position = {"id": 2, "question": "Test", "outcome": "Yes", "entry_price": 80.0, "amount": 100}
        
        tracker._send_exit_alert(position, 65.0, "stop_loss", 70.0)
        
        message = tracker.notifier.send_message.call_args[0][0]
        assert "STOP LOSS" in message
        assert "🛑" in message
    
    def test_sends_trailing_stop_alert(self, tracker):
        """Send formatted trailing stop alert."""
        position = {"id": 3, "question": "Test", "outcome": "Yes", "entry_price": 80.0, "amount": 100}
        
        tracker._send_exit_alert(position, 89.0, "trailing_stop", 90.0)
        
        message = tracker.notifier.send_message.call_args[0][0]
        assert "TRAILING STOP" in message
        assert "📉" in message
    
    def test_no_alert_when_notifier_disabled(self, tracker):
        """Don't crash when notifier is None."""
        tracker.notifier = None
        position = {"id": 4, "question": "Test", "outcome": "Yes", "entry_price": 80.0, "amount": 100}
        
        # Should not raise
        tracker._send_exit_alert(position, 96.0, "take_profit", 95.0)


class TestPortfolioSummary:
    """Tests for portfolio_summary."""
    
    def test_empty_portfolio(self, tracker):
        """Handle empty portfolio."""
        summary = tracker.portfolio_summary()
        
        assert summary["positions"] == []
        assert summary["total_invested"] == 0
        assert summary["total_unrealized_pnl"] == 0
        assert "timestamp" in summary
    
    def test_calculates_unrealized_pnl(self, tracker):
        """Calculate unrealized P&L for all positions."""
        trades = [
            {
                "id": 1,
                "status": "OPEN",
                "market_slug": "market-1",
                "question": "Question 1",
                "entry_price": 50.0,
                "amount": 100,
                "shares": 200,
                "outcome": "Yes"
            },
            {
                "id": 2,
                "status": "OPEN",
                "market_slug": "market-2",
                "question": "Question 2",
                "entry_price": 40.0,
                "amount": 50,
                "shares": 125,
                "outcome": "Yes"
            }
        ]
        with open(tracker.trades_file, "w") as f:
            json.dump(trades, f)
        
        def mock_price(slug):
            return {"market-1": 70.0, "market-2": 60.0}.get(slug)
        
        with patch.object(tracker, "get_current_price", side_effect=mock_price):
            summary = tracker.portfolio_summary()
        
        assert len(summary["positions"]) == 2
        assert summary["total_invested"] == 150
        
        # Position 1: (70-50)*200/100 = $40
        # Position 2: (60-40)*125/100 = $25
        assert summary["total_unrealized_pnl"] == 65.0
    
    def test_uses_entry_price_on_fetch_failure(self, tracker):
        """Use entry price when current price fetch fails."""
        trades = [{
            "id": 1,
            "status": "OPEN",
            "market_slug": "test",
            "question": "Test",
            "entry_price": 80.0,
            "amount": 100,
            "shares": 125,
            "outcome": "Yes"
        }]
        with open(tracker.trades_file, "w") as f:
            json.dump(trades, f)
        
        with patch.object(tracker, "get_current_price", return_value=None):
            summary = tracker.portfolio_summary()
        
        assert summary["positions"][0]["current"] == 80.0
        assert summary["positions"][0]["pnl"] == 0
    
    def test_includes_pnl_percentage(self, tracker):
        """Include P&L percentage in summary."""
        trades = [{
            "id": 1,
            "status": "OPEN",
            "market_slug": "test",
            "question": "Test",
            "entry_price": 50.0,
            "amount": 100,
            "shares": 200,
            "outcome": "Yes"
        }]
        with open(tracker.trades_file, "w") as f:
            json.dump(trades, f)
        
        with patch.object(tracker, "get_current_price", return_value=75.0):
            summary = tracker.portfolio_summary()
        
        # P&L = (75-50)*200/100 = $50, which is 50% of $100 invested
        assert summary["positions"][0]["pnl_pct"] == 50.0
