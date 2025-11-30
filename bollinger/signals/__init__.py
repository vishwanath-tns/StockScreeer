"""Signal generation for Bollinger Bands system."""
from .signal_generator import SignalGenerator
from .pullback_signals import PullbackSignalGenerator
from .mean_reversion_signals import MeanReversionSignalGenerator
from .breakout_signals import BreakoutSignalGenerator

__all__ = [
    'SignalGenerator', 'PullbackSignalGenerator',
    'MeanReversionSignalGenerator', 'BreakoutSignalGenerator'
]
