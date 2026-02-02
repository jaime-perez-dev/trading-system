#!/usr/bin/env python3
"""
Pre-Trade Checklist - Applies lessons from past failures before trades.

This module analyzes trade opportunities against historical failure patterns
to warn about common mistakes before capital is deployed.
"""

import json
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

DATA_DIR = Path(__file__).parent / "data"
TRADE_ANALYSIS_FILE = DATA_DIR / "trade_analysis.json"


@dataclass
class CheckResult:
    """Result of a single check."""
    passed: bool
    check_name: str
    message: str
    severity: str  # 'warning', 'critical', 'info'


@dataclass
class ChecklistResult:
    """Combined result of all checks."""
    all_passed: bool
    critical_failures: list[CheckResult]
    warnings: list[CheckResult]
    info: list[CheckResult]
    
    def get_summary(self) -> str:
        """Human-readable summary."""
        lines = []
        
        if self.all_passed:
            lines.append("✅ All pre-trade checks passed")
        else:
            lines.append("⚠️ Pre-trade checklist has warnings/failures:")
        
        if self.critical_failures:
            lines.append("\n🚨 CRITICAL (do not proceed):")
            for r in self.critical_failures:
                lines.append(f"  - {r.check_name}: {r.message}")
        
        if self.warnings:
            lines.append("\n⚠️ WARNINGS (proceed with caution):")
            for r in self.warnings:
                lines.append(f"  - {r.check_name}: {r.message}")
        
        if self.info:
            lines.append("\nℹ️ Notes:")
            for r in self.info:
                lines.append(f"  - {r.message}")
        
        return "\n".join(lines)


def load_trade_analysis() -> dict:
    """Load historical trade analysis if available."""
    if TRADE_ANALYSIS_FILE.exists():
        return json.loads(TRADE_ANALYSIS_FILE.read_text())
    return {}


def check_asymmetric_risk(entry_price: float, threshold: float = 85.0) -> CheckResult:
    """
    Check for asymmetric risk: high entry prices have limited upside.
    
    Learned from: Trade #2 at 95.9% - only 10% upside, 100% downside.
    """
    if entry_price > threshold:
        max_upside = 100 - entry_price
        max_downside = entry_price
        ratio = max_downside / max_upside if max_upside > 0 else float('inf')
        
        return CheckResult(
            passed=False,
            check_name="Asymmetric Risk",
            message=f"Entry at {entry_price:.1f}% gives only {max_upside:.1f}% upside vs {max_downside:.1f}% downside (ratio: {ratio:.1f}:1)",
            severity="warning" if entry_price < 92 else "critical"
        )
    
    return CheckResult(
        passed=True,
        check_name="Asymmetric Risk",
        message="Entry price allows reasonable risk/reward",
        severity="info"
    )


def check_vague_timeline(
    news_text: str, 
    deadline: Optional[datetime] = None,
    days_until_deadline: Optional[int] = None
) -> CheckResult:
    """
    Check for vague timeline language with tight deadlines.
    
    Learned from: Trade #1 - "Coming soon" rarely means "next week".
    """
    vague_terms = [
        "coming soon", "in the coming weeks", "shortly", "imminent",
        "around the corner", "in the near future", "expected soon",
        "any day now", "later this month"
    ]
    
    news_lower = news_text.lower()
    found_vague = [term for term in vague_terms if term in news_lower]
    
    if found_vague and days_until_deadline is not None and days_until_deadline <= 14:
        return CheckResult(
            passed=False,
            check_name="Vague Timeline",
            message=f"Found vague language ({', '.join(found_vague)}) with only {days_until_deadline} days until deadline",
            severity="critical"
        )
    elif found_vague:
        return CheckResult(
            passed=False,
            check_name="Vague Timeline",
            message=f"Found vague language: {', '.join(found_vague)}. Companies often miss vague deadlines.",
            severity="warning"
        )
    
    return CheckResult(
        passed=True,
        check_name="Vague Timeline",
        message="No vague timeline language detected",
        severity="info"
    )


def check_confirmation_bias(
    position_direction: str,  # 'yes' or 'no'
    current_price: float,
    thesis: str
) -> CheckResult:
    """
    Check if we might be chasing consensus.
    
    High prices on YES = market already believes it.
    """
    if position_direction.lower() == 'yes' and current_price > 80:
        return CheckResult(
            passed=False,
            check_name="Confirmation Bias",
            message=f"Betting YES at {current_price:.1f}% - you're agreeing with the crowd. What's your edge?",
            severity="warning"
        )
    elif position_direction.lower() == 'no' and current_price < 20:
        return CheckResult(
            passed=False,
            check_name="Confirmation Bias",
            message=f"Betting NO at {current_price:.1f}% - market already thinks NO. What's your edge?",
            severity="warning"
        )
    
    return CheckResult(
        passed=True,
        check_name="Confirmation Bias",
        message="Position is contrarian or neutral relative to market",
        severity="info"
    )


