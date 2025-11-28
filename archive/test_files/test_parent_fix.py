"""
Test the parent window fix for the double-click functionality
"""
import tkinter as tk
from tkinter import ttk

def test_parent_window_access():
    """Test different ways to access the parent window"""
    root = tk.Tk()
    root.title("Test Parent Access")
    root.withdraw()
    
    # Simulate MarketBreadthTab structure
    main_frame = ttk.Frame(root)
    main_frame.pack(fill=tk.BOTH, expand=True)
    
    print("Testing parent window access methods:")
    
    # Method 1: Through main_frame.winfo_toplevel()
    try:
        toplevel1 = main_frame.winfo_toplevel()
        print("Method 1 (main_frame.winfo_toplevel()): SUCCESS")
        print(f"  Type: {type(toplevel1)}")
    except Exception as e:
        print(f"Method 1: FAILED - {e}")
    
    # Method 2: Direct parent reference
    try:
        parent = root
        print("Method 2 (direct parent): SUCCESS")
        print(f"  Type: {type(parent)}")
    except Exception as e:
        print(f"Method 2: FAILED - {e}")
    
    root.destroy()
    print("Test completed")

if __name__ == "__main__":
    test_parent_window_access()