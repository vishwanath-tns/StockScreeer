"""
Generate detailed missing data report to file
"""

import sys
import os

# Add parent directory to path for imports
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(parent_dir)

import reporting_adv_decl as rad
from sqlalchemy import text
from datetime import datetime, timedelta

def generate_detailed_report():
    """Generate a detailed missing data report and save to file"""
    
    output_file = f"data_completeness_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    
    engine = rad.engine()
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("NSE DATA COMPLETENESS DETAILED REPORT\n")
        f.write("=" * 60 + "\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        
        # Get all missing dates from BHAV table
        with engine.connect() as conn:
            # Get the date range and missing dates
            f.write("1. NSE EQUITY BHAVCOPY MISSING DATES\n")
            f.write("-" * 40 + "\n")
            
            # Get available dates
            available_result = conn.execute(text("""
                SELECT DISTINCT trade_date 
                FROM nse_equity_bhavcopy_full 
                ORDER BY trade_date
            """))
            available_dates = {row[0] for row in available_result.fetchall()}
            
            # Get holidays
            holidays_result = conn.execute(text("""
                SELECT holiday_date FROM trading_holidays 
                WHERE holiday_date >= '2024-01-01' AND holiday_date <= '2025-12-31'
            """))
            holidays = {row[0] for row in holidays_result.fetchall()}
            
            # Find all missing dates in the range
            start_date = min(available_dates)
            end_date = max(available_dates)
            
            missing_dates = []
            current_date = start_date
            
            while current_date <= end_date:
                # Skip weekends and holidays
                if current_date.weekday() < 5 and current_date not in holidays:
                    if current_date not in available_dates:
                        missing_dates.append(current_date)
                current_date += timedelta(days=1)
            
            f.write(f"Date Range Analyzed: {start_date} to {end_date}\n")
            f.write(f"Total Missing Trading Days: {len(missing_dates)}\n\n")
            
            # Group missing dates by year and month for better readability
            missing_by_month = {}
            for date in missing_dates:
                month_key = f"{date.year}-{date.month:02d}"
                if month_key not in missing_by_month:
                    missing_by_month[month_key] = []
                missing_by_month[month_key].append(date)
            
            for month_key, dates in sorted(missing_by_month.items()):
                f.write(f"\n{month_key}:\n")
                for date in sorted(dates):
                    day_name = date.strftime("%A")
                    f.write(f"  {date.strftime('%Y-%m-%d')} ({day_name})\n")
            
            # Check if October 13, 2025 is a legitimate trading day
            oct_13_2025 = datetime(2025, 10, 13).date()
            f.write(f"\nOCTOBER 13, 2025 ANALYSIS:\n")
            f.write(f"Date: {oct_13_2025.strftime('%Y-%m-%d (%A)')}\n")
            f.write(f"Is Weekend: {'Yes' if oct_13_2025.weekday() >= 5 else 'No'}\n")
            f.write(f"Is Holiday: {'Yes' if oct_13_2025 in holidays else 'No'}\n")
            f.write(f"Should Have Data: {'No' if oct_13_2025.weekday() >= 5 or oct_13_2025 in holidays else 'Yes'}\n")
            f.write(f"Data Present: {'Yes' if oct_13_2025 in available_dates else 'No'}\n")
            
            # RSI Tables Analysis
            f.write(f"\n\n2. RSI TABLES MISSING DATES\n")
            f.write("-" * 40 + "\n")
            
            # nse_rsi_daily missing dates
            rsi_available_result = conn.execute(text("""
                SELECT DISTINCT trade_date 
                FROM nse_rsi_daily 
                ORDER BY trade_date
            """))
            rsi_available_dates = {row[0] for row in rsi_available_result.fetchall()}
            
            rsi_start = min(rsi_available_dates)
            rsi_end = max(rsi_available_dates)
            
            rsi_missing = []
            current_date = rsi_start
            
            while current_date <= rsi_end:
                if current_date.weekday() < 5 and current_date not in holidays:
                    if current_date not in rsi_available_dates:
                        rsi_missing.append(current_date)
                current_date += timedelta(days=1)
            
            f.write(f"\nRSI Daily Table Missing Dates:\n")
            f.write(f"Date Range: {rsi_start} to {rsi_end}\n")
            f.write(f"Total Missing: {len(rsi_missing)}\n")
            
            rsi_by_month = {}
            for date in rsi_missing:
                month_key = f"{date.year}-{date.month:02d}"
                if month_key not in rsi_by_month:
                    rsi_by_month[month_key] = []
                rsi_by_month[month_key].append(date)
            
            for month_key, dates in sorted(rsi_by_month.items()):
                f.write(f"\n{month_key}:\n")
                for date in sorted(dates):
                    day_name = date.strftime("%A")
                    f.write(f"  {date.strftime('%Y-%m-%d')} ({day_name})\n")
            
            # RSI Divergences analysis
            div_dates_result = conn.execute(text("""
                SELECT DISTINCT signal_date 
                FROM nse_rsi_divergences 
                ORDER BY signal_date
            """))
            div_dates = [row[0] for row in div_dates_result.fetchall()]
            
            f.write(f"\n\nRSI Divergences Table:\n")
            f.write(f"Date Range: {min(div_dates)} to {max(div_dates)}\n")
            f.write(f"Total Signal Days: {len(div_dates)}\n")
            f.write(f"Note: RSI divergences are calculated periodically, not daily.\n")
            f.write(f"Missing days are expected as signals are generated only when divergences are detected.\n")
            
            # Critical missing dates
            f.write(f"\n\n3. CRITICAL ANALYSIS\n")
            f.write("-" * 40 + "\n")
            
            # Recent missing dates (last 30 days)
            thirty_days_ago = datetime.now().date() - timedelta(days=30)
            recent_missing = [d for d in missing_dates if d >= thirty_days_ago]
            
            if recent_missing:
                f.write(f"\nRecent Missing Dates (Last 30 days):\n")
                for date in recent_missing:
                    f.write(f"  {date.strftime('%Y-%m-%d (%A)')}\n")
            else:
                f.write(f"\nNo missing dates in the last 30 days.\n")
            
            # Compare BHAV vs RSI consistency
            common_missing = set(missing_dates) & set(rsi_missing)
            f.write(f"\nConsistency Check:\n")
            f.write(f"BHAV missing dates: {len(missing_dates)}\n")
            f.write(f"RSI missing dates: {len(rsi_missing)}\n")
            f.write(f"Common missing dates: {len(common_missing)}\n")
            
            if len(common_missing) == len(missing_dates) == len(rsi_missing):
                f.write("✅ BHAV and RSI data gaps are consistent (same missing dates)\n")
            else:
                f.write("⚠️  BHAV and RSI data gaps are inconsistent\n")
            
            # Recommendations
            f.write(f"\n\n4. RECOMMENDATIONS\n")
            f.write("-" * 40 + "\n")
            f.write("1. Investigate why October 13, 2025 data is missing\n")
            f.write("2. Review data import processes for the identified missing dates\n")
            f.write("3. Check if missing dates correspond to unscheduled market closures\n")
            f.write("4. Verify trading calendar against actual market trading days\n")
            f.write("5. Consider backfilling missing data if sources are available\n")
            
    print(f"📄 Detailed report saved to: {output_file}")
    return output_file

if __name__ == "__main__":
    report_file = generate_detailed_report()
    print(f"✅ Report generation completed: {report_file}")