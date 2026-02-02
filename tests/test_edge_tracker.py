"""
Unit tests for edge_tracker.py
Tests event logging, updating, and statistics calculation.
"""
import json
import os
import pytest
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock
from datetime import datetime

# Import module under test
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
import edge_tracker


@pytest.fixture
def temp_data_dir(tmp_path):
    """Create a temporary data directory for tests."""
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    return data_dir


@pytest.fixture
def mock_data_dir(temp_data_dir, monkeypatch):
    """Mock the DATA_DIR and EDGE_LOG to use temp directory."""
    edge_log = temp_data_dir / "edge_events.json"
    monkeypatch.setattr(edge_tracker, 'DATA_DIR', temp_data_dir)
    monkeypatch.setattr(edge_tracker, 'EDGE_LOG', edge_log)
    return temp_data_dir


class TestLoadEvents:
    """Tests for load_events function."""
    
    def test_returns_empty_structure_when_no_file(self, mock_data_dir):
        """Should return empty events list when file doesn't exist."""
        result = edge_tracker.load_events()
        assert result == {"events": [], "stats": {}}
    
    def test_loads_existing_events(self, mock_data_dir):
        """Should load events from existing file."""
        test_data = {
            "events": [{"id": 1, "headline": "Test"}],
            "stats": {"total": 1}
        }
        edge_log = mock_data_dir / "edge_events.json"
        edge_log.write_text(json.dumps(test_data))
        
        result = edge_tracker.load_events()
        assert result == test_data
        assert len(result["events"]) == 1


class TestSaveEvents:
    """Tests for save_events function."""
    
    def test_saves_events_to_file(self, mock_data_dir):
        """Should write events to JSON file."""
        test_data = {
            "events": [{"id": 1, "headline": "Test event"}],
            "stats": {}
        }
        edge_tracker.save_events(test_data)
        
        edge_log = mock_data_dir / "edge_events.json"
        assert edge_log.exists()
        
        saved = json.loads(edge_log.read_text())
        assert saved == test_data
    
    def test_overwrites_existing_file(self, mock_data_dir):
        """Should overwrite existing file."""
        edge_log = mock_data_dir / "edge_events.json"
        edge_log.write_text('{"events": [{"id": 0}], "stats": {}}')
        
        new_data = {"events": [{"id": 1}, {"id": 2}], "stats": {}}
        edge_tracker.save_events(new_data)
        
        saved = json.loads(edge_log.read_text())
        assert len(saved["events"]) == 2


class TestLogNewsEvent:
    """Tests for log_news_event function."""
    
    def test_creates_event_with_required_fields(self, mock_data_dir):
        """Should create event with all required fields."""
        event_id = edge_tracker.log_news_event(
            headline="OpenAI releases GPT-5",
            source="Reuters"
        )
        
        assert event_id == 1
        
        data = edge_tracker.load_events()
        event = data["events"][0]
        
        assert event["id"] == 1
        assert event["type"] == "news"
        assert event["headline"] == "OpenAI releases GPT-5"
        assert event["source"] == "Reuters"
        assert event["market_slug"] is None
        assert "news_time" in event
        assert event["market_price_at_news"] is None
        assert event["market_price_1h_later"] is None
        assert event["market_price_24h_later"] is None
        assert event["final_resolution"] is None
        assert event["notes"] == ""
    
    def test_creates_event_with_market_slug(self, mock_data_dir):
        """Should include market slug when provided."""
        event_id = edge_tracker.log_news_event(
            headline="Test headline",
            source="Test source",
            market_slug="will-gpt5-release-2026"
        )
        
        data = edge_tracker.load_events()
        assert data["events"][0]["market_slug"] == "will-gpt5-release-2026"
    
    def test_increments_event_id(self, mock_data_dir):
        """Should increment event ID for each new event."""
        id1 = edge_tracker.log_news_event("Event 1", "Source 1")
        id2 = edge_tracker.log_news_event("Event 2", "Source 2")
        id3 = edge_tracker.log_news_event("Event 3", "Source 3")
        
        assert id1 == 1
        assert id2 == 2
        assert id3 == 3
    
    def test_news_time_is_valid_iso_format(self, mock_data_dir):
        """Should record news_time in ISO format."""
        edge_tracker.log_news_event("Test", "Source")
        
        data = edge_tracker.load_events()
        news_time = data["events"][0]["news_time"]
        
        # Should not raise
        datetime.fromisoformat(news_time)


