#!/usr/bin/env python3
"""
Telegram Notifier for Trading System
Sends alerts via Clawdbot gateway or standalone Telegram API
"""

import os
import json
import requests
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, List, Any

# Default chat ID for notifications
DEFAULT_CHAT_ID = "1623230691"

# Clawdbot gateway endpoint (if available)
CLAWDBOT_GATEWAY = os.environ.get("CLAWDBOT_GATEWAY_URL", "http://localhost:8765")


class TelegramNotifier:
    """
    Sends trading alerts via Telegram.
    
    Primary: Uses Clawdbot gateway (message tool)
    Fallback: Direct Telegram Bot API (requires TELEGRAM_BOT_TOKEN)
    """
    
    def __init__(self, chat_id: str = DEFAULT_CHAT_ID):
        self.chat_id = chat_id
        self.bot_token = os.environ.get("TELEGRAM_BOT_TOKEN")
        self.log_file = Path(__file__).parent.parent / "logs" / "notifications.log"
        self.log_file.parent.mkdir(exist_ok=True)
    
    def send(self, message: str, parse_mode: str = "Markdown") -> bool:
        """
        Send a notification message.
        
        Returns True if sent successfully, False otherwise.
        """
        # Log the attempt
        self._log(f"SEND: {message[:100]}...")
        
        # Try Clawdbot gateway first (preferred)
        if self._try_clawdbot(message):
            return True
        
        # Fallback to direct Telegram API
        if self.bot_token and self._try_direct_telegram(message, parse_mode):
            return True
        
        # If all fails, just log
        self._log("FAILED: No delivery method available")
        print(f"⚠️ Notification not sent (no gateway or bot token)")
        print(f"   Message: {message[:100]}...")
        return False
    
    def _try_clawdbot(self, message: str) -> bool:
        """Try sending via Clawdbot gateway."""
        try:
            # Check if gateway is available
            response = requests.get(f"{CLAWDBOT_GATEWAY}/health", timeout=2)
            if response.ok:
                # Use the message endpoint
                payload = {
                    "action": "send",
                    "target": self.chat_id,
                    "message": message
                }
                response = requests.post(
                    f"{CLAWDBOT_GATEWAY}/message",
                    json=payload,
                    timeout=10
                )
                if response.ok:
                    self._log(f"SENT via Clawdbot gateway")
                    return True
        except requests.RequestException:
            pass
        return False
    
    def _try_direct_telegram(self, message: str, parse_mode: str) -> bool:
        """Try sending via direct Telegram API."""
        try:
            url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
            payload = {
                "chat_id": self.chat_id,
                "text": message,
                "parse_mode": parse_mode
            }
            response = requests.post(url, json=payload, timeout=10)
            if response.ok:
                self._log(f"SENT via Telegram API")
                return True
        except requests.RequestException as e:
            self._log(f"Telegram API error: {e}")
        return False
    
    def _log(self, message: str):
        """Log notification activity."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(self.log_file, "a") as f:
            f.write(f"[{timestamp}] {message}\n")
    
    # ===== Alert Templates =====
    
    def alert_opportunity(self, news: Dict, markets: List[Dict]) -> bool:
        """Send an opportunity alert."""
        msg = f"🚨 *TRADING OPPORTUNITY*\n\n"
        msg += f"📰 *News:* {news.get('title', 'Unknown')[:100]}\n"
        msg += f"⏰ Source: {news.get('source', 'Unknown')}\n"
        
        if news.get('keywords'):
            msg += f"🏷️ Keywords: {', '.join(news['keywords'][:5])}\n"
        
        if markets:
            msg += f"\n📊 *Related Markets:*\n"
            for m in markets[:3]:
                question = m.get('question', 'Unknown')[:50]
                prices = m.get('outcomePrices', '[]')
                if isinstance(prices, str):
                    prices = json.loads(prices)
                price = float(prices[0]) * 100 if prices else 0
                msg += f"• {question}... ({price:.1f}%)\n"
        
        msg += f"\n⚡ _Act fast - news edges decay quickly!_"
        
        return self.send(msg)
    
    def alert_price_move(self, market: str, old_price: float, new_price: float, 
                         direction: str = "up") -> bool:
        """Send a price movement alert."""
        emoji = "📈" if direction == "up" else "📉"
        change = new_price - old_price
        change_pct = (change / old_price * 100) if old_price > 0 else 0
        
        msg = f"{emoji} *PRICE ALERT*\n\n"
        msg += f"📊 Market: {market[:60]}\n"
        msg += f"💰 {old_price:.1f}% → {new_price:.1f}%\n"
        msg += f"📐 Change: {'+' if change > 0 else ''}{change:.1f}pp ({change_pct:+.1f}%)\n"
        
        return self.send(msg)
    
    def alert_position_update(self, action: str, market: str, entry: float, 
                             exit_price: float = None, pnl: float = None) -> bool:
        """Send a position update alert."""
        if action.upper() == "OPEN":
            msg = f"📥 *POSITION OPENED*\n\n"
            msg += f"📊 {market[:60]}\n"
            msg += f"💰 Entry: {entry:.2f}%\n"
        elif action.upper() == "CLOSE":
            msg = f"📤 *POSITION CLOSED*\n\n"
            msg += f"📊 {market[:60]}\n"
            msg += f"💰 Entry: {entry:.2f}% → Exit: {exit_price:.2f}%\n"
            if pnl is not None:
                emoji = "🟢" if pnl >= 0 else "🔴"
                msg += f"{emoji} P&L: ${pnl:+.2f}\n"
        else:
            msg = f"📊 *POSITION UPDATE*\n\n{market}\n"
        
        return self.send(msg)
    
    def alert_system(self, title: str, message: str, level: str = "info") -> bool:
        """Send a system alert."""
        emoji_map = {
            "info": "ℹ️",
            "warning": "⚠️",
            "error": "🔴",
            "success": "✅"
        }
        emoji = emoji_map.get(level, "📢")
        
        msg = f"{emoji} *{title}*\n\n{message}"
        return self.send(msg)


def main():
    """Test the notifier."""
    notifier = TelegramNotifier()
    
    print("Testing Telegram Notifier...")
    print(f"Chat ID: {notifier.chat_id}")
    print(f"Bot token available: {bool(notifier.bot_token)}")
    
    # Test system alert
    success = notifier.alert_system(
        "Test Alert",
        "This is a test notification from the trading system.",
        level="info"
    )
    
    print(f"Test result: {'✅ Sent' if success else '❌ Failed'}")


if __name__ == "__main__":
    main()
