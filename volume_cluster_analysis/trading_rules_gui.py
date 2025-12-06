#!/usr/bin/env python3
"""
Volume-Based Trading Rules GUI
==============================
Interactive GUI for viewing and analyzing trading signals based on volume patterns.
"""

import tkinter as tk
from tkinter import ttk, messagebox
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Optional
import threading

from .trading_rules import (
    TradingRulesEngine, TradingSignal, RulePerformance,
    SignalType, SignalConfidence
)


class TradingRulesGUI:
    """GUI for the Volume-Based Trading Rules Engine."""
    
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("📊 Volume Trading Rules Engine")
        self.root.geometry("1400x800")
        
        # Initialize engine
        self.engine = None
        self.signals: List[TradingSignal] = []
        self.performances: List[RulePerformance] = []
        
        # Setup UI
        self._setup_styles()
        self._create_widgets()
        
        # Load data
        self.root.after(100, self._initialize_engine)
    
    def _setup_styles(self):
        """Setup ttk styles."""
        style = ttk.Style()
        style.theme_use('clam')
        
        # Configure colors
        style.configure('TFrame', background='#f5f5f5')
        style.configure('TLabel', background='#f5f5f5', font=('Arial', 10))
        style.configure('TButton', font=('Arial', 10))
        style.configure('Header.TLabel', font=('Arial', 14, 'bold'))
        style.configure('Stats.TLabel', font=('Arial', 11))
        
        # Signal type tags
        style.configure('StrongBuy.TLabel', foreground='#00aa00', font=('Arial', 10, 'bold'))
        style.configure('Buy.TLabel', foreground='#22aa22', font=('Arial', 10))
        style.configure('Avoid.TLabel', foreground='#cc0000', font=('Arial', 10))
        style.configure('Watch.TLabel', foreground='#cc8800', font=('Arial', 10))
    
    def _create_widgets(self):
        """Create all GUI widgets."""
        # Main container
        main_frame = ttk.Frame(self.root, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Create notebook for tabs
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True)
        
        # Tab 1: Trading Signals
        self.signals_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.signals_tab, text="📈 Trading Signals")
        self._create_signals_tab()
        
        # Tab 2: Rule Performance
        self.performance_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.performance_tab, text="📊 Rule Performance")
        self._create_performance_tab()
        
        # Tab 3: Signal Details
        self.details_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.details_tab, text="🔍 Signal Details")
        self._create_details_tab()
        
        # Status bar
        self.status_var = tk.StringVar(value="Initializing...")
        status_bar = ttk.Label(main_frame, textvariable=self.status_var, relief=tk.SUNKEN)
        status_bar.pack(fill=tk.X, pady=(5, 0))
    
    def _create_signals_tab(self):
        """Create the trading signals tab."""
        # Control frame
        control_frame = ttk.Frame(self.signals_tab)
        control_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # Days selection
        ttk.Label(control_frame, text="Look Back:").pack(side=tk.LEFT, padx=5)
        self.days_var = tk.StringVar(value="7")
        days_combo = ttk.Combobox(control_frame, textvariable=self.days_var,
                                   values=["3", "5", "7", "14", "30"], width=5, state='readonly')
        days_combo.pack(side=tk.LEFT, padx=5)
        
        # Signal type filter
        ttk.Label(control_frame, text="Filter:").pack(side=tk.LEFT, padx=(20, 5))
        self.filter_var = tk.StringVar(value="All")
        filter_combo = ttk.Combobox(control_frame, textvariable=self.filter_var,
                                     values=["All", "Buy Signals", "Avoid Signals", "High Confidence"],
                                     width=15, state='readonly')
        filter_combo.pack(side=tk.LEFT, padx=5)
        
        # Scan button
        ttk.Button(control_frame, text="🔄 Scan", command=self._load_signals).pack(side=tk.LEFT, padx=20)
        
        # Export button
        ttk.Button(control_frame, text="📋 Export", command=self._export_signals).pack(side=tk.LEFT, padx=5)
        
        # Stats label
        self.signals_stats_label = ttk.Label(control_frame, text="", style='Stats.TLabel')
        self.signals_stats_label.pack(side=tk.RIGHT, padx=10)
        
        # Create paned window for signals list and summary
        paned = ttk.PanedWindow(self.signals_tab, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # Left: Signals treeview
        signals_frame = ttk.Frame(paned)
        paned.add(signals_frame, weight=3)
        
        columns = ('symbol', 'date', 'signal', 'pattern', 'confidence', 'price', 'day%', 'relvol', 'winrate')
        self.signals_tree = ttk.Treeview(signals_frame, columns=columns, show='headings', height=20)
        
        # Column headings
        headings = {
            'symbol': ('Symbol', 80),
            'date': ('Date', 90),
            'signal': ('Signal', 90),
            'pattern': ('Pattern', 140),
            'confidence': ('Conf', 60),
            'price': ('Price', 80),
            'day%': ('Day %', 60),
            'relvol': ('RelVol', 60),
            'winrate': ('Win%', 60)
        }
        
        for col, (text, width) in headings.items():
            self.signals_tree.heading(col, text=text, command=lambda c=col: self._sort_signals(c))
            self.signals_tree.column(col, width=width, anchor=tk.CENTER if col != 'pattern' else tk.W)
        
        # Scrollbars
        y_scroll = ttk.Scrollbar(signals_frame, orient=tk.VERTICAL, command=self.signals_tree.yview)
        self.signals_tree.configure(yscrollcommand=y_scroll.set)
        
        self.signals_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        y_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Bind selection
        self.signals_tree.bind('<<TreeviewSelect>>', self._on_signal_select)
        self.signals_tree.bind('<Double-1>', self._show_signal_details)
        
        # Right: Quick summary
        summary_frame = ttk.LabelFrame(paned, text="Signal Summary", padding=10)
        paned.add(summary_frame, weight=1)
        
        self.summary_text = tk.Text(summary_frame, wrap=tk.WORD, font=('Consolas', 10), 
                                     state=tk.DISABLED, bg='#fafafa')
        self.summary_text.pack(fill=tk.BOTH, expand=True)
        
        # Configure tags for text colors
        self.summary_text.tag_configure('buy', foreground='#00aa00')
        self.summary_text.tag_configure('avoid', foreground='#cc0000')
        self.summary_text.tag_configure('watch', foreground='#cc8800')
        self.summary_text.tag_configure('header', font=('Consolas', 11, 'bold'))
        self.summary_text.tag_configure('bold', font=('Consolas', 10, 'bold'))
    
    def _create_performance_tab(self):
        """Create the rule performance tab."""
        # Control frame
        control_frame = ttk.Frame(self.performance_tab)
        control_frame.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Label(control_frame, text="Analysis Period:").pack(side=tk.LEFT, padx=5)
        self.perf_days_var = tk.StringVar(value="90")
        perf_days_combo = ttk.Combobox(control_frame, textvariable=self.perf_days_var,
                                        values=["30", "60", "90", "180", "365"], width=6, state='readonly')
        perf_days_combo.pack(side=tk.LEFT, padx=5)
        
        ttk.Button(control_frame, text="🔄 Analyze", command=self._load_performance).pack(side=tk.LEFT, padx=20)
        
        # Performance treeview
        perf_frame = ttk.Frame(self.performance_tab)
        perf_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        columns = ('rule', 'signals', 'winners', 'losers', 'winrate', 'avgwin', 'avgloss', 'expect', 'pf')
        self.perf_tree = ttk.Treeview(perf_frame, columns=columns, show='headings', height=15)
        
        headings = {
            'rule': ('Trading Rule', 200),
            'signals': ('Signals', 70),
            'winners': ('Winners', 70),
            'losers': ('Losers', 70),
            'winrate': ('Win %', 70),
            'avgwin': ('Avg Win', 80),
            'avgloss': ('Avg Loss', 80),
            'expect': ('Expect', 80),
            'pf': ('PF', 60)
        }
        
        for col, (text, width) in headings.items():
            self.perf_tree.heading(col, text=text)
            self.perf_tree.column(col, width=width, anchor=tk.CENTER if col != 'rule' else tk.W)
        
        y_scroll = ttk.Scrollbar(perf_frame, orient=tk.VERTICAL, command=self.perf_tree.yview)
        self.perf_tree.configure(yscrollcommand=y_scroll.set)
        
        self.perf_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        y_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Performance summary
        summary_frame = ttk.LabelFrame(self.performance_tab, text="Performance Insights", padding=10)
        summary_frame.pack(fill=tk.X, padx=10, pady=10)
        
        self.perf_summary_label = ttk.Label(summary_frame, text="", style='Stats.TLabel', wraplength=1200)
        self.perf_summary_label.pack(fill=tk.X)
    
    def _create_details_tab(self):
        """Create the signal details tab."""
        # Signal info frame
        info_frame = ttk.LabelFrame(self.details_tab, text="Signal Information", padding=10)
        info_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # Two columns for info
        left_frame = ttk.Frame(info_frame)
        left_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        right_frame = ttk.Frame(info_frame)
        right_frame.pack(side=tk.RIGHT, fill=tk.X, expand=True)
        
        # Left column labels
        self.detail_symbol = ttk.Label(left_frame, text="Symbol: -", style='Header.TLabel')
        self.detail_symbol.pack(anchor=tk.W, pady=2)
        
        self.detail_date = ttk.Label(left_frame, text="Date: -")
        self.detail_date.pack(anchor=tk.W, pady=2)
        
        self.detail_signal = ttk.Label(left_frame, text="Signal: -")
        self.detail_signal.pack(anchor=tk.W, pady=2)
        
        self.detail_pattern = ttk.Label(left_frame, text="Pattern: -")
        self.detail_pattern.pack(anchor=tk.W, pady=2)
        
        self.detail_confidence = ttk.Label(left_frame, text="Confidence: -")
        self.detail_confidence.pack(anchor=tk.W, pady=2)
        
        # Right column labels
        self.detail_price = ttk.Label(right_frame, text="Entry Price: -")
        self.detail_price.pack(anchor=tk.W, pady=2)
        
        self.detail_stop = ttk.Label(right_frame, text="Stop Loss: -")
        self.detail_stop.pack(anchor=tk.W, pady=2)
        
        self.detail_target1 = ttk.Label(right_frame, text="Target 1: -")
        self.detail_target1.pack(anchor=tk.W, pady=2)
        
        self.detail_target2 = ttk.Label(right_frame, text="Target 2: -")
        self.detail_target2.pack(anchor=tk.W, pady=2)
        
        self.detail_rr = ttk.Label(right_frame, text="Risk/Reward: -")
        self.detail_rr.pack(anchor=tk.W, pady=2)
        
        # Volume info frame
        vol_frame = ttk.LabelFrame(self.details_tab, text="Volume Analysis", padding=10)
        vol_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self.detail_volume = ttk.Label(vol_frame, text="Volume: -")
        self.detail_volume.pack(anchor=tk.W, pady=2)
        
        self.detail_relvol = ttk.Label(vol_frame, text="Relative Volume: -")
        self.detail_relvol.pack(anchor=tk.W, pady=2)
        
        self.detail_quintile = ttk.Label(vol_frame, text="Volume Quintile: -")
        self.detail_quintile.pack(anchor=tk.W, pady=2)
        
        self.detail_dayret = ttk.Label(vol_frame, text="Day Return: -")
        self.detail_dayret.pack(anchor=tk.W, pady=2)
        
        # Historical edge frame
        edge_frame = ttk.LabelFrame(self.details_tab, text="Historical Edge", padding=10)
        edge_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self.detail_winrate = ttk.Label(edge_frame, text="Win Rate: -")
        self.detail_winrate.pack(anchor=tk.W, pady=2)
        
        self.detail_avgret = ttk.Label(edge_frame, text="Avg Return: -")
        self.detail_avgret.pack(anchor=tk.W, pady=2)
        
        self.detail_sample = ttk.Label(edge_frame, text="Sample Size: -")
        self.detail_sample.pack(anchor=tk.W, pady=2)
        
        # Action buttons frame
        action_frame = ttk.Frame(self.details_tab)
        action_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self.chart_btn = ttk.Button(action_frame, text="📊 View Chart", command=self._launch_chart)
        self.chart_btn.pack(side=tk.LEFT, padx=5)
        
        ttk.Label(action_frame, text="(Double-click a signal to view chart)", 
                  foreground='gray').pack(side=tk.LEFT, padx=20)
        
        # Reasons frame
        reasons_frame = ttk.LabelFrame(self.details_tab, text="Signal Reasoning", padding=10)
        reasons_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        self.reasons_text = tk.Text(reasons_frame, wrap=tk.WORD, font=('Arial', 11), 
                                     height=10, state=tk.DISABLED, bg='#fafafa')
        self.reasons_text.pack(fill=tk.BOTH, expand=True)
        
        self.reasons_text.tag_configure('reason', foreground='#006600')
        self.reasons_text.tag_configure('warning', foreground='#cc6600')
        
        # Store currently selected symbol for chart
        self.current_symbol = None
    
    def _initialize_engine(self):
        """Initialize the trading rules engine in background."""
        def init():
            try:
                self.engine = TradingRulesEngine()
                self.root.after(0, lambda: self._on_engine_ready())
            except Exception as e:
                self.root.after(0, lambda: self._on_engine_error(str(e)))
        
        threading.Thread(target=init, daemon=True).start()
    
    def _on_engine_ready(self):
        """Called when engine is ready."""
        self.status_var.set("Ready - Click 'Scan' to find trading signals")
        self._load_signals()
        self._load_performance()
    
    def _on_engine_error(self, error: str):
        """Called on engine initialization error."""
        self.status_var.set(f"Error: {error}")
        messagebox.showerror("Initialization Error", f"Failed to initialize: {error}")
    
    def _load_signals(self):
        """Load trading signals."""
        if not self.engine:
            return
        
        self.status_var.set("Scanning for signals...")
        
        def load():
            try:
                days = int(self.days_var.get())
                signals = self.engine.generate_signals(days=days)
                self.root.after(0, lambda: self._display_signals(signals))
            except Exception as e:
                self.root.after(0, lambda: self.status_var.set(f"Error: {e}"))
        
        threading.Thread(target=load, daemon=True).start()
    
    def _display_signals(self, signals: List[TradingSignal]):
        """Display signals in the treeview."""
        self.signals = signals
        
        # Clear existing items
        for item in self.signals_tree.get_children():
            self.signals_tree.delete(item)
        
        # Apply filter
        filter_type = self.filter_var.get()
        filtered = signals
        
        if filter_type == "Buy Signals":
            filtered = [s for s in signals if s.signal_type in [SignalType.STRONG_BUY, SignalType.BUY]]
        elif filter_type == "Avoid Signals":
            filtered = [s for s in signals if s.signal_type in [SignalType.AVOID, SignalType.REDUCE]]
        elif filter_type == "High Confidence":
            filtered = [s for s in signals if s.confidence == SignalConfidence.HIGH]
        
        # Add to treeview
        for signal in filtered:
            signal_emoji = {
                SignalType.STRONG_BUY: "🚀 STRONG BUY",
                SignalType.BUY: "📈 BUY",
                SignalType.WATCH: "👀 WATCH",
                SignalType.REDUCE: "📉 REDUCE",
                SignalType.AVOID: "⛔ AVOID",
            }.get(signal.signal_type, str(signal.signal_type.value))
            
            conf_stars = {
                SignalConfidence.HIGH: "⭐⭐⭐",
                SignalConfidence.MEDIUM: "⭐⭐",
                SignalConfidence.LOW: "⭐",
            }.get(signal.confidence, "")
            
            values = (
                signal.symbol.replace('.NS', ''),
                str(signal.signal_date)[:10],
                signal_emoji,
                signal.pattern,
                conf_stars,
                f"₹{signal.entry_price:.2f}",
                f"{signal.day_return:+.1f}%",
                f"{signal.relative_volume:.1f}x",
                f"{signal.historical_win_rate:.0f}%"
            )
            
            item = self.signals_tree.insert('', tk.END, values=values)
            
            # Color code by signal type
            if signal.signal_type in [SignalType.STRONG_BUY, SignalType.BUY]:
                self.signals_tree.item(item, tags=('buy',))
            elif signal.signal_type in [SignalType.AVOID, SignalType.REDUCE]:
                self.signals_tree.item(item, tags=('avoid',))
            elif signal.signal_type == SignalType.WATCH:
                self.signals_tree.item(item, tags=('watch',))
        
        # Configure tag colors
        self.signals_tree.tag_configure('buy', foreground='#008800')
        self.signals_tree.tag_configure('avoid', foreground='#cc0000')
        self.signals_tree.tag_configure('watch', foreground='#cc8800')
        
        # Update stats
        buy_count = len([s for s in signals if s.signal_type in [SignalType.STRONG_BUY, SignalType.BUY]])
        avoid_count = len([s for s in signals if s.signal_type in [SignalType.AVOID, SignalType.REDUCE]])
        high_conf = len([s for s in signals if s.confidence == SignalConfidence.HIGH])
        
        self.signals_stats_label.config(
            text=f"Total: {len(signals)} | Buy: {buy_count} | Avoid: {avoid_count} | High Confidence: {high_conf}"
        )
        
        self.status_var.set(f"Found {len(signals)} signals ({len(filtered)} displayed)")
        
        # Update summary
        self._update_summary(signals)
    
    def _update_summary(self, signals: List[TradingSignal]):
        """Update the quick summary panel."""
        self.summary_text.config(state=tk.NORMAL)
        self.summary_text.delete(1.0, tk.END)
        
        # Strong buys
        strong_buys = [s for s in signals if s.signal_type == SignalType.STRONG_BUY]
        if strong_buys:
            self.summary_text.insert(tk.END, "🚀 STRONG BUY SIGNALS\n", 'header')
            for s in strong_buys[:5]:
                self.summary_text.insert(tk.END, f"  {s.symbol.replace('.NS', '')}: ", 'buy')
                self.summary_text.insert(tk.END, f"{s.pattern}\n")
                self.summary_text.insert(tk.END, f"    Entry: ₹{s.entry_price:.2f} | Stop: ₹{s.stop_loss:.2f}\n")
            self.summary_text.insert(tk.END, "\n")
        
        # Buy signals
        buys = [s for s in signals if s.signal_type == SignalType.BUY][:5]
        if buys:
            self.summary_text.insert(tk.END, "📈 BUY SIGNALS\n", 'header')
            for s in buys:
                self.summary_text.insert(tk.END, f"  {s.symbol.replace('.NS', '')}: ", 'buy')
                self.summary_text.insert(tk.END, f"{s.day_return:+.1f}% on {s.relative_volume:.1f}x vol\n")
            self.summary_text.insert(tk.END, "\n")
        
        # Avoid signals
        avoids = [s for s in signals if s.signal_type in [SignalType.AVOID, SignalType.REDUCE]][:5]
        if avoids:
            self.summary_text.insert(tk.END, "⛔ AVOID / REDUCE\n", 'header')
            for s in avoids:
                self.summary_text.insert(tk.END, f"  {s.symbol.replace('.NS', '')}: ", 'avoid')
                self.summary_text.insert(tk.END, f"{s.day_return:+.1f}% on {s.relative_volume:.1f}x vol\n")
        
        self.summary_text.config(state=tk.DISABLED)
    
    def _on_signal_select(self, event):
        """Handle signal selection."""
        selection = self.signals_tree.selection()
        if not selection:
            return
        
        idx = self.signals_tree.index(selection[0])
        
        # Find matching signal
        filter_type = self.filter_var.get()
        filtered = self.signals
        
        if filter_type == "Buy Signals":
            filtered = [s for s in self.signals if s.signal_type in [SignalType.STRONG_BUY, SignalType.BUY]]
        elif filter_type == "Avoid Signals":
            filtered = [s for s in self.signals if s.signal_type in [SignalType.AVOID, SignalType.REDUCE]]
        elif filter_type == "High Confidence":
            filtered = [s for s in self.signals if s.confidence == SignalConfidence.HIGH]
        
        if idx < len(filtered):
            self._show_signal_in_details(filtered[idx])
    
    def _show_signal_details(self, event):
        """Show detailed view of selected signal."""
        self._on_signal_select(event)
        self.notebook.select(self.details_tab)
    
    def _show_signal_in_details(self, signal: TradingSignal):
        """Display signal details in the details tab."""
        # Store for chart launch
        self.current_symbol = signal.symbol
        
        # Signal info
        signal_text = {
            SignalType.STRONG_BUY: "🚀 STRONG BUY",
            SignalType.BUY: "📈 BUY",
            SignalType.WATCH: "👀 WATCH",
            SignalType.REDUCE: "📉 REDUCE",
            SignalType.AVOID: "⛔ AVOID",
        }.get(signal.signal_type, str(signal.signal_type.value))
        
        conf_text = {
            SignalConfidence.HIGH: "⭐⭐⭐ HIGH",
            SignalConfidence.MEDIUM: "⭐⭐ MEDIUM",
            SignalConfidence.LOW: "⭐ LOW",
        }.get(signal.confidence, "")
        
        self.detail_symbol.config(text=f"Symbol: {signal.symbol}")
        self.detail_date.config(text=f"Date: {str(signal.signal_date)[:10]}")
        self.detail_signal.config(text=f"Signal: {signal_text}")
        self.detail_pattern.config(text=f"Pattern: {signal.pattern}")
        self.detail_confidence.config(text=f"Confidence: {conf_text}")
        
        self.detail_price.config(text=f"Entry Price: ₹{signal.entry_price:.2f}")
        self.detail_stop.config(text=f"Stop Loss: ₹{signal.stop_loss:.2f}")
        self.detail_target1.config(text=f"Target 1: ₹{signal.target_1:.2f}")
        self.detail_target2.config(text=f"Target 2: ₹{signal.target_2:.2f}")
        self.detail_rr.config(text=f"Risk/Reward: 1:{signal.risk_reward:.1f}")
        
        self.detail_volume.config(text=f"Volume: {signal.volume:,}")
        self.detail_relvol.config(text=f"Relative Volume: {signal.relative_volume}x average")
        self.detail_quintile.config(text=f"Volume Quintile: {signal.volume_quintile}")
        self.detail_dayret.config(text=f"Day Return: {signal.day_return:+.1f}%")
        
        self.detail_winrate.config(text=f"Win Rate: {signal.historical_win_rate:.0f}%")
        self.detail_avgret.config(text=f"Avg Return (1 week): {signal.historical_avg_return:+.1f}%")
        self.detail_sample.config(text=f"Sample Size: {signal.sample_size} similar events")
        
        # Reasons
        self.reasons_text.config(state=tk.NORMAL)
        self.reasons_text.delete(1.0, tk.END)
        
        self.reasons_text.insert(tk.END, "✓ Signal Reasons:\n\n", 'header')
        for reason in signal.reasons:
            self.reasons_text.insert(tk.END, f"  {reason}\n", 'reason')
        
        if signal.warnings:
            self.reasons_text.insert(tk.END, "\n⚠️ Warnings:\n\n", 'header')
            for warning in signal.warnings:
                self.reasons_text.insert(tk.END, f"  {warning}\n", 'warning')
        
        self.reasons_text.config(state=tk.DISABLED)
    
    def _load_performance(self):
        """Load rule performance data."""
        if not self.engine:
            return
        
        def load():
            try:
                days = int(self.perf_days_var.get())
                performances = self.engine.get_rule_performance(days=days)
                self.root.after(0, lambda: self._display_performance(performances))
            except Exception as e:
                self.root.after(0, lambda: self.status_var.set(f"Error: {e}"))
        
        threading.Thread(target=load, daemon=True).start()
    
    def _display_performance(self, performances: List[RulePerformance]):
        """Display performance in treeview."""
        self.performances = performances
        
        # Clear existing
        for item in self.perf_tree.get_children():
            self.perf_tree.delete(item)
        
        # Add rows
        for perf in performances:
            values = (
                perf.rule_name,
                perf.total_signals,
                perf.winning_trades,
                perf.losing_trades,
                f"{perf.win_rate:.1f}%",
                f"+{perf.avg_winner:.2f}%" if perf.avg_winner > 0 else f"{perf.avg_winner:.2f}%",
                f"{perf.avg_loser:.2f}%",
                f"{perf.expectancy:+.2f}%",
                f"{perf.profit_factor:.2f}"
            )
            
            item = self.perf_tree.insert('', tk.END, values=values)
            
            # Color by expectancy
            if perf.expectancy > 0.5:
                self.perf_tree.item(item, tags=('good',))
            elif perf.expectancy < 0:
                self.perf_tree.item(item, tags=('bad',))
        
        self.perf_tree.tag_configure('good', foreground='#008800')
        self.perf_tree.tag_configure('bad', foreground='#cc0000')
        
        # Summary
        if performances:
            best = performances[0]
            total_signals = sum(p.total_signals for p in performances)
            avg_winrate = sum(p.win_rate * p.total_signals for p in performances) / total_signals if total_signals > 0 else 0
            
            summary = (f"Best Rule: {best.rule_name} ({best.win_rate:.1f}% win rate, "
                      f"{best.expectancy:+.2f}% expectancy) | "
                      f"Total Signals: {total_signals} | "
                      f"Weighted Avg Win Rate: {avg_winrate:.1f}%")
            self.perf_summary_label.config(text=summary)
    
    def _sort_signals(self, column):
        """Sort signals by column."""
        # Get current items
        items = [(self.signals_tree.item(item)['values'], item) 
                 for item in self.signals_tree.get_children('')]
        
        # Determine column index
        columns = ('symbol', 'date', 'signal', 'pattern', 'confidence', 'price', 'day%', 'relvol', 'winrate')
        col_idx = columns.index(column)
        
        # Sort
        reverse = getattr(self, f'_sort_reverse_{column}', False)
        
        def sort_key(x):
            val = x[0][col_idx]
            # Try to extract numeric value
            if isinstance(val, str):
                # Remove currency, %, x symbols
                cleaned = val.replace('₹', '').replace('%', '').replace('x', '').replace('+', '').strip()
                try:
                    return float(cleaned)
                except ValueError:
                    return val.lower()
            return val
        
        items.sort(key=sort_key, reverse=reverse)
        
        # Reorder
        for idx, (_, item) in enumerate(items):
            self.signals_tree.move(item, '', idx)
        
        # Toggle sort direction
        setattr(self, f'_sort_reverse_{column}', not reverse)
    
    def _export_signals(self):
        """Export signals to clipboard."""
        if not self.signals:
            messagebox.showinfo("Export", "No signals to export")
            return
        
        lines = ["Symbol,Date,Signal,Pattern,Confidence,Price,Day%,RelVol,WinRate,StopLoss,Target1,Target2"]
        
        for s in self.signals:
            signal_type = s.signal_type.value
            confidence = s.confidence.value
            lines.append(f"{s.symbol},{s.signal_date},{signal_type},{s.pattern},{confidence},"
                        f"{s.entry_price:.2f},{s.day_return:.1f},{s.relative_volume:.1f},"
                        f"{s.historical_win_rate:.0f},{s.stop_loss:.2f},{s.target_1:.2f},{s.target_2:.2f}")
        
        # Copy to clipboard
        self.root.clipboard_clear()
        self.root.clipboard_append('\n'.join(lines))
        
        messagebox.showinfo("Export", f"Exported {len(self.signals)} signals to clipboard (CSV format)")

    def _launch_chart(self):
        """Launch the chart visualizer for the current symbol."""
        if not self.current_symbol:
            messagebox.showinfo("Chart", "Please select a signal first")
            return
        
        try:
            from .chart_visualizer import launch_chart
            launch_chart(self.current_symbol)
        except ImportError as e:
            messagebox.showerror("Error", f"Chart visualizer not available: {e}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to launch chart: {e}")


def main():
    """Main entry point."""
    root = tk.Tk()
    app = TradingRulesGUI(root)
    root.mainloop()


if __name__ == '__main__':
    main()
