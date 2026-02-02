#!/usr/bin/env python3
"""
Correlation Tracker - Prevent overexposure to correlated markets.

Groups markets by narrative/theme and tracks exposure to prevent betting
too heavily on outcomes that could all move together.

Example: Multiple AI company announcements could all tank on bad industry news.
"""

import json
import os
import re
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Optional
from pathlib import Path

DATA_DIR = Path(__file__).parent / "data"
CORRELATIONS_FILE = DATA_DIR / "correlations.json"
POSITIONS_FILE = DATA_DIR / "paper_trades.json"

# Narrative categories and their keywords
NARRATIVES = {
    "ai_companies": {
        "keywords": ["openai", "anthropic", "google ai", "deepmind", "meta ai", "microsoft ai", 
                     "claude", "gpt", "gemini", "llama", "chatgpt", "copilot"],
        "description": "AI company performance/announcements",
        "max_exposure_pct": 40,  # Max 40% of portfolio in correlated AI bets
    },
    "ai_regulation": {
        "keywords": ["ai regulation", "ai safety", "ai act", "executive order", "ai ban",
                     "ftc ai", "eu ai", "congress ai"],
        "description": "AI regulation and policy",
        "max_exposure_pct": 30,
    },
    "elections_us": {
        "keywords": ["trump", "biden", "harris", "election", "2024 election", "2026 election",
                     "republican", "democrat", "gop", "electoral"],
        "description": "US elections and politics",
        "max_exposure_pct": 35,
    },
    "crypto": {
        "keywords": ["bitcoin", "ethereum", "crypto", "btc", "eth", "sec crypto", "binance"],
        "description": "Cryptocurrency markets",
        "max_exposure_pct": 25,
    },
    "tech_earnings": {
        "keywords": ["earnings", "revenue", "quarterly", "q1", "q2", "q3", "q4", "guidance",
                     "nvidia", "apple", "meta", "alphabet", "amazon", "microsoft"],
        "description": "Tech company earnings",
        "max_exposure_pct": 35,
    },
    "geopolitics": {
        "keywords": ["china", "russia", "ukraine", "taiwan", "war", "sanctions", "tariff"],
        "description": "Geopolitical events",
        "max_exposure_pct": 30,
    },
}


@dataclass
class CorrelationCheck:
    """Result of a correlation check."""
    allowed: bool
    narrative: Optional[str] = None
    current_exposure_pct: float = 0.0
    max_exposure_pct: float = 100.0
    would_be_exposure_pct: float = 0.0
    warning: Optional[str] = None
    other_positions: list = field(default_factory=list)


