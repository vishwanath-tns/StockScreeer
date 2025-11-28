"""
Test script to debug PDF dialog button issues
"""
import tkinter as tk
from gui.pdf_report_dialog import PDFReportDialog

def test_dialog():
    """Test the PDF dialog with debug output"""
    root = tk.Tk()
    root.withdraw()  # Hide the main window
    
    try:
        dialog = PDFReportDialog(root)
        
        # Test button methods directly
        print("Testing methods directly:")
        
        print("1. Testing _select_all_sectors...")
        try:
            dialog._select_all_sectors()
            print("   ✓ _select_all_sectors works")
        except Exception as e:
            print(f"   ✗ _select_all_sectors error: {e}")
        
        print("2. Testing _clear_all_sectors...")
        try:
            dialog._clear_all_sectors()
            print("   ✓ _clear_all_sectors works")
        except Exception as e:
            print(f"   ✗ _clear_all_sectors error: {e}")
        
        print("3. Testing _browse_output_file...")
        try:
            # Just test that it can be called (will open file dialog)
            print("   Calling _browse_output_file (may open file dialog)...")
            dialog._browse_output_file()
            print("   ✓ _browse_output_file called successfully")
        except Exception as e:
            print(f"   ✗ _browse_output_file error: {e}")
        
        print("\n4. Checking if dialog displays correctly...")
        dialog.transient(root)
        dialog.grab_set()
        
        # Keep dialog open for testing
        print("Dialog should be visible now. Test the buttons manually.")
        print("Press Enter in console to close...")
        input()
        
        dialog.destroy()
        
    except Exception as e:
        print(f"Error creating dialog: {e}")
        import traceback
        traceback.print_exc()
    
    root.quit()
    root.destroy()

if __name__ == "__main__":
    test_dialog()