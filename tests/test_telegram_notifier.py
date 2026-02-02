"""
Tests for Telegram Notifier
Tests alert formatting, logging, and delivery logic
"""
import pytest
import json
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
import tempfile
import os
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from alerts.telegram_notifier import TelegramNotifier


class TestTelegramNotifierInit:
    """Test notifier initialization."""
    
    def test_default_chat_id(self):
        """Should use default chat ID."""
        notifier = TelegramNotifier()
        assert notifier.chat_id == "1623230691"
    
    def test_custom_chat_id(self):
        """Should accept custom chat ID."""
        notifier = TelegramNotifier(chat_id="123456789")
        assert notifier.chat_id == "123456789"
    
    def test_log_file_path(self):
        """Should set up log file path."""
        notifier = TelegramNotifier()
        assert "notifications.log" in str(notifier.log_file)
    
    def test_bot_token_from_env(self):
        """Should read bot token from environment."""
        with patch.dict(os.environ, {"TELEGRAM_BOT_TOKEN": "test-token"}):
            notifier = TelegramNotifier()
            assert notifier.bot_token == "test-token"


class TestAlertOpportunity:
    """Test opportunity alert formatting."""
    
    def test_basic_opportunity_format(self):
        """Should format basic opportunity alert."""
        notifier = TelegramNotifier()
        
        with patch.object(notifier, 'send', return_value=True) as mock_send:
            news = {
                "title": "OpenAI announces GPT-5",
                "source": "TechCrunch"
            }
            markets = []
            
            notifier.alert_opportunity(news, markets)
            
            call_args = mock_send.call_args[0][0]
            assert "TRADING OPPORTUNITY" in call_args
            assert "OpenAI announces GPT-5" in call_args
            assert "TechCrunch" in call_args
    
    def test_opportunity_with_keywords(self):
        """Should include keywords in alert."""
        notifier = TelegramNotifier()
        
        with patch.object(notifier, 'send', return_value=True) as mock_send:
            news = {
                "title": "Test news",
                "source": "Test",
                "keywords": ["AI", "GPT", "OpenAI", "prediction"]
            }
            
            notifier.alert_opportunity(news, [])
            
            call_args = mock_send.call_args[0][0]
            assert "Keywords:" in call_args
            assert "AI" in call_args
    
    def test_opportunity_with_markets(self):
        """Should include related markets."""
        notifier = TelegramNotifier()
        
        with patch.object(notifier, 'send', return_value=True) as mock_send:
            news = {"title": "Test", "source": "Test"}
            markets = [
                {
                    "question": "Will GPT-5 be released?",
                    "outcomePrices": "[0.75, 0.25]"
                }
            ]
            
            notifier.alert_opportunity(news, markets)
            
            call_args = mock_send.call_args[0][0]
            assert "Related Markets" in call_args
            assert "75.0%" in call_args
    
    def test_opportunity_truncates_long_title(self):
        """Should truncate very long news titles."""
        notifier = TelegramNotifier()
        
        with patch.object(notifier, 'send', return_value=True) as mock_send:
            long_title = "A" * 200
            news = {"title": long_title, "source": "Test"}
            
            notifier.alert_opportunity(news, [])
            
            call_args = mock_send.call_args[0][0]
            # Title should be truncated to 100 chars
            assert "A" * 100 in call_args
            assert "A" * 101 not in call_args


class TestAlertPriceMove:
    """Test price movement alert formatting."""
    
    def test_price_up_format(self):
        """Should format price increase correctly."""
        notifier = TelegramNotifier()
        
        with patch.object(notifier, 'send', return_value=True) as mock_send:
            notifier.alert_price_move("GPT-5 by March", 50.0, 60.0, "up")
            
            call_args = mock_send.call_args[0][0]
            assert "📈" in call_args
            assert "PRICE ALERT" in call_args
            assert "50.0% → 60.0%" in call_args
            assert "+10.0pp" in call_args
    
    def test_price_down_format(self):
        """Should format price decrease correctly."""
        notifier = TelegramNotifier()
        
        with patch.object(notifier, 'send', return_value=True) as mock_send:
            notifier.alert_price_move("GPT-5 by March", 60.0, 50.0, "down")
            
            call_args = mock_send.call_args[0][0]
            assert "📉" in call_args
            assert "-10.0pp" in call_args
    
    def test_handles_zero_old_price(self):
        """Should handle zero old price gracefully."""
        notifier = TelegramNotifier()
        
        with patch.object(notifier, 'send', return_value=True) as mock_send:
            notifier.alert_price_move("Test Market", 0.0, 50.0, "up")
            
            # Should not raise division by zero
            call_args = mock_send.call_args[0][0]
            assert "0.0% → 50.0%" in call_args


