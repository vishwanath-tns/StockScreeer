#!/usr/bin/env python3
"""
Enhanced launcher for Yahoo Finance Chart Visualizer
Works with your downloaded 5-year data
"""

import sys
import os
sys.path.append('.')
sys.path.append('./yahoo_finance_service')

def main():
    print("🚀 Starting Enhanced Yahoo Finance Chart Visualizer")
    print("📊 Visualizing Your Downloaded 5-Year Data")
    print("=" * 60)
    
    try:
        # Check data availability first
        from yahoo_finance_service.db_service import YFinanceDBService
        
        db_service = YFinanceDBService()
        conn = db_service.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(DISTINCT symbol) FROM yfinance_daily_quotes")
        symbol_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM yfinance_daily_quotes")
        total_records = cursor.fetchone()[0]
        
        cursor.close()
        
        print(f"📈 Available Data:")
        print(f"   • {symbol_count} symbols")
        print(f"   • {total_records:,} total records")
        print(f"   • 5-year history (2020-2025)")
        print()
        
        # Launch the chart visualizer
        from yahoo_finance_service.chart_visualizer import ChartVisualizerGUI
        
        print("🎯 Starting chart visualizer...")
        print("💡 Tips:")
        print("   • Select any stock symbol from dropdown")
        print("   • Choose date range or use presets")
        print("   • Try different chart types (Candlestick, Line, etc.)")
        print("   • Use 3 Months preset for quick visualization")
        print()
        
        app = ChartVisualizerGUI()
        app.run()
        
    except ImportError as e:
        print(f"❌ Import Error: {e}")
        print("\\nMissing packages? Install with:")
        print("pip install matplotlib mplfinance pandas numpy tkinter")
        return 1
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)