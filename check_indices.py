from ranking.db.schema import get_ranking_engine
from sqlalchemy import text

e = get_ranking_engine()
conn = e.connect()

# Check indices_daily
print("=== indices_daily ===")
try:
    r = conn.execute(text("SELECT * FROM indices_daily LIMIT 3")).fetchall()
    if r:
        cols = conn.execute(text("DESCRIBE indices_daily")).fetchall()
        print("Columns:", [c[0] for c in cols])
        print("Sample:", r[0] if r else "Empty")
        
        # Count Nifty 50
        r2 = conn.execute(text("SELECT COUNT(*) FROM indices_daily WHERE index_name LIKE '%NIFTY 50%' OR index_name = 'NIFTY 50'")).fetchone()
        print(f"Nifty 50 records: {r2[0]}")
except Exception as ex:
    print(f"Error: {ex}")

# Check nse_index_data
print("\n=== nse_index_data ===")
try:
    r = conn.execute(text("SELECT * FROM nse_index_data LIMIT 3")).fetchall()
    if r:
        cols = conn.execute(text("DESCRIBE nse_index_data")).fetchall()
        print("Columns:", [c[0] for c in cols])
        
        # Count Nifty 50
        r2 = conn.execute(text("SELECT COUNT(*) FROM nse_index_data WHERE index_name LIKE '%NIFTY%50%'")).fetchone()
        print(f"Nifty 50 records: {r2[0]}")
        
        # Sample
        r3 = conn.execute(text("SELECT trade_date, close_value FROM nse_index_data WHERE index_name LIKE '%NIFTY%50%' ORDER BY trade_date DESC LIMIT 5")).fetchall()
        print("Sample:", r3)
except Exception as ex:
    print(f"Error: {ex}")

# Check yfinance_indices_daily_quotes
print("\n=== yfinance_indices_daily_quotes ===")
try:
    cols = conn.execute(text("DESCRIBE yfinance_indices_daily_quotes")).fetchall()
    print("Columns:", [c[0] for c in cols])
    
    r = conn.execute(text("SELECT DISTINCT symbol FROM yfinance_indices_daily_quotes LIMIT 10")).fetchall()
    print("Symbols:", [x[0] for x in r])
    
    r2 = conn.execute(text("SELECT COUNT(*) FROM yfinance_indices_daily_quotes WHERE symbol = '^NSEI'")).fetchone()
    print(f"^NSEI records: {r2[0]}")
except Exception as ex:
    print(f"Error: {ex}")
