"""
Broader Universe VCP Backtest
============================

Extended VCP backtesting beyond Nifty 50 to include:
- Nifty 100 stocks
- Nifty Midcap 150 popular stocks
- High-volume traded stocks
- Sector leaders across market caps

This broader universe increases chances of finding VCP patterns since
mid-cap and small-cap stocks often exhibit better pattern formation.
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


# Expanded Stock Universe - Beyond Nifty 50
BROADER_STOCK_UNIVERSE = {
    # Nifty 50 (Core Large Caps)
    "RELIANCE": "Oil & Gas",
    "TCS": "IT",
    "HDFCBANK": "Banking",
    "INFY": "IT",
    "HINDUNILVR": "FMCG",
    "ITC": "FMCG",
    "SBIN": "Banking",
    "BHARTIARTL": "Telecom",
    "KOTAKBANK": "Banking",
    "LT": "Infrastructure",
    "ASIANPAINT": "Paint",
    "MARUTI": "Auto",
    "SUNPHARMA": "Pharma",
    "TITAN": "Consumer Discretionary",
    "ULTRACEMCO": "Cement",
    "NESTLEIND": "FMCG",
    "BAJFINANCE": "NBFC",
    "AXISBANK": "Banking",
    "HCLTECH": "IT",
    "ICICIBANK": "Banking",
    
    # Nifty Next 50 / Mid-caps with good liquidity
    "ADANIPORTS": "Infrastructure",
    "ADANIENT": "Conglomerate",
    "AMBUJACEM": "Cement",
    "APOLLOHOSP": "Healthcare",
    "ASHOKLEY": "Auto",
    "BAJAJFINSV": "Financial Services",
    "BANDHANBNK": "Banking",
    "BERGEPAINT": "Paint",
    "BIOCON": "Pharma",
    "BOSCHLTD": "Auto Components",
    "BPCL": "Oil & Gas",
    "BRITANNIA": "FMCG",
    "CADILAHC": "Pharma",
    "CANBK": "Banking",
    "CHOLAFIN": "NBFC",
    "CIPLA": "Pharma",
    "COALINDIA": "Mining",
    "COLPAL": "FMCG",
    "CONCOR": "Logistics",
    "COROMANDEL": "Fertilizers",
    "CROMPTON": "Consumer Durables",
    "CUB": "Banking",
    "CUMMINSIND": "Industrial",
    "DABUR": "FMCG",
    "DEEPAKNTR": "Chemicals",
    "DIVISLAB": "Pharma",
    "DLF": "Real Estate",
    "DRREDDY": "Pharma",
    "EICHERMOT": "Auto",
    "ESCORTS": "Auto",
    "EXIDEIND": "Auto Components",
    "FEDERALBNK": "Banking",
    "GAIL": "Oil & Gas",
    "GLENMARK": "Pharma",
    "GMRINFRA": "Infrastructure",
    "GODREJCP": "FMCG",
    "GODREJPROP": "Real Estate",
    "GRANULES": "Pharma",
    "GRASIM": "Textiles",
    "HAVELLS": "Consumer Durables",
    "HDFCAMC": "Asset Management",
    "HDFCLIFE": "Insurance",
    "HEROMOTOCO": "Auto",
    "HINDALCO": "Metals",
    "HINDPETRO": "Oil & Gas",
    "HINDUNILVR": "FMCG",
    "IBULHSGFIN": "Housing Finance",
    "ICICIPRULI": "Insurance",
    "IDFCFIRSTB": "Banking",
    "IEX": "Power Trading",
    "INDIGO": "Aviation",
    "INDUSINDBK": "Banking",
    "INDUSTOWER": "Telecom Infrastructure",
    "IOC": "Oil & Gas",
    "IRCTC": "Transportation",
    "ITC": "FMCG",
    "JINDALSTEL": "Metals",
    "JSWSTEEL": "Metals",
    "JUBLFOOD": "Food Services",
    "KOTAKBANK": "Banking",
    "L&TFH": "Housing Finance",
    "LICHSGFIN": "Housing Finance",
    "LUPIN": "Pharma",
    "MARICO": "FMCG",
    "MCDOWELL-N": "Beverages",
    "MFSL": "Financial Services",
    "MGL": "Gas Distribution",
    "MOTHERSUMI": "Auto Components",
    "MPHASIS": "IT",
    "MRF": "Tyres",
    "MUTHOOTFIN": "NBFC",
    "NATIONALUM": "Metals",
    "NAUKRI": "Internet",
    "NAVINFLUOR": "Chemicals",
    "NMDC": "Mining",
    "NTPC": "Power",
    "OBEROIRLTY": "Real Estate",
    "OFSS": "IT",
    "ONGC": "Oil & Gas",
    "PAGEIND": "FMCG",
    "PEL": "Consumer Durables",
    "PERSISTENT": "IT",
    "PETRONET": "Oil & Gas",
    "PFC": "Financial Services",
    "PIDILITIND": "Chemicals",
    "PIIND": "Chemicals",
    "PNB": "Banking",
    "POLYCAB": "Cables",
    "POWERGRID": "Power",
    "PVR": "Media & Entertainment",
    "RAMCOCEM": "Cement",
    "RBLBANK": "Banking",
    "RECLTD": "Financial Services",
    "SAIL": "Metals",
    "SBILIFE": "Insurance",
    "SHREECEM": "Cement",
    "SIEMENS": "Industrial",
    "SRF": "Chemicals",
    "SRTRANSFIN": "NBFC",
    "STARHEALTH": "Insurance",
    "TATACHEM": "Chemicals",
    "TATACOMM": "Telecom",
    "TATACONSUM": "FMCG",
    "TATAMOTORS": "Auto",
    "TATAPOWER": "Power",
    "TATASTEEL": "Metals",
    "TECHM": "IT",
    "TORNTPHARM": "Pharma",
    "TORNTPOWER": "Power",
    "TRENT": "Retail",
    "TVSMOTOR": "Auto",
    "UBL": "Beverages",
    "UNIONBANK": "Banking",
    "UPL": "Agrochemicals",
    "VEDL": "Metals",
    "VOLTAS": "Consumer Durables",
    "WIPRO": "IT",
    "ZEEL": "Media",
    "ZYDUSLIFE": "Pharma",
    
    # High Beta / High Growth Stocks (often show better patterns)
    "ADANIGREEN": "Renewable Energy",
    "ADANITRANS": "Logistics",
    "APOLLOTYRE": "Tyres",
    "AUROPHARMA": "Pharma",
    "BALKRISIND": "Tyres",
    "BATAINDIA": "Footwear",
    "BEL": "Defence",
    "BHARATFORG": "Auto Components",
    "BHARTIHEXA": "Telecom",
    "CANFINHOME": "Housing Finance",
    "DIXON": "Electronics",
    "GUJGASLTD": "Gas Distribution",
    "HAL": "Defence",
    "HONAUT": "Auto Components",
    "JKCEMENT": "Cement",
    "LALPATHLAB": "Healthcare",
    "MANAPPURAM": "NBFC",
    "MINDTREE": "IT",
    "MPHASIS": "IT",
    "PFIZER": "Pharma",
    "RELAXO": "Footwear",
    "SANOFI": "Pharma",
    "SCHAEFFLER": "Auto Components",
    "THYROCARE": "Healthcare",
    "TORNTPHARM": "Pharma",
    "WHIRLPOOL": "Consumer Durables"
}


class BroaderUniverseVCPTester:
    """
    VCP Testing with Broader Stock Universe
    
    Features:
    - 150+ stocks across market caps
    - Sector diversification
    - Lower quality threshold for discovery
    - Progressive filtering approach
    """
    
    def __init__(self):
        self.data_service = DataService()
        self.logger = logging.getLogger(__name__)
        
        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        
    def get_available_symbols_from_db(self) -> List[str]:
        """Get symbols that actually exist in the database"""
        
        all_symbols = list(BROADER_STOCK_UNIVERSE.keys())
        available_symbols = []
        
        print(f"Checking {len(all_symbols)} symbols in database...")
        
        try:
            # Check in batches to avoid query size limits
            batch_size = 20
            for i in range(0, len(all_symbols), batch_size):
                batch = all_symbols[i:i + batch_size]
                
                # Create parameterized query
                placeholders = ','.join([f"'{symbol}'" for symbol in batch])
                query = text(f"""
                SELECT DISTINCT symbol, COUNT(*) as record_count
                FROM nse_equity_bhavcopy_full 
                WHERE symbol IN ({placeholders})
                GROUP BY symbol
                HAVING COUNT(*) >= 100
                ORDER BY COUNT(*) DESC
                """)
                
                with self.data_service.engine.connect() as conn:
                    result = conn.execute(query).fetchall()
                    
                    for row in result:
                        available_symbols.append(row[0])
                        print(f"  ✓ {row[0]}: {row[1]} records")
                
                print(f"  Batch {i//batch_size + 1}/{(len(all_symbols) + batch_size - 1)//batch_size} completed")
            
        except Exception as e:
            self.logger.error(f"Error checking symbols: {e}")
            # Fallback to original list if check fails
            return all_symbols[:50]  # Safe subset
        
        print(f"Found {len(available_symbols)} symbols with sufficient data")
        return available_symbols
    
    def run_progressive_vcp_scan(
        self,
        symbols: List[str],
        quality_thresholds: List[float] = [30.0, 40.0, 50.0],
        max_stocks_per_threshold: int = 50
    ) -> Dict:
        """Run progressive scan with different quality thresholds"""
        
        print("\n=== PROGRESSIVE VCP PATTERN SCAN ===")
        
        all_results = {}
        found_patterns = []
        
        for threshold in quality_thresholds:
            print(f"\n🔍 SCANNING with Quality Threshold: {threshold}")
            print("-" * 50)
            
            config = BacktestConfig(
                stop_loss_pct=8.0,
                profit_target_pct=25.0,
                position_size_pct=10.0,
                min_quality_score=threshold
            )
            
            # Test subset of symbols for each threshold
            test_symbols = symbols[:max_stocks_per_threshold]
            print(f"Testing {len(test_symbols)} stocks...")
            
            threshold_patterns = []
            
            # Use scanner for faster pattern detection (no full backtesting)
            scanner = VCPScanner()
            
            for i, symbol in enumerate(test_symbols, 1):
                try:
                    print(f"[{i:2d}/{len(test_symbols)}] {symbol:12} ", end="")
                    
                    # Quick pattern scan
                    result = scanner.scan_single_stock(
                        symbol=symbol,
                        lookback_days=500,  # ~2 years
                        min_quality=threshold
                    )
                    
                    if result.best_pattern:
                        pattern_info = {
                            'symbol': symbol,
                            'sector': BROADER_STOCK_UNIVERSE.get(symbol, 'Unknown'),
                            'quality_score': result.best_pattern.quality_score,
                            'base_duration': result.best_pattern.base_duration,
                            'contractions': len(result.best_pattern.contractions),
                            'volatility_compression': result.best_pattern.volatility_compression,
                            'current_stage': result.best_pattern.current_stage,
                            'setup_complete': result.best_pattern.is_setup_complete,
                            'threshold_tested': threshold
                        }
                        
                        threshold_patterns.append(pattern_info)
                        found_patterns.append(pattern_info)
                        
                        print(f"✅ Pattern! Quality: {result.best_pattern.quality_score:.1f}")
                    else:
                        print("❌ No pattern")
                        
                except Exception as e:
                    print(f"⚠️  Error: {str(e)[:30]}...")
            
            all_results[f"threshold_{threshold}"] = {
                'threshold': threshold,
                'symbols_tested': len(test_symbols),
                'patterns_found': len(threshold_patterns),
                'patterns': threshold_patterns
            }
            
            print(f"\n📊 Threshold {threshold} Results:")
            print(f"   Symbols tested: {len(test_symbols)}")
            print(f"   Patterns found: {len(threshold_patterns)}")
            
            if threshold_patterns:
                print(f"   Top patterns:")
                sorted_patterns = sorted(threshold_patterns, 
                                       key=lambda x: x['quality_score'], 
                                       reverse=True)
                for pattern in sorted_patterns[:5]:
                    print(f"     {pattern['symbol']:12} Quality: {pattern['quality_score']:5.1f} "
                          f"Stage: {pattern['current_stage']} "
                          f"({pattern['sector']})")
            
            # If we found patterns at this threshold, we can be more selective
            if len(threshold_patterns) > 10:
                print(f"   Good pattern discovery rate, moving to next threshold...")
                continue
        
        return {
            'summary': {
                'total_symbols_available': len(symbols),
                'total_patterns_found': len(found_patterns),
                'thresholds_tested': quality_thresholds,
                'discovery_rate': len(found_patterns) / (max_stocks_per_threshold * len(quality_thresholds)) * 100
            },
            'threshold_results': all_results,
            'all_patterns': found_patterns,
            'best_patterns': sorted(found_patterns, key=lambda x: x['quality_score'], reverse=True)[:10]
        }
    
    def analyze_pattern_characteristics(self, patterns: List[Dict]) -> Dict:
        """Analyze characteristics of found patterns"""
        
        if not patterns:
            return {'error': 'No patterns to analyze'}
        
        # Sector analysis
        sector_counts = {}
        for pattern in patterns:
            sector = pattern['sector']
            if sector not in sector_counts:
                sector_counts[sector] = []
            sector_counts[sector].append(pattern)
        
        # Quality distribution
        qualities = [p['quality_score'] for p in patterns]
        
        # Stage analysis
        stages = {}
        for pattern in patterns:
            stage = pattern['current_stage']
            stages[stage] = stages.get(stage, 0) + 1
        
        return {
            'pattern_count': len(patterns),
            'quality_stats': {
                'average': np.mean(qualities),
                'median': np.median(qualities),
                'min': np.min(qualities),
                'max': np.max(qualities),
                'std': np.std(qualities)
            },
            'sector_distribution': {
                sector: len(patterns) for sector, patterns in sector_counts.items()
            },
            'stage_distribution': stages,
            'setup_completion': {
                'complete': len([p for p in patterns if p.get('setup_complete', False)]),
                'incomplete': len([p for p in patterns if not p.get('setup_complete', False)])
            },
            'top_sectors': sorted(sector_counts.items(), 
                                key=lambda x: len(x[1]), 
                                reverse=True)[:5]
        }
    
    def run_detailed_backtest_on_patterns(self, patterns: List[Dict], max_patterns: int = 20) -> Dict:
        """Run detailed backtest on discovered patterns"""
        
        if not patterns:
            return {'error': 'No patterns provided for backtesting'}
        
        print(f"\n=== DETAILED BACKTEST ON TOP PATTERNS ===")
        print(f"Running backtest on top {min(len(patterns), max_patterns)} patterns...")
        
        # Select top patterns for detailed analysis
        top_patterns = sorted(patterns, key=lambda x: x['quality_score'], reverse=True)[:max_patterns]
        
        config = BacktestConfig(
            stop_loss_pct=8.0,
            profit_target_pct=25.0,
            position_size_pct=10.0,
            min_quality_score=30.0  # Lower threshold since we already filtered
        )
        
        backtester = VCPBacktester(config)
        backtest_results = {}
        
        for i, pattern in enumerate(top_patterns, 1):
            symbol = pattern['symbol']
            print(f"[{i:2d}/{len(top_patterns)}] Backtesting {symbol}...")
            
            try:
                results = backtester.run_backtest(
                    symbols=[symbol],
                    lookback_days=500
                )
                
                backtest_results[symbol] = {
                    'symbol': symbol,
                    'sector': pattern['sector'],
                    'pattern_quality': pattern['quality_score'],
                    'backtest_results': results,
                    'performance_summary': {
                        'total_patterns': results.total_patterns,
                        'total_trades': results.total_trades,
                        'win_rate': results.win_rate,
                        'total_return': results.total_return,
                        'sharpe_ratio': results.sharpe_ratio,
                        'max_drawdown': results.max_drawdown
                    }
                }
                
                print(f"    ✅ {symbol}: {results.total_patterns} patterns, "
                      f"{results.total_trades} trades, {results.win_rate:.1f}% win rate")
                
            except Exception as e:
                print(f"    ❌ {symbol}: Error - {str(e)}")
                backtest_results[symbol] = {'error': str(e)}
        
        return backtest_results
    
    def save_comprehensive_results(self, scan_results: Dict, backtest_results: Dict):
        """Save all results to files"""
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = Path("broader_universe_results")
        output_dir.mkdir(exist_ok=True)
        
        # Save scan results
        scan_file = output_dir / f"vcp_scan_results_{timestamp}.json"
        with open(scan_file, 'w') as f:
            json.dump(scan_results, f, indent=2, default=str)
        
        # Save backtest results
        backtest_file = output_dir / f"vcp_backtest_results_{timestamp}.json"
        with open(backtest_file, 'w') as f:
            json.dump(backtest_results, f, indent=2, default=str)
        
        # Generate summary report
        report_file = output_dir / f"broader_universe_summary_{timestamp}.txt"
        self._generate_summary_report(scan_results, backtest_results, report_file)
        
        print(f"\n📁 Results saved to {output_dir}/")
        
        return {
            'scan_file': str(scan_file),
            'backtest_file': str(backtest_file),
            'report_file': str(report_file)
        }
    
    def _generate_summary_report(self, scan_results: Dict, backtest_results: Dict, report_file: Path):
        """Generate comprehensive summary report"""
        
        with open(report_file, 'w') as f:
            f.write("BROADER UNIVERSE VCP ANALYSIS REPORT\n")
            f.write("=" * 50 + "\n\n")
            
            # Scan summary
            summary = scan_results['summary']
            f.write("PATTERN DISCOVERY SUMMARY\n")
            f.write("-" * 30 + "\n")
            f.write(f"Symbols Available: {summary['total_symbols_available']}\n")
            f.write(f"Total Patterns Found: {summary['total_patterns_found']}\n")
            f.write(f"Discovery Rate: {summary['discovery_rate']:.1f}%\n")
            f.write(f"Thresholds Tested: {summary['thresholds_tested']}\n\n")
            
            # Best patterns
            if scan_results.get('best_patterns'):
                f.write("TOP 10 PATTERNS BY QUALITY\n")
                f.write("-" * 30 + "\n")
                for i, pattern in enumerate(scan_results['best_patterns'][:10], 1):
                    f.write(f"{i:2d}. {pattern['symbol']:12} "
                           f"Quality: {pattern['quality_score']:5.1f} "
                           f"Stage: {pattern['current_stage']} "
                           f"({pattern['sector']})\n")
                f.write("\n")
            
            # Backtest results
            if backtest_results:
                f.write("BACKTEST PERFORMANCE\n")
                f.write("-" * 25 + "\n")
                
                successful_backtests = [r for r in backtest_results.values() 
                                      if 'performance_summary' in r]
                
                if successful_backtests:
                    avg_return = np.mean([r['performance_summary']['total_return'] 
                                        for r in successful_backtests 
                                        if r['performance_summary']['total_return']])
                    avg_win_rate = np.mean([r['performance_summary']['win_rate'] 
                                          for r in successful_backtests])
                    
                    f.write(f"Stocks Backtested: {len(successful_backtests)}\n")
                    f.write(f"Average Return: {avg_return:.1f}%\n")
                    f.write(f"Average Win Rate: {avg_win_rate:.1f}%\n\n")
                    
                    f.write("Top Performers:\n")
                    sorted_performers = sorted(successful_backtests,
                                             key=lambda x: x['performance_summary']['total_return'],
                                             reverse=True)
                    
                    for i, result in enumerate(sorted_performers[:5], 1):
                        perf = result['performance_summary']
                        f.write(f"{i}. {result['symbol']}: {perf['total_return']:.1f}% "
                               f"({perf['total_trades']} trades)\n")


def main():
    """Run broader universe VCP analysis"""
    
    print("BROADER UNIVERSE VCP PATTERN ANALYSIS")
    print("=" * 50)
    print(f"Testing {len(BROADER_STOCK_UNIVERSE)} stocks across multiple sectors")
    print("Including large-cap, mid-cap, and high-growth stocks")
    
    # Initialize tester
    tester = BroaderUniverseVCPTester()
    
    # Get available symbols from database
    print("\n🔍 Phase 1: Database Symbol Verification")
    available_symbols = tester.get_available_symbols_from_db()
    
    if len(available_symbols) < 20:
        print("❌ Insufficient symbols found in database")
        return
    
    print(f"✅ Found {len(available_symbols)} symbols with sufficient data")
    
    # Run progressive scan
    print(f"\n🎯 Phase 2: Progressive VCP Pattern Scan")
    scan_results = tester.run_progressive_vcp_scan(
        symbols=available_symbols,
        quality_thresholds=[25.0, 35.0, 45.0],  # Lower thresholds for discovery
        max_stocks_per_threshold=60
    )
    
    # Analyze patterns
    if scan_results['all_patterns']:
        print(f"\n📊 Phase 3: Pattern Analysis")
        pattern_analysis = tester.analyze_pattern_characteristics(scan_results['all_patterns'])
        print(f"✅ Found {pattern_analysis['pattern_count']} total patterns")
        print(f"   Average Quality: {pattern_analysis['quality_stats']['average']:.1f}")
        print(f"   Top Sectors: {[sector for sector, count in pattern_analysis['top_sectors']]}")
        
        # Run detailed backtest on best patterns
        print(f"\n🚀 Phase 4: Detailed Backtesting")
        backtest_results = tester.run_detailed_backtest_on_patterns(
            patterns=scan_results['best_patterns'],
            max_patterns=15
        )
        
        # Save results
        print(f"\n💾 Phase 5: Saving Results")
        file_info = tester.save_comprehensive_results(scan_results, backtest_results)
        
        # Summary
        print(f"\n🎉 ANALYSIS COMPLETE!")
        print(f"   Patterns Found: {len(scan_results['all_patterns'])}")
        print(f"   Patterns Backtested: {len(backtest_results)}")
        print(f"   Files Saved: {len(file_info)}")
        
    else:
        print(f"\n❌ No VCP patterns found in broader universe")
        print(f"   Consider lowering quality thresholds further")
        print(f"   Or expanding the symbol universe")
    
    return scan_results


if __name__ == "__main__":
    results = main()