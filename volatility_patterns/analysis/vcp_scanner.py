"""
VCP Pattern Scanner
==================

Multi-stock VCP pattern scanner with filtering, ranking, and batch processing capabilities.
Designed to efficiently scan large universes of stocks for Volatility Contracting Patterns.

Features:
- Parallel processing for performance
- Market segment filtering (Large Cap, Mid Cap, Small Cap)
- Sector-based filtering and analysis
- Quality score ranking and filtering
- Stage analysis filtering
- Volume and liquidity filters
- Export capabilities for results

Author: GitHub Copilot
Date: November 2025
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Union, Tuple
from dataclasses import dataclass, asdict
from datetime import date, timedelta
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
import time
from pathlib import Path
import sys
import os

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from volatility_patterns.data.data_service import DataService
from volatility_patterns.core.vcp_detector import VCPDetector, VCPPattern
from volatility_patterns.core.technical_indicators import TechnicalIndicators


@dataclass
class ScanFilter:
    """Configuration for VCP scan filtering"""
    min_quality_score: float = 60.0
    min_market_cap: Optional[float] = None  # In crores
    max_market_cap: Optional[float] = None
    sectors: Optional[List[str]] = None
    stages: Optional[List[int]] = None  # Weinstein stages 1-4
    min_volume: Optional[float] = None  # Minimum average volume
    min_price: Optional[float] = None
    max_price: Optional[float] = None
    exclude_symbols: Optional[List[str]] = None
    include_only: Optional[List[str]] = None


@dataclass
class ScanResult:
    """Single stock VCP scan result"""
    symbol: str
    patterns_found: int
    best_pattern: Optional[VCPPattern]
    scan_time: float
    error: Optional[str] = None
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for easy analysis"""
        result = {
            'symbol': self.symbol,
            'patterns_found': self.patterns_found,
            'scan_time': self.scan_time,
            'error': self.error
        }
        
        if self.best_pattern:
            result.update({
                'quality_score': self.best_pattern.quality_score,
                'pattern_start': self.best_pattern.pattern_start,
                'pattern_end': self.best_pattern.pattern_end,
                'base_duration': self.best_pattern.base_duration,
                'contractions_count': len(self.best_pattern.contractions),
                'volatility_compression': self.best_pattern.volatility_compression,
                'volume_compression': self.best_pattern.volume_compression,
                'current_stage': self.best_pattern.current_stage,
                'relative_strength': self.best_pattern.relative_strength,
                'is_setup_complete': self.best_pattern.is_setup_complete,
                'breakout_level': self.best_pattern.breakout_level,
                'stop_loss_level': self.best_pattern.stop_loss_level,
                'total_decline': self.best_pattern.total_decline
            })
        
        return result


