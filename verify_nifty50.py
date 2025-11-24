"""
Verify Nifty 50 Coverage in Intraday Data
"""

from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL
from dotenv import load_dotenv
import os

load_dotenv()

# Nifty 50 stocks (as of Nov 2025) - WITHOUT .NS suffix (as stored in DB)
NIFTY_50_STOCKS = [
    'RELIANCE', 'TCS', 'HDFCBANK', 'INFY', 'ICICIBANK',
    'HINDUNILVR', 'ITC', 'SBIN', 'BHARTIARTL', 'KOTAKBANK',
    'BAJFINANCE', 'LT', 'ASIANPAINT', 'HCLTECH', 'AXISBANK',
    'MARUTI', 'SUNPHARMA', 'TITAN', 'ULTRACEMCO', 'WIPRO',
    'NESTLEIND', 'POWERGRID', 'NTPC', 'M&M', 'TATAMOTORS',
    'BAJAJFINSV', 'ONGC', 'COALINDIA', 'ADANIPORTS', 'TECHM',
    'TATASTEEL', 'JSWSTEEL', 'HINDALCO', 'INDUSINDBK', 'DRREDDY',
    'APOLLOHOSP', 'DIVISLAB', 'CIPLA', 'EICHERMOT', 'GRASIM',
    'HEROMOTOCO', 'TATACONSUM', 'BPCL', 'BRITANNIA', 'SBILIFE',
    'HDFCLIFE', 'BAJAJ-AUTO', 'ADANIENT', 'SHRIRAMFIN', 'LTIM'
]

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

def check_nifty50_coverage():
    engine = create_db_engine()
    
    print("=" * 80)
    print("NIFTY 50 COVERAGE IN INTRADAY DATA")
    print("=" * 80)
    
    stocks_with_data = []
    stocks_without_data = []
    
    with engine.connect() as conn:
        for symbol in NIFTY_50_STOCKS:
            result = conn.execute(text("""
                SELECT COUNT(*) 
                FROM intraday_1min_candles 
                WHERE symbol = :symbol
            """), {'symbol': symbol})
            
            count = result.scalar()
            
            if count > 0:
                stocks_with_data.append((symbol, count))
            else:
                stocks_without_data.append(symbol)
    
    print(f"\n✅ Nifty 50 stocks with data: {len(stocks_with_data)}/50")
    
    if stocks_with_data:
        print(f"\nNifty 50 stocks with intraday data:")
        print(f"{'Symbol':<20} {'Candles':>15}")
        print("-" * 40)
        for symbol, count in sorted(stocks_with_data, key=lambda x: x[0]):
            print(f"{symbol:<20} {count:>15,}")
    
    if stocks_without_data:
        print(f"\n⚠️  Nifty 50 stocks WITHOUT data ({len(stocks_without_data)}):")
        for symbol in stocks_without_data:
            print(f"   • {symbol}")
        return False
    else:
        print(f"\n✅ ALL NIFTY 50 STOCKS HAVE DATA!")
        return True
    
    engine.dispose()

if __name__ == "__main__":
    success = check_nifty50_coverage()
    print("=" * 80)
    if not success:
        print("\n💡 The missing stocks should be added to the download.")
    else:
        print("\n✅ No action needed - all Nifty 50 stocks are already included!")
    print("=" * 80)
