"""
Golden Cross / Death Cross Scanner Module
==========================================
Detect and track moving average crossover signals for Nifty 500 stocks.

Key Features:
- Detect Golden Cross (50 SMA crosses above 200 SMA)
- Detect Death Cross (50 SMA crosses below 200 SMA)
- Store historical signals in database
- Track signal history for each stock
- Daily incremental scanning
- Parallel processing for performance

Usage:
    # CLI - Scan for today's signals
    python -m scanners.golden_death_cross
    
    # API - Use in other modules
    from scanners.golden_death_cross import CrossoverDetector
    detector = CrossoverDetector()
    signals = detector.scan_all_stocks()

Author: Stock Screener Project
Date: 2025-12-08
"""

from .detector import (
    CrossoverDetector,
    CrossoverSignal,
    CrossoverType,
    run_daily_scan,
)
from .scanner_gui import CrossoverScannerGUI

__all__ = [
    'CrossoverDetector',
    'CrossoverSignal', 
    'CrossoverType',
    'CrossoverScannerGUI',
    'run_daily_scan',
]
