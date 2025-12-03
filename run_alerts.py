"""
Stock Alert System Launcher
===========================

A convenient launcher script for the Stock Alert System.
Run this script to start the alert system with various options.
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from stock_alerts.main import main

if __name__ == '__main__':
    main()
