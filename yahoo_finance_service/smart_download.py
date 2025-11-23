#!/usr/bin/env python3
"""
Yahoo Finance Download with Smart Duplicate Prevention
- Checks existing data before downloading
- Downloads only missing date ranges
- Prevents unnecessary API calls
"""

import sys
import os

# Add parent directory to path
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parent_dir)

from sync_bhav_gui import engine
from sqlalchemy import text
from datetime import datetime, date, timedelta
import yfinance as yf

def check_existing_data(symbol, start_date, end_date):
    """
    Check what data already exists for a symbol in the given date range
    Returns: (has_data, min_date, max_date, total_records, missing_ranges)
    """
    conn = engine().connect()
    
    # Get existing data info
    result = conn.execute(text("""
        SELECT 
            MIN(date) as min_date,
            MAX(date) as max_date,
            COUNT(*) as record_count
        FROM yfinance_daily_quotes
        WHERE symbol = :symbol
        AND date BETWEEN :start_date AND :end_date
    """), {'symbol': symbol, 'start_date': start_date, 'end_date': end_date})
    
    row = result.fetchone()
    has_data = row[2] > 0 if row else False
    min_date = row[0] if row else None
    max_date = row[1] if row else None
    record_count = row[2] if row else 0
    
    # Calculate expected trading days (approximate - excludes weekends)
    days_diff = (end_date - start_date).days + 1
    weekend_days = sum(1 for i in range(days_diff) if (start_date + timedelta(days=i)).weekday() >= 5)
    expected_days = days_diff - weekend_days
    
    # Check for missing ranges
    missing_ranges = []
    
    if not has_data:
        missing_ranges.append((start_date, end_date))
    else:
        # Check if there's a gap at the beginning
        if min_date and min_date > start_date:
            missing_ranges.append((start_date, min_date - timedelta(days=1)))
        
        # Check if there's a gap at the end
        if max_date and max_date < end_date:
            missing_ranges.append((max_date + timedelta(days=1), end_date))
        
        # Check for gaps in the middle (simplified - checks for large gaps)
        if min_date and max_date:
            result = conn.execute(text("""
                SELECT date, 
                       LAG(date) OVER (ORDER BY date) as prev_date
                FROM yfinance_daily_quotes
                WHERE symbol = :symbol
                AND date BETWEEN :start_date AND :end_date
                ORDER BY date
            """), {'symbol': symbol, 'start_date': start_date, 'end_date': end_date})
            
            for row in result:
                current_date = row[0]
                prev_date = row[1]
                
                if prev_date:
                    gap_days = (current_date - prev_date).days
                    # If gap is more than 7 days (accounting for weekends and holidays)
                    if gap_days > 7:
                        missing_ranges.append((prev_date + timedelta(days=1), current_date - timedelta(days=1)))
    
    conn.close()
    
    coverage_pct = (record_count / expected_days * 100) if expected_days > 0 else 0
    
    return {
        'has_data': has_data,
        'min_date': min_date,
        'max_date': max_date,
        'record_count': record_count,
        'expected_days': expected_days,
        'coverage_pct': coverage_pct,
        'missing_ranges': missing_ranges
    }

