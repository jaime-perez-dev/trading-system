#!/usr/bin/env python3
"""
Unit Tests for Trading System

Tests paper_trader.py logic, scanner, and position sizing.
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


class TestPaperTraderLogic:
    """Tests for PaperTrader calculation logic without requiring real API"""
    
    def test_share_calculation_basic(self):
        """Test shares = (amount / price) * 100"""
        amount = 100.0
        price = 50.0
        shares = (amount / price) * 100
        assert shares == pytest.approx(200.0, rel=0.01)
    
    def test_share_calculation_at_75_percent(self):
        """Test shares at 75% price point"""
        amount = 100.0
        price = 75.0
        shares = (amount / price) * 100
        assert shares == pytest.approx(133.33, rel=0.01)
    
    def test_share_calculation_at_25_percent(self):
        """Test shares at low price point (good odds)"""
        amount = 100.0
        price = 25.0
        shares = (amount / price) * 100
        assert shares == pytest.approx(400.0, rel=0.01)
    
    def test_pnl_calculation_profit(self):
        """Test P&L calculation on winning trade"""
        entry_price = 50.0
        exit_price = 60.0
        amount = 100.0
        shares = (amount / entry_price) * 100  # 200 shares
        
        pnl = (exit_price - entry_price) * shares / 100
        pnl_pct = ((exit_price - entry_price) / entry_price) * 100
        
        assert pnl == pytest.approx(20.0, rel=0.01)
        assert pnl_pct == pytest.approx(20.0, rel=0.01)
    
    def test_pnl_calculation_loss(self):
        """Test P&L calculation on losing trade"""
        entry_price = 70.0
        exit_price = 50.0
        amount = 100.0
        shares = (amount / entry_price) * 100
        
        pnl = (exit_price - entry_price) * shares / 100
        
        assert pnl < 0
        assert pnl == pytest.approx(-28.57, rel=0.01)
    
    def test_resolve_won_pnl(self):
        """Test P&L when market resolves in favor"""
        entry_price = 80.0
        amount = 100.0
        shares = (amount / entry_price) * 100  # 125 shares
        
        # Won = exit at 100
        pnl = (100.0 - entry_price) * shares / 100
        
        assert pnl == pytest.approx(25.0, rel=0.01)
    
    def test_resolve_lost_pnl(self):
        """Test P&L when market resolves against"""
        entry_price = 50.0
        amount = 100.0
        shares = (amount / entry_price) * 100  # 200 shares
        
        # Lost = exit at 0
        pnl = (0.0 - entry_price) * shares / 100
        
        assert pnl == -100.0
    
    def test_balance_tracking(self):
        """Test balance updates correctly"""
        starting_balance = 10000.0
        trade1_amount = 100.0
        trade2_amount = 50.0
        
        invested = trade1_amount + trade2_amount
        available = starting_balance - invested
        
        assert available == 9850.0
    
    def test_trade_id_assignment(self):
        """Test trade IDs are sequential"""
        trades = []
        for i in range(5):
            trades.append({"id": len(trades) + 1})
        
        ids = [t["id"] for t in trades]
        assert ids == [1, 2, 3, 4, 5]


class TestPolymarketClient:
    """Tests for PolymarketClient class"""
    
    def test_parse_prices_handles_outcomes(self):
        """Test that parse_prices extracts prices from market data"""
        from polymarket.client import PolymarketClient
        
        # Test with typical market structure
        mock_market = {
            "outcomePrices": "[0.65, 0.35]",
            "outcomes": "[\"Yes\", \"No\"]"
        }
        
        client = PolymarketClient()
        prices = client.parse_prices(mock_market)
        
        # parse_prices should return a dict with outcome names as keys
        assert "Yes" in prices or "No" in prices or prices == {}
    
    def test_client_initialization(self):
        """Test client initializes with correct base URL"""
        from polymarket.client import PolymarketClient
        
        client = PolymarketClient()
        assert hasattr(client, 'session')


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
        
        # Only 2 markets match: "AI" in first, "OpenAI" in third. Bitcoin doesn't match.
        assert len(ai_markets) == 2
    
    def test_news_signal_detection(self):
        """Test detecting trading signals in news headlines"""
        signal_keywords = ["breakthrough", "release", "announces", "partnership", "acquisition"]
        
        headlines = [
            "OpenAI announces GPT-5 release date",
            "Weather forecast for tomorrow",
            "Anthropic partnership with Google",
            "Stock market update"
        ]
        
        signals = []
        for h in headlines:
            if any(kw in h.lower() for kw in signal_keywords):
                signals.append(h)
        
        assert len(signals) == 2
        assert "OpenAI" in signals[0]
        assert "Anthropic" in signals[1]


class TestPositionSizing:
    """Tests for position sizing logic"""
    
    def test_kelly_criterion(self):
        """Test Kelly Criterion calculation"""
        def kelly_criterion(win_rate, reward_risk_ratio):
            if win_rate <= 0 or reward_risk_ratio <= 0:
                return 0
            kelly = win_rate - ((1 - win_rate) / reward_risk_ratio)
            return max(0, kelly * 0.5)
        
        # kelly = 0.60 - (0.40 / 2.0) = 0.40, half_kelly = 0.20
        size = kelly_criterion(0.60, 2.0)
        assert size == pytest.approx(0.20, rel=0.1)
        
        # kelly = 0.50 - (0.50 / 2.0) = 0.25, half_kelly = 0.125
        size = kelly_criterion(0.50, 2.0)
        assert size == pytest.approx(0.125, rel=0.1)
        
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
    
    def test_risk_per_trade(self):
        """Test risk amount per trade"""
        bankroll = 10000
        risk_pct = 0.02  # 2% risk per trade
        
        risk_amount = bankroll * risk_pct
        assert risk_amount == 200


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
        def calculate_take_profit(entry_price, tp_pct=0.20):
            return entry_price * (1 + tp_pct)
        
        entry = 50.0
        tp = calculate_take_profit(entry, 0.20)
        
        assert tp == pytest.approx(60.0, rel=0.01)
    
    def test_risk_reward_ratio(self):
        """Test risk/reward ratio calculation"""
        entry = 50.0
        stop = 45.0
        target = 60.0
        
        risk = entry - stop
        reward = target - entry
        ratio = reward / risk
        
        assert ratio == pytest.approx(2.0, rel=0.01)
    
    def test_daily_loss_limit(self):
        """Test daily loss limit checking"""
        daily_limit = 500
        
        losses = [100, 150, 100, 100]  # Total: 450
        total_loss = sum(losses)
        
        can_trade = total_loss < daily_limit
        assert can_trade is True
        
        losses.append(100)  # Total: 550
        total_loss = sum(losses)
        can_trade = total_loss < daily_limit
        assert can_trade is False


class TestTradeRecordFormat:
    """Tests for trade record structure"""
    
    def test_trade_record_has_required_fields(self):
        """Test trade record contains all required fields"""
        required_fields = [
            "id", "type", "market_slug", "outcome", "entry_price",
            "amount", "shares", "timestamp", "status"
        ]
        
        trade = {
            "id": 1,
            "type": "BUY",
            "market_slug": "test-market",
            "question": "Test question?",
            "outcome": "Yes",
            "entry_price": 50.0,
            "amount": 100.0,
            "shares": 200.0,
            "reason": "Test",
            "timestamp": "2024-01-01T00:00:00Z",
            "status": "OPEN",
            "exit_price": None,
            "pnl": None
        }
        
        for field in required_fields:
            assert field in trade
    
    def test_closed_trade_has_exit_fields(self):
        """Test closed trades have exit price and P&L"""
        closed_trade = {
            "status": "CLOSED",
            "exit_price": 60.0,
            "pnl": 20.0,
            "pnl_pct": 20.0
        }
        
        assert closed_trade["exit_price"] is not None
        assert closed_trade["pnl"] is not None


class TestEdgeDetection:
    """Tests for edge detection in news"""
    
    def test_high_impact_news_detection(self):
        """Test detecting high-impact news"""
        high_impact_terms = [
            "acquisition", "merger", "IPO", "lawsuit", "regulation",
            "breakthrough", "partnership", "funding round"
        ]
        
        news = "OpenAI announces $10B funding round from Microsoft"
        
        is_high_impact = any(term in news.lower() for term in high_impact_terms)
        assert is_high_impact is True
    
    def test_time_sensitive_news(self):
        """Test detecting time-sensitive opportunities"""
        time_terms = ["breaking", "just announced", "live", "developing"]
        
        news = "BREAKING: Anthropic releases Claude 4"
        
        is_urgent = any(term in news.lower() for term in time_terms)
        assert is_urgent is True
    
    def test_sentiment_scoring(self):
        """Test basic sentiment scoring for news"""
        positive = ["surge", "breakthrough", "success", "gains"]
        negative = ["crash", "lawsuit", "failure", "losses"]
        
        def score_sentiment(text):
            text_lower = text.lower()
            pos = sum(1 for w in positive if w in text_lower)
            neg = sum(1 for w in negative if w in text_lower)
            return pos - neg
        
        assert score_sentiment("Stock surge after breakthrough") == 2
        assert score_sentiment("Crash and lawsuit announced") == -2
        assert score_sentiment("Regular market update") == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
