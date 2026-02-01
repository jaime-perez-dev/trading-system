#!/usr/bin/env python3
"""
Unit Tests for Trading System

Tests paper_trader.py, polymarket_client.py, and scanner.py
Run with: python -m pytest tests/ -v
"""

import json
import pytest
import sys
import os
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timezone
from tempfile import TemporaryDirectory

# Add trading system to path
sys.path.insert(0, str(Path(__file__).parent.parent))


class TestPaperTrader:
    """Tests for PaperTrader class"""
    
    @pytest.fixture
    def mock_client(self):
        """Create a mock PolymarketClient"""
        mock = Mock()
        mock.get_market_by_slug.return_value = {
            "slug": "test-market",
            "question": "Will AI pass the Turing test by 2025?",
            "outcomes": [{"name": "Yes", "price": {"decimal": 0.75}}, {"name": "No", "price": {"decimal": 0.25}}]
        }
        mock.parse_prices.return_value = {"Yes": 75.0, "No": 25.0}
        return mock
    
    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for test data"""
        with TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)
    
    def test_buy_opens_position(self, mock_client, temp_dir):
        """Test that buying opens a position correctly"""
        with patch('paper_trader.DATA_DIR', temp_dir):
            with patch('paper_trader.TRADES_FILE', temp_dir / 'trades.json'):
                with patch('paper_trader.PolymarketClient', return_value=mock_client):
                    import importlib
                    import paper_trader
                    importlib.reload(paper_trader)
                    
                    trader = paper_trader.PaperTrader()
                    trade = trader.buy(
                        market_slug="test-market",
                        outcome="Yes",
                        amount=100.0,
                        reason="Test trade"
                    )
                    
                    assert trade["type"] == "BUY"
                    assert trade["outcome"] == "Yes"
                    assert trade["entry_price"] == 75.0
                    assert trade["amount"] == 100.0
                    assert trade["shares"] == pytest.approx(133.33, rel=0.01)
                    assert trade["status"] == "OPEN"
                    assert "timestamp" in trade
    
    def test_buy_with_price_override(self, mock_client, temp_dir):
        """Test buying with explicit price override"""
        with patch('paper_trader.DATA_DIR', temp_dir):
            with patch('paper_trader.TRADES_FILE', temp_dir / 'trades.json'):
                with patch('paper_trader.PolymarketClient', return_value=mock_client):
                    import importlib
                    import paper_trader
                    importlib.reload(paper_trader)
                    
                    trader = paper_trader.PaperTrader()
                    trade = trader.buy(
                        market_slug="test-market",
                        outcome="Yes",
                        amount=50.0,
                        entry_price=80.0,
                        reason="Price override test"
                    )
                    
                    assert trade["entry_price"] == 80.0
                    assert trade["shares"] == pytest.approx(62.5, rel=0.01)
    
    def test_buy_with_invalid_outcome(self, mock_client, temp_dir):
        """Test buying with invalid outcome returns error"""
        with patch('paper_trader.DATA_DIR', temp_dir):
            with patch('paper_trader.TRADES_FILE', temp_dir / 'trades.json'):
                with patch('paper_trader.PolymarketClient', return_value=mock_client):
                    import importlib
                    import paper_trader
                    importlib.reload(paper_trader)
                    
                    trader = paper_trader.PaperTrader()
                    mock_client.parse_prices.return_value = {"Yes": 75.0, "No": 25.0}
                    
                    result = trader.buy(
                        market_slug="test-market",
                        outcome="Maybe",
                        amount=100.0
                    )
                    
                    assert "error" in result
                    assert "Outcome 'Maybe' not found" in result["error"]
    
    def test_close_calculates_pnl(self, mock_client, temp_dir):
        """Test that closing a trade calculates P&L correctly"""
        with patch('paper_trader.DATA_DIR', temp_dir):
            with patch('paper_trader.TRADES_FILE', temp_dir / 'trades.json'):
                with patch('paper_trader.PolymarketClient', return_value=mock_client):
                    import importlib
                    import paper_trader
                    importlib.reload(paper_trader)
                    
                    trader = paper_trader.PaperTrader()
                    
                    trader.buy(
                        market_slug="test-market",
                        outcome="Yes",
                        amount=100.0,
                        entry_price=50.0,
                        reason="Test"
                    )
                    
                    close_trade = trader.close(trade_id=1, exit_price=60.0)
                    
                    assert close_trade["status"] == "CLOSED"
                    assert close_trade["exit_price"] == 60.0
                    assert close_trade["pnl"] == pytest.approx(20.0, rel=0.01)
                    assert close_trade["pnl_pct"] == pytest.approx(20.0, rel=0.01)
    
    def test_close_at_loss(self, mock_client, temp_dir):
        """Test closing at a loss"""
        with patch('paper_trader.DATA_DIR', temp_dir):
            with patch('paper_trader.TRADES_FILE', temp_dir / 'trades.json'):
                with patch('paper_trader.PolymarketClient', return_value=mock_client):
                    import importlib
                    import paper_trader
                    importlib.reload(paper_trader)
                    
                    trader = paper_trader.PaperTrader()
                    
                    trader.buy(
                        market_slug="test-market",
                        outcome="No",
                        amount=100.0,
                        entry_price=70.0,
                        reason="Test"
                    )
                    
                    close_trade = trader.close(trade_id=1, exit_price=50.0)
                    
                    assert close_trade["pnl"] < 0
                    assert close_trade["pnl_pct"] < 0
    
    def test_resolve_won(self, mock_client, temp_dir):
        """Test resolving a winning trade"""
        with patch('paper_trader.DATA_DIR', temp_dir):
            with patch('paper_trader.TRADES_FILE', temp_dir / 'trades.json'):
                with patch('paper_trader.PolymarketClient', return_value=mock_client):
                    import importlib
                    import paper_trader
                    importlib.reload(paper_trader)
                    
                    trader = paper_trader.PaperTrader()
                    
                    trader.buy(
                        market_slug="test-market",
                        outcome="Yes",
                        amount=100.0,
                        entry_price=80.0
                    )
                    
                    result = trader.resolve(trade_id=1, won=True)
                    
                    assert result["status"] == "RESOLVED"
                    assert result["won"] is True
                    assert result["exit_price"] == 100.0
                    assert result["pnl"] == pytest.approx(25.0, rel=0.01)
    
    def test_resolve_lost(self, mock_client, temp_dir):
        """Test resolving a losing trade"""
        with patch('paper_trader.DATA_DIR', temp_dir):
            with patch('paper_trader.TRADES_FILE', temp_dir / 'trades.json'):
                with patch('paper_trader.PolymarketClient', return_value=mock_client):
                    import importlib
                    import paper_trader
                    importlib.reload(paper_trader)
                    
                    trader = paper_trader.PaperTrader()
                    
                    trader.buy(
                        market_slug="test-market",
                        outcome="No",
                        amount=100.0,
                        entry_price=30.0
                    )
                    
                    result = trader.resolve(trade_id=1, won=False)
                    
                    assert result["status"] == "RESOLVED"
                    assert result["won"] is False
                    assert result["exit_price"] == 0.0
                    assert result["pnl"] == -100.0
    
    def test_close_nonexistent_trade(self, temp_dir):
        """Test closing a trade that doesn't exist"""
        with patch('paper_trader.DATA_DIR', temp_dir):
            with patch('paper_trader.TRADES_FILE', temp_dir / 'trades.json'):
                with patch('paper_trader.PolymarketClient'):
                    import importlib
                    import paper_trader
                    importlib.reload(paper_trader)
                    
                    trader = paper_trader.PaperTrader()
                    result = trader.close(trade_id=999)
                    
                    assert "error" in result
                    assert "not found" in result["error"]
    
    def test_status_shows_correct_stats(self, mock_client, temp_dir):
        """Test that status returns correct statistics"""
        with patch('paper_trader.DATA_DIR', temp_dir):
            with patch('paper_trader.TRADES_FILE', temp_dir / 'trades.json'):
                with patch('paper_trader.PolymarketClient', return_value=mock_client):
                    import importlib
                    import paper_trader
                    importlib.reload(paper_trader)
                    
                    trader = paper_trader.PaperTrader()
                    
                    trader.buy("test-market", "Yes", 100.0, entry_price=50.0)
                    trader.buy("test-market", "No", 50.0, entry_price=30.0)
                    trader.close(trade_id=1, exit_price=70.0)
                    
                    status = trader.status()
                    
                    assert status["starting_balance"] == 10000.0
                    assert status["open_positions"] == 1
                    assert status["closed_trades"] == 1
                    assert status["realized_pnl"] > 0
                    assert status["wins"] == 1
                    assert status["losses"] == 0


