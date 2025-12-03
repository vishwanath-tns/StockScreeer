"""
Volume Analysis Module
======================

A comprehensive module for detecting accumulation and distribution patterns
in stock price/volume data to identify potential breakout candidates.

Key Components:
- core/volume_indicators.py - OBV, A/D Line, CMF, VWAP calculations
- analysis/accumulation_detector.py - Accumulation/Distribution detection
- scanners/volume_scanner.py - Scan stocks for volume signals
- visualization/volume_charts.py - Multi-pane volume charts

Usage:
    from volume_analysis import VolumeScanner
    
    scanner = VolumeScanner()
    results = scanner.scan_nifty500()
    
    for stock in results.accumulation_stocks[:10]:
        print(f"{stock.symbol}: Score {stock.score:.1f}")
"""

from .core.volume_indicators import VolumeIndicators
from .analysis.accumulation_detector import AccumulationDetector
from .scanners.volume_scanner import VolumeScanner

__version__ = "1.0.0"
__all__ = [
    "VolumeIndicators",
    "AccumulationDetector",
    "VolumeScanner",
]
