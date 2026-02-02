"""
Tests for Market Watchlist module
"""

import json
import os
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

import pytest

# Add parent dir for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from market_watchlist import (
    WatchedMarket,
    load_watchlist,
    save_watchlist,
    add_market,
    remove_market,
    check_watchlist,
    list_watchlist,
    clear_watchlist,
    WATCHLIST_FILE
)


@pytest.fixture
def temp_watchlist(tmp_path, monkeypatch):
    """Use a temporary watchlist file"""
    temp_file = tmp_path / "watchlist.json"
    monkeypatch.setattr("market_watchlist.WATCHLIST_FILE", temp_file)
    monkeypatch.setattr("market_watchlist.DATA_DIR", tmp_path)
    return temp_file


class TestWatchedMarketDataclass:
    """Tests for WatchedMarket dataclass"""
    
    def test_create_minimal(self):
        """Test creating market with minimal fields"""
        m = WatchedMarket(
            slug="test-market",
            question="Test question?",
            added_at="2026-02-02T12:00:00Z"
        )
        assert m.slug == "test-market"
        assert m.target_price is None
        assert m.alert_on_move == 0.05
        
    def test_create_full(self):
        """Test creating market with all fields"""
        m = WatchedMarket(
            slug="test-market",
            question="Test question?",
            added_at="2026-02-02T12:00:00Z",
            target_price=0.35,
            alert_on_move=0.10,
            last_price=0.25,
            note="Watching for news"
        )
        assert m.target_price == 0.35
        assert m.alert_on_move == 0.10
        assert m.note == "Watching for news"


class TestLoadSaveWatchlist:
    """Tests for watchlist persistence"""
    
    def test_load_empty(self, temp_watchlist):
        """Test loading when file doesn't exist"""
        result = load_watchlist()
        assert result == {}
        
    def test_save_and_load(self, temp_watchlist):
        """Test saving and loading watchlist"""
        data = {
            "test-market": {
                "slug": "test-market",
                "question": "Test?",
                "added_at": "2026-02-02T12:00:00Z"
            }
        }
        save_watchlist(data)
        result = load_watchlist()
        assert result == data
        
    def test_load_corrupted_file(self, temp_watchlist):
        """Test loading when file is corrupted"""
        temp_watchlist.write_text("not valid json")
        result = load_watchlist()
        assert result == {}


class TestAddMarket:
    """Tests for add_market function"""
    
    @patch("market_watchlist.PolymarketClient")
    def test_add_basic(self, mock_client_class, temp_watchlist):
        """Test adding market with minimal params"""
        mock_client = Mock()
        mock_client.get_market_by_slug.return_value = {
            "question": "Will AI reach AGI by 2030?",
            "outcomePrices": '["0.25", "0.75"]'
        }
        mock_client_class.return_value = mock_client
        
        result = add_market("agi-2030")
        
        assert result.slug == "agi-2030"
        assert result.question == "Will AI reach AGI by 2030?"
        assert result.last_price == 0.25
        
        # Verify saved
        watchlist = load_watchlist()
        assert "agi-2030" in watchlist
        
    @patch("market_watchlist.PolymarketClient")
    def test_add_with_target(self, mock_client_class, temp_watchlist):
        """Test adding market with target price"""
        mock_client = Mock()
        mock_client.get_market_by_slug.return_value = {
            "question": "Will OpenAI IPO?",
            "outcomePrices": '["0.40", "0.60"]'
        }
        mock_client_class.return_value = mock_client
        
        result = add_market("openai-ipo", target=0.30, note="Waiting for news")
        
        assert result.target_price == 0.30
        assert result.note == "Waiting for news"
        
    @patch("market_watchlist.PolymarketClient")
    def test_add_not_found(self, mock_client_class, temp_watchlist):
        """Test adding non-existent market"""
        mock_client = Mock()
        mock_client.get_market_by_slug.return_value = None
        mock_client_class.return_value = mock_client
        
        with pytest.raises(ValueError, match="Market not found"):
            add_market("nonexistent-market")
            
    @patch("market_watchlist.PolymarketClient")
    def test_add_updates_existing(self, mock_client_class, temp_watchlist):
        """Test adding market that already exists updates it"""
        mock_client = Mock()
        mock_client.get_market_by_slug.return_value = {
            "question": "Test market",
            "outcomePrices": '["0.50"]'
        }
        mock_client_class.return_value = mock_client
        
        add_market("test-market", note="First note")
        add_market("test-market", note="Updated note")
        
        watchlist = load_watchlist()
        assert watchlist["test-market"]["note"] == "Updated note"


class TestRemoveMarket:
    """Tests for remove_market function"""
    
    def test_remove_existing(self, temp_watchlist):
        """Test removing existing market"""
        save_watchlist({
            "test-market": {"slug": "test-market", "question": "Test?"}
        })
        
        result = remove_market("test-market")
        
        assert result is True
        assert "test-market" not in load_watchlist()
        
    def test_remove_nonexistent(self, temp_watchlist):
        """Test removing market that doesn't exist"""
        result = remove_market("nonexistent")
        assert result is False


