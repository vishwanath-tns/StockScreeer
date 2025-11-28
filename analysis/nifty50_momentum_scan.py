"""
Nifty 50 Comprehensive Momentum Analysis
========================================

Analyzes momentum across all available Nifty 50 stocks with comprehensive reporting.
Includes multi-timeframe analysis, sector insights, and detailed export capabilities.

Features:
---------
- All available Nifty 50 stocks (46 stocks)
- Multiple timeframes: 1W, 1M, 3M, 6M
- Comprehensive reporting with all format exports
- Sector-wise momentum analysis
- Performance rankings and insights

Usage:
------
    python nifty50_momentum_scan.py

Output:
-------
- Console reports with rich formatting
- CSV exports for spreadsheet analysis
- JSON exports for API integration
- Markdown reports for documentation

Author: StockScreener
Date: November 17, 2025
"""

import sys
import os
from datetime import datetime, timedelta
from typing import List, Dict
import pandas as pd
import time

# Add current directory to Python path
sys.path.append('.')

# Import our momentum system
from services.momentum.momentum_calculator import MomentumCalculator, MomentumDuration
from services.momentum.momentum_reporting_service import (
    MomentumReportingService, ReportConfig, ReportType, ReportFormat
)

class Nifty50MomentumAnalyzer:
    """Comprehensive momentum analyzer for Nifty 50 stocks"""
    
    def __init__(self):
        self.calculator = MomentumCalculator()
        self.reporter = MomentumReportingService()
        
        # Nifty 50 stocks (excluding TATAMOTORS - not available in our DB)
        self.nifty50_stocks = [
            'ADANIPORTS', 'ASIANPAINT', 'AXISBANK', 'BAJAJ-AUTO', 'BAJFINANCE',
            'BAJAJFINSV', 'BPCL', 'BHARTIARTL', 'BRITANNIA', 'CIPLA', 'COALINDIA',
            'DIVISLAB', 'DRREDDY', 'EICHERMOT', 'GRASIM', 'HCLTECH', 'HDFCBANK',
            'HDFCLIFE', 'HEROMOTOCO', 'HINDALCO', 'HINDUNILVR', 'ICICIBANK',
            'ITC', 'INDUSINDBK', 'INFY', 'JSWSTEEL', 'KOTAKBANK', 'LT', 'M&M',
            'MARUTI', 'NTPC', 'NESTLEIND', 'ONGC', 'POWERGRID', 'RELIANCE',
            'SBILIFE', 'SBIN', 'SUNPHARMA', 'TCS', 'TATACONSUM', 'TATASTEEL',
            'TECHM', 'TITAN', 'ULTRACEMCO', 'UPL', 'WIPRO'
        ]
        
        # Sector mapping for enhanced analysis
        self.sector_mapping = {
            # Banking & Financial Services
            'AXISBANK': 'Banking', 'HDFCBANK': 'Banking', 'ICICIBANK': 'Banking',
            'INDUSINDBK': 'Banking', 'KOTAKBANK': 'Banking', 'SBIN': 'Banking',
            'BAJFINANCE': 'Financial Services', 'BAJAJFINSV': 'Financial Services',
            'HDFCLIFE': 'Financial Services', 'SBILIFE': 'Financial Services',
            
            # IT Services
            'INFY': 'IT Services', 'TCS': 'IT Services', 'TECHM': 'IT Services',
            'HCLTECH': 'IT Services', 'WIPRO': 'IT Services',
            
            # Oil & Gas
            'RELIANCE': 'Oil & Gas', 'ONGC': 'Oil & Gas', 'BPCL': 'Oil & Gas',
            
            # Metals & Mining
            'TATASTEEL': 'Metals', 'JSWSTEEL': 'Metals', 'HINDALCO': 'Metals',
            'COALINDIA': 'Metals',
            
            # Auto & Auto Components
            'MARUTI': 'Auto', 'BAJAJ-AUTO': 'Auto', 'M&M': 'Auto',
            'HEROMOTOCO': 'Auto', 'EICHERMOT': 'Auto',
            
            # Pharma
            'SUNPHARMA': 'Pharma', 'DRREDDY': 'Pharma', 'CIPLA': 'Pharma',
            'DIVISLAB': 'Pharma',
            
            # FMCG
            'HINDUNILVR': 'FMCG', 'BRITANNIA': 'FMCG', 'NESTLEIND': 'FMCG',
            'ITC': 'FMCG', 'TATACONSUM': 'FMCG',
            
            # Telecom
            'BHARTIARTL': 'Telecom',
            
            # Power & Utilities
            'NTPC': 'Power', 'POWERGRID': 'Power',
            
            # Cement & Construction
            'ULTRACEMCO': 'Cement', 'GRASIM': 'Cement', 'LT': 'Construction',
            
            # Chemicals & Paints
            'ASIANPAINT': 'Paints', 'UPL': 'Chemicals',
            
            # Logistics & Ports
            'ADANIPORTS': 'Logistics',
            
            # Jewellery & Consumer Goods
            'TITAN': 'Jewellery'
        }
    
    def calculate_nifty50_momentum(self, durations: List[MomentumDuration] = None) -> int:
        """
        Calculate momentum for all Nifty 50 stocks
        
        Args:
            durations: List of durations to calculate. Defaults to [1W, 1M, 3M, 6M]
            
        Returns:
            int: Number of successful calculations
        """
        if durations is None:
            durations = [
                MomentumDuration.ONE_WEEK,
                MomentumDuration.ONE_MONTH,
                MomentumDuration.THREE_MONTHS,
                MomentumDuration.SIX_MONTHS
            ]
        
        print(f"🚀 Starting Nifty 50 Momentum Analysis")
        print(f"📊 Stocks to analyze: {len(self.nifty50_stocks)}")
        print(f"⏱️  Durations: {[d.value for d in durations]}")
        print(f"🕐 Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 60)
        
        start_time = time.time()
        
        # Calculate momentum in batches for better performance
        batch_size = 10
        total_calculations = 0
        
        for i in range(0, len(self.nifty50_stocks), batch_size):
            batch_stocks = self.nifty50_stocks[i:i + batch_size]
            batch_num = (i // batch_size) + 1
            total_batches = (len(self.nifty50_stocks) + batch_size - 1) // batch_size
            
            print(f"\n📦 Processing batch {batch_num}/{total_batches}: {batch_stocks}")
            
            try:
                batch_results = self.calculator.calculate_momentum_batch(
                    symbols=batch_stocks,
                    durations=durations
                )
                
                # batch_results is a dict with symbol keys and lists of MomentumResult objects
                successful = len(batch_results)  # Number of symbols with results
                total_calculations += successful
                
                print(f"✅ Batch {batch_num} completed: {successful}/{len(batch_stocks)} successful")
                
                # Show some sample results from this batch
                for symbol, momentum_results in list(batch_results.items())[:3]:  # Show first 3 symbols
                    if momentum_results:
                        momentum = momentum_results[0]  # First duration result
                        print(f"   💹 {symbol}: {momentum.momentum_percentage:.2f}% ({momentum.duration.value})")
                
            except Exception as e:
                print(f"❌ Error processing batch {batch_num}: {e}")
                continue
        
        end_time = time.time()
        elapsed = end_time - start_time
        
        print("\n" + "=" * 60)
        print(f"🏁 Nifty 50 Momentum Analysis Complete!")
        print(f"✅ Total successful calculations: {total_calculations}")
        print(f"⏱️  Total time taken: {elapsed:.2f} seconds")
        print(f"📈 Average time per stock: {elapsed/len(self.nifty50_stocks):.2f} seconds")
        
        return total_calculations
    
    def generate_comprehensive_reports(self):
        """Generate all types of momentum reports for Nifty 50"""
        
        print("\n" + "🔥" * 20 + " COMPREHENSIVE NIFTY 50 REPORTS " + "🔥" * 20)
        
        # Report configurations for different analysis needs
        report_configs = [
            {
                'name': 'Market Summary',
                'config': ReportConfig(
                    report_type=ReportType.MOMENTUM_SUMMARY,
                    duration_types=[
                        MomentumDuration.ONE_WEEK,
                        MomentumDuration.ONE_MONTH,
                        MomentumDuration.THREE_MONTHS,
                        MomentumDuration.SIX_MONTHS
                    ]
                )
            },
            {
                'name': 'Top Performers (Weekly)',
                'config': ReportConfig(
                    report_type=ReportType.TOP_PERFORMERS,
                    duration_types=[MomentumDuration.ONE_WEEK],
                    top_n=20
                )
            },
            {
                'name': 'Top Performers (Monthly)',
                'config': ReportConfig(
                    report_type=ReportType.TOP_PERFORMERS,
                    duration_types=[MomentumDuration.ONE_MONTH],
                    top_n=20
                )
            },
            {
                'name': 'Cross-Duration Analysis',
                'config': ReportConfig(
                    report_type=ReportType.CROSS_DURATION_ANALYSIS,
                    duration_types=[
                        MomentumDuration.ONE_WEEK,
                        MomentumDuration.ONE_MONTH,
                        MomentumDuration.THREE_MONTHS
                    ]
                )
            },
            {
                'name': 'Momentum Heatmap',
                'config': ReportConfig(
                    report_type=ReportType.MOMENTUM_HEATMAP,
                    duration_types=[
                        MomentumDuration.ONE_WEEK,
                        MomentumDuration.ONE_MONTH,
                        MomentumDuration.THREE_MONTHS,
                        MomentumDuration.SIX_MONTHS
                    ]
                )
            },
            {
                'name': 'Strength Distribution',
                'config': ReportConfig(
                    report_type=ReportType.STRENGTH_DISTRIBUTION,
                    duration_types=[
                        MomentumDuration.ONE_WEEK,
                        MomentumDuration.ONE_MONTH,
                        MomentumDuration.THREE_MONTHS
                    ]
                )
            }
        ]
        
        # Generate console reports
        for i, report_config in enumerate(report_configs, 1):
            print(f"\n[{i}/{len(report_configs)}] 📊 {report_config['name']}")
            print("=" * 80)
            
            try:
                report = self.reporter.generate_report(report_config['config'])
                print(report)
            except Exception as e:
                print(f"❌ Error generating {report_config['name']}: {e}")
            
            print("-" * 80)
    
    def export_analysis_files(self):
        """Export comprehensive analysis to various file formats"""
        
        print("\n" + "💾" * 15 + " EXPORTING ANALYSIS FILES " + "💾" * 15)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Export configurations
        exports = [
            {
                'name': 'Nifty 50 Top Performers CSV',
                'config': ReportConfig(
                    report_type=ReportType.TOP_PERFORMERS,
                    duration_types=[
                        MomentumDuration.ONE_WEEK,
                        MomentumDuration.ONE_MONTH,
                        MomentumDuration.THREE_MONTHS
                    ],
                    top_n=50,
                    output_format=ReportFormat.CSV,
                    output_file=f'reports/nifty50_top_performers_{timestamp}.csv'
                )
            },
            {
                'name': 'Nifty 50 Market Summary JSON',
                'config': ReportConfig(
                    report_type=ReportType.MOMENTUM_SUMMARY,
                    duration_types=[
                        MomentumDuration.ONE_WEEK,
                        MomentumDuration.ONE_MONTH,
                        MomentumDuration.THREE_MONTHS,
                        MomentumDuration.SIX_MONTHS
                    ],
                    output_format=ReportFormat.JSON,
                    output_file=f'reports/nifty50_market_summary_{timestamp}.json'
                )
            },
            {
                'name': 'Nifty 50 Cross-Duration Analysis Markdown',
                'config': ReportConfig(
                    report_type=ReportType.CROSS_DURATION_ANALYSIS,
                    duration_types=[
                        MomentumDuration.ONE_WEEK,
                        MomentumDuration.ONE_MONTH,
                        MomentumDuration.THREE_MONTHS
                    ],
                    output_format=ReportFormat.MARKDOWN,
                    output_file=f'reports/nifty50_cross_duration_{timestamp}.md'
                )
            },
            {
                'name': 'Nifty 50 Momentum Heatmap CSV',
                'config': ReportConfig(
                    report_type=ReportType.MOMENTUM_HEATMAP,
                    duration_types=[
                        MomentumDuration.ONE_WEEK,
                        MomentumDuration.ONE_MONTH,
                        MomentumDuration.THREE_MONTHS,
                        MomentumDuration.SIX_MONTHS
                    ],
                    output_format=ReportFormat.CSV,
                    output_file=f'reports/nifty50_heatmap_{timestamp}.csv'
                )
            }
        ]
        
        # Generate exports
        for i, export in enumerate(exports, 1):
            print(f"\n[{i}/{len(exports)}] 📄 {export['name']}")
            
            try:
                result = self.reporter.generate_report(export['config'])
                print(f"✅ Successfully exported: {export['config'].output_file}")
                
                # Show file size if it exists
                if export['config'].output_file and os.path.exists(export['config'].output_file):
                    size = os.path.getsize(export['config'].output_file)
                    print(f"📊 File size: {size:,} bytes")
                
            except Exception as e:
                print(f"❌ Export failed: {e}")
    
    def run_full_analysis(self):
        """Run complete Nifty 50 momentum analysis pipeline"""
        
        print("🚀 NIFTY 50 COMPREHENSIVE MOMENTUM ANALYSIS")
        print("=" * 60)
        print(f"📅 Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"📊 Stocks: {len(self.nifty50_stocks)} Nifty 50 companies")
        print(f"⏱️  Timeframes: 1W, 1M, 3M, 6M")
        print(f"📈 Analysis: Multi-timeframe momentum with comprehensive reporting")
        print("=" * 60)
        
        # Step 1: Calculate momentum for all stocks
        calculations = self.calculate_nifty50_momentum()
        
        if calculations == 0:
            print("❌ No successful momentum calculations. Aborting analysis.")
            return False
        
        # Step 2: Generate comprehensive reports
        self.generate_comprehensive_reports()
        
        # Step 3: Export analysis files
        self.export_analysis_files()
        
        print("\n" + "🎉" * 15 + " ANALYSIS COMPLETE " + "🎉" * 15)
        print(f"✅ Successfully analyzed {calculations} momentum data points")
        print(f"📊 Generated comprehensive reports for Nifty 50 stocks")
        print(f"💾 Exported analysis files for further review")
        print(f"🕐 Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        return True


def main():
    """Main execution function"""
    
    try:
        # Create analyzer and run full analysis
        analyzer = Nifty50MomentumAnalyzer()
        success = analyzer.run_full_analysis()
        
        if success:
            print("\n💡 NEXT STEPS:")
            print("1. Review exported CSV files for spreadsheet analysis")
            print("2. Check JSON files for programmatic integration")
            print("3. Use Markdown reports for team sharing")
            print("4. Monitor top performers for trading opportunities")
            print("5. Set up daily automation for ongoing analysis")
            
        else:
            print("\n❌ Analysis failed. Please check database connection and data availability.")
            
    except Exception as e:
        print(f"\n💥 Critical error in main analysis: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True


if __name__ == "__main__":
    main()