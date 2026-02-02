import pytest
from risk_manager import RiskManager, RiskConfig, Position, NARRATIVE_KEYWORDS


class TestRiskManager:
    @pytest.fixture
    def manager(self):
        return RiskManager()

    def test_default_config(self, manager):
        assert manager.config.max_position_size == 100.0
        assert manager.config.asymmetric_risk_threshold == 85.0
        assert manager.config.max_market_exposure == 300.0
        assert manager.config.max_narrative_exposure == 500.0
        assert manager.config.max_daily_loss_pct == 5.0

    def test_check_trade_limits_valid(self, manager):
        allowed, msg = manager.check_trade_limits(
            amount=50.0, 
            open_positions_count=2, 
            daily_pnl=0.0
        )
        assert allowed is True
        assert msg == "OK"

    def test_check_trade_limits_size_exceeded(self, manager):
        allowed, msg = manager.check_trade_limits(
            amount=150.0, 
            open_positions_count=2, 
            daily_pnl=0.0
        )
        assert allowed is False
        assert "exceeds max position size" in msg

    def test_check_trade_limits_count_exceeded(self, manager):
        allowed, msg = manager.check_trade_limits(
            amount=50.0, 
            open_positions_count=5, 
            daily_pnl=0.0
        )
        assert allowed is False
        assert "max positions" in msg

    def test_check_trade_limits_drawdown_exceeded(self, manager):
        allowed, msg = manager.check_trade_limits(
            amount=50.0, 
            open_positions_count=2, 
            daily_pnl=-60.0
        )
        assert allowed is False
        assert "Daily loss limit" in msg

    def test_asymmetric_risk_warning(self, manager):
        # > 85%
        msg = manager.check_asymmetric_risk(90.0)
        assert msg is not None
        assert "ASYMMETRIC RISK WARNING" in msg
        assert "Entry at 90.0%" in msg
        
        # <= 85%
        msg = manager.check_asymmetric_risk(80.0)
        assert msg is None

    def test_kelly_size(self, manager):
        # 60% win prob, 2.0 odds (even money, 1:1)
        # b = 1
        # p = 0.6
        # q = 0.4
        # f = (1 * 0.6 - 0.4) / 1 = 0.2
        # safe_f = 0.2 * 0.25 = 0.05
        # bankroll = 1000
        # size = 50
        
        size = manager.calculate_kelly_size(0.6, 2.0, 1000.0)
        assert size == pytest.approx(50.0)

    def test_kelly_size_negative(self, manager):
        # 40% win prob, 2.0 odds -> negative expectation
        # f = (1 * 0.4 - 0.6) / 1 = -0.2
        size = manager.calculate_kelly_size(0.4, 2.0, 1000.0)
        assert size == 0.0


class TestMarketExposure:
    @pytest.fixture
    def manager(self):
        return RiskManager()
    
    def test_market_exposure_no_position(self, manager):
        """First position in a market should be allowed."""
        allowed, msg = manager.check_market_exposure("gpt-5-release", 100.0)
        assert allowed is True
        assert msg == "OK"
    
    def test_market_exposure_under_limit(self, manager):
        """Adding to position should be allowed under limit."""
        manager.add_position(Position(
            market_slug="gpt-5-release",
            market_title="Will GPT-5 be released by June?",
            amount=100.0,
            entry_price=45.0,
            side="yes"
        ))
        
        allowed, msg = manager.check_market_exposure("gpt-5-release", 100.0)
        assert allowed is True
        assert msg == "OK"
    
    def test_market_exposure_exceeds_limit(self, manager):
        """Should block when market exposure exceeds limit."""
        manager.add_position(Position(
            market_slug="gpt-5-release",
            market_title="Will GPT-5 be released by June?",
            amount=250.0,
            entry_price=45.0,
            side="yes"
        ))
        
        # 250 + 100 = 350 > 300 limit
        allowed, msg = manager.check_market_exposure("gpt-5-release", 100.0)
        assert allowed is False
        assert "would exceed limit" in msg
        assert "gpt-5-release" in msg
    
    def test_market_exposure_different_market(self, manager):
        """Exposure to one market shouldn't affect another."""
        manager.add_position(Position(
            market_slug="gpt-5-release",
            market_title="Will GPT-5 be released by June?",
            amount=300.0,
            entry_price=45.0,
            side="yes"
        ))
        
        # Different market, should be allowed
        allowed, msg = manager.check_market_exposure("claude-4-release", 100.0)
        assert allowed is True
        assert msg == "OK"


