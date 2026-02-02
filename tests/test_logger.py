#!/usr/bin/env python3
"""Unit tests for the logging module"""

import os
import sys
import json
import tempfile
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
import logging

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.logger import (
    get_logger,
    get_trade_logger,
    TradeLogger,
    ColoredFormatter,
    JsonFormatter,
    LOG_DIR,
)


class TestGetLogger:
    """Tests for get_logger function"""
    
    def test_returns_logger_instance(self):
        """Should return a logging.Logger instance"""
        logger = get_logger("test_basic")
        assert isinstance(logger, logging.Logger)
        assert logger.name == "test_basic"
    
    def test_logger_level_is_configurable(self):
        """Should respect the level parameter"""
        logger = get_logger("test_level", level=logging.DEBUG, console=False, file=False)
        assert logger.level == logging.DEBUG
        
        logger2 = get_logger("test_level_warn", level=logging.WARNING, console=False, file=False)
        assert logger2.level == logging.WARNING
    
    def test_console_handler_added_when_enabled(self):
        """Should add console handler when console=True"""
        # Clear any existing handlers
        logger_name = "test_console_handler"
        logger = logging.getLogger(logger_name)
        logger.handlers.clear()
        
        logger = get_logger(logger_name, console=True, file=False)
        stream_handlers = [h for h in logger.handlers if isinstance(h, logging.StreamHandler)]
        assert len(stream_handlers) == 1
    
    def test_no_console_handler_when_disabled(self):
        """Should not add console handler when console=False"""
        logger_name = "test_no_console"
        logger = logging.getLogger(logger_name)
        logger.handlers.clear()
        
        logger = get_logger(logger_name, console=False, file=False)
        stream_handlers = [h for h in logger.handlers if isinstance(h, logging.StreamHandler)]
        assert len(stream_handlers) == 0
    
    def test_same_logger_returned_on_subsequent_calls(self):
        """Should return the same logger instance with same handlers"""
        logger1 = get_logger("test_same", console=True, file=False)
        handler_count = len(logger1.handlers)
        
        logger2 = get_logger("test_same", console=True, file=False)
        
        # Should be same instance
        assert logger1 is logger2
        # Should not add duplicate handlers
        assert len(logger2.handlers) == handler_count


class TestColoredFormatter:
    """Tests for ColoredFormatter"""
    
    def test_formats_message(self):
        """Should format basic messages"""
        formatter = ColoredFormatter("%(message)s")
        record = logging.LogRecord(
            name="test", level=logging.INFO, pathname="", lineno=0,
            msg="Hello world", args=(), exc_info=None
        )
        result = formatter.format(record)
        assert "Hello" in result
    
    def test_colorizes_positive_money(self):
        """Should colorize positive dollar amounts in green"""
        formatter = ColoredFormatter("%(message)s")
        record = logging.LogRecord(
            name="test", level=logging.INFO, pathname="", lineno=0,
            msg="Profit: $100.50", args=(), exc_info=None
        )
        result = formatter.format(record)
        # Should contain green color code
        assert "\033[92m" in result or "$100.50" in result
    
    def test_colorizes_negative_money(self):
        """Should colorize negative dollar amounts in red"""
        formatter = ColoredFormatter("%(message)s")
        record = logging.LogRecord(
            name="test", level=logging.INFO, pathname="", lineno=0,
            msg="Loss: $-50.25", args=(), exc_info=None
        )
        result = formatter.format(record)
        # Should contain the dollar amount
        assert "50.25" in result


class TestJsonFormatter:
    """Tests for JsonFormatter"""
    
    def test_outputs_valid_json(self):
        """Should output valid JSON"""
        formatter = JsonFormatter()
        record = logging.LogRecord(
            name="test", level=logging.INFO, pathname="test.py", lineno=10,
            msg="Test message", args=(), exc_info=None
        )
        record.funcName = "test_func"
        record.module = "test_module"
        
        result = formatter.format(record)
        parsed = json.loads(result)
        
        assert parsed["message"] == "Test message"
        assert parsed["level"] == "INFO"
        assert parsed["logger"] == "test"
    
    def test_includes_timestamp(self):
        """Should include ISO timestamp"""
        formatter = JsonFormatter()
        record = logging.LogRecord(
            name="test", level=logging.INFO, pathname="", lineno=0,
            msg="Test", args=(), exc_info=None
        )
        record.funcName = "test"
        record.module = "test"
        
        result = formatter.format(record)
        parsed = json.loads(result)
        
        assert "timestamp" in parsed
        assert "Z" in parsed["timestamp"]  # UTC indicator
    
    def test_includes_extra_fields(self):
        """Should include extra fields like trade_id"""
        formatter = JsonFormatter()
        record = logging.LogRecord(
            name="test", level=logging.INFO, pathname="", lineno=0,
            msg="Test", args=(), exc_info=None
        )
        record.funcName = "test"
        record.module = "test"
        record.trade_id = 123
        record.market = "Test Market"
        
        result = formatter.format(record)
        parsed = json.loads(result)
        
        assert parsed["trade_id"] == 123
        assert parsed["market"] == "Test Market"


