#!/usr/bin/env python3
"""
Launch script for Yahoo Finance Data Downloader
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
        from yfinance_downloader_gui import YFinanceDownloaderGUI
        
        print("🚀 Starting Yahoo Finance Data Downloader...")
        print("📊 MarketData Database Integration")
        print("🎯 NIFTY Daily Data Collection")
        print("-" * 50)
        
        app = YFinanceDownloaderGUI()
        app.run()
        
    except ImportError as e:
        print(f"❌ Import Error: {e}")
        print("Make sure yfinance package is installed: pip install yfinance")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error starting application: {e}")
        sys.exit(1)