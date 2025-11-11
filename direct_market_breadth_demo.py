"""
Simple Market Breadth Analysis with Direct Database Connection

This demonstrates market breadth analysis for selected dates using
a direct database connection.
"""
import sys
import os
from datetime import datetime, date
from typing import Dict, List, Optional

# Add parent directory for imports
sys.path.append('d:/MyProjects/StockScreeer')

import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Database configuration
HOST = os.getenv("MYSQL_HOST", "127.0.0.1")
PORT = int(os.getenv("MYSQL_PORT", "3306"))
DB   = os.getenv("MYSQL_DB", "marketdata")
USER = os.getenv("MYSQL_USER", "root")
PWD  = os.getenv("MYSQL_PASSWORD", "")

def create_db_engine():
    """Create database engine with environment variables."""
    url = URL.create(
        drivername="mysql+pymysql",
        username=USER,
        password=PWD,
        host=HOST,
        port=int(PORT),
        database=DB,
        query={"charset": "utf8mb4"},
    )
    return create_engine(url, pool_pre_ping=True, pool_recycle=3600)


def get_market_breadth_by_ratings_direct(engine, trade_date: Optional[str] = None) -> pd.DataFrame:
    """Get market breadth analysis by trend rating groups for a specific date or latest date."""
    if trade_date:
        date_condition = "t.trade_date = :trade_date"
        params = {"trade_date": trade_date}
    else:
        date_condition = "t.trade_date = (SELECT MAX(trade_date) FROM trend_analysis)"
        params = {}
    
    sql = text(f"""
    SELECT 
        CASE 
            WHEN t.trend_rating >= 8 THEN 'Very Bullish (8 to 10)'
            WHEN t.trend_rating >= 5 THEN 'Bullish (5 to 7.9)'
            WHEN t.trend_rating >= 2 THEN 'Moderately Bullish (2 to 4.9)'
            WHEN t.trend_rating >= -2 THEN 'Neutral (-1.9 to 1.9)'
            WHEN t.trend_rating >= -5 THEN 'Moderately Bearish (-4.9 to -2)'
            WHEN t.trend_rating >= -8 THEN 'Bearish (-7.9 to -5)'
            ELSE 'Very Bearish (-10 to -8)'
        END as rating_category,
        COUNT(*) as stock_count,
        ROUND(AVG(t.trend_rating), 2) as avg_rating,
        MIN(t.trend_rating) as min_rating,
        MAX(t.trend_rating) as max_rating,
        t.trade_date
    FROM trend_analysis t
    WHERE {date_condition}
    GROUP BY 
        CASE 
            WHEN t.trend_rating >= 8 THEN 'Very Bullish (8 to 10)'
            WHEN t.trend_rating >= 5 THEN 'Bullish (5 to 7.9)'
            WHEN t.trend_rating >= 2 THEN 'Moderately Bullish (2 to 4.9)'
            WHEN t.trend_rating >= -2 THEN 'Neutral (-1.9 to 1.9)'
            WHEN t.trend_rating >= -5 THEN 'Moderately Bearish (-4.9 to -2)'
            WHEN t.trend_rating >= -8 THEN 'Bearish (-7.9 to -5)'
            ELSE 'Very Bearish (-10 to -8)'
        END,
        t.trade_date
    ORDER BY avg_rating DESC
    """)
    
    with engine.connect() as conn:
        return pd.read_sql(sql, con=conn, params=params)


def get_market_breadth_summary_direct(engine, trade_date: Optional[str] = None) -> dict:
    """Get overall market breadth summary with key metrics."""
    if trade_date:
        date_condition = "trade_date = :trade_date"
        params = {"trade_date": trade_date}
    else:
        date_condition = "trade_date = (SELECT MAX(trade_date) FROM trend_analysis)"
        params = {}
    
    sql = text(f"""
    SELECT 
        COUNT(*) as total_stocks,
        SUM(CASE WHEN trend_rating > 0 THEN 1 ELSE 0 END) as bullish_count,
        SUM(CASE WHEN trend_rating < 0 THEN 1 ELSE 0 END) as bearish_count,
        SUM(CASE WHEN trend_rating = 0 THEN 1 ELSE 0 END) as neutral_count,
        SUM(CASE WHEN trend_rating >= 5 THEN 1 ELSE 0 END) as strong_bullish_count,
        SUM(CASE WHEN trend_rating <= -5 THEN 1 ELSE 0 END) as strong_bearish_count,
        ROUND(AVG(trend_rating), 2) as market_avg_rating,
        MIN(trade_date) as analysis_date
    FROM trend_analysis 
    WHERE {date_condition}
    """)
    
    with engine.connect() as conn:
        df = pd.read_sql(sql, con=conn, params=params)
        if df.empty:
            return {}
        
        row = df.iloc[0]
        total = row['total_stocks']
        
        return {
            'analysis_date': row['analysis_date'],
            'total_stocks': total,
            'bullish_count': row['bullish_count'],
            'bearish_count': row['bearish_count'],
            'neutral_count': row['neutral_count'],
            'strong_bullish_count': row['strong_bullish_count'],
            'strong_bearish_count': row['strong_bearish_count'],
            'market_avg_rating': row['market_avg_rating'],
            'bullish_percentage': round((row['bullish_count'] / total) * 100, 1) if total > 0 else 0,
            'bearish_percentage': round((row['bearish_count'] / total) * 100, 1) if total > 0 else 0,
            'neutral_percentage': round((row['neutral_count'] / total) * 100, 1) if total > 0 else 0,
            'bullish_bearish_ratio': round(row['bullish_count'] / max(row['bearish_count'], 1), 2)
        }


