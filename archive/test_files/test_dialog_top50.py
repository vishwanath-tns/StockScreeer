"""
Test the dialog with top_n = 50 to verify it works end-to-end
"""
import tkinter as tk
from gui.pdf_report_dialog import PDFReportDialog

def test_dialog_with_top50():
    """Test dialog specifically with top 50"""
    root = tk.Tk()
    root.geometry("400x300")
    root.title("Test Top 50 Dialog")
    
    def launch_dialog():
        dialog_instance = PDFReportDialog(root)
        dialog_instance.show_dialog()
        
        # Pre-set the top_n to 50 for testing
        dialog_instance.top_n_var.set(50)
    
    tk.Label(root, text="Test PDF Dialog with Top 50", font=('Arial', 14, 'bold')).pack(pady=20)
    tk.Label(root, text="1. Click 'Launch Dialog'\n2. Select 'Nifty MidSmall Healthcare'\n3. Set Top N to 50\n4. Generate report\n5. Check that tables show 50 entries", 
             justify=tk.LEFT).pack(pady=20)
    
    tk.Button(root, text="Launch Dialog", command=launch_dialog, font=('Arial', 12)).pack(pady=20)
    
    root.mainloop()

if __name__ == "__main__":
    test_dialog_with_top50()