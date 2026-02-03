"""
Unit tests for polymarket/real_trader.py
Tests: TradingConfig, RealTrader, risk checks, order flow
All tests use mocking — no wallet/network/side effects.
"""
import json
import os
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import patch, MagicMock, PropertyMock

import pytest

# Add parent directory for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# Mock py_clob_client before importing real_trader (not installed in test env)
_mock_clob = MagicMock()
sys.modules["py_clob_client"] = _mock_clob
sys.modules["py_clob_client.client"] = _mock_clob
sys.modules["py_clob_client.clob_types"] = _mock_clob
sys.modules["py_clob_client.order_builder"] = _mock_clob
sys.modules["py_clob_client.order_builder.constants"] = MagicMock(BUY="BUY", SELL="SELL")


class TestTradingConfig:
    """Tests for TradingConfig class."""
    
    def test_default_values(self, tmp_path):
        """Config should have sensible defaults."""
        with patch("polymarket.real_trader.CONFIG_FILE", tmp_path / "config.json"):
            from polymarket.real_trader import TradingConfig
            config = TradingConfig()
            
            assert config.max_position_size == 100.0
            assert config.max_daily_loss == 50.0
            assert config.max_open_positions == 5
            assert config.min_confidence == 0.7
            assert config.enabled is False
    
    def test_load_from_file(self, tmp_path):
        """Config should load from existing file."""
        config_file = tmp_path / "config.json"
        config_file.write_text(json.dumps({
            "max_position_size": 200.0,
            "max_daily_loss": 100.0,
            "max_open_positions": 10,
            "min_confidence": 0.8,
            "enabled": True
        }))
        
        with patch("polymarket.real_trader.CONFIG_FILE", config_file):
            from polymarket.real_trader import TradingConfig
            config = TradingConfig()
            
            assert config.max_position_size == 200.0
            assert config.max_daily_loss == 100.0
            assert config.max_open_positions == 10
            assert config.min_confidence == 0.8
            assert config.enabled is True
    
    def test_save_config(self, tmp_path):
        """Config should save to file."""
        config_file = tmp_path / "config.json"
        data_dir = tmp_path
        
        with patch("polymarket.real_trader.CONFIG_FILE", config_file):
            with patch("polymarket.real_trader.DATA_DIR", data_dir):
                from polymarket.real_trader import TradingConfig
                config = TradingConfig()
                config.max_position_size = 500.0
                config.enabled = True
                config.save()
                
                saved = json.loads(config_file.read_text())
                assert saved["max_position_size"] == 500.0
                assert saved["enabled"] is True
    
    def test_partial_config_file(self, tmp_path):
        """Config should handle partial config files."""
        config_file = tmp_path / "config.json"
        config_file.write_text(json.dumps({
            "max_position_size": 150.0
            # Other fields missing
        }))
        
        with patch("polymarket.real_trader.CONFIG_FILE", config_file):
            from polymarket.real_trader import TradingConfig
            config = TradingConfig()
            
            assert config.max_position_size == 150.0
            assert config.max_daily_loss == 50.0  # Default


