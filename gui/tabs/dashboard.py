"""
Dashboard tab for Stock Screener GUI with organized subsections.

Provides:
1. Database Status - Database tables monitoring 
2. RSI Divergences - RSI divergence analysis
3. Trend Ratings Status - Trend rating distribution and analysis
4. SMA Trends Status - Moving average trend analysis
"""

import tkinter as tk
from tkinter import ttk
import os
from datetime import datetime, date
from typing import Dict, Any
from dotenv import load_dotenv

# Chart imports
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
try:
    import mplcursors
    CURSORS_AVAILABLE = True
except ImportError:
    CURSORS_AVAILABLE = False
    print("mplcursors not available - chart tooltips disabled")
import matplotlib.dates as mdates
import numpy as np
import pandas as pd

# SMA analysis imports
try:
    import sma50_scanner
except ImportError:
    sma50_scanner = None

# Configure matplotlib to suppress emoji warnings
import warnings
warnings.filterwarnings('ignore', category=UserWarning, message='.*Glyph.*missing from font.*')

# Load environment variables
load_dotenv()


class DashboardTab:
    """Enhanced Dashboard tab with organized subsections."""
    
    def __init__(self, parent):
        """Initialize the dashboard tab."""
        self.parent = parent
        self.main_frame = ttk.Frame(parent)
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Shared database engine to prevent connection pool exhaustion
        self._engine = None
        self._engine_lock = None
        
        # Initialize components
        self.create_dashboard()
        
        # Add loading indicator
        self.show_loading_state()
        
        # Start background refresh after a brief delay
        self.parent.after(100, self.start_background_refresh)
    
    def create_dashboard(self):
        """Create the dashboard UI with subsections."""
        # Title
        title_frame = ttk.Frame(self.main_frame)
        title_frame.pack(fill=tk.X, pady=(0, 20))
        
        ttk.Label(title_frame, text="📊 Database Dashboard", 
                 font=('Arial', 18, 'bold')).pack(side=tk.LEFT)
        
        # Refresh button
        ttk.Button(title_frame, text="🔄 Refresh All", 
                  command=self.refresh_dashboard).pack(side=tk.RIGHT)
        
        # Last updated label
        self.last_updated_label = ttk.Label(title_frame, text="", foreground="gray")
        self.last_updated_label.pack(side=tk.RIGHT, padx=(0, 10))
        
        # Create notebook for subsections
        self.notebook = ttk.Notebook(self.main_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True)
        
        # Create all subsections
        self.create_database_status_section()
        self.create_rsi_divergences_section()
        self.create_trend_ratings_section()  
        self.create_sma_trends_section()
        
        # Don't run initial refresh here - will be done in background
    
    def create_database_status_section(self):
        """Create Database Status subsection - monitors database tables."""
        db_frame = ttk.Frame(self.notebook)
        self.notebook.add(db_frame, text="🗄️ Database Status")
        
        # Status cards for database tables
        cards_frame = ttk.Frame(db_frame)
        cards_frame.pack(fill=tk.X, pady=10, padx=10)
        
        # Configure grid columns
        for i in range(4):
            cards_frame.grid_columnconfigure(i, weight=1)
        
        # Create status cards
        self.bhav_card = self.create_status_card(cards_frame, "📈 BHAV Data", "Loading...", "gray", 0, 0)
        self.sma_card = self.create_status_card(cards_frame, "📊 SMAs", "Loading...", "gray", 0, 1)
        self.rsi_card = self.create_status_card(cards_frame, "📉 RSI", "Loading...", "gray", 0, 2)
        self.trend_card = self.create_status_card(cards_frame, "🎯 Trends", "Loading...", "gray", 0, 3)
        
        # Database details section with charts
        details_frame = ttk.LabelFrame(db_frame, text="📋 Database Details & Analytics", padding=10)
        details_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Create notebook for details and charts
        details_notebook = ttk.Notebook(details_frame)
        details_notebook.pack(fill=tk.BOTH, expand=True)
        
        # Charts tab (first tab for immediate visual insight)
        charts_tab = ttk.Frame(details_notebook)
        details_notebook.add(charts_tab, text="📊 Analytics Charts")
        
        # Create database charts area
        self.db_charts_frame = charts_tab
        self.create_database_charts()
        
        # Text details tab (second tab for detailed information)
        text_tab = ttk.Frame(details_notebook)
        details_notebook.add(text_tab, text="📄 Status Report")
        
        text_frame = ttk.Frame(text_tab)
        text_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.db_details_text = tk.Text(text_frame, height=12, wrap=tk.WORD, font=('Consolas', 10))
        self.db_details_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        scrollbar = ttk.Scrollbar(text_frame, orient=tk.VERTICAL, command=self.db_details_text.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.db_details_text.configure(yscrollcommand=scrollbar.set)
    
    def create_rsi_divergences_section(self):
        """Create RSI Divergences subsection."""
        rsi_frame = ttk.Frame(self.notebook)
        self.notebook.add(rsi_frame, text="📈 RSI Divergences")
        
        # Header
        header_frame = ttk.Frame(rsi_frame)
        header_frame.pack(fill=tk.X, pady=10, padx=10)
        
        ttk.Label(header_frame, text="📈 RSI Divergence Analysis", 
                 font=('Arial', 14, 'bold')).pack(side=tk.LEFT)
        
        ttk.Button(header_frame, text="🔄 Refresh RSI", 
                  command=self.refresh_rsi_divergences).pack(side=tk.RIGHT)
        
        # Content area with charts
        content_frame = ttk.LabelFrame(rsi_frame, text="RSI Divergence Analysis", padding=10)
        content_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Create notebook for content and charts  
        content_notebook = ttk.Notebook(content_frame)
        content_notebook.pack(fill=tk.BOTH, expand=True)
        
        # Charts tab for RSI divergences (first tab for immediate visual insight)
        rsi_charts_tab = ttk.Frame(content_notebook)
        content_notebook.add(rsi_charts_tab, text="📊 Divergence Charts")
        
        # Create RSI charts area
        self.rsi_charts_frame = rsi_charts_tab
        self.create_rsi_charts()
        
        # Status report tab (second tab for detailed information)
        status_tab = ttk.Frame(content_notebook)
        content_notebook.add(status_tab, text="📄 Status Summary")
        
        text_frame = ttk.Frame(status_tab)
        text_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.rsi_content_text = tk.Text(text_frame, height=12, wrap=tk.WORD, font=('Consolas', 10))
        self.rsi_content_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        rsi_scrollbar = ttk.Scrollbar(text_frame, orient=tk.VERTICAL, command=self.rsi_content_text.yview)
        rsi_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.rsi_content_text.configure(yscrollcommand=rsi_scrollbar.set)
    
    def create_trend_ratings_section(self):
        """Create Trend Ratings Status subsection.""" 
        trend_frame = ttk.Frame(self.notebook)
        self.notebook.add(trend_frame, text="🎯 Trend Ratings")
        
        # Header
        header_frame = ttk.Frame(trend_frame)
        header_frame.pack(fill=tk.X, pady=10, padx=10)
        
        ttk.Label(header_frame, text="🎯 Trend Ratings Analysis", 
                 font=('Arial', 14, 'bold')).pack(side=tk.LEFT)
        
        ttk.Button(header_frame, text="🔄 Refresh Trends", 
                  command=self.refresh_trend_ratings).pack(side=tk.RIGHT)
        
        # Content area with future charts support
        content_frame = ttk.LabelFrame(trend_frame, text="Trend Ratings Analysis", padding=10)
        content_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Create notebook for future charts and content
        trend_notebook = ttk.Notebook(content_frame)
        trend_notebook.pack(fill=tk.BOTH, expand=True)
        
        # Charts tab (prepared for future implementation)
        trend_charts_tab = ttk.Frame(trend_notebook)
        trend_notebook.add(trend_charts_tab, text="📊 Rating Charts")
        
        # Placeholder for future charts
        placeholder_label = ttk.Label(trend_charts_tab, 
                                     text="📊 Trend Rating Charts\n\n🚧 Coming Soon!\n\nCharts will include:\n• Rating distribution (-3 to +3)\n• Sector-wise trends\n• Market breadth analysis\n• Trend momentum indicators", 
                                     font=('Arial', 11), 
                                     justify=tk.CENTER)
        placeholder_label.pack(expand=True)
        
        # Status report tab  
        status_tab = ttk.Frame(trend_notebook)
        trend_notebook.add(status_tab, text="📄 Status Summary")
        
        text_frame = ttk.Frame(status_tab)
        text_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.trend_content_text = tk.Text(text_frame, wrap=tk.WORD, font=('Consolas', 10))
        self.trend_content_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        trend_scrollbar = ttk.Scrollbar(text_frame, orient=tk.VERTICAL, command=self.trend_content_text.yview)
        trend_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.trend_content_text.configure(yscrollcommand=trend_scrollbar.set)
    
    def create_sma_trends_section(self):
        """Create SMA Trends Status subsection."""
        sma_frame = ttk.Frame(self.notebook)
        self.notebook.add(sma_frame, text="📊 SMA Trends")
        
        # Header
        header_frame = ttk.Frame(sma_frame)
        header_frame.pack(fill=tk.X, pady=10, padx=10)
        
        ttk.Label(header_frame, text="📊 SMA Trends Analysis", 
                 font=('Arial', 14, 'bold')).pack(side=tk.LEFT)
        
        ttk.Button(header_frame, text="🔄 Refresh SMA", 
                  command=self.refresh_sma_trends).pack(side=tk.RIGHT)
        
        # Content area with future charts support
        content_frame = ttk.LabelFrame(sma_frame, text="SMA Trend Analysis", padding=10)
        content_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Create notebook for future charts and content
        sma_notebook = ttk.Notebook(content_frame)
        sma_notebook.pack(fill=tk.BOTH, expand=True)
        
        # Charts tab with SMA 50 count analysis
        sma_charts_tab = ttk.Frame(sma_notebook)
        sma_notebook.add(sma_charts_tab, text="📊 SMA 50 Counts")
        
        # Create frame for SMA 50 charts
        self.sma_chart_frame = ttk.Frame(sma_charts_tab)
        self.sma_chart_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Initialize chart placeholder
        self.sma50_canvas = None
        self.create_sma50_chart_placeholder()
        
        # Status report tab
        status_tab = ttk.Frame(sma_notebook)
        sma_notebook.add(status_tab, text="📄 Status Summary")
        
        text_frame = ttk.Frame(status_tab)
        text_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.sma_content_text = tk.Text(text_frame, wrap=tk.WORD, font=('Consolas', 10))
        self.sma_content_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        sma_scrollbar = ttk.Scrollbar(text_frame, orient=tk.VERTICAL, command=self.sma_content_text.yview)
        sma_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.sma_content_text.configure(yscrollcommand=sma_scrollbar.set)
    
    def create_status_card(self, parent, title, status, color, row, col):
        """Create a status card widget."""
        card_frame = ttk.LabelFrame(parent, text="", padding=15)
        card_frame.grid(row=row, column=col, padx=5, pady=5, sticky="nsew")
        
        title_label = ttk.Label(card_frame, text=title, font=('Arial', 12, 'bold'))
        title_label.pack()
        
        status_label = ttk.Label(card_frame, text=status, foreground=color, font=('Arial', 10))
        status_label.pack(pady=(5, 0))
        
        details_label = ttk.Label(card_frame, text="", foreground="darkblue", font=('Arial', 9))
        details_label.pack(pady=(5, 0))
        
        return {'frame': card_frame, 'title': title_label, 'status': status_label, 'details': details_label}
    
    def create_database_charts(self):
        """Create database analytics charts."""
        try:
            # Configure matplotlib for tkinter
            plt.style.use('default')
            
            # Create figure with subplots
            self.db_fig = Figure(figsize=(12, 8), dpi=80)
            
            # Create canvas
            self.db_canvas = FigureCanvasTkAgg(self.db_fig, master=self.db_charts_frame)
            self.db_canvas.draw()
            self.db_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
            
            # Initialize with placeholder
            self.update_database_charts_placeholder()
            
        except Exception as e:
            # Fallback to text display if charts fail
            error_label = ttk.Label(self.db_charts_frame, text=f"Charts unavailable: {e}")
            error_label.pack(padx=10, pady=10)
            print(f"Error creating database charts: {e}")
    
    def create_rsi_charts(self):
        """Create RSI divergences charts."""
        try:
            # Configure matplotlib
            plt.style.use('default')
            
            # Create larger figure for 6 charts (2x3 layout)
            self.rsi_fig = Figure(figsize=(15, 10), dpi=80)
            
            # Create canvas
            self.rsi_canvas = FigureCanvasTkAgg(self.rsi_fig, master=self.rsi_charts_frame)
            self.rsi_canvas.draw()
            self.rsi_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
            
            # Initialize with placeholder
            self.update_rsi_charts_placeholder()
            
        except Exception as e:
            # Fallback to text display
            error_label = ttk.Label(self.rsi_charts_frame, text=f"Charts unavailable: {e}")
            error_label.pack(padx=10, pady=10)
            print(f"Error creating RSI charts: {e}")
    
    def update_database_charts_placeholder(self):
        """Show placeholder charts while loading."""
        try:
            self.db_fig.clear()
            
            # Create 2x2 subplot layout
            ax1 = self.db_fig.add_subplot(2, 2, 1)
            ax2 = self.db_fig.add_subplot(2, 2, 2)
            ax3 = self.db_fig.add_subplot(2, 1, 2)
            
            # Placeholder data
            tables = ['BHAV', 'SMAs', 'RSI', 'Trends']
            loading_data = [0, 0, 0, 0]
            
            # Bar chart - Record counts
            bars = ax1.bar(tables, loading_data, color=['lightgray']*4)
            ax1.set_title('Table Record Counts', fontweight='bold')
            ax1.set_ylabel('Records (in thousands)')
            for bar in bars:
                bar.set_height(100)  # Placeholder height
                
            # Pie chart - Data freshness  
            ax2.pie([1], labels=['Loading...'], colors=['lightgray'], autopct='')
            ax2.set_title('Data Freshness Status', fontweight='bold')
            
            # Timeline placeholder
            ax3.text(0.5, 0.5, 'Loading database analytics...', 
                    horizontalalignment='center', verticalalignment='center',
                    transform=ax3.transAxes, fontsize=12)
            ax3.set_title('Data Timeline Analysis', fontweight='bold')
            ax3.axis('off')
            
            self.db_fig.tight_layout()
            self.db_canvas.draw()
            
        except Exception as e:
            print(f"Error updating database chart placeholder: {e}")
    
    def create_sma50_chart_placeholder(self):
        """Create placeholder for SMA 50 count charts."""
        try:
            # Create figure for SMA 50 charts
            self.sma50_fig = Figure(figsize=(12, 8), dpi=80)
            
            # Create canvas
            if self.sma50_canvas:
                self.sma50_canvas.get_tk_widget().destroy()
            
            self.sma50_canvas = FigureCanvasTkAgg(self.sma50_fig, master=self.sma_chart_frame)
            self.sma50_canvas.draw()
            self.sma50_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
            
            # Show loading placeholder
            self.update_sma50_chart_placeholder()
            
        except Exception as e:
            print(f"Error creating SMA 50 chart placeholder: {e}")
    
    def update_sma50_chart_placeholder(self):
        """Show placeholder while loading SMA 50 data."""
        try:
            self.sma50_fig.clear()
            
            # Single placeholder
            ax = self.sma50_fig.add_subplot(1, 1, 1)
            ax.text(0.5, 0.5, '📊 Loading SMA 50 Count Analysis...\n\nCharts will show:\n• Stocks above/below 50-day SMA\n• Percentage trends over time\n• Market breadth indicators', 
                   horizontalalignment='center', verticalalignment='center',
                   transform=ax.transAxes, fontsize=12)
            ax.set_title('SMA 50 Count Analysis', fontweight='bold')
            ax.axis('off')
            
            self.sma50_fig.tight_layout()
            self.sma50_canvas.draw()
            
        except Exception as e:
            print(f"Error updating SMA 50 chart placeholder: {e}")
    
    def update_sma50_charts(self):
        """Update SMA 50 count charts with real data."""
        try:
            if sma50_scanner is None:
                print("SMA 50 scanner module not available")
                return
            
            print("🔍 [SMA LOG] Loading SMA 50 count data...")
            
            # Get engine for data fetching
            engine = self.get_database_engine()
            if not engine:
                print("❌ [SMA LOG] No database engine available")
                return
            
            # Fetch SMA 50 count data for last 3 months
            from datetime import datetime, timedelta
            end_date = datetime.now().strftime('%Y-%m-%d')
            start_date = (datetime.now() - timedelta(days=90)).strftime('%Y-%m-%d')
            
            # Get SMA counts data
            sma_data = sma50_scanner.fetch_counts(engine, start=start_date, end=end_date)
            
            if sma_data.empty:
                print("❌ [SMA LOG] No SMA 50 count data found")
                return
            
            print(f"✅ [SMA LOG] Loaded {len(sma_data)} days of SMA 50 data")
            
            # Clear figure and create new plots
            self.sma50_fig.clear()
            
            # Create 2x1 subplot layout
            ax1 = self.sma50_fig.add_subplot(2, 1, 1)
            ax2 = self.sma50_fig.add_subplot(2, 1, 2)
            
            # Plot 1: Count trends
            dates = sma_data['trade_date']
            line1 = ax1.plot(dates, sma_data['above_count'], label='Above 50 SMA', color='green', linewidth=2, marker='o', markersize=4)
            line2 = ax1.plot(dates, sma_data['below_count'], label='Below 50 SMA', color='red', linewidth=2, marker='o', markersize=4)
            ax1.fill_between(dates, sma_data['above_count'], alpha=0.3, color='green')
            ax1.fill_between(dates, sma_data['below_count'], alpha=0.3, color='red')
            
            # Add interactive tooltips for count trends
            if CURSORS_AVAILABLE:
                # Create copies of data for closure
                dates_copy = dates.copy()
                above_counts = sma_data['above_count'].copy()
                below_counts = sma_data['below_count'].copy()
                
                def format_tooltip_above(sel):
                    try:
                        # Find the closest data point index by distance calculation
                        line_data = sel.artist.get_xydata()
                        import numpy as np
                        distances = np.sqrt((line_data[:, 0] - sel.target[0])**2 + (line_data[:, 1] - sel.target[1])**2)
                        closest_idx = np.argmin(distances)
                        
                        # Get the data for this index
                        date_str = dates_copy.iloc[closest_idx].strftime('%Y-%m-%d')
                        count = int(above_counts.iloc[closest_idx])
                        sel.annotation.set_text(f"Date: {date_str}\nAbove 50 SMA: {count:,} stocks")
                    except Exception as e:
                        print(f"Tooltip error (above): {e}")
                        sel.annotation.set_text(f"Data point\nHover for details")
                
                def format_tooltip_below(sel):
                    try:
                        # Find the closest data point index by distance calculation  
                        line_data = sel.artist.get_xydata()
                        import numpy as np
                        distances = np.sqrt((line_data[:, 0] - sel.target[0])**2 + (line_data[:, 1] - sel.target[1])**2)
                        closest_idx = np.argmin(distances)
                        
                        # Get the data for this index
                        date_str = dates_copy.iloc[closest_idx].strftime('%Y-%m-%d')
                        count = int(below_counts.iloc[closest_idx])
                        sel.annotation.set_text(f"Date: {date_str}\nBelow 50 SMA: {count:,} stocks")
                    except Exception as e:
                        print(f"Tooltip error (below): {e}")
                        sel.annotation.set_text(f"Data point\nHover for details")
                
                # Get the actual Line2D objects from the plot lists
                cursor1 = mplcursors.cursor(line1[0], hover=True)
                cursor1.connect("add", format_tooltip_above)
                
                cursor2 = mplcursors.cursor(line2[0], hover=True)
                cursor2.connect("add", format_tooltip_below)
            
            ax1.set_title('Stocks Above/Below 50-Day SMA (Last 3 Months)', fontweight='bold', fontsize=12)
            ax1.set_ylabel('Number of Stocks')
            ax1.legend()
            ax1.grid(True, alpha=0.3)
            
            # Format x-axis
            ax1.tick_params(axis='x', rotation=45)
            
            # Plot 2: Percentage above SMA with total count
            ax2_twin = ax2.twinx()
            
            # Percentage line with markers
            line3 = ax2.plot(dates, sma_data['pct_above'], label='% Above 50 SMA', color='blue', linewidth=2, marker='o', markersize=4)
            ax2.fill_between(dates, sma_data['pct_above'], alpha=0.2, color='blue')
            ax2.set_ylabel('Percentage Above (%)', color='blue')
            ax2.tick_params(axis='y', labelcolor='blue')
            ax2.set_ylim(0, 100)
            
            # Add interactive tooltips for percentage chart
            if CURSORS_AVAILABLE:
                # Create copies of data for closure
                pct_above_data = sma_data['pct_above'].copy()
                above_count_data = sma_data['above_count'].copy()
                below_count_data = sma_data['below_count'].copy()
                total_count_data = sma_data['total_count'].copy()
                
                def format_tooltip_percentage(sel):
                    try:
                        # Find the closest data point index by distance calculation
                        line_data = sel.artist.get_xydata()
                        import numpy as np
                        distances = np.sqrt((line_data[:, 0] - sel.target[0])**2 + (line_data[:, 1] - sel.target[1])**2)
                        closest_idx = np.argmin(distances)
                        
                        # Get the data for this index
                        date_str = dates_copy.iloc[closest_idx].strftime('%Y-%m-%d')
                        pct = float(pct_above_data.iloc[closest_idx])
                        above = int(above_count_data.iloc[closest_idx])
                        below = int(below_count_data.iloc[closest_idx])
                        total = int(total_count_data.iloc[closest_idx])
                        sel.annotation.set_text(
                            f"Date: {date_str}\n"
                            f"Above 50 SMA: {pct:.1f}%\n"
                            f"Above: {above:,} stocks\n"
                            f"Below: {below:,} stocks\n"
                            f"Total: {total:,} stocks"
                        )
                    except Exception as e:
                        print(f"Tooltip error (percentage): {e}")
                        sel.annotation.set_text(f"Data point\nHover for details")
                
                cursor3 = mplcursors.cursor(line3[0], hover=True)
                cursor3.connect("add", format_tooltip_percentage)
            
            # Total count bars
            bars = ax2_twin.bar(dates, sma_data['total_count'], alpha=0.6, color='gray', width=1, label='Total Stocks')
            ax2_twin.set_ylabel('Total Stocks Analyzed', color='gray')
            ax2_twin.tick_params(axis='y', labelcolor='gray')
            
            # Combined legend
            lines1, labels1 = ax2.get_legend_handles_labels()
            lines2, labels2 = ax2_twin.get_legend_handles_labels()
            ax2.legend(lines1 + lines2, labels1 + labels2, loc='upper left')
            
            ax2.set_title('Market Breadth: Percentage Above 50-Day SMA', fontweight='bold', fontsize=12)
            ax2.grid(True, alpha=0.3)
            ax2.tick_params(axis='x', rotation=45)
            
            # Add summary statistics
            latest_data = sma_data.iloc[-1]
            summary_text = f"Latest: {latest_data['above_count']:.0f} above ({latest_data['pct_above']:.1f}%), {latest_data['below_count']:.0f} below"
            ax2.text(0.02, 0.98, summary_text, transform=ax2.transAxes, 
                    verticalalignment='top', bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))
            
            # Add tooltip availability notice
            if CURSORS_AVAILABLE:
                ax1.text(0.02, 0.02, "💡 Hover over chart points for detailed data", 
                        transform=ax1.transAxes, fontsize=9, style='italic', alpha=0.7)
            
            self.sma50_fig.tight_layout()
            self.sma50_canvas.draw()
            
            print("✅ [SMA LOG] SMA 50 charts updated successfully")
            
        except Exception as e:
            print(f"❌ [SMA LOG] Error updating SMA 50 charts: {e}")
            import traceback
            traceback.print_exc()
    
    def update_rsi_charts_placeholder(self):
        """Show placeholder RSI charts while loading."""
        try:
            self.rsi_fig.clear()
            
            # Create 2x2 subplot layout
            ax1 = self.rsi_fig.add_subplot(2, 2, 1)
            ax2 = self.rsi_fig.add_subplot(2, 2, 2)
            ax3 = self.rsi_fig.add_subplot(2, 1, 2)
            
            # Placeholder pie chart
            ax1.pie([1], labels=['Loading...'], colors=['lightgray'], autopct='')
            ax1.set_title('Divergence Types Distribution', fontweight='bold')
            
            # Placeholder bar chart
            ax2.bar(['Bullish', 'Bearish'], [0, 0], color=['lightgreen', 'lightcoral'])
            ax2.set_title('Latest Divergence Signals', fontweight='bold')
            ax2.set_ylabel('Signal Count')
            
            # Placeholder timeline
            ax3.text(0.5, 0.5, 'Loading RSI divergence analytics...', 
                    horizontalalignment='center', verticalalignment='center',
                    transform=ax3.transAxes, fontsize=12)
            ax3.set_title('Historical Divergence Trends', fontweight='bold')
            ax3.axis('off')
            
            self.rsi_fig.tight_layout()
            self.rsi_canvas.draw()
            
        except Exception as e:
            print(f"Error updating RSI chart placeholder: {e}")
    
    def auto_refresh(self):
        """Auto-refresh dashboard every 5 minutes to prevent connection exhaustion."""
        self.refresh_dashboard()
        # Increased from 30 seconds to 5 minutes (300 seconds) to reduce connection pressure
        self.parent.after(300000, self.auto_refresh)
    
    def start_background_refresh(self):
        """Start the background refresh process."""
        import threading
        
        def background_refresh():
            """Run refresh in background thread."""
            try:
                self.refresh_dashboard_async()
            except Exception as e:
                # Safe error display that handles threading issues
                try:
                    self.parent.after(0, lambda: self.show_error(f"Background refresh failed: {e}"))
                except RuntimeError:
                    # Main loop not running, print error instead
                    print(f"Background refresh failed: {e}")
        
        # Start background thread
        thread = threading.Thread(target=background_refresh, daemon=True)
        thread.start()
        
        # Schedule auto-refresh for future updates (5 minutes instead of 30 seconds)
        self.parent.after(300000, self.auto_refresh)
    
    def show_loading_state(self):
        """Show loading indicators while data is being fetched."""
        # Update status cards with loading state
        loading_status = {
            'status': '🔄 Loading...',
            'color': 'orange',
            'details': 'Connecting...',
            'latest_date': 'Fetching...',
            'trading_days': 0,
            'total_records': 0,
            'days_behind': 999,
            'symbols_count': 0
        }
        
        if hasattr(self, 'bhav_card'):
            self.update_status_card(self.bhav_card, loading_status)
        if hasattr(self, 'sma_card'):
            self.update_status_card(self.sma_card, loading_status)
        if hasattr(self, 'rsi_card'):
            self.update_status_card(self.rsi_card, loading_status)
        if hasattr(self, 'trend_card'):
            self.update_status_card(self.trend_card, loading_status)
        
        # Update text widgets with loading message
        loading_text = "🔄 Loading dashboard data in background...\n\nPlease wait while we fetch the latest information from the database.\nThis may take a few moments on first load.\n\n⏱️ Status: Connecting to database..."
        
        if hasattr(self, 'db_details_text'):
            self.db_details_text.delete(1.0, tk.END)
            self.db_details_text.insert(1.0, loading_text)
        
        if hasattr(self, 'rsi_content_text'):
            self.rsi_content_text.delete(1.0, tk.END)
            self.rsi_content_text.insert(1.0, "🔄 Loading RSI divergences data...\n\nConnecting to database and analyzing fractal-based signals...")
        
        if hasattr(self, 'trend_content_text'):
            self.trend_content_text.delete(1.0, tk.END)
            self.trend_content_text.insert(1.0, "🔄 Loading trend ratings data...\n\nAnalyzing trend patterns and ratings...")
        
        if hasattr(self, 'sma_content_text'):
            self.sma_content_text.delete(1.0, tk.END)
            self.sma_content_text.insert(1.0, "🔄 Loading SMA trends data...\n\nProcessing moving average calculations...")
    
    def refresh_dashboard_async(self):
        """Refresh dashboard data in background and update UI with single connection."""
        try:
            print(f"🔍 [DASHBOARD LOG] Starting refresh at {datetime.now().strftime('%H:%M:%S')}")
            
            # Use a flag to check if we're in the main thread
            import threading
            is_main_thread = threading.current_thread() is threading.main_thread()
            print(f"🔍 [DASHBOARD LOG] Is main thread: {is_main_thread}")
            
            # Helper function for safe UI updates
            def safe_update_ui(update_func):
                if is_main_thread:
                    print("🔍 [DASHBOARD LOG] Updating UI directly on main thread")
                    update_func()
                else:
                    try:
                        print("🔍 [DASHBOARD LOG] Scheduling UI update via after()")
                        self.parent.after(0, update_func)
                    except RuntimeError as e:
                        print(f"⚠️ [DASHBOARD LOG] RuntimeError: {e}, updating directly")
                        # Main loop not running, update directly (for testing)
                        update_func()
            
            # Update last updated time on main thread
            safe_update_ui(lambda: self.last_updated_label.config(
                text=f"🔄 Refreshing... Started: {datetime.now().strftime('%H:%M:%S')}"
            ))
            
            print("🔍 [DASHBOARD LOG] Getting database engine...")
            engine = self.get_database_engine()
            if not engine:
                print("❌ [DASHBOARD LOG] Database engine failed!")
                safe_update_ui(lambda: self.show_error("❌ Database connection failed"))
                return
            
            print("✅ [DASHBOARD LOG] Database engine created successfully")
            
            # Use single connection for entire refresh cycle to prevent pool exhaustion
            with engine.connect() as conn:
                print("✅ [DASHBOARD LOG] Database connection established")
                # Check database status using shared connection
                safe_update_ui(lambda: self.last_updated_label.config(
                    text="🔄 Checking BHAV data..."
                ))
                print("🔍 [DASHBOARD LOG] Checking BHAV data...")
                bhav_status = self.check_bhav_data_with_connection(conn)
                print(f"✅ [DASHBOARD LOG] BHAV result: {bhav_status}")
                
                safe_update_ui(lambda: self.last_updated_label.config(
                    text="🔄 Checking SMA data..."
                ))
                print("🔍 [DASHBOARD LOG] Checking SMA data...")
                sma_status = self.check_sma_data_with_connection(conn)
                print(f"✅ [DASHBOARD LOG] SMA result: {sma_status}")
                
                safe_update_ui(lambda: self.last_updated_label.config(
                    text="🔄 Checking RSI data..."
                ))
                print("🔍 [DASHBOARD LOG] Checking RSI data...")
                rsi_status = self.check_rsi_data_with_connection(conn)
                print(f"✅ [DASHBOARD LOG] RSI result: {rsi_status}")
                
                safe_update_ui(lambda: self.last_updated_label.config(
                    text="🔄 Checking trend data..."
                ))
                print("🔍 [DASHBOARD LOG] Checking trend data...")
                trend_status = self.check_trend_data_with_connection(conn)
                print(f"✅ [DASHBOARD LOG] Trend result: {trend_status}")
            
            print("🔍 [DASHBOARD LOG] All data checks completed, updating UI...")
            
            # Update UI on main thread
            def update_ui():
                try:
                    print("🔍 [DASHBOARD LOG] Starting UI update...")
                    
                    # Update database status cards
                    print("🔍 [DASHBOARD LOG] Updating BHAV card...")
                    self.update_status_card(self.bhav_card, bhav_status)
                    
                    print("🔍 [DASHBOARD LOG] Updating SMA card...")
                    self.update_status_card(self.sma_card, sma_status) 
                    
                    print("🔍 [DASHBOARD LOG] Updating RSI card...")
                    self.update_status_card(self.rsi_card, rsi_status)
                    
                    print("🔍 [DASHBOARD LOG] Updating Trend card...")
                    self.update_status_card(self.trend_card, trend_status)
                    
                    print("🔍 [DASHBOARD LOG] Updating database details...")
                    # Update detailed database status
                    self.update_database_details(bhav_status, sma_status, rsi_status, trend_status)
                    
                    print("🔍 [DASHBOARD LOG] Updating database charts...")
                    # Update database charts with real data
                    self.update_database_charts_with_data(bhav_status, sma_status, rsi_status, trend_status)
                    
                    print("🔍 [DASHBOARD LOG] Setting completion timestamp...")
                    # Update completion time
                    self.last_updated_label.config(
                        text=f"✅ Last updated: {datetime.now().strftime('%H:%M:%S')}"
                    )
                    
                    print("✅ [DASHBOARD LOG] UI update completed successfully!")
                    
                    # Also refresh other sections asynchronously
                    print("🔍 [DASHBOARD LOG] Refreshing other sections...")
                    self.refresh_other_sections()
                    print("✅ [DASHBOARD LOG] Other sections refresh completed!")
                    
                except Exception as e:
                    print(f"❌ [DASHBOARD LOG] Error in update_ui: {e}")
                    import traceback
                    traceback.print_exc()
                    self.show_error(f"Error updating UI: {e}")
            
            print("🔍 [DASHBOARD LOG] Calling safe_update_ui for final UI update...")
            # Use safe UI update
            safe_update_ui(update_ui)
            print("✅ [DASHBOARD LOG] Dashboard refresh task completed!")
            
        except Exception as e:
            print(f"❌ [DASHBOARD LOG] Exception in refresh_dashboard_async: {e}")
            import traceback
            traceback.print_exc()
            safe_update_ui(lambda: self.show_error(f"Background refresh failed: {e}"))

    def refresh_other_sections(self):
        """Refresh RSI, trends and SMA sections in background with proper synchronization."""
        import threading
        
        # Prevent multiple concurrent refreshes
        if hasattr(self, '_refresh_in_progress') and self._refresh_in_progress:
            return
            
        self._refresh_in_progress = True
        
        def refresh_section_safely(section_name, refresh_method):
            """Refresh a section with proper error handling and synchronization."""
            try:
                self.parent.after(0, lambda: self.last_updated_label.config(
                    text=f"🔄 Loading {section_name}..."
                ))
                refresh_method()
            except Exception as e:
                print(f"Error refreshing {section_name}: {e}")
                self.parent.after(0, lambda: self.last_updated_label.config(
                    text=f"❌ Error loading {section_name}"
                ))
        
        def refresh_all_sections():
            """Refresh all sections sequentially to avoid connection conflicts."""
            try:
                # Refresh sections one at a time to avoid connection pool exhaustion
                refresh_section_safely("RSI divergences", self.refresh_rsi_divergences)
                refresh_section_safely("trend ratings", self.refresh_trend_ratings) 
                refresh_section_safely("SMA trends", self.refresh_sma_trends)
                
                # Update last updated time
                self.parent.after(0, lambda: self.last_updated_label.config(
                    text=f"✅ Updated at {datetime.now().strftime('%H:%M:%S')}"
                ))
            finally:
                self._refresh_in_progress = False
        
        # Run all refreshes in a single background thread
        threading.Thread(target=refresh_all_sections, daemon=True).start()

    def refresh_dashboard(self):
        """Fallback refresh method for auto-refresh - uses async approach."""
        self.start_background_refresh()
    
    def refresh_rsi_divergences(self):
        """Refresh RSI divergences section with real analysis."""
        try:
            self.rsi_content_text.delete(1.0, tk.END)
            self.rsi_content_text.insert(tk.END, "🔄 Analyzing RSI Divergences...\n\n")
            
            engine = self.get_database_engine()
            if not engine:
                self.rsi_content_text.insert(tk.END, "❌ Database connection failed")
                return
            
            # Get RSI divergence analysis
            analysis = self.analyze_rsi_divergences(engine)
            
            content = f"""📈 RSI DIVERGENCE STATUS
{'=' * 40}

📊 LATEST SIGNALS ({analysis['latest_date']})
{'=' * 45}
� Hidden Bullish: {analysis['hidden_bullish_count']:,} stocks
� Hidden Bearish: {analysis['hidden_bearish_count']:,} stocks

📈 ALL-TIME HISTORY
{'=' * 25}  
🟢 Total Bullish: {analysis['total_bullish']:,}
🔴 Total Bearish: {analysis['total_bearish']:,}
📊 Grand Total: {analysis['total_signals']:,} signals

🧮 RSI CALCULATION STATUS
{'=' * 30}"""

            # Add RSI timeframe status
            for tf_name, tf_data in analysis['timeframe_status'].items():
                status_icon = "✅" if tf_data['current'] else "❌"
                content += f"""
{status_icon} {tf_name}:
   └─ Period: {tf_data['period']} days
   └─ Latest Date: {tf_data['latest_date']}
   └─ Symbols: {tf_data['symbols']:,}
   └─ Records: {tf_data['records']:,}
   └─ Status: {'Up to Date' if tf_data['current'] else 'Outdated'}"""

            content += f"""

🔍 DIVERGENCE DETECTION DETAILS
{'=' * 31}
Analysis Window: {analysis['lookback_days']} days
Minimum RSI Change: {analysis['min_rsi_change']}%
Minimum Price Change: {analysis['min_price_change']}%
Symbols Analyzed: {analysis['symbols_analyzed']:,}

� HIDDEN BULLISH DIVERGENCE CRITERIA:
• Recent price low > Previous price low (Higher Low)
• Recent RSI low < Previous RSI low (Lower Low)  
• RSI difference > {analysis['min_rsi_change']}%

📉 HIDDEN BEARISH DIVERGENCE CRITERIA:
• Recent price high < Previous price high (Lower High)
• Recent RSI high > Previous RSI high (Higher High)
• RSI difference > {analysis['min_rsi_change']}%

⚠️  ANALYSIS NOTES:
• Only Daily timeframe RSI (Period 9) currently available
• Weekly/Monthly RSI periods need to be calculated
• Divergences detected using {analysis['lookback_days']}-day lookback window
• Results are for latest trading date only

🎯 DATA QUALITY:
Price Data: {analysis['price_data_quality']}
RSI Data: {analysis['rsi_data_quality']}
Analysis Coverage: {analysis['coverage_percentage']:.1f}% of listed stocks"""

            self.rsi_content_text.insert(tk.END, content)
            
            # Update RSI charts with the analysis data
            self.update_rsi_charts_with_data(analysis)
            
        except Exception as e:
            error_msg = f"❌ Error analyzing RSI divergences: {str(e)}\n\n"
            error_msg += "This could be due to:\n"
            error_msg += "• Database connectivity issues\n" 
            error_msg += "• Missing RSI or price data\n"
            error_msg += "• Insufficient historical data for analysis\n"
            self.rsi_content_text.insert(tk.END, error_msg)
    
    def refresh_trend_ratings(self):
        """Refresh trend ratings section - placeholder for now."""
        try:
            self.trend_content_text.delete(1.0, tk.END)
            content = """🔄 Refreshing Trend Ratings data...

🎯 TREND RATINGS ANALYSIS
=======================

This section will contain:
• Trend rating distribution (-3 to +3 scale)
• Daily, weekly, monthly trend breakdowns
• Strong uptrend/downtrend symbol counts
• Trend momentum and strength analysis
• Trend direction changes and alerts

🚧 DEVELOPMENT STATUS
===================
▪ Trend calculation engine: Already implemented
▪ Rating distribution analysis: Coming soon
▪ Visual charts and graphs: Coming soon
▪ Trend change notifications: Coming soon

📊 RATING SCALE
==============
+3: Very Strong Uptrend
+2: Strong Uptrend  
+1: Weak Uptrend
 0: Sideways/Neutral
-1: Weak Downtrend
-2: Strong Downtrend
-3: Very Strong Downtrend

🔍 PLANNED FEATURES
=================
1. Real-time trend rating distribution
2. Sector-wise trend analysis
3. Market breadth based on trend ratings
4. Historical trend persistence analysis
5. Automated trend alerts and notifications

🔍 Current Status: Trend analysis table active, visualization next..."""

            self.trend_content_text.insert(tk.END, content)
        except Exception as e:
            self.trend_content_text.insert(tk.END, f"❌ Error refreshing trend data: {e}")
    
    def refresh_sma_trends(self):
        """Refresh SMA trends section with charts and analysis."""
        try:
            print("🔍 [SMA REFRESH] Starting SMA trends refresh...")
            
            # Update SMA 50 charts first
            self.update_sma50_charts()
            
            # Update text content
            self.sma_content_text.delete(1.0, tk.END)
            
            # Get basic SMA statistics
            engine = self.get_database_engine()
            sma_stats = self.get_sma_statistics(engine) if engine else None
            
            content = f"""📊 SMA TRENDS ANALYSIS - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
{'=' * 60}

📈 SMA 50 COUNT ANALYSIS
======================"""
            
            if sma_stats:
                content += f"""
Latest Data: {sma_stats.get('latest_date', 'N/A')}
Stocks Above 50 SMA: {sma_stats.get('above_50', 'N/A')} ({sma_stats.get('pct_above_50', 'N/A'):.1f}%)
Stocks Below 50 SMA: {sma_stats.get('below_50', 'N/A')}
Total Stocks Analyzed: {sma_stats.get('total_stocks', 'N/A')}

� MARKET BREADTH INDICATORS
==========================
Bullish Threshold: >60% above 50 SMA
Neutral Zone: 40-60% above 50 SMA  
Bearish Threshold: <40% above 50 SMA

Current Market State: {sma_stats.get('market_state', 'Unknown')}"""
            else:
                content += """
❌ Unable to load SMA statistics
Please check database connectivity and sma50_counts table."""
            
            content += """

📈 SMA INDICATORS AVAILABLE
=========================
• 5, 10, 20, 50, 100, 200 day moving averages (moving_averages table)
• Daily counts of stocks above/below 50 SMA (sma50_counts table)
• Historical trend analysis and market breadth indicators
• Percentage-based market strength measurements

🔍 CROSSOVER SIGNALS (Coming Soon)
================================
Golden Cross: 50 SMA crosses above 200 SMA (Bullish)
Death Cross: 50 SMA crosses below 200 SMA (Bearish)
Short-term: 5 SMA vs 20 SMA crossovers
Medium-term: 20 SMA vs 50 SMA crossovers

📊 CURRENT FEATURES
==================
✅ Daily SMA 50 count tracking
✅ Market breadth percentage analysis  
✅ Historical trend visualization
✅ Real-time data updates

🚧 PLANNED FEATURES
==================
🔄 SMA 200 count analysis (similar to SMA 50)
🔄 Multi-timeframe crossover detection
🔄 SMA trend strength scoring
🔄 Automated signal generation
🔄 Volume-weighted moving averages

📅 Data Coverage: Real-time daily updates with historical analysis"""

            self.sma_content_text.insert(tk.END, content)
            print("✅ [SMA REFRESH] SMA trends refresh completed")
            
        except Exception as e:
            error_msg = f"❌ Error refreshing SMA data: {e}"
            print(f"❌ [SMA REFRESH] {error_msg}")
            self.sma_content_text.delete(1.0, tk.END)
            self.sma_content_text.insert(tk.END, error_msg)
    
    def get_sma_statistics(self, engine):
        """Get current SMA statistics for display."""
        try:
            if not engine or sma50_scanner is None:
                return None
                
            # Get latest SMA 50 data
            from datetime import datetime
            end_date = datetime.now().strftime('%Y-%m-%d')
            
            sma_data = sma50_scanner.fetch_counts(engine, end=end_date)
            if sma_data.empty:
                return None
                
            latest = sma_data.iloc[-1]
            pct_above = latest['pct_above']
            
            # Determine market state based on percentage
            if pct_above > 60:
                market_state = "💚 Bullish (>60% above 50 SMA)"
            elif pct_above > 40:
                market_state = "🟡 Neutral (40-60% above 50 SMA)"
            else:
                market_state = "🔴 Bearish (<40% above 50 SMA)"
            
            return {
                'latest_date': latest['trade_date'].strftime('%Y-%m-%d'),
                'above_50': int(latest['above_count']),
                'below_50': int(latest['below_count']),
                'pct_above_50': pct_above,
                'total_stocks': int(latest['total_count']),
                'market_state': market_state
            }
            
        except Exception as e:
            print(f"Error getting SMA statistics: {e}")
            return None
    
    def get_database_engine(self):
        """Get shared database engine with optimized connection pooling."""
        import threading
        
        if self._engine_lock is None:
            self._engine_lock = threading.Lock()
            
        with self._engine_lock:
            if self._engine is None:
                try:
                    # Try using the reporting module's optimized engine
                    import reporting_adv_decl as rad
                    self._engine = rad.engine()
                except Exception:
                    try:
                        # Fallback to market breadth service
                        from services.market_breadth_service import get_engine
                        self._engine = get_engine()
                    except Exception:
                        try:
                            # Last resort: create optimized engine directly
                            from sqlalchemy import create_engine
                            import os
                            
                            # Database connection details
                            host = os.getenv('MYSQL_HOST', 'localhost')
                            port = os.getenv('MYSQL_PORT', '3306') 
                            database = os.getenv('MYSQL_DB', 'stock_analysis')
                            username = os.getenv('MYSQL_USER', 'root')
                            password = os.getenv('MYSQL_PASSWORD', '')
                            
                            # Create optimized engine with increased connection pool for dashboard
                            connection_string = f"mysql+pymysql://{username}:{password}@{host}:{port}/{database}?charset=utf8mb4"
                            self._engine = create_engine(
                                connection_string,
                                pool_size=8,           # Increased from 5 to handle dashboard queries
                                max_overflow=15,       # Increased from 10 to handle refresh cycles
                                pool_timeout=60,       # Increased from 30 to reduce timeouts
                                pool_recycle=3600,     # Recycle connections hourly
                                pool_pre_ping=True,    # Test connections before use
                                echo=False
                            )
                        except Exception as e:
                            print(f"Failed to create database engine: {e}")
                            return None
            
            return self._engine
    
    def check_bhav_data(self, engine) -> Dict[str, Any]:
        """Check BHAV data availability."""
        try:
            from sqlalchemy import text
            with engine.connect() as conn:
                query = text("""
                    SELECT MIN(trade_date) as earliest_date, MAX(trade_date) as latest_date,
                           COUNT(DISTINCT trade_date) as trading_days, COUNT(*) as total_records
                    FROM nse_equity_bhavcopy_full WHERE trade_date IS NOT NULL
                """)
                result = conn.execute(query).fetchone()
                
                if result and result.latest_date:
                    days_behind = (date.today() - result.latest_date).days
                    status = "✅ Up to Date" if days_behind <= 3 else "⚠️ Behind" if days_behind <= 7 else "❌ Outdated"
                    color = "green" if days_behind <= 3 else "orange" if days_behind <= 7 else "red"
                    
                    return {
                        'status': status, 'color': color,
                        'details': f"{result.trading_days:,} trading days\\n{result.total_records:,} records",
                        'earliest_date': result.earliest_date, 'latest_date': result.latest_date,
                        'trading_days': result.trading_days, 'total_records': result.total_records,
                        'days_behind': days_behind
                    }
                else:
                    return {'status': "❌ No Data", 'color': "red", 'details': "No BHAV data found", 'error': "No data"}
        except Exception as e:
            return {'status': "❌ Error", 'color': "red", 'details': "Check failed", 'error': str(e)}
    
    def check_sma_data(self, engine) -> Dict[str, Any]:
        """Check SMA data availability."""
        try:
            from sqlalchemy import text
            with engine.connect() as conn:
                # Check table exists
                check = conn.execute(text("SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = DATABASE() AND table_name = 'moving_averages'")).fetchone()
                if not check or check[0] == 0:
                    return {'status': "❌ No Table", 'color': "red", 'details': "SMAs table missing", 'error': "Table not found"}
                
                # Get statistics
                query = text("SELECT MAX(trade_date) as latest_date, COUNT(DISTINCT trade_date) as trading_days, COUNT(DISTINCT symbol) as symbols_count, COUNT(*) as total_records FROM moving_averages WHERE trade_date IS NOT NULL")
                result = conn.execute(query).fetchone()
                
                if result and result.latest_date:
                    days_behind = (date.today() - result.latest_date).days
                    status = "✅ Up to Date" if days_behind <= 3 else "⚠️ Behind" if days_behind <= 7 else "❌ Outdated"
                    color = "green" if days_behind <= 3 else "orange" if days_behind <= 7 else "red"
                    
                    return {
                        'status': status, 'color': color,
                        'details': f"{result.symbols_count:,} symbols\\n{result.trading_days:,} trading days",
                        'latest_date': result.latest_date, 'trading_days': result.trading_days,
                        'symbols_count': result.symbols_count, 'total_records': result.total_records,
                        'days_behind': days_behind
                    }
                else:
                    return {'status': "❌ No Data", 'color': "red", 'details': "No SMAs calculated", 'error': "No data"}
        except Exception as e:
            return {'status': "❌ Error", 'color': "red", 'details': "Check failed", 'error': str(e)}
    
    def check_rsi_data(self, engine) -> Dict[str, Any]:
        """Check RSI data availability."""
        try:
            from sqlalchemy import text
            with engine.connect() as conn:
                # Check table exists
                check = conn.execute(text("SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = DATABASE() AND table_name = 'nse_rsi_daily'")).fetchone()
                if not check or check[0] == 0:
                    return {'status': "❌ No Table", 'color': "red", 'details': "RSI table missing", 'error': "Table not found"}
                
                # Get statistics
                query = text("SELECT MAX(trade_date) as latest_date, COUNT(DISTINCT trade_date) as trading_days, COUNT(DISTINCT symbol) as symbols_count, COUNT(*) as total_records FROM nse_rsi_daily WHERE trade_date IS NOT NULL")
                result = conn.execute(query).fetchone()
                
                if result and result.latest_date:
                    days_behind = (date.today() - result.latest_date).days
                    status = "✅ Up to Date" if days_behind <= 3 else "⚠️ Behind" if days_behind <= 7 else "❌ Outdated"
                    color = "green" if days_behind <= 3 else "orange" if days_behind <= 7 else "red"
                    
                    return {
                        'status': status, 'color': color,
                        'details': f"{result.symbols_count:,} symbols\\n{result.trading_days:,} trading days",
                        'latest_date': result.latest_date, 'trading_days': result.trading_days,
                        'symbols_count': result.symbols_count, 'total_records': result.total_records,
                        'days_behind': days_behind
                    }
                else:
                    return {'status': "❌ No Data", 'color': "red", 'details': "No RSI data", 'error': "No data"}
        except Exception as e:
            return {'status': "❌ Error", 'color': "red", 'details': "Check failed", 'error': str(e)}
    
    def check_trend_data(self, engine) -> Dict[str, Any]:
        """Check trend analysis data availability."""
        try:
            from sqlalchemy import text
            with engine.connect() as conn:
                # Check table exists  
                check = conn.execute(text("SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = DATABASE() AND table_name = 'trend_analysis'")).fetchone()
                if not check or check[0] == 0:
                    return {'status': "❌ No Table", 'color': "red", 'details': "Trends table missing", 'error': "Table not found"}
                
                # Get statistics
                query = text("SELECT MAX(trade_date) as latest_date, COUNT(DISTINCT trade_date) as trading_days, COUNT(DISTINCT symbol) as symbols_count, COUNT(*) as total_records FROM trend_analysis WHERE trade_date IS NOT NULL")
                result = conn.execute(query).fetchone()
                
                if result and result.latest_date:
                    days_behind = (date.today() - result.latest_date).days
                    status = "✅ Up to Date" if days_behind <= 3 else "⚠️ Behind" if days_behind <= 7 else "❌ Outdated"
                    color = "green" if days_behind <= 3 else "orange" if days_behind <= 7 else "red"
                    
                    return {
                        'status': status, 'color': color,
                        'details': f"{result.symbols_count:,} symbols\\n{result.trading_days:,} trading days",
                        'latest_date': result.latest_date, 'trading_days': result.trading_days,
                        'symbols_count': result.symbols_count, 'total_records': result.total_records,
                        'days_behind': days_behind
                    }
                else:
                    return {'status': "❌ No Data", 'color': "red", 'details': "No trend data", 'error': "No data"}
        except Exception as e:
            return {'status': "❌ Error", 'color': "red", 'details': "Check failed", 'error': str(e)}
    
    def update_status_card(self, card, status_info):
        """Update status card with new information."""
        try:
            print(f"🔍 [DASHBOARD LOG] Updating status card with info: {status_info}")
            print(f"🔍 [DASHBOARD LOG] Card object: {card}")
            
            if 'status' not in card:
                print(f"❌ [DASHBOARD LOG] Card missing 'status' widget: {list(card.keys())}")
                return
                
            if 'details' not in card:
                print(f"❌ [DASHBOARD LOG] Card missing 'details' widget: {list(card.keys())}")
                return
            
            print(f"🔍 [DASHBOARD LOG] Setting status: {status_info['status']} with color: {status_info['color']}")
            card['status'].config(text=status_info['status'], foreground=status_info['color'])
            
            print(f"🔍 [DASHBOARD LOG] Setting details: {status_info['details']}")
            card['details'].config(text=status_info['details'])
            
            print("✅ [DASHBOARD LOG] Status card updated successfully!")
            
        except Exception as e:
            print(f"❌ [DASHBOARD LOG] Error updating status card: {e}")
            import traceback
            traceback.print_exc()
    
    def update_database_details(self, bhav_status, sma_status, rsi_status, trend_status):
        """Update database details section."""
        self.db_details_text.delete(1.0, tk.END)
        
        content = f"""📊 DATABASE STATUS REPORT
{'=' * 50}
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

📈 BHAV DATA STATUS:
   Status: {bhav_status['status']}"""
        
        if 'error' not in bhav_status:
            content += f"""
   Date Range: {bhav_status['earliest_date']} to {bhav_status['latest_date']}
   Trading Days: {bhav_status['trading_days']:,}
   Total Records: {bhav_status['total_records']:,}
   Days Behind: {bhav_status['days_behind']}"""
        else:
            content += f"\\n   Error: {bhav_status['error']}"
            
        content += f"""

📊 SMAs STATUS:
   Status: {sma_status['status']}"""
        
        if 'error' not in sma_status:
            content += f"""
   Latest Date: {sma_status['latest_date']}
   Trading Days: {sma_status['trading_days']:,}
   Symbols: {sma_status['symbols_count']:,}
   Total Records: {sma_status['total_records']:,}
   Days Behind: {sma_status['days_behind']}"""
        else:
            content += f"\\n   Error: {sma_status['error']}"
            
        content += f"""

📉 RSI STATUS:
   Status: {rsi_status['status']}"""
        
        if 'error' not in rsi_status:
            content += f"""
   Latest Date: {rsi_status['latest_date']}
   Trading Days: {rsi_status['trading_days']:,}
   Symbols: {rsi_status['symbols_count']:,}
   Total Records: {rsi_status['total_records']:,}
   Days Behind: {rsi_status['days_behind']}"""
        else:
            content += f"\\n   Error: {rsi_status['error']}"
            
        content += f"""

🎯 TREND ANALYSIS STATUS:
   Status: {trend_status['status']}"""
        
        if 'error' not in trend_status:
            content += f"""
   Latest Date: {trend_status['latest_date']}
   Trading Days: {trend_status['trading_days']:,}
   Symbols: {trend_status['symbols_count']:,}
   Total Records: {trend_status['total_records']:,}
   Days Behind: {trend_status['days_behind']}"""
        else:
            content += f"\\n   Error: {trend_status['error']}"
            
        # Summary
        content += f"""

📋 DATA QUALITY SUMMARY:
{'=' * 30}"""

        all_good = True
        for name, status in [("BHAV", bhav_status), ("SMAs", sma_status), ("RSI", rsi_status), ("Trends", trend_status)]:
            if 'error' in status:
                content += f"\\n❌ {name}: ERROR - {status.get('error', 'Unknown error')}"
                all_good = False
            elif status.get('days_behind', 999) > 7:
                content += f"\\n⚠️  {name}: OUTDATED - {status['days_behind']} days behind"
                all_good = False
            else:
                content += f"\\n✅ {name}: OK - Current data available"
        
        if all_good:
            content += "\\n\\n🎉 All systems operational!"
        else:
            content += "\\n\\n⚠️  Some systems need attention."
            
        self.db_details_text.insert(tk.END, content)
    
    def show_error(self, message):
        """Show error message."""
        for card in [self.bhav_card, self.sma_card, self.rsi_card, self.trend_card]:
            card['status'].config(text="❌ Error", foreground="red")
            card['details'].config(text="Check failed")
        
        self.db_details_text.delete(1.0, tk.END)
        self.db_details_text.insert(tk.END, f"{message}\\n\\nPlease check database connection and try again.")

    def analyze_rsi_divergences(self, engine):
        """Get comprehensive RSI divergences data including temporal distributions."""
        try:
            from sqlalchemy import text
            
            with engine.connect() as conn:
                # Get latest divergences summary
                latest_query = text("""
                    SELECT 
                        MAX(signal_date) as latest_date,
                        MIN(signal_date) as earliest_date,
                        COUNT(*) as total_signals,
                        SUM(CASE WHEN signal_type LIKE '%Bullish%' THEN 1 ELSE 0 END) as total_bullish,
                        SUM(CASE WHEN signal_type LIKE '%Bearish%' THEN 1 ELSE 0 END) as total_bearish
                    FROM nse_rsi_divergences
                """)
                result = conn.execute(latest_query).fetchone()
                
                latest_date = result[0] if result[0] else 'N/A'
                earliest_date = result[1] if result[1] else 'N/A'
                total_signals = result[2] if result[2] else 0
                total_bullish = result[3] if result[3] else 0
                total_bearish = result[4] if result[4] else 0
                
                # Get latest date specific counts
                latest_bullish = 0
                latest_bearish = 0
                if latest_date != 'N/A':
                    latest_counts = text("""
                        SELECT 
                            signal_type,
                            COUNT(*) as count 
                        FROM nse_rsi_divergences 
                        WHERE signal_date = :latest_date
                        GROUP BY signal_type
                    """)
                    latest_results = conn.execute(latest_counts, {"latest_date": latest_date}).fetchall()
                    
                    for signal_type, count in latest_results:
                        if 'Bullish' in signal_type:
                            latest_bullish += count
                        elif 'Bearish' in signal_type:
                            latest_bearish += count
                
                # Get yearly distribution
                yearly_query = text("""
                    SELECT 
                        YEAR(signal_date) as year,
                        CASE 
                            WHEN signal_type LIKE '%Bullish%' THEN 'Bullish'
                            WHEN signal_type LIKE '%Bearish%' THEN 'Bearish'
                            ELSE 'Other'
                        END as signal_category,
                        COUNT(*) as signal_count
                    FROM nse_rsi_divergences
                    GROUP BY YEAR(signal_date), signal_category
                    ORDER BY year DESC, signal_category
                """)
                yearly_results = conn.execute(yearly_query).fetchall()
                
                yearly_distribution = {}
                for year, category, count in yearly_results:
                    if year not in yearly_distribution:
                        yearly_distribution[year] = {'Bullish': 0, 'Bearish': 0}
                    yearly_distribution[year][category] = count
                
                # Get monthly distribution (last 18 months)
                monthly_query = text("""
                    SELECT 
                        DATE_FORMAT(signal_date, '%Y-%m') as month,
                        CASE 
                            WHEN signal_type LIKE '%Bullish%' THEN 'Bullish'
                            WHEN signal_type LIKE '%Bearish%' THEN 'Bearish'
                            ELSE 'Other'
                        END as signal_category,
                        COUNT(*) as signal_count
                    FROM nse_rsi_divergences
                    WHERE signal_date >= DATE_SUB(CURDATE(), INTERVAL 18 MONTH)
                    GROUP BY DATE_FORMAT(signal_date, '%Y-%m'), signal_category
                    ORDER BY month DESC, signal_category
                """)
                monthly_results = conn.execute(monthly_query).fetchall()
                
                monthly_distribution = {}
                for month, category, count in monthly_results:
                    if month not in monthly_distribution:
                        monthly_distribution[month] = {'Bullish': 0, 'Bearish': 0}
                    monthly_distribution[month][category] = count
                
                # Get weekly distribution (last 12 weeks)
                weekly_query = text("""
                    SELECT 
                        CONCAT(YEAR(signal_date), '-W', LPAD(WEEK(signal_date), 2, '0')) as week,
                        CASE 
                            WHEN signal_type LIKE '%Bullish%' THEN 'Bullish'
                            WHEN signal_type LIKE '%Bearish%' THEN 'Bearish'
                            ELSE 'Other'
                        END as signal_category,
                        COUNT(*) as signal_count
                    FROM nse_rsi_divergences
                    WHERE signal_date >= DATE_SUB(CURDATE(), INTERVAL 12 WEEK)
                    GROUP BY CONCAT(YEAR(signal_date), '-W', LPAD(WEEK(signal_date), 2, '0')), signal_category
                    ORDER BY week DESC, signal_category
                """)
                weekly_results = conn.execute(weekly_query).fetchall()
                
                weekly_distribution = {}
                for week, category, count in weekly_results:
                    if week not in weekly_distribution:
                        weekly_distribution[week] = {'Bullish': 0, 'Bearish': 0}
                    weekly_distribution[week][category] = count
                
                # Get RSI status
                try:
                    rsi_daily = conn.execute(text("""
                        SELECT MAX(trade_date) as latest_date, COUNT(DISTINCT symbol) as symbols, COUNT(*) as records
                        FROM nse_rsi_daily
                    """)).fetchone()
                    
                    rsi_weekly = conn.execute(text("""
                        SELECT MAX(trade_date) as latest_date, COUNT(DISTINCT symbol) as symbols, COUNT(*) as records
                        FROM nse_rsi_weekly
                    """)).fetchone()
                    
                    rsi_monthly = conn.execute(text("""
                        SELECT MAX(trade_date) as latest_date, COUNT(DISTINCT symbol) as symbols, COUNT(*) as records
                        FROM nse_rsi_monthly
                    """)).fetchone()
                    
                    # Get BHAV latest
                    bhav_latest = conn.execute(text("""
                        SELECT MAX(trade_date) FROM nse_equity_bhavcopy_full
                    """)).fetchone()[0]
                    
                    # Calculate status
                    rsi_current = rsi_daily[0] == bhav_latest if rsi_daily[0] and bhav_latest else False
                    
                    timeframe_status = {
                        "Daily RSI": {
                            "period": 9,
                            "latest_date": rsi_daily[0] if rsi_daily[0] else 'N/A',
                            "symbols": rsi_daily[1] if rsi_daily[1] else 0,
                            "records": rsi_daily[2] if rsi_daily[2] else 0,
                            "current": rsi_current
                        },
                        "Weekly RSI": {
                            "period": 9,
                            "latest_date": rsi_weekly[0] if rsi_weekly[0] else 'N/A',
                            "symbols": rsi_weekly[1] if rsi_weekly[1] else 0,
                            "records": rsi_weekly[2] if rsi_weekly[2] else 0,
                            "current": True
                        },
                        "Monthly RSI": {
                            "period": 9,
                            "latest_date": rsi_monthly[0] if rsi_monthly[0] else 'N/A',
                            "symbols": rsi_monthly[1] if rsi_monthly[1] else 0,
                            "records": rsi_monthly[2] if rsi_monthly[2] else 0,
                            "current": True
                        }
                    }
                    
                    # Calculate coverage
                    total_stocks_query = text("""
                        SELECT COUNT(DISTINCT symbol) FROM nse_equity_bhavcopy_full 
                        WHERE trade_date = :date
                    """)
                    total_stocks = conn.execute(total_stocks_query, {"date": bhav_latest}).fetchone()[0] if bhav_latest else 0
                    
                    coverage_percentage = (rsi_daily[1] / total_stocks * 100) if total_stocks > 0 else 0
                    
                except Exception:
                    timeframe_status = {
                        "Daily RSI": {"period": 9, "latest_date": "N/A", "symbols": 0, "records": 0, "current": False},
                        "Weekly RSI": {"period": 9, "latest_date": "N/A", "symbols": 0, "records": 0, "current": False},
                        "Monthly RSI": {"period": 9, "latest_date": "N/A", "symbols": 0, "records": 0, "current": False}
                    }
                    coverage_percentage = 0
                    
                return {
                    "latest_date": latest_date,
                    "hidden_bullish_count": latest_bullish,
                    "hidden_bearish_count": latest_bearish,
                    "timeframe_status": timeframe_status,
                    "lookback_days": 50,
                    "min_rsi_change": 5.0,
                    "min_price_change": 2.0,
                    "symbols_analyzed": timeframe_status["Daily RSI"]["symbols"],
                    "price_data_quality": f"BHAV data available",
                    "rsi_data_quality": f"RSI data current",
                    "coverage_percentage": coverage_percentage,
                    "total_signals": total_signals,
                    "total_bullish": total_bullish,
                    "total_bearish": total_bearish,
                    # New temporal distribution data
                    "yearly_distribution": yearly_distribution,
                    "monthly_distribution": monthly_distribution,
                    "weekly_distribution": weekly_distribution
                }
                
        except Exception as e:
            # Return error data structure with temporal distributions
            print(f"Error analyzing RSI divergences: {e}")
            return {
                "latest_date": "Error",
                "hidden_bullish_count": 0,
                "hidden_bearish_count": 0,
                "timeframe_status": {
                    "Daily RSI": {"period": 9, "latest_date": "N/A", "symbols": 0, "records": 0, "current": False},
                    "Weekly RSI": {"period": 9, "latest_date": "N/A", "symbols": 0, "records": 0, "current": False},
                    "Monthly RSI": {"period": 9, "latest_date": "N/A", "symbols": 0, "records": 0, "current": False}
                },
                "lookback_days": 50,
                "min_rsi_change": 5.0,
                "min_price_change": 2.0,
                "symbols_analyzed": 0,
                "price_data_quality": f"Error: {str(e)}",
                "rsi_data_quality": f"Error: {str(e)}",
                "coverage_percentage": 0.0,
                "total_signals": 0,
                "total_bullish": 0,
                "total_bearish": 0,
                "yearly_distribution": {},
                "monthly_distribution": {},
                "weekly_distribution": {}
            }

    def update_database_charts_with_data(self, bhav_status, sma_status, rsi_status, trend_status):
        """Update database charts with real data."""
        try:
            if not hasattr(self, 'db_fig'):
                return
                
            self.db_fig.clear()
            
            # Create 2x2 subplot layout
            ax1 = self.db_fig.add_subplot(2, 2, 1)
            ax2 = self.db_fig.add_subplot(2, 2, 2)
            ax3 = self.db_fig.add_subplot(2, 1, 2)
            
            # Bar chart - Record counts (in thousands)
            tables = ['BHAV', 'SMAs', 'RSI', 'Trends']
            record_counts = [
                bhav_status.get('total_records', 0) / 1000,
                sma_status.get('total_records', 0) / 1000,
                rsi_status.get('total_records', 0) / 1000,
                trend_status.get('total_records', 0) / 1000
            ]
            
            colors = []
            for status in [bhav_status, sma_status, rsi_status, trend_status]:
                if 'error' in status:
                    colors.append('#ff6b6b')  # Red for error
                elif status.get('days_behind', 0) > 7:
                    colors.append('#ffa726')  # Orange for outdated
                else:
                    colors.append('#4caf50')  # Green for current
            
            bars = ax1.bar(tables, record_counts, color=colors)
            ax1.set_title('Table Record Counts (thousands)', fontweight='bold')
            ax1.set_ylabel('Records (K)')
            
            # Add value labels on bars
            for bar, count in zip(bars, record_counts):
                height = bar.get_height()
                ax1.annotate(f'{count:.0f}K',
                           xy=(bar.get_x() + bar.get_width() / 2, height),
                           xytext=(0, 3),  # 3 points vertical offset
                           textcoords="offset points",
                           ha='center', va='bottom', fontsize=9)
            
            # Pie chart - Data freshness status
            current_count = sum(1 for status in [bhav_status, sma_status, rsi_status, trend_status] 
                              if 'error' not in status and status.get('days_behind', 0) <= 1)
            outdated_count = sum(1 for status in [bhav_status, sma_status, rsi_status, trend_status] 
                               if 'error' not in status and status.get('days_behind', 0) > 1)
            error_count = sum(1 for status in [bhav_status, sma_status, rsi_status, trend_status] 
                            if 'error' in status)
            
            freshness_data = []
            freshness_labels = []
            freshness_colors = []
            
            if current_count > 0:
                freshness_data.append(current_count)
                freshness_labels.append(f'Current ({current_count})')
                freshness_colors.append('#4caf50')
            
            if outdated_count > 0:
                freshness_data.append(outdated_count)
                freshness_labels.append(f'Outdated ({outdated_count})')
                freshness_colors.append('#ffa726')
                
            if error_count > 0:
                freshness_data.append(error_count)
                freshness_labels.append(f'Error ({error_count})')
                freshness_colors.append('#ff6b6b')
                
            if freshness_data:
                ax2.pie(freshness_data, labels=freshness_labels, colors=freshness_colors, 
                       autopct='%1.0f%%', startangle=90)
            else:
                ax2.pie([1], labels=['No Data'], colors=['lightgray'], autopct='')
            ax2.set_title('Data Freshness Status', fontweight='bold')
            
            # Timeline - Data coverage over time (simplified)
            try:
                # Use latest dates for timeline
                dates_data = []
                table_names = []
                
                for name, status in [('BHAV', bhav_status), ('SMA', sma_status), 
                                   ('RSI', rsi_status), ('Trends', trend_status)]:
                    if 'error' not in status and status.get('latest_date'):
                        dates_data.append(status['latest_date'])
                        table_names.append(name)
                
                if dates_data:
                    # Convert to pandas datetime for easier plotting
                    import pandas as pd
                    df_dates = pd.DataFrame({
                        'table': table_names,
                        'latest_date': pd.to_datetime(dates_data)
                    })
                    
                    # Simple bar chart showing how recent each table is
                    today = pd.Timestamp.now().normalize()
                    days_behind = [(today - date).days for date in df_dates['latest_date']]
                    
                    bars = ax3.barh(table_names, days_behind, 
                                   color=['#4caf50' if d <= 1 else '#ffa726' if d <= 7 else '#ff6b6b' 
                                         for d in days_behind])
                    ax3.set_title('Days Behind Current Date', fontweight='bold')
                    ax3.set_xlabel('Days Behind')
                    
                    # Add value labels
                    for bar, days in zip(bars, days_behind):
                        width = bar.get_width()
                        ax3.annotate(f'{days}d',
                                   xy=(width, bar.get_y() + bar.get_height() / 2),
                                   xytext=(3, 0),  # 3 points horizontal offset
                                   textcoords="offset points",
                                   ha='left', va='center', fontsize=9)
                else:
                    ax3.text(0.5, 0.5, 'No date data available', 
                           horizontalalignment='center', verticalalignment='center',
                           transform=ax3.transAxes, fontsize=12)
                    ax3.set_title('Data Timeline Analysis', fontweight='bold')
                    
            except Exception as e:
                ax3.text(0.5, 0.5, f'Timeline error: {str(e)}', 
                       horizontalalignment='center', verticalalignment='center',
                       transform=ax3.transAxes, fontsize=10)
                ax3.set_title('Data Timeline Analysis', fontweight='bold')
                print(f"Timeline chart error: {e}")
            
            self.db_fig.tight_layout()
            self.db_canvas.draw()
            
        except Exception as e:
            print(f"Error updating database charts: {e}")

    def update_rsi_charts_with_data(self, analysis):
        """Update RSI charts with temporal distribution data."""
        try:
            if not hasattr(self, 'rsi_fig') or self.rsi_fig is None:
                return
                
            # Clear figure safely
            for ax in list(self.rsi_fig.axes):
                self.rsi_fig.delaxes(ax)
            
            # Create 2x3 subplot layout for temporal analysis
            ax1 = self.rsi_fig.add_subplot(2, 3, 1)
            ax2 = self.rsi_fig.add_subplot(2, 3, 2) 
            ax3 = self.rsi_fig.add_subplot(2, 3, 3)
            ax4 = self.rsi_fig.add_subplot(2, 3, 4)
            ax5 = self.rsi_fig.add_subplot(2, 3, 5)
            ax6 = self.rsi_fig.add_subplot(2, 3, 6)
            
            # Pie chart - All-time divergence distribution
            if analysis.get('total_bullish', 0) > 0 or analysis.get('total_bearish', 0) > 0:
                div_data = [analysis.get('total_bullish', 0), analysis.get('total_bearish', 0)]
                div_labels = [f"Bullish ({analysis.get('total_bullish', 0):,})", 
                             f"Bearish ({analysis.get('total_bearish', 0):,})"]
                div_colors = ['#4caf50', '#ff6b6b']
                
                # Filter out zero values
                filtered_data = []
                filtered_labels = []
                filtered_colors = []
                for data, label, color in zip(div_data, div_labels, div_colors):
                    if data > 0:
                        filtered_data.append(data)
                        filtered_labels.append(label)
                        filtered_colors.append(color)
                
                if filtered_data:
                    ax1.pie(filtered_data, labels=filtered_labels, colors=filtered_colors, 
                           autopct='%1.1f%%', startangle=90)
                else:
                    ax1.pie([1], labels=['No Data'], colors=['lightgray'], autopct='')
            else:
                ax1.pie([1], labels=['No Divergences'], colors=['lightgray'], autopct='')
            ax1.set_title('All-Time Distribution', fontweight='bold', fontsize=10)
            
            # Bar chart - Latest signals
            latest_bullish = analysis.get('hidden_bullish_count', 0)
            latest_bearish = analysis.get('hidden_bearish_count', 0)
            
            bars = ax2.bar(['Bullish', 'Bearish'], [latest_bullish, latest_bearish], 
                          color=['#4caf50', '#ff6b6b'])
            ax2.set_title(f'Latest Signals\n({analysis.get("latest_date", "N/A")})', fontweight='bold', fontsize=10)
            ax2.set_ylabel('Signals', fontsize=9)
            
            # Add value labels on bars
            for bar, count in zip(bars, [latest_bullish, latest_bearish]):
                height = bar.get_height()
                if height > 0:
                    ax2.annotate(f'{count}',
                               xy=(bar.get_x() + bar.get_width() / 2, height),
                               xytext=(0, 3),
                               textcoords="offset points",
                               ha='center', va='bottom', fontsize=9, fontweight='bold')
            
            # Yearly distribution
            yearly_data = analysis.get('yearly_distribution', {})
            if yearly_data:
                years = sorted(yearly_data.keys())
                bullish_yearly = [yearly_data[year].get('Bullish', 0) for year in years]
                bearish_yearly = [yearly_data[year].get('Bearish', 0) for year in years]
                
                x = range(len(years))
                width = 0.35
                
                bars1 = ax3.bar([i - width/2 for i in x], bullish_yearly, width, 
                               label='Bullish', color='#4caf50')
                bars2 = ax3.bar([i + width/2 for i in x], bearish_yearly, width,
                               label='Bearish', color='#ff6b6b')
                
                ax3.set_xlabel('Year', fontsize=9)
                ax3.set_ylabel('Signals', fontsize=9)
                ax3.set_title('Yearly Distribution', fontweight='bold', fontsize=10)
                ax3.set_xticks(x)
                ax3.set_xticklabels(years, fontsize=8)
                ax3.legend(fontsize=8)
                
                # Add value labels on bars
                for bars in [bars1, bars2]:
                    for bar in bars:
                        height = bar.get_height()
                        if height > 0:
                            ax3.annotate(f'{int(height)}',
                                       xy=(bar.get_x() + bar.get_width() / 2, height),
                                       xytext=(0, 3),
                                       textcoords="offset points",
                                       ha='center', va='bottom', fontsize=7)
            else:
                ax3.text(0.5, 0.5, 'No yearly data', ha='center', va='center', 
                        transform=ax3.transAxes, fontsize=10)
                ax3.set_title('Yearly Distribution', fontweight='bold', fontsize=10)
            
            # Monthly distribution (last 12 months)
            monthly_data = analysis.get('monthly_distribution', {})
            if monthly_data:
                months = sorted(monthly_data.keys())[-12:]  # Last 12 months
                bullish_monthly = [monthly_data[month].get('Bullish', 0) for month in months]
                bearish_monthly = [monthly_data[month].get('Bearish', 0) for month in months]
                
                x = range(len(months))
                width = 0.35
                
                bars1 = ax4.bar([i - width/2 for i in x], bullish_monthly, width, 
                               label='Bullish', color='#4caf50')
                bars2 = ax4.bar([i + width/2 for i in x], bearish_monthly, width,
                               label='Bearish', color='#ff6b6b')
                
                ax4.set_xlabel('Month', fontsize=9)
                ax4.set_ylabel('Signals', fontsize=9)
                ax4.set_title('Monthly Distribution (Last 12M)', fontweight='bold', fontsize=10)
                ax4.set_xticks(x)
                
                # Format month labels (show only month name)
                month_labels = [month.split('-')[1] for month in months]
                ax4.set_xticklabels(month_labels, fontsize=7, rotation=45)
                ax4.legend(fontsize=8)
                
                # Add value labels for significant bars only
                for bars in [bars1, bars2]:
                    for bar in bars:
                        height = bar.get_height()
                        if height > 50:  # Only show labels for significant counts
                            ax4.annotate(f'{int(height)}',
                                       xy=(bar.get_x() + bar.get_width() / 2, height),
                                       xytext=(0, 3),
                                       textcoords="offset points",
                                       ha='center', va='bottom', fontsize=7)
            else:
                ax4.text(0.5, 0.5, 'No monthly data', ha='center', va='center', 
                        transform=ax4.transAxes, fontsize=10)
                ax4.set_title('Monthly Distribution', fontweight='bold', fontsize=10)
            
            # Weekly distribution (last 8 weeks)
            weekly_data = analysis.get('weekly_distribution', {})
            if weekly_data:
                weeks = sorted(weekly_data.keys())[-8:]  # Last 8 weeks
                bullish_weekly = [weekly_data[week].get('Bullish', 0) for week in weeks]
                bearish_weekly = [weekly_data[week].get('Bearish', 0) for week in weeks]
                
                x = range(len(weeks))
                width = 0.35
                
                bars1 = ax5.bar([i - width/2 for i in x], bullish_weekly, width, 
                               label='Bullish', color='#4caf50')
                bars2 = ax5.bar([i + width/2 for i in x], bearish_weekly, width,
                               label='Bearish', color='#ff6b6b')
                
                ax5.set_xlabel('Week', fontsize=9)
                ax5.set_ylabel('Signals', fontsize=9)
                ax5.set_title('Weekly Distribution (Last 8W)', fontweight='bold', fontsize=10)
                ax5.set_xticks(x)
                
                # Format week labels (show week start date)
                week_labels = [f"W{i+1}" for i in range(len(weeks))]
                ax5.set_xticklabels(week_labels, fontsize=7)
                ax5.legend(fontsize=8)
                
                # Add value labels for significant bars only
                for bars in [bars1, bars2]:
                    for bar in bars:
                        height = bar.get_height()
                        if height > 10:  # Only show labels for significant counts
                            ax5.annotate(f'{int(height)}',
                                       xy=(bar.get_x() + bar.get_width() / 2, height),
                                       xytext=(0, 3),
                                       textcoords="offset points",
                                       ha='center', va='bottom', fontsize=7)
            else:
                ax5.text(0.5, 0.5, 'No weekly data', ha='center', va='center', 
                        transform=ax5.transAxes, fontsize=10)
                ax5.set_title('Weekly Distribution', fontweight='bold', fontsize=10)
            
            # RSI timeframe coverage
            timeframe_data = analysis.get('timeframe_status', {})
            if timeframe_data:
                timeframes = list(timeframe_data.keys())
                symbol_counts = [tf_data.get('symbols', 0) for tf_data in timeframe_data.values()]
                
                bars = ax6.bar(timeframes, symbol_counts, color=['#2196f3', '#ff9800', '#9c27b0'])
                ax6.set_title('RSI Coverage', fontweight='bold', fontsize=10)
                ax6.set_ylabel('Symbols', fontsize=9)
                ax6.tick_params(axis='x', rotation=45, labelsize=8)
                
                # Add value labels on bars
                for bar, count in zip(bars, symbol_counts):
                    height = bar.get_height()
                    if height > 0:
                        ax6.annotate(f'{count:,}',
                                   xy=(bar.get_x() + bar.get_width() / 2, height),
                                   xytext=(0, 3),
                                   textcoords="offset points",
                                   ha='center', va='bottom', fontsize=7)
            else:
                ax6.text(0.5, 0.5, 'No timeframe data', ha='center', va='center', 
                        transform=ax6.transAxes, fontsize=10)
                ax6.set_title('RSI Coverage', fontweight='bold', fontsize=10)
            
            # Use subplots_adjust instead of tight_layout to avoid errors
            self.rsi_fig.subplots_adjust(left=0.08, right=0.95, top=0.92, bottom=0.15, 
                                       wspace=0.3, hspace=0.45)
            
            if hasattr(self, 'rsi_canvas') and self.rsi_canvas is not None:
                self.rsi_canvas.draw()
            
        except Exception as e:
            print(f"Error updating RSI charts: {e}")
            import traceback
            traceback.print_exc()

    # Optimized connection-reuse methods for dashboard refresh
    def check_bhav_data_with_connection(self, conn) -> Dict[str, Any]:
        """Check BHAV data availability using existing connection."""
        try:
            from sqlalchemy import text
            query = text("""
                SELECT MIN(trade_date) as earliest_date, MAX(trade_date) as latest_date,
                       COUNT(DISTINCT trade_date) as trading_days, COUNT(*) as total_records
                FROM nse_equity_bhavcopy_full WHERE trade_date IS NOT NULL
            """)
            result = conn.execute(query).fetchone()
            
            if result and result.latest_date:
                days_behind = (date.today() - result.latest_date).days
                status = "✅ Up to Date" if days_behind <= 3 else "⚠️ Behind" if days_behind <= 7 else "❌ Outdated"
                color = "green" if days_behind <= 3 else "orange" if days_behind <= 7 else "red"
                
                return {
                    'status': status, 'color': color,
                    'details': f"{result.trading_days:,} trading days\\n{result.total_records:,} records",
                    'earliest_date': result.earliest_date, 'latest_date': result.latest_date,
                    'trading_days': result.trading_days, 'total_records': result.total_records,
                    'days_behind': days_behind
                }
            else:
                return {'status': "❌ No Data", 'color': "red", 'details': "No BHAV data found",
                        'earliest_date': None, 'latest_date': None, 'trading_days': 0, 'total_records': 0, 'days_behind': 999}
        except Exception as e:
            return {'status': "❌ Error", 'color': "red", 'details': f"Query failed: {str(e)}",
                    'earliest_date': None, 'latest_date': None, 'trading_days': 0, 'total_records': 0, 'days_behind': 999}

    def check_sma_data_with_connection(self, conn) -> Dict[str, Any]:
        """Check SMA data availability using existing connection."""
        try:
            from sqlalchemy import text
            # Use actual table name 'moving_averages' instead of 'nse_sma_analysis'
            query = text("""
                SELECT MAX(trade_date) as latest_date, COUNT(DISTINCT trade_date) as trading_days,
                       COUNT(DISTINCT symbol) as symbols_count, COUNT(*) as total_records
                FROM moving_averages WHERE trade_date IS NOT NULL
            """)
            result = conn.execute(query).fetchone()
            
            if result and result.latest_date:
                days_behind = (date.today() - result.latest_date).days
                status = "✅ Current" if days_behind <= 3 else "⚠️ Behind" if days_behind <= 7 else "❌ Outdated"
                color = "green" if days_behind <= 3 else "orange" if days_behind <= 7 else "red"
                
                return {
                    'status': status, 'color': color,
                    'details': f"{result.symbols_count:,} symbols\\n{result.total_records:,} records",
                    'latest_date': result.latest_date, 'trading_days': result.trading_days,
                    'symbols_count': result.symbols_count, 'total_records': result.total_records, 'days_behind': days_behind
                }
            else:
                return {'status': "❌ No Data", 'color': "red", 'details': "No SMA data found",
                        'latest_date': None, 'trading_days': 0, 'symbols_count': 0, 'total_records': 0, 'days_behind': 999}
        except Exception as e:
            return {'status': "❌ Error", 'color': "red", 'details': f"Query failed: {str(e)}",
                    'latest_date': None, 'trading_days': 0, 'symbols_count': 0, 'total_records': 0, 'days_behind': 999}

    def check_rsi_data_with_connection(self, conn) -> Dict[str, Any]:
        """Check RSI data availability using existing connection."""
        try:
            from sqlalchemy import text
            query = text("""
                SELECT MAX(trade_date) as latest_date, COUNT(DISTINCT trade_date) as trading_days,
                       COUNT(DISTINCT symbol) as symbols_count, COUNT(*) as total_records
                FROM nse_rsi_daily WHERE trade_date IS NOT NULL
            """)
            result = conn.execute(query).fetchone()
            
            if result and result.latest_date:
                days_behind = (date.today() - result.latest_date).days
                status = "✅ Current" if days_behind <= 3 else "⚠️ Behind" if days_behind <= 7 else "❌ Outdated"
                color = "green" if days_behind <= 3 else "orange" if days_behind <= 7 else "red"
                
                return {
                    'status': status, 'color': color,
                    'details': f"{result.symbols_count:,} symbols\\n{result.total_records:,} records",
                    'latest_date': result.latest_date, 'trading_days': result.trading_days,
                    'symbols_count': result.symbols_count, 'total_records': result.total_records, 'days_behind': days_behind
                }
            else:
                return {'status': "❌ No Data", 'color': "red", 'details': "No RSI data found",
                        'latest_date': None, 'trading_days': 0, 'symbols_count': 0, 'total_records': 0, 'days_behind': 999}
        except Exception as e:
            return {'status': "❌ Error", 'color': "red", 'details': f"Query failed: {str(e)}",
                    'latest_date': None, 'trading_days': 0, 'symbols_count': 0, 'total_records': 0, 'days_behind': 999}

    def check_trend_data_with_connection(self, conn) -> Dict[str, Any]:
        """Check trend data availability using existing connection."""
        try:
            from sqlalchemy import text
            # Use actual table name 'trend_analysis' instead of 'nse_trend_ratings'
            query = text("""
                SELECT MAX(trade_date) as latest_date, COUNT(DISTINCT trade_date) as trading_days,
                       COUNT(DISTINCT symbol) as symbols_count, COUNT(*) as total_records
                FROM trend_analysis WHERE trade_date IS NOT NULL
            """)
            result = conn.execute(query).fetchone()
            
            if result and result.latest_date:
                days_behind = (date.today() - result.latest_date).days
                status = "✅ Current" if days_behind <= 3 else "⚠️ Behind" if days_behind <= 7 else "❌ Outdated"
                color = "green" if days_behind <= 3 else "orange" if days_behind <= 7 else "red"
                
                return {
                    'status': status, 'color': color,
                    'details': f"{result.symbols_count:,} symbols\\n{result.total_records:,} records",
                    'latest_date': result.latest_date, 'trading_days': result.trading_days,
                    'symbols_count': result.symbols_count, 'total_records': result.total_records, 'days_behind': days_behind
                }
            else:
                return {'status': "❌ No Data", 'color': "red", 'details': "No trend data found",
                        'latest_date': None, 'trading_days': 0, 'symbols_count': 0, 'total_records': 0, 'days_behind': 999}
        except Exception as e:
            return {'status': "❌ Error", 'color': "red", 'details': f"Query failed: {str(e)}",
                    'latest_date': None, 'trading_days': 0, 'symbols_count': 0, 'total_records': 0, 'days_behind': 999}

    def cleanup(self):
        """Clean up resources when dashboard is destroyed."""
        if hasattr(self, '_engine') and self._engine:
            try:
                self._engine.dispose()
                print("📊 Dashboard: Database engine disposed successfully")
            except Exception as e:
                print(f"📊 Dashboard: Error disposing engine: {e}")
            finally:
                self._engine = None

# Test function
if __name__ == "__main__":
    root = tk.Tk()
    root.title("Enhanced Dashboard Test")
    root.geometry("1200x800")
    dashboard = DashboardTab(root)
    root.mainloop()