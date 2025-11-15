"""
Market Breadth Analysis Service

This module provides market breadth analysis based on trend ratings to understand
overall market sentiment and stock distribution across rating categories.

Enhanced with sectoral analysis using index constituents.
"""

import pandas as pd
from typing import Dict, List, Optional, Tuple
from datetime import date, datetime, timedelta
import sys
import os
from sqlalchemy import text

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.connection import ensure_engine
from db.trends_repo import (
    get_market_breadth_by_ratings,
    get_market_breadth_summary,
    get_historical_market_breadth,
    get_stocks_by_rating_range,
    get_available_analysis_dates
)

# Fallback to direct connection if ensure_engine fails
def get_engine():
    """Get database engine with fallback to direct connection."""
    # Try direct connection using reporting module first (this works)
    try:
        import reporting_adv_decl as rad
        return rad.engine()
    except Exception:
        # Try the connection module
        try:
            from db.connection import ensure_engine
            return ensure_engine()
        except Exception:
            # Last resort - create engine directly
            import os
            from sqlalchemy import create_engine
            from sqlalchemy.engine import URL
            from dotenv import load_dotenv
            
            load_dotenv()
            
            url = URL.create(
                drivername="mysql+pymysql",
                username=os.getenv("MYSQL_USER", "root"),
                password=os.getenv("MYSQL_PASSWORD", ""),
                host=os.getenv("MYSQL_HOST", "127.0.0.1"),
                port=int(os.getenv("MYSQL_PORT", "3306")),
                database=os.getenv("MYSQL_DB", "marketdata"),
                query={"charset": "utf8mb4"},
            )
            return create_engine(url, pool_pre_ping=True, pool_recycle=3600)


def get_current_market_breadth() -> Dict:
    """Get current market breadth analysis with detailed metrics."""
    try:
        engine = get_engine()
        
        # Get rating distribution
        breadth_df = get_market_breadth_by_ratings(engine)
        summary = get_market_breadth_summary(engine)
        
        return {
            'success': True,
            'rating_distribution': breadth_df.to_dict('records') if not breadth_df.empty else [],
            'summary': summary,
            'analysis_date': summary.get('analysis_date', datetime.now().date()),
            'total_analyzed': summary.get('total_stocks', 0)
        }
    except Exception as e:
        print(f"Error getting market breadth: {e}")
        return {
            'success': False,
            'error': str(e),
            'rating_distribution': [],
            'summary': {},
            'analysis_date': None,
            'total_analyzed': 0
        }


def get_market_breadth_for_date(trade_date) -> Dict:
    """Get market breadth analysis for a specific date (accepts date object or string)."""
    try:
        engine = get_engine()
        
        # Convert date object to string if needed
        if isinstance(trade_date, date):
            trade_date_str = trade_date.strftime('%Y-%m-%d')
        else:
            trade_date_str = trade_date
            
        breadth_df = get_market_breadth_by_ratings(engine, trade_date_str)
        summary = get_market_breadth_summary(engine, trade_date_str)
        
        return {
            'success': True,
            'rating_distribution': breadth_df.to_dict('records') if not breadth_df.empty else [],
            'summary': summary,
            'analysis_date': trade_date_str,
            'total_analyzed': summary.get('total_stocks', 0)
        }
    except Exception as e:
        print(f"Error getting market breadth for {trade_date}: {e}")
        return {
            'success': False,
            'error': str(e),
            'rating_distribution': [],
            'summary': {},
            'analysis_date': trade_date,
            'total_analyzed': 0
        }


def get_market_breadth_for_date_string(trade_date: str) -> Dict:
    """Get market breadth analysis for a specific date (string format)."""
    engine = ensure_engine()
    
    try:
        breadth_df = get_market_breadth_by_ratings(engine, trade_date)
        summary = get_market_breadth_summary(engine, trade_date)
        
        return {
            'success': True,
            'rating_distribution': breadth_df.to_dict('records') if not breadth_df.empty else [],
            'summary': summary,
            'analysis_date': trade_date,
            'total_analyzed': summary.get('total_stocks', 0)
        }
    except Exception as e:
        print(f"Error getting market breadth for {trade_date}: {e}")
        return {
            'success': False,
            'error': str(e),
            'rating_distribution': [],
            'summary': {},
            'analysis_date': trade_date,
            'total_analyzed': 0
        }


def get_market_breadth_trend(days: int = 30) -> Dict:
    """Get historical market breadth trend analysis."""
    try:
        engine = get_engine()
        
        historical_df = get_historical_market_breadth(engine, days)
        
        if historical_df.empty:
            return {
                'success': False,
                'error': 'No historical data found',
                'trend_data': [],
                'days_analyzed': 0
            }
        
        # Calculate trend indicators
        latest = historical_df.iloc[0]
        oldest = historical_df.iloc[-1]
        
        trend_analysis = {
            'bullish_trend': 'up' if latest['bullish_percentage'] > oldest['bullish_percentage'] else 'down',
            'rating_trend': 'up' if latest['market_avg_rating'] > oldest['market_avg_rating'] else 'down',
            'breadth_momentum': calculate_breadth_momentum(historical_df),
            'avg_bullish_percentage': historical_df['bullish_percentage'].mean().round(1),
            'avg_bearish_percentage': historical_df['bearish_percentage'].mean().round(1),
            'avg_market_rating': historical_df['market_avg_rating'].mean().round(2)
        }
        
        return {
            'success': True,
            'trend_data': historical_df.to_dict('records'),
            'days_analyzed': len(historical_df),
            'trend_analysis': trend_analysis,
            'date_range': {
                'start': historical_df['trade_date'].min(),
                'end': historical_df['trade_date'].max()
            }
        }
    except Exception as e:
        print(f"Error getting market breadth trend: {e}")
        return {
            'success': False,
            'error': str(e),
            'trend_data': [],
            'days_analyzed': 0
        }


