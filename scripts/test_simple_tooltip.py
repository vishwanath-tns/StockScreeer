"""
Simple test to find the correct mplcursors API for getting data point indices.
"""

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

def test_simple_tooltip():
    """Test with simple numeric data first."""
    # Create simple test data
    x = np.arange(10)
    y = np.random.random(10)
    
    fig, ax = plt.subplots()
    line = ax.plot(x, y, 'o-', markersize=8)
    
    def tooltip_callback(sel):
        print(f"\n=== TOOLTIP DEBUG ===")
        print(f"sel attributes: {dir(sel)}")
        print(f"sel.target: {sel.target}")
        print(f"sel.target type: {type(sel.target)}")
        
        if hasattr(sel, 'index'):
            print(f"sel.index: {sel.index}")
        
        if hasattr(sel, 'artist'):
            print(f"sel.artist: {sel.artist}")
            print(f"sel.artist type: {type(sel.artist)}")
        
        # Try to get actual index
        try:
            # This is the correct approach for mplcursors
            data_idx = sel.target.index if hasattr(sel.target, 'index') else None
            print(f"data_idx from target.index: {data_idx}")
        except:
            print("No target.index")
            
        try:
            # Alternative approach
            line_data = sel.artist.get_xydata()
            print(f"line_data shape: {line_data.shape}")
            print(f"sel.target coordinates: {sel.target}")
            
            # Find closest point
            distances = np.sqrt((line_data[:, 0] - sel.target[0])**2 + (line_data[:, 1] - sel.target[1])**2)
            closest_idx = np.argmin(distances)
            print(f"closest index by distance: {closest_idx}")
            
            sel.annotation.set_text(f"Point {closest_idx}\nX: {x[closest_idx]:.1f}\nY: {y[closest_idx]:.3f}")
            
        except Exception as e:
            print(f"Error in tooltip: {e}")
            sel.annotation.set_text("Error")
        
        print("=== END DEBUG ===\n")
    
    cursor = mplcursors.cursor(line[0], hover=True)
    cursor.connect("add", tooltip_callback)
    
    ax.set_title('Simple Tooltip Test - Hover over points')
    ax.grid(True)
    
    print("\n🎯 Chart created - hover over points to see debug output")
    plt.show()

if __name__ == "__main__":
    test_simple_tooltip()