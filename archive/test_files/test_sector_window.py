"""
Simple test for sector detail window functionality
"""
import tkinter as tk
import sys
import os

# Add paths
sys.path.append('.')

def test_sector_window():
    """Test the sector detail window creation."""
    try:
        from gui.windows.sector_detail_window import SectorDetailWindow
        from datetime import date
        
        # Create test root
        root = tk.Tk()
        root.withdraw()  # Hide the test root
        
        print("Testing SectorDetailWindow creation...")
        
        # Test window creation (without actually showing it)
        test_date = date(2025, 11, 14)
        window = SectorDetailWindow(root, 'NIFTY-BANK', test_date)
        
        print("SUCCESS: SectorDetailWindow created successfully")
        print("Window title:", window.window.title())
        print("Window size:", window.window.winfo_reqwidth(), "x", window.window.winfo_reqheight())
        
        # Clean up
        window.window.destroy()
        root.destroy()
        
        return True
        
    except Exception as e:
        print("ERROR:", str(e))
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("Testing Sector Detail Window...")
    if test_sector_window():
        print("Test PASSED: Ready for use in GUI")
    else:
        print("Test FAILED: Need to fix issues")