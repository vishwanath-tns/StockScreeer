#!/usr/bin/env python3
"""
Debug version of scanner_gui.py to catch any silent errors.
"""

import sys
import traceback
import tkinter as tk
from scanner_gui import ScannerGUI

def debug_main():
    """Run the main GUI with enhanced error catching."""
    print("🔍 Starting debug GUI with error catching...")
    
    try:
        # Override the exception handler
        def handle_exception(exc_type, exc_value, exc_traceback):
            print(f"❌ UNCAUGHT EXCEPTION: {exc_type.__name__}: {exc_value}")
            traceback.print_exception(exc_type, exc_value, exc_traceback)
            
        sys.excepthook = handle_exception
        
        # Create GUI
        root = tk.Tk()
        app = ScannerGUI(root)
        
        print("✅ Main GUI created successfully")
        
        # Check dashboard specifically after creation
        def check_dashboard_after_init():
            try:
                print("🔍 Checking dashboard after initialization...")
                
                # Navigate to dashboard tab
                notebook = None
                for child in root.winfo_children():
                    if isinstance(child, tk.Frame):
                        for grandchild in child.winfo_children():
                            if hasattr(grandchild, 'tab'):
                                notebook = grandchild
                                break
                
                if notebook:
                    # Try to select dashboard tab
                    try:
                        notebook.select(0)  # Dashboard should be first tab
                        print("✅ Dashboard tab selected")
                    except Exception as e:
                        print(f"❌ Failed to select dashboard tab: {e}")
                        
                print("🎯 Dashboard check completed")
                        
            except Exception as e:
                print(f"❌ Error checking dashboard: {e}")
                traceback.print_exc()
        
        # Schedule dashboard check
        root.after(1000, check_dashboard_after_init)
        
        # Run the GUI
        root.mainloop()
        
    except Exception as e:
        print(f"❌ Error in main: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    debug_main()