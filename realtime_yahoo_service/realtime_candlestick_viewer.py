#!/usr/bin/env python3
"""
Real-time candlestick chart viewer using mplfinance
Connects to WebSocket and displays live candlestick charts
"""

import asyncio
import websockets
import json
import tkinter as tk
from tkinter import ttk
import pandas as pd
import mplfinance as mpf
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
from datetime import datetime
from collections import defaultdict
import threading

class RealtimeCandlestickViewer:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("📈 Real-Time Candlestick Chart Viewer")
        self.root.geometry("1400x900")
        
        # Data storage
        self.candle_data = defaultdict(list)
        self.current_symbol = None
        self.ws = None
        self.connected = False
        
        # Available symbols
        self.symbols = ['GC=F', 'SI=F', 'CL=F', 'ES=F', 'NQ=F', 'YM=F']
        
        self.create_widgets()
        
    def create_widgets(self):
        """Create UI widgets"""
        # Header frame
        header_frame = ttk.Frame(self.root, padding=10)
        header_frame.pack(fill=tk.X)
        
        # Title
        title_label = ttk.Label(header_frame, text="📈 Real-Time Candlestick Chart", 
                              font=('Arial', 16, 'bold'))
        title_label.pack(side=tk.LEFT)
        
        # Status
        self.status_label = ttk.Label(header_frame, text="● Disconnected", 
                                     foreground='red', font=('Arial', 10, 'bold'))
        self.status_label.pack(side=tk.RIGHT, padx=10)
        
        # Control frame
        control_frame = ttk.Frame(self.root, padding=10)
        control_frame.pack(fill=tk.X)
        
        ttk.Label(control_frame, text="Symbol:").pack(side=tk.LEFT, padx=5)
        
        self.symbol_var = tk.StringVar(value='GC=F')
        symbol_combo = ttk.Combobox(control_frame, textvariable=self.symbol_var, 
                                    values=self.symbols, width=15, state='readonly')
        symbol_combo.pack(side=tk.LEFT, padx=5)
        symbol_combo.bind('<<ComboboxSelected>>', lambda e: self.change_symbol())
        
        self.connect_btn = ttk.Button(control_frame, text="Connect", 
                                      command=self.connect)
        self.connect_btn.pack(side=tk.LEFT, padx=5)
        
        self.disconnect_btn = ttk.Button(control_frame, text="Disconnect", 
                                        command=self.disconnect, state='disabled')
        self.disconnect_btn.pack(side=tk.LEFT, padx=5)
        
        self.clear_btn = ttk.Button(control_frame, text="Clear Data", 
                                    command=self.clear_data)
        self.clear_btn.pack(side=tk.LEFT, padx=5)
        
        # Info label
        self.info_label = ttk.Label(control_frame, text="Data Points: 0 | Timeframe: 5m", 
                                   font=('Arial', 9))
        self.info_label.pack(side=tk.RIGHT, padx=10)
        
        # Stats frame
        stats_frame = ttk.LabelFrame(self.root, text="Current Stats", padding=10)
        stats_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self.stats_labels = {}
        stats_grid = ttk.Frame(stats_frame)
        stats_grid.pack()
        
        labels = ['Open', 'High', 'Low', 'Close', 'Volume', 'Change']
        for i, label in enumerate(labels):
            col = i % 3
            row = i // 3
            
            frame = ttk.Frame(stats_grid)
            frame.grid(row=row, column=col, padx=15, pady=5, sticky='w')
            
            ttk.Label(frame, text=f"{label}:", font=('Arial', 9, 'bold')).pack(side=tk.LEFT)
            self.stats_labels[label] = ttk.Label(frame, text="--", font=('Arial', 9))
            self.stats_labels[label].pack(side=tk.LEFT, padx=5)
        
        # Chart frame
        chart_frame = ttk.Frame(self.root, padding=10)
        chart_frame.pack(fill=tk.BOTH, expand=True)
        
        self.fig = Figure(figsize=(14, 7))
        self.canvas = FigureCanvasTkAgg(self.fig, master=chart_frame)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
        # Initial empty chart
        self.update_chart()
        
    def connect(self):
        """Connect to WebSocket"""
        self.current_symbol = self.symbol_var.get()
        self.connected = True
        
        self.status_label.config(text="● Connected", foreground='green')
        self.connect_btn.config(state='disabled')
        self.disconnect_btn.config(state='normal')
        
        # Start WebSocket in separate thread
        thread = threading.Thread(target=self.run_websocket, daemon=True)
        thread.start()
        
    def disconnect(self):
        """Disconnect from WebSocket"""
        self.connected = False
        self.status_label.config(text="● Disconnected", foreground='red')
        self.connect_btn.config(state='normal')
        self.disconnect_btn.config(state='disabled')
        
    def run_websocket(self):
        """Run WebSocket connection in thread"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(self.websocket_handler())
        
    async def websocket_handler(self):
        """Handle WebSocket connection"""
        try:
            async with websockets.connect('ws://localhost:8765') as ws:
                self.ws = ws
                while self.connected:
                    try:
                        message = await asyncio.wait_for(ws.recv(), timeout=1.0)
                        data = json.loads(message)
                        self.root.after(0, self.handle_message, data)
                    except asyncio.TimeoutError:
                        continue
                    except Exception as e:
                        print(f"Error receiving message: {e}")
                        break
        except Exception as e:
            print(f"WebSocket error: {e}")
            self.root.after(0, self.disconnect)
            
    def handle_message(self, message):
        """Process incoming WebSocket message"""
        try:
            data = message.get('data', message)
            symbol = data.get('symbol', '')
            
            print(f"Received data for {symbol}: O={data.get('open_price', 0):.2f} H={data.get('high_price', 0):.2f} L={data.get('low_price', 0):.2f} C={data.get('close_price', 0):.2f} V={data.get('volume', 0)}")
            
            # Only process data for selected symbol
            if symbol != self.current_symbol:
                return
                
            # Extract OHLCV data
            timestamp = data.get('timestamp', 0)
            if timestamp > 0:
                dt = datetime.fromtimestamp(timestamp)
            else:
                dt = datetime.now()
                
            open_price = data.get('open_price', data.get('open', 0))
            high_price = data.get('high_price', data.get('high', 0))
            low_price = data.get('low_price', data.get('low', 0))
            close_price = data.get('close_price', data.get('close', 0))
            volume = data.get('volume', 0)
            
            if all(v == 0 for v in [open_price, high_price, low_price, close_price]):
                return
            
            # Round timestamp to 5-minute intervals
            minute = dt.minute - (dt.minute % 5)
            rounded_dt = dt.replace(minute=minute, second=0, microsecond=0)
            
            # Check if we already have this candle
            existing_candles = self.candle_data[symbol]
            found = False
            
            for i, candle in enumerate(existing_candles):
                if candle['timestamp'] == rounded_dt:
                    # Update existing candle with latest data
                    existing_candles[i] = {
                        'timestamp': rounded_dt,
                        'open': candle['open'],  # Keep original open
                        'high': max(candle['high'], high_price),  # Update high
                        'low': min(candle['low'], low_price),  # Update low
                        'close': close_price,  # Update close
                        'volume': max(candle['volume'], volume)  # Update volume
                    }
                    found = True
                    break
            
            if not found:
                # Add new candle
                candle = {
                    'timestamp': rounded_dt,
                    'open': open_price,
                    'high': high_price,
                    'low': low_price,
                    'close': close_price,
                    'volume': volume
                }
                self.candle_data[symbol].append(candle)
                
                # Sort by timestamp
                self.candle_data[symbol].sort(key=lambda x: x['timestamp'])
            
            # Keep only last 100 candles
            if len(self.candle_data[symbol]) > 100:
                self.candle_data[symbol] = self.candle_data[symbol][-100:]
            
            # Update stats
            self.update_stats(data)
            
            # Update chart
            self.update_chart()
            
        except Exception as e:
            print(f"Error handling message: {e}")
            import traceback
            traceback.print_exc()
            
    def update_stats(self, data):
        """Update statistics display"""
        open_price = data.get('open_price', data.get('open', 0))
        high_price = data.get('high_price', data.get('high', 0))
        low_price = data.get('low_price', data.get('low', 0))
        close_price = data.get('close_price', data.get('close', 0))
        volume = data.get('volume', 0)
        prev_close = data.get('prev_close', open_price)
        
        change = close_price - prev_close
        change_pct = (change / prev_close * 100) if prev_close > 0 else 0
        
        self.stats_labels['Open'].config(text=f"${open_price:.2f}")
        self.stats_labels['High'].config(text=f"${high_price:.2f}")
        self.stats_labels['Low'].config(text=f"${low_price:.2f}")
        self.stats_labels['Close'].config(text=f"${close_price:.2f}")
        self.stats_labels['Volume'].config(text=self.format_volume(volume))
        
        change_text = f"{change:+.2f} ({change_pct:+.2f}%)"
        color = 'green' if change >= 0 else 'red'
        self.stats_labels['Change'].config(text=change_text, foreground=color)
        
    def format_volume(self, volume):
        """Format volume with K/M/B"""
        if volume == 0:
            return "-"
        if volume >= 1_000_000_000:
            return f"{volume/1_000_000_000:.2f}B"
        if volume >= 1_000_000:
            return f"{volume/1_000_000:.2f}M"
        if volume >= 1_000:
            return f"{volume/1_000:.2f}K"
        return str(volume)
        
    def update_chart(self):
        """Update candlestick chart"""
        try:
            if not self.current_symbol or not self.candle_data[self.current_symbol]:
                # Show empty chart
                self.fig.clear()
                ax = self.fig.add_subplot(111)
                ax.text(0.5, 0.5, 'No data available\nSelect a symbol and click Connect', 
                       ha='center', va='center', fontsize=14, color='gray')
                ax.set_xlim(0, 1)
                ax.set_ylim(0, 1)
                ax.axis('off')
                self.canvas.draw()
                return
                
            # Create DataFrame
            df = pd.DataFrame(self.candle_data[self.current_symbol])
            df.set_index('timestamp', inplace=True)
            df = df[['open', 'high', 'low', 'close', 'volume']]
            
            # Update info
            self.info_label.config(text=f"Data Points: {len(df)} | Timeframe: 5m | Symbol: {self.current_symbol}")
            
            # Custom style
            mc = mpf.make_marketcolors(up='#26a69a', down='#ef5350', 
                                      edge='inherit', wick='inherit', 
                                      volume='in')
            s = mpf.make_mpf_style(marketcolors=mc, gridstyle='--', 
                                  y_on_right=False)
            
            # Create new plot and get the figure
            import matplotlib.pyplot as plt
            fig, axes = mpf.plot(df, type='candle', style=s, volume=True,
                                title=f'{self.current_symbol} - Real-Time 5-Minute Candlestick Chart',
                                ylabel='Price ($)',
                                ylabel_lower='Volume',
                                figsize=(14, 7),
                                panel_ratios=(3, 1),
                                returnfig=True,
                                datetime_format='%H:%M',
                                xrotation=15)
            
            # Replace the old figure with the new one
            self.fig = fig
            self.canvas.figure = fig
            self.canvas.draw()
            
        except Exception as e:
            print(f"Error updating chart: {e}")
            import traceback
            traceback.print_exc()
            
    def change_symbol(self):
        """Change selected symbol"""
        new_symbol = self.symbol_var.get()
        if new_symbol != self.current_symbol:
            self.current_symbol = new_symbol
            if self.connected:
                self.update_chart()
                
    def clear_data(self):
        """Clear all data"""
        self.candle_data.clear()
        self.update_chart()
        for label in self.stats_labels.values():
            label.config(text="--", foreground='black')
        self.info_label.config(text="Data Points: 0 | Timeframe: 5m")
        
    def run(self):
        """Start the application"""
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.root.mainloop()
        
    def on_closing(self):
        """Handle window closing"""
        self.connected = False
        if self.ws:
            try:
                asyncio.run(self.ws.close())
            except:
                pass
        self.root.destroy()

if __name__ == "__main__":
    try:
        app = RealtimeCandlestickViewer()
        app.run()
    except KeyboardInterrupt:
        print("\nShutting down...")
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