def get_available_dates_direct(engine, limit: int = 30) -> List[date]:
    """Get available analysis dates."""
    sql = text("""
    SELECT DISTINCT trade_date 
    FROM trend_analysis 
    ORDER BY trade_date DESC 
    LIMIT :limit
    """)
    
    with engine.connect() as conn:
        df = pd.read_sql(sql, con=conn, params={"limit": limit})
        dates = []
        for _, row in df.iterrows():
            trade_date = row['trade_date']
            if isinstance(trade_date, str):
                try:
                    parsed_date = datetime.strptime(trade_date, '%Y-%m-%d').date()
                    dates.append(parsed_date)
                except ValueError:
                    continue
            elif isinstance(trade_date, datetime):
                dates.append(trade_date.date())
            elif isinstance(trade_date, date):
                dates.append(trade_date)
        
        return dates


def analyze_market_breadth_for_date(trade_date: Optional[str] = None) -> Dict:
    """Analyze market breadth for a specific date or latest."""
    engine = create_db_engine()
    
    try:
        # Get rating distribution
        breadth_df = get_market_breadth_by_ratings_direct(engine, trade_date)
        summary = get_market_breadth_summary_direct(engine, trade_date)
        
        return {
            'success': True,
            'rating_distribution': breadth_df.to_dict('records') if not breadth_df.empty else [],
            'summary': summary,
            'analysis_date': trade_date or summary.get('analysis_date', 'Latest'),
            'total_analyzed': summary.get('total_stocks', 0)
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'rating_distribution': [],
            'summary': {},
            'analysis_date': trade_date,
            'total_analyzed': 0
        }


def calculate_market_breadth_score(summary: Dict) -> tuple:
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


def print_market_breadth_analysis(data: Dict, date_label: str):
    """Print formatted market breadth analysis."""
    print(f"\n{'='*70}")
    print(f"MARKET BREADTH ANALYSIS FOR {date_label}")
    print(f"{'='*70}")
    
    if not data.get('success', False):
        print(f"❌ Error: {data.get('error', 'Unknown error')}")
        return
    
    summary = data.get('summary', {})
    distribution = data.get('rating_distribution', [])
    
    # Basic metrics
    print(f"\n📊 BASIC METRICS:")
    print(f"   Total Stocks Analyzed: {summary.get('total_stocks', 0):,}")
    print(f"   Analysis Date: {summary.get('analysis_date', 'N/A')}")
    print(f"   Market Average Rating: {summary.get('market_avg_rating', 0):.2f}")
    
    # Bullish/Bearish breakdown
    print(f"\n📈 BULLISH/BEARISH BREAKDOWN:")
    print(f"   Bullish Stocks: {summary.get('bullish_count', 0):,} ({summary.get('bullish_percentage', 0):.1f}%)")
    print(f"   Bearish Stocks: {summary.get('bearish_count', 0):,} ({summary.get('bearish_percentage', 0):.1f}%)")
    print(f"   Neutral Stocks: {summary.get('neutral_count', 0):,} ({summary.get('neutral_percentage', 0):.1f}%)")
    print(f"   Bull/Bear Ratio: {summary.get('bullish_bearish_ratio', 0):.2f}")
    
    # Strong signals
    print(f"\n🔥 STRONG SIGNALS:")
    print(f"   Very Bullish (≥5): {summary.get('strong_bullish_count', 0):,}")
    print(f"   Very Bearish (≤-5): {summary.get('strong_bearish_count', 0):,}")
    
    # Market breadth score
    score, interpretation = calculate_market_breadth_score(summary)
    print(f"\n🎯 MARKET BREADTH SCORE:")
    print(f"   Score: {score}/100")
    print(f"   Interpretation: {interpretation}")
    
    # Rating distribution
    if distribution:
        print(f"\n📋 RATING DISTRIBUTION:")
        print(f"{'Category':<30} {'Count':<8} {'Avg Rating':<12}")
        print(f"{'-'*52}")
        for dist in distribution:
            category = dist['rating_category']
            count = dist['stock_count']
            avg_rating = dist['avg_rating']
            print(f"{category:<30} {count:<8} {avg_rating:<12.1f}")


