from services.market_breadth_service import get_engine
import pandas as pd

eng = get_engine()

# Test the prev_close query
test = pd.read_sql("""
    SELECT symbol, close, date 
    FROM yfinance_daily_quotes 
    WHERE symbol = 'RELIANCE.NS' 
    AND date = (SELECT MAX(date) FROM yfinance_daily_quotes WHERE date < CURDATE())
""", eng)

print("Query result:")
print(test)

# Check all symbols with data for yesterday
count = pd.read_sql("""
    SELECT COUNT(*) as count
    FROM yfinance_daily_quotes 
    WHERE date = (SELECT MAX(date) FROM yfinance_daily_quotes WHERE date < CURDATE())
""", eng)

print(f"\nTotal symbols with yesterday's data: {count.iloc[0]['count']}")

eng.dispose()