def calculate_breadth_momentum(df: pd.DataFrame) -> str:
    """Calculate market breadth momentum based on recent changes."""
    if len(df) < 3:
        return 'insufficient_data'
    
    # Look at last 3 days of data
    recent = df.head(3)
    
    # Calculate momentum based on bullish percentage and average rating
    bullish_momentum = recent['bullish_percentage'].diff().mean()
    rating_momentum = recent['market_avg_rating'].diff().mean()
    
    if bullish_momentum > 2 and rating_momentum > 0.5:
        return 'strong_positive'
    elif bullish_momentum > 0 and rating_momentum > 0:
        return 'positive'
    elif bullish_momentum < -2 and rating_momentum < -0.5:
        return 'strong_negative'
    elif bullish_momentum < 0 and rating_momentum < 0:
        return 'negative'
    else:
        return 'neutral'


def get_breadth_categories() -> List[Dict]:
    """Get predefined breadth categories with color coding."""
    return [
        {
            'name': 'Very Bullish (8 to 10)',
            'min_rating': 8.0,
            'max_rating': 10.0,
            'color': '#00AA00',
            'description': 'Stocks with very strong bullish trends'
        },
        {
            'name': 'Bullish (5 to 7.9)',
            'min_rating': 5.0,
            'max_rating': 7.9,
            'color': '#44CC44',
            'description': 'Stocks with bullish trends'
        },
        {
            'name': 'Moderately Bullish (2 to 4.9)',
            'min_rating': 2.0,
            'max_rating': 4.9,
            'color': '#88DD88',
            'description': 'Stocks with moderate bullish bias'
        },
        {
            'name': 'Neutral (-1.9 to 1.9)',
            'min_rating': -1.9,
            'max_rating': 1.9,
            'color': '#FFAA00',
            'description': 'Stocks with neutral trends'
        },
        {
            'name': 'Moderately Bearish (-4.9 to -2)',
            'min_rating': -4.9,
            'max_rating': -2.0,
            'color': '#FF6666',
            'description': 'Stocks with moderate bearish bias'
        },
        {
            'name': 'Bearish (-7.9 to -5)',
            'min_rating': -7.9,
            'max_rating': -5.0,
            'color': '#CC3333',
            'description': 'Stocks with bearish trends'
        },
        {
            'name': 'Very Bearish (-10 to -8)',
            'min_rating': -10.0,
            'max_rating': -8.0,
            'color': '#AA0000',
            'description': 'Stocks with very strong bearish trends'
        }
    ]


def get_stocks_in_category(category_name: str, trade_date: Optional[str] = None, limit: int = 50) -> Dict:
    """Get stocks in a specific breadth category."""
    try:
        engine = get_engine()
        
        # Find category details
        categories = get_breadth_categories()
        category = next((c for c in categories if c['name'] == category_name), None)
        
        if not category:
            return {
                'success': False,
                'error': f'Category "{category_name}" not found',
                'stocks': []
            }
        
        stocks_df = get_stocks_by_rating_range(
            engine, 
            category['min_rating'], 
            category['max_rating'], 
            trade_date, 
            limit
        )
        
        return {
            'success': True,
            'category': category,
            'stocks': stocks_df.to_dict('records') if not stocks_df.empty else [],
            'total_found': len(stocks_df),
            'analysis_date': trade_date or datetime.now().date()
        }
    except Exception as e:
        print(f"Error getting stocks in category {category_name}: {e}")
        return {
            'success': False,
            'error': str(e),
            'stocks': []
        }


def calculate_market_breadth_score(summary: Dict) -> Tuple[float, str]:
    """Calculate overall market breadth score and interpretation."""
    if not summary:
        return 0.0, 'No data available'
    
    total = summary.get('total_stocks', 0)
    if total == 0:
        return 0.0, 'No stocks analyzed'
    
    # Weight different factors
    bullish_pct = summary.get('bullish_percentage', 0)
    strong_bullish_pct = (summary.get('strong_bullish_count', 0) / total) * 100
    avg_rating = summary.get('market_avg_rating', 0)
    bb_ratio = summary.get('bullish_bearish_ratio', 1)
    
    # Calculate weighted score (0-100)
    score = (
        bullish_pct * 0.4 +  # 40% weight on overall bullish percentage
        strong_bullish_pct * 0.3 +  # 30% weight on strong bullish stocks
        ((avg_rating + 10) / 20) * 100 * 0.2 +  # 20% weight on average rating (normalized)
        min(bb_ratio * 10, 50) * 0.1  # 10% weight on bullish/bearish ratio (capped at 50)
    )
    
    # Interpret score
    if score >= 80:
        interpretation = 'Very Bullish Market'
    elif score >= 65:
        interpretation = 'Bullish Market'
    elif score >= 50:
        interpretation = 'Moderately Bullish Market'
    elif score >= 35:
        interpretation = 'Neutral Market'
    elif score >= 20:
        interpretation = 'Bearish Market'
    else:
        interpretation = 'Very Bearish Market'
    
    return round(score, 1), interpretation


