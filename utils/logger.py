#!/usr/bin/env python3
"""
Centralized Logging for AI Trading System

Features:
- Structured logging with JSON support
- File rotation with daily logs
- Colored console output
- Trade-specific logging (entries, exits, alerts)
- Performance metrics logging
- Error tracking with context
"""

import logging
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler
from typing import Optional, Dict, Any


# Log directories
LOG_DIR = Path(__file__).parent.parent / "logs"
LOG_DIR.mkdir(exist_ok=True)


# ANSI colors for console output
class Colors:
    RESET = "\033[0m"
    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    MAGENTA = "\033[95m"
    CYAN = "\033[96m"
    GRAY = "\033[90m"


class ColoredFormatter(logging.Formatter):
    """Formatter that adds colors to console output"""
    
    LEVEL_COLORS = {
        logging.DEBUG: Colors.GRAY,
        logging.INFO: Colors.CYAN,
        logging.WARNING: Colors.YELLOW,
        logging.ERROR: Colors.RED,
        logging.CRITICAL: Colors.MAGENTA,
    }
    
    def format(self, record):
        # Add color to level name
        color = self.LEVEL_COLORS.get(record.levelno, Colors.RESET)
        record.levelname = f"{color}{record.levelname}{Colors.RESET}"
        
        # Colorize specific keywords in message
        message = super().format(record)
        
        # Highlight money amounts
        if "$" in message:
            parts = message.split("$")
            colored_parts = [parts[0]]
            for part in parts[1:]:
                # Find the number part
                num_end = 0
                for i, c in enumerate(part):
                    if c.isdigit() or c in ".,+-":
                        num_end = i + 1
                    else:
                        break
                if num_end > 0:
                    num = part[:num_end]
                    # Green for positive, red for negative
                    if num.startswith("-"):
                        colored_parts.append(f"{Colors.RED}${num}{Colors.RESET}{part[num_end:]}")
                    else:
                        colored_parts.append(f"{Colors.GREEN}${num}{Colors.RESET}{part[num_end:]}")
                else:
                    colored_parts.append("$" + part)
            message = "".join(colored_parts)
        
        return message


class JsonFormatter(logging.Formatter):
    """Formatter that outputs structured JSON logs"""
    
    def format(self, record):
        log_entry = {
            "timestamp": datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        
        # Add exception info if present
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)
        
        # Add extra fields
        if hasattr(record, "trade_id"):
            log_entry["trade_id"] = record.trade_id
        if hasattr(record, "market"):
            log_entry["market"] = record.market
        if hasattr(record, "pnl"):
            log_entry["pnl"] = record.pnl
        if hasattr(record, "context"):
            log_entry["context"] = record.context
        
        return json.dumps(log_entry)


