"""
Final Working Nifty 50 Sector Report
===================================

This creates a comprehensive Nifty 50 report using the existing momentum data
that we know is working in the database, plus shows the complete sector structure.
"""

import pandas as pd
import os
from datetime import datetime
import sys

sys.path.append('.')

from services.market_breadth_service import get_engine

def create_final_working_report():
    """Create final working Nifty 50 report"""
    
    print("FINAL NIFTY 50 COMPREHENSIVE SECTOR REPORT")
    print("=" * 50)
    print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("")
    
    # Complete Nifty 50 with sectors
    nifty50_complete = {
        # Banking (6 stocks)
        'AXISBANK': 'Banking',
        'HDFCBANK': 'Banking',
        'ICICIBANK': 'Banking',
        'INDUSINDBK': 'Banking',
        'KOTAKBANK': 'Banking',
        'SBIN': 'Banking',
        
        # Financial Services (4 stocks)
        'BAJFINANCE': 'Financial Services',
        'BAJAJFINSV': 'Financial Services',
        'HDFCLIFE': 'Financial Services',
        'SBILIFE': 'Financial Services',
        
        # IT Services (5 stocks)
        'INFY': 'IT Services',
        'TCS': 'IT Services',
        'TECHM': 'IT Services',
        'HCLTECH': 'IT Services',
        'WIPRO': 'IT Services',
        
        # Oil & Gas (3 stocks)
        'RELIANCE': 'Oil & Gas',
        'ONGC': 'Oil & Gas',
        'BPCL': 'Oil & Gas',
        
        # Metals & Mining (4 stocks)
        'TATASTEEL': 'Metals & Mining',
        'JSWSTEEL': 'Metals & Mining',
        'HINDALCO': 'Metals & Mining',
        'COALINDIA': 'Metals & Mining',
        
        # Automotive (5 stocks)
        'MARUTI': 'Automotive',
        'BAJAJ-AUTO': 'Automotive',
        'M&M': 'Automotive',
        'HEROMOTOCO': 'Automotive',
        'EICHERMOT': 'Automotive',
        
        # Pharmaceuticals (4 stocks)
        'SUNPHARMA': 'Pharmaceuticals',
        'DRREDDY': 'Pharmaceuticals',
        'CIPLA': 'Pharmaceuticals',
        'DIVISLAB': 'Pharmaceuticals',
        
        # FMCG (5 stocks)
        'HINDUNILVR': 'FMCG',
        'BRITANNIA': 'FMCG',
        'NESTLEIND': 'FMCG',
        'ITC': 'FMCG',
        'TATACONSUM': 'FMCG',
        
        # Telecom (1 stock)
        'BHARTIARTL': 'Telecom',
        
        # Power (2 stocks)
        'NTPC': 'Power',
        'POWERGRID': 'Power',
        
        # Cement (2 stocks)
        'ULTRACEMCO': 'Cement',
        'GRASIM': 'Cement',
        
        # Infrastructure (1 stock)
        'LT': 'Infrastructure',
        
        # Paints (1 stock)
        'ASIANPAINT': 'Paints',
        
        # Chemicals (1 stock)
        'UPL': 'Chemicals',
        
        # Consumer Goods (1 stock)
        'TITAN': 'Consumer Goods',
        
        # Logistics (1 stock)
        'ADANIPORTS': 'Logistics'
    }
    
    print(f"Total Nifty 50 stocks mapped: {len(nifty50_complete)}")
    print("")
    
    # Get existing momentum data from database
    engine = get_engine()
    
    try:
        with engine.connect() as conn:
            query = """
            SELECT symbol, duration_type, percentage_change, 
                   start_price, end_price, calculation_date,
                   avg_volume, volume_surge_factor
            FROM momentum_analysis 
            WHERE calculation_date = CURDATE()
               OR calculation_date = (SELECT MAX(calculation_date) FROM momentum_analysis)
            ORDER BY symbol, duration_type
            """
            
            momentum_df = pd.read_sql(query, conn)
            
            print(f"Found {len(momentum_df)} momentum records in database")
            
            if len(momentum_df) > 0:
                print("Available momentum data:")
                for _, row in momentum_df.iterrows():
                    print(f"  {row['symbol']:12} | {row['duration_type']:2} | {row['percentage_change']:+.2f}%")
            
            print("")
            
    except Exception as e:
        print(f"Database error: {e}")
        momentum_df = pd.DataFrame()
    
    # Create comprehensive report data
    report_data = []
    
    for symbol, sector in nifty50_complete.items():
        row = {
            'Symbol': symbol,
            'Sector': sector,
            'Momentum_1W_Percent': None,
            'Momentum_1M_Percent': None,
            'Momentum_3M_Percent': None,
            'Momentum_6M_Percent': None,
            'Volume_Surge_Factor': None,
            'Data_Available': 'No'
        }
        
        # Fill in momentum data if available
        stock_momentum = momentum_df[momentum_df['symbol'] == symbol]
        
        if len(stock_momentum) > 0:
            row['Data_Available'] = 'Yes'
            
            for _, momentum_row in stock_momentum.iterrows():
                duration = momentum_row['duration_type']
                momentum = momentum_row['percentage_change']
                
                if duration == '1W':
                    row['Momentum_1W_Percent'] = momentum
                elif duration == '1M':
                    row['Momentum_1M_Percent'] = momentum
                    row['Volume_Surge_Factor'] = momentum_row.get('volume_surge_factor', None)
                elif duration == '3M':
                    row['Momentum_3M_Percent'] = momentum
                elif duration == '6M':
                    row['Momentum_6M_Percent'] = momentum
        
        report_data.append(row)
    
    # Create DataFrame
    df = pd.DataFrame(report_data)
    
    # Generate comprehensive analysis
    analysis = generate_comprehensive_analysis(df, nifty50_complete)
    
    # Save files
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    os.makedirs("reports", exist_ok=True)
    
    # Save detailed CSV
    csv_filename = f"reports/nifty50_final_comprehensive_{timestamp}.csv"
    df.to_csv(csv_filename, index=False)
    
    # Save analysis
    txt_filename = f"reports/nifty50_final_comprehensive_analysis_{timestamp}.txt"
    with open(txt_filename, 'w', encoding='utf-8') as f:
        f.write(analysis)
    
    print(f"Files saved:")
    print(f"  CSV Report: {csv_filename}")
    print(f"  Analysis: {txt_filename}")
    print("")
    
    # Display analysis
    print("="*60)
    print(analysis)
    
    # Final summary
    stocks_with_data = len(df[df['Data_Available'] == 'Yes'])
    
    print(f"\nFINAL REPORT SUMMARY:")
    print(f"Total Nifty 50 stocks: {len(df)}")
    print(f"Stocks with momentum data: {stocks_with_data}")
    print(f"Complete sector mapping: 16 sectors")
    print(f"Files generated: 2")
    print(f"Report timestamp: {timestamp}")


