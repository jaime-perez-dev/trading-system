from dataclasses import dataclass
from typing import Optional, Dict
from datetime import datetime

@dataclass
class RiskConfig:
    """Risk management configuration"""
    max_position_size: float = 100.0
    max_daily_loss: float = 50.0
    max_open_positions: int = 5
    min_confidence: float = 0.7
    asymmetric_risk_threshold: float = 85.0  # Percentage
    kelly_fraction: float = 0.25  # Use quarter Kelly for sizing

class RiskManager:
    def __init__(self, config: Optional[RiskConfig] = None):
        self.config = config or RiskConfig()

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
