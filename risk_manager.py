from dataclasses import dataclass, field
from typing import Optional, Dict, List
from datetime import datetime, date
from collections import defaultdict


# Common narratives/themes for correlation tracking
NARRATIVE_KEYWORDS = {
    "ai_safety": ["safety", "alignment", "existential", "risk", "regulation", "oversight"],
    "ai_progress": ["gpt", "claude", "gemini", "llama", "model", "benchmark", "capability"],
    "ai_business": ["revenue", "valuation", "ipo", "acquisition", "partnership", "deal"],
    "ai_regulation": ["regulation", "congress", "eu", "law", "ban", "antitrust", "ftc"],
    "ai_release": ["release", "launch", "announce", "ship", "available", "api"],
}


@dataclass
class RiskConfig:
    """Risk management configuration"""
    max_position_size: float = 100.0
    max_daily_loss: float = 50.0
    max_open_positions: int = 5
    min_confidence: float = 0.7
    asymmetric_risk_threshold: float = 85.0  # Percentage
    kelly_fraction: float = 0.25  # Use quarter Kelly for sizing
    
    # New: Exposure limits
    max_market_exposure: float = 300.0  # Max total $ in one market
    max_narrative_exposure: float = 500.0  # Max total $ in one narrative
    max_daily_loss_pct: float = 5.0  # Stop trading if down X% of bankroll


@dataclass
class Position:
    """Represents an open position for exposure tracking"""
    market_slug: str
    market_title: str
    amount: float
    entry_price: float
    side: str  # "yes" or "no"
    narratives: List[str] = field(default_factory=list)


