"""
Data Completeness Analysis for NSE Equity and RSI Tables
========================================================

This script checks for missing data in:
1. nse_equity_bhavcopy_full
2. nse_rsi_daily 
3. nse_rsi_divergences
4. Other RSI-related tables

Excludes:
- Weekends (Saturday, Sunday)
- Trading holidays from trading_holidays table
"""

import sys
import os

# Add parent directory to path for imports
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(parent_dir)

import reporting_adv_decl as rad
import pandas as pd
from sqlalchemy import text
from datetime import datetime, timedelta
import numpy as np

def check_trading_holidays_table():
    """Check the structure and data of trading_holidays table"""
    print("🔍 CHECKING TRADING HOLIDAYS TABLE")
    print("=" * 50)
    
    engine = rad.engine()
    with engine.connect() as conn:
        # Check table structure
        try:
            structure_result = conn.execute(text("DESCRIBE trading_holidays"))
            print("📋 Table Structure:")
            print("-" * 30)
            for row in structure_result.fetchall():
                print(f"  {row[0]:<20} {row[1]:<15}")
            
            # Get sample data
            sample_result = conn.execute(text("""
                SELECT * FROM trading_holidays 
                ORDER BY holiday_date DESC 
                LIMIT 10
            """))
            
            print("\n📅 Sample Holiday Data (Latest 10):")
            print("-" * 40)
            for row in sample_result.fetchall():
                print(f"  {row}")
                
            # Get count and date range
            stats_result = conn.execute(text("""
                SELECT 
                    COUNT(*) as total_holidays,
                    MIN(holiday_date) as earliest_holiday,
                    MAX(holiday_date) as latest_holiday
                FROM trading_holidays
            """))
            
            stats = stats_result.fetchone()
            print(f"\n📊 Holiday Statistics:")
            print(f"  Total Holidays: {stats[0]}")
            print(f"  Date Range: {stats[1]} to {stats[2]}")
            
            return True
            
        except Exception as e:
            print(f"❌ Error checking trading_holidays table: {e}")
            return False

def get_trading_days_range(start_date, end_date):
    """Get all expected trading days between two dates, excluding weekends and holidays"""
    engine = rad.engine()
    
    with engine.connect() as conn:
        # Get holidays in the date range
        holidays_result = conn.execute(text("""
            SELECT holiday_date FROM trading_holidays 
            WHERE holiday_date BETWEEN :start_date AND :end_date
        """), {"start_date": start_date, "end_date": end_date})
        
        holidays = [row[0] for row in holidays_result.fetchall()]
        
        # Generate all trading days (excluding weekends and holidays)
        trading_days = []
        current_date = start_date
        
        while current_date <= end_date:
            # Skip weekends (5=Saturday, 6=Sunday)
            if current_date.weekday() < 5:  # Monday=0, Friday=4
                if current_date not in holidays:
                    trading_days.append(current_date)
            current_date += timedelta(days=1)
            
        return trading_days, holidays

def check_nse_equity_data():
    """Check for missing data in nse_equity_bhavcopy_full"""
    print("\n🔍 CHECKING NSE EQUITY BHAVCOPY DATA")
    print("=" * 50)
    
    engine = rad.engine()
    
    with engine.connect() as conn:
        # Get date range of available data
        range_result = conn.execute(text("""
            SELECT 
                MIN(trade_date) as earliest_date,
                MAX(trade_date) as latest_date,
                COUNT(DISTINCT trade_date) as total_days
            FROM nse_equity_bhavcopy_full
        """))
        
        date_range = range_result.fetchone()
        print(f"📅 Available Data Range: {date_range[0]} to {date_range[1]}")
        print(f"📊 Total Trading Days with Data: {date_range[2]}")
        
        # Get all unique dates with data
        dates_result = conn.execute(text("""
            SELECT DISTINCT trade_date 
            FROM nse_equity_bhavcopy_full 
            ORDER BY trade_date
        """))
        
        available_dates = [row[0] for row in dates_result.fetchall()]
        
        # Get expected trading days
        start_date = date_range[0]
        end_date = date_range[1]
        expected_dates, holidays = get_trading_days_range(start_date, end_date)
        
        print(f"📈 Expected Trading Days: {len(expected_dates)}")
        print(f"🏖️  Holidays Excluded: {len(holidays)}")
        
        # Find missing dates
        available_set = set(available_dates)
        expected_set = set(expected_dates)
        
        missing_dates = sorted(expected_set - available_set)
        extra_dates = sorted(available_set - expected_set)
        
        print(f"\n❌ Missing Trading Days: {len(missing_dates)}")
        if missing_dates:
            print("   Missing Dates:")
            for date in missing_dates:
                day_name = date.strftime("%A")
                print(f"   📅 {date} ({day_name})")
        
        print(f"\n⚠️  Extra/Unexpected Days: {len(extra_dates)}")
        if extra_dates:
            print("   Extra Dates:")
            for date in extra_dates:
                day_name = date.strftime("%A")
                print(f"   📅 {date} ({day_name})")
                
        return missing_dates, extra_dates