class CorrelationTracker:
    """Track and limit exposure to correlated markets."""
    
    def __init__(self, positions_file: Path = POSITIONS_FILE, 
                 correlations_file: Path = CORRELATIONS_FILE):
        self.positions_file = positions_file
        self.correlations_file = correlations_file
        self.custom_correlations = self._load_custom_correlations()
    
    def _load_custom_correlations(self) -> dict:
        """Load user-defined market correlations."""
        if self.correlations_file.exists():
            with open(self.correlations_file) as f:
                return json.load(f)
        return {}
    
    def _save_custom_correlations(self):
        """Save custom correlations."""
        self.correlations_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.correlations_file, 'w') as f:
            json.dump(self.custom_correlations, f, indent=2)
    
    def add_correlation(self, market_slug: str, narrative: str):
        """Manually tag a market with a narrative."""
        if narrative not in NARRATIVES:
            raise ValueError(f"Unknown narrative: {narrative}. Valid: {list(NARRATIVES.keys())}")
        self.custom_correlations[market_slug] = narrative
        self._save_custom_correlations()
    
    def remove_correlation(self, market_slug: str):
        """Remove manual correlation tag."""
        if market_slug in self.custom_correlations:
            del self.custom_correlations[market_slug]
            self._save_custom_correlations()
    
    def detect_narrative(self, market_name: str, market_slug: str = "") -> Optional[str]:
        """Auto-detect narrative from market name/slug."""
        # Check custom correlations first
        if market_slug in self.custom_correlations:
            return self.custom_correlations[market_slug]
        
        text = f"{market_name} {market_slug}".lower()
        
        # Score each narrative by keyword matches
        best_narrative = None
        best_score = 0
        
        for narrative, config in NARRATIVES.items():
            score = sum(1 for kw in config["keywords"] if kw in text)
            if score > best_score:
                best_score = score
                best_narrative = narrative
        
        return best_narrative if best_score > 0 else None
    
    def get_positions(self) -> list:
        """Load current open positions."""
        if not self.positions_file.exists():
            return []
        
        with open(self.positions_file) as f:
            data = json.load(f)
        
        # Filter to open positions only
        return [p for p in data.get("positions", []) 
                if p.get("status") == "open" and not p.get("is_test", False)]
    
    def get_portfolio_value(self) -> float:
        """Calculate total portfolio value from open positions."""
        positions = self.get_positions()
        return sum(p.get("shares", 0) * p.get("entry_price", 0) / 100 for p in positions)
    
    def get_narrative_exposure(self, narrative: str) -> tuple[float, list]:
        """Get current exposure to a narrative and list of positions."""
        positions = self.get_positions()
        narrative_positions = []
        exposure = 0.0
        
        for pos in positions:
            pos_narrative = self.detect_narrative(
                pos.get("market_name", ""), 
                pos.get("market_slug", "")
            )
            if pos_narrative == narrative:
                position_value = pos.get("shares", 0) * pos.get("entry_price", 0) / 100
                exposure += position_value
                narrative_positions.append({
                    "id": pos.get("id"),
                    "market": pos.get("market_name", "")[:50],
                    "value": position_value,
                })
        
        return exposure, narrative_positions
    
    def check_correlation(self, market_name: str, market_slug: str, 
                          trade_value: float) -> CorrelationCheck:
        """
        Check if a trade would exceed correlation limits.
        
        Args:
            market_name: Name of the market to trade
            market_slug: Slug/ID of the market
            trade_value: Dollar value of proposed trade
            
        Returns:
            CorrelationCheck with allowed status and details
        """
        narrative = self.detect_narrative(market_name, market_slug)
        
        if not narrative:
            return CorrelationCheck(
                allowed=True,
                warning="No narrative detected - no correlation check applied"
            )
        
        config = NARRATIVES[narrative]
        portfolio_value = self.get_portfolio_value()
        current_exposure, positions = self.get_narrative_exposure(narrative)
        
        # If portfolio is empty/small, use trade_value as baseline
        effective_portfolio = max(portfolio_value + trade_value, trade_value)
        
        current_pct = (current_exposure / effective_portfolio * 100) if effective_portfolio > 0 else 0
        would_be_exposure = current_exposure + trade_value
        would_be_pct = (would_be_exposure / effective_portfolio * 100) if effective_portfolio > 0 else 0
        
        max_pct = config["max_exposure_pct"]
        allowed = would_be_pct <= max_pct
        
        warning = None
        if not allowed:
            warning = (f"Would exceed {narrative} exposure limit: "
                      f"{would_be_pct:.1f}% > {max_pct}% max")
        elif would_be_pct > max_pct * 0.8:  # 80% of limit = warning
            warning = (f"Approaching {narrative} exposure limit: "
                      f"{would_be_pct:.1f}% (max {max_pct}%)")
        
        return CorrelationCheck(
            allowed=allowed,
            narrative=narrative,
            current_exposure_pct=current_pct,
            max_exposure_pct=max_pct,
            would_be_exposure_pct=would_be_pct,
            warning=warning,
            other_positions=positions,
        )
    
    def get_exposure_summary(self) -> dict:
        """Get exposure breakdown by narrative."""
        portfolio_value = self.get_portfolio_value()
        summary = {}
        
        for narrative, config in NARRATIVES.items():
            exposure, positions = self.get_narrative_exposure(narrative)
            pct = (exposure / portfolio_value * 100) if portfolio_value > 0 else 0
            
            if exposure > 0 or positions:
                summary[narrative] = {
                    "description": config["description"],
                    "exposure": exposure,
                    "exposure_pct": pct,
                    "max_pct": config["max_exposure_pct"],
                    "utilization_pct": (pct / config["max_exposure_pct"] * 100) if config["max_exposure_pct"] > 0 else 0,
                    "positions": positions,
                }
        
        return {
            "portfolio_value": portfolio_value,
            "narratives": summary,
        }


