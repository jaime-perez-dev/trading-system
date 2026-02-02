#!/usr/bin/env python3
"""Unit tests for PositionMonitor."""

import json
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from alerts.position_monitor import PositionMonitor


@pytest.fixture
def temp_data_dir():
    """Create temporary data directory for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def monitor(temp_data_dir):
    """Create PositionMonitor with mocked paths."""
    with patch.object(PositionMonitor, '__init__', lambda self, alert_threshold=5.0, notify=True: None):
        m = PositionMonitor()
        m.threshold = 5.0
        m.polymarket = MagicMock()
        m.notifier = MagicMock()
        m.data_dir = temp_data_dir
        m.state_file = temp_data_dir / "position_prices.json"
        return m


class TestLoadPositions:
    """Tests for load_positions."""
    
    def test_no_file_returns_empty(self, monitor):
        """Return empty list when trades file doesn't exist."""
        result = monitor.load_positions()
        assert result == []
    
    def test_loads_open_positions_only(self, monitor):
        """Only return positions with status OPEN."""
        trades_file = monitor.data_dir / "paper_trades.json"
        trades = [
            {"id": 1, "status": "OPEN", "market_slug": "test-1"},
            {"id": 2, "status": "CLOSED", "market_slug": "test-2"},
            {"id": 3, "status": "OPEN", "market_slug": "test-3"},
        ]
        with open(trades_file, "w") as f:
            json.dump(trades, f)
        
        result = monitor.load_positions()
        assert len(result) == 2
        assert result[0]["id"] == 1
        assert result[1]["id"] == 3
    
    def test_empty_file_returns_empty(self, monitor):
        """Handle empty trades file."""
        trades_file = monitor.data_dir / "paper_trades.json"
        with open(trades_file, "w") as f:
            json.dump([], f)
        
        result = monitor.load_positions()
        assert result == []


class TestLoadAndSavePrices:
    """Tests for load_last_prices and save_prices."""
    
    def test_no_file_returns_empty_dict(self, monitor):
        """Return empty dict when state file doesn't exist."""
        result = monitor.load_last_prices()
        assert result == {}
    
    def test_loads_existing_prices(self, monitor):
        """Load prices from state file."""
        prices = {"market-1": 85.5, "market-2": 42.0}
        with open(monitor.state_file, "w") as f:
            json.dump(prices, f)
        
        result = monitor.load_last_prices()
        assert result["market-1"] == 85.5
        assert result["market-2"] == 42.0
    
    def test_save_and_reload(self, monitor):
        """Save prices and reload them."""
        prices = {"test-market": 75.0}
        monitor.save_prices(prices)
        
        result = monitor.load_last_prices()
        assert result == prices


class TestGetCurrentPrice:
    """Tests for get_current_price."""
    
    def test_fetches_price_success(self, monitor):
        """Fetch and parse price from API."""
        mock_response = MagicMock()
        mock_response.ok = True
        mock_response.json.return_value = [{"outcomePrices": "[0.85, 0.15]"}]
        
        with patch("requests.get", return_value=mock_response):
            price = monitor.get_current_price("test-market")
        
        assert price == 85.0
    
    def test_handles_list_prices(self, monitor):
        """Handle outcomePrices as list instead of string."""
        mock_response = MagicMock()
        mock_response.ok = True
        mock_response.json.return_value = [{"outcomePrices": [0.72, 0.28]}]
        
        with patch("requests.get", return_value=mock_response):
            price = monitor.get_current_price("test-market")
        
        assert price == 72.0
    
    def test_returns_none_on_error(self, monitor):
        """Return None when API fails."""
        with patch("requests.get", side_effect=Exception("Network error")):
            price = monitor.get_current_price("test-market")
        
        assert price is None
    
    def test_returns_none_on_empty_response(self, monitor):
        """Return None when API returns empty data."""
        mock_response = MagicMock()
        mock_response.ok = True
        mock_response.json.return_value = []
        
        with patch("requests.get", return_value=mock_response):
            price = monitor.get_current_price("test-market")
        
        assert price is None
    
    def test_returns_none_on_bad_response(self, monitor):
        """Return None when response is not ok."""
        mock_response = MagicMock()
        mock_response.ok = False
        
        with patch("requests.get", return_value=mock_response):
            price = monitor.get_current_price("test-market")
        
        assert price is None
    
    def test_handles_missing_outcome_prices(self, monitor):
        """Return None when outcomePrices is missing."""
        mock_response = MagicMock()
        mock_response.ok = True
        mock_response.json.return_value = [{"other_field": "value"}]
        
        with patch("requests.get", return_value=mock_response):
            price = monitor.get_current_price("test-market")
        
        assert price is None