def get_logger(
    name: str,
    level: int = logging.INFO,
    console: bool = True,
    file: bool = True,
    json_logs: bool = False,
) -> logging.Logger:
    """
    Get a configured logger for a module.
    
    Args:
        name: Logger name (usually __name__)
        level: Minimum log level
        console: Enable console output
        file: Enable file logging
        json_logs: Use JSON format for file logs
    
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    
    # Avoid adding handlers multiple times
    if logger.handlers:
        return logger
    
    logger.setLevel(level)
    
    # Console handler with colors
    if console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(level)
        console_fmt = ColoredFormatter(
            "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            datefmt="%H:%M:%S"
        )
        console_handler.setFormatter(console_fmt)
        logger.addHandler(console_handler)
    
    # File handler with rotation
    if file:
        # Daily rotating log file
        log_file = LOG_DIR / f"{name.split('.')[-1]}.log"
        file_handler = TimedRotatingFileHandler(
            log_file,
            when="midnight",
            interval=1,
            backupCount=30,  # Keep 30 days
            encoding="utf-8"
        )
        file_handler.setLevel(level)
        
        if json_logs:
            file_handler.setFormatter(JsonFormatter())
        else:
            file_handler.setFormatter(logging.Formatter(
                "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
            ))
        
        logger.addHandler(file_handler)
    
    return logger


class TradeLogger:
    """
    Specialized logger for trading operations.
    
    Provides methods for logging trades, alerts, and performance.
    """
    
    def __init__(self, name: str = "trading"):
        self.logger = get_logger(name, json_logs=True)
        self._trades_file = LOG_DIR / "trades.jsonl"
        self._alerts_file = LOG_DIR / "alerts.jsonl"
    
    def _append_jsonl(self, filepath: Path, data: Dict[str, Any]):
        """Append a JSON object to a JSONL file"""
        with open(filepath, "a") as f:
            f.write(json.dumps(data) + "\n")
    
    def trade_entry(
        self,
        trade_id: int,
        market: str,
        side: str,
        shares: float,
        price: float,
        cost: float,
        thesis: Optional[str] = None,
    ):
        """Log a trade entry"""
        entry = {
            "type": "entry",
            "timestamp": datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
            "trade_id": trade_id,
            "market": market,
            "side": side,
            "shares": shares,
            "price": price,
            "cost": cost,
            "thesis": thesis,
        }
        self._append_jsonl(self._trades_file, entry)
        self.logger.info(
            f"ENTRY #{trade_id}: {side} {shares:.1f} shares @ ${price:.2f} on '{market[:50]}' (${cost:.2f})",
            extra={"trade_id": trade_id, "market": market}
        )
    
    def trade_exit(
        self,
        trade_id: int,
        market: str,
        exit_price: float,
        pnl: float,
        pnl_pct: float,
        reason: str,
        hold_time_hours: Optional[float] = None,
    ):
        """Log a trade exit"""
        entry = {
            "type": "exit",
            "timestamp": datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
            "trade_id": trade_id,
            "market": market,
            "exit_price": exit_price,
            "pnl": pnl,
            "pnl_pct": pnl_pct,
            "reason": reason,
            "hold_time_hours": hold_time_hours,
        }
        self._append_jsonl(self._trades_file, entry)
        
        emoji = "✅" if pnl >= 0 else "❌"
        sign = "+" if pnl >= 0 else ""
        self.logger.info(
            f"{emoji} EXIT #{trade_id}: {sign}${pnl:.2f} ({sign}{pnl_pct:.1f}%) - {reason}",
            extra={"trade_id": trade_id, "market": market, "pnl": pnl}
        )
    
    def alert(
        self,
        alert_type: str,
        message: str,
        market: Optional[str] = None,
        price: Optional[float] = None,
        context: Optional[Dict] = None,
    ):
        """Log a trading alert"""
        entry = {
            "type": "alert",
            "alert_type": alert_type,
            "timestamp": datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
            "message": message,
            "market": market,
            "price": price,
            "context": context,
        }
        self._append_jsonl(self._alerts_file, entry)
        self.logger.warning(f"🔔 {alert_type}: {message}", extra={"context": context})
    
    def opportunity(
        self,
        market: str,
        score: float,
        current_price: float,
        edge_type: str,
        details: str,
    ):
        """Log a detected trading opportunity"""
        entry = {
            "type": "opportunity",
            "timestamp": datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
            "market": market,
            "score": score,
            "price": current_price,
            "edge_type": edge_type,
            "details": details,
        }
        self._append_jsonl(self._alerts_file, entry)
        self.logger.info(
            f"🎯 OPPORTUNITY: {market[:40]}... | Score: {score:.2f} | Price: {current_price}¢ | {edge_type}",
            extra={"market": market}
        )
    
    def error(self, message: str, exc_info: bool = True, context: Optional[Dict] = None):
        """Log an error with context"""
        self.logger.error(message, exc_info=exc_info, extra={"context": context})
    
    def performance(self, stats: Dict[str, Any]):
        """Log periodic performance stats"""
        entry = {
            "type": "performance",
            "timestamp": datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
            **stats
        }
        self._append_jsonl(self._alerts_file, entry)
        
        pnl = stats.get("total_pnl", 0)
        win_rate = stats.get("win_rate", 0)
        trades = stats.get("total_trades", 0)
        
        sign = "+" if pnl >= 0 else ""
        self.logger.info(
            f"📊 PERFORMANCE: {sign}${pnl:.2f} | Win Rate: {win_rate:.1f}% | Trades: {trades}"
        )


# Singleton trade logger instance
_trade_logger: Optional[TradeLogger] = None


def get_trade_logger() -> TradeLogger:
    """Get the singleton trade logger"""
    global _trade_logger
    if _trade_logger is None:
        _trade_logger = TradeLogger()
    return _trade_logger


# Example usage
if __name__ == "__main__":
    # Test basic logger
    logger = get_logger(__name__)
    logger.debug("Debug message (gray)")
    logger.info("Info message with $100.50 positive")
    logger.warning("Warning about -$50.25 loss")
    logger.error("Error occurred!")
    
    # Test trade logger
    tl = get_trade_logger()
    tl.trade_entry(
        trade_id=1,
        market="Will OpenAI release GPT-5 by July 2026?",
        side="YES",
        shares=100,
        price=0.45,
        cost=45.00,
        thesis="Strong signals of imminent release"
    )
    tl.opportunity(
        market="Will Anthropic raise Series D by Q2 2026?",
        score=0.85,
        current_price=32,
        edge_type="news_lag",
        details="Reuters reporting negotiations"
    )
    tl.trade_exit(
        trade_id=1,
        market="Will OpenAI release GPT-5 by July 2026?",
        exit_price=0.92,
        pnl=47.00,
        pnl_pct=104.4,
        reason="Take profit target hit",
        hold_time_hours=48.5
    )
    tl.performance({
        "total_trades": 5,
        "win_rate": 60.0,
        "total_pnl": 125.50,
    })
    
    print(f"\n✅ Logs written to: {LOG_DIR}")
