#!/usr/bin/env python3
"""
Launch script for Yahoo Finance Chart Visualizer
"""

import sys
import os

# Add the service directory to the path
service_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, service_dir)

# Add parent directory to path for main project dependencies
parent_dir = os.path.dirname(service_dir)
sys.path.insert(0, parent_dir)

if __name__ == "__main__":
    try:
        from chart_visualizer import ChartVisualizerGUI
        
        print("🚀 Starting Yahoo Finance Chart Visualizer...")
        print("📊 Interactive Market Data Visualization")
        print("📈 Candlestick, Line, OHLC & Area Charts")
        print("-" * 50)
        
        app = ChartVisualizerGUI()
        app.run()
        
    except ImportError as e:
        print(f"❌ Import Error: {e}")
        print("Make sure all required packages are installed:")
        print("pip install matplotlib pandas numpy mplfinance")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error starting chart visualizer: {e}")
        sys.exit(1)