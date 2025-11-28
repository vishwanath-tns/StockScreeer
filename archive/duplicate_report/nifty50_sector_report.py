"""
Comprehensive Nifty 50 Sector-wise Momentum Report Generator
===========================================================

Generates detailed momentum analysis reports for all Nifty 50 stocks with proper
sector categorization and comprehensive market insights.

Features:
---------
- Complete Nifty 50 coverage (46 available stocks)
- Sector-wise analysis and rankings
- Multi-timeframe momentum (1W, 1M, 3M, 6M)
- Market breadth analysis
- Top/bottom performers by sector
- Professional reporting with multiple output formats

Author: StockScreener
Date: November 17, 2025
"""

import sys
import os
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import pandas as pd
import json
from dataclasses import dataclass

# Add current directory to Python path
sys.path.append('.')

# Import momentum system
from services.momentum.momentum_calculator import MomentumCalculator, MomentumDuration
from services.momentum.momentum_reporting_service import (
    MomentumReportingService, ReportConfig, ReportType, ReportFormat
)
from services.market_breadth_service import get_engine

@dataclass
class SectorInfo:
    """Information about a sector"""
    name: str
    stocks: List[str]
    description: str

@dataclass
class StockMomentumData:
    """Momentum data for a single stock"""
    symbol: str
    sector: str
    momentum_1w: Optional[float] = None
    momentum_1m: Optional[float] = None
    momentum_3m: Optional[float] = None
    momentum_6m: Optional[float] = None
    volume_trend: Optional[str] = None
    market_cap_category: Optional[str] = None

