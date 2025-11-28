"""
Simple test to check sector loading and browse functionality
"""
import tkinter as tk
from tkinter import filedialog
from services.reports.pdf_report_generator import PDFReportGenerator

def test_sector_loading():
    """Test sector loading directly"""
    print("Testing sector loading...")
    
    try:
        generator = PDFReportGenerator()
        sectors = generator.get_available_sectors()
        print(f"Found {len(sectors)} sectors:")
        for i, sector in enumerate(sectors[:10]):  # Show first 10
            print(f"  {i+1}. {sector}")
        
        if len(sectors) > 10:
            print(f"  ... and {len(sectors) - 10} more")
            
    except Exception as e:
        print(f"Error loading sectors: {e}")
        import traceback
        traceback.print_exc()

def test_file_dialog():
    """Test file dialog functionality"""
    print("\nTesting file dialog...")
    
    root = tk.Tk()
    root.withdraw()  # Hide the main window
    
    try:
        filename = filedialog.asksaveasfilename(
            title="Save PDF Report As",
            defaultextension=".pdf",
            filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")],
            initialfile="test_report.pdf"
        )
        
        if filename:
            print(f"Selected file: {filename}")
        else:
            print("No file selected")
            
    except Exception as e:
        print(f"Error with file dialog: {e}")
        import traceback
        traceback.print_exc()
    
    root.destroy()

if __name__ == "__main__":
    test_sector_loading()
    test_file_dialog()