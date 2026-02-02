#!/usr/bin/env python3
"""
Tests for Tavily search module
"""

import pytest
import json
from unittest.mock import patch, MagicMock
from monitors.tavily_search import (
    SearchResult,
    TradingSignal,
    hash_result,
    extract_entities,
    extract_keywords,
    score_relevance,
    search_tavily,
    search_for_signals,
    format_signal_alert,
    load_seen,
    save_seen,
)


class TestHashResult:
    """Tests for hash_result function"""
    
    def test_consistent_hash(self):
        """Same inputs produce same hash"""
        h1 = hash_result("Test Title", "https://example.com")
        h2 = hash_result("Test Title", "https://example.com")
        assert h1 == h2
    
    def test_different_inputs_different_hash(self):
        """Different inputs produce different hash"""
        h1 = hash_result("Title A", "https://a.com")
        h2 = hash_result("Title B", "https://b.com")
        assert h1 != h2
    
    def test_hash_length(self):
        """Hash is 12 characters"""
        h = hash_result("Test", "https://test.com")
        assert len(h) == 12


class TestExtractEntities:
    """Tests for entity extraction"""
    
    def test_finds_openai(self):
        """Finds OpenAI mention"""
        entities = extract_entities("OpenAI released GPT-5 today")
        assert 'OpenAI' in entities
    
    def test_finds_multiple_entities(self):
        """Finds multiple entities"""
        text = "Google and Microsoft are competing with OpenAI"
        entities = extract_entities(text)
        assert 'Google' in entities
        assert 'Microsoft' in entities
        assert 'OpenAI' in entities
    
    def test_case_insensitive(self):
        """Entity matching is case insensitive"""
        entities = extract_entities("OPENAI and openai are the same")
        assert 'OpenAI' in entities
    
    def test_finds_people(self):
        """Finds person entities"""
        text = "Sam Altman spoke about AGI with Elon Musk"
        entities = extract_entities(text)
        assert 'Sam Altman' in entities
        assert 'Elon Musk' in entities
    
    def test_finds_regulatory_bodies(self):
        """Finds regulatory entities"""
        text = "The FTC and EU are investigating"
        entities = extract_entities(text)
        assert 'FTC' in entities
        assert 'EU' in entities
    
    def test_empty_text(self):
        """Returns empty list for empty text"""
        entities = extract_entities("")
        assert entities == []


class TestExtractKeywords:
    """Tests for keyword extraction"""
    
    def test_finds_launch_keywords(self):
        """Finds product launch keywords"""
        text = "OpenAI will announce and release their new model"
        keywords = extract_keywords(text)
        assert 'announce' in keywords
        assert 'release' in keywords
    
    def test_finds_deal_keywords(self):
        """Finds business deal keywords"""
        text = "Microsoft to acquire AI startup, raise funding"
        keywords = extract_keywords(text)
        assert 'acquire' in keywords
        assert 'funding' in keywords
        assert 'raise' in keywords
    
    def test_finds_regulatory_keywords(self):
        """Finds regulatory keywords"""
        text = "EU to regulate AI, approves new policy on antitrust"
        keywords = extract_keywords(text)
        assert 'regulate' in keywords
        assert 'approve' in keywords
        assert 'policy' in keywords
        assert 'antitrust' in keywords
    
    def test_finds_ai_model_keywords(self):
        """Finds AI model keywords"""
        text = "GPT-5 achieves AGI benchmark, Claude beats Gemini"
        keywords = extract_keywords(text)
        assert 'gpt' in keywords
        assert 'claude' in keywords
        assert 'gemini' in keywords
        assert 'achieve' in keywords


class TestScoreRelevance:
    """Tests for relevance scoring"""
    
    def test_high_relevance_result(self):
        """High entity/keyword density = high score"""
        result = SearchResult(
            title="OpenAI announces GPT-5 release, Sam Altman unveils breakthrough",
            url="https://test.com",
            content="Google and Microsoft respond to the launch. NVIDIA stock rises.",
            score=0.9,
            published_date="2026-02-02",
            source="TechCrunch"
        )
        score = score_relevance(result)
        assert score > 0.7
    
    def test_low_relevance_result(self):
        """Low entity/keyword density = lower score"""
        result = SearchResult(
            title="Weather forecast for tomorrow",
            url="https://weather.com",
            content="It will be sunny with clear skies",
            score=0.2,
            published_date="2026-02-02",
            source="Weather.com"
        )
        score = score_relevance(result)
        assert score < 0.3
    
    def test_score_capped_at_one(self):
        """Score never exceeds 1.0"""
        result = SearchResult(
            title="OpenAI Google Microsoft Anthropic launch announce release",
            url="https://test.com",
            content="Sam Altman Elon Musk breakthrough funding acquire partner",
            score=1.0,
            published_date="2026-02-02",
            source="Test"
        )
        score = score_relevance(result)
        assert score <= 1.0


