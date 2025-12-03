"""
NSE Index Constituents Importer
===============================
Imports NSE index constituent lists (Nifty 500, Nifty 50, etc.) into MySQL database.

Usage:
    python utilities/import_nse_index_constituents.py <csv_path> <index_name>
    
Example:
    python utilities/import_nse_index_constituents.py "C:/Users/Admin/Downloads/ind_nifty500list.csv" NIFTY500
"""

import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL
from dotenv import load_dotenv
import os
import sys
from pathlib import Path

# Load environment variables
load_dotenv()

def get_engine():
    """Create database engine from environment variables."""
    host = os.getenv('MYSQL_HOST', '127.0.0.1')
    port = int(os.getenv('MYSQL_PORT', '3306'))
    db = os.getenv('MYSQL_DB', 'marketdata')
    user = os.getenv('MYSQL_USER', 'root')
    password = os.getenv('MYSQL_PASSWORD', '')
    
    # Use URL.create to properly handle special characters in password
    url = URL.create(
        drivername="mysql+pymysql",
        username=user,
        password=password,
        host=host,
        port=port,
        database=db,
        query={"charset": "utf8mb4"},
    )
    return create_engine(url, pool_pre_ping=True, pool_recycle=3600)


def create_table(engine):
    """Create the nse_index_constituents table if it doesn't exist."""
    create_table_sql = """
    CREATE TABLE IF NOT EXISTS nse_index_constituents (
        id INT AUTO_INCREMENT PRIMARY KEY,
        index_name VARCHAR(50) NOT NULL COMMENT 'Index name like NIFTY500, NIFTY50, NIFTYMIDCAP100',
        company_name VARCHAR(255) NOT NULL,
        industry VARCHAR(100),
        symbol VARCHAR(50) NOT NULL COMMENT 'NSE symbol without .NS suffix',
        series VARCHAR(10) DEFAULT 'EQ',
        isin_code VARCHAR(20),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        UNIQUE KEY idx_index_symbol (index_name, symbol),
        INDEX idx_symbol (symbol),
        INDEX idx_industry (industry)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    COMMENT='NSE Index constituent lists - official from NSE website';
    """
    
    with engine.connect() as conn:
        conn.execute(text(create_table_sql))
        conn.commit()
        print("✅ Table 'nse_index_constituents' created/verified successfully!")


def import_csv(engine, csv_path: str, index_name: str):
    """Import CSV file into the database."""
    # Read CSV
    df = pd.read_csv(csv_path)
    print(f"📄 Read {len(df)} rows from CSV")
    
    # Map CSV columns to database columns
    column_map = {
        'Company Name': 'company_name',
        'Industry': 'industry',
        'Symbol': 'symbol',
        'Series': 'series',
        'ISIN Code': 'isin_code'
    }
    
    # Rename columns
    df = df.rename(columns=column_map)
    
    # Add index_name
    df['index_name'] = index_name
    
    # Filter to only the columns we need
    cols = ['index_name', 'company_name', 'industry', 'symbol', 'series', 'isin_code']
    df = df[cols]
    
    # Filter out any dummy entries (like 'DUM...')
    df = df[~df['symbol'].str.startswith('DUM')]
    print(f"📊 After filtering dummy entries: {len(df)} rows")
    
    # Delete existing entries for this index
    with engine.connect() as conn:
        result = conn.execute(text("DELETE FROM nse_index_constituents WHERE index_name = :idx"), 
                              {'idx': index_name})
        deleted = result.rowcount
        conn.commit()
        if deleted > 0:
            print(f"🗑️ Deleted {deleted} existing entries for {index_name}")
    
    # Insert new data
    df.to_sql(
        'nse_index_constituents',
        engine,
        if_exists='append',
        index=False,
        method='multi',
        chunksize=100
    )
    print(f"✅ Imported {len(df)} constituents for {index_name}")
    
    return df


def compare_with_yahoo_list(engine, index_name: str):
    """Compare NSE constituents with the current Yahoo symbols list."""
    from utilities.nifty500_stocks_list import NIFTY_500_STOCKS
    
    # Get NSE symbols from database
    with engine.connect() as conn:
        result = conn.execute(text(
            "SELECT symbol FROM nse_index_constituents WHERE index_name = :idx"
        ), {'idx': index_name})
        nse_symbols = set(row[0] for row in result.fetchall())
    
    yahoo_symbols = set(NIFTY_500_STOCKS)
    
    print(f"\n📊 COMPARISON: NSE {index_name} vs Yahoo List")
    print("=" * 60)
    print(f"NSE Official: {len(nse_symbols)} symbols")
    print(f"Yahoo List (NIFTY_500_STOCKS): {len(yahoo_symbols)} symbols")
    
    # In NSE but not in Yahoo list
    missing_in_yahoo = nse_symbols - yahoo_symbols
    if missing_in_yahoo:
        print(f"\n❌ Missing in Yahoo list ({len(missing_in_yahoo)}):")
        for s in sorted(missing_in_yahoo):
            print(f"   {s}")
    
    # In Yahoo but not in NSE official list
    extra_in_yahoo = yahoo_symbols - nse_symbols
    if extra_in_yahoo:
        print(f"\n➕ Extra in Yahoo list (not in official NSE) ({len(extra_in_yahoo)}):")
        for s in sorted(extra_in_yahoo):
            print(f"   {s}")
    
    # Common symbols
    common = nse_symbols & yahoo_symbols
    print(f"\n✅ Common symbols: {len(common)}")
    
    return {
        'nse_count': len(nse_symbols),
        'yahoo_count': len(yahoo_symbols),
        'missing_in_yahoo': missing_in_yahoo,
        'extra_in_yahoo': extra_in_yahoo,
        'common': common
    }


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        print("\nRunning with defaults for Nifty 500...")
        csv_path = r"c:\Users\Admin\Downloads\ind_nifty500list.csv"
        index_name = "NIFTY500"
    else:
        csv_path = sys.argv[1]
        index_name = sys.argv[2].upper()
    
    if not Path(csv_path).exists():
        print(f"❌ CSV file not found: {csv_path}")
        sys.exit(1)
    
    print(f"🚀 Importing {index_name} from: {csv_path}")
    
    engine = get_engine()
    
    # Create table
    create_table(engine)
    
    # Import CSV
    df = import_csv(engine, csv_path, index_name)
    
    # Show sample data
    print(f"\n📋 Sample data imported:")
    print(df.head(10).to_string(index=False))
    
    # Compare with Yahoo list if it's Nifty 500
    if index_name == "NIFTY500":
        try:
            comparison = compare_with_yahoo_list(engine, index_name)
        except ImportError:
            print("\n⚠️ Could not import NIFTY_500_STOCKS for comparison")
    
    print(f"\n✅ Import complete for {index_name}!")


if __name__ == "__main__":
    main()
