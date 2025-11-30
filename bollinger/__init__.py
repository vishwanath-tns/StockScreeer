"""
Bollinger Bands Analysis System

A comprehensive, event-driven system for analyzing stocks using Bollinger Bands.
Features:
- Core BB calculations (%b, BandWidth, bands)
- Signal generation (buy/sell with confidence scoring)
- Multiple scanners (squeeze, bulge, trend, pullback, reversion)
- Redis-based parallel processing for scalability
- Interactive GUI with charts and analysis tools
"""

__version__ = "1.0.0"

# Core models
from .models import (
    BBConfig, BollingerBands, BBRating,
    SignalType, PatternType, BBSignal, SignalConfidence,
    ScanType, ScanResult
)

# Services  
from .services import (
    BBCalculator, SqueezeDetector, TrendAnalyzer,
    BBRatingService, BBOrchestrator,
    DailyBBCompute, ComputeStats, create_bb_tables, run_daily_compute
)

# Signal generators
from .signals import (
    SignalGenerator, PullbackSignalGenerator,
    MeanReversionSignalGenerator, BreakoutSignalGenerator
)

# Scanners
from .scanners import (
    SqueezeScanner, BulgeScanner, TrendScanner,
    PullbackScanner, MeanReversionScanner
)

# Database
from .db import BBRepository

# GUI (lazy import to avoid Qt dependency issues if not using GUI)
def get_gui_class():
    """Get the GUI class (lazy import)."""
    from .gui import BBAnalyzerGUI
    return BBAnalyzerGUI

# For convenience, allow direct import but only after GUI is needed
try:
    from .gui import BBAnalyzerGUI, BBChartWidget
except ImportError:
    BBAnalyzerGUI = None
    BBChartWidget = None

__all__ = [
    '__version__',
    # Models
    'BBConfig', 'BollingerBands', 'BBRating',
    'SignalType', 'PatternType', 'BBSignal', 'SignalConfidence',
    'ScanType', 'ScanResult',
    # Services
    'BBCalculator', 'SqueezeDetector', 'TrendAnalyzer',
    'BBRatingService', 'BBOrchestrator',
    'DailyBBCompute', 'ComputeStats', 'create_bb_tables', 'run_daily_compute',
    # Signals
    'SignalGenerator', 'PullbackSignalGenerator',
    'MeanReversionSignalGenerator', 'BreakoutSignalGenerator',
    # Scanners
    'SqueezeScanner', 'BulgeScanner', 'TrendScanner',
    'PullbackScanner', 'MeanReversionScanner',
    # Database
    'BBRepository',
    # GUI
    'BBAnalyzerGUI', 'BBChartWidget', 'get_gui_class'
]