class TestCheckPositions:
    """Tests for check_positions."""
    
    def test_no_positions(self, monitor, capsys):
        """Handle no open positions."""
        result = monitor.check_positions()
        
        assert result == []
        captured = capsys.readouterr()
        assert "No open positions" in captured.out
    
    def test_no_alert_within_threshold(self, monitor):
        """No alert when price change is below threshold."""
        trades_file = monitor.data_dir / "paper_trades.json"
        trades = [{
            "id": 1,
            "status": "OPEN",
            "market_slug": "test-market",
            "question": "Test Question",
            "entry_price": 80.0
        }]
        with open(trades_file, "w") as f:
            json.dump(trades, f)
        
        # Set last price
        monitor.save_prices({"test-market": 80.0})
        
        # Price moved only 2pp (below 5pp threshold)
        with patch.object(monitor, "get_current_price", return_value=82.0):
            alerts = monitor.check_positions()
        
        assert len(alerts) == 0
    
    def test_alert_on_price_increase(self, monitor):
        """Trigger alert when price increases above threshold."""
        trades_file = monitor.data_dir / "paper_trades.json"
        trades = [{
            "id": 1,
            "status": "OPEN",
            "market_slug": "test-market",
            "question": "Test Question",
            "entry_price": 80.0
        }]
        with open(trades_file, "w") as f:
            json.dump(trades, f)
        
        monitor.save_prices({"test-market": 80.0})
        
        # Price moved +6pp (above 5pp threshold)
        with patch.object(monitor, "get_current_price", return_value=86.0):
            alerts = monitor.check_positions()
        
        assert len(alerts) == 1
        assert alerts[0]["direction"] == "up"
        assert alerts[0]["change"] == 6.0
        assert alerts[0]["current"] == 86.0
    
    def test_alert_on_price_decrease(self, monitor):
        """Trigger alert when price decreases below threshold."""
        trades_file = monitor.data_dir / "paper_trades.json"
        trades = [{
            "id": 1,
            "status": "OPEN",
            "market_slug": "test-market",
            "question": "Test Question",
            "entry_price": 80.0
        }]
        with open(trades_file, "w") as f:
            json.dump(trades, f)
        
        monitor.save_prices({"test-market": 80.0})
        
        # Price moved -7pp
        with patch.object(monitor, "get_current_price", return_value=73.0):
            alerts = monitor.check_positions()
        
        assert len(alerts) == 1
        assert alerts[0]["direction"] == "down"
        assert alerts[0]["change"] == -7.0
    
    def test_uses_entry_price_when_no_last_price(self, monitor):
        """Use entry price for comparison when no last price exists."""
        trades_file = monitor.data_dir / "paper_trades.json"
        trades = [{
            "id": 1,
            "status": "OPEN",
            "market_slug": "test-market",
            "question": "Test Question",
            "entry_price": 50.0
        }]
        with open(trades_file, "w") as f:
            json.dump(trades, f)
        
        # No last prices saved - should compare to entry
        # Entry is 50%, current is 60% = +10pp change
        with patch.object(monitor, "get_current_price", return_value=60.0):
            alerts = monitor.check_positions()
        
        assert len(alerts) == 1
        assert alerts[0]["last"] == 50.0  # Used entry price
    
    def test_saves_current_prices(self, monitor):
        """Save current prices after checking."""
        trades_file = monitor.data_dir / "paper_trades.json"
        trades = [{
            "id": 1,
            "status": "OPEN",
            "market_slug": "test-market",
            "question": "Test Question",
            "entry_price": 80.0
        }]
        with open(trades_file, "w") as f:
            json.dump(trades, f)
        
        with patch.object(monitor, "get_current_price", return_value=85.0):
            monitor.check_positions()
        
        saved = monitor.load_last_prices()
        assert saved["test-market"] == 85.0
    
    def test_sends_telegram_notification(self, monitor):
        """Send Telegram alert when threshold exceeded."""
        trades_file = monitor.data_dir / "paper_trades.json"
        trades = [{
            "id": 1,
            "status": "OPEN",
            "market_slug": "test-market",
            "question": "Test Question",
            "entry_price": 80.0
        }]
        with open(trades_file, "w") as f:
            json.dump(trades, f)
        
        monitor.save_prices({"test-market": 80.0})
        
        with patch.object(monitor, "get_current_price", return_value=90.0):
            monitor.check_positions()
        
        monitor.notifier.alert_price_move.assert_called_once()
        call_kwargs = monitor.notifier.alert_price_move.call_args[1]
        assert call_kwargs["direction"] == "up"
        assert call_kwargs["old_price"] == 80.0
        assert call_kwargs["new_price"] == 90.0
    
    def test_handles_price_fetch_failure(self, monitor, capsys):
        """Continue checking when price fetch fails for one position."""
        trades_file = monitor.data_dir / "paper_trades.json"
        trades = [
            {"id": 1, "status": "OPEN", "market_slug": "fail-market", "question": "Fail", "entry_price": 50.0},
            {"id": 2, "status": "OPEN", "market_slug": "ok-market", "question": "OK", "entry_price": 50.0},
        ]
        with open(trades_file, "w") as f:
            json.dump(trades, f)
        
        def mock_price(slug):
            return None if slug == "fail-market" else 60.0
        
        with patch.object(monitor, "get_current_price", side_effect=mock_price):
            monitor.check_positions()
        
        captured = capsys.readouterr()
        assert "Could not fetch" in captured.out
        
        # Should still save the successful one
        saved = monitor.load_last_prices()
        assert "ok-market" in saved
        assert "fail-market" not in saved
    
    def test_multiple_positions_multiple_alerts(self, monitor):
        """Handle multiple positions with multiple alerts."""
        trades_file = monitor.data_dir / "paper_trades.json"
        trades = [
            {"id": 1, "status": "OPEN", "market_slug": "market-1", "question": "Q1", "entry_price": 50.0},
            {"id": 2, "status": "OPEN", "market_slug": "market-2", "question": "Q2", "entry_price": 50.0},
            {"id": 3, "status": "OPEN", "market_slug": "market-3", "question": "Q3", "entry_price": 50.0},
        ]
        with open(trades_file, "w") as f:
            json.dump(trades, f)
        
        monitor.save_prices({"market-1": 50.0, "market-2": 50.0, "market-3": 50.0})
        
        def mock_price(slug):
            # market-1: +6pp (alert), market-2: +2pp (no alert), market-3: -8pp (alert)
            return {"market-1": 56.0, "market-2": 52.0, "market-3": 42.0}.get(slug)
        
        with patch.object(monitor, "get_current_price", side_effect=mock_price):
            alerts = monitor.check_positions()
        
        assert len(alerts) == 2
        slugs = [a["slug"] for a in alerts]
        assert "market-1" in slugs
        assert "market-3" in slugs
        assert "market-2" not in slugs


