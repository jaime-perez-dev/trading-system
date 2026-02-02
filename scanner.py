#!/usr/bin/env python3
"""
Trading Edge Scanner
Combines news monitoring + Polymarket tracking to find opportunities
"""

import sys
import json
import argparse
from datetime import datetime, timezone
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent))

from monitors.news_monitor import NewsMonitor
from monitors.web_scraper import WebScraper
from polymarket.client import PolymarketClient
from alerts.telegram_notifier import TelegramNotifier
from correlation_tracker import CorrelationTracker, NewsEvent

# Market mappings: keywords -> relevant Polymarket searches
MARKET_MAPPINGS = {
    "OpenAI": ["OpenAI", "ChatGPT", "GPT"],
    "ads": ["OpenAI ads", "ChatGPT advertising"],
    "IPO": ["OpenAI IPO", "Anthropic IPO"],
    "Anthropic": ["Anthropic", "Claude"],
    "regulation": ["AI regulation", "AI ban"],
    "Google": ["Google AI", "Gemini"],
    "Microsoft": ["Microsoft AI", "Copilot"],
}


class TradingScanner:
    def __init__(self, notify: bool = False, chat_id: str = None):
        self.news_monitor = NewsMonitor()
        self.web_scraper = WebScraper()
        self.polymarket = PolymarketClient()
        self.data_dir = Path(__file__).parent / "data"
        self.data_dir.mkdir(exist_ok=True)
        self.notify = notify
        self.notifier = TelegramNotifier(chat_id) if (notify and chat_id) else TelegramNotifier() if notify else None
        self.seen_file = self.data_dir / "seen_scraped.json"
        self._load_seen_scraped()
    
    def _load_seen_scraped(self):
        """Load previously seen scraped articles"""
        try:
            with open(self.seen_file) as f:
                self.seen_scraped = set(json.load(f))
        except:
            self.seen_scraped = set()
    
    def _save_seen_scraped(self):
        """Save seen scraped articles"""
        with open(self.seen_file, "w") as f:
            json.dump(list(self.seen_scraped), f)
    
    def scan(self) -> dict:
        """Run full scan: news + markets"""
        print("=" * 60)
        print(f"🔍 TRADING SCANNER - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 60)
        
        # 1. Check RSS feeds
        print("\n📰 Checking RSS feeds...")
        new_articles = self.news_monitor.check_all_feeds()
        
        # 2. Web scrape for additional coverage (official blogs, etc)
        print("\n🕸️ Scraping news sites...")
        scraped_articles = self.web_scraper.scrape_all()
        tradeable_scraped = self.web_scraper.filter_tradeable(scraped_articles)
        
        # Filter out already-seen scraped articles and convert to standard format
        for article in tradeable_scraped:
            url_hash = article.url[:100]  # Use URL as unique key
            if url_hash not in self.seen_scraped:
                self.seen_scraped.add(url_hash)
                score = self.web_scraper.score_article(article)
                if score >= 20:  # Only high-score articles
                    # Convert to standard article format
                    converted = {
                        "source": article.source,
                        "title": article.title,
                        "link": article.url,
                        "summary": article.summary,
                        "score": score,
                        "keywords": [],  # Will be detected from title
                        "entities": [],  # Will be detected from title
                        "is_tradeable": True,
                        "scraped": True,
                    }
                    # Detect entities from title
                    title_lower = article.title.lower()
                    for entity in ["OpenAI", "Anthropic", "Google", "Microsoft", "Meta", "xAI"]:
                        if entity.lower() in title_lower:
                            converted["entities"].append(entity)
                    # Detect keywords
                    for kw in ["ads", "launch", "funding", "acquisition", "billion", "partnership"]:
                        if kw in title_lower:
                            converted["keywords"].append(kw)
                    
                    if converted["entities"]:  # Only if we found relevant entities
                        new_articles.append(converted)
                        print(f"🚨 SCRAPED: {article.title[:70]}...")
        
        self._save_seen_scraped()
        
        # 2. Get current AI market state
        print("\n📊 Fetching AI markets...")
        markets = self.polymarket.get_tracked_ai_markets()
        
        # Sort by volume
        markets.sort(key=lambda x: float(x.get("volume", 0)), reverse=True)
        top_markets = markets[:15]
        
        print(f"\n📈 Top {len(top_markets)} AI Markets by Volume:\n")
        for m in top_markets:
            print(self.polymarket.format_market(m))
        
        # 3. If we have tradeable news, find relevant markets
        opportunities = []
        if new_articles:
            print("\n" + "🚨" * 20)
            print("⚡ POTENTIAL OPPORTUNITIES DETECTED ⚡")
            print("🚨" * 20 + "\n")
            
            for article in new_articles:
                # Find related markets
                related_markets = []
                for entity in article["entities"]:
                    if entity in MARKET_MAPPINGS:
                        for search_term in MARKET_MAPPINGS[entity]:
                            results = self.polymarket.search_markets(search_term, limit=5)
                            related_markets.extend(results)
                
                # Dedupe
                seen_ids = set()
                unique_markets = []
                for m in related_markets:
                    if m.get("id") not in seen_ids:
                        seen_ids.add(m.get("id"))
                        unique_markets.append(m)
                
                opp = {
                    "news": article,
                    "markets": unique_markets[:5],
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
                opportunities.append(opp)
                
                print(f"📰 NEWS: {article['title'][:70]}...")
                print(f"   Keywords: {article['keywords']}")
                print(f"   Entities: {article['entities']}")
                print(f"\n   Related Markets:")
                for m in unique_markets[:5]:
                    print(f"   • {m.get('question', 'Unknown')[:60]}...")
                    if "outcomePrices" in m:
                        prices = json.loads(m["outcomePrices"]) if isinstance(m["outcomePrices"], str) else m["outcomePrices"]
                        if prices:
                            print(f"     Current: {float(prices[0])*100:.1f}%")
                print()
                
                # Send notification if enabled
                if self.notifier:
                    self.notifier.alert_opportunity(article, unique_markets[:3])
                    print("   📱 Telegram alert sent!")
        else:
            print("\n✅ No new tradeable news detected.")
        
        # Save state
        state = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "new_articles": len(new_articles),
            "markets_tracked": len(top_markets),
            "opportunities": len(opportunities),
        }
        
        with open(self.data_dir / "last_scan.json", "w") as f:
            json.dump(state, f, indent=2)
        
        return {
            "articles": new_articles,
            "markets": top_markets,
            "opportunities": opportunities,
        }


def main():
    parser = argparse.ArgumentParser(description="Trading Edge Scanner")
    parser.add_argument("--notify", "-n", action="store_true", 
                       help="Send Telegram alerts for opportunities")
    parser.add_argument("--chat-id", "-c", type=str, default=None,
                       help="Override default Telegram chat ID")
    parser.add_argument("--quiet", "-q", action="store_true",
                       help="Minimal output (for cron jobs)")
    args = parser.parse_args()
    
    scanner = TradingScanner(notify=args.notify, chat_id=args.chat_id)
    results = scanner.scan()
    
    if not args.quiet:
        print("\n" + "=" * 60)
        print("📋 SCAN SUMMARY")
        print("=" * 60)
        print(f"New tradeable articles: {len(results['articles'])}")
        print(f"AI markets tracked: {len(results['markets'])}")
        print(f"Opportunities flagged: {len(results['opportunities'])}")
        print("=" * 60)
    
    # Return exit code based on opportunities found
    if results['opportunities']:
        return 1  # Found opportunities
    return 0


if __name__ == "__main__":
    exit(main())
