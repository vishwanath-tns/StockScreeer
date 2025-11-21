#!/usr/bin/env python3
"""
Yahoo Finance Chart Visualizer
Interactive charting tool for market data visualization
"""

import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime, date, timedelta
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import mplfinance as mpf
import pandas as pd
import numpy as np
import logging
from typing import List, Optional
import sys
import os

# Add current directory to path for local imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from yahoo_client import YahooFinanceClient
from db_service import YFinanceDBService
from models import DailyQuote
from config import YFinanceConfig

# Setup logging
logging.basicConfig(level=YFinanceConfig.LOG_LEVEL)
logger = logging.getLogger(__name__)

class ChartVisualizerGUI:
    """Interactive chart visualization GUI"""
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("📊 Yahoo Finance Chart Visualizer")
        self.root.geometry("1400x900")
        self.root.configure(bg='#1a1a2e')
        
        # Services
        self.yahoo_client = YahooFinanceClient()
        self.db_service = YFinanceDBService()
        
        # Chart settings
        self.current_data = None
        self.chart_figure = None
        self.chart_canvas = None
        
        # Color scheme
        self.colors = {
            'bg': '#1a1a2e',
            'card': '#16213e', 
            'accent': '#0f3460',
            'primary': '#e94560',
            'text': '#ffffff',
            'secondary': '#a8a8a8',
            'success': '#2ecc71',
            'warning': '#f39c12',
            'error': '#e74c3c'
        }
        
        # Fonts
        self.fonts = {
            'title': ('Segoe UI', 16, 'bold'),
            'subtitle': ('Segoe UI', 12, 'bold'),
            'body': ('Segoe UI', 10),
            'small': ('Segoe UI', 9)
        }
        
        self.setup_ui()
        self.load_default_chart()
    
    def setup_ui(self):
        """Setup the user interface"""
        
        # Main container
        main_frame = tk.Frame(self.root, bg=self.colors['bg'])
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Top control panel
        self.setup_control_panel(main_frame)
        
        # Chart area
        self.setup_chart_area(main_frame)
        
        # Status bar
        self.setup_status_bar(main_frame)
    
    def setup_control_panel(self, parent):
        """Setup control panel with symbol and date selection"""
        control_frame = tk.LabelFrame(
            parent,
            text="📈 Chart Controls",
            font=self.fonts['subtitle'],
            bg=self.colors['card'],
            fg=self.colors['text'],
            relief=tk.RAISED,
            bd=2
        )
        control_frame.pack(fill=tk.X, pady=(0, 10))
        
        content_frame = tk.Frame(control_frame, bg=self.colors['card'])
        content_frame.pack(fill=tk.X, padx=15, pady=15)
        
        # Row 1: Symbol selection
        row1_frame = tk.Frame(content_frame, bg=self.colors['card'])
        row1_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Symbol selection
        tk.Label(
            row1_frame,
            text="Symbol:",
            font=self.fonts['body'],
            bg=self.colors['card'],
            fg=self.colors['text'],
            width=10,
            anchor='w'
        ).pack(side=tk.LEFT)
        
        # Load available symbols from database
        available_symbols = self.get_available_symbols()
        default_symbol = available_symbols[0] if available_symbols else "NIFTY"
        
        self.symbol_var = tk.StringVar(value=default_symbol)
        self.symbol_combo = ttk.Combobox(
            row1_frame,
            textvariable=self.symbol_var,
            values=available_symbols,
            width=20,
            state="readonly"
        )
        self.symbol_combo.pack(side=tk.LEFT, padx=(5, 20))
        
        # Add refresh button to reload symbols
        tk.Button(
            row1_frame,
            text="🔄",
            command=self.refresh_symbols,
            font=("Arial", 8),
            width=3,
            bg=self.colors['primary'],
            fg='white',
            relief=tk.FLAT
        ).pack(side=tk.LEFT, padx=(2, 20))
        
        # Chart type selection
        tk.Label(
            row1_frame,
            text="Chart Type:",
            font=self.fonts['body'],
            bg=self.colors['card'],
            fg=self.colors['text'],
            width=12,
            anchor='w'
        ).pack(side=tk.LEFT)
        
        self.chart_type_var = tk.StringVar(value="Line")
        chart_type_combo = ttk.Combobox(
            row1_frame,
            textvariable=self.chart_type_var,
            values=["Line", "Candlestick", "OHLC", "Area"],
            width=15,
            state="readonly"
        )
        chart_type_combo.pack(side=tk.LEFT, padx=(5, 20))
        chart_type_combo.bind('<<ComboboxSelected>>', self.on_chart_type_changed)
        
        # Time period selection
        tk.Label(
            row1_frame,
            text="Period:",
            font=self.fonts['body'],
            bg=self.colors['card'],
            fg=self.colors['text'],
            width=10,
            anchor='w'
        ).pack(side=tk.LEFT)
        
        self.period_var = tk.StringVar(value="3 Months")
        period_combo = ttk.Combobox(
            row1_frame,
            textvariable=self.period_var,
            values=["1 Month", "3 Months", "6 Months", "1 Year", "2 Years", "Custom"],
            width=12,
            state="readonly"
        )
        period_combo.pack(side=tk.LEFT, padx=(5, 20))
        period_combo.bind("<<ComboboxSelected>>", self.on_period_change)
        
        # Row 2: Date range (initially hidden)
        self.date_frame = tk.Frame(content_frame, bg=self.colors['card'])
        self.date_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Start date
        tk.Label(
            self.date_frame,
            text="Start Date:",
            font=self.fonts['body'],
            bg=self.colors['card'],
            fg=self.colors['text'],
            width=10,
            anchor='w'
        ).pack(side=tk.LEFT)
        
        # Default to 3 months ago
        default_start = date.today() - timedelta(days=90)
        self.start_year_var = tk.StringVar(value=str(default_start.year))
        self.start_month_var = tk.StringVar(value=f"{default_start.month:02d}")
        self.start_day_var = tk.StringVar(value=f"{default_start.day:02d}")
        
        ttk.Combobox(
            self.date_frame,
            textvariable=self.start_year_var,
            values=[str(year) for year in range(2020, 2026)],
            width=6,
            state="readonly"
        ).pack(side=tk.LEFT, padx=(5, 2))
        
        tk.Label(self.date_frame, text="/", bg=self.colors['card'], fg=self.colors['text']).pack(side=tk.LEFT)
        
        ttk.Combobox(
            self.date_frame,
            textvariable=self.start_month_var,
            values=[f"{i:02d}" for i in range(1, 13)],
            width=4,
            state="readonly"
        ).pack(side=tk.LEFT, padx=2)
        
        tk.Label(self.date_frame, text="/", bg=self.colors['card'], fg=self.colors['text']).pack(side=tk.LEFT)
        
        ttk.Combobox(
            self.date_frame,
            textvariable=self.start_day_var,
            values=[f"{i:02d}" for i in range(1, 32)],
            width=4,
            state="readonly"
        ).pack(side=tk.LEFT, padx=(2, 20))
        
        # End date
        tk.Label(
            self.date_frame,
            text="End Date:",
            font=self.fonts['body'],
            bg=self.colors['card'],
            fg=self.colors['text'],
            width=10,
            anchor='w'
        ).pack(side=tk.LEFT)
        
        today = date.today()
        self.end_year_var = tk.StringVar(value=str(today.year))
        self.end_month_var = tk.StringVar(value=f"{today.month:02d}")
        self.end_day_var = tk.StringVar(value=f"{today.day:02d}")
        
        ttk.Combobox(
            self.date_frame,
            textvariable=self.end_year_var,
            values=[str(year) for year in range(2020, 2026)],
            width=6,
            state="readonly"
        ).pack(side=tk.LEFT, padx=(5, 2))
        
        tk.Label(self.date_frame, text="/", bg=self.colors['card'], fg=self.colors['text']).pack(side=tk.LEFT)
        
        ttk.Combobox(
            self.date_frame,
            textvariable=self.end_month_var,
            values=[f"{i:02d}" for i in range(1, 13)],
            width=4,
            state="readonly"
        ).pack(side=tk.LEFT, padx=2)
        
        tk.Label(self.date_frame, text="/", bg=self.colors['card'], fg=self.colors['text']).pack(side=tk.LEFT)
        
        ttk.Combobox(
            self.date_frame,
            textvariable=self.end_day_var,
            values=[f"{i:02d}" for i in range(1, 32)],
            width=4,
            state="readonly"
        ).pack(side=tk.LEFT, padx=(2, 20))
        
        # Row 3: Action buttons
        button_frame = tk.Frame(content_frame, bg=self.colors['card'])
        button_frame.pack(fill=tk.X)
        
        # Update chart button
        self.update_button = tk.Button(
            button_frame,
            text="📊 Update Chart",
            command=self.update_chart,
            font=self.fonts['subtitle'],
            bg=self.colors['primary'],
            fg=self.colors['text'],
            relief=tk.FLAT,
            padx=20,
            pady=8
        )
        self.update_button.pack(side=tk.LEFT, padx=(0, 10))
        
        # Download data button  
        self.download_button = tk.Button(
            button_frame,
            text="⬇️ Download Data",
            command=self.download_data,
            font=self.fonts['body'],
            bg=self.colors['success'],
            fg=self.colors['text'],
            relief=tk.FLAT,
            padx=15,
            pady=6
        )
        self.download_button.pack(side=tk.LEFT, padx=(0, 10))
        
        # Export chart button
        self.export_button = tk.Button(
            button_frame,
            text="💾 Export Chart",
            command=self.export_chart,
            font=self.fonts['body'],
            bg=self.colors['warning'],
            fg=self.colors['text'],
            relief=tk.FLAT,
            padx=15,
            pady=6
        )
        self.export_button.pack(side=tk.LEFT, padx=(0, 10))
        
        # Data info
        self.data_info_label = tk.Label(
            button_frame,
            text="No data loaded",
            font=self.fonts['small'],
            bg=self.colors['card'],
            fg=self.colors['secondary']
        )
        self.data_info_label.pack(side=tk.RIGHT)
        
        # Initially hide date frame for preset periods
        self.date_frame.pack_forget()
    
    def setup_chart_area(self, parent):
        """Setup matplotlib chart area"""
        chart_frame = tk.LabelFrame(
            parent,
            text="📈 Chart Display",
            font=self.fonts['subtitle'],
            bg=self.colors['card'],
            fg=self.colors['text'],
            relief=tk.RAISED,
            bd=2
        )
        chart_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # Create matplotlib figure with dark theme
        self.chart_figure = Figure(figsize=(14, 8), facecolor='#1a1a2e')
        self.chart_figure.patch.set_facecolor('#1a1a2e')
        
        # Create canvas
        self.chart_canvas = FigureCanvasTkAgg(self.chart_figure, chart_frame)
        self.chart_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Add toolbar for zoom/pan
        from matplotlib.backends.backend_tkagg import NavigationToolbar2Tk
        toolbar = NavigationToolbar2Tk(self.chart_canvas, chart_frame)
        toolbar.update()
    
    def setup_status_bar(self, parent):
        """Setup status bar"""
        status_frame = tk.Frame(parent, bg=self.colors['accent'], relief=tk.SUNKEN, bd=1)
        status_frame.pack(fill=tk.X)
        
        self.status_var = tk.StringVar(value="Ready • Select symbol and date range to view charts")
        self.status_label = tk.Label(
            status_frame,
            textvariable=self.status_var,
            font=self.fonts['small'],
            bg=self.colors['accent'],
            fg=self.colors['text'],
            anchor='w'
        )
        self.status_label.pack(fill=tk.X, padx=10, pady=3)
    
    def on_period_change(self, event=None):
        """Handle period selection change"""
        period = self.period_var.get()
        
        if period == "Custom":
            # Show date selection controls
            self.date_frame.pack(fill=tk.X, pady=(0, 10), after=self.date_frame.master.winfo_children()[0])
        else:
            # Hide date selection and set predefined range
            self.date_frame.pack_forget()
            self.set_predefined_period(period)
    
    def set_predefined_period(self, period: str):
        """Set predefined date range based on period"""
        end_date = date.today()
        
        if period == "1 Month":
            start_date = end_date - timedelta(days=30)
        elif period == "3 Months":
            start_date = end_date - timedelta(days=90)
        elif period == "6 Months":
            start_date = end_date - timedelta(days=180)
        elif period == "1 Year":
            start_date = end_date - timedelta(days=365)
        elif period == "2 Years":
            start_date = end_date - timedelta(days=730)
        else:
            return
        
        # Update date variables
        self.start_year_var.set(str(start_date.year))
        self.start_month_var.set(f"{start_date.month:02d}")
        self.start_day_var.set(f"{start_date.day:02d}")
        
        self.end_year_var.set(str(end_date.year))
        self.end_month_var.set(f"{end_date.month:02d}")
        self.end_day_var.set(f"{end_date.day:02d}")
    
    def get_selected_dates(self) -> tuple:
        """Get selected date range"""
        try:
            start_date = date(
                int(self.start_year_var.get()),
                int(self.start_month_var.get()),
                int(self.start_day_var.get())
            )
            
            end_date = date(
                int(self.end_year_var.get()),
                int(self.end_month_var.get()),
                int(self.end_day_var.get())
            )
            
            return start_date, end_date
            
        except ValueError as e:
            raise ValueError(f"Invalid date selection: {e}")
    
    def on_chart_type_changed(self, event=None):
        """Handle chart type selection change"""
        if hasattr(self, 'current_data') and self.current_data is not None:
            symbol = self.symbol_var.get()
            self.update_chart_display(self.current_data, symbol)
    
    def get_available_symbols(self) -> List[str]:
        """Get list of available symbols from database"""
        try:
            # Get symbols from yfinance_daily_quotes table
            conn = self.db_service.get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT DISTINCT symbol 
                FROM yfinance_daily_quotes 
                ORDER BY symbol
            """)
            
            symbols = [row[0] for row in cursor.fetchall()]
            cursor.close()
            
            # Add default index symbols if not present
            default_symbols = ["^NSEI", "^NSEBANK", "^BSESN"]
            for symbol in default_symbols:
                if symbol not in symbols:
                    symbols.insert(0, symbol)
            
            return symbols if symbols else ["NIFTY", "BANKNIFTY", "SENSEX"]
            
        except Exception as e:
            logger.warning(f"Failed to load symbols from database: {e}")
            return ["NIFTY", "BANKNIFTY", "SENSEX"]
    
    def refresh_symbols(self):
        """Refresh the symbol dropdown with latest data"""
        try:
            self.status_var.set("Refreshing symbol list...")
            available_symbols = self.get_available_symbols()
            
            self.symbol_combo.configure(values=available_symbols)
            
            # Keep current selection if still available
            current = self.symbol_var.get()
            if current not in available_symbols and available_symbols:
                self.symbol_var.set(available_symbols[0])
            
            self.status_var.set(f"Loaded {len(available_symbols)} symbols")
            
        except Exception as e:
            logger.error(f"Failed to refresh symbols: {e}")
            self.status_var.set("Failed to refresh symbols")

    def load_data(self, symbol: str, start_date: date, end_date: date) -> pd.DataFrame:
        """Load data from database or download if missing"""
        try:
            # Try to get data from database first
            quotes = self.db_service.get_quotes(symbol, start_date, end_date)
            
            if not quotes:
                self.status_var.set(f"No data in database for {symbol}, downloading...")
                # Download data if not available
                quotes = self.yahoo_client.download_daily_data(symbol, start_date, end_date)
                
                if quotes:
                    # Save downloaded data
                    self.db_service.insert_quotes(quotes)
                    self.status_var.set(f"Downloaded and saved {len(quotes)} records for {symbol}")
                else:
                    raise ValueError(f"No data available for {symbol} in the specified date range")
            
            # Convert to pandas DataFrame
            data_dict = {
                'Date': [],
                'Open': [],
                'High': [], 
                'Low': [],
                'Close': [],
                'Volume': []
            }
            
            for quote in quotes:
                data_dict['Date'].append(quote.date)
                data_dict['Open'].append(float(quote.open) if quote.open else np.nan)
                data_dict['High'].append(float(quote.high) if quote.high else np.nan)
                data_dict['Low'].append(float(quote.low) if quote.low else np.nan)
                data_dict['Close'].append(float(quote.close) if quote.close else np.nan)
                data_dict['Volume'].append(int(quote.volume) if quote.volume else 0)
            
            df = pd.DataFrame(data_dict)
            df['Date'] = pd.to_datetime(df['Date'])
            df.set_index('Date', inplace=True)
            df.sort_index(inplace=True)
            
            # Remove any rows with NaN OHLC values
            df.dropna(subset=['Open', 'High', 'Low', 'Close'], inplace=True)
            
            return df
            
        except Exception as e:
            logger.error(f"Error loading data: {e}")
            raise
    
    def update_chart(self):
        """Update the chart with current settings"""
        try:
            symbol = self.symbol_var.get()
            chart_type = self.chart_type_var.get()
            
            # Get date range
            start_date, end_date = self.get_selected_dates()
            
            if start_date > end_date:
                messagebox.showerror("Error", "Start date must be before end date")
                return
            
            self.status_var.set(f"Loading data for {symbol}...")
            self.root.update()
            
            # Load data
            df = self.load_data(symbol, start_date, end_date)
            
            if df.empty:
                messagebox.showerror("Error", f"No data available for {symbol}")
                return
            
            self.current_data = df
            
            # Clear previous chart
            self.chart_figure.clear()
            
            # Create chart based on type
            chart_type = self.chart_type_var.get()
            if chart_type == "Candlestick":
                self.create_candlestick_chart(df, symbol)
            elif chart_type == "OHLC":
                self.create_ohlc_chart(df, symbol)
            elif chart_type == "Line":
                self.create_line_chart(df, symbol)
            elif chart_type == "Area":
                self.create_area_chart(df, symbol)
            else:
                # Default to line chart
                self.create_line_chart(df, symbol)
            
            # Refresh canvas
            self.chart_canvas.draw()
            
            # Update info
            self.data_info_label.config(
                text=f"{len(df)} records • {df.index[0].strftime('%Y-%m-%d')} to {df.index[-1].strftime('%Y-%m-%d')}",
                fg=self.colors['success']
            )
            
            self.status_var.set(f"Chart updated for {symbol} • {len(df)} data points")
            
        except Exception as e:
            logger.error(f"Error updating chart: {e}")
            messagebox.showerror("Error", f"Failed to update chart: {str(e)}")
            self.status_var.set("Chart update failed")
    
    def update_chart_display(self, df: pd.DataFrame, symbol: str):
        """Update chart display without reloading data"""
        try:
            chart_type = self.chart_type_var.get()
            
            # Clear previous chart
            self.chart_figure.clear()
            
            # Create chart based on type
            if chart_type == "Candlestick":
                self.create_candlestick_chart(df, symbol)
            elif chart_type == "OHLC":
                self.create_ohlc_chart(df, symbol)
            elif chart_type == "Line":
                self.create_line_chart(df, symbol)
            elif chart_type == "Area":
                self.create_area_chart(df, symbol)
            else:
                self.create_line_chart(df, symbol)
            
            # Refresh canvas
            self.chart_canvas.draw()
            
            self.status_var.set(f"Chart updated to {chart_type} view for {symbol}")
            
        except Exception as e:
            logger.error(f"Error updating chart display: {e}")
            self.status_var.set("Chart display update failed")
    
    def create_candlestick_chart(self, df: pd.DataFrame, symbol: str):
        """Create candlestick chart using matplotlib"""
        try:
            ax = self.chart_figure.add_subplot(111)
            ax.set_facecolor('#1a1a2e')
            
            # Import Rectangle here to avoid import issues
            from matplotlib.patches import Rectangle
            
            # Prepare data for candlestick plotting
            for i, (date, row) in enumerate(df.iterrows()):
                open_price = float(row['Open'])
                high_price = float(row['High']) 
                low_price = float(row['Low'])
                close_price = float(row['Close'])
                
                # Determine color - green for up, red for down
                is_up = close_price >= open_price
                color = '#2ecc71' if is_up else '#e74c3c'
                edge_color = '#1e8449' if is_up else '#c0392b'
                
                # Draw high-low line (wick) first
                ax.plot([i, i], [low_price, high_price], 
                       color=color, linewidth=1.5, alpha=0.8, solid_capstyle='round')
                
                # Draw open-close rectangle (body)
                body_height = abs(close_price - open_price)
                body_bottom = min(open_price, close_price)
                
                if body_height > 0:
                    # Create rectangle for candle body
                    rect = Rectangle(
                        (i-0.4, body_bottom), 
                        0.8, 
                        body_height,
                        facecolor=color,
                        edgecolor=edge_color,
                        alpha=0.9,
                        linewidth=0.5
                    )
                    ax.add_patch(rect)
                else:
                    # Doji (open == close) - draw horizontal line
                    ax.plot([i-0.4, i+0.4], [open_price, open_price], 
                           color=color, linewidth=2, alpha=0.8)
            
            # Customize chart appearance
            ax.set_title(f'{symbol} Candlestick Chart', color='white', fontsize=16, pad=20, weight='bold')
            ax.set_ylabel('Price (₹)', color='white', fontsize=12)
            ax.tick_params(colors='white', labelsize=10)
            
            # Format x-axis with dates
            if len(df) > 0:
                # Show date labels - adjust density based on data length
                step = max(1, len(df) // 8)  # Show ~8 labels
                tick_positions = list(range(0, len(df), step))
                tick_labels = [df.index[i].strftime('%m/%d') for i in tick_positions if i < len(df)]
                
                ax.set_xticks(tick_positions)
                ax.set_xticklabels(tick_labels, rotation=45, ha='right')
                ax.set_xlim(-0.5, len(df) - 0.5)
            
            # Add grid and styling
            ax.grid(True, alpha=0.2, color='gray', linestyle='--')
            ax.spines['bottom'].set_color('#34495e')
            ax.spines['top'].set_color('#34495e') 
            ax.spines['right'].set_color('#34495e')
            ax.spines['left'].set_color('#34495e')
            
            # Add price range info
            if len(df) > 0:
                price_range = df['High'].max() - df['Low'].min()
                ax.text(0.02, 0.98, f"Range: ₹{price_range:.2f}", 
                       transform=ax.transAxes, color='white', fontsize=10, 
                       verticalalignment='top', alpha=0.8,
                       bbox=dict(boxstyle="round,pad=0.3", facecolor='#34495e', alpha=0.7))
            
            plt.tight_layout()
            
        except Exception as e:
            logger.error(f"Error creating candlestick chart: {e}")
            # Fallback to line chart if candlestick fails
            self.create_line_chart(df, symbol)
            
            ax.set_xticks(tick_positions)
            ax.set_xticklabels(tick_labels, rotation=45, ha='right')
            
            # Add grid
            ax.grid(True, alpha=0.3, color='#4a4a4a')
            
            # Set margins
            ax.margins(x=0.02)
            
            # Adjust layout
            self.chart_figure.tight_layout()
            
        except Exception as e:
            logger.error(f"Error creating candlestick chart: {e}")
            # Fallback to simple line chart
            self.create_line_chart(df, symbol)
    
    def create_ohlc_chart(self, df: pd.DataFrame, symbol: str):
        """Create OHLC bar chart"""
        ax = self.chart_figure.add_subplot(111)
        ax.set_facecolor('#1a1a2e')
        
        # OHLC bars
        for i, (date, row) in enumerate(df.iterrows()):
            color = '#2ecc71' if row['Close'] >= row['Open'] else '#e74c3c'
            
            # High-Low line
            ax.plot([i, i], [row['Low'], row['High']], color=color, linewidth=1)
            
            # Open tick
            ax.plot([i-0.1, i], [row['Open'], row['Open']], color=color, linewidth=2)
            
            # Close tick
            ax.plot([i, i+0.1], [row['Close'], row['Close']], color=color, linewidth=2)
        
        ax.set_title(f'{symbol} OHLC Chart', color='white', fontsize=14)
        ax.set_ylabel('Price (₹)', color='white')
        ax.tick_params(colors='white')
        
        # Set x-axis labels
        step = max(1, len(df) // 10)
        ax.set_xticks(range(0, len(df), step))
        ax.set_xticklabels([df.index[i].strftime('%Y-%m-%d') for i in range(0, len(df), step)], rotation=45)
        
        ax.grid(True, alpha=0.3)
    
    def create_line_chart(self, df: pd.DataFrame, symbol: str):
        """Create line chart"""
        ax = self.chart_figure.add_subplot(111)
        ax.set_facecolor('#1a1a2e')
        
        ax.plot(df.index, df['Close'], color='#3498db', linewidth=2, label='Close Price')
        
        ax.set_title(f'{symbol} Price Chart', color='white', fontsize=14, pad=20)
        ax.set_ylabel('Price (₹)', color='white')
        ax.tick_params(colors='white')
        ax.tick_params(axis='x', rotation=45)
        ax.grid(True, alpha=0.3, color='#4a4a4a')
        ax.legend(facecolor='#16213e', edgecolor='white', labelcolor='white')
        
        # Add price statistics
        current_price = df['Close'].iloc[-1]
        price_change = current_price - df['Close'].iloc[0]
        price_change_pct = (price_change / df['Close'].iloc[0]) * 100
        
        # Add text box with stats
        stats_text = f'Current: ₹{current_price:.2f}\nChange: ₹{price_change:.2f} ({price_change_pct:+.2f}%)'
        ax.text(0.02, 0.98, stats_text, transform=ax.transAxes, 
                verticalalignment='top', fontsize=10, color='white',
                bbox=dict(boxstyle='round', facecolor='#16213e', alpha=0.8))
        
        self.chart_figure.tight_layout()
    
    def create_area_chart(self, df: pd.DataFrame, symbol: str):
        """Create area chart"""
        ax = self.chart_figure.add_subplot(111)
        ax.set_facecolor('#1a1a2e')
        
        ax.fill_between(df.index, df['Close'], alpha=0.7, color='#3498db', label='Close Price')
        ax.plot(df.index, df['Close'], color='#2980b9', linewidth=1)
        
        ax.set_title(f'{symbol} Price Area Chart', color='white', fontsize=14, pad=20)
        ax.set_ylabel('Price (₹)', color='white')
        ax.tick_params(colors='white')
        ax.tick_params(axis='x', rotation=45)
        ax.grid(True, alpha=0.3, color='#4a4a4a')
        ax.legend(facecolor='#16213e', edgecolor='white', labelcolor='white')
        
        # Add price statistics
        current_price = df['Close'].iloc[-1]
        min_price = df['Close'].min()
        max_price = df['Close'].max()
        
        stats_text = f'Current: ₹{current_price:.2f}\nRange: ₹{min_price:.2f} - ₹{max_price:.2f}'
        ax.text(0.02, 0.98, stats_text, transform=ax.transAxes,
                verticalalignment='top', fontsize=10, color='white',
                bbox=dict(boxstyle='round', facecolor='#16213e', alpha=0.8))
        
        self.chart_figure.tight_layout()
    
    def download_data(self):
        """Download data for selected symbol and date range"""
        try:
            symbol = self.symbol_var.get()
            start_date, end_date = self.get_selected_dates()
            
            self.status_var.set(f"Downloading {symbol} data...")
            self.root.update()
            
            # Download from Yahoo Finance
            quotes = self.yahoo_client.download_daily_data(symbol, start_date, end_date)
            
            if quotes:
                # Save to database
                inserted, updated = self.db_service.insert_quotes(quotes)
                self.status_var.set(f"Downloaded {symbol}: {inserted} new, {updated} updated records")
                messagebox.showinfo("Success", f"Downloaded {len(quotes)} records for {symbol}")
            else:
                messagebox.showerror("Error", f"No data available for {symbol}")
                
        except Exception as e:
            logger.error(f"Error downloading data: {e}")
            messagebox.showerror("Error", f"Failed to download data: {str(e)}")
    
    def export_chart(self):
        """Export current chart to file"""
        if self.current_data is None:
            messagebox.showerror("Error", "No chart data to export")
            return
        
        try:
            from tkinter import filedialog
            
            symbol = self.symbol_var.get()
            filename = f"{symbol}_chart_{date.today().strftime('%Y%m%d')}.png"
            
            file_path = filedialog.asksaveasfilename(
                defaultextension=".png",
                initialfile=filename,  # Use initialfile instead of initialfilename
                filetypes=[("PNG files", "*.png"), ("PDF files", "*.pdf"), ("All files", "*.*")]
            )
            
            if file_path:
                self.chart_figure.savefig(file_path, dpi=300, bbox_inches='tight', facecolor='#1a1a2e')
                messagebox.showinfo("Success", f"Chart exported to {file_path}")
                self.status_var.set(f"Chart exported: {file_path}")
                
        except Exception as e:
            logger.error(f"Error exporting chart: {e}")
            messagebox.showerror("Error", f"Failed to export chart: {str(e)}")
    
    def load_default_chart(self):
        """Load default 3-month NIFTY candlestick chart"""
        try:
            # Set default period to 3 months
            self.set_predefined_period("3 Months")
            
            # Update chart with default settings
            self.root.after(1000, self.update_chart)  # Delay to ensure UI is ready
            
        except Exception as e:
            logger.error(f"Error loading default chart: {e}")
            self.status_var.set("Failed to load default chart")
    
    def run(self):
        """Start the application"""
        try:
            self.root.mainloop()
        except KeyboardInterrupt:
            logger.info("Application interrupted by user")
            self.root.quit()

if __name__ == "__main__":
    # Check if required packages are available
    try:
        import mplfinance
        import matplotlib
    except ImportError:
        print("❌ Missing required packages: mplfinance, matplotlib")
        print("Install with: pip install mplfinance matplotlib")
        exit(1)
    
    app = ChartVisualizerGUI()
    app.run()