def get_breadth_alerts(summary: Dict, threshold_config: Optional[Dict] = None) -> List[Dict]:
    """Generate market breadth alerts based on thresholds."""
    if not summary:
        return []
    
    # Default thresholds
    thresholds = threshold_config or {
        'very_bullish_threshold': 15,  # % of very bullish stocks
        'very_bearish_threshold': 15,  # % of very bearish stocks
        'extreme_rating_threshold': 7,  # Average rating above/below this
        'low_participation_threshold': 500  # Minimum stocks for valid analysis
    }
    
    alerts = []
    total = summary.get('total_stocks', 0)
    
    # Low participation alert
    if total < thresholds['low_participation_threshold']:
        alerts.append({
            'type': 'warning',
            'title': 'Low Market Participation',
            'message': f'Only {total} stocks analyzed. Results may not be representative.',
            'severity': 'medium'
        })
    
    # Extreme bullish condition
    strong_bullish_pct = (summary.get('strong_bullish_count', 0) / max(total, 1)) * 100
    if strong_bullish_pct > thresholds['very_bullish_threshold']:
        alerts.append({
            'type': 'bullish',
            'title': 'Strong Bullish Breadth',
            'message': f'{strong_bullish_pct:.1f}% of stocks are very bullish (rating ≥ 5)',
            'severity': 'high'
        })
    
    # Extreme bearish condition
    strong_bearish_pct = (summary.get('strong_bearish_count', 0) / max(total, 1)) * 100
    if strong_bearish_pct > thresholds['very_bearish_threshold']:
        alerts.append({
            'type': 'bearish',
            'title': 'Strong Bearish Breadth',
            'message': f'{strong_bearish_pct:.1f}% of stocks are very bearish (rating ≤ -5)',
            'severity': 'high'
        })
    
    # Extreme average rating
    avg_rating = summary.get('market_avg_rating', 0)
    if avg_rating > thresholds['extreme_rating_threshold']:
        alerts.append({
            'type': 'bullish',
            'title': 'Extreme Bullish Rating',
            'message': f'Market average rating is {avg_rating}, indicating very strong bullish sentiment',
            'severity': 'high'
        })
    elif avg_rating < -thresholds['extreme_rating_threshold']:
        alerts.append({
            'type': 'bearish',
            'title': 'Extreme Bearish Rating',
            'message': f'Market average rating is {avg_rating}, indicating very strong bearish sentiment',
            'severity': 'high'
        })
    
    return alerts


def get_available_dates(limit: int = 30) -> List[date]:
    """Get list of available analysis dates for market breadth."""
    try:
        engine = get_engine()
        
        dates_df = get_available_analysis_dates(engine, limit=limit)
        if dates_df.empty:
            return []
        
        # Convert to list of date objects
        dates = []
        for _, row in dates_df.iterrows():
            trade_date = row['trade_date']
            if isinstance(trade_date, str):
                # Parse string date
                try:
                    parsed_date = datetime.strptime(trade_date, '%Y-%m-%d').date()
                    dates.append(parsed_date)
                except ValueError:
                    # Try other formats if needed
                    try:
                        parsed_date = datetime.strptime(trade_date, '%d-%m-%Y').date()
                        dates.append(parsed_date)
                    except ValueError:
                        continue
            elif isinstance(trade_date, datetime):
                dates.append(trade_date.date())
            elif isinstance(trade_date, date):
                dates.append(trade_date)
        
        return sorted(dates, reverse=True)  # Most recent first
    except Exception as e:
        print(f"Error getting available dates: {e}")
        return []


# Test function for development
def test_market_breadth():
    """Test market breadth functionality."""
    print("Testing Market Breadth Analysis")
    print("=" * 50)
    
    # Test current breadth
    current = get_current_market_breadth()
    print(f"Current breadth success: {current['success']}")
    if current['success']:
        print(f"Total stocks analyzed: {current['total_analyzed']}")
        print(f"Analysis date: {current['analysis_date']}")
        
        summary = current['summary']
        score, interpretation = calculate_market_breadth_score(summary)
        print(f"Market breadth score: {score} ({interpretation})")
        
        alerts = get_breadth_alerts(summary)
        print(f"Active alerts: {len(alerts)}")
        
        print("\nRating Distribution:")
        for dist in current['rating_distribution']:
            print(f"  {dist['rating_category']}: {dist['stock_count']} stocks")
    
    # Test trend analysis
    print(f"\nTrend Analysis (30 days):")
    trend = get_market_breadth_trend(30)
    print(f"Trend analysis success: {trend['success']}")
    if trend['success']:
        print(f"Days analyzed: {trend['days_analyzed']}")
        trend_analysis = trend['trend_analysis']
        print(f"Breadth momentum: {trend_analysis['breadth_momentum']}")
        print(f"Average bullish %: {trend_analysis['avg_bullish_percentage']}")


def check_trend_data_exists(trade_date) -> bool:
    """Check if trend analysis data exists for a specific date."""
    try:
        engine = get_engine()
        
        # Convert date object to string if needed
        if isinstance(trade_date, date):
            trade_date_str = trade_date.strftime('%Y-%m-%d')
        else:
            trade_date_str = trade_date
            
        # Import the function from trends_repo
        from db.trends_repo import get_trend_analysis
        
        # Check if any trend data exists for the date
        trend_df = get_trend_analysis(engine, trade_date_str, limit=1)
        return not trend_df.empty
        
    except Exception as e:
        print(f"Error checking trend data for {trade_date}: {e}")
        return False


