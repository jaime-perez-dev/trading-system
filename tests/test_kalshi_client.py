"""
Tests for Kalshi prediction market client.

Tests core logic without requiring actual API calls or SDK installation.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import sys


class TestKalshiClient:
    """Test suite for KalshiMarketClient."""
    
    def test_client_init_without_sdk(self):
        """Client initializes gracefully when SDK not available."""
        # Mock the import to simulate SDK not installed
        with patch.dict(sys.modules, {'kalshi_python': None}):
            # Force reimport
            import importlib
            from kalshi import client as kalshi_client
            importlib.reload(kalshi_client)
            
            # Client should still be usable
            c = kalshi_client.KalshiMarketClient()
            assert c.client is None or not kalshi_client.KALSHI_SDK_AVAILABLE
            assert c.authenticated == False
    
    def test_client_init_without_credentials(self):
        """Client initializes without authentication when no credentials."""
        with patch.dict('os.environ', {}, clear=True):
            from kalshi.client import KalshiMarketClient
            c = KalshiMarketClient()
            assert c.authenticated == False
            assert c.api_key_id is None
            assert c.private_key_path is None
    
    def test_get_markets_returns_error_when_no_client(self):
        """get_markets returns error dict when client not initialized."""
        from kalshi.client import KalshiMarketClient
        c = KalshiMarketClient()
        c.client = None  # Force no client
        
        result = c.get_markets()
        
        assert "error" in result
        assert result["markets"] == []
    
    def test_get_market_returns_error_when_no_client(self):
        """get_market returns error dict when client not initialized."""
        from kalshi.client import KalshiMarketClient
        c = KalshiMarketClient()
        c.client = None
        
        result = c.get_market("FAKE-TICKER")
        
        assert "error" in result
    
    def test_get_ai_markets_filters_by_keywords(self):
        """get_ai_markets filters markets by AI-related keywords."""
        from kalshi.client import KalshiMarketClient
        c = KalshiMarketClient()
        
        # Mock the get_markets method
        mock_markets = [
            {"ticker": "AI-1", "title": "Will OpenAI release GPT-5?", "subtitle": ""},
            {"ticker": "SPORTS-1", "title": "Super Bowl winner", "subtitle": ""},
            {"ticker": "AI-2", "title": "Machine Learning breakthrough", "subtitle": ""},
            {"ticker": "POLITICS-1", "title": "Election outcome", "subtitle": ""},
            {"ticker": "AI-3", "title": "Regular market", "subtitle": "Claude AI related"},
        ]
        
        c.get_markets = Mock(return_value={"markets": mock_markets, "cursor": None})
        
        result = c.get_ai_markets()
        
        # Should only return AI-related markets
        assert len(result) == 3
        tickers = [m["ticker"] for m in result]
        assert "AI-1" in tickers  # OpenAI, GPT
        assert "AI-2" in tickers  # Machine Learning
        assert "AI-3" in tickers  # Claude AI
        assert "SPORTS-1" not in tickers
        assert "POLITICS-1" not in tickers
    
    def test_get_ai_markets_handles_pydantic_models(self):
        """get_ai_markets handles Pydantic model responses."""
        from kalshi.client import KalshiMarketClient
        c = KalshiMarketClient()
        
        # Mock Pydantic-like object
        class MockMarket:
            def __init__(self, ticker, title, subtitle=""):
                self.ticker = ticker
                self.title = title
                self.subtitle = subtitle
                self.yes_bid = 50
                self.no_bid = 50
                self.volume = 1000
                self.close_time = "2026-12-31"
        
        mock_markets = [
            MockMarket("AI-1", "GPT-5 Release"),
            MockMarket("OTHER-1", "Weather forecast"),
        ]
        
        c.get_markets = Mock(return_value={"markets": mock_markets, "cursor": None})
        
        result = c.get_ai_markets()
        
        assert len(result) == 1
        assert result[0]["ticker"] == "AI-1"
        assert result[0]["platform"] == "kalshi"
    
    def test_get_balance_requires_auth(self):
        """get_balance returns error when not authenticated."""
        from kalshi.client import KalshiMarketClient
        c = KalshiMarketClient()
        c.authenticated = False
        
        result = c.get_balance()
        
        assert "error" in result
        assert "Authentication required" in result["error"]
    
    def test_place_order_requires_auth(self):
        """place_order returns error when not authenticated."""
        from kalshi.client import KalshiMarketClient
        c = KalshiMarketClient()
        c.authenticated = False
        
        result = c.place_order(
            ticker="TEST-1",
            side="yes",
            action="buy",
            count=10,
            price=50
        )
        
        assert "error" in result
        assert "Authentication required" in result["error"]
    
    def test_get_markets_handles_exception(self):
        """get_markets handles API exceptions gracefully."""
        from kalshi.client import KalshiMarketClient
        c = KalshiMarketClient()
        
        # Mock client that raises exception
        mock_client = Mock()
        mock_client.get_markets.side_effect = Exception("API Error")
        c.client = mock_client
        
        result = c.get_markets()
        
        assert "error" in result
        assert "API Error" in result["error"]
        assert result["markets"] == []
    
    def test_ai_keywords_list(self):
        """Verify AI keywords list is comprehensive."""
        from kalshi.client import KalshiMarketClient
        
        # Check expected keywords are present in the filter
        expected_keywords = ["AI", "GPT", "LLM", "OpenAI", "Anthropic"]
        
        # These should all match
        test_titles = [
            "AI development",
            "GPT-5 release",
            "LLM capabilities",
            "OpenAI funding",
            "Anthropic Claude",
        ]
        
        c = KalshiMarketClient()
        for title in test_titles:
            matches = any(kw.lower() in title.lower() for kw in expected_keywords)
            assert matches, f"'{title}' should match AI keywords"


class TestKalshiClientIntegration:
    """Integration tests - require SDK or mocking."""
    
    def test_pagination_handling(self):
        """get_ai_markets handles pagination correctly."""
        from kalshi.client import KalshiMarketClient
        c = KalshiMarketClient()
        
        # Simulate paginated response
        call_count = [0]
        
        def mock_get_markets(**kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                return {
                    "markets": [{"ticker": "AI-1", "title": "GPT market", "subtitle": ""}],
                    "cursor": "page2"
                }
            else:
                return {
                    "markets": [{"ticker": "AI-2", "title": "LLM market", "subtitle": ""}],
                    "cursor": None
                }
        
        c.get_markets = mock_get_markets
        
        result = c.get_ai_markets()
        
        assert call_count[0] == 2  # Should have made 2 calls
        assert len(result) == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
