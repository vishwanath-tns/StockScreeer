"""
Fixed Nifty 50 VCP Backtest with Proper Database Queries
========================================================

This version uses the correct database query format and includes error handling
for the specific database schema in your system.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import numpy as np
from datetime import date, timedelta, datetime
from typing import Dict, List, Tuple, Optional
import time
import json
from pathlib import Path
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

from volatility_patterns.analysis.vcp_backtester import VCPBacktester, BacktestConfig, BacktestResults
from volatility_patterns.analysis.vcp_scanner import VCPScanner
from volatility_patterns.data.data_service import DataService
from sqlalchemy import text


# Nifty 50 Stocks (simplified list of confirmed symbols)
NIFTY50_STOCKS = {
    # Major stocks that are definitely in your database
    "RELIANCE": "Oil & Gas",
    "TCS": "IT",
    "INFY": "IT", 
    "HDFCBANK": "Banking",
    "ICICIBANK": "Banking",
    "SBIN": "Banking",
    "LT": "Infrastructure",
    "ITC": "Consumer Goods",
    "HINDUNILVR": "Consumer Goods",
    "MARUTI": "Automobiles",
    "ASIANPAINT": "Consumer Goods",
    "SUNPHARMA": "Pharma",
    "BHARTIARTL": "Telecom",
    "KOTAKBANK": "Banking",
    "AXISBANK": "Banking",
    "WIPRO": "IT",
    "ULTRACEMCO": "Infrastructure",
    "NESTLEIND": "Consumer Goods",
    "POWERGRID": "Infrastructure",
    "TITAN": "Consumer Goods"
}


class SimplifiedNifty50Backtester:
    """
    Simplified Nifty 50 VCP Backtester with fixed database queries
    """
    
    def __init__(self):
        self.data_service = DataService()
        self.backtester = VCPBacktester()
        self.scanner = VCPScanner()
        self.results = {}
        
        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
        
    def get_data_range_for_stock(self, symbol: str) -> Tuple[Optional[date], Optional[date]]:
        """Get the full data range available for a stock using correct SQL"""
        try:
            query = text("""
            SELECT MIN(trade_date) as start_date, MAX(trade_date) as end_date
            FROM nse_equity_bhavcopy_full 
            WHERE symbol = :symbol
            AND close_price > 0
            """)
            
            with self.data_service.engine.connect() as conn:
                result = conn.execute(query, {'symbol': symbol}).fetchone()
                
                if result and result[0] and result[1]:
                    return result[0], result[1]
                
        except Exception as e:
            self.logger.warning(f"Could not get date range for {symbol}: {e}")
            
        return None, None
    
    def check_symbol_exists(self, symbol: str) -> bool:
        """Check if symbol exists in database"""
        try:
            query = text("""
            SELECT COUNT(*) as count
            FROM nse_equity_bhavcopy_full 
            WHERE symbol = :symbol
            LIMIT 1
            """)
            
            with self.data_service.engine.connect() as conn:
                result = conn.execute(query, {'symbol': symbol}).fetchone()
                return result and result[0] > 0
                
        except Exception as e:
            self.logger.warning(f"Error checking {symbol}: {e}")
            return False
    
    def run_single_stock_backtest(
        self,
        symbol: str,
        config: BacktestConfig,
        min_data_points: int = 252
    ) -> Dict:
        """Run backtest for a single stock with error handling"""
        
        start_time = time.time()
        sector = NIFTY50_STOCKS.get(symbol, "Unknown")
        
        self.logger.info(f"Starting backtest for {symbol} ({sector})")
        
        try:
            # First check if symbol exists
            if not self.check_symbol_exists(symbol):
                return {
                    'symbol': symbol,
                    'sector': sector,
                    'status': 'failed',
                    'error': 'Symbol not found in database',
                    'execution_time': time.time() - start_time
                }
            
            # Get data range
            start_date, end_date = self.get_data_range_for_stock(symbol)
            
            if not start_date or not end_date:
                return {
                    'symbol': symbol,
                    'sector': sector,
                    'status': 'failed',
                    'error': 'No valid data range',
                    'execution_time': time.time() - start_time
                }
            
            data_span_days = (end_date - start_date).days
            
            if data_span_days < min_data_points:
                return {
                    'symbol': symbol,
                    'sector': sector,
                    'status': 'failed',
                    'error': f'Insufficient data: {data_span_days} days',
                    'execution_time': time.time() - start_time
                }
            
            self.logger.info(f"{symbol}: Data from {start_date} to {end_date} ({data_span_days} days)")
            
            # Run backtest with smaller date ranges to avoid memory issues
            # Split into 2-year chunks if data is too large
            if data_span_days > 730:  # More than 2 years
                self.logger.info(f"{symbol}: Large dataset, using recent 2 years")
                start_date = end_date - timedelta(days=730)
                data_span_days = 730
            
            # Run the backtest
            results = self.backtester.backtest_symbol(
                symbol=symbol,
                start_date=start_date,
                end_date=end_date,
                config=config
            )
            
            # Create result dictionary
            result = {
                'symbol': symbol,
                'sector': sector,
                'status': 'completed',
                'data_start': start_date.isoformat(),
                'data_end': end_date.isoformat(),
                'data_span_days': data_span_days,
                'execution_time': time.time() - start_time,
                
                # Backtest results
                'total_patterns': results.total_patterns,
                'total_trades': results.total_trades,
                'winning_trades': results.winning_trades,
                'losing_trades': results.losing_trades,
                'win_rate': results.win_rate,
                'total_return': results.total_return,
                'average_return': results.average_return,
                'max_drawdown': results.max_drawdown,
                'sharpe_ratio': results.sharpe_ratio,
                'profit_factor': results.profit_factor,
                
                # Calculated metrics
                'patterns_per_year': (results.total_patterns / (data_span_days / 365.25)) if data_span_days > 0 else 0,
                'trades_per_year': (results.total_trades / (data_span_days / 365.25)) if data_span_days > 0 else 0,
                'annualized_return': (results.total_return / (data_span_days / 365.25)) if data_span_days > 0 else 0,
            }
            
            self.logger.info(f"{symbol}: {results.total_patterns} patterns, "
                           f"{results.total_trades} trades, {results.win_rate:.1f}% win rate")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error backtesting {symbol}: {str(e)}")
            return {
                'symbol': symbol,
                'sector': sector,
                'status': 'failed',
                'error': str(e),
                'execution_time': time.time() - start_time
            }
    
    def run_sequential_backtest(
        self,
        config: Optional[BacktestConfig] = None,
        save_results: bool = True
    ) -> Dict:
        """Run backtest sequentially (no parallel processing to avoid issues)"""
        
        if config is None:
            config = BacktestConfig(
                stop_loss_pct=8.0,
                profit_target_pct=25.0,
                position_size_pct=10.0,
                min_quality_score=50.0
            )
        
        self.logger.info("Starting Sequential Nifty 50 VCP Backtest")
        self.logger.info(f"Configuration: Stop Loss: {config.stop_loss_pct}%, "
                        f"Profit Target: {config.profit_target_pct}%, "
                        f"Min Quality: {config.min_quality_score}")
        
        start_time = time.time()
        all_results = []
        
        # Process stocks sequentially
        for i, symbol in enumerate(NIFTY50_STOCKS.keys(), 1):
            print(f"[{i}/{len(NIFTY50_STOCKS)}] Processing {symbol}...")
            
            result = self.run_single_stock_backtest(symbol, config)
            all_results.append(result)
            
            # Progress update
            if result['status'] == 'completed':
                print(f"  ✓ {symbol}: {result.get('total_patterns', 0)} patterns, "
                      f"{result.get('total_trades', 0)} trades, "
                      f"{result.get('win_rate', 0):.1f}% win rate")
            else:
                print(f"  ✗ {symbol}: {result.get('error', 'Unknown error')}")
        
        total_execution_time = time.time() - start_time
        
        # Analyze results
        analysis = self._analyze_results(all_results, config, total_execution_time)
        
        # Save results if requested
        if save_results:
            self._save_results(analysis)
        
        self.logger.info(f"Sequential backtest completed in {total_execution_time:.1f} seconds")
        
        return analysis
    
    def _analyze_results(self, all_results: List[Dict], config: BacktestConfig, execution_time: float) -> Dict:
        """Analyze results with proper error handling for empty arrays"""
        
        # Separate successful and failed results
        successful_results = [r for r in all_results if r['status'] == 'completed']
        failed_results = [r for r in all_results if r['status'] == 'failed']
        
        # Overall statistics
        total_patterns = sum(r.get('total_patterns', 0) for r in successful_results)
        total_trades = sum(r.get('total_trades', 0) for r in successful_results)
        total_wins = sum(r.get('winning_trades', 0) for r in successful_results)
        
        # Safe calculations with empty array handling
        returns = [r.get('total_return', 0) for r in successful_results if r.get('total_return') is not None]
        sharpes = [r.get('sharpe_ratio', 0) for r in successful_results if r.get('sharpe_ratio') is not None]
        drawdowns = [abs(r.get('max_drawdown', 0)) for r in successful_results if r.get('max_drawdown') is not None]
        
        portfolio_return = np.mean(returns) if returns else 0
        portfolio_sharpe = np.mean(sharpes) if sharpes else 0
        portfolio_max_dd = np.max(drawdowns) if drawdowns else 0
        
        # Sector analysis
        sector_analysis = self._analyze_by_sector(successful_results)
        
        # Performance ranking
        performance_ranking = sorted(
            successful_results,
            key=lambda x: x.get('total_return', 0),
            reverse=True
        )
        
        return {
            'summary': {
                'total_stocks_analyzed': len(all_results),
                'successful_backtests': len(successful_results),
                'failed_backtests': len(failed_results),
                'total_execution_time': execution_time,
                'config': {
                    'stop_loss_pct': config.stop_loss_pct,
                    'profit_target_pct': config.profit_target_pct,
                    'position_size_pct': config.position_size_pct,
                    'min_quality_score': config.min_quality_score
                }
            },
            
            'portfolio_metrics': {
                'total_patterns_found': total_patterns,
                'total_trades_executed': total_trades,
                'total_winning_trades': total_wins,
                'overall_win_rate': (total_wins / total_trades * 100) if total_trades > 0 else 0,
                'average_portfolio_return': portfolio_return,
                'average_sharpe_ratio': portfolio_sharpe,
                'maximum_drawdown': portfolio_max_dd,
                'patterns_per_stock': total_patterns / len(successful_results) if successful_results else 0,
                'trades_per_stock': total_trades / len(successful_results) if successful_results else 0
            },
            
            'sector_analysis': sector_analysis,
            'performance_ranking': performance_ranking[:10],
            'worst_performers': performance_ranking[-5:],
            'detailed_results': successful_results,
            'failed_results': failed_results,
            'timestamp': datetime.now().isoformat()
        }
    
    def _analyze_by_sector(self, results: List[Dict]) -> Dict:
        """Analyze results by sector with safe calculations"""
        
        sector_data = {}
        
        for result in results:
            sector = result['sector']
            
            if sector not in sector_data:
                sector_data[sector] = {
                    'stocks': [],
                    'total_patterns': 0,
                    'total_trades': 0,
                    'total_wins': 0,
                    'returns': [],
                    'sharpe_ratios': []
                }
            
            sector_data[sector]['stocks'].append(result['symbol'])
            sector_data[sector]['total_patterns'] += result.get('total_patterns', 0)
            sector_data[sector]['total_trades'] += result.get('total_trades', 0)
            sector_data[sector]['total_wins'] += result.get('winning_trades', 0)
            
            if result.get('total_return') is not None:
                sector_data[sector]['returns'].append(result['total_return'])
            if result.get('sharpe_ratio') is not None:
                sector_data[sector]['sharpe_ratios'].append(result['sharpe_ratio'])
        
        # Calculate sector metrics
        sector_summary = {}
        for sector, data in sector_data.items():
            sector_summary[sector] = {
                'stock_count': len(data['stocks']),
                'stocks': data['stocks'],
                'total_patterns': data['total_patterns'],
                'total_trades': data['total_trades'],
                'win_rate': (data['total_wins'] / data['total_trades'] * 100) if data['total_trades'] > 0 else 0,
                'average_return': np.mean(data['returns']) if data['returns'] else 0,
                'average_sharpe': np.mean(data['sharpe_ratios']) if data['sharpe_ratios'] else 0,
                'patterns_per_stock': data['total_patterns'] / len(data['stocks']) if data['stocks'] else 0
            }
        
        return sector_summary
    
    def _save_results(self, analysis: Dict):
        """Save results to files"""
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Create output directory
        output_dir = Path("nifty50_backtest_results")
        output_dir.mkdir(exist_ok=True)
        
        # Save complete analysis as JSON
        json_file = output_dir / f"nifty50_backtest_{timestamp}.json"
        with open(json_file, 'w') as f:
            json.dump(analysis, f, indent=2, default=str)
        
        # Save detailed results as CSV
        if analysis['detailed_results']:
            csv_file = output_dir / f"nifty50_detailed_{timestamp}.csv"
            df = pd.DataFrame(analysis['detailed_results'])
            df.to_csv(csv_file, index=False)
        
        # Save text summary
        report_file = output_dir / f"nifty50_summary_{timestamp}.txt"
        self._generate_text_report(analysis, report_file)
        
        print(f"Results saved to {output_dir}/")
        
        return {
            'json_file': str(json_file),
            'csv_file': str(csv_file) if analysis['detailed_results'] else None,
            'report_file': str(report_file)
        }
    
    def _generate_text_report(self, analysis: Dict, report_file: Path):
        """Generate text summary report"""
        
        with open(report_file, 'w') as f:
            f.write("NIFTY 50 VCP BACKTEST REPORT\n")
            f.write("=" * 40 + "\n\n")
            
            f.write(f"Analysis Date: {analysis['timestamp']}\n")
            f.write(f"Execution Time: {analysis['summary']['total_execution_time']:.1f} seconds\n\n")
            
            # Summary
            s = analysis['summary']
            f.write("SUMMARY\n")
            f.write("-" * 15 + "\n")
            f.write(f"Total Stocks: {s['total_stocks_analyzed']}\n")
            f.write(f"Successfully Analyzed: {s['successful_backtests']}\n")
            f.write(f"Failed: {s['failed_backtests']}\n\n")
            
            # Portfolio metrics
            pm = analysis['portfolio_metrics']
            f.write("PORTFOLIO PERFORMANCE\n")
            f.write("-" * 25 + "\n")
            f.write(f"Total Patterns: {pm['total_patterns_found']}\n")
            f.write(f"Total Trades: {pm['total_trades_executed']}\n")
            f.write(f"Win Rate: {pm['overall_win_rate']:.1f}%\n")
            f.write(f"Average Return: {pm['average_portfolio_return']:.1f}%\n")
            f.write(f"Average Sharpe: {pm['average_sharpe_ratio']:.2f}\n")
            f.write(f"Max Drawdown: {pm['maximum_drawdown']:.1f}%\n\n")
            
            # Top performers
            f.write("TOP 5 PERFORMERS\n")
            f.write("-" * 20 + "\n")
            for i, stock in enumerate(analysis['performance_ranking'][:5], 1):
                f.write(f"{i}. {stock['symbol']} ({stock['sector']}): "
                       f"{stock.get('total_return', 0):.1f}% "
                       f"({stock.get('total_trades', 0)} trades)\n")
            
            # Sector analysis
            f.write(f"\nSECTOR ANALYSIS\n")
            f.write("-" * 20 + "\n")
            for sector, data in analysis['sector_analysis'].items():
                f.write(f"{sector}: {data['average_return']:.1f}% avg return "
                       f"({data['stock_count']} stocks, {data['total_patterns']} patterns)\n")


def main():
    """Run the simplified Nifty 50 backtest"""
    
    print("NIFTY 50 VCP BACKTEST (SIMPLIFIED)")
    print("=" * 45)
    
    # Initialize
    backtester = SimplifiedNifty50Backtester()
    
    # Configuration
    config = BacktestConfig(
        stop_loss_pct=8.0,
        profit_target_pct=25.0,
        position_size_pct=10.0,
        min_quality_score=50.0
    )
    
    print(f"Configuration:")
    print(f"- Stop Loss: {config.stop_loss_pct}%")
    print(f"- Profit Target: {config.profit_target_pct}%")
    print(f"- Min Quality: {config.min_quality_score}")
    print(f"- Stocks to test: {len(NIFTY50_STOCKS)}")
    
    # Run backtest
    print(f"\nStarting sequential backtest...\n")
    
    start_time = time.time()
    analysis = backtester.run_sequential_backtest(config=config, save_results=True)
    execution_time = time.time() - start_time
    
    # Display results
    print(f"\n" + "=" * 45)
    print(f"BACKTEST COMPLETED IN {execution_time:.1f} SECONDS")
    print(f"=" * 45)
    
    s = analysis['summary']
    pm = analysis['portfolio_metrics']
    
    print(f"\nSUMMARY:")
    print(f"- Stocks analyzed: {s['successful_backtests']}/{s['total_stocks_analyzed']}")
    print(f"- Total patterns: {pm['total_patterns_found']}")
    print(f"- Total trades: {pm['total_trades_executed']}")
    print(f"- Win rate: {pm['overall_win_rate']:.1f}%")
    print(f"- Avg return: {pm['average_portfolio_return']:.1f}%")
    print(f"- Avg Sharpe: {pm['average_sharpe_ratio']:.2f}")
    
    if analysis['performance_ranking']:
        print(f"\nTOP 5 PERFORMERS:")
        for i, stock in enumerate(analysis['performance_ranking'][:5], 1):
            print(f"{i}. {stock['symbol']} ({stock['sector']}): "
                  f"{stock.get('total_return', 0):.1f}% return, "
                  f"{stock.get('total_trades', 0)} trades")
    
    if analysis['sector_analysis']:
        print(f"\nSECTOR PERFORMANCE:")
        sector_sorted = sorted(
            analysis['sector_analysis'].items(),
            key=lambda x: x[1]['average_return'],
            reverse=True
        )
        
        for sector, data in sector_sorted[:5]:
            print(f"- {sector}: {data['average_return']:.1f}% "
                  f"({data['stock_count']} stocks)")
    
    print(f"\nResults saved to nifty50_backtest_results/")
    
    return analysis


if __name__ == "__main__":
    analysis = main()