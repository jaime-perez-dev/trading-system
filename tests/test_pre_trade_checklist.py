#!/usr/bin/env python3
"""Tests for pre_trade_checklist module."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from pre_trade_checklist import (
    check_asymmetric_risk,
    check_vague_timeline,
    check_confirmation_bias,
    check_position_size,
    check_exit_strategy,
    check_thesis_clarity,
    run_checklist,
    CheckResult,
    ChecklistResult,
)


class TestAsymmetricRisk:
    """Tests for asymmetric risk check."""
    
    def test_high_price_fails(self):
        """Entry at 95% should fail - limited upside."""
        result = check_asymmetric_risk(95.0)
        assert not result.passed
        assert result.severity in ["warning", "critical"]
        assert "upside" in result.message.lower()
    
    def test_very_high_price_is_critical(self):
        """Entry above 92% should be critical."""
        result = check_asymmetric_risk(95.0)
        assert result.severity == "critical"
    
    def test_moderate_high_price_is_warning(self):
        """Entry between 85-92% should be warning."""
        result = check_asymmetric_risk(88.0)
        assert not result.passed
        assert result.severity == "warning"
    
    def test_reasonable_price_passes(self):
        """Entry at 60% should pass."""
        result = check_asymmetric_risk(60.0)
        assert result.passed
    
    def test_low_price_passes(self):
        """Entry at 20% should pass."""
        result = check_asymmetric_risk(20.0)
        assert result.passed
    
    def test_custom_threshold(self):
        """Custom threshold should work."""
        result = check_asymmetric_risk(75.0, threshold=70.0)
        assert not result.passed


class TestVagueTimeline:
    """Tests for vague timeline language detection."""
    
    def test_coming_soon_with_tight_deadline_fails(self):
        """Vague language + tight deadline = critical failure."""
        result = check_vague_timeline(
            "OpenAI says feature coming soon",
            days_until_deadline=7
        )
        assert not result.passed
        assert result.severity == "critical"
    
    def test_coming_soon_without_deadline_warns(self):
        """Vague language without tight deadline = warning."""
        result = check_vague_timeline(
            "OpenAI says feature coming soon",
            days_until_deadline=None
        )
        assert not result.passed
        assert result.severity == "warning"
    
    def test_specific_date_passes(self):
        """Specific dates should pass."""
        result = check_vague_timeline(
            "OpenAI announces launch on January 15, 2026"
        )
        assert result.passed
    
    def test_in_the_coming_weeks_detected(self):
        """Should detect 'in the coming weeks'."""
        result = check_vague_timeline(
            "Feature expected in the coming weeks",
            days_until_deadline=7
        )
        assert not result.passed
        assert "coming weeks" in result.message.lower()
    
    def test_case_insensitive(self):
        """Detection should be case insensitive."""
        result = check_vague_timeline(
            "COMING SOON to all users",
            days_until_deadline=7
        )
        assert not result.passed


class TestConfirmationBias:
    """Tests for confirmation bias check."""
    
    def test_yes_at_high_price_warns(self):
        """Betting YES at 85%+ should warn."""
        result = check_confirmation_bias("yes", 85.0, "some thesis")
        assert not result.passed
        assert "crowd" in result.message.lower()
    
    def test_no_at_low_price_warns(self):
        """Betting NO at 15% or less should warn."""
        result = check_confirmation_bias("no", 15.0, "some thesis")
        assert not result.passed
    
    def test_yes_at_low_price_passes(self):
        """Contrarian YES at low price should pass."""
        result = check_confirmation_bias("yes", 30.0, "some thesis")
        assert result.passed
    
    def test_no_at_high_price_passes(self):
        """Contrarian NO at high price should pass."""
        result = check_confirmation_bias("no", 80.0, "some thesis")
        assert result.passed


class TestPositionSize:
    """Tests for position size check."""
    
    def test_oversized_position_fails(self):
        """Position > 10% of portfolio should fail."""
        result = check_position_size(1500, 10000, max_single_trade_pct=10.0)
        assert not result.passed
        assert "15.0%" in result.message
    
    def test_very_oversized_is_critical(self):
        """Position > 20% should be critical."""
        result = check_position_size(2500, 10000)
        assert result.severity == "critical"
    
    def test_moderate_oversized_is_warning(self):
        """Position 10-20% should be warning."""
        result = check_position_size(1500, 10000)
        assert result.severity == "warning"
    
    def test_reasonable_size_passes(self):
        """Position < 10% should pass."""
        result = check_position_size(500, 10000)
        assert result.passed


class TestExitStrategy:
    """Tests for exit strategy check."""
    
    def test_no_exit_strategy_fails(self):
        """No exit strategy should fail."""
        result = check_exit_strategy(False, False, False)
        assert not result.passed
        assert result.severity == "warning"
    
    def test_stop_loss_passes(self):
        """Having stop-loss should pass."""
        result = check_exit_strategy(True, False, False)
        assert result.passed
        assert "stop-loss" in result.message
    
    def test_take_profit_passes(self):
        """Having take-profit should pass."""
        result = check_exit_strategy(False, True, False)
        assert result.passed
    
    def test_all_exits_listed(self):
        """All exit types should be listed."""
        result = check_exit_strategy(True, True, True)
        assert result.passed
        assert "stop-loss" in result.message
        assert "take-profit" in result.message
        assert "trailing-stop" in result.message


class TestThesisClarity:
    """Tests for thesis clarity check."""
    
    def test_short_thesis_fails(self):
        """Thesis < 10 words should fail."""
        result = check_thesis_clarity("buy the dip")
        assert not result.passed
    
    def test_long_thesis_passes(self):
        """Thesis with enough words should pass."""
        thesis = "OpenAI announced ads coming and the market hasn't fully priced in the timeline based on their blog post"
        result = check_thesis_clarity(thesis)
        assert result.passed
    
    def test_custom_min_words(self):
        """Custom minimum should work."""
        result = check_thesis_clarity("short thesis works", min_words=3)
        assert result.passed


class TestFullChecklist:
    """Tests for the full checklist runner."""
    
    def test_good_trade_passes(self):
        """A well-structured trade should pass all checks."""
        result = run_checklist(
            entry_price=50.0,
            trade_amount=500,
            portfolio_value=10000,
            position_direction="yes",
            thesis="Market undervalues this because of X, Y, Z. My edge is that I have information suggesting otherwise.",
            news_text="Company announces specific launch date of February 15",
            days_until_deadline=30,
            has_stop_loss=True,
            has_take_profit=True,
        )
        assert result.all_passed
        assert len(result.critical_failures) == 0
        assert len(result.warnings) == 0
    
    def test_bad_trade_fails(self):
        """A poorly structured trade should fail."""
        result = run_checklist(
            entry_price=95.9,
            trade_amount=2000,
            portfolio_value=10000,
            position_direction="yes",
            thesis="just go",
            news_text="coming soon in the coming weeks",
            days_until_deadline=5,
            has_stop_loss=False,
            has_take_profit=False,
        )
        assert not result.all_passed
        assert len(result.critical_failures) > 0
    
    def test_summary_format(self):
        """Summary should be properly formatted."""
        result = run_checklist(
            entry_price=95.0,
            trade_amount=500,
            portfolio_value=10000,
            position_direction="yes",
            thesis="detailed thesis with many words explaining the edge",
            news_text="specific announcement",
            has_stop_loss=True,
        )
        summary = result.get_summary()
        assert isinstance(summary, str)
        assert len(summary) > 0


class TestCheckResultDataclass:
    """Tests for CheckResult dataclass."""
    
    def test_check_result_creation(self):
        """CheckResult should store all fields."""
        result = CheckResult(
            passed=True,
            check_name="Test Check",
            message="Test message",
            severity="info"
        )
        assert result.passed
        assert result.check_name == "Test Check"
        assert result.message == "Test message"
        assert result.severity == "info"


class TestChecklistResultDataclass:
    """Tests for ChecklistResult dataclass."""
    
    def test_checklist_result_creation(self):
        """ChecklistResult should store all fields."""
        result = ChecklistResult(
            all_passed=True,
            critical_failures=[],
            warnings=[],
            info=[]
        )
        assert result.all_passed
        assert len(result.critical_failures) == 0


if __name__ == "__main__":
    import subprocess
    subprocess.run(["python3", "-m", "pytest", __file__, "-v"])
