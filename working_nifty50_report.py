"""
Simple Working Nifty 50 Report Generator
======================================

This will generate a complete Nifty 50 report with actual momentum data
using the proven working calculation methods.
"""

import sys
import os
from datetime import datetime
import pandas as pd

sys.path.append('.')

# Use the proven working quick scan approach
def generate_working_nifty50_report():
    """Generate Nifty 50 report using proven working methods"""
    
    print("Generating Nifty 50 Report with Live Momentum Data")
    print("=" * 55)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("")
    
    # Import the working quick scan
    try:
        # Run the proven working momentum calculation
        import subprocess
        import sys
        
        print("Step 1: Running proven momentum calculations...")
        result = subprocess.run([sys.executable, "quick_nifty50_scan.py"], 
                              capture_output=True, text=True, cwd=".")
        
        if result.returncode == 0:
            print("✅ Momentum calculations completed successfully!")
            print("")
            
            # Now generate report from database
            print("Step 2: Generating comprehensive report from calculated data...")
            
            from services.market_breadth_service import get_engine
            
            engine = get_engine()
            
            with engine.connect() as conn:
                # Get the fresh momentum data
                query = """
                SELECT symbol, duration_type, percentage_change, 
                       start_price, end_price, calculation_date,
                       avg_volume, volume_surge_factor
                FROM momentum_analysis 
                WHERE calculation_date = CURDATE()
                ORDER BY symbol, duration_type
                """
                
                df = pd.read_sql(query, conn)
                
                if len(df) == 0:
                    # Try getting latest data
                    query = """
                    SELECT symbol, duration_type, percentage_change, 
                           start_price, end_price, calculation_date,
                           avg_volume, volume_surge_factor
                    FROM momentum_analysis 
                    WHERE calculation_date = (SELECT MAX(calculation_date) FROM momentum_analysis)
                    ORDER BY symbol, duration_type
                    """
                    df = pd.read_sql(query, conn)
                
                print(f"✅ Retrieved {len(df)} momentum records from database")
                
                if len(df) > 0:
                    # Create comprehensive report
                    generate_comprehensive_report(df)
                else:
                    print("❌ No momentum data found in database")
                    
        else:
            print(f"❌ Momentum calculation failed: {result.stderr}")
            
    except Exception as e:
        print(f"❌ Error: {e}")


