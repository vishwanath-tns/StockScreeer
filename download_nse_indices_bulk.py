#!/usr/bin/env python3
"""
Download 5 Years Historical Data for All NSE Indices from Yahoo Finance
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

# All 24 available NSE indices on Yahoo Finance
NSE_INDICES = {
    # BROAD MARKET
    "Nifty 50": "^NSEI",
    "Nifty Next 50": "^NSMIDCP",
    "Nifty LargeMidcap 250": "NIFTY_LARGEMID250.NS",
    
    # SECTORAL
    "Nifty Auto": "^CNXAUTO",
    "Nifty Bank": "^NSEBANK",
    "Nifty Financial Services": "NIFTY_FIN_SERVICE.NS",
    "Nifty FMCG": "^CNXFMCG",
    "Nifty IT": "^CNXIT",
    "Nifty Metal": "^CNXMETAL",
    "Nifty Pharma": "^CNXPHARMA",
    "Nifty PSU Bank": "^CNXPSUBANK",
    "Nifty Private Bank": "NIFTY_PVT_BANK.NS",
    "Nifty Realty": "^CNXREALTY",
    "Nifty Energy": "^CNXENERGY",
    "Nifty Infrastructure": "^CNXINFRA",
    "Nifty CPSE": "NIFTY_CPSE.NS",
    "Nifty Oil & Gas": "NIFTY_OIL_AND_GAS.NS",
    "Nifty Healthcare": "NIFTY_HEALTHCARE.NS",
    
    # THEMATIC
    "Nifty India Consumption": "NIFTY_CONSR_DURBL.NS",
    "Nifty Mobility": "NIFTY_MOBILITY.NS",
    "Nifty Housing": "NIFTY_HOUSING.NS",
    
    # STRATEGY
    "Nifty100 Equal Weight": "NIFTY100_EQL_WGT.NS",
    "Nifty200 Momentum 30": "NIFTY200MOMENTM30.NS",
    "Nifty 100 ESG": "NIFTY100_ESG.NS",
}

def check_existing_data(symbol, start_date, end_date):
    """Check existing data coverage for an index"""
    conn = engine().connect()
    
    result = conn.execute(text("""
        SELECT 
            MIN(date) as min_date,
            MAX(date) as max_date,
            COUNT(*) as record_count
        FROM yfinance_indices_daily_quotes
        WHERE symbol = :symbol
        AND date BETWEEN :start_date AND :end_date
    """), {'symbol': symbol, 'start_date': start_date, 'end_date': end_date})
    
    row = result.fetchone()
    count = row[2] if row else 0
    min_date = row[0] if row else None
    max_date = row[1] if row else None
    
    # Calculate expected trading days
    days_diff = (end_date - start_date).days + 1
    weekend_days = sum(1 for i in range(days_diff) if (start_date + timedelta(days=i)).weekday() >= 5)
    expected = days_diff - weekend_days
    coverage = (count / expected * 100) if expected > 0 else 0
    
    conn.close()
    
    return count, coverage, min_date, max_date

def download_index_data(name, symbol, start_date, end_date):
    """Download historical data for a single index"""
    try:
        print(f"  📥 Downloading from Yahoo Finance...")
        
        # Download from Yahoo Finance
        ticker = yf.Ticker(symbol)
        data = ticker.history(start=start_date, end=end_date, interval="1d")
        
        if data.empty:
            return 0, 0, "No data from Yahoo"
        
        # Prepare records
        records = []
        for date_val, row in data.iterrows():
            records.append({
                'symbol': symbol,
                'date': date_val.date(),
                'open': float(row['Open']),
                'high': float(row['High']),
                'low': float(row['Low']),
                'close': float(row['Close']),
                'volume': int(row['Volume']) if 'Volume' in row and row['Volume'] > 0 else 0,
                'adj_close': float(row['Close'])
            })
        
        # Bulk insert with fresh connection
        conn = engine().connect()
        trans = conn.begin()
        
        try:
            inserted = 0
            updated = 0
            
            # Batch insert
            for record in records:
                result = conn.execute(text("""
                    INSERT INTO yfinance_indices_daily_quotes
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
            trans.rollback()
            return 0, 0, str(e)
        
        finally:
            conn.close()
    
    except Exception as e:
        return 0, 0, str(e)

