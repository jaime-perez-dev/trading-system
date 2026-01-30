#!/usr/bin/env python3
"""
Web Scraper for News Sources
Direct scraping when RSS/search APIs are unavailable
Enhanced with OpenAI blog and better selectors
"""

import requests
import re
import json
import hashlib
from datetime import datetime, timezone
from typing import List, Dict, Optional
from pathlib import Path
from dataclasses import dataclass

try:
    from bs4 import BeautifulSoup
except ImportError:
    print("Installing beautifulsoup4...")
    import subprocess
    subprocess.run(["pip", "install", "beautifulsoup4", "lxml"], check=True)
    from bs4 import BeautifulSoup

@dataclass
class ScrapedArticle:
    """Article scraped from the web"""
    title: str
    url: str
    source: str
    summary: str = ""
    published: Optional[datetime] = None
    
    def to_dict(self) -> dict:
        return {
            "title": self.title,
            "url": self.url,
            "source": self.source,
            "summary": self.summary,
            "published": self.published.isoformat() if self.published else None
        }


class WebScraper:
    """Direct web scraper for news sites"""
    
    SOURCES = {
        # TechCrunch - various AI topics
        "techcrunch_openai": {
            "url": "https://techcrunch.com/tag/openai/",
            "selector": "a.loop-card__title-link, h2.post-block__title a, h3.mini-view__item__title a",
            "base_url": "https://techcrunch.com",
        },
        "techcrunch_ai": {
            "url": "https://techcrunch.com/category/artificial-intelligence/",
            "selector": "a.loop-card__title-link, h2.post-block__title a, h3.mini-view__item__title a",
            "base_url": "https://techcrunch.com",
        },
        "techcrunch_anthropic": {
            "url": "https://techcrunch.com/tag/anthropic/",
            "selector": "a.loop-card__title-link, h2.post-block__title a, h3.mini-view__item__title a",
            "base_url": "https://techcrunch.com",
        },
        # The Verge - updated selectors
        "theverge_ai": {
            "url": "https://www.theverge.com/ai-artificial-intelligence",
            "selector": "a[href*='/20']",  # Match links with year in URL
            "filter_pattern": r"/\d{4}/\d{1,2}/\d{1,2}/",  # Date pattern in URL
            "base_url": "https://www.theverge.com",
        },
        "theverge_openai": {
            "url": "https://www.theverge.com/openai",
            "selector": "a[href*='/20']",
            "filter_pattern": r"/\d{4}/\d{1,2}/\d{1,2}/",
            "base_url": "https://www.theverge.com",
        },
        # Ars Technica
        "arstechnica_ai": {
            "url": "https://arstechnica.com/ai/",
            "selector": "h2 a, h2.title a",
            "base_url": "https://arstechnica.com",
        },
        # OpenAI Official Blog
        "openai_blog": {
            "url": "https://openai.com/blog",
            "selector": "a[href*='/index/']",
            "base_url": "https://openai.com",
        },
        "openai_news": {
            "url": "https://openai.com/news",
            "selector": "a[href*='/index/']",
            "base_url": "https://openai.com",
        },
        # Anthropic Official Blog
        "anthropic_news": {
            "url": "https://www.anthropic.com/news",
            "selector": "a[href*='/news/']",
            "base_url": "https://www.anthropic.com",
        },
        # Google AI Blog
        "google_ai": {
            "url": "https://blog.google/technology/ai/",
            "selector": "a[href*='/technology/ai/']",
            "base_url": "https://blog.google",
        },
    }
    
    # Keywords for AI-related tradeable news
    TRADEABLE_KEYWORDS = [
        # Companies & Products
        "openai", "chatgpt", "gpt-5", "gpt-6", "gpt-7", "o1", "o2", "o3",
        "anthropic", "claude", "google", "gemini", "deepmind",
        "microsoft", "copilot", "meta", "llama", "facebook",
        "xai", "grok", "perplexity", "mistral", "cohere",
        "nvidia", "a100", "h100", "blackwell",
        # Market-moving events
        "ads", "advertising", "ipo", "going public",
        "acquisition", "acquired", "merger", "partnership", "deal",
        "funding", "raised", "billion", "valuation", "series",
        "launch", "released", "announces", "unveiled", "introducing",
        "shutdown", "banned", "regulation", "lawsuit", "sued",
        "hardware", "chip", "device", "wearable", "robot",
        # Specific tradeable events
        "government contract", "enterprise", "api pricing",
        "subscription", "revenue", "profit", "earnings",
    ]
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
        })
    
    def scrape_source(self, source_name: str) -> List[ScrapedArticle]:
        """Scrape a single news source"""
        if source_name not in self.SOURCES:
            return []
        
        config = self.SOURCES[source_name]
        articles = []
        seen_urls = set()
        
        try:
            resp = self.session.get(config["url"], timeout=15)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "lxml")
            
            # Find all matching links
            links = soup.select(config["selector"])[:30]  # Check more, filter down
            
            filter_pattern = config.get("filter_pattern")
            
            for link in links:
                title = link.get_text(strip=True)
                url = link.get("href", "")
                
                # Skip if no title or url
                if not title or not url or len(title) < 10:
                    continue
                
                # Apply URL pattern filter if specified
                if filter_pattern and not re.search(filter_pattern, url):
                    continue
                
                # Make absolute URL if relative
                if url.startswith("/"):
                    url = config.get("base_url", "") + url
                
                # Skip duplicates
                if url in seen_urls:
                    continue
                seen_urls.add(url)
                
                articles.append(ScrapedArticle(
                    title=title,
                    url=url,
                    source=source_name
                ))
                
                # Cap at 10 unique articles per source
                if len(articles) >= 10:
                    break
                    
        except requests.exceptions.RequestException as e:
            print(f"⚠️ Network error scraping {source_name}: {e}")
        except Exception as e:
            print(f"⚠️ Error scraping {source_name}: {e}")
        
        return articles
    
    def scrape_all(self) -> List[ScrapedArticle]:
        """Scrape all configured sources"""
        all_articles = []
        for source in self.SOURCES:
            articles = self.scrape_source(source)
            all_articles.extend(articles)
            if articles:
                print(f"📰 {source}: {len(articles)} articles")
            else:
                print(f"⚠️ {source}: 0 articles")
        return all_articles
    
    def filter_tradeable(self, articles: List[ScrapedArticle]) -> List[ScrapedArticle]:
        """Filter articles for tradeable news"""
        tradeable = []
        seen_titles = set()
        
        for article in articles:
            # Dedupe by similar titles
            title_key = article.title.lower()[:50]
            if title_key in seen_titles:
                continue
            seen_titles.add(title_key)
            
            if any(kw in title_key for kw in self.TRADEABLE_KEYWORDS):
                tradeable.append(article)
        return tradeable
    
    def get_article_content(self, url: str) -> str:
        """Fetch article content for analysis"""
        try:
            resp = self.session.get(url, timeout=15)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "lxml")
            
            # Try common article selectors
            for selector in ["article", ".article-body", ".post-content", "main", "[role='main']"]:
                content = soup.select_one(selector)
                if content:
                    # Get text, remove script/style
                    for tag in content.find_all(["script", "style", "nav", "footer"]):
                        tag.decompose()
                    text = content.get_text(strip=True, separator=" ")
                    # Clean up whitespace
                    text = re.sub(r'\s+', ' ', text)
                    return text[:3000]
            
            return ""
        except Exception as e:
            return f"Error: {e}"
    
    def score_article(self, article: ScrapedArticle) -> int:
        """Score article for trading relevance (0-100)"""
        title_lower = article.title.lower()
        score = 0
        
        # High-impact keywords
        high_impact = ["ads", "advertising", "ipo", "acquisition", "billion", "launch", "released"]
        for kw in high_impact:
            if kw in title_lower:
                score += 20
        
        # Medium-impact keywords
        medium_impact = ["funding", "partnership", "announces", "unveiled", "deal"]
        for kw in medium_impact:
            if kw in title_lower:
                score += 10
        
        # Entity mentions
        entities = ["openai", "anthropic", "google", "microsoft", "meta", "xai"]
        for entity in entities:
            if entity in title_lower:
                score += 15
        
        return min(score, 100)


def main():
    """Test the web scraper"""
    print("🕸️ Web Scraper Test\n")
    
    scraper = WebScraper()
    
    # Scrape all sources
    all_articles = scraper.scrape_all()
    
    print(f"\n📊 Total articles: {len(all_articles)}")
    
    # Filter for tradeable
    tradeable = scraper.filter_tradeable(all_articles)
    
    print(f"🎯 Tradeable articles: {len(tradeable)}")
    
    if tradeable:
        print("\n📰 Tradeable Headlines (sorted by score):")
        # Sort by score
        scored = [(a, scraper.score_article(a)) for a in tradeable]
        scored.sort(key=lambda x: x[1], reverse=True)
        
        for i, (article, score) in enumerate(scored[:15], 1):
            print(f"  {i}. [{article.source}] (score:{score}) {article.title[:60]}...")
            print(f"     {article.url}")


if __name__ == "__main__":
    main()