def generate_comprehensive_report(momentum_df):
    """Generate comprehensive report from momentum data"""
    
    # Nifty 50 sector mapping
    sector_mapping = {
        # Banking
        'AXISBANK': 'Banking', 'HDFCBANK': 'Banking', 'ICICIBANK': 'Banking',
        'INDUSINDBK': 'Banking', 'KOTAKBANK': 'Banking', 'SBIN': 'Banking',
        
        # Financial Services
        'BAJFINANCE': 'Financial Services', 'BAJAJFINSV': 'Financial Services',
        'HDFCLIFE': 'Financial Services', 'SBILIFE': 'Financial Services',
        
        # IT Services
        'INFY': 'IT Services', 'TCS': 'IT Services', 'TECHM': 'IT Services',
        'HCLTECH': 'IT Services', 'WIPRO': 'IT Services',
        
        # Oil & Gas
        'RELIANCE': 'Oil & Gas', 'ONGC': 'Oil & Gas', 'BPCL': 'Oil & Gas',
        
        # Metals & Mining
        'TATASTEEL': 'Metals & Mining', 'JSWSTEEL': 'Metals & Mining',
        'HINDALCO': 'Metals & Mining', 'COALINDIA': 'Metals & Mining',
        
        # Automotive
        'MARUTI': 'Automotive', 'BAJAJ-AUTO': 'Automotive', 'M&M': 'Automotive',
        'HEROMOTOCO': 'Automotive', 'EICHERMOT': 'Automotive',
        
        # Pharmaceuticals
        'SUNPHARMA': 'Pharmaceuticals', 'DRREDDY': 'Pharmaceuticals',
        'CIPLA': 'Pharmaceuticals', 'DIVISLAB': 'Pharmaceuticals',
        
        # FMCG
        'HINDUNILVR': 'FMCG', 'BRITANNIA': 'FMCG', 'NESTLEIND': 'FMCG',
        'ITC': 'FMCG', 'TATACONSUM': 'FMCG',
        
        # Others
        'BHARTIARTL': 'Telecom', 'NTPC': 'Power', 'POWERGRID': 'Power',
        'ULTRACEMCO': 'Cement', 'GRASIM': 'Cement', 'LT': 'Infrastructure',
        'ASIANPAINT': 'Paints', 'UPL': 'Chemicals', 'TITAN': 'Consumer Goods',
        'ADANIPORTS': 'Logistics'
    }
    
    # All Nifty 50 stocks
    all_nifty50 = list(sector_mapping.keys())
    
    # Create comprehensive dataset
    report_data = []
    
    for symbol in all_nifty50:
        sector = sector_mapping[symbol]
        
        # Get momentum data for this stock
        stock_data = momentum_df[momentum_df['symbol'] == symbol]
        
        row = {
            'Symbol': symbol,
            'Sector': sector,
            'Momentum_1W_Percent': None,
            'Momentum_1M_Percent': None,
            'Momentum_3M_Percent': None,
            'Momentum_6M_Percent': None,
            'Volume_Surge_Factor': None,
            'Start_Price_1M': None,
            'End_Price_1M': None
        }
        
        for _, momentum_row in stock_data.iterrows():
            duration = momentum_row['duration_type']
            momentum = momentum_row['percentage_change']
            
            if duration == '1W':
                row['Momentum_1W_Percent'] = momentum
            elif duration == '1M':
                row['Momentum_1M_Percent'] = momentum
                row['Start_Price_1M'] = momentum_row.get('start_price', None)
                row['End_Price_1M'] = momentum_row.get('end_price', None)
                row['Volume_Surge_Factor'] = momentum_row.get('volume_surge_factor', None)
            elif duration == '3M':
                row['Momentum_3M_Percent'] = momentum
            elif duration == '6M':
                row['Momentum_6M_Percent'] = momentum
        
        report_data.append(row)
    
    # Create DataFrame
    report_df = pd.DataFrame(report_data)
    
    # Generate timestamp
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    os.makedirs("reports", exist_ok=True)
    
    # Save CSV
    csv_filename = f"reports/nifty50_working_report_{timestamp}.csv"
    report_df.to_csv(csv_filename, index=False)
    
    print(f"✅ CSV Report saved: {csv_filename}")
    
    # Generate analysis
    analysis_text = generate_sector_analysis(report_df)
    
    # Save analysis
    txt_filename = f"reports/nifty50_working_analysis_{timestamp}.txt"
    with open(txt_filename, 'w', encoding='utf-8') as f:
        f.write(analysis_text)
    
    print(f"✅ Analysis saved: {txt_filename}")
    
    # Display analysis
    print("")
    print("="*60)
    print(analysis_text)
    
    # Summary
    stocks_with_data = len(report_df[(report_df['Momentum_1W_Percent'].notna()) | 
                                   (report_df['Momentum_1M_Percent'].notna())])
    
    print(f"\n🎉 COMPREHENSIVE REPORT COMPLETE!")
    print(f"📊 Stocks with momentum data: {stocks_with_data}/{len(report_df)}")
    print(f"📁 Files created:")
    print(f"   📄 CSV: {csv_filename}")
    print(f"   📋 TXT: {txt_filename}")