def scan_and_calculate_market_breadth(trade_date) -> Dict:
    """Scan for trend ratings and calculate market breadth for a specific date."""
    try:
        engine = get_engine()
        
        # Convert date object to string if needed
        if isinstance(trade_date, date):
            trade_date_str = trade_date.strftime('%Y-%m-%d')
            trade_date_obj = trade_date
        else:
            trade_date_str = trade_date
            trade_date_obj = datetime.strptime(trade_date_str, '%Y-%m-%d').date()
            
        print(f"🔍 Scanning and calculating market breadth for {trade_date_str}...")
        
        # First check if we have BHAV data for this date
        from sqlalchemy import text
        with engine.connect() as conn:
            bhav_check_sql = text("""
                SELECT COUNT(*) as count 
                FROM nse_equity_bhavcopy_full 
                WHERE trade_date = :trade_date
            """)
            bhav_result = conn.execute(bhav_check_sql, {"trade_date": trade_date_str}).fetchone()
            
            if not bhav_result or bhav_result.count == 0:
                return {
                    'success': False,
                    'error': f'No BHAV data available for {trade_date_str}',
                    'rating_distribution': [],
                    'summary': {},
                    'analysis_date': trade_date_str,
                    'total_analyzed': 0
                }
        
        # Import trend scanning functions
        from services.trends_service import scan_historical_trends_for_range
        
        # Scan trends for this specific date (single day range)
        print(f"📊 Scanning trend data for {trade_date_str}...")
        trend_df = scan_historical_trends_for_range(trade_date_obj, trade_date_obj, engine)
        
        if trend_df.empty:
            return {
                'success': False,
                'error': f'Failed to calculate trend data for {trade_date_str}',
                'rating_distribution': [],
                'summary': {},
                'analysis_date': trade_date_str,
                'total_analyzed': 0
            }
        
        # Now get the market breadth analysis using the newly calculated data
        print(f"📈 Calculating market breadth from trend data...")
        breadth_df = get_market_breadth_by_ratings(engine, trade_date_str)
        summary = get_market_breadth_summary(engine, trade_date_str)
        
        return {
            'success': True,
            'rating_distribution': breadth_df.to_dict('records') if not breadth_df.empty else [],
            'summary': summary,
            'analysis_date': trade_date_str,
            'total_analyzed': summary.get('total_stocks', 0),
            'newly_calculated': True  # Flag to indicate this was just calculated
        }
        
    except Exception as e:
        print(f"❌ Error scanning and calculating market breadth for {trade_date}: {e}")
        import traceback
        traceback.print_exc()
        return {
            'success': False,
            'error': str(e),
            'rating_distribution': [],
            'summary': {},
            'analysis_date': trade_date,
            'total_analyzed': 0
        }


def get_market_depth_analysis_for_range(start_date, end_date) -> Dict:
    """Get market depth analysis for a date range using trend ratings."""
    try:
        engine = get_engine()
        
        # Convert date objects to strings if needed
        if isinstance(start_date, date):
            start_date_str = start_date.strftime('%Y-%m-%d')
            start_date_obj = start_date
        else:
            start_date_str = start_date
            start_date_obj = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            
        if isinstance(end_date, date):
            end_date_str = end_date.strftime('%Y-%m-%d')
            end_date_obj = end_date
        else:
            end_date_str = end_date
            end_date_obj = datetime.strptime(end_date_str, '%Y-%m-%d').date()
            
        print(f"🔍 Analyzing market depth from {start_date_str} to {end_date_str}...")
        
        # Get all trading dates in the range with trend data
        from sqlalchemy import text
        with engine.connect() as conn:
            sql = text("""
                SELECT DISTINCT trade_date,
                       COUNT(*) as total_stocks,
                       AVG(trend_rating) as avg_rating,
                       SUM(CASE WHEN trend_rating >= 2 THEN 1 ELSE 0 END) as bullish_count,
                       SUM(CASE WHEN trend_rating <= -2 THEN 1 ELSE 0 END) as bearish_count,
                       SUM(CASE WHEN trend_rating > -2 AND trend_rating < 2 THEN 1 ELSE 0 END) as neutral_count,
                       SUM(CASE WHEN trend_rating >= 8 THEN 1 ELSE 0 END) as very_bullish_count,
                       SUM(CASE WHEN trend_rating <= -8 THEN 1 ELSE 0 END) as very_bearish_count
                FROM trend_analysis 
                WHERE trade_date >= :start_date AND trade_date <= :end_date
                GROUP BY trade_date
                ORDER BY trade_date
            """)
            
            df = pd.read_sql(sql, con=conn, params={
                'start_date': start_date_str,
                'end_date': end_date_str
            })
        
        if df.empty:
            return {
                'success': False,
                'error': f'No trend data found for date range {start_date_str} to {end_date_str}',
                'daily_analysis': [],
                'summary': {},
                'date_range': {'start': start_date_str, 'end': end_date_str},
                'total_days': 0
            }
        
        # Calculate percentages
        df['bullish_percentage'] = (df['bullish_count'] / df['total_stocks'] * 100).round(1)
        df['bearish_percentage'] = (df['bearish_count'] / df['total_stocks'] * 100).round(1)
        df['neutral_percentage'] = (df['neutral_count'] / df['total_stocks'] * 100).round(1)
        
        # Calculate summary statistics for the entire range
        total_days = len(df)
        avg_total_stocks = df['total_stocks'].mean()
        avg_bullish_pct = df['bullish_percentage'].mean()
        avg_bearish_pct = df['bearish_percentage'].mean()
        avg_rating = df['avg_rating'].mean()
        
        # Market sentiment trend (comparing first and last week)
        if total_days >= 7:
            first_week = df.head(5)['bullish_percentage'].mean()
            last_week = df.tail(5)['bullish_percentage'].mean()
            sentiment_trend = last_week - first_week
        else:
            sentiment_trend = 0
        
        # Volatility measure (standard deviation of bullish percentage)
        volatility = df['bullish_percentage'].std()
        
        summary = {
            'date_range': {'start': start_date_str, 'end': end_date_str},
            'total_days_analyzed': total_days,
            'avg_total_stocks': round(avg_total_stocks),
            'avg_bullish_percentage': round(avg_bullish_pct, 1),
            'avg_bearish_percentage': round(avg_bearish_pct, 1),
            'avg_market_rating': round(avg_rating, 2),
            'sentiment_trend': round(sentiment_trend, 1),
            'market_volatility': round(volatility, 1),
            'max_bullish_day': {
                'date': df.loc[df['bullish_percentage'].idxmax(), 'trade_date'].strftime('%Y-%m-%d'),
                'percentage': df['bullish_percentage'].max()
            },
            'min_bullish_day': {
                'date': df.loc[df['bullish_percentage'].idxmin(), 'trade_date'].strftime('%Y-%m-%d'),
                'percentage': df['bullish_percentage'].min()
            }
        }
        
        # Convert DataFrame to list of dictionaries for JSON serialization
        daily_analysis = []
        for _, row in df.iterrows():
            daily_analysis.append({
                'trade_date': row['trade_date'].strftime('%Y-%m-%d'),
                'total_stocks': int(row['total_stocks']),
                'avg_rating': round(row['avg_rating'], 2),
                'bullish_count': int(row['bullish_count']),
                'bearish_count': int(row['bearish_count']),
                'neutral_count': int(row['neutral_count']),
                'bullish_percentage': row['bullish_percentage'],
                'bearish_percentage': row['bearish_percentage'],
                'neutral_percentage': row['neutral_percentage'],
                'very_bullish_count': int(row['very_bullish_count']),
                'very_bearish_count': int(row['very_bearish_count'])
            })
        
        return {
            'success': True,
            'daily_analysis': daily_analysis,
            'summary': summary,
            'date_range': {'start': start_date_str, 'end': end_date_str},
            'total_days': total_days
        }
        
    except Exception as e:
        print(f"❌ Error in market depth analysis for range {start_date} to {end_date}: {e}")
        import traceback
        traceback.print_exc()
        return {
            'success': False,
            'error': str(e),
            'daily_analysis': [],
            'summary': {},
            'date_range': {'start': str(start_date), 'end': str(end_date)},
            'total_days': 0
        }