def main():
    """CLI interface for correlation tracker."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Track market correlations")
    subparsers = parser.add_subparsers(dest="command", help="Commands")
    
    # Check command
    check_parser = subparsers.add_parser("check", help="Check if trade would exceed limits")
    check_parser.add_argument("market", help="Market name")
    check_parser.add_argument("--slug", default="", help="Market slug")
    check_parser.add_argument("--value", type=float, required=True, help="Trade value in USD")
    check_parser.add_argument("--json", action="store_true", help="JSON output")
    
    # Summary command
    summary_parser = subparsers.add_parser("summary", help="Show exposure summary")
    summary_parser.add_argument("--json", action="store_true", help="JSON output")
    
    # Tag command
    tag_parser = subparsers.add_parser("tag", help="Manually tag market with narrative")
    tag_parser.add_argument("market_slug", help="Market slug")
    tag_parser.add_argument("narrative", help="Narrative name")
    
    # Untag command
    untag_parser = subparsers.add_parser("untag", help="Remove manual tag")
    untag_parser.add_argument("market_slug", help="Market slug")
    
    # Narratives command
    subparsers.add_parser("narratives", help="List available narratives")
    
    args = parser.parse_args()
    tracker = CorrelationTracker()
    
    if args.command == "check":
        result = tracker.check_correlation(args.market, args.slug, args.value)
        if args.json:
            print(json.dumps(asdict(result), indent=2))
        else:
            status = "✅ ALLOWED" if result.allowed else "❌ BLOCKED"
            print(f"\n{status}")
            if result.narrative:
                print(f"Narrative: {result.narrative}")
                print(f"Current exposure: {result.current_exposure_pct:.1f}%")
                print(f"Would-be exposure: {result.would_be_exposure_pct:.1f}%")
                print(f"Max allowed: {result.max_exposure_pct}%")
            if result.warning:
                print(f"\n⚠️  {result.warning}")
            if result.other_positions:
                print(f"\nCorrelated positions:")
                for p in result.other_positions:
                    print(f"  - #{p['id']}: {p['market']} (${p['value']:.2f})")
    
    elif args.command == "summary":
        summary = tracker.get_exposure_summary()
        if args.json:
            print(json.dumps(summary, indent=2))
        else:
            print(f"\n📊 Portfolio Exposure Summary")
            print(f"Total Value: ${summary['portfolio_value']:.2f}\n")
            
            if not summary['narratives']:
                print("No correlated positions detected.")
            else:
                for name, data in summary['narratives'].items():
                    bar_len = int(data['utilization_pct'] / 5)  # 20 char max
                    bar = "█" * bar_len + "░" * (20 - bar_len)
                    status = "🔴" if data['utilization_pct'] > 100 else "🟡" if data['utilization_pct'] > 80 else "🟢"
                    print(f"{status} {name}: {data['exposure_pct']:.1f}% / {data['max_pct']}%")
                    print(f"   [{bar}] ${data['exposure']:.2f}")
                    print(f"   {data['description']}")
                    print()
    
    elif args.command == "tag":
        try:
            tracker.add_correlation(args.market_slug, args.narrative)
            print(f"✅ Tagged '{args.market_slug}' as '{args.narrative}'")
        except ValueError as e:
            print(f"❌ {e}")
    
    elif args.command == "untag":
        tracker.remove_correlation(args.market_slug)
        print(f"✅ Removed tag from '{args.market_slug}'")
    
    elif args.command == "narratives":
        print("\n📚 Available Narratives:\n")
        for name, config in NARRATIVES.items():
            print(f"  {name}")
            print(f"    {config['description']}")
            print(f"    Max exposure: {config['max_exposure_pct']}%")
            print(f"    Keywords: {', '.join(config['keywords'][:5])}...")
            print()
    
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