class TestRealTraderInit:
    """Tests for RealTrader initialization."""
    
    def test_dry_run_default(self, tmp_path):
        """Trader should default to dry_run=True."""
        with patch("polymarket.real_trader.DATA_DIR", tmp_path):
            with patch("polymarket.real_trader.CONFIG_FILE", tmp_path / "config.json"):
                with patch("polymarket.real_trader.TRADES_FILE", tmp_path / "trades.json"):
                    with patch.dict(os.environ, {}, clear=True):
                        with patch("polymarket.real_trader.ClobClient") as mock_client:
                            from polymarket.real_trader import RealTrader
                            trader = RealTrader()
                            
                            assert trader.dry_run is True
    
    def test_without_private_key(self, tmp_path):
        """Trader should work in read-only mode without private key."""
        with patch("polymarket.real_trader.DATA_DIR", tmp_path):
            with patch("polymarket.real_trader.CONFIG_FILE", tmp_path / "config.json"):
                with patch("polymarket.real_trader.TRADES_FILE", tmp_path / "trades.json"):
                    with patch.dict(os.environ, {}, clear=True):
                        with patch("polymarket.real_trader.ClobClient") as mock_client:
                            from polymarket.real_trader import RealTrader
                            trader = RealTrader()
                            
                            # Should create read-only client
                            mock_client.assert_called()
    
    def test_with_private_key(self, tmp_path):
        """Trader should initialize full client with private key."""
        with patch("polymarket.real_trader.DATA_DIR", tmp_path):
            with patch("polymarket.real_trader.CONFIG_FILE", tmp_path / "config.json"):
                with patch("polymarket.real_trader.TRADES_FILE", tmp_path / "trades.json"):
                    with patch.dict(os.environ, {"POLYMARKET_PRIVATE_KEY": "0x123abc"}):
                        with patch("polymarket.real_trader.ClobClient") as mock_client:
                            from polymarket.real_trader import RealTrader
                            trader = RealTrader()
                            
                            # Should create full client with key
                            calls = mock_client.call_args_list
                            assert len(calls) > 0


class TestRealTraderRiskChecks:
    """Tests for risk management checks."""
    
    def test_is_trading_enabled_default(self, tmp_path):
        """Trading should be disabled by default."""
        with patch("polymarket.real_trader.DATA_DIR", tmp_path):
            with patch("polymarket.real_trader.CONFIG_FILE", tmp_path / "config.json"):
                with patch("polymarket.real_trader.TRADES_FILE", tmp_path / "trades.json"):
                    with patch.dict(os.environ, {}, clear=True):
                        with patch("polymarket.real_trader.ClobClient"):
                            from polymarket.real_trader import RealTrader
                            trader = RealTrader()
                            
                            assert trader.is_trading_enabled() is False
    
    def test_is_trading_enabled_when_enabled(self, tmp_path):
        """Trading should be enabled when config says so."""
        config_file = tmp_path / "config.json"
        config_file.write_text(json.dumps({"enabled": True}))
        
        with patch("polymarket.real_trader.DATA_DIR", tmp_path):
            with patch("polymarket.real_trader.CONFIG_FILE", config_file):
                with patch("polymarket.real_trader.TRADES_FILE", tmp_path / "trades.json"):
                    with patch.dict(os.environ, {"POLYMARKET_PRIVATE_KEY": "0x123"}):
                        with patch("polymarket.real_trader.ClobClient"):
                            from polymarket.real_trader import RealTrader
                            trader = RealTrader(dry_run=False)
                            
                            assert trader.is_trading_enabled() is True
    
    def test_check_risk_limits_rejects_over_max(self, tmp_path):
        """Should reject positions over max size."""
        config_file = tmp_path / "config.json"
        config_file.write_text(json.dumps({
            "max_position_size": 100.0,
            "enabled": True
        }))
        
        with patch("polymarket.real_trader.DATA_DIR", tmp_path):
            with patch("polymarket.real_trader.CONFIG_FILE", config_file):
                with patch("polymarket.real_trader.TRADES_FILE", tmp_path / "trades.json"):
                    with patch.dict(os.environ, {}, clear=True):
                        with patch("polymarket.real_trader.ClobClient"):
                            from polymarket.real_trader import RealTrader
                            trader = RealTrader()
                            
                            can, reason = trader.check_risk_limits(150.0)
                            assert can is False
                            assert "max" in reason.lower() or "position" in reason.lower() or "exceeds" in reason.lower()
    
    def test_check_risk_limits_accepts_valid(self, tmp_path):
        """Should accept positions under max size."""
        config_file = tmp_path / "config.json"
        config_file.write_text(json.dumps({
            "max_position_size": 100.0,
            "enabled": True
        }))
        
        with patch("polymarket.real_trader.DATA_DIR", tmp_path):
            with patch("polymarket.real_trader.CONFIG_FILE", config_file):
                with patch("polymarket.real_trader.TRADES_FILE", tmp_path / "trades.json"):
                    with patch.dict(os.environ, {}, clear=True):
                        with patch("polymarket.real_trader.ClobClient"):
                            from polymarket.real_trader import RealTrader
                            trader = RealTrader()
                            trader.config.enabled = True
                            
                            can, reason = trader.check_risk_limits(50.0)
                            assert can is True


