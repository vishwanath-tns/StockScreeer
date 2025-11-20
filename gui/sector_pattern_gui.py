"""
Sector Pattern Scanner GUI

Provides user interface for:
1. Multi-sector selection with checkboxes
2. Timeframe selection (Daily/Weekly/Monthly)  
3. Pattern scanning and breakout analysis
4. PDF report generation
5. Real-time progress tracking

Author: Stock Screener System
Date: November 2025
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog, scrolledtext
import threading
from datetime import datetime
import os
from typing import List, Dict, Optional, Callable

# Local imports
from services.sector_pattern_scanner import SectorPatternScanner, PatternResult, SectorSummary
from services.sector_report_generator import SectorPatternReportGenerator

class SectorPatternGUI:
    """
    Main GUI class for sector-wise pattern scanning
    """
    
    def __init__(self, parent=None):
        self.parent = parent
        self.scanner = SectorPatternScanner()
        self.report_generator = SectorPatternReportGenerator()
        
        # GUI state
        self.scanning = False
        self.available_sectors = []
        self.sector_vars = {}  # Checkboxes for sector selection
        self.timeframe_vars = {}  # Checkboxes for timeframe selection
        
        # Results storage
        self.current_patterns = []
        self.current_summaries = []
        
        self.setup_gui()
        self.load_sectors()
        
    def setup_gui(self):
        """Setup the main GUI components"""
        if self.parent:
            self.root = tk.Toplevel(self.parent)
            self.root.title("Sector Pattern Scanner")
        else:
            self.root = tk.Tk()
            self.root.title("Sector Pattern Scanner - Standalone")
        
        self.root.geometry("1000x700")
        
        # Create main notebook for tabs
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Setup tabs
        self.setup_scanner_tab()
        self.setup_results_tab()
        self.setup_reports_tab()
        
    def setup_scanner_tab(self):
        """Setup the main scanner configuration tab"""
        # Scanner tab
        scanner_frame = ttk.Frame(self.notebook)
        self.notebook.add(scanner_frame, text="Scanner")
        
        # Create main layout with left panel (controls) and right panel (progress)
        main_paned = ttk.PanedWindow(scanner_frame, orient=tk.HORIZONTAL)
        main_paned.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Left panel - Controls
        left_frame = ttk.Frame(main_paned)
        main_paned.add(left_frame, weight=1)
        
        # Right panel - Progress and status
        right_frame = ttk.Frame(main_paned)
        main_paned.add(right_frame, weight=1)
        
        # === LEFT PANEL - CONTROLS ===
        
        # Sector selection
        sector_label = ttk.Label(left_frame, text="Select Sectors to Analyze:", font=('Arial', 12, 'bold'))
        sector_label.pack(anchor=tk.W, pady=(10, 5))
        
        # Sector selection frame with scrollbar
        sector_container = ttk.Frame(left_frame)
        sector_container.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # Canvas and scrollbar for sectors
        sector_canvas = tk.Canvas(sector_container, height=200)
        sector_scrollbar = ttk.Scrollbar(sector_container, orient=tk.VERTICAL, command=sector_canvas.yview)
        self.sector_scrollable_frame = ttk.Frame(sector_canvas)
        
        self.sector_scrollable_frame.bind(
            "<Configure>",
            lambda e: sector_canvas.configure(scrollregion=sector_canvas.bbox("all"))
        )
        
        sector_canvas.create_window((0, 0), window=self.sector_scrollable_frame, anchor=tk.NW)
        sector_canvas.configure(yscrollcommand=sector_scrollbar.set)
        
        sector_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sector_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Sector selection buttons
        sector_buttons_frame = ttk.Frame(left_frame)
        sector_buttons_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Button(sector_buttons_frame, text="Select All", command=self.select_all_sectors).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(sector_buttons_frame, text="Clear All", command=self.clear_all_sectors).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(sector_buttons_frame, text="Select Major", command=self.select_major_sectors).pack(side=tk.LEFT)
        
        # Timeframe selection
        timeframe_label = ttk.Label(left_frame, text="Select Timeframes:", font=('Arial', 12, 'bold'))
        timeframe_label.pack(anchor=tk.W, pady=(10, 5))
        
        timeframe_frame = ttk.Frame(left_frame)
        timeframe_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Timeframe checkboxes
        timeframes = ['DAILY', 'WEEKLY', 'MONTHLY']
        for timeframe in timeframes:
            var = tk.BooleanVar(value=True)  # Default all selected
            self.timeframe_vars[timeframe] = var
            cb = ttk.Checkbutton(timeframe_frame, text=timeframe, variable=var)
            cb.pack(side=tk.LEFT, padx=(0, 15))
        
        # Options
        options_label = ttk.Label(left_frame, text="Analysis Options:", font=('Arial', 12, 'bold'))
        options_label.pack(anchor=tk.W, pady=(10, 5))
        
        options_frame = ttk.Frame(left_frame)
        options_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.include_breakouts_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(options_frame, text="Include Breakout Analysis", 
                       variable=self.include_breakouts_var).pack(anchor=tk.W)
        
        self.generate_pdf_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(options_frame, text="Auto-generate PDF Report", 
                       variable=self.generate_pdf_var).pack(anchor=tk.W)
        
        # Action buttons
        action_frame = ttk.Frame(left_frame)
        action_frame.pack(fill=tk.X, pady=20)
        
        self.scan_button = ttk.Button(action_frame, text="Start Pattern Scan", 
                                     command=self.start_scan, style='Accent.TButton')
        self.scan_button.pack(side=tk.LEFT, padx=(0, 10))
        
        self.stop_button = ttk.Button(action_frame, text="Stop Scan", 
                                     command=self.stop_scan, state=tk.DISABLED)
        self.stop_button.pack(side=tk.LEFT)
        
        # === RIGHT PANEL - PROGRESS & STATUS ===
        
        # Progress section
        progress_label = ttk.Label(right_frame, text="Scan Progress:", font=('Arial', 12, 'bold'))
        progress_label.pack(anchor=tk.W, pady=(10, 5))
        
        # Progress bar
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(right_frame, variable=self.progress_var, 
                                          maximum=100, length=300)
        self.progress_bar.pack(fill=tk.X, pady=(0, 10))
        
        # Status label
        self.status_var = tk.StringVar(value="Ready to scan")
        status_label = ttk.Label(right_frame, textvariable=self.status_var, 
                               font=('Arial', 10, 'italic'))
        status_label.pack(anchor=tk.W, pady=(0, 10))
        
        # Results summary
        results_label = ttk.Label(right_frame, text="Latest Scan Results:", font=('Arial', 12, 'bold'))
        results_label.pack(anchor=tk.W, pady=(10, 5))
        
        # Results tree view
        self.results_tree = ttk.Treeview(right_frame, columns=('Sector', 'Patterns', 'Breakouts'), 
                                        show='tree headings', height=8)
        
        self.results_tree.heading('#0', text='Summary')
        self.results_tree.heading('Sector', text='Sector')
        self.results_tree.heading('Patterns', text='Patterns')
        self.results_tree.heading('Breakouts', text='Breakouts')
        
        self.results_tree.column('#0', width=100)
        self.results_tree.column('Sector', width=180)
        self.results_tree.column('Patterns', width=80)
        self.results_tree.column('Breakouts', width=80)
        
        self.results_tree.pack(fill=tk.BOTH, expand=True)
        
        # Results scrollbar
        results_scrollbar = ttk.Scrollbar(right_frame, orient=tk.VERTICAL, 
                                         command=self.results_tree.yview)
        self.results_tree.configure(yscrollcommand=results_scrollbar.set)
        
        # Data freshness info
        freshness_frame = ttk.Frame(right_frame)
        freshness_frame.pack(fill=tk.X, pady=(10, 0))
        
        freshness_label = ttk.Label(freshness_frame, text="Data Freshness:", font=('Arial', 10, 'bold'))
        freshness_label.pack(anchor=tk.W)
        
        self.freshness_text = tk.StringVar(value="Loading...")
        freshness_info = ttk.Label(freshness_frame, textvariable=self.freshness_text, 
                                  font=('Arial', 9), foreground='gray')
        freshness_info.pack(anchor=tk.W)
        
        # Load data freshness info
        self.update_data_freshness()
        
    def setup_results_tab(self):
        """Setup the results display tab"""
        results_frame = ttk.Frame(self.notebook)
        self.notebook.add(results_frame, text="Results")
        
        # Results controls
        controls_frame = ttk.Frame(results_frame)
        controls_frame.pack(fill=tk.X, padx=10, pady=(10, 5))
        
        ttk.Label(controls_frame, text="Pattern Analysis Results", 
                 font=('Arial', 14, 'bold')).pack(side=tk.LEFT)
        
        ttk.Button(controls_frame, text="Export to CSV", 
                  command=self.export_results_csv).pack(side=tk.RIGHT, padx=(5, 0))
        ttk.Button(controls_frame, text="Generate PDF Report", 
                  command=self.generate_pdf_report).pack(side=tk.RIGHT)
        
        # Results display with tabs
        results_notebook = ttk.Notebook(results_frame)
        results_notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # Patterns tab
        patterns_frame = ttk.Frame(results_notebook)
        results_notebook.add(patterns_frame, text="All Patterns")
        
        # Detailed patterns tree
        self.detailed_tree = ttk.Treeview(patterns_frame, 
                                         columns=('Symbol', 'Sector', 'Pattern', 'Timeframe', 'Date', 'Range', 'Breakout'),
                                         show='headings')
        
        # Setup columns
        columns = {
            'Symbol': 80,
            'Sector': 120, 
            'Pattern': 60,
            'Timeframe': 80,
            'Date': 80,
            'Range': 70,
            'Breakout': 100
        }
        
        for col, width in columns.items():
            self.detailed_tree.heading(col, text=col)
            self.detailed_tree.column(col, width=width)
        
        self.detailed_tree.pack(fill=tk.BOTH, expand=True)
        
        # Patterns scrollbar
        detailed_scrollbar = ttk.Scrollbar(patterns_frame, orient=tk.VERTICAL, 
                                          command=self.detailed_tree.yview)
        self.detailed_tree.configure(yscrollcommand=detailed_scrollbar.set)
        detailed_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Breakouts tab
        breakouts_frame = ttk.Frame(results_notebook)
        results_notebook.add(breakouts_frame, text="Breakouts Only")
        
        # Breakouts tree
        self.breakouts_tree = ttk.Treeview(breakouts_frame,
                                          columns=('Symbol', 'Sector', 'Signal', 'Current', 'Previous', 'Volume'),
                                          show='headings')
        
        breakout_columns = {
            'Symbol': 80,
            'Sector': 150,
            'Signal': 120,
            'Current': 80,
            'Previous': 80,
            'Volume': 100
        }
        
        for col, width in breakout_columns.items():
            self.breakouts_tree.heading(col, text=col)
            self.breakouts_tree.column(col, width=width)
        
        self.breakouts_tree.pack(fill=tk.BOTH, expand=True)
        
    def setup_reports_tab(self):
        """Setup the reports generation and management tab"""
        reports_frame = ttk.Frame(self.notebook)
        self.notebook.add(reports_frame, text="Reports")
        
        # Report controls
        controls_frame = ttk.Frame(reports_frame)
        controls_frame.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Label(controls_frame, text="PDF Report Generation", 
                 font=('Arial', 14, 'bold')).pack(anchor=tk.W)
        
        # Quick report buttons
        quick_reports_frame = ttk.LabelFrame(reports_frame, text="Quick Reports")
        quick_reports_frame.pack(fill=tk.X, padx=10, pady=(10, 5))
        
        quick_buttons_frame = ttk.Frame(quick_reports_frame)
        quick_buttons_frame.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Button(quick_buttons_frame, text="Nifty Bank Report", 
                  command=self.generate_nifty_bank_report).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(quick_buttons_frame, text="All Major Sectors", 
                  command=self.generate_all_sectors_report).pack(side=tk.LEFT)
        
        # Custom report options
        custom_frame = ttk.LabelFrame(reports_frame, text="Custom Report Options")
        custom_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # Report generation log
        log_label = ttk.Label(custom_frame, text="Report Generation Log:")
        log_label.pack(anchor=tk.W, padx=10, pady=(10, 5))
        
        self.report_log = scrolledtext.ScrolledText(custom_frame, height=15, width=80)
        self.report_log.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
        
    def load_sectors(self):
        """Load available sectors into the GUI"""
        try:
            self.available_sectors = self.scanner.get_available_sectors()
            
            # Clear existing sector checkboxes
            for widget in self.sector_scrollable_frame.winfo_children():
                widget.destroy()
            self.sector_vars.clear()
            
            # Create checkboxes for each sector
            for sector_id, sector_name in self.available_sectors:
                var = tk.BooleanVar(value=False)
                self.sector_vars[sector_id] = var
                
                cb = ttk.Checkbutton(self.sector_scrollable_frame, text=f"{sector_name}", 
                                   variable=var)
                cb.pack(anchor=tk.W, padx=5, pady=2)
                
            self.log_message(f"Loaded {len(self.available_sectors)} sectors")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load sectors: {e}")
    
    def select_all_sectors(self):
        """Select all available sectors"""
        for var in self.sector_vars.values():
            var.set(True)
    
    def clear_all_sectors(self):
        """Clear all sector selections"""
        for var in self.sector_vars.values():
            var.set(False)
    
    def select_major_sectors(self):
        """Select major Nifty sectors only"""
        # Major sector IDs based on importance
        major_sector_ids = [1, 2, 4, 5, 8, 9]  # Nifty 50, Next 50, Bank, Financial Services, etc.
        
        self.clear_all_sectors()
        for sector_id in major_sector_ids:
            if sector_id in self.sector_vars:
                self.sector_vars[sector_id].set(True)
    
    def get_selected_sectors(self) -> List[int]:
        """Get list of selected sector IDs"""
        selected = []
        for sector_id, var in self.sector_vars.items():
            if var.get():
                selected.append(sector_id)
        return selected
    
    def get_selected_timeframes(self) -> List[str]:
        """Get list of selected timeframes"""
        selected = []
        for timeframe, var in self.timeframe_vars.items():
            if var.get():
                selected.append(timeframe)
        return selected
    
    def update_data_freshness(self):
        """Update data freshness information"""
        try:
            latest_dates = self.scanner.get_latest_dates()
            freshness_info = []
            for timeframe, date in latest_dates.items():
                freshness_info.append(f"{timeframe}: {date}")
            
            self.freshness_text.set(" | ".join(freshness_info))
        except Exception as e:
            self.freshness_text.set("Error loading data freshness")
    
    def start_scan(self):
        """Start the pattern scanning process"""
        # Validate inputs
        selected_sectors = self.get_selected_sectors()
        selected_timeframes = self.get_selected_timeframes()
        
        if not selected_sectors:
            messagebox.showwarning("Warning", "Please select at least one sector to analyze.")
            return
            
        if not selected_timeframes:
            messagebox.showwarning("Warning", "Please select at least one timeframe.")
            return
        
        # Update UI state
        self.scanning = True
        self.scan_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.NORMAL)
        self.progress_var.set(0)
        
        # Clear previous results
        self.clear_results()
        
        # Start scanning in background thread
        scan_thread = threading.Thread(target=self.run_scan, 
                                      args=(selected_sectors, selected_timeframes))
        scan_thread.daemon = True
        scan_thread.start()
    
    def stop_scan(self):
        """Stop the current scan"""
        self.scanning = False
        self.scan_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)
        self.status_var.set("Scan stopped by user")
    
    def run_scan(self, sector_ids: List[int], timeframes: List[str]):
        """Run the actual scanning process"""
        try:
            self.update_status("Initializing scan...")
            self.update_progress(10)
            
            if not self.scanning:
                return
            
            self.update_status("Scanning patterns...")
            self.update_progress(30)
            
            # Perform the scan
            include_breakouts = self.include_breakouts_var.get()
            patterns, summaries = self.scanner.scan_sectors_comprehensive(
                sector_ids, timeframes, include_breakouts
            )
            
            if not self.scanning:
                return
            
            self.update_progress(70)
            self.update_status("Processing results...")
            
            # Store results
            self.current_patterns = patterns
            self.current_summaries = summaries
            
            # Update UI with results
            self.root.after(0, self.display_results)
            
            self.update_progress(90)
            
            # Generate PDF if requested
            if self.generate_pdf_var.get() and self.scanning:
                self.update_status("Generating PDF report...")
                self.root.after(0, self.generate_pdf_report)
            
            self.update_progress(100)
            self.update_status(f"Scan completed! Found {len(patterns)} patterns across {len(summaries)} sectors")
            
        except Exception as e:
            self.update_status(f"Scan failed: {str(e)}")
            messagebox.showerror("Error", f"Scan failed: {e}")
        finally:
            # Reset UI state
            self.root.after(0, lambda: self.scan_button.config(state=tk.NORMAL))
            self.root.after(0, lambda: self.stop_button.config(state=tk.DISABLED))
            self.scanning = False
    
    def update_status(self, message: str):
        """Update status message"""
        self.root.after(0, lambda: self.status_var.set(message))
    
    def update_progress(self, value: float):
        """Update progress bar"""
        self.root.after(0, lambda: self.progress_var.set(value))
    
    def clear_results(self):
        """Clear previous results from display"""
        # Clear tree views
        for item in self.results_tree.get_children():
            self.results_tree.delete(item)
            
        for item in self.detailed_tree.get_children():
            self.detailed_tree.delete(item)
            
        for item in self.breakouts_tree.get_children():
            self.breakouts_tree.delete(item)
    
    def display_results(self):
        """Display scan results in the UI"""
        # Update summary tree
        for summary in self.current_summaries:
            total_patterns = sum(summary.pattern_counts.values())
            total_breakouts = summary.breakout_counts.get('BREAKOUT_ABOVE', 0) + \
                            summary.breakout_counts.get('BREAKDOWN_BELOW', 0)
            
            self.results_tree.insert('', 'end', text='Sector', 
                                   values=(summary.sector_name[:30], total_patterns, total_breakouts))
        
        # Update detailed patterns tree
        for pattern in self.current_patterns:
            breakout_signal = pattern.breakout_signal or "No Breakout"
            
            self.detailed_tree.insert('', 'end', values=(
                pattern.symbol,
                pattern.sector[:20],
                pattern.pattern_type,
                pattern.timeframe,
                pattern.pattern_date,
                f"{pattern.current_range:.2f}",
                breakout_signal[:15] + "..." if len(breakout_signal) > 15 else breakout_signal
            ))
        
        # Update breakouts tree (only breakout patterns)
        breakout_patterns = [p for p in self.current_patterns if p.breakout_signal]
        for pattern in breakout_patterns:
            signal_type = "ABOVE" if "BREAKOUT_ABOVE" in pattern.breakout_signal else "BELOW"
            current_price = f"{pattern.close_price:.2f}"
            previous_info = f"NR:{pattern.previous_nr_high:.2f}" if pattern.previous_nr_high else "N/A"
            volume = f"{pattern.volume:,}" if pattern.volume else "N/A"
            
            self.breakouts_tree.insert('', 'end', values=(
                pattern.symbol,
                pattern.sector[:25],
                signal_type,
                current_price,
                previous_info,
                volume
            ))
    
    def generate_pdf_report(self):
        """Generate PDF report for current results"""
        if not self.current_patterns and not self.current_summaries:
            messagebox.showwarning("Warning", "No scan results available. Please run a scan first.")
            return
        
        try:
            # Ask for save location
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            default_filename = f"sector_pattern_report_{timestamp}.pdf"
            
            filepath = filedialog.asksaveasfilename(
                defaultextension=".pdf",
                filetypes=[("PDF files", "*.pdf")],
                initialfilename=default_filename,
                title="Save PDF Report As..."
            )
            
            if not filepath:
                return
            
            # Generate report
            self.update_status("Generating PDF report...")
            
            selected_sectors = self.get_selected_sectors()
            selected_timeframes = self.get_selected_timeframes()
            
            report_path = self.report_generator.generate_comprehensive_report(
                selected_sectors, selected_timeframes, filepath
            )
            
            self.log_message(f"PDF report generated: {report_path}")
            messagebox.showinfo("Success", f"PDF report generated successfully!\nSaved to: {report_path}")
            
            # Ask if user wants to open the report
            if messagebox.askyesno("Open Report", "Would you like to open the PDF report now?"):
                os.startfile(report_path)  # Windows
            
        except Exception as e:
            self.log_message(f"Error generating PDF: {e}")
            messagebox.showerror("Error", f"Failed to generate PDF report: {e}")
    
    def generate_nifty_bank_report(self):
        """Generate quick report for Nifty Bank sector"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filepath = f"reports/nifty_bank_report_{timestamp}.pdf"
            
            # Ensure reports directory exists
            os.makedirs("reports", exist_ok=True)
            
            self.log_message("Generating Nifty Bank report...")
            
            from services.sector_report_generator import generate_nifty_bank_report
            report_path = generate_nifty_bank_report(filepath)
            
            self.log_message(f"Nifty Bank report generated: {report_path}")
            messagebox.showinfo("Success", f"Nifty Bank report generated!\nSaved to: {report_path}")
            
        except Exception as e:
            self.log_message(f"Error generating Nifty Bank report: {e}")
            messagebox.showerror("Error", f"Failed to generate report: {e}")
    
    def generate_all_sectors_report(self):
        """Generate quick report for all major sectors"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filepath = f"reports/all_major_sectors_report_{timestamp}.pdf"
            
            # Ensure reports directory exists
            os.makedirs("reports", exist_ok=True)
            
            self.log_message("Generating all major sectors report...")
            
            from services.sector_report_generator import generate_all_major_sectors_report
            report_path = generate_all_major_sectors_report(filepath)
            
            self.log_message(f"All sectors report generated: {report_path}")
            messagebox.showinfo("Success", f"Major sectors report generated!\nSaved to: {report_path}")
            
        except Exception as e:
            self.log_message(f"Error generating all sectors report: {e}")
            messagebox.showerror("Error", f"Failed to generate report: {e}")
    
    def export_results_csv(self):
        """Export current results to CSV"""
        if not self.current_patterns:
            messagebox.showwarning("Warning", "No results to export. Please run a scan first.")
            return
        
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filepath = filedialog.asksaveasfilename(
                defaultextension=".csv",
                filetypes=[("CSV files", "*.csv")],
                initialfilename=f"pattern_results_{timestamp}.csv",
                title="Export Results to CSV"
            )
            
            if not filepath:
                return
            
            # Convert patterns to DataFrame and save
            import pandas as pd
            
            data = []
            for pattern in self.current_patterns:
                data.append({
                    'Symbol': pattern.symbol,
                    'Sector': pattern.sector,
                    'Pattern_Type': pattern.pattern_type,
                    'Timeframe': pattern.timeframe,
                    'Pattern_Date': pattern.pattern_date,
                    'Current_Range': pattern.current_range,
                    'Range_Rank': pattern.range_rank,
                    'High_Price': pattern.high_price,
                    'Low_Price': pattern.low_price,
                    'Close_Price': pattern.close_price,
                    'Volume': pattern.volume,
                    'Breakout_Signal': pattern.breakout_signal or "",
                    'Previous_NR_Date': pattern.previous_nr_date or "",
                    'Previous_NR_High': pattern.previous_nr_high or "",
                    'Previous_NR_Low': pattern.previous_nr_low or ""
                })
            
            df = pd.DataFrame(data)
            df.to_csv(filepath, index=False)
            
            messagebox.showinfo("Success", f"Results exported to: {filepath}")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to export results: {e}")
    
    def log_message(self, message: str):
        """Log message to the report generation log"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] {message}\n"
        
        self.report_log.insert(tk.END, log_entry)
        self.report_log.see(tk.END)
    
    def run(self):
        """Run the GUI application"""
        if not self.parent:
            self.root.mainloop()

# Standalone usage
if __name__ == "__main__":
    app = SectorPatternGUI()
    app.run()