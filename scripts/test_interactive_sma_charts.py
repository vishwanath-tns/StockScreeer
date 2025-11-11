"""
Test script to demonstrate the new interactive SMA 50 charts with hover tooltips.

This script shows how the enhanced charts work:
1. Hover over any point on the charts to see detailed information
2. Date and exact counts are displayed in tooltips
3. Works for both the count trends chart and percentage chart
"""

import sys
import os
sys.path.append(os.path.dirname(__file__))

import matplotlib.pyplot as plt
import pandas as pd
from datetime import datetime, timedelta

def format_tooltip_above(sel, dates, above_counts):
    """Format tooltip for above SMA 50 chart with error handling."""
    try:
        idx = int(sel.target.index)
        date_str = dates.iloc[idx].strftime('%Y-%m-%d')
        count_val = above_counts.iloc[idx]
        return f"Date: {date_str}\nAbove 50 SMA: {count_val:,} stocks"
    except (AttributeError, IndexError, TypeError):
        return "Date: N/A\nAbove 50 SMA: N/A"

def format_tooltip_below(sel, dates, below_counts):
    """Format tooltip for below SMA 50 chart with error handling."""
    try:
        idx = int(sel.target.index)
        date_str = dates.iloc[idx].strftime('%Y-%m-%d')
        count_val = below_counts.iloc[idx]
        return f"Date: {date_str}\nBelow 50 SMA: {count_val:,} stocks"
    except (AttributeError, IndexError, TypeError):
        return "Date: N/A\nBelow 50 SMA: N/A"

def format_tooltip_percentage(sel, dates, sma_data):
    """Format tooltip for percentage chart with error handling."""
    try:
        idx = int(sel.target.index)
        date_str = dates.iloc[idx].strftime('%Y-%m-%d')
        pct_above = sma_data['pct_above'].iloc[idx]
        above_count = sma_data['above_count'].iloc[idx]
        below_count = sma_data['below_count'].iloc[idx]
        total_count = sma_data['total_count'].iloc[idx]
        return (f"Date: {date_str}\n"
                f"Above 50 SMA: {pct_above:.1f}%\n"
                f"Above: {above_count:,} stocks\n"
                f"Below: {below_count:,} stocks\n"
                f"Total: {total_count:,} stocks")
    except (AttributeError, IndexError, TypeError):
        return "Date: N/A\nData: N/A"
try:
    import mplcursors
    CURSORS_AVAILABLE = True
    print("✅ mplcursors available - interactive tooltips enabled")
except ImportError:
    CURSORS_AVAILABLE = False
    print("❌ mplcursors not available - install with: pip install mplcursors")

# Import our modules
import reporting_adv_decl as rad
import sma50_scanner

def test_interactive_charts():
    """Test the interactive SMA 50 charts with hover functionality."""
    print("\n=== Testing Interactive SMA 50 Charts ===")
    
    # Get database connection
    engine = rad.engine()
    
    # Fetch recent SMA data
    end_date = datetime.now().strftime('%Y-%m-%d')
    start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')  # Last 30 days
    
    print(f"Fetching SMA data from {start_date} to {end_date}...")
    sma_data = sma50_scanner.fetch_counts(engine, start=start_date, end=end_date)
    
    if sma_data.empty:
        print("❌ No SMA data found!")
        return
    
    print(f"✅ Loaded {len(sma_data)} days of SMA data")
    
    # Create figure
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8))
    
    # Plot 1: Count trends with interactive tooltips
    dates = sma_data['trade_date']
    line1 = ax1.plot(dates, sma_data['above_count'], 
                     label='Above 50 SMA', color='green', 
                     linewidth=2, marker='o', markersize=6)
    line2 = ax1.plot(dates, sma_data['below_count'], 
                     label='Below 50 SMA', color='red', 
                     linewidth=2, marker='o', markersize=6)
    
    # Add fill areas
    ax1.fill_between(dates, sma_data['above_count'], alpha=0.3, color='green')
    ax1.fill_between(dates, sma_data['below_count'], alpha=0.3, color='red')
    
    # Interactive tooltips for count trends
    if CURSORS_AVAILABLE:
        cursor1 = mplcursors.cursor(line1, hover=True)
        cursor1.connect("add", lambda sel: sel.annotation.set_text(
            format_tooltip_above(sel, dates, sma_data['above_count'])
        ))
        
        cursor2 = mplcursors.cursor(line2, hover=True)
        cursor2.connect("add", lambda sel: sel.annotation.set_text(
            format_tooltip_below(sel, dates, sma_data['below_count'])
        ))
    
    ax1.set_title('Interactive SMA 50 Count Trends', fontweight='bold', fontsize=14)
    ax1.set_ylabel('Number of Stocks')
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    ax1.tick_params(axis='x', rotation=45)
    
    # Plot 2: Percentage with interactive tooltips  
    ax2_twin = ax2.twinx()
    
    line3 = ax2.plot(dates, sma_data['pct_above'], 
                     label='% Above 50 SMA', color='blue', 
                     linewidth=2, marker='o', markersize=6)
    ax2.fill_between(dates, sma_data['pct_above'], alpha=0.2, color='blue')
    
    # Interactive tooltips for percentage chart
    if CURSORS_AVAILABLE:
        cursor3 = mplcursors.cursor(line3, hover=True)
        cursor3.connect("add", lambda sel: sel.annotation.set_text(
            format_tooltip_percentage(sel, dates, sma_data)
        ))
    
    # Total count bars
    bars = ax2_twin.bar(dates, sma_data['total_count'], alpha=0.6, color='gray', width=1)
    
    ax2.set_title('Interactive Market Breadth Analysis', fontweight='bold', fontsize=14)
    ax2.set_ylabel('Percentage Above (%)', color='blue')
    ax2_twin.set_ylabel('Total Stocks Analyzed', color='gray')
    ax2.legend()
    ax2.grid(True, alpha=0.3)
    ax2.tick_params(axis='x', rotation=45)
    
    # Add instruction text
    if CURSORS_AVAILABLE:
        fig.suptitle('💡 Hover over any chart point to see detailed data!', fontsize=16, fontweight='bold')
    else:
        fig.suptitle('Install mplcursors for interactive hover tooltips', fontsize=16)
    
    plt.tight_layout()
    
    # Show sample data
    print("\n📊 Sample of recent data:")
    print("Date\t\tAbove\tBelow\tTotal\t% Above")
    print("-" * 50)
    for _, row in sma_data.tail(5).iterrows():
        print(f"{row['trade_date']}\t{row['above_count']}\t{row['below_count']}\t{row['total_count']}\t{row['pct_above']:.1f}%")
    
    print(f"\n🎯 Now showing interactive chart...")
    print("✨ Hover over chart points to see detailed tooltips with dates and counts!")
    plt.show()

if __name__ == "__main__":
    test_interactive_charts()