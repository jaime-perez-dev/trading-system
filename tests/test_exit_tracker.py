"""
Unit tests for alerts/exit_tracker.py
Tests position tracking, exit targets, and P&L calculations.
"""
import json
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from alerts.exit_tracker import ExitTracker


@pytest.fixture
def temp_data_dir(tmp_path):
    """Create a temporary data directory for tests."""
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    return data_dir


@pytest.fixture
def tracker(temp_data_dir, monkeypatch):
    """Create ExitTracker with mocked paths and disabled notifications."""
    with patch('alerts.exit_tracker.TelegramNotifier'):
        tracker = ExitTracker(notify=False)
        tracker.data_dir = temp_data_dir
        tracker.targets_file = temp_data_dir / "exit_targets.json"
        tracker.trades_file = temp_data_dir / "paper_trades.json"
        return tracker


class TestLoadPositions:
    """Tests for load_positions method."""
    
    def test_returns_empty_list_when_no_file(self, tracker):
        """Should return empty list when trades file doesn't exist."""
        result = tracker.load_positions()
        assert result == []
    
    def test_returns_only_open_positions(self, tracker):
        """Should filter to only OPEN positions."""
        trades = [
            {"id": 1, "status": "OPEN", "market_slug": "test-1"},
            {"id": 2, "status": "CLOSED", "market_slug": "test-2"},
            {"id": 3, "status": "OPEN", "market_slug": "test-3"},
        ]
        tracker.trades_file.write_text(json.dumps(trades))
        
        result = tracker.load_positions()
        assert len(result) == 2
        assert all(p["status"] == "OPEN" for p in result)


class TestLoadSaveTargets:
    """Tests for load_targets and save_targets methods."""
    
    def test_returns_empty_dict_when_no_file(self, tracker):
        """Should return empty dict when targets file doesn't exist."""
        result = tracker.load_targets()
        assert result == {}
    
    def test_loads_existing_targets(self, tracker):
        """Should load targets from existing file."""
        targets = {
            "1": {"take_profit": 95.0, "stop_loss": 85.0},
            "2": {"take_profit": 90.0}
        }
        tracker.targets_file.write_text(json.dumps(targets))
        
        result = tracker.load_targets()
        assert result == targets
    
    def test_saves_targets_to_file(self, tracker):
        """Should write targets to JSON file."""
        targets = {"1": {"take_profit": 98.0, "stop_loss": 80.0}}
        tracker.save_targets(targets)
        
        assert tracker.targets_file.exists()
        saved = json.loads(tracker.targets_file.read_text())
        assert saved == targets


class TestSetExitTarget:
    """Tests for set_exit_target method."""
    
    def test_sets_take_profit_target(self, tracker, capsys):
        """Should set take profit target."""
        tracker.set_exit_target(1, take_profit=95.0)
        
        targets = tracker.load_targets()
        assert "1" in targets
        assert targets["1"]["take_profit"] == 95.0
        assert targets["1"]["stop_loss"] is None
        
        captured = capsys.readouterr()
        assert "Take profit: 95.0%" in captured.out
    
    def test_sets_stop_loss_target(self, tracker, capsys):
        """Should set stop loss target."""
        tracker.set_exit_target(2, stop_loss=80.0)
        
        targets = tracker.load_targets()
        assert targets["2"]["stop_loss"] == 80.0
        
        captured = capsys.readouterr()
        assert "Stop loss: 80.0%" in captured.out
    
    def test_sets_trailing_stop(self, tracker, capsys):
        """Should set trailing stop."""
        tracker.set_exit_target(3, trailing_stop=5.0)
        
        targets = tracker.load_targets()
        assert targets["3"]["trailing_stop"] == 5.0
        assert targets["3"]["peak_price"] is None
        
        captured = capsys.readouterr()
        assert "Trailing stop: 5.0pp" in captured.out
    
    def test_sets_multiple_targets(self, tracker):
        """Should set all targets at once."""
        tracker.set_exit_target(4, take_profit=98.0, stop_loss=85.0, trailing_stop=3.0)
        
        targets = tracker.load_targets()
        assert targets["4"]["take_profit"] == 98.0
        assert targets["4"]["stop_loss"] == 85.0
        assert targets["4"]["trailing_stop"] == 3.0
    
    def test_includes_timestamp(self, tracker):
        """Should include set_at timestamp."""
        tracker.set_exit_target(5, take_profit=90.0)
        
        targets = tracker.load_targets()
        assert "set_at" in targets["5"]
        # Should be valid ISO format
        datetime.fromisoformat(targets["5"]["set_at"].replace("Z", "+00:00"))


