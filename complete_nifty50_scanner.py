"""
Complete Nifty 50 Momentum Scanner
=================================

This scanner calculates momentum data for ALL Nifty 50 stocks across multiple timeframes
and stores the results in the database for comprehensive analysis.
"""

import sys
import os
from datetime import datetime, timedelta
import time
from typing import List, Optional
import pandas as pd

sys.path.append('.')

# Import services
from services.momentum.momentum_calculator import MomentumCalculator, MomentumDuration
from services.momentum.database_service import DatabaseService
from volatility_patterns.data.data_service import DataService
from services.market_breadth_service import get_engine

class CompleteNifty50Scanner:
    """Complete momentum scanner for all Nifty 50 stocks"""
    
    def __init__(self):
        self.calculator = MomentumCalculator()
        self.db_service = DatabaseService()
        self.data_service = DataService()
        
        # Complete Nifty 50 list
        self.nifty50_stocks = [
            # Banking
            'AXISBANK', 'HDFCBANK', 'ICICIBANK', 'INDUSINDBK', 'KOTAKBANK', 'SBIN',
            
            # Financial Services
            'BAJFINANCE', 'BAJAJFINSV', 'HDFCLIFE', 'SBILIFE',
            
            # IT Services
            'INFY', 'TCS', 'TECHM', 'HCLTECH', 'WIPRO',
            
            # Oil & Gas
            'RELIANCE', 'ONGC', 'BPCL',
            
            # Metals & Mining
            'TATASTEEL', 'JSWSTEEL', 'HINDALCO', 'COALINDIA',
            
            # Automotive
            'MARUTI', 'BAJAJ-AUTO', 'M&M', 'HEROMOTOCO', 'EICHERMOT',
            
            # Pharmaceuticals
            'SUNPHARMA', 'DRREDDY', 'CIPLA', 'DIVISLAB',
            
            # FMCG
            'HINDUNILVR', 'BRITANNIA', 'NESTLEIND', 'ITC', 'TATACONSUM',
            
            # Others
            'BHARTIARTL', 'NTPC', 'POWERGRID', 'ULTRACEMCO', 'GRASIM',
            'LT', 'ASIANPAINT', 'UPL', 'TITAN', 'ADANIPORTS'
        ]
        
        print(f"Initialized scanner for {len(self.nifty50_stocks)} Nifty 50 stocks")
    
    def check_data_availability(self, symbol: str) -> bool:
        """Check if sufficient data exists for momentum calculation"""
        try:
            end_date = datetime.now().date()
            start_date = end_date - timedelta(days=40)  # Extra buffer for data
            
            df = self.data_service.fetch_stock_data(symbol, start_date, end_date)
            
            if df is None or len(df) < 30:  # Need at least 30 days for 1M calculation
                return False
            
            return True
            
        except Exception as e:
            print(f"  Error checking data for {symbol}: {e}")
            return False
    
    def calculate_stock_momentum(self, symbol: str, durations: List[MomentumDuration]) -> int:
        """Calculate momentum for a single stock across multiple durations"""
        
        successful_calculations = 0
        
        for duration in durations:
            try:
                # Use the batch calculation method that works
                results = self.calculator.calculate_momentum_batch([symbol], [duration])
                
                if results and len(results) > 0:
                    result = results[0]
                    
                    # Check if result has the expected attributes
                    if hasattr(result, 'percentage_change') and hasattr(result, 'symbol'):
                        print(f"    {duration.value}: {result.percentage_change:+.2f}%")
                        successful_calculations += 1
                    else:
                        print(f"    {duration.value}: Unexpected result format")
                else:
                    print(f"    {duration.value}: No result returned")
                    
            except Exception as e:
                print(f"    {duration.value}: Error - {e}")
        
        return successful_calculations
    
    def scan_all_stocks(self):
        """Scan all Nifty 50 stocks for momentum"""
        
        print("COMPLETE NIFTY 50 MOMENTUM SCAN")
        print("=" * 40)
        print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Total stocks to scan: {len(self.nifty50_stocks)}")
        print("")
        
        # Durations to calculate
        durations = [
            MomentumDuration.ONE_WEEK, 
            MomentumDuration.ONE_MONTH,
            MomentumDuration.THREE_MONTHS,
            MomentumDuration.SIX_MONTHS
        ]
        
        print(f"Calculating {len(durations)} timeframes: {[d.value for d in durations]}")
        print("")
        
        total_calculations = 0
        successful_stocks = 0
        stocks_with_data = []
        stocks_without_data = []
        
        # Process each stock
        for i, symbol in enumerate(self.nifty50_stocks, 1):
            print(f"{i:2d}/{len(self.nifty50_stocks):2d} Processing {symbol}")
            
            # Check data availability first
            if not self.check_data_availability(symbol):
                print(f"  Insufficient data available")
                stocks_without_data.append(symbol)
                continue
            
            # Calculate momentum for this stock
            calculations_done = self.calculate_stock_momentum(symbol, durations)
            
            if calculations_done > 0:
                total_calculations += calculations_done
                successful_stocks += 1
                stocks_with_data.append(symbol)
                print(f"  Success: {calculations_done}/{len(durations)} calculations completed")
            else:
                stocks_without_data.append(symbol)
                print(f"  Failed: No successful calculations")
            
            # Small delay to be nice to the database
            time.sleep(0.1)
            
            print("")
        
        # Summary
        print("SCAN COMPLETION SUMMARY")
        print("=" * 30)
        print(f"Total stocks scanned: {len(self.nifty50_stocks)}")
        print(f"Stocks with data: {successful_stocks}")
        print(f"Stocks without data: {len(stocks_without_data)}")
        print(f"Total calculations: {total_calculations}")
        print(f"Success rate: {successful_stocks/len(self.nifty50_stocks)*100:.1f}%")
        
        if stocks_with_data:
            print(f"\nStocks with momentum data:")
            for stock in stocks_with_data[:10]:  # Show first 10
                print(f"  {stock}")
            if len(stocks_with_data) > 10:
                print(f"  ... and {len(stocks_with_data)-10} more")
        
        if stocks_without_data:
            print(f"\nStocks needing attention:")
            for stock in stocks_without_data[:5]:  # Show first 5
                print(f"  {stock}")
            if len(stocks_without_data) > 5:
                print(f"  ... and {len(stocks_without_data)-5} more")
        
        return {
            'total_stocks': len(self.nifty50_stocks),
            'successful_stocks': successful_stocks,
            'total_calculations': total_calculations,
            'stocks_with_data': stocks_with_data,
            'stocks_without_data': stocks_without_data
        }
    
    def verify_database_data(self):
        """Verify what data is now in the database"""
        
        print("\nVERIFYING DATABASE DATA")
        print("=" * 25)
        
        try:
            engine = get_engine()
            
            with engine.connect() as conn:
                # Count total records
                count_query = "SELECT COUNT(*) as total FROM momentum_analysis WHERE calculation_date = CURDATE()"
                total_records = pd.read_sql(count_query, conn).iloc[0]['total']
                
                # Count unique symbols
                symbol_query = """
                SELECT COUNT(DISTINCT symbol) as unique_symbols 
                FROM momentum_analysis 
                WHERE calculation_date = CURDATE()
                """
                unique_symbols = pd.read_sql(symbol_query, conn).iloc[0]['unique_symbols']
                
                # Get sample data
                sample_query = """
                SELECT symbol, duration_type, percentage_change 
                FROM momentum_analysis 
                WHERE calculation_date = CURDATE()
                ORDER BY symbol, duration_type
                LIMIT 10
                """
                sample_data = pd.read_sql(sample_query, conn)
                
                print(f"Total momentum records today: {total_records}")
                print(f"Unique symbols: {unique_symbols}")
                print(f"Expected total: {len(self.nifty50_stocks) * 4} (46 stocks × 4 durations)")
                print("")
                
                if len(sample_data) > 0:
                    print("Sample records in database:")
                    for _, row in sample_data.iterrows():
                        print(f"  {row['symbol']:12} | {row['duration_type']:2} | {row['percentage_change']:+.2f}%")
                else:
                    print("No momentum data found in database for today")
                
        except Exception as e:
            print(f"Error verifying database: {e}")
    
    def run_complete_scan(self):
        """Run the complete scanning process"""
        
        print("NIFTY 50 COMPLETE MOMENTUM SCANNING")
        print("=" * 50)
        print(f"Starting comprehensive scan at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("")
        
        # Run the scan
        results = self.scan_all_stocks()
        
        # Verify database
        self.verify_database_data()
        
        # Final summary
        print(f"\nFINAL RESULTS:")
        print(f"Scan completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Database should now contain momentum data for {results['successful_stocks']} stocks")
        print(f"Total momentum calculations: {results['total_calculations']}")
        
        if results['successful_stocks'] >= 40:  # If we got most stocks
            print("SUCCESS: Database is now populated with comprehensive Nifty 50 momentum data!")
        elif results['successful_stocks'] >= 20:
            print("PARTIAL SUCCESS: Good coverage achieved, some stocks may need attention")
        else:
            print("LIMITED SUCCESS: Many stocks need data or system attention")
        
        return results


def main():
    """Main execution function"""
    try:
        scanner = CompleteNifty50Scanner()
        results = scanner.run_complete_scan()
        
        print(f"\nScan completed successfully!")
        print(f"Run the report generator again to see updated data for all stocks.")
        
    except Exception as e:
        print(f"Error during scan: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()