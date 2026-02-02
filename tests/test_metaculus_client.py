"""
Tests for Metaculus forecasting platform client.

Tests core logic without requiring actual API calls.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock


class TestMetaculusClient:
    """Test suite for MetaculusClient."""
    
    def test_client_init(self):
        """Client initializes with correct defaults."""
        from metaculus.client import MetaculusClient
        c = MetaculusClient()
        
        assert c.BASE_URL == "https://www.metaculus.com/api2"
        assert c.session is not None
        assert "Accept" in c.session.headers
        assert c.session.headers["Accept"] == "application/json"
    
    def test_get_questions_builds_correct_params(self):
        """get_questions builds query parameters correctly."""
        from metaculus.client import MetaculusClient
        c = MetaculusClient()
        
        # Mock the session
        mock_response = Mock()
        mock_response.json.return_value = {"results": []}
        mock_response.raise_for_status = Mock()
        c.session.get = Mock(return_value=mock_response)
        
        c.get_questions(
            categories="artificial-intelligence",
            status="open",
            search="GPT",
            limit=50,
            offset=10,
            order_by="-publish_time"
        )
        
        # Verify correct API call
        c.session.get.assert_called_once()
        call_args = c.session.get.call_args
        assert "questions" in call_args[0][0]
        params = call_args[1]["params"]
        assert params["categories"] == "artificial-intelligence"
        assert params["status"] == "open"
        assert params["search"] == "GPT"
        assert params["limit"] == 50
        assert params["offset"] == 10
        assert params["order_by"] == "-publish_time"
    
    def test_get_questions_handles_error(self):
        """get_questions returns error dict on failure."""
        from metaculus.client import MetaculusClient
        c = MetaculusClient()
        
        c.session.get = Mock(side_effect=Exception("Network error"))
        
        result = c.get_questions()
        
        assert "error" in result
        assert "Network error" in result["error"]
        assert result["results"] == []
    
    def test_get_question_handles_error(self):
        """get_question returns error dict on failure."""
        from metaculus.client import MetaculusClient
        c = MetaculusClient()
        
        c.session.get = Mock(side_effect=Exception("Not found"))
        
        result = c.get_question(12345)
        
        assert "error" in result
    
    def test_get_ai_questions_extracts_data_correctly(self):
        """get_ai_questions extracts and formats question data."""
        from metaculus.client import MetaculusClient
        c = MetaculusClient()
        
        # Mock API response
        mock_response = {
            "results": [
                {
                    "id": 123,
                    "title": "Will GPT-5 be released in 2026?",
                    "short_title": "GPT-5 2026",
                    "slug": "gpt-5-release-2026",
                    "status": "open",
                    "nr_forecasters": 150,
                    "question": {
                        "type": "binary",
                        "scheduled_close_time": "2026-12-31T00:00:00Z",
                        "scheduled_resolve_time": "2027-01-15T00:00:00Z",
                        "aggregations": {
                            "unweighted": {
                                "latest": {
                                    "centers": [0.75]
                                }
                            }
                        }
                    },
                    "projects": {
                        "category": [{"name": "AI"}]
                    }
                }
            ]
        }
        
        c.get_questions = Mock(return_value=mock_response)
        
        result = c.get_ai_questions(limit=10)
        
        assert len(result) == 1
        q = result[0]
        assert q["id"] == 123
        assert q["title"] == "Will GPT-5 be released in 2026?"
        assert q["community_probability"] == 0.75
        assert q["forecasters_count"] == 150
        assert q["type"] == "binary"
        assert q["platform"] == "metaculus"
        assert "metaculus.com/questions/123" in q["url"]
    
    def test_get_ai_questions_handles_missing_probability(self):
        """get_ai_questions handles questions without probability data."""
        from metaculus.client import MetaculusClient
        c = MetaculusClient()
        
        mock_response = {
            "results": [
                {
                    "id": 456,
                    "title": "Test question",
                    "slug": "test",
                    "status": "open",
                    "nr_forecasters": 0,
                    "question": {
                        "type": "binary",
                        "aggregations": {}  # No probability data
                    },
                    "projects": {}
                }
            ]
        }
        
        c.get_questions = Mock(return_value=mock_response)
        
        result = c.get_ai_questions()
        
        assert len(result) == 1
        assert result[0]["community_probability"] is None
    
    def test_search_questions(self):
        """search_questions calls get_questions with search param."""
        from metaculus.client import MetaculusClient
        c = MetaculusClient()
        
        mock_response = {
            "results": [
                {"id": 1, "title": "Test", "slug": "test", "status": "open", "nr_forecasters": 10}
            ]
        }
        c.get_questions = Mock(return_value=mock_response)
        
        result = c.search_questions("GPT-5", limit=5)
        
        c.get_questions.assert_called_once_with(search="GPT-5", limit=5)
        assert len(result) == 1
        assert result[0]["id"] == 1
        assert result[0]["platform"] == "metaculus"


class TestCompareWithMarket:
    """Test suite for market comparison logic."""
    
    def test_identifies_buy_yes_opportunity(self):
        """Identifies BUY_YES when Metaculus > market."""
        from metaculus.client import MetaculusClient
        c = MetaculusClient()
        
        result = c.compare_with_market(
            metaculus_prob=0.75,
            market_price=0.55,
            threshold=0.10
        )
        
        assert result["direction"] == "BUY_YES"
        assert result["is_opportunity"] == True
        assert result["difference"] == pytest.approx(0.20)
        assert result["edge"] == pytest.approx(20.0)
    
    def test_identifies_buy_no_opportunity(self):
        """Identifies BUY_NO when Metaculus < market."""
        from metaculus.client import MetaculusClient
        c = MetaculusClient()
        
        result = c.compare_with_market(
            metaculus_prob=0.30,
            market_price=0.55,
            threshold=0.10
        )
        
        assert result["direction"] == "BUY_NO"
        assert result["is_opportunity"] == True
        assert result["difference"] == pytest.approx(-0.25)
    
    def test_identifies_hold_when_close(self):
        """Identifies HOLD when prices are within threshold."""
        from metaculus.client import MetaculusClient
        c = MetaculusClient()
        
        result = c.compare_with_market(
            metaculus_prob=0.52,
            market_price=0.50,
            threshold=0.10
        )
        
        assert result["direction"] == "HOLD"
        assert result["is_opportunity"] == False
    
    def test_threshold_at_boundary(self):
        """Correctly handles difference above threshold."""
        from metaculus.client import MetaculusClient
        c = MetaculusClient()
        
        # Slightly above threshold should trigger
        result = c.compare_with_market(
            metaculus_prob=0.61,
            market_price=0.50,
            threshold=0.10
        )
        
        assert result["is_opportunity"] == True
        assert result["direction"] == "BUY_YES"
    
    def test_custom_threshold(self):
        """Respects custom threshold parameter."""
        from metaculus.client import MetaculusClient
        c = MetaculusClient()
        
        # With 5% threshold, 8% diff should trigger
        result = c.compare_with_market(
            metaculus_prob=0.58,
            market_price=0.50,
            threshold=0.05
        )
        
        assert result["is_opportunity"] == True
        
        # With 15% threshold, 8% diff should not trigger
        result = c.compare_with_market(
            metaculus_prob=0.58,
            market_price=0.50,
            threshold=0.15
        )
        
        assert result["is_opportunity"] == False
    
    def test_edge_calculation(self):
        """Edge is calculated as absolute percentage points."""
        from metaculus.client import MetaculusClient
        c = MetaculusClient()
        
        result = c.compare_with_market(0.75, 0.50)
        
        # 0.25 difference = 25 percentage points
        assert result["edge"] == 25.0
        
        result = c.compare_with_market(0.30, 0.50)
        
        # -0.20 difference = 20 percentage points (abs)
        assert result["edge"] == 20.0
    
    def test_all_fields_present(self):
        """compare_with_market returns all expected fields."""
        from metaculus.client import MetaculusClient
        c = MetaculusClient()
        
        result = c.compare_with_market(0.60, 0.50)
        
        expected_fields = [
            "metaculus", "market", "difference",
            "abs_difference", "is_opportunity", "direction", "edge"
        ]
        
        for field in expected_fields:
            assert field in result, f"Missing field: {field}"


class TestMetaculusIntegration:
    """Integration tests for Metaculus client."""
    
    def test_question_url_format(self):
        """Generated URLs are valid Metaculus URLs."""
        from metaculus.client import MetaculusClient
        c = MetaculusClient()
        
        mock_response = {
            "results": [
                {"id": 12345, "title": "Test", "slug": "test", "status": "open", "nr_forecasters": 0}
            ]
        }
        c.get_questions = Mock(return_value=mock_response)
        
        result = c.search_questions("test", limit=1)
        
        assert result[0]["url"] == "https://www.metaculus.com/questions/12345/"
    
    def test_handles_non_binary_questions(self):
        """Correctly handles non-binary question types."""
        from metaculus.client import MetaculusClient
        c = MetaculusClient()
        
        mock_response = {
            "results": [
                {
                    "id": 789,
                    "title": "Numeric question",
                    "slug": "numeric",
                    "status": "open",
                    "nr_forecasters": 50,
                    "question": {
                        "type": "numeric",  # Not binary
                        "aggregations": {
                            "unweighted": {
                                "latest": {
                                    "centers": [100]  # Different meaning for numeric
                                }
                            }
                        }
                    },
                    "projects": {}
                }
            ]
        }
        
        c.get_questions = Mock(return_value=mock_response)
        
        result = c.get_ai_questions()
        
        # For non-binary, community_probability should be None
        assert result[0]["type"] == "numeric"
        assert result[0]["community_probability"] is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