class TestGetCurrentPrice:
    """Tests for get_current_price method."""
    
    def test_returns_price_on_success(self, tracker):
        """Should return price from API response."""
        mock_response = MagicMock()
        mock_response.ok = True
        mock_response.json.return_value = [{"outcomePrices": "[0.75, 0.25]"}]
        
        with patch('requests.get', return_value=mock_response):
            price = tracker.get_current_price("test-market")
        
        assert price == 75.0
    
    def test_handles_list_format_prices(self, tracker):
        """Should handle prices as list instead of JSON string."""
        mock_response = MagicMock()
        mock_response.ok = True
        mock_response.json.return_value = [{"outcomePrices": [0.82, 0.18]}]
        
        with patch('requests.get', return_value=mock_response):
            price = tracker.get_current_price("test-market")
        
        assert price == 82.0
    
    def test_returns_none_on_error(self, tracker):
        """Should return None on API error."""
        with patch('requests.get', side_effect=Exception("Network error")):
            price = tracker.get_current_price("test-market")
        
        assert price is None
    
    def test_returns_none_on_empty_response(self, tracker):
        """Should return None when no data returned."""
        mock_response = MagicMock()
        mock_response.ok = True
        mock_response.json.return_value = []
        
        with patch('requests.get', return_value=mock_response):
            price = tracker.get_current_price("test-market")
        
        assert price is None


class TestCheckExits:
    """Tests for check_exits method."""
    
    def test_returns_empty_when_no_positions(self, tracker, capsys):
        """Should return empty list when no positions."""
        result = tracker.check_exits()
        
        assert result == []
        captured = capsys.readouterr()
        assert "No open positions" in captured.out
    
    def test_detects_take_profit_trigger(self, tracker):
        """Should detect when take profit is hit."""
        # Setup position
        trades = [{
            "id": 1,
            "status": "OPEN",
            "market_slug": "test-market",
            "question": "Test Question?",
            "entry_price": 60.0,
            "amount": 100,
            "shares": 166.67,
            "outcome": "Yes"
        }]
        tracker.trades_file.write_text(json.dumps(trades))
        
        # Setup target
        tracker.set_exit_target(1, take_profit=80.0)
        
        # Mock price above take profit
        with patch.object(tracker, 'get_current_price', return_value=85.0):
            triggered = tracker.check_exits()
        
        assert len(triggered) == 1
        assert triggered[0]["type"] == "take_profit"
        assert triggered[0]["current_price"] == 85.0
    
    def test_detects_stop_loss_trigger(self, tracker):
        """Should detect when stop loss is hit."""
        trades = [{
            "id": 1,
            "status": "OPEN",
            "market_slug": "test-market",
            "question": "Test?",
            "entry_price": 70.0,
            "amount": 100,
            "shares": 142.86,
            "outcome": "Yes"
        }]
        tracker.trades_file.write_text(json.dumps(trades))
        
        tracker.set_exit_target(1, stop_loss=65.0)
        
        # Mock price below stop loss
        with patch.object(tracker, 'get_current_price', return_value=60.0):
            triggered = tracker.check_exits()
        
        assert len(triggered) == 1
        assert triggered[0]["type"] == "stop_loss"
    
    def test_detects_trailing_stop_trigger(self, tracker):
        """Should detect trailing stop when price drops from peak."""
        trades = [{
            "id": 1,
            "status": "OPEN",
            "market_slug": "test-market",
            "question": "Test?",
            "entry_price": 50.0,
            "amount": 100,
            "shares": 200,
            "outcome": "Yes"
        }]
        tracker.trades_file.write_text(json.dumps(trades))
        
        # Set trailing stop with existing peak
        targets = {
            "1": {
                "take_profit": None,
                "stop_loss": None,
                "trailing_stop": 10.0,
                "peak_price": 80.0,
                "set_at": datetime.now(timezone.utc).isoformat()
            }
        }
        tracker.save_targets(targets)
        
        # Price drops more than 10pp from peak (80 - 10 = 70, current is 65)
        with patch.object(tracker, 'get_current_price', return_value=65.0):
            triggered = tracker.check_exits()
        
        assert len(triggered) == 1
        assert triggered[0]["type"] == "trailing_stop"
    
    def test_updates_peak_price_for_trailing_stop(self, tracker):
        """Should update peak price when current exceeds it."""
        trades = [{
            "id": 1,
            "status": "OPEN",
            "market_slug": "test-market",
            "question": "Test?",
            "entry_price": 50.0,
            "amount": 100,
            "shares": 200,
            "outcome": "Yes"
        }]
        tracker.trades_file.write_text(json.dumps(trades))
        
        tracker.set_exit_target(1, trailing_stop=5.0)
        
        # Price goes up
        with patch.object(tracker, 'get_current_price', return_value=75.0):
            tracker.check_exits()
        
        targets = tracker.load_targets()
        assert targets["1"]["peak_price"] == 75.0
    
    def test_calculates_pnl_correctly(self, tracker, capsys):
        """Should calculate P&L correctly for Yes positions."""
        trades = [{
            "id": 1,
            "status": "OPEN",
            "market_slug": "test-market",
            "question": "Test?",
            "entry_price": 50.0,
            "amount": 100,
            "shares": 200,  # $100 / 0.50 = 200 shares
            "outcome": "Yes"
        }]
        tracker.trades_file.write_text(json.dumps(trades))
        
        # Price goes to 75% = +25pp * 200 shares / 100 = $50 profit
        with patch.object(tracker, 'get_current_price', return_value=75.0):
            tracker.check_exits()
        
        captured = capsys.readouterr()
        assert "+50.00" in captured.out or "+$50" in captured.out


