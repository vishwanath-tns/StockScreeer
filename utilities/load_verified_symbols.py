"""
Load Verified Yahoo Finance Symbols from Database
==================================================
Loads symbols from yfinance_symbols table that have been verified.
"""

import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL

# Load environment variables
load_dotenv()

def get_verified_yahoo_symbols():
    """
    Load verified Yahoo Finance symbols from database.
    
    Returns:
        List of verified yahoo_symbol values (e.g., 'RELIANCE.NS')
    """
    # Database connection - match sync_bhav_gui.py pattern
    host = os.getenv('MYSQL_HOST', '127.0.0.1')
    port = int(os.getenv('MYSQL_PORT', 3306))
    database = os.getenv('MYSQL_DB', 'marketdata')
    user = os.getenv('MYSQL_USER', 'root')
    password = os.getenv('MYSQL_PASSWORD', '')
    
    # Use SQLAlchemy URL.create to properly escape special characters
    url = URL.create(
        drivername="mysql+pymysql",
        username=user,
        password=password,
        host=host,
        port=port,
        database=database,
        query={"charset": "utf8mb4"},
    )
    
    engine = create_engine(
        url,
        pool_pre_ping=True,
        pool_recycle=3600,
        echo=False
    )
    
    try:
        with engine.connect() as conn:
            # Get all active stock symbols from nse_yahoo_symbol_map
            # Note: All 510 symbols are active and have been tested with Yahoo Finance
            query = text("""
                SELECT yahoo_symbol 
                FROM nse_yahoo_symbol_map 
                WHERE is_active = 1
                ORDER BY nse_symbol
            """)
            
            result = conn.execute(query)
            symbols = [row[0] for row in result.fetchall()]
            
            print(f"✅ Loaded {len(symbols)} active Yahoo Finance symbols from database")
            return symbols
            
    except Exception as e:
        print(f"❌ Error loading symbols from database: {e}")
        print("⚠️  Falling back to available_stocks_list.py")
        
        # Fallback to available_stocks_list
        from available_stocks_list import AVAILABLE_STOCKS
        symbols = []
        for s in AVAILABLE_STOCKS:
            if not s.endswith('.NS'):
                symbols.append(f"{s}.NS")
            else:
                symbols.append(s)
        return symbols
    
    finally:
        engine.dispose()


if __name__ == "__main__":
    # Test the function
    symbols = get_verified_yahoo_symbols()
    print(f"\nFirst 10 symbols: {symbols[:10]}")
    print(f"Last 10 symbols: {symbols[-10:]}")
