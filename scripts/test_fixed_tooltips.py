"""
Test the fixed dashboard tooltip implementation.
"""

import sys
import os
sys.path.append(os.path.dirname(__file__))

import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

try:
    import mplcursors
    print("✅ mplcursors available")
except ImportError:
    print("❌ mplcursors not available")
    exit()

# Import our modules
import reporting_adv_decl as rad
import sma50_scanner

def test_fixed_tooltips():
    """Test the fixed dashboard tooltip approach."""
    print("\n=== Testing Fixed Dashboard Tooltips ===")
    
    # Get database connection
    engine = rad.engine()
    
    # Fetch recent SMA data
    end_date = datetime.now().strftime('%Y-%m-%d')
    start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
    
    print(f"Fetching SMA data from {start_date} to {end_date}...")
    sma_data = sma50_scanner.fetch_counts(engine, start=start_date, end=end_date)
    
    if sma_data.empty:
        print("❌ No SMA data found!")
        return
    
    print(f"✅ Loaded {len(sma_data)} days of SMA data")
    
    # Create plot exactly like dashboard
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8))
    
    # Plot 1: Count trends (same as dashboard)
    dates = sma_data['trade_date']
    line1 = ax1.plot(dates, sma_data['above_count'], label='Above 50 SMA', color='green', linewidth=2, marker='o', markersize=4)
    line2 = ax1.plot(dates, sma_data['below_count'], label='Below 50 SMA', color='red', linewidth=2, marker='o', markersize=4)
    ax1.fill_between(dates, sma_data['above_count'], alpha=0.3, color='green')
    ax1.fill_between(dates, sma_data['below_count'], alpha=0.3, color='red')
    
    # Add tooltips using the FIXED approach
    dates_copy = dates.copy()
    above_counts = sma_data['above_count'].copy()
    below_counts = sma_data['below_count'].copy()
    
    def format_tooltip_above(sel):
        try:
            # Find the closest data point index by distance calculation
            line_data = sel.artist.get_xydata()
            distances = np.sqrt((line_data[:, 0] - sel.target[0])**2 + (line_data[:, 1] - sel.target[1])**2)
            closest_idx = np.argmin(distances)
            
            # Get the data for this index
            date_str = dates_copy.iloc[closest_idx].strftime('%Y-%m-%d')
            count = int(above_counts.iloc[closest_idx])
            tooltip_text = f"Date: {date_str}\nAbove 50 SMA: {count:,} stocks"
            
            print(f"ABOVE TOOLTIP: idx={closest_idx}, date={date_str}, count={count}")
            sel.annotation.set_text(tooltip_text)
        except Exception as e:
            print(f"Tooltip error (above): {e}")
            sel.annotation.set_text(f"Error: {str(e)}")
    
    def format_tooltip_below(sel):
        try:
            # Find the closest data point index by distance calculation  
            line_data = sel.artist.get_xydata()
            distances = np.sqrt((line_data[:, 0] - sel.target[0])**2 + (line_data[:, 1] - sel.target[1])**2)
            closest_idx = np.argmin(distances)
            
            # Get the data for this index
            date_str = dates_copy.iloc[closest_idx].strftime('%Y-%m-%d')
            count = int(below_counts.iloc[closest_idx])
            tooltip_text = f"Date: {date_str}\nBelow 50 SMA: {count:,} stocks"
            
            print(f"BELOW TOOLTIP: idx={closest_idx}, date={date_str}, count={count}")
            sel.annotation.set_text(tooltip_text)
        except Exception as e:
            print(f"Tooltip error (below): {e}")
            sel.annotation.set_text(f"Error: {str(e)}")
    
    # Connect tooltips
    cursor1 = mplcursors.cursor(line1[0], hover=True)
    cursor1.connect("add", format_tooltip_above)
    
    cursor2 = mplcursors.cursor(line2[0], hover=True)
    cursor2.connect("add", format_tooltip_below)
    
    ax1.set_title('Fixed Dashboard Tooltips Test - SMA Count Trends')
    ax1.set_ylabel('Number of Stocks')
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    ax1.tick_params(axis='x', rotation=45)
    
    # Plot 2: Percentage chart
    line3 = ax2.plot(dates, sma_data['pct_above'], label='% Above 50 SMA', color='blue', linewidth=2, marker='o', markersize=4)
    ax2.fill_between(dates, sma_data['pct_above'], alpha=0.2, color='blue')
    
    def format_tooltip_percentage(sel):
        try:
            # Find the closest data point index by distance calculation
            line_data = sel.artist.get_xydata()
            distances = np.sqrt((line_data[:, 0] - sel.target[0])**2 + (line_data[:, 1] - sel.target[1])**2)
            closest_idx = np.argmin(distances)
            
            # Get the data for this index
            date_str = dates_copy.iloc[closest_idx].strftime('%Y-%m-%d')
            pct = float(sma_data['pct_above'].iloc[closest_idx])
            above = int(sma_data['above_count'].iloc[closest_idx])
            below = int(sma_data['below_count'].iloc[closest_idx])
            total = int(sma_data['total_count'].iloc[closest_idx])
            tooltip_text = (f"Date: {date_str}\n"
                           f"Above 50 SMA: {pct:.1f}%\n"
                           f"Above: {above:,} stocks\n"
                           f"Below: {below:,} stocks\n"
                           f"Total: {total:,} stocks")
            
            print(f"PERCENT TOOLTIP: idx={closest_idx}, date={date_str}, pct={pct:.1f}%")
            sel.annotation.set_text(tooltip_text)
        except Exception as e:
            print(f"Tooltip error (percentage): {e}")
            sel.annotation.set_text(f"Error: {str(e)}")
    
    cursor3 = mplcursors.cursor(line3[0], hover=True)
    cursor3.connect("add", format_tooltip_percentage)
    
    ax2.set_title('Fixed Dashboard Tooltips Test - Market Breadth')
    ax2.set_ylabel('Percentage Above (%)')
    ax2.legend()
    ax2.grid(True, alpha=0.3)
    ax2.tick_params(axis='x', rotation=45)
    
    plt.tight_layout()
    
    print("\n🎯 Chart created with FIXED tooltips")
    print("✨ Hover over points to see actual date and count data!")
    print("💬 Check console for debug output confirming tooltips work")
    plt.show()

if __name__ == "__main__":
    test_fixed_tooltips()