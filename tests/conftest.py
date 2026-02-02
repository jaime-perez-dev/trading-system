"""
Pytest configuration and shared fixtures
"""

import pytest
import sys
from pathlib import Path

# Ensure parent module is importable
sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.fixture
def sample_market():
    """Standard test market data"""
    return {
        "id": "test-123",
        "question": "Will OpenAI release GPT-5 by Q2 2026?",
        "slug": "openai-gpt5-q2-2026",
        "endDate": "2026-06-30T23:59:59Z",
        "outcomes": [
            {"name": "Yes", "price": 0.42},
            {"name": "No", "price": 0.58}
        ],
        "volume24hr": 25000,
        "liquidity": 150000
    }


@pytest.fixture
def sample_trade():
    """Standard test trade"""
    return {
        "id": 1,
        "type": "BUY",
        "market_slug": "openai-gpt5-q2-2026",
        "question": "Will OpenAI release GPT-5 by Q2 2026?",
        "outcome": "Yes",
        "entry_price": 0.42,
        "amount": 200.0,
        "shares": 476.19,  # (200/0.42)*100
        "reason": "GPT-5 development confirmed, expecting Q2 release",
        "timestamp": "2026-02-01T21:00:00Z",
        "status": "OPEN",
        "exit_price": None,
        "pnl": None
    }


@pytest.fixture 
def sample_news():
    """Standard test news item"""
    return {
        "title": "OpenAI announces major breakthrough in reasoning capabilities",
        "source": "TechCrunch",
        "url": "https://techcrunch.com/openai-breakthrough",
        "published": "2026-02-01T20:00:00Z",
        "entities": ["OpenAI"],
        "sentiment": "positive"
    }
