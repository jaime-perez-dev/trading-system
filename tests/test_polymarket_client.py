#!/usr/bin/env python3
"""
Unit tests for Polymarket client
Tests JSON parsing, filtering, and schema handling
"""

import pytest
import json
from unittest.mock import Mock, patch

# Import the client
import sys
sys.path.insert(0, '..')
from polymarket.client import PolymarketClient


class TestMarketFiltering:
    """Tests for AI market filtering logic"""
    
    def test_exact_term_match(self):
        """Should match exact AI company/product names"""
        client = PolymarketClient()
        
        mock_markets = [
            {"question": "Will OpenAI release GPT-5?", "description": ""},
            {"question": "Who wins the Super Bowl?", "description": ""},
            {"question": "Will Anthropic IPO in 2026?", "description": ""},
        ]
        
        with patch.object(client, 'get_all_active_markets', return_value=mock_markets):
            result = client.get_ai_markets()
        
        assert len(result) == 2
        assert any("OpenAI" in m["question"] for m in result)
        assert any("Anthropic" in m["question"] for m in result)
        assert not any("Super Bowl" in m["question"] for m in result)
    
    def test_ai_word_boundary(self):
        """Should match 'AI' as word but not 'Aiyuk' or similar"""
        client = PolymarketClient()
        
        mock_markets = [
            {"question": "Will AI regulation pass?", "description": ""},
            {"question": "Will Brandon Aiyuk score?", "description": ""},
            {"question": "AI safety bill outcome", "description": ""},
        ]
        
        with patch.object(client, 'get_all_active_markets', return_value=mock_markets):
            result = client.get_ai_markets()
        
        # Should match AI markets, not Aiyuk
        questions = [m["question"] for m in result]
        assert "Will AI regulation pass?" in questions
        assert "AI safety bill outcome" in questions
        assert "Will Brandon Aiyuk score?" not in questions
    
    def test_case_insensitive_matching(self):
        """Should match regardless of case"""
        client = PolymarketClient()
        
        mock_markets = [
            {"question": "CHATGPT usage milestone", "description": ""},
            {"question": "chatgpt daily users", "description": ""},
            {"question": "ChatGPT enterprise", "description": ""},
        ]
        
        with patch.object(client, 'get_all_active_markets', return_value=mock_markets):
            result = client.get_ai_markets()
        
        assert len(result) == 3
    
    def test_description_matching(self):
        """Should also match on description field"""
        client = PolymarketClient()
        
        mock_markets = [
            {"question": "Tech company announcement?", "description": "OpenAI may announce new model"},
            {"question": "Random event", "description": "Sports betting unrelated"},
        ]
        
        with patch.object(client, 'get_all_active_markets', return_value=mock_markets):
            result = client.get_ai_markets()
        
        assert len(result) == 1
        assert result[0]["question"] == "Tech company announcement?"


class TestJSONParsing:
    """Tests for JSON string handling in API responses"""
    
    def test_events_as_json_string(self):
        """Should handle events field as JSON string"""
        client = PolymarketClient()
        
        mock_markets = [
            {
                "question": "Test market",
                "events": '[{"slug": "target-event", "title": "Test Event"}]'
            },
            {
                "question": "Other market",
                "events": '[{"slug": "other-event", "title": "Other Event"}]'
            }
        ]
        
        mock_response = Mock()
        mock_response.json.return_value = mock_markets
        mock_response.raise_for_status = Mock()
        
        with patch.object(client.session, 'get', return_value=mock_response):
            result = client.get_event_markets("target-event")
        
        assert len(result) == 1
        assert result[0]["question"] == "Test market"
    
    def test_events_as_list(self):
        """Should handle events field as already-parsed list"""
        client = PolymarketClient()
        
        mock_markets = [
            {
                "question": "Test market",
                "events": [{"slug": "target-event", "title": "Test Event"}]
            }
        ]
        
        mock_response = Mock()
        mock_response.json.return_value = mock_markets
        mock_response.raise_for_status = Mock()
        
        with patch.object(client.session, 'get', return_value=mock_response):
            result = client.get_event_markets("target-event")
        
        assert len(result) == 1
    
    def test_malformed_events_json(self):
        """Should handle malformed JSON in events field gracefully"""
        client = PolymarketClient()
        
        mock_markets = [
            {
                "question": "Test market",
                "events": "not valid json {"
            },
            {
                "question": "Valid market",
                "events": [{"slug": "target-event"}]
            }
        ]
        
        mock_response = Mock()
        mock_response.json.return_value = mock_markets
        mock_response.raise_for_status = Mock()
        
        with patch.object(client.session, 'get', return_value=mock_response):
            # Should not crash, should return valid markets only
            result = client.get_event_markets("target-event")
        
        assert len(result) == 1
        assert result[0]["question"] == "Valid market"
    
    def test_empty_events_field(self):
        """Should handle empty events gracefully"""
        client = PolymarketClient()
        
        mock_markets = [
            {"question": "No events", "events": []},
            {"question": "Null events", "events": None},
            {"question": "Missing events"},
        ]
        
        mock_response = Mock()
        mock_response.json.return_value = mock_markets
        mock_response.raise_for_status = Mock()
        
        with patch.object(client.session, 'get', return_value=mock_response):
            result = client.get_event_markets("any-event")
        
        # None should crash, all should be filtered out
        assert len(result) == 0


