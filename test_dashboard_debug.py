#!/usr/bin/env python3
"""
Debug test script for dashboard to identify the exact issue.
"""

import tkinter as tk
from tkinter import ttk
from gui.tabs.dashboard import DashboardTab
import reporting_adv_decl as rad

def test_dashboard():
    """Test dashboard creation and data loading."""
    print("🔍 Starting dashboard debug test...")
    
    try:
        # Create GUI
        root = tk.Tk()
        root.title('Debug Dashboard Test')
        root.geometry('800x600')
        
        print("✅ Root window created")
        
        # Create dashboard
        dashboard = DashboardTab(root)
        print("✅ Dashboard instance created")
        
        # Check if cards exist
        if hasattr(dashboard, 'bhav_card'):
            print("✅ BHAV card exists")
        else:
            print("❌ BHAV card missing")
            
        if hasattr(dashboard, 'sma_card'):
            print("✅ SMA card exists")
        else:
            print("❌ SMA card missing")
            
        if hasattr(dashboard, 'rsi_card'):
            print("✅ RSI card exists")  
        else:
            print("❌ RSI card missing")
            
        if hasattr(dashboard, 'trend_card'):
            print("✅ Trend card exists")
        else:
            print("❌ Trend card missing")
        
        # Test database connection
        engine = rad.engine()
        print("✅ Database engine created")
        
        with engine.connect() as conn:
            print("✅ Database connection established")
            
            # Test data loading
            bhav_result = dashboard.check_bhav_data_with_connection(conn)
            print(f"✅ BHAV data loaded: {bhav_result['status']}")
            
            # Test manual card update
            if hasattr(dashboard, 'bhav_card'):
                try:
                    dashboard.update_status_card(dashboard.bhav_card, bhav_result)
                    print("✅ Manual card update successful")
                except Exception as e:
                    print(f"❌ Manual card update failed: {e}")
        
        # Test refresh method
        print("🔄 Testing refresh method...")
        dashboard.refresh_dashboard()
        print("✅ Refresh method completed")
        
        # Let GUI run for a bit to see the results
        def check_results():
            print("🔍 Checking card states...")
            if hasattr(dashboard, 'bhav_card'):
                status_text = dashboard.bhav_card['status'].cget('text')
                print(f"BHAV card status: '{status_text}'")
                
                details_text = dashboard.bhav_card['details'].cget('text')
                print(f"BHAV card details: '{details_text}'")
            
            root.quit()
        
        # Schedule check after dashboard should be loaded
        root.after(3000, check_results)
        root.mainloop()
        
    except Exception as e:
        import traceback
        print(f"❌ Error: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    test_dashboard()