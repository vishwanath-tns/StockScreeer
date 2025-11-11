#!/usr/bin/env python3
"""Test the asynchronous dashboard loading."""

import tkinter as tk
from gui.tabs.dashboard import DashboardTab
import time

def test_async_dashboard():
    """Test that dashboard loads quickly without blocking."""
    root = tk.Tk()
    root.title("Dashboard Async Test")
    root.geometry("800x600")
    
    start_time = time.time()
    
    try:
        # This should return quickly now
        dashboard = DashboardTab(root)
        
        load_time = time.time() - start_time
        print(f"✅ Dashboard loaded in {load_time:.2f} seconds")
        
        if load_time < 1.0:
            print("🚀 FAST LOADING: Dashboard loads in under 1 second!")
        elif load_time < 3.0:
            print("✅ GOOD: Dashboard loads in reasonable time")
        else:
            print("⚠️  SLOW: Dashboard took longer than expected")
        
        # Let the dashboard run for a few seconds to see background loading
        print("🔄 Letting dashboard run for 5 seconds to observe background loading...")
        root.after(5000, root.quit)  # Auto-quit after 5 seconds
        root.mainloop()
        
    except Exception as e:
        print(f"❌ Error testing dashboard: {e}")
        import traceback
        traceback.print_exc()
    finally:
        try:
            root.destroy()
        except:
            pass

if __name__ == "__main__":
    test_async_dashboard()