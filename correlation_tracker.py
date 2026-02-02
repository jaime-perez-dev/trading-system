#!/usr/bin/env python3
"""
Enhanced Correlation Tracker - Analyzes correlation between news events and market movements.

This module:
1. Tracks the timing between news events and price movements
2. Identifies which types of news have the strongest correlation with market movements
3. Adds a confidence score to opportunities based on historical correlation
4. Implements a feedback mechanism to track whether recommended trades were successful
5. Adds visualization capabilities to show the correlation between news and market movements
"""

import json
import os
import re
import sqlite3
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Tuple
from pathlib import Path
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
from collections import defaultdict
from scipy.stats import pearsonr
import warnings

warnings.filterwarnings('ignore')

DATA_DIR = Path(__file__).parent / "data"
CORRELATION_DB = DATA_DIR / "correlation_analysis.db"
CORRELATIONS_FILE = DATA_DIR / "correlations.json"
POSITIONS_FILE = DATA_DIR / "paper_trades.json"

# News categories and their keywords
NEWS_CATEGORIES = {
    "ai_company_announcements": {
        "keywords": ["openai", "anthropic", "google ai", "deepmind", "meta ai", "microsoft ai", 
                     "claude", "gpt", "gemini", "llama", "chatgpt", "copilot", "product launch",
                     "partnership", "acquisition", "funding", "valuation"],
        "description": "AI company announcements and business developments",
    },
    "ai_regulation_policy": {
        "keywords": ["ai regulation", "ai safety", "ai act", "executive order", "ai ban",
                     "ftc ai", "eu ai", "congress ai", "policy", "legislation", "compliance"],
        "description": "AI regulation and policy developments",
    },
    "election_politics": {
        "keywords": ["trump", "biden", "harris", "election", "2024 election", "2026 election",
                     "republican", "democrat", "gop", "electoral", "president", "senate", "house"],
        "description": "Election and political developments",
    },
    "crypto_news": {
        "keywords": ["bitcoin", "ethereum", "crypto", "btc", "eth", "sec crypto", "binance",
                     "cryptocurrency", "blockchain", "defi", "altcoin"],
        "description": "Cryptocurrency market news",
    },
    "tech_earnings": {
        "keywords": ["earnings", "revenue", "quarterly", "q1", "q2", "q3", "q4", "guidance",
                     "nvidia", "apple", "meta", "alphabet", "amazon", "microsoft", "results"],
        "description": "Tech company earnings reports",
    },
    "geopolitics": {
        "keywords": ["china", "russia", "ukraine", "taiwan", "war", "sanctions", "tariff",
                     "conflict", "diplomacy", "trade war"],
        "description": "Geopolitical events and conflicts",
    },
    "market_movers": {
        "keywords": ["stock market", "nasdaq", "s&p 500", "dow jones", "indices", "trading",
                     "market crash", "bull market", "bear market", "volatility"],
        "description": "General market movement news",
    }
}


@dataclass
class NewsEvent:
    """Represents a news event."""
    id: str
    title: str
    source: str
    publish_time: datetime
    category: str
    entities: List[str]
    keywords: List[str]
    sentiment_score: float = 0.0  # -1 to 1 scale


@dataclass
class PriceMovement:
    """Represents a price movement."""
    market_id: str
    market_name: str
    timestamp: datetime
    price_before: float
    price_after: float
    price_change: float
    volume: float = 0.0


@dataclass
class CorrelationRecord:
    """Represents a correlation between news and price movement."""
    news_id: str
    market_id: str
    news_time: datetime
    price_time: datetime
    time_diff_hours: float
    news_category: str
    price_change: float
    news_sentiment: float
    correlation_strength: float = 0.0


@dataclass
class OpportunityAnalysis:
    """Analysis result for a potential trading opportunity."""
    news_event: NewsEvent
    markets: List[Dict]
    correlation_confidence: float  # 0.0 to 1.0
    historical_correlation_score: float
    predicted_movement_direction: str  # 'up', 'down', 'neutral'
    success_probability: float
    recommendation: str  # 'strong_buy', 'buy', 'hold', 'sell', 'strong_sell'


@dataclass
class CorrelationFeedback:
    """Feedback on whether a trade was successful."""
    opportunity_id: str
    actual_outcome: str  # 'profit', 'loss', 'breakeven'
    realized_return: float  # percentage return
    time_to_outcome: int  # hours
    confidence_was_accurate: bool  # did correlation predict correctly?