def check_position_size(
    trade_amount: float,
    portfolio_value: float,
    max_single_trade_pct: float = 10.0
) -> CheckResult:
    """
    Check position sizing against portfolio.
    
    Kelly criterion suggests never betting more than your edge.
    """
    pct_of_portfolio = (trade_amount / portfolio_value) * 100
    
    if pct_of_portfolio > max_single_trade_pct:
        return CheckResult(
            passed=False,
            check_name="Position Size",
            message=f"Trade is {pct_of_portfolio:.1f}% of portfolio (max recommended: {max_single_trade_pct}%)",
            severity="warning" if pct_of_portfolio < 20 else "critical"
        )
    
    return CheckResult(
        passed=True,
        check_name="Position Size",
        message=f"Trade is {pct_of_portfolio:.1f}% of portfolio (within limits)",
        severity="info"
    )


def check_exit_strategy(
    has_stop_loss: bool,
    has_take_profit: bool,
    has_trailing_stop: bool
) -> CheckResult:
    """
    Verify exit strategy is defined before entry.
    
    Learned from: Trade #2 - early exit without clear criteria.
    """
    if not any([has_stop_loss, has_take_profit, has_trailing_stop]):
        return CheckResult(
            passed=False,
            check_name="Exit Strategy",
            message="No exit strategy defined. Set stop-loss and/or take-profit before entering.",
            severity="warning"
        )
    
    exits = []
    if has_stop_loss:
        exits.append("stop-loss")
    if has_take_profit:
        exits.append("take-profit")
    if has_trailing_stop:
        exits.append("trailing-stop")
    
    return CheckResult(
        passed=True,
        check_name="Exit Strategy",
        message=f"Exit strategy defined: {', '.join(exits)}",
        severity="info"
    )


def check_thesis_clarity(thesis: str, min_words: int = 10) -> CheckResult:
    """
    Ensure thesis is clearly articulated.
    
    If you can't explain why you're trading, you shouldn't trade.
    """
    words = thesis.strip().split()
    
    if len(words) < min_words:
        return CheckResult(
            passed=False,
            check_name="Thesis Clarity",
            message=f"Thesis too short ({len(words)} words). Articulate your edge clearly.",
            severity="warning"
        )
    
    return CheckResult(
        passed=True,
        check_name="Thesis Clarity",
        message="Thesis is clearly articulated",
        severity="info"
    )


def check_recent_losses(min_trades: int = 3, max_loss_streak: int = 3) -> CheckResult:
    """
    Check for loss streaks that might indicate strategy issues.
    """
    analysis = load_trade_analysis()
    
    if not analysis or 'stats' not in analysis:
        return CheckResult(
            passed=True,
            check_name="Recent Performance",
            message="No historical trades to analyze",
            severity="info"
        )
    
    stats = analysis['stats']
    win_rate = stats.get('win_rate_pct', 0)
    total_trades = stats.get('total_trades', 0)
    
    if total_trades >= min_trades and win_rate == 0:
        return CheckResult(
            passed=False,
            check_name="Recent Performance",
            message=f"Win rate is {win_rate}% over {total_trades} trades. Consider reviewing strategy.",
            severity="critical"
        )
    elif total_trades >= min_trades and win_rate < 40:
        return CheckResult(
            passed=False,
            check_name="Recent Performance",
            message=f"Win rate is {win_rate:.1f}% over {total_trades} trades. Proceed with smaller size.",
            severity="warning"
        )
    
    return CheckResult(
        passed=True,
        check_name="Recent Performance",
        message=f"Historical performance: {win_rate:.1f}% win rate",
        severity="info"
    )


def run_checklist(
    entry_price: float,
    trade_amount: float,
    portfolio_value: float,
    position_direction: str,
    thesis: str,
    news_text: str = "",
    days_until_deadline: Optional[int] = None,
    has_stop_loss: bool = False,
    has_take_profit: bool = False,
    has_trailing_stop: bool = False,
) -> ChecklistResult:
    """
    Run all pre-trade checks and return combined result.
    
    Example:
        result = run_checklist(
            entry_price=95.0,
            trade_amount=500,
            portfolio_value=10000,
            position_direction="yes",
            thesis="OpenAI announced ads coming, market hasn't priced in yet",
            news_text="OpenAI says ads coming soon",
            days_until_deadline=7
        )
        print(result.get_summary())
    """
    checks = [
        check_asymmetric_risk(entry_price),
        check_vague_timeline(news_text, days_until_deadline=days_until_deadline),
        check_confirmation_bias(position_direction, entry_price, thesis),
        check_position_size(trade_amount, portfolio_value),
        check_exit_strategy(has_stop_loss, has_take_profit, has_trailing_stop),
        check_thesis_clarity(thesis),
        check_recent_losses(),
    ]
    
    critical = [c for c in checks if not c.passed and c.severity == 'critical']
    warnings = [c for c in checks if not c.passed and c.severity == 'warning']
    info = [c for c in checks if c.passed]
    
    return ChecklistResult(
        all_passed=len(critical) == 0 and len(warnings) == 0,
        critical_failures=critical,
        warnings=warnings,
        info=info
    )


if __name__ == "__main__":
    # Demo with a problematic trade (similar to Trade #2)
    print("=" * 60)
    print("PRE-TRADE CHECKLIST DEMO")
    print("=" * 60)
    
    result = run_checklist(
        entry_price=95.9,
        trade_amount=500,
        portfolio_value=10000,
        position_direction="yes",
        thesis="High confidence play - OpenAI confirmed ads",
        news_text="OpenAI says ads coming soon in the coming weeks",
        days_until_deadline=7,
        has_stop_loss=False,
        has_take_profit=False,
    )
    
    print(result.get_summary())