def check_rsi_tables():
    """Check for missing data in RSI-related tables"""
    print("\n🔍 CHECKING RSI TABLES DATA")
    print("=" * 50)
    
    engine = rad.engine()
    
    # Tables to check
    rsi_tables = [
        'nse_rsi_daily',
        'nse_rsi_divergences',
        'sma50_counts'  # SMA related data
    ]
    
    table_results = {}
    
    for table in rsi_tables:
        print(f"\n📊 Checking {table}...")
        
        with engine.connect() as conn:
            try:
                # Get date range and count
                if table == 'nse_rsi_divergences':
                    # This table uses signal_date
                    range_result = conn.execute(text(f"""
                        SELECT 
                            MIN(signal_date) as earliest_date,
                            MAX(signal_date) as latest_date,
                            COUNT(DISTINCT signal_date) as total_days,
                            COUNT(*) as total_records
                        FROM {table}
                    """))
                else:
                    # These tables use trade_date
                    range_result = conn.execute(text(f"""
                        SELECT 
                            MIN(trade_date) as earliest_date,
                            MAX(trade_date) as latest_date,
                            COUNT(DISTINCT trade_date) as total_days,
                            COUNT(*) as total_records
                        FROM {table}
                    """))
                
                range_data = range_result.fetchone()
                
                if range_data[0]:  # If data exists
                    print(f"   📅 Date Range: {range_data[0]} to {range_data[1]}")
                    print(f"   📊 Trading Days: {range_data[2]}")
                    print(f"   📋 Total Records: {range_data[3]}")
                    
                    # Get actual dates
                    if table == 'nse_rsi_divergences':
                        dates_result = conn.execute(text(f"""
                            SELECT DISTINCT signal_date 
                            FROM {table} 
                            ORDER BY signal_date
                        """))
                    else:
                        dates_result = conn.execute(text(f"""
                            SELECT DISTINCT trade_date 
                            FROM {table} 
                            ORDER BY trade_date
                        """))
                    
                    available_dates = [row[0] for row in dates_result.fetchall()]
                    
                    # Calculate missing dates
                    start_date = range_data[0]
                    end_date = range_data[1]
                    expected_dates, holidays = get_trading_days_range(start_date, end_date)
                    
                    missing_dates = sorted(set(expected_dates) - set(available_dates))
                    
                    print(f"   ❌ Missing Days: {len(missing_dates)}")
                    if missing_dates and len(missing_dates) <= 20:  # Only show if not too many
                        for date in missing_dates:
                            day_name = date.strftime("%A")
                            print(f"      📅 {date} ({day_name})")
                    elif missing_dates:
                        print(f"      📅 First few: {missing_dates[:5]}...")
                        print(f"      📅 Last few: {missing_dates[-5:]}...")
                    
                    table_results[table] = {
                        'available_days': range_data[2],
                        'total_records': range_data[3],
                        'missing_dates': missing_dates,
                        'date_range': (range_data[0], range_data[1])
                    }
                    
                else:
                    print(f"   ❌ No data found in {table}")
                    table_results[table] = None
                    
            except Exception as e:
                print(f"   ❌ Error checking {table}: {e}")
                table_results[table] = None
    
    return table_results

def generate_summary_report(bhav_missing, bhav_extra, rsi_results):
    """Generate a comprehensive summary report"""
    print("\n" + "=" * 60)
    print("📋 DATA COMPLETENESS SUMMARY REPORT")
    print("=" * 60)
    
    print(f"\n🏢 NSE EQUITY BHAVCOPY DATA:")
    print(f"   ❌ Missing Trading Days: {len(bhav_missing)}")
    print(f"   ⚠️  Extra/Unexpected Days: {len(bhav_extra)}")
    
    print(f"\n📊 RSI & RELATED TABLES:")
    for table, result in rsi_results.items():
        if result:
            print(f"   📈 {table}:")
            print(f"      📅 Available Days: {result['available_days']}")
            print(f"      📋 Total Records: {result['total_records']:,}")
            print(f"      ❌ Missing Days: {len(result['missing_dates'])}")
        else:
            print(f"   ❌ {table}: No data or error")
    
    # Highlight critical issues
    print(f"\n🚨 CRITICAL ISSUES:")
    critical_issues = []
    
    if len(bhav_missing) > 0:
        critical_issues.append(f"BHAV data missing for {len(bhav_missing)} trading days")
    
    for table, result in rsi_results.items():
        if result and len(result['missing_dates']) > 5:  # More than 5 missing days
            critical_issues.append(f"{table} missing {len(result['missing_dates'])} days of data")
    
    if critical_issues:
        for issue in critical_issues:
            print(f"   🔴 {issue}")
    else:
        print(f"   ✅ No critical data gaps found!")
    
    # October 13th specific check
    oct_13_2025 = datetime(2025, 10, 13).date()
    print(f"\n🔍 OCTOBER 13TH, 2025 SPECIFIC CHECK:")
    
    if oct_13_2025 in bhav_missing:
        print(f"   ❌ October 13th data is missing from BHAV table")
    else:
        print(f"   ✅ October 13th data is present in BHAV table")
    
    for table, result in rsi_results.items():
        if result:
            if oct_13_2025 in result['missing_dates']:
                print(f"   ❌ October 13th data is missing from {table}")
            else:
                print(f"   ✅ October 13th data is present in {table}")

def main():
    """Main function to run all data completeness checks"""
    print("🔍 NSE DATA COMPLETENESS ANALYSIS")
    print("=" * 60)
    print(f"📅 Analysis Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Check trading holidays table
    holidays_ok = check_trading_holidays_table()
    
    if not holidays_ok:
        print("❌ Cannot proceed without trading holidays data")
        return
    
    # Check BHAV data
    bhav_missing, bhav_extra = check_nse_equity_data()
    
    # Check RSI tables
    rsi_results = check_rsi_tables()
    
    # Generate summary
    generate_summary_report(bhav_missing, bhav_extra, rsi_results)

if __name__ == "__main__":
    main()