class TestTradeLogger:
    """Tests for TradeLogger class"""
    
    @pytest.fixture
    def temp_log_dir(self, tmp_path):
        """Create temporary log directory"""
        return tmp_path
    
    @pytest.fixture
    def trade_logger(self, temp_log_dir):
        """Create a TradeLogger with temp directory"""
        with patch('utils.logger.LOG_DIR', temp_log_dir):
            tl = TradeLogger("test_trades")
            tl._trades_file = temp_log_dir / "trades.jsonl"
            tl._alerts_file = temp_log_dir / "alerts.jsonl"
            return tl
    
    def test_trade_entry_logs_to_file(self, trade_logger, temp_log_dir):
        """Should append trade entry to JSONL file"""
        trade_logger.trade_entry(
            trade_id=1,
            market="Test Market",
            side="YES",
            shares=100,
            price=0.50,
            cost=50.00,
            thesis="Test thesis"
        )
        
        trades_file = temp_log_dir / "trades.jsonl"
        assert trades_file.exists()
        
        with open(trades_file) as f:
            entry = json.loads(f.readline())
        
        assert entry["type"] == "entry"
        assert entry["trade_id"] == 1
        assert entry["market"] == "Test Market"
        assert entry["side"] == "YES"
        assert entry["shares"] == 100
    
    def test_trade_exit_logs_pnl(self, trade_logger, temp_log_dir):
        """Should log exit with P&L information"""
        trade_logger.trade_exit(
            trade_id=1,
            market="Test Market",
            exit_price=0.80,
            pnl=30.00,
            pnl_pct=60.0,
            reason="Take profit",
            hold_time_hours=24.5
        )
        
        trades_file = temp_log_dir / "trades.jsonl"
        with open(trades_file) as f:
            entry = json.loads(f.readline())
        
        assert entry["type"] == "exit"
        assert entry["pnl"] == 30.00
        assert entry["pnl_pct"] == 60.0
        assert entry["reason"] == "Take profit"
    
    def test_alert_logs_to_alerts_file(self, trade_logger, temp_log_dir):
        """Should log alerts to separate file"""
        trade_logger.alert(
            alert_type="PRICE_MOVE",
            message="Price moved 10%",
            market="Test Market",
            price=0.55,
            context={"previous": 0.50}
        )
        
        alerts_file = temp_log_dir / "alerts.jsonl"
        assert alerts_file.exists()
        
        with open(alerts_file) as f:
            entry = json.loads(f.readline())
        
        assert entry["type"] == "alert"
        assert entry["alert_type"] == "PRICE_MOVE"
        assert entry["context"]["previous"] == 0.50
    
    def test_opportunity_logs_correctly(self, trade_logger, temp_log_dir):
        """Should log trading opportunities"""
        trade_logger.opportunity(
            market="Will X happen by Y?",
            score=0.85,
            current_price=45,
            edge_type="news_lag",
            details="Breaking news detected"
        )
        
        alerts_file = temp_log_dir / "alerts.jsonl"
        with open(alerts_file) as f:
            entry = json.loads(f.readline())
        
        assert entry["type"] == "opportunity"
        assert entry["score"] == 0.85
        assert entry["edge_type"] == "news_lag"
    
    def test_performance_logs_stats(self, trade_logger, temp_log_dir):
        """Should log performance statistics"""
        trade_logger.performance({
            "total_trades": 10,
            "win_rate": 70.0,
            "total_pnl": 250.00,
            "avg_hold_time": 48.5
        })
        
        alerts_file = temp_log_dir / "alerts.jsonl"
        with open(alerts_file) as f:
            entry = json.loads(f.readline())
        
        assert entry["type"] == "performance"
        assert entry["total_trades"] == 10
        assert entry["win_rate"] == 70.0
    
    def test_multiple_entries_appended(self, trade_logger, temp_log_dir):
        """Should append multiple entries to same file"""
        trade_logger.trade_entry(trade_id=1, market="M1", side="YES", shares=100, price=0.50, cost=50)
        trade_logger.trade_entry(trade_id=2, market="M2", side="NO", shares=50, price=0.60, cost=30)
        trade_logger.trade_exit(trade_id=1, market="M1", exit_price=0.80, pnl=30, pnl_pct=60, reason="TP")
        
        trades_file = temp_log_dir / "trades.jsonl"
        with open(trades_file) as f:
            lines = f.readlines()
        
        assert len(lines) == 3


class TestGetTradeLogger:
    """Tests for get_trade_logger singleton"""
    
    def test_returns_same_instance(self):
        """Should return the same TradeLogger instance"""
        # Reset the singleton
        import utils.logger
        utils.logger._trade_logger = None
        
        logger1 = get_trade_logger()
        logger2 = get_trade_logger()
        
        assert logger1 is logger2
    
    def test_returns_trade_logger_type(self):
        """Should return a TradeLogger instance"""
        import utils.logger
        utils.logger._trade_logger = None
        
        logger = get_trade_logger()
        assert isinstance(logger, TradeLogger)


class TestLogDirectory:
    """Tests for log directory management"""
    
    def test_log_dir_exists(self):
        """LOG_DIR should exist"""
        assert LOG_DIR.exists()
        assert LOG_DIR.is_dir()
    
    def test_log_dir_is_in_project(self):
        """LOG_DIR should be in the trading-system project"""
        assert "trading-system" in str(LOG_DIR)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
