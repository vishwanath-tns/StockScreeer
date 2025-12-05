#!/usr/bin/env python3
"""
Mean Reversion Trade Visualizer
===============================

Generates detailed charts showing exactly when and why trades were executed
for the Mean Reversion strategies.

Usage:
    python analysis/visualize_trades.py --symbol RELIANCE --strategy bb

Dependencies:
    pip install matplotlib seaborn

Author: StockScreeer Project
"""

import sys
import os
import argparse
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.dates import DateFormatter
import seaborn as sns

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from analysis.mean_reversion_backtest import DataService, BacktestEngine

def plot_bollinger_strategy(df, symbol, output_dir="analysis/plots"):
    """Visualize Bollinger Band Mean Reversion Trades"""
    # Calculate Indicators
    data = df.copy()
    data['sma20'] = data['close'].rolling(window=20).mean()
    data['std20'] = data['close'].rolling(window=20).std()
    data['upper_bb'] = data['sma20'] + (2 * data['std20'])
    data['lower_bb'] = data['sma20'] - (2 * data['std20'])
    
    # Get Trades
    trades = BacktestEngine.run_bb_strategy(data)
    
    if not trades:
        print(f"No trades found for {symbol} (BB Strategy)")
        return

    # Setup Plot
    plt.style.use('bmh') # Clean style
    fig, ax = plt.subplots(figsize=(15, 8))
    
    # LIMIT DATA: Plot last 1 year (approx 252 trading days) for clarity 
    # unless trades are sparse, but let's stick to 1.5 years max.
    plot_data = data.tail(400)
    
    # 1. Price and Bands
    ax.plot(plot_data.index, plot_data['close'], label='Price', color='black', alpha=0.7, linewidth=1)
    ax.plot(plot_data.index, plot_data['upper_bb'], label='Upper BB', color='gray', alpha=0.3, linestyle='--')
    ax.plot(plot_data.index, plot_data['lower_bb'], label='Lower BB', color='blue', alpha=0.5, linestyle='-')
    ax.plot(plot_data.index, plot_data['sma20'], label='SMA 20', color='orange', alpha=0.5)
    
    # Fill between bands
    ax.fill_between(plot_data.index, plot_data['upper_bb'], plot_data['lower_bb'], color='gray', alpha=0.1)
    
    # 2. Plot Trades
    trade_count = 0
    
    for trade in trades:
        entry_date = trade['entry_date']
        exit_date = trade['exit_date']
        
        # Only plot if in range
        if entry_date >= plot_data.index[0] and exit_date <= plot_data.index[-1]:
            # Entry Marker
            ax.scatter(entry_date, plot_data.loc[entry_date]['close'], color='green', marker='^', s=120, zorder=5, label='Long Entry' if trade_count == 0 else "")
            
            # Exit Marker
            ax.scatter(exit_date, plot_data.loc[exit_date]['close'], color='red', marker='v', s=120, zorder=5, label='Long Exit' if trade_count == 0 else "")
            
            # Connecting Line (The Swing)
            color = 'green' if trade['return_pct'] > 0 else 'red'
            ax.plot([entry_date, exit_date], 
                   [plot_data.loc[entry_date]['close'], plot_data.loc[exit_date]['close']], 
                   color=color, linewidth=2, linestyle='--', alpha=0.7)
            
            trade_count += 1
            
    ax.set_title(f"{symbol} - Bollinger Band Mean Reversion (LONG ONLY)\nBuy Dip < Lower Band, Sell Rip > SMA 20", fontsize=14)
    ax.set_xlabel("Date")
    ax.set_ylabel("Price")
    # Improve legend handling to avoid duplicates
    handles, labels = ax.get_legend_handles_labels()
    by_label = dict(zip(labels, handles))
    ax.legend(by_label.values(), by_label.keys(), loc='best')
    ax.grid(True, alpha=0.3)
    
    # Format Date
    date_form = DateFormatter("%Y-%m")
    ax.xaxis.set_major_formatter(date_form)
    
    # Save
    os.makedirs(output_dir, exist_ok=True)
    filename = f"{output_dir}/BB_Trades_{symbol}.png"
    plt.tight_layout()
    plt.savefig(filename)
    plt.close()
    
    print(f"Generated chart: {filename} ({trade_count} trades shown)")


