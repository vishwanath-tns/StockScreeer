"""
Quick test of market breadth analysis with date selection
"""
import sys
sys.path.append('d:/MyProjects/StockScreeer')

from services.market_breadth_service import (
    get_current_market_breadth, 
    get_market_breadth_for_date, 
    get_available_dates,
    calculate_market_breadth_score
)
from datetime import date

def test_market_breadth():
    print("🚀 TESTING MARKET BREADTH ANALYSIS WITH DATE SELECTION")
    print("=" * 60)
    
    # Test 1: Get current market breadth
    print("\n1. Testing current market breadth...")
    current = get_current_market_breadth()
    if current.get('success'):
        summary = current['summary']
        analysis_date = summary.get('analysis_date')
        total_stocks = summary.get('total_stocks', 0)
        bullish_pct = summary.get('bullish_percentage', 0)
        bearish_pct = summary.get('bearish_percentage', 0)
        avg_rating = summary.get('market_avg_rating', 0)
        
        print(f"✅ Current analysis successful for {analysis_date}")
        print(f"   Total stocks: {total_stocks:,}")
        print(f"   Bullish %: {bullish_pct:.1f}%")
        print(f"   Bearish %: {bearish_pct:.1f}%")
        print(f"   Market avg rating: {avg_rating:.2f}")
        
        # Calculate breadth score
        score, interpretation = calculate_market_breadth_score(summary)
        print(f"   Breadth Score: {score}/100 ({interpretation})")
    else:
        error_msg = current.get('error', 'Unknown error')
        print(f"❌ Current analysis failed: {error_msg}")
    
    # Test 2: Get available dates
    print("\n2. Getting available dates...")
    dates = get_available_dates(10)
    if dates:
        print(f"✅ Found {len(dates)} available dates")
        print("   Recent dates:")
        for i, dt in enumerate(dates[:5]):
            print(f"   {i+1}. {dt}")
    else:
        print("❌ No dates found")
        return
    
    # Test 3: Analyze specific date
    if len(dates) > 1:
        specific_date = dates[1]  # Get second most recent date
        print(f"\n3. Testing specific date analysis for {specific_date}...")
        specific = get_market_breadth_for_date(specific_date)
        if specific.get('success'):
            summary = specific['summary']
            total_stocks = summary.get('total_stocks', 0)
            bullish_pct = summary.get('bullish_percentage', 0)
            avg_rating = summary.get('market_avg_rating', 0)
            
            print("✅ Specific date analysis successful")
            print(f"   Total stocks: {total_stocks:,}")
            print(f"   Bullish %: {bullish_pct:.1f}%")
            print(f"   Market avg rating: {avg_rating:.2f}")
            
            # Calculate breadth score
            score, interpretation = calculate_market_breadth_score(summary)
            print(f"   Breadth Score: {score}/100 ({interpretation})")
        else:
            error_msg = specific.get('error', 'Unknown error')
            print(f"❌ Specific date analysis failed: {error_msg}")
    
    # Test 4: Compare latest vs older date
    if len(dates) > 2:
        print(f"\n4. Comparing latest vs {dates[2]}...")
        latest_data = get_market_breadth_for_date(dates[0])
        older_data = get_market_breadth_for_date(dates[2])
        
        if latest_data.get('success') and older_data.get('success'):
            latest_summary = latest_data['summary']
            older_summary = older_data['summary']
            
            latest_bullish = latest_summary.get('bullish_percentage', 0)
            older_bullish = older_summary.get('bullish_percentage', 0)
            bullish_change = latest_bullish - older_bullish
            
            latest_rating = latest_summary.get('market_avg_rating', 0)
            older_rating = older_summary.get('market_avg_rating', 0)
            rating_change = latest_rating - older_rating
            
            print(f"✅ Comparison successful:")
            print(f"   Bullish % change: {bullish_change:+.1f}% ({older_bullish:.1f}% → {latest_bullish:.1f}%)")
            print(f"   Rating change: {rating_change:+.2f} ({older_rating:.2f} → {latest_rating:.2f})")
            
            if bullish_change > 0:
                print("   📈 Market breadth improved")
            elif bullish_change < 0:
                print("   📉 Market breadth weakened")
            else:
                print("   ➡️ Market breadth unchanged")
    
    print(f"\n✅ Market breadth analysis test completed successfully!")

if __name__ == "__main__":
    test_market_breadth()