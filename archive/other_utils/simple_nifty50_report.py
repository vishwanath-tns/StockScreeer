"""
Simple Nifty 50 Sector Report Using Existing Database Data
========================================================

This generates a Nifty 50 sector report using the momentum data that's 
already available in the database from previous successful runs.
"""

import sys
import os
from datetime import datetime
import pandas as pd

sys.path.append('.')

from services.market_breadth_service import get_engine

def create_nifty50_report_from_db():
    """Create Nifty 50 sector report from existing database data"""
    
    print("NIFTY 50 COMPREHENSIVE SECTOR REPORT")
    print("=" * 50)
    print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("")
    
    # Complete Nifty 50 sector mapping
    sector_mapping = {
        # Banking (6 stocks)
        'AXISBANK': 'Banking', 'HDFCBANK': 'Banking', 'ICICIBANK': 'Banking',
        'INDUSINDBK': 'Banking', 'KOTAKBANK': 'Banking', 'SBIN': 'Banking',
        
        # Financial Services (4 stocks)
        'BAJFINANCE': 'Financial Services', 'BAJAJFINSV': 'Financial Services',
        'HDFCLIFE': 'Financial Services', 'SBILIFE': 'Financial Services',
        
        # IT Services (5 stocks)
        'INFY': 'IT Services', 'TCS': 'IT Services', 'TECHM': 'IT Services',
        'HCLTECH': 'IT Services', 'WIPRO': 'IT Services',
        
        # Oil & Gas (3 stocks)
        'RELIANCE': 'Oil & Gas', 'ONGC': 'Oil & Gas', 'BPCL': 'Oil & Gas',
        
        # Metals & Mining (4 stocks)
        'TATASTEEL': 'Metals & Mining', 'JSWSTEEL': 'Metals & Mining',
        'HINDALCO': 'Metals & Mining', 'COALINDIA': 'Metals & Mining',
        
        # Automotive (5 stocks)
        'MARUTI': 'Automotive', 'BAJAJ-AUTO': 'Automotive', 'M&M': 'Automotive',
        'HEROMOTOCO': 'Automotive', 'EICHERMOT': 'Automotive',
        
        # Pharmaceuticals (4 stocks)
        'SUNPHARMA': 'Pharmaceuticals', 'DRREDDY': 'Pharmaceuticals',
        'CIPLA': 'Pharmaceuticals', 'DIVISLAB': 'Pharmaceuticals',
        
        # FMCG (5 stocks)
        'HINDUNILVR': 'FMCG', 'BRITANNIA': 'FMCG', 'NESTLEIND': 'FMCG',
        'ITC': 'FMCG', 'TATACONSUM': 'FMCG',
        
        # Others
        'BHARTIARTL': 'Telecom', 'NTPC': 'Power', 'POWERGRID': 'Power',
        'ULTRACEMCO': 'Cement', 'GRASIM': 'Cement', 'LT': 'Infrastructure',
        'ASIANPAINT': 'Paints', 'UPL': 'Chemicals', 'TITAN': 'Consumer Goods',
        'ADANIPORTS': 'Logistics'
    }
    
    # Get data from database
    engine = get_engine()
    
    try:
        with engine.connect() as conn:
            # Get momentum data
            query = """
            SELECT symbol, duration_type, percentage_change, 
                   start_price, end_price, calculation_date
            FROM momentum_analysis 
            WHERE calculation_date = CURDATE() 
               OR calculation_date = (SELECT MAX(calculation_date) FROM momentum_analysis)
            ORDER BY symbol, duration_type
            """
            
            df = pd.read_sql(query, conn)
            
            if len(df) == 0:
                print("No momentum data found in database.")
                print("Run 'python quick_nifty50_scan.py' first to generate momentum data.")
                return
            
            print(f"Database momentum records: {len(df)}")
            print("")
            
            # Create pivot table for easier analysis
            pivot_df = df.pivot(index='symbol', columns='duration_type', values='percentage_change')
            
            # Market Overview
            print("MARKET OVERVIEW")
            print("-" * 30)
            
            all_symbols = pivot_df.index.tolist()
            print(f"Stocks with momentum data: {len(all_symbols)}")
            
            if '1W' in pivot_df.columns:
                week_data = pivot_df['1W'].dropna()
                if len(week_data) > 0:
                    avg_1w = week_data.mean()
                    positive_1w = (week_data > 0).sum()
                    print(f"1W Average: {avg_1w:+.2f}%")
                    print(f"1W Positive: {positive_1w}/{len(week_data)} ({positive_1w/len(week_data)*100:.1f}%)")
            
            if '1M' in pivot_df.columns:
                month_data = pivot_df['1M'].dropna()
                if len(month_data) > 0:
                    avg_1m = month_data.mean()
                    positive_1m = (month_data > 0).sum()
                    print(f"1M Average: {avg_1m:+.2f}%")
                    print(f"1M Positive: {positive_1m}/{len(month_data)} ({positive_1m/len(month_data)*100:.1f}%)")
            
            print("")
            
            # Sector Analysis
            print("SECTOR-WISE ANALYSIS")
            print("-" * 40)
            
            sector_data = {}
            for symbol in all_symbols:
                sector = sector_mapping.get(symbol, 'Other')
                if sector not in sector_data:
                    sector_data[sector] = []
                sector_data[sector].append(symbol)
            
            sector_performance = []
            
            for sector, symbols in sorted(sector_data.items()):
                print(f"{sector.upper()} ({len(symbols)} stocks)")
                
                sector_1w_values = []
                sector_1m_values = []
                
                for symbol in symbols:
                    if symbol in pivot_df.index:
                        row_data = pivot_df.loc[symbol]
                        
                        mom_1w = row_data.get('1W', None)
                        mom_1m = row_data.get('1M', None)
                        
                        if pd.notna(mom_1w):
                            sector_1w_values.append(mom_1w)
                        if pd.notna(mom_1m):
                            sector_1m_values.append(mom_1m)
                        
                        # Show individual stock performance
                        w1_str = f"{mom_1w:+.2f}%" if pd.notna(mom_1w) else "N/A"
                        m1_str = f"{mom_1m:+.2f}%" if pd.notna(mom_1m) else "N/A"
                        print(f"  {symbol:12} | 1W: {w1_str:>8} | 1M: {m1_str:>8}")
                
                # Sector averages
                if sector_1w_values:
                    avg_1w = sum(sector_1w_values) / len(sector_1w_values)
                    print(f"  Sector 1W Average: {avg_1w:+.2f}%")
                
                if sector_1m_values:
                    avg_1m = sum(sector_1m_values) / len(sector_1m_values)
                    print(f"  Sector 1M Average: {avg_1m:+.2f}%")
                    sector_performance.append((sector, avg_1m))
                
                print("")
            
            # Top performing sectors
            if sector_performance:
                print("TOP PERFORMING SECTORS (1M)")
                print("-" * 30)
                sector_performance.sort(key=lambda x: x[1], reverse=True)
                
                for i, (sector, performance) in enumerate(sector_performance, 1):
                    emoji = "🟢" if performance > 2 else "🟡" if performance > 0 else "🔴"
                    print(f"{i}. {sector:20} {performance:+.2f}%")
            
            # Export to CSV
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            os.makedirs("reports", exist_ok=True)
            
            csv_filename = f"reports/nifty50_database_report_{timestamp}.csv"
            
            # Prepare CSV data
            csv_data = []
            for symbol in pivot_df.index:
                sector = sector_mapping.get(symbol, 'Other')
                row = pivot_df.loc[symbol]
                
                csv_data.append({
                    'Symbol': symbol,
                    'Sector': sector,
                    'Momentum_1W': row.get('1W', None),
                    'Momentum_1M': row.get('1M', None),
                    'Momentum_3M': row.get('3M', None),
                    'Momentum_6M': row.get('6M', None)
                })
            
            csv_df = pd.DataFrame(csv_data)
            csv_df.to_csv(csv_filename, index=False)
            
            print(f"\nReport exported to: {csv_filename}")
            print(f"Analysis completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            
    except Exception as e:
        print(f"Error accessing database: {e}")
        print("Make sure the database is running and momentum data exists.")


if __name__ == "__main__":
    create_nifty50_report_from_db()