class Nifty50SectorReport:
    """Comprehensive Nifty 50 sector-wise momentum report generator"""
    
    def __init__(self):
        self.calculator = MomentumCalculator()
        self.reporter = MomentumReportingService()
        
        # Comprehensive sector mapping for Nifty 50 stocks
        self.sectors = {
            'Banking': SectorInfo(
                name='Banking',
                stocks=['AXISBANK', 'HDFCBANK', 'ICICIBANK', 'INDUSINDBK', 'KOTAKBANK', 'SBIN'],
                description='Private and public sector banks'
            ),
            'Financial Services': SectorInfo(
                name='Financial Services',
                stocks=['BAJFINANCE', 'BAJAJFINSV', 'HDFCLIFE', 'SBILIFE'],
                description='NBFCs, insurance and financial services'
            ),
            'Information Technology': SectorInfo(
                name='Information Technology',
                stocks=['INFY', 'TCS', 'TECHM', 'HCLTECH', 'WIPRO'],
                description='Software services and IT consulting'
            ),
            'Oil & Gas': SectorInfo(
                name='Oil & Gas',
                stocks=['RELIANCE', 'ONGC', 'BPCL'],
                description='Oil exploration, refining and marketing'
            ),
            'Metals & Mining': SectorInfo(
                name='Metals & Mining',
                stocks=['TATASTEEL', 'JSWSTEEL', 'HINDALCO', 'COALINDIA'],
                description='Steel, aluminum, and mining companies'
            ),
            'Automotive': SectorInfo(
                name='Automotive',
                stocks=['MARUTI', 'BAJAJ-AUTO', 'M&M', 'HEROMOTOCO', 'EICHERMOT'],
                description='Auto manufacturers and components'
            ),
            'Pharmaceuticals': SectorInfo(
                name='Pharmaceuticals',
                stocks=['SUNPHARMA', 'DRREDDY', 'CIPLA', 'DIVISLAB'],
                description='Pharmaceutical and healthcare companies'
            ),
            'FMCG': SectorInfo(
                name='FMCG',
                stocks=['HINDUNILVR', 'BRITANNIA', 'NESTLEIND', 'ITC', 'TATACONSUM'],
                description='Fast moving consumer goods'
            ),
            'Telecom': SectorInfo(
                name='Telecom',
                stocks=['BHARTIARTL'],
                description='Telecommunications services'
            ),
            'Power & Utilities': SectorInfo(
                name='Power & Utilities',
                stocks=['NTPC', 'POWERGRID'],
                description='Power generation and transmission'
            ),
            'Cement & Construction': SectorInfo(
                name='Cement & Construction',
                stocks=['ULTRACEMCO', 'GRASIM', 'LT'],
                description='Cement manufacturing and infrastructure'
            ),
            'Chemicals & Materials': SectorInfo(
                name='Chemicals & Materials',
                stocks=['ASIANPAINT', 'UPL'],
                description='Paints, chemicals and materials'
            ),
            'Consumer Goods': SectorInfo(
                name='Consumer Goods',
                stocks=['TITAN'],
                description='Jewelry and consumer discretionary'
            ),
            'Logistics': SectorInfo(
                name='Logistics',
                stocks=['ADANIPORTS'],
                description='Ports and logistics services'
            )
        }
        
        # Create reverse mapping for quick sector lookup
        self.stock_to_sector = {}
        for sector_name, sector_info in self.sectors.items():
            for stock in sector_info.stocks:
                self.stock_to_sector[stock] = sector_name
    
    def get_current_momentum_data(self) -> Dict[str, StockMomentumData]:
        """Retrieve current momentum data from database"""
        
        print("📊 Retrieving momentum data from database...")
        
        # Get current momentum data
        engine = get_engine()
        
        try:
            with engine.connect() as conn:
                # Query momentum data
                query = """
                SELECT symbol, duration_type, percentage_change, 
                       start_price, end_price, trading_days,
                       avg_volume, volume_surge_factor
                FROM momentum_analysis 
                WHERE calculation_date = CURDATE()
                OR calculation_date = (SELECT MAX(calculation_date) FROM momentum_analysis)
                ORDER BY symbol, duration_type
                """
                
                momentum_df = pd.read_sql(query, conn)
                
        except Exception as e:
            print(f"⚠️  Database error: {e}")
            print("📝 Using sample data for demonstration...")
            momentum_df = self._get_sample_momentum_data()
        
        # Convert to our data structure
        stock_data = {}
        
        # Get all Nifty 50 stocks
        all_nifty50 = []
        for sector_info in self.sectors.values():
            all_nifty50.extend(sector_info.stocks)
        
        for stock in all_nifty50:
            sector = self.stock_to_sector.get(stock, 'Other')
            stock_data[stock] = StockMomentumData(symbol=stock, sector=sector)
            
            # Fill momentum data if available
            stock_momentum = momentum_df[momentum_df['symbol'] == stock]
            
            for _, row in stock_momentum.iterrows():
                duration = row['duration_type']
                momentum = float(row['percentage_change'])
                
                if duration == '1W':
                    stock_data[stock].momentum_1w = momentum
                elif duration == '1M':
                    stock_data[stock].momentum_1m = momentum
                elif duration == '3M':
                    stock_data[stock].momentum_3m = momentum
                elif duration == '6M':
                    stock_data[stock].momentum_6m = momentum
        
        print(f"✅ Retrieved momentum data for {len(stock_data)} stocks")
        return stock_data
    
    def _get_sample_momentum_data(self) -> pd.DataFrame:
        """Generate sample momentum data for demonstration"""
        import random
        
        all_stocks = []
        for sector_info in self.sectors.values():
            all_stocks.extend(sector_info.stocks)
        
        data = []
        for stock in all_stocks[:10]:  # Sample 10 stocks
            for duration in ['1W', '1M']:
                momentum = random.uniform(-5, 8)  # Random momentum between -5% and +8%
                data.append({
                    'symbol': stock,
                    'duration_type': duration,
                    'percentage_change': momentum,
                    'start_price': 1000,
                    'end_price': 1000 * (1 + momentum/100),
                    'trading_days': 5 if duration == '1W' else 20,
                    'avg_volume': 1000000,
                    'volume_surge_factor': 1.0
                })
        
        return pd.DataFrame(data)
    
    def generate_sector_analysis(self, stock_data: Dict[str, StockMomentumData]) -> str:
        """Generate comprehensive sector-wise analysis"""
        
        report = []
        report.append("🏗️  NIFTY 50 SECTOR-WISE MOMENTUM ANALYSIS")
        report.append("=" * 60)
        report.append(f"📅 Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"📊 Total Stocks Analyzed: {len(stock_data)}")
        report.append(f"🏢 Total Sectors: {len(self.sectors)}")
        report.append("")
        
        # Sector-wise analysis
        for sector_name, sector_info in self.sectors.items():
            report.append(f"## 🏢 {sector_name.upper()}")
            report.append(f"📝 {sector_info.description}")
            report.append(f"📈 Stocks: {len(sector_info.stocks)}")
            report.append("")
            
            # Get stocks in this sector
            sector_stocks = []
            for stock_symbol in sector_info.stocks:
                if stock_symbol in stock_data:
                    sector_stocks.append(stock_data[stock_symbol])
            
            if not sector_stocks:
                report.append("⚠️  No momentum data available for this sector")
                report.append("")
                continue
            
            # Analyze 1W momentum
            stocks_with_1w = [s for s in sector_stocks if s.momentum_1w is not None]
            if stocks_with_1w:
                avg_1w = sum(s.momentum_1w for s in stocks_with_1w) / len(stocks_with_1w)
                positive_1w = len([s for s in stocks_with_1w if s.momentum_1w > 0])
                
                report.append(f"⏱️  1W Momentum:")
                report.append(f"   📊 Average: {avg_1w:+.2f}%")
                report.append(f"   📈 Positive: {positive_1w}/{len(stocks_with_1w)} ({positive_1w/len(stocks_with_1w)*100:.1f}%)")
                
                # Top and bottom performers
                stocks_with_1w.sort(key=lambda x: x.momentum_1w or 0, reverse=True)
                
                report.append(f"   🏆 Top: {stocks_with_1w[0].symbol} ({stocks_with_1w[0].momentum_1w:+.2f}%)")
                if len(stocks_with_1w) > 1:
                    report.append(f"   📉 Bottom: {stocks_with_1w[-1].symbol} ({stocks_with_1w[-1].momentum_1w:+.2f}%)")
                report.append("")
            
            # Analyze 1M momentum
            stocks_with_1m = [s for s in sector_stocks if s.momentum_1m is not None]
            if stocks_with_1m:
                avg_1m = sum(s.momentum_1m for s in stocks_with_1m) / len(stocks_with_1m)
                positive_1m = len([s for s in stocks_with_1m if s.momentum_1m > 0])
                
                report.append(f"⏱️  1M Momentum:")
                report.append(f"   📊 Average: {avg_1m:+.2f}%")
                report.append(f"   📈 Positive: {positive_1m}/{len(stocks_with_1m)} ({positive_1m/len(stocks_with_1m)*100:.1f}%)")
                
                # Top and bottom performers
                stocks_with_1m.sort(key=lambda x: x.momentum_1m or 0, reverse=True)
                
                report.append(f"   🏆 Top: {stocks_with_1m[0].symbol} ({stocks_with_1m[0].momentum_1m:+.2f}%)")
                if len(stocks_with_1m) > 1:
                    report.append(f"   📉 Bottom: {stocks_with_1m[-1].symbol} ({stocks_with_1m[-1].momentum_1m:+.2f}%)")
                report.append("")
            
            # Individual stock details
            report.append("📋 Individual Stock Performance:")
            for stock in sorted(sector_stocks, key=lambda x: x.symbol):
                momentum_1w = f"{stock.momentum_1w:+.2f}%" if stock.momentum_1w is not None else "N/A"
                momentum_1m = f"{stock.momentum_1m:+.2f}%" if stock.momentum_1m is not None else "N/A"
                report.append(f"   {stock.symbol:12} | 1W: {momentum_1w:>8} | 1M: {momentum_1m:>8}")
            
            report.append("")
            report.append("-" * 50)
            report.append("")
        
        return "\n".join(report)
    
    def generate_market_summary(self, stock_data: Dict[str, StockMomentumData]) -> str:
        """Generate overall market summary"""
        
        report = []
        report.append("🌍 NIFTY 50 MARKET SUMMARY")
        report.append("=" * 40)
        
        # Overall statistics
        all_stocks = list(stock_data.values())
        stocks_with_1w = [s for s in all_stocks if s.momentum_1w is not None]
        stocks_with_1m = [s for s in all_stocks if s.momentum_1m is not None]
        
        if stocks_with_1w:
            avg_1w = sum(s.momentum_1w for s in stocks_with_1w) / len(stocks_with_1w)
            positive_1w = len([s for s in stocks_with_1w if s.momentum_1w > 0])
            
            report.append(f"📊 1W Market Momentum:")
            report.append(f"   Average: {avg_1w:+.2f}%")
            report.append(f"   Bullish: {positive_1w}/{len(stocks_with_1w)} ({positive_1w/len(stocks_with_1w)*100:.1f}%)")
            
            # Market sentiment
            if positive_1w / len(stocks_with_1w) > 0.6:
                sentiment_1w = "🟢 Bullish"
            elif positive_1w / len(stocks_with_1w) > 0.4:
                sentiment_1w = "🟡 Neutral"
            else:
                sentiment_1w = "🔴 Bearish"
            
            report.append(f"   Sentiment: {sentiment_1w}")
            report.append("")
        
        if stocks_with_1m:
            avg_1m = sum(s.momentum_1m for s in stocks_with_1m) / len(stocks_with_1m)
            positive_1m = len([s for s in stocks_with_1m if s.momentum_1m > 0])
            
            report.append(f"📊 1M Market Momentum:")
            report.append(f"   Average: {avg_1m:+.2f}%")
            report.append(f"   Bullish: {positive_1m}/{len(stocks_with_1m)} ({positive_1m/len(stocks_with_1m)*100:.1f}%)")
            
            # Market sentiment
            if positive_1m / len(stocks_with_1m) > 0.6:
                sentiment_1m = "🟢 Bullish"
            elif positive_1m / len(stocks_with_1m) > 0.4:
                sentiment_1m = "🟡 Neutral"
            else:
                sentiment_1m = "🔴 Bearish"
            
            report.append(f"   Sentiment: {sentiment_1m}")
            report.append("")
        
        # Sector rankings
        sector_performance = {}
        for sector_name, sector_info in self.sectors.items():
            sector_stocks = [stock_data[s] for s in sector_info.stocks if s in stock_data]
            
            if sector_stocks:
                stocks_1m = [s for s in sector_stocks if s.momentum_1m is not None]
                if stocks_1m:
                    avg_momentum = sum(s.momentum_1m for s in stocks_1m) / len(stocks_1m)
                    sector_performance[sector_name] = avg_momentum
        
        if sector_performance:
            report.append("🏆 TOP PERFORMING SECTORS (1M):")
            sorted_sectors = sorted(sector_performance.items(), key=lambda x: x[1], reverse=True)
            for i, (sector, performance) in enumerate(sorted_sectors[:5], 1):
                report.append(f"   {i}. {sector:20} {performance:+.2f}%")
            report.append("")
        
        return "\n".join(report)
    
    def export_detailed_csv(self, stock_data: Dict[str, StockMomentumData], filename: str):
        """Export detailed data to CSV"""
        
        csv_data = []
        for stock in stock_data.values():
            csv_data.append({
                'Symbol': stock.symbol,
                'Sector': stock.sector,
                'Momentum_1W': stock.momentum_1w,
                'Momentum_1M': stock.momentum_1m,
                'Momentum_3M': stock.momentum_3m,
                'Momentum_6M': stock.momentum_6m
            })
        
        df = pd.DataFrame(csv_data)
        df.to_csv(filename, index=False)
        print(f"📄 Detailed data exported to: {filename}")
    
    def generate_comprehensive_report(self):
        """Generate complete Nifty 50 sector-wise momentum report"""
        
        print("🚀 NIFTY 50 COMPREHENSIVE SECTOR REPORT")
        print("=" * 50)
        print(f"🕐 Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("")
        
        # Get momentum data
        stock_data = self.get_current_momentum_data()
        
        # Generate market summary
        market_summary = self.generate_market_summary(stock_data)
        print(market_summary)
        print("")
        
        # Generate sector analysis
        sector_analysis = self.generate_sector_analysis(stock_data)
        print(sector_analysis)
        
        # Export to files
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Export CSV
        csv_filename = f"reports/nifty50_sector_analysis_{timestamp}.csv"
        os.makedirs("reports", exist_ok=True)
        self.export_detailed_csv(stock_data, csv_filename)
        
        # Export full report
        full_report = market_summary + "\n\n" + sector_analysis
        txt_filename = f"reports/nifty50_sector_report_{timestamp}.txt"
        with open(txt_filename, 'w', encoding='utf-8') as f:
            f.write(full_report)
        
        print(f"📋 Full report saved to: {txt_filename}")
        
        # Summary statistics
        total_stocks = len(stock_data)
        stocks_with_data = len([s for s in stock_data.values() if s.momentum_1w is not None or s.momentum_1m is not None])
        
        print(f"\n📊 REPORT SUMMARY:")
        print(f"   Total Nifty 50 stocks: {total_stocks}")
        print(f"   Stocks with momentum data: {stocks_with_data}")
        print(f"   Total sectors analyzed: {len(self.sectors)}")
        print(f"   Reports generated: 2 files")
        print(f"🎉 Analysis complete!")


def main():
    """Main execution function"""
    
    try:
        reporter = Nifty50SectorReport()
        reporter.generate_comprehensive_report()
        
    except Exception as e:
        print(f"❌ Error generating report: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()