#!/usr/bin/env python3
"""
Tavily News Search - Web search for AI trading news
Uses Tavily API for AI-optimized search results.
"""

import os
import json
import hashlib
import requests
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict

# Try to load from environment, fall back to known key
TAVILY_API_KEY = os.environ.get('TAVILY_API_KEY', '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')
TAVILY_API_URL = 'https://api.tavily.com/search'

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data')
SEEN_FILE = os.path.join(DATA_DIR, 'tavily_seen.json')


@dataclass
class SearchResult:
    """A search result from Tavily"""
    title: str
    url: str
    content: str
    score: float
    published_date: Optional[str]
    source: str


@dataclass
class TradingSignal:
    """A potential trading signal extracted from search results"""
    headline: str
    url: str
    relevance_score: float
    entities: List[str]
    keywords: List[str]
    timestamp: str
    hash: str


# Keywords that indicate trading opportunities
TRADING_KEYWORDS = [
    # Product launches
    'launch', 'release', 'announce', 'unveil', 'introduce', 'debut', 'preview',
    # Partnerships/Deals
    'partner', 'deal', 'acquire', 'merge', 'invest', 'funding', 'raise',
    # Regulation
    'regulate', 'ban', 'approve', 'law', 'policy', 'antitrust', 'lawsuit',
    # Technical
    'breakthrough', 'achieve', 'milestone', 'benchmark', 'surpass', 'beat',
    # Business
    'revenue', 'profit', 'earnings', 'stock', 'shares', 'ipo', 'valuation',
    # AI-specific
    'gpt', 'claude', 'gemini', 'llama', 'agi', 'multimodal', 'reasoning',
]

# Entities we care about for prediction markets
TRACKED_ENTITIES = [
    'OpenAI', 'Anthropic', 'Google', 'DeepMind', 'Microsoft', 'Meta', 'Apple',
    'NVIDIA', 'xAI', 'Elon Musk', 'Sam Altman', 'Dario Amodei', 'Sundar Pichai',
    'Satya Nadella', 'Mark Zuckerberg', 'Jensen Huang', 'Mistral', 'Cohere',
    'Perplexity', 'Amazon', 'Tesla', 'Biden', 'Trump', 'FTC', 'EU', 'SEC',
]


def load_seen() -> set:
    """Load previously seen result hashes"""
    if os.path.exists(SEEN_FILE):
        with open(SEEN_FILE, 'r') as f:
            return set(json.load(f))
    return set()


def save_seen(seen: set):
    """Save seen result hashes"""
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(SEEN_FILE, 'w') as f:
        json.dump(list(seen), f)


def hash_result(title: str, url: str) -> str:
    """Create a unique hash for a search result"""
    return hashlib.md5(f"{title}|{url}".encode()).hexdigest()[:12]


