"""
Nifty 50 Comprehensive VCP Backtesting System
===========================================

Runs complete VCP backtesting on all Nifty 50 stocks using the entire
historical database. Provides sector-wise analysis, performance rankings,
and comprehensive profitability validation.

Features:
- All Nifty 50 stocks analysis
- Complete historical data usage
- Sector-wise performance breakdowns
- Risk-adjusted returns analysis
- Pattern frequency analysis
- Export comprehensive reports

Author: GitHub Copilot
Date: November 2025
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


# Nifty 50 Stocks with Sector Classification
NIFTY50_STOCKS = {
    # IT Services
    "TCS": "IT",
    "INFY": "IT", 
    "HCLTECH": "IT",
    "WIPRO": "IT",
    "TECHM": "IT",
    "LTI": "IT",
    
    # Banking
    "HDFCBANK": "Banking",
    "ICICIBANK": "Banking", 
    "KOTAKBANK": "Banking",
    "AXISBANK": "Banking",
    "INDUSINDBK": "Banking",
    "SBIN": "Banking",
    
    # Financial Services
    "HDFCLIFE": "Financial Services",
    "BAJFINANCE": "Financial Services",
    "BAJAJFINSV": "Financial Services",
    "SBILIFE": "Financial Services",
    
    # Oil & Gas
    "RELIANCE": "Oil & Gas",
    "ONGC": "Oil & Gas",
    "BPCL": "Oil & Gas",
    "IOC": "Oil & Gas",
    
    # Consumer Goods
    "HINDUNILVR": "Consumer Goods",
    "ITC": "Consumer Goods", 
    "NESTLEIND": "Consumer Goods",
    "BRITANNIA": "Consumer Goods",
    "DABUR": "Consumer Goods",
    
    # Automobiles
    "MARUTI": "Automobiles",
    "M&M": "Automobiles",
    "TATAMOTORS": "Automobiles",
    "BAJAJ-AUTO": "Automobiles",
    "EICHERMOT": "Automobiles",
    
    # Pharma
    "SUNPHARMA": "Pharma",
    "DRREDDY": "Pharma",
    "CIPLA": "Pharma",
    "DIVISLAB": "Pharma",
    
    # Infrastructure/Utilities
    "LT": "Infrastructure",
    "ULTRACEMCO": "Infrastructure", 
    "GRASIM": "Infrastructure",
    "ADANIPORTS": "Infrastructure",
    "POWERGRID": "Infrastructure",
    
    # Telecom
    "BHARTIARTL": "Telecom",
    "JSWSTEEL": "Metals",
    "TATASTEEL": "Metals",
    "HINDALCO": "Metals",
    
    # Others
    "ASIANPAINT": "Consumer Goods",
    "TITAN": "Consumer Goods",
    "APOLLOHOSP": "Healthcare"
}


class Nifty50VCPBacktester:
    """
    Comprehensive VCP Backtesting for all Nifty 50 stocks
    
    Features:
    - Complete historical data analysis
    - Sector-wise performance breakdown
    - Risk-adjusted metrics calculation
    - Pattern frequency analysis
    - Comprehensive reporting
    """
    
    def __init__(self):
        self.data_service = DataService()
        self.backtester = VCPBacktester()
        self.scanner = VCPScanner()
        self.results = {}
        self.sector_results = {}
        
        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
        
    def get_data_range_for_stock(self, symbol: str) -> Tuple[Optional[date], Optional[date]]:
        """Get the full data range available for a stock"""
        try:
            # Query database for date range
            query = """
            SELECT MIN(trade_date) as start_date, MAX(trade_date) as end_date
            FROM nse_equity_bhavcopy_full 
            WHERE symbol = %s
            AND close_price > 0
            """
            
            with self.data_service.engine.connect() as conn:
                result = conn.execute(query, (symbol,)).fetchone()
                
                if result and result[0] and result[1]:
                    return result[0], result[1]
                
        except Exception as e:
            self.logger.warning(f"Could not get date range for {symbol}: {e}")
            
        return None, None
    
    def run_single_stock_backtest(
        self,
        symbol: str,
        config: BacktestConfig,
        min_data_points: int = 252  # 1 year minimum
    ) -> Dict:
        """Run comprehensive backtest for a single stock"""
        
        start_time = time.time()
        sector = NIFTY50_STOCKS.get(symbol, "Unknown")
        
        self.logger.info(f"Starting backtest for {symbol} ({sector})")
        
        try:
            # Get full data range for this stock
            start_date, end_date = self.get_data_range_for_stock(symbol)
            
            if not start_date or not end_date:
                return {
                    'symbol': symbol,
                    'sector': sector,
                    'status': 'failed',
                    'error': 'No data available',
                    'execution_time': time.time() - start_time
                }
            
            # Calculate data span
            data_span_days = (end_date - start_date).days
            
            if data_span_days < min_data_points:
                return {
                    'symbol': symbol,
                    'sector': sector,
                    'status': 'failed',
                    'error': f'Insufficient data: {data_span_days} days',
                    'execution_time': time.time() - start_time
                }
            
            self.logger.info(f"{symbol}: Using data from {start_date} to {end_date} ({data_span_days} days)")
            
            # Run the backtest
            results = self.backtester.backtest_symbol(
                symbol=symbol,
                start_date=start_date,
                end_date=end_date,
                config=config
            )
            
            # Enhanced result structure
            result = {
                'symbol': symbol,
                'sector': sector,
                'status': 'completed',
                'data_start': start_date.isoformat(),
                'data_end': end_date.isoformat(),
                'data_span_days': data_span_days,
                'execution_time': time.time() - start_time,
                
                # Core backtest results
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
                
                # Additional analysis
                'patterns_per_year': (results.total_patterns / (data_span_days / 365.25)) if data_span_days > 0 else 0,
                'trades_per_year': (results.total_trades / (data_span_days / 365.25)) if data_span_days > 0 else 0,
                'return_per_year': (results.total_return / (data_span_days / 365.25)) if data_span_days > 0 else 0,
                
                # Risk metrics
                'risk_adjusted_return': results.sharpe_ratio * np.sqrt(252) if results.sharpe_ratio else 0,
                'calmar_ratio': (results.total_return / abs(results.max_drawdown)) if results.max_drawdown != 0 else 0,
            }
            
            self.logger.info(f"{symbol} completed: {results.total_patterns} patterns, "
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
    
    def run_nifty50_backtest(
        self,
        config: Optional[BacktestConfig] = None,
        max_workers: int = 4,
        save_results: bool = True
    ) -> Dict:
        """
        Run comprehensive backtest on all Nifty 50 stocks
        
        Args:
            config: Backtest configuration (uses default if None)
            max_workers: Number of parallel workers
            save_results: Whether to save results to files
            
        Returns:
            Dictionary with complete analysis results
        """
        
        if config is None:
            config = BacktestConfig(
                stop_loss_pct=8.0,
                profit_target_pct=25.0,
                position_size_pct=10.0,
                min_quality_score=60.0
            )
        
        self.logger.info("Starting Nifty 50 VCP Comprehensive Backtest")
        self.logger.info(f"Configuration: {config}")
        self.logger.info(f"Stocks to analyze: {len(NIFTY50_STOCKS)}")
        
        start_time = time.time()
        
        # Run backtests in parallel
        all_results = []
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all jobs
            future_to_symbol = {
                executor.submit(self.run_single_stock_backtest, symbol, config): symbol
                for symbol in NIFTY50_STOCKS.keys()
            }
            
            # Collect results as they complete
            for future in as_completed(future_to_symbol):
                symbol = future_to_symbol[future]
                try:
                    result = future.result()
                    all_results.append(result)
                    
                    # Progress update
                    completed = len(all_results)
                    total = len(NIFTY50_STOCKS)
                    progress = (completed / total) * 100
                    
                    if result['status'] == 'completed':
                        self.logger.info(f"[{completed}/{total}] {symbol} - "
                                       f"Patterns: {result.get('total_patterns', 0)}, "
                                       f"Trades: {result.get('total_trades', 0)}")
                    else:
                        self.logger.warning(f"[{completed}/{total}] {symbol} - "
                                          f"Failed: {result.get('error', 'Unknown error')}")
                    
                except Exception as e:
                    self.logger.error(f"Failed to process {symbol}: {e}")
                    all_results.append({
                        'symbol': symbol,
                        'sector': NIFTY50_STOCKS.get(symbol, 'Unknown'),
                        'status': 'failed',
                        'error': str(e)
                    })
        
        total_execution_time = time.time() - start_time
        
        # Analyze results
        analysis = self._analyze_results(all_results, config, total_execution_time)
        
        # Save results if requested
        if save_results:
            self._save_results(analysis)
        
        self.logger.info(f"Nifty 50 backtest completed in {total_execution_time:.1f} seconds")
        
        return analysis
    
    def _analyze_results(
        self,
        all_results: List[Dict],
        config: BacktestConfig,
        execution_time: float
    ) -> Dict:
        """Analyze and summarize all backtest results"""
        
        # Separate successful and failed results
        successful_results = [r for r in all_results if r['status'] == 'completed']
        failed_results = [r for r in all_results if r['status'] == 'failed']
        
        # Overall statistics
        total_patterns = sum(r.get('total_patterns', 0) for r in successful_results)
        total_trades = sum(r.get('total_trades', 0) for r in successful_results)
        total_wins = sum(r.get('winning_trades', 0) for r in successful_results)
        
        # Calculate portfolio-level metrics
        portfolio_return = np.mean([r.get('total_return', 0) for r in successful_results if r.get('total_return')])
        portfolio_sharpe = np.mean([r.get('sharpe_ratio', 0) for r in successful_results if r.get('sharpe_ratio')])
        portfolio_max_dd = np.max([abs(r.get('max_drawdown', 0)) for r in successful_results if r.get('max_drawdown')])
        
        # Sector-wise analysis
        sector_analysis = self._analyze_by_sector(successful_results)
        
        # Performance ranking
        performance_ranking = sorted(
            successful_results,
            key=lambda x: x.get('total_return', 0),
            reverse=True
        )
        
        # Pattern analysis
        pattern_analysis = self._analyze_patterns(successful_results)
        
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
            'performance_ranking': performance_ranking[:10],  # Top 10
            'worst_performers': performance_ranking[-10:],     # Bottom 10
            'pattern_analysis': pattern_analysis,
            
            'detailed_results': successful_results,
            'failed_results': failed_results,
            
            'timestamp': datetime.now().isoformat()
        }
    
    def _analyze_by_sector(self, results: List[Dict]) -> Dict:
        """Analyze results by sector"""
        
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
                    'sharpe_ratios': [],
                    'max_drawdowns': []
                }
            
            sector_data[sector]['stocks'].append(result['symbol'])
            sector_data[sector]['total_patterns'] += result.get('total_patterns', 0)
            sector_data[sector]['total_trades'] += result.get('total_trades', 0)
            sector_data[sector]['total_wins'] += result.get('winning_trades', 0)
            
            if result.get('total_return'):
                sector_data[sector]['returns'].append(result['total_return'])
            if result.get('sharpe_ratio'):
                sector_data[sector]['sharpe_ratios'].append(result['sharpe_ratio'])
            if result.get('max_drawdown'):
                sector_data[sector]['max_drawdowns'].append(abs(result['max_drawdown']))
        
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
                'average_max_drawdown': np.mean(data['max_drawdowns']) if data['max_drawdowns'] else 0,
                'patterns_per_stock': data['total_patterns'] / len(data['stocks']) if data['stocks'] else 0
            }
        
        return sector_summary
    
    def _analyze_patterns(self, results: List[Dict]) -> Dict:
        """Analyze pattern characteristics"""
        
        stocks_with_patterns = [r for r in results if r.get('total_patterns', 0) > 0]
        stocks_with_trades = [r for r in results if r.get('total_trades', 0) > 0]
        
        return {
            'pattern_frequency': {
                'stocks_with_patterns': len(stocks_with_patterns),
                'stocks_without_patterns': len(results) - len(stocks_with_patterns),
                'pattern_detection_rate': len(stocks_with_patterns) / len(results) * 100 if results else 0
            },
            
            'trade_frequency': {
                'stocks_with_trades': len(stocks_with_trades),
                'stocks_without_trades': len(results) - len(stocks_with_trades),
                'trade_conversion_rate': len(stocks_with_trades) / len(stocks_with_patterns) * 100 if stocks_with_patterns else 0
            },
            
            'performance_distribution': {
                'profitable_stocks': len([r for r in results if r.get('total_return', 0) > 0]),
                'unprofitable_stocks': len([r for r in results if r.get('total_return', 0) < 0]),
                'breakeven_stocks': len([r for r in results if r.get('total_return', 0) == 0])
            }
        }
    
    def _save_results(self, analysis: Dict):
        """Save analysis results to files"""
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Create output directory
        output_dir = Path("nifty50_backtest_results")
        output_dir.mkdir(exist_ok=True)
        
        # Save complete analysis as JSON
        json_file = output_dir / f"nifty50_vcp_backtest_{timestamp}.json"
        with open(json_file, 'w') as f:
            json.dump(analysis, f, indent=2, default=str)
        
        # Save detailed results as CSV
        csv_file = output_dir / f"nifty50_detailed_results_{timestamp}.csv"
        df = pd.DataFrame(analysis['detailed_results'])
        df.to_csv(csv_file, index=False)
        
        # Save sector summary as CSV
        sector_csv = output_dir / f"nifty50_sector_analysis_{timestamp}.csv"
        sector_df = pd.DataFrame.from_dict(analysis['sector_analysis'], orient='index')
        sector_df.to_csv(sector_csv)
        
        # Save summary report
        report_file = output_dir / f"nifty50_summary_report_{timestamp}.txt"
        self._generate_text_report(analysis, report_file)
        
        self.logger.info(f"Results saved to {output_dir}/")
        
        return {
            'json_file': str(json_file),
            'csv_file': str(csv_file),
            'sector_csv': str(sector_csv),
            'report_file': str(report_file)
        }
    
    def _generate_text_report(self, analysis: Dict, report_file: Path):
        """Generate a comprehensive text report"""
        
        with open(report_file, 'w') as f:
            f.write("NIFTY 50 VCP BACKTEST COMPREHENSIVE REPORT\n")
            f.write("=" * 50 + "\n\n")
            
            f.write(f"Analysis Date: {analysis['timestamp']}\n")
            f.write(f"Total Execution Time: {analysis['summary']['total_execution_time']:.1f} seconds\n\n")
            
            # Configuration
            f.write("BACKTEST CONFIGURATION\n")
            f.write("-" * 25 + "\n")
            config = analysis['summary']['config']
            f.write(f"Stop Loss: {config['stop_loss_pct']}%\n")
            f.write(f"Profit Target: {config['profit_target_pct']}%\n")
            f.write(f"Position Size: {config['position_size_pct']}%\n")
            f.write(f"Min Quality Score: {config['min_quality_score']}\n\n")
            
            # Portfolio Metrics
            f.write("PORTFOLIO PERFORMANCE\n")
            f.write("-" * 25 + "\n")
            pm = analysis['portfolio_metrics']
            f.write(f"Stocks Analyzed: {analysis['summary']['successful_backtests']}/{analysis['summary']['total_stocks_analyzed']}\n")
            f.write(f"Total Patterns Found: {pm['total_patterns_found']}\n")
            f.write(f"Total Trades Executed: {pm['total_trades_executed']}\n")
            f.write(f"Overall Win Rate: {pm['overall_win_rate']:.1f}%\n")
            f.write(f"Average Portfolio Return: {pm['average_portfolio_return']:.1f}%\n")
            f.write(f"Average Sharpe Ratio: {pm['average_sharpe_ratio']:.2f}\n")
            f.write(f"Maximum Drawdown: {pm['maximum_drawdown']:.1f}%\n")
            f.write(f"Patterns per Stock: {pm['patterns_per_stock']:.1f}\n")
            f.write(f"Trades per Stock: {pm['trades_per_stock']:.1f}\n\n")
            
            # Sector Analysis
            f.write("SECTOR PERFORMANCE\n")
            f.write("-" * 25 + "\n")
            for sector, data in analysis['sector_analysis'].items():
                f.write(f"{sector}:\n")
                f.write(f"  Stocks: {data['stock_count']} ({', '.join(data['stocks'])})\n")
                f.write(f"  Patterns: {data['total_patterns']}\n")
                f.write(f"  Trades: {data['total_trades']}\n")
                f.write(f"  Win Rate: {data['win_rate']:.1f}%\n")
                f.write(f"  Avg Return: {data['average_return']:.1f}%\n")
                f.write(f"  Avg Sharpe: {data['average_sharpe']:.2f}\n\n")
            
            # Top Performers
            f.write("TOP 10 PERFORMERS\n")
            f.write("-" * 25 + "\n")
            for i, stock in enumerate(analysis['performance_ranking'][:10], 1):
                f.write(f"{i:2d}. {stock['symbol']:12} ({stock['sector']:15}) "
                       f"Return: {stock.get('total_return', 0):6.1f}% "
                       f"Trades: {stock.get('total_trades', 0):3d} "
                       f"Win Rate: {stock.get('win_rate', 0):5.1f}%\n")
            
            f.write(f"\nReport saved at: {report_file}\n")


def main():
    """Run the comprehensive Nifty 50 VCP backtest"""
    
    print("NIFTY 50 COMPREHENSIVE VCP BACKTEST")
    print("=" * 50)
    
    # Initialize backtester
    nifty_backtester = Nifty50VCPBacktester()
    
    # Configure backtest
    config = BacktestConfig(
        stop_loss_pct=8.0,          # 8% stop loss
        profit_target_pct=25.0,     # 25% profit target  
        position_size_pct=10.0,     # 10% position sizing
        min_quality_score=50.0      # Minimum pattern quality
    )
    
    print(f"Configuration:")
    print(f"- Stop Loss: {config.stop_loss_pct}%")
    print(f"- Profit Target: {config.profit_target_pct}%")
    print(f"- Position Size: {config.position_size_pct}%")
    print(f"- Min Quality: {config.min_quality_score}")
    print(f"- Stocks to analyze: {len(NIFTY50_STOCKS)}")
    
    # Run comprehensive backtest
    print(f"\nStarting comprehensive backtest...")
    
    start_time = time.time()
    
    analysis = nifty_backtester.run_nifty50_backtest(
        config=config,
        max_workers=4,  # Parallel processing
        save_results=True
    )
    
    execution_time = time.time() - start_time
    
    # Display summary
    print(f"\n" + "=" * 50)
    print(f"BACKTEST COMPLETED IN {execution_time:.1f} SECONDS")
    print(f"=" * 50)
    
    pm = analysis['portfolio_metrics']
    print(f"\nPORTFOLIO SUMMARY:")
    print(f"- Stocks analyzed: {analysis['summary']['successful_backtests']}/{analysis['summary']['total_stocks_analyzed']}")
    print(f"- Total patterns: {pm['total_patterns_found']}")
    print(f"- Total trades: {pm['total_trades_executed']}")
    print(f"- Win rate: {pm['overall_win_rate']:.1f}%")
    print(f"- Avg return: {pm['average_portfolio_return']:.1f}%")
    print(f"- Avg Sharpe: {pm['average_sharpe_ratio']:.2f}")
    print(f"- Max drawdown: {pm['maximum_drawdown']:.1f}%")
    
    print(f"\nTOP 5 PERFORMERS:")
    for i, stock in enumerate(analysis['performance_ranking'][:5], 1):
        print(f"{i}. {stock['symbol']} ({stock['sector']}): "
              f"{stock.get('total_return', 0):.1f}% return, "
              f"{stock.get('total_trades', 0)} trades")
    
    print(f"\nBEST SECTORS BY AVERAGE RETURN:")
    sector_sorted = sorted(
        analysis['sector_analysis'].items(),
        key=lambda x: x[1]['average_return'],
        reverse=True
    )
    
    for sector, data in sector_sorted[:5]:
        print(f"- {sector}: {data['average_return']:.1f}% "
              f"({data['stock_count']} stocks, {data['total_patterns']} patterns)")
    
    print(f"\nDetailed results saved to: nifty50_backtest_results/")
    
    return analysis


if __name__ == "__main__":
    analysis = main()