class TestNarrativeExposure:
    @pytest.fixture
    def manager(self):
        return RiskManager()
    
    def test_detect_narratives_ai_progress(self, manager):
        """Should detect ai_progress narrative."""
        narratives = manager._detect_narratives("Will GPT-5 benchmark beat Claude?")
        assert "ai_progress" in narratives
    
    def test_detect_narratives_ai_regulation(self, manager):
        """Should detect ai_regulation narrative."""
        narratives = manager._detect_narratives("Will Congress pass AI regulation bill?")
        assert "ai_regulation" in narratives
    
    def test_detect_narratives_multiple(self, manager):
        """Should detect multiple narratives."""
        narratives = manager._detect_narratives("Will EU ban GPT-5 release?")
        assert "ai_regulation" in narratives
        assert "ai_release" in narratives
    
    def test_detect_narratives_none(self, manager):
        """Should return empty list for unrelated market."""
        narratives = manager._detect_narratives("Will Bitcoin reach 100k?")
        assert narratives == []
    
    def test_narrative_exposure_under_limit(self, manager):
        """Should allow when narrative exposure under limit."""
        manager.add_position(Position(
            market_slug="gpt-5-release",
            market_title="Will GPT-5 be released by June?",
            amount=200.0,
            entry_price=45.0,
            side="yes",
            narratives=["ai_release"]
        ))
        
        # Same narrative, but under 500 limit
        allowed, msg = manager.check_narrative_exposure("Claude 4 release date", 200.0)
        assert allowed is True
        assert msg == "OK"
    
    def test_narrative_exposure_exceeds_limit(self, manager):
        """Should block when narrative exposure exceeds limit."""
        manager.add_position(Position(
            market_slug="gpt-5-release",
            market_title="Will GPT-5 be released by June?",
            amount=400.0,
            entry_price=45.0,
            side="yes",
            narratives=["ai_release"]
        ))
        
        # 400 + 200 = 600 > 500 limit
        allowed, msg = manager.check_narrative_exposure("Claude 4 release date", 200.0)
        assert allowed is False
        assert "ai_release" in msg
        assert "would exceed limit" in msg
    
    def test_narrative_exposure_different_narrative(self, manager):
        """Different narrative should have separate limit."""
        manager.add_position(Position(
            market_slug="gpt-5-release",
            market_title="Will GPT-5 be released by June?",
            amount=500.0,
            entry_price=45.0,
            side="yes",
            narratives=["ai_release"]
        ))
        
        # Different narrative (regulation), should be allowed
        allowed, msg = manager.check_narrative_exposure("Will EU regulate AI?", 200.0)
        assert allowed is True
        assert msg == "OK"


class TestExposureSummary:
    @pytest.fixture
    def manager(self):
        return RiskManager()
    
    def test_exposure_summary_empty(self, manager):
        """Empty positions should return zeros."""
        summary = manager.get_exposure_summary()
        assert summary["total_exposure"] == 0
        assert summary["position_count"] == 0
        assert summary["market_exposure"] == {}
        assert summary["narrative_exposure"] == {}
    
    def test_exposure_summary_with_positions(self, manager):
        """Should calculate exposure correctly."""
        manager.add_position(Position(
            market_slug="gpt-5-release",
            market_title="Will GPT-5 be released by June?",
            amount=200.0,
            entry_price=45.0,
            side="yes",
            narratives=["ai_release", "ai_progress"]
        ))
        manager.add_position(Position(
            market_slug="ai-regulation",
            market_title="Will Congress pass AI regulation?",
            amount=100.0,
            entry_price=30.0,
            side="no",
            narratives=["ai_regulation"]
        ))
        
        summary = manager.get_exposure_summary()
        assert summary["total_exposure"] == 300.0
        assert summary["position_count"] == 2
        assert summary["market_exposure"]["gpt-5-release"] == 200.0
        assert summary["market_exposure"]["ai-regulation"] == 100.0
        assert summary["narrative_exposure"]["ai_release"] == 200.0
        assert summary["narrative_exposure"]["ai_progress"] == 200.0
        assert summary["narrative_exposure"]["ai_regulation"] == 100.0


class TestDailyLossPercentage:
    @pytest.fixture
    def manager(self):
        return RiskManager()
    
    def test_daily_loss_under_limit(self, manager):
        """Should allow trading when loss under limit."""
        # 4% loss on 1000 bankroll = $40 loss
        allowed, msg = manager.check_daily_loss_percentage(-40.0, 1000.0)
        assert allowed is True
        assert msg == "OK"
    
    def test_daily_loss_at_limit(self, manager):
        """Should block trading when loss at limit."""
        # 5% loss on 1000 bankroll = $50 loss
        allowed, msg = manager.check_daily_loss_percentage(-50.0, 1000.0)
        assert allowed is False
        assert "exceeds limit" in msg
        assert "Stop trading" in msg
    
    def test_daily_loss_exceeds_limit(self, manager):
        """Should block trading when loss exceeds limit."""
        # 10% loss
        allowed, msg = manager.check_daily_loss_percentage(-100.0, 1000.0)
        assert allowed is False
        assert "10.0%" in msg
    
    def test_daily_profit_always_allowed(self, manager):
        """Profitable days should always allow trading."""
        allowed, msg = manager.check_daily_loss_percentage(500.0, 1000.0)
        assert allowed is True
        assert msg == "OK"
    
    def test_invalid_bankroll(self, manager):
        """Zero/negative bankroll should be rejected."""
        allowed, msg = manager.check_daily_loss_percentage(-10.0, 0.0)
        assert allowed is False
        assert "Invalid bankroll" in msg


