#!/usr/bin/env python3
"""Unit tests for correlation tracker."""

import json
import pytest
import tempfile
from pathlib import Path
from unittest.mock import patch

from correlation_tracker import (
    CorrelationTracker, 
    CorrelationCheck,
    NARRATIVES,
)


@pytest.fixture
def temp_dir():
    """Create temp directory for test data."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def tracker(temp_dir):
    """Create tracker with temp files."""
    positions_file = temp_dir / "positions.json"
    correlations_file = temp_dir / "correlations.json"
    return CorrelationTracker(positions_file, correlations_file)


@pytest.fixture
def tracker_with_positions(temp_dir):
    """Create tracker with some open positions."""
    positions_file = temp_dir / "positions.json"
    correlations_file = temp_dir / "correlations.json"
    
    positions_data = {
        "positions": [
            {
                "id": 1,
                "market_name": "Will OpenAI release GPT-5 by June 2026?",
                "market_slug": "openai-gpt5-june-2026",
                "shares": 100,
                "entry_price": 45,  # 45 cents
                "status": "open",
            },
            {
                "id": 2,
                "market_name": "Will Anthropic raise another funding round?",
                "market_slug": "anthropic-funding-2026",
                "shares": 200,
                "entry_price": 60,
                "status": "open",
            },
            {
                "id": 3,
                "market_name": "Will Trump win 2026 election?",
                "market_slug": "trump-2026-election",
                "shares": 150,
                "entry_price": 50,
                "status": "open",
            },
            {
                "id": 4,
                "market_name": "Closed position",
                "market_slug": "closed-market",
                "shares": 500,
                "entry_price": 80,
                "status": "closed",  # Should be excluded
            },
            {
                "id": 5,
                "market_name": "Test position",
                "market_slug": "test-market",
                "shares": 100,
                "entry_price": 50,
                "status": "open",
                "is_test": True,  # Should be excluded
            },
        ]
    }
    
    positions_file.write_text(json.dumps(positions_data))
    return CorrelationTracker(positions_file, correlations_file)


class TestNarrativeDetection:
    """Tests for auto-detecting narrative from market names."""
    
    def test_detects_ai_companies(self, tracker):
        """Should detect AI company narrative."""
        assert tracker.detect_narrative("Will OpenAI release GPT-5?") == "ai_companies"
        assert tracker.detect_narrative("Anthropic valuation above $50B") == "ai_companies"
        assert tracker.detect_narrative("Google AI announces Gemini 2") == "ai_companies"
        assert tracker.detect_narrative("Meta AI releases Llama 4") == "ai_companies"
    
    def test_detects_ai_regulation(self, tracker):
        """Should detect AI regulation narrative."""
        assert tracker.detect_narrative("EU AI Act implementation") == "ai_regulation"
        assert tracker.detect_narrative("Congress passes AI safety bill") == "ai_regulation"
        assert tracker.detect_narrative("Executive order on AI") == "ai_regulation"
    
    def test_detects_elections(self, tracker):
        """Should detect election narrative."""
        assert tracker.detect_narrative("Trump wins 2026 election") == "elections_us"
        assert tracker.detect_narrative("Biden approval rating") == "elections_us"
        assert tracker.detect_narrative("Republican takes Senate") == "elections_us"
    
    def test_detects_crypto(self, tracker):
        """Should detect crypto narrative."""
        assert tracker.detect_narrative("Bitcoin reaches $100k") == "crypto"
        assert tracker.detect_narrative("Ethereum merge success") == "crypto"
        assert tracker.detect_narrative("SEC crypto regulation") == "crypto"
    
    def test_detects_tech_earnings(self, tracker):
        """Should detect tech earnings narrative."""
        assert tracker.detect_narrative("NVIDIA Q4 earnings beat") == "tech_earnings"
        assert tracker.detect_narrative("Apple revenue guidance") == "tech_earnings"
        assert tracker.detect_narrative("Microsoft quarterly results") == "tech_earnings"
    
    def test_detects_geopolitics(self, tracker):
        """Should detect geopolitical narrative."""
        assert tracker.detect_narrative("China Taiwan tensions") == "geopolitics"
        assert tracker.detect_narrative("Russia sanctions expanded") == "geopolitics"
        assert tracker.detect_narrative("Ukraine war escalation") == "geopolitics"
    
    def test_returns_none_for_unknown(self, tracker):
        """Should return None for unrecognized markets."""
        assert tracker.detect_narrative("Random unrelated market") is None
        assert tracker.detect_narrative("Sports outcome") is None
    
    def test_case_insensitive(self, tracker):
        """Should be case insensitive."""
        assert tracker.detect_narrative("OPENAI GPT-5") == "ai_companies"
        assert tracker.detect_narrative("openai gpt-5") == "ai_companies"
        assert tracker.detect_narrative("OpenAI GPT-5") == "ai_companies"
    
    def test_uses_slug_for_detection(self, tracker):
        """Should use market slug in detection."""
        # Name doesn't match but slug does
        assert tracker.detect_narrative("Some market", "openai-product-launch") == "ai_companies"


class TestCustomCorrelations:
    """Tests for manual market tagging."""
    
    def test_add_custom_correlation(self, tracker):
        """Should add custom correlation."""
        tracker.add_correlation("my-market", "crypto")
        assert tracker.detect_narrative("Unrelated name", "my-market") == "crypto"
    
    def test_remove_custom_correlation(self, tracker):
        """Should remove custom correlation."""
        tracker.add_correlation("my-market", "crypto")
        tracker.remove_correlation("my-market")
        assert tracker.detect_narrative("Unrelated name", "my-market") is None
    
    def test_custom_overrides_auto(self, tracker):
        """Custom tag should override auto-detection."""
        # This would auto-detect as ai_companies
        tracker.add_correlation("openai-market", "geopolitics")
        assert tracker.detect_narrative("OpenAI news", "openai-market") == "geopolitics"
    
    def test_invalid_narrative_raises(self, tracker):
        """Should raise for invalid narrative name."""
        with pytest.raises(ValueError) as exc_info:
            tracker.add_correlation("market", "invalid_narrative")
        assert "Unknown narrative" in str(exc_info.value)
    
    def test_persistence(self, temp_dir):
        """Custom correlations should persist."""
        positions_file = temp_dir / "positions.json"
        correlations_file = temp_dir / "correlations.json"
        
        # Create tracker and add correlation
        tracker1 = CorrelationTracker(positions_file, correlations_file)
        tracker1.add_correlation("my-market", "crypto")
        
        # Create new tracker instance
        tracker2 = CorrelationTracker(positions_file, correlations_file)
        assert tracker2.detect_narrative("", "my-market") == "crypto"


class TestPositionLoading:
    """Tests for loading positions."""
    
    def test_empty_when_no_file(self, tracker):
        """Should return empty list when no positions file."""
        assert tracker.get_positions() == []
    
    def test_loads_open_positions(self, tracker_with_positions):
        """Should load only open positions."""
        positions = tracker_with_positions.get_positions()
        assert len(positions) == 3  # Excludes closed and test
    
    def test_excludes_closed(self, tracker_with_positions):
        """Should exclude closed positions."""
        positions = tracker_with_positions.get_positions()
        slugs = [p["market_slug"] for p in positions]
        assert "closed-market" not in slugs
    
    def test_excludes_test(self, tracker_with_positions):
        """Should exclude test positions."""
        positions = tracker_with_positions.get_positions()
        slugs = [p["market_slug"] for p in positions]
        assert "test-market" not in slugs


class TestPortfolioValue:
    """Tests for portfolio value calculation."""
    
    def test_zero_when_empty(self, tracker):
        """Should return 0 for empty portfolio."""
        assert tracker.get_portfolio_value() == 0.0
    
    def test_calculates_value(self, tracker_with_positions):
        """Should calculate total portfolio value."""
        # Position 1: 100 shares * $0.45 = $45
        # Position 2: 200 shares * $0.60 = $120
        # Position 3: 150 shares * $0.50 = $75
        # Total: $240
        value = tracker_with_positions.get_portfolio_value()
        assert value == 240.0


class TestNarrativeExposure:
    """Tests for narrative exposure calculation."""
    
    def test_exposure_empty_portfolio(self, tracker):
        """Should return 0 exposure for empty portfolio."""
        exposure, positions = tracker.get_narrative_exposure("ai_companies")
        assert exposure == 0.0
        assert positions == []
    
    def test_exposure_with_positions(self, tracker_with_positions):
        """Should calculate exposure correctly."""
        # AI positions: OpenAI ($45) + Anthropic ($120) = $165
        exposure, positions = tracker_with_positions.get_narrative_exposure("ai_companies")
        assert exposure == 165.0
        assert len(positions) == 2
    
    def test_exposure_different_narrative(self, tracker_with_positions):
        """Should separate narratives correctly."""
        # Election position: Trump ($75)
        exposure, positions = tracker_with_positions.get_narrative_exposure("elections_us")
        assert exposure == 75.0
        assert len(positions) == 1


class TestCorrelationCheck:
    """Tests for the main correlation check logic."""
    
    def test_allows_no_narrative(self, tracker):
        """Should allow trades with no detected narrative."""
        result = tracker.check_correlation("Random market", "", 100)
        assert result.allowed is True
        assert result.narrative is None
    
    def test_allows_under_limit(self, tracker_with_positions):
        """Should allow trades under the limit."""
        # Current AI exposure: $165 / $240 = 68.75%
        # But max is 40%, so we're already over!
        # Let's check a small crypto trade instead
        result = tracker_with_positions.check_correlation(
            "Bitcoin $150k", "bitcoin-150k", 10
        )
        # Crypto has 0 exposure, so this should be allowed
        assert result.allowed is True
        assert result.narrative == "crypto"
    
    def test_blocks_over_limit(self, tracker_with_positions):
        """Should block trades that exceed limit."""
        # Try to add another large AI position
        result = tracker_with_positions.check_correlation(
            "Google AI launches AGI", "google-agi", 200
        )
        # This would put AI at ($165 + $200) / ($240 + $200) = 82.9%
        # Max is 40%, so should be blocked
        assert result.allowed is False
        assert result.narrative == "ai_companies"
        assert "exceed" in result.warning.lower()
    
    def test_warns_approaching_limit(self, temp_dir):
        """Should warn when approaching limit."""
        # Create a portfolio close to the limit
        positions_file = temp_dir / "positions.json"
        positions_data = {
            "positions": [
                {
                    "id": 1,
                    "market_name": "Some crypto market",
                    "market_slug": "bitcoin-price",
                    "shares": 100,
                    "entry_price": 20,  # $20 value
                    "status": "open",
                }
            ]
        }
        positions_file.write_text(json.dumps(positions_data))
        tracker = CorrelationTracker(positions_file, temp_dir / "corr.json")
        
        # Try to add another crypto position that brings us close to 25% limit
        result = tracker.check_correlation("Ethereum $10k", "eth-10k", 5)
        # Current: $20, adding $5, total $25
        # Crypto exposure: $25/$25 = 100%, but max is 25%
        # This should be blocked
        assert result.allowed is False
    
    def test_includes_correlated_positions(self, tracker_with_positions):
        """Should list other correlated positions."""
        result = tracker_with_positions.check_correlation(
            "Claude 4 release", "claude-4", 50
        )
        assert len(result.other_positions) == 2  # OpenAI and Anthropic positions
    
    def test_handles_empty_portfolio_new_trade(self, tracker):
        """Should handle first trade in empty portfolio."""
        result = tracker.check_correlation("OpenAI news", "openai-news", 100)
        # First trade to a single narrative = 100% exposure, which exceeds 40% limit
        # This is correct behavior - prevents all-in bets on correlated assets
        assert result.allowed is False
        assert result.current_exposure_pct == 0.0
        assert result.would_be_exposure_pct == 100.0  # 100% of new portfolio
        assert "exceed" in result.warning.lower()
    
    def test_allows_first_uncorrelated_trade(self, tracker):
        """Should allow first trade with no narrative."""
        result = tracker.check_correlation("Random sports bet", "", 100)
        assert result.allowed is True  # No narrative = no limit
        assert result.narrative is None


class TestExposureSummary:
    """Tests for exposure summary report."""
    
    def test_empty_portfolio(self, tracker):
        """Should handle empty portfolio."""
        summary = tracker.get_exposure_summary()
        assert summary["portfolio_value"] == 0.0
        assert summary["narratives"] == {}
    
    def test_shows_all_exposures(self, tracker_with_positions):
        """Should show all narrative exposures."""
        summary = tracker_with_positions.get_exposure_summary()
        
        assert summary["portfolio_value"] == 240.0
        assert "ai_companies" in summary["narratives"]
        assert "elections_us" in summary["narratives"]
        
        ai = summary["narratives"]["ai_companies"]
        assert ai["exposure"] == 165.0
        assert ai["exposure_pct"] == pytest.approx(68.75, rel=0.01)
        assert ai["max_pct"] == 40


class TestNarrativesConfig:
    """Tests for narrative configuration."""
    
    def test_all_narratives_have_keywords(self):
        """All narratives should have keywords."""
        for name, config in NARRATIVES.items():
            assert "keywords" in config
            assert len(config["keywords"]) > 0
    
    def test_all_narratives_have_max_exposure(self):
        """All narratives should have max exposure."""
        for name, config in NARRATIVES.items():
            assert "max_exposure_pct" in config
            assert 0 < config["max_exposure_pct"] <= 100
    
    def test_all_narratives_have_description(self):
        """All narratives should have description."""
        for name, config in NARRATIVES.items():
            assert "description" in config
            assert len(config["description"]) > 0


class TestCorrelationCheckDataclass:
    """Tests for CorrelationCheck dataclass."""
    
    def test_default_values(self):
        """Should have sensible defaults."""
        check = CorrelationCheck(allowed=True)
        assert check.narrative is None
        assert check.current_exposure_pct == 0.0
        assert check.max_exposure_pct == 100.0
        assert check.would_be_exposure_pct == 0.0
        assert check.warning is None
        assert check.other_positions == []
    
    def test_all_fields(self):
        """Should accept all fields."""
        check = CorrelationCheck(
            allowed=False,
            narrative="ai_companies",
            current_exposure_pct=30.0,
            max_exposure_pct=40.0,
            would_be_exposure_pct=50.0,
            warning="Over limit",
            other_positions=[{"id": 1}]
        )
        assert check.allowed is False
        assert check.narrative == "ai_companies"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
