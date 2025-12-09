"""
Volume Profile Analysis Module
==============================
Calculate and visualize Volume Profiles with VPOC and Value Area.

Key Concepts:
- Volume Profile: Distribution of volume at each price level
- VPOC (Volume Point of Control): Price level with highest volume
- VA (Value Area): Price range containing 70% of volume (configurable)
- VAH (Value Area High): Upper boundary of Value Area
- VAL (Value Area Low): Lower boundary of Value Area

Usage:
    from volume_profile import VolumeProfileVisualizer
    
    # Launch the GUI
    python -m volume_profile.visualizer

Author: Stock Screener Project
Date: 2025-12-09
"""

from .calculator import VolumeProfileCalculator, VolumeProfile
from .visualizer import VolumeProfileVisualizer

__all__ = [
    'VolumeProfileCalculator',
    'VolumeProfile',
    'VolumeProfileVisualizer',
]
