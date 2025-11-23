#!/usr/bin/env python3
"""
Download 5 years of Yahoo Finance data for all Nifty 500 stocks
With smart duplicate prevention and progress tracking
"""

import sys
import os
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parent_dir)

from sync_bhav_gui import engine
from sqlalchemy import text
from datetime import datetime, date, timedelta
import yfinance as yf
import time

def get_nifty500_symbols():
    """Get all Nifty 500 symbols with their Yahoo Finance mappings"""
    conn = engine().connect()
    
    result = conn.execute(text("""
        SELECT DISTINCT n.symbol, m.yahoo_symbol, m.is_verified
        FROM nse_index_constituents n
        JOIN nse_yahoo_symbol_map m ON n.symbol = m.nse_symbol
        WHERE n.index_id = 25
        AND m.is_active = TRUE
        ORDER BY n.symbol
    """))
    
    symbols = [(row[0], row[1], row[2]) for row in result.fetchall()]
    conn.close()
    
    return symbols

def check_existing_data(symbol, start_date, end_date):
    """Quick check for existing data"""
    conn = engine().connect()
    
    result = conn.execute(text("""
        SELECT COUNT(*) as count,
               MIN(date) as min_date,
               MAX(date) as max_date
        FROM yfinance_daily_quotes
        WHERE symbol = :symbol
        AND date BETWEEN :start_date AND :end_date
    """), {'symbol': symbol, 'start_date': start_date, 'end_date': end_date})
    
    row = result.fetchone()
    conn.close()
    
    count = row[0] if row else 0
    min_date = row[1] if row else None
    max_date = row[2] if row else None
    
    # Calculate expected trading days (approximate)
    days_diff = (end_date - start_date).days + 1
    weekend_days = sum(1 for i in range(days_diff) if (start_date + timedelta(days=i)).weekday() >= 5)
    expected = days_diff - weekend_days
    coverage = (count / expected * 100) if expected > 0 else 0
    
    return count, coverage, min_date, max_date

