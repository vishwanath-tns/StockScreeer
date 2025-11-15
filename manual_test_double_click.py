"""
Quick manual test for the double-click functionality
Run this to verify everything works before testing in the main GUI
"""

import tkinter as tk
import sys
import os

# Ensure paths are set correctly
sys.path.append('.')
sys.path.append('./gui')

def test_double_click_simulation():
    """Simulate the double-click functionality"""
    print("Simulating double-click functionality...")
    
    # Create a test GUI similar to the market breadth tab
    root = tk.Tk()
    root.title("Test Double-Click")
    root.geometry("600x400")
    
    # Create a treeview similar to comparison_tree
    from tkinter import ttk
    columns = ('Sector', 'Total Stocks', 'Bullish %', 'Bearish %')
    tree = ttk.Treeview(root, columns=columns, show='headings', height=10)
    
    for col in columns:
        tree.heading(col, text=col)
        tree.column(col, width=120)
    
    # Add sample data
    tree.insert('', tk.END, values=('PHARMA', '10', '75.0%', '25.0%'))
    tree.insert('', tk.END, values=('BANK', '12', '66.7%', '33.3%'))
    tree.insert('', tk.END, values=('IT', '15', '60.0%', '40.0%'))
    
    tree.pack(fill=tk.BOTH, expand=True)
    
    # Define the double-click handler
    def on_double_click(event):
        selection = tree.selection()
        if not selection:
            return
        
        item = tree.item(selection[0])
        if not item['values']:
            return
        
        sector_name = item['values'][0]
        sector_code = f"NIFTY-{sector_name}"
        
        print(f"Double-clicked on: {sector_name}")
        print(f"Sector code: {sector_code}")
        
        # Test the sector detail window
        try:
            from gui.windows.sector_detail_window import SectorDetailWindow
            from datetime import date
            SectorDetailWindow(root, sector_code, date(2025, 11, 14))
            print("SUCCESS: Sector detail window opened!")
        except Exception as e:
            print(f"ERROR: {e}")
            import traceback
            traceback.print_exc()
    
    # Bind the double-click
    tree.bind('<Double-1>', on_double_click)
    
    # Instructions
    label = tk.Label(root, text="Double-click any sector row to test the functionality", 
                     font=('Arial', 12, 'bold'))
    label.pack(pady=10)
    
    print("Test window created. Double-click any sector row to test.")
    print("Close the window when done testing.")
    
    root.mainloop()

if __name__ == "__main__":
    test_double_click_simulation()