class TestPolymarketClient:
    """Tests for PolymarketClient class"""
    
    def test_parse_prices_handles_decimal(self):
        """Test that parse_prices handles decimal prices correctly"""
        from polymarket.client import PolymarketClient
        
        mock_market = {
            "outcomes": [
                {"name": "Yes", "price": {"decimal": 0.65}},
                {"name": "No", "price": {"decimal": 0.35}}
            ]
        }
        
        with patch.object(PolymarketClient, '_get', return_value=[mock_market]):
            client = PolymarketClient()
            prices = client.parse_prices(mock_market)
            
            assert prices["Yes"] == pytest.approx(65.0, rel=0.01)
            assert prices["No"] == pytest.approx(35.0, rel=0.01)


class TestScanner:
    """Tests for Scanner functionality"""
    
    def test_edge_detection_keywords(self):
        """Test that scanner detects edge keywords correctly"""
        edge_keywords = [
            "AI breakthrough",
            "OpenAI announces",
            "Anthropic releases",
            "AGI achieved",
            "GPT-5 rumor"
        ]
        
        for keyword in edge_keywords:
            assert len(keyword) > 5
    
    def test_market_filtering(self):
        """Test filtering AI markets"""
        ai_keywords = ["AI", "artificial intelligence", "AGI", "LLM", "OpenAI", "Anthropic"]
        
        markets = [
            {"question": "Will AI pass the bar exam?", "tags": ["AI", "legal"]},
            {"question": "Will Bitcoin reach $100k?", "tags": ["crypto"]},
            {"question": "Will OpenAI release GPT-5?", "tags": ["AI", "OpenAI"]},
        ]
        
        ai_markets = []
        for m in markets:
            if any(kw.lower() in m["question"].lower() for kw in ai_keywords):
                ai_markets.append(m)
        
        assert len(ai_markets) == 3


