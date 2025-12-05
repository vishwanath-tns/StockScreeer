"""
Volume Events Visualization GUI
Shows all high volume events for a stock with forward returns (positive and negative)
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
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
from datetime import datetime


class VolumeEventsGUI:
    """GUI for visualizing volume events and forward returns."""
    
    def __init__(self, root):
        self.root = root
        self.root.title("Volume Cluster Events Analyzer")
        self.root.geometry("1400x900")
        
        load_dotenv()
        self.engine = self._create_engine()
        self.symbols = self._load_symbols()
        self.current_df = None
        
        self._create_ui()
        
        if self.symbols:
            self.symbol_var.set(self.symbols[0])
            self.load_stock_data()
    
    def _create_engine(self):
        password = quote_plus(os.getenv('MYSQL_PASSWORD', ''))
        host = os.getenv('MYSQL_HOST', 'localhost')
        port = os.getenv('MYSQL_PORT', '3306')
        db = os.getenv('MYSQL_DB', 'marketdata')
        user = os.getenv('MYSQL_USER', 'root')
        return create_engine(f'mysql+pymysql://{user}:{password}@{host}:{port}/{db}')
    
    def _load_symbols(self):
        query = "SELECT DISTINCT symbol FROM volume_cluster_events ORDER BY symbol"
        with self.engine.connect() as conn:
            result = conn.execute(text(query))
            return [row[0] for row in result]
    
    def _create_ui(self):
        control_frame = ttk.Frame(self.root, padding="10")
        control_frame.pack(fill=tk.X)
        
        ttk.Label(control_frame, text="Symbol:").pack(side=tk.LEFT, padx=5)
        self.symbol_var = tk.StringVar()
        symbol_combo = ttk.Combobox(control_frame, textvariable=self.symbol_var, 
                                     values=self.symbols, width=20, state='readonly')
        symbol_combo.pack(side=tk.LEFT, padx=5)
        symbol_combo.bind('<<ComboboxSelected>>', lambda e: self.load_stock_data())
        
        ttk.Label(control_frame, text="Quintile:").pack(side=tk.LEFT, padx=(20, 5))
        self.quintile_var = tk.StringVar(value="Very High")
        quintile_combo = ttk.Combobox(control_frame, textvariable=self.quintile_var,
                                       values=["All", "High", "Very High"], width=12, state='readonly')
        quintile_combo.pack(side=tk.LEFT, padx=5)
        quintile_combo.bind('<<ComboboxSelected>>', lambda e: self.load_stock_data())
        
        ttk.Button(control_frame, text="Refresh", command=self.load_stock_data).pack(side=tk.LEFT, padx=20)
        
        self.stats_label = ttk.Label(control_frame, text="", font=('Arial', 10))
        self.stats_label.pack(side=tk.RIGHT, padx=10)
        
        main_paned = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        main_paned.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        left_frame = ttk.Frame(main_paned)
        main_paned.add(left_frame, weight=1)
        
        table_label = ttk.Label(left_frame, text="Volume Events", font=('Arial', 11, 'bold'))
        table_label.pack(anchor=tk.W, pady=(0, 5))
        
        tree_frame = ttk.Frame(left_frame)
        tree_frame.pack(fill=tk.BOTH, expand=True)
        
        columns = ('date', 'volume', 'quintile', 'day_ret', '1d', '1w', '2w', '3w', '1m')
        self.tree = ttk.Treeview(tree_frame, columns=columns, show='headings', height=20)
        
        self.tree.heading('date', text='Date')
        self.tree.heading('volume', text='Volume')
        self.tree.heading('quintile', text='Quintile')
        self.tree.heading('day_ret', text='Day %')
        self.tree.heading('1d', text='1D %')
        self.tree.heading('1w', text='1W %')
        self.tree.heading('2w', text='2W %')
        self.tree.heading('3w', text='3W %')
        self.tree.heading('1m', text='1M %')
        
        self.tree.column('date', width=90)
        self.tree.column('volume', width=100)
        self.tree.column('quintile', width=80)
        self.tree.column('day_ret', width=60)
        self.tree.column('1d', width=60)
        self.tree.column('1w', width=60)
        self.tree.column('2w', width=60)
        self.tree.column('3w', width=60)
        self.tree.column('1m', width=60)
        
        scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        right_frame = ttk.Frame(main_paned)
        main_paned.add(right_frame, weight=2)
        
        self.fig = Figure(figsize=(10, 8), dpi=100)
        self.canvas = FigureCanvasTkAgg(self.fig, master=right_frame)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
        stats_frame = ttk.LabelFrame(self.root, text="Return Statistics", padding="10")
        stats_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self.stats_text = tk.Text(stats_frame, height=6, font=('Courier', 10))
        self.stats_text.pack(fill=tk.X)
    
    def load_stock_data(self):
        symbol = self.symbol_var.get()
        quintile = self.quintile_var.get()
        
        if not symbol:
            return
        
        query = "SELECT * FROM volume_cluster_events WHERE symbol = :symbol"
        params = {'symbol': symbol}
        
        if quintile != "All":
            query += " AND volume_quintile = :quintile"
            params['quintile'] = quintile
        
        query += " ORDER BY event_date DESC"
        
        with self.engine.connect() as conn:
            self.current_df = pd.read_sql(text(query), conn, params=params)
        
        if self.current_df.empty:
            messagebox.showinfo("No Data", f"No volume events found for {symbol}")
            return
        
        self._update_table()
        self._update_charts()
        self._update_statistics()
        
        n_events = len(self.current_df)
        self.stats_label.config(text=f"{n_events} events")
    
    def _update_table(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        for _, row in self.current_df.iterrows():
            date_str = row['event_date'].strftime('%Y-%m-%d') if pd.notna(row['event_date']) else ''
            volume_str = f"{row['volume']:,.0f}" if pd.notna(row['volume']) else ''
            
            def fmt_ret(val):
                if pd.isna(val):
                    return ''
                return f"{val:+.1f}"
            
            values = (
                date_str,
                volume_str,
                row['volume_quintile'],
                fmt_ret(row['day_return']),
                fmt_ret(row['return_1d']),
                fmt_ret(row['return_1w']),
                fmt_ret(row['return_2w']),
                fmt_ret(row['return_3w']),
                fmt_ret(row['return_1m']),
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
            
            self.tree.insert('', tk.END, values=values, tags=(tag,))
        
        self.tree.tag_configure('very_positive', background='#90EE90')
        self.tree.tag_configure('positive', background='#E8F5E9')
        self.tree.tag_configure('negative', background='#FFEBEE')
        self.tree.tag_configure('very_negative', background='#EF9A9A')
    
    def _update_charts(self):
        self.fig.clear()
        
        if self.current_df.empty:
            return
        
        ax1 = self.fig.add_subplot(2, 2, 1)
        ax2 = self.fig.add_subplot(2, 2, 2)
        ax3 = self.fig.add_subplot(2, 2, 3)
        ax4 = self.fig.add_subplot(2, 2, 4)
        
        symbol = self.symbol_var.get()
        
        returns_1m = self.current_df['return_1m'].dropna()
        if len(returns_1m) > 0:
            ax1.hist(returns_1m, bins=30, edgecolor='black', alpha=0.7, 
                    color='green' if returns_1m.mean() > 0 else 'red')
            ax1.axvline(x=0, color='black', linestyle='--', linewidth=1)
            ax1.axvline(x=returns_1m.mean(), color='blue', linestyle='-', linewidth=2, 
                       label=f'Mean: {returns_1m.mean():.1f}%')
            ax1.set_xlabel('1-Month Return (%)')
            ax1.set_ylabel('Frequency')
            ax1.set_title(f'{symbol} - 1M Return Distribution after High Volume')
            ax1.legend()
        
        periods = ['return_1d', 'return_1w', 'return_2w', 'return_3w', 'return_1m']
        period_labels = ['1D', '1W', '2W', '3W', '1M']
        data_for_box = [self.current_df[p].dropna() for p in periods]
        
        bp = ax2.boxplot(data_for_box, labels=period_labels, patch_artist=True)
        for patch in bp['boxes']:
            patch.set_facecolor('lightblue')
        ax2.axhline(y=0, color='red', linestyle='--', linewidth=1)
        ax2.set_ylabel('Return (%)')
        ax2.set_title('Return Distribution by Period')
        
        win_rates = []
        for p in periods:
            valid = self.current_df[p].dropna()
            win_rate = (valid > 0).mean() * 100 if len(valid) > 0 else 0
            win_rates.append(win_rate)
        
        bars = ax3.bar(period_labels, win_rates, color=['green' if w > 50 else 'red' for w in win_rates])
        ax3.axhline(y=50, color='black', linestyle='--', linewidth=1)
        ax3.set_ylabel('Win Rate (%)')
        ax3.set_title('Percentage of Positive Returns by Period')
        ax3.set_ylim(0, 100)
        
        for bar, rate in zip(bars, win_rates):
            ax3.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1,
                    f'{rate:.0f}%', ha='center', va='bottom', fontsize=9)
        
        mask = self.current_df['day_return'].notna() & self.current_df['return_1m'].notna()
        if mask.sum() > 0:
            x = self.current_df.loc[mask, 'day_return']
            y = self.current_df.loc[mask, 'return_1m']
            
            colors = ['green' if yi > 0 else 'red' for yi in y]
            ax4.scatter(x, y, c=colors, alpha=0.5, edgecolors='black', linewidth=0.5)
            ax4.axhline(y=0, color='gray', linestyle='--', linewidth=1)
            ax4.axvline(x=0, color='gray', linestyle='--', linewidth=1)
            ax4.set_xlabel('Same Day Return (%)')
            ax4.set_ylabel('1-Month Forward Return (%)')
            ax4.set_title('Day Return vs 1M Forward Return')
        
        self.fig.tight_layout()
        self.canvas.draw()
    
    def _update_statistics(self):
        if self.current_df.empty:
            self.stats_text.delete(1.0, tk.END)
            return
        
        self.stats_text.delete(1.0, tk.END)
        
        periods = [('1D', 'return_1d'), ('1W', 'return_1w'), ('2W', 'return_2w'), 
                   ('3W', 'return_3w'), ('1M', 'return_1m')]
        
        header = "  Period |    Mean   |  Median   |   Std     |  Win%   |  Lose%  |   Min     |   Max\n"
        self.stats_text.insert(tk.END, header)
        self.stats_text.insert(tk.END, "-" * 85 + "\n")
        
        for label, col in periods:
            valid = self.current_df[col].dropna()
            if len(valid) == 0:
                continue
            
            mean_val = valid.mean()
            median_val = valid.median()
            std_val = valid.std()
            win_pct = (valid > 0).mean() * 100
            lose_pct = (valid < 0).mean() * 100
            min_val = valid.min()
            max_val = valid.max()
            
            line = f"  {label:>5}  | {mean_val:>+7.2f}% | {median_val:>+7.2f}% | {std_val:>7.2f}% | {win_pct:>5.1f}% | {lose_pct:>5.1f}% | {min_val:>+7.1f}% | {max_val:>+7.1f}%\n"
            self.stats_text.insert(tk.END, line)


def main():
    root = tk.Tk()
    app = VolumeEventsGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