def download_symbol_data(yahoo_symbol, start_date, end_date):
    """Download data for a single symbol with robust error handling"""
    conn = None
    trans = None
    
    try:
        # Download from Yahoo Finance
        ticker = yf.Ticker(yahoo_symbol)
        data = ticker.history(start=start_date, end=end_date, interval="1d")
        
        if data.empty:
            return 0, 0, "No data from Yahoo"
        
        # Prepare data for bulk insert
        records = []
        for date_val, row in data.iterrows():
            records.append({
                'symbol': yahoo_symbol,
                'date': date_val.date(),
                'open': float(row['Open']),
                'high': float(row['High']),
                'low': float(row['Low']),
                'close': float(row['Close']),
                'volume': int(row['Volume']),
                'adj_close': float(row['Close'])
            })
        
        # Bulk insert with fresh connection
        conn = engine().connect()
        trans = conn.begin()
        
        inserted = 0
        updated = 0
        
        # Batch insert in chunks of 100
        chunk_size = 100
        for i in range(0, len(records), chunk_size):
            chunk = records[i:i+chunk_size]
            
            for record in chunk:
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
                """), record)
                
                if result.rowcount == 1:
                    inserted += 1
                elif result.rowcount == 2:
                    updated += 1
        
        trans.commit()
        return inserted, updated, None
            
    except Exception as e:
        if trans:
            try:
                trans.rollback()
            except:
                pass
        return 0, 0, str(e)
    
    finally:
        if conn:
            try:
                conn.close()
            except:
                pass

def download_all_nifty500(start_date, end_date, skip_if_complete=True, rate_limit=0.5, start_from=1):
    """
    Download data for all Nifty 500 stocks
    
    Args:
        start_date: Start date for download
        end_date: End date for download
        skip_if_complete: Skip if coverage >= 90% (default True)
        rate_limit: Delay between downloads in seconds (default 0.5)
        start_from: Resume from symbol number (default 1)
    """
    
    print("\n" + "="*100)
    print("NIFTY 500 BULK DOWNLOAD - 5 YEARS DATA")
    print("="*100)
    print(f"Date Range: {start_date} to {end_date}")
    print(f"Skip if Complete: {skip_if_complete}")
    print(f"Rate Limit: {rate_limit}s between downloads")
    if start_from > 1:
        print(f"⚡ RESUMING from symbol #{start_from}")
    print("="*100)
    
    # Get all symbols
    print("\n📋 Loading Nifty 500 symbols...")
    symbols_data = get_nifty500_symbols()
    
    print(f"✅ Found {len(symbols_data)} symbols")
    
    # Statistics
    stats = {
        'total': len(symbols_data),
        'skipped': 0,
        'downloaded': 0,
        'failed': 0,
        'new_records': 0,
        'updated_records': 0,
        'verified': sum(1 for s in symbols_data if s[2]),
        'unverified': sum(1 for s in symbols_data if not s[2])
    }
    
    print(f"   Verified mappings: {stats['verified']}")
    print(f"   Unverified mappings: {stats['unverified']}")
    
    print("\n" + "="*100)
    print("Starting download...")
    print("="*100)
    
    start_time = time.time()
    
    # Process each symbol
    for i, (nse_symbol, yahoo_symbol, is_verified) in enumerate(symbols_data, 1):
        # Skip if resuming
        if i < start_from:
            continue
            
        print(f"\n[{i}/{stats['total']}] {nse_symbol} → {yahoo_symbol}")
        
        # Check existing data
        count, coverage, min_date, max_date = check_existing_data(yahoo_symbol, start_date, end_date)
        
        print(f"  Existing: {count} records ({coverage:.1f}% coverage)")
        if count > 0:
            print(f"  Range: {min_date} to {max_date}")
        
        # Skip if already complete
        if skip_if_complete and coverage >= 90:
            print(f"  ⏭️  SKIPPED (coverage {coverage:.1f}% - sufficient)")
            stats['skipped'] += 1
            continue
        
        # Download
        print(f"  📥 Downloading...")
        inserted, updated, error = download_symbol_data(yahoo_symbol, start_date, end_date)
        
        if error:
            print(f"  ❌ FAILED: {error}")
            stats['failed'] += 1
        else:
            print(f"  ✅ SUCCESS: {inserted} new, {updated} updated")
            stats['downloaded'] += 1
            stats['new_records'] += inserted
            stats['updated_records'] += updated
        
        # Rate limiting to avoid overwhelming Yahoo Finance
        if i < stats['total']:
            time.sleep(rate_limit)
        
        # Progress update every 50 symbols
        if i % 50 == 0:
            elapsed = time.time() - start_time
            avg_time = elapsed / i
            remaining = (stats['total'] - i) * avg_time
            
            print(f"\n{'='*100}")
            print(f"PROGRESS UPDATE: {i}/{stats['total']} ({i/stats['total']*100:.1f}%)")
            print(f"Elapsed: {elapsed/60:.1f}min | Estimated remaining: {remaining/60:.1f}min")
            print(f"Downloaded: {stats['downloaded']} | Skipped: {stats['skipped']} | Failed: {stats['failed']}")
            print(f"New records: {stats['new_records']:,} | Updated: {stats['updated_records']:,}")
            print("="*100)
    
    # Final summary
    total_time = time.time() - start_time
    
    print("\n" + "="*100)
    print("DOWNLOAD COMPLETE!")
    print("="*100)
    print(f"Total Symbols: {stats['total']}")
    print(f"  Downloaded: {stats['downloaded']}")
    print(f"  Skipped: {stats['skipped']}")
    print(f"  Failed: {stats['failed']}")
    print(f"\nNew Records: {stats['new_records']:,}")
    print(f"Updated Records: {stats['updated_records']:,}")
    print(f"Total Records: {stats['new_records'] + stats['updated_records']:,}")
    print(f"\nTime Taken: {total_time/60:.1f} minutes")
    print(f"Average: {total_time/stats['total']:.2f}s per symbol")
    print("="*100)
    
    # Recommendations
    if stats['failed'] > 0:
        print(f"\n⚠️  {stats['failed']} symbols failed to download")
        print("   Run the script again to retry failed symbols")
    
    if stats['unverified'] > 0:
        print(f"\n⚠️  {stats['unverified']} symbols have unverified mappings")
        print("   Some downloads may have failed due to incorrect Yahoo symbols")
        print("   Run: python yahoo_finance_service/validate_symbol_mapping.py")
    
    print()

def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Bulk download 5 years of Yahoo Finance data for all Nifty 500 stocks'
    )
    parser.add_argument('--years', type=int, default=5, 
                       help='Number of years to download (default: 5)')
    parser.add_argument('--force', action='store_true',
                       help='Force download even if data is complete')
    parser.add_argument('--rate-limit', type=float, default=0.5,
                       help='Delay between downloads in seconds (default: 0.5)')
    parser.add_argument('--start-from', type=int, default=1,
                       help='Resume from symbol number (default: 1)')
    
    args = parser.parse_args()
    
    # Calculate date range
    end_date = date.today()
    start_date = end_date - timedelta(days=args.years * 365)
    
    print(f"\n📅 Date Range: {args.years} years")
    print(f"   From: {start_date}")
    print(f"   To: {end_date}")
    
    skip_complete = not args.force
    
    # Confirm
    if not args.force:
        print("\n⚠️  This will download data for 501 stocks!")
        print("   Estimated time: 5-10 minutes (with rate limiting)")
        print("   Stocks with 90%+ coverage will be skipped")
        response = input("\nProceed? (y/n): ").strip().lower()
        if response != 'y':
            print("❌ Cancelled")
            return 1
    
    try:
        download_all_nifty500(start_date, end_date, skip_complete, args.rate_limit, args.start_from)
        return 0
    except KeyboardInterrupt:
        print("\n\n⚠️  INTERRUPTED BY USER")
        print("To resume, run:")
        print(f"   python download_nifty500_bulk.py --start-from XXX")
        print("(Replace XXX with the last completed symbol number)")
        return 1
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == '__main__':
    sys.exit(main())