def calculate_market_depth_trends(daily_analysis: List[Dict]) -> Dict:
    """Calculate trend indicators for market depth analysis."""
    if not daily_analysis or len(daily_analysis) < 2:
        return {}
    
    try:
        # Convert to DataFrame for easier analysis
        df = pd.DataFrame(daily_analysis)
        df['trade_date'] = pd.to_datetime(df['trade_date'])
        
        # Calculate moving averages for trend analysis
        df['bullish_ma5'] = df['bullish_percentage'].rolling(window=min(5, len(df))).mean()
        df['rating_ma5'] = df['avg_rating'].rolling(window=min(5, len(df))).mean()
        
        # Trend direction (linear regression slope)
        from scipy import stats
        if len(df) > 1:
            x = range(len(df))
            bullish_slope, _, _, _, _ = stats.linregress(x, df['bullish_percentage'])
            rating_slope, _, _, _, _ = stats.linregress(x, df['avg_rating'])
        else:
            bullish_slope = rating_slope = 0
        
        # Momentum indicators
        recent_period = min(5, len(df))
        recent_bullish = df['bullish_percentage'].tail(recent_period).mean()
        early_bullish = df['bullish_percentage'].head(recent_period).mean()
        momentum = recent_bullish - early_bullish
        
        return {
            'bullish_trend_slope': round(bullish_slope, 3),
            'rating_trend_slope': round(rating_slope, 3),
            'momentum_change': round(momentum, 1),
            'trend_direction': 'Improving' if bullish_slope > 0.1 else 'Declining' if bullish_slope < -0.1 else 'Stable',
            'recent_avg_bullish': round(recent_bullish, 1),
            'early_avg_bullish': round(early_bullish, 1)
        }
        
    except ImportError:
        # Fallback if scipy is not available
        return {
            'trend_direction': 'Unknown (scipy not available)',
            'momentum_change': 0
        }
    except Exception as e:
        print(f"Error calculating trends: {e}")
        return {}


def get_or_calculate_market_breadth(trade_date) -> Dict:
    """Get market breadth for a date, calculating if needed."""
    try:
        # First try to get existing data
        print(f"🔍 Checking for existing market breadth data for {trade_date}...")
        existing_data = get_market_breadth_for_date(trade_date)
        
        if existing_data['success'] and existing_data['total_analyzed'] > 0:
            print(f"✅ Found existing data: {existing_data['total_analyzed']} stocks analyzed")
            return existing_data
        
        # Check if trend data exists
        print(f"🔍 Checking if trend data exists for {trade_date}...")
        if check_trend_data_exists(trade_date):
            print(f"✅ Trend data exists, but market breadth calculation may have failed. Retrying...")
            # Try again in case it was a temporary issue
            retry_data = get_market_breadth_for_date(trade_date)
            if retry_data['success'] and retry_data['total_analyzed'] > 0:
                return retry_data
        
        # No data available, need to scan and calculate
        print(f"📊 No existing data found. Scanning and calculating...")
        return scan_and_calculate_market_breadth(trade_date)
        
    except Exception as e:
        print(f"❌ Error in get_or_calculate_market_breadth for {trade_date}: {e}")
        return {
            'success': False,
            'error': str(e),
            'rating_distribution': [],
            'summary': {},
            'analysis_date': trade_date,
            'total_analyzed': 0
        }


