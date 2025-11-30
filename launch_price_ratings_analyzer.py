#!/usr/bin/env python3
"""
Launch Price & Ratings Correlation Analyzer

Visualize stock price alongside all rating components to identify:
- How price and ratings correlate
- Whether ratings are leading indicators
- Entry/exit signals for swing trades and investments
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ranking.gui.price_ratings_analyzer import main

if __name__ == "__main__":
    main()