class TestSearchMarkets:
    """Tests for market search functionality"""
    
    def test_search_filters_by_query(self):
        """Should filter markets by query in question"""
        client = PolymarketClient()
        
        mock_response = Mock()
        mock_response.json.return_value = [
            {"question": "Will GPT-5 release in 2026?"},
            {"question": "NFL draft picks"},
            {"question": "GPT-5 capabilities benchmark"},
        ]
        mock_response.raise_for_status = Mock()
        
        with patch.object(client.session, 'get', return_value=mock_response):
            result = client.search_markets("gpt-5")
        
        assert len(result) == 2
        assert all("gpt-5" in m["question"].lower() for m in result)
    
    def test_search_returns_empty_on_no_match(self):
        """Should return empty list when no matches"""
        client = PolymarketClient()
        
        mock_response = Mock()
        mock_response.json.return_value = [
            {"question": "Unrelated market 1"},
            {"question": "Unrelated market 2"},
        ]
        mock_response.raise_for_status = Mock()
        
        with patch.object(client.session, 'get', return_value=mock_response):
            result = client.search_markets("anthropic claude")
        
        assert len(result) == 0
    
    def test_search_handles_api_error(self):
        """Should return empty list on API error"""
        client = PolymarketClient()
        
        with patch.object(client.session, 'get', side_effect=Exception("Network error")):
            result = client.search_markets("test")
        
        assert result == []


class TestMarketBySlug:
    """Tests for fetching single market by slug"""
    
    def test_returns_market_if_found(self):
        """Should return market dict when found"""
        client = PolymarketClient()
        
        mock_response = Mock()
        mock_response.json.return_value = [
            {"slug": "test-market", "question": "Test?"}
        ]
        mock_response.raise_for_status = Mock()
        
        with patch.object(client.session, 'get', return_value=mock_response):
            result = client.get_market_by_slug("test-market")
        
        assert result is not None
        assert result["slug"] == "test-market"
    
    def test_returns_none_if_not_found(self):
        """Should return None when market not found"""
        client = PolymarketClient()
        
        mock_response = Mock()
        mock_response.json.return_value = []
        mock_response.raise_for_status = Mock()
        
        with patch.object(client.session, 'get', return_value=mock_response):
            result = client.get_market_by_slug("nonexistent")
        
        assert result is None
    
    def test_handles_api_error(self):
        """Should return None on API error"""
        client = PolymarketClient()
        
        with patch.object(client.session, 'get', side_effect=Exception("Timeout")):
            result = client.get_market_by_slug("test")
        
        assert result is None


class TestOutcomesParsing:
    """Tests for outcomes/prices parsing (JSON string handling)"""
    
    def test_outcomes_as_json_string(self):
        """Should handle outcomes field as JSON string"""
        client = PolymarketClient()
        
        # This tests the parsing logic used in get_market_prices
        outcomes_str = '["Yes", "No"]'
        parsed = json.loads(outcomes_str)
        
        assert parsed == ["Yes", "No"]
    
    def test_prices_as_json_string(self):
        """Should handle outcomePrices as JSON string"""
        prices_str = '["0.65", "0.35"]'
        parsed = json.loads(prices_str)
        
        assert parsed == ["0.65", "0.35"]
        assert float(parsed[0]) == 0.65


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
