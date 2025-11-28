"""
Intraday Advance-Decline Offline Viewer
========================================

Offline viewer for historical intraday advance-decline data.
Reads from database and displays charts for any date.

Features:
- View any historical trading day
- Intraday advance-decline trends
- Market sentiment analysis
- Top gainers/losers at different times
"""

import os
import sys
from datetime import datetime, date, timedelta
from typing import List, Dict, Optional, Tuple
import tkinter as tk
from tkinter import ttk, messagebox
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL
from dotenv import load_dotenv
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment
load_dotenv()


class IntradayAdvDeclViewer:
    """Offline viewer for intraday advance-decline data"""
    
    def __init__(self, root):
        self.root = root
        self.root.title("Intraday Advance-Decline Offline Viewer")
        self.root.geometry("1200x900")
        
        # Database engine
        self.engine = self._create_engine()
        
        # Current data
        self.current_date = None
        self.breadth_data = None
        self.candle_data = None
        
        # UI setup
        self.setup_ui()
        
        # Load available dates
        self.load_available_dates()
    
    def _create_engine(self):
        """Create SQLAlchemy engine from environment variables"""
        url = URL.create(
            drivername="mysql+pymysql",
            username=os.getenv('MYSQL_USER', 'root'),
            password=os.getenv('MYSQL_PASSWORD', ''),
            host=os.getenv('MYSQL_HOST', 'localhost'),
            port=int(os.getenv('MYSQL_PORT', 3306)),
            database=os.getenv('MYSQL_DB', 'marketdata'),
            query={"charset": "utf8mb4"}
        )
        
        return create_engine(url, pool_pre_ping=True, pool_recycle=3600)
    
    def setup_ui(self):
        """Setup the user interface"""
        
        # Title bar
        title_frame = tk.Frame(self.root, bg='#2c3e50', height=60)
        title_frame.pack(fill=tk.X)
        title_frame.pack_propagate(False)
        
        title_label = tk.Label(
            title_frame,
            text="📊 Intraday Advance-Decline Viewer",
            font=('Segoe UI', 18, 'bold'),
            bg='#2c3e50',
            fg='white'
        )
        title_label.pack(pady=15)
        
        # Control panel
        control_frame = tk.Frame(self.root, bg='#ecf0f1', height=80)
        control_frame.pack(fill=tk.X, padx=10, pady=5)
        control_frame.pack_propagate(False)
        
        # Date selection
        tk.Label(
            control_frame,
            text="Select Date:",
            font=('Segoe UI', 11),
            bg='#ecf0f1'
        ).pack(side=tk.LEFT, padx=10)
        
        self.date_combo = ttk.Combobox(
            control_frame,
            font=('Segoe UI', 11),
            width=15,
            state='readonly'
        )
        self.date_combo.pack(side=tk.LEFT, padx=5)
        self.date_combo.bind('<<ComboboxSelected>>', self.on_date_selected)
        
        # Load button
        load_btn = tk.Button(
            control_frame,
            text="📈 Load Data",
            font=('Segoe UI', 11, 'bold'),
            bg='#3498db',
            fg='white',
            cursor='hand2',
            command=self.load_selected_date
        )
        load_btn.pack(side=tk.LEFT, padx=10)
        
        # Refresh dates button
        refresh_btn = tk.Button(
            control_frame,
            text="🔄 Refresh Dates",
            font=('Segoe UI', 10),
            bg='#95a5a6',
            fg='white',
            cursor='hand2',
            command=self.load_available_dates
        )
        refresh_btn.pack(side=tk.LEFT, padx=5)
        
        # Status label
        self.status_label = tk.Label(
            control_frame,
            text="Ready",
            font=('Segoe UI', 10),
            bg='#ecf0f1',
            fg='#7f8c8d'
        )
        self.status_label.pack(side=tk.RIGHT, padx=10)
        
        # Main content area
        content_frame = tk.Frame(self.root)
        content_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # Left panel - Chart
        chart_frame = tk.LabelFrame(
            content_frame,
            text="Intraday Advance-Decline Trend",
            font=('Segoe UI', 11, 'bold'),
            bg='white'
        )
        chart_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))
        
        # Create matplotlib figure
        self.fig = Figure(figsize=(10, 7), dpi=100)
        self.canvas = FigureCanvasTkAgg(self.fig, master=chart_frame)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Right panel - Summary & Statistics
        right_frame = tk.Frame(content_frame)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, padx=(5, 0))
        
        # Summary panel
        summary_frame = tk.LabelFrame(
            right_frame,
            text="Summary",
            font=('Segoe UI', 11, 'bold'),
            bg='white',
            width=300
        )
        summary_frame.pack(fill=tk.X, pady=(0, 5))
        summary_frame.pack_propagate(False)
        
        self.summary_text = tk.Text(
            summary_frame,
            height=12,
            font=('Consolas', 10),
            bg='#f8f9fa',
            relief=tk.FLAT,
            padx=10,
            pady=10
        )
        self.summary_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Statistics panel
        stats_frame = tk.LabelFrame(
            right_frame,
            text="Statistics",
            font=('Segoe UI', 11, 'bold'),
            bg='white'
        )
        stats_frame.pack(fill=tk.BOTH, expand=True)
        
        self.stats_text = tk.Text(
            stats_frame,
            font=('Consolas', 9),
            bg='#f8f9fa',
            relief=tk.FLAT,
            padx=10,
            pady=10
        )
        self.stats_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Bottom status bar
        status_bar = tk.Frame(self.root, bg='#34495e', height=30)
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        status_bar.pack_propagate(False)
        
        self.bottom_status = tk.Label(
            status_bar,
            text="Ready to load data",
            font=('Segoe UI', 9),
            bg='#34495e',
            fg='white'
        )
        self.bottom_status.pack(side=tk.LEFT, padx=10)
    
    def load_available_dates(self):
        """Load list of dates that have intraday data"""
        try:
            query = text("""
                SELECT DISTINCT trade_date
                FROM intraday_advance_decline
                ORDER BY trade_date DESC
            """)
            
            with self.engine.connect() as conn:
                result = conn.execute(query)
                dates = [row[0] for row in result]
            
            if dates:
                date_strings = [d.strftime('%Y-%m-%d') for d in dates]
                self.date_combo['values'] = date_strings
                self.date_combo.current(0)  # Select most recent date
                self.status_label.config(text=f"{len(dates)} dates available")
                logger.info(f"Loaded {len(dates)} dates with intraday data")
            else:
                self.date_combo['values'] = []
                self.status_label.config(text="No data available")
                messagebox.showwarning(
                    "No Data",
                    "No intraday advance-decline data found in database.\n\n"
                    "Please run the real-time dashboard first to collect data."
                )
        
        except Exception as e:
            logger.error(f"Failed to load available dates: {e}")
            messagebox.showerror("Error", f"Failed to load dates:\n{e}")
    
    def on_date_selected(self, event):
        """Handle date selection from dropdown"""
        self.status_label.config(text="Date selected. Click 'Load Data' to view.")
    
    def load_selected_date(self):
        """Load data for selected date"""
        selected = self.date_combo.get()
        if not selected:
            messagebox.showwarning("No Date", "Please select a date first")
            return
        
        try:
            selected_date = datetime.strptime(selected, '%Y-%m-%d').date()
            self.current_date = selected_date
            self.status_label.config(text=f"Loading {selected}...")
            self.bottom_status.config(text=f"Loading data for {selected}...")
            
            # Load breadth data
            self.load_breadth_data(selected_date)
            
            # Update display
            self.update_display()
            
            self.status_label.config(text=f"Loaded: {selected}")
            self.bottom_status.config(text=f"Displaying data for {selected}")
            
        except Exception as e:
            logger.error(f"Failed to load data: {e}")
            messagebox.showerror("Error", f"Failed to load data:\n{e}")
            self.status_label.config(text="Error loading data")
    
    def load_breadth_data(self, trade_date: date):
        """Load intraday breadth data for given date"""
        query = text("""
            SELECT 
                poll_time,
                advances,
                declines,
                unchanged,
                total_stocks,
                adv_pct,
                decl_pct,
                adv_decl_ratio,
                adv_decl_diff,
                market_sentiment
            FROM intraday_advance_decline
            WHERE trade_date = :trade_date
            ORDER BY poll_time
        """)
        
        with self.engine.connect() as conn:
            result = conn.execute(query, {'trade_date': trade_date})
            rows = result.fetchall()
        
        if not rows:
            messagebox.showinfo(
                "No Data",
                f"No intraday data found for {trade_date}"
            )
            self.breadth_data = None
            return
        
        # Convert to DataFrame
        self.breadth_data = pd.DataFrame(rows, columns=[
            'poll_time', 'advances', 'declines', 'unchanged', 'total_stocks',
            'adv_pct', 'decl_pct', 'adv_decl_ratio', 'adv_decl_diff', 'market_sentiment'
        ])
        
        logger.info(f"Loaded {len(self.breadth_data)} breadth snapshots for {trade_date}")
    
    def update_display(self):
        """Update all display components"""
        if self.breadth_data is None or len(self.breadth_data) == 0:
            return
        
        # Update chart
        self.plot_breadth_chart()
        
        # Update summary
        self.update_summary()
        
        # Update statistics
        self.update_statistics()
    
    def plot_breadth_chart(self):
        """Plot advance-decline chart"""
        if self.breadth_data is None or len(self.breadth_data) == 0:
            return
        
        self.fig.clear()
        
        df = self.breadth_data
        
        # Create subplots
        ax1 = self.fig.add_subplot(3, 1, 1)
        ax2 = self.fig.add_subplot(3, 1, 2)
        ax3 = self.fig.add_subplot(3, 1, 3)
        
        # Extract times for x-axis
        times = df['poll_time'].tolist()
        time_labels = [t.strftime('%H:%M') for t in times]
        
        # Plot 1: Advances vs Declines
        ax1.plot(times, df['advances'], 'g-', linewidth=2, label='Advances', marker='o')
        ax1.plot(times, df['declines'], 'r-', linewidth=2, label='Declines', marker='o')
        ax1.plot(times, df['unchanged'], 'gray', linewidth=1, label='Unchanged', linestyle='--')
        ax1.set_title(f'Intraday Advance-Decline: {self.current_date}', fontsize=12, fontweight='bold')
        ax1.set_ylabel('Count', fontsize=10)
        ax1.legend(loc='best')
        ax1.grid(True, alpha=0.3)
        
        # Plot 2: Advance %
        ax2.plot(times, df['adv_pct'], 'b-', linewidth=2, marker='o')
        ax2.axhline(y=50, color='gray', linestyle='--', alpha=0.5)
        ax2.fill_between(times, 50, df['adv_pct'], 
                          where=(df['adv_pct'] >= 50), 
                          color='green', alpha=0.2, label='Above 50%')
        ax2.fill_between(times, df['adv_pct'], 50,
                          where=(df['adv_pct'] < 50),
                          color='red', alpha=0.2, label='Below 50%')
        ax2.set_ylabel('Advance %', fontsize=10)
        ax2.set_ylim(0, 100)
        ax2.legend(loc='best')
        ax2.grid(True, alpha=0.3)
        
        # Plot 3: A/D Difference - use line plot instead of bar for clarity
        colors = ['green' if x >= 0 else 'red' for x in df['adv_decl_diff']]
        ax3.fill_between(times, 0, df['adv_decl_diff'], 
                         where=(df['adv_decl_diff'] >= 0),
                         color='green', alpha=0.3, label='Positive')
        ax3.fill_between(times, df['adv_decl_diff'], 0,
                         where=(df['adv_decl_diff'] < 0),
                         color='red', alpha=0.3, label='Negative')
        ax3.plot(times, df['adv_decl_diff'], 'b-', linewidth=2, marker='o', markersize=3)
        ax3.axhline(y=0, color='black', linestyle='-', linewidth=1.5)
        ax3.set_ylabel('A/D Difference', fontsize=10)
        ax3.set_xlabel('Time', fontsize=10)
        ax3.legend(loc='best')
        ax3.grid(True, alpha=0.3)
        
        # Format x-axis
        for ax in [ax1, ax2, ax3]:
            ax.set_xticks(times)
            ax.set_xticklabels(time_labels, rotation=45, ha='right')
        
        self.fig.tight_layout()
        self.canvas.draw()
    
    def update_summary(self):
        """Update summary text"""
        if self.breadth_data is None or len(self.breadth_data) == 0:
            return
        
        df = self.breadth_data
        
        # Latest snapshot
        latest = df.iloc[-1]
        
        # Opening snapshot
        opening = df.iloc[0]
        
        self.summary_text.delete('1.0', tk.END)
        
        summary = f"""
DATE: {self.current_date}

LATEST ({latest['poll_time'].strftime('%H:%M')}):
  Advances:   {latest['advances']:>4} ({latest['adv_pct']:.1f}%)
  Declines:   {latest['declines']:>4} ({latest['decl_pct']:.1f}%)
  Unchanged:  {latest['unchanged']:>4}
  Total:      {latest['total_stocks']:>4}
  
  A/D Ratio:  {latest['adv_decl_ratio']:.2f}
  A/D Diff:   {latest['adv_decl_diff']:+d}
  Sentiment:  {latest['market_sentiment']}

OPENING ({opening['poll_time'].strftime('%H:%M')}):
  Advances:   {opening['advances']:>4} ({opening['adv_pct']:.1f}%)
  Declines:   {opening['declines']:>4} ({opening['decl_pct']:.1f}%)
"""
        
        self.summary_text.insert('1.0', summary)
    
    def update_statistics(self):
        """Update statistics text"""
        if self.breadth_data is None or len(self.breadth_data) == 0:
            return
        
        df = self.breadth_data
        
        # Calculate statistics
        avg_adv = df['advances'].mean()
        avg_decl = df['declines'].mean()
        avg_adv_pct = df['adv_pct'].mean()
        max_adv_pct = df['adv_pct'].max()
        min_adv_pct = df['adv_pct'].min()
        
        max_adv_time = df.loc[df['adv_pct'].idxmax(), 'poll_time'].strftime('%H:%M')
        min_adv_time = df.loc[df['adv_pct'].idxmin(), 'poll_time'].strftime('%H:%M')
        
        # Trend analysis
        first_half = df.iloc[:len(df)//2]['adv_pct'].mean()
        second_half = df.iloc[len(df)//2:]['adv_pct'].mean()
        trend = "Strengthening" if second_half > first_half else "Weakening"
        
        # Sentiment distribution
        sentiment_counts = df['market_sentiment'].value_counts().to_dict()
        
        self.stats_text.delete('1.0', tk.END)
        
        stats = f"""
STATISTICS FOR {self.current_date}
{'='*40}

AVERAGES:
  Avg Advances:     {avg_adv:.1f}
  Avg Declines:     {avg_decl:.1f}
  Avg Advance %:    {avg_adv_pct:.1f}%

EXTREMES:
  Max Advance %:    {max_adv_pct:.1f}% at {max_adv_time}
  Min Advance %:    {min_adv_pct:.1f}% at {min_adv_time}
  Range:            {max_adv_pct - min_adv_pct:.1f}%

TREND:
  First Half Avg:   {first_half:.1f}%
  Second Half Avg:  {second_half:.1f}%
  Trend:            {trend}

SENTIMENT DISTRIBUTION:
"""
        
        for sentiment, count in sentiment_counts.items():
            pct = count / len(df) * 100
            stats += f"  {sentiment:20s} {count:3d} ({pct:.1f}%)\n"
        
        stats += f"\nDATA POINTS: {len(df)} snapshots\n"
        
        self.stats_text.insert('1.0', stats)


def main():
    """Main entry point"""
    root = tk.Tk()
    app = IntradayAdvDeclViewer(root)
    root.mainloop()


if __name__ == "__main__":
    main()