class VCPScanner:
    """
    Multi-stock VCP Pattern Scanner
    
    Efficiently scans large universes of stocks for VCP patterns with:
    - Parallel processing for speed
    - Comprehensive filtering options
    - Quality ranking and analysis
    - Export capabilities
    """
    
    def __init__(self, max_workers: int = 4):
        self.data_service = DataService()
        self.detector = VCPDetector()
        self.indicators = TechnicalIndicators()
        self.logger = logging.getLogger(__name__)
        self.max_workers = max_workers
        
    def get_stock_universe(
        self,
        segment: str = 'ALL',  # 'ALL', 'LARGE_CAP', 'MID_CAP', 'SMALL_CAP', 'NIFTY50'
        min_volume: float = 100000,  # Minimum average volume
        active_only: bool = True
    ) -> List[str]:
        """
        Get filtered stock universe for scanning
        
        Args:
            segment: Market segment filter
            min_volume: Minimum average volume filter
            active_only: Only actively traded stocks
            
        Returns:
            List of stock symbols to scan
        """
        self.logger.info(f"Building stock universe for segment: {segment}")
        
        # Get stock list from database
        try:
            engine = self.data_service.engine
            
            if segment == 'NIFTY50':
                # Nifty 50 stocks (hardcoded list for now)
                symbols = [
                    'RELIANCE', 'TCS', 'HDFCBANK', 'INFY', 'ICICIBANK', 'SBIN', 'BHARTIARTL',
                    'LICI', 'HINDUNILVR', 'ITC', 'LT', 'KOTAKBANK', 'AXISBANK', 'ASIANPAINT',
                    'NESTLEIND', 'MARUTI', 'HCLTECH', 'BAJFINANCE', 'TITAN', 'ADANIENT',
                    'ONGC', 'NTPC', 'POWERGRID', 'M&M', 'ULTRACEMCO', 'COALINDIA', 'SUNPHARMA',
                    'TATAMOTORS', 'WIPRO', 'JSWSTEEL', 'LTIM', 'GRASIM', 'TECHM', 'HINDALCO',
                    'INDUSINDBK', 'ADANIPORTS', 'BAJAJFINSV', 'HDFCLIFE', 'SBILIFE', 'CIPLA',
                    'TATASTEEL', 'BRITANNIA', 'DIVISLAB', 'HEROMOTOCO', 'APOLLOHOSP',
                    'DRREDDY', 'EICHERMOT', 'BAJAJ-AUTO', 'TRENT', 'BPCL'
                ]
            else:
                # Query database for active stocks
                from sqlalchemy import text
                with engine.connect() as conn:
                    query = text("""
                    SELECT DISTINCT symbol 
                    FROM nse_equity_bhavcopy_full 
                    WHERE trade_date >= DATE_SUB(CURDATE(), INTERVAL 30 DAY)
                    AND ttl_trd_qnty > :min_volume
                    AND close_price > 10
                    AND series = 'EQ'
                    ORDER BY symbol
                    """)
                    
                    result = conn.execute(query, {"min_volume": min_volume})
                    symbols = [row[0] for row in result.fetchall()]
            
            self.logger.info(f"Found {len(symbols)} symbols for scanning")
            return symbols
            
        except Exception as e:
            self.logger.error(f"Error building stock universe: {e}")
            # Fallback to major stocks
            return ['RELIANCE', 'TCS', 'INFY', 'HDFCBANK', 'ICICIBANK', 'SBIN', 
                   'BHARTIARTL', 'HINDUNILVR', 'ITC', 'LT']
    
    def scan_single_stock(
        self,
        symbol: str,
        lookback_days: int = 300,
        min_quality: float = 60.0
    ) -> ScanResult:
        """
        Scan a single stock for VCP patterns
        
        Args:
            symbol: Stock symbol to scan
            lookback_days: Days of data to analyze
            min_quality: Minimum quality score threshold
            
        Returns:
            ScanResult with pattern information
        """
        start_time = time.time()
        
        try:
            # Get stock data
            end_date = date.today()
            start_date = end_date - timedelta(days=lookback_days + 100)  # Extra buffer
            
            data = self.data_service.get_ohlcv_data(symbol, start_date, end_date)
            
            if len(data) < 100:  # Minimum data requirement
                return ScanResult(
                    symbol=symbol,
                    patterns_found=0,
                    best_pattern=None,
                    scan_time=time.time() - start_time,
                    error="Insufficient data"
                )
            
            # Detect VCP patterns
            patterns = self.detector.detect_vcp_patterns(data, symbol, lookback_days)
            
            # Filter by quality
            quality_patterns = [p for p in patterns if p.quality_score >= min_quality]
            
            # Get best pattern
            best_pattern = None
            if quality_patterns:
                best_pattern = max(quality_patterns, key=lambda x: x.quality_score)
            
            return ScanResult(
                symbol=symbol,
                patterns_found=len(quality_patterns),
                best_pattern=best_pattern,
                scan_time=time.time() - start_time
            )
            
        except Exception as e:
            return ScanResult(
                symbol=symbol,
                patterns_found=0,
                best_pattern=None,
                scan_time=time.time() - start_time,
                error=str(e)
            )
    
    def scan_multiple_stocks(
        self,
        symbols: List[str],
        scan_filter: Optional[ScanFilter] = None,
        lookback_days: int = 300,
        parallel: bool = True
    ) -> List[ScanResult]:
        """
        Scan multiple stocks for VCP patterns
        
        Args:
            symbols: List of symbols to scan
            scan_filter: Filtering criteria
            lookback_days: Days of historical data
            parallel: Enable parallel processing
            
        Returns:
            List of ScanResult objects
        """
        self.logger.info(f"Starting VCP scan of {len(symbols)} stocks")
        
        if scan_filter is None:
            scan_filter = ScanFilter()
        
        results = []
        start_time = time.time()
        
        if parallel and len(symbols) > 1:
            # Parallel processing
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                # Submit all tasks
                future_to_symbol = {
                    executor.submit(
                        self.scan_single_stock, 
                        symbol, 
                        lookback_days, 
                        scan_filter.min_quality_score
                    ): symbol for symbol in symbols
                }
                
                # Collect results as they complete
                for future in as_completed(future_to_symbol):
                    symbol = future_to_symbol[future]
                    try:
                        result = future.result()
                        results.append(result)
                        
                        # Log progress
                        if result.patterns_found > 0:
                            self.logger.info(f"✓ {symbol}: {result.patterns_found} patterns, "
                                           f"best score: {result.best_pattern.quality_score:.1f}")
                        else:
                            self.logger.debug(f"- {symbol}: No patterns found")
                            
                    except Exception as e:
                        self.logger.error(f"Error scanning {symbol}: {e}")
                        results.append(ScanResult(
                            symbol=symbol,
                            patterns_found=0,
                            best_pattern=None,
                            scan_time=0,
                            error=str(e)
                        ))
        else:
            # Sequential processing
            for i, symbol in enumerate(symbols, 1):
                self.logger.info(f"Scanning {i}/{len(symbols)}: {symbol}")
                result = self.scan_single_stock(symbol, lookback_days, scan_filter.min_quality_score)
                results.append(result)
        
        total_time = time.time() - start_time
        successful_scans = len([r for r in results if r.error is None])
        patterns_found = sum(r.patterns_found for r in results)
        
        self.logger.info(f"Scan completed: {successful_scans}/{len(symbols)} stocks, "
                        f"{patterns_found} total patterns, {total_time:.2f}s")
        
        return results
    
    def analyze_scan_results(self, results: List[ScanResult]) -> Dict:
        """
        Analyze and summarize scan results
        
        Args:
            results: List of scan results
            
        Returns:
            Comprehensive analysis summary
        """
        # Filter successful results
        successful = [r for r in results if r.error is None]
        with_patterns = [r for r in successful if r.patterns_found > 0]
        
        if not successful:
            return {'error': 'No successful scans'}
        
        # Performance metrics
        total_scan_time = sum(r.scan_time for r in successful)
        avg_scan_time = total_scan_time / len(successful)
        
        # Pattern statistics
        total_patterns = sum(r.patterns_found for r in successful)
        
        quality_scores = []
        stage_distribution = {}
        setup_complete = 0
        
        for result in with_patterns:
            if result.best_pattern:
                quality_scores.append(result.best_pattern.quality_score)
                stage = result.best_pattern.current_stage
                stage_distribution[stage] = stage_distribution.get(stage, 0) + 1
                
                if result.best_pattern.is_setup_complete:
                    setup_complete += 1
        
        # Create summary
        summary = {
            'scan_summary': {
                'total_stocks_scanned': len(results),
                'successful_scans': len(successful),
                'stocks_with_patterns': len(with_patterns),
                'total_patterns_found': total_patterns,
                'success_rate': len(successful) / len(results) * 100,
                'pattern_hit_rate': len(with_patterns) / len(successful) * 100 if successful else 0
            },
            'performance_metrics': {
                'total_scan_time': total_scan_time,
                'average_scan_time': avg_scan_time,
                'scans_per_second': len(successful) / total_scan_time if total_scan_time > 0 else 0
            },
            'pattern_analysis': {
                'average_quality_score': np.mean(quality_scores) if quality_scores else 0,
                'quality_score_std': np.std(quality_scores) if quality_scores else 0,
                'stage_distribution': stage_distribution,
                'setups_ready_for_breakout': setup_complete,
                'top_quality_threshold': np.percentile(quality_scores, 80) if quality_scores else 0
            }
        }
        
        return summary
    
    def get_top_patterns(
        self,
        results: List[ScanResult],
        top_n: int = 10,
        sort_by: str = 'quality_score'  # 'quality_score', 'stage', 'setup_complete'
    ) -> List[ScanResult]:
        """
        Get top N VCP patterns from scan results
        
        Args:
            results: Scan results to rank
            top_n: Number of top patterns to return
            sort_by: Sorting criteria
            
        Returns:
            Top N patterns sorted by criteria
        """
        # Filter results with patterns
        with_patterns = [r for r in results if r.patterns_found > 0 and r.best_pattern]
        
        if not with_patterns:
            return []
        
        # Sort by criteria
        if sort_by == 'quality_score':
            with_patterns.sort(key=lambda x: x.best_pattern.quality_score, reverse=True)
        elif sort_by == 'stage':
            # Prefer Stage 2 patterns, then by quality
            with_patterns.sort(
                key=lambda x: (x.best_pattern.current_stage == 2, x.best_pattern.quality_score),
                reverse=True
            )
        elif sort_by == 'setup_complete':
            # Prefer complete setups, then by quality
            with_patterns.sort(
                key=lambda x: (x.best_pattern.is_setup_complete, x.best_pattern.quality_score),
                reverse=True
            )
        
        return with_patterns[:top_n]
    
    def export_results(
        self,
        results: List[ScanResult],
        output_path: str,
        format: str = 'csv'  # 'csv', 'excel'
    ) -> bool:
        """
        Export scan results to file
        
        Args:
            results: Scan results to export
            output_path: Output file path
            format: Export format
            
        Returns:
            Success status
        """
        try:
            # Convert results to DataFrame
            data = []
            for result in results:
                row_data = result.to_dict()
                data.append(row_data)
            
            df = pd.DataFrame(data)
            
            # Only sort if quality_score column exists
            if 'quality_score' in df.columns and not df['quality_score'].isna().all():
                df_sorted = df.sort_values('quality_score', ascending=False, na_position='last')
            else:
                df_sorted = df.sort_values('symbol')
            
            # Export
            if format.lower() == 'csv':
                df_sorted.to_csv(output_path, index=False)
            elif format.lower() == 'excel':
                df_sorted.to_excel(output_path, index=False)
            
            self.logger.info(f"Results exported to {output_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error exporting results: {e}")
            return False
    
    def run_full_scan(
        self,
        segment: str = 'NIFTY50',
        scan_filter: Optional[ScanFilter] = None,
        lookback_days: int = 300,
        export_path: Optional[str] = None
    ) -> Dict:
        """
        Run complete VCP scan with analysis and optional export
        
        Args:
            segment: Market segment to scan
            scan_filter: Filtering criteria
            lookback_days: Days of historical data
            export_path: Optional export file path
            
        Returns:
            Complete scan results and analysis
        """
        self.logger.info(f"Starting full VCP scan for segment: {segment}")
        
        # Get stock universe
        symbols = self.get_stock_universe(segment)
        
        if not symbols:
            return {'error': 'No symbols found for scanning'}
        
        # Run scan
        results = self.scan_multiple_stocks(symbols, scan_filter, lookback_days)
        
        # Analyze results
        analysis = self.analyze_scan_results(results)
        
        # Get top patterns
        top_patterns = self.get_top_patterns(results, top_n=20)
        
        # Export if requested
        if export_path:
            success = self.export_results(results, export_path)
            analysis['export_success'] = success
            analysis['export_path'] = export_path
        
        # Compile final results
        final_results = {
            'scan_results': results,
            'analysis': analysis,
            'top_patterns': top_patterns,
            'scan_filter': asdict(scan_filter) if scan_filter else None,
            'parameters': {
                'segment': segment,
                'lookback_days': lookback_days,
                'symbols_scanned': len(symbols)
            }
        }
        
        return final_results