"""
Stock Alert Manager - Desktop GUI Launcher
==========================================

Launch the Stock Alert Manager desktop application.
"""

import sys
import os
import logging

# Add parent to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

from stock_alerts.gui.main_window import run_gui

if __name__ == '__main__':
    run_gui()
