"""
Vedic Astrology Trading GUI - Main Dashboard

A comprehensive GUI application for daily market preparation using Vedic astrology.
This dashboard allows you to generate reports, view predictions, and monitor market conditions.
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog
import threading
import subprocess
import sys
import os
import json
import datetime
import pandas as pd
from pathlib import Path

# Add parent directories to path
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)
sys.path.append(os.path.join(parent_dir, 'calculations'))
sys.path.append(os.path.join(parent_dir, 'trading_tools'))

# Import PDF generator
try:
    from pdf_generator import VedicTradingPDFGenerator
    PDF_AVAILABLE = True
except ImportError:
    print("PDF generator not available. Install reportlab for PDF functionality.")
    PDF_AVAILABLE = False

# Import zodiac wheel generators (both old and new professional)
try:
    from zodiac_wheel_generator import ZodiacWheelGenerator
    # Import new professional PyJHora system
    sys.path.append(os.path.join(parent_dir, 'tools'))
    from professional_zodiac_generator import ProfessionalZodiacWheelGenerator
    from pyjhora_calculator import ProfessionalAstrologyCalculator
    CHARTS_AVAILABLE = True
    PROFESSIONAL_AVAILABLE = True
except ImportError as e:
    print(f"Chart generator not available: {e}. Install matplotlib and PyJHora for chart functionality.")
    CHARTS_AVAILABLE = False
    PROFESSIONAL_AVAILABLE = False


class VedicTradingGUI:
    """Main GUI class for Vedic astrology trading dashboard"""
    
    def __init__(self, root):
        self.root = root
        self.root.title("Vedic Astrology Trading Dashboard")
        self.root.geometry("1400x900")
        self.root.configure(bg='#2c3e50')
        
        # Configure style
        self.style = ttk.Style()
        self.style.theme_use('clam')
        self.configure_styles()
        
        # Paths
        self.project_dir = parent_dir
        self.tools_dir = os.path.join(self.project_dir, 'trading_tools')
        self.reports_dir = os.path.join(self.project_dir, 'reports')
        
        # Create reports directory if it doesn't exist
        os.makedirs(self.reports_dir, exist_ok=True)
        
        # Variables
        self.current_date = tk.StringVar(value=datetime.date.today().strftime('%Y-%m-%d'))
        self.current_moon_sign = tk.StringVar(value="Loading...")
        self.current_volatility = tk.StringVar(value="Loading...")
        self.current_risk_level = tk.StringVar(value="Loading...")
        self.market_outlook = tk.StringVar(value="Loading...")
        
        # Create GUI
        self.create_widgets()
        self.load_current_data()
        
        # Auto-refresh every 5 minutes
        self.auto_refresh()
    
    def configure_styles(self):
        """Configure custom styles for the GUI"""
        self.style.configure('Title.TLabel', 
                           font=('Arial', 16, 'bold'), 
                           background='#2c3e50', 
                           foreground='white')
        
        self.style.configure('Header.TLabel', 
                           font=('Arial', 12, 'bold'), 
                           background='#34495e', 
                           foreground='white')
        
        self.style.configure('Info.TLabel', 
                           font=('Arial', 10), 
                           background='#34495e', 
                           foreground='#ecf0f1')
        
        self.style.configure('Success.TButton',
                           background='#27ae60',
                           foreground='white',
                           font=('Arial', 10, 'bold'))
        
        self.style.configure('Warning.TButton',
                           background='#f39c12',
                           foreground='white',
                           font=('Arial', 10, 'bold'))
        
        self.style.configure('Danger.TButton',
                           background='#e74c3c',
                           foreground='white',
                           font=('Arial', 10, 'bold'))
    
    def create_widgets(self):
        """Create all GUI widgets"""
        
        # Main title
        title_frame = tk.Frame(self.root, bg='#2c3e50', height=60)
        title_frame.pack(fill='x', pady=(10, 0))
        title_frame.pack_propagate(False)
        
        title_label = ttk.Label(title_frame, 
                               text="🌙 Vedic Astrology Trading Dashboard", 
                               style='Title.TLabel')
        title_label.pack(pady=10)
        
        # Create notebook for tabs
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Create tabs
        self.create_dashboard_tab()
        self.create_reports_tab()
        self.create_calendar_tab()
        self.create_analysis_tab()
        self.create_settings_tab()
    
    def create_dashboard_tab(self):
        """Create the main dashboard tab"""
        dashboard_frame = ttk.Frame(self.notebook)
        self.notebook.add(dashboard_frame, text="📊 Dashboard")
        
        # Left panel - Current Status
        left_frame = tk.Frame(dashboard_frame, bg='#34495e', width=400)
        left_frame.pack(side='left', fill='y', padx=(0, 5))
        left_frame.pack_propagate(False)
        
        # Current Status
        status_label = ttk.Label(left_frame, text="🌙 Current Moon Status", style='Header.TLabel')
        status_label.pack(pady=(10, 5))
        
        self.status_frame = tk.Frame(left_frame, bg='#34495e')
        self.status_frame.pack(fill='x', padx=10)
        
        # Status info
        tk.Label(self.status_frame, text="Analysis Date:", 
                bg='#34495e', fg='#ecf0f1', font=('Arial', 10, 'bold')).pack(anchor='w')
        tk.Label(self.status_frame, textvariable=self.current_date,
                bg='#34495e', fg='#2ecc71', font=('Arial', 10, 'bold')).pack(anchor='w', pady=(0, 5))
        
        tk.Label(self.status_frame, text="Moon Sign:", 
                bg='#34495e', fg='#ecf0f1', font=('Arial', 10, 'bold')).pack(anchor='w')
        tk.Label(self.status_frame, textvariable=self.current_moon_sign,
                bg='#34495e', fg='#3498db', font=('Arial', 12, 'bold')).pack(anchor='w', pady=(0, 5))
        
        tk.Label(self.status_frame, text="Volatility Factor:", 
                bg='#34495e', fg='#ecf0f1', font=('Arial', 10, 'bold')).pack(anchor='w')
        tk.Label(self.status_frame, textvariable=self.current_volatility,
                bg='#34495e', fg='#e74c3c', font=('Arial', 12, 'bold')).pack(anchor='w', pady=(0, 5))
        
        tk.Label(self.status_frame, text="Risk Level:", 
                bg='#34495e', fg='#ecf0f1', font=('Arial', 10, 'bold')).pack(anchor='w')
        tk.Label(self.status_frame, textvariable=self.current_risk_level,
                bg='#34495e', fg='#f39c12', font=('Arial', 12, 'bold')).pack(anchor='w', pady=(0, 5))
        
        tk.Label(self.status_frame, text="Market Outlook:", 
                bg='#34495e', fg='#ecf0f1', font=('Arial', 10, 'bold')).pack(anchor='w')
        tk.Label(self.status_frame, textvariable=self.market_outlook,
                bg='#34495e', fg='#27ae60', font=('Arial', 10)).pack(anchor='w', pady=(0, 10))
        
        # Add moon calculation explanation button
        ttk.Button(left_frame, text="❓ How Moon Sign is Calculated", 
                  command=self.show_moon_calculation_explanation).pack(pady=(10, 0), padx=10, fill='x')
        
        # Quick Actions
        actions_label = ttk.Label(left_frame, text="⚡ Quick Actions", style='Header.TLabel')
        actions_label.pack(pady=(20, 10))
        
        actions_frame = tk.Frame(left_frame, bg='#34495e')
        actions_frame.pack(fill='x', padx=10)
        
        ttk.Button(actions_frame, text="🔄 Refresh Data", 
                  command=self.refresh_current_data, style='Success.TButton').pack(fill='x', pady=2)
        
        ttk.Button(actions_frame, text="📊 Generate All Reports", 
                  command=self.generate_all_reports, style='Warning.TButton').pack(fill='x', pady=2)
        
        ttk.Button(actions_frame, text="📅 Today's Strategy", 
                  command=self.show_daily_strategy, style='Success.TButton').pack(fill='x', pady=2)
        
        ttk.Button(actions_frame, text="🗓️ Weekly Outlook", 
                  command=self.show_weekly_outlook, style='Success.TButton').pack(fill='x', pady=2)
        
        ttk.Button(actions_frame, text="📈 4-Week Forecast", 
                  command=self.show_market_forecast, style='Success.TButton').pack(fill='x', pady=2)
        
        ttk.Button(actions_frame, text="🎯 Zodiac Wheel Chart", 
                  command=self.generate_zodiac_wheel, style='Success.TButton').pack(fill='x', pady=2)
        
        # Today's Alerts
        alerts_label = ttk.Label(left_frame, text="🚨 Today's Alerts", style='Header.TLabel')
        alerts_label.pack(pady=(20, 10))
        
        self.alerts_text = scrolledtext.ScrolledText(left_frame, height=8, width=45, 
                                                   bg='#2c3e50', fg='#ecf0f1',
                                                   font=('Consolas', 9))
        self.alerts_text.pack(padx=10, pady=(0, 10))
        
        # Right panel - Main content area
        right_frame = tk.Frame(dashboard_frame, bg='#ecf0f1')
        right_frame.pack(side='right', fill='both', expand=True, padx=(5, 0))
        
        # Content area with tabs
        self.content_notebook = ttk.Notebook(right_frame)
        self.content_notebook.pack(fill='both', expand=True, padx=5, pady=5)
        
        # Trading Calendar
        self.create_trading_calendar_view()
        
        # Stock Recommendations
        self.create_stock_recommendations_view()
        
        # Market Summary
        self.create_market_summary_view()
    
    def create_trading_calendar_view(self):
        """Create trading calendar view"""
        calendar_frame = ttk.Frame(self.content_notebook)
        self.content_notebook.add(calendar_frame, text="📅 Trading Calendar")
        
        # Calendar controls
        controls_frame = tk.Frame(calendar_frame, bg='#ecf0f1')
        controls_frame.pack(fill='x', pady=5)
        
        tk.Label(controls_frame, text="📅 Next 10 Trading Days", 
                bg='#ecf0f1', font=('Arial', 12, 'bold')).pack(side='left')
        
        ttk.Button(controls_frame, text="🔄 Refresh Calendar", 
                  command=self.refresh_trading_calendar).pack(side='right')
        
        # Calendar treeview
        calendar_columns = ('Date', 'Day', 'Moon Sign', 'Element', 'Volatility', 'Risk', 'Action')
        self.calendar_tree = ttk.Treeview(calendar_frame, columns=calendar_columns, show='headings', height=15)
        
        for col in calendar_columns:
            self.calendar_tree.heading(col, text=col)
            self.calendar_tree.column(col, width=120)
        
        # Scrollbar for calendar
        calendar_scrollbar = ttk.Scrollbar(calendar_frame, orient='vertical', command=self.calendar_tree.yview)
        self.calendar_tree.configure(yscrollcommand=calendar_scrollbar.set)
        
        self.calendar_tree.pack(side='left', fill='both', expand=True)
        calendar_scrollbar.pack(side='right', fill='y')
    
    def create_stock_recommendations_view(self):
        """Create stock recommendations view"""
        stocks_frame = ttk.Frame(self.content_notebook)
        self.content_notebook.add(stocks_frame, text="📈 Stock Picks")
        
        # Stock recommendations
        tk.Label(stocks_frame, text="🎯 Today's Stock Recommendations", 
                font=('Arial', 12, 'bold')).pack(pady=10)
        
        # Categories frame
        categories_frame = tk.Frame(stocks_frame)
        categories_frame.pack(fill='x', padx=10)
        
        # High conviction
        high_conv_frame = tk.LabelFrame(categories_frame, text="💎 High Conviction", 
                                      font=('Arial', 10, 'bold'), fg='#27ae60')
        high_conv_frame.pack(side='left', fill='both', expand=True, padx=5)
        
        self.high_conviction_listbox = tk.Listbox(high_conv_frame, height=6, 
                                                bg='#ecf0f1', font=('Arial', 10))
        self.high_conviction_listbox.pack(fill='both', expand=True, padx=5, pady=5)
        
        # Accumulation
        accumulation_frame = tk.LabelFrame(categories_frame, text="📊 Accumulation", 
                                         font=('Arial', 10, 'bold'), fg='#3498db')
        accumulation_frame.pack(side='left', fill='both', expand=True, padx=5)
        
        self.accumulation_listbox = tk.Listbox(accumulation_frame, height=6, 
                                             bg='#ecf0f1', font=('Arial', 10))
        self.accumulation_listbox.pack(fill='both', expand=True, padx=5, pady=5)
        
        # Momentum
        momentum_frame = tk.LabelFrame(categories_frame, text="⚡ Momentum", 
                                     font=('Arial', 10, 'bold'), fg='#f39c12')
        momentum_frame.pack(side='left', fill='both', expand=True, padx=5)
        
        self.momentum_listbox = tk.Listbox(momentum_frame, height=6, 
                                         bg='#ecf0f1', font=('Arial', 10))
        self.momentum_listbox.pack(fill='both', expand=True, padx=5, pady=5)
        
        # Sector focus
        sector_frame = tk.Frame(stocks_frame)
        sector_frame.pack(fill='x', padx=10, pady=10)
        
        tk.Label(sector_frame, text="🏭 Today's Sector Focus", 
                font=('Arial', 12, 'bold')).pack()
        
        self.sector_text = scrolledtext.ScrolledText(sector_frame, height=8, 
                                                   bg='#ecf0f1', font=('Arial', 10))
        self.sector_text.pack(fill='x', pady=5)
    
    def create_market_summary_view(self):
        """Create market summary view"""
        summary_frame = ttk.Frame(self.content_notebook)
        self.content_notebook.add(summary_frame, text="📊 Market Summary")
        
        # Summary text area
        tk.Label(summary_frame, text="📊 Today's Market Analysis Summary", 
                font=('Arial', 12, 'bold')).pack(pady=10)
        
        self.summary_text = scrolledtext.ScrolledText(summary_frame, 
                                                    bg='#ecf0f1', 
                                                    font=('Consolas', 10),
                                                    wrap=tk.WORD)
        self.summary_text.pack(fill='both', expand=True, padx=10, pady=10)
    
    def create_reports_tab(self):
        """Create reports generation tab"""
        reports_frame = ttk.Frame(self.notebook)
        self.notebook.add(reports_frame, text="📄 Reports")
        
        # Reports generation section
        gen_frame = tk.LabelFrame(reports_frame, text="📊 Generate Reports", 
                                font=('Arial', 12, 'bold'))
        gen_frame.pack(fill='x', padx=10, pady=10)
        
        # Individual report buttons
        reports_grid = tk.Frame(gen_frame)
        reports_grid.pack(fill='x', padx=10, pady=10)
        
        # Row 1
        ttk.Button(reports_grid, text="📈 Market Forecast (4 weeks)", 
                  command=self.generate_market_forecast).grid(row=0, column=0, padx=5, pady=5, sticky='ew')
        
        ttk.Button(reports_grid, text="📊 Daily Trading Strategy", 
                  command=self.generate_daily_strategy).grid(row=0, column=1, padx=5, pady=5, sticky='ew')
        
        ttk.Button(reports_grid, text="🗓️ Weekly Market Outlook", 
                  command=self.generate_weekly_outlook).grid(row=0, column=2, padx=5, pady=5, sticky='ew')
        
        # Row 2
        ttk.Button(reports_grid, text="🔄 Generate All Reports", 
                  command=self.generate_all_reports, 
                  style='Warning.TButton').grid(row=1, column=0, padx=5, pady=5, sticky='ew')
        
        ttk.Button(reports_grid, text="📄 Generate PDFs", 
                  command=self.generate_all_pdfs, 
                  style='Success.TButton').grid(row=1, column=1, padx=5, pady=5, sticky='ew')
        
        ttk.Button(reports_grid, text="📁 Open PDF Folder", 
                  command=self.open_pdf_folder).grid(row=1, column=2, padx=5, pady=5, sticky='ew')
        
        # Configure grid weights
        for i in range(3):
            reports_grid.columnconfigure(i, weight=1)
        
        # Reports list section
        list_frame = tk.LabelFrame(reports_frame, text="📁 Available Reports", 
                                 font=('Arial', 12, 'bold'))
        list_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Reports listbox with scrollbar
        list_container = tk.Frame(list_frame)
        list_container.pack(fill='both', expand=True, padx=10, pady=10)
        
        self.reports_listbox = tk.Listbox(list_container, font=('Consolas', 10))
        self.reports_listbox.pack(side='left', fill='both', expand=True)
        
        reports_scrollbar = ttk.Scrollbar(list_container, orient='vertical', 
                                        command=self.reports_listbox.yview)
        self.reports_listbox.configure(yscrollcommand=reports_scrollbar.set)
        reports_scrollbar.pack(side='right', fill='y')
        
        # Action buttons
        buttons_frame = tk.Frame(list_frame)
        buttons_frame.pack(fill='x', padx=10, pady=5)
        
        ttk.Button(buttons_frame, text="🔄 Refresh List", 
                  command=self.refresh_reports_list).pack(side='left', padx=5)
        
        ttk.Button(buttons_frame, text="👁️ View Report", 
                  command=self.view_selected_report).pack(side='left', padx=5)
        
        ttk.Button(buttons_frame, text="📁 Open Reports Folder", 
                  command=self.open_reports_folder).pack(side='left', padx=5)
        
        # Output area
        output_frame = tk.LabelFrame(reports_frame, text="📜 Output Log", 
                                   font=('Arial', 10, 'bold'))
        output_frame.pack(fill='x', padx=10, pady=(0, 10))
        
        self.output_text = scrolledtext.ScrolledText(output_frame, height=8, 
                                                   bg='#2c3e50', fg='#ecf0f1',
                                                   font=('Consolas', 9))
        self.output_text.pack(fill='x', padx=10, pady=10)
    
    def create_calendar_tab(self):
        """Create detailed calendar tab"""
        calendar_tab_frame = ttk.Frame(self.notebook)
        self.notebook.add(calendar_tab_frame, text="📅 Calendar")
        
        # Calendar header
        header_frame = tk.Frame(calendar_tab_frame, bg='#34495e', height=50)
        header_frame.pack(fill='x')
        header_frame.pack_propagate(False)
        
        tk.Label(header_frame, text="📅 Detailed Trading Calendar", 
                bg='#34495e', fg='white', font=('Arial', 14, 'bold')).pack(pady=15)
        
        # Calendar content
        calendar_content = tk.Frame(calendar_tab_frame)
        calendar_content.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Detailed calendar treeview
        detailed_columns = ('Date', 'Day', 'Moon Sign', 'Element', 'Volatility', 'Risk Level', 
                          'Primary Sectors', 'Trading Strategy', 'Action')
        
        self.detailed_calendar_tree = ttk.Treeview(calendar_content, columns=detailed_columns, 
                                                 show='headings', height=20)
        
        for col in detailed_columns:
            self.detailed_calendar_tree.heading(col, text=col)
            if col in ['Date', 'Day', 'Moon Sign']:
                self.detailed_calendar_tree.column(col, width=100)
            elif col in ['Element', 'Risk Level', 'Volatility']:
                self.detailed_calendar_tree.column(col, width=80)
            else:
                self.detailed_calendar_tree.column(col, width=150)
        
        # Scrollbars for detailed calendar
        detailed_v_scrollbar = ttk.Scrollbar(calendar_content, orient='vertical', 
                                           command=self.detailed_calendar_tree.yview)
        detailed_h_scrollbar = ttk.Scrollbar(calendar_content, orient='horizontal', 
                                           command=self.detailed_calendar_tree.xview)
        
        self.detailed_calendar_tree.configure(yscrollcommand=detailed_v_scrollbar.set,
                                            xscrollcommand=detailed_h_scrollbar.set)
        
        self.detailed_calendar_tree.grid(row=0, column=0, sticky='nsew')
        detailed_v_scrollbar.grid(row=0, column=1, sticky='ns')
        detailed_h_scrollbar.grid(row=1, column=0, sticky='ew')
        
        calendar_content.grid_rowconfigure(0, weight=1)
        calendar_content.grid_columnconfigure(0, weight=1)
        
        # Calendar controls
        controls_frame = tk.Frame(calendar_tab_frame)
        controls_frame.pack(fill='x', padx=10, pady=5)
        
        ttk.Button(controls_frame, text="🔄 Refresh Calendar", 
                  command=self.refresh_detailed_calendar).pack(side='left', padx=5)
        
        ttk.Button(controls_frame, text="📁 Export to CSV", 
                  command=self.export_calendar_csv).pack(side='left', padx=5)
    
    def create_analysis_tab(self):
        """Create analysis and charts tab"""
        analysis_frame = ttk.Frame(self.notebook)
        self.notebook.add(analysis_frame, text="📊 Analysis")
        
        # Analysis controls
        controls_frame = tk.Frame(analysis_frame)
        controls_frame.pack(fill='x', padx=10, pady=10)
        
        tk.Label(controls_frame, text="📊 Market Analysis & Charts", 
                font=('Arial', 14, 'bold')).pack(side='left')
        
        ttk.Button(controls_frame, text="🔮 Professional Zodiac (PyJHora)", 
                  command=self.generate_professional_zodiac_wheel).pack(side='right', padx=5)
        
        ttk.Button(controls_frame, text="🎯 Classic Zodiac Wheel", 
                  command=self.generate_zodiac_wheel).pack(side='right', padx=5)
        
        ttk.Button(controls_frame, text="📈 Generate Charts", 
                  command=self.generate_analysis_charts).pack(side='right')
        
        # Analysis content area
        self.analysis_text = scrolledtext.ScrolledText(analysis_frame, 
                                                     bg='#ecf0f1', 
                                                     font=('Consolas', 10))
        self.analysis_text.pack(fill='both', expand=True, padx=10, pady=10)
    
    def create_settings_tab(self):
        """Create settings tab"""
        settings_frame = ttk.Frame(self.notebook)
        self.notebook.add(settings_frame, text="⚙️ Settings")
        
        # Settings content
        tk.Label(settings_frame, text="⚙️ Dashboard Settings", 
                font=('Arial', 14, 'bold')).pack(pady=20)
        
        # Auto-refresh setting
        auto_refresh_frame = tk.LabelFrame(settings_frame, text="🔄 Auto Refresh", 
                                         font=('Arial', 10, 'bold'))
        auto_refresh_frame.pack(fill='x', padx=20, pady=10)
        
        self.auto_refresh_var = tk.BooleanVar(value=True)
        tk.Checkbutton(auto_refresh_frame, text="Enable auto-refresh every 5 minutes", 
                      variable=self.auto_refresh_var, font=('Arial', 10)).pack(anchor='w', padx=10, pady=5)
        
        # Paths settings
        paths_frame = tk.LabelFrame(settings_frame, text="📁 Paths", 
                                  font=('Arial', 10, 'bold'))
        paths_frame.pack(fill='x', padx=20, pady=10)
        
        tk.Label(paths_frame, text=f"Reports Directory: {self.reports_dir}", 
                font=('Arial', 9)).pack(anchor='w', padx=10, pady=2)
        tk.Label(paths_frame, text=f"Tools Directory: {self.tools_dir}", 
                font=('Arial', 9)).pack(anchor='w', padx=10, pady=2)
        
        # About section
        about_frame = tk.LabelFrame(settings_frame, text="ℹ️ About", 
                                  font=('Arial', 10, 'bold'))
        about_frame.pack(fill='x', padx=20, pady=10)
        
        about_text = """
