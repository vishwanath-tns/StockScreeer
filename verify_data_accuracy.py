#!/usr/bin/env python3
"""
Comprehensive Data Accuracy Verification for Sectoral Analysis
This script performs detailed mathematical and logical validation of sectoral analysis results.
"""

import sys
import os
from datetime import datetime, timedelta
import pandas as pd
from typing import Dict, List, Tuple

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.market_breadth_service import get_sectoral_breadth, get_sectoral_analysis_dates, get_engine

class SectoralDataVerifier:
    """Comprehensive verification system for sectoral analysis data accuracy."""
    
    def __init__(self):
        self.engine = None
        self.verification_results = {}
        self.analysis_date = "2025-11-14"  # Default to latest available
        
    def connect_to_database(self):
        """Establish database connection."""
        try:
            self.engine = get_engine()
            print("✅ Database connection established")
            return True
        except Exception as e:
            print(f"❌ Database connection failed: {e}")
            return False
    
    def verify_data_accuracy_complete(self):
        """Complete data accuracy verification workflow."""
        print("🔍 SECTORAL DATA ACCURACY VERIFICATION")
        print("=" * 70)
        
        if not self.connect_to_database():
            print("❌ Cannot proceed without database connection")
            return False
        
        # Get latest available date
        try:
            dates = get_sectoral_analysis_dates()
            if dates:
                self.analysis_date = dates[-1]
                print(f"📅 Using analysis date: {self.analysis_date}")
            else:
                print("❌ No analysis dates found")
                return False
        except Exception as e:
            print(f"❌ Error getting dates: {e}")
            return False
        
        # Run all verification tests
        results = {
            "mathematical_accuracy": self.verify_mathematical_accuracy(),
            "data_consistency": self.verify_data_consistency(), 
            "sector_classification": self.verify_sector_classification(),
            "trend_logic": self.verify_trend_logic(),
            "cross_validation": self.verify_cross_validation()
        }
        
        # Generate final report
        self.generate_accuracy_report(results)
        return all(results.values())
    
    def verify_mathematical_accuracy(self):
        """Verify mathematical calculations are correct."""
        print("\n🧮 STEP 1: Mathematical Accuracy Verification")
        print("-" * 50)
        
        try:
            # Test with NIFTY-PHARMA (top performer from screenshot)
            result = get_sectoral_breadth("NIFTY-PHARMA", analysis_date=self.analysis_date)
            
            if result.get('status') != 'success':
                print(f"❌ Failed to get NIFTY-PHARMA data: {result.get('message')}")
                return False
            
            summary = result.get('summary', {})
            
            # Extract values
            total_stocks = summary.get('total_stocks', 0)
            bullish_count = summary.get('bullish_count', 0)
            bearish_count = summary.get('bearish_count', 0)
            bullish_percent = summary.get('bullish_percent', 0)
            bearish_percent = summary.get('bearish_percent', 0)
            
            print(f"📊 NIFTY-PHARMA Raw Data:")
            print(f"   Total Stocks: {total_stocks}")
            print(f"   Bullish Count: {bullish_count}")
            print(f"   Bearish Count: {bearish_count}")
            print(f"   Bullish %: {bullish_percent:.1f}%")
            print(f"   Bearish %: {bearish_percent:.1f}%")
            
            # Mathematical verification
            errors = []
            
            # Test 1: Count totals
            if bullish_count + bearish_count != total_stocks:
                errors.append(f"Count mismatch: {bullish_count} + {bearish_count} != {total_stocks}")
            
            # Test 2: Percentage calculations
            expected_bullish_pct = (bullish_count / total_stocks * 100) if total_stocks > 0 else 0
            expected_bearish_pct = (bearish_count / total_stocks * 100) if total_stocks > 0 else 0
            
            if abs(bullish_percent - expected_bullish_pct) > 0.1:
                errors.append(f"Bullish % wrong: got {bullish_percent:.1f}%, expected {expected_bullish_pct:.1f}%")
            
            if abs(bearish_percent - expected_bearish_pct) > 0.1:
                errors.append(f"Bearish % wrong: got {bearish_percent:.1f}%, expected {expected_bearish_pct:.1f}%")
            
            # Test 3: Percentage total
            if abs((bullish_percent + bearish_percent) - 100) > 0.1:
                errors.append(f"Percentages don't add to 100%: {bullish_percent + bearish_percent:.1f}%")
            
            if errors:
                print("❌ Mathematical errors found:")
                for error in errors:
                    print(f"   • {error}")
                return False
            else:
                print("✅ All mathematical calculations are correct")
                print(f"   • Count totals match: {bullish_count} + {bearish_count} = {total_stocks}")
                print(f"   • Percentages accurate: {bullish_percent:.1f}% + {bearish_percent:.1f}% = 100%")
                return True
                
        except Exception as e:
            print(f"❌ Mathematical verification error: {e}")
            return False
    
    def verify_data_consistency(self):
        """Verify data consistency across multiple sectors."""
        print("\n📊 STEP 2: Data Consistency Verification")
        print("-" * 50)
        
        test_sectors = ["NIFTY-PHARMA", "NIFTY-BANK", "NIFTY-IT", "NIFTY-AUTO"]
        sector_data = {}
        
        try:
            for sector in test_sectors:
                result = get_sectoral_breadth(sector, analysis_date=self.analysis_date)
                
                if result.get('status') == 'success':
                    sector_data[sector] = result.get('summary', {})
                    print(f"✅ {sector}: {sector_data[sector].get('total_stocks', 0)} stocks")
                else:
                    print(f"❌ {sector}: Failed to get data")
            
            if len(sector_data) < 2:
                print("❌ Insufficient data for consistency check")
                return False
            
            # Consistency checks
            consistency_issues = []
            
            # Check stock counts are reasonable
            for sector, data in sector_data.items():
                total = data.get('total_stocks', 0)
                if total < 5 or total > 50:
                    consistency_issues.append(f"{sector} has unusual stock count: {total}")
            
            # Check percentage ranges are realistic
            for sector, data in sector_data.items():
                bullish_pct = data.get('bullish_percent', 0)
                if bullish_pct < 0 or bullish_pct > 100:
                    consistency_issues.append(f"{sector} has invalid bullish %: {bullish_pct}")
            
            # Check for extreme outliers
            bullish_percentages = [data.get('bullish_percent', 0) for data in sector_data.values()]
            if bullish_percentages:
                min_pct, max_pct = min(bullish_percentages), max(bullish_percentages)
                if max_pct - min_pct > 80:  # More than 80% spread might indicate data issue
                    consistency_issues.append(f"Extreme spread in bullish %: {min_pct:.1f}% to {max_pct:.1f}%")
            
            if consistency_issues:
                print("⚠️ Consistency issues found:")
                for issue in consistency_issues:
                    print(f"   • {issue}")
                return False
            else:
                print("✅ Data consistency verified across sectors")
                return True
                
        except Exception as e:
            print(f"❌ Consistency verification error: {e}")
            return False
    
    def verify_sector_classification(self):
        """Verify stocks are correctly classified into sectors."""
        print("\n🏷️ STEP 3: Sector Classification Verification")
        print("-" * 50)
        
        try:
            # Direct database query to verify sector mappings
            query = """
            SELECT 
                index_name,
                COUNT(DISTINCT symbol) as total_symbols,
                GROUP_CONCAT(DISTINCT symbol ORDER BY symbol LIMIT 5) as sample_symbols
            FROM nse_index_constituents 
            WHERE index_name IN ('NIFTY-PHARMA', 'NIFTY-BANK', 'NIFTY-IT')
            GROUP BY index_name
            ORDER BY index_name
            """
            
            with self.engine.connect() as conn:
                df = pd.read_sql(query, conn)
                
                if df.empty:
                    print("❌ No sector classification data found")
                    return False
                
                print("✅ Sector classification verification:")
                classification_valid = True
                
                for _, row in df.iterrows():
                    sector = row['index_name']
                    count = row['total_symbols']
                    samples = row['sample_symbols']
                    
                    print(f"   🏷️ {sector}: {count} stocks")
                    print(f"      📄 Sample symbols: {samples}")
                    
                    # Verify count matches sectoral analysis
                    result = get_sectoral_breadth(sector, analysis_date=self.analysis_date, use_latest=False)
                    if result.get('status') == 'success':
                        analysis_count = result.get('summary', {}).get('total_stocks', 0)
                        if analysis_count != count:
                            print(f"      ⚠️ Count mismatch: DB has {count}, analysis shows {analysis_count}")
                            classification_valid = False
                        else:
                            print(f"      ✅ Count matches: {analysis_count}")
                    
                return classification_valid
                
        except Exception as e:
            print(f"❌ Classification verification error: {e}")
            return False
    
    def verify_trend_logic(self):
        """Verify trend rating logic is sound."""
        print("\n📈 STEP 4: Trend Logic Verification")
        print("-" * 50)
        
        try:
            # Get individual stock data for NIFTY-PHARMA to verify trend logic
            query = """
            SELECT 
                t.symbol,
                t.trend_rating,
                t.daily_trend,
                t.weekly_trend,
                t.close_price,
                t.sma_20,
                t.sma_50,
                n.index_name
            FROM trend_analysis t
            JOIN nse_index_constituents n ON t.symbol = n.symbol
            WHERE n.index_name = 'NIFTY-PHARMA'
            AND t.analysis_date = %s
            ORDER BY t.trend_rating DESC
            LIMIT 10
            """
            
            with self.engine.connect() as conn:
                df = pd.read_sql(query, conn, params=[self.analysis_date])
                
                if df.empty:
                    print("❌ No individual stock data found for trend verification")
                    return False
                
                print("✅ Trend logic verification for NIFTY-PHARMA:")
                logic_valid = True
                
                for _, row in df.iterrows():
                    symbol = row['symbol']
                    rating = row['trend_rating']
                    daily = row['daily_trend']
                    weekly = row['weekly_trend']
                    close = row['close_price']
                    sma20 = row['sma_20']
                    sma50 = row['sma_50']
                    
                    # Logical checks
                    issues = []
                    
                    # Check if bullish rating aligns with price/SMA relationship
                    if rating >= 3:  # Bullish
                        if close < sma20 and close < sma50:
                            issues.append("High rating but price below both SMAs")
                    elif rating <= 2:  # Bearish
                        if close > sma20 and close > sma50:
                            issues.append("Low rating but price above both SMAs")
                    
                    # Check daily/weekly trend consistency
                    if daily == 'Uptrend' and weekly == 'Downtrend' and rating >= 4:
                        issues.append("High rating despite weekly downtrend")
                    
                    if issues:
                        print(f"      ⚠️ {symbol}: Rating {rating}, Issues: {', '.join(issues)}")
                        logic_valid = False
                    else:
                        trend_emoji = "🟢" if rating >= 3 else "🔴"
                        print(f"      {trend_emoji} {symbol}: Rating {rating}, {daily}/{weekly}")
                
                return logic_valid
                
        except Exception as e:
            print(f"❌ Trend logic verification error: {e}")
            return False
    
    def verify_cross_validation(self):
        """Cross-validate results with alternative calculation method."""
        print("\n🔄 STEP 5: Cross-Validation with Alternative Method")
        print("-" * 50)
        
        try:
            # Alternative calculation: Direct aggregation
            query = """
            SELECT 
                n.index_name,
                COUNT(*) as total_stocks,
                SUM(CASE WHEN t.trend_rating >= 3 THEN 1 ELSE 0 END) as bullish_count_alt,
                SUM(CASE WHEN t.trend_rating <= 2 THEN 1 ELSE 0 END) as bearish_count_alt,
                ROUND(SUM(CASE WHEN t.trend_rating >= 3 THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 1) as bullish_pct_alt
            FROM trend_analysis t
            JOIN nse_index_constituents n ON t.symbol = n.symbol
            WHERE n.index_name IN ('NIFTY-PHARMA', 'NIFTY-BANK') 
            AND t.analysis_date = %s
            GROUP BY n.index_name
            """
            
            with self.engine.connect() as conn:
                df = pd.read_sql(query, conn, params=[self.analysis_date])
                
                if df.empty:
                    print("❌ No data for cross-validation")
                    return False
                
                print("✅ Cross-validation results:")
                validation_passed = True
                
                for _, row in df.iterrows():
                    sector = row['index_name']
                    alt_bullish_pct = row['bullish_pct_alt']
                    alt_total = row['total_stocks']
                    
                    # Get original analysis result
                    original = get_sectoral_breadth(sector, analysis_date=self.analysis_date)
                    
                    if original.get('status') == 'success':
                        orig_bullish_pct = original.get('summary', {}).get('bullish_percent', 0)
                        orig_total = original.get('summary', {}).get('total_stocks', 0)
                        
                        # Compare results
                        pct_diff = abs(alt_bullish_pct - orig_bullish_pct)
                        count_diff = abs(alt_total - orig_total)
                        
                        if pct_diff <= 0.1 and count_diff == 0:
                            print(f"   ✅ {sector}: {orig_bullish_pct:.1f}% ↔ {alt_bullish_pct:.1f}% (Match)")
                        else:
                            print(f"   ❌ {sector}: {orig_bullish_pct:.1f}% ↔ {alt_bullish_pct:.1f}% (Mismatch)")
                            validation_passed = False
                    
                return validation_passed
                
        except Exception as e:
            print(f"❌ Cross-validation error: {e}")
            return False
    
    def generate_accuracy_report(self, results: Dict[str, bool]):
        """Generate final accuracy assessment report."""
        print("\n" + "=" * 70)
        print("📋 DATA ACCURACY VERIFICATION REPORT")
        print("=" * 70)
        
        total_tests = len(results)
        passed_tests = sum(results.values())
        accuracy_score = (passed_tests / total_tests) * 100
        
        print(f"\n🎯 OVERALL ACCURACY SCORE: {accuracy_score:.1f}% ({passed_tests}/{total_tests} tests passed)")
        
        print(f"\n📊 DETAILED RESULTS:")
        for test_name, passed in results.items():
            status = "✅ PASSED" if passed else "❌ FAILED"
            test_display = test_name.replace('_', ' ').title()
            print(f"   {status} - {test_display}")
        
        print(f"\n💡 INTERPRETATION:")
        if accuracy_score >= 90:
            print("   🎉 EXCELLENT: Your sectoral analysis data is highly accurate and reliable")
            print("   ✅ Safe to use for trading and investment decisions")
        elif accuracy_score >= 70:
            print("   ✅ GOOD: Your sectoral analysis data is mostly accurate")
            print("   ⚠️ Review failed tests and consider data quality improvements")
        else:
            print("   ❌ NEEDS ATTENTION: Significant data accuracy issues detected")
            print("   🔧 Review data sources, calculations, and database integrity")
        
        print(f"\n🔍 RECOMMENDATIONS:")
        if not results.get('mathematical_accuracy', True):
            print("   • Check percentage calculation formulas in market_breadth_service.py")
        if not results.get('data_consistency', True):
            print("   • Verify data quality in trend_analysis table")
        if not results.get('sector_classification', True):
            print("   • Review nse_index_constituents table mappings")
        if not results.get('trend_logic', True):
            print("   • Validate trend rating algorithm logic")
        if not results.get('cross_validation', True):
            print("   • Compare with external data sources")
        
        print("\n" + "=" * 70)

def main():
    """Run complete data accuracy verification."""
    verifier = SectoralDataVerifier()
    success = verifier.verify_data_accuracy_complete()
    
    if success:
        print("🎉 Data accuracy verification completed successfully!")
    else:
        print("⚠️ Data accuracy issues detected. Please review the report above.")
    
    return success

if __name__ == "__main__":
    main()