"""
Kalshi Prediction Market Client

API Documentation: https://docs.kalshi.com
Python SDK: kalshi-python (v2.1.4)

NOTE: Kalshi requires API key authentication for trading.
Read-only market data may be available without auth.
"""

import os
from typing import Optional, List, Dict, Any
from datetime import datetime

try:
    from kalshi_python import Configuration, KalshiClient
    KALSHI_SDK_AVAILABLE = True
except ImportError:
    KALSHI_SDK_AVAILABLE = False
    print("Warning: kalshi-python not installed. Run: pip install kalshi-python")


class KalshiMarketClient:
    """Client for Kalshi prediction market data and trading."""
    
    # Kalshi API endpoint
    BASE_URL = "https://api.elections.kalshi.com/trade-api/v2"
    
    def __init__(self, api_key_id: Optional[str] = None, private_key_path: Optional[str] = None):
        """
        Initialize Kalshi client.
        
        Args:
            api_key_id: Kalshi API key ID (or set KALSHI_API_KEY_ID env var)
            private_key_path: Path to private key PEM file (or set KALSHI_PRIVATE_KEY_PATH env var)
        """
        self.api_key_id = api_key_id or os.getenv("KALSHI_API_KEY_ID")
        self.private_key_path = private_key_path or os.getenv("KALSHI_PRIVATE_KEY_PATH")
        self.client = None
        self.authenticated = False
        
        if KALSHI_SDK_AVAILABLE:
            self._init_client()
    
    def _init_client(self):
        """Initialize the Kalshi SDK client."""
        config = Configuration(host=self.BASE_URL)
        
        # Add auth if credentials available
        if self.api_key_id and self.private_key_path:
            try:
                with open(self.private_key_path, "r") as f:
                    private_key = f.read()
                config.api_key_id = self.api_key_id
                config.private_key_pem = private_key
                self.authenticated = True
            except FileNotFoundError:
                print(f"Warning: Private key not found at {self.private_key_path}")
        
        self.client = KalshiClient(config)
    
    def get_markets(self, 
                    status: str = "open",
                    series_ticker: Optional[str] = None,
                    limit: int = 100,
                    cursor: Optional[str] = None) -> Dict[str, Any]:
        """
        Get list of markets.
        
        Args:
            status: Market status (open, closed, settled)
            series_ticker: Filter by series (e.g., "KXAITRAINING" for AI markets)
            limit: Max results per page
            cursor: Pagination cursor
            
        Returns:
            Dict with markets list and pagination info
        """
        if not self.client:
            return {"error": "Client not initialized", "markets": []}
        
        try:
            params = {"status": status, "limit": limit}
            if series_ticker:
                params["series_ticker"] = series_ticker
            if cursor:
                params["cursor"] = cursor
            
            response = self.client.get_markets(**params)
            
            # Convert Pydantic models to dicts if needed
            markets = response.markets if hasattr(response, 'markets') else []
            markets_list = []
            for m in markets:
                if hasattr(m, 'model_dump'):
                    # Pydantic v2
                    markets_list.append(m.model_dump())
                elif hasattr(m, 'dict'):
                    # Pydantic v1
                    markets_list.append(m.dict())
                elif hasattr(m, 'title'):
                    # Keep as is, handle in get_ai_markets
                    markets_list.append(m)
                else:
                    markets_list.append(m)
            
            return {
                "markets": markets_list,
                "cursor": response.cursor if hasattr(response, 'cursor') else None
            }
        except Exception as e:
            return {"error": str(e), "markets": []}
    
    def get_market(self, ticker: str) -> Dict[str, Any]:
        """
        Get details for a specific market.
        
        Args:
            ticker: Market ticker (e.g., "KXAITRAINING-26FEB28")
            
        Returns:
            Market details dict
        """
        if not self.client:
            return {"error": "Client not initialized"}
        
        try:
            response = self.client.get_market(ticker=ticker)
            return response.market if hasattr(response, 'market') else response
        except Exception as e:
            return {"error": str(e)}
    
    def get_ai_markets(self) -> List[Dict[str, Any]]:
        """
        Get AI-related markets.
        
        Searches for markets related to AI, ML, LLMs, GPT, etc.
        
        Returns:
            List of AI market dicts
        """
        ai_keywords = ["AI", "GPT", "LLM", "artificial intelligence", "machine learning", 
                       "OpenAI", "Anthropic", "Google AI", "ChatGPT", "Claude"]
        
        all_markets = []
        cursor = None
        
        while True:
            result = self.get_markets(status="open", limit=200, cursor=cursor)
            if "error" in result:
                break
            
            markets = result.get("markets", [])
            if not markets:
                break
            
            # Filter for AI-related
            for market in markets:
                # Handle both dict and Pydantic model responses
                if hasattr(market, 'title'):
                    # Pydantic model
                    title = (market.title or "").lower()
                    subtitle = (market.subtitle or "").lower() if hasattr(market, 'subtitle') else ""
                    ticker = market.ticker if hasattr(market, 'ticker') else None
                    yes_bid = market.yes_bid if hasattr(market, 'yes_bid') else None
                    no_bid = market.no_bid if hasattr(market, 'no_bid') else None
                    volume = market.volume if hasattr(market, 'volume') else 0
                    close_time = market.close_time if hasattr(market, 'close_time') else None
                else:
                    # Dict
                    title = market.get("title", "").lower()
                    subtitle = market.get("subtitle", "").lower()
                    ticker = market.get("ticker")
                    yes_bid = market.get("yes_bid")
                    no_bid = market.get("no_bid")
                    volume = market.get("volume", 0)
                    close_time = market.get("close_time")
                
                if any(kw.lower() in title or kw.lower() in subtitle for kw in ai_keywords):
                    all_markets.append({
                        "ticker": ticker,
                        "title": title,
                        "subtitle": subtitle,
                        "yes_price": yes_bid,
                        "no_price": no_bid,
                        "volume": volume,
                        "close_time": close_time,
                        "platform": "kalshi"
                    })
            
            cursor = result.get("cursor")
            if not cursor:
                break
        
        return all_markets
    
    def get_balance(self) -> Dict[str, Any]:
        """Get account balance (requires auth)."""
        if not self.authenticated:
            return {"error": "Authentication required"}
        
        try:
            response = self.client.get_balance()
            return {
                "balance_cents": response.balance,
                "balance_usd": response.balance / 100
            }
        except Exception as e:
            return {"error": str(e)}
    
    def place_order(self, 
                    ticker: str,
                    side: str,  # "yes" or "no"
                    action: str,  # "buy" or "sell"
                    count: int,
                    price: int  # Price in cents (1-99)
                    ) -> Dict[str, Any]:
        """
        Place an order (requires auth).
        
        Args:
            ticker: Market ticker
            side: "yes" or "no"
            action: "buy" or "sell"
            count: Number of contracts
            price: Price per contract in cents (1-99)
            
        Returns:
            Order confirmation or error
        """
        if not self.authenticated:
            return {"error": "Authentication required"}
        
        try:
            response = self.client.create_order(
                ticker=ticker,
                side=side,
                action=action,
                count=count,
                type="limit",
                yes_price=price if side == "yes" else None,
                no_price=price if side == "no" else None
            )
            return {"order": response}
        except Exception as e:
            return {"error": str(e)}


def test_client():
    """Test Kalshi client (read-only, no auth needed)."""
    client = KalshiMarketClient()
    
    print("Testing Kalshi Client...")
    print(f"SDK Available: {KALSHI_SDK_AVAILABLE}")
    print(f"Authenticated: {client.authenticated}")
    
    # Try to get markets
    print("\nFetching markets...")
    result = client.get_markets(limit=5)
    
    if "error" in result:
        print(f"Error: {result['error']}")
    else:
        print(f"Found {len(result.get('markets', []))} markets")
        for m in result.get('markets', [])[:3]:
            print(f"  - {m.get('ticker')}: {m.get('title')}")
    
    # Try AI markets
    print("\nFetching AI markets...")
    ai_markets = client.get_ai_markets()
    print(f"Found {len(ai_markets)} AI-related markets")
    for m in ai_markets[:5]:
        print(f"  - {m['ticker']}: {m['title'][:60]}...")


if __name__ == "__main__":
    test_client()
