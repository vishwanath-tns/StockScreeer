#!/usr/bin/env python3
"""
Manual Data Accuracy Checker for Sectoral Analysis
Simple tool to manually verify specific sectors and dates.
"""

import sys
import os
import pandas as pd
from datetime import datetime

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.market_breadth_service import get_sectoral_breadth, get_engine

def manual_sector_check(sector_name, analysis_date):
    """Manually verify a specific sector's data accuracy."""
    print(f"\n🔍 MANUAL VERIFICATION: {sector_name} on {analysis_date}")
    print("-" * 60)
    
    try:
        engine = get_engine()
        
        # Step 1: Get sectoral analysis result
        print("📊 Step 1: Getting sectoral analysis result...")
        result = get_sectoral_breadth(sector_name, analysis_date=analysis_date)
        
        if result.get('status') != 'success':
            print(f"❌ Analysis failed: {result.get('message')}")
            return False
        
        summary = result.get('summary', {})
        print(f"✅ Analysis Result:")
        print(f"   Total Stocks: {summary.get('total_stocks', 0)}")
        print(f"   Bullish Count: {summary.get('bullish_count', 0)}")
        print(f"   Bearish Count: {summary.get('bearish_count', 0)}")
        print(f"   Bullish %: {summary.get('bullish_percent', 0):.1f}%")
        print(f"   Bearish %: {summary.get('bearish_percent', 0):.1f}%")
        
        # Step 2: Manual database verification
        print(f"\n🗄️ Step 2: Manual database verification...")
        query = """
        SELECT 
            t.symbol,
            t.trend_rating,
            t.daily_trend,
            t.weekly_trend,
            t.close_price,
            CASE 
                WHEN t.trend_rating >= 3 THEN 'Bullish'
                ELSE 'Bearish' 
            END as classification
        FROM trend_analysis t
        JOIN nse_index_constituents n ON t.symbol = n.symbol
        WHERE n.index_name = %s
        AND t.analysis_date = %s
        ORDER BY t.trend_rating DESC
        """
        
        with engine.connect() as conn:
            df = pd.read_sql(query, conn, params=[sector_name, analysis_date])
            
            if df.empty:
                print("❌ No database records found")
                return False
            
            # Manual calculations
            total_manual = len(df)
            bullish_manual = len(df[df['trend_rating'] >= 3])
            bearish_manual = len(df[df['trend_rating'] <= 2])
            bullish_pct_manual = (bullish_manual / total_manual * 100) if total_manual > 0 else 0
            bearish_pct_manual = (bearish_manual / total_manual * 100) if total_manual > 0 else 0
            
            print(f"✅ Manual Database Calculation:")
            print(f"   Total Stocks: {total_manual}")
            print(f"   Bullish Count: {bullish_manual} (rating >= 3)")
            print(f"   Bearish Count: {bearish_manual} (rating <= 2)")
            print(f"   Bullish %: {bullish_pct_manual:.1f}%")
            print(f"   Bearish %: {bearish_pct_manual:.1f}%")
            
            # Step 3: Comparison
            print(f"\n⚖️ Step 3: Accuracy Check...")
            total_match = summary.get('total_stocks', 0) == total_manual
            bullish_match = summary.get('bullish_count', 0) == bullish_manual
            bearish_match = summary.get('bearish_count', 0) == bearish_manual
            bullish_pct_match = abs(summary.get('bullish_percent', 0) - bullish_pct_manual) < 0.1
            bearish_pct_match = abs(summary.get('bearish_percent', 0) - bearish_pct_manual) < 0.1
            
            all_match = all([total_match, bullish_match, bearish_match, bullish_pct_match, bearish_pct_match])
            
            if all_match:
                print("✅ PERFECT MATCH: All calculations are accurate!")
            else:
                print("❌ DISCREPANCY DETECTED:")
                if not total_match:
                    print(f"   • Total count: Analysis={summary.get('total_stocks', 0)}, Manual={total_manual}")
                if not bullish_match:
                    print(f"   • Bullish count: Analysis={summary.get('bullish_count', 0)}, Manual={bullish_manual}")
                if not bearish_match:
                    print(f"   • Bearish count: Analysis={summary.get('bearish_count', 0)}, Manual={bearish_manual}")
                if not bullish_pct_match:
                    print(f"   • Bullish %: Analysis={summary.get('bullish_percent', 0):.1f}%, Manual={bullish_pct_manual:.1f}%")
                if not bearish_pct_match:
                    print(f"   • Bearish %: Analysis={summary.get('bearish_percent', 0):.1f}%, Manual={bearish_pct_manual:.1f}%")
            
            # Step 4: Show individual stock details
            print(f"\n📋 Step 4: Individual Stock Details (Top 10):")
            print(f"{'Symbol':<15} {'Rating':<8} {'Daily':<12} {'Weekly':<12} {'Class':<10}")
            print("-" * 65)
            
            for _, row in df.head(10).iterrows():
                rating_color = "🟢" if row['trend_rating'] >= 3 else "🔴"
                print(f"{row['symbol']:<15} {rating_color}{row['trend_rating']:<7} {row['daily_trend']:<12} {row['weekly_trend']:<12} {row['classification']:<10}")
            
            return all_match
            
    except Exception as e:
        print(f"❌ Verification error: {e}")
        return False

def quick_spot_check():
    """Quick spot check of current results."""
    print("🎯 QUICK SPOT CHECK OF SECTORAL DATA ACCURACY")
    print("=" * 60)
    
    # Test sectors from your screenshot
    test_cases = [
        ("NIFTY-PHARMA", "2025-11-14"),      # Best performer
        ("NIFTY-BANK", "2025-11-14"),       # Mid performer  
        ("NIFTY-CONSUMER-DURABLES", "2025-11-14")  # Worst performer
    ]
    
    results = []
    for sector, date in test_cases:
        print(f"\n{'='*20} {sector} {'='*20}")
        accurate = manual_sector_check(sector, date)
        results.append((sector, accurate))
    
    # Summary
    print(f"\n🎯 SPOT CHECK SUMMARY")
    print("=" * 40)
    
    passed = sum(1 for _, accurate in results if accurate)
    total = len(results)
    
    for sector, accurate in results:
        status = "✅ ACCURATE" if accurate else "❌ INACCURATE"
        print(f"{status} - {sector}")
    
    accuracy_rate = (passed / total * 100) if total > 0 else 0
    print(f"\n📊 Overall Accuracy: {accuracy_rate:.1f}% ({passed}/{total} sectors)")
    
    if accuracy_rate >= 90:
        print("🎉 EXCELLENT: Your data is highly accurate!")
    elif accuracy_rate >= 70:
        print("✅ GOOD: Minor issues may exist")
    else:
        print("⚠️ NEEDS REVIEW: Significant accuracy problems detected")
    
    return accuracy_rate >= 70

if __name__ == "__main__":
    quick_spot_check()