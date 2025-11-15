"""
Final test for the double-click sector detail window fix
"""
import tkinter as tk
from tkinter import ttk
from datetime import date

# Simulate the exact structure as in scanner_gui
class MockScannerGUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Mock Scanner GUI")
        self.root.geometry("800x600")
        
        # Create notebook (like in scanner_gui)
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True)
        
        # Create market breadth frame
        self.breadth_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.breadth_frame, text="Market Breadth")
        
        # Create MarketBreadthTab-like class
        self.market_breadth_tab = MockMarketBreadthTab(self.breadth_frame)

class MockMarketBreadthTab:
    def __init__(self, parent):
        self.parent = parent
        
        # Create main frame
        self.main_frame = ttk.Frame(parent)
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Create comparison tree
        columns = ('Sector', 'Total Stocks', 'Bullish %', 'Bearish %')
        self.comparison_tree = ttk.Treeview(self.main_frame, columns=columns, show='headings')
        
        for col in columns:
            self.comparison_tree.heading(col, text=col)
            self.comparison_tree.column(col, width=120)
        
        # Add test data
        self.comparison_tree.insert('', tk.END, values=('PHARMA', '20', '75.0%', '25.0%'))
        self.comparison_tree.insert('', tk.END, values=('BANK', '12', '66.7%', '33.3%'))
        
        self.comparison_tree.pack(fill=tk.BOTH, expand=True)
        
        # Bind double-click
        self.comparison_tree.bind('<Double-1>', self.on_sector_comparison_double_click)
    
    def get_sectoral_analysis_date(self):
        return date(2025, 11, 14)
    
    def on_sector_comparison_double_click(self, event):
        """Test the double-click handler with the new fix"""
        try:
            selection = self.comparison_tree.selection()
            if not selection:
                return
            
            item = self.comparison_tree.item(selection[0])
            if not item['values']:
                return
            
            sector_name = item['values'][0]
            sector_code = f"NIFTY-{sector_name}"
            analysis_date = self.get_sectoral_analysis_date()
            
            print(f"Double-clicked on: {sector_name}")
            print(f"Sector code: {sector_code}")
            print(f"Analysis date: {analysis_date}")
            
            # Test the parent approach
            try:
                print("Testing parent window access...")
                parent_window = self.parent
                print(f"Parent window type: {type(parent_window)}")
                
                # Test import
                print("Testing import...")
                from gui.windows.sector_detail_window import SectorDetailWindow
                print("Import successful!")
                
                # Test window creation
                print("Creating sector detail window...")
                SectorDetailWindow(parent_window, sector_code, analysis_date)
                print("SUCCESS: Sector detail window created!")
                
            except Exception as e:
                print(f"ERROR: {e}")
                import traceback
                traceback.print_exc()
                
        except Exception as outer_e:
            print(f"OUTER ERROR: {outer_e}")
            import traceback
            traceback.print_exc()

def test_double_click_fix():
    """Run the test"""
    print("Testing Double-Click Fix")
    print("=" * 30)
    
    # Create mock GUI
    gui = MockScannerGUI()
    
    # Add instructions
    instructions = tk.Label(gui.root, 
                          text="Double-click any sector row to test the fix", 
                          font=('Arial', 12, 'bold'))
    instructions.pack(pady=10)
    
    print("Mock GUI created. Double-click any sector row to test.")
    print("Close the window when done.")
    
    # Show GUI
    gui.root.mainloop()

if __name__ == "__main__":
    import sys
    sys.path.append('.')
    test_double_click_fix()