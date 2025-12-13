"""
Index Importer - Parses NSE MarketWatch CSV files and imports indices to database.
"""
import os
import re
import pandas as pd
from datetime import datetime
from pathlib import Path
from sqlalchemy import create_engine, text
from urllib.parse import quote_plus
from dotenv import load_dotenv

load_dotenv()


def get_db_engine():
    """Create database engine."""
    pw = quote_plus(os.getenv("MYSQL_PASSWORD", ""))
    user = os.getenv("MYSQL_USER", "root")
    host = os.getenv("MYSQL_HOST", "localhost")
    port = os.getenv("MYSQL_PORT", "3306")
    db = os.getenv("MYSQL_DB", "dhan_trading")
    return create_engine(f"mysql+pymysql://{user}:{pw}@{host}:{port}/{db}")


def parse_index_name(filename: str) -> tuple:
    """
    Extract index name and date from filename.
    Example: MW-NIFTY-50-13-Dec-2025.csv -> ('NIFTY 50', '2025-12-13')
    """
    # Remove .csv extension
    name = filename.replace('.csv', '')
    
    # Remove MW- prefix
    if name.startswith('MW-'):
        name = name[3:]
    
    # Extract date from end (format: DD-Mon-YYYY)
    date_pattern = r'-(\d{1,2})-([A-Za-z]{3})-(\d{4})(?:\(\d+\))?$'
    match = re.search(date_pattern, name)
    
    if match:
        day, month, year = match.groups()
        # Convert to date
        date_str = f"{day}-{month}-{year}"
        try:
            data_date = datetime.strptime(date_str, "%d-%b-%Y").date()
        except:
            data_date = datetime.now().date()
        
        # Remove date part from name
        index_name = re.sub(date_pattern, '', name)
    else:
        data_date = datetime.now().date()
        index_name = name
    
    # Clean up index name (replace hyphens with spaces, handle special cases)
    index_name = index_name.replace('-', ' ').strip()
    
    # Handle special cases
    index_name = index_name.replace('&', '&')  # Keep ampersand
    
    return index_name, data_date


def clean_numeric(value):
    """Clean numeric value from string with commas and special characters."""
    try:
        # Handle Series (shouldn't happen, but just in case)
        if isinstance(value, pd.Series):
            value = value.iloc[0] if len(value) > 0 else None
        
        if value is None:
            return None
        if isinstance(value, (int, float)):
            if pd.isna(value):
                return None
            return value
        
        # Convert to string and check
        str_val = str(value).strip()
        if str_val in ('-', '', 'nan', 'NaN', 'NA', 'N/A'):
            return None
        
        # Remove commas and currency symbols
        cleaned = str_val.replace(',', '').replace('₹', '').strip()
        return float(cleaned)
    except:
        return None


def parse_index_file(filepath: str) -> tuple:
    """
    Parse a MarketWatch CSV file and return index info and constituents.
    Returns: (index_name, data_date, constituents_df)
    """
    filename = os.path.basename(filepath)
    index_name, data_date = parse_index_name(filename)
    
    # Read CSV - skip header cleaning issues
    df = pd.read_csv(filepath, encoding='utf-8')
    
    # Clean column names (remove newlines and extra spaces)
    df.columns = [col.strip().replace('\n', '').replace(' ', '_').upper() for col in df.columns]
    
    # Rename first column to symbol (it's the SYMBOL column)
    first_col = df.columns[0]
    df = df.rename(columns={first_col: 'symbol'})
    
    # Find matching columns - order matters! More specific patterns first
    rename_map = {}
    for old_col in df.columns:
        if old_col == 'symbol':
            continue
        old_upper = old_col.upper()
        
        # Check for specific patterns - ORDER MATTERS (more specific first)
        if 'VOLUME' in old_upper:
            rename_map[old_col] = 'volume'
        elif 'VALUE' in old_upper:
            rename_map[old_col] = 'value_cr'
        elif '52W_H' in old_upper or '52WH' in old_upper:
            rename_map[old_col] = 'week52_high'
        elif '52W_L' in old_upper or '52WL' in old_upper:
            rename_map[old_col] = 'week52_low'
        elif '30_D' in old_upper or '30D' in old_upper:
            rename_map[old_col] = 'day30_change_pct'
        elif '365_D' in old_upper or '365D' in old_upper:
            rename_map[old_col] = 'day365_change_pct'
        elif '%CHNG' in old_upper or 'PCHNG' in old_upper or '%_CHNG' in old_upper:
            # Percent change - MUST check before plain CHNG
            rename_map[old_col] = 'change_pct'
        elif 'CHNG' in old_upper and '%' not in old_upper:
            # Plain change value (not percent)
            rename_map[old_col] = 'change_val'
        elif 'PREV' in old_upper and 'CLOSE' in old_upper:
            rename_map[old_col] = 'prev_close'
        elif old_upper in ('OPEN', 'OPEN_'):
            rename_map[old_col] = 'open_price'
        elif old_upper in ('HIGH', 'HIGH_'):
            rename_map[old_col] = 'high_price'
        elif old_upper in ('LOW', 'LOW_'):
            rename_map[old_col] = 'low_price'
        elif old_upper in ('LTP', 'LTP_'):
            rename_map[old_col] = 'ltp'
    
    df = df.rename(columns=rename_map)
    
    # Clean symbol column
    df['symbol'] = df['symbol'].astype(str).str.strip()
    
    # Filter out empty symbols and index row (first row usually has space in symbol)
    df = df[df['symbol'].notna() & (df['symbol'] != '')]
    
    # Skip the first row if it contains a space (it's the index, not a stock)
    if len(df) > 0 and ' ' in df.iloc[0]['symbol']:
        df = df.iloc[1:].copy()
    
    # Reset index
    df = df.reset_index(drop=True)
    
    # Clean numeric columns
    numeric_cols = ['open_price', 'high_price', 'low_price', 'prev_close', 'ltp',
                    'change_val', 'change_pct', 'volume', 'value_cr', 
                    'week52_high', 'week52_low', 'day30_change_pct', 'day365_change_pct']
    
    for col in numeric_cols:
        if col in df.columns:
            df[col] = df[col].apply(clean_numeric)
    
    # Replace NaN with None for MySQL compatibility
    df = df.where(pd.notnull(df), None)
    
    df['data_date'] = data_date
    
    return index_name, data_date, df, filename


