"""
Test the complete PDF dialog with all fixes
"""
import tkinter as tk
from gui.pdf_report_dialog import PDFReportDialog

def test_complete_dialog():
    """Test the PDF dialog completely"""
    root = tk.Tk()
    root.geometry("300x200")
    root.title("Test PDF Dialog")
    
    # Create a button to launch the dialog
    def launch_dialog():
        dialog_instance = PDFReportDialog(root)
        dialog_instance.show_dialog()
    
    launch_btn = tk.Button(root, text="Launch PDF Dialog", command=launch_dialog)
    launch_btn.pack(pady=50)
    
    instructions = tk.Label(root, text="Click button to test PDF dialog.\nCheck that:\n- Sectors are loaded\n- Browse button works\n- Select/Clear All work")
    instructions.pack()
    
    root.mainloop()

if __name__ == "__main__":
    test_complete_dialog()