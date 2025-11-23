#!/usr/bin/env python3
"""
List all stocks in Nifty 500 index
"""

from sync_bhav_gui import engine
from sqlalchemy import text

def list_nifty500_stocks():
    """List all stocks in Nifty 500 with their latest data"""
    conn = engine().connect()
    
    result = conn.execute(text("""
        SELECT symbol, ltp, prev_close, change_percent, volume, data_date
        FROM nse_index_constituents 
        WHERE index_id = 25 
        ORDER BY symbol
    """))
    
    stocks = result.fetchall()
    
    print(f"\n{'='*100}")
    print(f"NIFTY 500 CONSTITUENTS - Total: {len(stocks)} stocks")
    print(f"{'='*100}\n")
    print(f"{'Symbol':<15} {'LTP':>10} {'Prev Close':>12} {'Change %':>10} {'Volume':>15} {'Date':>12}")
    print('-' * 100)
    
    for row in stocks:
        symbol = row[0]
        ltp = float(row[1]) if row[1] else 0
        prev_close = float(row[2]) if row[2] else 0
        change_pct = float(row[3]) if row[3] else 0
        volume = row[4] if row[4] else 0
        data_date = row[5]
        
        print(f"{symbol:<15} {ltp:>10.2f} {prev_close:>12.2f} {change_pct:>10.2f} {volume:>15,} {data_date!s:>12}")
    
    conn.close()
    
    print(f"\n{'='*100}\n")

if __name__ == '__main__':
    list_nifty500_stocks()
