import sys
import os
import pandas as pd
from sqlalchemy import text
from datetime import datetime

# Adjust path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mean_reversion.data_access.data_loader import DatabaseLoader
from utilities.nifty500_stocks_list import NIFTY_500_STOCKS

def check_data_years():
    print("Connecting to database...")
    db = DatabaseLoader()
    engine = db.get_engine()
    
    print("Querying data duration for Nifty 500 stocks...")
    
    results = []
    
    # We can do this with a single efficient query instead of 500 queries
    # Constructing a large IN clause or just grouping by symbol
    query = """
    SELECT 
        symbol, 
        MIN(date) as start_date, 
        MAX(date) as end_date,
        COUNT(*) as count
    FROM yfinance_daily_quotes 
    GROUP BY symbol
    """
    
    try:
        df = pd.read_sql(query, engine)
    except Exception as e:
        print(f"Error querying database: {e}")
        return

    print(f"\nFound data for {len(df)} symbols in the database.")
    
    summary_data = []
    
    for symbol in NIFTY_500_STOCKS:
        # Match symbol (handle .NS suffix in DB vs List)
        # DB usually has .NS for yahoo data, list doesn't
        search_sym = symbol if symbol.endswith(('.NS','.BO')) else f"{symbol}.NS"
        
        row = df[df['symbol'] == search_sym]
        
        if not row.empty:
            start = pd.to_datetime(row.iloc[0]['start_date'])
            end = pd.to_datetime(row.iloc[0]['end_date'])
            duration = (end - start).days / 365.25
            count = row.iloc[0]['count']
            
            summary_data.append({
                'Symbol': symbol,
                'Start': start.strftime('%Y-%m-%d'),
                'End': end.strftime('%Y-%m-%d'),
                'Years': round(duration, 1),
                'Rows': count
            })
        else:
            summary_data.append({
                'Symbol': symbol,
                'Start': '-',
                'End': '-',
                'Years': 0,
                'Rows': 0
            })
            
    summary_df = pd.DataFrame(summary_data)
    
    # Analysis
    print("\nData Availability Summary:")
    print("="*60)
    print(f"Total Stocks Checked: {len(NIFTY_500_STOCKS)}")
    print(f"Stocks with Data:     {len(summary_df[summary_df['Years'] > 0])}")
    print("-" * 30)
    
    # Binning
    bins = [0, 1, 5, 10, 20, 100]
    labels = ['< 1 yr', '1-5 yrs', '5-10 yrs', '10-20 yrs', '20+ yrs']
    summary_df['Duration_Bin'] = pd.cut(summary_df['Years'], bins=bins, labels=labels, right=False)
    
    dist = summary_df['Duration_Bin'].value_counts().sort_index()
    print("Duration Distribution:")
    for label, count in dist.items():
        print(f"{label:<10}: {count} stocks")
        
    print("\nTop 10 Stocks by Data Duration:")
    print(summary_df.nlargest(10, 'Years')[['Symbol', 'Years', 'Start']])
    
    print("\nStocks with NO Data:")
    no_data = summary_df[summary_df['Years'] == 0]['Symbol'].tolist()
    print(no_data[:20], "..." if len(no_data) > 20 else "")

if __name__ == "__main__":
    check_data_years()
