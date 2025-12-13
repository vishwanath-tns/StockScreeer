"""Parse Nifty 50 CSV and check database mapping."""
import pandas as pd
from sqlalchemy import create_engine, text
from urllib.parse import quote_plus
import os
from dotenv import load_dotenv

load_dotenv()
pw = quote_plus(os.getenv('MYSQL_PASSWORD',''))
e = create_engine(f'mysql+pymysql://root:{pw}@localhost:3306/dhan_trading')

# Read CSV
csv_path = r"C:\Users\Admin\Downloads\MW-NIFTY-50-11-Dec-2025.csv"
df = pd.read_csv(csv_path)

# Clean column names and get symbols
df.columns = df.columns.str.strip()
symbols = df['SYMBOL'].str.strip().tolist()

# Remove 'NIFTY 50' and 'MAXHEALTH', 'INDIGO' (not in Nifty 50 index)
symbols = [s for s in symbols if s and s not in ['NIFTY 50', 'MAXHEALTH', 'INDIGO']]

print(f"Total symbols from CSV: {len(symbols)}")
print(f"Symbols: {symbols}\n")

with e.connect() as c:
    print("=== Checking Symbols in dhan_instruments ===\n")
    
    found = []
    missing = []
    
    for sym in symbols:
        r = c.execute(text(f"""
            SELECT security_id, symbol, display_name, exchange_segment, series
            FROM dhan_instruments 
            WHERE underlying_symbol = '{sym}'
              AND exchange_segment = 'NSE_EQ'
            LIMIT 1
        """))
        
        row = r.fetchone()
        if row:
            found.append((sym, row[0], row[1], row[2]))
            print(f"✅ {sym:12s} | ID: {row[0]:6d} | {row[1]:20s} | {row[2]}")
        else:
            missing.append(sym)
            print(f"❌ {sym:12s} | NOT FOUND in NSE_EQ")
    
    print(f"\n=== Summary ===")
    print(f"✅ Found: {len(found)}/50")
    print(f"❌ Missing: {len(missing)}/50")
    
    if missing:
        print(f"\nMissing symbols: {', '.join(missing)}")
        
        print("\n=== Checking if missing symbols exist in other segments ===")
        for sym in missing:
            r = c.execute(text(f"""
                SELECT exchange_segment, series, security_id
                FROM dhan_instruments 
                WHERE underlying_symbol = '{sym}'
                LIMIT 3
            """))
            rows = r.fetchall()
            if rows:
                print(f"\n{sym} found in:")
                for row in rows:
                    print(f"  - {row[0]} | Series: {row[1]} | ID: {row[2]}")
            else:
                print(f"\n{sym} - Not found in any segment")