def plot_rsi_strategy(df, symbol, output_dir="analysis/plots"):
    """Visualize RSI Strategy Trades"""
    # Calculate Indicators
    data = df.copy()
    data['rsi2'] = BacktestEngine.calculate_rsi(data['close'], 2)
    data['sma5'] = data['close'].rolling(window=5).mean()
    
    trades = BacktestEngine.run_rsi_strategy(data)
    
    if not trades:
        print(f"No trades found for {symbol} (RSI Strategy)")
        return

    # Setup Plot (Two Panels)
    plt.style.use('bmh')
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(15, 10), gridspec_kw={'height_ratios': [3, 1]}, sharex=True)
    
    plot_data = data.tail(200) # RSI(2) is very high frequency, show less history
    
    # Panel 1: Price
    ax1.plot(plot_data.index, plot_data['close'], label='Price', color='black', alpha=0.8)
    ax1.plot(plot_data.index, plot_data['sma5'], label='SMA 5', color='orange', alpha=0.8)
    
    trade_count = 0
    for trade in trades:
        entry_date = trade['entry_date']
        exit_date = trade['exit_date']
        
        if entry_date >= plot_data.index[0] and exit_date <= plot_data.index[-1]:
            ax1.scatter(entry_date, plot_data.loc[entry_date]['close'], color='green', marker='^', s=120, zorder=5, label='Long Entry' if trade_count == 0 else "")
            ax1.scatter(exit_date, plot_data.loc[exit_date]['close'], color='red', marker='v', s=120, zorder=5, label='Long Exit' if trade_count == 0 else "")
            
            color = 'green' if trade['return_pct'] > 0 else 'red'
            ax1.plot([entry_date, exit_date], 
                   [plot_data.loc[entry_date]['close'], plot_data.loc[exit_date]['close']], 
                   color=color, linewidth=2, linestyle='--', alpha=0.7)
            trade_count += 1
            
    ax1.set_title(f"{symbol} - RSI(2) Mean Reversion (LONG ONLY)\nBuy: RSI(2)<10 | Sell: RSI(2)>90 or Close>SMA(5)")
    
    handles, labels = ax1.get_legend_handles_labels()
    by_label = dict(zip(labels, handles))
    ax1.legend(by_label.values(), by_label.keys(), loc='best')
    ax1.grid(True, alpha=0.3)
    
    # Panel 2: RSI
    ax2.plot(plot_data.index, plot_data['rsi2'], color='purple', linewidth=1.5)
    ax2.axhline(10, color='green', linestyle='--', alpha=0.5, label='Oversold (10)')
    ax2.axhline(90, color='red', linestyle='--', alpha=0.5, label='Overbought (90)')
    ax2.fill_between(plot_data.index, 0, 10, color='green', alpha=0.1)
    ax2.fill_between(plot_data.index, 90, 100, color='red', alpha=0.1)
    ax2.set_ylim(0, 100)
    ax2.set_ylabel("RSI(2)")
    ax2.legend(loc='lower right')
    ax2.grid(True, alpha=0.3)
    
    # Save
    os.makedirs(output_dir, exist_ok=True)
    filename = f"{output_dir}/RSI_Trades_{symbol}.png"
    plt.tight_layout()
    plt.savefig(filename)
    plt.close()
    
    print(f"Generated chart: {filename} ({trade_count} trades shown)")

def main():
    parser = argparse.ArgumentParser(description="Visualize Mean Reversion Trades")
    parser.add_argument('--symbol', type=str, required=True, help="Stock Symbol (e.g., RELIANCE)")
    parser.add_argument('--strategy', type=str, choices=['bb', 'rsi', 'both'], default='both', help="Strategy to visualize")
    
    args = parser.parse_args()
    
    symbol = args.symbol.upper()
    if not symbol.endswith('.NS') and not symbol.endswith('.BO'):
         # Simple heuristic for common Indian stocks
         # But DataService handles the .NS addition logic.
         pass
         
    service = DataService()
    print(f"Fetching data for {symbol}...")
    df = service.get_data(symbol)
    
    if df.empty:
        print("No data found.")
        return

    if args.strategy in ['bb', 'both']:
        plot_bollinger_strategy(df, symbol)
        
    if args.strategy in ['rsi', 'both']:
        plot_rsi_strategy(df, symbol)

if __name__ == "__main__":
    main()
