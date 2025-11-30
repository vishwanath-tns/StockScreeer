"""
Bollinger Bands Orchestrator

Main coordinator for the BB analysis system.
Provides a unified interface for all BB operations.
"""

import logging
from datetime import date, datetime, timedelta
from typing import Any, Callable, Dict, List, Optional, Tuple
import pandas as pd

from ..models.bb_models import BBConfig, BollingerBands, BBRating
from ..models.signal_models import BBSignal, SignalType
from ..models.scan_models import ScanType, ScanResult
from ..db.bb_repository import BBRepository
from ..db.bb_schema import create_bb_tables
from .bb_calculator import BBCalculator
from .squeeze_detector import SqueezeDetector
from .trend_analyzer import TrendAnalyzer
from .bb_rating_service import BBRatingService
from ..signals.signal_generator import SignalGenerator
from ..signals.pullback_signals import PullbackSignalGenerator
from ..signals.mean_reversion_signals import MeanReversionSignalGenerator
from ..signals.breakout_signals import BreakoutSignalGenerator
from ..scanners.squeeze_scanner import SqueezeScanner
from ..scanners.bulge_scanner import BulgeScanner
from ..scanners.trend_scanner import TrendScanner
from ..scanners.pullback_scanner import PullbackScanner
from ..scanners.reversion_scanner import MeanReversionScanner


logger = logging.getLogger(__name__)