class TestUpdateEvent:
    """Tests for update_event function."""
    
    def test_updates_existing_event(self, mock_data_dir, capsys):
        """Should update fields on existing event."""
        edge_tracker.log_news_event("Test headline", "Test source")
        
        edge_tracker.update_event(1, market_price_at_news=65.0)
        
        data = edge_tracker.load_events()
        assert data["events"][0]["market_price_at_news"] == 65.0
        
        captured = capsys.readouterr()
        assert "Updated event #1" in captured.out
    
    def test_updates_multiple_fields(self, mock_data_dir):
        """Should update multiple fields at once."""
        edge_tracker.log_news_event("Test", "Source")
        
        edge_tracker.update_event(
            1,
            market_price_at_news=50.0,
            market_price_1h_later=75.0,
            final_resolution="yes",
            notes="Big move!"
        )
        
        data = edge_tracker.load_events()
        event = data["events"][0]
        assert event["market_price_at_news"] == 50.0
        assert event["market_price_1h_later"] == 75.0
        assert event["final_resolution"] == "yes"
        assert event["notes"] == "Big move!"
    
    def test_handles_nonexistent_event(self, mock_data_dir, capsys):
        """Should print message for nonexistent event."""
        edge_tracker.update_event(999, notes="test")
        
        captured = capsys.readouterr()
        assert "Event #999 not found" in captured.out
    
    def test_preserves_other_events(self, mock_data_dir):
        """Should not modify other events."""
        edge_tracker.log_news_event("Event 1", "Source")
        edge_tracker.log_news_event("Event 2", "Source")
        
        edge_tracker.update_event(2, notes="Updated")
        
        data = edge_tracker.load_events()
        assert data["events"][0]["notes"] == ""
        assert data["events"][1]["notes"] == "Updated"


class TestCalculateStats:
    """Tests for calculate_stats function."""
    
    def test_handles_no_events(self, mock_data_dir, capsys):
        """Should handle empty events list."""
        edge_tracker.calculate_stats()
        
        captured = capsys.readouterr()
        assert "No events logged yet" in captured.out
    
    def test_shows_basic_counts(self, mock_data_dir, capsys):
        """Should show total event count."""
        edge_tracker.log_news_event("Event 1", "Source")
        edge_tracker.log_news_event("Event 2", "Source")
        
        edge_tracker.calculate_stats()
        
        captured = capsys.readouterr()
        assert "Total events: 2" in captured.out
    
    def test_calculates_price_movement(self, mock_data_dir, capsys):
        """Should calculate average price movement."""
        edge_tracker.log_news_event("Event 1", "Source")
        edge_tracker.update_event(1, 
            market_price_at_news=50.0,
            market_price_1h_later=60.0
        )
        
        edge_tracker.log_news_event("Event 2", "Source")
        edge_tracker.update_event(2,
            market_price_at_news=40.0,
            market_price_1h_later=48.0
        )
        
        edge_tracker.calculate_stats()
        
        captured = capsys.readouterr()
        # Event 1: (60-50)/50 = 20%
        # Event 2: (48-40)/40 = 20%
        # Average = 20%
        assert "Avg 1h price move: +20.0%" in captured.out
    
    def test_calculates_win_rate(self, mock_data_dir, capsys):
        """Should calculate win rate from resolved events."""
        edge_tracker.log_news_event("Win 1", "Source")
        edge_tracker.update_event(1, final_resolution="yes", trade_result="win")
        
        edge_tracker.log_news_event("Win 2", "Source")
        edge_tracker.update_event(2, final_resolution="yes", trade_result="win")
        
        edge_tracker.log_news_event("Loss 1", "Source")
        edge_tracker.update_event(3, final_resolution="no", trade_result="loss")
        
        edge_tracker.calculate_stats()
        
        captured = capsys.readouterr()
        assert "Win rate: 2/3" in captured.out
        assert "67%" in captured.out


class TestShowEvents:
    """Tests for show_events function."""
    
    def test_shows_recent_events(self, mock_data_dir, capsys):
        """Should display recent events."""
        edge_tracker.log_news_event("First event headline", "Reuters")
        edge_tracker.log_news_event("Second event headline", "AP")
        
        edge_tracker.show_events(10)
        
        captured = capsys.readouterr()
        assert "First event headline" in captured.out
        assert "Second event headline" in captured.out
    
    def test_limits_output_count(self, mock_data_dir, capsys):
        """Should respect the n parameter."""
        for i in range(5):
            edge_tracker.log_news_event(f"Event {i}", "Source")
        
        # Clear the log output from event creation
        capsys.readouterr()
        
        edge_tracker.show_events(2)
        
        captured = capsys.readouterr()
        # Should only show last 2 events (Event 3 and Event 4)
        assert "Event 3" in captured.out
        assert "Event 4" in captured.out
        # Event 0, 1, 2 should not be in the show_events output
        assert "#1:" not in captured.out
        assert "#2:" not in captured.out
    
    def test_shows_price_data_when_available(self, mock_data_dir, capsys):
        """Should display price data if present."""
        edge_tracker.log_news_event("Test event", "Source")
        edge_tracker.update_event(1, 
            market_price_at_news=55.0,
            market_price_1h_later=70.0
        )
        
        edge_tracker.show_events()
        
        captured = capsys.readouterr()
        assert "55.0%" in captured.out
        assert "70.0%" in captured.out
    
    def test_shows_resolution_status(self, mock_data_dir, capsys):
        """Should show checkmark for resolved events."""
        edge_tracker.log_news_event("Unresolved", "Source")
        edge_tracker.log_news_event("Resolved", "Source")
        edge_tracker.update_event(2, final_resolution="yes")
        
        edge_tracker.show_events()
        
        captured = capsys.readouterr()
        assert "⏳ #1" in captured.out  # Pending
        assert "✓ #2" in captured.out   # Resolved
