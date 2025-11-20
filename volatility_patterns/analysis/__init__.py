"""
Analysis Module for VCP Detection System
========================================

Provides scanning, backtesting and performance analysis capabilities:
- VCP Pattern Scanner for multi-stock analysis
- Backtesting framework for pattern validation
- Performance tracking for detected patterns
- Statistical analysis and reporting
"""

from .vcp_scanner import VCPScanner, ScanFilter, ScanResult
from .vcp_backtester import VCPBacktester, BacktestConfig, BacktestResults, Trade
# from .performance_tracker import PerformanceTracker  # To be implemented

__all__ = ['VCPScanner', 'ScanFilter', 'ScanResult', 'VCPBacktester', 'BacktestConfig', 'BacktestResults', 'Trade']  # , 'PerformanceTracker'