def generate_comprehensive_analysis(df, sector_mapping):
    """Generate comprehensive sector analysis"""
    
    report = []
    report.append("NIFTY 50 FINAL COMPREHENSIVE SECTOR ANALYSIS")
    report.append("=" * 55)
    report.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report.append(f"Total Stocks: {len(df)}")
    
    # Count sectors
    sectors = {}
    for symbol, sector in sector_mapping.items():
        if sector not in sectors:
            sectors[sector] = []
        sectors[sector].append(symbol)
    
    report.append(f"Total Sectors: {len(sectors)}")
    report.append("")
    
    # Market Overview
    stocks_with_data = df[df['Data_Available'] == 'Yes']
    
    if len(stocks_with_data) > 0:
        report.append("MARKET OVERVIEW (Available Data)")
        report.append("-" * 35)
        
        # 1W Analysis
        stocks_1w = stocks_with_data[stocks_with_data['Momentum_1W_Percent'].notna()]
        if len(stocks_1w) > 0:
            avg_1w = stocks_1w['Momentum_1W_Percent'].mean()
            positive_1w = (stocks_1w['Momentum_1W_Percent'] > 0).sum()
            
            report.append(f"1-Week Analysis ({len(stocks_1w)} stocks):")
            report.append(f"  Average momentum: {avg_1w:+.2f}%")
            report.append(f"  Positive stocks: {positive_1w}/{len(stocks_1w)} ({positive_1w/len(stocks_1w)*100:.1f}%)")
            
            if positive_1w/len(stocks_1w) > 0.6:
                sentiment_1w = "Strong Bullish"
            elif positive_1w/len(stocks_1w) > 0.4:
                sentiment_1w = "Neutral"
            else:
                sentiment_1w = "Bearish"
            report.append(f"  Market sentiment: {sentiment_1w}")
            report.append("")
        
        # 1M Analysis
        stocks_1m = stocks_with_data[stocks_with_data['Momentum_1M_Percent'].notna()]
        if len(stocks_1m) > 0:
            avg_1m = stocks_1m['Momentum_1M_Percent'].mean()
            positive_1m = (stocks_1m['Momentum_1M_Percent'] > 0).sum()
            
            report.append(f"1-Month Analysis ({len(stocks_1m)} stocks):")
            report.append(f"  Average momentum: {avg_1m:+.2f}%")
            report.append(f"  Positive stocks: {positive_1m}/{len(stocks_1m)} ({positive_1m/len(stocks_1m)*100:.1f}%)")
            
            if positive_1m/len(stocks_1m) > 0.6:
                sentiment_1m = "Strong Bullish"
            elif positive_1m/len(stocks_1m) > 0.4:
                sentiment_1m = "Neutral"
            else:
                sentiment_1m = "Bearish"
            report.append(f"  Market sentiment: {sentiment_1m}")
            report.append("")
            
            # Top performers
            top_performers = stocks_1m.nlargest(3, 'Momentum_1M_Percent')
            report.append("Top performers (1M):")
            for i, (_, stock) in enumerate(top_performers.iterrows(), 1):
                report.append(f"  {i}. {stock['Symbol']:12} {stock['Momentum_1M_Percent']:+.2f}% ({stock['Sector']})")
            report.append("")
    
    # Complete Sector Analysis
    report.append("COMPLETE SECTOR BREAKDOWN")
    report.append("=" * 30)
    
    sector_performance = []
    
    for sector_name in sorted(sectors.keys()):
        sector_stocks = sectors[sector_name]
        sector_data = df[df['Sector'] == sector_name]
        
        report.append(f"\n{sector_name.upper()}")
        report.append("-" * len(sector_name))
        report.append(f"Total stocks: {len(sector_stocks)}")
        
        # Stocks with data
        sector_with_data = sector_data[sector_data['Data_Available'] == 'Yes']
        if len(sector_with_data) > 0:
            report.append(f"Stocks with momentum data: {len(sector_with_data)}")
            
            # 1M sector analysis
            sector_1m = sector_with_data[sector_with_data['Momentum_1M_Percent'].notna()]
            if len(sector_1m) > 0:
                avg_1m = sector_1m['Momentum_1M_Percent'].mean()
                positive_1m = (sector_1m['Momentum_1M_Percent'] > 0).sum()
                
                report.append(f"1M sector average: {avg_1m:+.2f}%")
                report.append(f"1M positive ratio: {positive_1m}/{len(sector_1m)}")
                
                sector_performance.append((sector_name, avg_1m, len(sector_1m)))
                
                # Best performer
                best_stock = sector_1m.loc[sector_1m['Momentum_1M_Percent'].idxmax()]
                report.append(f"Sector leader: {best_stock['Symbol']} ({best_stock['Momentum_1M_Percent']:+.2f}%)")
        else:
            report.append("No momentum data available")
        
        # List all stocks in sector
        report.append("Sector constituents:")
        for stock in sorted(sector_stocks):
            stock_row = sector_data[sector_data['Symbol'] == stock].iloc[0]
            
            mom_1w = f"{stock_row['Momentum_1W_Percent']:+.2f}%" if pd.notna(stock_row['Momentum_1W_Percent']) else "N/A"
            mom_1m = f"{stock_row['Momentum_1M_Percent']:+.2f}%" if pd.notna(stock_row['Momentum_1M_Percent']) else "N/A"
            
            data_status = stock_row['Data_Available']
            status_indicator = "*" if data_status == "Yes" else " "
            
            report.append(f"  {status_indicator} {stock:12} | 1W: {mom_1w:>8} | 1M: {mom_1m:>8}")
    
    # Sector performance ranking
    if sector_performance:
        report.append(f"\n\nSECTOR PERFORMANCE RANKING (1M)")
        report.append("=" * 35)
        
        sector_performance.sort(key=lambda x: x[1], reverse=True)
        
        for i, (sector, avg_perf, count) in enumerate(sector_performance, 1):
            status = "Strong" if avg_perf > 3 else "Positive" if avg_perf > 0 else "Weak"
            report.append(f"{i:2d}. {sector:20} {avg_perf:+.2f}% ({count} stocks) - {status}")
    
    report.append(f"\n\nNOTES:")
    report.append(f"* = Stock has momentum data available")
    report.append(f"N/A = No momentum data calculated")
    report.append(f"Total data coverage: {len(stocks_with_data)}/{len(df)} stocks")
    
    return "\n".join(report)


if __name__ == "__main__":
    create_final_working_report()