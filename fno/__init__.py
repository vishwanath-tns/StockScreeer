# NSE F&O Analysis Module
# Version 1.0.0 - December 2025

"""
NSE Futures & Options Analysis System

This module provides comprehensive analysis tools for NSE F&O segment:
- Import futures and options bhavcopy data
- Track daily imports to avoid duplicates
- Compare with previous day's data (OI changes, price changes)
- Option chain analysis for support/resistance levels
- Futures analysis for long/short buildup detection

Database: fno_marketdata (MySQL)
"""

__version__ = "1.0.0"
__author__ = "StockScreener Team"
