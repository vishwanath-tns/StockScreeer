"""
Simple test for PDF dialog buttons after fixes
"""
import tkinter as tk
from gui.pdf_report_dialog import PDFReportDialog

def test_dialog_after_show():
    """Test the PDF dialog buttons after showing dialog"""
    root = tk.Tk()
    root.withdraw()  # Hide the main window
    
    try:
        dialog_instance = PDFReportDialog(root)
        
        # Show the dialog first (this creates all widgets)
        dialog_instance.show_dialog()
        
        # Now test the methods after the dialog is shown
        print("Testing methods after show_dialog():")
        
        print("1. Testing _select_all_sectors...")
        try:
            dialog_instance._select_all_sectors()
            print("   ✓ _select_all_sectors works")
        except Exception as e:
            print(f"   ✗ _select_all_sectors error: {e}")
        
        print("2. Testing _clear_all_sectors...")
        try:
            dialog_instance._clear_all_sectors()
            print("   ✓ _clear_all_sectors works")
        except Exception as e:
            print(f"   ✗ _clear_all_sectors error: {e}")
        
        print("\n3. Dialog shown successfully. Test buttons manually...")
        print("Close dialog window to continue...")
        
        # Wait for dialog to be closed
        dialog_instance.dialog.wait_window()
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    
    root.quit()
    root.destroy()

if __name__ == "__main__":
    test_dialog_after_show()