class TestRealTraderOrders:
    """Tests for order placement."""
    
    def test_place_market_order_dry_run(self, tmp_path):
        """Market order in dry run should not execute."""
        config_file = tmp_path / "config.json"
        config_file.write_text(json.dumps({"enabled": True}))
        
        with patch("polymarket.real_trader.DATA_DIR", tmp_path):
            with patch("polymarket.real_trader.CONFIG_FILE", config_file):
                with patch("polymarket.real_trader.TRADES_FILE", tmp_path / "trades.json"):
                    with patch.dict(os.environ, {"POLYMARKET_PRIVATE_KEY": "0xtest123"}):
                        with patch("polymarket.real_trader.ClobClient"):
                            from polymarket.real_trader import RealTrader
                            trader = RealTrader(dry_run=True)
                            
                            result = trader.place_market_order(
                                token_id="0xtest",
                                side="BUY",
                                amount=10.0,
                                market_name="Test Market"
                            )
                            
                            assert result.get("dry_run") is True
                            assert result.get("success") is True
    
    def test_place_market_order_trading_disabled(self, tmp_path):
        """Market order should fail when trading disabled."""
        with patch("polymarket.real_trader.DATA_DIR", tmp_path):
            with patch("polymarket.real_trader.CONFIG_FILE", tmp_path / "config.json"):
                with patch("polymarket.real_trader.TRADES_FILE", tmp_path / "trades.json"):
                    with patch.dict(os.environ, {}, clear=True):
                        with patch("polymarket.real_trader.ClobClient"):
                            from polymarket.real_trader import RealTrader
                            trader = RealTrader(dry_run=False)
                            trader.config.enabled = False
                            
                            result = trader.place_market_order(
                                token_id="0xtest",
                                side="BUY",
                                amount=10.0,
                                market_name="Test Market"
                            )
                            
                            assert result.get("success") is False
                            assert "not enabled" in result.get("error", "").lower()
    
    def test_place_limit_order_dry_run(self, tmp_path):
        """Limit order in dry run should not execute."""
        config_file = tmp_path / "config.json"
        config_file.write_text(json.dumps({"enabled": True}))
        
        with patch("polymarket.real_trader.DATA_DIR", tmp_path):
            with patch("polymarket.real_trader.CONFIG_FILE", config_file):
                with patch("polymarket.real_trader.TRADES_FILE", tmp_path / "trades.json"):
                    with patch.dict(os.environ, {"POLYMARKET_PRIVATE_KEY": "0xtest123"}):
                        with patch("polymarket.real_trader.ClobClient"):
                            from polymarket.real_trader import RealTrader
                            trader = RealTrader(dry_run=True)
                            
                            result = trader.place_limit_order(
                                token_id="0xtest",
                                side="BUY",
                                price=0.50,
                                size=10,
                                market_name="Test Market"
                            )
                            
                            assert result.get("dry_run") is True
                            assert result.get("success") is True