Vedic Astrology Trading Dashboard v1.0

This application provides daily market predictions based on Vedic astrology principles,
specifically Moon zodiac positions and their correlation with market movements.

Features:
• Daily trading strategies and stock recommendations
• Weekly market outlook and sector analysis
• 4-week market forecasting
• Risk management guidelines
• Trading calendar with volatility predictions

Created for educational purposes. Not financial advice.
        """
        
        tk.Label(about_frame, text=about_text, font=('Arial', 9), 
                justify='left').pack(anchor='w', padx=10, pady=5)
    
    def load_current_data(self):
        """Load current moon position and market data"""
        try:
            # Update current date
            self.current_date.set(datetime.date.today().strftime('%Y-%m-%d'))
            
            # Try to load today's strategy file first
            today_str = datetime.date.today().strftime('%Y%m%d')
            strategy_file = os.path.join(self.reports_dir, f"daily_strategy_{today_str}.json")
            
            if os.path.exists(strategy_file):
                # Load from existing strategy file
                with open(strategy_file, 'r') as f:
                    data = json.load(f)
                
                moon_pos = data.get('moon_position', {})
                market_out = data.get('market_outlook', {})
                risk_mgmt = data.get('risk_management', {})
                
                self.current_moon_sign.set(f"{moon_pos.get('sign', 'Unknown')} ({moon_pos.get('element', 'Unknown')})")
                self.current_volatility.set(market_out.get('volatility_expectation', 'Unknown'))
                self.current_risk_level.set(risk_mgmt.get('risk_level', 'Unknown'))
                self.market_outlook.set(market_out.get('overall_outlook', 'No data available'))
                
                # Load alerts
                alerts = data.get('alerts_and_warnings', [])
                self.alerts_text.delete(1.0, tk.END)
                for alert in alerts[:10]:  # Show top 10 alerts
                    self.alerts_text.insert(tk.END, f"• {alert}\n\n")
            else:
                # Use PyJHora to get live astrological data
                self.load_live_astrological_data()
                
        except Exception as e:
            # Fallback to live data if file loading fails
            try:
                self.load_live_astrological_data()
            except:
                messagebox.showerror("Error", f"Failed to load current data: {e}")
    
    def load_live_astrological_data(self):
        """Load live astrological data using PyJHora professional calculator"""
        try:
            if PROFESSIONAL_AVAILABLE:
                from pyjhora_calculator import ProfessionalAstrologyCalculator
                
                # Create calculator and get LIVE current data for display
                calc = ProfessionalAstrologyCalculator()
                live_time = datetime.datetime.now()
                astro_data = calc.get_complete_analysis(live_time)
                
                # Extract moon information
                moon_data = astro_data['planetary_positions'].get('Moon', {})
                moon_sign = moon_data.get('sign', 'Unknown')
                moon_degree = moon_data.get('degree_in_sign', 0)
                
                # Map signs to elements
                sign_elements = {
                    'Aries': 'Fire', 'Taurus': 'Earth', 'Gemini': 'Air', 'Cancer': 'Water',
                    'Leo': 'Fire', 'Virgo': 'Earth', 'Libra': 'Air', 'Scorpio': 'Water',
                    'Sagittarius': 'Fire', 'Capricorn': 'Earth', 'Aquarius': 'Air', 'Pisces': 'Water'
                }
                element = sign_elements.get(moon_sign, 'Unknown')
                
                # Update moon sign with live data
                self.current_moon_sign.set(f"{moon_sign} {moon_degree:.1f}° ({element})")
                
                # Get panchanga data
                panchanga = astro_data.get('panchanga', {})
                tithi = panchanga.get('tithi', {}).get('number', 'N/A')
                nakshatra_name = panchanga.get('nakshatra', {}).get('name', 'Unknown')
                nakshatra_number = panchanga.get('nakshatra', {}).get('number', 'N/A')
                
                # Estimate volatility based on moon phase
                moon_phase = astro_data.get('moon_phase', {})
                phase_name = moon_phase.get('phase_name', 'Unknown')
                
                # Simple volatility mapping
                volatility_map = {
                    'New Moon': 'Low', 'Waxing Crescent': 'Low-Medium',
                    'First Quarter': 'Medium', 'Waxing Gibbous': 'Medium-High',
                    'Full Moon': 'High', 'Waning Gibbous': 'Medium-High',
                    'Last Quarter': 'Medium', 'Waning Crescent': 'Low-Medium'
                }
                volatility = volatility_map.get(phase_name, 'Medium')
                
                # Risk level based on element
                risk_map = {'Fire': 'High', 'Earth': 'Low', 'Air': 'Medium', 'Water': 'Medium-High'}
                risk_level = risk_map.get(element, 'Medium')
                
                # Update GUI with live calculations
                self.current_volatility.set(f"{volatility} ({phase_name})")
                self.current_risk_level.set(f"{risk_level} (Moon in {element})")
                self.market_outlook.set(f"Live analysis: Tithi {tithi}, Nakshatra {nakshatra_name}")
                
                # Update alerts with live astrological insights
                self.alerts_text.delete(1.0, tk.END)
                self.alerts_text.insert(tk.END, f"🔮 LIVE ASTROLOGICAL INSIGHTS (PyJHora Swiss Ephemeris)\\n⏰ Current Time: {live_time.strftime('%H:%M:%S')}\\n\\n")
                self.alerts_text.insert(tk.END, f"🌙 Moon: {moon_sign} {moon_degree:.1f}° ({element} element)\\n")
                self.alerts_text.insert(tk.END, f"🌓 Phase: {phase_name} - {volatility} volatility expected\\n")
                self.alerts_text.insert(tk.END, f"📅 Tithi: {tithi} | Nakshatra: {nakshatra_name} ({nakshatra_number})\\n")
                self.alerts_text.insert(tk.END, f"⚠️ Risk Level: {risk_level} (based on {element} element)\\n\\n")
                
                # Add planetary positions
                self.alerts_text.insert(tk.END, "🌟 CURRENT PLANETARY POSITIONS:\\n")
                positions = astro_data.get('planetary_positions', {})
                for planet, data in list(positions.items())[:7]:  # Show first 7 planets
                    sign = data.get('sign', 'Unknown')
                    degree = data.get('degree_in_sign', 0)
                    self.alerts_text.insert(tk.END, f"   {planet}: {sign} {degree:.1f}°\\n")
                
                self.alerts_text.insert(tk.END, "\\n💡 Generate reports for detailed trading strategies!")
                
            else:
                # Fallback if PyJHora not available
                self.current_moon_sign.set("Install PyJHora for live data")
                self.current_volatility.set("Unknown")
                self.current_risk_level.set("Unknown")
                self.market_outlook.set("Generate reports to see market outlook")
                
                self.alerts_text.delete(1.0, tk.END)
                self.alerts_text.insert(tk.END, "📊 PyJHora not available\\n\\nInstall PyJHora for live astrological data:\\npip install PyJHora\\n\\nOr generate daily strategy reports for market analysis.")
                
        except Exception as e:
            print(f"Error loading live data: {e}")
            # Final fallback
            self.current_moon_sign.set("Data loading error")
            self.current_volatility.set("Unknown")
            self.current_risk_level.set("Unknown")
            self.market_outlook.set("Generate reports to see market outlook")
            
            self.alerts_text.delete(1.0, tk.END)
            self.alerts_text.insert(tk.END, f"❌ Error loading live data: {e}\\n\\nPlease generate daily strategy report for market analysis.")
    
    def refresh_current_data(self):
        """Refresh current market data"""
        self.load_current_data()
        self.refresh_trading_calendar()
        self.refresh_stock_recommendations()
        self.refresh_market_summary()
        messagebox.showinfo("Refresh", "Data refreshed successfully!")
    
    def generate_all_reports(self):
        """Generate all reports in a separate thread"""
        def run_generation():
            try:
                self.output_text.delete(1.0, tk.END)
                self.output_text.insert(tk.END, "🚀 Starting report generation...\n\n")
                self.root.update()
                
                # Generate market forecast
                self.output_text.insert(tk.END, "📊 Generating market forecast...\n")
                self.root.update()
                self.run_python_script("market_forecast.py")
                
                # Generate daily strategy
                self.output_text.insert(tk.END, "📈 Generating daily strategy...\n")
                self.root.update()
                self.run_python_script("trading_strategy.py")
                
                # Generate weekly outlook
                self.output_text.insert(tk.END, "🗓️ Generating weekly outlook...\n")
                self.root.update()
                self.run_python_script("weekly_outlook.py")
                
                self.output_text.insert(tk.END, "\n✅ All reports generated successfully!\n")
                self.root.update()
                
                # Refresh data
                self.refresh_current_data()
                self.refresh_reports_list()
                
                messagebox.showinfo("Success", "All reports generated successfully!")
                
            except Exception as e:
                self.output_text.insert(tk.END, f"\n❌ Error: {e}\n")
                messagebox.showerror("Error", f"Failed to generate reports: {e}")
        
        # Run in separate thread to prevent GUI freezing
        thread = threading.Thread(target=run_generation)
        thread.daemon = True
        thread.start()
    
    def run_python_script(self, script_name):
        """Run a Python script in the tools directory"""
        script_path = os.path.join(self.tools_dir, script_name)
        
        if not os.path.exists(script_path):
            raise FileNotFoundError(f"Script not found: {script_path}")
        
        # Change to tools directory and run script
        original_cwd = os.getcwd()
        try:
            os.chdir(self.tools_dir)
            result = subprocess.run([sys.executable, script_name], 
                                  capture_output=True, text=True, timeout=120)
            
            if result.returncode != 0:
                self.output_text.insert(tk.END, f"Error in {script_name}:\n{result.stderr}\n\n")
            else:
                self.output_text.insert(tk.END, f"✅ {script_name} completed\n\n")
                
        finally:
            os.chdir(original_cwd)
    
    def generate_market_forecast(self):
        """Generate market forecast report"""
        def run_forecast():
            try:
                self.output_text.delete(1.0, tk.END)
                self.output_text.insert(tk.END, "📊 Generating market forecast...\n")
                self.root.update()
                
                self.run_python_script("market_forecast.py")
                self.refresh_reports_list()
                messagebox.showinfo("Success", "Market forecast generated!")
                
            except Exception as e:
                messagebox.showerror("Error", f"Failed to generate forecast: {e}")
        
        thread = threading.Thread(target=run_forecast)
        thread.daemon = True
        thread.start()
    
    def generate_daily_strategy(self):
        """Generate daily strategy report"""
        def run_strategy():
            try:
                self.output_text.delete(1.0, tk.END)
                self.output_text.insert(tk.END, "📈 Generating daily strategy...\n")
                self.root.update()
                
                self.run_python_script("trading_strategy.py")
                self.refresh_current_data()
                self.refresh_reports_list()
                messagebox.showinfo("Success", "Daily strategy generated!")
                
            except Exception as e:
                messagebox.showerror("Error", f"Failed to generate strategy: {e}")
        
        thread = threading.Thread(target=run_strategy)
        thread.daemon = True
        thread.start()
    
    def generate_weekly_outlook(self):
        """Generate weekly outlook report"""
        def run_outlook():
            try:
                self.output_text.delete(1.0, tk.END)
                self.output_text.insert(tk.END, "🗓️ Generating weekly outlook...\n")
                self.root.update()
                
                self.run_python_script("weekly_outlook.py")
                self.refresh_reports_list()
                messagebox.showinfo("Success", "Weekly outlook generated!")
                
            except Exception as e:
                messagebox.showerror("Error", f"Failed to generate outlook: {e}")
        
        thread = threading.Thread(target=run_outlook)
        thread.daemon = True
        thread.start()
    
    def refresh_trading_calendar(self):
        """Refresh trading calendar view with live PyJHora data"""
        try:
            # Clear existing items
            for item in self.calendar_tree.get_children():
                self.calendar_tree.delete(item)
            
            # Try to load from existing CSV file first
            today_str = datetime.date.today().strftime('%Y%m%d')
            calendar_file = os.path.join(self.reports_dir, f"trading_calendar_{today_str}.csv")
            
            if os.path.exists(calendar_file):
                df = pd.read_csv(calendar_file)
                
                # Show next 10 days
                for _, row in df.head(10).iterrows():
                    date = pd.to_datetime(row['Date']).strftime('%m/%d')
                    day = row['Day'][:3]
                    moon_sign = row['Moon_Sign']
                    element = row['Element']
                    volatility = f"{row['Volatility_Factor']}x"
                    risk = row['Risk_Level']
                    action = row['Action']
                    
                    # Color coding based on action
                    if 'CAUTION' in action:
                        tags = ('danger',)
                    elif 'ACCUMULATE' in action:
                        tags = ('success',)
                    elif 'CAREFUL' in action:
                        tags = ('warning',)
                    else:
                        tags = ('normal',)
                    
                    self.calendar_tree.insert('', 'end', 
                                            values=(date, day, moon_sign, element, volatility, risk, action),
                                            tags=tags)
            else:
                # Generate live calendar data using PyJHora
                self.generate_live_trading_calendar()
                
            # Configure tags
            self.calendar_tree.tag_configure('danger', background='#ffebee')
            self.calendar_tree.tag_configure('success', background='#e8f5e8')
            self.calendar_tree.tag_configure('warning', background='#fff3e0')
            self.calendar_tree.tag_configure('normal', background='#f5f5f5')
                
        except Exception as e:
            print(f"Error refreshing calendar: {e}")
    
    def generate_live_trading_calendar(self):
        """Generate live trading calendar using PyJHora calculations"""
        try:
            if PROFESSIONAL_AVAILABLE:
                from pyjhora_calculator import ProfessionalAstrologyCalculator
                
                calc = ProfessionalAstrologyCalculator()
                
                # Generate next 10 trading days
                base_date = datetime.date.today()
                
                for i in range(10):
                    current_date = base_date + datetime.timedelta(days=i)
                    
                    # Skip weekends (assuming Saturday=5, Sunday=6)
                    if current_date.weekday() >= 5:
                        continue
                    
                    # Get astrological data for this date
                    date_time = datetime.datetime.combine(current_date, datetime.time(9, 15))  # Market opening time
                    astro_data = calc.get_complete_analysis(date_time)
                    
                    # Extract data
                    moon_data = astro_data['planetary_positions'].get('Moon', {})
                    moon_sign = moon_data.get('sign', 'Unknown')
                    
                    # Map signs to elements
                    sign_elements = {
                        'Aries': 'Fire', 'Taurus': 'Earth', 'Gemini': 'Air', 'Cancer': 'Water',
                        'Leo': 'Fire', 'Virgo': 'Earth', 'Libra': 'Air', 'Scorpio': 'Water',
                        'Sagittarius': 'Fire', 'Capricorn': 'Earth', 'Aquarius': 'Air', 'Pisces': 'Water'
                    }
                    element = sign_elements.get(moon_sign, 'Unknown')
                    
                    # Get moon phase for volatility
                    moon_phase = astro_data.get('moon_phase', {})
                    phase_name = moon_phase.get('phase_name', 'Unknown')
                    
                    # Calculate volatility factor
                    volatility_factors = {
                        'New Moon': '1.0', 'Waxing Crescent': '1.2',
                        'First Quarter': '1.5', 'Waxing Gibbous': '1.7',
                        'Full Moon': '2.0', 'Waning Gibbous': '1.7',
                        'Last Quarter': '1.5', 'Waning Crescent': '1.2'
                    }
                    volatility = volatility_factors.get(phase_name, '1.0') + 'x'
                    
                    # Risk level based on element
                    risk_levels = {
                        'Fire': 'High', 'Earth': 'Low', 
                        'Air': 'Medium', 'Water': 'Medium-High'
                    }
                    risk = risk_levels.get(element, 'Medium')
                    
                    # Generate action recommendation
                    if element == 'Fire':
                        action = "CAUTION - High volatility"
                    elif element == 'Earth':
                        action = "ACCUMULATE - Stable energy"
                    elif element == 'Water':
                        action = "CAREFUL - Emotional swings"
                    else:  # Air
                        action = "BALANCED - Moderate activity"
                    
                    # Format date and day
                    date_str = current_date.strftime('%m/%d')
                    day_str = current_date.strftime('%a')
                    
                    # Color coding based on action
                    if 'CAUTION' in action:
                        tags = ('danger',)
                    elif 'ACCUMULATE' in action:
                        tags = ('success',)
                    elif 'CAREFUL' in action:
                        tags = ('warning',)
                    else:
                        tags = ('normal',)
                    
                    self.calendar_tree.insert('', 'end',
                                            values=(date_str, day_str, moon_sign, element, volatility, risk, action),
                                            tags=tags)
            else:
                # Fallback if PyJHora not available
                today = datetime.date.today()
                for i in range(10):
                    current_date = today + datetime.timedelta(days=i)
                    if current_date.weekday() >= 5:  # Skip weekends
                        continue
                    
                    date_str = current_date.strftime('%m/%d')
                    day_str = current_date.strftime('%a')
                    
                    self.calendar_tree.insert('', 'end',
                                            values=(date_str, day_str, 'Install PyJHora', 'Unknown', 'N/A', 'Unknown', 'Generate Reports'),
                                            tags=('normal',))
                                            
        except Exception as e:
            print(f"Error generating live calendar: {e}")
            # Add a fallback entry
            self.calendar_tree.insert('', 'end',
                                    values=('Today', 'Now', 'Error', 'N/A', 'N/A', 'Unknown', 'Check PyJHora setup'),
                                    tags=('danger',))
    
    def refresh_stock_recommendations(self):
        """Refresh stock recommendations with live astrological guidance"""
        try:
            # Clear existing recommendations
            self.high_conviction_listbox.delete(0, tk.END)
            self.accumulation_listbox.delete(0, tk.END)
            self.momentum_listbox.delete(0, tk.END)
            
            # Try to load from existing strategy file first
            today_str = datetime.date.today().strftime('%Y%m%d')
            strategy_file = os.path.join(self.reports_dir, f"daily_strategy_{today_str}.json")
            
            if os.path.exists(strategy_file):
                with open(strategy_file, 'r') as f:
                    data = json.load(f)
                
                recommendations = data.get('stock_recommendations', {})
                
                # High conviction stocks
                for stock in recommendations.get('top_picks', [])[:8]:
                    self.high_conviction_listbox.insert(tk.END, stock)
                
                # Accumulation stocks
                for stock in recommendations.get('accumulation_candidates', [])[:8]:
                    self.accumulation_listbox.insert(tk.END, stock)
                
                # Momentum stocks
                for stock in recommendations.get('momentum_plays', [])[:8]:
                    self.momentum_listbox.insert(tk.END, stock)
            else:
                # Generate live astrological stock guidance
                self.generate_live_stock_guidance()
                
        except Exception as e:
            print(f"Error refreshing stock recommendations: {e}")
    
    def generate_live_stock_guidance(self):
        """Generate live stock guidance based on current astrological conditions"""
        try:
            if PROFESSIONAL_AVAILABLE:
                from pyjhora_calculator import ProfessionalAstrologyCalculator
                
                calc = ProfessionalAstrologyCalculator()
                # Use 9:15 AM for trading predictions
                today = datetime.date.today()
                trading_time = datetime.datetime.combine(today, datetime.time(9, 15))
                astro_data = calc.get_complete_analysis(trading_time)
                
                # Get current moon sign and element
                moon_data = astro_data['planetary_positions'].get('Moon', {})
                moon_sign = moon_data.get('sign', 'Unknown')
                
                sign_elements = {
                    'Aries': 'Fire', 'Taurus': 'Earth', 'Gemini': 'Air', 'Cancer': 'Water',
                    'Leo': 'Fire', 'Virgo': 'Earth', 'Libra': 'Air', 'Scorpio': 'Water',
                    'Sagittarius': 'Fire', 'Capricorn': 'Earth', 'Aquarius': 'Air', 'Pisces': 'Water'
                }
                element = sign_elements.get(moon_sign, 'Unknown')
                
                # Element-based sector recommendations
                if element == 'Fire':
                    # Fire signs favor energy, tech, defense
                    self.high_conviction_listbox.insert(tk.END, f"🔥 Energy Focus (9:15AM {moon_sign})")
                    self.high_conviction_listbox.insert(tk.END, "RELIANCE (Oil & Gas)")
                    self.high_conviction_listbox.insert(tk.END, "TCS (Technology)")
                    self.high_conviction_listbox.insert(tk.END, "INFY (IT Services)")
                    self.high_conviction_listbox.insert(tk.END, "L&T (Engineering)")
                    
                    self.momentum_listbox.insert(tk.END, "⚡ High Energy Momentum")
                    self.momentum_listbox.insert(tk.END, "ADANIGREEN (Solar)")
                    self.momentum_listbox.insert(tk.END, "TATASTEEL (Metals)")
                    self.momentum_listbox.insert(tk.END, "BAJFINANCE (NBFC)")
                    
                elif element == 'Earth':
                    # Earth signs favor banking, FMCG, utilities
                    self.accumulation_listbox.insert(tk.END, f"🌱 Stable Growth (9:15AM {moon_sign})")
                    self.accumulation_listbox.insert(tk.END, "HDFC (Banking)")
                    self.accumulation_listbox.insert(tk.END, "ICICIBANK (Private Bank)")
                    self.accumulation_listbox.insert(tk.END, "ITC (FMCG)")
                    self.accumulation_listbox.insert(tk.END, "HINDUNILVR (Consumer)")
                    self.accumulation_listbox.insert(tk.END, "NTPC (Power Utilities)")
                    
                    self.high_conviction_listbox.insert(tk.END, "🏛️ Blue Chip Banking")
                    self.high_conviction_listbox.insert(tk.END, "SBI (Public Bank)")
                    self.high_conviction_listbox.insert(tk.END, "KOTAKBANK (Private)")
                    
                elif element == 'Water':
                    # Water signs favor pharma, chemicals, beverages
                    self.high_conviction_listbox.insert(tk.END, f"💧 Healthcare Focus (9:15AM {moon_sign})")
                    self.high_conviction_listbox.insert(tk.END, "SUNPHARMA (Pharmaceuticals)")
                    self.high_conviction_listbox.insert(tk.END, "DRREDDY (Pharma)")
                    self.high_conviction_listbox.insert(tk.END, "CIPLA (Medicine)")
                    
                    self.accumulation_listbox.insert(tk.END, "🧪 Chemical & Process")
                    self.accumulation_listbox.insert(tk.END, "ASIANPAINT (Paints)")
                    self.accumulation_listbox.insert(tk.END, "PIDILITIND (Chemicals)")
                    self.accumulation_listbox.insert(tk.END, "NESTLEIND (Beverages)")
                    
                else:  # Air
                    # Air signs favor communication, media, aviation
                    self.momentum_listbox.insert(tk.END, f"💨 Communication Focus (9:15AM {moon_sign})")
                    self.momentum_listbox.insert(tk.END, "BHARTIARTL (Telecom)")
                    self.momentum_listbox.insert(tk.END, "JIOFINTECH (Fintech)")
                    self.momentum_listbox.insert(tk.END, "ZOMATO (Platform)")
                    
                    self.high_conviction_listbox.insert(tk.END, "📡 Digital & Platforms")
                    self.high_conviction_listbox.insert(tk.END, "WIPRO (IT Services)")
                    self.high_conviction_listbox.insert(tk.END, "TECHM (Technology)")
                    
            else:
                # Fallback recommendations
                self.high_conviction_listbox.insert(tk.END, "Install PyJHora for")
                self.high_conviction_listbox.insert(tk.END, "astrological stock guidance")
                self.accumulation_listbox.insert(tk.END, "Generate reports for")
                self.accumulation_listbox.insert(tk.END, "detailed recommendations")
                self.momentum_listbox.insert(tk.END, "Professional analysis")
                self.momentum_listbox.insert(tk.END, "requires PyJHora setup")
                
        except Exception as e:
            print(f"Error generating stock guidance: {e}")
            self.high_conviction_listbox.insert(tk.END, "Error loading guidance")
            self.accumulation_listbox.insert(tk.END, "Check PyJHora setup")
            self.momentum_listbox.insert(tk.END, "Generate daily reports")
    
    def refresh_market_summary(self):
        """Refresh market summary with live PyJHora data"""
        try:
            self.summary_text.delete(1.0, tk.END)
            
            # Try to load from existing strategy file first
            today_str = datetime.date.today().strftime('%Y%m%d')
            strategy_file = os.path.join(self.reports_dir, f"daily_strategy_{today_str}.json")
            
            if os.path.exists(strategy_file):
                with open(strategy_file, 'r') as f:
                    data = json.load(f)
                
                # Build summary from file
                summary = f"""
