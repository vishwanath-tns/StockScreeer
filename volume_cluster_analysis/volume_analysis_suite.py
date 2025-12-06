#!/usr/bin/env python3
"""
Volume Cluster Analysis - Enhanced GUI
======================================
Comprehensive GUI with:
- Stock Events Tab: View historical volume events for any stock
- Scanner Tab: Find recent high volume events across all stocks
- Alerts Tab: Monitor and manage volume alerts
- Patterns Tab: Analyze volume-price pattern performance
"""

import tkinter as tk
from tkinter import ttk, messagebox
import pandas as pd
import numpy as np
from sqlalchemy import create_engine, text
from urllib.parse import quote_plus
import os
from dotenv import load_dotenv
import matplotlib
matplotlib.use('TkAgg')
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
from datetime import datetime, timedelta
import threading

# Import our modules
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from scanner import VolumeEventScanner
from alerts import VolumeAlertSystem
from pattern_analyzer import VolumePatternAnalyzer


class VolumeAnalysisGUI:
    """Enhanced Volume Analysis GUI with multiple tabs."""
    
    def __init__(self, root):
        self.root = root
        self.root.title("📊 Volume Cluster Analysis Suite")
        self.root.geometry("1500x950")
        
        load_dotenv()
        self.engine = self._create_engine()
        
        # Initialize components
        self.scanner = VolumeEventScanner()
        self.alert_system = VolumeAlertSystem()
        self.pattern_analyzer = VolumePatternAnalyzer()
        
        self._create_ui()
        
        # Auto-refresh alerts
        self._start_alert_check()
    
    def _create_engine(self):
        password = quote_plus(os.getenv('MYSQL_PASSWORD', ''))
        host = os.getenv('MYSQL_HOST', 'localhost')
        port = os.getenv('MYSQL_PORT', '3306')
        db = os.getenv('MYSQL_DB', 'marketdata')
        user = os.getenv('MYSQL_USER', 'root')
        return create_engine(f'mysql+pymysql://{user}:{password}@{host}:{port}/{db}')
    
    def _create_ui(self):
        """Create the main UI with notebook tabs."""
        
        # Status bar at top
        self.status_frame = ttk.Frame(self.root)
        self.status_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self.status_label = ttk.Label(self.status_frame, text="Ready", font=('Arial', 10))
        self.status_label.pack(side=tk.LEFT)
        
        self.alert_badge = ttk.Label(self.status_frame, text="", font=('Arial', 10, 'bold'), foreground='red')
        self.alert_badge.pack(side=tk.RIGHT, padx=10)
        
        # Main notebook
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # Create tabs
        self._create_scanner_tab()
        self._create_stock_events_tab()
        self._create_alerts_tab()
        self._create_patterns_tab()
        
        # Load initial data
        self._load_scanner_data()
    
    # =========================================================================
    # SCANNER TAB
    # =========================================================================
    
    def _create_scanner_tab(self):
        """Create the scanner tab for finding recent high volume events."""
        self.scanner_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.scanner_tab, text="🔍 Scanner")
        
        # Controls
        control_frame = ttk.Frame(self.scanner_tab)
        control_frame.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Label(control_frame, text="Look Back:").pack(side=tk.LEFT, padx=5)
        self.scanner_days_var = tk.StringVar(value="5")
        days_combo = ttk.Combobox(control_frame, textvariable=self.scanner_days_var,
                                   values=["3", "5", "10", "20"], width=5, state='readonly')
        days_combo.pack(side=tk.LEFT, padx=5)
        
        ttk.Label(control_frame, text="Filter:").pack(side=tk.LEFT, padx=(20, 5))
        self.scanner_filter_var = tk.StringVar(value="All")
        filter_combo = ttk.Combobox(control_frame, textvariable=self.scanner_filter_var,
                                     values=["All", "Breakouts", "Breakdowns", "Volume Leaders"],
                                     width=15, state='readonly')
        filter_combo.pack(side=tk.LEFT, padx=5)
        
        ttk.Button(control_frame, text="🔄 Scan", command=self._load_scanner_data).pack(side=tk.LEFT, padx=20)
        
        self.scanner_count_label = ttk.Label(control_frame, text="", font=('Arial', 10))
        self.scanner_count_label.pack(side=tk.RIGHT, padx=10)
        
        # Results pane
        paned = ttk.PanedWindow(self.scanner_tab, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # Left: Table
        left_frame = ttk.Frame(paned)
        paned.add(left_frame, weight=1)
        
        columns = ('symbol', 'date', 'pattern', 'day_ret', 'rel_vol', 'since', 'ret_since')
        self.scanner_tree = ttk.Treeview(left_frame, columns=columns, show='headings', height=25)
        
        self.scanner_tree.heading('symbol', text='Symbol')
        self.scanner_tree.heading('date', text='Date')
        self.scanner_tree.heading('pattern', text='Pattern')
        self.scanner_tree.heading('day_ret', text='Day %')
        self.scanner_tree.heading('rel_vol', text='Rel Vol')
        self.scanner_tree.heading('since', text='Days')
        self.scanner_tree.heading('ret_since', text='Return')
        
        self.scanner_tree.column('symbol', width=100)
        self.scanner_tree.column('date', width=90)
        self.scanner_tree.column('pattern', width=100)
        self.scanner_tree.column('day_ret', width=70)
        self.scanner_tree.column('rel_vol', width=70)
        self.scanner_tree.column('since', width=50)
        self.scanner_tree.column('ret_since', width=70)
        
        scrollbar = ttk.Scrollbar(left_frame, orient=tk.VERTICAL, command=self.scanner_tree.yview)
        self.scanner_tree.configure(yscrollcommand=scrollbar.set)
        
        self.scanner_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Double-click to open chart
        self.scanner_tree.bind('<Double-1>', self._on_scanner_double_click)
        
        # Configure tags for coloring
        self.scanner_tree.tag_configure('breakout', background='#C8E6C9')
        self.scanner_tree.tag_configure('breakdown', background='#FFCDD2')
        self.scanner_tree.tag_configure('gap_up', background='#E8F5E9')
        self.scanner_tree.tag_configure('gap_down', background='#FFEBEE')
        
        # Right: Pattern stats summary
        right_frame = ttk.LabelFrame(paned, text="Pattern Statistics")
        paned.add(right_frame, weight=1)
        
        self.scanner_fig = Figure(figsize=(6, 8), dpi=100)
        self.scanner_canvas = FigureCanvasTkAgg(self.scanner_fig, master=right_frame)
        self.scanner_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
    
    def _load_scanner_data(self):
        """Load scanner data based on filters."""
        self.status_label.config(text="Scanning...")
        self.root.update()
        
        days = int(self.scanner_days_var.get())
        filter_type = self.scanner_filter_var.get()
        
        try:
            if filter_type == "Breakouts":
                events = self.scanner.scan_breakouts(days=days)
            elif filter_type == "Breakdowns":
                events = self.scanner.scan_breakdowns(days=days)
            elif filter_type == "Volume Leaders":
                events = self.scanner.get_volume_leaders(days=days)
            else:
                events = self.scanner.scan_recent_events(days=days)
            
            # Clear tree
            for item in self.scanner_tree.get_children():
                self.scanner_tree.delete(item)
            
            # Populate
            for e in events:
                ret_str = f"{e.return_since_event:+.1f}%" if e.return_since_event else "N/A"
                
                values = (
                    e.symbol,
                    str(e.event_date)[:10],
                    e.pattern.replace('_', ' ').title(),
                    f"{e.day_return:+.1f}%",
                    f"{e.relative_volume:.1f}x",
                    f"{e.days_since_event}d",
                    ret_str
                )
                
                tag = e.pattern if e.pattern in ['breakout', 'breakdown', 'gap_up', 'gap_down'] else ''
                self.scanner_tree.insert('', tk.END, values=values, tags=(tag,))
            
            self.scanner_count_label.config(text=f"{len(events)} events found")
            
            # Update chart
            self._update_scanner_chart(events)
            
            self.status_label.config(text="Ready")
            
        except Exception as e:
            messagebox.showerror("Error", f"Scanner error: {e}")
            self.status_label.config(text="Error")
    
    def _update_scanner_chart(self, events):
        """Update scanner summary chart."""
        self.scanner_fig.clear()
        
        if not events:
            return
        
        # Pattern distribution
        ax1 = self.scanner_fig.add_subplot(2, 1, 1)
        patterns = [e.pattern for e in events]
        pattern_counts = pd.Series(patterns).value_counts()
        
        colors = {
            'breakout': '#4CAF50', 'breakdown': '#F44336',
            'gap_up': '#8BC34A', 'gap_down': '#E57373',
            'neutral': '#9E9E9E'
        }
        bar_colors = [colors.get(p, '#9E9E9E') for p in pattern_counts.index]
        
        ax1.barh(pattern_counts.index, pattern_counts.values, color=bar_colors)
        ax1.set_xlabel('Count')
        ax1.set_title('Pattern Distribution')
        
        # Returns since event
        ax2 = self.scanner_fig.add_subplot(2, 1, 2)
        returns = [e.return_since_event for e in events if e.return_since_event is not None]
        
        if returns:
            ax2.hist(returns, bins=20, color='steelblue', edgecolor='black', alpha=0.7)
            ax2.axvline(x=0, color='red', linestyle='--', linewidth=1)
            ax2.axvline(x=np.mean(returns), color='green', linestyle='-', linewidth=2,
                       label=f'Mean: {np.mean(returns):.1f}%')
            ax2.set_xlabel('Return Since Event (%)')
            ax2.set_ylabel('Frequency')
            ax2.set_title('Returns Since High Volume Event')
            ax2.legend()
        
        self.scanner_fig.tight_layout()
        self.scanner_canvas.draw()
    
    # =========================================================================
    # STOCK EVENTS TAB
    # =========================================================================
    
    def _create_stock_events_tab(self):
        """Create tab for viewing individual stock events."""
        self.events_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.events_tab, text="📈 Stock Events")
        
        # Controls
        control_frame = ttk.Frame(self.events_tab)
        control_frame.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Label(control_frame, text="Symbol:").pack(side=tk.LEFT, padx=5)
        
        symbols = self._load_symbols()
        self.stock_symbol_var = tk.StringVar(value=symbols[0] if symbols else "")
        symbol_combo = ttk.Combobox(control_frame, textvariable=self.stock_symbol_var,
                                     values=symbols, width=20, state='readonly')
        symbol_combo.pack(side=tk.LEFT, padx=5)
        symbol_combo.bind('<<ComboboxSelected>>', lambda e: self._load_stock_events())
        
        ttk.Label(control_frame, text="Quintile:").pack(side=tk.LEFT, padx=(20, 5))
        self.stock_quintile_var = tk.StringVar(value="Ultra High")
        quintile_combo = ttk.Combobox(control_frame, textvariable=self.stock_quintile_var,
                                       values=["All", "High", "Very High", "Ultra High"], width=12, state='readonly')
        quintile_combo.pack(side=tk.LEFT, padx=5)
        quintile_combo.bind('<<ComboboxSelected>>', lambda e: self._load_stock_events())
        
        ttk.Button(control_frame, text="Load", command=self._load_stock_events).pack(side=tk.LEFT, padx=20)
        
        self.stock_stats_label = ttk.Label(control_frame, text="", font=('Arial', 10))
        self.stock_stats_label.pack(side=tk.RIGHT, padx=10)
        
        # Main content
        paned = ttk.PanedWindow(self.events_tab, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # Left: Table
        left_frame = ttk.Frame(paned)
        paned.add(left_frame, weight=1)
        
        columns = ('date', 'volume', 'quintile', 'day_ret', '1d', '1w', '2w', '1m')
        self.stock_tree = ttk.Treeview(left_frame, columns=columns, show='headings', height=20)
        
        for col, width in [('date', 90), ('volume', 100), ('quintile', 80), ('day_ret', 60),
                           ('1d', 60), ('1w', 60), ('2w', 60), ('1m', 60)]:
            self.stock_tree.heading(col, text=col.upper())
            self.stock_tree.column(col, width=width)
        
        scrollbar = ttk.Scrollbar(left_frame, orient=tk.VERTICAL, command=self.stock_tree.yview)
        self.stock_tree.configure(yscrollcommand=scrollbar.set)
        
        self.stock_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Configure tags
        self.stock_tree.tag_configure('very_positive', background='#81C784')
        self.stock_tree.tag_configure('positive', background='#C8E6C9')
        self.stock_tree.tag_configure('negative', background='#FFCDD2')
        self.stock_tree.tag_configure('very_negative', background='#E57373')
        
        # Right: Charts
        right_frame = ttk.Frame(paned)
        paned.add(right_frame, weight=2)
        
        self.stock_fig = Figure(figsize=(10, 8), dpi=100)
        self.stock_canvas = FigureCanvasTkAgg(self.stock_fig, master=right_frame)
        self.stock_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
        # Load initial
        if symbols:
            self._load_stock_events()
    
    def _load_symbols(self):
        """Load available symbols."""
        query = "SELECT DISTINCT symbol FROM volume_cluster_events ORDER BY symbol"
        with self.engine.connect() as conn:
            result = conn.execute(text(query))
            return [row[0] for row in result]
    
    def _load_stock_events(self):
        """Load events for selected stock."""
        symbol = self.stock_symbol_var.get()
        quintile = self.stock_quintile_var.get()
        
        if not symbol:
            return
        
        query = "SELECT * FROM volume_cluster_events WHERE symbol = :symbol"
        params = {'symbol': symbol}
        
        if quintile != "All":
            query += " AND volume_quintile = :quintile"
            params['quintile'] = quintile
        
        query += " ORDER BY event_date DESC"
        
        with self.engine.connect() as conn:
            df = pd.read_sql(text(query), conn, params=params)
        
        # Clear and populate tree
        for item in self.stock_tree.get_children():
            self.stock_tree.delete(item)
        
        for _, row in df.iterrows():
            def fmt(val):
                return f"{val:+.1f}" if pd.notna(val) else ""
            
            values = (
                str(row['event_date'])[:10],
                f"{row['volume']:,.0f}",
                row['volume_quintile'],
                fmt(row['day_return']),
                fmt(row['return_1d']),
                fmt(row['return_1w']),
                fmt(row['return_2w']),
                fmt(row['return_1m']),
            )
            
            tag = ''
            if pd.notna(row['return_1m']):
                if row['return_1m'] > 5:
                    tag = 'very_positive'
                elif row['return_1m'] > 0:
                    tag = 'positive'
                elif row['return_1m'] < -5:
                    tag = 'very_negative'
                else:
                    tag = 'negative'
            
            self.stock_tree.insert('', tk.END, values=values, tags=(tag,))
        
        self.stock_stats_label.config(text=f"{len(df)} events")
        
        # Update charts
        self._update_stock_charts(df, symbol)
    
    def _update_stock_charts(self, df, symbol):
        """Update stock event charts."""
        self.stock_fig.clear()
        
        if df.empty:
            return
        
        # 1-month return distribution
        ax1 = self.stock_fig.add_subplot(2, 2, 1)
        returns = df['return_1m'].dropna()
        if len(returns) > 0:
            ax1.hist(returns, bins=25, color='steelblue', edgecolor='black', alpha=0.7)
            ax1.axvline(x=0, color='red', linestyle='--')
            ax1.axvline(x=returns.mean(), color='green', linestyle='-', 
                       label=f'Mean: {returns.mean():.1f}%')
            ax1.set_xlabel('1-Month Return (%)')
            ax1.set_title(f'{symbol} - Return Distribution')
            ax1.legend()
        
        # Box plot by period
        ax2 = self.stock_fig.add_subplot(2, 2, 2)
        periods = ['return_1d', 'return_1w', 'return_2w', 'return_1m']
        data = [df[p].dropna() for p in periods]
        bp = ax2.boxplot(data, labels=['1D', '1W', '2W', '1M'], patch_artist=True)
        for patch in bp['boxes']:
            patch.set_facecolor('lightblue')
        ax2.axhline(y=0, color='red', linestyle='--')
        ax2.set_ylabel('Return (%)')
        ax2.set_title('Return by Period')
        
        # Win rate by period
        ax3 = self.stock_fig.add_subplot(2, 2, 3)
        win_rates = []
        for p in periods:
            valid = df[p].dropna()
            wr = (valid > 0).mean() * 100 if len(valid) > 0 else 0
            win_rates.append(wr)
        
        colors = ['green' if w > 50 else 'red' for w in win_rates]
        bars = ax3.bar(['1D', '1W', '2W', '1M'], win_rates, color=colors, alpha=0.7)
        ax3.axhline(y=50, color='black', linestyle='--')
        ax3.set_ylabel('Win Rate (%)')
        ax3.set_title('Win Rate by Period')
        ax3.set_ylim(0, 100)
        
        for bar, rate in zip(bars, win_rates):
            ax3.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1,
                    f'{rate:.0f}%', ha='center', fontsize=9)
        
        # Timeline
        ax4 = self.stock_fig.add_subplot(2, 2, 4)
        df_sorted = df.sort_values('event_date')
        dates = pd.to_datetime(df_sorted['event_date'])
        returns_1m = df_sorted['return_1m']
        
        colors = ['green' if r > 0 else 'red' for r in returns_1m.fillna(0)]
        ax4.scatter(dates, returns_1m, c=colors, alpha=0.6, edgecolors='black', linewidth=0.5)
        ax4.axhline(y=0, color='gray', linestyle='--')
        ax4.set_xlabel('Date')
        ax4.set_ylabel('1M Return (%)')
        ax4.set_title('Events Timeline')
        ax4.tick_params(axis='x', rotation=45)
        
        self.stock_fig.tight_layout()
        self.stock_canvas.draw()
    
    # =========================================================================
    # ALERTS TAB
    # =========================================================================
    
    def _create_alerts_tab(self):
        """Create alerts monitoring tab."""
        self.alerts_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.alerts_tab, text="🔔 Alerts")
        
        # Controls
        control_frame = ttk.Frame(self.alerts_tab)
        control_frame.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Button(control_frame, text="🔄 Check Alerts", command=self._check_alerts).pack(side=tk.LEFT, padx=5)
        ttk.Button(control_frame, text="✓ Acknowledge All", command=self._ack_all_alerts).pack(side=tk.LEFT, padx=5)
        ttk.Button(control_frame, text="🗑️ Clear Old", command=self._clear_old_alerts).pack(side=tk.LEFT, padx=5)
        
        self.alert_summary_label = ttk.Label(control_frame, text="", font=('Arial', 10))
        self.alert_summary_label.pack(side=tk.RIGHT, padx=10)
        
        # Main content
        paned = ttk.PanedWindow(self.alerts_tab, orient=tk.VERTICAL)
        paned.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # Top: Alert list
        top_frame = ttk.LabelFrame(paned, text="Volume Alerts")
        paned.add(top_frame, weight=2)
        
        columns = ('priority', 'symbol', 'date', 'type', 'rel_vol', 'return', 'message')
        self.alerts_tree = ttk.Treeview(top_frame, columns=columns, show='headings', height=15)
        
        self.alerts_tree.heading('priority', text='⚠')
        self.alerts_tree.heading('symbol', text='Symbol')
        self.alerts_tree.heading('date', text='Date')
        self.alerts_tree.heading('type', text='Type')
        self.alerts_tree.heading('rel_vol', text='Rel Vol')
        self.alerts_tree.heading('return', text='Day %')
        self.alerts_tree.heading('message', text='Message')
        
        self.alerts_tree.column('priority', width=30)
        self.alerts_tree.column('symbol', width=100)
        self.alerts_tree.column('date', width=90)
        self.alerts_tree.column('type', width=100)
        self.alerts_tree.column('rel_vol', width=70)
        self.alerts_tree.column('return', width=70)
        self.alerts_tree.column('message', width=400)
        
        scrollbar = ttk.Scrollbar(top_frame, orient=tk.VERTICAL, command=self.alerts_tree.yview)
        self.alerts_tree.configure(yscrollcommand=scrollbar.set)
        
        self.alerts_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.alerts_tree.tag_configure('critical', background='#FFCDD2')
        self.alerts_tree.tag_configure('high', background='#FFE0B2')
        self.alerts_tree.tag_configure('medium', background='#FFF9C4')
        
        # Bottom: Summary stats
        bottom_frame = ttk.LabelFrame(paned, text="Alert Statistics")
        paned.add(bottom_frame, weight=1)
        
        self.alerts_stats_text = tk.Text(bottom_frame, height=8, font=('Courier', 10))
        self.alerts_stats_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Initial load
        self._load_alerts()
    
    def _load_alerts(self):
        """Load and display alerts."""
        alerts = self.alert_system.get_recent_alerts(days=7)
        
        # Clear tree
        for item in self.alerts_tree.get_children():
            self.alerts_tree.delete(item)
        
        priority_icons = {'critical': '🔴', 'high': '🟠', 'medium': '🟡', 'low': '🟢'}
        
        for alert in alerts:
            values = (
                priority_icons.get(alert.priority, '⚪'),
                alert.symbol,
                alert.event_date,
                alert.alert_type.replace('_', ' ').title(),
                f"{alert.relative_volume:.1f}x",
                f"{alert.day_return:+.1f}%",
                alert.message
            )
            self.alerts_tree.insert('', tk.END, values=values, tags=(alert.priority,))
        
        # Update summary
        summary = self.alert_system.get_summary()
        self.alert_summary_label.config(text=f"{summary['unacknowledged']} unread alerts")
        
        # Update stats text
        self.alerts_stats_text.delete(1.0, tk.END)
        stats_text = f"""
ALERT SUMMARY (Last 7 Days)
{'='*40}
Total Alerts:      {summary['total_alerts']}
Unacknowledged:    {summary['unacknowledged']}
Recent (3 days):   {summary['recent_3d']}

BY PRIORITY:
🔴 Critical:       {summary['critical']}
🟠 High:           {summary['high']}
🟡 Medium:         {summary['medium']}

BY TYPE:
🚀 Breakouts:      {summary['breakouts']}
⚠️ Breakdowns:     {summary['breakdowns']}
"""
        self.alerts_stats_text.insert(tk.END, stats_text)
        
        # Update badge
        if summary['unacknowledged'] > 0:
            self.alert_badge.config(text=f"🔔 {summary['unacknowledged']} alerts")
        else:
            self.alert_badge.config(text="")
    
    def _check_alerts(self):
        """Check for new alerts."""
        self.status_label.config(text="Checking for alerts...")
        self.root.update()
        
        new_alerts = self.alert_system.check_for_alerts()
        self._load_alerts()
        
        if new_alerts:
            messagebox.showinfo("New Alerts", f"Found {len(new_alerts)} new volume alerts!")
        
        self.status_label.config(text="Ready")
    
    def _ack_all_alerts(self):
        """Acknowledge all alerts."""
        self.alert_system.acknowledge_all()
        self._load_alerts()
    
    def _clear_old_alerts(self):
        """Clear old alerts."""
        self.alert_system.clear_old_alerts(days=7)
        self._load_alerts()
    
    def _start_alert_check(self):
        """Start periodic alert checking."""
        def check():
            try:
                self.alert_system.check_for_alerts()
                self.root.after(0, self._update_alert_badge)
            except:
                pass
        
        # Check every 5 minutes
        self.root.after(300000, self._start_alert_check)
        
        # Initial check in background
        threading.Thread(target=check, daemon=True).start()
    
    def _update_alert_badge(self):
        """Update alert badge."""
        summary = self.alert_system.get_summary()
        if summary['unacknowledged'] > 0:
            self.alert_badge.config(text=f"🔔 {summary['unacknowledged']} alerts")
        else:
            self.alert_badge.config(text="")
    
    # =========================================================================
    # PATTERNS TAB
    # =========================================================================
    
    def _create_patterns_tab(self):
        """Create pattern analysis tab."""
        self.patterns_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.patterns_tab, text="📊 Patterns")
        
        # Controls
        control_frame = ttk.Frame(self.patterns_tab)
        control_frame.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Button(control_frame, text="📈 Analyze Patterns", command=self._analyze_patterns).pack(side=tk.LEFT, padx=5)
        
        ttk.Label(control_frame, text="Sort By:").pack(side=tk.LEFT, padx=(20, 5))
        self.pattern_sort_var = tk.StringVar(value="Return")
        sort_combo = ttk.Combobox(control_frame, textvariable=self.pattern_sort_var,
                                   values=["Return", "Win Rate", "Events"], width=12, state='readonly')
        sort_combo.pack(side=tk.LEFT, padx=5)
        sort_combo.bind('<<ComboboxSelected>>', lambda e: self._analyze_patterns())
        
        # Main content
        paned = ttk.PanedWindow(self.patterns_tab, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # Left: Pattern table
        left_frame = ttk.LabelFrame(paned, text="Pattern Performance")
        paned.add(left_frame, weight=1)
        
        columns = ('pattern', 'events', 'avg_day', 'avg_1w', 'avg_1m', 'win_1m')
        self.patterns_tree = ttk.Treeview(left_frame, columns=columns, show='headings', height=15)
        
        self.patterns_tree.heading('pattern', text='Pattern')
        self.patterns_tree.heading('events', text='Events')
        self.patterns_tree.heading('avg_day', text='Avg Day')
        self.patterns_tree.heading('avg_1w', text='Avg 1W')
        self.patterns_tree.heading('avg_1m', text='Avg 1M')
        self.patterns_tree.heading('win_1m', text='Win% 1M')
        
        self.patterns_tree.column('pattern', width=150)
        self.patterns_tree.column('events', width=70)
        self.patterns_tree.column('avg_day', width=70)
        self.patterns_tree.column('avg_1w', width=70)
        self.patterns_tree.column('avg_1m', width=70)
        self.patterns_tree.column('win_1m', width=70)
        
        self.patterns_tree.pack(fill=tk.BOTH, expand=True)
        
        self.patterns_tree.tag_configure('good', background='#C8E6C9')
        self.patterns_tree.tag_configure('bad', background='#FFCDD2')
        
        # Right: Chart
        right_frame = ttk.Frame(paned)
        paned.add(right_frame, weight=1)
        
        self.patterns_fig = Figure(figsize=(8, 8), dpi=100)
        self.patterns_canvas = FigureCanvasTkAgg(self.patterns_fig, master=right_frame)
        self.patterns_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
        # Initial load
        self._analyze_patterns()
    
    def _analyze_patterns(self):
        """Analyze and display pattern performance."""
        self.status_label.config(text="Analyzing patterns...")
        self.root.update()
        
        try:
            sort_by = self.pattern_sort_var.get()
            
            if sort_by == "Return":
                stats = self.pattern_analyzer.get_best_patterns_by_return()
            elif sort_by == "Win Rate":
                stats = self.pattern_analyzer.get_best_patterns_by_win_rate()
            else:
                stats = self.pattern_analyzer.analyze_pattern_performance()
            
            # Clear tree
            for item in self.patterns_tree.get_children():
                self.patterns_tree.delete(item)
            
            for _, row in stats.iterrows():
                values = (
                    row['pattern'],
                    row['events'],
                    f"{row['avg_day_return']:+.1f}%",
                    f"{row['avg_1w']:+.1f}%",
                    f"{row['avg_1m']:+.1f}%",
                    f"{row['win_1m']:.0f}%"
                )
                
                tag = 'good' if row['win_1m'] >= 55 else 'bad' if row['win_1m'] < 45 else ''
                self.patterns_tree.insert('', tk.END, values=values, tags=(tag,))
            
            # Update chart
            self._update_patterns_chart(stats)
            
            self.status_label.config(text="Ready")
            
        except Exception as e:
            messagebox.showerror("Error", f"Pattern analysis error: {e}")
            self.status_label.config(text="Error")
    
    def _update_patterns_chart(self, stats):
        """Update pattern performance chart."""
        self.patterns_fig.clear()
        
        if stats.empty:
            return
        
        # Bar chart of 1M returns
        ax1 = self.patterns_fig.add_subplot(2, 1, 1)
        patterns = stats['pattern']
        returns = stats['avg_1m']
        colors = ['green' if r > 0 else 'red' for r in returns]
        
        bars = ax1.barh(patterns, returns, color=colors, alpha=0.7)
        ax1.axvline(x=0, color='black', linestyle='-', linewidth=0.5)
        ax1.set_xlabel('Average 1-Month Return (%)')
        ax1.set_title('Pattern Performance: 1-Month Return')
        
        # Win rate chart
        ax2 = self.patterns_fig.add_subplot(2, 1, 2)
        win_rates = stats['win_1m']
        colors = ['green' if w >= 55 else 'red' if w < 45 else 'orange' for w in win_rates]
        
        ax2.barh(patterns, win_rates, color=colors, alpha=0.7)
        ax2.axvline(x=50, color='black', linestyle='--', linewidth=1)
        ax2.set_xlabel('Win Rate (%)')
        ax2.set_title('Pattern Performance: Win Rate')
        ax2.set_xlim(0, 100)
        
        self.patterns_fig.tight_layout()
        self.patterns_canvas.draw()

    def _on_scanner_double_click(self, event):
        """Handle double-click on scanner tree - open chart visualizer."""
        selected = self.scanner_tree.selection()
        if not selected:
            return
        
        item = self.scanner_tree.item(selected[0])
        values = item.get('values', [])
        if values:
            symbol = values[0]  # First column is symbol
            self._launch_chart(symbol)
    
    def _launch_chart(self, symbol: str):
        """Launch the chart visualizer for a symbol."""
        try:
            # Use subprocess to launch chart in separate process to avoid import issues
            import subprocess
            import sys
            subprocess.Popen([sys.executable, '-m', 'volume_cluster_analysis.chart_visualizer', symbol])
        except Exception as e:
            messagebox.showerror("Error", f"Failed to launch chart: {e}")


def main():
    root = tk.Tk()
    app = VolumeAnalysisGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
