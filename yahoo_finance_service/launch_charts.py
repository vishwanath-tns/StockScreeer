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
        print("🕯️ Candlestick Charts with Symbol Selection")
        print("-" * 50)
        
        # Check required packages
        missing_packages = []
        
        try:
            import mplfinance
        except ImportError:
            missing_packages.append('mplfinance')
            
        try:
            import matplotlib
        except ImportError:
            missing_packages.append('matplotlib')
        
        if missing_packages:
            print(f"❌ Missing required packages: {', '.join(missing_packages)}")
            print(f"Install with: pip install {' '.join(missing_packages)}")
            sys.exit(1)
        
        app = ChartVisualizerGUI()
        app.run()
        
    except ImportError as e:
        print(f"❌ Import Error: {e}")
        print("Make sure all required packages are installed:")
        print("pip install mplfinance matplotlib tkinter")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error starting application: {e}")
        sys.exit(1)