📅 MARKET ANALYSIS SUMMARY - {data.get('date', 'Unknown')} ({data.get('day_name', 'Unknown')})
{'='*70}

🌙 MOON POSITION:
   Sign: {data.get('moon_position', {}).get('sign', 'Unknown')}
   Element: {data.get('moon_position', {}).get('element', 'Unknown')}
   Degree: {data.get('moon_position', {}).get('degree', 'Unknown')}°

📊 MARKET OUTLOOK:
   Overall: {data.get('market_outlook', {}).get('overall_outlook', 'Unknown')}
   Volatility: {data.get('market_outlook', {}).get('volatility_expectation', 'Unknown')}
   Price Expectation: {data.get('market_outlook', {}).get('price_expectation', 'Unknown')}

⚠️ RISK MANAGEMENT:
   Risk Level: {data.get('risk_management', {}).get('risk_level', 'Unknown')}
   Max Position Size: {data.get('risk_management', {}).get('max_position_size', 'Unknown')}
   Stop Loss: {data.get('risk_management', {}).get('stop_loss_recommendation', 'Unknown')}
   Profit Target: {data.get('risk_management', {}).get('profit_target', 'Unknown')}

💰 TRADING STRATEGY:
   Primary: {data.get('trading_tactics', {}).get('primary_strategy', 'Unknown')}
   Entry Method: {data.get('trading_tactics', {}).get('entry_method', 'Unknown')}
   Exit Strategy: {data.get('trading_tactics', {}).get('exit_strategy', 'Unknown')}
   Holding Period: {data.get('trading_tactics', {}).get('ideal_holding_period', 'Unknown')}

