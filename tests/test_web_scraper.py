"""
Unit tests for monitors/web_scraper.py
Tests: WebScraper class, scraping logic, filtering, scoring
All tests use mocking — no network/side effects.
"""
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

# Add parent directory for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from monitors.web_scraper import ScrapedArticle, WebScraper


class TestWebScraper(unittest.TestCase):
    """Tests for WebScraper class."""

    def setUp(self):
        """Set up test fixtures."""
        self.scraper = WebScraper()

    @patch("requests.Session.get")
    def test_scrape_source_success(self, mock_get):
        """Test scraping a source successfully."""
        # Mock HTML response
        mock_html = """
        <html>
            <body>
                <a class="loop-card__title-link" href="/article/1">AI News Title 1</a>
                <a class="loop-card__title-link" href="/article/2">AI News Title 2</a>
            </body>
        </html>
        """
        mock_response = MagicMock()
        mock_response.text = mock_html
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        # Test with TechCrunch source
        articles = self.scraper.scrape_source("techcrunch_openai")

        self.assertEqual(len(articles), 2)
        self.assertEqual(articles[0].title, "AI News Title 1")
        self.assertEqual(articles[0].url, "https://techcrunch.com/article/1")
        self.assertEqual(articles[0].source, "techcrunch_openai")

    def test_scrape_source_invalid(self):
        """Test scraping an invalid source."""
        articles = self.scraper.scrape_source("invalid_source")
        self.assertEqual(articles, [])

    @patch("requests.Session.get")
    def test_scrape_source_network_error(self, mock_get):
        """Test handling of network errors."""
        mock_get.side_effect = Exception("Network Error")
        
        # Should catch exception and return empty list
        articles = self.scraper.scrape_source("techcrunch_openai")
        self.assertEqual(articles, [])

    @patch("requests.Session.get")
    def test_scrape_source_filter_pattern(self, mock_get):
        """Test URL pattern filtering."""
        # Config has filter_pattern for The Verge
        mock_html = """
        <html>
            <body>
                <a href="/2024/02/01/valid-article">Valid Article</a>
                <a href="/other/invalid-article">Invalid Article</a>
            </body>
        </html>
        """
        mock_response = MagicMock()
        mock_response.text = mock_html
        mock_get.return_value = mock_response

        articles = self.scraper.scrape_source("theverge_ai")
        
        # Should only get the valid article
        self.assertEqual(len(articles), 1)
        self.assertIn("valid-article", articles[0].url)

    def test_filter_tradeable(self):
        """Test filtering for tradeable keywords."""
        articles = [
            ScrapedArticle("OpenAI announces GPT-5", "url1", "src"),
            ScrapedArticle("Local sports team wins", "url2", "src"),
            ScrapedArticle("New cookie recipe", "url3", "src"),
            ScrapedArticle("Anthropic releases Claude 4", "url4", "src"),
        ]
        
        filtered = self.scraper.filter_tradeable(articles)
        
        self.assertEqual(len(filtered), 2)
        self.assertIn("GPT-5", filtered[0].title)
        self.assertIn("Claude 4", filtered[1].title)

    def test_score_article(self):
        """Test article scoring logic."""
        # High score: Entity + High Impact
        article1 = ScrapedArticle("OpenAI launches IPO", "url", "src")
        score1 = self.scraper.score_article(article1)
        # OpenAI (15) + IPO (20) + launches (20) = 55
        self.assertGreater(score1, 30)

        # Medium score: Just entity
        article2 = ScrapedArticle("Microsoft updates Windows", "url", "src")
        score2 = self.scraper.score_article(article2)
        # Microsoft (15) = 15
        self.assertEqual(score2, 15)

        # Zero score
        article3 = ScrapedArticle("Nothing relevant here", "url", "src")
        score3 = self.scraper.score_article(article3)
        self.assertEqual(score3, 0)

    @patch("requests.Session.get")
    def test_get_article_content(self, mock_get):
        """Test fetching article content."""
        mock_html = """
        <html>
            <body>
                <article>
                    <h1>Title</h1>
                    <p>This is the article content.</p>
                    <script>var x = 1;</script>
                </article>
            </body>
        </html>
        """
        mock_response = MagicMock()
        mock_response.text = mock_html
        mock_get.return_value = mock_response

        content = self.scraper.get_article_content("http://test.com")
        
        self.assertIn("This is the article content", content)
        self.assertNotIn("var x", content)  # Script should be removed

if __name__ == "__main__":
    unittest.main()
