"""
Metaculus Forecasting Platform Client

API: https://www.metaculus.com/api2/
No authentication required for read-only access.

Metaculus is a forecasting aggregation platform (not a trading market).
Use it to:
1. Get community probability estimates for events
2. Compare Metaculus forecasts vs Polymarket/Kalshi prices for arbitrage
3. Find new events to track on prediction markets
"""

import requests
from typing import Optional, List, Dict, Any
from datetime import datetime
from urllib.parse import urlencode


class MetaculusClient:
    """Client for Metaculus forecasting API."""
    
    BASE_URL = "https://www.metaculus.com/api2"
    
    def __init__(self):
        """Initialize Metaculus client (no auth needed)."""
        self.session = requests.Session()
        self.session.headers.update({
            "Accept": "application/json",
            "User-Agent": "EdgeSignals/1.0"
        })
    
    def get_questions(self,
                      categories: Optional[str] = None,
                      status: str = "open",
                      search: Optional[str] = None,
                      limit: int = 20,
                      offset: int = 0,
                      order_by: str = "-activity") -> Dict[str, Any]:
        """
        Get questions from Metaculus.
        
        Args:
            categories: Category slug (e.g., "artificial-intelligence", "science-technology")
            status: Question status (open, closed, resolved)
            search: Search query string
            limit: Results per page (max 100)
            offset: Pagination offset
            order_by: Sort order (-activity, -publish_time, -close_time)
            
        Returns:
            Dict with questions list and pagination info
        """
        params = {
            "status": status,
            "limit": limit,
            "offset": offset,
            "order_by": order_by
        }
        
        if categories:
            params["categories"] = categories
        if search:
            params["search"] = search
        
        try:
            response = self.session.get(f"{self.BASE_URL}/questions/", params=params)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            return {"error": str(e), "results": []}
    
    def get_question(self, question_id: int) -> Dict[str, Any]:
        """
        Get details for a specific question.
        
        Args:
            question_id: Metaculus question ID
            
        Returns:
            Question details dict
        """
        try:
            response = self.session.get(f"{self.BASE_URL}/questions/{question_id}/")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            return {"error": str(e)}
    
    def get_ai_questions(self, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Get AI-related questions with community predictions.
        
        Returns:
            List of AI questions with probability data
        """
        result = self.get_questions(
            categories="artificial-intelligence",
            status="open",
            limit=limit,
            order_by="-activity"
        )
        
        questions = []
        for q in result.get("results", []):
            # Extract community prediction if available
            question_data = q.get("question", {})
            aggregations = question_data.get("aggregations", {})
            unweighted = aggregations.get("unweighted", {})
            latest = unweighted.get("latest", {})
            
            # Get median probability for binary questions
            community_prob = None
            if question_data.get("type") == "binary":
                if latest and "centers" in latest:
                    community_prob = latest["centers"][0] if latest["centers"] else None
            
            questions.append({
                "id": q.get("id"),
                "title": q.get("title"),
                "short_title": q.get("short_title"),
                "slug": q.get("slug"),
                "url": f"https://www.metaculus.com/questions/{q.get('id')}/",
                "status": q.get("status"),
                "type": question_data.get("type"),  # binary, numeric, multiple_choice
                "community_probability": community_prob,
                "forecasters_count": q.get("nr_forecasters", 0),
                "close_time": question_data.get("scheduled_close_time"),
                "resolve_time": question_data.get("scheduled_resolve_time"),
                "categories": [c.get("name") for c in q.get("projects", {}).get("category", [])],
                "platform": "metaculus"
            })
        
        return questions
    
    def search_questions(self, query: str, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Search for questions matching a query.
        
        Args:
            query: Search string
            limit: Max results
            
        Returns:
            List of matching questions
        """
        result = self.get_questions(search=query, limit=limit)
        
        questions = []
        for q in result.get("results", []):
            questions.append({
                "id": q.get("id"),
                "title": q.get("title"),
                "url": f"https://www.metaculus.com/questions/{q.get('id')}/",
                "status": q.get("status"),
                "forecasters_count": q.get("nr_forecasters", 0),
                "platform": "metaculus"
            })
        
        return questions
    
    def compare_with_market(self, 
                            metaculus_prob: float,
                            market_price: float,
                            threshold: float = 0.10) -> Dict[str, Any]:
        """
        Compare Metaculus community prediction with market price.
        
        Useful for finding arbitrage opportunities where crowd wisdom
        differs significantly from market pricing.
        
        Args:
            metaculus_prob: Metaculus community probability (0-1)
            market_price: Market price (0-1)
            threshold: Minimum difference to flag as opportunity
            
        Returns:
            Analysis dict
        """
        diff = metaculus_prob - market_price
        
        return {
            "metaculus": metaculus_prob,
            "market": market_price,
            "difference": diff,
            "abs_difference": abs(diff),
            "is_opportunity": abs(diff) >= threshold,
            "direction": "BUY_YES" if diff > threshold else "BUY_NO" if diff < -threshold else "HOLD",
            "edge": abs(diff) * 100  # Potential edge in percentage points
        }


def test_client():
    """Test Metaculus client."""
    client = MetaculusClient()
    
    print("Testing Metaculus Client...")
    print("=" * 50)
    
    # Get AI questions
    print("\nFetching AI questions...")
    ai_questions = client.get_ai_questions(limit=10)
    
    print(f"Found {len(ai_questions)} AI questions")
    print("\nTop 5 AI Questions:")
    for q in ai_questions[:5]:
        prob = q['community_probability']
        prob_str = f"{prob*100:.1f}%" if prob else "N/A"
        print(f"\n  [{prob_str}] {q['title'][:70]}...")
        print(f"    - {q['forecasters_count']} forecasters")
        print(f"    - {q['url']}")
    
    # Search example
    print("\n" + "=" * 50)
    print("\nSearching for 'GPT' questions...")
    gpt_questions = client.search_questions("GPT", limit=5)
    for q in gpt_questions[:3]:
        print(f"  - {q['title'][:60]}...")
    
    # Comparison example
    print("\n" + "=" * 50)
    print("\nExample: Compare Metaculus (65%) vs Market (55%)")
    comparison = client.compare_with_market(0.65, 0.55)
    print(f"  Difference: {comparison['difference']*100:.1f}pp")
    print(f"  Direction: {comparison['direction']}")
    print(f"  Edge: {comparison['edge']:.1f}pp")


if __name__ == "__main__":
    test_client()
