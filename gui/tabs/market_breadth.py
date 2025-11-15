"""
Market Breadth Analysis Tab

Provides visual analysis of market breadth based on trend ratings,
showing distribution of stocks across bullish/bearish categories.
"""

import tkinter as tk
from tkinter import ttk, messagebox
from tkcalendar import DateEntry
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import threading
import sys
import os

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from services.market_breadth_service import (
    get_current_market_breadth,
    get_market_breadth_for_date,
    get_market_breadth_trend,
    get_breadth_categories,
    get_stocks_in_category,
    calculate_market_breadth_score,
    get_breadth_alerts,
    get_available_dates,
    get_or_calculate_market_breadth,  # New function for on-demand calculation
    get_market_depth_analysis_for_range,  # New function for date range analysis
    calculate_market_depth_trends,  # New function for trend calculations
    get_nifty_with_breadth_chart_data,  # New function for chart data
    get_sectoral_breadth,  # New sectoral analysis function
    compare_sectoral_breadth  # New multi-sector comparison function
)

# Import index symbols API for sectoral analysis
try:
    from services.index_symbols_api import IndexSymbolsAPI
    index_api = IndexSymbolsAPI()
except ImportError:
    index_api = None

# Import PDF generator for sectoral reports
try:
    from services.simple_pdf_generator import generate_sectoral_pdf_report
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False

# Import chart window for displaying stock charts
try:
    from chart_window import show_stock_chart
except ImportError:
    show_stock_chart = None

# Import Nifty breadth chart
try:
    from nifty_breadth_chart import show_nifty_breadth_chart
except ImportError:
    show_nifty_breadth_chart = None


