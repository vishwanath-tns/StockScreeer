"""
Final Enhanced Nifty 50 Momentum Report with Complete Data Collection
====================================================================

This script generates the most comprehensive Nifty 50 momentum analysis possible
by leveraging all available data and providing detailed sector insights.

Features:
- Complete momentum calculations for all 46 Nifty 50 stocks
- Advanced sector analysis with performance rankings
- Market breadth indicators and sentiment analysis
- Professional reporting with multiple export formats
- Real-time data processing with error handling
"""

import sys
import os
from datetime import datetime
import pandas as pd
from typing import Dict, List, Optional
from dataclasses import dataclass

sys.path.append('.')

# Import momentum system
from services.momentum.momentum_calculator import MomentumCalculator, MomentumDuration
from services.market_breadth_service import get_engine

@dataclass
class StockMomentum:
    """Complete momentum data for a stock"""
    symbol: str
    sector: str
    momentum_1w: Optional[float] = None
    momentum_1m: Optional[float] = None
    momentum_3m: Optional[float] = None
    momentum_6m: Optional[float] = None
    avg_volume: Optional[float] = None
    market_cap: str = "Large Cap"  # Default for Nifty 50

class EnhancedNifty50Report:
    """Enhanced Nifty 50 momentum report with comprehensive analysis"""
    
    def __init__(self):
        self.calculator = MomentumCalculator()
        
        # Complete Nifty 50 sector mapping
        self.sector_mapping = {
            # Banking
            'AXISBANK': 'Banking', 'HDFCBANK': 'Banking', 'ICICIBANK': 'Banking',
            'INDUSINDBK': 'Banking', 'KOTAKBANK': 'Banking', 'SBIN': 'Banking',
            
            # Financial Services
            'BAJFINANCE': 'Financial Services', 'BAJAJFINSV': 'Financial Services',
            'HDFCLIFE': 'Financial Services', 'SBILIFE': 'Financial Services',
            
            # Information Technology
            'INFY': 'Information Technology', 'TCS': 'Information Technology',
            'TECHM': 'Information Technology', 'HCLTECH': 'Information Technology',
            'WIPRO': 'Information Technology',
            
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
            
            # Telecom
            'BHARTIARTL': 'Telecom',
            
            # Power & Utilities
            'NTPC': 'Power & Utilities', 'POWERGRID': 'Power & Utilities',
            
            # Cement & Construction
            'ULTRACEMCO': 'Cement & Construction', 'GRASIM': 'Cement & Construction',
            'LT': 'Cement & Construction',
            
            # Chemicals & Materials
            'ASIANPAINT': 'Chemicals & Materials', 'UPL': 'Chemicals & Materials',
            
            # Consumer Goods
            'TITAN': 'Consumer Goods',
            
            # Logistics
            'ADANIPORTS': 'Logistics'
        }
        
        self.nifty50_stocks = list(self.sector_mapping.keys())
    
    def collect_momentum_data(self) -> Dict[str, StockMomentum]:
        """Collect momentum data using batch calculation"""
        
        print("🔄 Collecting momentum data for all Nifty 50 stocks...")
        
        stock_data = {}
        
        # Initialize stock data structures
        for symbol in self.nifty50_stocks:
            sector = self.sector_mapping[symbol]
            stock_data[symbol] = StockMomentum(symbol=symbol, sector=sector)
        
        # Use batch calculation for efficiency
        durations = [MomentumDuration.ONE_WEEK, MomentumDuration.ONE_MONTH, 
                    MomentumDuration.THREE_MONTHS, MomentumDuration.SIX_MONTHS]
        
        for duration in durations:
            print(f"📊 Calculating {duration.value} momentum for {len(self.nifty50_stocks)} stocks...")
            
            try:
                # Use batch calculation
                results = self.calculator.calculate_momentum_batch(self.nifty50_stocks, duration)
                
                # Process results
                for result in results:
                    if result and result.symbol in stock_data:
                        stock = stock_data[result.symbol]
                        momentum_value = result.percentage_change
                        
                        if duration == MomentumDuration.ONE_WEEK:
                            stock.momentum_1w = momentum_value
                        elif duration == MomentumDuration.ONE_MONTH:
                            stock.momentum_1m = momentum_value
                        elif duration == MomentumDuration.THREE_MONTHS:
                            stock.momentum_3m = momentum_value
                        elif duration == MomentumDuration.SIX_MONTHS:
                            stock.momentum_6m = momentum_value
                        
                        # Store volume data if available
                        if hasattr(result, 'avg_volume') and result.avg_volume:
                            stock.avg_volume = result.avg_volume
                
                print(f"✅ {duration.value} momentum calculated for {len(results)} stocks")
                
            except Exception as e:
                print(f"⚠️  Error calculating {duration.value} momentum: {e}")
        
        # Count stocks with data
        stocks_with_data = sum(1 for s in stock_data.values() 
                              if any([s.momentum_1w, s.momentum_1m, s.momentum_3m, s.momentum_6m]))
        
        print(f"📈 Total stocks with momentum data: {stocks_with_data}/{len(stock_data)}")
        
        return stock_data
    
    def generate_sector_summary(self, stock_data: Dict[str, StockMomentum]) -> str:
        """Generate comprehensive sector analysis"""
        
        # Group by sector
        sectors = {}
        for stock in stock_data.values():
            if stock.sector not in sectors:
                sectors[stock.sector] = []
            sectors[stock.sector].append(stock)
        
        report = []
        report.append("🏢 SECTOR-WISE MOMENTUM ANALYSIS")
        report.append("=" * 50)
        report.append("")
        
        # Analyze each sector
        sector_performance = {}
        
        for sector_name, stocks in sectors.items():
            report.append(f"### {sector_name.upper()}")
            report.append(f"📊 Stocks: {len(stocks)}")
            
            # Calculate sector averages for different timeframes
            momentum_1w = [s.momentum_1w for s in stocks if s.momentum_1w is not None]
            momentum_1m = [s.momentum_1m for s in stocks if s.momentum_1m is not None]
            momentum_3m = [s.momentum_3m for s in stocks if s.momentum_3m is not None]
            momentum_6m = [s.momentum_6m for s in stocks if s.momentum_6m is not None]
            
            # 1W Analysis
            if momentum_1w:
                avg_1w = sum(momentum_1w) / len(momentum_1w)
                positive_1w = len([m for m in momentum_1w if m > 0])
                report.append(f"1W: {avg_1w:+.2f}% avg, {positive_1w}/{len(momentum_1w)} positive")
            else:
                avg_1w = None
                report.append("1W: No data")
            
            # 1M Analysis
            if momentum_1m:
                avg_1m = sum(momentum_1m) / len(momentum_1m)
                positive_1m = len([m for m in momentum_1m if m > 0])
                report.append(f"1M: {avg_1m:+.2f}% avg, {positive_1m}/{len(momentum_1m)} positive")
                sector_performance[sector_name] = avg_1m  # Use 1M for ranking
            else:
                avg_1m = None
                report.append("1M: No data")
                sector_performance[sector_name] = 0
            
            # 3M Analysis
            if momentum_3m:
                avg_3m = sum(momentum_3m) / len(momentum_3m)
                positive_3m = len([m for m in momentum_3m if m > 0])
                report.append(f"3M: {avg_3m:+.2f}% avg, {positive_3m}/{len(momentum_3m)} positive")
            else:
                report.append("3M: No data")
            
            # Best and worst performers
            stocks_with_1m = [s for s in stocks if s.momentum_1m is not None]
            if stocks_with_1m:
                best = max(stocks_with_1m, key=lambda x: x.momentum_1m)
                worst = min(stocks_with_1m, key=lambda x: x.momentum_1m)
                report.append(f"🏆 Best: {best.symbol} ({best.momentum_1m:+.2f}%)")
                report.append(f"📉 Worst: {worst.symbol} ({worst.momentum_1m:+.2f}%)")
            
            report.append("")
        
        # Sector rankings
        report.append("🏆 SECTOR RANKINGS (1M Momentum):")
        sorted_sectors = sorted(sector_performance.items(), key=lambda x: x[1], reverse=True)
        for i, (sector, performance) in enumerate(sorted_sectors, 1):
            if performance > 0:
                emoji = "🟢"
            elif performance > -2:
                emoji = "🟡"
            else:
                emoji = "🔴"
            report.append(f"{i:2d}. {emoji} {sector:20} {performance:+.2f}%")
        
        report.append("")
        
        return "\n".join(report)
    
    def generate_market_overview(self, stock_data: Dict[str, StockMomentum]) -> str:
        """Generate overall market overview"""
        
        report = []
        report.append("🌍 NIFTY 50 MARKET OVERVIEW")
        report.append("=" * 40)
        report.append(f"📅 Analysis Date: {datetime.now().strftime('%Y-%m-%d')}")
        report.append(f"📊 Total Stocks: {len(stock_data)}")
        report.append("")
        
        # Collect all momentum values
        all_1w = [s.momentum_1w for s in stock_data.values() if s.momentum_1w is not None]
        all_1m = [s.momentum_1m for s in stock_data.values() if s.momentum_1m is not None]
        all_3m = [s.momentum_3m for s in stock_data.values() if s.momentum_3m is not None]
        all_6m = [s.momentum_6m for s in stock_data.values() if s.momentum_6m is not None]
        
        # Market breadth analysis
        if all_1w:
            avg_1w = sum(all_1w) / len(all_1w)
            positive_1w = len([m for m in all_1w if m > 0])
            pct_positive_1w = positive_1w / len(all_1w) * 100
            
            report.append(f"📈 1W Market Momentum:")
            report.append(f"   Average: {avg_1w:+.2f}%")
            report.append(f"   Bullish stocks: {positive_1w}/{len(all_1w)} ({pct_positive_1w:.1f}%)")
            
            if pct_positive_1w > 60:
                sentiment = "🟢 Strong Bullish"
            elif pct_positive_1w > 40:
                sentiment = "🟡 Neutral"
            else:
                sentiment = "🔴 Bearish"
            report.append(f"   Market Sentiment: {sentiment}")
            report.append("")
        
        if all_1m:
            avg_1m = sum(all_1m) / len(all_1m)
            positive_1m = len([m for m in all_1m if m > 0])
            pct_positive_1m = positive_1m / len(all_1m) * 100
            
            report.append(f"📈 1M Market Momentum:")
            report.append(f"   Average: {avg_1m:+.2f}%")
            report.append(f"   Bullish stocks: {positive_1m}/{len(all_1m)} ({pct_positive_1m:.1f}%)")
            
            if pct_positive_1m > 60:
                sentiment = "🟢 Strong Bullish"
            elif pct_positive_1m > 40:
                sentiment = "🟡 Neutral"
            else:
                sentiment = "🔴 Bearish"
            report.append(f"   Market Sentiment: {sentiment}")
            report.append("")
        
        # Top and bottom performers
        if all_1m:
            stocks_with_1m = [s for s in stock_data.values() if s.momentum_1m is not None]
            stocks_with_1m.sort(key=lambda x: x.momentum_1m, reverse=True)
            
            report.append("🏆 TOP PERFORMERS (1M):")
            for i, stock in enumerate(stocks_with_1m[:5], 1):
                report.append(f"   {i}. {stock.symbol:12} {stock.momentum_1m:+.2f}% ({stock.sector})")
            report.append("")
            
            report.append("📉 BOTTOM PERFORMERS (1M):")
            for i, stock in enumerate(stocks_with_1m[-5:], 1):
                report.append(f"   {i}. {stock.symbol:12} {stock.momentum_1m:+.2f}% ({stock.sector})")
            report.append("")
        
        return "\n".join(report)
    
    def export_to_files(self, stock_data: Dict[str, StockMomentum], 
                       market_overview: str, sector_analysis: str):
        """Export analysis to multiple file formats"""
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        os.makedirs("reports", exist_ok=True)
        
        # CSV Export
        csv_data = []
        for stock in stock_data.values():
            csv_data.append({
                'Symbol': stock.symbol,
                'Sector': stock.sector,
                'Momentum_1W': stock.momentum_1w,
                'Momentum_1M': stock.momentum_1m,
                'Momentum_3M': stock.momentum_3m,
                'Momentum_6M': stock.momentum_6m,
                'Avg_Volume': stock.avg_volume,
                'Market_Cap': stock.market_cap
            })
        
        csv_filename = f"reports/nifty50_enhanced_analysis_{timestamp}.csv"
        df = pd.DataFrame(csv_data)
        df.to_csv(csv_filename, index=False)
        
        # Text Report
        full_report = market_overview + "\n\n" + sector_analysis
        txt_filename = f"reports/nifty50_enhanced_report_{timestamp}.txt"
        with open(txt_filename, 'w', encoding='utf-8') as f:
            f.write(full_report)
        
        print(f"📄 CSV data exported to: {csv_filename}")
        print(f"📋 Full report exported to: {txt_filename}")
        
        return csv_filename, txt_filename
    
    def run_complete_analysis(self):
        """Run the complete enhanced Nifty 50 analysis"""
        
        print("🚀 ENHANCED NIFTY 50 MOMENTUM ANALYSIS")
        print("=" * 60)
        print(f"⏰ Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("")
        
        # Step 1: Collect momentum data
        stock_data = self.collect_momentum_data()
        
        # Step 2: Generate market overview
        print("\n📊 Generating market overview...")
        market_overview = self.generate_market_overview(stock_data)
        
        # Step 3: Generate sector analysis
        print("🏢 Generating sector analysis...")
        sector_analysis = self.generate_sector_summary(stock_data)
        
        # Step 4: Display results
        print("\n" + market_overview)
        print("\n" + sector_analysis)
        
        # Step 5: Export to files
        print("💾 Exporting analysis to files...")
        csv_file, txt_file = self.export_to_files(stock_data, market_overview, sector_analysis)
        
        # Summary
        stocks_with_data = sum(1 for s in stock_data.values() 
                              if any([s.momentum_1w, s.momentum_1m, s.momentum_3m, s.momentum_6m]))
        
        print(f"\n🎉 ANALYSIS COMPLETE!")
        print(f"📈 Stocks analyzed: {stocks_with_data}/{len(stock_data)}")
        print(f"📁 Files generated: 2")
        print(f"⏱️  Completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


def main():
    """Main execution function"""
    try:
        analyzer = EnhancedNifty50Report()
        analyzer.run_complete_analysis()
        
    except Exception as e:
        print(f"❌ Error in analysis: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()