"""
Check Nifty 50 Coverage in Intraday Data
"""

from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL
from dotenv import load_dotenv
import os

load_dotenv()

def create_db_engine():
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

def check_nifty50():
    engine = create_db_engine()
    
    print("=" * 80)
    print("NIFTY 50 COVERAGE CHECK")
    print("=" * 80)
    
    with engine.connect() as conn:
        # Check Nifty 50 mapping
        result = conn.execute(text("""
            SELECT COUNT(*) 
            FROM nse_yahoo_symbol_map 
            WHERE is_nifty50 = 1 AND is_active = 1
        """))
        nifty50_mapped = result.scalar()
        
        print(f"\n1. Nifty 50 stocks in mapping table: {nifty50_mapped}")
        
        # Check Nifty 50 in intraday data
        result = conn.execute(text("""
            SELECT DISTINCT m.yahoo_symbol, m.nse_symbol
            FROM nse_yahoo_symbol_map m
            WHERE m.is_nifty50 = 1 AND m.is_active = 1
            ORDER BY m.nse_symbol
        """))
        nifty50_stocks = result.fetchall()
        
        # Check which ones have data
        stocks_with_data = []
        stocks_without_data = []
        
        for yahoo_symbol, nse_symbol in nifty50_stocks:
            result = conn.execute(text("""
                SELECT COUNT(*) 
                FROM intraday_1min_candles 
                WHERE symbol = :symbol
            """), {'symbol': yahoo_symbol})
            
            count = result.scalar()
            if count > 0:
                stocks_with_data.append((yahoo_symbol, nse_symbol, count))
            else:
                stocks_without_data.append((yahoo_symbol, nse_symbol))
        
        print(f"2. Nifty 50 stocks with intraday data: {len(stocks_with_data)}/{nifty50_mapped}")
        
        if stocks_without_data:
            print(f"\n⚠️  Missing data for {len(stocks_without_data)} Nifty 50 stocks:")
            for yahoo_symbol, nse_symbol in stocks_without_data:
                print(f"   • {nse_symbol:<20} ({yahoo_symbol})")
        else:
            print(f"\n✅ All Nifty 50 stocks have data!")
        
        if stocks_with_data:
            print(f"\n✅ Nifty 50 stocks with data ({len(stocks_with_data)}):")
            for yahoo_symbol, nse_symbol, count in stocks_with_data[:10]:
                print(f"   • {nse_symbol:<20} ({yahoo_symbol}): {count:,} candles")
            if len(stocks_with_data) > 10:
                print(f"   ... and {len(stocks_with_data) - 10} more")
    
    print("=" * 80)
    
    return len(stocks_without_data) == 0

if __name__ == "__main__":
    check_nifty50()
