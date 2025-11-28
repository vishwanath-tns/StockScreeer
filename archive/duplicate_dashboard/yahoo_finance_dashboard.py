#!/usr/bin/env python3
"""
Yahoo Finance Features Dashboard
Centralized access to all Yahoo Finance related features and tools
"""

import tkinter as tk
from tkinter import ttk, messagebox
import subprocess
import sys
import os
from datetime import datetime

class YahooFinanceDashboard:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("📊 Yahoo Finance Data Dashboard")
        self.root.geometry("1200x800")
        self.root.configure(bg='#0f0f23')
        
        self.create_ui()
        
    def create_ui(self):
        """Create the dashboard UI"""
        # Main container
        main_frame = tk.Frame(self.root, bg='#0f0f23')
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Title
        title_label = tk.Label(
            main_frame,
            text="📊 Yahoo Finance Data Dashboard",
            font=('Segoe UI', 24, 'bold'),
            fg='#00d4ff',
            bg='#0f0f23'
        )
        title_label.pack(pady=(0, 10))
        
        subtitle_label = tk.Label(
            main_frame,
            text="Complete Access to All Yahoo Finance Features",
            font=('Segoe UI', 12),
            fg='#888888',
            bg='#0f0f23'
        )
        subtitle_label.pack(pady=(0, 20))
        
        # Create notebook for tabs
        notebook = ttk.Notebook(main_frame)
        notebook.pack(fill=tk.BOTH, expand=True)
        
        # Configure notebook style
        style = ttk.Style()
        style.theme_use('clam')
        style.configure('TNotebook', background='#0f0f23', borderwidth=0)
        style.configure('TNotebook.Tab', background='#1a1a2e', foreground='white', 
                       padding=[20, 10], font=('Segoe UI', 10, 'bold'))
        style.map('TNotebook.Tab', background=[('selected', '#00d4ff')],
                 foreground=[('selected', '#0f0f23')])
        
        # Create tabs
        self.create_download_tab(notebook)
        self.create_diagnostics_tab(notebook)
        self.create_realtime_tab(notebook)
        self.create_analysis_tab(notebook)
        self.create_maintenance_tab(notebook)
        
        # Status bar
        status_frame = tk.Frame(self.root, bg='#1a1a2e', height=30)
        status_frame.pack(fill=tk.X, side=tk.BOTTOM)
        
        self.status_label = tk.Label(
            status_frame,
            text=f"Ready | Dashboard Loaded: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            font=('Segoe UI', 9),
            fg='#00ff00',
            bg='#1a1a2e',
            anchor='w'
        )
        self.status_label.pack(fill=tk.X, padx=10, pady=5)
        
    def create_download_tab(self, notebook):
        """Tab 1: Data Download Tools"""
        tab = tk.Frame(notebook, bg='#0f0f23')
        notebook.add(tab, text='📥 Download Data')
        
        # Create scrollable canvas
        canvas = tk.Canvas(tab, bg='#0f0f23', highlightthickness=0)
        scrollbar = ttk.Scrollbar(tab, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg='#0f0f23')
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True, padx=10, pady=10)
        scrollbar.pack(side="right", fill="y")
        
        # Section 1: Main Download Tools
        self.create_section(scrollable_frame, "🔽 Main Download Tools", [
            ("📈 Yahoo Finance Data Downloader (GUI)", 
             "Full-featured GUI for downloading daily data for stocks and indices",
             lambda: self.launch_script('yahoo_finance_service/launch_downloader.py')),
            ("📊 Chart Visualizer & Downloader",
             "Download data and visualize charts with technical indicators",
             lambda: self.launch_script('yahoo_finance_service/launch_chart_visualizer.py')),
            ("⚡ Bulk Stock Downloader",
             "Download data for multiple stocks in bulk with progress tracking",
             lambda: self.launch_script('yahoo_finance_service/bulk_stock_downloader.py')),
        ])
        
        # Section 2: Quick Download Scripts
        self.create_section(scrollable_frame, "⚡ Quick Download Scripts", [
            ("📅 Check & Update Daily Quotes",
             "Check latest data and download missing dates till today",
             lambda: self.launch_script('check_and_update_daily_quotes.py')),
            ("📆 Quick Download Today's Data",
             "Quick download of today's data for all symbols in database",
             lambda: self.launch_script('quick_download_today.py')),
            ("🔢 Quick Download Nifty 500",
             "Download last 7 days of data for all Nifty 500 stocks",
             lambda: self.launch_script('quick_download_nifty500.py')),
            ("📊 Download Nifty 500 Bulk (5 Years)",
             "Bulk download 5 years of data for all Nifty 500 stocks",
             lambda: self.launch_script('download_nifty500_bulk.py')),
            ("🔍 Download Indices Data",
             "Download historical data for NSE indices",
             lambda: self.launch_script('download_indices_data.py')),
            ("📈 Download Indices Today",
             "Download today's data for all NSE indices",
             lambda: self.launch_script('download_indices_today.py')),
        ])
        
        # Section 3: Smart Download Tools
        self.create_section(scrollable_frame, "🧠 Smart Download Tools", [
            ("🎯 Smart Download (CLI)",
             "Smart downloader with duplicate prevention and gap filling",
             lambda: self.launch_script('yahoo_finance_service/smart_download.py', 
                                      '--help', 'Smart Download Help')),
            ("🔧 Symbol Mapping Validator",
             "Validate NSE to Yahoo Finance symbol mappings",
             lambda: self.launch_script('yahoo_finance_service/validate_symbol_mapping.py')),
        ])
        
    def create_diagnostics_tab(self, notebook):
        """Tab 2: Data Quality & Diagnostics"""
        tab = tk.Frame(notebook, bg='#0f0f23')
        notebook.add(tab, text='🔍 Diagnostics')
        
        canvas = tk.Canvas(tab, bg='#0f0f23', highlightthickness=0)
        scrollbar = ttk.Scrollbar(tab, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg='#0f0f23')
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True, padx=10, pady=10)
        scrollbar.pack(side="right", fill="y")
        
        # Section: Data Completeness Checks
        self.create_section(scrollable_frame, "✅ Data Completeness Checks", [
            ("📊 Check All Symbols Completeness",
             "Comprehensive check of data completeness for all symbols",
             lambda: self.launch_script('check_all_symbols_completeness.py')),
            ("🔢 Check Nifty 500 Yesterday's Data",
             "Check which Nifty 500 stocks have yesterday's data",
             lambda: self.launch_script('check_nifty500_yesterday.py')),
            ("📈 Check Previous Close Coverage",
             "Check previous close data coverage for Nifty 500",
             lambda: self.launch_script('check_prevclose_coverage.py')),
            ("🎯 Check Nifty 500 Coverage",
             "Check overall coverage of Nifty 500 stocks",
             lambda: self.launch_script('check_nifty500_coverage.py')),
        ])
        
        # Section: Symbol & Mapping Checks
        self.create_section(scrollable_frame, "🔗 Symbol & Mapping Checks", [
            ("📋 Analyze Symbol Formats",
             "Analyze symbol formats in yfinance_daily_quotes table",
             lambda: self.launch_script('analyze_symbol_formats.py')),
            ("🗺️ Check Symbol Mappings",
             "Check NSE to Yahoo Finance symbol mappings",
             lambda: self.launch_script('check_nifty500_symbol_mapping.py')),
            ("✓ Check Active Symbols",
             "Check active symbol status in mapping table",
             lambda: self.launch_script('check_active_symbols.py')),
            ("🔍 Find Optimal Symbol List",
             "Find optimal list of symbols with complete data",
             lambda: self.launch_script('find_optimal_symbol_list.py')),
        ])
        
        # Section: Database Checks
        self.create_section(scrollable_frame, "💾 Database Checks", [
            ("📊 Check Indices Tables",
             "Check structure and data in indices tables",
             lambda: self.launch_script('check_indices_tables.py')),
            ("📈 Check Indices Download Status",
             "Check download status of NSE indices",
             lambda: self.launch_script('check_indices_download_status.py')),
            ("📏 Check Data Size",
             "Check size of yfinance tables in database",
             lambda: self.launch_script('check_data_size.py')),
            ("🔧 Check Table Structures",
             "Verify table structures are correct",
             lambda: self.launch_script('check_structures.py')),
        ])
        
        # Section: Specific Symbol Checks
        self.create_section(scrollable_frame, "🎯 Specific Symbol Checks", [
            ("📊 Check NIFTY Today",
             "Check NIFTY (^NSEI) real-time data availability",
             lambda: self.launch_script('check_nifty_today.py')),
            ("🔍 Check YFinance Symbols",
             "List all symbols in yfinance tables",
             lambda: self.launch_script('check_yfinance_symbols.py')),
            ("📈 Test Chart Data",
             "Test chart data retrieval for sample symbols",
             lambda: self.launch_script('test_chart_data.py')),
        ])
        
    def create_realtime_tab(self, notebook):
        """Tab 3: Real-time Market Data"""
        tab = tk.Frame(notebook, bg='#0f0f23')
        notebook.add(tab, text='⚡ Real-time Data')
        
        canvas = tk.Canvas(tab, bg='#0f0f23', highlightthickness=0)
        scrollbar = ttk.Scrollbar(tab, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg='#0f0f23')
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True, padx=10, pady=10)
        scrollbar.pack(side="right", fill="y")
        
        # Section: Real-time Dashboards
        self.create_section(scrollable_frame, "📊 Real-time Dashboards", [
            ("🎯 Real-time Advance-Decline Dashboard",
             "Live market breadth tracking for Nifty 500 stocks",
             lambda: self.launch_script('realtime_adv_decl_dashboard.py')),
            ("📈 Intraday Advance-Decline Viewer",
             "View historical intraday advance-decline data",
             lambda: self.launch_script('intraday_adv_decl_viewer.py')),
            ("📊 Intraday 1-Min Viewer",
             "View 1-minute intraday candle data",
             lambda: self.launch_script('intraday_1min_viewer.py')),
            ("📉 Intraday Candlestick Viewer",
             "View intraday candlestick charts",
             lambda: self.launch_script('realtime_yahoo_service/realtime_candlestick_viewer.py')),
        ])
        
        # Section: Real-time Services
        self.create_section(scrollable_frame, "⚙️ Real-time Services", [
            ("🚀 Real-time Yahoo Finance Service",
             "Advanced real-time data streaming service (Event-driven)",
             lambda: self.launch_realtime_service()),
            ("📡 Check Service Status",
             "Check if real-time service is running",
             lambda: self.launch_script('realtime_yahoo_service/check_service_status.py')),
            ("🌐 Real-time Dashboard (HTML)",
             "Open real-time web dashboard in browser",
             lambda: self.open_html_dashboard()),
        ])
        
        # Section: Market Breadth Analysis
        self.create_section(scrollable_frame, "📊 Market Breadth Analysis", [
            ("📈 Nifty 500 Advance-Decline Calculator",
             "Calculate advance-decline metrics for Nifty 500",
             lambda: self.launch_script('nifty500_adv_decl_calculator.py')),
            ("📊 Nifty 500 Advance-Decline Visualizer",
             "Visualize advance-decline trends",
             lambda: self.launch_script('nifty500_adv_decl_visualizer.py')),
            ("🔄 Test Market Breadth Integration",
             "Test market breadth system integration",
             lambda: self.launch_script('test_market_breadth_integration.py')),
        ])
        
    def create_analysis_tab(self, notebook):
        """Tab 4: Data Analysis & Reports"""
        tab = tk.Frame(notebook, bg='#0f0f23')
        notebook.add(tab, text='📈 Analysis')
        
        canvas = tk.Canvas(tab, bg='#0f0f23', highlightthickness=0)
        scrollbar = ttk.Scrollbar(tab, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg='#0f0f23')
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True, padx=10, pady=10)
        scrollbar.pack(side="right", fill="y")
        
        # Section: Chart Analysis
        self.create_section(scrollable_frame, "📊 Chart Analysis", [
            ("📈 Chart Visualizer",
             "Advanced charting with technical indicators",
             lambda: self.launch_script('yahoo_finance_service/chart_visualizer.py')),
            ("🎯 Stock Chart with Ratings",
             "View stock charts with trend ratings",
             lambda: self.launch_script('stock_chart_with_ratings.py')),
            ("🚀 Launch Stock Charts",
             "Quick access to stock charting tools",
             lambda: self.launch_script('launch_stock_charts.py')),
        ])
        
        # Section: Scanner & Screeners
        self.create_section(scrollable_frame, "🔍 Scanners & Screeners", [
            ("🎯 Nifty 500 Momentum Scanner",
             "Scan Nifty 500 for momentum patterns",
             lambda: self.launch_script('nifty500_momentum_scanner.py')),
            ("📊 Scanner GUI",
             "Main scanner interface for pattern detection",
             lambda: self.launch_script('scanner_gui.py')),
            ("📈 VCP Market Scanner",
             "Scan for Volatility Contraction Pattern (VCP)",
             lambda: self.launch_script('vcp_market_scanner.py')),
        ])
        
        # Section: PDF Reports
        self.create_section(scrollable_frame, "📄 PDF Reports", [
            ("📊 Nifty 500 Momentum Report (PDF)",
             "Generate comprehensive momentum analysis report",
             lambda: self.launch_script('nifty500_momentum_report.py')),
            ("📈 Nifty 50 Sector Report (PDF)",
             "Generate sectoral analysis report for Nifty 50",
             lambda: self.launch_script('nifty50_sector_report.py')),
            ("🎯 Demo PDF Reports",
             "Generate sample PDF reports with all features",
             lambda: self.launch_script('demo_pdf_reports.py')),
        ])
        
        # Section: Data Verification
        self.create_section(scrollable_frame, "✓ Data Verification", [
            ("📊 Verify Data Accuracy",
             "Verify accuracy of downloaded data",
             lambda: self.launch_script('verify_data_accuracy.py')),
            ("🔍 Quick Accuracy Check",
             "Quick check of data accuracy for sample symbols",
             lambda: self.launch_script('quick_accuracy_check.py')),
            ("📈 Test YFinance Connectivity",
             "Test connection to Yahoo Finance API",
             lambda: self.launch_script('test_yfinance_connectivity.py')),
        ])
        
    def create_maintenance_tab(self, notebook):
        """Tab 5: Database Maintenance"""
        tab = tk.Frame(notebook, bg='#0f0f23')
        notebook.add(tab, text='🔧 Maintenance')
        
        canvas = tk.Canvas(tab, bg='#0f0f23', highlightthickness=0)
        scrollbar = ttk.Scrollbar(tab, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg='#0f0f23')
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True, padx=10, pady=10)
        scrollbar.pack(side="right", fill="y")
        
        # Section: Database Setup
        self.create_section(scrollable_frame, "🗄️ Database Setup", [
            ("⚙️ Create YFinance Tables",
             "Create or update yfinance_daily_quotes table",
             lambda: self.launch_script('yahoo_finance_service/create_tables.py')),
            ("🔧 Setup YFinance Service",
             "Setup and test Yahoo Finance service configuration",
             lambda: self.launch_script('yahoo_finance_service/setup_yfinance.py')),
            ("📊 Create Indices Tables",
             "Create tables for NSE indices data",
             lambda: self.launch_script('create_indices_tables.py')),
        ])
        
        # Section: Symbol Management
        self.create_section(scrollable_frame, "🔗 Symbol Management", [
            ("📝 Create Symbol Mapping",
             "Create NSE to Yahoo Finance symbol mappings",
             lambda: self.launch_script('yahoo_finance_service/create_symbol_mapping.py')),
            ("🎯 Auto Map Nifty 500 to Yahoo",
             "Automatically map Nifty 500 symbols to Yahoo format",
             lambda: self.launch_script('auto_map_nifty500_to_yahoo.py')),
            ("📋 Update Symbol Mappings",
             "Update and verify symbol mappings",
             lambda: self.launch_script('update_symbol_mappings.py')),
            ("✓ Auto Verify Symbols",
             "Automatically verify all symbol mappings",
             lambda: self.launch_script('auto_verify_symbols.py')),
        ])
        
        # Section: Data Cleanup
        self.create_section(scrollable_frame, "🧹 Data Cleanup", [
            ("🔍 Rebuild Intraday Data",
             "Rebuild intraday 1-minute candle data",
             lambda: self.launch_script('rebuild_intraday_data.py')),
            ("⚡ Rebuild Intraday Full",
             "Full rebuild of all intraday data",
             lambda: self.launch_script('rebuild_intraday_full.py')),
            ("🔄 Refetch NIFTY Today",
             "Delete and refetch today's NIFTY data",
             lambda: self.launch_script('refetch_nifty_today.py')),
        ])
        
        # Section: Documentation
        self.create_section(scrollable_frame, "📚 Documentation", [
            ("📖 Duplicate Prevention Guide",
             "View documentation on duplicate prevention system",
             lambda: self.open_file('yahoo_finance_service/DUPLICATE_PREVENTION.md')),
            ("📘 Chart Visualizer README",
             "View chart visualizer documentation",
             lambda: self.open_file('yahoo_finance_service/CHART_VISUALIZER_README.md')),
            ("📗 Real-time Dashboard History",
             "View real-time dashboard version history",
             lambda: self.open_file('REALTIME_DASHBOARD_VERSION_HISTORY.md')),
            ("📕 Market Breadth Features",
             "View market breadth system features",
             lambda: self.open_file('MARKET_BREADTH_FEATURES.md')),
        ])
        
    def create_section(self, parent, title, buttons):
        """Create a section with title and buttons"""
        # Section frame
        section_frame = tk.Frame(parent, bg='#1a1a2e', relief=tk.RAISED, bd=2)
        section_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # Section title
        title_label = tk.Label(
            section_frame,
            text=title,
            font=('Segoe UI', 14, 'bold'),
            fg='#00d4ff',
            bg='#1a1a2e',
            anchor='w'
        )
        title_label.pack(fill=tk.X, padx=15, pady=(15, 10))
        
        # Buttons
        for btn_text, description, command in buttons:
            self.create_feature_button(section_frame, btn_text, description, command)
            
    def create_feature_button(self, parent, text, description, command):
        """Create a styled feature button with description"""
        btn_frame = tk.Frame(parent, bg='#1a1a2e')
        btn_frame.pack(fill=tk.X, padx=15, pady=5)
        
        # Button
        btn = tk.Button(
            btn_frame,
            text=text,
            font=('Segoe UI', 10, 'bold'),
            bg='#2a2a4e',
            fg='white',
            activebackground='#00d4ff',
            activeforeground='#0f0f23',
            relief=tk.FLAT,
            cursor='hand2',
            command=command,
            width=45,
            anchor='w',
            padx=15,
            pady=10
        )
        btn.pack(side=tk.LEFT, fill=tk.X)
        
        # Description
        desc_label = tk.Label(
            btn_frame,
            text=description,
            font=('Segoe UI', 9),
            fg='#888888',
            bg='#1a1a2e',
            anchor='w'
        )
        desc_label.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(10, 0))
        
        # Hover effects
        def on_enter(e):
            btn.config(bg='#00d4ff', fg='#0f0f23')
            
        def on_leave(e):
            btn.config(bg='#2a2a4e', fg='white')
            
        btn.bind("<Enter>", on_enter)
        btn.bind("<Leave>", on_leave)
        
    def launch_script(self, script_path, args='', title_suffix=''):
        """Launch a Python script in a new terminal window"""
        try:
            script_full_path = os.path.join(os.path.dirname(__file__), script_path)
            
            if not os.path.exists(script_full_path):
                messagebox.showerror(
                    "File Not Found",
                    f"Script not found:\n{script_full_path}"
                )
                return
            
            # Create title for window
            title = f"Yahoo Finance - {os.path.basename(script_path)}"
            if title_suffix:
                title += f" - {title_suffix}"
            
            # Launch in new PowerShell window with proper escaping
            # Use Start-Process with separate arguments to avoid quote issues
            script_dir = os.path.dirname(script_full_path)
            
            # Build the command to execute
            exec_cmd = f"cd '{script_dir}'; python '{script_full_path}' {args}"
            
            # Launch new PowerShell window
            subprocess.Popen([
                'powershell.exe',
                '-NoExit',
                '-Command',
                f"$host.UI.RawUI.WindowTitle = '{title}'; {exec_cmd}"
            ])
            
            self.status_label.config(
                text=f"Launched: {os.path.basename(script_path)} | {datetime.now().strftime('%H:%M:%S')}",
                fg='#00ff00'
            )
            
        except Exception as e:
            messagebox.showerror(
                "Launch Error",
                f"Failed to launch script:\n{str(e)}"
            )
            self.status_label.config(
                text=f"Error launching: {os.path.basename(script_path)} | {datetime.now().strftime('%H:%M:%S')}",
                fg='#ff0000'
            )
            
    def launch_realtime_service(self):
        """Launch the real-time Yahoo Finance service"""
        try:
            service_dir = os.path.join(os.path.dirname(__file__), 'realtime_yahoo_service')
            config_file = os.path.join(service_dir, 'config', 'local_test_with_db.yaml')
            
            if not os.path.exists(config_file):
                messagebox.showwarning(
                    "Config Not Found",
                    "Using default configuration.\nFor custom config, create:\nrealtime_yahoo_service/config/local_test_with_db.yaml"
                )
                config_file = os.path.join(service_dir, 'config', 'local_test.yaml')
            
            # Build command
            title = "Real-time Yahoo Finance Service"
            exec_cmd = f"cd '{service_dir}'; python main.py --config '{config_file}'"
            
            # Launch new PowerShell window
            subprocess.Popen([
                'powershell.exe',
                '-NoExit',
                '-Command',
                f"$host.UI.RawUI.WindowTitle = '{title}'; {exec_cmd}"
            ])
            
            self.status_label.config(
                text=f"Launched: Real-time Service | {datetime.now().strftime('%H:%M:%S')}",
                fg='#00ff00'
            )
            
        except Exception as e:
            messagebox.showerror(
                "Launch Error",
                f"Failed to launch real-time service:\n{str(e)}"
            )
            
    def open_html_dashboard(self):
        """Open the HTML dashboard in browser"""
        try:
            html_file = os.path.join(
                os.path.dirname(__file__),
                'realtime_yahoo_service',
                'dashboard.html'
            )
            
            if os.path.exists(html_file):
                import webbrowser
                webbrowser.open(f'file:///{html_file.replace(os.sep, "/")}')
                
                self.status_label.config(
                    text=f"Opened: HTML Dashboard | {datetime.now().strftime('%H:%M:%S')}",
                    fg='#00ff00'
                )
            else:
                messagebox.showerror(
                    "File Not Found",
                    "HTML dashboard not found:\nrealtime_yahoo_service/dashboard.html"
                )
                
        except Exception as e:
            messagebox.showerror(
                "Open Error",
                f"Failed to open HTML dashboard:\n{str(e)}"
            )
            
    def open_file(self, file_path):
        """Open a file with default application"""
        try:
            full_path = os.path.join(os.path.dirname(__file__), file_path)
            
            if os.path.exists(full_path):
                os.startfile(full_path)
                
                self.status_label.config(
                    text=f"Opened: {os.path.basename(file_path)} | {datetime.now().strftime('%H:%M:%S')}",
                    fg='#00ff00'
                )
            else:
                messagebox.showerror(
                    "File Not Found",
                    f"File not found:\n{full_path}"
                )
                
        except Exception as e:
            messagebox.showerror(
                "Open Error",
                f"Failed to open file:\n{str(e)}"
            )
            
    def run(self):
        """Start the dashboard"""
        self.root.mainloop()


def main():
    """Main entry point"""
    dashboard = YahooFinanceDashboard()
    dashboard.run()


if __name__ == '__main__':
    main()
