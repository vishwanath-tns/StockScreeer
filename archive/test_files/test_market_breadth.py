"""
Test Market Breadth Analysis

This script tests the market breadth functionality with actual data.
"""

import sys
import os

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.market_breadth_service import (
    get_current_market_breadth,
    get_market_breadth_trend,
    get_breadth_categories,
    get_stocks_in_category,
    calculate_market_breadth_score,
    get_breadth_alerts
)


def test_market_breadth_analysis():
    """Test all market breadth analysis functions."""
    print("=" * 60)
    print("MARKET BREADTH ANALYSIS TEST")
    print("=" * 60)
    
    # Test 1: Current Market Breadth
    print("\n1. Current Market Breadth Analysis")
    print("-" * 40)
    
    current = get_current_market_breadth()
    print(f"Success: {current['success']}")
    
    if current['success']:
        summary = current['summary']
        print(f"Analysis Date: {current['analysis_date']}")
        print(f"Total Stocks: {current['total_analyzed']}")
        print(f"Bullish Stocks: {summary.get('bullish_count', 0)} ({summary.get('bullish_percentage', 0)}%)")
        print(f"Bearish Stocks: {summary.get('bearish_count', 0)} ({summary.get('bearish_percentage', 0)}%)")
        print(f"Neutral Stocks: {summary.get('neutral_count', 0)} ({summary.get('neutral_percentage', 0)}%)")
        print(f"Average Market Rating: {summary.get('market_avg_rating', 0)}")
        print(f"Bull/Bear Ratio: {summary.get('bullish_bearish_ratio', 0)}")
        
        # Calculate breadth score
        score, interpretation = calculate_market_breadth_score(summary)
        print(f"Market Breadth Score: {score} ({interpretation})")
        
        # Get alerts
        alerts = get_breadth_alerts(summary)
        print(f"Active Alerts: {len(alerts)}")
        for alert in alerts:
            print(f"  - {alert['type'].upper()}: {alert['title']}")
        
        # Show rating distribution
        print("\nRating Distribution:")
        for dist in current['rating_distribution']:
            print(f"  {dist['rating_category']}: {dist['stock_count']} stocks (avg: {dist['avg_rating']})")
    else:
        print(f"Error: {current.get('error', 'Unknown error')}")
    
    # Test 2: Trend Analysis
    print("\n2. Market Breadth Trend Analysis (30 days)")
    print("-" * 40)
    
    trend = get_market_breadth_trend(30)
    print(f"Success: {trend['success']}")
    
    if trend['success']:
        print(f"Days Analyzed: {trend['days_analyzed']}")
        trend_analysis = trend['trend_analysis']
        print(f"Bullish Trend: {trend_analysis['bullish_trend']}")
        print(f"Rating Trend: {trend_analysis['rating_trend']}")
        print(f"Breadth Momentum: {trend_analysis['breadth_momentum']}")
        print(f"Average Bullish %: {trend_analysis['avg_bullish_percentage']}")
        print(f"Average Bearish %: {trend_analysis['avg_bearish_percentage']}")
        print(f"Average Market Rating: {trend_analysis['avg_market_rating']}")
        
        # Show recent trend data
        print("\nRecent Trend Data (last 5 days):")
        recent_data = trend['trend_data'][:5]
        for day in recent_data:
            print(f"  {day['trade_date']}: Bullish {day['bullish_percentage']}%, Rating {day['market_avg_rating']}")
    else:
        print(f"Error: {trend.get('error', 'Unknown error')}")
    
    # Test 3: Category Analysis
    print("\n3. Stock Category Analysis")
    print("-" * 40)
    
    categories = get_breadth_categories()
    print(f"Available Categories: {len(categories)}")
    
    # Test each category
    for i, category in enumerate(categories):
        if i < 3:  # Test first 3 categories only
            print(f"\nTesting Category: {category['name']}")
            result = get_stocks_in_category(category['name'], limit=5)
            
            if result['success']:
                print(f"  Stocks Found: {result['total_found']}")
                print(f"  Sample Stocks:")
                for stock in result['stocks'][:3]:
                    print(f"    {stock['symbol']}: Rating {stock['trend_rating']:.1f}, Price ₹{stock['close_price']:.1f}")
            else:
                print(f"  Error: {result.get('error', 'Unknown error')}")
    
    print("\n" + "=" * 60)
    print("MARKET BREADTH ANALYSIS TEST COMPLETED")
    print("=" * 60)


if __name__ == "__main__":
    test_market_breadth_analysis()