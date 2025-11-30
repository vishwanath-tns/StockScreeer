#!/usr/bin/env python3
"""
Rankings Analyzer GUI

Visualize and validate historical stock rankings data.
Features:
- Summary statistics
- Distribution charts
- Time series analysis
- Symbol lookup
- Data quality checks
"""

import os
import sys
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime, date, timedelta
import threading

# Add project root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import pandas as pd
import numpy as np
from sqlalchemy import text

try:
    import matplotlib
    matplotlib.use('TkAgg')
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
    from matplotlib.figure import Figure
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False
    print("Warning: matplotlib not available, charts disabled")

from ranking.db.schema import get_ranking_engine


class RankingsAnalyzerGUI:
    """GUI for analyzing historical rankings data."""
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Rankings Data Analyzer")
        self.root.geometry("1200x800")
        
        self.engine = get_ranking_engine()
        self.current_data = None
        
        self._create_ui()
        self._load_summary()
    
    def _create_ui(self):
        """Create the GUI layout."""
        # Main container
        main = ttk.Frame(self.root, padding=10)
        main.pack(fill=tk.BOTH, expand=True)
        
        # Title
        title = ttk.Label(
            main,
            text="📊 Historical Rankings Analyzer",
            font=("Segoe UI", 16, "bold")
        )
        title.pack(pady=(0, 10))
        
        # Create notebook for tabs
        notebook = ttk.Notebook(main)
        notebook.pack(fill=tk.BOTH, expand=True)
        
        # Tab 1: Summary
        self._create_summary_tab(notebook)
        
        # Tab 2: Distribution Charts
        self._create_distribution_tab(notebook)
        
        # Tab 3: Time Series
        self._create_timeseries_tab(notebook)
        
        # Tab 4: Symbol Lookup
        self._create_symbol_tab(notebook)
        
        # Tab 5: Data Quality
        self._create_quality_tab(notebook)
    
    def _create_summary_tab(self, notebook):
        """Create summary statistics tab."""
        tab = ttk.Frame(notebook, padding=10)
        notebook.add(tab, text="📈 Summary")
        
        # Summary text
        self.summary_text = tk.Text(tab, font=("Consolas", 11), wrap=tk.WORD)
        self.summary_text.pack(fill=tk.BOTH, expand=True)
        
        # Refresh button
        ttk.Button(tab, text="🔄 Refresh", command=self._load_summary).pack(pady=5)
    
    def _create_distribution_tab(self, notebook):
        """Create distribution charts tab."""
        tab = ttk.Frame(notebook, padding=10)
        notebook.add(tab, text="📊 Distributions")
        
        # Controls
        controls = ttk.Frame(tab)
        controls.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(controls, text="Date:").pack(side=tk.LEFT)
        self.dist_date_var = tk.StringVar(value=date.today().strftime("%Y-%m-%d"))
        ttk.Entry(controls, textvariable=self.dist_date_var, width=12).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(controls, text="📊 Plot Distributions", command=self._plot_distributions).pack(side=tk.LEFT, padx=10)
        
        # Chart area
        if HAS_MATPLOTLIB:
            self.dist_figure = Figure(figsize=(12, 8), dpi=100)
            self.dist_canvas = FigureCanvasTkAgg(self.dist_figure, tab)
            self.dist_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
            
            toolbar_frame = ttk.Frame(tab)
            toolbar_frame.pack(fill=tk.X)
            NavigationToolbar2Tk(self.dist_canvas, toolbar_frame)
        else:
            ttk.Label(tab, text="matplotlib not available").pack()
    
    def _create_timeseries_tab(self, notebook):
        """Create time series analysis tab."""
        tab = ttk.Frame(notebook, padding=10)
        notebook.add(tab, text="📈 Time Series")
        
        # Controls
        controls = ttk.Frame(tab)
        controls.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(controls, text="Symbol:").pack(side=tk.LEFT)
        self.ts_symbol_var = tk.StringVar(value="RELIANCE.NS")
        ttk.Entry(controls, textvariable=self.ts_symbol_var, width=15).pack(side=tk.LEFT, padx=5)
        
        ttk.Label(controls, text="Days:").pack(side=tk.LEFT, padx=(10, 0))
        self.ts_days_var = tk.StringVar(value="252")
        ttk.Entry(controls, textvariable=self.ts_days_var, width=6).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(controls, text="📈 Plot History", command=self._plot_timeseries).pack(side=tk.LEFT, padx=10)
        
        # Chart area
        if HAS_MATPLOTLIB:
            self.ts_figure = Figure(figsize=(12, 8), dpi=100)
            self.ts_canvas = FigureCanvasTkAgg(self.ts_figure, tab)
            self.ts_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
            
            toolbar_frame = ttk.Frame(tab)
            toolbar_frame.pack(fill=tk.X)
            NavigationToolbar2Tk(self.ts_canvas, toolbar_frame)
        else:
            ttk.Label(tab, text="matplotlib not available").pack()
    
    def _create_symbol_tab(self, notebook):
        """Create symbol lookup tab."""
        tab = ttk.Frame(notebook, padding=10)
        notebook.add(tab, text="🔍 Symbol Lookup")
        
        # Controls
        controls = ttk.Frame(tab)
        controls.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(controls, text="Symbol:").pack(side=tk.LEFT)
        self.lookup_symbol_var = tk.StringVar()
        symbol_entry = ttk.Entry(controls, textvariable=self.lookup_symbol_var, width=15)
        symbol_entry.pack(side=tk.LEFT, padx=5)
        symbol_entry.bind('<Return>', lambda e: self._lookup_symbol())
        
        ttk.Button(controls, text="🔍 Lookup", command=self._lookup_symbol).pack(side=tk.LEFT, padx=10)
        
        # Results tree
        columns = ("Date", "RS Rating", "Momentum", "Trend", "Technical", "Composite", "Rank", "Percentile")
        self.lookup_tree = ttk.Treeview(tab, columns=columns, show="headings", height=25)
        
        for col in columns:
            self.lookup_tree.heading(col, text=col)
            width = 100 if col != "Date" else 120
            self.lookup_tree.column(col, width=width, anchor=tk.CENTER)
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(tab, orient=tk.VERTICAL, command=self.lookup_tree.yview)
        self.lookup_tree.configure(yscrollcommand=scrollbar.set)
        
        self.lookup_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    
    def _create_quality_tab(self, notebook):
        """Create data quality tab."""
        tab = ttk.Frame(notebook, padding=10)
        notebook.add(tab, text="✅ Data Quality")
        
        # Quality report text
        self.quality_text = tk.Text(tab, font=("Consolas", 11), wrap=tk.WORD)
        self.quality_text.pack(fill=tk.BOTH, expand=True)
        
        # Buttons
        btn_frame = ttk.Frame(tab)
        btn_frame.pack(fill=tk.X, pady=5)
        ttk.Button(btn_frame, text="🔍 Run Quality Check", command=self._run_quality_check).pack(side=tk.LEFT)
        ttk.Button(btn_frame, text="📊 Coverage Report", command=self._coverage_report).pack(side=tk.LEFT, padx=10)
    
    def _load_summary(self):
        """Load summary statistics."""
        self.summary_text.delete("1.0", tk.END)
        self.summary_text.insert(tk.END, "Loading summary...\n")
        self.root.update()
        
        try:
            with self.engine.connect() as conn:
                summary = []
                
                # Total records
                result = conn.execute(text("SELECT COUNT(*) FROM stock_rankings_history")).fetchone()
                summary.append(f"📊 HISTORICAL RANKINGS SUMMARY")
                summary.append(f"{'='*50}")
                summary.append(f"\n📈 Total Records: {result[0]:,}")
                
                # Date range
                result = conn.execute(text("SELECT MIN(ranking_date), MAX(ranking_date) FROM stock_rankings_history")).fetchone()
                summary.append(f"📅 Date Range: {result[0]} to {result[1]}")
                
                # Unique dates
                result = conn.execute(text("SELECT COUNT(DISTINCT ranking_date) FROM stock_rankings_history")).fetchone()
                summary.append(f"📆 Trading Days: {result[0]:,}")
                
                # Unique symbols
                result = conn.execute(text("SELECT COUNT(DISTINCT symbol) FROM stock_rankings_history")).fetchone()
                summary.append(f"🏢 Unique Symbols: {result[0]:,}")
                
                # Average per day
                result = conn.execute(text("""
                    SELECT AVG(cnt) FROM (
                        SELECT COUNT(*) as cnt FROM stock_rankings_history GROUP BY ranking_date
                    ) t
                """)).fetchone()
                summary.append(f"📊 Avg Symbols/Day: {result[0]:.0f}")
                
                # Score statistics
                summary.append(f"\n{'='*50}")
                summary.append(f"📊 SCORE STATISTICS")
                summary.append(f"{'='*50}\n")
                
                result = conn.execute(text("""
                    SELECT 
                        'RS Rating' as metric,
                        MIN(rs_rating), AVG(rs_rating), MAX(rs_rating), STDDEV(rs_rating)
                    FROM stock_rankings_history WHERE rs_rating IS NOT NULL
                    UNION ALL
                    SELECT 
                        'Momentum',
                        MIN(momentum_score), AVG(momentum_score), MAX(momentum_score), STDDEV(momentum_score)
                    FROM stock_rankings_history WHERE momentum_score IS NOT NULL
                    UNION ALL
                    SELECT 
                        'Trend Template',
                        MIN(trend_template_score), AVG(trend_template_score), MAX(trend_template_score), STDDEV(trend_template_score)
                    FROM stock_rankings_history WHERE trend_template_score IS NOT NULL
                    UNION ALL
                    SELECT 
                        'Technical',
                        MIN(technical_score), AVG(technical_score), MAX(technical_score), STDDEV(technical_score)
                    FROM stock_rankings_history WHERE technical_score IS NOT NULL
                    UNION ALL
                    SELECT 
                        'Composite',
                        MIN(composite_score), AVG(composite_score), MAX(composite_score), STDDEV(composite_score)
                    FROM stock_rankings_history WHERE composite_score IS NOT NULL
                """)).fetchall()
                
                summary.append(f"{'Metric':<18} {'Min':>8} {'Avg':>8} {'Max':>8} {'StdDev':>8}")
                summary.append(f"{'-'*50}")
                for row in result:
                    summary.append(f"{row[0]:<18} {row[1]:>8.2f} {row[2]:>8.2f} {row[3]:>8.2f} {row[4]:>8.2f}")
                
                # Top performers (latest date)
                summary.append(f"\n{'='*50}")
                summary.append(f"🏆 TOP 10 COMPOSITE SCORES (Latest)")
                summary.append(f"{'='*50}\n")
                
                result = conn.execute(text("""
                    SELECT symbol, composite_score, composite_rank, rs_rating, momentum_score
                    FROM stock_rankings_history
                    WHERE ranking_date = (SELECT MAX(ranking_date) FROM stock_rankings_history)
                    ORDER BY composite_rank
                    LIMIT 10
                """)).fetchall()
                
                summary.append(f"{'Rank':<6} {'Symbol':<15} {'Composite':>10} {'RS':>8} {'Momentum':>10}")
                summary.append(f"{'-'*50}")
                for row in result:
                    summary.append(f"{row[2]:<6} {row[0]:<15} {row[1]:>10.2f} {row[3]:>8.1f} {row[4]:>10.1f}")
                
                # Monthly coverage
                summary.append(f"\n{'='*50}")
                summary.append(f"📅 MONTHLY COVERAGE")
                summary.append(f"{'='*50}\n")
                
                result = conn.execute(text("""
                    SELECT 
                        DATE_FORMAT(ranking_date, '%Y-%m') as month,
                        COUNT(DISTINCT ranking_date) as days,
                        COUNT(*) as records,
                        COUNT(DISTINCT symbol) as symbols
                    FROM stock_rankings_history
                    GROUP BY DATE_FORMAT(ranking_date, '%Y-%m')
                    ORDER BY month DESC
                    LIMIT 12
                """)).fetchall()
                
                summary.append(f"{'Month':<10} {'Days':>8} {'Records':>12} {'Symbols':>10}")
                summary.append(f"{'-'*50}")
                for row in result:
                    summary.append(f"{row[0]:<10} {row[1]:>8} {row[2]:>12,} {row[3]:>10}")
                
                self.summary_text.delete("1.0", tk.END)
                self.summary_text.insert(tk.END, "\n".join(summary))
                
        except Exception as e:
            self.summary_text.delete("1.0", tk.END)
            self.summary_text.insert(tk.END, f"Error: {e}")
    
    def _plot_distributions(self):
        """Plot score distributions for a date."""
        if not HAS_MATPLOTLIB:
            messagebox.showerror("Error", "matplotlib not available")
            return
        
        try:
            date_str = self.dist_date_var.get()
            
            with self.engine.connect() as conn:
                df = pd.read_sql(text("""
                    SELECT rs_rating, momentum_score, trend_template_score, 
                           technical_score, composite_score
                    FROM stock_rankings_history
                    WHERE ranking_date = :dt
                """), conn, params={"dt": date_str})
            
            if df.empty:
                messagebox.showwarning("No Data", f"No data for {date_str}")
                return
            
            self.dist_figure.clear()
            
            # Create 2x3 subplots
            axes = self.dist_figure.subplots(2, 3)
            self.dist_figure.suptitle(f"Score Distributions - {date_str} ({len(df)} stocks)", fontsize=14)
            
            # RS Rating
            ax = axes[0, 0]
            ax.hist(df['rs_rating'].dropna(), bins=50, color='#3498db', edgecolor='white', alpha=0.7)
            ax.set_title('RS Rating (1-99)')
            ax.set_xlabel('Score')
            ax.axvline(df['rs_rating'].mean(), color='red', linestyle='--', label=f"Mean: {df['rs_rating'].mean():.1f}")
            ax.legend()
            
            # Momentum
            ax = axes[0, 1]
            ax.hist(df['momentum_score'].dropna(), bins=50, color='#e67e22', edgecolor='white', alpha=0.7)
            ax.set_title('Momentum Score (0-100)')
            ax.set_xlabel('Score')
            ax.axvline(df['momentum_score'].mean(), color='red', linestyle='--', label=f"Mean: {df['momentum_score'].mean():.1f}")
            ax.legend()
            
            # Trend Template
            ax = axes[0, 2]
            trend_counts = df['trend_template_score'].value_counts().sort_index()
            ax.bar(trend_counts.index, trend_counts.values, color='#9b59b6', edgecolor='white', alpha=0.7)
            ax.set_title('Trend Template (0-8)')
            ax.set_xlabel('Score')
            ax.set_xticks(range(9))
            
            # Technical
            ax = axes[1, 0]
            ax.hist(df['technical_score'].dropna(), bins=50, color='#27ae60', edgecolor='white', alpha=0.7)
            ax.set_title('Technical Score (0-100)')
            ax.set_xlabel('Score')
            ax.axvline(df['technical_score'].mean(), color='red', linestyle='--', label=f"Mean: {df['technical_score'].mean():.1f}")
            ax.legend()
            
            # Composite
            ax = axes[1, 1]
            ax.hist(df['composite_score'].dropna(), bins=50, color='#c0392b', edgecolor='white', alpha=0.7)
            ax.set_title('Composite Score (0-100)')
            ax.set_xlabel('Score')
            ax.axvline(df['composite_score'].mean(), color='blue', linestyle='--', label=f"Mean: {df['composite_score'].mean():.1f}")
            ax.legend()
            
            # Correlation heatmap
            ax = axes[1, 2]
            corr = df[['rs_rating', 'momentum_score', 'trend_template_score', 'technical_score', 'composite_score']].corr()
            im = ax.imshow(corr, cmap='RdYlGn', vmin=-1, vmax=1)
            ax.set_xticks(range(5))
            ax.set_yticks(range(5))
            ax.set_xticklabels(['RS', 'Mom', 'Trend', 'Tech', 'Comp'], rotation=45)
            ax.set_yticklabels(['RS', 'Mom', 'Trend', 'Tech', 'Comp'])
            ax.set_title('Score Correlations')
            
            # Add correlation values
            for i in range(5):
                for j in range(5):
                    ax.text(j, i, f"{corr.iloc[i, j]:.2f}", ha='center', va='center', fontsize=8)
            
            self.dist_figure.tight_layout()
            self.dist_canvas.draw()
            
        except Exception as e:
            messagebox.showerror("Error", str(e))
    
    def _plot_timeseries(self):
        """Plot time series of rankings for a symbol."""
        if not HAS_MATPLOTLIB:
            messagebox.showerror("Error", "matplotlib not available")
            return
        
        try:
            symbol = self.ts_symbol_var.get().strip().upper()
            days = int(self.ts_days_var.get())
            
            with self.engine.connect() as conn:
                df = pd.read_sql(text("""
                    SELECT ranking_date, rs_rating, momentum_score, trend_template_score,
                           technical_score, composite_score, composite_rank, composite_percentile
                    FROM stock_rankings_history
                    WHERE symbol = :symbol
                    ORDER BY ranking_date DESC
                    LIMIT :days
                """), conn, params={"symbol": symbol, "days": days})
            
            if df.empty:
                messagebox.showwarning("No Data", f"No data for {symbol}")
                return
            
            df = df.sort_values('ranking_date')
            df['ranking_date'] = pd.to_datetime(df['ranking_date'])
            
            self.ts_figure.clear()
            
            # Create 2x2 subplots
            axes = self.ts_figure.subplots(2, 2)
            self.ts_figure.suptitle(f"{symbol} - Rankings History ({len(df)} days)", fontsize=14)
            
            # All scores
            ax = axes[0, 0]
            ax.plot(df['ranking_date'], df['rs_rating'], label='RS Rating', linewidth=1.5)
            ax.plot(df['ranking_date'], df['momentum_score'], label='Momentum', linewidth=1.5)
            ax.plot(df['ranking_date'], df['technical_score'], label='Technical', linewidth=1.5)
            ax.set_title('Score History')
            ax.legend(loc='upper left', fontsize=8)
            ax.set_ylabel('Score')
            ax.grid(True, alpha=0.3)
            
            # Composite score
            ax = axes[0, 1]
            ax.fill_between(df['ranking_date'], df['composite_score'], alpha=0.3, color='#c0392b')
            ax.plot(df['ranking_date'], df['composite_score'], color='#c0392b', linewidth=2)
            ax.set_title('Composite Score')
            ax.set_ylabel('Score')
            ax.axhline(75, color='green', linestyle='--', alpha=0.5, label='Strong (75)')
            ax.axhline(50, color='orange', linestyle='--', alpha=0.5, label='Average (50)')
            ax.legend(fontsize=8)
            ax.grid(True, alpha=0.3)
            
            # Trend Template
            ax = axes[1, 0]
            ax.fill_between(df['ranking_date'], df['trend_template_score'], alpha=0.3, color='#9b59b6')
            ax.plot(df['ranking_date'], df['trend_template_score'], color='#9b59b6', linewidth=2)
            ax.set_title('Trend Template Score (0-8)')
            ax.set_ylabel('Score')
            ax.set_ylim(-0.5, 8.5)
            ax.axhline(6, color='green', linestyle='--', alpha=0.5, label='Strong (6+)')
            ax.legend(fontsize=8)
            ax.grid(True, alpha=0.3)
            
            # Composite Rank
            ax = axes[1, 1]
            ax.plot(df['ranking_date'], df['composite_rank'], color='#2c3e50', linewidth=2)
            ax.set_title('Composite Rank (lower = better)')
            ax.set_ylabel('Rank')
            ax.invert_yaxis()  # Lower rank is better
            ax.grid(True, alpha=0.3)
            
            self.ts_figure.tight_layout()
            self.ts_canvas.draw()
            
        except Exception as e:
            messagebox.showerror("Error", str(e))
    
    def _lookup_symbol(self):
        """Lookup rankings history for a symbol."""
        symbol = self.lookup_symbol_var.get().strip().upper()
        if not symbol:
            return
        
        # Clear tree
        for item in self.lookup_tree.get_children():
            self.lookup_tree.delete(item)
        
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text("""
                    SELECT ranking_date, rs_rating, momentum_score, trend_template_score,
                           technical_score, composite_score, composite_rank, composite_percentile
                    FROM stock_rankings_history
                    WHERE symbol = :symbol
                    ORDER BY ranking_date DESC
                    LIMIT 500
                """), {"symbol": symbol}).fetchall()
            
            for row in result:
                self.lookup_tree.insert("", tk.END, values=(
                    str(row[0]),
                    f"{row[1]:.1f}" if row[1] else "-",
                    f"{row[2]:.1f}" if row[2] else "-",
                    str(row[3]) if row[3] is not None else "-",
                    f"{row[4]:.1f}" if row[4] else "-",
                    f"{row[5]:.1f}" if row[5] else "-",
                    str(row[6]) if row[6] else "-",
                    f"{row[7]:.1f}%" if row[7] else "-",
                ))
                
        except Exception as e:
            messagebox.showerror("Error", str(e))
    
    def _run_quality_check(self):
        """Run data quality checks."""
        self.quality_text.delete("1.0", tk.END)
        self.quality_text.insert(tk.END, "Running quality checks...\n\n")
        self.root.update()
        
        try:
            checks = []
            checks.append("📋 DATA QUALITY REPORT")
            checks.append("=" * 60)
            
            with self.engine.connect() as conn:
                # Check 1: Null values
                checks.append("\n✅ NULL VALUE CHECK")
                checks.append("-" * 40)
                
                result = conn.execute(text("""
                    SELECT 
                        SUM(CASE WHEN rs_rating IS NULL THEN 1 ELSE 0 END) as null_rs,
                        SUM(CASE WHEN momentum_score IS NULL THEN 1 ELSE 0 END) as null_mom,
                        SUM(CASE WHEN trend_template_score IS NULL THEN 1 ELSE 0 END) as null_trend,
                        SUM(CASE WHEN technical_score IS NULL THEN 1 ELSE 0 END) as null_tech,
                        SUM(CASE WHEN composite_score IS NULL THEN 1 ELSE 0 END) as null_comp,
                        COUNT(*) as total
                    FROM stock_rankings_history
                """)).fetchone()
                
                total = result[5]
                checks.append(f"  RS Rating nulls:     {result[0]:,} ({result[0]/total*100:.2f}%)")
                checks.append(f"  Momentum nulls:      {result[1]:,} ({result[1]/total*100:.2f}%)")
                checks.append(f"  Trend Template nulls: {result[2]:,} ({result[2]/total*100:.2f}%)")
                checks.append(f"  Technical nulls:     {result[3]:,} ({result[3]/total*100:.2f}%)")
                checks.append(f"  Composite nulls:     {result[4]:,} ({result[4]/total*100:.2f}%)")
                
                # Check 2: Value ranges
                checks.append("\n✅ VALUE RANGE CHECK")
                checks.append("-" * 40)
                
                # RS Rating should be 0-100
                result = conn.execute(text("""
                    SELECT COUNT(*) FROM stock_rankings_history
                    WHERE rs_rating < 0 OR rs_rating > 100
                """)).fetchone()
                status = "✓ PASS" if result[0] == 0 else f"✗ FAIL ({result[0]} out of range)"
                checks.append(f"  RS Rating (0-100): {status}")
                
                # Momentum 0-100
                result = conn.execute(text("""
                    SELECT COUNT(*) FROM stock_rankings_history
                    WHERE momentum_score < 0 OR momentum_score > 100
                """)).fetchone()
                status = "✓ PASS" if result[0] == 0 else f"✗ FAIL ({result[0]} out of range)"
                checks.append(f"  Momentum (0-100): {status}")
                
                # Trend 0-8
                result = conn.execute(text("""
                    SELECT COUNT(*) FROM stock_rankings_history
                    WHERE trend_template_score < 0 OR trend_template_score > 8
                """)).fetchone()
                status = "✓ PASS" if result[0] == 0 else f"✗ FAIL ({result[0]} out of range)"
                checks.append(f"  Trend Template (0-8): {status}")
                
                # Technical 0-100
                result = conn.execute(text("""
                    SELECT COUNT(*) FROM stock_rankings_history
                    WHERE technical_score < 0 OR technical_score > 100
                """)).fetchone()
                status = "✓ PASS" if result[0] == 0 else f"✗ FAIL ({result[0]} out of range)"
                checks.append(f"  Technical (0-100): {status}")
                
                # Composite 0-100
                result = conn.execute(text("""
                    SELECT COUNT(*) FROM stock_rankings_history
                    WHERE composite_score < 0 OR composite_score > 100
                """)).fetchone()
                status = "✓ PASS" if result[0] == 0 else f"✗ FAIL ({result[0]} out of range)"
                checks.append(f"  Composite (0-100): {status}")
                
                # Check 3: Duplicates
                checks.append("\n✅ DUPLICATE CHECK")
                checks.append("-" * 40)
                
                result = conn.execute(text("""
                    SELECT symbol, ranking_date, COUNT(*) as cnt
                    FROM stock_rankings_history
                    GROUP BY symbol, ranking_date
                    HAVING COUNT(*) > 1
                    LIMIT 5
                """)).fetchall()
                
                if not result:
                    checks.append("  ✓ No duplicates found")
                else:
                    checks.append(f"  ✗ Found {len(result)} duplicate pairs (sample):")
                    for row in result:
                        checks.append(f"    - {row[0]} on {row[1]}: {row[2]} records")
                
                # Check 4: Date gaps
                checks.append("\n✅ DATE CONTINUITY CHECK")
                checks.append("-" * 40)
                
                result = conn.execute(text("""
                    SELECT ranking_date, gap FROM (
                        SELECT ranking_date, 
                               DATEDIFF(ranking_date, LAG(ranking_date) OVER (ORDER BY ranking_date)) as gap
                        FROM (SELECT DISTINCT ranking_date FROM stock_rankings_history) t
                    ) gaps
                    WHERE gap > 5
                    ORDER BY ranking_date DESC
                    LIMIT 5
                """)).fetchall()
                
                if not result:
                    checks.append("  ✓ No significant gaps (>5 days) found")
                else:
                    checks.append(f"  ⚠ Found gaps > 5 days:")
                    for row in result:
                        checks.append(f"    - {row[0]}: {row[1]} day gap before")
                
                # Check 5: Symbols coverage
                checks.append("\n✅ SYMBOL COVERAGE CHECK")
                checks.append("-" * 40)
                
                result = conn.execute(text("""
                    SELECT 
                        (SELECT COUNT(DISTINCT symbol) FROM stock_rankings_history) as ranked,
                        (SELECT COUNT(DISTINCT symbol) FROM yfinance_daily_quotes) as available
                """)).fetchone()
                
                coverage = result[0] / result[1] * 100 if result[1] > 0 else 0
                checks.append(f"  Ranked symbols: {result[0]:,}")
                checks.append(f"  Available symbols: {result[1]:,}")
                checks.append(f"  Coverage: {coverage:.1f}%")
                
            checks.append("\n" + "=" * 60)
            checks.append("✅ Quality check complete!")
            
            self.quality_text.delete("1.0", tk.END)
            self.quality_text.insert(tk.END, "\n".join(checks))
            
        except Exception as e:
            self.quality_text.delete("1.0", tk.END)
            self.quality_text.insert(tk.END, f"Error: {e}")
    
    def _coverage_report(self):
        """Generate coverage report."""
        self.quality_text.delete("1.0", tk.END)
        self.quality_text.insert(tk.END, "Generating coverage report...\n\n")
        self.root.update()
        
        try:
            report = []
            report.append("📊 COVERAGE REPORT - Symbols Per Day")
            report.append("=" * 60)
            
            with self.engine.connect() as conn:
                result = conn.execute(text("""
                    SELECT ranking_date, COUNT(*) as symbols
                    FROM stock_rankings_history
                    GROUP BY ranking_date
                    ORDER BY ranking_date DESC
                    LIMIT 60
                """)).fetchall()
            
            report.append(f"\n{'Date':<15} {'Symbols':>10} {'Bar':>35}")
            report.append("-" * 60)
            
            max_symbols = max(r[1] for r in result) if result else 1
            
            for row in result:
                bar_len = int(row[1] / max_symbols * 30)
                bar = "█" * bar_len
                report.append(f"{str(row[0]):<15} {row[1]:>10} {bar}")
            
            self.quality_text.delete("1.0", tk.END)
            self.quality_text.insert(tk.END, "\n".join(report))
            
        except Exception as e:
            self.quality_text.delete("1.0", tk.END)
            self.quality_text.insert(tk.END, f"Error: {e}")
    
    def run(self):
        """Run the GUI."""
        self.root.mainloop()


def main():
    """Main entry point."""
    gui = RankingsAnalyzerGUI()
    gui.run()


if __name__ == "__main__":
    main()
