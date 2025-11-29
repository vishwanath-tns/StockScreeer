#!/usr/bin/env python3
"""
Price Cluster Analyzer
======================

Identifies price zones where stock spent the most time (high candle distribution).
These clusters often act as support/resistance levels.

Features:
- Analyze price distribution over configurable duration (1Y, 2Y, 5Y, etc.)
- Find clusters above and below current price
- Volume-weighted clustering for stronger levels
- Visual histogram of price distribution
- Export results to CSV

Algorithm:
1. Fetch historical data for the given duration
2. Divide price range into bins (configurable granularity)
3. Count candles in each bin (optionally weighted by volume)
4. Identify clusters (consecutive bins with high counts)
5. Rank clusters by strength (candle count * volume)

Usage:
    python analysis/price_cluster_analyzer.py

Author: StockScreener Project
Version: 1.0.0
Date: November 2025
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from datetime import datetime, date, timedelta
import threading
import sys
import os
import pandas as pd
import numpy as np
import logging
import mysql.connector
from mysql.connector import Error
from sqlalchemy import create_engine
from dataclasses import dataclass
from typing import List, Tuple, Optional

# Matplotlib for charting
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.patches import Rectangle
import mplfinance as mpf

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from utilities.nifty500_stocks_list import NIFTY_500_STOCKS

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# =============================================================================
# DATA MODELS
# =============================================================================

@dataclass
class PriceCluster:
    """Represents a price cluster/zone"""
    price_low: float
    price_high: float
    price_mid: float
    candle_count: int
    volume_sum: int
    strength: float  # Combined score
    pct_from_current: float  # Percentage from current price
    position: str  # 'above' or 'below'
    
    @property
    def price_range(self) -> str:
        return f"₹{self.price_low:.2f} - ₹{self.price_high:.2f}"


# =============================================================================
# DATABASE SERVICE
# =============================================================================

class ClusterDBService:
    """Database service for price cluster analysis"""
    
    def __init__(self):
        self.db_config = {
            'host': os.getenv('MYSQL_HOST', 'localhost'),
            'port': int(os.getenv('MYSQL_PORT', 3306)),
            'user': os.getenv('MYSQL_USER', 'root'),
            'password': os.getenv('MYSQL_PASSWORD', ''),
            'database': os.getenv('MYSQL_DATABASE', 'marketdata'),
            'charset': 'utf8mb4'
        }
        self._engine = None
    
    def get_engine(self):
        """Get SQLAlchemy engine"""
        if self._engine is None:
            from urllib.parse import quote_plus
            user = self.db_config['user']
            password = quote_plus(self.db_config['password']) if self.db_config['password'] else ''
            host = self.db_config['host']
            port = self.db_config['port']
            database = self.db_config['database']
            conn_str = f"mysql+mysqlconnector://{user}:{password}@{host}:{port}/{database}"
            self._engine = create_engine(conn_str)
        return self._engine
    
    def get_historical_data(self, symbol: str, start_date: date, end_date: date) -> pd.DataFrame:
        """Get historical OHLCV data for a symbol"""
        try:
            engine = self.get_engine()
            
            query = """
                SELECT date, open, high, low, close, volume
                FROM yfinance_daily_quotes
                WHERE symbol = %s AND date BETWEEN %s AND %s
                ORDER BY date
            """
            
            df = pd.read_sql(query, engine, params=(symbol, start_date, end_date))
            
            if not df.empty:
                df['date'] = pd.to_datetime(df['date'])
            
            return df
            
        except Exception as e:
            logger.error(f"Error fetching data for {symbol}: {e}")
            return pd.DataFrame()
    
    def get_current_price(self, symbol: str) -> Tuple[float, date]:
        """Get the most recent closing price for a symbol"""
        try:
            engine = self.get_engine()
            
            query = """
                SELECT close, date
                FROM yfinance_daily_quotes
                WHERE symbol = %s
                ORDER BY date DESC
                LIMIT 1
            """
            
            df = pd.read_sql(query, engine, params=(symbol,))
            
            if not df.empty:
                return float(df['close'].iloc[0]), df['date'].iloc[0]
            
            return None, None
            
        except Exception as e:
            logger.error(f"Error fetching current price for {symbol}: {e}")
            return None, None


# =============================================================================
# PRICE CLUSTER CALCULATOR
# =============================================================================

class PriceClusterCalculator:
    """Calculate price clusters from historical data"""
    
    def __init__(self, db_service: ClusterDBService):
        self.db_service = db_service
    
    def calculate_clusters(
        self,
        symbol: str,
        years: int = 5,
        num_bins: int = 50,
        min_cluster_strength: float = 0.05,
        volume_weighted: bool = True,
        merge_adjacent: bool = True
    ) -> Tuple[List[PriceCluster], float, pd.DataFrame]:
        """
        Calculate price clusters for a symbol.
        
        Args:
            symbol: Stock symbol with .NS suffix
            years: Number of years of history to analyze
            num_bins: Number of price bins to divide range into
            min_cluster_strength: Minimum relative strength to consider a cluster
            volume_weighted: Whether to weight by volume
            merge_adjacent: Whether to merge adjacent high-density bins
            
        Returns:
            Tuple of (clusters_list, current_price, histogram_data)
        """
        # Get date range
        end_date = date.today()
        start_date = end_date - timedelta(days=years * 365)
        
        # Fetch data
        df = self.db_service.get_historical_data(symbol, start_date, end_date)
        
        if df.empty or len(df) < 20:
            logger.warning(f"Insufficient data for {symbol}")
            return [], None, pd.DataFrame()
        
        # Get current price
        current_price, price_date = self.db_service.get_current_price(symbol)
        if current_price is None:
            current_price = float(df['close'].iloc[-1])
        
        # Calculate price range
        price_min = df['low'].min()
        price_max = df['high'].max()
        price_range = price_max - price_min
        bin_size = price_range / num_bins
        
        # Create bins
        bins = np.linspace(price_min, price_max, num_bins + 1)
        bin_centers = (bins[:-1] + bins[1:]) / 2
        
        # Count candles and volume in each bin
        bin_counts = np.zeros(num_bins)
        bin_volumes = np.zeros(num_bins)
        
        for _, row in df.iterrows():
            # A candle touches all bins between its low and high
            low, high = row['low'], row['high']
            volume = row['volume'] if pd.notna(row['volume']) else 0
            
            for i in range(num_bins):
                bin_low, bin_high = bins[i], bins[i + 1]
                
                # Check if candle overlaps with this bin
                if low <= bin_high and high >= bin_low:
                    bin_counts[i] += 1
                    bin_volumes[i] += volume
        
        # Calculate strength (normalized)
        if volume_weighted and bin_volumes.max() > 0:
            # Combine count and volume
            count_norm = bin_counts / bin_counts.max() if bin_counts.max() > 0 else bin_counts
            volume_norm = bin_volumes / bin_volumes.max() if bin_volumes.max() > 0 else bin_volumes
            strengths = (count_norm + volume_norm) / 2
        else:
            strengths = bin_counts / bin_counts.max() if bin_counts.max() > 0 else bin_counts
        
        # Create histogram dataframe
        hist_df = pd.DataFrame({
            'bin_low': bins[:-1],
            'bin_high': bins[1:],
            'bin_center': bin_centers,
            'candle_count': bin_counts.astype(int),
            'volume_sum': bin_volumes.astype(int),
            'strength': strengths
        })
        
        # Find clusters (bins above threshold)
        clusters = []
        threshold = min_cluster_strength
        
        if merge_adjacent:
            # Merge adjacent high-strength bins into clusters
            in_cluster = False
            cluster_start = 0
            
            for i in range(num_bins):
                if strengths[i] >= threshold:
                    if not in_cluster:
                        in_cluster = True
                        cluster_start = i
                else:
                    if in_cluster:
                        # End of cluster
                        cluster = self._create_cluster(
                            bins, bin_counts, bin_volumes, strengths,
                            cluster_start, i - 1, current_price
                        )
                        clusters.append(cluster)
                        in_cluster = False
            
            # Handle cluster at end
            if in_cluster:
                cluster = self._create_cluster(
                    bins, bin_counts, bin_volumes, strengths,
                    cluster_start, num_bins - 1, current_price
                )
                clusters.append(cluster)
        else:
            # Each bin above threshold is a separate cluster
            for i in range(num_bins):
                if strengths[i] >= threshold:
                    cluster = self._create_cluster(
                        bins, bin_counts, bin_volumes, strengths,
                        i, i, current_price
                    )
                    clusters.append(cluster)
        
        # Sort by strength
        clusters.sort(key=lambda c: c.strength, reverse=True)
        
        return clusters, current_price, hist_df
    
    def _create_cluster(
        self, bins, counts, volumes, strengths,
        start_idx: int, end_idx: int, current_price: float
    ) -> PriceCluster:
        """Create a PriceCluster from bin range"""
        price_low = bins[start_idx]
        price_high = bins[end_idx + 1]
        price_mid = (price_low + price_high) / 2
        
        candle_count = int(sum(counts[start_idx:end_idx + 1]))
        volume_sum = int(sum(volumes[start_idx:end_idx + 1]))
        strength = float(np.mean(strengths[start_idx:end_idx + 1]))
        
        pct_from_current = ((price_mid - current_price) / current_price) * 100
        position = 'above' if price_mid > current_price else 'below'
        
        return PriceCluster(
            price_low=float(price_low),
            price_high=float(price_high),
            price_mid=float(price_mid),
            candle_count=candle_count,
            volume_sum=volume_sum,
            strength=strength,
            pct_from_current=pct_from_current,
            position=position
        )


# =============================================================================
# GUI
# =============================================================================

class PriceClusterGUI:
    """Price Cluster Analysis GUI"""
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("📊 Price Cluster Analyzer")
        self.root.geometry("1100x800")
        
        # Initialize services
        self.db_service = ClusterDBService()
        self.calculator = PriceClusterCalculator(self.db_service)
        
        # State
        self.current_clusters = []
        self.current_histogram = None
        self.current_price = None
        self.current_symbol = None
        self.current_data = None  # Store historical OHLCV data for charting
        
        # Color scheme - Light theme
        self.colors = {
            'bg': '#f5f7fa',
            'card': '#ffffff',
            'accent': '#e8ecf1',
            'primary': '#2563eb',
            'text': '#0f172a',
            'secondary': '#334155',
            'success': '#16a34a',
            'warning': '#ea580c',
            'error': '#dc2626',
            'resistance': '#ef4444',  # Red for resistance (above)
            'support': '#22c55e',      # Green for support (below)
        }
        
        # Fonts
        self.fonts = {
            'title': ('Segoe UI', 18, 'bold'),
            'subtitle': ('Segoe UI', 12, 'bold'),
            'body': ('Segoe UI', 10, 'bold'),
            'small': ('Segoe UI', 9),
        }
        
        self.root.configure(bg=self.colors['bg'])
        self.setup_ui()
    
    def setup_ui(self):
        """Setup the user interface"""
        # Main container
        main_frame = tk.Frame(self.root, bg=self.colors['bg'])
        main_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=15)
        
        # Title
        self.setup_title(main_frame)
        
        # Settings panel
        self.setup_settings(main_frame)
        
        # Results panel (split into above/below)
        self.setup_results(main_frame)
        
        # Status bar
        self.setup_status_bar(main_frame)
    
    def setup_title(self, parent):
        """Setup title section"""
        title_frame = tk.Frame(parent, bg=self.colors['bg'])
        title_frame.pack(fill=tk.X, pady=(0, 10))
        
        title_label = tk.Label(
            title_frame,
            text="📊 Price Cluster Analyzer",
            font=self.fonts['title'],
            fg=self.colors['primary'],
            bg=self.colors['bg']
        )
        title_label.pack(side=tk.LEFT)
        
        subtitle = tk.Label(
            title_frame,
            text="Find support/resistance zones based on historical price distribution",
            font=self.fonts['small'],
            fg=self.colors['secondary'],
            bg=self.colors['bg']
        )
        subtitle.pack(side=tk.LEFT, padx=20)
    
    def setup_settings(self, parent):
        """Setup settings panel"""
        settings_card = tk.Frame(parent, bg=self.colors['card'], relief='flat')
        settings_card.pack(fill=tk.X, pady=10)
        
        inner = tk.Frame(settings_card, bg=self.colors['card'])
        inner.pack(fill=tk.X, padx=15, pady=15)
        
        # Row 1: Symbol and Duration
        row1 = tk.Frame(inner, bg=self.colors['card'])
        row1.pack(fill=tk.X, pady=5)
        
        # Symbol selection
        tk.Label(row1, text="Symbol:", font=self.fonts['body'],
                fg=self.colors['text'], bg=self.colors['card']).pack(side=tk.LEFT, padx=5)
        
        self.symbol_var = tk.StringVar(value="RELIANCE")
        symbols = NIFTY_500_STOCKS[:100]  # First 100 for dropdown
        self.symbol_combo = ttk.Combobox(
            row1, textvariable=self.symbol_var,
            values=symbols, width=15
        )
        self.symbol_combo.pack(side=tk.LEFT, padx=5)
        
        # Duration
        tk.Label(row1, text="Duration:", font=self.fonts['body'],
                fg=self.colors['text'], bg=self.colors['card']).pack(side=tk.LEFT, padx=(20, 5))
        
        self.duration_var = tk.StringVar(value="5 Years")
        duration_combo = ttk.Combobox(
            row1, textvariable=self.duration_var,
            values=["1 Year", "2 Years", "3 Years", "5 Years", "10 Years"],
            width=10, state='readonly'
        )
        duration_combo.pack(side=tk.LEFT, padx=5)
        
        # Number of bins
        tk.Label(row1, text="Price Zones:", font=self.fonts['body'],
                fg=self.colors['text'], bg=self.colors['card']).pack(side=tk.LEFT, padx=(20, 5))
        
        self.bins_var = tk.StringVar(value="100")
        bins_combo = ttk.Combobox(
            row1, textvariable=self.bins_var,
            values=["50", "75", "100", "150", "200"],
            width=8, state='readonly'
        )
        bins_combo.pack(side=tk.LEFT, padx=5)
        
        # Row 2: Options
        row2 = tk.Frame(inner, bg=self.colors['card'])
        row2.pack(fill=tk.X, pady=10)
        
        self.volume_weighted_var = tk.BooleanVar(value=True)
        tk.Checkbutton(
            row2, text="Volume Weighted",
            variable=self.volume_weighted_var,
            font=self.fonts['body'], fg=self.colors['text'], bg=self.colors['card'],
            selectcolor=self.colors['accent']
        ).pack(side=tk.LEFT, padx=10)
        
        self.merge_adjacent_var = tk.BooleanVar(value=False)
        tk.Checkbutton(
            row2, text="Merge Adjacent Zones",
            variable=self.merge_adjacent_var,
            font=self.fonts['body'], fg=self.colors['text'], bg=self.colors['card'],
            selectcolor=self.colors['accent']
        ).pack(side=tk.LEFT, padx=10)
        
        # Min strength slider
        tk.Label(row2, text="Min Strength:", font=self.fonts['body'],
                fg=self.colors['text'], bg=self.colors['card']).pack(side=tk.LEFT, padx=(20, 5))
        
        self.strength_var = tk.DoubleVar(value=0.5)
        strength_scale = tk.Scale(
            row2, from_=0.2, to=0.9, resolution=0.05,
            variable=self.strength_var, orient=tk.HORIZONTAL,
            length=150, bg=self.colors['card'], highlightthickness=0
        )
        strength_scale.pack(side=tk.LEFT, padx=5)
        
        # Analyze button
        self.analyze_btn = tk.Button(
            row2, text="🔍 Analyze Clusters",
            command=self.analyze_clusters,
            font=self.fonts['subtitle'], fg='#ffffff', bg=self.colors['primary'],
            activebackground='#1d4ed8', relief='flat', cursor='hand2', padx=20
        )
        self.analyze_btn.pack(side=tk.RIGHT, padx=10)
        
        # Show Chart button
        self.chart_btn = tk.Button(
            row2, text="📈 Show Chart",
            command=self.show_chart,
            font=self.fonts['body'], fg='#ffffff', bg=self.colors['success'],
            activebackground='#15803d', relief='flat', cursor='hand2', padx=15
        )
        self.chart_btn.pack(side=tk.RIGHT, padx=5)
        
        # Export button
        self.export_btn = tk.Button(
            row2, text="📥 Export CSV",
            command=self.export_csv,
            font=self.fonts['body'], fg=self.colors['text'], bg=self.colors['accent'],
            activebackground='#cbd5e1', relief='flat', cursor='hand2', padx=15
        )
        self.export_btn.pack(side=tk.RIGHT, padx=5)
    
    def setup_results(self, parent):
        """Setup results panel"""
        results_frame = tk.Frame(parent, bg=self.colors['bg'])
        results_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        # Current price display
        price_frame = tk.Frame(results_frame, bg=self.colors['card'])
        price_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.current_price_label = tk.Label(
            price_frame,
            text="Current Price: --",
            font=('Segoe UI', 14, 'bold'),
            fg=self.colors['primary'],
            bg=self.colors['card'],
            pady=10
        )
        self.current_price_label.pack()
        
        # Split view: Resistance (above) and Support (below)
        split_frame = tk.Frame(results_frame, bg=self.colors['bg'])
        split_frame.pack(fill=tk.BOTH, expand=True)
        split_frame.grid_columnconfigure(0, weight=1)
        split_frame.grid_columnconfigure(1, weight=1)
        split_frame.grid_rowconfigure(0, weight=1)
        
        # Resistance zones (above current price)
        resistance_frame = tk.LabelFrame(
            split_frame, text="🔴 Resistance Zones (Above Current Price)",
            font=self.fonts['subtitle'], fg=self.colors['resistance'], bg=self.colors['card']
        )
        resistance_frame.grid(row=0, column=0, sticky='nsew', padx=(0, 5), pady=5)
        
        self.resistance_tree = self._create_treeview(resistance_frame)
        
        # Support zones (below current price)
        support_frame = tk.LabelFrame(
            split_frame, text="🟢 Support Zones (Below Current Price)",
            font=self.fonts['subtitle'], fg=self.colors['support'], bg=self.colors['card']
        )
        support_frame.grid(row=0, column=1, sticky='nsew', padx=(5, 0), pady=5)
        
        self.support_tree = self._create_treeview(support_frame)
    
    def _create_treeview(self, parent) -> ttk.Treeview:
        """Create a treeview for cluster display"""
        # Columns
        columns = ('range', 'mid', 'pct', 'candles', 'strength')
        
        tree_frame = tk.Frame(parent, bg=self.colors['card'])
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(tree_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        tree = ttk.Treeview(
            tree_frame,
            columns=columns,
            show='headings',
            yscrollcommand=scrollbar.set,
            height=15
        )
        tree.pack(fill=tk.BOTH, expand=True)
        scrollbar.config(command=tree.yview)
        
        # Configure columns
        tree.heading('range', text='Price Range')
        tree.heading('mid', text='Mid Price')
        tree.heading('pct', text='% from CMP')
        tree.heading('candles', text='Candles')
        tree.heading('strength', text='Strength')
        
        tree.column('range', width=140, anchor='center')
        tree.column('mid', width=80, anchor='center')
        tree.column('pct', width=80, anchor='center')
        tree.column('candles', width=70, anchor='center')
        tree.column('strength', width=70, anchor='center')
        
        # Style
        style = ttk.Style()
        style.configure('Treeview',
                       background='#ffffff',
                       foreground='#0f172a',
                       fieldbackground='#ffffff',
                       rowheight=25,
                       font=('Segoe UI', 9, 'bold'))
        style.configure('Treeview.Heading',
                       background='#e2e8f0',
                       foreground='#1e3a8a',
                       font=('Segoe UI', 9, 'bold'))
        
        return tree
    
    def setup_status_bar(self, parent):
        """Setup status bar"""
        status_frame = tk.Frame(parent, bg=self.colors['accent'])
        status_frame.pack(fill=tk.X, pady=(10, 0))
        
        self.status_label = tk.Label(
            status_frame,
            text="Select a stock and click 'Analyze Clusters' to find price zones",
            font=self.fonts['small'],
            fg=self.colors['text'],
            bg=self.colors['accent'],
            pady=5
        )
        self.status_label.pack(side=tk.LEFT, padx=10)
    
    def get_duration_years(self) -> int:
        """Parse duration string to years"""
        duration = self.duration_var.get()
        return int(duration.split()[0])
    
    def analyze_clusters(self):
        """Analyze price clusters for selected symbol"""
        symbol = self.symbol_var.get().strip().upper()
        if not symbol:
            messagebox.showwarning("Warning", "Please enter a stock symbol")
            return
        
        # Add .NS suffix if not present
        if not symbol.endswith('.NS'):
            symbol = f"{symbol}.NS"
        
        self.analyze_btn.configure(state='disabled')
        self.status_label.configure(text=f"Analyzing {symbol}...")
        
        # Run in background thread
        thread = threading.Thread(target=self._analyze_worker, args=(symbol,))
        thread.daemon = True
        thread.start()
    
    def _analyze_worker(self, symbol: str):
        """Background worker for cluster analysis"""
        try:
            years = self.get_duration_years()
            num_bins = int(self.bins_var.get())
            min_strength = self.strength_var.get()
            volume_weighted = self.volume_weighted_var.get()
            merge_adjacent = self.merge_adjacent_var.get()
            
            clusters, current_price, histogram = self.calculator.calculate_clusters(
                symbol=symbol,
                years=years,
                num_bins=num_bins,
                min_cluster_strength=min_strength,
                volume_weighted=volume_weighted,
                merge_adjacent=merge_adjacent
            )
            
            # Also fetch historical data for charting
            end_date = date.today()
            start_date = end_date - timedelta(days=years * 365)
            historical_data = self.db_service.get_historical_data(symbol, start_date, end_date)
            
            self.current_clusters = clusters
            self.current_histogram = histogram
            self.current_price = current_price
            self.current_symbol = symbol
            self.current_data = historical_data
            
            # Update UI on main thread
            self.root.after(0, lambda: self._update_results(symbol, clusters, current_price))
            
        except Exception as e:
            logger.error(f"Error analyzing {symbol}: {e}")
            self.root.after(0, lambda: self.status_label.configure(
                text=f"Error: {e}"
            ))
        finally:
            self.root.after(0, lambda: self.analyze_btn.configure(state='normal'))
    
    def _update_results(self, symbol: str, clusters: List[PriceCluster], current_price: float):
        """Update results display"""
        # Update current price
        if current_price:
            self.current_price_label.configure(
                text=f"Current Price: ₹{current_price:.2f} ({symbol})"
            )
        
        # Clear existing items
        for item in self.resistance_tree.get_children():
            self.resistance_tree.delete(item)
        for item in self.support_tree.get_children():
            self.support_tree.delete(item)
        
        # Separate into above and below
        above_clusters = [c for c in clusters if c.position == 'above']
        below_clusters = [c for c in clusters if c.position == 'below']
        
        # Sort: above by distance (closest first), below by distance (closest first)
        above_clusters.sort(key=lambda c: c.pct_from_current)
        below_clusters.sort(key=lambda c: -c.pct_from_current)  # Negative, so reverse
        
        # Add to resistance tree
        for cluster in above_clusters:
            self.resistance_tree.insert('', 'end', values=(
                cluster.price_range,
                f"₹{cluster.price_mid:.2f}",
                f"+{cluster.pct_from_current:.1f}%",
                cluster.candle_count,
                f"{cluster.strength:.2f}"
            ))
        
        # Add to support tree
        for cluster in below_clusters:
            self.support_tree.insert('', 'end', values=(
                cluster.price_range,
                f"₹{cluster.price_mid:.2f}",
                f"{cluster.pct_from_current:.1f}%",
                cluster.candle_count,
                f"{cluster.strength:.2f}"
            ))
        
        # Update status
        self.status_label.configure(
            text=f"Found {len(above_clusters)} resistance zones and {len(below_clusters)} support zones"
        )
    
    def export_csv(self):
        """Export clusters to CSV"""
        if not self.current_clusters:
            messagebox.showinfo("Info", "No clusters to export. Run analysis first.")
            return
        
        filepath = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv")],
            initialfile=f"price_clusters_{self.symbol_var.get()}.csv"
        )
        
        if not filepath:
            return
        
        try:
            # Create dataframe
            data = []
            for c in self.current_clusters:
                data.append({
                    'Position': c.position.upper(),
                    'Price_Low': c.price_low,
                    'Price_High': c.price_high,
                    'Price_Mid': c.price_mid,
                    'Pct_From_Current': c.pct_from_current,
                    'Candle_Count': c.candle_count,
                    'Volume_Sum': c.volume_sum,
                    'Strength': c.strength
                })
            
            df = pd.DataFrame(data)
            df.to_csv(filepath, index=False)
            
            messagebox.showinfo("Success", f"Exported {len(data)} clusters to {filepath}")
            
        except Exception as e:
            messagebox.showerror("Error", f"Export failed: {e}")
    
    def show_chart(self):
        """Show candlestick chart with price zones marked"""
        if self.current_data is None or self.current_data.empty:
            messagebox.showinfo("Info", "No data available. Run analysis first.")
            return
        
        if not self.current_clusters:
            messagebox.showinfo("Info", "No clusters found. Run analysis first.")
            return
        
        # Create chart window
        chart_window = tk.Toplevel(self.root)
        chart_window.title(f"📈 {self.current_symbol} - Price Clusters Chart")
        chart_window.geometry("1400x900")
        chart_window.configure(bg='#ffffff')
        
        # Prepare data for mplfinance
        df = self.current_data.copy()
        df['date'] = pd.to_datetime(df['date'])
        df.set_index('date', inplace=True)
        df.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
        
        # Limit to last 1 year for clarity (or user-selected duration)
        chart_days = min(365, len(df))
        df_chart = df.tail(chart_days)
        
        # Create sequential x indices (removes weekend gaps)
        x_indices = np.arange(len(df_chart))
        
        # Create figure
        fig, axes = plt.subplots(2, 1, figsize=(14, 9), height_ratios=[3, 1], 
                                  gridspec_kw={'hspace': 0.05})
        
        # Main price axis
        ax_price = axes[0]
        ax_volume = axes[1]
        
        # Plot candlesticks with sequential x-axis
        self._plot_candlesticks(ax_price, df_chart, x_indices)
        
        # Draw price zones
        self._draw_zones(ax_price, df_chart, x_indices)
        
        # Plot volume
        self._plot_volume(ax_volume, df_chart, x_indices)
        
        # Setup x-axis labels (show dates at intervals)
        self._setup_xaxis(ax_price, ax_volume, df_chart, x_indices)
        
        # Style the chart
        ax_price.set_title(f"{self.current_symbol} - Price Clusters (Last {chart_days} days)", 
                          fontsize=14, fontweight='bold', pad=10)
        ax_price.set_ylabel("Price (₹)", fontsize=10)
        ax_price.grid(True, alpha=0.3, linestyle='--')
        ax_price.set_facecolor('#fafafa')
        
        ax_volume.set_ylabel("Volume", fontsize=10)
        ax_volume.grid(True, alpha=0.3, linestyle='--')
        ax_volume.set_facecolor('#fafafa')
        
        # Add current price line
        if self.current_price:
            ax_price.axhline(y=self.current_price, color='#2563eb', linestyle='-', 
                           linewidth=2, label=f'Current: ₹{self.current_price:.2f}')
        
        # Add legend
        self._add_legend(ax_price)
        
        fig.subplots_adjust(left=0.08, right=0.88, top=0.95, bottom=0.1, hspace=0.05)
        
        # Embed in tkinter
        canvas = FigureCanvasTkAgg(fig, master=chart_window)
        canvas.draw()
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Add toolbar
        toolbar_frame = tk.Frame(chart_window)
        toolbar_frame.pack(fill=tk.X)
        toolbar = NavigationToolbar2Tk(canvas, toolbar_frame)
        toolbar.update()
        
        # Duration selector for chart
        control_frame = tk.Frame(chart_window, bg='#f0f0f0')
        control_frame.pack(fill=tk.X, padx=10, pady=5)
        
        tk.Label(control_frame, text="Chart Duration:", bg='#f0f0f0', 
                font=('Segoe UI', 10, 'bold')).pack(side=tk.LEFT, padx=5)
        
        chart_duration_var = tk.StringVar(value="1 Year")
        duration_combo = ttk.Combobox(
            control_frame, textvariable=chart_duration_var,
            values=["3 Months", "6 Months", "1 Year", "2 Years", "3 Years", "5 Years", "All Data"],
            width=12, state='readonly'
        )
        duration_combo.pack(side=tk.LEFT, padx=5)
        
        def update_chart():
            """Update chart with new duration"""
            duration_map = {
                "3 Months": 90, "6 Months": 180,
                "1 Year": 365, "2 Years": 730, "3 Years": 1095,
                "5 Years": 1825, "All Data": len(df)
            }
            days = duration_map.get(chart_duration_var.get(), 365)
            df_new = df.tail(min(days, len(df)))
            x_new = np.arange(len(df_new))
            
            ax_price.clear()
            ax_volume.clear()
            
            self._plot_candlesticks(ax_price, df_new, x_new)
            self._draw_zones(ax_price, df_new, x_new)
            self._plot_volume(ax_volume, df_new, x_new)
            self._setup_xaxis(ax_price, ax_volume, df_new, x_new)
            
            ax_price.set_title(f"{self.current_symbol} - Price Clusters (Last {len(df_new)} days)",
                              fontsize=14, fontweight='bold', pad=10)
            ax_price.set_ylabel("Price (₹)", fontsize=10)
            ax_price.grid(True, alpha=0.3, linestyle='--')
            ax_price.set_facecolor('#fafafa')
            
            if self.current_price:
                ax_price.axhline(y=self.current_price, color='#2563eb', linestyle='-',
                               linewidth=2, label=f'Current: ₹{self.current_price:.2f}')
            
            self._add_legend(ax_price)
            
            ax_volume.set_ylabel("Volume", fontsize=10)
            ax_volume.grid(True, alpha=0.3, linestyle='--')
            ax_volume.set_facecolor('#fafafa')
            
            canvas.draw()
        
        update_btn = tk.Button(control_frame, text="Update", command=update_chart,
                              bg='#2563eb', fg='white', font=('Segoe UI', 9, 'bold'))
        update_btn.pack(side=tk.LEFT, padx=10)
        
        # Zone legend
        zone_legend = tk.Label(
            control_frame,
            text="🔴 Resistance Zones (Above) | 🟢 Support Zones (Below) | 🔵 Current Price",
            bg='#f0f0f0', font=('Segoe UI', 9)
        )
        zone_legend.pack(side=tk.RIGHT, padx=10)
    
    def _plot_candlesticks(self, ax, df, x_indices=None):
        """Plot candlestick chart with sequential x-axis (no weekend gaps)"""
        if x_indices is None:
            x_indices = np.arange(len(df))
        
        width = 0.6
        width2 = 0.1
        
        # Up candles (green)
        up_color = '#22c55e'
        down_color = '#ef4444'
        
        for i, (idx, row) in enumerate(df.iterrows()):
            x = x_indices[i]
            o, h, l, c = row['Open'], row['High'], row['Low'], row['Close']
            
            color = up_color if c >= o else down_color
            
            # Body
            body_bottom = min(o, c)
            body_height = abs(c - o)
            if body_height < 0.001:  # Doji - make it visible
                body_height = (h - l) * 0.02
            
            ax.bar(x, body_height, width, bottom=body_bottom, color=color, edgecolor=color)
            
            # Upper wick
            ax.bar(x, h - max(o, c), width2, bottom=max(o, c), color=color, edgecolor=color)
            
            # Lower wick
            ax.bar(x, min(o, c) - l, width2, bottom=l, color=color, edgecolor=color)
    
    def _draw_zones(self, ax, df, x_indices=None):
        """Draw price cluster zones on chart using sequential x-axis"""
        if x_indices is None:
            x_indices = np.arange(len(df))
        
        x_start = x_indices[0] - 0.5
        x_end = x_indices[-1] + 0.5
        x_width = x_end - x_start
        
        # Get chart price range
        chart_low = df['Low'].min()
        chart_high = df['High'].max()
        chart_range = chart_high - chart_low
        
        # Collect zones to plot and track y-axis extension needed
        zones_to_plot = []
        
        # Draw resistance zones (above current price) - closest 5
        resistance_clusters = [c for c in self.current_clusters if c.position == 'above']
        resistance_clusters.sort(key=lambda c: c.pct_from_current)  # Closest first
        for cluster in resistance_clusters[:5]:
            zones_to_plot.append(('resistance', cluster))
        
        # Draw support zones (below current price) - closest 5
        support_clusters = [c for c in self.current_clusters if c.position == 'below']
        support_clusters.sort(key=lambda c: -c.pct_from_current)  # Closest first (least negative)
        for cluster in support_clusters[:5]:
            zones_to_plot.append(('support', cluster))
        
        # Calculate required y-axis range to show all zones
        if zones_to_plot:
            all_zone_lows = [c.price_low for _, c in zones_to_plot]
            all_zone_highs = [c.price_high for _, c in zones_to_plot]
            
            # Extend y-axis to include zones with some padding
            y_min = min(chart_low, min(all_zone_lows)) * 0.98
            y_max = max(chart_high, max(all_zone_highs)) * 1.02
            ax.set_ylim(y_min, y_max)
        
        # Now plot all zones
        for zone_type, cluster in zones_to_plot:
            if zone_type == 'resistance':
                alpha = min(0.4, 0.2 + cluster.strength * 0.3)
                rect = Rectangle(
                    (x_start, cluster.price_low),
                    x_width,
                    cluster.price_high - cluster.price_low,
                    linewidth=1.5, edgecolor='#ef4444', facecolor='#fecaca',
                    alpha=alpha, linestyle='--', zorder=1
                )
                ax.add_patch(rect)
                # Add label at right edge
                ax.text(x_end + 1, cluster.price_mid, 
                       f'R: ₹{cluster.price_mid:.0f}', 
                       fontsize=8, color='#dc2626', va='center',
                       fontweight='bold', alpha=0.9)
            else:  # support
                alpha = min(0.4, 0.2 + cluster.strength * 0.3)
                rect = Rectangle(
                    (x_start, cluster.price_low),
                    x_width,
                    cluster.price_high - cluster.price_low,
                    linewidth=1.5, edgecolor='#22c55e', facecolor='#bbf7d0',
                    alpha=alpha, linestyle='--', zorder=1
                )
                ax.add_patch(rect)
                # Add label at right edge
                ax.text(x_end + 1, cluster.price_mid,
                       f'S: ₹{cluster.price_mid:.0f}',
                       fontsize=8, color='#16a34a', va='center',
                       fontweight='bold', alpha=0.9)
    
    def _plot_volume(self, ax, df, x_indices=None):
        """Plot volume bars with sequential x-axis"""
        if x_indices is None:
            x_indices = np.arange(len(df))
        
        colors = ['#22c55e' if c >= o else '#ef4444' 
                  for c, o in zip(df['Close'], df['Open'])]
        ax.bar(x_indices, df['Volume'].values, color=colors, alpha=0.7, width=0.8)
        
        # Format y-axis for volume
        ax.yaxis.set_major_formatter(plt.FuncFormatter(
            lambda x, p: f'{x/1e6:.1f}M' if x >= 1e6 else f'{x/1e3:.0f}K'
        ))
    
    def _setup_xaxis(self, ax_price, ax_volume, df, x_indices):
        """Setup x-axis with date labels at appropriate intervals"""
        n = len(df)
        
        # Determine number of labels based on data length
        if n <= 30:
            step = 5
        elif n <= 90:
            step = 10
        elif n <= 180:
            step = 20
        elif n <= 365:
            step = 30
        else:
            step = 60
        
        # Create tick positions and labels
        tick_positions = list(range(0, n, step))
        if n - 1 not in tick_positions:
            tick_positions.append(n - 1)  # Always show last date
        
        tick_labels = [df.index[i].strftime('%d-%b-%y') for i in tick_positions]
        
        # Hide x-axis labels on price chart, show on volume
        ax_price.set_xticks(tick_positions)
        ax_price.set_xticklabels([])
        
        ax_volume.set_xticks(tick_positions)
        ax_volume.set_xticklabels(tick_labels, rotation=45, ha='right', fontsize=8)
        ax_volume.set_xlabel("Date", fontsize=10)
        
        # Set x-axis limits
        ax_price.set_xlim(-1, n)
        ax_volume.set_xlim(-1, n)
    
    def _add_legend(self, ax):
        """Add custom legend for zones"""
        from matplotlib.patches import Patch
        from matplotlib.lines import Line2D
        
        legend_elements = [
            Patch(facecolor='#fecaca', edgecolor='#ef4444', alpha=0.4, 
                  linestyle='--', label='Resistance Zone'),
            Patch(facecolor='#bbf7d0', edgecolor='#22c55e', alpha=0.4,
                  linestyle='--', label='Support Zone'),
            Line2D([0], [0], color='#2563eb', linewidth=2, label='Current Price')
        ]
        ax.legend(handles=legend_elements, loc='upper left', fontsize=8)
    
    def run(self):
        """Start the GUI"""
        self.root.mainloop()


# =============================================================================
# MAIN
# =============================================================================

def main():
    """Main entry point"""
    app = PriceClusterGUI()
    app.run()


if __name__ == "__main__":
    main()