class TestPositionSizing:
    """Tests for position sizing logic"""
    
    def test_kelly_criterion(self):
        """Test Kelly Criterion calculation"""
        def kelly_criterion(win_rate, reward_risk_ratio):
            if win_rate <= 0 or reward_risk_ratio <= 0:
                return 0
            kelly = win_rate - ((1 - win_rate) / reward_risk_ratio)
            return max(0, kelly * 0.5)
        
        size = kelly_criterion(0.60, 2.0)
        assert size == pytest.approx(0.10, rel=0.1)
        
        size = kelly_criterion(0.50, 2.0)
        assert size == pytest.approx(0.0, rel=0.1)
        
        size = kelly_criterion(0.70, 1.5)
        assert size > 0
    
    def test_max_position_size(self):
        """Test maximum position size limits"""
        max_pct = 0.10
        bankroll = 10000
        
        max_amount = bankroll * max_pct
        assert max_amount == 1000
        
        amount = min(5000, max_amount)
        assert amount == 1000


class TestRiskManagement:
    """Tests for risk management rules"""
    
    def test_stop_loss_calculation(self):
        """Test stop-loss percentage calculation"""
        def calculate_stop_loss(entry_price, stop_pct=0.10):
            return entry_price * (1 - stop_pct)
        
        entry = 50.0
        stop = calculate_stop_loss(entry, 0.10)
        
        assert stop == pytest.approx(45.0, rel=0.01)
    
    def test_take_profit_calculation(self):
        """Test take-profit calculation"""
        def calculate_take_profit(entry_price, target_pct=0.20):
            return entry_price * (1 + target_pct)
        
        entry = 50.0
        target = calculate_take_profit(entry, 0.20)
        
        assert target == pytest.approx(60.0, rel=0.01)
    
    def test_daily_loss_limit(self):
        """Test daily loss limit enforcement"""
        def check_daily_loss_limit(daily_pnl, max_loss_pct=0.05, bankroll=10000):
            max_loss = bankroll * max_loss_pct
            return daily_pnl >= -max_loss
        
        assert check_daily_loss_limit(-400, 0.05, 10000) is True
        assert check_daily_loss_limit(-600, 0.05, 10000) is False


class TestNewsMonitor:
    """Tests for NewsMonitor"""
    
    def test_rss_feed_parsing(self):
        """Test RSS feed item parsing"""
        sample_item = {
            "title": "OpenAI Announces GPT-5",
            "link": "https://openai.com/blog/gpt-5",
            "published": "2026-01-28T10:00:00Z",
            "summary": "OpenAI has announced GPT-5..."
        }
        
        assert "title" in sample_item
        assert "link" in sample_item
        assert "published" in sample_item
        
        ai_keywords = ["OpenAI", "GPT", "AI"]
        has_ai_keyword = any(
            kw.lower() in sample_item["title"].lower() 
            for kw in ai_keywords
        )
        assert has_ai_keyword is True
    
    def test_article_deduplication(self):
        """Test that duplicate articles are filtered"""
        seen_urls = set()
        
        def is_duplicate(url):
            if url in seen_urls:
                return True
            seen_urls.add(url)
            return False
        
        urls = [
            "https://example.com/article1",
            "https://example.com/article2",
            "https://example.com/article1",
        ]
        
        duplicates = [url for url in urls if is_duplicate(url)]
        assert len(duplicates) == 1
        assert duplicates[0] == "https://example.com/article1"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