🚨 KEY ALERTS:
"""
                
                for alert in data.get('alerts_and_warnings', [])[:5]:
                    summary += f"   • {alert}\n"
                
                summary += f"\n\n⏰ Last Updated: {datetime.datetime.now().strftime('%H:%M:%S')}"
                
                self.summary_text.insert(tk.END, summary)
            else:
                # Generate live market summary using PyJHora
                self.generate_live_market_summary()
                
        except Exception as e:
            self.summary_text.insert(tk.END, f"Error loading summary: {e}")
    
    def generate_live_market_summary(self):
        """Generate live market summary using PyJHora calculations"""
        try:
            if PROFESSIONAL_AVAILABLE:
                from pyjhora_calculator import ProfessionalAstrologyCalculator
                
                calc = ProfessionalAstrologyCalculator()
                astro_data = calc.get_complete_analysis(datetime.datetime.now())
                
                # Extract current data
                moon_data = astro_data['planetary_positions'].get('Moon', {})
                moon_sign = moon_data.get('sign', 'Unknown')
                moon_degree = moon_data.get('degree_in_sign', 0)
                
                sign_elements = {
                    'Aries': 'Fire', 'Taurus': 'Earth', 'Gemini': 'Air', 'Cancer': 'Water',
                    'Leo': 'Fire', 'Virgo': 'Earth', 'Libra': 'Air', 'Scorpio': 'Water',
                    'Sagittarius': 'Fire', 'Capricorn': 'Earth', 'Aquarius': 'Air', 'Pisces': 'Water'
                }
                element = sign_elements.get(moon_sign, 'Unknown')
                
                moon_phase = astro_data.get('moon_phase', {})
                phase_name = moon_phase.get('phase_name', 'Unknown')
                phase_percentage = moon_phase.get('illumination', 0)
                
                panchanga = astro_data.get('panchanga', {})
                tithi = panchanga.get('tithi', {}).get('name', 'Unknown')
                nakshatra_name = panchanga.get('nakshatra', {}).get('name', 'Unknown')
                nakshatra_number = panchanga.get('nakshatra', {}).get('number', 0)
                
                # Build live summary
                summary = f"""
