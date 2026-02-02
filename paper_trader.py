#!/usr/bin/env python3
"""
Paper Trading Tracker
Log hypothetical trades and track P&L
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, List, Dict
import sys

sys.path.insert(0, str(Path(__file__).parent))
from polymarket.client import PolymarketClient
from alerts.exit_tracker import ExitTracker
from risk_manager import RiskManager, Position

DATA_DIR = Path(__file__).parent / "data"
TRADES_FILE = DATA_DIR / "paper_trades.json"
STARTING_BALANCE = 10000.00  # $10k paper money


class PaperTrader:
    def __init__(self):
        DATA_DIR.mkdir(exist_ok=True)
        self.client = PolymarketClient()
        self.exit_tracker = ExitTracker(notify=False)  # Don't double notify on init
        self.risk_manager = RiskManager()
        self.trades = self._load_trades()
        self._sync_positions_to_risk_manager()
    
    def _sync_positions_to_risk_manager(self):
        """Sync open positions from trades file to RiskManager for exposure tracking."""
        open_trades = [t for t in self.trades if t["status"] == "OPEN"]
        for t in open_trades:
            # Skip test trades
            if t.get("market_slug", "").startswith("test"):
                continue
            
            position = Position(
                market_slug=t["market_slug"],
                market_title=t.get("question", t["market_slug"]),
                amount=t["amount"],
                entry_price=t["entry_price"],
                side=t["outcome"].lower()
            )
            self.risk_manager.add_position(position)
    
    def _load_trades(self) -> List[Dict]:
        """Load trade history"""
        if TRADES_FILE.exists():
            with open(TRADES_FILE) as f:
                return json.load(f)
        return []
    
    def _save_trades(self):
        """Save trade history"""
        with open(TRADES_FILE, "w") as f:
            json.dump(self.trades, f, indent=2)
    
    def buy(self, market_slug: str, outcome: str, amount: float, 
            entry_price: Optional[float] = None, reason: str = "",
            take_profit: Optional[float] = None,
            stop_loss: Optional[float] = None,
            trailing_stop: Optional[float] = None) -> Dict:
        """
        Paper buy a position
        
        Args:
            market_slug: Polymarket event slug
            outcome: Which outcome to buy (e.g., "Yes", "No")
            amount: Dollar amount to "spend"
            entry_price: Optional override price (otherwise fetched live)
            reason: Why we're taking this trade
            take_profit: Price target to exit
            stop_loss: Price target to stop loss
            trailing_stop: Trailing stop distance in pp
        """
        # Get current market data
        market = self.client.get_market_by_slug(market_slug)
        
        if not market and not entry_price:
            return {"error": f"Market not found: {market_slug}"}
        
        # Get price
        if entry_price is None:
            prices = self.client.parse_prices(market)
            if outcome not in prices:
                return {"error": f"Outcome '{outcome}' not found. Available: {list(prices.keys())}"}
            entry_price = prices[outcome]
        
        # Get current portfolio state for risk checks
        open_trades = [t for t in self.trades if t["status"] == "OPEN"]
        open_positions_count = len(open_trades)
        
        # Calculate daily P&L (closed trades today)
        from datetime import date
        today = date.today().isoformat()
        closed_today = [t for t in self.trades 
                       if t["status"] in ["CLOSED", "RESOLVED"] 
                       and t.get("closed_at", "")[:10] == today]
        daily_pnl = sum(t.get("pnl", 0) for t in closed_today)
        
        # Calculate current bankroll
        realized_pnl = sum(t.get("pnl", 0) for t in self.trades if t["status"] in ["CLOSED", "RESOLVED"])
        total_invested = sum(t["amount"] for t in open_trades)
        bankroll = STARTING_BALANCE + realized_pnl - total_invested
        
        # Full risk assessment
        market_title = market.get("question", market_slug) if market else market_slug
        allowed, messages = self.risk_manager.full_risk_check(
            market_slug=market_slug,
            market_title=market_title,
            amount=amount,
            entry_price=entry_price,
            open_positions_count=open_positions_count,
            daily_pnl=daily_pnl,
            bankroll=bankroll
        )
        
        # Print all risk messages (warnings and errors)
        for msg in messages:
            print(msg)
        
        # Block trade if risk checks fail
        if not allowed:
            return {"error": "Trade blocked by risk checks", "risk_messages": messages}
        
        # Calculate shares
        shares = (amount / entry_price) * 100  # Each share pays $1 if correct
        
        trade_id = len(self.trades) + 1
        trade = {
            "id": trade_id,
            "type": "BUY",
            "market_slug": market_slug,
            "question": market.get("question", "Unknown") if market else market_slug,
            "outcome": outcome,
            "entry_price": entry_price,
            "amount": amount,
            "shares": shares,
            "reason": reason,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "status": "OPEN",
            "exit_price": None,
            "pnl": None,
        }
        
        self.trades.append(trade)
        self._save_trades()
        
        # Track position in RiskManager for exposure calculations
        position = Position(
            market_slug=market_slug,
            market_title=market_title,
            amount=amount,
            entry_price=entry_price,
            side=outcome.lower()
        )
        self.risk_manager.add_position(position)
        
        # Set exit targets if provided
        if any([take_profit, stop_loss, trailing_stop]):
            self.exit_tracker.set_exit_target(
                trade_id, 
                take_profit=take_profit, 
                stop_loss=stop_loss, 
                trailing_stop=trailing_stop
            )
        
        print(f"""