class TestPositionManagement:
    @pytest.fixture
    def manager(self):
        return RiskManager()
    
    def test_add_position(self, manager):
        """Should add position to tracking."""
        pos = Position(
            market_slug="test-market",
            market_title="Test Market",
            amount=100.0,
            entry_price=50.0,
            side="yes"
        )
        manager.add_position(pos)
        
        positions = manager.get_positions()
        assert "test-market" in positions
        assert positions["test-market"].amount == 100.0
    
    def test_remove_position(self, manager):
        """Should remove position from tracking."""
        pos = Position(
            market_slug="test-market",
            market_title="Test Market",
            amount=100.0,
            entry_price=50.0,
            side="yes"
        )
        manager.add_position(pos)
        manager.remove_position("test-market")
        
        positions = manager.get_positions()
        assert "test-market" not in positions
    
    def test_remove_nonexistent_position(self, manager):
        """Removing nonexistent position should not error."""
        manager.remove_position("nonexistent")  # Should not raise


class TestFullRiskCheck:
    @pytest.fixture
    def manager(self):
        return RiskManager()
    
    def test_full_check_all_pass(self, manager):
        """All checks pass for valid trade."""
        allowed, messages = manager.full_risk_check(
            market_slug="test-market",
            market_title="Will GPT-5 release?",
            amount=50.0,
            entry_price=45.0,
            open_positions_count=2,
            daily_pnl=10.0,
            bankroll=1000.0
        )
        
        assert allowed is True
        assert "All risk checks passed" in messages[0]
    
    def test_full_check_size_fail(self, manager):
        """Should fail on position size."""
        allowed, messages = manager.full_risk_check(
            market_slug="test-market",
            market_title="Will GPT-5 release?",
            amount=150.0,  # > 100 limit
            entry_price=45.0,
            open_positions_count=2,
            daily_pnl=10.0,
            bankroll=1000.0
        )
        
        assert allowed is False
        assert any("exceeds max position size" in m for m in messages)
    
    def test_full_check_asymmetric_warning(self, manager):
        """Should include asymmetric risk warning but still allow."""
        allowed, messages = manager.full_risk_check(
            market_slug="test-market",
            market_title="Will GPT-5 release?",
            amount=50.0,
            entry_price=95.0,  # High price = asymmetric risk
            open_positions_count=2,
            daily_pnl=10.0,
            bankroll=1000.0
        )
        
        # Allowed because asymmetric is warning-only
        assert allowed is True
        assert any("ASYMMETRIC RISK WARNING" in m for m in messages)
    
    def test_full_check_multiple_failures(self, manager):
        """Should report failures from multiple check types."""
        allowed, messages = manager.full_risk_check(
            market_slug="test-market",
            market_title="Will GPT-5 release?",
            amount=150.0,  # Size fail (from check_trade_limits)
            entry_price=95.0,  # Asymmetric warning
            open_positions_count=2,  # OK
            daily_pnl=-60.0,  # % fail (6% > 5%)
            bankroll=1000.0
        )
        
        assert allowed is False
        error_msgs = [m for m in messages if "❌" in m]
        # Size fail + daily loss % fail = 2 failures
        assert len(error_msgs) >= 2
        # Should also have asymmetric warning
        assert any("ASYMMETRIC RISK WARNING" in m for m in messages)
    
    def test_full_check_narrative_fail(self, manager):
        """Should fail on narrative exposure."""
        # First, add a position with ai_release narrative
        manager.add_position(Position(
            market_slug="existing-market",
            market_title="Claude 4 release date",
            amount=450.0,
            entry_price=50.0,
            side="yes",
            narratives=["ai_release"]
        ))
        
        # Try to add more to same narrative
        allowed, messages = manager.full_risk_check(
            market_slug="new-market",
            market_title="Will GPT-5 release?",  # Same ai_release narrative
            amount=100.0,  # Would push to 550 > 500 limit
            entry_price=45.0,
            open_positions_count=2,
            daily_pnl=0.0,
            bankroll=1000.0
        )
        
        assert allowed is False
        assert any("ai_release" in m for m in messages)