def get_nifty_with_breadth_chart_data(start_date, end_date, index_name='NIFTY 50'):
    """
    Get Nifty chart data combined with bullish/bearish stock counts for charting.
    
    Returns:
    {
        'success': bool,
        'nifty_data': DataFrame with OHLC data,
        'breadth_data': DataFrame with bullish/bearish counts,
        'combined_data': DataFrame with aligned dates,
        'error': str (if success=False)
    }
    """
    print(f"🔍 Getting Nifty + Breadth chart data from {start_date} to {end_date}...")
    
    try:
        engine = get_engine()
        
        # Convert dates to strings for SQL
        start_date_str = start_date.strftime('%Y-%m-%d') if hasattr(start_date, 'strftime') else str(start_date)
        end_date_str = end_date.strftime('%Y-%m-%d') if hasattr(end_date, 'strftime') else str(end_date)
        
        with engine.connect() as conn:
            # 1. Get Nifty index data
            nifty_sql = text("""
                SELECT 
                    trade_date,
                    `open`,
                    `high`, 
                    `low`,
                    `close`,
                    shares_traded,
                    turnover_cr
                FROM indices_daily 
                WHERE index_name = :index_name 
                AND trade_date BETWEEN :start_date AND :end_date
                ORDER BY trade_date
            """)
            
            nifty_df = pd.read_sql(nifty_sql, con=conn, params={
                'index_name': index_name,
                'start_date': start_date_str,
                'end_date': end_date_str
            })
            
            # 2. Get breadth data (bullish/bearish counts)
            breadth_sql = text("""
                SELECT 
                    trade_date,
                    COUNT(*) as total_stocks,
                    AVG(trend_rating) as avg_rating,
                    SUM(CASE WHEN trend_rating > 0 THEN 1 ELSE 0 END) as bullish_count,
                    SUM(CASE WHEN trend_rating < 0 THEN 1 ELSE 0 END) as bearish_count,
                    SUM(CASE WHEN trend_rating = 0 THEN 1 ELSE 0 END) as neutral_count,
                    SUM(CASE WHEN trend_rating >= 7 THEN 1 ELSE 0 END) as very_bullish_count,
                    SUM(CASE WHEN trend_rating <= -7 THEN 1 ELSE 0 END) as very_bearish_count
                FROM trend_analysis 
                WHERE trade_date BETWEEN :start_date AND :end_date 
                GROUP BY trade_date 
                ORDER BY trade_date
            """)
            
            breadth_df = pd.read_sql(breadth_sql, con=conn, params={
                'start_date': start_date_str,
                'end_date': end_date_str
            })
        
        # Check if we have data
        if nifty_df.empty and breadth_df.empty:
            return {
                'success': False,
                'error': f'No data found for {index_name} or breadth analysis between {start_date_str} and {end_date_str}',
                'nifty_data': pd.DataFrame(),
                'breadth_data': pd.DataFrame(),
                'combined_data': pd.DataFrame()
            }
        
        # Log data availability
        print(f"📊 Data availability: Nifty={len(nifty_df)} rows, Breadth={len(breadth_df)} rows")
        if not nifty_df.empty:
            print(f"   📈 Nifty date range: {nifty_df['trade_date'].min()} to {nifty_df['trade_date'].max()}")
        if not breadth_df.empty:
            print(f"   📊 Breadth date range: {breadth_df['trade_date'].min()} to {breadth_df['trade_date'].max()}")
        
        # Process breadth data
        if not breadth_df.empty:
            breadth_df['bullish_percentage'] = (breadth_df['bullish_count'] / breadth_df['total_stocks'] * 100).round(1)
            breadth_df['bearish_percentage'] = (breadth_df['bearish_count'] / breadth_df['total_stocks'] * 100).round(1)
            breadth_df['neutral_percentage'] = (breadth_df['neutral_count'] / breadth_df['total_stocks'] * 100).round(1)
        
        # Combine data on trade_date for aligned charting
        combined_df = pd.DataFrame()
        if not nifty_df.empty and not breadth_df.empty:
            # Merge on trade_date with inner join to keep only common dates
            combined_df = pd.merge(nifty_df, breadth_df, on='trade_date', how='inner')
            combined_df = combined_df.sort_values('trade_date')
            combined_df['trade_date'] = pd.to_datetime(combined_df['trade_date'])
            
            # If inner join results in empty data, fall back to outer join with interpolation
            if combined_df.empty:
                print("⚠️ No overlapping dates found, using outer join with interpolation...")
                combined_df = pd.merge(nifty_df, breadth_df, on='trade_date', how='outer')
                combined_df = combined_df.sort_values('trade_date')
                combined_df['trade_date'] = pd.to_datetime(combined_df['trade_date'])
                
                # Forward fill missing values for better visualization
                numeric_cols = ['open', 'high', 'low', 'close', 'bullish_count', 'bearish_count', 'neutral_count']
                for col in numeric_cols:
                    if col in combined_df.columns:
                        combined_df[col] = combined_df[col].ffill().bfill()
        elif not nifty_df.empty:
            combined_df = nifty_df.copy()
            combined_df['trade_date'] = pd.to_datetime(combined_df['trade_date'])
        elif not breadth_df.empty:
            combined_df = breadth_df.copy()
            combined_df['trade_date'] = pd.to_datetime(combined_df['trade_date'])
        
        return {
            'success': True,
            'nifty_data': nifty_df,
            'breadth_data': breadth_df,
            'combined_data': combined_df,
            'date_range': {'start': start_date_str, 'end': end_date_str},
            'index_name': index_name,
            'total_days': len(combined_df)
        }
        
    except Exception as e:
        print(f"❌ Error getting Nifty + Breadth chart data: {e}")
        import traceback
        traceback.print_exc()
        return {
            'success': False,
            'error': str(e),
            'nifty_data': pd.DataFrame(),
            'breadth_data': pd.DataFrame(),
            'combined_data': pd.DataFrame()
        }


