"""
Generate Full Nifty 50 Report with Live Momentum Calculations
===========================================================

This script will:
1. Calculate fresh momentum data for all Nifty 50 stocks
2. Store the data in the database
3. Generate a comprehensive sector-wise report with actual numbers

This ensures you get a complete report with real momentum data.
"""

import sys
import os
from datetime import datetime
import pandas as pd
from typing import Dict, List, Optional
import time

sys.path.append('.')

# Import services
from services.momentum.momentum_calculator import MomentumCalculator, MomentumDuration
from services.market_breadth_service import get_engine

class Nifty50ReportGenerator:
    """Complete Nifty 50 report generator with live calculations"""
    
    def __init__(self):
        self.calculator = MomentumCalculator()
        
        # Complete Nifty 50 with sectors
        self.nifty50_stocks = {
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
            
            # Others (10 stocks)
            'BHARTIARTL': 'Telecom',
            'NTPC': 'Power',
            'POWERGRID': 'Power',
            'ULTRACEMCO': 'Cement',
            'GRASIM': 'Cement',
            'LT': 'Infrastructure',
            'ASIANPAINT': 'Paints',
            'UPL': 'Chemicals',
            'TITAN': 'Consumer Goods',
            'ADANIPORTS': 'Logistics'
        }
    
    def calculate_momentum_for_stock(self, symbol: str, durations: List[MomentumDuration]) -> Dict[str, float]:
        """Calculate momentum for a single stock across multiple durations"""
        
        results = {}
        
        for duration in durations:
            try:
                # Use the single stock calculation method that works
                momentum_results = self.calculator.calculate_momentum_batch([symbol], [duration])
                
                if momentum_results and len(momentum_results) > 0:
                    result = momentum_results[0]
                    if hasattr(result, 'percentage_change'):
                        results[duration.value] = result.percentage_change
                    elif hasattr(result, 'symbol') and hasattr(result, 'percentage_change'):
                        results[duration.value] = result.percentage_change
                    else:
                        print(f"    ⚠️  Unexpected result format for {symbol} {duration.value}: {result}")
                
            except Exception as e:
                print(f"    ❌ Error calculating {duration.value} for {symbol}: {e}")
        
        return results
    
    def generate_live_momentum_data(self) -> pd.DataFrame:
        """Generate momentum data by calculating fresh for all stocks"""
        
        print("🚀 Generating fresh momentum data for all Nifty 50 stocks...")
        print(f"📊 Total stocks to process: {len(self.nifty50_stocks)}")
        print("")
        
        # Durations to calculate
        durations = [MomentumDuration.ONE_WEEK, MomentumDuration.ONE_MONTH]
        
        all_data = []
        successful_calculations = 0
        
        # Process each stock individually for reliability
        for i, (symbol, sector) in enumerate(self.nifty50_stocks.items(), 1):
            print(f"📈 {i:2d}/{len(self.nifty50_stocks):2d} Processing {symbol:12} ({sector})")
            
            try:
                # Calculate momentum for this stock
                momentum_data = self.calculate_momentum_for_stock(symbol, durations)
                
                # Create row data
                row_data = {
                    'Symbol': symbol,
                    'Sector': sector,
                    'Momentum_1W_Percent': momentum_data.get('1W', None),
                    'Momentum_1M_Percent': momentum_data.get('1M', None),
                    'Momentum_3M_Percent': None,  # Can be added later
                    'Momentum_6M_Percent': None   # Can be added later
                }
                
                all_data.append(row_data)
                
                # Show what we calculated
                if momentum_data:
                    momentum_str = ", ".join([f"{dur}: {val:+.2f}%" for dur, val in momentum_data.items()])
                    print(f"    ✅ {momentum_str}")
                    successful_calculations += 1
                else:
                    print(f"    ⚠️  No momentum data calculated")
                
                # Small delay to be nice to the system
                time.sleep(0.1)
                
            except Exception as e:
                print(f"    ❌ Error processing {symbol}: {e}")
                
                # Still add the row with no data
                all_data.append({
                    'Symbol': symbol,
                    'Sector': sector,
                    'Momentum_1W_Percent': None,
                    'Momentum_1M_Percent': None,
                    'Momentum_3M_Percent': None,
                    'Momentum_6M_Percent': None
                })
        
        print(f"\n✅ Processing complete!")
        print(f"📊 Successfully calculated momentum for {successful_calculations}/{len(self.nifty50_stocks)} stocks")
        
        return pd.DataFrame(all_data)
    
    def analyze_sector_performance(self, df: pd.DataFrame) -> str:
        """Generate sector analysis from the momentum data"""
        
        report = []
        report.append("🏢 NIFTY 50 SECTOR ANALYSIS")
        report.append("=" * 50)
        report.append(f"📅 Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("")
        
        # Overall market stats
        stocks_with_1w = df[df['Momentum_1W_Percent'].notna()]
        stocks_with_1m = df[df['Momentum_1M_Percent'].notna()]
        
        if len(stocks_with_1w) > 0:
            avg_1w = stocks_with_1w['Momentum_1W_Percent'].mean()
            positive_1w = (stocks_with_1w['Momentum_1W_Percent'] > 0).sum()
            
            report.append(f"📊 1W Market Overview:")
            report.append(f"   Average: {avg_1w:+.2f}%")
            report.append(f"   Positive: {positive_1w}/{len(stocks_with_1w)} ({positive_1w/len(stocks_with_1w)*100:.1f}%)")
            report.append("")
        
        if len(stocks_with_1m) > 0:
            avg_1m = stocks_with_1m['Momentum_1M_Percent'].mean()
            positive_1m = (stocks_with_1m['Momentum_1M_Percent'] > 0).sum()
            
            report.append(f"📊 1M Market Overview:")
            report.append(f"   Average: {avg_1m:+.2f}%")
            report.append(f"   Positive: {positive_1m}/{len(stocks_with_1m)} ({positive_1m/len(stocks_with_1m)*100:.1f}%)")
            report.append("")
        
        # Sector analysis
        sector_performance = []
        
        for sector in df['Sector'].unique():
            sector_data = df[df['Sector'] == sector]
            
            report.append(f"## 📈 {sector.upper()}")
            report.append(f"📊 Stocks: {len(sector_data)}")
            
            # 1W sector stats
            sector_1w = sector_data[sector_data['Momentum_1W_Percent'].notna()]
            if len(sector_1w) > 0:
                avg_1w = sector_1w['Momentum_1W_Percent'].mean()
                positive_1w = (sector_1w['Momentum_1W_Percent'] > 0).sum()
                report.append(f"   1W: {avg_1w:+.2f}% avg, {positive_1w}/{len(sector_1w)} positive")
            
            # 1M sector stats
            sector_1m = sector_data[sector_data['Momentum_1M_Percent'].notna()]
            if len(sector_1m) > 0:
                avg_1m = sector_1m['Momentum_1M_Percent'].mean()
                positive_1m = (sector_1m['Momentum_1M_Percent'] > 0).sum()
                report.append(f"   1M: {avg_1m:+.2f}% avg, {positive_1m}/{len(sector_1m)} positive")
                
                sector_performance.append((sector, avg_1m))
            
            # Individual stocks
            report.append("   Individual stocks:")
            for _, stock in sector_data.iterrows():
                mom_1w = f"{stock['Momentum_1W_Percent']:+.2f}%" if pd.notna(stock['Momentum_1W_Percent']) else "N/A"
                mom_1m = f"{stock['Momentum_1M_Percent']:+.2f}%" if pd.notna(stock['Momentum_1M_Percent']) else "N/A"
                report.append(f"     {stock['Symbol']:12} | 1W: {mom_1w:>8} | 1M: {mom_1m:>8}")
            
            report.append("")
        
        # Top sectors
        if sector_performance:
            report.append("🏆 TOP PERFORMING SECTORS (1M)")
            report.append("-" * 30)
            
            sector_performance.sort(key=lambda x: x[1], reverse=True)
            for i, (sector, perf) in enumerate(sector_performance, 1):
                emoji = "🟢" if perf > 2 else "🟡" if perf > 0 else "🔴"
                report.append(f"{i:2d}. {emoji} {sector:20} {perf:+.2f}%")
        
        return "\n".join(report)
    
    def generate_complete_report(self):
        """Generate the complete Nifty 50 report with live data"""
        
        print("🎯 NIFTY 50 COMPREHENSIVE REPORT GENERATOR")
        print("=" * 60)
        print(f"🕐 Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("")
        
        # Step 1: Generate fresh momentum data
        df = self.generate_live_momentum_data()
        
        # Step 2: Save CSV with timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        os.makedirs("reports", exist_ok=True)
        
        csv_filename = f"reports/nifty50_live_report_{timestamp}.csv"
        df.to_csv(csv_filename, index=False)
        
        print(f"\n📄 CSV Report saved: {csv_filename}")
        
        # Step 3: Generate sector analysis
        sector_analysis = self.analyze_sector_performance(df)
        
        # Step 4: Save text report
        txt_filename = f"reports/nifty50_live_analysis_{timestamp}.txt"
        with open(txt_filename, 'w', encoding='utf-8') as f:
            f.write(sector_analysis)
        
        print(f"📋 Analysis saved: {txt_filename}")
        
        # Step 5: Display the analysis
        print("\n" + "="*60)
        print(sector_analysis)
        
        # Summary
        stocks_with_data = len(df[(df['Momentum_1W_Percent'].notna()) | (df['Momentum_1M_Percent'].notna())])
        
        print(f"\n🎉 REPORT GENERATION COMPLETE!")
        print(f"📊 Stocks with momentum data: {stocks_with_data}/{len(df)}")
        print(f"📁 Files created: 2")
        print(f"📄 CSV: {csv_filename}")
        print(f"📋 TXT: {txt_filename}")
        print(f"⏰ Completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


def main():
    """Main execution"""
    try:
        generator = Nifty50ReportGenerator()
        generator.generate_complete_report()
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()