class TestAlertPositionUpdate:
    """Test position update alert formatting."""
    
    def test_position_open_format(self):
        """Should format position open correctly."""
        notifier = TelegramNotifier()
        
        with patch.object(notifier, 'send', return_value=True) as mock_send:
            notifier.alert_position_update("OPEN", "GPT-5 Market", 95.0)
            
            call_args = mock_send.call_args[0][0]
            assert "POSITION OPENED" in call_args
            assert "Entry: 95.00%" in call_args
    
    def test_position_close_with_profit(self):
        """Should format profitable close correctly."""
        notifier = TelegramNotifier()
        
        with patch.object(notifier, 'send', return_value=True) as mock_send:
            notifier.alert_position_update("CLOSE", "GPT-5 Market", 95.0, 
                                          exit_price=98.0, pnl=50.0)
            
            call_args = mock_send.call_args[0][0]
            assert "POSITION CLOSED" in call_args
            assert "🟢" in call_args
            assert "$+50.00" in call_args
    
    def test_position_close_with_loss(self):
        """Should format losing close correctly."""
        notifier = TelegramNotifier()
        
        with patch.object(notifier, 'send', return_value=True) as mock_send:
            notifier.alert_position_update("CLOSE", "GPT-5 Market", 95.0,
                                          exit_price=90.0, pnl=-25.0)
            
            call_args = mock_send.call_args[0][0]
            assert "🔴" in call_args
            assert "$-25.00" in call_args


class TestAlertSystem:
    """Test system alert formatting."""
    
    def test_info_level(self):
        """Should use info emoji."""
        notifier = TelegramNotifier()
        
        with patch.object(notifier, 'send', return_value=True) as mock_send:
            notifier.alert_system("Test Title", "Test message", "info")
            
            call_args = mock_send.call_args[0][0]
            assert "ℹ️" in call_args
            assert "Test Title" in call_args
    
    def test_warning_level(self):
        """Should use warning emoji."""
        notifier = TelegramNotifier()
        
        with patch.object(notifier, 'send', return_value=True) as mock_send:
            notifier.alert_system("Warning", "Something is wrong", "warning")
            
            call_args = mock_send.call_args[0][0]
            assert "⚠️" in call_args
    
    def test_error_level(self):
        """Should use error emoji."""
        notifier = TelegramNotifier()
        
        with patch.object(notifier, 'send', return_value=True) as mock_send:
            notifier.alert_system("Error", "System failed", "error")
            
            call_args = mock_send.call_args[0][0]
            assert "🔴" in call_args
    
    def test_success_level(self):
        """Should use success emoji."""
        notifier = TelegramNotifier()
        
        with patch.object(notifier, 'send', return_value=True) as mock_send:
            notifier.alert_system("Success", "Trade completed", "success")
            
            call_args = mock_send.call_args[0][0]
            assert "✅" in call_args
    
    def test_unknown_level_fallback(self):
        """Should use fallback emoji for unknown level."""
        notifier = TelegramNotifier()
        
        with patch.object(notifier, 'send', return_value=True) as mock_send:
            notifier.alert_system("Custom", "Custom alert", "custom")
            
            call_args = mock_send.call_args[0][0]
            assert "📢" in call_args


class TestSendLogic:
    """Test send delivery logic."""
    
    def test_tries_clawdbot_first(self):
        """Should try Clawdbot gateway first."""
        notifier = TelegramNotifier()
        
        with patch.object(notifier, '_try_clawdbot', return_value=True) as mock_claw:
            with patch.object(notifier, '_try_direct_telegram') as mock_tg:
                notifier.send("Test message")
                
                mock_claw.assert_called_once()
                mock_tg.assert_not_called()
    
    def test_falls_back_to_telegram(self):
        """Should fall back to direct Telegram if Clawdbot fails."""
        notifier = TelegramNotifier()
        notifier.bot_token = "test-token"
        
        with patch.object(notifier, '_try_clawdbot', return_value=False):
            with patch.object(notifier, '_try_direct_telegram', return_value=True) as mock_tg:
                result = notifier.send("Test message")
                
                mock_tg.assert_called_once()
                assert result is True
    
    def test_returns_false_when_all_fail(self):
        """Should return False when all delivery methods fail."""
        notifier = TelegramNotifier()
        notifier.bot_token = None  # No direct API fallback
        
        with patch.object(notifier, '_try_clawdbot', return_value=False):
            with patch.object(notifier, '_log'):  # Suppress logging
                result = notifier.send("Test message")
                
                assert result is False


class TestLogging:
    """Test logging functionality."""
    
    def test_log_writes_to_file(self):
        """Should write log messages to file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            notifier = TelegramNotifier()
            log_path = Path(tmpdir) / "test.log"
            notifier.log_file = log_path
            
            notifier._log("Test log message")
            
            assert log_path.exists()
            content = log_path.read_text()
            assert "Test log message" in content
    
    def test_log_includes_timestamp(self):
        """Should include timestamp in log."""
        with tempfile.TemporaryDirectory() as tmpdir:
            notifier = TelegramNotifier()
            notifier.log_file = Path(tmpdir) / "test.log"
            
            notifier._log("Test message")
            
            content = notifier.log_file.read_text()
            # Should have format like [2026-02-02 08:50:00]
            assert "[20" in content
