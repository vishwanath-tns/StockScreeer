#!/usr/bin/env python3

from gui.tabs.dashboard import DashboardTab
import tkinter as tk
import reporting_adv_decl as rad

def test_rsi_divergences():
    # Create a mock root for testing
    root = tk.Tk()
    root.withdraw()  # Hide the window
    
    try:
        dashboard = DashboardTab(root)
        engine = dashboard.get_database_engine()
        analysis = dashboard.analyze_rsi_divergences(engine)

        print('RSI Divergences Analysis:')
        print(f'Latest Date: {analysis["latest_date"]}')  
        print(f'Hidden Bullish: {analysis["hidden_bullish_count"]:,}')
        print(f'Hidden Bearish: {analysis["hidden_bearish_count"]:,}')
        print(f'Coverage: {analysis["coverage_percentage"]:.1f}%')
        print('Timeframe Status:')
        for k, v in analysis['timeframe_status'].items():
            print(f'  {k}: {v["latest_date"]} ({v["symbols"]:,} stocks)')
    finally:
        root.destroy()  # Clean up

if __name__ == "__main__":
    test_rsi_divergences()