def search_tavily(query: str, topic: str = 'news', max_results: int = 10, 
                   days: int = 3) -> List[SearchResult]:
    """
    Search Tavily API for news.
    
    Args:
        query: Search query
        topic: 'news' or 'general'
        max_results: Number of results to return
        days: For news, limit to last N days
    
    Returns:
        List of SearchResult objects
    """
    if not TAVILY_API_KEY:
        raise ValueError("TAVILY_API_KEY not set")
    
    payload = {
        'api_key': TAVILY_API_KEY,
        'query': query,
        'topic': topic,
        'max_results': max_results,
        'include_raw_content': False,
        'include_answer': False,
    }
    
    if topic == 'news':
        payload['days'] = days
    
    try:
        resp = requests.post(TAVILY_API_URL, json=payload, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        
        results = []
        for item in data.get('results', []):
            results.append(SearchResult(
                title=item.get('title', ''),
                url=item.get('url', ''),
                content=item.get('content', ''),
                score=item.get('score', 0.0),
                published_date=item.get('published_date'),
                source=item.get('source', '')
            ))
        return results
    except requests.RequestException as e:
        print(f"Tavily API error: {e}")
        return []


def extract_entities(text: str) -> List[str]:
    """Extract tracked entities from text"""
    text_lower = text.lower()
    found = []
    for entity in TRACKED_ENTITIES:
        if entity.lower() in text_lower:
            found.append(entity)
    return found


def extract_keywords(text: str) -> List[str]:
    """Extract trading-relevant keywords from text"""
    text_lower = text.lower()
    found = []
    for keyword in TRADING_KEYWORDS:
        if keyword in text_lower:
            found.append(keyword)
    return found


def score_relevance(result: SearchResult) -> float:
    """
    Score how relevant a search result is for trading.
    Higher score = more likely to be a trading signal.
    """
    text = f"{result.title} {result.content}"
    
    # Base score from Tavily's relevance
    score = result.score * 0.5
    
    # Boost for entities
    entities = extract_entities(text)
    score += len(entities) * 0.15
    
    # Boost for keywords
    keywords = extract_keywords(text)
    score += len(keywords) * 0.1
    
    # Cap at 1.0
    return min(score, 1.0)


def search_for_signals(queries: Optional[List[str]] = None, 
                       min_score: float = 0.4) -> List[TradingSignal]:
    """
    Search for trading signals using Tavily.
    
    Args:
        queries: Custom queries to search (defaults to AI-focused queries)
        min_score: Minimum relevance score to include
    
    Returns:
        List of TradingSignal objects, sorted by relevance
    """
    if queries is None:
        queries = [
            'AI news today OpenAI Anthropic Google',
            'artificial intelligence announcement launch',
            'AI regulation policy government',
            'AI company funding investment acquisition',
            'GPT Claude Gemini release update',
        ]
    
    seen = load_seen()
    all_signals = []
    
    for query in queries:
        results = search_tavily(query, topic='news', max_results=5, days=2)
        
        for result in results:
            result_hash = hash_result(result.title, result.url)
            
            # Skip already seen
            if result_hash in seen:
                continue
            
            # Score relevance
            relevance = score_relevance(result)
            if relevance < min_score:
                continue
            
            text = f"{result.title} {result.content}"
            signal = TradingSignal(
                headline=result.title,
                url=result.url,
                relevance_score=relevance,
                entities=extract_entities(text),
                keywords=extract_keywords(text),
                timestamp=datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
                hash=result_hash
            )
            all_signals.append(signal)
            seen.add(result_hash)
    
    # Save seen hashes
    save_seen(seen)
    
    # Sort by relevance (highest first)
    all_signals.sort(key=lambda s: s.relevance_score, reverse=True)
    
    return all_signals


def format_signal_alert(signal: TradingSignal) -> str:
    """Format a signal as a readable alert"""
    entities_str = ', '.join(signal.entities[:3]) if signal.entities else 'None'
    return f"""📰 **{signal.headline}**

Relevance: {signal.relevance_score:.0%}
Entities: {entities_str}
Keywords: {', '.join(signal.keywords[:5])}
URL: {signal.url}
"""


def main():
    """CLI entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Search for AI trading signals')
    parser.add_argument('-q', '--query', help='Custom search query')
    parser.add_argument('-n', '--num', type=int, default=10, help='Max results')
    parser.add_argument('--min-score', type=float, default=0.4, help='Min relevance')
    parser.add_argument('--json', action='store_true', help='Output as JSON')
    args = parser.parse_args()
    
    queries = [args.query] if args.query else None
    signals = search_for_signals(queries=queries, min_score=args.min_score)
    
    if args.json:
        print(json.dumps([asdict(s) for s in signals], indent=2))
    else:
        if not signals:
            print("No new trading signals found.")
        else:
            print(f"Found {len(signals)} trading signals:\n")
            for signal in signals[:args.num]:
                print(format_signal_alert(signal))
                print("-" * 50)


if __name__ == '__main__':
    main()
