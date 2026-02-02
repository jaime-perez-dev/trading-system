#!/usr/bin/env python3
"""
Unit tests for multi_scanner.py

Tests the MultiPlatformScanner class with mocked platform clients.
No network calls required.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestParsePrice:
    """Tests for the _parse_price helper method."""
    
    def test_parse_json_string(self):
        """Parse prices from JSON string format."""
        from multi_scanner import MultiPlatformScanner
        
        with patch.object(MultiPlatformScanner, '__init__', lambda x, notify=False: None):
            scanner = MultiPlatformScanner()
            
            result = scanner._parse_price('["0.95", "0.05"]')
            assert result == 0.95
    
    def test_parse_list_directly(self):
        """Parse prices from list (already parsed)."""
        from multi_scanner import MultiPlatformScanner
        
        with patch.object(MultiPlatformScanner, '__init__', lambda x, notify=False: None):
            scanner = MultiPlatformScanner()
            
            result = scanner._parse_price([0.75, 0.25])
            assert result == 0.75
    
    def test_parse_empty_string(self):
        """Handle empty JSON string."""
        from multi_scanner import MultiPlatformScanner
        
        with patch.object(MultiPlatformScanner, '__init__', lambda x, notify=False: None):
            scanner = MultiPlatformScanner()
            
            result = scanner._parse_price('[]')
            assert result is None
    
    def test_parse_invalid_json(self):
        """Handle invalid JSON gracefully."""
        from multi_scanner import MultiPlatformScanner
        
        with patch.object(MultiPlatformScanner, '__init__', lambda x, notify=False: None):
            scanner = MultiPlatformScanner()
            
            result = scanner._parse_price('not valid json')
            assert result is None
    
    def test_parse_none_input(self):
        """Handle None input gracefully."""
        from multi_scanner import MultiPlatformScanner
        
        with patch.object(MultiPlatformScanner, '__init__', lambda x, notify=False: None):
            scanner = MultiPlatformScanner()
            
            result = scanner._parse_price(None)
            assert result is None


class TestTitlesSimilar:
    """Tests for the _titles_similar matching method."""
    
    def test_gpt_openai_match(self):
        """Titles with GPT and OpenAI should match."""
        from multi_scanner import MultiPlatformScanner
        
        with patch.object(MultiPlatformScanner, '__init__', lambda x, notify=False: None):
            scanner = MultiPlatformScanner()
            
            result = scanner._titles_similar(
                "will gpt-5 be released by openai in 2026",
                "openai gpt-5 release date prediction"
            )
            assert result is True
    
    def test_claude_anthropic_match(self):
        """Titles with Claude and Anthropic should match."""
        from multi_scanner import MultiPlatformScanner
        
        with patch.object(MultiPlatformScanner, '__init__', lambda x, notify=False: None):
            scanner = MultiPlatformScanner()
            
            result = scanner._titles_similar(
                "when will claude 4 be released by anthropic",
                "anthropic claude next version"
            )
            assert result is True
    
    def test_single_keyword_no_match(self):
        """Single keyword overlap should not match."""
        from multi_scanner import MultiPlatformScanner
        
        with patch.object(MultiPlatformScanner, '__init__', lambda x, notify=False: None):
            scanner = MultiPlatformScanner()
            
            result = scanner._titles_similar(
                "will ai take over jobs",
                "ai regulation in europe"
            )
            assert result is False  # Only 'ai' overlaps
    
    def test_no_keywords_no_match(self):
        """Titles without any tracked keywords should not match."""
        from multi_scanner import MultiPlatformScanner
        
        with patch.object(MultiPlatformScanner, '__init__', lambda x, notify=False: None):
            scanner = MultiPlatformScanner()
            
            result = scanner._titles_similar(
                "will it rain tomorrow",
                "weather forecast for next week"
            )
            assert result is False
    
    def test_case_insensitive(self):
        """Matching should be case insensitive (input already lowercased by caller)."""
        from multi_scanner import MultiPlatformScanner
        
        with patch.object(MultiPlatformScanner, '__init__', lambda x, notify=False: None):
            scanner = MultiPlatformScanner()
            
            # Note: compare_platforms() lowercases before calling _titles_similar
            result = scanner._titles_similar(
                "gpt and openai partnership",
                "openai gpt models"
            )
            assert result is True
    
    def test_bitcoin_trump_match(self):
        """Multiple non-AI keywords should also match."""
        from multi_scanner import MultiPlatformScanner
        
        with patch.object(MultiPlatformScanner, '__init__', lambda x, notify=False: None):
            scanner = MultiPlatformScanner()
            
            result = scanner._titles_similar(
                "will trump support bitcoin as president",
                "trump bitcoin reserve policy"
            )
            assert result is True


class TestScannerInitialization:
    """Tests for scanner initialization."""
    
    @patch('multi_scanner.PolymarketClient')
    @patch('multi_scanner.MetaculusClient')
    def test_init_without_kalshi(self, mock_metaculus, mock_polymarket):
        """Scanner initializes even without Kalshi SDK."""
        from multi_scanner import MultiPlatformScanner
        
        # Temporarily make Kalshi unavailable
        with patch('multi_scanner.KALSHI_SDK_AVAILABLE', False):
            scanner = MultiPlatformScanner(notify=False)
            
            assert scanner.polymarket is not None
            assert scanner.metaculus is not None
            assert scanner.kalshi is None
    
    @patch('multi_scanner.PolymarketClient')
    @patch('multi_scanner.MetaculusClient')
    def test_notifier_not_loaded_when_disabled(self, mock_metaculus, mock_polymarket):
        """Notifier should not be loaded when notify=False."""
        from multi_scanner import MultiPlatformScanner
        
        with patch('multi_scanner.KALSHI_SDK_AVAILABLE', False):
            scanner = MultiPlatformScanner(notify=False)
            
            assert scanner.notifier is None


class TestScanPolymarket:
    """Tests for Polymarket scanning."""
    
    @patch('multi_scanner.PolymarketClient')
    @patch('multi_scanner.MetaculusClient')
    def test_scan_polymarket_returns_formatted_results(self, mock_metaculus, mock_polymarket):
        """Polymarket results should be properly formatted."""
        from multi_scanner import MultiPlatformScanner
        
        # Mock the client response
        mock_client = Mock()
        mock_client.get_ai_markets.return_value = [
            {
                "condition_id": "123",
                "question": "Will GPT-5 be released?",
                "outcomePrices": '["0.85", "0.15"]',
                "volume": 50000.0,
                "slug": "gpt-5-release"
            }
        ]
        mock_polymarket.return_value = mock_client
        
        with patch('multi_scanner.KALSHI_SDK_AVAILABLE', False):
            scanner = MultiPlatformScanner(notify=False)
            results = scanner.scan_polymarket(ai_only=True)
        
        assert len(results) == 1
        assert results[0]["platform"] == "polymarket"
        assert results[0]["id"] == "123"
        assert results[0]["title"] == "Will GPT-5 be released?"
        assert results[0]["yes_price"] == 0.85
        assert results[0]["volume"] == 50000.0
        assert "polymarket.com" in results[0]["url"]
    
    @patch('multi_scanner.PolymarketClient')
    @patch('multi_scanner.MetaculusClient')
    def test_scan_polymarket_handles_missing_fields(self, mock_metaculus, mock_polymarket):
        """Scanner should handle markets with missing optional fields."""
        from multi_scanner import MultiPlatformScanner
        
        mock_client = Mock()
        mock_client.get_ai_markets.return_value = [
            {
                "id": "456",  # Using 'id' instead of 'condition_id'
                "title": "Some market",  # Using 'title' instead of 'question'
                # Missing outcomePrices, volume, slug
            }
        ]
        mock_polymarket.return_value = mock_client
        
        with patch('multi_scanner.KALSHI_SDK_AVAILABLE', False):
            scanner = MultiPlatformScanner(notify=False)
            results = scanner.scan_polymarket(ai_only=True)
        
        assert len(results) == 1
        assert results[0]["id"] == "456"
        assert results[0]["title"] == "Some market"
        assert results[0]["yes_price"] is None  # Missing prices
        assert results[0]["volume"] == 0.0  # Default


class TestScanMetaculus:
    """Tests for Metaculus scanning."""
    
    @patch('multi_scanner.PolymarketClient')
    @patch('multi_scanner.MetaculusClient')
    def test_scan_metaculus_filters_no_probability(self, mock_metaculus, mock_polymarket):
        """Questions without community probability should be filtered out."""
        from multi_scanner import MultiPlatformScanner
        
        mock_client = Mock()
        mock_client.get_ai_questions.return_value = [
            {
                "id": 1,
                "title": "Question with forecast",
                "community_probability": 0.65,
                "forecasters_count": 100,
                "url": "https://metaculus.com/q/1"
            },
            {
                "id": 2,
                "title": "Question without forecast",
                "community_probability": None,  # No forecast yet
                "forecasters_count": 0,
                "url": "https://metaculus.com/q/2"
            }
        ]
        mock_metaculus.return_value = mock_client
        
        with patch('multi_scanner.KALSHI_SDK_AVAILABLE', False):
            scanner = MultiPlatformScanner(notify=False)
            results = scanner.scan_metaculus(ai_only=True)
        
        assert len(results) == 1
        assert results[0]["id"] == 1
        assert results[0]["community_prob"] == 0.65


class TestComparePlatforms:
    """Tests for cross-platform comparison."""
    
    @patch('multi_scanner.PolymarketClient')
    @patch('multi_scanner.MetaculusClient')
    def test_compare_finds_discrepancy(self, mock_metaculus, mock_polymarket):
        """Comparison should detect significant price discrepancies."""
        from multi_scanner import MultiPlatformScanner
        
        # Mock Polymarket
        mock_pm = Mock()
        mock_pm.get_ai_markets.return_value = [
            {
                "condition_id": "pm1",
                "question": "Will OpenAI release GPT-5 by end of 2026?",
                "outcomePrices": '["0.60", "0.40"]',
                "volume": 100000,
                "slug": "gpt-5"
            }
        ]
        mock_polymarket.return_value = mock_pm
        
        # Mock Metaculus with different probability
        mock_mc = Mock()
        mock_mc.get_ai_questions.return_value = [
            {
                "id": 1,
                "title": "OpenAI GPT-5 release by 2026",
                "community_probability": 0.80,  # 20pp higher than Polymarket
                "forecasters_count": 500,
                "url": "https://metaculus.com/q/1"
            }
        ]
        mock_metaculus.return_value = mock_mc
        
        with patch('multi_scanner.KALSHI_SDK_AVAILABLE', False):
            scanner = MultiPlatformScanner(notify=False)
            opportunities = scanner.compare_platforms()
        
        assert len(opportunities) == 1
        opp = opportunities[0]
        assert opp["type"] == "metaculus_vs_polymarket"
        assert opp["metaculus_prob"] == 0.80
        assert opp["polymarket_price"] == 0.60
        assert opp["difference_pp"] == pytest.approx(20.0)  # Use approx for floating point
        assert opp["direction"] == "BUY_YES"  # Metaculus higher = buy yes on Polymarket
    
    @patch('multi_scanner.PolymarketClient')
    @patch('multi_scanner.MetaculusClient')
    def test_compare_ignores_small_discrepancy(self, mock_metaculus, mock_polymarket):
        """Discrepancies under 5pp threshold should be ignored."""
        from multi_scanner import MultiPlatformScanner
        
        mock_pm = Mock()
        mock_pm.get_ai_markets.return_value = [
            {
                "condition_id": "pm1",
                "question": "Will OpenAI release GPT-5?",
                "outcomePrices": '["0.75", "0.25"]',
                "volume": 100000,
                "slug": "gpt-5"
            }
        ]
        mock_polymarket.return_value = mock_pm
        
        mock_mc = Mock()
        mock_mc.get_ai_questions.return_value = [
            {
                "id": 1,
                "title": "OpenAI GPT-5 release",
                "community_probability": 0.78,  # Only 3pp difference
                "forecasters_count": 500,
                "url": "https://metaculus.com/q/1"
            }
        ]
        mock_metaculus.return_value = mock_mc
        
        with patch('multi_scanner.KALSHI_SDK_AVAILABLE', False):
            scanner = MultiPlatformScanner(notify=False)
            opportunities = scanner.compare_platforms()
        
        assert len(opportunities) == 0  # 3pp < 5pp threshold


class TestScanAll:
    """Tests for the scan_all method."""
    
    @patch('multi_scanner.PolymarketClient')
    @patch('multi_scanner.MetaculusClient')
    def test_scan_all_returns_all_platforms(self, mock_metaculus, mock_polymarket):
        """scan_all should return results from all platforms."""
        from multi_scanner import MultiPlatformScanner
        
        mock_pm = Mock()
        mock_pm.get_ai_markets.return_value = [{"id": "1", "question": "Q1"}]
        mock_polymarket.return_value = mock_pm
        
        mock_mc = Mock()
        mock_mc.get_ai_questions.return_value = [{"id": 1, "title": "Q1", "community_probability": 0.5}]
        mock_metaculus.return_value = mock_mc
        
        with patch('multi_scanner.KALSHI_SDK_AVAILABLE', False):
            scanner = MultiPlatformScanner(notify=False)
            results = scanner.scan_all(ai_only=True)
        
        assert "polymarket" in results
        assert "kalshi" in results
        assert "metaculus" in results
        assert "timestamp" in results
        assert len(results["polymarket"]) == 1
        assert len(results["kalshi"]) == 0  # Kalshi SDK not available
        assert len(results["metaculus"]) == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
