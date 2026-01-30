#!/usr/bin/env python3
"""
News Monitor
Polls RSS feeds and detects AI-related news
"""

import feedparser
import requests
import re
import json
import hashlib
from datetime import datetime, timezone
from typing import List, Dict, Optional
from pathlib import Path

# RSS Feeds to monitor
RSS_FEEDS = {
    "the_verge_ai": "https://www.theverge.com/rss/ai-artificial-intelligence/index.xml",
    "the_verge_tech": "https://www.theverge.com/rss/tech/index.xml",
    "techcrunch_ai": "https://techcrunch.com/category/artificial-intelligence/feed/",
    "ars_technica": "https://feeds.arstechnica.com/arstechnica/technology-lab",
    "wired_ai": "https://www.wired.com/feed/tag/ai/latest/rss",
    "reuters_tech": "https://www.reutersagency.com/feed/?best-topics=tech",
}

# Keywords that signal tradeable news
KEYWORDS = {
    "high_impact": [
        "ads", "advertising", "IPO", "going public", "GPT-5", "GPT-6",
        "acquisition", "acquired", "merger", "partnership", "deal",
        "funding", "raised", "valuation", "billion",
        "launch", "released", "announces", "unveiled",
        "shutdown", "banned", "regulation", "lawsuit", "sued",
    ],
    "entities": [
        "OpenAI", "ChatGPT", "Anthropic", "Claude", "Google", "Gemini",
        "Microsoft", "Meta", "xAI", "Grok", "Perplexity", "Mistral",
    ]
}

DATA_DIR = Path(__file__).parent.parent / "data"


class NewsMonitor:
    def __init__(self):
        self.seen_file = DATA_DIR / "seen_articles.json"
        self.seen = self._load_seen()
        DATA_DIR.mkdir(parents=True, exist_ok=True)
    
    def _load_seen(self) -> set:
        """Load previously seen article hashes"""
        if self.seen_file.exists():
            with open(self.seen_file) as f:
                return set(json.load(f))
        return set()
    
    def _save_seen(self):
        """Save seen article hashes"""
        with open(self.seen_file, "w") as f:
            json.dump(list(self.seen), f)
    
    def _hash_article(self, title: str, link: str) -> str:
        """Create unique hash for article"""
        return hashlib.md5(f"{title}:{link}".encode()).hexdigest()
    
    def _score_article(self, title: str, summary: str) -> Dict:
        """Score article for trading relevance"""
        text = f"{title} {summary}".lower()
        
        score = 0
        matched_keywords = []
        matched_entities = []
        
        # Check high-impact keywords
        for kw in KEYWORDS["high_impact"]:
            if kw.lower() in text:
                score += 10
                matched_keywords.append(kw)
        
        # Check entities
        for entity in KEYWORDS["entities"]:
            if entity.lower() in text:
                score += 5
                matched_entities.append(entity)
        
        return {
            "score": score,
            "keywords": matched_keywords,
            "entities": matched_entities,
            "is_tradeable": score >= 15 and len(matched_entities) > 0
        }
    
    def fetch_feed(self, name: str, url: str) -> List[Dict]:
        """Fetch and parse a single RSS feed"""
        try:
            feed = feedparser.parse(url)
            articles = []
            
            for entry in feed.entries[:20]:  # Last 20 entries
                article = {
                    "source": name,
                    "title": entry.get("title", ""),
                    "link": entry.get("link", ""),
                    "summary": entry.get("summary", "")[:500],
                    "published": entry.get("published", ""),
                    "fetched_at": datetime.now(timezone.utc).isoformat(),
                }
                
                # Score it
                score_result = self._score_article(article["title"], article["summary"])
                article.update(score_result)
                
                articles.append(article)
            
            return articles
        except Exception as e:
            print(f"Error fetching {name}: {e}")
            return []
    
    def check_all_feeds(self) -> List[Dict]:
        """Check all feeds for new tradeable articles"""
        new_articles = []
        
        for name, url in RSS_FEEDS.items():
            articles = self.fetch_feed(name, url)
            
            for article in articles:
                article_hash = self._hash_article(article["title"], article["link"])
                
                if article_hash not in self.seen:
                    self.seen.add(article_hash)
                    
                    if article["is_tradeable"]:
                        new_articles.append(article)
                        print(f"🚨 TRADEABLE: {article['title'][:80]}...")
                        print(f"   Score: {article['score']} | Keywords: {article['keywords']}")
                        print(f"   Entities: {article['entities']}")
                        print(f"   Link: {article['link']}\n")
        
        self._save_seen()
        return new_articles
    
    def format_alert(self, article: Dict) -> str:
        """Format article as alert message"""
        return f"""
🚨 **TRADEABLE NEWS DETECTED**

📰 **{article['title']}**

🎯 Score: {article['score']}
🔑 Keywords: {', '.join(article['keywords'])}
🏢 Entities: {', '.join(article['entities'])}
📍 Source: {article['source']}
🔗 {article['link']}

⏰ Check Polymarket NOW for mispriced markets!
"""


def main():
    """Test the monitor"""
    print("📡 News Monitor Starting...\n")
    
    monitor = NewsMonitor()
    new_articles = monitor.check_all_feeds()
    
    print(f"\n✅ Found {len(new_articles)} new tradeable articles")
    
    if new_articles:
        print("\n" + "=" * 50)
        for article in new_articles:
            print(monitor.format_alert(article))


if __name__ == "__main__":
    main()
