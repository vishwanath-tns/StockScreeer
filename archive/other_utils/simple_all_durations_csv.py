"""
Simple All Durations Nifty 50 CSV Report Generator
=================================================

Generates CSV report with momentum data for all 6 timeframes.
"""

import sys
import os
from datetime import datetime
import pandas as pd

sys.path.append('.')

from services.market_breadth_service import get_engine
from sqlalchemy import text

def generate_simple_all_durations_csv():
    """Generate simple CSV with all momentum durations"""
    
    print("NIFTY 50 ALL DURATIONS CSV GENERATOR")
    print("=" * 45)
    print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("")
    
    # Complete Nifty 50 with sectors
    nifty50_sectors = {
        # Banking (6)
        'AXISBANK': 'Banking', 'HDFCBANK': 'Banking', 'ICICIBANK': 'Banking', 
        'INDUSINDBK': 'Banking', 'KOTAKBANK': 'Banking', 'SBIN': 'Banking',
        
        # Financial Services (4)
        'BAJFINANCE': 'Financial Services', 'BAJAJFINSV': 'Financial Services', 
        'HDFCLIFE': 'Financial Services', 'SBILIFE': 'Financial Services',
        
        # IT Services (5)
        'INFY': 'IT Services', 'TCS': 'IT Services', 'TECHM': 'IT Services',
        'HCLTECH': 'IT Services', 'WIPRO': 'IT Services',
        
        # Oil & Gas (3)
        'RELIANCE': 'Oil & Gas', 'ONGC': 'Oil & Gas', 'BPCL': 'Oil & Gas',
        
        # Metals & Mining (4)
        'TATASTEEL': 'Metals & Mining', 'JSWSTEEL': 'Metals & Mining',
        'HINDALCO': 'Metals & Mining', 'COALINDIA': 'Metals & Mining',
        
        # Automotive (5)
        'MARUTI': 'Automotive', 'BAJAJ-AUTO': 'Automotive', 'M&M': 'Automotive',
        'HEROMOTOCO': 'Automotive', 'EICHERMOT': 'Automotive',
        
        # Pharmaceuticals (4)
        'SUNPHARMA': 'Pharmaceuticals', 'DRREDDY': 'Pharmaceuticals',
        'CIPLA': 'Pharmaceuticals', 'DIVISLAB': 'Pharmaceuticals',
        
        # FMCG (5)
        'HINDUNILVR': 'FMCG', 'BRITANNIA': 'FMCG', 'NESTLEIND': 'FMCG',
        'ITC': 'FMCG', 'TATACONSUM': 'FMCG',
        
        # Others
        'BHARTIARTL': 'Telecom',
        'NTPC': 'Power', 'POWERGRID': 'Power',
        'ULTRACEMCO': 'Cement', 'GRASIM': 'Cement',
        'LT': 'Infrastructure',
        'ASIANPAINT': 'Paints',
        'UPL': 'Chemicals',
        'TITAN': 'Consumer Goods',
        'ADANIPORTS': 'Logistics'
    }
    
    print(f"Total Nifty 50 stocks mapped: {len(nifty50_sectors)}")
    
    # Fetch all momentum data from database
    engine = get_engine()
    
    with engine.connect() as conn:
        # Get all today's momentum data
        momentum_query = text("""
            SELECT symbol, duration_type, percentage_change, volume_surge_factor, overall_rank
            FROM momentum_analysis 
            WHERE DATE(calculation_date) = CURDATE()
            ORDER BY symbol, 
                CASE duration_type 
                    WHEN '1W' THEN 1
                    WHEN '1M' THEN 2 
                    WHEN '3M' THEN 3
                    WHEN '6M' THEN 4
                    WHEN '9M' THEN 5
                    WHEN '12M' THEN 6
                END
        """)
        
        momentum_data = conn.execute(momentum_query).fetchall()
    
    print(f"Found {len(momentum_data)} momentum records in database")
    
    if not momentum_data:
        print("❌ No momentum data found for today!")
        return
    
    # Process momentum data into structured format
    momentum_dict = {}
    
    for symbol, duration, pct_change, vol_surge, rank in momentum_data:
        if symbol not in momentum_dict:
            momentum_dict[symbol] = {}
        
        momentum_dict[symbol][duration] = {
            'percentage_change': float(pct_change) if pct_change is not None else None,
            'volume_surge_factor': float(vol_surge) if vol_surge is not None else None,
            'overall_rank': int(rank) if rank is not None else None
        }
    
    # Create comprehensive dataset
    report_data = []
    
    for symbol, sector in nifty50_sectors.items():
        if symbol in momentum_dict:
            row = {
                'Symbol': symbol,
                'Sector': sector,
                'Momentum_1W_Percent': momentum_dict[symbol].get('1W', {}).get('percentage_change', ''),
                'Momentum_1M_Percent': momentum_dict[symbol].get('1M', {}).get('percentage_change', ''),
                'Momentum_3M_Percent': momentum_dict[symbol].get('3M', {}).get('percentage_change', ''),
                'Momentum_6M_Percent': momentum_dict[symbol].get('6M', {}).get('percentage_change', ''),
                'Momentum_9M_Percent': momentum_dict[symbol].get('9M', {}).get('percentage_change', ''),
                'Momentum_12M_Percent': momentum_dict[symbol].get('12M', {}).get('percentage_change', ''),
                'Volume_Surge_1W': momentum_dict[symbol].get('1W', {}).get('volume_surge_factor', ''),
                'Volume_Surge_1M': momentum_dict[symbol].get('1M', {}).get('volume_surge_factor', ''),
                'Overall_Rank_1M': momentum_dict[symbol].get('1M', {}).get('overall_rank', ''),
                'Data_Available': 'Yes'
            }
        else:
            row = {
                'Symbol': symbol,
                'Sector': sector,
                'Momentum_1W_Percent': '',
                'Momentum_1M_Percent': '',
                'Momentum_3M_Percent': '',
                'Momentum_6M_Percent': '',
                'Momentum_9M_Percent': '',
                'Momentum_12M_Percent': '',
                'Volume_Surge_1W': '',
                'Volume_Surge_1M': '',
                'Overall_Rank_1M': '',
                'Data_Available': 'No'
            }
        
        report_data.append(row)
    
    # Create DataFrame
    df = pd.DataFrame(report_data)
    
    # Sort by 1M momentum in descending order (handle empty values)
    df['Momentum_1M_Numeric'] = pd.to_numeric(df['Momentum_1M_Percent'], errors='coerce')
    df = df.sort_values('Momentum_1M_Numeric', ascending=False, na_position='last')
    df = df.drop('Momentum_1M_Numeric', axis=1)  # Remove helper column
    
    # Generate timestamp for files
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    # Save comprehensive CSV
    csv_filename = f"reports/nifty50_all_durations_complete_{timestamp}.csv"
    df.to_csv(csv_filename, index=False)
    
    print(f"\n✅ CSV Report Generated: {csv_filename}")
    
    # Display top and bottom performers for each duration
    print(f"\n📊 MOMENTUM LEADERS BY DURATION:")
    print("-" * 40)
    
    durations = ['1W', '1M', '3M', '6M', '9M', '12M']
    
    for duration in durations:
        col_name = f'Momentum_{duration}_Percent'
        
        # Convert to numeric and get top 3
        df_numeric = df[df[col_name] != ''].copy()
        if len(df_numeric) > 0:
            df_numeric[f'{duration}_numeric'] = pd.to_numeric(df_numeric[col_name], errors='coerce')
            top_3 = df_numeric.nlargest(3, f'{duration}_numeric')
            
            print(f"\n{duration} Top 3:")
            for i, (_, row) in enumerate(top_3.iterrows(), 1):
                momentum = row[col_name]
                symbol = row['Symbol']
                sector = row['Sector']
                print(f"  {i}. {symbol:12} {momentum:+7.2f}% ({sector})")
    
    # Display summary statistics
    print(f"\n📈 SUMMARY STATISTICS:")
    print("-" * 25)
    
    for duration in durations:
        col_name = f'Momentum_{duration}_Percent'
        valid_data = df[df[col_name] != '']
        
        if len(valid_data) > 0:
            valid_data_numeric = pd.to_numeric(valid_data[col_name], errors='coerce')
            valid_data_numeric = valid_data_numeric.dropna()
            
            if len(valid_data_numeric) > 0:
                avg_momentum = valid_data_numeric.mean()
                positive_count = len(valid_data_numeric[valid_data_numeric > 0])
                total_count = len(valid_data_numeric)
                positive_ratio = positive_count / total_count * 100
                
                print(f"{duration}: Avg {avg_momentum:+6.2f}% | Positive {positive_count}/{total_count} ({positive_ratio:4.1f}%)")
    
    print(f"\n🎉 COMPLETE ALL DURATIONS REPORT READY!")
    print(f"   Database contains momentum data for all 6 timeframes.")
    print(f"   {len(df)} stocks analyzed across {len(durations)} duration periods.")
    print(f"   CSV saved: {csv_filename}")
    
    return csv_filename


if __name__ == "__main__":
    generate_simple_all_durations_csv()