def main():
    """Main demonstration of market breadth analysis with date selection."""
    print("🚀 MARKET BREADTH ANALYSIS - DATE SELECTION DEMO")
    print("Using Direct Database Connection")
    
    try:
        # Test database connection
        engine = create_db_engine()
        with engine.connect() as conn:
            result = conn.execute(text("SELECT COUNT(*) FROM trend_analysis")).fetchone()
            print(f"✅ Database connected successfully - {result[0]:,} trend analysis records")
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return
    
    # 1. Get available dates
    print(f"\n📅 GETTING AVAILABLE ANALYSIS DATES...")
    try:
        available_dates = get_available_dates_direct(engine)
        
        if available_dates:
            print(f"✅ Found {len(available_dates)} available analysis dates")
            print("📋 Recent dates available:")
            for i, date_obj in enumerate(available_dates[:10]):
                print(f"   {i+1:2d}. {date_obj}")
        else:
            print("❌ No analysis dates found")
            return
        
        # 2. Analyze latest date
        print(f"\n🔍 1. LATEST MARKET BREADTH ANALYSIS")
        latest_data = analyze_market_breadth_for_date()
        print_market_breadth_analysis(latest_data, "Latest Available")
        
        # 3. Analyze a specific date (e.g., 3 days ago)
        if len(available_dates) > 3:
            specific_date = available_dates[3]
            specific_date_str = specific_date.strftime('%Y-%m-%d')
            print(f"\n🔍 2. SPECIFIC DATE ANALYSIS")
            specific_data = analyze_market_breadth_for_date(specific_date_str)
            print_market_breadth_analysis(specific_data, specific_date_str)
            
            # 4. Compare latest vs specific date
            if latest_data.get('success') and specific_data.get('success'):
                print(f"\n🔄 3. COMPARISON: Latest vs {specific_date_str}")
                print("=" * 70)
                
                latest_summary = latest_data['summary']
                specific_summary = specific_data['summary']
                
                # Compare key metrics
                metrics = [
                    ('Total Stocks', 'total_stocks'),
                    ('Bullish %', 'bullish_percentage'),
                    ('Bearish %', 'bearish_percentage'),
                    ('Avg Rating', 'market_avg_rating'),
                    ('Bull/Bear Ratio', 'bullish_bearish_ratio')
                ]
                
                print(f"{'Metric':<20} {'Latest':<15} {specific_date_str:<15} {'Change':<15}")
                print("-" * 65)
                
                for label, key in metrics:
                    latest_val = latest_summary.get(key, 0)
                    specific_val = specific_summary.get(key, 0)
                    change = latest_val - specific_val
                    
                    if key in ['bullish_percentage', 'bearish_percentage']:
                        latest_str = f"{latest_val:.1f}%"
                        specific_str = f"{specific_val:.1f}%"
                        change_str = f"{change:+.1f}%"
                    elif key in ['market_avg_rating', 'bullish_bearish_ratio']:
                        latest_str = f"{latest_val:.2f}"
                        specific_str = f"{specific_val:.2f}"
                        change_str = f"{change:+.2f}"
                    else:
                        latest_str = f"{latest_val:,}"
                        specific_str = f"{specific_val:,}"
                        change_str = f"{change:+d}"
                    
                    print(f"{label:<20} {latest_str:<15} {specific_str:<15} {change_str:<15}")
                
                # Calculate and compare breadth scores
                latest_score, latest_interp = calculate_market_breadth_score(latest_summary)
                specific_score, specific_interp = calculate_market_breadth_score(specific_summary)
                score_change = latest_score - specific_score
                
                print(f"\n🎯 BREADTH SCORE COMPARISON:")
                print(f"   Latest: {latest_score}/100 ({latest_interp})")
                print(f"   {specific_date_str}: {specific_score}/100 ({specific_interp})")
                print(f"   Change: {score_change:+.1f} points")
                
                if score_change > 5:
                    print("   📈 Significant improvement in market breadth")
                elif score_change < -5:
                    print("   📉 Significant deterioration in market breadth")
                else:
                    print("   ➡️ Market breadth relatively stable")
        
        print(f"\n✅ Market breadth analysis demonstration completed successfully!")
        print("\n💡 KEY FEATURES DEMONSTRATED:")
        print("   ✓ Latest market breadth analysis")
        print("   ✓ Historical date selection")
        print("   ✓ Date-to-date comparison")
        print("   ✓ Market breadth scoring")
        print("   ✓ Rating distribution analysis")
        
    except Exception as e:
        print(f"❌ Error during analysis: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()