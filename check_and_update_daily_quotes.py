"""
Check and Update Daily Quotes from Yahoo Finance
=================================================
Checks the most recent date in yfinance_daily_quotes and downloads missing data till today.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'yahoo_finance_service'))

from datetime import datetime, date, timedelta
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL
from dotenv import load_dotenv
from yahoo_client import YahooFinanceClient
from db_service import YFinanceDBService

load_dotenv()


def create_db_engine():
    """Create database engine"""
    url = URL.create(
        drivername="mysql+pymysql",
        username=os.getenv('MYSQL_USER', 'root'),
        password=os.getenv('MYSQL_PASSWORD', ''),
        host=os.getenv('MYSQL_HOST', 'localhost'),
        port=int(os.getenv('MYSQL_PORT', 3306)),
        database=os.getenv('MYSQL_DB', 'marketdata'),
        query={"charset": "utf8mb4"}
    )
    return create_engine(url, pool_pre_ping=True)


def check_latest_data():
    """Check the most recent date in the table"""
    print("=" * 80)
    print("CHECKING LATEST DATA IN yfinance_daily_quotes")
    print("=" * 80)
    
    engine = create_db_engine()
    
    with engine.connect() as conn:
        # Get total records
        result = conn.execute(text("SELECT COUNT(*) FROM yfinance_daily_quotes"))
        total_records = result.scalar()
        print(f"\n📊 Total records in table: {total_records:,}")
        
        # Get date range
        result = conn.execute(text("""
            SELECT MIN(date) as min_date, MAX(date) as max_date 
            FROM yfinance_daily_quotes
        """))
        row = result.fetchone()
        if row and row[0]:
            min_date = row[0]
            max_date = row[1]
            print(f"📅 Date range: {min_date} to {max_date}")
            
            days_old = (date.today() - max_date).days
            print(f"⏱️  Data is {days_old} days old (latest: {max_date})")
            
            # Get symbol count
            result = conn.execute(text("SELECT COUNT(DISTINCT symbol) FROM yfinance_daily_quotes"))
            symbol_count = result.scalar()
            print(f"📈 Unique symbols: {symbol_count}")
            
            # Get sample of latest data
            result = conn.execute(text("""
                SELECT symbol, date, close, volume 
                FROM yfinance_daily_quotes 
                WHERE date = :max_date 
                ORDER BY symbol 
                LIMIT 10
            """), {'max_date': max_date})
            
            print(f"\n📋 Sample of latest data (date: {max_date}):")
            print(f"{'Symbol':<15} {'Date':<12} {'Close':>12} {'Volume':>15}")
            print("-" * 60)
            for row in result:
                print(f"{row[0]:<15} {str(row[1]):<12} {float(row[2]):>12.2f} {int(row[3]) if row[3] else 0:>15,}")
            
            return max_date, symbol_count, days_old
        else:
            print("❌ No data found in table")
            return None, 0, 0


def download_missing_data(start_date, symbol_count):
    """Download missing data from start_date to today"""
    today = date.today()
    
    if start_date >= today:
        print("\n✅ Data is already up to date!")
        return
    
    print("\n" + "=" * 80)
    print("DOWNLOADING MISSING DATA")
    print("=" * 80)
    
    # Calculate next trading day (start_date + 1 day)
    from_date = start_date + timedelta(days=1)
    days_to_download = (today - from_date).days + 1
    
    print(f"\n📥 Will download data from {from_date} to {today}")
    print(f"📆 Approximately {days_to_download} calendar days to process")
    print(f"📊 For {symbol_count} symbols")
    
    response = input("\n❓ Do you want to proceed with the download? (yes/no): ").strip().lower()
    
    if response not in ['yes', 'y']:
        print("❌ Download cancelled by user")
        return
    
    print("\n🚀 Starting download...\n")
    
    # Get list of symbols from the database
    engine = create_db_engine()
    with engine.connect() as conn:
        # Get all symbols and identify duplicates
        result = conn.execute(text("""
            SELECT symbol
            FROM (SELECT DISTINCT symbol FROM yfinance_daily_quotes) s
            ORDER BY symbol
        """))
        all_symbols = [row[0] for row in result]
        
        # Filter out duplicates - keep only .NS version if both exist
        symbols = []
        seen_base = set()
        
        for symbol in all_symbols:
            # Get base symbol (without .NS)
            if symbol.endswith('.NS'):
                base_symbol = symbol[:-3]
            else:
                base_symbol = symbol
            
            # Skip if we've seen this base symbol already
            if base_symbol in seen_base:
                continue
            
            # Check if both versions exist
            base_exists = base_symbol in all_symbols
            ns_exists = f"{base_symbol}.NS" in all_symbols
            
            if base_exists and ns_exists:
                # Both exist - prefer .NS version for stocks
                if not symbol.startswith('^'):
                    if symbol.endswith('.NS'):
                        symbols.append(symbol)
                        seen_base.add(base_symbol)
                else:
                    # Index - use as is
                    symbols.append(symbol)
                    seen_base.add(base_symbol)
            else:
                # Only one version exists - use it
                symbols.append(symbol)
                seen_base.add(base_symbol)
    
    print(f"Found {len(all_symbols)} total symbols, filtered to {len(symbols)} unique symbols\n")
    
    # Initialize services
    yahoo_client = YahooFinanceClient()
    db_service = YFinanceDBService()
    
    success_count = 0
    error_count = 0
    total_quotes = 0
    failed_symbols = []
    
    for i, symbol in enumerate(symbols, 1):
        try:
            # Determine Yahoo symbol - don't add .NS if already present
            if symbol.startswith('^'):
                # Index symbols
                yahoo_symbol = symbol
            elif symbol.endswith('.NS'):
                # Already has .NS suffix
                yahoo_symbol = symbol
            else:
                # Add .NS suffix for NSE stocks
                yahoo_symbol = f"{symbol}.NS"
            
            print(f"[{i}/{len(symbols)}] Downloading {symbol} ({yahoo_symbol})...", end=' ', flush=True)
            
            # Download data
            quotes = yahoo_client.download_daily_data_with_symbol(
                symbol, 
                yahoo_symbol, 
                from_date, 
                today
            )
            
            if quotes:
                # Save to database using insert_quotes method
                inserted, updated = db_service.insert_quotes(quotes)
                print(f"✅ {len(quotes)} quotes (inserted: {inserted}, updated: {updated})")
                success_count += 1
                total_quotes += len(quotes)
            else:
                print("⚠️  No data returned")
                error_count += 1
                failed_symbols.append((symbol, "No data returned"))
                
        except Exception as e:
            print(f"❌ Error: {str(e)[:100]}")
            error_count += 1
            failed_symbols.append((symbol, str(e)))
            continue
    
    print("\n" + "=" * 80)
    print("DOWNLOAD COMPLETE")
    print("=" * 80)
    print(f"✅ Successful: {success_count}/{len(symbols)}")
    print(f"❌ Errors: {error_count}/{len(symbols)}")
    print(f"📊 Total quotes downloaded: {total_quotes:,}")
    
    if failed_symbols:
        print(f"\n⚠️  Failed symbols ({len(failed_symbols)}):")
        for symbol, error in failed_symbols[:20]:  # Show first 20
            print(f"  - {symbol}: {error[:80]}")
        if len(failed_symbols) > 20:
            print(f"  ... and {len(failed_symbols) - 20} more")
    
    print("=" * 80)


def main():
    """Main entry point"""
    try:
        # Check latest data
        max_date, symbol_count, days_old = check_latest_data()
        
        if max_date and days_old > 0:
            # Download missing data
            download_missing_data(max_date, symbol_count)
            
            # Verify update
            print("\n" + "=" * 80)
            print("VERIFICATION AFTER UPDATE")
            print("=" * 80)
            check_latest_data()
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
