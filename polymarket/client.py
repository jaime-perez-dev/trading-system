#!/usr/bin/env python3
"""
Polymarket API Client v2
Better search + AI market targeting
"""

import requests
import json
from datetime import datetime
from typing import Optional, List, Dict

GAMMA_API = "https://gamma-api.polymarket.com"

# AI-related event slugs to track
AI_EVENT_SLUGS = [
    "openai-implements-ads-on-llm-by-december-31",  # GPT ads
    "openai-ipo-closing-market-cap",  # OpenAI IPO
    "anthropic-ipo-closing-market-cap",  # Anthropic IPO
    "gpt-6-released-by",  # GPT-6
    "claude-5-released-by",  # Claude 5
    "grok-5-released-by",  # Grok 5
    "will-openai-launch-a-consumer-hardware-product-by",  # OpenAI hardware
]

class PolymarketClient:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"
        })
    
    def search_markets(self, query: str, limit: int = 20) -> List[Dict]:
        """Search for markets by keyword"""
        url = f"{GAMMA_API}/markets"
        params = {
            "limit": limit,
            "active": "true",
            "closed": "false",
            "tag": "ai",  # Filter by AI tag when possible
        }
        try:
            resp = self.session.get(url, params=params, timeout=15)
            resp.raise_for_status()
            markets = resp.json()
            
            # Filter by query in question text (strict - no fallback to all markets)
            query_lower = query.lower()
            filtered = [m for m in markets if query_lower in m.get("question", "").lower()]
            
            return filtered  # Return only matches, empty list if none
        except Exception as e:
            print(f"Error searching markets: {e}")
            return []
    
    def get_all_active_markets(self, limit: int = 100) -> List[Dict]:
        """Get all active markets"""
        url = f"{GAMMA_API}/markets"
        params = {
            "limit": limit,
            "active": "true",
            "closed": "false",
        }
        try:
            resp = self.session.get(url, params=params, timeout=15)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            print(f"Error fetching markets: {e}")
            return []
    
    def get_ai_markets(self) -> List[Dict]:
        """Get AI-related markets with better filtering"""
        import re
        all_markets = self.get_all_active_markets(limit=200)
        
        # Exact company/product names (case-insensitive)
        exact_terms = [
            "openai", "chatgpt", "gpt-4", "gpt-5", "gpt-6",
            "anthropic", "claude", "gemini", "deepmind",
            "copilot", "deepseek", "llama", "grok", "perplexity",
            "mistral", "hugging face", "midjourney", "stable diffusion",
            "sora", "dall-e", "dalle", "o1", "o3"
        ]
        
        # AI as a concept (need word boundaries to avoid false positives like "Aiyuk")
        concept_patterns = [
            r'\bai\b',  # "AI" as word, not in "Aiyuk"
            r'\bartificial intelligence\b',
            r'\bmachine learning\b',
            r'\blarge language model\b',
            r'\bllm\b',
            r'\bneural network\b',
            r'\bdeep learning\b',
            r'\bagi\b',  # artificial general intelligence
        ]
        
        ai_markets = []
        for m in all_markets:
            question = m.get("question", "").lower()
            description = m.get("description", "").lower()
            text = f"{question} {description}"
            
            # Check exact terms
            if any(term in text for term in exact_terms):
                ai_markets.append(m)
                continue
            
            # Check concept patterns with word boundaries
            if any(re.search(pattern, text) for pattern in concept_patterns):
                ai_markets.append(m)
        
        return ai_markets
    
    def get_market_by_slug(self, slug: str) -> Optional[Dict]:
        """Get specific market by slug"""
        url = f"{GAMMA_API}/markets"
        params = {"slug": slug}
        try:
            resp = self.session.get(url, params=params, timeout=10)
            resp.raise_for_status()
            markets = resp.json()
            return markets[0] if markets else None
        except Exception as e:
            print(f"Error fetching market: {e}")
            return None
    
    def get_event_markets(self, event_slug: str) -> List[Dict]:
        """Get all markets for a given event slug"""
        url = f"{GAMMA_API}/markets"
        params = {"limit": 50}
        try:
            resp = self.session.get(url, params=params, timeout=15)
            resp.raise_for_status()
            all_markets = resp.json()
            
            # Filter by event slug - handle events as JSON string if needed
            filtered_markets = []
            for m in all_markets:
                events = m.get("events", [])
                # Handle events as JSON string
                if isinstance(events, str):
                    try:
                        events = json.loads(events)
                    except json.JSONDecodeError:
                        events = []
                
                for e in events:
                    if e.get("slug") == event_slug:
                        filtered_markets.append(m)
                        break
            return filtered_markets
        except Exception as e:
            print(f"Error fetching event markets: {e}")
            return []
    
    def get_all_ai_events(self) -> List[Dict]:
        """Get all active AI-related events"""
        url = f"{GAMMA_API}/events"
        params = {"limit": 200, "active": "true", "closed": "false"}
        try:
            resp = self.session.get(url, params=params, timeout=15)
            resp.raise_for_status()
            events = resp.json()
            
            ai_patterns = [
                "gpt", "openai", "chatgpt", "anthropic", "claude",
                "gemini", "deepseek", "llama", "grok", "mistral",
                "ai model", "agi", "llm"
            ]
            
            ai_events = []
            for e in events:
                # Handle nested markets as JSON string if needed
                markets = e.get("markets", [])
                if isinstance(markets, str):
                    try:
                        markets = json.loads(markets)
                        e["markets"] = markets  # Update in place
                    except json.JSONDecodeError:
                        e["markets"] = []
                
                title = e.get("title", "").lower()
                if any(p in title for p in ai_patterns):
                    ai_events.append(e)
            
            return ai_events
        except Exception as e:
            print(f"Error fetching AI events: {e}")
            return []
    
    def get_tracked_ai_markets(self) -> List[Dict]:
        """Get markets for all tracked AI events by fetching event details"""
        all_markets = []
        seen_ids = set()
        
        # Get AI events with their nested markets
        events = self.get_all_ai_events()
        
        for event in events:
            markets = event.get("markets", [])
            for m in markets:
                market_id = m.get("id")
                if market_id and market_id not in seen_ids:
                    if m.get("active") and not m.get("closed"):
                        all_markets.append(m)
                        seen_ids.add(market_id)
        
        return all_markets
    
    def get_event_with_markets(self, event_slug: str) -> Optional[Dict]:
        """Get a specific event with all its markets"""
        url = f"{GAMMA_API}/events"
        params = {"slug": event_slug}
        try:
            resp = self.session.get(url, params=params, timeout=10)
            resp.raise_for_status()
            events = resp.json()
            
            if not events:
                return None
                
            event = events[0]
            
            # Handle nested markets as JSON string if needed
            markets = event.get("markets", [])
            if isinstance(markets, str):
                try:
                    markets = json.loads(markets)
                    event["markets"] = markets  # Update in place
                except json.JSONDecodeError:
                    event["markets"] = []
            
            return event
        except Exception as e:
            print(f"Error fetching event: {e}")
            return None
    
    def parse_prices(self, market: Dict) -> Dict[str, float]:
        """Parse outcome prices from market data"""
        prices = {}
        outcomes = market.get("outcomes", [])
        
        # BUGFIX: outcomes can be a JSON string, need to parse it
        if isinstance(outcomes, str):
            outcomes = json.loads(outcomes)
        
        if "outcomePrices" in market:
            raw_prices = market["outcomePrices"]
            if isinstance(raw_prices, str):
                raw_prices = json.loads(raw_prices)
            
            for i, outcome in enumerate(outcomes):
                if i < len(raw_prices):
                    prices[outcome] = float(raw_prices[i]) * 100
        
        return prices
    
    def format_market(self, market: Dict, compact: bool = False) -> str:
        """Format market for display"""
        question = market.get("question", "Unknown")
        prices = self.parse_prices(market)
        volume = float(market.get("volume", 0))
        liquidity = float(market.get("liquidity", 0))
        slug = market.get("slug", "")
        
        if compact:
            price_str = " | ".join([f"{k}: {v:.1f}%" for k, v in prices.items()])
            return f"{question[:50]}... | {price_str} | Vol: ${volume:,.0f}"
        
        prices_str = "\n".join([f"  • {k}: {v:.1f}%" for k, v in prices.items()])
        
        return f"""
📊 {question}
{prices_str}
💰 Volume: ${volume:,.0f} | Liquidity: ${liquidity:,.0f}
🔗 https://polymarket.com/event/{slug}
"""


def main():
    """Test improved client"""
    client = PolymarketClient()
    
    print("🔍 Searching AI markets with improved filter...\n")
    markets = client.get_ai_markets()
    
    # Sort by volume
    markets.sort(key=lambda x: float(x.get("volume", 0)), reverse=True)
    
    print(f"Found {len(markets)} AI-related markets:\n")
    
    for m in markets[:20]:
        print(client.format_market(m))
        print("-" * 50)


if __name__ == "__main__":
    main()
