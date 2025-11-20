"""
Core Module for VCP Detection System
====================================

Contains the main VCP detection algorithms and supporting components:
- Technical indicators calculation
- VCP pattern detection logic
- Pattern criteria validation
- Quality scoring system
"""

from .technical_indicators import TechnicalIndicators

# Future VCP detection components (to be implemented in later iterations)
# from .vcp_detector import VCPDetector
# from .pattern_criteria import VCPCriteria
# from .scoring_engine import ScoringEngine

__all__ = ['TechnicalIndicators']  # , 'VCPDetector', 'VCPCriteria', 'ScoringEngine'