class TestCheckWatchlist:
    """Tests for check_watchlist function"""
    
    def test_check_empty(self, temp_watchlist):
        """Test checking empty watchlist"""
        result = check_watchlist()
        assert result == []
        
    @patch("market_watchlist.PolymarketClient")
    def test_check_no_alerts(self, mock_client_class, temp_watchlist):
        """Test checking watchlist with no alerts triggered"""
        save_watchlist({
            "test-market": {
                "slug": "test-market",
                "question": "Test?",
                "last_price": 0.50,
                "alert_on_move": 0.05
            }
        })
        
        mock_client = Mock()
        mock_client.get_market_by_slug.return_value = {
            "outcomePrices": '["0.51"]'  # Only 2% move, below threshold
        }
        mock_client_class.return_value = mock_client
        
        alerts = check_watchlist()
        assert alerts == []
        
    @patch("market_watchlist.PolymarketClient")
    def test_check_price_move_alert(self, mock_client_class, temp_watchlist):
        """Test alert triggered on significant price move"""
        save_watchlist({
            "test-market": {
                "slug": "test-market",
                "question": "Test market?",
                "last_price": 0.50,
                "alert_on_move": 0.05
            }
        })
        
        mock_client = Mock()
        mock_client.get_market_by_slug.return_value = {
            "outcomePrices": '["0.60"]'  # 20% move
        }
        mock_client_class.return_value = mock_client
        
        alerts = check_watchlist()
        
        assert len(alerts) == 1
        assert alerts[0]["slug"] == "test-market"
        assert alerts[0]["old_price"] == 0.50
        assert alerts[0]["new_price"] == 0.60
        
    @patch("market_watchlist.PolymarketClient")
    def test_check_target_hit_alert(self, mock_client_class, temp_watchlist):
        """Test alert triggered when target price hit"""
        save_watchlist({
            "test-market": {
                "slug": "test-market",
                "question": "Test market?",
                "last_price": 0.25,
                "target_price": 0.30,
                "alert_on_move": 0.50  # High threshold so no move alert
            }
        })
        
        mock_client = Mock()
        mock_client.get_market_by_slug.return_value = {
            "outcomePrices": '["0.32"]'  # Crossed target of 0.30
        }
        mock_client_class.return_value = mock_client
        
        alerts = check_watchlist()
        
        assert len(alerts) == 1
        assert "target" in alerts[0]
        assert alerts[0]["target"] == 0.30
        
    @patch("market_watchlist.PolymarketClient")
    def test_check_updates_last_price(self, mock_client_class, temp_watchlist):
        """Test that check updates last_price in watchlist"""
        save_watchlist({
            "test-market": {
                "slug": "test-market",
                "question": "Test?",
                "last_price": 0.50,
                "alert_on_move": 0.05
            }
        })
        
        mock_client = Mock()
        mock_client.get_market_by_slug.return_value = {
            "outcomePrices": '["0.55"]'
        }
        mock_client_class.return_value = mock_client
        
        check_watchlist()
        
        watchlist = load_watchlist()
        assert watchlist["test-market"]["last_price"] == 0.55


class TestListWatchlist:
    """Tests for list_watchlist function"""
    
    def test_list_empty(self, temp_watchlist):
        """Test listing empty watchlist"""
        result = list_watchlist()
        assert result == []
        
    def test_list_multiple(self, temp_watchlist):
        """Test listing multiple markets"""
        save_watchlist({
            "market-1": {"slug": "market-1", "question": "Q1?", "last_price": 0.30},
            "market-2": {"slug": "market-2", "question": "Q2?", "last_price": 0.70}
        })
        
        result = list_watchlist()
        assert len(result) == 2


class TestClearWatchlist:
    """Tests for clear_watchlist function"""
    
    def test_clear(self, temp_watchlist):
        """Test clearing watchlist"""
        save_watchlist({
            "market-1": {"slug": "market-1"},
            "market-2": {"slug": "market-2"},
            "market-3": {"slug": "market-3"}
        })
        
        count = clear_watchlist()
        
        assert count == 3
        assert load_watchlist() == {}
        
    def test_clear_empty(self, temp_watchlist):
        """Test clearing already empty watchlist"""
        count = clear_watchlist()
        assert count == 0


class TestAlertThresholds:
    """Tests for different alert threshold scenarios"""
    
    @patch("market_watchlist.PolymarketClient")
    def test_custom_move_threshold(self, mock_client_class, temp_watchlist):
        """Test custom alert_on_move threshold"""
        save_watchlist({
            "test-market": {
                "slug": "test-market",
                "question": "Test?",
                "last_price": 0.50,
                "alert_on_move": 0.20  # 20% threshold
            }
        })
        
        mock_client = Mock()
        mock_client.get_market_by_slug.return_value = {
            "outcomePrices": '["0.58"]'  # 16% move, below 20% threshold
        }
        mock_client_class.return_value = mock_client
        
        alerts = check_watchlist()
        assert alerts == []  # No alert because 16% < 20%
        
    @patch("market_watchlist.PolymarketClient")
    def test_downward_move_alert(self, mock_client_class, temp_watchlist):
        """Test alert on downward price move"""
        save_watchlist({
            "test-market": {
                "slug": "test-market",
                "question": "Test?",
                "last_price": 0.60,
                "alert_on_move": 0.05
            }
        })
        
        mock_client = Mock()
        mock_client.get_market_by_slug.return_value = {
            "outcomePrices": '["0.45"]'  # Dropped 25%
        }
        mock_client_class.return_value = mock_client
        
        alerts = check_watchlist()
        
        assert len(alerts) == 1
        assert alerts[0]["change"] < 0  # Negative change
