"""
Tests for NewsMonitor
"""

import pytest
import json
from pathlib import Path
from unittest.mock import patch, MagicMock

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from monitors.news_monitor import NewsMonitor, KEYWORDS, RSS_FEEDS


class TestNewsMonitor:
    """Test NewsMonitor class"""

    def test_hash_article_consistent(self):
        """Same input produces same hash"""
        monitor = NewsMonitor()
        hash1 = monitor._hash_article("Test Title", "https://example.com")
        hash2 = monitor._hash_article("Test Title", "https://example.com")
        assert hash1 == hash2

    def test_hash_article_different_inputs(self):
        """Different inputs produce different hashes"""
        monitor = NewsMonitor()
        hash1 = monitor._hash_article("Title A", "https://example.com/a")
        hash2 = monitor._hash_article("Title B", "https://example.com/b")
        assert hash1 != hash2

    def test_score_article_high_impact_keyword(self):
        """High impact keywords increase score"""
        monitor = NewsMonitor()
        result = monitor._score_article(
            "OpenAI announces GPT-5 launch", 
            "The company has unveiled their new model"
        )
        assert result["score"] >= 20  # "launch", "announces", "unveiled" + "GPT-5"
        assert "GPT-5" in result["keywords"]
        assert "OpenAI" in result["entities"]

    def test_score_article_no_keywords(self):
        """Article with no keywords scores zero"""
        monitor = NewsMonitor()
        result = monitor._score_article(
            "Weather report for Tuesday",
            "Sunny skies expected all week"
        )
        assert result["score"] == 0
        assert result["keywords"] == []
        assert result["entities"] == []
        assert result["is_tradeable"] == False

    def test_score_article_entity_only(self):
        """Entity without keyword is not tradeable"""
        monitor = NewsMonitor()
        result = monitor._score_article(
            "OpenAI office decorations updated",
            "New plants in the lobby"
        )
        # Has entity but no high-impact keywords
        assert "OpenAI" in result["entities"]
        assert result["is_tradeable"] == False  # Need score >= 15 AND entities

    def test_score_article_keyword_only(self):
        """Keywords without entity not tradeable"""
        monitor = NewsMonitor()
        result = monitor._score_article(
            "Some company announces IPO",
            "A startup raised funding"
        )
        assert len(result["keywords"]) > 0
        assert result["entities"] == []
        assert result["is_tradeable"] == False  # Need entities

    def test_score_article_tradeable_threshold(self):
        """Article meets tradeable threshold"""
        monitor = NewsMonitor()
        result = monitor._score_article(
            "Microsoft announces acquisition of AI startup for $2 billion",
            "The deal was unveiled today in partnership"
        )
        assert result["is_tradeable"] == True
        assert result["score"] >= 15
        assert "Microsoft" in result["entities"]

    def test_score_article_case_insensitive(self):
        """Keyword matching is case insensitive"""
        monitor = NewsMonitor()
        result = monitor._score_article(
            "OPENAI ANNOUNCES GPT-5",
            "chatgpt gets massive upgrade"
        )
        assert "OpenAI" in result["entities"]
        assert "ChatGPT" in result["entities"]

    def test_format_alert(self):
        """Alert formatting includes all fields"""
        monitor = NewsMonitor()
        article = {
            "title": "Test Article",
            "source": "test_feed",
            "score": 25,
            "keywords": ["IPO", "launch"],
            "entities": ["OpenAI"],
            "link": "https://example.com/article"
        }
        alert = monitor.format_alert(article)
        assert "Test Article" in alert
        assert "25" in alert
        assert "IPO" in alert
        assert "OpenAI" in alert

    def test_seen_file_persistence(self, tmp_path):
        """Seen articles persist across instances"""
        # Patch DATA_DIR to use temp path
        with patch('monitors.news_monitor.DATA_DIR', tmp_path):
            monitor1 = NewsMonitor()
            monitor1.seen_file = tmp_path / "seen_articles.json"
            monitor1.seen = set()
            monitor1.seen.add("hash123")
            monitor1._save_seen()
            
            # New instance should load same data
            monitor2 = NewsMonitor()
            monitor2.seen_file = tmp_path / "seen_articles.json"
            loaded = monitor2._load_seen()
            assert "hash123" in loaded


class TestRSSFeeds:
    """Test RSS feed configuration"""

    def test_feeds_have_urls(self):
        """All feeds have valid URL format"""
        for name, url in RSS_FEEDS.items():
            assert url.startswith("http"), f"{name} has invalid URL"

    def test_keywords_structure(self):
        """Keywords dict has expected structure"""
        assert "high_impact" in KEYWORDS
        assert "entities" in KEYWORDS
        assert len(KEYWORDS["high_impact"]) > 10
        assert len(KEYWORDS["entities"]) > 5


class TestFetchFeed:
    """Test feed fetching (mocked)"""

    def test_fetch_feed_success(self):
        """Successful feed fetch returns articles"""
        monitor = NewsMonitor()
        
        # Mock feedparser response
        mock_entry = MagicMock()
        mock_entry.get = lambda k, default="": {
            "title": "OpenAI launches GPT-5",
            "link": "https://example.com/article",
            "summary": "Revolutionary AI model announced today",
            "published": "2026-02-01"
        }.get(k, default)
        
        mock_feed = MagicMock()
        mock_feed.entries = [mock_entry]
        
        with patch('monitors.news_monitor.feedparser.parse', return_value=mock_feed):
            articles = monitor.fetch_feed("test", "https://example.com/rss")
            
            assert len(articles) == 1
            assert articles[0]["title"] == "OpenAI launches GPT-5"
            assert articles[0]["source"] == "test"
            assert "score" in articles[0]

    def test_fetch_feed_error_handling(self):
        """Feed fetch errors return empty list"""
        monitor = NewsMonitor()
        
        with patch('monitors.news_monitor.feedparser.parse', side_effect=Exception("Network error")):
            articles = monitor.fetch_feed("test", "https://example.com/rss")
            assert articles == []


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