def smart_download(symbol, start_date, end_date, force=False):
    """
    Smart download that avoids duplicates
    - Checks existing data first
    - Downloads only missing ranges if force=False
    - Downloads everything if force=True (will update existing records)
    """
    
    print(f"\n{'='*80}")
    print(f"SMART DOWNLOAD: {symbol}")
    print(f"{'='*80}")
    print(f"Requested Range: {start_date} to {end_date}")
    
    if not force:
        # Check existing data
        print("\n🔍 Checking existing data...")
        info = check_existing_data(symbol, start_date, end_date)
        
        print(f"\nExisting Data:")
        print(f"  Records: {info['record_count']}")
        print(f"  Coverage: {info['coverage_pct']:.1f}%")
        
        if info['has_data']:
            print(f"  Date Range: {info['min_date']} to {info['max_date']}")
        
        if info['coverage_pct'] >= 95:
            print(f"\n✅ Data is {info['coverage_pct']:.1f}% complete - No download needed!")
            print("   Use --force flag to re-download and update existing records.")
            return True
        
        if info['missing_ranges']:
            print(f"\n⚠️  Found {len(info['missing_ranges'])} missing date ranges:")
            for i, (start, end) in enumerate(info['missing_ranges'], 1):
                days = (end - start).days + 1
                print(f"  {i}. {start} to {end} ({days} days)")
            
            print("\n📥 Downloading missing data only...")
            # Download each missing range
            for start, end in info['missing_ranges']:
                download_range(symbol, start, end)
        else:
            print("\n✅ No missing data - coverage is good!")
            return True
    else:
        print("\n🔄 FORCE MODE: Downloading/updating all data...")
        download_range(symbol, start_date, end_date)
    
    print(f"\n{'='*80}\n")
    return True

def download_range(symbol, start_date, end_date):
    """Download data for a specific date range"""
    try:
        print(f"  Downloading {symbol} from {start_date} to {end_date}...")
        
        # Download from Yahoo Finance
        ticker = yf.Ticker(symbol)
        data = ticker.history(start=start_date, end=end_date, interval="1d")
        
        if data.empty:
            print(f"  ⚠️  No data returned from Yahoo Finance")
            return False
        
        # Insert into database
        conn = engine().connect()
        trans = conn.begin()
        
        try:
            inserted = 0
            updated = 0
            
            for date_val, row in data.iterrows():
                result = conn.execute(text("""
                    INSERT INTO yfinance_daily_quotes
                    (symbol, date, open, high, low, close, volume, adj_close, 
                     timeframe, source, created_at)
                    VALUES (:symbol, :date, :open, :high, :low, :close, :volume, 
                            :adj_close, 'Daily', 'Yahoo Finance', NOW())
                    ON DUPLICATE KEY UPDATE
                        open = VALUES(open),
                        high = VALUES(high),
                        low = VALUES(low),
                        close = VALUES(close),
                        volume = VALUES(volume),
                        adj_close = VALUES(adj_close),
                        updated_at = CURRENT_TIMESTAMP
                """), {
                    'symbol': symbol,
                    'date': date_val.date(),
                    'open': float(row['Open']),
                    'high': float(row['High']),
                    'low': float(row['Low']),
                    'close': float(row['Close']),
                    'volume': int(row['Volume']),
                    'adj_close': float(row['Close'])  # Using Close as Adj Close
                })
                
                # Check if row was inserted or updated
                if result.rowcount == 1:
                    inserted += 1
                elif result.rowcount == 2:  # ON DUPLICATE KEY UPDATE returns 2
                    updated += 1
            
            trans.commit()
            print(f"  ✅ Success: {inserted} new, {updated} updated")
            
            conn.close()
            return True
            
        except Exception as e:
            trans.rollback()
            print(f"  ❌ Error inserting data: {e}")
            conn.close()
            return False
    
    except Exception as e:
        print(f"  ❌ Download failed: {e}")
        return False

def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Smart Yahoo Finance downloader with duplicate prevention'
    )
    parser.add_argument('symbol', help='Stock symbol (e.g., RELIANCE.NS)')
    parser.add_argument('--start', required=True, help='Start date (YYYY-MM-DD)')
    parser.add_argument('--end', required=True, help='End date (YYYY-MM-DD)')
    parser.add_argument('--force', action='store_true', 
                       help='Force re-download even if data exists')
    
    args = parser.parse_args()
    
    try:
        start_date = datetime.strptime(args.start, '%Y-%m-%d').date()
        end_date = datetime.strptime(args.end, '%Y-%m-%d').date()
        
        smart_download(args.symbol, start_date, end_date, args.force)
        
    except ValueError as e:
        print(f"❌ Invalid date format: {e}")
        print("   Use format: YYYY-MM-DD")
        return 1
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == '__main__':
    sys.exit(main())
