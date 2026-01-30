#!/usr/bin/env python3
"""
Multi-Platform Prediction Market Scanner

Scans across multiple platforms:
1. Polymarket (primary, has trading)
2. Kalshi (secondary, regulated US exchange)
3. Metaculus (forecasting, for comparison/arbitrage detection)

Usage:
    ./venv/bin/python multi_scanner.py              # Scan all platforms
    ./venv/bin/python multi_scanner.py --ai         # AI markets only
    ./venv/bin/python multi_scanner.py --compare    # Cross-platform comparison
    ./venv/bin/python multi_scanner.py --notify     # Send Telegram alerts
"""

import argparse
import json
import os
import sys
from datetime import datetime
from typing import List, Dict, Any, Optional

# Add parent dir to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from polymarket.client import PolymarketClient
from metaculus.client import MetaculusClient

# Try Kalshi (may fail if no auth configured)
try:
    from kalshi.client import KalshiMarketClient, KALSHI_SDK_AVAILABLE
except ImportError:
    KALSHI_SDK_AVAILABLE = False
    KalshiMarketClient = None


class MultiPlatformScanner:
    """Scanner that aggregates opportunities across prediction market platforms."""
    
    def __init__(self, notify: bool = False):
        """Initialize scanner with all platform clients."""
        self.notify = notify
        
        # Initialize clients
        self.polymarket = PolymarketClient()
        self.metaculus = MetaculusClient()
        
        if KALSHI_SDK_AVAILABLE and KalshiMarketClient:
            self.kalshi = KalshiMarketClient()
        else:
            self.kalshi = None
            print("⚠️  Kalshi SDK not available")
        
        # For notifications
        self.notifier = None
        if notify:
            try:
                from alerts.telegram_notifier import TelegramNotifier
                self.notifier = TelegramNotifier()
            except Exception as e:
                print(f"⚠️  Telegram notifier not available: {e}")
    
    def scan_polymarket(self, ai_only: bool = True) -> List[Dict[str, Any]]:
        """Scan Polymarket for opportunities."""
        print("\n📊 Scanning Polymarket...")
        
        if ai_only:
            markets = self.polymarket.get_ai_markets()
        else:
            markets = self.polymarket.get_markets(limit=100)
        
        results = []
        for m in markets:
            results.append({
                "platform": "polymarket",
                "id": m.get("condition_id") or m.get("id"),
                "title": m.get("question") or m.get("title"),
                "yes_price": self._parse_price(m.get("outcomePrices", "[]")),
                "volume": float(m.get("volume", 0)),
                "url": f"https://polymarket.com/event/{m.get('slug', '')}"
            })
        
        print(f"   Found {len(results)} markets")
        return results
    
    def scan_kalshi(self, ai_only: bool = True) -> List[Dict[str, Any]]:
        """Scan Kalshi for opportunities."""
        if not self.kalshi:
            print("\n⏭️  Skipping Kalshi (SDK not configured)")
            return []
        
        print("\n🏛️  Scanning Kalshi...")
        
        if ai_only:
            markets = self.kalshi.get_ai_markets()
        else:
            result = self.kalshi.get_markets(limit=100)
            markets = result.get("markets", [])
        
        results = []
        for m in markets:
            results.append({
                "platform": "kalshi",
                "id": m.get("ticker"),
                "title": m.get("title"),
                "yes_price": m.get("yes_price"),
                "volume": m.get("volume", 0),
                "url": f"https://kalshi.com/markets/{m.get('ticker', '')}"
            })
        
        print(f"   Found {len(results)} markets")
        return results
    
    def scan_metaculus(self, ai_only: bool = True) -> List[Dict[str, Any]]:
        """Scan Metaculus for forecasts (not tradeable, but useful for comparison)."""
        print("\n🔮 Scanning Metaculus...")
        
        if ai_only:
            questions = self.metaculus.get_ai_questions(limit=50)
        else:
            result = self.metaculus.get_questions(limit=50)
            questions = result.get("results", [])
        
        results = []
        for q in questions:
            prob = q.get("community_probability")
            if prob is not None:  # Only include questions with forecasts
                results.append({
                    "platform": "metaculus",
                    "id": q.get("id"),
                    "title": q.get("title"),
                    "community_prob": prob,
                    "forecasters": q.get("forecasters_count", 0),
                    "url": q.get("url")
                })
        
        print(f"   Found {len(results)} questions with forecasts")
        return results
    
    def _parse_price(self, prices_str: str) -> Optional[float]:
        """Parse outcome prices from Polymarket JSON string."""
        try:
            if isinstance(prices_str, str):
                prices = json.loads(prices_str)
            else:
                prices = prices_str
            
            if prices and len(prices) > 0:
                return float(prices[0])
        except:
            pass
        return None
    
    def compare_platforms(self) -> List[Dict[str, Any]]:
        """
        Find arbitrage opportunities by comparing prices across platforms.
        
        Compares:
        - Polymarket vs Metaculus community predictions
        - Kalshi vs Polymarket (same underlying events)
        """
        print("\n🔄 Cross-Platform Comparison")
        print("=" * 60)
        
        # Get all markets/forecasts
        polymarket = self.scan_polymarket(ai_only=True)
        metaculus = self.scan_metaculus(ai_only=True)
        
        # Build keyword index for matching
        opportunities = []
        
        # Try to match Metaculus forecasts to Polymarket markets
        for mc in metaculus:
            if mc.get("community_prob") is None:
                continue
            
            mc_title = mc["title"].lower()
            mc_prob = mc["community_prob"]
            
            for pm in polymarket:
                pm_title = (pm.get("title") or "").lower()
                
                # Simple keyword matching (could be improved with embeddings)
                if self._titles_similar(mc_title, pm_title):
                    pm_price = pm.get("yes_price")
                    if pm_price is not None:
                        diff = mc_prob - pm_price
                        if abs(diff) > 0.05:  # 5pp threshold
                            opportunities.append({
                                "type": "metaculus_vs_polymarket",
                                "metaculus_title": mc["title"][:60],
                                "polymarket_title": pm["title"][:60],
                                "metaculus_prob": mc_prob,
                                "polymarket_price": pm_price,
                                "difference_pp": abs(diff) * 100,
                                "direction": "BUY_YES" if diff > 0 else "BUY_NO",
                                "polymarket_url": pm["url"]
                            })
        
        if opportunities:
            print(f"\n🎯 Found {len(opportunities)} potential arbitrage opportunities:\n")
            for opp in sorted(opportunities, key=lambda x: -x["difference_pp"])[:5]:
                print(f"  [{opp['difference_pp']:.1f}pp] {opp['direction']}")
                print(f"    Metaculus: {opp['metaculus_prob']*100:.1f}%")
                print(f"    Polymarket: {opp['polymarket_price']*100:.1f}%")
                print(f"    {opp['polymarket_title'][:50]}...")
                print()
        else:
            print("\n   No significant discrepancies found")
        
        return opportunities
    
    def _titles_similar(self, title1: str, title2: str) -> bool:
        """Check if two titles refer to the same event (simple keyword match)."""
        # Extract key entities
        keywords = ["gpt", "openai", "chatgpt", "anthropic", "claude", "google", "gemini",
                    "agi", "ai", "llm", "trump", "biden", "election", "bitcoin", "btc"]
        
        t1_keywords = set(kw for kw in keywords if kw in title1)
        t2_keywords = set(kw for kw in keywords if kw in title2)
        
        if not t1_keywords or not t2_keywords:
            return False
        
        # Need at least 2 keyword overlaps
        overlap = t1_keywords & t2_keywords
        return len(overlap) >= 2
    
    def scan_all(self, ai_only: bool = True) -> Dict[str, List[Dict[str, Any]]]:
        """Scan all platforms and return combined results."""
        print("=" * 60)
        print("🌐 Multi-Platform Prediction Market Scanner")
        print(f"   Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"   Mode: {'AI Markets Only' if ai_only else 'All Markets'}")
        print("=" * 60)
        
        results = {
            "polymarket": self.scan_polymarket(ai_only),
            "kalshi": self.scan_kalshi(ai_only),
            "metaculus": self.scan_metaculus(ai_only),
            "timestamp": datetime.now().isoformat()
        }
        
        # Summary
        total = sum(len(v) for k, v in results.items() if isinstance(v, list))
        print("\n" + "=" * 60)
        print(f"📈 Total: {total} markets/forecasts across 3 platforms")
        
        if self.notify and self.notifier:
            self._send_summary_alert(results)
        
        return results
    
    def _send_summary_alert(self, results: Dict):
        """Send summary alert via Telegram."""
        pm_count = len(results.get("polymarket", []))
        kl_count = len(results.get("kalshi", []))
        mc_count = len(results.get("metaculus", []))
        
        message = f"""🌐 **Multi-Platform Scan Complete**

📊 Polymarket: {pm_count} markets
🏛️ Kalshi: {kl_count} markets
🔮 Metaculus: {mc_count} forecasts

Total: {pm_count + kl_count + mc_count} opportunities tracked"""
        
        try:
            self.notifier.send_message(message)
        except Exception as e:
            print(f"⚠️  Failed to send alert: {e}")


def main():
    parser = argparse.ArgumentParser(description="Multi-Platform Prediction Market Scanner")
    parser.add_argument("--ai", action="store_true", help="AI markets only (default)")
    parser.add_argument("--all", action="store_true", help="All markets, not just AI")
    parser.add_argument("--compare", action="store_true", help="Cross-platform comparison")
    parser.add_argument("--notify", action="store_true", help="Send Telegram alerts")
    
    args = parser.parse_args()
    
    ai_only = not args.all
    scanner = MultiPlatformScanner(notify=args.notify)
    
    if args.compare:
        scanner.compare_platforms()
    else:
        scanner.scan_all(ai_only=ai_only)


if __name__ == "__main__":
    main()
