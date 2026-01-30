#!/usr/bin/env python3
"""
Real Trading Module for Polymarket
Uses py-clob-client for actual order execution

CAUTION: This trades real money. Use with care.

Setup Requirements:
1. Private key (EOA wallet) stored in .env
2. USDC on Polygon network
3. Token allowances set (for MetaMask/EOA)
"""

import os
import json
from datetime import datetime
from typing import Optional, Dict, List
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# py-clob-client imports
from py_clob_client.client import ClobClient
from py_clob_client.clob_types import (
    MarketOrderArgs,
    OrderArgs,
    OrderType,
    OpenOrderParams,
    BookParams
)
from py_clob_client.order_builder.constants import BUY, SELL

# Configuration
CLOB_HOST = "https://clob.polymarket.com"
CHAIN_ID = 137  # Polygon mainnet

# Data paths
DATA_DIR = Path(__file__).parent.parent / "data"
TRADES_FILE = DATA_DIR / "real_trades.json"
CONFIG_FILE = DATA_DIR / "trading_config.json"

class TradingConfig:
    """Trading configuration and limits"""
    def __init__(self):
        self.max_position_size = 100.0  # Max $ per position
        self.max_daily_loss = 50.0      # Stop trading if down this much
        self.max_open_positions = 5     # Max concurrent positions
        self.min_confidence = 0.7       # Minimum edge confidence
        self.enabled = False            # Trading disabled by default
        
        # Load config if exists
        if CONFIG_FILE.exists():
            with open(CONFIG_FILE) as f:
                config = json.load(f)
                self.max_position_size = config.get("max_position_size", self.max_position_size)
                self.max_daily_loss = config.get("max_daily_loss", self.max_daily_loss)
                self.max_open_positions = config.get("max_open_positions", self.max_open_positions)
                self.min_confidence = config.get("min_confidence", self.min_confidence)
                self.enabled = config.get("enabled", self.enabled)
    
    def save(self):
        """Save current config"""
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        with open(CONFIG_FILE, "w") as f:
            json.dump({
                "max_position_size": self.max_position_size,
                "max_daily_loss": self.max_daily_loss,
                "max_open_positions": self.max_open_positions,
                "min_confidence": self.min_confidence,
                "enabled": self.enabled
            }, f, indent=2)