def safe_get(row, col):
    """Safely get a value from a row, converting NaN/inf to None."""
    if col not in row.index:
        return None
    val = row.get(col)
    if val is None:
        return None
    # Check for numpy/pandas NaN
    if isinstance(val, float) and (pd.isna(val) or val != val):  # NaN != NaN
        return None
    return val


def import_indices_to_db(indices_folder: str, log_cb=print):
    """
    Import all indices from folder to database.
    """
    engine = get_db_engine()
    indices_path = Path(indices_folder)
    
    if not indices_path.exists():
        log_cb(f"❌ Folder not found: {indices_folder}")
        return
    
    # Get all CSV files
    csv_files = list(indices_path.glob("*.csv"))
    log_cb(f"Found {len(csv_files)} index files")
    
    # Track unique stocks across all indices
    all_stocks = set()
    imported_indices = []
    
    with engine.begin() as conn:
        for csv_file in csv_files:
            try:
                index_name, data_date, constituents_df, filename = parse_index_file(str(csv_file))
                
                if len(constituents_df) == 0:
                    log_cb(f"⚠ Skipping empty file: {filename}")
                    continue
                
                # Insert/update index
                conn.execute(text("""
                    INSERT INTO dhan_indices (index_name, display_name, source_file, num_constituents)
                    VALUES (:index_name, :display_name, :source_file, :num_constituents)
                    ON DUPLICATE KEY UPDATE 
                        source_file = VALUES(source_file),
                        num_constituents = VALUES(num_constituents),
                        last_updated = CURRENT_TIMESTAMP
                """), {
                    'index_name': index_name,
                    'display_name': index_name,
                    'source_file': filename,
                    'num_constituents': len(constituents_df)
                })
                
                # Get index ID
                result = conn.execute(text(
                    "SELECT id FROM dhan_indices WHERE index_name = :index_name"
                ), {'index_name': index_name})
                index_id = result.scalar()
                
                # Delete existing constituents for this index and date
                conn.execute(text("""
                    DELETE FROM dhan_index_constituents 
                    WHERE index_id = :index_id AND data_date = :data_date
                """), {'index_id': index_id, 'data_date': data_date})
                
                # Insert constituents
                for _, row in constituents_df.iterrows():
                    symbol = str(row['symbol']).strip()
                    if not symbol:
                        continue
                    
                    all_stocks.add(symbol)
                    
                    conn.execute(text("""
                        INSERT INTO dhan_index_constituents 
                        (index_id, symbol, open_price, high_price, low_price, prev_close, ltp,
                         change_val, change_pct, volume, value_cr, week52_high, week52_low,
                         day30_change_pct, day365_change_pct, data_date)
                        VALUES 
                        (:index_id, :symbol, :open_price, :high_price, :low_price, :prev_close, :ltp,
                         :change_val, :change_pct, :volume, :value_cr, :week52_high, :week52_low,
                         :day30_change_pct, :day365_change_pct, :data_date)
                    """), {
                        'index_id': index_id,
                        'symbol': symbol,
                        'open_price': safe_get(row, 'open_price'),
                        'high_price': safe_get(row, 'high_price'),
                        'low_price': safe_get(row, 'low_price'),
                        'prev_close': safe_get(row, 'prev_close'),
                        'ltp': safe_get(row, 'ltp'),
                        'change_val': safe_get(row, 'change_val'),
                        'change_pct': safe_get(row, 'change_pct'),
                        'volume': safe_get(row, 'volume'),
                        'value_cr': safe_get(row, 'value_cr'),
                        'week52_high': safe_get(row, 'week52_high'),
                        'week52_low': safe_get(row, 'week52_low'),
                        'day30_change_pct': safe_get(row, 'day30_change_pct'),
                        'day365_change_pct': safe_get(row, 'day365_change_pct'),
                        'data_date': data_date,
                    })
                
                imported_indices.append(index_name)
                log_cb(f"✓ {index_name}: {len(constituents_df)} stocks")
                
            except Exception as e:
                import traceback
                log_cb(f"❌ Error processing {csv_file.name}: {e}")
                traceback.print_exc()
        
        # Now insert unique stocks
        log_cb(f"\n📊 Creating unique stocks list: {len(all_stocks)} stocks")
        
        for symbol in all_stocks:
            # Count how many indices this stock is in
            result = conn.execute(text("""
                SELECT COUNT(DISTINCT index_id) FROM dhan_index_constituents WHERE symbol = :symbol
            """), {'symbol': symbol})
            indices_count = result.scalar()
            
            # Try to get security_id from dhan_instruments
            result = conn.execute(text("""
                SELECT security_id FROM dhan_instruments 
                WHERE symbol = :symbol AND exchange_segment IN (1, 'NSE', 'NSE_EQ')
                LIMIT 1
            """), {'symbol': symbol})
            row = result.fetchone()
            security_id = row[0] if row else None
            
            conn.execute(text("""
                INSERT INTO dhan_stocks (symbol, security_id, indices_count)
                VALUES (:symbol, :security_id, :indices_count)
                ON DUPLICATE KEY UPDATE 
                    security_id = COALESCE(VALUES(security_id), security_id),
                    indices_count = VALUES(indices_count),
                    last_updated = CURRENT_TIMESTAMP
            """), {
                'symbol': symbol,
                'security_id': security_id,
                'indices_count': indices_count
            })
        
        # Create stock-index links
        log_cb("\n🔗 Creating stock-index links...")
        conn.execute(text("DELETE FROM dhan_stock_index_link"))
        conn.execute(text("""
            INSERT INTO dhan_stock_index_link (stock_id, index_id)
            SELECT DISTINCT s.id, c.index_id
            FROM dhan_stocks s
            JOIN dhan_index_constituents c ON s.symbol = c.symbol
        """))
    
    log_cb(f"\n✅ Import complete!")
    log_cb(f"   Indices imported: {len(imported_indices)}")
    log_cb(f"   Unique stocks: {len(all_stocks)}")
    
    return imported_indices, all_stocks