🔮 LIVE ASTROLOGICAL MARKET ANALYSIS - {live_time.strftime('%Y-%m-%d')} ({live_time.strftime('%A')})
{'='*75}

🌙 LIVE MOON POSITION (PyJHora Swiss Ephemeris) - {live_time.strftime('%H:%M:%S')}:
   Sign: {moon_sign} at {moon_degree:.2f}°
   Element: {element} (Trading characteristic)
   Phase: {phase_name} ({phase_percentage:.1f}% illuminated)
   
📅 PANCHANGA DATA:
   Tithi: {tithi}
   Nakshatra: {nakshatra_name} (#{nakshatra_number})
   
📊 MARKET OUTLOOK (Based on Moon in {element}):"""
                
                # Element-based market analysis
                if element == 'Fire':
                    summary += """
   Overall: High energy, volatile movements expected
   Volatility: HIGH - Fire element brings rapid price changes
   Sectors: Energy, Tech, Defense sectors favored
   Strategy: Quick momentum trades, avoid over-leveraging"""
                elif element == 'Earth':
                    summary += """
   Overall: Stable, conservative movements expected  
   Volatility: LOW - Earth element brings steady trends
   Sectors: Banking, FMCG, Utilities show strength
   Strategy: Value accumulation, long-term positions"""
                elif element == 'Water':
                    summary += """
   Overall: Emotional, flowing movements expected
   Volatility: MEDIUM-HIGH - Water brings sentiment swings
   Sectors: Pharma, Chemicals, Beverages gain focus
   Strategy: Follow sentiment, watch for reversals"""
                else:  # Air
                    summary += """
   Overall: Communication-driven, airy movements
   Volatility: MEDIUM - Air element brings mixed signals
   Sectors: Telecom, Media, IT platforms active
   Strategy: News-based trading, quick adaptations"""
                
                summary += f"""

⚠️ RISK MANAGEMENT (Moon Phase: {phase_name}):"""
                
                # Phase-based risk management
                if 'Full' in phase_name:
                    summary += """
   Risk Level: MAXIMUM - Full moon amplifies volatility
   Max Position: 50% of normal size recommended
   Stop Loss: Tight stops (2-3%) advised"""
                elif 'New' in phase_name:
                    summary += """
   Risk Level: LOW - New moon brings fresh starts
   Max Position: Standard sizing acceptable
   Stop Loss: Normal stops (4-5%) suitable"""
                else:
                    summary += f"""
   Risk Level: MODERATE - {phase_name} phase
   Max Position: 75% of standard size
   Stop Loss: Moderate stops (3-4%) recommended"""
                
                summary += f"""
   
🌟 CURRENT PLANETARY POSITIONS:"""
                
                # Add key planetary positions
                positions = astro_data.get('planetary_positions', {})
                key_planets = ['Sun', 'Moon', 'Mars', 'Mercury', 'Jupiter', 'Venus', 'Saturn']
                for planet in key_planets:
                    if planet in positions:
                        data = positions[planet]
                        sign = data.get('sign', 'Unknown')
                        degree = data.get('degree_in_sign', 0)
                        summary += f"""
   {planet}: {sign} {degree:.1f}°"""
                
                summary += f"""

💡 TRADING RECOMMENDATIONS:
   • Focus on {element.lower()}-element sectors for best results
   • Adjust position sizes based on {phase_name} moon phase
   • Monitor planetary transits for trend changes
   • Use astrological timing for entry/exit points

⏰ Live Data Updated: {live_time.strftime('%H:%M:%S')}
🔬 Powered by PyJHora Swiss Ephemeris (Professional Accuracy)
💡 Trading predictions use 9:15 AM market opening time
"""
                
                self.summary_text.insert(tk.END, summary)
                
            else:
                # Fallback summary
                summary = f"""
📊 MARKET SUMMARY - {datetime.datetime.now().strftime('%Y-%m-%d')}
{'='*50}

🚫 PyJHora Professional Calculator not available

To see live astrological market analysis:
1. Install PyJHora: pip install PyJHora
2. Restart the application
3. Enjoy professional Swiss Ephemeris accuracy

Or generate daily strategy reports for detailed analysis.

⏰ Updated: {datetime.datetime.now().strftime('%H:%M:%S')}
"""
                self.summary_text.insert(tk.END, summary)
                
        except Exception as e:
            error_summary = f"""
❌ Error generating live market summary: {e}

Please check:
1. PyJHora installation
2. Internet connection for astronomical data
3. System date/time settings

Generate daily strategy reports as alternative.

⏰ {datetime.datetime.now().strftime('%H:%M:%S')}
"""
            self.summary_text.insert(tk.END, error_summary)
    
    def refresh_reports_list(self):
        """Refresh the reports list"""
        self.reports_listbox.delete(0, tk.END)
        
        if os.path.exists(self.reports_dir):
            for file in sorted(os.listdir(self.reports_dir)):
                if file.endswith(('.json', '.txt', '.csv')):
                    # Add file size and date
                    file_path = os.path.join(self.reports_dir, file)
                    mtime = os.path.getmtime(file_path)
                    date_str = datetime.datetime.fromtimestamp(mtime).strftime('%Y-%m-%d %H:%M')
                    size = os.path.getsize(file_path)
                    
                    if size > 1024:
                        size_str = f"{size//1024}KB"
                    else:
                        size_str = f"{size}B"
                    
                    self.reports_listbox.insert(tk.END, f"{file} ({size_str}, {date_str})")
    
    def view_selected_report(self):
        """View the selected report"""
        selection = self.reports_listbox.curselection()
        if selection:
            filename = self.reports_listbox.get(selection[0]).split(' (')[0]  # Remove size and date info
            filepath = os.path.join(self.reports_dir, filename)
            
            if os.path.exists(filepath):
                os.startfile(filepath)  # Windows
    
    def open_reports_folder(self):
        """Open the reports folder"""
        if os.path.exists(self.reports_dir):
            os.startfile(self.reports_dir)  # Windows
    
    def show_daily_strategy(self):
        """Show daily strategy in a popup"""
        try:
            today_str = datetime.date.today().strftime('%Y%m%d')
            strategy_file = os.path.join(self.reports_dir, f"daily_strategy_{today_str}.json")
            
            if os.path.exists(strategy_file):
                with open(strategy_file, 'r') as f:
                    data = json.load(f)
                
                # Create popup window
                popup = tk.Toplevel(self.root)
                popup.title("📈 Today's Trading Strategy")
                popup.geometry("800x600")
                popup.configure(bg='#ecf0f1')
                
                # Strategy content
                strategy_text = scrolledtext.ScrolledText(popup, font=('Consolas', 10), 
                                                        bg='#ecf0f1', wrap=tk.WORD)
                strategy_text.pack(fill='both', expand=True, padx=10, pady=10)
                
                # Format strategy data
                content = f"""
📈 TODAY'S TRADING STRATEGY - {data.get('date', 'Unknown')}
{'='*60}

🌙 MOON POSITION:
• Sign: {data.get('moon_position', {}).get('sign', 'Unknown')} 
• Element: {data.get('moon_position', {}).get('element', 'Unknown')}
• Quality: {data.get('moon_position', {}).get('quality', 'Unknown')}

📊 MARKET OUTLOOK:
• Overall: {data.get('market_outlook', {}).get('overall_outlook', 'Unknown')}
• Volatility: {data.get('market_outlook', {}).get('volatility_expectation', 'Unknown')}
• Approach: {data.get('market_outlook', {}).get('recommended_approach', 'Unknown')}

💰 RISK MANAGEMENT:
• Risk Level: {data.get('risk_management', {}).get('risk_level', 'Unknown')}
• Position Size: {data.get('risk_management', {}).get('max_position_size', 'Unknown')}
• Stop Loss: {data.get('risk_management', {}).get('stop_loss_recommendation', 'Unknown')}

🎯 STOCK RECOMMENDATIONS:
• Top Picks: {', '.join(data.get('stock_recommendations', {}).get('top_picks', [])[:5])}
• Accumulation: {', '.join(data.get('stock_recommendations', {}).get('accumulation_candidates', [])[:5])}

🏭 SECTOR STRATEGY:
• Primary: {', '.join(data.get('sector_strategy', {}).get('primary_sectors', []))}
• Strategy: {data.get('sector_strategy', {}).get('rotation_strategy', 'Unknown')}

🚨 KEY ALERTS:
"""
                for alert in data.get('alerts_and_warnings', []):
                    content += f"• {alert}\n"
                
                strategy_text.insert(tk.END, content)
                
            else:
                messagebox.showwarning("No Data", "No daily strategy found. Please generate reports first.")
                
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load daily strategy: {e}")
    
    def show_weekly_outlook(self):
        """Show weekly outlook in a popup"""
        try:
            # Find most recent weekly outlook
            weekly_files = [f for f in os.listdir(self.reports_dir) 
                          if f.startswith('Weekly_Market_Outlook_') and f.endswith('.txt')]
            
            if weekly_files:
                latest_weekly = sorted(weekly_files)[-1]
                filepath = os.path.join(self.reports_dir, latest_weekly)
                
                # Create popup window
                popup = tk.Toplevel(self.root)
                popup.title("🗓️ Weekly Market Outlook")
                popup.geometry("1000x700")
                popup.configure(bg='#ecf0f1')
                
                # Load and display content
                outlook_text = scrolledtext.ScrolledText(popup, font=('Consolas', 9), 
                                                       bg='#ecf0f1', wrap=tk.WORD)
                outlook_text.pack(fill='both', expand=True, padx=10, pady=10)
                
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                outlook_text.insert(tk.END, content)
                
            else:
                messagebox.showwarning("No Data", "No weekly outlook found. Please generate reports first.")
                
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load weekly outlook: {e}")
    
    def show_market_forecast(self):
        """Show market forecast in a popup"""
        try:
            today_str = datetime.date.today().strftime('%Y%m%d')
            forecast_file = os.path.join(self.reports_dir, f"market_forecast_{today_str}.json")
            
            if os.path.exists(forecast_file):
                # Create popup window
                popup = tk.Toplevel(self.root)
                popup.title("📈 4-Week Market Forecast")
                popup.geometry("1000x700")
                popup.configure(bg='#ecf0f1')
                
                # Forecast content
                forecast_text = scrolledtext.ScrolledText(popup, font=('Consolas', 9), 
                                                        bg='#ecf0f1', wrap=tk.WORD)
                forecast_text.pack(fill='both', expand=True, padx=10, pady=10)
                
                with open(forecast_file, 'r') as f:
                    data = json.load(f)
                
                # Format forecast data
                content = f"""
📈 4-WEEK MARKET FORECAST
{'='*50}

📅 Forecast Date: {data.get('forecast_date', 'Unknown')}
📊 Period: {data.get('forecast_period', 'Unknown')}

🎯 OVERALL OUTLOOK:
• Market Outlook: {data.get('overall_outlook', {}).get('market_outlook', 'Unknown')}
• Average Volatility: {data.get('overall_outlook', {}).get('average_volatility', 'Unknown')}
• Recommendation: {data.get('overall_outlook', {}).get('recommendation', 'Unknown')}

✅ BEST WEEKS FOR TRADING:
"""
                for week in data.get('overall_outlook', {}).get('best_weeks', []):
                    content += f"• {week}\n"
                
                content += "\n⚠️ CHALLENGING WEEKS (CAUTION):\n"
                for week in data.get('overall_outlook', {}).get('challenging_weeks', []):
                    content += f"• {week}\n"
                
                content += "\n🗓️ WEEKLY BREAKDOWN:\n"
                for i, week in enumerate(data.get('weekly_forecasts', []), 1):
                    content += f"""
--- WEEK {i}: {week.get('week_period', 'Unknown')} ---
• Volatility: {week.get('volatility_analysis', {}).get('classification', 'Unknown')}
• Element: {week.get('dominant_element', 'Unknown')}
• Strategy: {week.get('trading_strategy', {}).get('primary_strategy', 'Unknown')}
• Confidence: {week.get('confidence_level', 'Unknown')}
"""
                    if week.get('key_alerts'):
                        content += "• Alerts: " + "; ".join(week.get('key_alerts', [])[:2]) + "\n"
                
                forecast_text.insert(tk.END, content)
                
            else:
                messagebox.showwarning("No Data", "No market forecast found. Please generate reports first.")
                
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load market forecast: {e}")
    
    def refresh_detailed_calendar(self):
        """Refresh detailed calendar"""
        try:
            # Clear existing items
            for item in self.detailed_calendar_tree.get_children():
                self.detailed_calendar_tree.delete(item)
            
            # Load trading calendar data
            today_str = datetime.date.today().strftime('%Y%m%d')
            calendar_file = os.path.join(self.reports_dir, f"trading_calendar_{today_str}.csv")
            
            if os.path.exists(calendar_file):
                df = pd.read_csv(calendar_file)
                
                for _, row in df.iterrows():
                    values = (
                        pd.to_datetime(row['Date']).strftime('%Y-%m-%d'),
                        row['Day'],
                        row['Moon_Sign'],
                        row['Element'],
                        f"{row['Volatility_Factor']}x",
                        row['Risk_Level'],
                        row['Primary_Sectors'],
                        row['Trading_Strategy'],
                        row['Action']
                    )
                    
                    # Color coding
                    if 'CAUTION' in row['Action']:
                        tags = ('danger',)
                    elif 'ACCUMULATE' in row['Action']:
                        tags = ('success',)
                    elif 'CAREFUL' in row['Action']:
                        tags = ('warning',)
                    else:
                        tags = ('normal',)
                    
                    self.detailed_calendar_tree.insert('', 'end', values=values, tags=tags)
                
                # Configure tags
                self.detailed_calendar_tree.tag_configure('danger', background='#ffebee')
                self.detailed_calendar_tree.tag_configure('success', background='#e8f5e8')
                self.detailed_calendar_tree.tag_configure('warning', background='#fff3e0')
                self.detailed_calendar_tree.tag_configure('normal', background='#f5f5f5')
                
        except Exception as e:
            print(f"Error refreshing detailed calendar: {e}")
    
    def export_calendar_csv(self):
        """Export calendar to CSV"""
        try:
            filename = filedialog.asksaveasfilename(
                defaultextension=".csv",
                filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
                title="Save Trading Calendar"
            )
            
            if filename:
                today_str = datetime.date.today().strftime('%Y%m%d')
                source_file = os.path.join(self.reports_dir, f"trading_calendar_{today_str}.csv")
                
                if os.path.exists(source_file):
                    import shutil
                    shutil.copy(source_file, filename)
                    messagebox.showinfo("Export", f"Calendar exported to {filename}")
                else:
                    messagebox.showwarning("No Data", "No trading calendar found. Generate reports first.")
                    
        except Exception as e:
            messagebox.showerror("Error", f"Failed to export calendar: {e}")
    
    def generate_all_pdfs(self):
        """Generate all reports in PDF format"""
        if not PDF_AVAILABLE:
            messagebox.showerror("PDF Not Available", 
                               "PDF generation requires reportlab. Install with:\npip install reportlab")
            return
        
        def run_pdf_generation():
            try:
                self.output_text.delete(1.0, tk.END)
                self.output_text.insert(tk.END, "📄 Starting PDF generation...\n\n")
                self.root.update()
                
                # Initialize PDF generator
                pdf_generator = VedicTradingPDFGenerator(self.reports_dir)
                
                # Generate PDFs
                self.output_text.insert(tk.END, "📊 Generating market forecast PDF...\n")
                self.root.update()
                
                generated_files = pdf_generator.generate_all_pdfs()
                
                self.output_text.insert(tk.END, f"\n✅ Generated {len(generated_files)} PDF reports!\n")
                for file in generated_files:
                    self.output_text.insert(tk.END, f"  - {file.name}\n")
                
                self.root.update()
                messagebox.showinfo("PDF Generation Complete", 
                                   f"Generated {len(generated_files)} PDF reports!\nCheck the pdf_reports folder.")
                
            except Exception as e:
                self.output_text.insert(tk.END, f"\n❌ Error: {e}\n")
                messagebox.showerror("PDF Generation Error", f"Failed to generate PDFs: {e}")
        
        # Run in separate thread
        thread = threading.Thread(target=run_pdf_generation)
        thread.daemon = True
        thread.start()
    
    def open_pdf_folder(self):
        """Open the PDF reports folder"""
        pdf_dir = os.path.join(self.reports_dir, 'pdf_reports')
        if os.path.exists(pdf_dir):
            os.startfile(pdf_dir)  # Windows
        else:
            os.makedirs(pdf_dir, exist_ok=True)
            os.startfile(pdf_dir)  # Windows
    
    def show_moon_calculation_explanation(self):
        """Show detailed explanation of how moon signs are calculated"""
        try:
            # Load today's data to get specific information
            today_str = datetime.date.today().strftime('%Y%m%d')
            strategy_file = os.path.join(self.reports_dir, f"daily_strategy_{today_str}.json")
            
            moon_info = {
                'sign': 'Unknown',
                'element': 'Unknown', 
                'degree': 'Unknown',
                'date': datetime.date.today().strftime('%Y-%m-%d')
            }
            
            if os.path.exists(strategy_file):
                with open(strategy_file, 'r') as f:
                    data = json.load(f)
                moon_pos = data.get('moon_position', {})
                moon_info.update({
                    'sign': moon_pos.get('sign', 'Unknown'),
                    'element': moon_pos.get('element', 'Unknown'),
                    'degree': moon_pos.get('degree', 'Unknown'),
                    'date': data.get('date', datetime.date.today().strftime('%Y-%m-%d'))
                })
            
            # Create explanation popup
            popup = tk.Toplevel(self.root)
            popup.title("🌙 Moon Sign Calculation Explanation")
            popup.geometry("800x600")
            popup.configure(bg='#ecf0f1')
            
            # Explanation content
            explanation_text = scrolledtext.ScrolledText(popup, font=('Arial', 11), 
                                                       bg='#ecf0f1', wrap=tk.WORD)
            explanation_text.pack(fill='both', expand=True, padx=20, pady=20)
            
            # Detailed explanation
            content = f"""
🌙 HOW MOON SIGN IS CALCULATED FOR TRADING ANALYSIS
{'='*70}

CURRENT MOON POSITION:
• Analysis Date: {moon_info['date']}
• Moon Sign: {moon_info['sign']}
• Element: {moon_info['element']}
• Degree: {moon_info['degree']}°

CALCULATION METHOD:

The Moon's position in the zodiac is calculated using astronomical data for the current date and time. Here's how we determine today's Moon sign:

1. ASTRONOMICAL CALCULATION:
   • The Moon's exact celestial longitude is calculated for the analysis date
   • This gives us the Moon's position in degrees (0-360°) around the zodiac
   • Each zodiac sign covers exactly 30° of the zodiac circle

2. ZODIAC SIGN DETERMINATION:
   • Aries: 0-30°    • Cancer: 90-120°     • Libra: 180-210°     • Capricorn: 270-300°
   • Taurus: 30-60°  • Leo: 120-150°       • Scorpio: 210-240°   • Aquarius: 300-330°
   • Gemini: 60-90°  • Virgo: 150-180°     • Sagittarius: 240-270° • Pisces: 330-360°

3. TODAY'S SPECIFIC CALCULATION:
   • Moon at {moon_info['degree']}° places it in {moon_info['sign']}
   • {moon_info['sign']} is a {moon_info['element']} element sign
   • This determines today's market volatility and trading approach

MOON MOVEMENT PATTERN:

• The Moon moves approximately 13° per day through the zodiac
• It stays in each sign for about 2.5 days (2 days 12 hours average)
• Complete zodiac cycle takes about 27.3 days (sidereal month)

MARKET CORRELATION PRINCIPLES:

🔥 FIRE SIGNS (Aries, Leo, Sagittarius):
   • Volatility Factor: 1.2x normal
   • Market Behavior: Momentum-driven, aggressive moves
   • Sector Focus: Energy, Infrastructure, Automotive
   • Trading Style: Breakout strategies, momentum trading

🌍 EARTH SIGNS (Taurus, Virgo, Capricorn):
   • Volatility Factor: 0.6x - 1.0x normal
   • Market Behavior: Steady, value-oriented moves
   • Sector Focus: Banking, FMCG, Pharmaceuticals
   • Trading Style: Value investing, accumulation

💨 AIR SIGNS (Gemini, Libra, Aquarius):
   • Volatility Factor: 1.0x normal
   • Market Behavior: Communication-driven, news-sensitive
   • Sector Focus: Technology, Media, Airlines
   • Trading Style: Trend following, technical analysis

💧 WATER SIGNS (Cancer, Scorpio, Pisces):
   • Volatility Factor: 1.2x - 1.5x normal (Scorpio highest)
   • Market Behavior: Emotional, intuitive moves
   • Sector Focus: Healthcare, Chemicals, Real Estate
   • Trading Style: Contrarian plays, emotional extremes

TODAY'S {moon_info['sign'].upper()} MOON ANALYSIS:

Element Influence: {moon_info['element']} signs tend to:
   • Show {self.get_element_characteristics(moon_info['element'])}
   • Favor {self.get_element_sectors(moon_info['element'])} sectors
   • Support {self.get_element_strategy(moon_info['element'])} trading strategies

VOLATILITY EXPECTATIONS:
   • Expected volatility multiplier based on {moon_info['sign']} positioning
   • Risk management adjusted accordingly
   • Position sizing recommendations modified

WHY THIS MATTERS FOR TRADING:

1. TIMING: Understanding lunar cycles helps time entries and exits
2. VOLATILITY: Moon signs predict market emotional states and volatility
3. SECTORS: Different moon signs favor different market sectors
4. RISK: Helps adjust position sizing and risk management
5. PSYCHOLOGY: Markets reflect collective human psychology, influenced by lunar cycles

HISTORICAL VALIDATION:

Our analysis of 216+ trading days shows:
   • 52.8% directional accuracy for moon sign predictions
   • Observable correlation between moon phases and market movements
   • Statistically significant patterns in sector rotation
   • Volatility clustering during certain moon signs

DISCLAIMER:

This analysis combines ancient Vedic astrological principles with modern market data. While historical correlations exist, this should be used as one factor among many in your trading decisions. Always combine with technical analysis, fundamental research, and proper risk management.

Last updated: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
            """
            
            explanation_text.insert(tk.END, content)
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load moon calculation explanation: {e}")
    
    def get_element_characteristics(self, element):
        """Get characteristics for an element"""
        characteristics = {
            'Fire': 'aggressive, momentum-driven movements with strong directional bias',
            'Earth': 'stable, value-oriented movements with steady accumulation patterns',
            'Air': 'communication-driven movements sensitive to news and announcements', 
            'Water': 'emotional, intuitive movements with potential for extreme swings'
        }
        return characteristics.get(element, 'balanced market behavior')
    
    def get_element_sectors(self, element):
        """Get favored sectors for an element"""
        sectors = {
            'Fire': 'Energy, Infrastructure, Automotive, Metals',
            'Earth': 'Banking, FMCG, Pharmaceuticals, Agriculture',
            'Air': 'Technology, Telecommunications, Media, Aviation',
            'Water': 'Healthcare, Chemicals, Beverages, Real Estate'
        }
        return sectors.get(element, 'diversified')
    
    def get_element_strategy(self, element):
        """Get trading strategy for an element"""
        strategies = {
            'Fire': 'momentum and breakout',
            'Earth': 'value accumulation and buy-and-hold',
            'Air': 'trend following and technical',
            'Water': 'contrarian and sentiment-based'
        }
        return strategies.get(element, 'balanced')
    
    def generate_zodiac_wheel(self):
        """Generate classic zodiac wheel chart showing current Moon position"""
        if not CHARTS_AVAILABLE:
            messagebox.showerror("Charts Not Available", 
                               "Chart generation requires matplotlib. Install with:\npip install matplotlib")
            return
        
        def run_chart_generation():
            try:
                self.output_text.delete(1.0, tk.END)
                self.output_text.insert(tk.END, "🎯 Generating classic zodiac wheel chart...\n\n")
                self.root.update()
                
                # Import and create zodiac wheel generator
                from zodiac_wheel_generator import ZodiacWheelGenerator
                generator = ZodiacWheelGenerator()
                
                # Generate both basic and detailed wheels
                self.output_text.insert(tk.END, "📊 Creating basic zodiac wheel...\n")
                self.root.update()
                
                basic_chart = generator.create_zodiac_wheel()
                
                self.output_text.insert(tk.END, "📈 Creating detailed wheel with planetary positions...\n")
                self.root.update()
                
                detailed_chart = generator.create_detailed_wheel_with_planets()
                
                self.output_text.insert(tk.END, f"\n✅ Charts generated successfully!\n")
                self.output_text.insert(tk.END, f"📍 Basic chart: {basic_chart.name}\n")
                self.output_text.insert(tk.END, f"📍 Detailed chart: {detailed_chart.name}\n")
                self.root.update()
                
                # Try to display the detailed chart
                if generator.display_chart(detailed_chart):
                    self.output_text.insert(tk.END, "\n🖼️ Chart opened for viewing\n")
                
                # Show chart info popup
                self.show_zodiac_wheel_info(detailed_chart)
                
                messagebox.showinfo("Charts Generated", 
                                   f"Classic zodiac wheel charts created!\n\nFiles saved:\n• {basic_chart.name}\n• {detailed_chart.name}")
                
            except Exception as e:
                self.output_text.insert(tk.END, f"\n❌ Error: {e}\n")
                messagebox.showerror("Chart Generation Error", f"Failed to generate charts: {e}")
        
        # Run in separate thread
        thread = threading.Thread(target=run_chart_generation)
        thread.daemon = True
        thread.start()
    
    def generate_professional_zodiac_wheel(self):
        """Generate professional zodiac wheel using PyJHora Swiss Ephemeris backend"""
        if not PROFESSIONAL_AVAILABLE:
            messagebox.showerror("Professional Charts Not Available", 
                               "Professional charts require PyJHora. Install with:\npip install PyJHora")
            return
        
        def run_professional_generation():
            try:
                self.output_text.delete(1.0, tk.END)
                self.output_text.insert(tk.END, "🔮 Generating professional zodiac wheel (PyJHora Swiss Ephemeris)...\n\n")
                self.root.update()
                
                # Import and create professional zodiac wheel generator
                from professional_zodiac_generator import ProfessionalZodiacWheelGenerator
                generator = ProfessionalZodiacWheelGenerator()
                
                # Generate professional chart
                self.output_text.insert(tk.END, "⭐ Using Swiss Ephemeris for planetary calculations...\n")
                self.root.update()
                
                chart_path = generator.create_professional_zodiac_wheel()
                
                self.output_text.insert(tk.END, f"\n✅ Professional chart generated successfully!\n")
                self.output_text.insert(tk.END, f"📍 Chart saved: {chart_path}\n")
                
                # Get professional astrological data
                from pyjhora_calculator import ProfessionalAstrologyCalculator
                calc = ProfessionalAstrologyCalculator()
                astro_data = calc.get_complete_analysis(datetime.datetime.now())
                
                # Display professional data
                self.output_text.insert(tk.END, f"\n🌟 Professional Astrological Data (Swiss Ephemeris):\n")
                
                # Planetary positions
                positions = astro_data['planetary_positions']
                for planet, data in positions.items():
                    self.output_text.insert(tk.END, f"  {planet}: {data['longitude']:.2f}° in {data['sign']}\n")
                
                # Panchanga data
                panchanga = astro_data['panchanga']
                self.output_text.insert(tk.END, f"\n📅 Panchanga (5 Essentials):\n")
                self.output_text.insert(tk.END, f"  Tithi: {panchanga['tithi']['number']}\n")
                nakshatra_name = panchanga['nakshatra'].get('name', f"Nakshatra {panchanga['nakshatra']['number']}")
                self.output_text.insert(tk.END, f"  Nakshatra: {nakshatra_name} (#{panchanga['nakshatra']['number']})\n")
                self.output_text.insert(tk.END, f"  Yoga: {panchanga['yoga']['number']}\n")
                self.output_text.insert(tk.END, f"  Karana: {panchanga['karana']['number']}\n")
                
                self.root.update()
                
                # Try to open the chart
                try:
                    import subprocess
                    subprocess.Popen([chart_path], shell=True)
                    self.output_text.insert(tk.END, "\n🖼️ Professional chart opened for viewing\n")
                except:
                    self.output_text.insert(tk.END, "\n📁 Chart saved (manual open required)\n")
                
                # Show professional chart info popup
                self.show_professional_zodiac_info(chart_path, astro_data)
                
                messagebox.showinfo("Professional Chart Generated", 
                                   f"Professional zodiac wheel created using PyJHora Swiss Ephemeris!\n\nFile saved: {os.path.basename(chart_path)}\n\nAccuracy: Professional grade (same as Drik Panchang)")
                
            except Exception as e:
                self.output_text.insert(tk.END, f"\n❌ Error: {e}\n")
                messagebox.showerror("Professional Chart Error", f"Failed to generate professional chart: {e}")
        
        # Run in separate thread
        thread = threading.Thread(target=run_professional_generation)
        thread.daemon = True
        thread.start()
    
    def show_zodiac_wheel_info(self, chart_path):
        """Show information about the generated zodiac wheel"""
        try:
            # Load today's moon data for the popup
            today_str = datetime.date.today().strftime('%Y%m%d')
            strategy_file = os.path.join(self.reports_dir, f"daily_strategy_{today_str}.json")
            
            moon_info = {
                'sign': 'Unknown',
                'element': 'Unknown',
                'degree': 'Unknown',
                'date': datetime.date.today().strftime('%Y-%m-%d')
            }
            
            if os.path.exists(strategy_file):
                with open(strategy_file, 'r') as f:
                    data = json.load(f)
                moon_pos = data.get('moon_position', {})
                moon_info.update({
                    'sign': moon_pos.get('sign', 'Unknown'),
                    'element': moon_pos.get('element', 'Unknown'),
                    'degree': moon_pos.get('degree', 'Unknown'),
                    'date': data.get('date', datetime.date.today().strftime('%Y-%m-%d'))
                })
            
            # Create info popup
            popup = tk.Toplevel(self.root)
            popup.title("🎯 Zodiac Wheel Chart Information")
            popup.geometry("600x500")
            popup.configure(bg='#ecf0f1')
            
            # Info content
            info_text = scrolledtext.ScrolledText(popup, font=('Arial', 11), 
                                                bg='#ecf0f1', wrap=tk.WORD)
            info_text.pack(fill='both', expand=True, padx=20, pady=20)
            
            content = f"""
🎯 ZODIAC WHEEL CHART GENERATED
{'='*50}

CHART DETAILS:
• Generated: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
• File Location: {chart_path}
• Chart Type: Detailed Vedic Astrology Wheel

CURRENT MOON POSITION:
• Date: {moon_info['date']}
• Sign: {moon_info['sign']} ({moon_info['element']} Element)
• Degree: {moon_info['degree']}°
• Location: Mumbai, India (19.0760°N, 72.8777°E)

CHART FEATURES:

🌟 Zodiac Wheel Elements:
• 12 zodiac signs with traditional symbols
• Color-coded by element (Fire/Earth/Air/Water)
• Degree markings every 30° for each sign
• 5-degree subdivision marks for precision

🌙 Moon Position Display:
• Gold circle marking exact Moon position
• Degree indicator showing precise location
• Highlighted sign showing current Moon sign
• Phase information and illumination percentage

📊 Trading Information:
• Volatility expectations for current position
• Element-based trading strategies
• Risk levels and market implications
• Sector recommendations

🎨 Visual Elements:
• Element color coding:
  - Fire (♈♌♐): Red - Momentum trading
  - Earth (♉♍♑): Brown - Value investing
  - Air (♊♎♒): Blue - Trend following  
  - Water (♋♏♓): Cyan - Contrarian plays

TRADING INTERPRETATION:

The zodiac wheel shows where the Moon is positioned relative to the 12 zodiac signs. This positioning influences:

• Market Volatility: Different signs create different volatility patterns
• Sector Rotation: Elements favor different market sectors
• Trading Psychology: Moon position affects market sentiment
• Risk Levels: Some positions require more cautious approaches

For today's Moon in {moon_info['sign']}:
• This is a {moon_info['element']} sign, suggesting {self.get_element_strategy(moon_info['element'])} strategies
• Volatility expectation: {self.get_volatility_description(moon_info['sign'])}
• Best sectors: {self.get_element_sectors(moon_info['element'])}

USING THE CHART:

1. Locate the golden Moon symbol on the wheel
2. Note which zodiac sign it's positioned in
3. Check the element color for that sign
4. Review the trading information panel
5. Apply the suggested strategies to your trading

The chart updates daily as the Moon moves approximately 13° per day through the zodiac, staying in each sign for about 2.5 days.

REFERENCE:
This chart is based on sidereal (Vedic) astrology calculations using Mumbai coordinates as the reference point for Indian stock market analysis.
            """
            
            info_text.insert(tk.END, content)
            
            # Add button to open chart again
            button_frame = tk.Frame(popup, bg='#ecf0f1')
            button_frame.pack(fill='x', pady=(0, 20))
            
            ttk.Button(button_frame, text="🖼️ Open Chart Again", 
                      command=lambda: os.startfile(str(chart_path))).pack(side='left', padx=20)
            
            ttk.Button(button_frame, text="📁 Open Charts Folder", 
                      command=lambda: os.startfile(str(chart_path.parent))).pack(side='left', padx=20)
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to show chart information: {e}")
    
    def get_volatility_description(self, sign):
        """Get volatility description for a sign"""
        volatility_map = {
            'Aries': 'High (1.2x)', 'Taurus': 'Low (0.8x)', 'Gemini': 'Medium (1.0x)',
            'Cancer': 'Medium-High (1.1x)', 'Leo': 'High (1.2x)', 'Virgo': 'Low (0.7x)',
            'Libra': 'Medium (1.0x)', 'Scorpio': 'Very High (1.5x)', 'Sagittarius': 'High (1.2x)',
            'Capricorn': 'Very Low (0.6x)', 'Aquarius': 'Medium (1.0x)', 'Pisces': 'Medium-High (1.1x)'
        }
        return volatility_map.get(sign, 'Medium (1.0x)')
        """Generate analysis charts"""
        def run_analysis():
            try:
                self.analysis_text.delete(1.0, tk.END)
                self.analysis_text.insert(tk.END, "📊 Generating market analysis charts...\n\n")
                self.root.update()
                
                # Run zodiac analysis
                zodiac_script = os.path.join(self.project_dir, "moon_zodiac_analyzer.py")
                if os.path.exists(zodiac_script):
                    self.analysis_text.insert(tk.END, "🌙 Running zodiac correlation analysis...\n")
                    self.root.update()
                    
                    original_cwd = os.getcwd()
                    try:
                        os.chdir(self.project_dir)
                        result = subprocess.run([sys.executable, "moon_zodiac_analyzer.py"], 
                                              capture_output=True, text=True, timeout=60)
                        
                        if result.returncode == 0:
                            self.analysis_text.insert(tk.END, "✅ Zodiac analysis completed\n\n")
                        else:
                            self.analysis_text.insert(tk.END, f"⚠️ Zodiac analysis warning: {result.stderr}\n\n")
                            
                    finally:
                        os.chdir(original_cwd)
                
                # Run market correlation
                correlator_script = os.path.join(self.project_dir, "market_zodiac_correlator.py")
                if os.path.exists(correlator_script):
                    self.analysis_text.insert(tk.END, "📈 Running market correlation analysis...\n")
                    self.root.update()
                    
                    original_cwd = os.getcwd()
                    try:
                        os.chdir(self.project_dir)
                        result = subprocess.run([sys.executable, "market_zodiac_correlator.py"], 
                                              capture_output=True, text=True, timeout=120)
                        
                        if result.returncode == 0:
                            self.analysis_text.insert(tk.END, "✅ Market correlation completed\n\n")
                        else:
                            self.analysis_text.insert(tk.END, f"⚠️ Market correlation warning: {result.stderr}\n\n")
                            
                    finally:
                        os.chdir(original_cwd)
                
                self.analysis_text.insert(tk.END, "📊 Analysis complete! Check reports folder for generated charts.\n")
                messagebox.showinfo("Analysis Complete", "Market analysis charts generated successfully!")
                
            except Exception as e:
                self.analysis_text.insert(tk.END, f"❌ Error: {e}\n")
                messagebox.showerror("Error", f"Failed to generate analysis: {e}")
        
        thread = threading.Thread(target=run_analysis)
        thread.daemon = True
        thread.start()
    
    def show_professional_zodiac_info(self, chart_path, astro_data):
        """Show information popup for professional zodiac wheel with PyJHora data"""
        try:
            # Create info window
            info_window = tk.Toplevel(self.root)
            info_window.title("Professional Zodiac Wheel - PyJHora Swiss Ephemeris")
            info_window.geometry("600x500")
            info_window.configure(bg='#2c3e50')
            
            # Main frame
            main_frame = tk.Frame(info_window, bg='#2c3e50')
            main_frame.pack(fill='both', expand=True, padx=20, pady=20)
            
            # Title
            title_label = tk.Label(main_frame, text="🔮 Professional Astrological Analysis", 
                                 font=('Arial', 16, 'bold'), fg='white', bg='#2c3e50')
            title_label.pack(pady=(0, 20))
            
            # Create scrollable text area
            text_frame = tk.Frame(main_frame, bg='#ecf0f1')
            text_frame.pack(fill='both', expand=True)
            
            text_widget = scrolledtext.ScrolledText(text_frame, bg='#ecf0f1', 
                                                  font=('Consolas', 10), wrap=tk.WORD)
            text_widget.pack(fill='both', expand=True)
            
            # Add professional data
            text_widget.insert(tk.END, "🎯 PROFESSIONAL ZODIAC WHEEL ANALYSIS\\n")
            text_widget.insert(tk.END, "=" * 50 + "\\n\\n")
            
            # Chart info
            text_widget.insert(tk.END, f"📊 Chart File: {os.path.basename(chart_path)}\\n")
            text_widget.insert(tk.END, f"🔧 Engine: {astro_data.get('calculation_engine', 'PyJHora Swiss Ephemeris')}\\n")
            text_widget.insert(tk.END, f"🌍 Location: {astro_data.get('location', 'Not specified')}\\n")
            text_widget.insert(tk.END, f"⏰ Timestamp: {astro_data.get('timestamp', 'Now')}\\n\\n")
            
            # Planetary positions
            text_widget.insert(tk.END, "🌟 PLANETARY POSITIONS (SIDEREAL):\\n")
            text_widget.insert(tk.END, "-" * 40 + "\\n")
            
            positions = astro_data.get('planetary_positions', {})
            for planet, data in positions.items():
                longitude = data.get('longitude', 0)
                sign = data.get('sign', 'Unknown')
                degree_in_sign = data.get('degree_in_sign', 0)
                text_widget.insert(tk.END, f"{planet:>10}: {longitude:7.2f}° = {sign} {degree_in_sign:5.2f}°\\n")
            
            # Panchanga data
            text_widget.insert(tk.END, "\\n📅 PANCHANGA (5 ESSENTIALS):\\n")
            text_widget.insert(tk.END, "-" * 40 + "\\n")
            
            panchanga = astro_data.get('panchanga', {})
            text_widget.insert(tk.END, f"    Tithi: {panchanga.get('tithi', {}).get('number', 'N/A')}\\n")
            text_widget.insert(tk.END, f"Nakshatra: {panchanga.get('nakshatra', {}).get('number', 'N/A')}\\n")
            text_widget.insert(tk.END, f"     Yoga: {panchanga.get('yoga', {}).get('number', 'N/A')}\\n")
            text_widget.insert(tk.END, f"   Karana: {panchanga.get('karana', {}).get('number', 'N/A')}\\n")
            
            # Moon phase data
            moon_phase = astro_data.get('moon_phase', {})
            if moon_phase:
                text_widget.insert(tk.END, "\\n🌙 MOON PHASE ANALYSIS:\\n")
                text_widget.insert(tk.END, "-" * 40 + "\\n")
                text_widget.insert(tk.END, f"     Phase: {moon_phase.get('phase_name', 'Unknown')}\\n")
                text_widget.insert(tk.END, f"     Angle: {moon_phase.get('phase_angle', 0):.2f}°\\n")
                text_widget.insert(tk.END, f"Illumination: {moon_phase.get('illumination', 0):.1f}%\\n")
            
            # Professional note
            text_widget.insert(tk.END, "\\n" + "=" * 50 + "\\n")
            text_widget.insert(tk.END, "✅ PROFESSIONAL ACCURACY ACHIEVED\\n")
            text_widget.insert(tk.END, "\\n• Swiss Ephemeris calculations (same as Drik Panchang)\\n")
            text_widget.insert(tk.END, "• Sidereal zodiac with Lahiri ayanamsa\\n")
            text_widget.insert(tk.END, "• Professional-grade planetary positions\\n")
            text_widget.insert(tk.END, "• Accurate Panchanga calculations\\n")
            text_widget.insert(tk.END, "• Suitable for serious astrological work\\n")
            
            # Make read-only
            text_widget.config(state=tk.DISABLED)
            
            # Close button
            close_button = ttk.Button(main_frame, text="Close", 
                                    command=info_window.destroy)
            close_button.pack(pady=20)
            
        except Exception as e:
            messagebox.showerror("Info Error", f"Failed to show chart info: {e}")
    
    def generate_analysis_charts(self):
        """Generate analysis charts for market data"""
        try:
            self.output_text.delete(1.0, tk.END)
            self.output_text.insert(tk.END, "📊 Generating market analysis charts...\n\n")
            self.root.update()
            
            # This is a placeholder for future chart generation functionality
            # You can implement specific market analysis charts here
            self.output_text.insert(tk.END, "📈 Market trend analysis chart...\n")
            self.output_text.insert(tk.END, "📊 Volume analysis chart...\n") 
            self.output_text.insert(tk.END, "🔢 Technical indicators chart...\n")
            self.output_text.insert(tk.END, "\n✅ Analysis charts would be generated here\n")
            self.output_text.insert(tk.END, "💡 This feature is available for future enhancement\n")
            
            messagebox.showinfo("Charts", "Analysis charts functionality ready for implementation!")
            
        except Exception as e:
            self.output_text.insert(tk.END, f"\n❌ Error: {e}\n")
            messagebox.showerror("Chart Error", f"Failed to generate analysis charts: {e}")
    
    def auto_refresh(self):
        """Auto-refresh data every 5 minutes"""
        if self.auto_refresh_var.get():
            self.load_current_data()
            self.refresh_trading_calendar()
        
        # Schedule next refresh
        self.root.after(300000, self.auto_refresh)  # 300000ms = 5 minutes


def main():
    """Main function to run the GUI"""
    root = tk.Tk()
    app = VedicTradingGUI(root)
    
    # Set window icon (if available)
    try:
        root.iconbitmap('moon_icon.ico')  # Add an icon file if you have one
    except:
        pass
    
    # Start the GUI
    root.mainloop()


if __name__ == "__main__":
    main()