class CorrelationTracker:
    """Enhanced correlation tracker with news-price movement analysis."""
    
    def __init__(self, db_path: Path = CORRELATION_DB):
        self.db_path = db_path
        self.data_dir = DATA_DIR
        self.data_dir.mkdir(exist_ok=True)
        self._init_db()
    
    def _init_db(self):
        """Initialize SQLite database for storing correlation data."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Table for news events
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS news_events (
                id TEXT PRIMARY KEY,
                title TEXT,
                source TEXT,
                publish_time TIMESTAMP,
                category TEXT,
                entities TEXT,
                keywords TEXT,
                sentiment_score REAL
            )
        ''')
        
        # Table for price movements
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS price_movements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                market_id TEXT,
                market_name TEXT,
                timestamp TIMESTAMP,
                price_before REAL,
                price_after REAL,
                price_change REAL,
                volume REAL
            )
        ''')
        
        # Table for correlation records
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS correlations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                news_id TEXT,
                market_id TEXT,
                news_time TIMESTAMP,
                price_time TIMESTAMP,
                time_diff_hours REAL,
                news_category TEXT,
                price_change REAL,
                news_sentiment REAL,
                correlation_strength REAL,
                FOREIGN KEY (news_id) REFERENCES news_events (id)
            )
        ''')
        
        # Table for opportunity analyses
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS opportunity_analyses (
                id TEXT PRIMARY KEY,
                news_id TEXT,
                market_id TEXT,
                timestamp TIMESTAMP,
                correlation_confidence REAL,
                historical_correlation_score REAL,
                predicted_direction TEXT,
                success_probability REAL,
                recommendation TEXT,
                FOREIGN KEY (news_id) REFERENCES news_events (id)
            )
        ''')
        
        # Table for feedback records
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS feedback_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                opportunity_id TEXT,
                actual_outcome TEXT,
                realized_return REAL,
                time_to_outcome INTEGER,
                confidence_was_accurate BOOLEAN
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def categorize_news(self, title: str, source: str = "", entities: List[str] = None) -> str:
        """Categorize news based on title, source, and entities."""
        if entities is None:
            entities = []
        
        text = f"{title} {source} {' '.join(entities)}".lower()
        
        # Score each category by keyword matches
        best_category = "unknown"
        best_score = 0
        
        for category, config in NEWS_CATEGORIES.items():
            score = sum(1 for kw in config["keywords"] if kw in text)
            if score > best_score:
                best_score = score
                best_category = category
        
        return best_category if best_score > 0 else "general"
    
    def record_news_event(self, news_id: str, title: str, source: str, 
                         publish_time: datetime, entities: List[str], 
                         keywords: List[str], sentiment_score: float = 0.0) -> bool:
        """Record a news event and its details."""
        category = self.categorize_news(title, source, entities)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT OR REPLACE INTO news_events 
                (id, title, source, publish_time, category, entities, keywords, sentiment_score)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                news_id, title, source, publish_time.isoformat(), category,
                json.dumps(entities), json.dumps(keywords), sentiment_score
            ))
            conn.commit()
            return True
        except Exception as e:
            print(f"Error recording news event: {e}")
            return False
        finally:
            conn.close()
    
    def record_price_movement(self, market_id: str, market_name: str, 
                             timestamp: datetime, price_before: float, 
                             price_after: float, volume: float = 0.0) -> bool:
        """Record a price movement for a market."""
        price_change = price_after - price_before
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT INTO price_movements 
                (market_id, market_name, timestamp, price_before, price_after, price_change, volume)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (market_id, market_name, timestamp.isoformat(), price_before, price_after, price_change, volume))
            conn.commit()
            return True
        except Exception as e:
            print(f"Error recording price movement: {e}")
            return False
        finally:
            conn.close()
    
    def analyze_correlation(self, news_id: str, market_id: str, 
                           time_window_hours: int = 24) -> Optional[CorrelationRecord]:
        """Analyze correlation between a specific news event and market movement."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get news event details
        cursor.execute('''
            SELECT publish_time, category, sentiment_score FROM news_events WHERE id = ?
        ''', (news_id,))
        news_result = cursor.fetchone()
        
        if not news_result:
            conn.close()
            return None
        
        news_time_str, news_category, news_sentiment = news_result
        news_time = datetime.fromisoformat(news_time_str)
        
        # Get price movements within time window
        start_time = news_time
        end_time = news_time + timedelta(hours=time_window_hours)
        
        cursor.execute('''
            SELECT timestamp, price_change FROM price_movements 
            WHERE market_id = ? AND timestamp BETWEEN ? AND ?
            ORDER BY timestamp ASC
        ''', (market_id, start_time.isoformat(), end_time.isoformat()))
        
        movements = cursor.fetchall()
        conn.close()
        
        if not movements:
            return None
        
        # Find the most significant movement within the window
        best_movement = max(movements, key=lambda x: abs(x[1]))
        movement_time = datetime.fromisoformat(best_movement[0])
        price_change = best_movement[1]
        
        # Calculate time difference in hours
        time_diff_hours = (movement_time - news_time).total_seconds() / 3600
        
        # Calculate correlation strength (simple approach for now)
        correlation_strength = abs(price_change) * (1.0 if (price_change > 0) == (news_sentiment > 0) else -1.0)
        
        return CorrelationRecord(
            news_id=news_id,
            market_id=market_id,
            news_time=news_time,
            price_time=movement_time,
            time_diff_hours=time_diff_hours,
            news_category=news_category,
            price_change=price_change,
            news_sentiment=news_sentiment,
            correlation_strength=correlation_strength
        )
    
    def store_correlation_record(self, record: CorrelationRecord) -> bool:
        """Store a correlation record in the database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT INTO correlations 
                (news_id, market_id, news_time, price_time, time_diff_hours, 
                 news_category, price_change, news_sentiment, correlation_strength)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                record.news_id, record.market_id, record.news_time.isoformat(), record.price_time.isoformat(),
                record.time_diff_hours, record.news_category, record.price_change,
                record.news_sentiment, record.correlation_strength
            ))
            conn.commit()
            return True
        except Exception as e:
            print(f"Error storing correlation record: {e}")
            return False
        finally:
            conn.close()
    
    def calculate_historical_correlation(self, news_category: str, market_id: str = None) -> Dict:
        """Calculate historical correlation statistics for a news category."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        query = '''
            SELECT news_sentiment, price_change, time_diff_hours, correlation_strength
            FROM correlations 
            WHERE news_category = ?
        '''
        params = [news_category]
        
        if market_id:
            query += " AND market_id = ?"
            params.append(market_id)
        
        cursor.execute(query, params)
        results = cursor.fetchall()
        conn.close()
        
        if not results:
            return {
                "count": 0,
                "avg_correlation_strength": 0.0,
                "avg_time_diff_hours": 0.0,
                "positive_correlations": 0,
                "negative_correlations": 0,
                "accuracy_rate": 0.0,
                "correlation_coefficient": 0.0
            }
        
        sentiments = [row[0] for row in results]
        price_changes = [row[1] for row in results]
        time_diffs = [row[2] for row in results]
        correlations = [row[3] for row in results]
        
        # Calculate correlation between sentiment and price change
        if len(sentiments) > 1:
            try:
                corr_coef, _ = pearsonr(sentiments, price_changes)
            except:
                corr_coef = 0.0
        else:
            corr_coef = 0.0
        
        positive_corr = sum(1 for c in correlations if c > 0)
        negative_corr = sum(1 for c in correlations if c < 0)
        
        return {
            "count": len(results),
            "avg_correlation_strength": float(np.mean(correlations)) if correlations else 0.0,
            "avg_time_diff_hours": float(np.mean(time_diffs)) if time_diffs else 0.0,
            "positive_correlations": positive_corr,
            "negative_correlations": negative_corr,
            "accuracy_rate": positive_corr / len(results) if len(results) > 0 else 0.0,
            "correlation_coefficient": float(corr_coef)
        }
    
    def analyze_opportunity(self, news_event: NewsEvent, markets: List[Dict]) -> List[OpportunityAnalysis]:
        """Analyze potential trading opportunities based on news and historical correlations."""
        analyses = []
        
        for market in markets:
            market_id = market.get('id', '')
            market_name = market.get('question', '')
            
            # Calculate historical correlation for this news category and market
            hist_corr = self.calculate_historical_correlation(news_event.category, market_id)
            
            # Determine predicted direction based on historical patterns
            if hist_corr["correlation_coefficient"] > 0.1:
                predicted_direction = "up" if news_event.sentiment_score > 0 else "down"
            elif hist_corr["correlation_coefficient"] < -0.1:
                predicted_direction = "down" if news_event.sentiment_score > 0 else "up"
            else:
                predicted_direction = "neutral"
            
            # Calculate confidence based on historical accuracy and sample size
            confidence = min(1.0, hist_corr["accuracy_rate"] * (hist_corr["count"] / max(1, hist_corr["count"])))
            
            # Calculate success probability
            success_prob = hist_corr["accuracy_rate"] if hist_corr["count"] > 0 else 0.5
            
            # Determine recommendation based on confidence and direction
            if confidence > 0.7 and success_prob > 0.6:
                if predicted_direction == "up":
                    recommendation = "strong_buy"
                elif predicted_direction == "down":
                    recommendation = "strong_sell"
                else:
                    recommendation = "hold"
            elif confidence > 0.5 and success_prob > 0.55:
                if predicted_direction == "up":
                    recommendation = "buy"
                elif predicted_direction == "down":
                    recommendation = "sell"
                else:
                    recommendation = "hold"
            else:
                recommendation = "hold"
            
            analysis = OpportunityAnalysis(
                news_event=news_event,
                markets=[market],
                correlation_confidence=confidence,
                historical_correlation_score=hist_corr["correlation_coefficient"],
                predicted_movement_direction=predicted_direction,
                success_probability=success_prob,
                recommendation=recommendation
            )
            
            analyses.append(analysis)
            
            # Store the analysis in database
            self._store_opportunity_analysis(analysis)
        
        return analyses
    
    def _store_opportunity_analysis(self, analysis: OpportunityAnalysis):
        """Store opportunity analysis in database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        opportunity_id = f"{analysis.news_event.id}_{analysis.markets[0]['id']}_{datetime.now().timestamp()}"
        
        try:
            cursor.execute('''
                INSERT INTO opportunity_analyses 
                (id, news_id, market_id, timestamp, correlation_confidence, 
                 historical_correlation_score, predicted_direction, success_probability, recommendation)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                opportunity_id,
                analysis.news_event.id,
                analysis.markets[0]['id'],
                datetime.now(),
                analysis.correlation_confidence,
                analysis.historical_correlation_score,
                analysis.predicted_movement_direction,
                analysis.success_probability,
                analysis.recommendation
            ))
            conn.commit()
        except Exception as e:
            print(f"Error storing opportunity analysis: {e}")
        finally:
            conn.close()
    
    def record_feedback(self, opportunity_id: str, actual_outcome: str, 
                       realized_return: float, time_to_outcome: int,
                       confidence_was_accurate: bool):
        """Record feedback on whether a trade was successful."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT INTO feedback_records 
                (opportunity_id, actual_outcome, realized_return, time_to_outcome, confidence_was_accurate)
                VALUES (?, ?, ?, ?, ?)
            ''', (opportunity_id, actual_outcome, realized_return, time_to_outcome, confidence_was_accurate))
            conn.commit()
        except Exception as e:
            print(f"Error recording feedback: {e}")
        finally:
            conn.close()
    
    def get_correlation_feedback_stats(self) -> Dict:
        """Get statistics on correlation prediction accuracy."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT 
                COUNT(*) as total_predictions,
                AVG(CASE WHEN confidence_was_accurate THEN 1 ELSE 0 END) as accuracy_rate,
                AVG(realized_return) as avg_return,
                COUNT(CASE WHEN actual_outcome = 'profit' THEN 1 END) as profitable_trades,
                COUNT(CASE WHEN actual_outcome = 'loss' THEN 1 END) as losing_trades
            FROM feedback_records
        ''')
        
        result = cursor.fetchone()
        conn.close()
        
        if result:
            return {
                "total_predictions": result[0] or 0,
                "accuracy_rate": result[1] or 0.0,
                "avg_return": result[2] or 0.0,
                "profitable_trades": result[3] or 0,
                "losing_trades": result[4] or 0
            }
        else:
            return {
                "total_predictions": 0,
                "accuracy_rate": 0.0,
                "avg_return": 0.0,
                "profitable_trades": 0,
                "losing_trades": 0
            }
    
    def generate_correlation_report(self) -> Dict:
        """Generate a comprehensive correlation analysis report."""
        report = {
            "timestamp": datetime.now().isoformat(),
            "category_correlations": {},
            "feedback_stats": self.get_correlation_feedback_stats(),
            "top_correlated_categories": [],
            "visualization_data": {}
        }
        
        # Get correlation stats for each category
        for category in NEWS_CATEGORIES.keys():
            stats = self.calculate_historical_correlation(category)
            if stats["count"] > 0:
                report["category_correlations"][category] = stats
        
        # Sort categories by correlation strength
        sorted_categories = sorted(
            report["category_correlations"].items(),
            key=lambda x: abs(x[1]["correlation_coefficient"]),
            reverse=True
        )
        report["top_correlated_categories"] = [cat for cat, stats in sorted_categories]
        
        return report
    
    def create_visualization(self, output_path: Path = None) -> str:
        """Create visualization of correlation data."""
        if output_path is None:
            output_path = self.data_dir / f"correlation_visualization_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        
        conn = sqlite3.connect(self.db_path)
        
        # Get correlation data
        df = pd.read_sql_query('''
            SELECT news_category, correlation_strength, time_diff_hours, price_change, news_sentiment
            FROM correlations
            ORDER BY news_time DESC
            LIMIT 1000
        ''', conn)
        
        conn.close()
        
        if df.empty:
            # Create a simple placeholder image if no data
            fig, ax = plt.subplots(figsize=(12, 8))
            ax.text(0.5, 0.5, 'No correlation data available', 
                   horizontalalignment='center', verticalalignment='center',
                   transform=ax.transAxes, fontsize=16)
            ax.set_title('Correlation Analysis Visualization')
            plt.tight_layout()
            plt.savefig(output_path, dpi=150, bbox_inches='tight')
            plt.close()
            return str(output_path)
        
        # Create subplots
        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(15, 12))
        
        # Plot 1: Correlation by category
        category_counts = df.groupby('news_category').size().sort_values(ascending=False)
        ax1.bar(range(len(category_counts)), category_counts.values)
        ax1.set_xticks(range(len(category_counts)))
        ax1.set_xticklabels(category_counts.index, rotation=45, ha='right')
        ax1.set_title('Number of Correlations by Category')
        ax1.set_ylabel('Count')
        
        # Plot 2: Correlation strength vs time difference
        scatter = ax2.scatter(df['time_diff_hours'], df['correlation_strength'], 
                             c=df['news_sentiment'], cmap='RdBu', alpha=0.6)
        ax2.set_xlabel('Time Difference (hours)')
        ax2.set_ylabel('Correlation Strength')
        ax2.set_title('Correlation Strength vs Time Difference (colored by sentiment)')
        plt.colorbar(scatter, ax=ax2)
        
        # Plot 3: Price change distribution by category (top 5 categories)
        top_categories = df['news_category'].value_counts().head(5).index
        filtered_df = df[df['news_category'].isin(top_categories)]
        
        for i, category in enumerate(top_categories):
            category_data = filtered_df[filtered_df['news_category'] == category]['price_change']
            ax3.hist(category_data, alpha=0.6, label=category, bins=20)
        ax3.set_xlabel('Price Change')
        ax3.set_ylabel('Frequency')
        ax3.set_title('Price Change Distribution by Category (Top 5)')
        ax3.legend()
        
        # Plot 4: Average correlation by category
        avg_correlations = df.groupby('news_category')['correlation_strength'].mean().sort_values(ascending=False)
        top_avg = avg_correlations.head(8)
        ax4.barh(range(len(top_avg)), top_avg.values)
        ax4.set_yticks(range(len(top_avg)))
        ax4.set_yticklabels(top_avg.index)
        ax4.set_xlabel('Average Correlation Strength')
        ax4.set_title('Average Correlation Strength by Category (Top 8)')
        
        plt.tight_layout()
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        plt.close()
        
        return str(output_path)
    
    def get_top_correlations(self, limit: int = 10) -> List[Dict]:
        """Get the top correlation records."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT n.title, n.category, p.market_name, c.correlation_strength, 
                   c.time_diff_hours, c.price_change, c.news_sentiment
            FROM correlations c
            JOIN news_events n ON c.news_id = n.id
            JOIN price_movements p ON c.market_id = p.market_id
            ORDER BY ABS(c.correlation_strength) DESC
            LIMIT ?
        ''', (limit,))
        
        results = cursor.fetchall()
        conn.close()
        
        correlations = []
        for row in results:
            correlations.append({
                "news_title": row[0],
                "news_category": row[1],
                "market_name": row[2],
                "correlation_strength": row[3],
                "time_diff_hours": row[4],
                "price_change": row[5],
                "news_sentiment": row[6]
            })
        
        return correlations