class TestSearchTavily:
    """Tests for Tavily API calls"""
    
    @patch('monitors.tavily_search.requests.post')
    def test_successful_search(self, mock_post):
        """Parses successful API response"""
        mock_post.return_value = MagicMock(
            status_code=200,
            json=lambda: {
                'results': [
                    {
                        'title': 'Test Article',
                        'url': 'https://test.com',
                        'content': 'Article content here',
                        'score': 0.8,
                        'published_date': '2026-02-02',
                        'source': 'Test Source'
                    }
                ]
            }
        )
        
        results = search_tavily("test query")
        
        assert len(results) == 1
        assert results[0].title == 'Test Article'
        assert results[0].score == 0.8
    
    @patch('monitors.tavily_search.requests.post')
    def test_empty_results(self, mock_post):
        """Handles empty results"""
        mock_post.return_value = MagicMock(
            status_code=200,
            json=lambda: {'results': []}
        )
        
        results = search_tavily("test query")
        assert results == []
    
    @patch('monitors.tavily_search.requests.post')
    def test_api_error_handling(self, mock_post):
        """Handles API errors gracefully"""
        import requests
        mock_post.side_effect = requests.RequestException("API error")
        
        results = search_tavily("test query")
        assert results == []
    
    @patch('monitors.tavily_search.requests.post')
    def test_news_topic_includes_days(self, mock_post):
        """News topic includes days parameter"""
        mock_post.return_value = MagicMock(
            status_code=200,
            json=lambda: {'results': []}
        )
        
        search_tavily("test", topic='news', days=5)
        
        call_payload = mock_post.call_args[1]['json']
        assert call_payload['topic'] == 'news'
        assert call_payload['days'] == 5


class TestSearchForSignals:
    """Tests for the main signal search function"""
    
    @patch('monitors.tavily_search.search_tavily')
    @patch('monitors.tavily_search.load_seen')
    @patch('monitors.tavily_search.save_seen')
    def test_filters_by_min_score(self, mock_save, mock_load, mock_search):
        """Filters results below minimum score"""
        mock_load.return_value = set()
        mock_search.return_value = [
            SearchResult(
                title="Irrelevant article about cooking",
                url="https://cooking.com",
                content="How to make pasta",
                score=0.1,
                published_date=None,
                source="Cooking Site"
            )
        ]
        
        signals = search_for_signals(queries=["test"], min_score=0.5)
        assert len(signals) == 0
    
    @patch('monitors.tavily_search.search_tavily')
    @patch('monitors.tavily_search.load_seen')
    @patch('monitors.tavily_search.save_seen')
    def test_skips_seen_results(self, mock_save, mock_load, mock_search):
        """Skips previously seen results"""
        # Hash for "Test|https://test.com"
        seen_hash = hash_result("Test", "https://test.com")
        mock_load.return_value = {seen_hash}
        mock_search.return_value = [
            SearchResult(
                title="Test",
                url="https://test.com",
                content="OpenAI launch announcement",
                score=0.9,
                published_date=None,
                source="Test"
            )
        ]
        
        signals = search_for_signals(queries=["test"], min_score=0.1)
        assert len(signals) == 0
    
    @patch('monitors.tavily_search.search_tavily')
    @patch('monitors.tavily_search.load_seen')
    @patch('monitors.tavily_search.save_seen')
    def test_sorts_by_relevance(self, mock_save, mock_load, mock_search):
        """Results are sorted by relevance score"""
        mock_load.return_value = set()
        mock_search.return_value = [
            SearchResult(
                title="Low relevance",
                url="https://low.com",
                content="Some news",
                score=0.3,
                published_date=None,
                source="Low"
            ),
            SearchResult(
                title="OpenAI announces GPT-5",
                url="https://high.com",
                content="Sam Altman launches breakthrough",
                score=0.9,
                published_date=None,
                source="High"
            )
        ]
        
        signals = search_for_signals(queries=["test"], min_score=0.1)
        assert len(signals) == 2
        assert signals[0].relevance_score > signals[1].relevance_score


class TestFormatSignalAlert:
    """Tests for alert formatting"""
    
    def test_formats_signal(self):
        """Formats signal as readable alert"""
        signal = TradingSignal(
            headline="OpenAI releases GPT-5",
            url="https://test.com",
            relevance_score=0.85,
            entities=['OpenAI', 'Sam Altman'],
            keywords=['release', 'launch'],
            timestamp="2026-02-02T12:00:00Z",
            hash="abc123"
        )
        
        formatted = format_signal_alert(signal)
        
        assert "OpenAI releases GPT-5" in formatted
        assert "85%" in formatted
        assert "OpenAI" in formatted
        assert "release" in formatted
        assert "https://test.com" in formatted
    
    def test_handles_empty_entities(self):
        """Handles signals with no entities"""
        signal = TradingSignal(
            headline="Some news",
            url="https://test.com",
            relevance_score=0.5,
            entities=[],
            keywords=['news'],
            timestamp="2026-02-02T12:00:00Z",
            hash="abc123"
        )
        
        formatted = format_signal_alert(signal)
        assert "None" in formatted


class TestSeenPersistence:
    """Tests for seen hash persistence"""
    
    def test_load_seen_empty_file(self, tmp_path):
        """Returns empty set when file doesn't exist"""
        import monitors.tavily_search as ts
        original_file = ts.SEEN_FILE
        ts.SEEN_FILE = str(tmp_path / "nonexistent.json")
        
        try:
            seen = load_seen()
            assert seen == set()
        finally:
            ts.SEEN_FILE = original_file
    
    def test_save_and_load_seen(self, tmp_path):
        """Can save and load seen hashes"""
        import monitors.tavily_search as ts
        original_file = ts.SEEN_FILE
        ts.SEEN_FILE = str(tmp_path / "seen.json")
        
        try:
            save_seen({'hash1', 'hash2', 'hash3'})
            loaded = load_seen()
            assert loaded == {'hash1', 'hash2', 'hash3'}
        finally:
            ts.SEEN_FILE = original_file


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
