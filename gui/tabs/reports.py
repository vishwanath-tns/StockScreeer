"""
Reports Tab for Scanner GUI
===========================

This module provides the Reports tab functionality including:
- RSI Divergences PDF Generation
- Future report types can be added here

The tab contains subsections for different types of reports.
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path


class ReportsTab:
    def __init__(self, parent_frame):
        self.parent_frame = parent_frame
        self.build_reports_tab()
    
    def build_reports_tab(self):
        """Build the Reports tab with RSI Divergences subsection"""
        
        # Main container with padding
        main_container = ttk.Frame(self.parent_frame, padding="10")
        main_container.pack(fill="both", expand=True)
        
        # Title
        title_label = ttk.Label(main_container, text="📊 Reports Generator", 
                               font=("Segoe UI", 14, "bold"))
        title_label.pack(anchor="w", pady=(0, 15))
        
        # Description
        desc_label = ttk.Label(main_container, 
                              text="Generate professional PDF reports for technical analysis and trading insights.",
                              font=("Segoe UI", 9))
        desc_label.pack(anchor="w", pady=(0, 20))
        
        # Create notebook for report subsections
        self.reports_notebook = ttk.Notebook(main_container)
        self.reports_notebook.pack(fill="both", expand=True)
        
        # RSI Divergences subsection
        self._create_rsi_divergences_tab()
        
        # Placeholder for future report types
        self._create_placeholder_tabs()
    
    def _create_rsi_divergences_tab(self):
        """Create RSI Divergences report subsection"""
        
        # Create frame for RSI Divergences
        rsi_frame = ttk.Frame(self.reports_notebook, padding="15")
        self.reports_notebook.add(rsi_frame, text="📈 RSI Divergences")
        
        # Header
        header_label = ttk.Label(rsi_frame, text="RSI Divergence Analysis Report", 
                                font=("Segoe UI", 12, "bold"))
        header_label.pack(anchor="w", pady=(0, 10))
        
        # Description
        desc_text = """Generate comprehensive PDF reports with:
• Candlestick charts with even spacing (no weekend gaps)
• Color-coded divergence lines (Green: Bullish, Red: Bearish)  
• Trading table with buy/sell levels
• Professional formatting with 150 DPI quality
• Mixed signal verification for comprehensive analysis"""
        
        desc_label = ttk.Label(rsi_frame, text=desc_text, font=("Segoe UI", 9),
                              justify="left")
        desc_label.pack(anchor="w", pady=(0, 20))
        
        # Configuration frame
        config_frame = ttk.LabelFrame(rsi_frame, text="Report Configuration", padding="10")
        config_frame.pack(fill="x", pady=(0, 15))
        
        # Max stocks setting
        stocks_frame = ttk.Frame(config_frame)
        stocks_frame.pack(fill="x", pady=(0, 10))
        
        ttk.Label(stocks_frame, text="Max Stocks to Include:").pack(side="left")
        self.max_stocks_var = tk.StringVar(value="15")
        stocks_spinbox = ttk.Spinbox(stocks_frame, from_=5, to=50, width=10, 
                                    textvariable=self.max_stocks_var)
        stocks_spinbox.pack(side="left", padx=(10, 0))
        
        # Report type setting
        type_frame = ttk.Frame(config_frame)
        type_frame.pack(fill="x", pady=(0, 10))
        
        ttk.Label(type_frame, text="Report Type:").pack(side="left")
        self.report_type_var = tk.StringVar(value="enhanced")
        type_combo = ttk.Combobox(type_frame, textvariable=self.report_type_var,
                                 values=["enhanced", "basic"], state="readonly", width=15)
        type_combo.pack(side="left", padx=(10, 0))
        type_combo.set("enhanced")
        
        # Buttons frame
        buttons_frame = ttk.Frame(rsi_frame)
        buttons_frame.pack(fill="x", pady=(0, 15))
        
        # First row of buttons
        buttons_row1 = ttk.Frame(buttons_frame)
        buttons_row1.pack(fill="x", pady=(0, 5))
        
        # Generate full report button
        self.generate_btn = ttk.Button(buttons_row1, text="🚀 Generate All Signals PDF",
                                      command=self._generate_rsi_report)
        self.generate_btn.pack(side="left", padx=(0, 10))
        
        # Generate 7-day report button
        self.generate_7day_btn = ttk.Button(buttons_row1, text="📅 Generate Last 7 Days PDF",
                                           command=self._generate_7day_report)
        self.generate_7day_btn.pack(side="left", padx=(0, 10))
        
        # Second row of buttons
        buttons_row2 = ttk.Frame(buttons_frame)
        buttons_row2.pack(fill="x")
        
        # Open folder button
        self.open_folder_btn = ttk.Button(buttons_row2, text="📁 Open Reports Folder",
                                         command=self._open_reports_folder)
        self.open_folder_btn.pack(side="left", padx=(0, 10))
        
        # View last report button
        self.view_report_btn = ttk.Button(buttons_row2, text="👁️ View Last Report",
                                         command=self._view_last_report, state="disabled")
        self.view_report_btn.pack(side="left")
        
        # Progress frame
        progress_frame = ttk.Frame(rsi_frame)
        progress_frame.pack(fill="x", pady=(0, 15))
        
        # Progress bar
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(progress_frame, variable=self.progress_var,
                                           maximum=100, length=400)
        self.progress_bar.pack(side="left", fill="x", expand=True)
        
        # Status label
        self.status_var = tk.StringVar(value="Ready to generate reports")
        self.status_label = ttk.Label(progress_frame, textvariable=self.status_var,
                                     font=("Segoe UI", 9))
        self.status_label.pack(side="left", padx=(10, 0))
        
        # Log output
        log_frame = ttk.LabelFrame(rsi_frame, text="Generation Log", padding="5")
        log_frame.pack(fill="both", expand=True)
        
        # Create text widget with scrollbar
        self.log_text = tk.Text(log_frame, height=12, wrap="word", font=("Consolas", 9))
        scrollbar = ttk.Scrollbar(log_frame, orient="vertical", command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=scrollbar.set)
        
        self.log_text.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Store last generated report path
        self.last_report_path = None
    
    def _create_placeholder_tabs(self):
        """Create placeholder tabs for future report types"""
        
        # Market Breadth Reports (placeholder)
        breadth_frame = ttk.Frame(self.reports_notebook, padding="15")
        self.reports_notebook.add(breadth_frame, text="📊 Market Breadth")
        
        ttk.Label(breadth_frame, text="Market Breadth Reports", 
                 font=("Segoe UI", 12, "bold")).pack(anchor="w", pady=(0, 10))
        ttk.Label(breadth_frame, text="Coming soon: Advanced/Decline analysis, sector rotation reports, and market health indicators.",
                 font=("Segoe UI", 9), foreground="gray").pack(anchor="w")
        
        # Technical Analysis Reports (placeholder)
        tech_frame = ttk.Frame(self.reports_notebook, padding="15")
        self.reports_notebook.add(tech_frame, text="🔍 Technical Analysis")
        
        ttk.Label(tech_frame, text="Technical Analysis Reports", 
                 font=("Segoe UI", 12, "bold")).pack(anchor="w", pady=(0, 10))
        ttk.Label(tech_frame, text="Coming soon: Moving average crossovers, trend analysis, and momentum reports.",
                 font=("Segoe UI", 9), foreground="gray").pack(anchor="w")
        
        # Portfolio Reports (placeholder)
        portfolio_frame = ttk.Frame(self.reports_notebook, padding="15")
        self.reports_notebook.add(portfolio_frame, text="💼 Portfolio")
        
        ttk.Label(portfolio_frame, text="Portfolio Reports", 
                 font=("Segoe UI", 12, "bold")).pack(anchor="w", pady=(0, 10))
        ttk.Label(portfolio_frame, text="Coming soon: Performance analysis, risk assessment, and allocation reports.",
                 font=("Segoe UI", 9), foreground="gray").pack(anchor="w")
    
    def _generate_rsi_report(self):
        """Generate RSI Divergence PDF report in background thread"""
        
        # Disable button during generation
        self.generate_btn.config(state="disabled")
        self.progress_var.set(0)
        self.status_var.set("Starting PDF generation...")
        self._clear_log()
        
        # Start generation in background thread
        generation_thread = threading.Thread(target=self._run_rsi_generation, daemon=True)
        generation_thread.start()
    
    def _run_rsi_generation(self):
        """Run RSI report generation in background thread"""
        try:
            self._update_status("Initializing report generator...")
            self._update_progress(10)
            
            # Get configuration values
            max_stocks = int(self.max_stocks_var.get())
            
            self._log_message(f"📊 Starting RSI Divergence PDF Generation")
            self._log_message(f"📋 Configuration: Max Stocks = {max_stocks}")
            self._log_message(f"📅 Report Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            self._log_message("-" * 50)
            
            # Import and run the enhanced PDF generator
            self._update_status("Loading report generator...")
            self._update_progress(20)
            
            # Change to project directory
            project_dir = Path(__file__).parent.parent.parent
            original_cwd = os.getcwd()
            os.chdir(project_dir)
            
            try:
                # Set matplotlib to use non-GUI backend for threading
                import matplotlib
                matplotlib.use('Agg')  # Use non-GUI backend for threading
                
                # Import the PDF generator
                self._log_message("🔍 Importing PDF generator module...")
                sys.path.insert(0, str(project_dir / "scripts"))
                import generate_enhanced_rsi_divergence_pdf as pdf_gen
                
                self._update_status("Fetching divergence data...")
                self._update_progress(40)
                
                # Generate the PDF with progress updates
                self._log_message("📊 Fetching RSI divergence data from database...")
                
                # Call the PDF generation function
                self._log_message("🚀 Generating enhanced PDF report...")
                result = pdf_gen.generate_enhanced_pdf_report(max_stocks=max_stocks)
                
                self._update_progress(90)
                self._update_status("Finalizing PDF report...")
                
                # Check if generation was successful
                if result and result.get('success', False):
                    # PDF generation succeeded
                    pdf_filename = result.get('filename')
                    if pdf_filename and Path(pdf_filename).exists():
                        self.last_report_path = str(Path(pdf_filename).resolve())
                        file_size = Path(pdf_filename).stat().st_size / 1024  # KB
                        
                        self._log_message("-" * 50)
                        self._log_message(f"✅ PDF Report Generated Successfully!")
                        self._log_message(f"📄 Filename: {pdf_filename}")
                        self._log_message(f"📊 File Size: {file_size:.1f} KB")
                        self._log_message(f"� Total Charts: {result.get('total_stocks', 0)}")
                        self._log_message(f"📈 Total Signals: {result.get('total_signals', 0)}")
                        self._log_message(f"� Buy Opportunities: {result.get('buy_opportunities', 0)}")
                        self._log_message(f"🔴 Sell Opportunities: {result.get('sell_opportunities', 0)}")
                        self._log_message(f"📁 Location: {self.last_report_path}")
                        self._log_message(f"📅 Created: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                        
                        self._update_status(f"✅ Report generated: {Path(pdf_filename).name}")
                        self._update_progress(100)
                        
                        # Enable view button
                        self.view_report_btn.config(state="normal")
                    else:
                        self._log_message(f"❌ Error: PDF file not found: {pdf_filename}")
                        self._update_status("❌ Error: PDF file not found after generation")
                elif result and not result.get('success', True):
                    # PDF generation failed with error
                    error_msg = result.get('error', 'Unknown error')
                    self._log_message(f"❌ PDF generation failed: {error_msg}")
                    self._update_status(f"❌ Generation failed: {error_msg}")
                else:
                    # Unexpected result format
                    self._log_message(f"❌ Unexpected result from PDF generator: {result}")
                    self._update_status("❌ PDF generation failed (unexpected result)")
                    
            except Exception as e:
                self._log_message(f"❌ Error during generation: {str(e)}")
                self._update_status(f"❌ Error: {str(e)}")
                import traceback
                self._log_message(f"💻 Technical details:")
                error_lines = traceback.format_exc().split('\n')
                for line in error_lines:
                    if line.strip():
                        self._log_message(f"   {line}")
            finally:
                os.chdir(original_cwd)
                
        except Exception as e:
            self._log_message(f"💥 Unexpected error: {str(e)}")
            self._update_status(f"💥 Unexpected error: {str(e)}")
        finally:
            # Re-enable button
            self.generate_btn.config(state="normal")
    
    def _generate_7day_report(self):
        """Generate RSI Divergence PDF report for last 7 days in background thread"""
        
        # Disable button during generation
        self.generate_7day_btn.config(state="disabled")
        self.progress_var.set(0)
        self.status_var.set("Starting 7-day PDF generation...")
        self._clear_log()
        
        # Start generation in background thread
        generation_thread = threading.Thread(target=self._run_7day_generation, daemon=True)
        generation_thread.start()
    
    def _run_7day_generation(self):
        """Run 7-day RSI report generation in background thread"""
        try:
            self._update_status("Initializing 7-day report generator...")
            self._update_progress(10)
            
            # Get configuration values
            max_stocks = int(self.max_stocks_var.get())
            
            self._log_message(f"📊 Starting 7-Day RSI Divergence PDF Generation")
            self._log_message(f"📋 Configuration: Max Stocks = {max_stocks}")
            self._log_message(f"📅 Report Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            self._log_message(f"🔍 Filter: Last 7 days signals only")
            self._log_message("-" * 50)
            
            # Import and run the enhanced PDF generator
            self._update_status("Loading 7-day report generator...")
            self._update_progress(20)
            
            # Change to project directory
            project_dir = Path(__file__).parent.parent.parent
            original_cwd = os.getcwd()
            os.chdir(project_dir)
            
            try:
                # Set matplotlib to use non-GUI backend for threading
                import matplotlib
                matplotlib.use('Agg')  # Use non-GUI backend for threading
                
                # Import the PDF generator
                self._log_message("🔍 Importing 7-day PDF generator module...")
                sys.path.insert(0, str(project_dir / "scripts"))
                import generate_enhanced_rsi_divergence_pdf as pdf_gen
                
                self._update_status("Fetching last 7 days divergence data...")
                self._update_progress(40)
                
                # Generate the PDF with progress updates
                self._log_message("📊 Fetching RSI divergence data for last 7 days...")
                
                # Call the PDF generation function with 7-day filter
                self._log_message("🚀 Generating enhanced 7-day PDF report...")
                result = pdf_gen.generate_enhanced_pdf_report_7days(max_stocks=max_stocks)
                
                self._update_progress(90)
                self._update_status("Finalizing 7-day PDF report...")
                
                # Check if generation was successful
                if result and result.get('success', False):
                    # PDF generation succeeded
                    pdf_filename = result.get('filename')
                    if pdf_filename and Path(pdf_filename).exists():
                        self.last_report_path = str(Path(pdf_filename).resolve())
                        file_size = Path(pdf_filename).stat().st_size / 1024  # KB
                        
                        self._log_message("-" * 50)
                        self._log_message(f"✅ 7-Day PDF Report Generated Successfully!")
                        self._log_message(f"📄 Filename: {pdf_filename}")
                        self._log_message(f"📊 File Size: {file_size:.1f} KB")
                        self._log_message(f"📈 Total Charts: {result.get('total_stocks', 0)}")
                        self._log_message(f"📊 Total Signals: {result.get('total_signals', 0)}")
                        self._log_message(f"🟢 Buy Opportunities: {result.get('buy_opportunities', 0)}")
                        self._log_message(f"🔴 Sell Opportunities: {result.get('sell_opportunities', 0)}")
                        self._log_message(f"📁 Location: {self.last_report_path}")
                        self._log_message(f"📅 Created: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                        self._log_message(f"🕐 Period: Last 7 days signals only")
                        
                        self._update_status(f"✅ 7-day report generated: {Path(pdf_filename).name}")
                        self._update_progress(100)
                        
                        # Enable view button
                        self.view_report_btn.config(state="normal")
                    else:
                        self._log_message(f"❌ Error: PDF file not found: {pdf_filename}")
                        self._update_status("❌ Error: PDF file not found after generation")
                elif result and not result.get('success', True):
                    # PDF generation failed with error
                    error_msg = result.get('error', 'Unknown error')
                    self._log_message(f"❌ 7-day PDF generation failed: {error_msg}")
                    self._update_status(f"❌ 7-day generation failed: {error_msg}")
                else:
                    # Unexpected result format
                    self._log_message(f"❌ Unexpected result from 7-day PDF generator: {result}")
                    self._update_status("❌ 7-day PDF generation failed (unexpected result)")
                    
            except Exception as e:
                self._log_message(f"💥 Error during 7-day PDF generation: {str(e)}")
                self._update_status(f"💥 7-day generation error: {str(e)}")
                import traceback
                self._log_message(f"💥 Stack trace:\n{traceback.format_exc()}")
            finally:
                os.chdir(original_cwd)
                
        except Exception as e:
            self._log_message(f"💥 Unexpected 7-day error: {str(e)}")
            self._update_status(f"💥 Unexpected 7-day error: {str(e)}")
        finally:
            # Re-enable button
            self.generate_7day_btn.config(state="normal")
    
    def _open_reports_folder(self):
        """Open the reports folder in file explorer"""
        try:
            project_dir = Path(__file__).parent.parent.parent
            os.startfile(project_dir)
        except Exception as e:
            messagebox.showerror("Error", f"Could not open folder: {str(e)}")
    
    def _view_last_report(self):
        """Open the last generated report in default PDF viewer"""
        if self.last_report_path and Path(self.last_report_path).exists():
            try:
                os.startfile(self.last_report_path)
            except Exception as e:
                messagebox.showerror("Error", f"Could not open PDF: {str(e)}")
        else:
            messagebox.showwarning("Warning", "No recent report found or file has been moved.")
    
    def _update_status(self, message):
        """Thread-safe status update"""
        def update():
            self.status_var.set(message)
        
        self.parent_frame.after(0, update)
    
    def _update_progress(self, value):
        """Thread-safe progress update"""
        def update():
            self.progress_var.set(value)
        
        self.parent_frame.after(0, update)
    
    def _log_message(self, message):
        """Thread-safe log message"""
        def update():
            timestamp = datetime.now().strftime("%H:%M:%S")
            self.log_text.insert("end", f"[{timestamp}] {message}\n")
            self.log_text.see("end")
        
        self.parent_frame.after(0, update)
    
    def _clear_log(self):
        """Clear the log text"""
        def update():
            self.log_text.delete(1.0, "end")
        
        self.parent_frame.after(0, update)