class TestSendExitAlert:
    """Tests for _send_exit_alert method."""
    
    def test_does_not_send_when_notify_disabled(self, tracker):
        """Should not send when notifier is None."""
        position = {"id": 1, "question": "Test?", "outcome": "Yes", "entry_price": 50, "amount": 100}
        
        # Should not raise
        tracker._send_exit_alert(position, 80.0, "take_profit", 75.0)
    
    def test_sends_alert_when_notify_enabled(self, temp_data_dir):
        """Should send notification when enabled."""
        mock_notifier = MagicMock()
        
        with patch('alerts.exit_tracker.TelegramNotifier', return_value=mock_notifier):
            tracker = ExitTracker(notify=True)
            tracker.data_dir = temp_data_dir
            tracker.targets_file = temp_data_dir / "exit_targets.json"
            tracker.trades_file = temp_data_dir / "paper_trades.json"
            
            position = {"id": 1, "question": "Test?", "outcome": "Yes", "entry_price": 50, "amount": 100}
            tracker._send_exit_alert(position, 80.0, "take_profit", 75.0)
        
        mock_notifier.send_message.assert_called_once()
        call_args = mock_notifier.send_message.call_args[0][0]
        assert "TAKE PROFIT" in call_args


class TestPortfolioSummary:
    """Tests for portfolio_summary method."""
    
    def test_returns_empty_when_no_positions(self, tracker):
        """Should return empty positions list."""
        summary = tracker.portfolio_summary()
        
        assert summary["positions"] == []
        assert summary["total_invested"] == 0
        assert summary["total_unrealized_pnl"] == 0
    
    def test_calculates_portfolio_totals(self, tracker):
        """Should calculate total invested and P&L."""
        trades = [
            {
                "id": 1,
                "status": "OPEN",
                "market_slug": "market-1",
                "question": "Q1?",
                "entry_price": 50.0,
                "amount": 100,
                "shares": 200,
                "outcome": "Yes"
            },
            {
                "id": 2,
                "status": "OPEN",
                "market_slug": "market-2",
                "question": "Q2?",
                "entry_price": 60.0,
                "amount": 150,
                "shares": 250,
                "outcome": "Yes"
            }
        ]
        tracker.trades_file.write_text(json.dumps(trades))
        
        # Market 1: 50 -> 70 = +20pp * 200 / 100 = +$40
        # Market 2: 60 -> 55 = -5pp * 250 / 100 = -$12.50
        def mock_price(slug):
            return {"market-1": 70.0, "market-2": 55.0}.get(slug, 50.0)
        
        with patch.object(tracker, 'get_current_price', side_effect=mock_price):
            summary = tracker.portfolio_summary()
        
        assert summary["total_invested"] == 250
        assert abs(summary["total_unrealized_pnl"] - 27.5) < 0.01  # 40 - 12.5 = 27.5
    
    def test_includes_position_details(self, tracker):
        """Should include individual position details."""
        trades = [{
            "id": 1,
            "status": "OPEN",
            "market_slug": "test",
            "question": "Test Question?",
            "entry_price": 40.0,
            "amount": 100,
            "shares": 250,
            "outcome": "Yes"
        }]
        tracker.trades_file.write_text(json.dumps(trades))
        
        with patch.object(tracker, 'get_current_price', return_value=60.0):
            summary = tracker.portfolio_summary()
        
        assert len(summary["positions"]) == 1
        pos = summary["positions"][0]
        assert pos["id"] == 1
        assert pos["market"] == "Test Question?"
        assert pos["entry"] == 40.0
        assert pos["current"] == 60.0
        assert pos["pnl"] == 50.0  # (60-40) * 250 / 100 = 50
        assert pos["pnl_pct"] == 50.0  # 50/100 * 100 = 50%
    
    def test_handles_no_outcome_for_fallback(self, tracker):
        """Should calculate P&L for No positions correctly."""
        trades = [{
            "id": 1,
            "status": "OPEN",
            "market_slug": "test",
            "question": "Test?",
            "entry_price": 70.0,  # Bought No at 70%
            "amount": 100,
            "shares": 142.86,
            "outcome": "No"
        }]
        tracker.trades_file.write_text(json.dumps(trades))
        
        # No position profits when Yes price goes down (our 70% No means Yes was 30%)
        # Now Yes is 20%, so No is 80% -> profit
        # P&L = (entry - current_yes_price) * shares / 100
        # But outcome is No, so we calculate: (70 - 40) * 142.86 / 100 = 42.86
        with patch.object(tracker, 'get_current_price', return_value=40.0):
            summary = tracker.portfolio_summary()
        
        # For No outcome: pnl = (entry - current) * shares / 100
        # = (70 - 40) * 142.86 / 100 = 42.86
        assert abs(summary["positions"][0]["pnl"] - 42.86) < 0.1