def get_sectoral_analysis_dates(days: int = 30) -> List[date]:
    """
    Get available dates for sectoral analysis from trend_analysis table
    
    Args:
        days: Number of recent days to retrieve
        
    Returns:
        List of available dates sorted by most recent first
    """
    try:
        engine = ensure_engine()
        with engine.connect() as conn:
            query = text("""
                SELECT DISTINCT trade_date
                FROM trend_analysis 
                ORDER BY trade_date DESC
                LIMIT :days
            """)
            
            result = conn.execute(query, {"days": days})
            dates = [row[0] for row in result.fetchall()]
            
            return dates
            
    except Exception as e:
        print(f"❌ Error getting sectoral analysis dates: {e}")
        return []


def get_sectoral_breadth(sector_code: str, analysis_date: Optional[date] = None) -> Dict:
    """
    Get market breadth analysis for a specific sector
    
    Args:
        sector_code: Index code (e.g., 'NIFTY-BANK', 'NIFTY-IT')
        analysis_date: Date for analysis (defaults to latest)
        
    Returns:
        Dict with sectoral breadth analysis
    """
    try:
        # Import the index symbols API
        from services.index_symbols_api import get_index_symbols
        
        # Get symbols for the sector
        sector_symbols = get_index_symbols(sector_code)
        
        if not sector_symbols:
            return {
                'success': False,
                'error': f'No symbols found for sector {sector_code}',
                'sector_code': sector_code,
                'analysis_date': analysis_date
            }
        
        if analysis_date is None:
            analysis_date = date.today()
        
        # Get breadth data filtered to sector symbols
        engine = ensure_engine()
        with engine.connect() as conn:
            # Build the symbol list for SQL
            symbol_list = ','.join(f"'{symbol}'" for symbol in sector_symbols)
            
            query = text(f"""
                SELECT 
                    symbol,
                    trend_rating,
                    daily_trend,
                    weekly_trend,
                    monthly_trend
                FROM trend_analysis 
                WHERE trade_date = :analysis_date
                AND symbol IN ({symbol_list})
                ORDER BY symbol
            """)
            
            result = conn.execute(query, {"analysis_date": analysis_date})
            df = pd.DataFrame(result.fetchall(), columns=[
                'symbol', 'trend_rating', 'daily_trend', 
                'weekly_trend', 'monthly_trend'
            ])
        
        if df.empty:
            # No data for the selected date - check for available dates nearby
            with engine.connect() as conn:
                # Check for the latest available date
                latest_query = text("""
                    SELECT MAX(trade_date) as latest_date
                    FROM trend_analysis 
                """)
                latest_result = conn.execute(latest_query).fetchone()
                latest_available = latest_result[0] if latest_result[0] else None
                
                # Check for available dates around the requested date
                nearby_query = text("""
                    SELECT DISTINCT trade_date 
                    FROM trend_analysis 
                    WHERE trade_date BETWEEN DATE_SUB(:analysis_date, INTERVAL 7 DAY) 
                    AND DATE_ADD(:analysis_date, INTERVAL 7 DAY)
                    ORDER BY ABS(DATEDIFF(trade_date, :analysis_date))
                    LIMIT 5
                """)
                nearby_result = conn.execute(nearby_query, {"analysis_date": analysis_date})
                nearby_dates = [str(row[0]) for row in nearby_result.fetchall()]
                
            # Build helpful error message
            error_msg = f'No trend data found for {sector_code} on {analysis_date}'
            if latest_available:
                error_msg += f'\nLatest available data: {latest_available}'
            if nearby_dates:
                error_msg += f'\nNearby available dates: {", ".join(nearby_dates)}'
            
            return {
                'success': False,
                'error': error_msg,
                'sector_code': sector_code,
                'analysis_date': analysis_date,
                'latest_available': latest_available,
                'nearby_dates': nearby_dates
            }
        
        # Calculate sectoral breadth metrics
        total_stocks = len(df)
        
        # Rating distribution (using trend_rating numeric values)
        # Convert numeric ratings to categories
        def categorize_trend_rating(rating):
            if rating >= 5:
                return 'Very Bullish'
            elif rating >= 2:
                return 'Bullish'
            elif rating >= -1.9:
                return 'Neutral'
            elif rating >= -5:
                return 'Bearish'
            else:
                return 'Very Bearish'
        
        df['trend_category'] = df['trend_rating'].apply(categorize_trend_rating)
        rating_dist = df['trend_category'].value_counts().to_dict()
        rating_percentages = {
            rating: (count / total_stocks) * 100 
            for rating, count in rating_dist.items()
        }
        
        # Bullish vs Bearish breakdown
        bullish_count = df[df['trend_category'].isin(['Very Bullish', 'Bullish'])].shape[0]
        bearish_count = df[df['trend_category'].isin(['Very Bearish', 'Bearish'])].shape[0]
        neutral_count = df[df['trend_category'] == 'Neutral'].shape[0]
        
        # Trend breakdowns
        daily_up = df[df['daily_trend'] == 'UP'].shape[0]
        weekly_up = df[df['weekly_trend'] == 'UP'].shape[0]
        monthly_up = df[df['monthly_trend'] == 'UP'].shape[0]
        
        return {
            'success': True,
            'sector_code': sector_code,
            'analysis_date': analysis_date,
            'total_stocks': total_stocks,
            'symbols_analyzed': len(df),
            'coverage_percent': (len(df) / len(sector_symbols)) * 100,
            'rating_distribution': rating_dist,
            'rating_percentages': rating_percentages,
            'breadth_summary': {
                'bullish_count': bullish_count,
                'bullish_percent': (bullish_count / total_stocks) * 100,
                'bearish_count': bearish_count,
                'bearish_percent': (bearish_count / total_stocks) * 100,
                'neutral_count': neutral_count,
                'neutral_percent': (neutral_count / total_stocks) * 100,
            },
            'technical_breadth': {
                'daily_uptrend_count': daily_up,
                'daily_uptrend_percent': (daily_up / total_stocks) * 100,
                'weekly_uptrend_count': weekly_up,
                'weekly_uptrend_percent': (weekly_up / total_stocks) * 100,
                'monthly_uptrend_count': monthly_up,
                'monthly_uptrend_percent': (monthly_up / total_stocks) * 100,
            },
            'sector_data': df
        }
        
    except Exception as e:
        return {
            'success': False,
            'error': f'Error analyzing sectoral breadth: {str(e)}',
            'sector_code': sector_code,
            'analysis_date': analysis_date
        }