✅ PAPER TRADE OPENED
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 {trade['question'][:60]}...
🎯 Position: {outcome} @ {entry_price:.1f}%
💵 Amount: ${amount:.2f}
📈 Shares: {shares:.2f}
💡 Reason: {reason}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
""")
        if trailing_stop:
            print(f"🛡️ Trailing Stop set: {trailing_stop:.1f}pp")
        
        return trade
    
    def close(self, trade_id: int, exit_price: Optional[float] = None) -> Dict:
        """Close a paper trade"""
        trade = None
        for t in self.trades:
            if t["id"] == trade_id and t["status"] == "OPEN":
                trade = t
                break
        
        if not trade:
            return {"error": f"Open trade {trade_id} not found"}
        
        # Get current price if not provided
        if exit_price is None:
            market = self.client.get_market_by_slug(trade["market_slug"])
            if market:
                prices = self.client.parse_prices(market)
                exit_price = prices.get(trade["outcome"], 0)
            else:
                return {"error": "Could not fetch current price"}
        
        # Calculate P&L
        # If price went up, we profit
        price_change = exit_price - trade["entry_price"]
        pnl = (price_change / 100) * trade["shares"]
        pnl_pct = (pnl / trade["amount"]) * 100
        
        trade["status"] = "CLOSED"
        trade["exit_price"] = exit_price
        trade["pnl"] = pnl
        trade["pnl_pct"] = pnl_pct
        trade["closed_at"] = datetime.now(timezone.utc).isoformat()
        
        self._save_trades()
        
        # Remove position from RiskManager
        self.risk_manager.remove_position(trade["market_slug"])
        
        emoji = "🟢" if pnl >= 0 else "🔴"
        print(f"""
{emoji} PAPER TRADE CLOSED
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 {trade['question'][:60]}...
🎯 {trade['outcome']}: {trade['entry_price']:.1f}% → {exit_price:.1f}%
💵 P&L: ${pnl:+.2f} ({pnl_pct:+.1f}%)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
""")
        
        return trade
    
    def resolve(self, trade_id: int, won: bool) -> Dict:
        """Resolve a trade when market settles"""
        trade = None
        for t in self.trades:
            if t["id"] == trade_id:
                trade = t
                break
        
        if not trade:
            return {"error": f"Trade {trade_id} not found"}
        
        if won:
            # Each share pays $1
            pnl = trade["shares"] - trade["amount"]
        else:
            # Lost everything
            pnl = -trade["amount"]
        
        pnl_pct = (pnl / trade["amount"]) * 100
        
        trade["status"] = "RESOLVED"
        trade["won"] = won
        trade["exit_price"] = 100 if won else 0
        trade["pnl"] = pnl
        trade["pnl_pct"] = pnl_pct
        trade["resolved_at"] = datetime.now(timezone.utc).isoformat()
        
        self._save_trades()
        
        emoji = "🏆" if won else "💀"
        print(f"""
{emoji} TRADE RESOLVED
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 {trade['question'][:60]}...
🎯 {trade['outcome']}: {"WON" if won else "LOST"}
💵 P&L: ${pnl:+.2f} ({pnl_pct:+.1f}%)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
""")
        
        return trade
    
    def status(self, exclude_test: bool = False, json_output: bool = False) -> Dict:
        """Get portfolio status"""
        trades = self.trades
        if exclude_test:
            trades = [t for t in trades if not t.get("market_slug", "").startswith("test")]
        open_trades = [t for t in trades if t["status"] == "OPEN"]
        closed_trades = [t for t in trades if t["status"] in ["CLOSED", "RESOLVED"]]
        
        total_invested = sum(t["amount"] for t in open_trades)
        realized_pnl = sum(t.get("pnl", 0) for t in closed_trades)
        
        wins = len([t for t in closed_trades if t.get("pnl", 0) > 0])
        losses = len([t for t in closed_trades if t.get("pnl", 0) <= 0])
        win_rate = (wins / len(closed_trades) * 100) if closed_trades else 0
        
        balance = STARTING_BALANCE + realized_pnl - total_invested
        
        status = {
            "starting_balance": STARTING_BALANCE,
            "current_balance": balance,
            "total_invested": total_invested,
            "realized_pnl": realized_pnl,
            "open_positions": len(open_trades),
            "closed_trades": len(closed_trades),
            "wins": wins,
            "losses": losses,
            "win_rate": win_rate,
            "open_trades": open_trades,
        }
        
        if json_output:
            return status
        
        print(f"""