def main():
    """CLI interface for enhanced correlation tracker."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Enhanced correlation tracker for news-market analysis")
    subparsers = parser.add_subparsers(dest="command", help="Commands")
    
    # Analyze command
    analyze_parser = subparsers.add_parser("analyze", help="Analyze correlations")
    analyze_parser.add_argument("--category", help="News category to analyze")
    analyze_parser.add_argument("--market", help="Specific market ID to analyze")
    analyze_parser.add_argument("--json", action="store_true", help="JSON output")
    
    # Report command
    report_parser = subparsers.add_parser("report", help="Generate correlation report")
    report_parser.add_argument("--json", action="store_true", help="JSON output")
    
    # Visualize command
    visualize_parser = subparsers.add_parser("visualize", help="Create correlation visualization")
    visualize_parser.add_argument("--output", help="Output path for visualization")
    
    # Top correlations command
    top_parser = subparsers.add_parser("top", help="Show top correlations")
    top_parser.add_argument("--limit", type=int, default=10, help="Number of correlations to show")
    top_parser.add_argument("--json", action="store_true", help="JSON output")
    
    # Feedback command
    feedback_parser = subparsers.add_parser("feedback", help="Record feedback on prediction")
    feedback_parser.add_argument("opportunity_id", help="Opportunity ID")
    feedback_parser.add_argument("outcome", choices=['profit', 'loss', 'breakeven'], help="Actual outcome")
    feedback_parser.add_argument("--return", type=float, dest="return_val", default=0.0, help="Realized return")
    feedback_parser.add_argument("--time", type=int, default=0, help="Time to outcome in hours")
    feedback_parser.add_argument("--accurate", action="store_true", help="Was prediction accurate?")
    
    args = parser.parse_args()
    tracker = CorrelationTracker()
    
    if args.command == "analyze":
        if args.category:
            stats = tracker.calculate_historical_correlation(args.category, args.market)
            if args.json:
                print(json.dumps(stats, indent=2))
            else:
                print(f"\n📊 Correlation Analysis for '{args.category}'")
                if args.market:
                    print(f"   Market: {args.market}")
                print(f"   Count: {stats['count']}")
                print(f"   Avg Correlation: {stats['avg_correlation_strength']:.3f}")
                print(f"   Avg Time Diff: {stats['avg_time_diff_hours']:.2f} hours")
                print(f"   Accuracy Rate: {stats['accuracy_rate']:.2%}")
                print(f"   Correlation Coef: {stats['correlation_coefficient']:.3f}")
        else:
            print("Please specify a category to analyze (--category)")
    
    elif args.command == "report":
        report = tracker.generate_correlation_report()
        if args.json:
            print(json.dumps(report, indent=2))
        else:
            print(f"\n📋 Correlation Analysis Report")
            print(f"Generated: {report['timestamp']}")
            print(f"\n📈 Feedback Stats:")
            stats = report['feedback_stats']
            print(f"  Total Predictions: {stats['total_predictions']}")
            print(f"  Accuracy Rate: {stats['accuracy_rate']:.2%}")
            print(f"  Avg Return: {stats['avg_return']:.2%}")
            print(f"  Profitable Trades: {stats['profitable_trades']}")
            print(f"  Losing Trades: {stats['losing_trades']}")
            
            print(f"\n🏆 Top Correlated Categories:")
            for i, cat in enumerate(report['top_correlated_categories'][:5], 1):
                cat_stats = report['category_correlations'][cat]
                print(f"  {i}. {cat}: {cat_stats['correlation_coefficient']:.3f} (n={cat_stats['count']})")
    
    elif args.command == "visualize":
        output_path = args.output or tracker.data_dir / f"correlation_viz_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        path = tracker.create_visualization(Path(output_path))
        print(f"📊 Visualization saved to: {path}")
    
    elif args.command == "top":
        correlations = tracker.get_top_correlations(args.limit)
        if args.json:
            print(json.dumps(correlations, indent=2))
        else:
            print(f"\n🔥 Top {args.limit} Correlations:")
            for i, corr in enumerate(correlations, 1):
                print(f"\n{i}. {corr['news_category'].upper()}")
                print(f"   News: {corr['news_title'][:60]}...")
                print(f"   Market: {corr['market_name'][:50]}...")
                print(f"   Correlation: {corr['correlation_strength']:.3f}")
                print(f"   Time Diff: {corr['time_diff_hours']:.1f}h")
                print(f"   Price Change: {corr['price_change']:+.3f}")
    
    elif args.command == "feedback":
        tracker.record_feedback(
            args.opportunity_id, 
            args.outcome, 
            args.return_val, 
            args.time, 
            args.accurate
        )
        print(f"✅ Feedback recorded for opportunity {args.opportunity_id}")
    
    else:
        parser.print_help()


if __name__ == "__main__":
    main()