class MarketBreadthTab:
    """Market Breadth Analysis Tab for the scanner GUI."""
    
    def __init__(self, parent):
        self.parent = parent
        self.current_data = {}
        self.trend_data = {}
        
        # Create main frame
        self.main_frame = ttk.Frame(parent)
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Initialize UI components
        self.setup_ui()
        
        # Compatibility bridge for old code that still references date_status_var
        class StatusVar:
            def __init__(self, status_label):
                self.status_label = status_label
            
            def set(self, text):
                # Convert old status text to new format
                if "🔄" in text:
                    color = "orange"
                elif "✅" in text:
                    color = "green" 
                elif "❌" in text:
                    color = "red"
                else:
                    color = "blue"
                self.status_label.configure(text=text, foreground=color)
        
        class DateVar:
            def __init__(self, use_latest, date_picker):
                self.use_latest = use_latest
                self.date_picker = date_picker
            
            def get(self):
                if self.use_latest.get():
                    return "Latest"
                else:
                    try:
                        return self.date_picker.get_date().strftime('%Y-%m-%d')
                    except:
                        return "Latest"
            
            def set(self, value):
                if value == "Latest":
                    self.use_latest.set(True)
                else:
                    self.use_latest.set(False)
                    try:
                        from datetime import datetime
                        date_obj = datetime.strptime(value, '%Y-%m-%d').date()
                        self.date_picker.set_date(date_obj)
                    except:
                        pass
        
        self.date_status_var = StatusVar(self.status_label)
        self.date_var = DateVar(self.use_latest, self.date_picker)
        
        # Load initial data
        self.refresh_data()
    
    def setup_ui(self):
        """Set up the user interface components."""
        
        # Title and controls
        title_frame = ttk.Frame(self.main_frame)
        title_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(title_frame, text="Market Breadth Analysis", 
                 font=('Arial', 16, 'bold')).pack(side=tk.LEFT)
        
        # Refresh button
        ttk.Button(title_frame, text="Refresh Data", 
                  command=self.refresh_data).pack(side=tk.RIGHT)
        
        # Date selection
        date_frame = ttk.Frame(title_frame)
        date_frame.pack(side=tk.RIGHT, padx=(0, 10))
        
        # Latest data toggle
        self.use_latest = tk.BooleanVar(value=True)
        latest_check = ttk.Checkbutton(date_frame, text="Latest Data", 
                                     variable=self.use_latest, 
                                     command=self.on_latest_toggle)
        latest_check.pack(side=tk.LEFT, padx=(0, 10))
        
        # Date picker
        ttk.Label(date_frame, text="Select Date:").pack(side=tk.LEFT)
        
        # Initialize date picker with current date
        self.date_picker = DateEntry(date_frame, width=12, background='darkblue',
                                   foreground='white', borderwidth=2,
                                   date_pattern='yyyy-mm-dd', state='disabled')
        self.date_picker.pack(side=tk.LEFT, padx=(5, 0))
        self.date_picker.bind('<<DateEntrySelected>>', self.on_date_selected)
        
        # Analyze button for selected date
        self.analyze_btn = ttk.Button(date_frame, text="Analyze Date", 
                                    command=self.analyze_selected_date,
                                    state='disabled')
        self.analyze_btn.pack(side=tk.LEFT, padx=(5, 0))
        
        # Status label
        self.status_label = ttk.Label(date_frame, text="Using latest data", 
                                    foreground="green")
        self.status_label.pack(side=tk.LEFT, padx=(10, 0))
        
        # Date Range Analysis Frame
        try:
            range_frame = ttk.LabelFrame(self.main_frame, text="Market Depth Analysis - Date Range", padding=10)
            range_frame.pack(fill=tk.X, padx=10, pady=(10, 5))
            
            # Calculate default dates (last 30 days)
            from datetime import datetime, timedelta
            end_default = datetime.now().date()
            start_default = end_default - timedelta(days=30)
            
            # Start date
            start_date_frame = ttk.Frame(range_frame)
            start_date_frame.pack(side=tk.LEFT, padx=(0, 10))
            ttk.Label(start_date_frame, text="Start Date:").pack(anchor=tk.W)
            self.start_date_picker = DateEntry(start_date_frame, width=12, background='darkblue',
                                             foreground='white', borderwidth=2)
            self.start_date_picker.set_date(start_default)
            self.start_date_picker.pack()
            
            # End date
            end_date_frame = ttk.Frame(range_frame)
            end_date_frame.pack(side=tk.LEFT, padx=(0, 10))
            ttk.Label(end_date_frame, text="End Date:").pack(anchor=tk.W)
            self.end_date_picker = DateEntry(end_date_frame, width=12, background='darkblue',
                                           foreground='white', borderwidth=2)
            self.end_date_picker.set_date(end_default)
            self.end_date_picker.pack()
            
            # Analyze range button
            self.analyze_range_btn = ttk.Button(range_frame, text="Analyze Date Range", 
                                              command=self.analyze_date_range)
            self.analyze_range_btn.pack(side=tk.LEFT, padx=(10, 0))
            
            # Chart button
            self.chart_btn = ttk.Button(range_frame, text="Show Nifty + Breadth Chart", 
                                      command=self.show_nifty_breadth_chart)
            self.chart_btn.pack(side=tk.LEFT, padx=(5, 0))
            
            # Range status label
            self.range_status_label = ttk.Label(range_frame, text="Select date range for analysis", 
                                              foreground="blue")
            self.range_status_label.pack(side=tk.LEFT, padx=(10, 0))
            
            print("✅ Date range components created successfully")
            
        except Exception as e:
            print(f"❌ Error creating date range components: {e}")
            import traceback
            traceback.print_exc()
            
            # Create a fallback label
            error_frame = ttk.LabelFrame(self.main_frame, text="Date Range (Error)", padding=10)
            error_frame.pack(fill=tk.X, padx=10, pady=(10, 5))
            ttk.Label(error_frame, text=f"Error: {str(e)}", foreground="red").pack()
        
        # Create notebook for different views
        self.notebook = ttk.Notebook(self.main_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True)
        
        # Summary tab
        self.setup_summary_tab()
        
        # Distribution tab
        self.setup_distribution_tab()
        
        # Trend tab
        self.setup_trend_tab()
        
        # Stocks tab
        self.setup_stocks_tab()
        
        # Sectoral Analysis tab
        self.setup_sectoral_tab()
    
    def setup_summary_tab(self):
        """Set up the summary overview tab."""
        summary_frame = ttk.Frame(self.notebook)
        self.notebook.add(summary_frame, text="Summary")
        
        # Summary metrics frame
        metrics_frame = ttk.LabelFrame(summary_frame, text="Market Breadth Metrics", 
                                     padding=10)
        metrics_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # Create metrics display
        self.setup_metrics_display(metrics_frame)
        
        # Alerts frame
        alerts_frame = ttk.LabelFrame(summary_frame, text="Market Alerts", 
                                    padding=10)
        alerts_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Alerts listbox
        alerts_scroll = ttk.Scrollbar(alerts_frame)
        self.alerts_listbox = tk.Listbox(alerts_frame, yscrollcommand=alerts_scroll.set,
                                        font=('Arial', 10))
        alerts_scroll.config(command=self.alerts_listbox.yview)
        alerts_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.alerts_listbox.pack(fill=tk.BOTH, expand=True)
    
    def setup_metrics_display(self, parent):
        """Set up the metrics display grid."""
        # Create grid for metrics
        metrics_grid = ttk.Frame(parent)
        metrics_grid.pack(fill=tk.X)
        
        # Define metrics
        self.metric_labels = {}
        metrics = [
            ('total_stocks', 'Total Stocks', 0, 0),
            ('bullish_count', 'Bullish Stocks', 0, 1),
            ('bearish_count', 'Bearish Stocks', 0, 2),
            ('neutral_count', 'Neutral Stocks', 0, 3),
            ('market_avg_rating', 'Avg Rating', 1, 0),
            ('bullish_percentage', 'Bullish %', 1, 1),
            ('bearish_percentage', 'Bearish %', 1, 2),
            ('bullish_bearish_ratio', 'Bull/Bear Ratio', 1, 3),
        ]
        
        for key, label, row, col in metrics:
            frame = ttk.Frame(metrics_grid)
            frame.grid(row=row, column=col, padx=10, pady=5, sticky='w')
            
            ttk.Label(frame, text=f"{label}:", font=('Arial', 10, 'bold')).pack()
            value_label = ttk.Label(frame, text="--", font=('Arial', 12))
            value_label.pack()
            self.metric_labels[key] = value_label
        
        # Market breadth score
        score_frame = ttk.Frame(parent)
        score_frame.pack(fill=tk.X, pady=(10, 0))
        
        ttk.Label(score_frame, text="Market Breadth Score:", 
                 font=('Arial', 12, 'bold')).pack(side=tk.LEFT)
        self.score_label = ttk.Label(score_frame, text="--", 
                                   font=('Arial', 14, 'bold'))
        self.score_label.pack(side=tk.LEFT, padx=(10, 0))
        
        self.interpretation_label = ttk.Label(score_frame, text="", 
                                            font=('Arial', 12))
        self.interpretation_label.pack(side=tk.LEFT, padx=(20, 0))
    
    def setup_distribution_tab(self):
        """Set up the distribution visualization tab."""
        dist_frame = ttk.Frame(self.notebook)
        self.notebook.add(dist_frame, text="Distribution")
        
        # Create matplotlib figure for pie chart
        self.dist_fig = Figure(figsize=(12, 8), dpi=100)
        
        # Create canvas
        self.dist_canvas = FigureCanvasTkAgg(self.dist_fig, master=dist_frame)
        self.dist_canvas.draw()
        self.dist_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
    
    def setup_trend_tab(self):
        """Set up the trend analysis tab."""
        trend_frame = ttk.Frame(self.notebook)
        self.notebook.add(trend_frame, text="Trend Analysis")
        
        # Controls frame
        controls_frame = ttk.Frame(trend_frame)
        controls_frame.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Label(controls_frame, text="Days to analyze:").pack(side=tk.LEFT)
        self.days_var = tk.StringVar(value="30")
        days_combo = ttk.Combobox(controls_frame, textvariable=self.days_var,
                                 values=["7", "15", "30", "60", "90"], width=8)
        days_combo.pack(side=tk.LEFT, padx=(5, 0))
        days_combo.bind('<<ComboboxSelected>>', self.on_days_change)
        
        ttk.Button(controls_frame, text="Update Trend", 
                  command=self.update_trend_analysis).pack(side=tk.LEFT, padx=(10, 0))
        
        # Create matplotlib figure for trend charts
        self.trend_fig = Figure(figsize=(14, 10), dpi=100)
        
        # Create canvas
        self.trend_canvas = FigureCanvasTkAgg(self.trend_fig, master=trend_frame)
        self.trend_canvas.draw()
        self.trend_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
    
    def setup_stocks_tab(self):
        """Set up the stocks by category tab."""
        stocks_frame = ttk.Frame(self.notebook)
        self.notebook.add(stocks_frame, text="Stocks by Category")
        
        # Controls frame
        controls_frame = ttk.Frame(stocks_frame)
        controls_frame.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Label(controls_frame, text="Category:").pack(side=tk.LEFT)
        self.category_var = tk.StringVar()
        categories = [cat['name'] for cat in get_breadth_categories()]
        category_combo = ttk.Combobox(controls_frame, textvariable=self.category_var,
                                     values=categories, width=25)
        category_combo.pack(side=tk.LEFT, padx=(5, 0))
        category_combo.bind('<<ComboboxSelected>>', self.on_category_change)
        if categories:
            category_combo.set(categories[0])
        
        ttk.Button(controls_frame, text="Load Stocks", 
                  command=self.load_category_stocks).pack(side=tk.LEFT, padx=(10, 0))
        
        # Stocks treeview
        tree_frame = ttk.Frame(stocks_frame)
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        columns = ('Symbol', 'Rating', 'Daily', 'Weekly', 'Monthly', 'Price', 'Change %')
        self.stocks_tree = ttk.Treeview(tree_frame, columns=columns, show='headings', height=15)
        
        # Configure columns
        for col in columns:
            self.stocks_tree.heading(col, text=col)
            self.stocks_tree.column(col, width=100)
        
        # Bind double-click event to show stock chart
        self.stocks_tree.bind('<Double-1>', self.on_stock_double_click)
        
        # Add context menu for right-click
        self.create_context_menu()
        self.stocks_tree.bind('<Button-3>', self.show_context_menu)  # Right-click
        
        # Add tooltip instruction
        instruction_label = ttk.Label(tree_frame, 
                                    text="💡 Double-click any stock to view its trend chart | Right-click for menu", 
                                    font=('Arial', 9), foreground='blue')
        instruction_label.pack(pady=(5, 0))
        
        # Scrollbars
        v_scroll = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.stocks_tree.yview)
        h_scroll = ttk.Scrollbar(tree_frame, orient=tk.HORIZONTAL, command=self.stocks_tree.xview)
        self.stocks_tree.configure(yscrollcommand=v_scroll.set, xscrollcommand=h_scroll.set)
        
        # Pack components
        self.stocks_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        v_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        h_scroll.pack(side=tk.BOTTOM, fill=tk.X)
    
    def refresh_data(self):
        """Refresh all market breadth data."""
        self.status_label.configure(text="🔄 Loading data...", foreground="orange")
        
        def fetch_data():
            try:
                # Get available dates first
                print("📅 Fetching available dates...")
                available_dates = get_available_dates(30)
                print(f"📅 Found {len(available_dates) if available_dates else 0} available dates")
                
                if not available_dates:
                    print("❌ No available dates found")
                    self.parent.after(0, lambda: self.handle_no_dates_error())
                    return
                
                # Log the dates for debugging
                print(f"📅 Available dates: {[str(d) for d in available_dates[:5]]}")
                
                # Check current date selection
                if self.use_latest.get():
                    # Get current market breadth
                    print("🔍 Getting current market breadth...")
                    self.current_data = get_current_market_breadth()
                else:
                    # Get data for selected date from date picker
                    try:
                        selected_date = self.date_picker.get_date()
                        print(f"🔍 Getting market breadth for {selected_date}...")
                        self.current_data = get_market_breadth_for_date(selected_date)
                    except Exception as date_error:
                        # Fall back to current data if date picker fails
                        print(f"⚠️ Date picker error: {date_error}, falling back to current data")
                        self.current_data = get_current_market_breadth()
                
                # Get trend data
                print("📈 Getting trend data...")
                self.trend_data = get_market_breadth_trend(int(self.days_var.get()) if hasattr(self, 'days_var') else 30)
                
                # Store available dates for dropdown
                self.available_dates = available_dates
                print(f"✅ Stored {len(available_dates)} dates for dropdown")
                
                # Update UI on main thread
                self.parent.after(0, self.update_ui)
                
            except Exception as e:
                print(f"❌ Error in fetch_data: {e}")
                import traceback
                traceback.print_exc()
                error_msg = str(e)
                self.parent.after(0, lambda: self.handle_refresh_error(error_msg))
        
        # Fetch data in background thread
        threading.Thread(target=fetch_data, daemon=True).start()
    
    def refresh_dates_only(self):
        """Refresh only the available dates dropdown."""
        self.date_status_var.set("🔄 Refreshing dates...")
        
        def fetch_dates():
            try:
                print("📅 Manually refreshing available dates...")
                available_dates = get_available_dates(30)
                print(f"📅 Manual refresh found {len(available_dates) if available_dates else 0} dates")
                
                if available_dates:
                    # Store dates
                    self.available_dates = available_dates
                    print(f"📅 Dates: {[str(d) for d in available_dates[:10]]}")
                    
                    # Update UI on main thread
                    self.parent.after(0, self.update_dates_only)
                else:
                    self.parent.after(0, lambda: self.handle_no_dates_error())
                    
            except Exception as e:
                print(f"❌ Error refreshing dates: {e}")
                import traceback
                traceback.print_exc()
                self.parent.after(0, lambda: self.handle_refresh_error(f"Date refresh failed: {e}"))
        
        threading.Thread(target=fetch_dates, daemon=True).start()
    
    def update_dates_only(self):
        """Update only the date dropdown without refreshing analysis data."""
        try:
            if hasattr(self, 'available_dates') and self.available_dates:
                # Create date strings for dropdown
                date_options = ["Latest"]
                for date_obj in self.available_dates:
                    date_str = date_obj.strftime('%Y-%m-%d')
                    date_options.append(date_str)
                
                # Update combobox values
                self.date_combo['values'] = date_options
                
                # Keep current selection if it's still valid
                current_value = self.date_var.get()
                if current_value not in date_options:
                    self.date_var.set("Latest")
                
                self.date_status_var.set(f"✅ {len(self.available_dates)} dates loaded")
                print(f"✅ Successfully updated dropdown with {len(date_options)} options")
                
                # Show success message
                messagebox.showinfo("Dates Refreshed", 
                                  f"Successfully loaded {len(self.available_dates)} analysis dates!\n\n"
                                  f"Available dates:\n" + 
                                  "\n".join([f"• {d}" for d in self.available_dates[:5]]) +
                                  (f"\n... and {len(self.available_dates) - 5} more" if len(self.available_dates) > 5 else ""))
            else:
                self.date_status_var.set("❌ No dates")
                messagebox.showwarning("No Dates", "No analysis dates found in database.")
                
        except Exception as e:
            print(f"❌ Error updating dates only: {e}")
            self.date_status_var.set("❌ Error")
            messagebox.showerror("Error", f"Failed to update dates: {e}")
    
    def handle_no_dates_error(self):
        """Handle case when no dates are available."""
        self.date_status_var.set("❌ No dates")
        messagebox.showerror("No Data", 
                           "No trend analysis dates found in database.\n\n"
                           "Please ensure:\n"
                           "1. Database connection is working\n"
                           "2. trend_analysis table has data\n"
                           "3. Check database configuration in .env file")
    
    def handle_refresh_error(self, error_msg):
        """Handle refresh errors."""
        self.date_status_var.set("❌ Error")
        messagebox.showerror("Refresh Error", f"Failed to refresh data:\n\n{error_msg}")
        print(f"Market breadth refresh error: {error_msg}")
    
    def update_ui(self):
        """Update all UI components with current data."""
        if not self.current_data.get('success', False):
            error_msg = self.current_data.get('error', 'Unknown error')
            self.date_status_var.set("❌ Error")
            messagebox.showerror("Analysis Error", f"Market breadth analysis failed:\n\n{error_msg}")
            return
        
        # Update status with data info
        total_stocks = self.current_data.get('total_analyzed', 0)
        analysis_date = self.current_data.get('analysis_date', 'Unknown')
        self.status_label.configure(text=f"✅ {total_stocks:,} stocks ({analysis_date})", foreground="green")
        
        # Update summary metrics
        self.update_summary()
        
        # Update distribution chart
        self.update_distribution_chart()
        
        # Update trend chart
        self.update_trend_chart()
        
        # Update date options
        self.update_date_options()
    
    def update_date_options(self):
        """Update the date dropdown with available dates."""
        try:
            if hasattr(self, 'available_dates') and self.available_dates:
                # Create date strings for dropdown
                date_options = ["Latest"]
                for date_obj in self.available_dates:
                    date_str = date_obj.strftime('%Y-%m-%d')
                    date_options.append(date_str)
                
                # Update combobox values
                self.date_combo['values'] = date_options
                
                # Keep current selection if it's still valid
                current_value = self.date_var.get()
                if current_value not in date_options:
                    self.date_var.set("Latest")
                
                print(f"✅ Updated date dropdown with {len(date_options)} options: {date_options[:5]}")
            else:
                # No dates available, keep only "Latest"
                self.date_combo['values'] = ["Latest"]
                self.date_var.set("Latest")
                print(f"⚠️ No available dates found, using only 'Latest'")
                
        except Exception as e:
            print(f"❌ Error updating date options: {e}")
            # Fallback to Latest only
            self.date_combo['values'] = ["Latest"]
            self.date_var.set("Latest")
    
    def update_summary(self):
        """Update summary metrics display."""
        summary = self.current_data.get('summary', {})
        
        # Update metric labels
        for key, label in self.metric_labels.items():
            value = summary.get(key, '--')
            if isinstance(value, (int, float)):
                if key in ['bullish_percentage', 'bearish_percentage', 'neutral_percentage']:
                    label.config(text=f"{value}%")
                elif key == 'market_avg_rating':
                    label.config(text=f"{value:.1f}")
                elif key == 'bullish_bearish_ratio':
                    label.config(text=f"{value:.2f}")
                else:
                    label.config(text=str(value))
            else:
                label.config(text=str(value))
        
        # Update breadth score
        score, interpretation = calculate_market_breadth_score(summary)
        self.score_label.config(text=f"{score}")
        self.interpretation_label.config(text=interpretation)
        
        # Update alerts
        alerts = get_breadth_alerts(summary)
        self.update_alerts_display(alerts)
    
    def update_alerts_display(self, alerts):
        """Update the alerts display."""
        self.alerts_listbox.delete(0, tk.END)
        
        if not alerts:
            self.alerts_listbox.insert(tk.END, "No alerts - Market conditions are normal")
        else:
            for alert in alerts:
                severity_icon = "⚠️" if alert['severity'] == 'high' else "ℹ️"
                self.alerts_listbox.insert(tk.END, f"{severity_icon} {alert['title']}: {alert['message']}")
    
    def update_distribution_chart(self):
        """Update the distribution pie chart."""
        self.dist_fig.clear()
        
        distribution = self.current_data.get('rating_distribution', [])
        if not distribution:
            ax = self.dist_fig.add_subplot(111)
            ax.text(0.5, 0.5, 'No distribution data available', 
                   ha='center', va='center', transform=ax.transAxes)
            self.dist_canvas.draw()
            return
        
        # Create pie chart
        ax1 = self.dist_fig.add_subplot(121)
        
        labels = [item['rating_category'] for item in distribution]
        sizes = [item['stock_count'] for item in distribution]
        colors = ['#00AA00', '#44CC44', '#88DD88', '#FFAA00', '#FF6666', '#CC3333', '#AA0000']
        
        wedges, texts, autotexts = ax1.pie(sizes, labels=labels, colors=colors[:len(sizes)], 
                                          autopct='%1.1f%%', startangle=90)
        ax1.set_title('Stock Distribution by Rating Category', fontsize=14, fontweight='bold')
        
        # Create bar chart
        ax2 = self.dist_fig.add_subplot(122)
        
        y_pos = np.arange(len(labels))
        ax2.barh(y_pos, sizes, color=colors[:len(sizes)])
        ax2.set_yticks(y_pos)
        ax2.set_yticklabels(labels)
        ax2.set_xlabel('Number of Stocks')
        ax2.set_title('Stock Count by Category', fontsize=14, fontweight='bold')
        
        self.dist_fig.tight_layout()
        self.dist_canvas.draw()
    
    def update_trend_chart(self):
        """Update the trend analysis charts."""
        self.trend_fig.clear()
        
        if not self.trend_data.get('success', False):
            ax = self.trend_fig.add_subplot(111)
            ax.text(0.5, 0.5, 'No trend data available', 
                   ha='center', va='center', transform=ax.transAxes)
            self.trend_canvas.draw()
            return
        
        trend_data = self.trend_data.get('trend_data', [])
        if not trend_data:
            return
        
        df = pd.DataFrame(trend_data)
        df['trade_date'] = pd.to_datetime(df['trade_date'])
        
        # Create subplots
        ax1 = self.trend_fig.add_subplot(211)
        ax2 = self.trend_fig.add_subplot(212)
        
        # Plot bullish/bearish percentages
        ax1.plot(df['trade_date'], df['bullish_percentage'], 
                label='Bullish %', color='green', linewidth=2)
        ax1.plot(df['trade_date'], df['bearish_percentage'], 
                label='Bearish %', color='red', linewidth=2)
        ax1.set_title('Market Breadth Trend - Bullish vs Bearish %', fontweight='bold')
        ax1.set_ylabel('Percentage of Stocks')
        ax1.legend()
        ax1.grid(True, alpha=0.3)
        
        # Plot average market rating
        ax2.plot(df['trade_date'], df['market_avg_rating'], 
                label='Avg Market Rating', color='purple', linewidth=2)
        ax2.axhline(y=0, color='black', linestyle='--', alpha=0.5)
        ax2.set_title('Average Market Rating Trend', fontweight='bold')
        ax2.set_ylabel('Average Rating')
        ax2.set_xlabel('Date')
        ax2.legend()
        ax2.grid(True, alpha=0.3)
        
        self.trend_fig.tight_layout()
        self.trend_canvas.draw()
    
    def update_date_options(self):
        """Update available date options."""
        # For now, just use "Latest" - can be expanded later
        pass
    
    def analyze_selected_date(self):
        """Analyze market breadth for the currently selected date."""
        if self.use_latest.get():
            # Using latest data
            self.status_label.configure(text="Loading latest data...", foreground="orange")
            
            def fetch_latest():
                try:
                    self.current_data = get_current_market_breadth()
                    analysis_label = "Latest Available"
                    self.parent.after(0, lambda: self.update_analysis_results(analysis_label))
                except Exception as e:
                    error_msg = f"Failed to get latest data: {str(e)}"
                    self.parent.after(0, lambda: self.handle_analysis_error(error_msg))
            
            threading.Thread(target=fetch_latest, daemon=True).start()
        else:
            # Using date picker
            selected_date = self.date_picker.get_date()
            if not selected_date:
                messagebox.showwarning("No Date", "Please select a date to analyze.")
                return
            
            date_str = selected_date.strftime('%Y-%m-%d')
            self.status_label.configure(text=f"Analyzing {date_str}...", foreground="orange")
            
            def fetch_analysis():
                try:
                    # Use the new get_or_calculate_market_breadth function
                    # This will either get existing data or calculate it if needed
                    self.current_data = get_or_calculate_market_breadth(selected_date)
                    analysis_label = date_str
                    
                    # Check if data was newly calculated
                    if self.current_data.get('newly_calculated'):
                        message = f"✨ Calculated new market breadth data for {date_str}"
                        self.parent.after(0, lambda: self.status_label.configure(
                            text=message, foreground="green"))
                    
                    self.parent.after(0, lambda: self.update_analysis_results(analysis_label))
                    
                except Exception as e:
                    error_msg = f"Failed to analyze {date_str}: {str(e)}"
                    self.parent.after(0, lambda: self.handle_analysis_error(error_msg))
            
            threading.Thread(target=fetch_analysis, daemon=True).start()
    
    def update_analysis_results(self, analysis_label):
        """Update UI with analysis results."""
        if not self.current_data.get('success', False):
            error_msg = self.current_data.get('error', 'Unknown error')
            self.status_label.configure(text="❌ Analysis failed", foreground="red")
            messagebox.showerror("Analysis Error", f"Analysis failed: {error_msg}")
            return
        
        # Update status
        total_stocks = self.current_data.get('total_analyzed', 0)
        self.status_label.configure(text=f"✅ {total_stocks:,} stocks analyzed", foreground="green")
        
        # Update all UI components
        self.update_summary()
        self.update_distribution_chart()
        self.load_category_stocks()
        
        # Show success message with key metrics if it's a newly calculated result
        if self.current_data.get('newly_calculated'):
            summary = self.current_data.get('summary', {})
            bullish_pct = summary.get('bullish_percentage', 0)
            bearish_pct = summary.get('bearish_percentage', 0)
            avg_rating = summary.get('market_avg_rating', 0)
            
            messagebox.showinfo("New Analysis Complete", 
                              f"✨ Calculated Market Breadth for {analysis_label}:\n\n"
                              f"📊 Total Stocks: {total_stocks:,}\n"
                              f"📈 Bullish: {bullish_pct:.1f}%\n"
                              f"📉 Bearish: {bearish_pct:.1f}%\n"
                              f"⭐ Avg Rating: {avg_rating:.2f}\n\n"
                              f"💾 Results saved for future use!")
    
    def handle_analysis_error(self, error_msg):
        """Handle analysis errors."""
        self.status_label.configure(text="❌ Analysis failed", foreground="red")
        messagebox.showerror("Analysis Error", error_msg)
        print(f"Market breadth analysis error: {error_msg}")

    def analyze_date_range(self):
        """Analyze market depth trends for a date range."""
        start_date = self.start_date_picker.get_date()
        end_date = self.end_date_picker.get_date()
        
        if not start_date or not end_date:
            messagebox.showwarning("Date Range Required", 
                                 "Please select both start and end dates for analysis.")
            return
        
        if start_date > end_date:
            messagebox.showwarning("Invalid Date Range", 
                                 "Start date must be before or equal to end date.")
            return
        
        # Check for reasonable range (not more than 6 months)
        date_diff = (end_date - start_date).days
        if date_diff > 180:
            result = messagebox.askyesno("Large Date Range", 
                                       f"You selected {date_diff} days. This might take a while. Continue?")
            if not result:
                return
        
        start_str = start_date.strftime('%Y-%m-%d')
        end_str = end_date.strftime('%Y-%m-%d')
        self.range_status_label.configure(text=f"Analyzing {start_str} to {end_str}...", 
                                        foreground="orange")
        
        def fetch_range_analysis():
            try:
                # Call the new range analysis function
                range_data = get_market_depth_analysis_for_range(start_date, end_date)
                
                if not range_data.get('success', False):
                    error_msg = range_data.get('error', 'Failed to analyze date range')
                    self.parent.after(0, lambda: self.handle_range_analysis_error(error_msg))
                    return
                
                # Calculate trend analysis
                trend_analysis = calculate_market_depth_trends(range_data['daily_analysis'])
                range_data['trend_analysis'] = trend_analysis
                
                self.parent.after(0, lambda: self.display_range_analysis_results(range_data, start_str, end_str))
                
            except Exception as e:
                error_msg = f"Failed to analyze date range: {str(e)}"
                self.parent.after(0, lambda: self.handle_range_analysis_error(error_msg))
        
        threading.Thread(target=fetch_range_analysis, daemon=True).start()
    
    def display_range_analysis_results(self, range_data, start_str, end_str):
        """Display the results of date range analysis."""
        summary = range_data.get('summary', {})
        trend_analysis = range_data.get('trend_analysis', {})
        
        # Update status
        total_days = len(range_data.get('daily_analysis', []))
        self.range_status_label.configure(
            text=f"✅ Analyzed {total_days} trading days", 
            foreground="green"
        )
        
        # Create results window
        results_window = tk.Toplevel(self.parent)
        results_window.title(f"Market Depth Analysis: {start_str} to {end_str}")
        results_window.geometry("800x600")
        results_window.transient(self.parent)
        
        # Create notebook for different views
        notebook = ttk.Notebook(results_window)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Summary tab
        summary_frame = ttk.Frame(notebook)
        notebook.add(summary_frame, text="Summary")
        
        # Summary text with scrollbar
        summary_text_frame = ttk.Frame(summary_frame)
        summary_text_frame.pack(fill=tk.BOTH, expand=True)
        
        summary_text = tk.Text(summary_text_frame, wrap=tk.WORD, font=('Consolas', 10))
        summary_scrollbar = ttk.Scrollbar(summary_text_frame, orient=tk.VERTICAL, command=summary_text.yview)
        summary_text.configure(yscrollcommand=summary_scrollbar.set)
        
        # Build summary content
        content = f"📊 MARKET DEPTH ANALYSIS REPORT\n"
        content += f"{'='*50}\n\n"
        content += f"📅 Analysis Period: {start_str} to {end_str}\n"
        content += f"📈 Trading Days Analyzed: {total_days}\n\n"
        
        content += f"📊 OVERALL STATISTICS\n"
        content += f"{'-'*30}\n"
        content += f"Average Daily Stocks: {summary.get('avg_total_stocks', 0):,.0f}\n"
        content += f"Average Bullish %: {summary.get('avg_bullish_percentage', 0):.1f}%\n"
        content += f"Average Bearish %: {summary.get('avg_bearish_percentage', 0):.1f}%\n"
        content += f"Average Market Rating: {summary.get('avg_market_rating', 0):.2f}\n\n"
        
        content += f"📈 TREND ANALYSIS\n"
        content += f"{'-'*30}\n"
        if trend_analysis:
            content += f"Bullish Trend: {trend_analysis.get('bullish_trend_direction', 'N/A')}\n"
            content += f"Bearish Trend: {trend_analysis.get('bearish_trend_direction', 'N/A')}\n"
            content += f"Rating Trend: {trend_analysis.get('rating_trend_direction', 'N/A')}\n"
            content += f"Market Volatility: {trend_analysis.get('volatility_assessment', 'N/A')}\n\n"
        
        content += f"🎯 EXTREMES\n"
        content += f"{'-'*30}\n"
        max_bullish_day = summary.get('max_bullish_day', {})
        min_bullish_day = summary.get('min_bullish_day', {})
        content += f"Highest Bullish %: {max_bullish_day.get('percentage', 0):.1f}% ({max_bullish_day.get('date', 'N/A')})\n"
        content += f"Lowest Bullish %: {min_bullish_day.get('percentage', 0):.1f}% ({min_bullish_day.get('date', 'N/A')})\n"
        content += f"Market Volatility: {summary.get('market_volatility', 0):.1f}\n"
        content += f"Sentiment Trend: {summary.get('sentiment_trend', 0):.1f}\n"
        
        summary_text.insert(tk.END, content)
        summary_text.configure(state='disabled')
        
        summary_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        summary_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Add close button
        close_btn = ttk.Button(results_window, text="Close", command=results_window.destroy)
        close_btn.pack(pady=5)
        
    def handle_range_analysis_error(self, error_msg):
        """Handle range analysis errors."""
        self.range_status_label.configure(text="❌ Range analysis failed", foreground="red")
        messagebox.showerror("Range Analysis Error", error_msg)
        print(f"Market depth range analysis error: {error_msg}")

    def show_nifty_breadth_chart(self):
        """Show Nifty chart with market breadth indicators."""
        if show_nifty_breadth_chart is None:
            messagebox.showerror("Chart Unavailable", 
                               "Nifty breadth chart functionality is not available. Please ensure nifty_breadth_chart.py is accessible.")
            return
        
        start_date = self.start_date_picker.get_date()
        end_date = self.end_date_picker.get_date()
        
        if not start_date or not end_date:
            messagebox.showwarning("Date Range Required", 
                                 "Please select both start and end dates for the chart.")
            return
        
        if start_date > end_date:
            messagebox.showwarning("Invalid Date Range", 
                                 "Start date must be before or equal to end date.")
            return
        
        try:
            # Show the chart window
            print(f"Creating Nifty + Breadth chart for {start_date} to {end_date}")
            chart_window = show_nifty_breadth_chart(self.parent, start_date, end_date, 'NIFTY 50')
            
        except Exception as e:
            messagebox.showerror("Chart Error", f"Failed to display Nifty + Breadth chart:\n{str(e)}")
            print(f"Error showing Nifty + Breadth chart: {e}")
            import traceback
            traceback.print_exc()

    def on_latest_toggle(self):
        """Handle toggle between latest data and date picker."""
        if self.use_latest.get():
            # Using latest data
            self.date_picker.configure(state='disabled')
            self.analyze_btn.configure(state='disabled')
            self.status_label.configure(text="Using latest data", foreground="green")
            # Auto-refresh with latest data
            self.refresh_data()
        else:
            # Using date picker
            self.date_picker.configure(state='normal')
            self.analyze_btn.configure(state='normal')
            self.status_label.configure(text="Select a date to analyze", foreground="blue")
    
    def on_date_selected(self, event=None):
        """Handle date picker selection."""
        if not self.use_latest.get():
            selected_date = self.date_picker.get_date()
            self.status_label.configure(
                text=f"Selected: {selected_date.strftime('%Y-%m-%d')}", 
                foreground="blue"
            )

    def on_date_change(self, event=None):
        """Handle date selection change (legacy method for compatibility)."""
        # This method is kept for backward compatibility but not used with date picker
        pass
    
    def update_date_specific_ui(self):
        """Update UI components that depend on the selected date."""
        if not self.current_data.get('success', False):
            messagebox.showerror("Error", self.current_data.get('error', 'Unknown error'))
            return
        
        # Update summary metrics
        self.update_summary()
        
        # Update distribution chart
        self.update_distribution_chart()
        
        # Refresh category stocks for current date
        self.load_category_stocks()
    
    def on_days_change(self, event=None):
        """Handle days selection change for trend analysis."""
        self.update_trend_analysis()
    
    def on_category_change(self, event=None):
        """Handle category selection change."""
        self.load_category_stocks()
    
    def update_trend_analysis(self):
        """Update trend analysis with new day range."""
        def fetch_trend_data():
            try:
                days = int(self.days_var.get())
                self.trend_data = get_market_breadth_trend(days)
                self.parent.after(0, self.update_trend_chart)
            except Exception as e:
                self.parent.after(0, lambda: messagebox.showerror("Error", f"Failed to update trend: {e}"))
        
        threading.Thread(target=fetch_trend_data, daemon=True).start()
    
    def load_category_stocks(self):
        """Load stocks for the selected category."""
        category = self.category_var.get()
        if not category:
            return
        
        def fetch_stocks():
            try:
                # Get selected date from the new date picker approach
                trade_date = None
                
                if not self.use_latest.get():
                    try:
                        # Get date from date picker
                        selected_date = self.date_picker.get_date()
                        trade_date = selected_date.strftime('%Y-%m-%d')
                    except Exception:
                        pass  # Use None (latest) if date picker fails
                
                result = get_stocks_in_category(category, trade_date=trade_date)
                self.parent.after(0, lambda: self.update_stocks_display(result))
            except Exception as e:
                error_msg = str(e)
                self.parent.after(0, lambda: messagebox.showerror("Error", f"Failed to load stocks: {error_msg}"))
        
        threading.Thread(target=fetch_stocks, daemon=True).start()
    
    def update_stocks_display(self, result):
        """Update the stocks treeview with category data."""
        # Clear existing items
        for item in self.stocks_tree.get_children():
            self.stocks_tree.delete(item)
        
        if not result.get('success', False):
            messagebox.showerror("Error", result.get('error', 'Unknown error'))
            return
        
        stocks = result.get('stocks', [])
        for stock in stocks:
            values = (
                stock.get('symbol', '--'),
                f"{stock.get('trend_rating', 0):.1f}",
                stock.get('daily_trend', '--'),
                stock.get('weekly_trend', '--'),
                stock.get('monthly_trend', '--'),
                f"₹{stock.get('close_price', 0):.1f}",
                f"{stock.get('daily_change_pct', 0):.1f}%"
            )
            self.stocks_tree.insert('', tk.END, values=values)
    
    def create_context_menu(self):
        """Create context menu for stock list."""
        self.context_menu = tk.Menu(self.parent, tearoff=0)
        self.context_menu.add_command(label="📈 Show Trend Chart", command=self.show_selected_chart)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="📋 Copy Symbol", command=self.copy_symbol)
    
    def show_context_menu(self, event):
        """Show context menu on right-click."""
        # Select the item under cursor
        item = self.stocks_tree.identify_row(event.y)
        if item:
            self.stocks_tree.selection_set(item)
            try:
                self.context_menu.tk_popup(event.x_root, event.y_root)
            finally:
                self.context_menu.grab_release()
    
    def show_selected_chart(self):
        """Show chart for currently selected stock."""
        selection = self.stocks_tree.selection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select a stock first.")
            return
        
        item = self.stocks_tree.item(selection[0])
        values = item['values']
        if values:
            symbol = values[0]
            self.display_stock_chart(symbol)
    
    def copy_symbol(self):
        """Copy selected stock symbol to clipboard."""
        selection = self.stocks_tree.selection()
        if not selection:
            return
        
        item = self.stocks_tree.item(selection[0])
        values = item['values']
        if values:
            symbol = values[0]
            self.parent.clipboard_clear()
            self.parent.clipboard_append(symbol)
            # Show brief confirmation
            messagebox.showinfo("Copied", f"Symbol '{symbol}' copied to clipboard!")
    
    def on_stock_double_click(self, event):
        """Handle double-click on stock to show trend analysis chart."""
        # Get selected item
        selection = self.stocks_tree.selection()
        if not selection:
            return
        
        # Get stock symbol from the first column
        item = self.stocks_tree.item(selection[0])
        values = item['values']
        if not values:
            return
        
        symbol = values[0]  # Symbol is in the first column
        
        if not symbol or symbol == '--':
            messagebox.showwarning("No Stock Selected", "Please select a valid stock symbol.")
            return
        
        # Show chart in new window
        self.display_stock_chart(symbol)
    
    def display_stock_chart(self, symbol):
        """Show trend analysis chart for the selected stock."""
        if show_stock_chart is None:
            messagebox.showerror("Chart Unavailable", 
                               "Chart functionality is not available. Please ensure chart_window.py is accessible.")
            return
        
        try:
            # Use the parent directly (same as trends tab approach)
            print(f"Creating chart for {symbol} with parent type: {type(self.parent)}")
            chart_window = show_stock_chart(self.parent, symbol, days=90)
            
        except Exception as e:
            messagebox.showerror("Chart Error", f"Failed to display chart for {symbol}:\n{str(e)}")
            print(f"Error showing chart for {symbol}: {e}")
            import traceback
            traceback.print_exc()
    
    def setup_sectoral_tab(self):
        """Set up the sectoral analysis tab."""
        sectoral_frame = ttk.Frame(self.notebook)
        self.notebook.add(sectoral_frame, text="🏭 Sectoral Analysis")
        
        # Title
        title_frame = ttk.Frame(sectoral_frame)
        title_frame.pack(fill=tk.X, padx=10, pady=10)
        ttk.Label(title_frame, text="Sectoral Trend Analysis", 
                 font=('Arial', 14, 'bold')).pack(side=tk.LEFT)
        
        # Refresh sectoral data button
        ttk.Button(title_frame, text="Refresh Sectoral Data", 
                  command=self.refresh_sectoral_data).pack(side=tk.RIGHT)
        
        # Controls frame
        controls_frame = ttk.LabelFrame(sectoral_frame, text="Analysis Controls", padding=10)
        controls_frame.pack(fill=tk.X, padx=10, pady=(0, 10))
        
        # Sector selection
        sector_select_frame = ttk.Frame(controls_frame)
        sector_select_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(sector_select_frame, text="Select Sector:").pack(side=tk.LEFT)
        self.sector_var = tk.StringVar()
        
        # Populate sectors dynamically
        available_sectors = []
        if index_api:
            try:
                all_indices = index_api.get_all_indices()
                # Focus on major sectoral indices
                priority_sectors = ['NIFTY-BANK', 'NIFTY-IT', 'NIFTY-PHARMA', 'NIFTY-AUTO', 
                                  'NIFTY-FMCG', 'NIFTY-METALS', 'NIFTY-ENERGY', 'NIFTY-REALTY']
                available_sectors = [s for s in priority_sectors if s in all_indices]
                # Add other available sectors
                for sector in all_indices:
                    if sector not in available_sectors and 'NIFTY' in sector:
                        available_sectors.append(sector)
            except:
                available_sectors = ['NIFTY-BANK', 'NIFTY-IT', 'NIFTY-PHARMA', 'NIFTY-AUTO', 'NIFTY-FMCG']
        else:
            available_sectors = ['NIFTY-BANK', 'NIFTY-IT', 'NIFTY-PHARMA', 'NIFTY-AUTO', 'NIFTY-FMCG']
        
        self.sector_combo = ttk.Combobox(sector_select_frame, textvariable=self.sector_var,
                                        values=available_sectors, width=20)
        self.sector_combo.pack(side=tk.LEFT, padx=(5, 0))
        if available_sectors:
            self.sector_combo.set(available_sectors[0])
        
        # Analysis date (dedicated for sectoral analysis)
        date_frame = ttk.Frame(controls_frame)
        date_frame.pack(fill=tk.X, pady=(10, 0))
        
        # Latest data toggle for sectoral analysis
        self.sectoral_use_latest = tk.BooleanVar(value=True)
        latest_check = ttk.Checkbutton(date_frame, text="Use Latest Data", 
                                     variable=self.sectoral_use_latest, 
                                     command=self.on_sectoral_latest_toggle)
        latest_check.pack(side=tk.LEFT, padx=(0, 10))
        
        # Date picker for sectoral analysis
        ttk.Label(date_frame, text="Select Date:").pack(side=tk.LEFT)
        
        # Initialize sectoral date picker with current date
        self.sectoral_date_picker = DateEntry(date_frame, width=12, background='darkblue',
                                   foreground='white', borderwidth=2,
                                   date_pattern='yyyy-mm-dd', state='disabled')
        self.sectoral_date_picker.pack(side=tk.LEFT, padx=(5, 10))
        self.sectoral_date_picker.bind('<<DateEntrySelected>>', self.on_sectoral_date_selected)
        
        # Status for sectoral date selection
        self.sectoral_date_info = ttk.Label(date_frame, text="Using latest available data", foreground="green")
        self.sectoral_date_info.pack(side=tk.LEFT, padx=(10, 0))
        
        # Refresh available dates button
        ttk.Button(date_frame, text="📅 Check Available Dates", 
                  command=self.check_sectoral_dates).pack(side=tk.LEFT, padx=(10, 0))
        
        # Analyze buttons
        button_frame = ttk.Frame(controls_frame)
        button_frame.pack(fill=tk.X)
        
        ttk.Button(button_frame, text="Analyze Single Sector", 
                  command=self.analyze_single_sector).pack(side=tk.LEFT, padx=(0, 10))
        
        ttk.Button(button_frame, text="Compare Top 5 Sectors", 
                  command=self.compare_top_sectors).pack(side=tk.LEFT, padx=(0, 10))
        
        ttk.Button(button_frame, text="Compare All Major Sectors", 
                  command=self.compare_all_sectors).pack(side=tk.LEFT, padx=(0, 10))
        
        # PDF Report button
        ttk.Button(button_frame, text="📄 Generate PDF Report", 
                  command=self.generate_sectoral_pdf_report).pack(side=tk.LEFT, padx=(0, 10))
        
        # Results frame with notebook for different views
        results_frame = ttk.LabelFrame(sectoral_frame, text="Analysis Results", padding=10)
        results_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
        
        # Create notebook for sectoral results
        self.sectoral_notebook = ttk.Notebook(results_frame)
        self.sectoral_notebook.pack(fill=tk.BOTH, expand=True)
        
        # Single sector analysis tab
        self.setup_single_sector_tab()
        
        # Multi-sector comparison tab
        self.setup_multi_sector_tab()
        
        # Status bar for sectoral analysis
        self.sectoral_status = ttk.Label(sectoral_frame, text="Ready for sectoral analysis", 
                                       foreground="blue")
        self.sectoral_status.pack(side=tk.BOTTOM, fill=tk.X, padx=10, pady=(0, 5))
    
    def setup_single_sector_tab(self):
        """Set up single sector analysis view."""
        single_sector_frame = ttk.Frame(self.sectoral_notebook)
        self.sectoral_notebook.add(single_sector_frame, text="Single Sector")
        
        # Metrics display
        metrics_frame = ttk.LabelFrame(single_sector_frame, text="Sector Metrics", padding=10)
        metrics_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Create metrics grid for single sector
        self.sectoral_metrics_frame = ttk.Frame(metrics_frame)
        self.sectoral_metrics_frame.pack(fill=tk.X)
        
        self.sectoral_metric_labels = {}
        sectoral_metrics = [
            ('sector_name', 'Sector', 0, 0),
            ('total_stocks', 'Total Stocks', 0, 1),
            ('symbols_analyzed', 'Analyzed', 0, 2),
            ('bullish_percent', 'Bullish %', 1, 0),
            ('bearish_percent', 'Bearish %', 1, 1),
            ('daily_uptrend_percent', 'Daily Uptrend %', 1, 2),
        ]
        
        for key, label, row, col in sectoral_metrics:
            frame = ttk.Frame(self.sectoral_metrics_frame)
            frame.grid(row=row, column=col, padx=10, pady=5, sticky='w')
            
            ttk.Label(frame, text=f"{label}:", font=('Arial', 10, 'bold')).pack()
            value_label = ttk.Label(frame, text="--", font=('Arial', 12))
            value_label.pack()
            self.sectoral_metric_labels[key] = value_label
        
        # Stock breakdown
        stocks_frame = ttk.LabelFrame(single_sector_frame, text="Stock Breakdown", padding=10)
        stocks_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Treeview for individual stocks
        columns = ('Symbol', 'Trend Rating', 'Daily Trend', 'Weekly Trend', 'Monthly Trend')
        self.sectoral_stocks_tree = ttk.Treeview(stocks_frame, columns=columns, show='headings', height=10)
        
        for col in columns:
            self.sectoral_stocks_tree.heading(col, text=col)
            self.sectoral_stocks_tree.column(col, width=120)
        
        # Scrollbar for stocks tree
        stocks_scroll = ttk.Scrollbar(stocks_frame, orient=tk.VERTICAL, command=self.sectoral_stocks_tree.yview)
        self.sectoral_stocks_tree.configure(yscrollcommand=stocks_scroll.set)
        
        self.sectoral_stocks_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        stocks_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Bind double-click to show stock chart
        self.sectoral_stocks_tree.bind('<Double-1>', self.on_sectoral_stock_double_click)
    
    def setup_multi_sector_tab(self):
        """Set up multi-sector comparison view."""
        multi_sector_frame = ttk.Frame(self.sectoral_notebook)
        self.sectoral_notebook.add(multi_sector_frame, text="Multi-Sector Comparison")
        
        # Comparison table
        comparison_frame = ttk.LabelFrame(multi_sector_frame, text="Sector Performance Comparison", padding=10)
        comparison_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Treeview for comparison
        columns = ('Sector', 'Total Stocks', 'Bullish %', 'Bearish %', 'Daily Uptrend %', 'Weekly Uptrend %')
        self.comparison_tree = ttk.Treeview(comparison_frame, columns=columns, show='headings', height=12)
        
        for col in columns:
            self.comparison_tree.heading(col, text=col, command=lambda _col=col: self.sort_comparison(_col))
            self.comparison_tree.column(col, width=120)
        
        # Scrollbar for comparison tree
        comparison_scroll = ttk.Scrollbar(comparison_frame, orient=tk.VERTICAL, command=self.comparison_tree.yview)
        self.comparison_tree.configure(yscrollcommand=comparison_scroll.set)
        
        self.comparison_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        comparison_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Bind double-click to show detailed sector stocks
        self.comparison_tree.bind('<Double-1>', self.on_sector_comparison_double_click)
        
        # Add summary labels below the comparison
        summary_frame = ttk.Frame(multi_sector_frame)
        summary_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.best_sector_label = ttk.Label(summary_frame, text="Best Performing Sector: --", 
                                         font=('Arial', 11, 'bold'), foreground="green")
        self.best_sector_label.pack(anchor=tk.W)
        
        self.worst_sector_label = ttk.Label(summary_frame, text="Weakest Performing Sector: --", 
                                          font=('Arial', 11, 'bold'), foreground="red")
        self.worst_sector_label.pack(anchor=tk.W)
    
    def refresh_sectoral_data(self):
        """Refresh sectoral analysis data."""
        if index_api is None:
            messagebox.showerror("API Unavailable", "Index symbols API is not available. Please check the setup.")
            return
        
        self.sectoral_status.configure(text="🔄 Refreshing sectoral data...", foreground="orange")
        
        def refresh_indices():
            try:
                # Get fresh list of available indices
                all_indices = index_api.get_all_indices()
                
                # Update sector combo values
                priority_sectors = ['NIFTY-BANK', 'NIFTY-IT', 'NIFTY-PHARMA', 'NIFTY-AUTO', 
                                  'NIFTY-FMCG', 'NIFTY-METALS', 'NIFTY-ENERGY', 'NIFTY-REALTY']
                available_sectors = [s for s in priority_sectors if s in all_indices]
                
                # Add other available sectors
                for sector in all_indices:
                    if sector not in available_sectors and 'NIFTY' in sector:
                        available_sectors.append(sector)
                
                def update_ui():
                    self.sector_combo['values'] = available_sectors
                    if available_sectors and not self.sector_var.get():
                        self.sector_combo.set(available_sectors[0])
                    
                    self.sectoral_status.configure(
                        text=f"✅ {len(available_sectors)} sectors available", 
                        foreground="green"
                    )
                
                self.parent.after(0, update_ui)
                
            except Exception as e:
                error_msg = f"Failed to refresh sectoral data: {str(e)}"
                self.parent.after(0, lambda: self.handle_sectoral_error(error_msg))
        
        threading.Thread(target=refresh_indices, daemon=True).start()
    
    def get_analysis_date(self):
        """Get the current analysis date from main date picker."""
        if self.use_latest.get():
            return None  # Use latest available
        else:
            try:
                return self.date_picker.get_date()
            except:
                return None
    
    def get_sectoral_analysis_date(self):
        """Get the current analysis date for sectoral analysis."""
        if self.sectoral_use_latest.get():
            return None  # Use latest available
        else:
            try:
                return self.sectoral_date_picker.get_date()
            except:
                return None
    
    def on_sectoral_latest_toggle(self):
        """Handle toggle between latest data and date picker for sectoral analysis."""
        if self.sectoral_use_latest.get():
            # Using latest data
            self.sectoral_date_picker.configure(state='disabled')
            self.sectoral_date_info.configure(text="Using latest available data", foreground="green")
        else:
            # Using date picker
            self.sectoral_date_picker.configure(state='normal')
            self.sectoral_date_info.configure(text="Select a date to analyze", foreground="blue")
    
    def on_sectoral_date_selected(self, event=None):
        """Handle sectoral date picker selection."""
        if not self.sectoral_use_latest.get():
            try:
                selected_date = self.sectoral_date_picker.get_date()
                self.sectoral_date_info.configure(
                    text=f"Selected: {selected_date.strftime('%Y-%m-%d')}", 
                    foreground="blue"
                )
            except Exception as e:
                self.sectoral_date_info.configure(
                    text="Date selection error", 
                    foreground="red"
                )
    
    def check_sectoral_dates(self):
        """Check and display available dates for sectoral analysis."""
        self.sectoral_status.configure(text="🔄 Checking available dates...", foreground="orange")
        
        def fetch_dates():
            try:
                # Import the function
                from services.market_breadth_service import get_sectoral_analysis_dates
                
                available_dates = get_sectoral_analysis_dates(30)
                
                def show_dates():
                    if available_dates:
                        date_list = '\n'.join([f"📅 {d}" for d in available_dates[:15]])
                        if len(available_dates) > 15:
                            date_list += f"\n... and {len(available_dates) - 15} more dates"
                        
                        messagebox.showinfo(
                            "Available Analysis Dates", 
                            f"📊 Found {len(available_dates)} dates with trend analysis data:\n\n"
                            f"{date_list}\n\n"
                            f"💡 Latest: {available_dates[0]}\n"
                            f"📈 You can analyze any sector for these dates."
                        )
                        
                        # Update status
                        self.sectoral_status.configure(
                            text=f"✅ {len(available_dates)} analysis dates available (latest: {available_dates[0]})", 
                            foreground="green"
                        )
                    else:
                        messagebox.showwarning(
                            "No Data Available",
                            "❌ No trend analysis data found in database.\n\n"
                            "Please ensure:\n"
                            "• Database connection is working\n"
                            "• trend_analysis table has data\n"
                            "• Run trend analysis calculations first"
                        )
                        self.sectoral_status.configure(text="❌ No analysis data available", foreground="red")
                
                self.parent.after(0, show_dates)
                
            except Exception as e:
                error_msg = f"Error checking dates: {str(e)}"
                self.parent.after(0, lambda: self.handle_sectoral_error(error_msg))
        
        threading.Thread(target=fetch_dates, daemon=True).start()
    
    def analyze_single_sector(self):
        """Analyze a single sector."""
        sector = self.sector_var.get()
        if not sector:
            messagebox.showwarning("No Sector", "Please select a sector to analyze.")
            return
        
        # Get the selected date
        analysis_date = self.get_sectoral_analysis_date()
        date_str = analysis_date.strftime('%Y-%m-%d') if analysis_date else "latest"
        
        self.sectoral_status.configure(text=f"🔄 Analyzing {sector} for {date_str}...", foreground="orange")
        
        def fetch_analysis():
            try:
                result = get_sectoral_breadth(sector, analysis_date)
                
                self.parent.after(0, lambda: self.update_single_sector_display(result, sector))
                
            except Exception as e:
                error_msg = f"Failed to analyze {sector} for {date_str}: {str(e)}"
                self.parent.after(0, lambda: self.handle_sectoral_error(error_msg))
        
        threading.Thread(target=fetch_analysis, daemon=True).start()
    
    def compare_top_sectors(self):
        """Compare top 5 major sectors."""
        top_sectors = ['NIFTY-BANK', 'NIFTY-IT', 'NIFTY-PHARMA', 'NIFTY-AUTO', 'NIFTY-FMCG']
        self._compare_sectors(top_sectors, "top 5 sectors")
    
    def compare_all_sectors(self):
        """Compare all major sectors."""
        if index_api is None:
            messagebox.showerror("API Unavailable", "Index symbols API is not available.")
            return
        
        try:
            all_indices = index_api.get_all_indices()
            major_sectors = [s for s in all_indices.keys() if 'NIFTY' in s and len(s) < 25]  # Filter reasonable sector names
            major_sectors = major_sectors[:10]  # Limit to first 10 to avoid overload
            self._compare_sectors(major_sectors, f"{len(major_sectors)} major sectors")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to get sectors list: {str(e)}")
    
    def _compare_sectors(self, sectors, description):
        """Internal method to compare multiple sectors."""
        if not sectors:
            messagebox.showwarning("No Sectors", "No sectors to compare.")
            return
        
        # Get the selected date
        analysis_date = self.get_sectoral_analysis_date()
        date_str = analysis_date.strftime('%Y-%m-%d') if analysis_date else "latest"
        
        self.sectoral_status.configure(text=f"🔄 Comparing {description} for {date_str}...", foreground="orange")
        
        def fetch_comparison():
            try:
                result = compare_sectoral_breadth(sectors, analysis_date)
                
                self.parent.after(0, lambda: self.update_comparison_display(result, description))
                
            except Exception as e:
                error_msg = f"Failed to compare {description} for {date_str}: {str(e)}"
                self.parent.after(0, lambda: self.handle_sectoral_error(error_msg))
        
        threading.Thread(target=fetch_comparison, daemon=True).start()
    
    def update_single_sector_display(self, result, sector):
        """Update single sector analysis display."""
        if not result.get('success', False):
            error_msg = result.get('error', 'Unknown error')
            
            # Enhanced error message with suggestions
            enhanced_msg = f"Failed to analyze {sector}:\n\n{error_msg}"
            
            # Add helpful suggestions if available
            if 'latest_available' in result and result['latest_available']:
                enhanced_msg += f"\n\n💡 Suggestions:"
                enhanced_msg += f"\n• Try latest available date: {result['latest_available']}"
                
            if 'nearby_dates' in result and result['nearby_dates']:
                enhanced_msg += f"\n• Try nearby dates: {', '.join(result['nearby_dates'][:3])}"
            
            enhanced_msg += "\n\n📅 Click 'Check Available Dates' to see all available analysis dates."
            
            messagebox.showerror("Sectoral Analysis Error", enhanced_msg)
            self.sectoral_status.configure(text="❌ Analysis failed - check available dates", foreground="red")
            return
        
        # Switch to single sector tab
        self.sectoral_notebook.select(0)
        
        # Update metrics
        metrics = {
            'sector_name': sector,
            'total_stocks': result.get('total_stocks', 0),
            'symbols_analyzed': result.get('symbols_analyzed', 0),
            'bullish_percent': result.get('breadth_summary', {}).get('bullish_percent', 0),
            'bearish_percent': result.get('breadth_summary', {}).get('bearish_percent', 0),
            'daily_uptrend_percent': result.get('technical_breadth', {}).get('daily_uptrend_percent', 0),
        }
        
        for key, value in metrics.items():
            if key in self.sectoral_metric_labels:
                if key == 'sector_name':
                    self.sectoral_metric_labels[key].config(text=str(value))
                elif isinstance(value, (int, float)) and key.endswith('_percent'):
                    self.sectoral_metric_labels[key].config(text=f"{value:.1f}%")
                else:
                    self.sectoral_metric_labels[key].config(text=str(value))
        
        # Update stocks tree
        for item in self.sectoral_stocks_tree.get_children():
            self.sectoral_stocks_tree.delete(item)
        
        # Get individual stock data from the result
        sector_data = result.get('sector_data')
        if sector_data is not None and not sector_data.empty:
            for _, row in sector_data.iterrows():
                values = (
                    row['symbol'],
                    f"{row['trend_rating']:.1f}",
                    row['daily_trend'],
                    row['weekly_trend'],
                    row['monthly_trend']
                )
                self.sectoral_stocks_tree.insert('', tk.END, values=values)
        
        # Update status
        analysis_date = result.get('analysis_date', 'latest')
        self.sectoral_status.configure(
            text=f"✅ {sector}: {metrics['symbols_analyzed']}/{metrics['total_stocks']} stocks analyzed ({analysis_date})", 
            foreground="green"
        )
        
        # Update sectoral date info
        self.sectoral_date_info.configure(text=f"Analyzed: {analysis_date}")
        
        # Show success message for first-time users
        if result.get('symbols_analyzed', 0) > 0:
            coverage = result.get('coverage_percent', 0)
            messagebox.showinfo(
                "Sectoral Analysis Complete",
                f"✅ {sector} Analysis Results:\n\n"
                f"📊 Coverage: {metrics['symbols_analyzed']}/{metrics['total_stocks']} stocks ({coverage:.1f}%)\n"
                f"📈 Bullish: {metrics['bullish_percent']:.1f}%\n"
                f"📉 Bearish: {metrics['bearish_percent']:.1f}%\n"
                f"⬆️ Daily Uptrend: {metrics['daily_uptrend_percent']:.1f}%\n\n"
                f"💡 Double-click any stock to view its chart!"
            )
    
    def update_comparison_display(self, result, description):
        """Update multi-sector comparison display."""
        if not result.get('comparison_summary'):
            # Enhanced error handling for comparison
            error_details = "No comparison data available"
            if 'sectors_attempted' in result:
                error_details += f" (tried {result['sectors_attempted']} sectors)"
            
            messagebox.showwarning(
                "Sectoral Comparison Failed",
                f"❌ {error_details} for {description}.\n\n"
                f"📅 Analysis Date: {result.get('analysis_date', 'latest')}\n\n"
                f"💡 Possible solutions:\n"
                f"• Try a different date\n"
                f"• Click 'Check Available Dates' to see valid dates\n"
                f"• Check if sectors have data for this date"
            )
            self.sectoral_status.configure(text="❌ Comparison failed - check available dates", foreground="red")
            return
        
        # Switch to comparison tab
        self.sectoral_notebook.select(1)
        
        # Clear existing items
        for item in self.comparison_tree.get_children():
            self.comparison_tree.delete(item)
        
        # Sort by bullish percentage (descending)
        comparison_data = sorted(result['comparison_summary'], 
                               key=lambda x: x.get('bullish_percent', 0), reverse=True)
        
        # Populate comparison tree
        for sector_data in comparison_data:
            values = (
                sector_data.get('sector', '--'),
                sector_data.get('total_stocks', 0),
                f"{sector_data.get('bullish_percent', 0):.1f}%",
                f"{sector_data.get('bearish_percent', 0):.1f}%",
                f"{sector_data.get('daily_uptrend_percent', 0):.1f}%",
                f"{sector_data.get('weekly_uptrend_percent', 0):.1f}%"
            )
            self.comparison_tree.insert('', tk.END, values=values)
        
        # Update summary labels
        if comparison_data:
            best_sector = comparison_data[0]
            worst_sector = comparison_data[-1]
            
            self.best_sector_label.configure(
                text=f"Best Performing: {best_sector['sector']} ({best_sector.get('bullish_percent', 0):.1f}% bullish)"
            )
            self.worst_sector_label.configure(
                text=f"Weakest Performing: {worst_sector['sector']} ({worst_sector.get('bullish_percent', 0):.1f}% bullish)"
            )
        
        # Update status
        analysis_date = result.get('analysis_date', 'latest')
        successful_analyses = result.get('successful_analyses', 0)
        total_attempted = result.get('sectors_analyzed', 0)
        
        self.sectoral_status.configure(
            text=f"✅ Compared {successful_analyses}/{total_attempted} sectors successfully ({analysis_date})", 
            foreground="green"
        )
        
        # Update sectoral date info
        self.sectoral_date_info.configure(text=f"Compared: {analysis_date}")
        
        # Show comparison summary
        if successful_analyses > 0:
            messagebox.showinfo(
                "Sectoral Comparison Complete",
                f"📊 {description.title()} Comparison Results:\n\n"
                f"✅ Successfully analyzed: {successful_analyses} sectors\n"
                f"🥇 Best performer: {best_sector['sector']} ({best_sector.get('bullish_percent', 0):.1f}% bullish)\n"
                f"🔴 Weakest: {worst_sector['sector']} ({worst_sector.get('bullish_percent', 0):.1f}% bullish)\n\n"
                f"📅 Analysis date: {analysis_date}\n"
                f"📈 Click on any sector row for details!"
            )
    
    def sort_comparison(self, column):
        """Sort comparison tree by column."""
        # This is a simplified sort - could be enhanced
        children = list(self.comparison_tree.get_children())
        if not children:
            return
        
        # Get column index
        columns = self.comparison_tree['columns']
        try:
            col_idx = list(columns).index(column)
        except ValueError:
            return
        
        # Extract values and sort
        def get_sort_value(item):
            values = self.comparison_tree.item(item, 'values')
            if col_idx < len(values):
                val = values[col_idx]
                # Try to convert percentage to float
                if isinstance(val, str) and val.endswith('%'):
                    try:
                        return float(val[:-1])
                    except ValueError:
                        return 0
                # Try to convert to float
                try:
                    return float(val)
                except (ValueError, TypeError):
                    return str(val)
            return ''
        
        children.sort(key=get_sort_value, reverse=True)
        
        # Reorder items
        for index, item in enumerate(children):
            self.comparison_tree.move(item, '', index)
    
    def on_sectoral_stock_double_click(self, event):
        """Handle double-click on sectoral stock."""
        selection = self.sectoral_stocks_tree.selection()
        if not selection:
            return
        
        item = self.sectoral_stocks_tree.item(selection[0])
        values = item['values']
        if not values:
            return
        
        symbol = values[0]
        self.display_stock_chart(symbol)
    
    def on_sector_comparison_double_click(self, event):
        """Handle double-click on sector in comparison table to show detailed stocks."""
        try:
            selection = self.comparison_tree.selection()
            if not selection:
                messagebox.showinfo("No Selection", "Please select a sector row first.")
                return
            
            item = self.comparison_tree.item(selection[0])
            if not item['values']:
                messagebox.showwarning("No Data", "Selected row has no data.")
                return
            
            sector_name = item['values'][0]  # First column is sector name
            
            # Convert sector name back to sector code
            sector_code = f"NIFTY-{sector_name}" if not sector_name.startswith('NIFTY') else sector_name
            
            # Get analysis date
            analysis_date = self.get_sectoral_analysis_date()
            
            # Debug information
            print(f"Opening sector detail for: {sector_code}")
            print(f"Analysis date: {analysis_date}")
            
            # Open detailed sector window
            try:
                from gui.windows.sector_detail_window import SectorDetailWindow
                # Use the parent window directly - this is most reliable
                parent_window = self.parent
                SectorDetailWindow(parent_window, sector_code, analysis_date)
                print("Sector detail window opened successfully")
                
            except ImportError as e:
                messagebox.showerror("Import Error", f"Could not import SectorDetailWindow:\n{str(e)}")
            except Exception as e:
                import traceback
                error_details = traceback.format_exc()
                print(f"Error opening sector window: {e}")
                print(f"Error details: {error_details}")
                messagebox.showerror("Error", f"Failed to open sector detail window:\n{str(e)}")
                
        except Exception as outer_e:
            print(f"Outer error in double-click handler: {outer_e}")
            import traceback
            traceback.print_exc()
            messagebox.showerror("Handler Error", f"Error in double-click handler:\n{str(outer_e)}")
    
    def generate_sectoral_pdf_report(self):
        """Generate PDF report for sectoral analysis."""
        if not PDF_AVAILABLE:
            messagebox.showerror(
                "PDF Generation Unavailable",
                "PDF generation requires the ReportLab library.\n\n"
                "Please install it using:\n"
                "pip install reportlab"
            )
            return
        
        # Get the selected analysis date
        analysis_date = self.get_sectoral_analysis_date()
        
        # Convert date to string format for PDF generation
        if analysis_date is None:
            # Use latest date - need to get it from available dates
            try:
                from services.market_breadth_service import get_sectoral_analysis_dates
                available_dates = get_sectoral_analysis_dates(1)
                if available_dates:
                    analysis_date_str = available_dates[0]
                    display_date = analysis_date_str
                else:
                    analysis_date_str = datetime.now().strftime('%Y-%m-%d')
                    display_date = "latest available"
            except:
                analysis_date_str = datetime.now().strftime('%Y-%m-%d')
                display_date = "latest available"
        else:
            # Convert date object to string
            if hasattr(analysis_date, 'strftime'):
                analysis_date_str = analysis_date.strftime('%Y-%m-%d')
                display_date = analysis_date_str
            else:
                analysis_date_str = str(analysis_date)
                display_date = analysis_date_str
        
        # Show progress dialog
        progress_window = tk.Toplevel(self.parent)
        progress_window.title("Generating PDF Report")
        progress_window.geometry("400x150")
        progress_window.transient(self.parent)
        progress_window.grab_set()
        
        # Center the progress window
        progress_window.update_idletasks()
        x = (progress_window.winfo_screenwidth() // 2) - (400 // 2)
        y = (progress_window.winfo_screenheight() // 2) - (150 // 2)
        progress_window.geometry(f"400x150+{x}+{y}")
        
        # Progress content
        ttk.Label(progress_window, text="📄 Generating Sectoral Analysis PDF Report", 
                 font=("Arial", 12, "bold")).pack(pady=10)
        
        progress_label = ttk.Label(progress_window, text=f"📅 Analysis Date: {display_date}")
        progress_label.pack(pady=5)
        
        status_label = ttk.Label(progress_window, text="🔄 Collecting sectoral data...", 
                               foreground="blue")
        status_label.pack(pady=5)
        
        # Progress bar
        progress_bar = ttk.Progressbar(progress_window, mode='indeterminate')
        progress_bar.pack(pady=10, padx=20, fill=tk.X)
        progress_bar.start()
        
        def generate_pdf():
            """Generate PDF in background thread."""
            try:
                status_label.config(text="📊 Analyzing all major sectors...")
                self.parent.update_idletasks()
                
                # Generate PDF report
                success, result = generate_sectoral_pdf_report(analysis_date_str)
                
                self.parent.after(0, lambda: handle_pdf_result(success, result))
                
            except Exception as e:
                self.parent.after(0, lambda: handle_pdf_result(False, f"Unexpected error: {str(e)}"))
        
        def handle_pdf_result(success, result):
            """Handle PDF generation result."""
            progress_bar.stop()
            progress_window.destroy()
            
            if success:
                # Success - show file location and options
                result_window = tk.Toplevel(self.parent)
                result_window.title("PDF Report Generated")
                result_window.geometry("500x200")
                result_window.transient(self.parent)
                result_window.grab_set()
                
                # Center the result window
                result_window.update_idletasks()
                x = (result_window.winfo_screenwidth() // 2) - (500 // 2)
                y = (result_window.winfo_screenheight() // 2) - (200 // 2)
                result_window.geometry(f"500x200+{x}+{y}")
                
                ttk.Label(result_window, text="✅ PDF Report Generated Successfully!", 
                         font=("Arial", 14, "bold"), foreground="green").pack(pady=10)
                
                ttk.Label(result_window, text=f"📁 File: {os.path.basename(result)}", 
                         font=("Arial", 10)).pack(pady=5)
                
                ttk.Label(result_window, text=f"📍 Location: {os.path.dirname(os.path.abspath(result))}", 
                         font=("Arial", 9), foreground="gray").pack(pady=5)
                
                # Action buttons
                button_frame = ttk.Frame(result_window)
                button_frame.pack(pady=20)
                
                ttk.Button(button_frame, text="📂 Open Folder", 
                          command=lambda: self.open_file_location(result)).pack(side=tk.LEFT, padx=10)
                
                ttk.Button(button_frame, text="📄 Open PDF", 
                          command=lambda: self.open_pdf_file(result)).pack(side=tk.LEFT, padx=10)
                
                ttk.Button(button_frame, text="✓ Close", 
                          command=result_window.destroy).pack(side=tk.LEFT, padx=10)
                
                # Update status
                self.sectoral_status.configure(text=f"✅ PDF report generated successfully ({display_date})", 
                                             foreground="green")
            else:
                # Error - show error message
                messagebox.showerror(
                    "PDF Generation Failed", 
                    f"Failed to generate PDF report:\n\n{result}\n\n"
                    f"Please check:\n"
                    f"• Database connection is working\n"
                    f"• ReportLab library is installed\n"
                    f"• Selected date has analysis data available"
                )
                
                self.sectoral_status.configure(text=f"❌ PDF generation failed", foreground="red")
        
        # Start PDF generation in background
        threading.Thread(target=generate_pdf, daemon=True).start()
    
    def open_file_location(self, file_path):
        """Open the file location in system explorer."""
        try:
            import subprocess
            import platform
            
            if platform.system() == 'Windows':
                subprocess.run(['explorer', '/select,', file_path])
            elif platform.system() == 'Darwin':  # macOS
                subprocess.run(['open', '-R', file_path])
            else:  # Linux and others
                subprocess.run(['xdg-open', os.path.dirname(file_path)])
        except Exception as e:
            messagebox.showinfo("File Location", f"File saved at:\n{os.path.abspath(file_path)}")
    
    def open_pdf_file(self, file_path):
        """Open the PDF file with default application."""
        try:
            import subprocess
            import platform
            
            if platform.system() == 'Windows':
                os.startfile(file_path)
            elif platform.system() == 'Darwin':  # macOS
                subprocess.run(['open', file_path])
            else:  # Linux and others
                subprocess.run(['xdg-open', file_path])
        except Exception as e:
            messagebox.showerror("Open PDF", f"Could not open PDF file:\n{str(e)}")
    
    def handle_sectoral_error(self, error_msg):
        """Handle sectoral analysis errors."""
        self.sectoral_status.configure(text="❌ Sectoral analysis failed", foreground="red")
        messagebox.showerror("Sectoral Analysis Error", error_msg)
        print(f"Sectoral analysis error: {error_msg}")


# Test function for development
def test_market_breadth_gui():
    """Test the market breadth GUI."""
    root = tk.Tk()
    root.title("Market Breadth Analysis Test")
    root.geometry("1200x800")
    
    # Create the tab
    tab = MarketBreadthTab(root)
    
    root.mainloop()


if __name__ == "__main__":
    test_market_breadth_gui()