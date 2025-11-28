"""
Final Nifty 50 Sector Report Using Proven Working Code
=====================================================

This report uses the proven working momentum calculation system to generate
a comprehensive Nifty 50 sector analysis with actual momentum data.

Based on successful quick_nifty50_scan.py implementation.
"""

import sys
import os
from datetime import datetime
import pandas as pd
from typing import Dict, List, Optional
from dataclasses import dataclass

sys.path.append('.')

# Import proven working momentum system
from services.momentum.momentum_calculator import MomentumCalculator, MomentumDuration
from services.market_breadth_service import get_engine

@dataclass
class NiftyStock:
    """Nifty 50 stock with sector and momentum data"""
    symbol: str
    sector: str
    momentum_1w: Optional[float] = None
    momentum_1m: Optional[float] = None
    momentum_3m: Optional[float] = None

class FinalNifty50SectorReport:
    """Final comprehensive Nifty 50 sector report using proven working code"""
    
    def __init__(self):
        # Complete Nifty 50 with sector mapping
        self.nifty50_with_sectors = {
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
            
            # Information Technology (5 stocks)
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
            
            # Others
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
        
        self.calculator = MomentumCalculator()
    
    def calculate_nifty50_momentum_data(self) -> Dict[str, NiftyStock]:
        """Calculate momentum using proven working approach"""
        
        print("📊 Calculating momentum data for all Nifty 50 stocks...")
        print(f"📈 Total stocks to analyze: {len(self.nifty50_with_sectors)}")
        
        # Initialize stock data
        stock_data = {}
        for symbol, sector in self.nifty50_with_sectors.items():
            stock_data[symbol] = NiftyStock(symbol=symbol, sector=sector)
        
        # Calculate momentum using the proven working batch approach
        all_symbols = list(self.nifty50_with_sectors.keys())
        
        # Split into smaller batches for reliability
        batch_size = 10
        batches = [all_symbols[i:i+batch_size] for i in range(0, len(all_symbols), batch_size)]
        
        print(f"🔄 Processing {len(batches)} batches of {batch_size} stocks each...")
        
        # Process each batch
        for batch_num, batch_symbols in enumerate(batches, 1):
            print(f"\n📊 Processing Batch {batch_num}/{len(batches)}: {len(batch_symbols)} stocks")
            
            # Calculate 1W momentum for this batch
            try:
                results_1w = self.calculator.calculate_momentum_batch(
                    batch_symbols, 
                    [MomentumDuration.ONE_WEEK]
                )
                
                for result in results_1w:
                    if result and result.symbol in stock_data:
                        stock_data[result.symbol].momentum_1w = result.percentage_change
                        
                print(f"  ✅ 1W momentum calculated for {len(results_1w)} stocks")
                        
            except Exception as e:
                print(f"  ⚠️  1W momentum error: {e}")
            
            # Calculate 1M momentum for this batch
            try:
                results_1m = self.calculator.calculate_momentum_batch(
                    batch_symbols, 
                    [MomentumDuration.ONE_MONTH]
                )
                
                for result in results_1m:
                    if result and result.symbol in stock_data:
                        stock_data[result.symbol].momentum_1m = result.percentage_change
                        
                print(f"  ✅ 1M momentum calculated for {len(results_1m)} stocks")
                        
            except Exception as e:
                print(f"  ⚠️  1M momentum error: {e}")
            
            # Show batch completion
            batch_stocks_with_data = [s for s in batch_symbols if stock_data[s].momentum_1w is not None or stock_data[s].momentum_1m is not None]
            print(f"  📈 Batch {batch_num} completed: {len(batch_stocks_with_data)}/{len(batch_symbols)} stocks with data")
        
        # Final summary
        total_with_data = sum(1 for s in stock_data.values() 
                             if s.momentum_1w is not None or s.momentum_1m is not None)
        
        print(f"\n✅ Momentum calculation completed!")
        print(f"📊 Total stocks with momentum data: {total_with_data}/{len(stock_data)}")
        
        return stock_data
    
    def generate_sector_wise_report(self, stock_data: Dict[str, NiftyStock]) -> str:
        """Generate comprehensive sector-wise analysis"""
        
        # Group stocks by sector
        sectors = {}
        for stock in stock_data.values():
            if stock.sector not in sectors:
                sectors[stock.sector] = []
            sectors[stock.sector].append(stock)
        
        report = []
        report.append("🏢 NIFTY 50 COMPREHENSIVE SECTOR ANALYSIS")
        report.append("=" * 60)
        report.append(f"📅 Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"📊 Total Stocks: {len(stock_data)}")
        report.append(f"🏢 Total Sectors: {len(sectors)}")
        report.append("")
        
        sector_rankings = []
        
        for sector_name in sorted(sectors.keys()):
            stocks = sectors[sector_name]
            report.append(f"## 📈 {sector_name.upper()}")
            report.append(f"📊 Stocks in sector: {len(stocks)}")
            report.append("")
            
            # Calculate sector statistics
            stocks_1w = [s for s in stocks if s.momentum_1w is not None]
            stocks_1m = [s for s in stocks if s.momentum_1m is not None]
            
            # 1W Analysis
            if stocks_1w:
                avg_1w = sum(s.momentum_1w for s in stocks_1w) / len(stocks_1w)
                positive_1w = len([s for s in stocks_1w if s.momentum_1w > 0])
                report.append(f"📊 1W Performance:")
                report.append(f"   Average: {avg_1w:+.2f}%")
                report.append(f"   Positive: {positive_1w}/{len(stocks_1w)} ({positive_1w/len(stocks_1w)*100:.1f}%)")
                
                best_1w = max(stocks_1w, key=lambda x: x.momentum_1w)
                worst_1w = min(stocks_1w, key=lambda x: x.momentum_1w)
                report.append(f"   🏆 Best: {best_1w.symbol} ({best_1w.momentum_1w:+.2f}%)")
                report.append(f"   📉 Worst: {worst_1w.symbol} ({worst_1w.momentum_1w:+.2f}%)")
                report.append("")
            
            # 1M Analysis
            if stocks_1m:
                avg_1m = sum(s.momentum_1m for s in stocks_1m) / len(stocks_1m)
                positive_1m = len([s for s in stocks_1m if s.momentum_1m > 0])
                report.append(f"📊 1M Performance:")
                report.append(f"   Average: {avg_1m:+.2f}%")
                report.append(f"   Positive: {positive_1m}/{len(stocks_1m)} ({positive_1m/len(stocks_1m)*100:.1f}%)")
                
                best_1m = max(stocks_1m, key=lambda x: x.momentum_1m)
                worst_1m = min(stocks_1m, key=lambda x: x.momentum_1m)
                report.append(f"   🏆 Best: {best_1m.symbol} ({best_1m.momentum_1m:+.2f}%)")
                report.append(f"   📉 Worst: {worst_1m.symbol} ({worst_1m.momentum_1m:+.2f}%)")
                
                # Store for sector ranking
                sector_rankings.append((sector_name, avg_1m, len(stocks_1m)))
                report.append("")
            else:
                sector_rankings.append((sector_name, 0, 0))
            
            # Individual stock details
            report.append("📋 Individual Stock Performance:")
            for stock in sorted(stocks, key=lambda x: x.symbol):
                mom_1w = f"{stock.momentum_1w:+.2f}%" if stock.momentum_1w is not None else "N/A"
                mom_1m = f"{stock.momentum_1m:+.2f}%" if stock.momentum_1m is not None else "N/A"
                report.append(f"   {stock.symbol:12} | 1W: {mom_1w:>8} | 1M: {mom_1m:>8}")
            
            report.append("")
            report.append("-" * 50)
            report.append("")
        
        # Add sector rankings
        report.append("🏆 SECTOR PERFORMANCE RANKING (1M Momentum)")
        report.append("=" * 50)
        
        # Sort sectors by 1M average performance
        sector_rankings.sort(key=lambda x: x[1], reverse=True)
        
        for rank, (sector, avg_perf, count) in enumerate(sector_rankings, 1):
            if count > 0:
                if avg_perf > 2:
                    emoji = "🟢"
                elif avg_perf > 0:
                    emoji = "🟡"
                else:
                    emoji = "🔴"
                
                report.append(f"{rank:2d}. {emoji} {sector:20} {avg_perf:+.2f}% ({count} stocks)")
            else:
                report.append(f"{rank:2d}. ⚪ {sector:20}  No data")
        
        return "\n".join(report)
    
    def generate_market_summary(self, stock_data: Dict[str, NiftyStock]) -> str:
        """Generate market-wide summary"""
        
        report = []
        report.append("🌍 NIFTY 50 MARKET SUMMARY")
        report.append("=" * 40)
        
        # Collect all momentum data
        all_1w = [s.momentum_1w for s in stock_data.values() if s.momentum_1w is not None]
        all_1m = [s.momentum_1m for s in stock_data.values() if s.momentum_1m is not None]
        
        if all_1w:
            avg_1w = sum(all_1w) / len(all_1w)
            positive_1w = len([m for m in all_1w if m > 0])
            
            report.append(f"📊 1W Market Momentum:")
            report.append(f"   Average: {avg_1w:+.2f}%")
            report.append(f"   Bullish Stocks: {positive_1w}/{len(all_1w)} ({positive_1w/len(all_1w)*100:.1f}%)")
            
            if positive_1w/len(all_1w) > 0.6:
                sentiment = "🟢 Strong Bullish"
            elif positive_1w/len(all_1w) > 0.4:
                sentiment = "🟡 Neutral" 
            else:
                sentiment = "🔴 Bearish"
            report.append(f"   Market Sentiment: {sentiment}")
            report.append("")
        
        if all_1m:
            avg_1m = sum(all_1m) / len(all_1m)
            positive_1m = len([m for m in all_1m if m > 0])
            
            report.append(f"📊 1M Market Momentum:")
            report.append(f"   Average: {avg_1m:+.2f}%")
            report.append(f"   Bullish Stocks: {positive_1m}/{len(all_1m)} ({positive_1m/len(all_1m)*100:.1f}%)")
            
            if positive_1m/len(all_1m) > 0.6:
                sentiment = "🟢 Strong Bullish"
            elif positive_1m/len(all_1m) > 0.4:
                sentiment = "🟡 Neutral"
            else:
                sentiment = "🔴 Bearish"
            report.append(f"   Market Sentiment: {sentiment}")
            report.append("")
        
        # Top performers
        if all_1m:
            stocks_with_1m = [s for s in stock_data.values() if s.momentum_1m is not None]
            stocks_with_1m.sort(key=lambda x: x.momentum_1m, reverse=True)
            
            report.append("🏆 TOP PERFORMERS (1M):")
            for i, stock in enumerate(stocks_with_1m[:5], 1):
                report.append(f"   {i}. {stock.symbol:12} {stock.momentum_1m:+.2f}% ({stock.sector})")
            
            report.append("")
            report.append("📉 UNDERPERFORMERS (1M):")
            for i, stock in enumerate(stocks_with_1m[-5:], 1):
                report.append(f"   {i}. {stock.symbol:12} {stock.momentum_1m:+.2f}% ({stock.sector})")
        
        return "\n".join(report)
    
    def export_to_csv(self, stock_data: Dict[str, NiftyStock]) -> str:
        """Export detailed data to CSV"""
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        os.makedirs("reports", exist_ok=True)
        
        csv_data = []
        for stock in stock_data.values():
            csv_data.append({
                'Symbol': stock.symbol,
                'Sector': stock.sector,
                'Momentum_1W_Percent': stock.momentum_1w,
                'Momentum_1M_Percent': stock.momentum_1m,
                'Momentum_3M_Percent': stock.momentum_3m
            })
        
        filename = f"reports/nifty50_final_sector_analysis_{timestamp}.csv"
        df = pd.DataFrame(csv_data)
        df.to_csv(filename, index=False)
        
        return filename
    
    def run_comprehensive_analysis(self):
        """Execute complete Nifty 50 sector analysis"""
        
        print("🚀 FINAL NIFTY 50 COMPREHENSIVE SECTOR ANALYSIS")
        print("=" * 70)
        print(f"⏰ Analysis started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("")
        
        # Step 1: Calculate momentum data
        stock_data = self.calculate_nifty50_momentum_data()
        
        # Step 2: Generate market summary
        print("\n🌍 Generating market summary...")
        market_summary = self.generate_market_summary(stock_data)
        
        # Step 3: Generate sector analysis
        print("🏢 Generating sector-wise analysis...")
        sector_report = self.generate_sector_wise_report(stock_data)
        
        # Step 4: Display results
        print("\n" + "="*70)
        print(market_summary)
        print("\n" + "="*70)
        print(sector_report)
        
        # Step 5: Export to CSV
        print("\n💾 Exporting data to CSV...")
        csv_file = self.export_to_csv(stock_data)
        print(f"📄 CSV exported to: {csv_file}")
        
        # Step 6: Export full report
        full_report = market_summary + "\n\n" + sector_report
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        txt_file = f"reports/nifty50_final_sector_report_{timestamp}.txt"
        with open(txt_file, 'w', encoding='utf-8') as f:
            f.write(full_report)
        print(f"📋 Full report exported to: {txt_file}")
        
        # Final summary
        total_with_data = sum(1 for s in stock_data.values() 
                             if s.momentum_1w is not None or s.momentum_1m is not None)
        
        print(f"\n🎉 ANALYSIS COMPLETED SUCCESSFULLY!")
        print(f"📈 Stocks analyzed: {total_with_data}/{len(stock_data)}")
        print(f"📁 Files generated: 2 (CSV + TXT)")
        print(f"⏱️  Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


def main():
    """Main execution"""
    try:
        analyzer = FinalNifty50SectorReport()
        analyzer.run_comprehensive_analysis()
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()