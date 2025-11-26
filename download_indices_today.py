"""
Download today's indices data (26-Nov-2025)
"""
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'yahoo_finance_service'))

from datetime import date, timedelta
from yahoo_client import YahooFinanceClient
from db_service import YFinanceDBService

def download_indices_data():
    """Download indices data for today"""
    
    # Index mappings: NSE symbol -> Yahoo symbol
    indices = [
        ('NIFTY', '^NSEI'),
        ('BANKNIFTY', '^NSEBANK'),
        ('SENSEX', '^BSESN')
    ]
    
    today = date.today()
    yesterday = today - timedelta(days=1)
    
    print("=" * 80)
    print(f"DOWNLOADING INDICES DATA FOR {yesterday} TO {today}")
    print("=" * 80)
    
    yahoo_client = YahooFinanceClient()
    db_service = YFinanceDBService()
    
    success_count = 0
    error_count = 0
    total_quotes = 0
    
    for nse_symbol, yahoo_symbol in indices:
        try:
            print(f"\n[{nse_symbol}] Downloading {yahoo_symbol}...", end=' ', flush=True)
            
            # Download data - use yahoo_symbol as the storage symbol
            quotes = yahoo_client.download_daily_data_with_symbol(
                yahoo_symbol,  # Use yahoo symbol as storage symbol
                yahoo_symbol,  # Yahoo symbol for download
                yesterday,
                today
            )
            
            if quotes:
                # Save to database
                inserted, updated = db_service.insert_quotes(quotes)
                print(f"✅ {len(quotes)} quotes (inserted: {inserted}, updated: {updated})")
                success_count += 1
                total_quotes += len(quotes)
            else:
                print("⚠️  No data returned")
                error_count += 1
                
        except Exception as e:
            print(f"❌ Error: {str(e)[:100]}")
            error_count += 1
            continue
    
    print("\n" + "=" * 80)
    print("DOWNLOAD COMPLETE")
    print("=" * 80)
    print(f"✅ Successful: {success_count}/{len(indices)}")
    print(f"❌ Errors: {error_count}/{len(indices)}")
    print(f"📊 Total quotes downloaded: {total_quotes}")
    print("=" * 80)

if __name__ == "__main__":
    download_indices_data()