def generate_sector_analysis(df):
    """Generate sector analysis text"""
    
    report = []
    report.append("NIFTY 50 COMPREHENSIVE SECTOR ANALYSIS")
    report.append("=" * 50)
    report.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report.append(f"Total Stocks: {len(df)}")
    report.append("")
    
    # Market overview
    stocks_1w = df[df['Momentum_1W_Percent'].notna()]
    stocks_1m = df[df['Momentum_1M_Percent'].notna()]
    
    if len(stocks_1w) > 0:
        avg_1w = stocks_1w['Momentum_1W_Percent'].mean()
        positive_1w = (stocks_1w['Momentum_1W_Percent'] > 0).sum()
        
        report.append("MARKET OVERVIEW - 1 WEEK")
        report.append("-" * 30)
        report.append(f"Average Momentum: {avg_1w:+.2f}%")
        report.append(f"Stocks with positive momentum: {positive_1w}/{len(stocks_1w)} ({positive_1w/len(stocks_1w)*100:.1f}%)")
        
        sentiment = "Bullish" if positive_1w/len(stocks_1w) > 0.5 else "Bearish"
        report.append(f"Market Sentiment: {sentiment}")
        report.append("")
    
    if len(stocks_1m) > 0:
        avg_1m = stocks_1m['Momentum_1M_Percent'].mean()
        positive_1m = (stocks_1m['Momentum_1M_Percent'] > 0).sum()
        
        report.append("MARKET OVERVIEW - 1 MONTH")
        report.append("-" * 30)
        report.append(f"Average Momentum: {avg_1m:+.2f}%")
        report.append(f"Stocks with positive momentum: {positive_1m}/{len(stocks_1m)} ({positive_1m/len(stocks_1m)*100:.1f}%)")
        
        sentiment = "Bullish" if positive_1m/len(stocks_1m) > 0.5 else "Bearish"
        report.append(f"Market Sentiment: {sentiment}")
        report.append("")
    
    # Sector analysis
    report.append("SECTOR-WISE PERFORMANCE")
    report.append("=" * 30)
    
    sector_performance = []
    
    for sector in df['Sector'].unique():
        sector_data = df[df['Sector'] == sector]
        
        report.append(f"\n{sector.upper()}")
        report.append("-" * len(sector))
        report.append(f"Stocks: {len(sector_data)}")
        
        # 1M analysis (main timeframe)
        sector_1m = sector_data[sector_data['Momentum_1M_Percent'].notna()]
        
        if len(sector_1m) > 0:
            avg_1m = sector_1m['Momentum_1M_Percent'].mean()
            positive_1m = (sector_1m['Momentum_1M_Percent'] > 0).sum()
            
            report.append(f"1M Average: {avg_1m:+.2f}%")
            report.append(f"1M Positive: {positive_1m}/{len(sector_1m)} stocks")
            
            sector_performance.append((sector, avg_1m, len(sector_1m)))
            
            # Best performer
            best_stock = sector_1m.loc[sector_1m['Momentum_1M_Percent'].idxmax()]
            report.append(f"Top performer: {best_stock['Symbol']} ({best_stock['Momentum_1M_Percent']:+.2f}%)")
        
        # Individual stocks
        report.append("\nIndividual Performance:")
        for _, stock in sector_data.iterrows():
            mom_1w = f"{stock['Momentum_1W_Percent']:+.2f}%" if pd.notna(stock['Momentum_1W_Percent']) else "N/A"
            mom_1m = f"{stock['Momentum_1M_Percent']:+.2f}%" if pd.notna(stock['Momentum_1M_Percent']) else "N/A"
            report.append(f"  {stock['Symbol']:12} | 1W: {mom_1w:>8} | 1M: {mom_1m:>8}")
    
    # Top sectors
    if sector_performance:
        report.append("\n\nTOP PERFORMING SECTORS (1M)")
        report.append("=" * 35)
        
        sector_performance.sort(key=lambda x: x[1], reverse=True)
        
        for i, (sector, avg_perf, count) in enumerate(sector_performance, 1):
            if count > 0:
                report.append(f"{i:2d}. {sector:20} {avg_perf:+.2f}% ({count} stocks)")
    
    return "\n".join(report)


if __name__ == "__main__":
    generate_working_nifty50_report()