class TestCustomThreshold:
    """Tests for custom alert thresholds."""
    
    def test_higher_threshold(self, monitor):
        """Respect custom higher threshold."""
        monitor.threshold = 10.0  # 10pp threshold
        
        trades_file = monitor.data_dir / "paper_trades.json"
        trades = [{"id": 1, "status": "OPEN", "market_slug": "test", "question": "Test", "entry_price": 50.0}]
        with open(trades_file, "w") as f:
            json.dump(trades, f)
        
        monitor.save_prices({"test": 50.0})
        
        # 8pp change - below 10pp threshold
        with patch.object(monitor, "get_current_price", return_value=58.0):
            alerts = monitor.check_positions()
        
        assert len(alerts) == 0
    
    def test_lower_threshold(self, monitor):
        """Respect custom lower threshold."""
        monitor.threshold = 2.0  # 2pp threshold
        
        trades_file = monitor.data_dir / "paper_trades.json"
        trades = [{"id": 1, "status": "OPEN", "market_slug": "test", "question": "Test", "entry_price": 50.0}]
        with open(trades_file, "w") as f:
            json.dump(trades, f)
        
        monitor.save_prices({"test": 50.0})
        
        # 3pp change - above 2pp threshold
        with patch.object(monitor, "get_current_price", return_value=53.0):
            alerts = monitor.check_positions()
        
        assert len(alerts) == 1


