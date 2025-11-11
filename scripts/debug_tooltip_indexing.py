"""
Focused test to debug mplcursors tooltip indexing issues.
"""

import sys
import os
sys.path.append(os.path.dirname(__file__))

import matplotlib.pyplot as plt
import pandas as pd
from datetime import datetime, timedelta

try:
    import mplcursors
    CURSORS_AVAILABLE = True
    print("✅ mplcursors available")
except ImportError:
    CURSORS_AVAILABLE = False
    print("❌ mplcursors not available")

# Import our modules
import reporting_adv_decl as rad
import sma50_scanner

def debug_tooltip_indexing():
    """Debug exactly what mplcursors provides in sel.target.index."""
    print("\n=== Debugging Tooltip Indexing ===")
    
    # Get database connection
    engine = rad.engine()
    
    # Fetch recent SMA data (last 30 days for simplicity)
    end_date = datetime.now().strftime('%Y-%m-%d')
    start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
    
    print(f"Fetching SMA data from {start_date} to {end_date}...")
    sma_data = sma50_scanner.fetch_counts(engine, start=start_date, end=end_date)
    
    if sma_data.empty:
        print("❌ No SMA data found!")
        return
    
    print(f"✅ Loaded {len(sma_data)} days of SMA data")
    
    # Create simple plot
    fig, ax = plt.subplots(figsize=(10, 6))
    
    # Plot data
    dates = sma_data['trade_date']
    line = ax.plot(dates, sma_data['above_count'], 
                   label='Above 50 SMA', color='green', 
                   linewidth=2, marker='o', markersize=6)
    
    # Add debug tooltip
    if CURSORS_AVAILABLE:
        # Create copies for closure
        dates_copy = dates.copy()
        above_counts = sma_data['above_count'].copy()
        
        def debug_tooltip(sel):
            print(f"\n=== TOOLTIP DEBUG ===")
            print(f"sel.target type: {type(sel.target)}")
            print(f"sel.target.index type: {type(sel.target.index)}")
            print(f"sel.target.index value: {sel.target.index}")
            
            try:
                # Try different approaches to get index
                if hasattr(sel.target, 'index'):
                    idx_raw = sel.target.index
                    print(f"Raw index: {idx_raw}")
                    
                    if isinstance(idx_raw, (int, float)):
                        idx = int(idx_raw)
                        print(f"Converted index: {idx}")
                    elif hasattr(idx_raw, '__len__') and len(idx_raw) > 0:
                        idx = int(idx_raw[0])
                        print(f"First element index: {idx}")
                    else:
                        print(f"Cannot convert index: {idx_raw}")
                        sel.annotation.set_text(f"Index error: {type(idx_raw)}")
                        return
                
                # Try to access data
                if 0 <= idx < len(dates_copy):
                    date_str = dates_copy.iloc[idx].strftime('%Y-%m-%d')
                    count = int(above_counts.iloc[idx])
                    
                    tooltip_text = f"DEBUG SUCCESS\nIndex: {idx}\nDate: {date_str}\nCount: {count:,}"
                    print(f"Tooltip text: {tooltip_text}")
                    sel.annotation.set_text(tooltip_text)
                else:
                    error_text = f"Index {idx} out of range [0-{len(dates_copy)-1}]"
                    print(f"Range error: {error_text}")
                    sel.annotation.set_text(error_text)
                
            except Exception as e:
                error_text = f"ERROR: {str(e)}"
                print(f"Exception: {error_text}")
                sel.annotation.set_text(error_text)
            
            print("=== END DEBUG ===\n")
        
        cursor = mplcursors.cursor(line[0], hover=True)
        cursor.connect("add", debug_tooltip)
        
        print("\n🎯 Chart created with debug tooltips")
        print("✨ Hover over points to see debug information in console and tooltip")
    
    ax.set_title('Debug: SMA 50 Count Trends with Tooltip Debugging')
    ax.set_ylabel('Number of Stocks Above 50 SMA')
    ax.legend()
    ax.grid(True, alpha=0.3)
    ax.tick_params(axis='x', rotation=45)
    
    plt.tight_layout()
    plt.show()

if __name__ == "__main__":
    debug_tooltip_indexing()