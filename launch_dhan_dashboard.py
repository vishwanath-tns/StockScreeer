"""
Dhan Services Dashboard Launcher
================================
Launch the market data services dashboard.

Usage:
    python launch_dhan_dashboard.py
"""
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dhan_trading.dashboard.service_dashboard import main

if __name__ == "__main__":
    main()
