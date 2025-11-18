"""
Candlestick Pattern Scanner GUI
==============================

GUI component for candlestick pattern detection with date selection and progress tracking.
"""

import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime, timedelta
import threading
from typing import Optional
import sys
import os

# Add project path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.candlestick_patterns_enhanced import PatternScannerService, CandleDataService

class PatternScannerGUI:
    """GUI for candlestick pattern scanning"""
    
    def __init__(self, parent_notebook):
        self.parent = parent_notebook
        self.scanner_service = None
        self.is_scanning = False
        self.current_job_id = None
        
        self.create_gui()
    
    def create_gui(self):
        """Create the pattern scanner GUI"""
        # Create main frame
        self.frame = ttk.Frame(self.parent)
        
        # Title
        title_frame = ttk.Frame(self.frame)
        title_frame.pack(fill=tk.X, padx=10, pady=(10, 5))
        
        ttk.Label(title_frame, text="🕯️ Candlestick Pattern Scanner", 
                 font=('Arial', 14, 'bold')).pack(side=tk.LEFT)
        
        # Configuration section
        config_frame = ttk.LabelFrame(self.frame, text="📅 Scan Configuration", padding="10")
        config_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # Date selection
        date_frame = ttk.Frame(config_frame)
        date_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Start date
        ttk.Label(date_frame, text="Start Date:").grid(row=0, column=0, sticky=tk.W, padx=(0, 5))
        self.start_date_var = tk.StringVar(value="")
        self.start_date_entry = ttk.Entry(date_frame, textvariable=self.start_date_var, width=15)
        self.start_date_entry.grid(row=0, column=1, padx=(0, 10))
        
        # End date
        ttk.Label(date_frame, text="End Date:").grid(row=0, column=2, sticky=tk.W, padx=(0, 5))
        self.end_date_var = tk.StringVar(value="")
        self.end_date_entry = ttk.Entry(date_frame, textvariable=self.end_date_var, width=15)
        self.end_date_entry.grid(row=0, column=3, padx=(0, 10))
        
        # Quick date buttons
        ttk.Button(date_frame, text="Last 6 Months", command=self.set_last_6_months).grid(row=0, column=4, padx=5)
        ttk.Button(date_frame, text="Last 1 Year", command=self.set_last_1_year).grid(row=0, column=5, padx=5)
        ttk.Button(date_frame, text="Clear Dates", command=self.clear_dates).grid(row=0, column=6, padx=5)
        
        # Timeframe selection
        timeframe_frame = ttk.Frame(config_frame)
        timeframe_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(timeframe_frame, text="Timeframe:").pack(side=tk.LEFT, padx=(0, 10))
        
        self.timeframe_var = tk.StringVar(value="Monthly")
        self.timeframe_combo = ttk.Combobox(timeframe_frame, textvariable=self.timeframe_var, 
                                          values=["Daily", "Weekly", "Monthly"], 
                                          width=12, state="readonly")
        self.timeframe_combo.pack(side=tk.LEFT, padx=(0, 20))
        self.timeframe_combo.bind('<<ComboboxSelected>>', self.on_timeframe_change)
        
        # Data status label
        self.data_status_var = tk.StringVar(value="📊 Checking data...")
        self.data_status_label = ttk.Label(timeframe_frame, textvariable=self.data_status_var, 
                                         font=('Arial', 9))
        self.data_status_label.pack(side=tk.LEFT, padx=(10, 0))
        
        # Pattern types selection
        pattern_frame = ttk.Frame(config_frame)
        pattern_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(pattern_frame, text="Pattern Types:").pack(side=tk.LEFT, padx=(0, 10))
        
        self.pattern_vars = {
            'NR4': tk.BooleanVar(value=True),
            'NR7': tk.BooleanVar(value=True),
            'NR13': tk.BooleanVar(value=True),
            'NR21': tk.BooleanVar(value=True)
        }
        
        for pattern_type, var in self.pattern_vars.items():
            ttk.Checkbutton(pattern_frame, text=pattern_type, variable=var).pack(side=tk.LEFT, padx=5)
        
        # Performance settings
        perf_frame = ttk.Frame(config_frame)
        perf_frame.pack(fill=tk.X)
        
        ttk.Label(perf_frame, text="Batch Size:").grid(row=0, column=0, sticky=tk.W, padx=(0, 5))
        self.batch_size_var = tk.IntVar(value=50)
        batch_spin = ttk.Spinbox(perf_frame, from_=10, to=200, width=10, textvariable=self.batch_size_var)
        batch_spin.grid(row=0, column=1, padx=(0, 20))
        
        ttk.Label(perf_frame, text="Workers:").grid(row=0, column=2, sticky=tk.W, padx=(0, 5))
        self.workers_var = tk.IntVar(value=4)
        workers_spin = ttk.Spinbox(perf_frame, from_=1, to=8, width=10, textvariable=self.workers_var)
        workers_spin.grid(row=0, column=3, padx=(0, 20))
        
        # Control buttons
        control_frame = ttk.Frame(self.frame)
        control_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self.scan_button = ttk.Button(control_frame, text="🚀 Start Pattern Scan", 
                                     command=self.start_scan, style="Accent.TButton")
        self.scan_button.pack(side=tk.LEFT, padx=(0, 10))
        
        self.stop_button = ttk.Button(control_frame, text="⏹️ Stop Scan", 
                                     command=self.stop_scan, state=tk.DISABLED)
        self.stop_button.pack(side=tk.LEFT, padx=(0, 10))
        
        self.latest_button = ttk.Button(control_frame, text="📊 Scan Latest Only", 
                                       command=self.scan_latest_only)
        self.latest_button.pack(side=tk.LEFT)
        
        # Progress section
        progress_frame = ttk.LabelFrame(self.frame, text="📈 Progress", padding="10")
        progress_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # Progress bar
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(progress_frame, variable=self.progress_var, 
                                          mode='determinate', length=400)
        self.progress_bar.pack(fill=tk.X, pady=(0, 5))
        
        # Status labels
        status_info_frame = ttk.Frame(progress_frame)
        status_info_frame.pack(fill=tk.X)
        
        self.status_label = ttk.Label(status_info_frame, text="Ready to scan", foreground="blue")
        self.status_label.pack(side=tk.LEFT)
        
        self.stats_label = ttk.Label(status_info_frame, text="", foreground="darkgreen")
        self.stats_label.pack(side=tk.RIGHT)
        
        # Results section
        results_frame = ttk.LabelFrame(self.frame, text="📋 Recent Results", padding="10")
        results_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # Results treeview
        columns = ('Date', 'Symbol', 'Pattern', 'Range', 'Rank')
        self.results_tree = ttk.Treeview(results_frame, columns=columns, show='headings', height=10)
        
        for col in columns:
            self.results_tree.heading(col, text=col)
            width = 80 if col in ['Date', 'Range', 'Rank'] else 120
            self.results_tree.column(col, width=width)
        
        # Scrollbar for treeview
        scrollbar = ttk.Scrollbar(results_frame, orient=tk.VERTICAL, command=self.results_tree.yview)
        self.results_tree.configure(yscrollcommand=scrollbar.set)
        
        self.results_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Results summary
        summary_frame = ttk.Frame(results_frame)
        summary_frame.pack(fill=tk.X, pady=(5, 0))
        
        self.summary_label = ttk.Label(summary_frame, text="No patterns detected yet", 
                                      font=('Arial', 9, 'italic'))
        self.summary_label.pack(side=tk.LEFT)
        
        # Load recent results on startup
        self.load_recent_patterns()
        
        # Initialize data service and check data status
        self.data_service = CandleDataService()
        self.check_timeframe_data()
    
    def on_timeframe_change(self, event=None):
        """Handle timeframe selection change"""
        self.check_timeframe_data()
    
    def check_timeframe_data(self):
        """Check data availability for selected timeframe"""
        try:
            timeframe = self.timeframe_var.get()
            self.data_status_var.set("🔄 Checking data...")
            
            # Run in thread to avoid blocking UI
            def check_data():
                try:
                    freshness = self.data_service.check_data_freshness(timeframe)
                    
                    # Update UI in main thread
                    def update_ui():
                        status = freshness['status']
                        latest_date = freshness['latest_date']
                        symbol_count = freshness['symbol_count']
                        
                        if latest_date:
                            date_str = latest_date.strftime("%Y-%m-%d")
                            status_text = f"{status} | {symbol_count:,} symbols | Latest: {date_str}"
                        else:
                            status_text = f"{status} | No data available"
                        
                        self.data_status_var.set(status_text)
                    
                    # Schedule UI update
                    self.frame.after(0, update_ui)
                    
                except Exception as e:
                    def update_error():
                        self.data_status_var.set(f"❌ Error checking data: {str(e)}")
                    self.frame.after(0, update_error)
            
            # Start background thread
            threading.Thread(target=check_data, daemon=True).start()
            
        except Exception as e:
            self.data_status_var.set(f"❌ Error: {str(e)}")
    
    def set_last_6_months(self):
        """Set date range to last 6 months"""
        end_date = datetime.now()
        start_date = end_date - timedelta(days=180)
        
        self.start_date_var.set(start_date.strftime("%Y-%m-%d"))
        self.end_date_var.set(end_date.strftime("%Y-%m-%d"))
    
    def set_last_1_year(self):
        """Set date range to last 1 year"""
        end_date = datetime.now()
        start_date = end_date - timedelta(days=365)
        
        self.start_date_var.set(start_date.strftime("%Y-%m-%d"))
        self.end_date_var.set(end_date.strftime("%Y-%m-%d"))
    
    def clear_dates(self):
        """Clear date selection"""
        self.start_date_var.set("")
        self.end_date_var.set("")
    
    def start_scan(self):
        """Start pattern scanning"""
        if self.is_scanning:
            messagebox.showwarning("Scan in Progress", "A pattern scan is already in progress!")
            return
        
        # Validate inputs
        pattern_types = [ptype for ptype, var in self.pattern_vars.items() if var.get()]
        if not pattern_types:
            messagebox.showerror("No Patterns", "Please select at least one pattern type!")
            return
        
        # Parse dates
        start_date = None
        end_date = None
        
        if self.start_date_var.get():
            try:
                start_date = datetime.strptime(self.start_date_var.get(), "%Y-%m-%d")
            except ValueError:
                messagebox.showerror("Invalid Date", "Start date must be in YYYY-MM-DD format!")
                return
        
        if self.end_date_var.get():
            try:
                end_date = datetime.strptime(self.end_date_var.get(), "%Y-%m-%d")
            except ValueError:
                messagebox.showerror("Invalid Date", "End date must be in YYYY-MM-DD format!")
                return
        
        if start_date and end_date and start_date > end_date:
            messagebox.showerror("Invalid Range", "Start date must be before end date!")
            return
        
        # Update UI state
        self.is_scanning = True
        self.scan_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.NORMAL)
        self.progress_var.set(0)
        self.status_label.config(text="Initializing scan...", foreground="orange")
        
        # Start scan in background thread
        scan_args = {
            'start_date': start_date,
            'end_date': end_date,
            'pattern_types': pattern_types,
            'timeframe': self.timeframe_var.get(),
            'batch_size': self.batch_size_var.get(),
            'max_workers': self.workers_var.get()
        }
        
        scan_thread = threading.Thread(target=self._run_scan, args=(scan_args,), daemon=True)
        scan_thread.start()
    
    def _run_scan(self, scan_args):
        """Run the pattern scan in background thread"""
        try:
            # Create scanner with progress callback
            self.scanner_service = PatternScannerService(progress_callback=self._progress_callback)
            
            # Run scan with timeframe
            results = self.scanner_service.scan_patterns(
                symbols=None,
                start_date=scan_args['start_date'],
                end_date=scan_args['end_date'],
                pattern_types=scan_args['pattern_types'],
                timeframe=scan_args['timeframe'],
                batch_size=scan_args['batch_size'],
                max_workers=scan_args['max_workers'],
                progress_callback=self._progress_callback_simple
            )
            
            # Update UI on completion
            self.frame.after(0, lambda: self._scan_completed(results))
            
        except Exception as e:
            # Handle errors
            self.frame.after(0, lambda: self._scan_error(str(e)))
    
    def _progress_callback_simple(self, message, percentage):
        """Handle simple progress updates"""
        def update_ui():
            self.progress_var.set(percentage)
            self.status_label.config(text=message)
        
        self.frame.after(0, update_ui)
    
    def _progress_callback(self, processed, total, percentage, current_symbol):
        """Handle progress updates"""
        def update_ui():
            self.progress_var.set(percentage)
            self.status_label.config(text=f"Processing: {current_symbol}")
            self.stats_label.config(text=f"{processed}/{total} symbols")
        
        self.frame.after(0, update_ui)
    
    def _scan_completed(self, results):
        """Handle scan completion"""
        self.is_scanning = False
        self.scan_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)
        self.progress_var.set(100)
        
        # Handle results - could be list of patterns or dict with stats
        if isinstance(results, list):
            patterns_found = len(results)
            processed_symbols = "Unknown"
            processing_time = "Unknown"
        else:
            patterns_found = results.get('patterns_found', 0)
            processing_time = results.get('processing_time', 0)
            processed_symbols = results.get('processed', 0)
        
        self.status_label.config(text=f"Scan completed! Found {patterns_found} patterns", 
                                foreground="green")
        self.stats_label.config(text=f"Processed symbols, {processing_time}s")
        
        # Refresh results
        self.load_recent_patterns()
        
        # Show completion message
        messagebox.showinfo("Scan Complete", 
                           f"Pattern scan completed!\n\n"
                           f"Patterns found: {patterns_found}\n"
                           f"Processing completed successfully!")
    
    def _scan_error(self, error_message):
        """Handle scan errors"""
        self.is_scanning = False
        self.scan_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)
        self.progress_var.set(0)
        self.status_label.config(text="Scan failed", foreground="red")
        
        messagebox.showerror("Scan Error", f"Pattern scan failed:\n\n{error_message}")
    
    def stop_scan(self):
        """Stop the current scan"""
        if self.is_scanning:
            # Note: This is a basic stop - in production you'd want proper thread cancellation
            self.is_scanning = False
            self.scan_button.config(state=tk.NORMAL)
            self.stop_button.config(state=tk.DISABLED)
            self.progress_var.set(0)
            self.status_label.config(text="Scan stopped", foreground="red")
    
    def scan_latest_only(self):
        """Scan only the latest available candle"""
        if self.is_scanning:
            messagebox.showwarning("Scan in Progress", "Please wait for current scan to complete!")
            return
        
        # Clear dates and set pattern types to all
        self.clear_dates()
        for var in self.pattern_vars.values():
            var.set(True)
        
        # Set aggressive performance settings for quick scan
        self.batch_size_var.set(100)
        self.workers_var.set(6)
        
        # Start scan
        self.start_scan()
    
    def load_recent_patterns(self):
        """Load recent patterns from database"""
        try:
            # Clear existing items
            for item in self.results_tree.get_children():
                self.results_tree.delete(item)
            
            # Import storage service
            from services.candlestick_patterns import PatternStorageService
            storage_service = PatternStorageService()
            
            # Get recent patterns (last 30 days)
            end_date = datetime.now()
            start_date = end_date - timedelta(days=30)
            
            patterns = storage_service.get_patterns(start_date=start_date, end_date=end_date)
            
            if patterns:
                # Sort by date descending
                patterns.sort(key=lambda x: x['pattern_date'], reverse=True)
                
                # Add to tree (limit to 100 most recent)
                for pattern in patterns[:100]:
                    self.results_tree.insert('', 'end', values=(
                        pattern['pattern_date'].strftime('%Y-%m-%d'),
                        pattern['symbol'],
                        pattern['pattern_type'],
                        f"{pattern['current_range']:.2f}",
                        pattern['range_rank']
                    ))
                
                # Update summary
                self.summary_label.config(text=f"Showing {min(len(patterns), 100)} of {len(patterns)} recent patterns")
            else:
                self.summary_label.config(text="No recent patterns found")
                
        except Exception as e:
            self.summary_label.config(text=f"Error loading patterns: {str(e)}")
    
    def get_frame(self):
        """Get the main frame for adding to notebook"""
        return self.frame