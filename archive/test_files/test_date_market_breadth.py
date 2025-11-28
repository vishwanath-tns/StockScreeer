"""
Test Market Breadth Analysis for Selected Date

This script demonstrates how to perform market breadth analysis 
using trend ratings on a specific selected date.
"""

import sys
import os
from datetime import datetime, date, timedelta

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.market_breadth_service import (
    get_current_market_breadth,
    get_market_breadth_for_date,
    get_available_dates,
    calculate_market_breadth_score,
    get_breadth_alerts,
    get_stocks_in_category
)


def print_market_breadth_summary(data, analysis_date):
    """Print a formatted summary of market breadth data."""
    print(f"\n{'='*60}")
    print(f"MARKET BREADTH ANALYSIS FOR {analysis_date}")
    print(f"{'='*60}")
    
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
    
    # Alerts
    alerts = get_breadth_alerts(summary)
    if alerts:
        print(f"\n⚠️  MARKET ALERTS:")
        for alert in alerts:
            severity_icon = "🚨" if alert['severity'] == 'high' else "ℹ️"
            print(f"   {severity_icon} {alert['title']}: {alert['message']}")
    else:
        print(f"\n✅ No alerts - Market conditions are normal")
    
    # Rating distribution
    if distribution:
        print(f"\n📋 RATING DISTRIBUTION:")
        for dist in distribution:
            category = dist['rating_category']
            count = dist['stock_count']
            avg_rating = dist['avg_rating']
            print(f"   {category}: {count:,} stocks (avg: {avg_rating:.1f})")


def analyze_specific_date(target_date):
    """Analyze market breadth for a specific date."""
    print(f"\n🔍 ANALYZING MARKET BREADTH FOR {target_date}")
    print("-" * 50)
    
    # Convert string date to proper format if needed
    if isinstance(target_date, str):
        try:
            # Try parsing different date formats
            for fmt in ['%Y-%m-%d', '%d-%m-%Y', '%m/%d/%Y']:
                try:
                    parsed_date = datetime.strptime(target_date, fmt).date()
                    break
                except ValueError:
                    continue
            else:
                print(f"❌ Error: Could not parse date '{target_date}'. Use format: YYYY-MM-DD")
                return
        except Exception as e:
            print(f"❌ Error parsing date: {e}")
            return
    else:
        parsed_date = target_date
    
    # Get market breadth data for the specific date
    data = get_market_breadth_for_date(parsed_date)
    
    # Print summary
    print_market_breadth_summary(data, parsed_date)
    
    return data


def compare_dates(date1, date2):
    """Compare market breadth between two dates."""
    print(f"\n🔄 COMPARING MARKET BREADTH: {date1} vs {date2}")
    print("=" * 60)
    
    # Get data for both dates
    data1 = get_market_breadth_for_date(date1)
    data2 = get_market_breadth_for_date(date2)
    
    if not data1.get('success') or not data2.get('success'):
        print("❌ Error: Could not retrieve data for one or both dates")
        return
    
    summary1 = data1.get('summary', {})
    summary2 = data2.get('summary', {})
    
    # Compare key metrics
    print(f"\n📊 KEY METRICS COMPARISON:")
    print(f"{'Metric':<25} {'Date 1':<15} {'Date 2':<15} {'Change':<15}")
    print("-" * 70)
    
    metrics = [
        ('Total Stocks', 'total_stocks'),
        ('Bullish %', 'bullish_percentage'),
        ('Bearish %', 'bearish_percentage'),
        ('Avg Rating', 'market_avg_rating'),
        ('Bull/Bear Ratio', 'bullish_bearish_ratio')
    ]
    
    for label, key in metrics:
        val1 = summary1.get(key, 0)
        val2 = summary2.get(key, 0)
        
        if key in ['bullish_percentage', 'bearish_percentage']:
            change = val2 - val1
            change_str = f"{change:+.1f}%"
        elif key == 'market_avg_rating':
            change = val2 - val1
            change_str = f"{change:+.2f}"
        elif key == 'bullish_bearish_ratio':
            change = val2 - val1
            change_str = f"{change:+.2f}"
        else:
            change = val2 - val1
            change_str = f"{change:+d}"
        
        # Format values
        if key in ['bullish_percentage', 'bearish_percentage']:
            val1_str = f"{val1:.1f}%"
            val2_str = f"{val2:.1f}%"
        elif key in ['market_avg_rating', 'bullish_bearish_ratio']:
            val1_str = f"{val1:.2f}"
            val2_str = f"{val2:.2f}"
        else:
            val1_str = f"{val1:,}"
            val2_str = f"{val2:,}"
        
        print(f"{label:<25} {val1_str:<15} {val2_str:<15} {change_str:<15}")
    
    # Calculate and compare breadth scores
    score1, interp1 = calculate_market_breadth_score(summary1)
    score2, interp2 = calculate_market_breadth_score(summary2)
    score_change = score2 - score1
    
    print(f"\n🎯 BREADTH SCORE COMPARISON:")
    print(f"   {date1}: {score1}/100 ({interp1})")
    print(f"   {date2}: {score2}/100 ({interp2})")
    print(f"   Change: {score_change:+.1f} points")


