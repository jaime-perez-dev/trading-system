#!/usr/bin/env python3
"""
Tests for Performance Report Generator
"""

import pytest
import json
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone
from reports.performance_report import (
    TradeStats,
    calculate_stats,
    generate_summary_report,
    generate_marketing_snippet,
    is_test_trade,
    format_currency,
    format_percent
)

@pytest.fixture
def sample_trades():
    return [
        {
            "id": 1,
            "status": "RESOLVED",
            "market_slug": "market-1",
            "question": "Q1",
            "amount": 100.0,
            "pnl": 50.0,
            "won": True,
            "timestamp": "2026-01-01T10:00:00Z",
            "resolved_at": "2026-01-02T10:00:00Z"
        },
        {
            "id": 2,
            "status": "CLOSED",
            "market_slug": "market-2",
            "question": "Q2",
            "amount": 100.0,
            "pnl": -20.0,
            "won": False,
            "timestamp": "2026-01-03T10:00:00Z",
            "closed_at": "2026-01-03T12:00:00Z"
        },
        {
            "id": 3,
            "status": "OPEN",
            "market_slug": "market-3",
            "question": "Q3",
            "amount": 50.0,
            "pnl": None,
            "timestamp": "2026-02-01T10:00:00Z"
        },
        {
            "id": 4,
            "status": "RESOLVED",
            "market_slug": "test-market",
            "question": "Test Q",
            "amount": 10.0,
            "pnl": 10.0,
            "won": True,
            "timestamp": "2026-01-01T10:00:00Z"
        }
    ]

class TestTradeStats:
    def test_calculate_stats_excludes_test_trades_by_default(self, sample_trades):
        stats = calculate_stats(sample_trades, include_test=False)
        assert stats.total_trades == 3
        assert stats.real_trades == 3

    def test_calculate_stats_includes_test_trades(self, sample_trades):
        stats = calculate_stats(sample_trades, include_test=True)
        assert stats.total_trades == 4
        assert stats.real_trades == 3

    def test_financial_math(self, sample_trades):
        stats = calculate_stats(sample_trades)
        # Trades 1 (100) + 2 (100) + 3 (50) = 250 invested
        assert stats.total_invested == 250.0
        # PnL: 50 - 20 = 30
        assert stats.total_pnl == 30.0
        # Return: 30 / 250 = 12%
        assert stats.total_pnl_pct == 12.0

    def test_win_rate(self, sample_trades):
        stats = calculate_stats(sample_trades)
        # Completed trades: 1 (Win), 2 (Loss)
        assert stats.wins == 1
        assert stats.losses == 1
        assert stats.win_rate == 50.0

    def test_hold_time(self, sample_trades):
        stats = calculate_stats(sample_trades)
        # Trade 1: 1 day (24h)
        # Trade 2: 2 hours (0.083 days)
        # Trade 3: Open (ignored for avg_hold calculation in this logic, or handled differently)
        # Check logic: calculate_hold_days is called for CLOSED/RESOLVED
        assert stats.avg_hold_days > 0

class TestFormatting:
    def test_currency(self):
        assert format_currency(10.5) == "$10.50"
        assert format_currency(-10.5) == "-$10.50"
        assert format_currency(1000) == "$1,000.00"

    def test_percent(self):
        assert format_percent(10.5) == "+10.5%"
        assert format_percent(-5.2) == "-5.2%"
        assert format_percent(0) == "+0.0%"

class TestReportGeneration:
    def test_summary_contains_key_metrics(self, sample_trades):
        stats = calculate_stats(sample_trades)
        report = generate_summary_report(stats)
        
        assert "EdgeSignals Performance Report" in report
        assert "$250.00" in report  # Total Invested
        assert "$30.00" in report   # Net PnL
        assert "50.0%" in report    # Win Rate

    def test_marketing_snippet(self, sample_trades):
        stats = calculate_stats(sample_trades)
        snippet = generate_marketing_snippet(stats)
        
        assert "EdgeSignals Track Record" in snippet
        assert "📈 $30.00" in snippet
        assert "+12.0%" in snippet
        assert "50% win rate" in snippet

class TestUtils:
    def test_is_test_trade(self):
        assert is_test_trade({"market_slug": "test-market"})
        assert is_test_trade({"question": "This is a Test question"})
        assert not is_test_trade({"market_slug": "real-market", "question": "Real Q"})