def get_unique_stocks():
    """Get list of all unique stocks from database."""
    engine = get_db_engine()
    
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT symbol, security_id, indices_count 
            FROM dhan_stocks 
            WHERE is_active = 1
            ORDER BY indices_count DESC, symbol
        """))
        return [(row[0], row[1], row[2]) for row in result]


def show_import_summary():
    """Show summary of imported data."""
    engine = get_db_engine()
    
    with engine.connect() as conn:
        print("\n" + "=" * 60)
        print("INDEX IMPORT SUMMARY")
        print("=" * 60)
        
        # Count indices
        result = conn.execute(text("SELECT COUNT(*) FROM dhan_indices"))
        print(f"\nTotal Indices: {result.scalar()}")
        
        # List indices with constituent count
        print("\nIndices and Constituents:")
        print("-" * 50)
        result = conn.execute(text("""
            SELECT index_name, num_constituents 
            FROM dhan_indices 
            ORDER BY num_constituents DESC
        """))
        for row in result:
            print(f"  {row[0]:40} : {row[1]:>4} stocks")
        
        # Unique stocks
        result = conn.execute(text("SELECT COUNT(*) FROM dhan_stocks"))
        print(f"\nUnique Stocks: {result.scalar()}")
        
        # Stocks with security_id mapped
        result = conn.execute(text("SELECT COUNT(*) FROM dhan_stocks WHERE security_id IS NOT NULL"))
        print(f"Stocks with Security ID: {result.scalar()}")
        
        # Top stocks by index membership
        print("\nTop 20 Stocks by Index Membership:")
        print("-" * 50)
        result = conn.execute(text("""
            SELECT symbol, indices_count 
            FROM dhan_stocks 
            ORDER BY indices_count DESC 
            LIMIT 20
        """))
        for row in result:
            print(f"  {row[0]:20} : in {row[1]:>2} indices")


if __name__ == "__main__":
    # Import indices from the indices folder
    indices_folder = os.path.join(os.path.dirname(__file__), "..", "indices")
    indices_folder = os.path.abspath(indices_folder)
    
    print(f"Importing indices from: {indices_folder}")
    import_indices_to_db(indices_folder)
    show_import_summary()