def get_top_stocks_in_category(category_name, trade_date=None, top_n=10):
    """Get top stocks in a specific category."""
    print(f"\n🏆 TOP {top_n} STOCKS IN CATEGORY: {category_name}")
    if trade_date:
        print(f"📅 Date: {trade_date}")
    print("-" * 60)
    
    # Get stocks in category
    result = get_stocks_in_category(category_name, trade_date=trade_date, limit=top_n)
    
    if not result.get('success', False):
        print(f"❌ Error: {result.get('error', 'Unknown error')}")
        return
    
    stocks = result.get('stocks', [])
    if not stocks:
        print("📭 No stocks found in this category")
        return
    
    print(f"{'Symbol':<12} {'Rating':<8} {'Price':<10} {'Change %':<10} {'Daily':<8} {'Weekly':<8} {'Monthly':<8}")
    print("-" * 75)
    
    for stock in stocks[:top_n]:
        symbol = stock.get('symbol', 'N/A')[:10]
        rating = f"{stock.get('trend_rating', 0):.1f}"
        price = f"₹{stock.get('close_price', 0):.1f}"
        change_pct = f"{stock.get('daily_change_pct', 0):.1f}%"
        daily = stock.get('daily_trend', 'N/A')[:6]
        weekly = stock.get('weekly_trend', 'N/A')[:6]
        monthly = stock.get('monthly_trend', 'N/A')[:6]
        
        print(f"{symbol:<12} {rating:<8} {price:<10} {change_pct:<10} {daily:<8} {weekly:<8} {monthly:<8}")


def main():
    """Main function to demonstrate market breadth analysis for selected dates."""
    print("🚀 MARKET BREADTH ANALYSIS - DATE SELECTION DEMO")
    print("=" * 60)
    
    # 1. Get available dates
    print("\n📅 GETTING AVAILABLE ANALYSIS DATES...")
    available_dates = get_available_dates(30)  # Last 30 dates
    
    if available_dates:
        print(f"✅ Found {len(available_dates)} available analysis dates")
        print("📋 Recent dates available:")
        for i, date_obj in enumerate(available_dates[:10]):
            print(f"   {i+1}. {date_obj}")
    else:
        print("❌ No analysis dates found")
        return
    
    # 2. Analyze latest date
    print("\n" + "="*60)
    print("🔍 1. LATEST MARKET BREADTH ANALYSIS")
    latest_data = get_current_market_breadth()
    print_market_breadth_summary(latest_data, "Latest Available")
    
    # 3. Analyze a specific date (e.g., 5 days ago)
    if len(available_dates) > 5:
        specific_date = available_dates[5]  # 5 days ago
        print("\n" + "="*60)
        print(f"🔍 2. SPECIFIC DATE ANALYSIS")
        specific_data = analyze_specific_date(specific_date)
        
        # 4. Compare latest vs specific date
        if specific_data and specific_data.get('success'):
            latest_date = available_dates[0]
            compare_dates(specific_date, latest_date)
    
    # 5. Show top stocks in different categories for latest date
    categories = [
        "Very Bullish (8 to 10)",
        "Bullish (5 to 7.9)",
        "Very Bearish (-10 to -8)",
        "Bearish (-7.9 to -5)"
    ]
    
    print("\n" + "="*60)
    print("🏆 TOP STOCKS BY CATEGORY (LATEST DATE)")
    
    for category in categories:
        get_top_stocks_in_category(category, top_n=5)
    
    # 6. Interactive date selection example
    print("\n" + "="*60)
    print("🔧 INTERACTIVE DATE SELECTION EXAMPLE")
    print("=" * 60)
    
    print("\n💡 You can analyze any specific date like this:")
    print("   # Example 1: Using date string")
    print("   analyze_specific_date('2025-01-15')")
    print("   ")
    print("   # Example 2: Using date object")
    print("   from datetime import date")
    print("   analyze_specific_date(date(2025, 1, 15))")
    print("   ")
    print("   # Example 3: Compare two dates")
    print("   compare_dates('2025-01-10', '2025-01-15')")
    
    print(f"\n✅ Demo completed successfully!")


def interactive_date_analysis():
    """Interactive function to analyze user-selected dates."""
    print("\n🎮 INTERACTIVE DATE ANALYSIS")
    print("=" * 40)
    
    # Get available dates
    available_dates = get_available_dates(30)
    if not available_dates:
        print("❌ No analysis dates available")
        return
    
    print("📅 Available dates (last 30):")
    for i, date_obj in enumerate(available_dates[:15]):
        print(f"   {i+1:2d}. {date_obj}")
    
    try:
        while True:
            print("\n" + "-"*40)
            print("OPTIONS:")
            print("1. Analyze specific date")
            print("2. Compare two dates")
            print("3. Show available dates")
            print("4. Exit")
            
            choice = input("\nEnter your choice (1-4): ").strip()
            
            if choice == '1':
                date_input = input("Enter date (YYYY-MM-DD) or number from list: ").strip()
                try:
                    if date_input.isdigit():
                        # User selected number from list
                        idx = int(date_input) - 1
                        if 0 <= idx < len(available_dates):
                            selected_date = available_dates[idx]
                            analyze_specific_date(selected_date)
                        else:
                            print("❌ Invalid number")
                    else:
                        # User entered date string
                        analyze_specific_date(date_input)
                except Exception as e:
                    print(f"❌ Error: {e}")
            
            elif choice == '2':
                date1 = input("Enter first date (YYYY-MM-DD): ").strip()
                date2 = input("Enter second date (YYYY-MM-DD): ").strip()
                try:
                    compare_dates(date1, date2)
                except Exception as e:
                    print(f"❌ Error: {e}")
            
            elif choice == '3':
                print("📅 Available dates:")
                for i, date_obj in enumerate(available_dates):
                    print(f"   {i+1:2d}. {date_obj}")
            
            elif choice == '4':
                print("👋 Goodbye!")
                break
            
            else:
                print("❌ Invalid choice")
                
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")


if __name__ == "__main__":
    # Run main demo
    main()
    
    # Uncomment to run interactive mode
    # interactive_date_analysis()