class RiskManager:
    def __init__(self, config: Optional[RiskConfig] = None):
        self.config = config or RiskConfig()
        self._positions: Dict[str, Position] = {}  # market_slug -> Position
        self._daily_pnl: Dict[str, float] = {}  # date string -> P&L
    
    def add_position(self, position: Position) -> None:
        """Track a new position for exposure calculations."""
        self._positions[position.market_slug] = position
    
    def remove_position(self, market_slug: str) -> None:
        """Remove a closed position from tracking."""
        self._positions.pop(market_slug, None)
    
    def get_positions(self) -> Dict[str, Position]:
        """Get all tracked positions."""
        return self._positions.copy()

    def check_trade_limits(self, amount: float, open_positions_count: int, 
                          daily_pnl: float) -> tuple[bool, str]:
        """
        Check if a trade passes hard risk limits (size, count, drawdown).
        Used primarily by RealTrader.
        """
        # 1. Position Size
        if amount > self.config.max_position_size:
            return False, f"Amount ${amount} exceeds max position size ${self.config.max_position_size}"
            
        # 2. Max Open Positions
        if open_positions_count >= self.config.max_open_positions:
            return False, f"Already at max positions ({open_positions_count})"
            
        # 3. Daily Loss Limit
        if daily_pnl <= -self.config.max_daily_loss:
            return False, f"Daily loss limit reached (${daily_pnl:.2f})"
            
        return True, "OK"

    def check_market_exposure(self, market_slug: str, additional_amount: float) -> tuple[bool, str]:
        """
        Check if adding to a market would exceed per-market exposure limits.
        
        Args:
            market_slug: The market identifier
            additional_amount: Amount to add to the position
            
        Returns:
            (allowed, message) tuple
        """
        current_exposure = 0.0
        if market_slug in self._positions:
            current_exposure = self._positions[market_slug].amount
        
        new_exposure = current_exposure + additional_amount
        
        if new_exposure > self.config.max_market_exposure:
            return False, (
                f"Market exposure ${new_exposure:.2f} would exceed limit "
                f"${self.config.max_market_exposure:.2f} for {market_slug}"
            )
        
        return True, "OK"
    
    def check_narrative_exposure(self, market_title: str, additional_amount: float) -> tuple[bool, str]:
        """
        Check if a trade would overexpose to a particular narrative/theme.
        
        Args:
            market_title: The market title to analyze for narrative
            additional_amount: Amount being added
            
        Returns:
            (allowed, message) tuple with any warnings
        """
        # Detect narratives from market title
        detected_narratives = self._detect_narratives(market_title)
        
        if not detected_narratives:
            return True, "OK"  # No narrative detected, allow
        
        # Calculate current exposure per narrative
        narrative_exposure = self._calculate_narrative_exposure()
        
        # Check each detected narrative
        for narrative in detected_narratives:
            current = narrative_exposure.get(narrative, 0.0)
            new_exposure = current + additional_amount
            
            if new_exposure > self.config.max_narrative_exposure:
                return False, (
                    f"Narrative '{narrative}' exposure ${new_exposure:.2f} would exceed "
                    f"limit ${self.config.max_narrative_exposure:.2f}"
                )
        
        return True, "OK"
    
    def get_exposure_summary(self) -> Dict:
        """
        Get a summary of current exposure by market and narrative.
        
        Returns:
            Dict with market_exposure, narrative_exposure, and total_exposure
        """
        market_exposure = {}
        for slug, pos in self._positions.items():
            market_exposure[slug] = pos.amount
        
        narrative_exposure = self._calculate_narrative_exposure()
        total_exposure = sum(pos.amount for pos in self._positions.values())
        
        return {
            "market_exposure": market_exposure,
            "narrative_exposure": narrative_exposure,
            "total_exposure": total_exposure,
            "position_count": len(self._positions),
        }
    
    def _detect_narratives(self, text: str) -> List[str]:
        """Detect which narratives a market title belongs to."""
        text_lower = text.lower()
        detected = []
        
        for narrative, keywords in NARRATIVE_KEYWORDS.items():
            if any(kw in text_lower for kw in keywords):
                detected.append(narrative)
        
        return detected
    
    def _calculate_narrative_exposure(self) -> Dict[str, float]:
        """Calculate total exposure per narrative across all positions."""
        exposure = defaultdict(float)
        
        for pos in self._positions.values():
            narratives = pos.narratives or self._detect_narratives(pos.market_title)
            for narrative in narratives:
                exposure[narrative] += pos.amount
        
        return dict(exposure)

    def check_asymmetric_risk(self, entry_price: float) -> Optional[str]:
        """
        Check for asymmetric risk (high entry price).
        Returns formatted warning message if risky, None otherwise.
        """
        if entry_price > self.config.asymmetric_risk_threshold:
            upside_pct = (100 - entry_price) / entry_price * 100
            downside_pct = entry_price / entry_price * 100
            
            # Calculate Risk/Reward ratio (Upside / Downside)
            # e.g. 10% upside / 100% downside = 0.1 ratio
            rr_ratio = upside_pct / 100.0
            
            return f"""
⚠️  ASYMMETRIC RISK WARNING
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Entry at {entry_price:.1f}% means:
  📈 Max upside: +{upside_pct:.1f}% (price to 100%)
  📉 Max downside: -{downside_pct:.1f}% (price to 0%)
  
Risk/Reward: 1:{rr_ratio:.2f} — very unfavorable
Consider smaller position size or skip.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
        return None

    def calculate_kelly_size(self, win_prob: float, odds: float, bankroll: float) -> float:
        """
        Calculate position size using Kelly Criterion.
        
        Args:
            win_prob: Probability of winning (0.0-1.0)
            odds: Decimal odds (e.g. 2.0 for 1:1 payout) - Polymarket is binary, so odds depend on price
                  If price is 0.40, odds are 1/0.40 = 2.5
            bankroll: Total available capital
            
        Returns:
            Recommended dollar amount to wager
        """
        # Kelly Formula: f = (bp - q) / b
        # b = odds - 1 (net decimal odds)
        # p = probability of winning
        # q = probability of losing (1-p)
        
        if win_prob <= 0 or win_prob >= 1:
            return 0.0
            
        b = odds - 1
        p = win_prob
        q = 1 - p
        
        f = (b * p - q) / b
        
        # Apply fractional Kelly for safety
        f_safe = f * self.config.kelly_fraction
        
        if f_safe <= 0:
            return 0.0
            
        return bankroll * f_safe
    
    def check_daily_loss_percentage(self, daily_pnl: float, bankroll: float) -> tuple[bool, str]:
        """
        Check if daily loss exceeds percentage of bankroll.
        
        Args:
            daily_pnl: Today's P&L (negative if losing)
            bankroll: Total bankroll
            
        Returns:
            (allowed_to_trade, message) tuple
        """
        if bankroll <= 0:
            return False, "Invalid bankroll"
        
        loss_pct = abs(min(0, daily_pnl)) / bankroll * 100
        
        if loss_pct >= self.config.max_daily_loss_pct:
            return False, (
                f"Daily loss {loss_pct:.1f}% exceeds limit {self.config.max_daily_loss_pct:.1f}%. "
                "Stop trading for today."
            )
        
        return True, "OK"
    
    def full_risk_check(
        self, 
        market_slug: str,
        market_title: str,
        amount: float, 
        entry_price: float,
        open_positions_count: int,
        daily_pnl: float,
        bankroll: float
    ) -> tuple[bool, List[str]]:
        """
        Run all risk checks for a proposed trade.
        
        Returns:
            (allowed, messages) - allowed is False if any hard limit hit,
            messages contains all warnings and errors
        """
        messages = []
        allowed = True
        
        # 1. Basic trade limits
        ok, msg = self.check_trade_limits(amount, open_positions_count, daily_pnl)
        if not ok:
            allowed = False
            messages.append(f"❌ {msg}")
        
        # 2. Market exposure
        ok, msg = self.check_market_exposure(market_slug, amount)
        if not ok:
            allowed = False
            messages.append(f"❌ {msg}")
        
        # 3. Narrative exposure
        ok, msg = self.check_narrative_exposure(market_title, amount)
        if not ok:
            allowed = False
            messages.append(f"❌ {msg}")
        
        # 4. Daily loss percentage
        ok, msg = self.check_daily_loss_percentage(daily_pnl, bankroll)
        if not ok:
            allowed = False
            messages.append(f"❌ {msg}")
        
        # 5. Asymmetric risk (warning only, doesn't block)
        warning = self.check_asymmetric_risk(entry_price)
        if warning:
            messages.append(warning)
        
        if allowed and not messages:
            messages.append("✅ All risk checks passed")
        
        return allowed, messages