📊 PAPER TRADING STATUS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
💰 Starting Balance: ${STARTING_BALANCE:,.2f}
💵 Current Balance:  ${balance:,.2f}
📈 Realized P&L:     ${realized_pnl:+,.2f}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📂 Open Positions:   {len(open_trades)}
💼 Total Invested:   ${total_invested:,.2f}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ Wins:  {wins}
❌ Losses: {losses}
🎯 Win Rate: {win_rate:.1f}%
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
""")
        
        if open_trades:
            print("OPEN POSITIONS:")
            for t in open_trades:
                print(f"  #{t['id']} {t['outcome']} @ {t['entry_price']:.1f}% | ${t['amount']:.2f}")
                print(f"      {t['question'][:50]}...")
        
        return status
    
    def list_trades(self, status_filter: Optional[str] = None, exclude_test: bool = False, json_output: bool = False) -> List[Dict]:
        """List all trades"""
        trades = self.trades
        if status_filter:
            trades = [t for t in trades if t["status"] == status_filter.upper()]
        if exclude_test:
            trades = [t for t in trades if not t.get("market_slug", "").startswith("test")]
        
        if json_output:
            return trades
        
        for t in trades:
            emoji = {"OPEN": "🔵", "CLOSED": "⚪", "RESOLVED": "🟢" if t.get("won") else "🔴"}.get(t["status"], "⚪")
            pnl_str = f"${t.get('pnl', 0):+.2f}" if t.get("pnl") is not None else "—"
            print(f"{emoji} #{t['id']} | {t['outcome']} @ {t['entry_price']:.1f}% | {pnl_str} | {t['question'][:40]}...")
        
        return trades
    
    def cleanup_test_trades(self, dry_run: bool = True, json_output: bool = False) -> Dict:
        """Remove all test trades (market_slug starting with 'test')"""
        test_trades = [t for t in self.trades if t.get("market_slug", "").startswith("test")]
        real_trades = [t for t in self.trades if not t.get("market_slug", "").startswith("test")]
        
        count = len(test_trades)
        
        result = {"removed": 0, "remaining": len(real_trades), "would_remove": count, "dry_run": dry_run}
        
        if count == 0:
            if not json_output:
                print("✅ No test trades found.")
            return result
        
        if dry_run:
            if not json_output:
                print(f"🔍 DRY RUN: Would remove {count} test trades, keeping {len(real_trades)} real trades.")
                print("   Run with --confirm to actually remove them.")
        else:
            self.trades = real_trades
            # Re-number remaining trades
            for i, t in enumerate(self.trades, 1):
                t["id"] = i
            self._save_trades()
            result["removed"] = count
            if not json_output:
                print(f"🗑️  Removed {count} test trades. {len(real_trades)} real trades remaining.")
        
        return result


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Paper Trading CLI")
    parser.add_argument("command", choices=["buy", "close", "resolve", "status", "list", "cleanup"])
    parser.add_argument("--slug", help="Market slug")
    parser.add_argument("--outcome", help="Outcome (Yes/No)")
    parser.add_argument("--amount", type=float, help="Dollar amount")
    parser.add_argument("--price", type=float, help="Entry/exit price override")
    parser.add_argument("--reason", default="", help="Trade reason")
    parser.add_argument("--id", type=int, help="Trade ID")
    parser.add_argument("--won", action="store_true", help="Trade won (for resolve)")
    parser.add_argument("--real", action="store_true", help="Exclude test trades from output")
    parser.add_argument("--confirm", action="store_true", help="Confirm cleanup action")
    
    # Exit targets
    parser.add_argument("--tp", type=float, help="Take profit price")
    parser.add_argument("--sl", type=float, help="Stop loss price")
    parser.add_argument("--ts", type=float, help="Trailing stop distance (pp)")
    
    # Output format
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    
    args = parser.parse_args()
    trader = PaperTrader()
    
    if args.command == "buy":
        if not all([args.slug, args.outcome, args.amount]):
            print("Usage: paper_trader.py buy --slug <slug> --outcome <Yes/No> --amount <$> [--tp N] [--sl N] [--ts N]")
            return
        trader.buy(
            args.slug, args.outcome, args.amount, args.price, args.reason,
            take_profit=args.tp, stop_loss=args.sl, trailing_stop=args.ts
        )
    
    elif args.command == "close":
        if not args.id:
            print("Usage: paper_trader.py close --id <trade_id>")
            return
        trader.close(args.id, args.price)
    
    elif args.command == "resolve":
        if not args.id:
            print("Usage: paper_trader.py resolve --id <trade_id> [--won]")
            return
        trader.resolve(args.id, args.won)
    
    elif args.command == "status":
        result = trader.status(exclude_test=args.real, json_output=args.json)
        if args.json:
            import json
            print(json.dumps(result, indent=2))
    
    elif args.command == "list":
        result = trader.list_trades(exclude_test=args.real, json_output=args.json)
        if args.json:
            import json
            print(json.dumps(result, indent=2))
    
    elif args.command == "cleanup":
        result = trader.cleanup_test_trades(dry_run=not args.confirm, json_output=args.json)
        if args.json:
            import json
            print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
