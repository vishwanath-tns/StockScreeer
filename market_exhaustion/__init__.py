"""
Market Exhaustion Detection Module
==================================
Tools for detecting market exhaustion and protecting portfolios from drawdowns.

Key Features:
- Daily breadth analysis (% stocks above SMAs)
- Divergence detection (price vs breadth)
- Overbought/Oversold zones
- Portfolio protection signals
"""

from .daily_detector import DailyExhaustionDetector
from .visualizer import ExhaustionVisualizer

__all__ = ['DailyExhaustionDetector', 'ExhaustionVisualizer']
