"""
Working Nifty 50 VCP Comprehensive Backtest
==========================================

Complete VCP backtesting system for all Nifty 50 stocks using the actual
backtester interface and all available historical data.
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

from volatility_patterns.analysis.vcp_backtester import VCPBacktester, BacktestConfig, BacktestResults
from volatility_patterns.analysis.vcp_scanner import VCPScanner
from volatility_patterns.data.data_service import DataService
from sqlalchemy import text


# Nifty 50 Stocks (confirmed symbols)
NIFTY50_STOCKS = {
    # Banking Sector
    "HDFCBANK": "Banking",
    "ICICIBANK": "Banking",
    "SBIN": "Banking", 
    "KOTAKBANK": "Banking",
    "AXISBANK": "Banking",
    "INDUSINDBK": "Banking",
    
    # IT Sector
    "TCS": "IT",
    "INFY": "IT",
    "HCLTECH": "IT",
    "WIPRO": "IT",
    "TECHM": "IT",
    
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
    "ASIANPAINT": "Consumer Goods",
    "TITAN": "Consumer Goods",
    
    # Infrastructure/Industrials
    "LT": "Infrastructure",
    "ULTRACEMCO": "Infrastructure",
    "GRASIM": "Infrastructure",
    "ADANIPORTS": "Infrastructure",
    "POWERGRID": "Infrastructure",
    
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
    
    # Financial Services
    "BAJFINANCE": "Financial Services",
    "BAJAJFINSV": "Financial Services",
    "HDFCLIFE": "Financial Services",
    "SBILIFE": "Financial Services",
    
    # Telecom
    "BHARTIARTL": "Telecom",
    
    # Metals
    "JSWSTEEL": "Metals",
    "TATASTEEL": "Metals", 
    "HINDALCO": "Metals",
    
    # Healthcare
    "APOLLOHOSP": "Healthcare"
}


class ComprehensiveNifty50Backtester:
    """
    Complete VCP backtesting system for Nifty 50 stocks
    """
    
    def __init__(self):
        self.data_service = DataService()
        self.logger = logging.getLogger(__name__)
        
        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        
    def check_available_symbols(self) -> Dict[str, bool]:
        """Check which symbols are available in the database"""
        
        available_symbols = {}
        
        query = text("""
        SELECT DISTINCT symbol 
        FROM nse_equity_bhavcopy_full 
        WHERE symbol IN :symbols
        """)
        
        symbol_list = list(NIFTY50_STOCKS.keys())
        
        try:
            with self.data_service.engine.connect() as conn:
                # Check symbols in batches
                for i in range(0, len(symbol_list), 10):
                    batch = symbol_list[i:i+10]
                    batch_query = text(f"""
                    SELECT DISTINCT symbol 
                    FROM nse_equity_bhavcopy_full 
                    WHERE symbol IN ({','.join([f"'{s}'" for s in batch])})
                    """)
                    
                    result = conn.execute(batch_query).fetchall()
                    found_symbols = {row[0] for row in result}
                    
                    for symbol in batch:
                        available_symbols[symbol] = symbol in found_symbols
                        
        except Exception as e:
            self.logger.error(f"Error checking symbols: {e}")
            # Assume all symbols are available if check fails
            available_symbols = {symbol: True for symbol in NIFTY50_STOCKS.keys()}
        
        return available_symbols
    
    def get_data_statistics(self) -> Dict:
        """Get basic statistics about the available data"""
        
        try:
            query = text("""
            SELECT 
                MIN(trade_date) as earliest_date,
                MAX(trade_date) as latest_date,
                COUNT(DISTINCT symbol) as total_symbols,
                COUNT(*) as total_records
            FROM nse_equity_bhavcopy_full
            """)
            
            with self.data_service.engine.connect() as conn:
                result = conn.execute(query).fetchone()
                
                return {
                    'earliest_date': result[0],
                    'latest_date': result[1], 
                    'total_symbols': result[2],
                    'total_records': result[3]
                }
                
        except Exception as e:
            self.logger.error(f"Error getting data statistics: {e}")
            return {}
    
    def run_sector_backtest(self, sector: str, symbols: List[str], config: BacktestConfig) -> Dict:
        """Run backtest for a specific sector"""
        
        self.logger.info(f"Running backtest for {sector} sector ({len(symbols)} stocks)")
        
        start_time = time.time()
        
        # Initialize backtester with config
        backtester = VCPBacktester(config)
        
        try:
            # Run backtest for the sector symbols
            results = backtester.run_backtest(
                symbols=symbols,
                lookback_days=500  # ~2 years of data
            )
            
            execution_time = time.time() - start_time
            
            return {
                'sector': sector,
                'symbols': symbols,
                'status': 'completed',
                'execution_time': execution_time,
                'results': results,
                'symbol_count': len(symbols)
            }
            
        except Exception as e:
            self.logger.error(f"Error in {sector} backtest: {e}")
            return {
                'sector': sector,
                'symbols': symbols,
                'status': 'failed',
                'error': str(e),
                'execution_time': time.time() - start_time,
                'symbol_count': len(symbols)
            }
    
    def run_comprehensive_backtest(self, config: Optional[BacktestConfig] = None) -> Dict:
        """Run comprehensive backtest across all available Nifty 50 stocks"""
        
        if config is None:
            config = BacktestConfig(
                stop_loss_pct=8.0,
                profit_target_pct=25.0,
                position_size_pct=10.0,
                min_quality_score=50.0
            )
        
        self.logger.info("Starting Comprehensive Nifty 50 VCP Backtest")
        
        # Get data statistics
        data_stats = self.get_data_statistics()
        self.logger.info(f"Database: {data_stats.get('total_records', 0)} records, "
                        f"Date range: {data_stats.get('earliest_date')} to {data_stats.get('latest_date')}")
        
        # Check available symbols
        available_symbols = self.check_available_symbols()
        valid_symbols = [symbol for symbol, available in available_symbols.items() if available]
        
        self.logger.info(f"Available symbols: {len(valid_symbols)}/{len(NIFTY50_STOCKS)}")
        
        if not valid_symbols:
            return {
                'error': 'No valid symbols found in database',
                'available_symbols': available_symbols
            }
        
        # Group symbols by sector
        sectors = {}
        for symbol in valid_symbols:
            sector = NIFTY50_STOCKS[symbol]
            if sector not in sectors:
                sectors[sector] = []
            sectors[sector].append(symbol)
        
        start_time = time.time()
        sector_results = {}
        all_trades = []
        total_patterns = 0
        
        # Run backtest for each sector
        for sector, symbols in sectors.items():
            print(f"\n[{sector}] Testing {len(symbols)} stocks...")
            
            sector_result = self.run_sector_backtest(sector, symbols, config)
            sector_results[sector] = sector_result
            
            if sector_result['status'] == 'completed':
                results = sector_result['results']
                
                print(f"  ✓ {sector}: {results.total_patterns} patterns, "
                      f"{results.total_trades} trades, {results.win_rate:.1f}% win rate")
                
                total_patterns += results.total_patterns
                if hasattr(results, 'trades') and results.trades:
                    all_trades.extend(results.trades)
                    
            else:
                print(f"  ✗ {sector}: {sector_result.get('error', 'Unknown error')}")
        
        total_execution_time = time.time() - start_time
        
        # Aggregate results
        analysis = self._analyze_comprehensive_results(
            sector_results, config, total_execution_time, data_stats
        )
        
        return analysis
    
    def _analyze_comprehensive_results(
        self,
        sector_results: Dict,
        config: BacktestConfig,
        execution_time: float,
        data_stats: Dict
    ) -> Dict:
        """Analyze and summarize comprehensive backtest results"""
        
        # Aggregate metrics
        successful_sectors = {k: v for k, v in sector_results.items() if v['status'] == 'completed'}
        failed_sectors = {k: v for k, v in sector_results.items() if v['status'] == 'failed'}
        
        # Combine all results
        total_patterns = sum(r['results'].total_patterns for r in successful_sectors.values())
        total_trades = sum(r['results'].total_trades for r in successful_sectors.values())
        total_winners = sum(r['results'].winning_trades for r in successful_sectors.values())
        
        # Calculate portfolio metrics
        all_returns = []
        all_sharpes = []
        all_drawdowns = []
        
        for sector_result in successful_sectors.values():
            results = sector_result['results']
            if results.total_return is not None:
                all_returns.append(results.total_return)
            if results.sharpe_ratio is not None:
                all_sharpes.append(results.sharpe_ratio)
            if results.max_drawdown is not None:
                all_drawdowns.append(abs(results.max_drawdown))
        
        portfolio_return = np.mean(all_returns) if all_returns else 0
        portfolio_sharpe = np.mean(all_sharpes) if all_sharpes else 0
        portfolio_max_dd = np.max(all_drawdowns) if all_drawdowns else 0
        
        # Sector performance ranking
        sector_performance = []
        for sector, result in successful_sectors.items():
            if result['results'].total_return is not None:
                sector_performance.append({
                    'sector': sector,
                    'stocks': len(result['symbols']),
                    'symbols': result['symbols'],
                    'patterns': result['results'].total_patterns,
                    'trades': result['results'].total_trades,
                    'win_rate': result['results'].win_rate,
                    'total_return': result['results'].total_return,
                    'sharpe_ratio': result['results'].sharpe_ratio,
                    'max_drawdown': result['results'].max_drawdown
                })
        
        sector_performance.sort(key=lambda x: x['total_return'], reverse=True)
        
        return {
            'summary': {
                'execution_time': execution_time,
                'data_range': f"{data_stats.get('earliest_date')} to {data_stats.get('latest_date')}",
                'total_records': data_stats.get('total_records', 0),
                'successful_sectors': len(successful_sectors),
                'failed_sectors': len(failed_sectors),
                'total_stocks_tested': sum(len(r['symbols']) for r in sector_results.values()),
                'config': {
                    'stop_loss_pct': config.stop_loss_pct,
                    'profit_target_pct': config.profit_target_pct,
                    'min_quality_score': config.min_quality_score
                }
            },
            
            'portfolio_metrics': {
                'total_patterns': total_patterns,
                'total_trades': total_trades,
                'total_winners': total_winners,
                'overall_win_rate': (total_winners / total_trades * 100) if total_trades > 0 else 0,
                'portfolio_return': portfolio_return,
                'portfolio_sharpe': portfolio_sharpe,
                'portfolio_max_drawdown': portfolio_max_dd,
                'patterns_per_sector': total_patterns / len(successful_sectors) if successful_sectors else 0,
                'trades_per_sector': total_trades / len(successful_sectors) if successful_sectors else 0
            },
            
            'sector_performance': sector_performance,
            'sector_results': sector_results,
            'failed_sectors': failed_sectors,
            'timestamp': datetime.now().isoformat()
        }
    
    def save_results(self, analysis: Dict):
        """Save comprehensive results to files"""
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Create output directory
        output_dir = Path("nifty50_comprehensive_results")
        output_dir.mkdir(exist_ok=True)
        
        # Save complete analysis
        json_file = output_dir / f"nifty50_comprehensive_{timestamp}.json"
        with open(json_file, 'w') as f:
            json.dump(analysis, f, indent=2, default=str)
        
        # Save sector performance
        if analysis['sector_performance']:
            sector_df = pd.DataFrame(analysis['sector_performance'])
            sector_csv = output_dir / f"sector_performance_{timestamp}.csv"
            sector_df.to_csv(sector_csv, index=False)
        
        # Generate summary report
        report_file = output_dir / f"comprehensive_report_{timestamp}.txt"
        self._generate_comprehensive_report(analysis, report_file)
        
        self.logger.info(f"Comprehensive results saved to {output_dir}/")
        
        return {
            'json_file': str(json_file),
            'sector_csv': str(sector_csv) if analysis['sector_performance'] else None,
            'report_file': str(report_file)
        }
    
    def _generate_comprehensive_report(self, analysis: Dict, report_file: Path):
        """Generate comprehensive text report"""
        
        with open(report_file, 'w') as f:
            f.write("NIFTY 50 COMPREHENSIVE VCP BACKTEST REPORT\n")
            f.write("=" * 50 + "\n\n")
            
            # Summary
            s = analysis['summary']
            f.write(f"Analysis Date: {analysis['timestamp']}\n")
            f.write(f"Execution Time: {s['execution_time']:.1f} seconds\n")
            f.write(f"Data Range: {s['data_range']}\n")
            f.write(f"Total Database Records: {s['total_records']:,}\n\n")
            
            # Configuration
            config = s['config']
            f.write("BACKTEST CONFIGURATION\n")
            f.write("-" * 25 + "\n")
            f.write(f"Stop Loss: {config['stop_loss_pct']}%\n")
            f.write(f"Profit Target: {config['profit_target_pct']}%\n")
            f.write(f"Min Quality Score: {config['min_quality_score']}\n\n")
            
            # Portfolio Performance
            pm = analysis['portfolio_metrics']
            f.write("PORTFOLIO PERFORMANCE\n")
            f.write("-" * 25 + "\n")
            f.write(f"Sectors Tested: {s['successful_sectors']}/{s['successful_sectors'] + s['failed_sectors']}\n")
            f.write(f"Stocks Tested: {s['total_stocks_tested']}\n")
            f.write(f"Total Patterns: {pm['total_patterns']}\n")
            f.write(f"Total Trades: {pm['total_trades']}\n")
            f.write(f"Win Rate: {pm['overall_win_rate']:.1f}%\n")
            f.write(f"Portfolio Return: {pm['portfolio_return']:.1f}%\n")
            f.write(f"Portfolio Sharpe: {pm['portfolio_sharpe']:.2f}\n")
            f.write(f"Max Drawdown: {pm['portfolio_max_drawdown']:.1f}%\n\n")
            
            # Sector Performance
            f.write("SECTOR PERFORMANCE RANKING\n")
            f.write("-" * 30 + "\n")
            for i, sector in enumerate(analysis['sector_performance'][:10], 1):
                f.write(f"{i:2d}. {sector['sector']:15} "
                       f"Return: {sector['total_return']:6.1f}% "
                       f"Sharpe: {sector['sharpe_ratio']:5.2f} "
                       f"({sector['stocks']} stocks, {sector['patterns']} patterns)\n")
            
            f.write(f"\nDetailed sector results included in JSON file.\n")


def main():
    """Run comprehensive Nifty 50 VCP backtest"""
    
    print("NIFTY 50 COMPREHENSIVE VCP BACKTEST")
    print("=" * 50)
    
    # Initialize backtester
    nifty_backtester = ComprehensiveNifty50Backtester()
    
    # Configuration
    config = BacktestConfig(
        stop_loss_pct=8.0,
        profit_target_pct=25.0,
        position_size_pct=10.0,
        min_quality_score=50.0
    )
    
    print(f"\nConfiguration:")
    print(f"- Stop Loss: {config.stop_loss_pct}%")
    print(f"- Profit Target: {config.profit_target_pct}%") 
    print(f"- Min Quality Score: {config.min_quality_score}")
    print(f"- Max symbols to test: {len(NIFTY50_STOCKS)}")
    
    # Run comprehensive backtest
    print(f"\nStarting comprehensive sector-wise backtest...")
    
    start_time = time.time()
    analysis = nifty_backtester.run_comprehensive_backtest(config)
    total_time = time.time() - start_time
    
    # Check for errors
    if 'error' in analysis:
        print(f"ERROR: {analysis['error']}")
        return analysis
    
    # Display results
    print(f"\n" + "=" * 50)
    print(f"COMPREHENSIVE BACKTEST COMPLETED")
    print(f"=" * 50)
    
    s = analysis['summary']
    pm = analysis['portfolio_metrics']
    
    print(f"\nSUMMARY:")
    print(f"- Execution Time: {s['execution_time']:.1f} seconds")
    print(f"- Data Range: {s['data_range']}")
    print(f"- Sectors Tested: {s['successful_sectors']}")
    print(f"- Stocks Tested: {s['total_stocks_tested']}")
    
    print(f"\nPORTFOLIO PERFORMANCE:")
    print(f"- Total Patterns: {pm['total_patterns']}")
    print(f"- Total Trades: {pm['total_trades']}")
    print(f"- Win Rate: {pm['overall_win_rate']:.1f}%")
    print(f"- Portfolio Return: {pm['portfolio_return']:.1f}%")
    print(f"- Portfolio Sharpe: {pm['portfolio_sharpe']:.2f}")
    print(f"- Max Drawdown: {pm['portfolio_max_drawdown']:.1f}%")
    
    if analysis['sector_performance']:
        print(f"\nTOP 5 SECTOR PERFORMANCE:")
        for i, sector in enumerate(analysis['sector_performance'][:5], 1):
            print(f"{i}. {sector['sector']}: {sector['total_return']:.1f}% "
                  f"({sector['stocks']} stocks, {sector['patterns']} patterns)")
    
    # Save results
    nifty_backtester.save_results(analysis)
    
    return analysis


if __name__ == "__main__":
    results = main()