class TestRealTraderTradeHistory:
    """Tests for trade history management."""
    
    def test_get_trade_history_empty(self, tmp_path):
        """Should return empty list when no trades."""
        with patch("polymarket.real_trader.DATA_DIR", tmp_path):
            with patch("polymarket.real_trader.CONFIG_FILE", tmp_path / "config.json"):
                with patch("polymarket.real_trader.TRADES_FILE", tmp_path / "trades.json"):
                    with patch.dict(os.environ, {}, clear=True):
                        with patch("polymarket.real_trader.ClobClient"):
                            from polymarket.real_trader import RealTrader
                            trader = RealTrader()
                            
                            history = trader.get_trade_history()
                            assert history == []
    
    def test_load_existing_trades(self, tmp_path):
        """Should load trades from file."""
        trades_file = tmp_path / "trades.json"
        trades_file.write_text(json.dumps([
            {"id": 1, "token_id": "0x123", "amount": 10.0}
        ]))
        
        with patch("polymarket.real_trader.DATA_DIR", tmp_path):
            with patch("polymarket.real_trader.CONFIG_FILE", tmp_path / "config.json"):
                with patch("polymarket.real_trader.TRADES_FILE", trades_file):
                    with patch.dict(os.environ, {}, clear=True):
                        with patch("polymarket.real_trader.ClobClient"):
                            from polymarket.real_trader import RealTrader
                            trader = RealTrader()
                            
                            history = trader.get_trade_history()
                            assert len(history) == 1
                            assert history[0]["id"] == 1


class TestRealTraderOpenOrders:
    """Tests for open order management."""
    
    def test_get_open_orders_disabled(self, tmp_path):
        """Should return empty when trading disabled."""
        with patch("polymarket.real_trader.DATA_DIR", tmp_path):
            with patch("polymarket.real_trader.CONFIG_FILE", tmp_path / "config.json"):
                with patch("polymarket.real_trader.TRADES_FILE", tmp_path / "trades.json"):
                    with patch.dict(os.environ, {}, clear=True):
                        with patch("polymarket.real_trader.ClobClient"):
                            from polymarket.real_trader import RealTrader
                            trader = RealTrader()
                            
                            orders = trader.get_open_orders()
                            assert orders == []
    
    def test_cancel_order_disabled(self, tmp_path):
        """Cancel should fail when trading disabled."""
        with patch("polymarket.real_trader.DATA_DIR", tmp_path):
            with patch("polymarket.real_trader.CONFIG_FILE", tmp_path / "config.json"):
                with patch("polymarket.real_trader.TRADES_FILE", tmp_path / "trades.json"):
                    with patch.dict(os.environ, {}, clear=True):
                        with patch("polymarket.real_trader.ClobClient"):
                            from polymarket.real_trader import RealTrader
                            trader = RealTrader()
                            
                            result = trader.cancel_order("order-123")
                            assert result is False
    
    def test_cancel_all_orders_disabled(self, tmp_path):
        """Cancel all should fail when trading disabled."""
        with patch("polymarket.real_trader.DATA_DIR", tmp_path):
            with patch("polymarket.real_trader.CONFIG_FILE", tmp_path / "config.json"):
                with patch("polymarket.real_trader.TRADES_FILE", tmp_path / "trades.json"):
                    with patch.dict(os.environ, {}, clear=True):
                        with patch("polymarket.real_trader.ClobClient"):
                            from polymarket.real_trader import RealTrader
                            trader = RealTrader()
                            
                            result = trader.cancel_all_orders()
                            assert result is False


class TestRealTraderStatus:
    """Tests for status display."""
    
    def test_status_runs_without_error(self, tmp_path, capsys):
        """Status should print without errors."""
        with patch("polymarket.real_trader.DATA_DIR", tmp_path):
            with patch("polymarket.real_trader.CONFIG_FILE", tmp_path / "config.json"):
                with patch("polymarket.real_trader.TRADES_FILE", tmp_path / "trades.json"):
                    with patch.dict(os.environ, {}, clear=True):
                        with patch("polymarket.real_trader.ClobClient"):
                            from polymarket.real_trader import RealTrader
                            trader = RealTrader()
                            
                            # Should not raise
                            trader.status()
                            
                            captured = capsys.readouterr()
                            assert "REAL TRADER STATUS" in captured.out
                            assert "Trading Enabled" in captured.out
                            assert "Risk Limits" in captured.out
