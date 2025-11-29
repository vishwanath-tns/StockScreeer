"""
Historical Rankings Module

Builds historical stock rankings for backtesting and analysis.
This is a one-time operation, not part of the daily wizard.
"""

from .historical_rankings_builder import HistoricalRankingsBuilder

__all__ = ["HistoricalRankingsBuilder"]
