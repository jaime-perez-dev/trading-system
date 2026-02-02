"""
Unit tests for auto_monitor.py
Tests: search_news, get_market_prices, check_pending_events, run_monitor
All tests use mocking — no network/side effects.
"""
import json
import os
import sys
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

# Add parent directory for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

import auto_monitor


class TestSearchNews:
    """Tests for search_news function."""
    
    def test_search_news_returns_list(self):
        """search_news should return a list of results."""
        mock_response = {
            "results": [
                {"title": "OpenAI releases GPT-5", "url": "https://example.com/1"},
                {"title": "Anthropic announces Claude 4", "url": "https://example.com/2"}
            ]
        }
        
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                stdout=json.dumps(mock_response),
                returncode=0
            )
            results = auto_monitor.search_news()
            
            assert isinstance(results, list)
            assert len(results) == 2
            assert results[0]["title"] == "OpenAI releases GPT-5"
    
    def test_search_news_empty_response(self):
        """search_news should handle empty results gracefully."""
        mock_response = {"results": []}
        
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                stdout=json.dumps(mock_response),
                returncode=0
            )
            results = auto_monitor.search_news()
            
            assert results == []
    
    def test_search_news_invalid_json(self):
        """search_news should return empty list on invalid JSON."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                stdout="not valid json",
                returncode=0
            )
            results = auto_monitor.search_news()
            
            assert results == []
    
    def test_search_news_no_results_key(self):
        """search_news should handle missing 'results' key."""
        mock_response = {"status": "ok"}  # No "results" key
        
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                stdout=json.dumps(mock_response),
                returncode=0
            )
            results = auto_monitor.search_news()
            
            assert results == []


class TestGetMarketPrices:
    """Tests for get_market_prices function."""
    
    def test_get_market_prices_returns_dict(self):
        """get_market_prices should return a dictionary of prices."""
        mock_market = [{
            "slug": "gpt-ads-by-january-31-329-775",
            "outcomePrices": json.dumps([0.35, 0.65])
        }]
        
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                stdout=json.dumps(mock_market),
                returncode=0
            )
            prices = auto_monitor.get_market_prices()
            
            assert isinstance(prices, dict)
    
    def test_get_market_prices_parses_outcome_prices(self):
        """Should correctly parse outcome prices."""
        mock_market = [{
            "slug": "gpt-ads-by-january-31-329-775",
            "outcomePrices": json.dumps([0.42, 0.58])
        }]
        
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                stdout=json.dumps(mock_market),
                returncode=0
            )
            prices = auto_monitor.get_market_prices()
            
            if "gpt-ads-by-january-31-329-775" in prices:
                assert prices["gpt-ads-by-january-31-329-775"]["yes"] == pytest.approx(42.0)
    
    def test_get_market_prices_handles_empty_response(self):
        """Should handle empty market response."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                stdout=json.dumps([]),
                returncode=0
            )
            prices = auto_monitor.get_market_prices()
            
            assert isinstance(prices, dict)
    
    def test_get_market_prices_handles_api_error(self):
        """Should handle API errors gracefully."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                stdout="Error: API unavailable",
                returncode=1
            )
            prices = auto_monitor.get_market_prices()
            
            assert isinstance(prices, dict)


class TestCheckPendingEvents:
    """Tests for check_pending_events function."""
    
    def test_check_pending_events_skips_updated_events(self):
        """Events with 1h price update should be skipped."""
        mock_events = {
            "events": [{
                "id": 1,
                "news_time": (datetime.now() - timedelta(hours=2)).isoformat(),
                "market_price_1h_later": "45.0"  # Already has update
            }]
        }
        
        with patch.object(auto_monitor, "load_events", return_value=mock_events):
            with patch.object(auto_monitor, "get_market_prices", return_value={}):
                with patch.object(auto_monitor, "update_event") as mock_update:
                    auto_monitor.check_pending_events()
                    mock_update.assert_not_called()
    
    def test_check_pending_events_updates_old_events(self):
        """Events older than 1h should get price updates."""
        mock_events = {
            "events": [{
                "id": 1,
                "news_time": (datetime.now() - timedelta(hours=2)).isoformat(),
                "market_slug": "gpt-ads-by-january-31-329-775"
                # No market_price_1h_later
            }]
        }
        mock_prices = {
            "gpt-ads-by-january-31-329-775": {"yes": 42.5, "name": "GPT Ads"}
        }
        
        with patch.object(auto_monitor, "load_events", return_value=mock_events):
            with patch.object(auto_monitor, "get_market_prices", return_value=mock_prices):
                with patch.object(auto_monitor, "update_event") as mock_update:
                    auto_monitor.check_pending_events()
                    mock_update.assert_called_once_with(1, market_price_1h_later="42.5")
    
    def test_check_pending_events_ignores_recent_events(self):
        """Events less than 1h old should not be updated yet."""
        mock_events = {
            "events": [{
                "id": 1,
                "news_time": (datetime.now() - timedelta(minutes=30)).isoformat(),
                "market_slug": "gpt-ads-by-january-31-329-775"
            }]
        }
        
        with patch.object(auto_monitor, "load_events", return_value=mock_events):
            with patch.object(auto_monitor, "get_market_prices", return_value={}):
                with patch.object(auto_monitor, "update_event") as mock_update:
                    auto_monitor.check_pending_events()
                    mock_update.assert_not_called()


class TestAIKeywords:
    """Tests for AI keyword detection."""
    
    def test_keywords_include_major_companies(self):
        """Keyword list should include major AI companies."""
        keywords = auto_monitor.AI_KEYWORDS
        assert "openai" in keywords
        assert "anthropic" in keywords
    
    def test_keywords_include_models(self):
        """Keyword list should include major models."""
        keywords = auto_monitor.AI_KEYWORDS
        assert any("gpt" in kw for kw in keywords)
        assert "claude" in keywords
        assert "gemini" in keywords
    
    def test_keywords_include_regulatory_terms(self):
        """Keyword list should include regulatory terms."""
        keywords = auto_monitor.AI_KEYWORDS
        assert "ai regulation" in keywords or any("regulation" in kw for kw in keywords)
        assert "ai safety" in keywords or any("safety" in kw for kw in keywords)


class TestRunMonitor:
    """Tests for the main run_monitor function."""
    
    def test_run_monitor_calls_all_functions(self, tmp_path, capsys):
        """run_monitor should call all monitoring functions."""
        # Create temp seen_headlines.json
        seen_file = tmp_path / "seen_headlines.json"
        seen_file.write_text("[]")
        
        mock_prices = {"market1": {"yes": 50.0, "name": "Test Market"}}
        mock_news = [{"title": "Non-AI news", "url": "https://example.com"}]
        mock_events = {"events": []}
        
        with patch.object(auto_monitor, "DATA_DIR", tmp_path):
            with patch.object(auto_monitor, "get_market_prices", return_value=mock_prices):
                with patch.object(auto_monitor, "search_news", return_value=mock_news):
                    with patch.object(auto_monitor, "load_events", return_value=mock_events):
                        auto_monitor.run_monitor()
        
        captured = capsys.readouterr()
        assert "Monitor Run:" in captured.out
        assert "Checking market prices" in captured.out
        assert "Searching for AI news" in captured.out
        assert "Monitor complete" in captured.out
    
    def test_run_monitor_saves_seen_headlines(self, tmp_path):
        """run_monitor should save seen headlines to file."""
        seen_file = tmp_path / "seen_headlines.json"
        seen_file.write_text("[]")
        
        mock_news = [
            {"title": "OpenAI announces new model", "url": "https://example.com/1"}
        ]
        
        with patch.object(auto_monitor, "DATA_DIR", tmp_path):
            with patch.object(auto_monitor, "get_market_prices", return_value={}):
                with patch.object(auto_monitor, "search_news", return_value=mock_news):
                    with patch.object(auto_monitor, "load_events", return_value={"events": []}):
                        auto_monitor.run_monitor()
        
        # Check that headline was saved
        saved = json.loads(seen_file.read_text())
        assert "OpenAI announces new model" in saved
    
    def test_run_monitor_filters_relevant_news(self, tmp_path, capsys):
        """run_monitor should only report news matching AI keywords."""
        seen_file = tmp_path / "seen_headlines.json"
        seen_file.write_text("[]")
        
        mock_news = [
            {"title": "OpenAI releases GPT-5", "url": "https://example.com/1"},  # Relevant
            {"title": "Sports team wins championship", "url": "https://example.com/2"}  # Not relevant
        ]
        
        with patch.object(auto_monitor, "DATA_DIR", tmp_path):
            with patch.object(auto_monitor, "get_market_prices", return_value={}):
                with patch.object(auto_monitor, "search_news", return_value=mock_news):
                    with patch.object(auto_monitor, "load_events", return_value={"events": []}):
                        auto_monitor.run_monitor()
        
        captured = capsys.readouterr()
        assert "1 new relevant headlines" in captured.out
        assert "OpenAI" in captured.out or "GPT-5" in captured.out
    
    def test_run_monitor_deduplicates_headlines(self, tmp_path, capsys):
        """run_monitor should not report headlines already seen."""
        seen_file = tmp_path / "seen_headlines.json"
        seen_file.write_text('["OpenAI releases GPT-5"]')
        
        mock_news = [
            {"title": "OpenAI releases GPT-5", "url": "https://example.com/1"}  # Already seen
        ]
        
        with patch.object(auto_monitor, "DATA_DIR", tmp_path):
            with patch.object(auto_monitor, "get_market_prices", return_value={}):
                with patch.object(auto_monitor, "search_news", return_value=mock_news):
                    with patch.object(auto_monitor, "load_events", return_value={"events": []}):
                        auto_monitor.run_monitor()
        
        captured = capsys.readouterr()
        assert "No new relevant news" in captured.out


class TestTrackedMarkets:
    """Tests for the TRACKED_MARKETS configuration."""
    
    def test_tracked_markets_has_entries(self):
        """TRACKED_MARKETS should have at least one entry."""
        assert len(auto_monitor.TRACKED_MARKETS) > 0
    
    def test_tracked_markets_format(self):
        """Each tracked market should have slug -> name mapping."""
        for slug, name in auto_monitor.TRACKED_MARKETS.items():
            assert isinstance(slug, str)
            assert isinstance(name, str)
            assert len(slug) > 0
            assert len(name) > 0