class BBOrchestrator:
    """
    Main orchestrator for Bollinger Bands analysis.
    
    Provides:
    - Unified API for all BB operations
    - Coordination between calculators, generators, and scanners
    - Database operations
    - Event handling
    """
    
    # Default backfill start date (5 years back to match rankings)
    DEFAULT_BACKFILL_START = date(2020, 12, 1)
    
    def __init__(self,
                 config: BBConfig = None,
                 use_redis: bool = False):
        """
        Initialize orchestrator.
        
        Args:
            config: BB calculation config
            use_redis: Enable Redis for parallel processing
        """
        self.config = config or BBConfig.STANDARD
        self.use_redis = use_redis
        
        # Initialize components
        self.repository = BBRepository()
        self.calculator = BBCalculator(self.config)
        self.squeeze_detector = SqueezeDetector()
        self.trend_analyzer = TrendAnalyzer()
        self.rating_service = BBRatingService()
        
        # Signal generators
        self.signal_generator = SignalGenerator()
        self.pullback_generator = PullbackSignalGenerator()
        self.reversion_generator = MeanReversionSignalGenerator()
        self.breakout_generator = BreakoutSignalGenerator()
        
        # Scanners
        self.squeeze_scanner = SqueezeScanner()
        self.bulge_scanner = BulgeScanner()
        self.trend_scanner = TrendScanner()
        self.pullback_scanner = PullbackScanner()
        self.reversion_scanner = MeanReversionScanner()
        
        # Redis components (optional)
        self.dispatcher = None
        if use_redis:
            try:
                from ..parallel.bb_dispatcher import BBDispatcher
                self.dispatcher = BBDispatcher()
                logger.info("Redis dispatcher enabled")
            except ImportError:
                logger.warning("Redis not available, falling back to sync processing")
        
        # Event callbacks
        self._progress_callbacks: List[Callable] = []
    
    def initialize(self):
        """Initialize database tables."""
        create_bb_tables()
        logger.info("BB database tables initialized")
    
    # ========== Calculation Operations ==========
    
    def calculate_daily(self, symbol: str, df: pd.DataFrame) -> List[BollingerBands]:
        """
        Calculate Bollinger Bands for a symbol.
        
        Args:
            symbol: Stock symbol
            df: DataFrame with OHLCV data
            
        Returns:
            List of BollingerBands (most recent first)
        """
        if df.empty:
            return []
        
        # Calculate BB series
        bb_df = self.calculator.calculate_series(df)
        
        # Convert to BollingerBands objects
        result = []
        for idx, row in bb_df.iterrows():
            bb = BollingerBands(
                date=idx.date() if hasattr(idx, 'date') else idx,
                close=row['close'],
                upper=row['bb_upper'],
                middle=row['bb_middle'],
                lower=row['bb_lower'],
                percent_b=row['bb_percent_b'],
                bandwidth=row['bb_bandwidth'],
                bandwidth_percentile=row.get('bb_bandwidth_percentile', 50.0)
            )
            result.append(bb)
        
        # Sort most recent first
        result.sort(key=lambda x: x.date, reverse=True)
        
        return result
    
    def calculate_and_save(self, symbol: str, df: pd.DataFrame) -> int:
        """
        Calculate BB and save to database.
        
        Args:
            symbol: Stock symbol
            df: DataFrame with OHLCV data
            
        Returns:
            Number of records saved
        """
        bb_list = self.calculate_daily(symbol, df)
        
        if not bb_list:
            return 0
        
        # Convert to dict format for storage
        count = 0
        for bb in bb_list:
            # Detect squeeze/bulge state
            squeeze_state = self.squeeze_detector.get_squeeze_state(bb_list)
            
            data = {
                "symbol": symbol,
                "trade_date": bb.date,
                "close": bb.close,
                "upper_band": bb.upper,
                "middle_band": bb.middle,
                "lower_band": bb.lower,
                "percent_b": bb.percent_b,
                "bandwidth": bb.bandwidth,
                "bandwidth_percentile": bb.bandwidth_percentile,
                "in_squeeze": squeeze_state.name == "SQUEEZE",
                "in_bulge": squeeze_state.name == "BULGE"
            }
            
            if self.repository.save_bb_daily(data):
                count += 1
        
        logger.info(f"Saved {count} BB records for {symbol}")
        
        return count
    
    def backfill_symbol(self, symbol: str, df: pd.DataFrame,
                        start_date: date = None,
                        progress_callback: Callable = None) -> int:
        """
        Backfill historical BB data for a symbol.
        
        Args:
            symbol: Stock symbol
            df: Full historical DataFrame
            start_date: Start date for backfill
            progress_callback: Optional progress callback
            
        Returns:
            Number of records saved
        """
        start_date = start_date or self.DEFAULT_BACKFILL_START
        
        # Filter to date range
        df = df[df.index >= pd.Timestamp(start_date)]
        
        if df.empty:
            return 0
        
        # Calculate full series
        bb_df = self.calculator.calculate_series(df)
        
        # Convert and save in batches
        total = len(bb_df)
        saved = 0
        
        for idx, row in bb_df.iterrows():
            data = {
                "symbol": symbol,
                "trade_date": idx.date() if hasattr(idx, 'date') else idx,
                "close": row['close'],
                "upper_band": row['bb_upper'],
                "middle_band": row['bb_middle'],
                "lower_band": row['bb_lower'],
                "percent_b": row['bb_percent_b'],
                "bandwidth": row['bb_bandwidth'],
                "bandwidth_percentile": row.get('bb_bandwidth_percentile', 50.0),
                "in_squeeze": False,  # Will be calculated separately
                "in_bulge": False
            }
            
            if self.repository.save_bb_daily(data):
                saved += 1
            
            if progress_callback and saved % 100 == 0:
                progress = saved / total * 100
                progress_callback(symbol, progress)
        
        return saved
    
    # ========== Rating Operations ==========
    
    def calculate_rating(self, symbol: str, 
                         bb_history: List[BollingerBands]) -> Optional[BBRating]:
        """
        Calculate BB rating for a symbol.
        
        Args:
            symbol: Stock symbol
            bb_history: BB history (most recent first)
            
        Returns:
            BBRating or None
        """
        if not bb_history:
            return None
        
        return self.rating_service.calculate_rating(symbol, bb_history)
    
    def calculate_all_ratings(self, 
                              trade_date: date = None,
                              progress_callback: Callable = None) -> Dict[str, BBRating]:
        """
        Calculate ratings for all symbols.
        
        Args:
            trade_date: Date for ratings
            progress_callback: Optional progress callback
            
        Returns:
            Dict mapping symbol to BBRating
        """
        trade_date = trade_date or date.today()
        
        # Get all symbols with data
        # In real implementation, fetch from database
        ratings = {}
        
        # ... implementation ...
        
        return ratings
    
    # ========== Signal Operations ==========
    
    def generate_signals(self, symbol: str,
                         bb_history: List[BollingerBands],
                         volume_data: List[float] = None,
                         avg_volume: float = None) -> List[BBSignal]:
        """
        Generate all signals for a symbol.
        
        Args:
            symbol: Stock symbol
            bb_history: BB history
            volume_data: Volume data
            avg_volume: Average volume
            
        Returns:
            List of BBSignal
        """
        signals = []
        
        # Main patterns (W-bottom, M-top, squeeze breakout)
        main_signals = self.signal_generator.generate_signals(
            bb_history, symbol, volume_data, avg_volume
        )
        signals.extend(main_signals)
        
        # Pullback signals
        pullback = self.pullback_generator.generate_signal(
            bb_history, symbol, volume_data, avg_volume
        )
        if pullback:
            signals.append(pullback)
        
        # Mean reversion signals
        reversion = self.reversion_generator.generate_signal(
            bb_history, symbol, volume_data, avg_volume
        )
        if reversion:
            signals.append(reversion)
        
        # Breakout signals
        breakout = self.breakout_generator.generate_signal(
            bb_history, symbol, volume_data, avg_volume
        )
        if breakout:
            signals.append(breakout)
        
        # Sort by confidence
        signals.sort(key=lambda s: s.confidence_score, reverse=True)
        
        return signals
    
    def get_buy_signals(self, 
                        all_bb_data: Dict[str, List[BollingerBands]],
                        min_confidence: float = 60.0) -> List[BBSignal]:
        """
        Get all buy signals across universe.
        
        Args:
            all_bb_data: BB data for all symbols
            min_confidence: Minimum confidence score
            
        Returns:
            List of buy signals sorted by confidence
        """
        buy_signals = []
        
        for symbol, bb_history in all_bb_data.items():
            signals = self.generate_signals(symbol, bb_history)
            for signal in signals:
                if signal.signal_type == SignalType.BUY and signal.confidence_score >= min_confidence:
                    buy_signals.append(signal)
        
        buy_signals.sort(key=lambda s: s.confidence_score, reverse=True)
        
        return buy_signals
    
    def get_sell_signals(self,
                         all_bb_data: Dict[str, List[BollingerBands]],
                         min_confidence: float = 60.0) -> List[BBSignal]:
        """
        Get all sell signals across universe.
        """
        sell_signals = []
        
        for symbol, bb_history in all_bb_data.items():
            signals = self.generate_signals(symbol, bb_history)
            for signal in signals:
                if signal.signal_type == SignalType.SELL and signal.confidence_score >= min_confidence:
                    sell_signals.append(signal)
        
        sell_signals.sort(key=lambda s: s.confidence_score, reverse=True)
        
        return sell_signals
    
    # ========== Scan Operations ==========
    
    def run_scan(self, scan_type: ScanType,
                 all_bb_data: Dict[str, List[BollingerBands]]) -> List[ScanResult]:
        """
        Run a specific scan.
        
        Args:
            scan_type: Type of scan to run
            all_bb_data: BB data for all symbols
            
        Returns:
            List of scan results
        """
        if scan_type == ScanType.SQUEEZE:
            return self.squeeze_scanner.scan(all_bb_data)
        elif scan_type == ScanType.BULGE:
            return self.bulge_scanner.scan(all_bb_data)
        elif scan_type == ScanType.TREND_UP:
            return self.trend_scanner.scan_uptrends(all_bb_data)
        elif scan_type == ScanType.TREND_DOWN:
            return self.trend_scanner.scan_downtrends(all_bb_data)
        elif scan_type == ScanType.PULLBACK_BUY:
            return self.pullback_scanner.scan_bullish_pullbacks(all_bb_data)
        elif scan_type == ScanType.PULLBACK_SELL:
            return self.pullback_scanner.scan_bearish_rallies(all_bb_data)
        elif scan_type == ScanType.OVERSOLD:
            return self.reversion_scanner.scan_oversold(all_bb_data)
        elif scan_type == ScanType.OVERBOUGHT:
            return self.reversion_scanner.scan_overbought(all_bb_data)
        else:
            raise ValueError(f"Unknown scan type: {scan_type}")
    
    def run_all_scans(self,
                      all_bb_data: Dict[str, List[BollingerBands]]) -> Dict[str, List]:
        """
        Run all available scans.
        
        Returns:
            Dict mapping scan type to results
        """
        results = {}
        
        for scan_type in ScanType:
            try:
                results[scan_type.value] = self.run_scan(scan_type, all_bb_data)
            except Exception as e:
                logger.error(f"Scan {scan_type} failed: {e}")
                results[scan_type.value] = []
        
        return results
    
    def find_trading_opportunities(self,
                                   all_bb_data: Dict[str, List[BollingerBands]],
                                   min_confidence: float = 60.0) -> Dict[str, List]:
        """
        Find all trading opportunities.
        
        Returns:
            Dict with:
            - buy_signals: High-confidence buy signals
            - sell_signals: High-confidence sell signals
            - squeeze_setups: Stocks in squeeze
            - pullback_buys: Pullback buy setups
            - mean_reversion: Mean reversion candidates
        """
        return {
            "buy_signals": self.get_buy_signals(all_bb_data, min_confidence),
            "sell_signals": self.get_sell_signals(all_bb_data, min_confidence),
            "squeeze_setups": self.squeeze_scanner.find_imminent_breakouts(all_bb_data),
            "pullback_buys": self.pullback_scanner.scan_bullish_pullbacks(all_bb_data),
            "mean_reversion": self.reversion_scanner.find_reversal_with_confirmation(all_bb_data)
        }
    
    # ========== Event Handling ==========
    
    def on_progress(self, callback: Callable[[str, float], None]):
        """Register progress callback."""
        self._progress_callbacks.append(callback)
    
    def _notify_progress(self, operation: str, progress: float):
        """Notify all progress callbacks."""
        for callback in self._progress_callbacks:
            try:
                callback(operation, progress)
            except Exception as e:
                logger.warning(f"Progress callback error: {e}")
    
    # ========== Utility Methods ==========
    
    def get_symbol_summary(self, symbol: str,
                           bb_history: List[BollingerBands]) -> Dict[str, Any]:
        """
        Get comprehensive BB summary for a symbol.
        
        Returns:
            Dict with current state, signals, rating, etc.
        """
        if not bb_history:
            return {"symbol": symbol, "error": "No data"}
        
        current = bb_history[0]
        
        # Get state analysis
        squeeze_state = self.squeeze_detector.get_squeeze_state(bb_history)
        trend = self.trend_analyzer.analyze_trend(bb_history)
        rating = self.calculate_rating(symbol, bb_history)
        signals = self.generate_signals(symbol, bb_history)
        
        return {
            "symbol": symbol,
            "date": str(current.date),
            "close": current.close,
            "percent_b": current.percent_b,
            "bandwidth": current.bandwidth,
            "bandwidth_percentile": current.bandwidth_percentile,
            "upper_band": current.upper,
            "middle_band": current.middle,
            "lower_band": current.lower,
            "squeeze_state": squeeze_state.name,
            "trend": trend.name if hasattr(trend, 'name') else str(trend),
            "rating": rating.composite_score if rating else None,
            "grade": rating.letter_grade if rating else None,
            "active_signals": len(signals),
            "buy_signals": len([s for s in signals if s.signal_type == SignalType.BUY]),
            "sell_signals": len([s for s in signals if s.signal_type == SignalType.SELL])
        }
