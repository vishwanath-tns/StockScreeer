"""
Complete All Durations Nifty 50 Report Generator
==============================================

Generates comprehensive reports with momentum data for all 6 timeframes:
1W, 1M, 3M, 6M, 9M, 12M
"""

import sys
import os
from datetime import datetime
import pandas as pd

sys.path.append('.')

from services.market_breadth_service import get_engine
from sqlalchemy import text

def generate_complete_all_durations_report():
    """Generate comprehensive report with all momentum durations"""
    
    print("NIFTY 50 COMPLETE ALL DURATIONS REPORT")
    print("=" * 50)
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
    print("")
    
    # Fetch all momentum data from database
    engine = get_engine()
    
    with engine.connect() as conn:
        # Get all today's momentum data
        momentum_query = text("""
            SELECT symbol, duration_type, percentage_change, volume_surge_factor,
                   start_price, end_price, high_price, low_price,
                   price_volatility, overall_rank
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
    
    for symbol, duration, pct_change, vol_surge, start_price, end_price, high_price, low_price, volatility, rank in momentum_data:
        if symbol not in momentum_dict:
            momentum_dict[symbol] = {}
        
        momentum_dict[symbol][duration] = {
            'percentage_change': pct_change,
            'volume_surge_factor': vol_surge,
            'start_price': start_price,
            'end_price': end_price,
            'high_price': high_price,
            'low_price': low_price,
            'volatility': volatility,
            'overall_rank': rank
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
                'Volatility_1M': momentum_dict[symbol].get('1M', {}).get('volatility', ''),
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
                'Volatility_1M': '',
                'Overall_Rank_1M': '',
                'Data_Available': 'No'
            }
        
        report_data.append(row)
    
    # Create DataFrame
    df = pd.DataFrame(report_data)
    
    # Sort by 1M momentum in descending order
    df = df.sort_values('Momentum_1M_Percent', ascending=False, na_position='last')
    
    # Generate timestamp for files
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    # Save comprehensive CSV
    csv_filename = f"reports/nifty50_all_durations_comprehensive_{timestamp}.csv"
    df.to_csv(csv_filename, index=False)
    
    # Display sample data with all durations
    print("SAMPLE DATA (Top 10 by 1M momentum):")
    print("-" * 50)
    
    for i, row in df.head(10).iterrows():
        symbol = row['Symbol']
        sector = row['Sector']
        print(f"\n{symbol:12} ({sector})")
        if row['Data_Available'] == 'Yes':
            durations = ['1W', '1M', '3M', '6M', '9M', '12M']
            for duration in durations:
                col_name = f'Momentum_{duration}_Percent'
                if col_name in row and row[col_name] != '':
                    value = row[col_name]
                    print(f"  {duration:3}: {value:+7.2f}%")
                else:
                    print(f"  {duration:3}:     N/A")
        else:
            print("  No momentum data available")
    
    # Generate analysis summary
    analysis_filename = f"reports/nifty50_all_durations_analysis_{timestamp}.txt"
    
    with open(analysis_filename, 'w') as f:
        f.write("NIFTY 50 COMPLETE ALL DURATIONS MOMENTUM ANALYSIS\n")
        f.write("=" * 60 + "\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Total Stocks: {len(nifty50_sectors)}\n\n")
        
        # Calculate duration statistics
        durations = ['1W', '1M', '3M', '6M', '9M', '12M']
        
        f.write("MOMENTUM DURATION ANALYSIS\n")
        f.write("-" * 30 + "\n")
        
        for duration in durations:
            col_name = f'Momentum_{duration}_Percent'
            valid_data = df[df[col_name] != '']
            
            if len(valid_data) > 0:
                avg_momentum = valid_data[col_name].mean()
                positive_count = len(valid_data[valid_data[col_name] > 0])
                total_count = len(valid_data)
                positive_ratio = positive_count / total_count * 100
                
                # Get top 3 performers for this duration
                top_3 = valid_data.nlargest(3, col_name)
                
                f.write(f"\n{duration} Analysis ({total_count} stocks):\n")
                f.write(f"  Average momentum: {avg_momentum:+.2f}%\n")
                f.write(f"  Positive stocks: {positive_count}/{total_count} ({positive_ratio:.1f}%)\n")
                f.write(f"  Top performers:\n")
                
                for idx, (_, row) in enumerate(top_3.iterrows(), 1):
                    momentum = row[col_name]
                    f.write(f"    {idx}. {row['Symbol']:12} {momentum:+7.2f}% ({row['Sector']})\n")
        
        # Sector analysis for each duration
        f.write(f"\n\nSECTOR PERFORMANCE BY DURATION\n")
        f.write("=" * 35 + "\n")
        
        sectors = df['Sector'].unique()
        
        for duration in durations:
            f.write(f"\n{duration} Sector Rankings:\n")
            f.write("-" * 20 + "\n")
            
            col_name = f'Momentum_{duration}_Percent'
            sector_performance = []
            
            for sector in sectors:
                sector_data = df[(df['Sector'] == sector) & (df[col_name] != '')]
                
                if len(sector_data) > 0:
                    avg_momentum = sector_data[col_name].mean()
                    stock_count = len(sector_data)
                    sector_performance.append((sector, avg_momentum, stock_count))
            
            # Sort by average momentum
            sector_performance.sort(key=lambda x: x[1], reverse=True)
            
            for i, (sector, avg_momentum, count) in enumerate(sector_performance[:10], 1):
                f.write(f"  {i:2}. {sector:20} {avg_momentum:+7.2f}% ({count} stocks)\n")
    
    print(f"\nFiles generated:")
    print(f"  📊 Complete CSV: {csv_filename}")
    print(f"  📋 Analysis: {analysis_filename}")
    
    # Display key insights
    print(f"\n📈 KEY INSIGHTS (All Durations):")
    print("-" * 40)
    
    # Find best performing stock across all durations
    best_performers = {}
    for duration in durations:
        col_name = f'Momentum_{duration}_Percent'
        valid_data = df[df[col_name] != '']
        if len(valid_data) > 0:
            best_stock = valid_data.loc[valid_data[col_name].idxmax()]
            best_performers[duration] = {
                'symbol': best_stock['Symbol'],
                'sector': best_stock['Sector'],
                'momentum': best_stock[col_name]
            }
    
    print("\nTop performer by duration:")
    for duration in durations:
        if duration in best_performers:
            bp = best_performers[duration]
            print(f"  {duration:3}: {bp['symbol']:12} {bp['momentum']:+7.2f}% ({bp['sector']})")
    
    print(f"\n🎉 COMPLETE ALL DURATIONS REPORT GENERATED!")
    print(f"   Database contains momentum data for all 6 timeframes.")
    print(f"   {len(df)} stocks analyzed across {len(durations)} duration periods.")


if __name__ == "__main__":
    generate_complete_all_durations_report()