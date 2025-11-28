#!/usr/bin/env python3
"""
Get Nifty 500 Stocks List
=========================

This script extracts the top 500 most actively traded stocks from the database
as a proxy for Nifty 500, since the exact Nifty 500 index may not be in the database.
"""

import sys
import os
sys.path.append('.')

from services.market_breadth_service import get_engine
from sqlalchemy import text

def get_nifty500_stocks():
    """Get the top 500 most actively traded stocks"""
    
    print("🔍 Getting Nifty 500 equivalent stocks from database...")
    
    engine = get_engine()
    
    with engine.connect() as conn:
        # Check total EQ stocks available
        result = conn.execute(text("""
            SELECT COUNT(DISTINCT symbol) 
            FROM nse_equity_bhavcopy_full 
            WHERE series = 'EQ'
        """))
        total_stocks = result.fetchone()[0]
        print(f"📊 Total EQ stocks in database: {total_stocks}")
        
        # Get top 500 stocks by average trading volume (last 30 days)
        result = conn.execute(text("""
            SELECT 
                symbol,
                AVG(ttl_trd_qnty) as avg_volume,
                AVG(turnover_lacs) as avg_turnover,
                COUNT(*) as trading_days
            FROM nse_equity_bhavcopy_full 
            WHERE series = 'EQ' 
                AND trade_date >= DATE_SUB(CURDATE(), INTERVAL 30 DAY)
                AND ttl_trd_qnty > 0
            GROUP BY symbol 
            HAVING trading_days >= 15  -- At least 15 trading days
            ORDER BY avg_volume DESC 
            LIMIT 500
        """))
        
        top500_data = result.fetchall()
        top500_stocks = [row[0] for row in top500_data]
        
        print(f"✅ Retrieved top {len(top500_stocks)} most active stocks")
        print()
        
        # Show some statistics
        print("📈 Top 20 Most Active Stocks:")
        print("-" * 60)
        print(f"{'Rank':<4} {'Symbol':<12} {'Avg Volume':<15} {'Avg Turnover':<12}")
        print("-" * 60)
        
        for i, (symbol, avg_vol, avg_turnover, days) in enumerate(top500_data[:20]):
            print(f"{i+1:2d}.  {symbol:<12} {int(avg_vol):>12,} {avg_turnover:>10.2f}")
        
        print("-" * 60)
        print()
        
        # Save to file
        with open('nifty500_stocks.txt', 'w') as f:
            f.write("# Nifty 500 Equivalent Stocks (Top 500 by Volume)\n")
            f.write("# Generated from NSE equity database\n")
            f.write("\n")
            for stock in top500_stocks:
                f.write(f"{stock}\n")
        
        print(f"💾 Saved {len(top500_stocks)} stocks to 'nifty500_stocks.txt'")
        
        return top500_stocks

def create_nifty500_python_list():
    """Create a Python list format for easy use in code"""
    
    stocks = get_nifty500_stocks()
    
    # Create Python list format
    python_list = "NIFTY_500_STOCKS = [\n"
    
    # Group by batches of 10 for readability
    for i in range(0, len(stocks), 10):
        batch = stocks[i:i+10]
        python_list += "    "
        python_list += ", ".join(f"'{stock}'" for stock in batch)
        if i + 10 < len(stocks):
            python_list += ","
        python_list += "\n"
    
    python_list += "]\n"
    
    # Save Python format
    with open('nifty500_stocks_list.py', 'w') as f:
        f.write(f'"""\nNifty 500 Equivalent Stocks List\n================================\n\n')
        f.write(f'Top 500 most actively traded stocks from NSE equity database.\n')
        f.write(f'Generated on: {__import__("datetime").datetime.now().strftime("%Y-%m-%d %H:%M:%S")}\n')
        f.write(f'Total stocks: {len(stocks)}\n"""\n\n')
        f.write(python_list)
        f.write(f'\n# Total stocks: {len(stocks)}\n')
        f.write(f'print(f"Nifty 500 equivalent stocks loaded: {{len(NIFTY_500_STOCKS)}} stocks")\n')
    
    print(f"🐍 Created Python list in 'nifty500_stocks_list.py'")
    
    return stocks

if __name__ == "__main__":
    create_nifty500_python_list()