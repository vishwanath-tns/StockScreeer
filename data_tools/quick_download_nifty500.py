#!/usr/bin/env python3
"""
Quick download yesterday's data for all Nifty 500 stocks
Uses the same NIFTY_500_STOCKS list as the dashboard
"""

from nifty500_stocks_list import NIFTY_500_STOCKS
from sync_bhav_gui import engine
from sqlalchemy import text
from datetime import datetime, date, timedelta
import yfinance as yf
import time

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
        
        for record in records:
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

def main():
    """Download yesterday's data for all Nifty 500 stocks"""
    
    print("\n" + "="*100)
    print("QUICK DOWNLOAD - Yesterday's Data for Nifty 500")
    print("="*100)
    
    # Get yesterday's date (or last trading day)
    end_date = date.today()
    start_date = end_date - timedelta(days=7)  # Download last 7 days to be safe
    
    print(f"Date Range: {start_date} to {end_date}")
    print(f"Total Symbols: {len(NIFTY_500_STOCKS)}")
    
    # Convert to Yahoo format
    yahoo_symbols = [f"{symbol}.NS" for symbol in NIFTY_500_STOCKS]
    
    stats = {
        'total': len(yahoo_symbols),
        'success': 0,
        'failed': 0,
        'new_records': 0,
        'updated_records': 0
    }
    
    failed_symbols = []
    
    print("\n" + "="*100)
    print("Starting download...")
    print("="*100)
    
    start_time = time.time()
    
    for i, (nse_symbol, yahoo_symbol) in enumerate(zip(NIFTY_500_STOCKS, yahoo_symbols), 1):
        print(f"\n[{i}/{stats['total']}] {nse_symbol} → {yahoo_symbol}")
        
        inserted, updated, error = download_symbol_data(yahoo_symbol, start_date, end_date)
        
        if error:
            print(f"  ❌ FAILED: {error}")
            stats['failed'] += 1
            failed_symbols.append((nse_symbol, yahoo_symbol, error))
        else:
            print(f"  ✅ SUCCESS: {inserted} new, {updated} updated")
            stats['success'] += 1
            stats['new_records'] += inserted
            stats['updated_records'] += updated
        
        # Rate limiting (2 requests per second max for free Yahoo Finance)
        if i < stats['total']:
            time.sleep(0.6)
        
        # Progress update every 50 symbols
        if i % 50 == 0:
            elapsed = time.time() - start_time
            avg_time = elapsed / i
            remaining = (stats['total'] - i) * avg_time
            
            print(f"\n{'='*100}")
            print(f"PROGRESS: {i}/{stats['total']} ({i/stats['total']*100:.1f}%)")
            print(f"Elapsed: {elapsed/60:.1f}min | Estimated remaining: {remaining/60:.1f}min")
            print(f"Success: {stats['success']} | Failed: {stats['failed']}")
            print(f"New: {stats['new_records']:,} | Updated: {stats['updated_records']:,}")
            print("="*100)
    
    # Final summary
    total_time = time.time() - start_time
    
    print("\n" + "="*100)
    print("DOWNLOAD COMPLETE!")
    print("="*100)
    print(f"Total Symbols: {stats['total']}")
    print(f"  Success: {stats['success']}")
    print(f"  Failed: {stats['failed']}")
    print(f"\nNew Records: {stats['new_records']:,}")
    print(f"Updated Records: {stats['updated_records']:,}")
    print(f"Total Records: {stats['new_records'] + stats['updated_records']:,}")
    print(f"\nTime Taken: {total_time/60:.1f} minutes")
    print(f"Average: {total_time/stats['total']:.2f}s per symbol")
    print("="*100)
    
    if failed_symbols:
        print(f"\n⚠️  Failed Symbols ({len(failed_symbols)}):")
        print("="*100)
        for nse, yahoo, error in failed_symbols[:20]:  # Show first 20
            print(f"  {nse:15} → {yahoo:20} : {error}")
        if len(failed_symbols) > 20:
            print(f"  ... and {len(failed_symbols) - 20} more")
    
    print("\n✅ Now restart the dashboard to see updated advance-decline metrics!")
    print()

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  INTERRUPTED BY USER")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