def download_all_indices(start_date, end_date, skip_if_complete=True, rate_limit=0.5):
    """
    Download data for all NSE indices
    
    Args:
        start_date: Start date
        end_date: End date
        skip_if_complete: Skip if coverage >= 90%
        rate_limit: Delay between downloads (seconds)
    """
    
    print("\n" + "="*100)
    print("NSE INDICES BULK DOWNLOAD - 5 YEARS DATA")
    print("="*100)
    print(f"Date Range: {start_date} to {end_date}")
    print(f"Skip if Complete: {skip_if_complete}")
    print(f"Rate Limit: {rate_limit}s between downloads")
    print("="*100)
    
    print(f"\n📋 Loading {len(NSE_INDICES)} NSE indices...")
    
    # Statistics
    stats = {
        'total': len(NSE_INDICES),
        'skipped': 0,
        'downloaded': 0,
        'failed': 0,
        'new_records': 0,
        'updated_records': 0
    }
    
    print("\n" + "="*100)
    print("Starting download...")
    print("="*100)
    
    start_time = time.time()
    
    # Process each index
    for i, (name, symbol) in enumerate(NSE_INDICES.items(), 1):
        print(f"\n[{i}/{stats['total']}] {name} → {symbol}")
        
        # Check existing data
        count, coverage, min_date, max_date = check_existing_data(symbol, start_date, end_date)
        
        print(f"  Existing: {count} records ({coverage:.1f}% coverage)")
        if count > 0:
            print(f"  Range: {min_date} to {max_date}")
        
        # Skip if already complete
        if skip_if_complete and coverage >= 90:
            print(f"  ⏭️  SKIPPED (coverage {coverage:.1f}% - sufficient)")
            stats['skipped'] += 1
            continue
        
        # Download
        inserted, updated, error = download_index_data(name, symbol, start_date, end_date)
        
        if error:
            print(f"  ❌ FAILED: {error}")
            stats['failed'] += 1
        else:
            print(f"  ✅ SUCCESS: {inserted} new, {updated} updated")
            stats['downloaded'] += 1
            stats['new_records'] += inserted
            stats['updated_records'] += updated
        
        # Rate limiting
        if i < stats['total']:
            time.sleep(rate_limit)
        
        # Progress update every 10 indices
        if i % 10 == 0:
            elapsed = time.time() - start_time
            avg_time = elapsed / i
            remaining = (stats['total'] - i) * avg_time
            
            print(f"\n{'='*100}")
            print(f"PROGRESS: {i}/{stats['total']} ({i/stats['total']*100:.1f}%)")
            print(f"Elapsed: {elapsed/60:.1f}min | Remaining: {remaining/60:.1f}min")
            print(f"Downloaded: {stats['downloaded']} | Skipped: {stats['skipped']} | Failed: {stats['failed']}")
            print(f"Records: {stats['new_records']:,} new, {stats['updated_records']:,} updated")
            print("="*100)
    
    # Final summary
    total_time = time.time() - start_time
    
    print("\n" + "="*100)
    print("DOWNLOAD COMPLETE!")
    print("="*100)
    print(f"Total Indices: {stats['total']}")
    print(f"  Downloaded: {stats['downloaded']}")
    print(f"  Skipped: {stats['skipped']}")
    print(f"  Failed: {stats['failed']}")
    print(f"\nNew Records: {stats['new_records']:,}")
    print(f"Updated Records: {stats['updated_records']:,}")
    print(f"Total Records: {stats['new_records'] + stats['updated_records']:,}")
    print(f"\nTime Taken: {total_time/60:.1f} minutes")
    print(f"Average: {total_time/stats['total']:.2f}s per index")
    print("="*100)
    
    # Recommendations
    if stats['failed'] > 0:
        print(f"\n⚠️  {stats['failed']} indices failed to download")
        print("   Run the script again to retry")
    
    print()

def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Bulk download 5 years of Yahoo Finance data for all NSE indices'
    )
    parser.add_argument('--years', type=int, default=5,
                       help='Number of years to download (default: 5)')
    parser.add_argument('--force', action='store_true',
                       help='Force download even if data is complete')
    parser.add_argument('--rate-limit', type=float, default=0.5,
                       help='Delay between downloads in seconds (default: 0.5)')
    
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
        print(f"\n⚠️  This will download data for {len(NSE_INDICES)} NSE indices!")
        print("   Estimated time: 1-2 minutes")
        print("   Indices with 90%+ coverage will be skipped")
        response = input("\nProceed? (y/n): ").strip().lower()
        if response != 'y':
            print("❌ Cancelled")
            return 1
    
    try:
        download_all_indices(start_date, end_date, skip_complete, args.rate_limit)
        return 0
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == '__main__':
    sys.exit(main())