class RealTrader:
    """
    Real trading client for Polymarket
    
    Environment variables required:
    - POLYMARKET_PRIVATE_KEY: Your wallet's private key
    - POLYMARKET_FUNDER: Address that holds your funds (optional for EOA)
    """
    
    def __init__(self, dry_run: bool = True):
        """
        Initialize the real trader
        
        Args:
            dry_run: If True, simulate orders but don't execute
        """
        self.dry_run = dry_run
        self.config = TradingConfig()
        self.client: Optional[ClobClient] = None
        self._trades: List[Dict] = []
        self._load_trades()
        
        # Try to initialize client
        self._init_client()
    
    def _init_client(self):
        """Initialize the CLOB client if credentials are available"""
        private_key = os.getenv("POLYMARKET_PRIVATE_KEY")
        funder = os.getenv("POLYMARKET_FUNDER")
        
        if not private_key:
            print("⚠️  POLYMARKET_PRIVATE_KEY not set - read-only mode")
            # Read-only client
            self.client = ClobClient(CLOB_HOST)
            return
        
        try:
            # Full client with trading capabilities
            self.client = ClobClient(
                CLOB_HOST,
                key=private_key,
                chain_id=CHAIN_ID,
                signature_type=0,  # EOA signature
                funder=funder if funder else None
            )
            # Set API credentials
            self.client.set_api_creds(self.client.create_or_derive_api_creds())
            print("✅ Trading client initialized")
        except Exception as e:
            print(f"❌ Failed to initialize trading client: {e}")
            self.client = ClobClient(CLOB_HOST)  # Fallback to read-only
    
    def _load_trades(self):
        """Load trade history"""
        if TRADES_FILE.exists():
            with open(TRADES_FILE) as f:
                self._trades = json.load(f)
    
    def _save_trades(self):
        """Save trade history"""
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        with open(TRADES_FILE, "w") as f:
            json.dump(self._trades, f, indent=2)
    
    def is_trading_enabled(self) -> bool:
        """Check if real trading is enabled and configured"""
        if not self.config.enabled:
            return False
        
        private_key = os.getenv("POLYMARKET_PRIVATE_KEY")
        if not private_key:
            return False
        
        return True
    
    def get_balance(self) -> Optional[float]:
        """Get USDC balance (requires full client)"""
        # Note: py-clob-client doesn't directly provide balance
        # Would need to query Polygon RPC or Polymarket's API
        print("⚠️  Balance check not implemented - use Polymarket UI")
        return None
    
    def get_orderbook(self, token_id: str) -> Dict:
        """Get orderbook for a market"""
        if not self.client:
            return {}
        
        try:
            book = self.client.get_order_book(token_id)
            return {
                "bids": [(o.price, o.size) for o in book.bids],
                "asks": [(o.price, o.size) for o in book.asks],
                "market": book.market
            }
        except Exception as e:
            print(f"Error fetching orderbook: {e}")
            return {}
    
    def get_midpoint(self, token_id: str) -> Optional[float]:
        """Get midpoint price for a token"""
        if not self.client:
            return None
        
        try:
            mid = self.client.get_midpoint(token_id)
            return float(mid) if mid else None
        except Exception as e:
            print(f"Error fetching midpoint: {e}")
            return None
    
    def get_price(self, token_id: str, side: str = "BUY") -> Optional[float]:
        """Get best available price for a side"""
        if not self.client:
            return None
        
        try:
            price = self.client.get_price(token_id, side=side)
            return float(price) if price else None
        except Exception as e:
            print(f"Error fetching price: {e}")
            return None
    
    def check_risk_limits(self, amount: float) -> tuple[bool, str]:
        """
        Check if trade passes risk limits
        
        Returns:
            (allowed, reason)
        """
        # Check position size
        if amount > self.config.max_position_size:
            return False, f"Amount ${amount} exceeds max position size ${self.config.max_position_size}"
        
        # Check number of open positions
        open_positions = sum(1 for t in self._trades if t.get("status") == "open")
        if open_positions >= self.config.max_open_positions:
            return False, f"Already at max positions ({open_positions})"
        
        # Check daily loss
        today = datetime.now().strftime("%Y-%m-%d")
        today_pnl = sum(
            t.get("realized_pnl", 0) 
            for t in self._trades 
            if t.get("closed_at", "").startswith(today)
        )
        if today_pnl <= -self.config.max_daily_loss:
            return False, f"Daily loss limit reached (${today_pnl:.2f})"
        
        return True, "OK"
    
    def place_market_order(
        self,
        token_id: str,
        side: str,  # "BUY" or "SELL"
        amount: float,
        market_name: str = ""
    ) -> Dict:
        """
        Place a market order (fill-or-kill)
        
        Args:
            token_id: The token to trade
            side: "BUY" or "SELL"
            amount: Dollar amount to trade
            market_name: Human-readable market name for logging
            
        Returns:
            Trade result dict
        """
        # Risk checks
        allowed, reason = self.check_risk_limits(amount)
        if not allowed:
            return {"success": False, "error": reason}
        
        if not self.is_trading_enabled():
            return {"success": False, "error": "Trading not enabled. Set POLYMARKET_PRIVATE_KEY and enable in config."}
        
        if self.dry_run:
            print(f"🧪 DRY RUN: Would {side} ${amount} of {token_id}")
            return {"success": True, "dry_run": True, "order": None}
        
        try:
            side_const = BUY if side.upper() == "BUY" else SELL
            
            order_args = MarketOrderArgs(
                token_id=token_id,
                amount=amount,
                side=side_const,
                order_type=OrderType.FOK  # Fill-or-kill
            )
            
            signed_order = self.client.create_market_order(order_args)
            response = self.client.post_order(signed_order, OrderType.FOK)
            
            # Log the trade
            trade = {
                "id": len(self._trades) + 1,
                "token_id": token_id,
                "market_name": market_name,
                "side": side,
                "amount": amount,
                "status": "open",
                "order_response": response,
                "created_at": datetime.now().isoformat()
            }
            self._trades.append(trade)
            self._save_trades()
            
            print(f"✅ Order placed: {side} ${amount} of {market_name}")
            return {"success": True, "trade": trade, "response": response}
            
        except Exception as e:
            print(f"❌ Order failed: {e}")
            return {"success": False, "error": str(e)}
    
    def place_limit_order(
        self,
        token_id: str,
        side: str,
        price: float,
        size: float,
        market_name: str = ""
    ) -> Dict:
        """
        Place a limit order (good-til-cancelled)
        
        Args:
            token_id: The token to trade
            side: "BUY" or "SELL"
            price: Limit price (0.00-1.00)
            size: Number of shares
            market_name: Human-readable market name
            
        Returns:
            Trade result dict
        """
        amount = price * size  # Approximate cost
        
        # Risk checks
        allowed, reason = self.check_risk_limits(amount)
        if not allowed:
            return {"success": False, "error": reason}
        
        if not self.is_trading_enabled():
            return {"success": False, "error": "Trading not enabled"}
        
        if self.dry_run:
            print(f"🧪 DRY RUN: Would place limit {side} {size} @ ${price} of {token_id}")
            return {"success": True, "dry_run": True, "order": None}
        
        try:
            side_const = BUY if side.upper() == "BUY" else SELL
            
            order_args = OrderArgs(
                token_id=token_id,
                price=price,
                size=size,
                side=side_const
            )
            
            signed_order = self.client.create_order(order_args)
            response = self.client.post_order(signed_order, OrderType.GTC)
            
            # Log the order
            trade = {
                "id": len(self._trades) + 1,
                "token_id": token_id,
                "market_name": market_name,
                "side": side,
                "type": "limit",
                "price": price,
                "size": size,
                "status": "pending",
                "order_response": response,
                "created_at": datetime.now().isoformat()
            }
            self._trades.append(trade)
            self._save_trades()
            
            print(f"✅ Limit order placed: {side} {size} shares @ ${price}")
            return {"success": True, "trade": trade, "response": response}
            
        except Exception as e:
            print(f"❌ Limit order failed: {e}")
            return {"success": False, "error": str(e)}
    
    def get_open_orders(self) -> List[Dict]:
        """Get all open orders"""
        if not self.is_trading_enabled():
            return []
        
        try:
            orders = self.client.get_orders(OpenOrderParams())
            return orders
        except Exception as e:
            print(f"Error fetching orders: {e}")
            return []
    
    def cancel_order(self, order_id: str) -> bool:
        """Cancel a specific order"""
        if not self.is_trading_enabled():
            return False
        
        try:
            self.client.cancel(order_id)
            print(f"✅ Order {order_id} cancelled")
            return True
        except Exception as e:
            print(f"❌ Cancel failed: {e}")
            return False
    
    def cancel_all_orders(self) -> bool:
        """Cancel all open orders"""
        if not self.is_trading_enabled():
            return False
        
        try:
            self.client.cancel_all()
            print("✅ All orders cancelled")
            return True
        except Exception as e:
            print(f"❌ Cancel all failed: {e}")
            return False
    
    def get_trade_history(self) -> List[Dict]:
        """Get local trade history"""
        return self._trades
    
    def status(self):
        """Print current status"""
        print("\n" + "=" * 60)
        print("  🤖 REAL TRADER STATUS")
        print("=" * 60)
        
        # Config
        print(f"\n  Trading Enabled: {'✅ YES' if self.config.enabled else '❌ NO'}")
        print(f"  Dry Run Mode: {'✅ YES' if self.dry_run else '❌ NO (LIVE!)'}")
        print(f"  Credentials: {'✅ Set' if os.getenv('POLYMARKET_PRIVATE_KEY') else '❌ Not set'}")
        
        # Limits
        print(f"\n  📊 Risk Limits:")
        print(f"     Max Position: ${self.config.max_position_size}")
        print(f"     Max Daily Loss: ${self.config.max_daily_loss}")
        print(f"     Max Open Positions: {self.config.max_open_positions}")
        
        # Trade history
        open_trades = [t for t in self._trades if t.get("status") == "open"]
        closed_trades = [t for t in self._trades if t.get("status") == "closed"]
        
        print(f"\n  📜 Trade History:")
        print(f"     Open Positions: {len(open_trades)}")
        print(f"     Closed Trades: {len(closed_trades)}")
        
        total_pnl = sum(t.get("realized_pnl", 0) for t in closed_trades)
        print(f"     Total Realized P&L: ${total_pnl:.2f}")
        
        print("=" * 60 + "\n")


def main():
    """CLI interface"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Polymarket Real Trader")
    parser.add_argument("--status", action="store_true", help="Show status")
    parser.add_argument("--enable", action="store_true", help="Enable trading")
    parser.add_argument("--disable", action="store_true", help="Disable trading")
    parser.add_argument("--dry-run", action="store_true", default=True, help="Run in dry-run mode")
    parser.add_argument("--live", action="store_true", help="Run in live mode (CAUTION)")
    
    args = parser.parse_args()
    
    dry_run = not args.live
    trader = RealTrader(dry_run=dry_run)
    
    if args.enable:
        trader.config.enabled = True
        trader.config.save()
        print("✅ Trading enabled")
    
    if args.disable:
        trader.config.enabled = False
        trader.config.save()
        print("❌ Trading disabled")
    
    if args.status or not any([args.enable, args.disable]):
        trader.status()


if __name__ == "__main__":
    main()
