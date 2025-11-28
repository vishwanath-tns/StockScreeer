#!/usr/bin/env python3
"""
Test script for Market Depth Analysis with Date Range functionality.
This script demonstrates the new date range analysis features.
"""

from datetime import datetime, timedelta
from services.market_breadth_service import (
    get_market_depth_analysis_for_range, 
    calculate_market_depth_trends
)

def test_date_range_analysis():
    """Test the date range analysis functionality."""
    print("🧪 Testing Market Depth Analysis - Date Range")
    print("=" * 50)
    
    # Test with last 7 days
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=7)
    
    print(f"📅 Testing date range: {start_date} to {end_date}")
    print("🔄 Fetching market depth analysis...")
    
    try:
        # Get range analysis
        range_data = get_market_depth_analysis_for_range(start_date, end_date)
        
        if not range_data.get('success', False):
            print(f"❌ Analysis failed: {range_data.get('error', 'Unknown error')}")
            return
        
        # Calculate trends
        print("📈 Calculating trend analysis...")
        trend_analysis = calculate_market_depth_trends(range_data['daily_analysis'])
        
        # Display results
        summary = range_data.get('summary', {})
        daily_analysis = range_data.get('daily_analysis', [])
        
        print(f"\n📊 ANALYSIS RESULTS")
        print(f"📈 Trading Days: {len(daily_analysis)}")
        print(f"📊 Avg Stocks: {summary.get('avg_total_stocks', 0):,.0f}")
        print(f"📈 Avg Bullish %: {summary.get('avg_bullish_percentage', 0):.1f}%")
        print(f"📉 Avg Bearish %: {summary.get('avg_bearish_percentage', 0):.1f}%")
        print(f"⭐ Avg Rating: {summary.get('avg_market_rating', 0):.2f}")
        
        print(f"\n📈 TREND ANALYSIS")
        if trend_analysis:
            print(f"📈 Bullish Trend: {trend_analysis.get('bullish_trend_direction', 'N/A')}")
            print(f"📉 Bearish Trend: {trend_analysis.get('bearish_trend_direction', 'N/A')}")
            print(f"⭐ Rating Trend: {trend_analysis.get('rating_trend_direction', 'N/A')}")
            print(f"📊 Volatility: {trend_analysis.get('volatility_assessment', 'N/A')}")
        
        print(f"\n🎯 EXTREMES")
        max_bullish_day = summary.get('max_bullish_day', {})
        min_bullish_day = summary.get('min_bullish_day', {})
        print(f"📈 Max Bullish %: {max_bullish_day.get('percentage', 0):.1f}%")
        print(f"📉 Min Bullish %: {min_bullish_day.get('percentage', 0):.1f}%")
        print(f"⭐ Volatility: {summary.get('market_volatility', 0):.1f}")
        print(f"📈 Sentiment Trend: {summary.get('sentiment_trend', 0):.1f}")
        
        print(f"\n✅ Date range analysis completed successfully!")
        
    except Exception as e:
        print(f"❌ Error during analysis: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_date_range_analysis()