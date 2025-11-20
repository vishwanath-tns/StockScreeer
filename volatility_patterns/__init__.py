"""
Volatility Contracting Patterns (VCP) Detection System
====================================================

A comprehensive system for detecting Mark Minervini-style Volatility Contracting Patterns
in stock price data, with backtesting and performance validation capabilities.

Modules:
--------
- data: Data fetching, split adjustment, and timeframe conversion
- core: VCP detection algorithms, technical indicators, and scoring
- scanners: Historical scanning and pattern validation
- analysis: Performance tracking and backtesting framework
- tests: Unit tests and validation suites

Features:
---------
- Timeframe-agnostic design (works with any timeframe data)
- Split-adjusted analysis for accurate historical patterns
- Mark Minervini VCP criteria implementation
- Historical backtesting with performance metrics
- Modular, scalable architecture

Usage:
------
    from volatility_patterns.data import DataService
    from volatility_patterns.core import VCPDetector
    
    # Initialize data service
    data_service = DataService()
    
    # Get price data
    data = data_service.get_ohlcv_data('RELIANCE', '2024-01-01', '2024-12-31')
    
    # Detect VCP patterns
    vcp_detector = VCPDetector()
    patterns = vcp_detector.detect_vcp_pattern(data, 'RELIANCE')

Author: AI Assistant
Created: November 16, 2025
Version: 1.0.0 (MVP)
"""

__version__ = "1.0.0"
__author__ = "AI Assistant"
__email__ = "assistant@ai.com"

# Package-level imports for easier access (commented out to avoid circular imports in MVP)
# from .data import DataService
# from .core import VCPDetector, TechnicalIndicators

# Version info
VERSION_INFO = {
    'major': 1,
    'minor': 0,
    'patch': 0,
    'status': 'MVP'
}

def get_version():
    """Get the current version string."""
    return f"{VERSION_INFO['major']}.{VERSION_INFO['minor']}.{VERSION_INFO['patch']}-{VERSION_INFO['status']}"

# Configuration constants
DEFAULT_TIMEFRAME = '1D'
DEFAULT_LOOKBACK_PERIODS = 252  # ~1 year of trading days
DEFAULT_VCP_MIN_BASE_WEEKS = 4
DEFAULT_VCP_MAX_BASE_WEEKS = 12
DEFAULT_PRIOR_UPTREND_THRESHOLD = 0.30  # 30% minimum gain

__all__ = [
    # 'DataService',
    # 'VCPDetector', 
    # 'TechnicalIndicators',
    'get_version',
    '__version__'
]