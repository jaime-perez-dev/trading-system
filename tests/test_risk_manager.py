import pytest
from risk_manager import RiskManager, RiskConfig

class TestRiskManager:
    @pytest.fixture
    def manager(self):
        return RiskManager()

    def test_default_config(self, manager):
        assert manager.config.max_position_size == 100.0
        assert manager.config.asymmetric_risk_threshold == 85.0

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
