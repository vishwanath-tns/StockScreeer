"""
PDF Report Dialog for Scanner GUI
===============================

Provides a user interface for generating customizable PDF reports
with options for duration, sector filtering, and report parameters.
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from datetime import datetime
from typing import List, Optional
import threading
import os
import sys

# Add project path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from services.reports.pdf_report_generator import PDFReportGenerator
    PDF_GENERATOR_AVAILABLE = True
except ImportError as e:
    print(f"PDF Generator not available: {e}")
    PDF_GENERATOR_AVAILABLE = False

class PDFReportDialog:
    """
    Dialog for configuring and generating PDF reports
    """
    
    def __init__(self, parent):
        self.parent = parent
        self.generator = PDFReportGenerator() if PDF_GENERATOR_AVAILABLE else None
        self.dialog = None
        self.progress_var = tk.StringVar(value="Ready to generate report")
        
        # Options
        self.selected_durations = []
        self.selected_sectors = []
        self.top_n_var = tk.IntVar(value=10)
        self.include_charts_var = tk.BooleanVar(value=True)
        self.output_path_var = tk.StringVar(value="")
        
    def show_dialog(self):
        """Show the PDF report configuration dialog"""
        if not PDF_GENERATOR_AVAILABLE:
            messagebox.showerror("Error", "PDF generation not available. Please install reportlab: pip install reportlab")
            return
            
        self.dialog = tk.Toplevel(self.parent)
        self.dialog.title("Generate Nifty 500 PDF Report")
        self.dialog.geometry("600x700")
        self.dialog.resizable(True, True)
        
        # Make dialog modal
        self.dialog.transient(self.parent)
        self.dialog.grab_set()
        
        self._create_widgets()
        self._load_initial_data()
        
        # Center dialog
        self.dialog.update_idletasks()
        x = (self.dialog.winfo_screenwidth() // 2) - (self.dialog.winfo_width() // 2)
        y = (self.dialog.winfo_screenheight() // 2) - (self.dialog.winfo_height() // 2)
        self.dialog.geometry(f"+{x}+{y}")
    
    def _create_widgets(self):
        """Create dialog widgets"""
        main_frame = ttk.Frame(self.dialog, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        self.dialog.columnconfigure(0, weight=1)
        self.dialog.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        
        row = 0
        
        # Title
        title_label = ttk.Label(main_frame, text="Nifty 500 Momentum PDF Report Generator", 
                               font=('Arial', 12, 'bold'))
        title_label.grid(row=row, column=0, columnspan=2, pady=(0, 15), sticky=tk.W)
        row += 1
        
        # Duration selection
        ttk.Label(main_frame, text="Select Duration(s):", font=('Arial', 10, 'bold')).grid(
            row=row, column=0, sticky=tk.W, pady=(0, 5))
        row += 1
        
        duration_frame = ttk.LabelFrame(main_frame, text="Timeframes (Higher TF first)", padding="5")
        duration_frame.grid(row=row, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        duration_frame.columnconfigure(0, weight=1)
        row += 1
        
        # Duration checkboxes
        durations = [('12M', 'Twelve Months'), ('9M', 'Nine Months'), ('6M', 'Six Months'),
                    ('3M', 'Three Months'), ('1M', 'One Month'), ('1W', 'One Week')]
        
        self.duration_vars = {}
        duration_row = 0
        for i, (duration, label) in enumerate(durations):
            col = i % 3
            if col == 0 and i > 0:
                duration_row += 1
                
            var = tk.BooleanVar(value=True)  # Default all selected
            self.duration_vars[duration] = var
            
            cb = ttk.Checkbutton(duration_frame, text=f"{duration} ({label})", variable=var,
                               command=self._update_duration_selection)
            cb.grid(row=duration_row, column=col, sticky=tk.W, padx=5, pady=2)
        
        # Sector selection
        ttk.Label(main_frame, text="Select Sector(s):", font=('Arial', 10, 'bold')).grid(
            row=row, column=0, sticky=tk.W, pady=(10, 5))
        row += 1
        
        sector_frame = ttk.LabelFrame(main_frame, text="Sectors (Leave blank for all)", padding="5")
        sector_frame.grid(row=row, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        sector_frame.columnconfigure(0, weight=1)
        row += 1
        
        # Sector listbox with scrollbar
        sector_list_frame = ttk.Frame(sector_frame)
        sector_list_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=5)
        sector_list_frame.columnconfigure(0, weight=1)
        sector_frame.rowconfigure(0, weight=1)
        
        self.sector_listbox = tk.Listbox(sector_list_frame, selectmode=tk.MULTIPLE, height=6)
        sector_scrollbar = ttk.Scrollbar(sector_list_frame, orient=tk.VERTICAL, command=self.sector_listbox.yview)
        self.sector_listbox.configure(yscrollcommand=sector_scrollbar.set)
        
        self.sector_listbox.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        sector_scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        sector_list_frame.rowconfigure(0, weight=1)
        
        # Sector selection buttons
        sector_btn_frame = ttk.Frame(sector_frame)
        sector_btn_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=5)
        
        ttk.Button(sector_btn_frame, text="Select All", command=self._select_all_sectors).pack(side=tk.LEFT, padx=5)
        ttk.Button(sector_btn_frame, text="Clear All", command=self._clear_all_sectors).pack(side=tk.LEFT, padx=5)
        
        # Report parameters
        ttk.Label(main_frame, text="Report Parameters:", font=('Arial', 10, 'bold')).grid(
            row=row, column=0, sticky=tk.W, pady=(10, 5))
        row += 1
        
        param_frame = ttk.LabelFrame(main_frame, text="Customize Report", padding="5")
        param_frame.grid(row=row, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        row += 1
        
        # Top N selection
        ttk.Label(param_frame, text="Top N Gainers/Losers:").grid(row=0, column=0, sticky=tk.W, pady=2)
        top_n_spinbox = ttk.Spinbox(param_frame, from_=5, to=50, textvariable=self.top_n_var, width=10)
        top_n_spinbox.grid(row=0, column=1, sticky=tk.W, padx=(10, 0), pady=2)
        
        # Include charts checkbox
        ttk.Checkbutton(param_frame, text="Include analysis charts", 
                       variable=self.include_charts_var).grid(row=1, column=0, columnspan=2, sticky=tk.W, pady=5)
        
        # Output file selection
        ttk.Label(main_frame, text="Output File:", font=('Arial', 10, 'bold')).grid(
            row=row, column=0, sticky=tk.W, pady=(10, 5))
        row += 1
        
        output_frame = ttk.Frame(main_frame)
        output_frame.grid(row=row, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        output_frame.columnconfigure(0, weight=1)
        row += 1
        
        self.output_entry = ttk.Entry(output_frame, textvariable=self.output_path_var)
        self.output_entry.grid(row=0, column=0, sticky=(tk.W, tk.E), padx=(0, 5))
        
        ttk.Button(output_frame, text="Browse...", command=self._browse_output_file).grid(row=0, column=1)
        
        # Progress and status
        ttk.Label(main_frame, text="Status:", font=('Arial', 10, 'bold')).grid(
            row=row, column=0, sticky=tk.W, pady=(10, 5))
        row += 1
        
        self.progress_label = ttk.Label(main_frame, textvariable=self.progress_var, foreground="blue")
        self.progress_label.grid(row=row, column=0, columnspan=2, sticky=tk.W)
        row += 1
        
        self.progress_bar = ttk.Progressbar(main_frame, mode='indeterminate')
        self.progress_bar.grid(row=row, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)
        row += 1
        
        # Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=row, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(15, 0))
        
        ttk.Button(button_frame, text="Generate Report", command=self._generate_report).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Preview Settings", command=self._preview_settings).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Close", command=self._close_dialog).pack(side=tk.RIGHT, padx=5)
        
        # Set default output file
        default_filename = f"nifty500_momentum_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        self.output_path_var.set(default_filename)
    
    def _load_initial_data(self):
        """Load initial data (sectors)"""
        if not self.generator:
            return
            
        try:
            # Load sectors in background
            threading.Thread(target=self._load_sectors, daemon=True).start()
        except Exception as e:
            print(f"Error loading initial data: {e}")
    
    def _load_sectors(self):
        """Load available sectors"""
        try:
            sectors = self.generator.get_available_sectors()
            
            # Update UI in main thread
            self.dialog.after(0, lambda: self._populate_sectors(sectors))
        except Exception as e:
            self.dialog.after(0, lambda: self._show_error(f"Error loading sectors: {e}"))
    
    def _populate_sectors(self, sectors):
        """Populate sector listbox"""
        self.sector_listbox.delete(0, tk.END)
        for sector in sectors:
            self.sector_listbox.insert(tk.END, sector)
    
    def _update_duration_selection(self):
        """Update selected durations"""
        self.selected_durations = [duration for duration, var in self.duration_vars.items() if var.get()]
    
    def _select_all_sectors(self):
        """Select all sectors"""
        self.sector_listbox.select_set(0, tk.END)
    
    def _clear_all_sectors(self):
        """Clear all sector selections"""
        self.sector_listbox.selection_clear(0, tk.END)
    
    def _browse_output_file(self):
        """Browse for output file location"""
        filename = filedialog.asksaveasfilename(
            title="Save PDF Report As",
            defaultextension=".pdf",
            filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")],
            initialfile=f"nifty500_momentum_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        )
        
        if filename:
            self.output_path_var.set(filename)
    
    def _preview_settings(self):
        """Show preview of current settings"""
        selected_sectors = [self.sector_listbox.get(i) for i in self.sector_listbox.curselection()]
        selected_durations = [duration for duration, var in self.duration_vars.items() if var.get()]
        
        preview_text = f"""Report Settings Preview:

Durations: {', '.join(selected_durations) if selected_durations else 'None selected'}
Sectors: {', '.join(selected_sectors) if selected_sectors else 'All sectors'}
Top N: {self.top_n_var.get()}
Include Charts: {self.include_charts_var.get()}
Output File: {self.output_path_var.get()}

Estimated Report Size: {len(selected_durations) * (2 if selected_durations else 12)} pages
"""
        
        messagebox.showinfo("Report Preview", preview_text)
    
    def _generate_report(self):
        """Generate the PDF report"""
        if not self.generator:
            messagebox.showerror("Error", "PDF generator not available")
            return
        
        # Validate selections
        selected_durations = [duration for duration, var in self.duration_vars.items() if var.get()]
        if not selected_durations:
            messagebox.showerror("Error", "Please select at least one duration")
            return
        
        output_path = self.output_path_var.get().strip()
        if not output_path:
            messagebox.showerror("Error", "Please specify an output file")
            return
        
        # Get selected sectors
        selected_sectors = [self.sector_listbox.get(i) for i in self.sector_listbox.curselection()]
        
        # Start progress
        self.progress_var.set("Generating PDF report...")
        self.progress_bar.start()
        
        # Generate report in background thread
        threading.Thread(target=self._generate_report_worker, 
                        args=(selected_durations, selected_sectors, output_path), 
                        daemon=True).start()
    
    def _generate_report_worker(self, durations, sectors, output_path):
        """Worker thread for generating report"""
        try:
            success = self.generator.generate_top_performers_report(
                output_path=output_path,
                top_n=self.top_n_var.get(),
                duration_filter=durations if durations else None,
                sector_filter=sectors if sectors else None,
                include_charts=self.include_charts_var.get()
            )
            
            # Update UI in main thread
            self.dialog.after(0, lambda: self._report_complete(success, output_path))
            
        except Exception as e:
            self.dialog.after(0, lambda: self._report_error(str(e)))
    
    def _report_complete(self, success, output_path):
        """Handle report completion"""
        self.progress_bar.stop()
        
        if success:
            self.progress_var.set("Report generated successfully!")
            messagebox.showinfo("Success", f"PDF report generated successfully!\n\nFile: {output_path}")
            
            # Ask if user wants to open the file
            if messagebox.askyesno("Open Report", "Would you like to open the report now?"):
                try:
                    import subprocess
                    import platform
                    
                    if platform.system() == 'Darwin':       # macOS
                        subprocess.call(('open', output_path))
                    elif platform.system() == 'Windows':   # Windows
                        os.startfile(output_path)
                    else:                                   # linux variants
                        subprocess.call(('xdg-open', output_path))
                except Exception as e:
                    messagebox.showerror("Error", f"Could not open file: {e}")
        else:
            self.progress_var.set("Report generation failed!")
            messagebox.showerror("Error", "Failed to generate PDF report. Check the console for details.")
    
    def _report_error(self, error_msg):
        """Handle report generation error"""
        self.progress_bar.stop()
        self.progress_var.set("Error occurred during report generation")
        messagebox.showerror("Error", f"Report generation failed:\n{error_msg}")
    
    def _show_error(self, message):
        """Show error message"""
        messagebox.showerror("Error", message)
    
    def _close_dialog(self):
        """Close the dialog"""
        if self.dialog:
            self.dialog.destroy()

def create_pdf_report_button(parent, **kwargs):
    """
    Create a button that opens the PDF report dialog
    """
    def open_pdf_dialog():
        dialog = PDFReportDialog(parent)
        dialog.show_dialog()
    
    button = ttk.Button(parent, text="Generate PDF Report", command=open_pdf_dialog, **kwargs)
    return button

# Test the dialog standalone
if __name__ == "__main__":
    root = tk.Tk()
    root.title("PDF Report Test")
    root.geometry("300x200")
    
    # Create test button
    test_button = create_pdf_report_button(root)
    test_button.pack(pady=50)
    
    root.mainloop()