class TestSummary:
    """Tests for summary method."""
    
    def test_empty_portfolio(self, monitor):
        """Handle empty portfolio."""
        summary = monitor.summary()
        
        assert summary["positions"] == []
        assert summary["total_invested"] == 0
        assert summary["unrealized_pnl"] == 0
        assert "timestamp" in summary
    
    def test_calculates_unrealized_pnl(self, monitor):
        """Calculate unrealized P&L for all positions."""
        trades_file = monitor.data_dir / "paper_trades.json"
        trades = [
            {
                "id": 1,
                "status": "OPEN",
                "market_slug": "market-1",
                "question": "Question 1",
                "entry_price": 50.0,
                "amount": 100,
                "shares": 200  # $100 at 50% = 200 shares
            },
            {
                "id": 2,
                "status": "OPEN",
                "market_slug": "market-2",
                "question": "Question 2",
                "entry_price": 40.0,
                "amount": 50,
                "shares": 125  # $50 at 40% = 125 shares
            }
        ]
        with open(trades_file, "w") as f:
            json.dump(trades, f)
        
        def mock_price(slug):
            return {"market-1": 70.0, "market-2": 60.0}.get(slug)
        
        with patch.object(monitor, "get_current_price", side_effect=mock_price):
            summary = monitor.summary()
        
        assert len(summary["positions"]) == 2
        assert summary["total_invested"] == 150
        
        # Position 1: (70-50)*200/100 = $40
        # Position 2: (60-40)*125/100 = $25
        assert summary["unrealized_pnl"] == 65.0
    
    def test_uses_entry_price_on_fetch_failure(self, monitor):
        """Use entry price when current price fetch fails."""
        trades_file = monitor.data_dir / "paper_trades.json"
        trades = [{
            "id": 1,
            "status": "OPEN",
            "market_slug": "test",
            "question": "Test",
            "entry_price": 80.0,
            "amount": 100,
            "shares": 125
        }]
        with open(trades_file, "w") as f:
            json.dump(trades, f)
        
        with patch.object(monitor, "get_current_price", return_value=None):
            summary = monitor.summary()
        
        assert summary["positions"][0]["current"] == 80.0
        assert summary["positions"][0]["pnl"] == 0
    
    def test_includes_position_details(self, monitor):
        """Include all position details in summary."""
        trades_file = monitor.data_dir / "paper_trades.json"
        trades = [{
            "id": 1,
            "status": "OPEN",
            "market_slug": "test",
            "question": "Test Market Question",
            "entry_price": 60.0,
            "amount": 200,
            "shares": 333
        }]
        with open(trades_file, "w") as f:
            json.dump(trades, f)
        
        with patch.object(monitor, "get_current_price", return_value=75.0):
            summary = monitor.summary()
        
        pos = summary["positions"][0]
        assert pos["question"] == "Test Market Question"
        assert pos["entry"] == 60.0
        assert pos["current"] == 75.0
        assert pos["amount"] == 200
        # P&L = (75-60)*333/100 = $49.95
        assert abs(pos["pnl"] - 49.95) < 0.01


class TestNotifierDisabled:
    """Tests when notifier is disabled."""
    
    def test_no_crash_when_notifier_none(self, monitor):
        """Don't crash when notifier is None."""
        monitor.notifier = None
        
        trades_file = monitor.data_dir / "paper_trades.json"
        trades = [{"id": 1, "status": "OPEN", "market_slug": "test", "question": "Test", "entry_price": 50.0}]
        with open(trades_file, "w") as f:
            json.dump(trades, f)
        
        monitor.save_prices({"test": 50.0})
        
        # Should not raise even with alert triggered
        with patch.object(monitor, "get_current_price", return_value=60.0):
            alerts = monitor.check_positions()
        
        assert len(alerts) == 1
