"""
Generate updated nifty500_stocks_list.py from official NSE data
"""
import sys
sys.path.insert(0, '.')
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL
from dotenv import load_dotenv
import os
from datetime import datetime

load_dotenv()

url = URL.create(
    drivername='mysql+pymysql',
    username=os.getenv('MYSQL_USER', 'root'),
    password=os.getenv('MYSQL_PASSWORD', ''),
    host=os.getenv('MYSQL_HOST', '127.0.0.1'),
    port=int(os.getenv('MYSQL_PORT', '3306')),
    database=os.getenv('MYSQL_DB', 'marketdata'),
    query={'charset': 'utf8mb4'},
)
engine = create_engine(url)

# Get NSE official Nifty 500 symbols from DB
with engine.connect() as conn:
    result = conn.execute(text("SELECT symbol FROM nse_index_constituents WHERE index_name = 'NIFTY500' ORDER BY symbol"))
    nse_symbols = [row[0] for row in result.fetchall()]

print(f"Total official Nifty 500 symbols: {len(nse_symbols)}")

# Generate the Python file content
output = f'''"""
Nifty 500 Official Constituents List
====================================

Official Nifty 500 Index constituents from NSE India.
Source: NSE India - https://www.nseindia.com/
Generated on: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
Total stocks: {len(nse_symbols)}

Note: These are NSE symbols without .NS suffix.
      Add .NS suffix when using with Yahoo Finance API.
"""

NIFTY_500_STOCKS = [
'''

# Add symbols in rows of 10
for i in range(0, len(nse_symbols), 10):
    batch = nse_symbols[i:i+10]
    line = "    " + ", ".join(f"'{s}'" for s in batch) + ","
    output += line + "\n"

output += f''']

# Total stocks: {len(nse_symbols)}
print(f"Nifty 500 official constituents loaded: {{len(NIFTY_500_STOCKS)}} stocks")
'''

# Write the file
output_path = "utilities/nifty500_stocks_list.py"
with open(output_path, 'w') as f:
    f.write(output)

print(f"✅ Updated {output_path} with {len(nse_symbols)} official Nifty 500 symbols")
print("\nFirst 20 symbols:")
print(nse_symbols[:20])
print("\nLast 20 symbols:")
print(nse_symbols[-20:])