def compare_sectoral_breadth(sector_codes: List[str], analysis_date: Optional[date] = None) -> Dict:
    """
    Compare breadth analysis across multiple sectors
    
    Args:
        sector_codes: List of sector index codes
        analysis_date: Date for analysis (defaults to latest)
        
    Returns:
        Dict with comparative sectoral analysis
    """
    if analysis_date is None:
        analysis_date = date.today()
    
    sector_results = {}
    comparison_summary = []
    
    for sector_code in sector_codes:
        sector_data = get_sectoral_breadth(sector_code, analysis_date)
        sector_results[sector_code] = sector_data
        
        if sector_data['success']:
            comparison_summary.append({
                'sector': sector_code,
                'total_stocks': sector_data['total_stocks'],
                'bullish_percent': sector_data['breadth_summary']['bullish_percent'],
                'bearish_percent': sector_data['breadth_summary']['bearish_percent'],
                'daily_uptrend_percent': sector_data['technical_breadth']['daily_uptrend_percent'],
                'weekly_uptrend_percent': sector_data['technical_breadth']['weekly_uptrend_percent'],
            })
    
    # Sort by bullish percentage
    comparison_summary.sort(key=lambda x: x['bullish_percent'], reverse=True)
    
    return {
        'analysis_date': analysis_date,
        'sectors_analyzed': len(sector_codes),
        'successful_analyses': len(comparison_summary),
        'sector_results': sector_results,
        'comparison_summary': comparison_summary,
        'top_performing_sector': comparison_summary[0] if comparison_summary else None,
        'weakest_performing_sector': comparison_summary[-1] if comparison_summary else None
    }


def get_all_sectoral_breadth(analysis_date: Optional[date] = None) -> Dict:
    """
    Get breadth analysis for all major sectors
    
    Args:
        analysis_date: Date for analysis (defaults to latest)
        
    Returns:
        Dict with all sectoral breadth data
    """
    major_sectors = [
        'NIFTY-BANK', 'NIFTY-IT', 'NIFTY-AUTO', 'NIFTY-PHARMA', 
        'NIFTY-METAL', 'NIFTY-FMCG', 'NIFTY-REALTY', 'NIFTY-MEDIA'
    ]
    
    return compare_sectoral_breadth(major_sectors, analysis_date)


def test_sectoral_breadth():
    """Test sectoral breadth analysis"""
    print("🧪 Testing Sectoral Breadth Analysis")
    print("=" * 50)
    
    # Test single sector
    print("\n📊 1. Single Sector Analysis (NIFTY-BANK):")
    bank_data = get_sectoral_breadth('NIFTY-BANK')
    if bank_data['success']:
        print(f"   ✅ Banking sector: {bank_data['symbols_analyzed']}/{bank_data['total_stocks']} stocks analyzed")
        print(f"   📈 Bullish: {bank_data['breadth_summary']['bullish_percent']:.1f}%")
        print(f"   📉 Bearish: {bank_data['breadth_summary']['bearish_percent']:.1f}%")
    else:
        print(f"   ❌ Error: {bank_data['error']}")
    
    # Test multi-sector comparison
    print("\n🔄 2. Multi-Sector Comparison:")
    comparison = compare_sectoral_breadth(['NIFTY-BANK', 'NIFTY-IT', 'NIFTY-PHARMA'])
    if comparison['comparison_summary']:
        for sector_data in comparison['comparison_summary']:
            print(f"   {sector_data['sector']:<15}: {sector_data['bullish_percent']:>5.1f}% bullish, "
                  f"{sector_data['daily_uptrend_percent']:>5.1f}% daily uptrend")
    
    # Test all sectors
    print("\n📈 3. All Major Sectors:")
    all_sectors = get_all_sectoral_breadth()
    if all_sectors['comparison_summary']:
        print(f"   Analyzed {all_sectors['successful_analyses']} sectors:")
        top_sector = all_sectors['top_performing_sector']
        weak_sector = all_sectors['weakest_performing_sector']
        print(f"   🥇 Best: {top_sector['sector']} ({top_sector['bullish_percent']:.1f}% bullish)")
        print(f"   🥉 Weak: {weak_sector['sector']} ({weak_sector['bullish_percent']:.1f}% bullish)")


if __name__ == "__main__":
    print("🔍 Market Breadth Service with Sectoral Analysis")
    print("=" * 60)
    
    # Run original market breadth test
    test_market_breadth()
    
    print("\n" + "=" * 60)
    
    # Run new sectoral breadth test
    test_sectoral_breadth()