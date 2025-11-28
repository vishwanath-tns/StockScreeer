"""
Test the double-click functionality within the scanner GUI context
"""
import sys
import os

# Add the same path as scanner_gui.py would
sys.path.append('.')
sys.path.append('./gui')
sys.path.append('./services')

def test_import_from_gui_context():
    """Test importing SectorDetailWindow from GUI context"""
    print("Testing import from GUI context...")
    
    try:
        # This is exactly how it's imported in market_breadth.py
        from gui.windows.sector_detail_window import SectorDetailWindow
        print("SUCCESS: Import successful")
        return True
    except Exception as e:
        print("ERROR importing:", str(e))
        import traceback
        traceback.print_exc()
        return False

def test_sector_data_retrieval():
    """Test if sector data retrieval works"""
    print("Testing sector data retrieval...")
    
    try:
        from services.market_breadth_service import get_sectoral_breadth
        from datetime import date
        
        result = get_sectoral_breadth('NIFTY-BANK', date(2025, 11, 14))
        if result and result.get('success'):
            print("SUCCESS: Sector data retrieved")
            print("Total stocks:", result.get('total_stocks', 0))
            return True
        else:
            print("ERROR: No data retrieved")
            return False
            
    except Exception as e:
        print("ERROR in data retrieval:", str(e))
        return False

def test_complete_workflow():
    """Test the complete workflow"""
    print("Testing complete workflow...")
    
    if not test_import_from_gui_context():
        return False
        
    if not test_sector_data_retrieval():
        return False
        
    # Test the actual window creation
    try:
        import tkinter as tk
        from gui.windows.sector_detail_window import SectorDetailWindow
        from datetime import date
        
        root = tk.Tk()
        root.withdraw()
        
        window = SectorDetailWindow(root, 'NIFTY-BANK', date(2025, 11, 14))
        print("SUCCESS: Complete workflow working")
        
        # Clean up
        window.window.destroy()
        root.destroy()
        return True
        
    except Exception as e:
        print("ERROR in complete workflow:", str(e))
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("Testing Double-Click Functionality")
    print("=" * 40)
    
    success = test_complete_workflow()
    
    print("=" * 40)
    if success:
        print("RESULT: All tests PASSED - Double-click should work!")
    else:
        print("RESULT: Tests FAILED - Need to investigate")
    
    print("\nTo test in GUI:")
    print("1. Run: python scanner_gui.py")
    print("2. Go to Market Breadth -> Sectoral Analysis")
    print("3. Click 'Compare All Sectors'")
    print("4. Double-click any sector row")