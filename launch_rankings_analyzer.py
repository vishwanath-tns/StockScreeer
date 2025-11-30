#!/usr/bin/env python3
"""
Launch Rankings Analyzer GUI

Quick launcher for the rankings data analyzer.
"""

import os
import sys

# Add project root
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ranking.gui.rankings_analyzer import main

if __name__ == "__main__":
    main()
