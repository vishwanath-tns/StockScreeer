"""
Direct Nifty 50 Momentum Report Generator
=======================================

This directly calculates momentum data and generates a comprehensive report
without Unicode issues.
"""

import sys
import os
from datetime import datetime, timedelta
import pandas as pd
import numpy as np

sys.path.append('.')

from volatility_patterns.data.data_service import DataService
from services.market_breadth_service import get_engine

class DirectNifty50Report:
    """Direct momentum calculator and report generator"""
    
    def __init__(self):
        self.data_service = DataService()
        
        # Nifty 50 stocks with sectors
        self.nifty50_stocks = {
            'AXISBANK': 'Banking', 'HDFCBANK': 'Banking', 'ICICIBANK': 'Banking',
            'INDUSINDBK': 'Banking', 'KOTAKBANK': 'Banking', 'SBIN': 'Banking',
            'BAJFINANCE': 'Financial Services', 'BAJAJFINSV': 'Financial Services',
            'HDFCLIFE': 'Financial Services', 'SBILIFE': 'Financial Services',
            'INFY': 'IT Services', 'TCS': 'IT Services', 'TECHM': 'IT Services',
            'HCLTECH': 'IT Services', 'WIPRO': 'IT Services',
            'RELIANCE': 'Oil & Gas', 'ONGC': 'Oil & Gas', 'BPCL': 'Oil & Gas',
            'TATASTEEL': 'Metals & Mining', 'JSWSTEEL': 'Metals & Mining',
            'HINDALCO': 'Metals & Mining', 'COALINDIA': 'Metals & Mining',
            'MARUTI': 'Automotive', 'BAJAJ-AUTO': 'Automotive', 'M&M': 'Automotive',
            'HEROMOTOCO': 'Automotive', 'EICHERMOT': 'Automotive',
            'SUNPHARMA': 'Pharmaceuticals', 'DRREDDY': 'Pharmaceuticals',
            'CIPLA': 'Pharmaceuticals', 'DIVISLAB': 'Pharmaceuticals',
            'HINDUNILVR': 'FMCG', 'BRITANNIA': 'FMCG', 'NESTLEIND': 'FMCG',
            'ITC': 'FMCG', 'TATACONSUM': 'FMCG',
            'BHARTIARTL': 'Telecom', 'NTPC': 'Power', 'POWERGRID': 'Power',
            'ULTRACEMCO': 'Cement', 'GRASIM': 'Cement', 'LT': 'Infrastructure',
            'ASIANPAINT': 'Paints', 'UPL': 'Chemicals', 'TITAN': 'Consumer Goods',
            'ADANIPORTS': 'Logistics'
        }
    
    def calculate_momentum(self, symbol, days_back):
        """Calculate momentum for a stock over specified days"""
        try:
            # Get stock data
            end_date = datetime.now().date()
            start_date = end_date - timedelta(days=days_back + 10)  # Extra buffer
            
            df = self.data_service.get_stock_data(symbol, start_date, end_date)
            
            if df is None or len(df) < days_back:
                return None
            
            # Sort by date
            df = df.sort_values('trade_date')
            
            if len(df) < 2:
                return None
            
            # Get start and end prices
            end_price = df.iloc[-1]['close_price']
            
            # Find price from days_back ago
            if len(df) >= days_back:
                start_price = df.iloc[-(days_back+1)]['close_price']
            else:
                start_price = df.iloc[0]['close_price']
            
            # Calculate momentum
            if start_price > 0:
                momentum = ((end_price - start_price) / start_price) * 100
                return {
                    'momentum': momentum,
                    'start_price': start_price,
                    'end_price': end_price,
                    'days': len(df)
                }
            
        except Exception as e:
            print(f"Error calculating momentum for {symbol}: {e}")
        
        return None
    
    def generate_momentum_data(self):
        """Generate momentum data for all Nifty 50 stocks"""
        
        print("Calculating momentum for Nifty 50 stocks...")
        print(f"Total stocks to process: {len(self.nifty50_stocks)}")
        print("")
        
        results = []
        successful = 0
        
        for i, (symbol, sector) in enumerate(self.nifty50_stocks.items(), 1):
            print(f"{i:2d}/{len(self.nifty50_stocks):2d} Processing {symbol:12} ({sector})")
            
            # Calculate 1W and 1M momentum
            momentum_1w = self.calculate_momentum(symbol, 7)
            momentum_1m = self.calculate_momentum(symbol, 30)
            
            row_data = {
                'Symbol': symbol,
                'Sector': sector,
                'Momentum_1W_Percent': None,
                'Momentum_1M_Percent': None,
                'Start_Price_1W': None,
                'End_Price_1W': None,
                'Start_Price_1M': None,
                'End_Price_1M': None
            }
            
            # Store 1W data
            if momentum_1w:
                row_data['Momentum_1W_Percent'] = momentum_1w['momentum']
                row_data['Start_Price_1W'] = momentum_1w['start_price']
                row_data['End_Price_1W'] = momentum_1w['end_price']
            
            # Store 1M data
            if momentum_1m:
                row_data['Momentum_1M_Percent'] = momentum_1m['momentum']
                row_data['Start_Price_1M'] = momentum_1m['start_price']
                row_data['End_Price_1M'] = momentum_1m['end_price']
            
            results.append(row_data)
            
            # Show results
            if momentum_1w or momentum_1m:
                result_parts = []
                if momentum_1w:
                    result_parts.append(f"1W: {momentum_1w['momentum']:+.2f}%")
                if momentum_1m:
                    result_parts.append(f"1M: {momentum_1m['momentum']:+.2f}%")
                
                print(f"    Success: {', '.join(result_parts)}")
                successful += 1
            else:
                print(f"    No data available")
        
        print(f"\nCalculation complete: {successful}/{len(self.nifty50_stocks)} stocks have momentum data")
        
        return pd.DataFrame(results)
    
    def generate_sector_report(self, df):
        """Generate sector analysis report"""
        
        report = []
        report.append("NIFTY 50 COMPREHENSIVE SECTOR ANALYSIS")
        report.append("=" * 50)
        report.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"Total Stocks: {len(df)}")
        report.append("")
        
        # Market overview
        stocks_1w = df[df['Momentum_1W_Percent'].notna()]
        stocks_1m = df[df['Momentum_1M_Percent'].notna()]
        
        # 1W Market Overview
        if len(stocks_1w) > 0:
            avg_1w = stocks_1w['Momentum_1W_Percent'].mean()
            positive_1w = (stocks_1w['Momentum_1W_Percent'] > 0).sum()
            
            report.append("1-WEEK MARKET OVERVIEW")
            report.append("-" * 25)
            report.append(f"Average Momentum: {avg_1w:+.2f}%")
            report.append(f"Positive Stocks: {positive_1w}/{len(stocks_1w)} ({positive_1w/len(stocks_1w)*100:.1f}%)")
            
            if positive_1w/len(stocks_1w) > 0.6:
                sentiment = "Strong Bullish"
            elif positive_1w/len(stocks_1w) > 0.4:
                sentiment = "Neutral"
            else:
                sentiment = "Bearish"
            report.append(f"Market Sentiment: {sentiment}")
            report.append("")
        
        # 1M Market Overview
        if len(stocks_1m) > 0:
            avg_1m = stocks_1m['Momentum_1M_Percent'].mean()
            positive_1m = (stocks_1m['Momentum_1M_Percent'] > 0).sum()
            
            report.append("1-MONTH MARKET OVERVIEW")
            report.append("-" * 26)
            report.append(f"Average Momentum: {avg_1m:+.2f}%")
            report.append(f"Positive Stocks: {positive_1m}/{len(stocks_1m)} ({positive_1m/len(stocks_1m)*100:.1f}%)")
            
            if positive_1m/len(stocks_1m) > 0.6:
                sentiment = "Strong Bullish"
            elif positive_1m/len(stocks_1m) > 0.4:
                sentiment = "Neutral"
            else:
                sentiment = "Bearish"
            report.append(f"Market Sentiment: {sentiment}")
            report.append("")
        
        # Top/Bottom performers
        if len(stocks_1m) > 0:
            report.append("TOP PERFORMERS (1-MONTH)")
            report.append("-" * 25)
            
            top_performers = stocks_1m.nlargest(5, 'Momentum_1M_Percent')
            for i, (_, stock) in enumerate(top_performers.iterrows(), 1):
                report.append(f"{i}. {stock['Symbol']:12} {stock['Momentum_1M_Percent']:+.2f}% ({stock['Sector']})")
            
            report.append("")
            report.append("BOTTOM PERFORMERS (1-MONTH)")
            report.append("-" * 28)
            
            bottom_performers = stocks_1m.nsmallest(5, 'Momentum_1M_Percent')
            for i, (_, stock) in enumerate(bottom_performers.iterrows(), 1):
                report.append(f"{i}. {stock['Symbol']:12} {stock['Momentum_1M_Percent']:+.2f}% ({stock['Sector']})")
            
            report.append("")
        
        # Sector Analysis
        report.append("DETAILED SECTOR ANALYSIS")
        report.append("=" * 30)
        
        sector_performance = []
        
        for sector in sorted(df['Sector'].unique()):
            sector_data = df[df['Sector'] == sector]
            
            report.append(f"\n{sector.upper()}")
            report.append("-" * len(sector))
            report.append(f"Total Stocks: {len(sector_data)}")
            
            # 1W Sector Analysis
            sector_1w = sector_data[sector_data['Momentum_1W_Percent'].notna()]
            if len(sector_1w) > 0:
                avg_1w = sector_1w['Momentum_1W_Percent'].mean()
                positive_1w = (sector_1w['Momentum_1W_Percent'] > 0).sum()
                report.append(f"1W Average: {avg_1w:+.2f}% ({positive_1w}/{len(sector_1w)} positive)")
            
            # 1M Sector Analysis
            sector_1m = sector_data[sector_data['Momentum_1M_Percent'].notna()]
            if len(sector_1m) > 0:
                avg_1m = sector_1m['Momentum_1M_Percent'].mean()
                positive_1m = (sector_1m['Momentum_1M_Percent'] > 0).sum()
                report.append(f"1M Average: {avg_1m:+.2f}% ({positive_1m}/{len(sector_1m)} positive)")
                
                sector_performance.append((sector, avg_1m, len(sector_1m)))
                
                # Best performer in sector
                best_stock = sector_1m.loc[sector_1m['Momentum_1M_Percent'].idxmax()]
                report.append(f"Best: {best_stock['Symbol']} ({best_stock['Momentum_1M_Percent']:+.2f}%)")
            
            # Individual stocks
            report.append("Individual Performance:")
            for _, stock in sector_data.iterrows():
                mom_1w = f"{stock['Momentum_1W_Percent']:+.2f}%" if pd.notna(stock['Momentum_1W_Percent']) else "N/A"
                mom_1m = f"{stock['Momentum_1M_Percent']:+.2f}%" if pd.notna(stock['Momentum_1M_Percent']) else "N/A"
                report.append(f"  {stock['Symbol']:12} | 1W: {mom_1w:>8} | 1M: {mom_1m:>8}")
        
        # Sector Rankings
        if sector_performance:
            report.append("\n\nSECTOR PERFORMANCE RANKING (1-MONTH)")
            report.append("=" * 40)
            
            sector_performance.sort(key=lambda x: x[1], reverse=True)
            
            for i, (sector, avg_perf, count) in enumerate(sector_performance, 1):
                status = "Strong" if avg_perf > 3 else "Positive" if avg_perf > 0 else "Negative"
                report.append(f"{i:2d}. {sector:20} {avg_perf:+.2f}% ({count} stocks) - {status}")
        
        return "\n".join(report)
    
    def generate_complete_report(self):
        """Generate the complete Nifty 50 report"""
        
        print("NIFTY 50 MOMENTUM ANALYSIS REPORT")
        print("=" * 40)
        print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("")
        
        # Step 1: Calculate momentum data
        df = self.generate_momentum_data()
        
        # Step 2: Generate analysis
        analysis = self.generate_sector_report(df)
        
        # Step 3: Save files
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        os.makedirs("reports", exist_ok=True)
        
        # Save CSV
        csv_filename = f"reports/nifty50_direct_report_{timestamp}.csv"
        df.to_csv(csv_filename, index=False)
        
        # Save analysis
        txt_filename = f"reports/nifty50_direct_analysis_{timestamp}.txt"
        with open(txt_filename, 'w', encoding='utf-8') as f:
            f.write(analysis)
        
        print(f"\nFiles saved:")
        print(f"  CSV Report: {csv_filename}")
        print(f"  Analysis: {txt_filename}")
        
        # Step 4: Display analysis
        print("\n" + "="*60)
        print(analysis)
        
        # Summary
        stocks_with_data = len(df[(df['Momentum_1W_Percent'].notna()) | 
                                (df['Momentum_1M_Percent'].notna())])
        
        print(f"\nREPORT SUMMARY:")
        print(f"Stocks analyzed: {stocks_with_data}/{len(df)}")
        print(f"Files generated: 2")
        print(f"Analysis complete: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


def main():
    """Main function"""
    try:
        reporter = DirectNifty50Report()
        reporter.generate_complete_report()
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()