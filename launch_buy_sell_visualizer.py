#!/usr/bin/env python
"""
Launch Buy/Sell Pressure Visualizer
====================================
Real-time visualization of total_buy_qty and total_sell_qty from FNO quotes.

Features:
- Chart 1: Buy Qty (green) and Sell Qty (red) lines
- Chart 2: Net Pressure (Buy - Sell) with color coding
- Symbol selector dropdown
- Scrollable history for the day
- Real-time updates from Redis

Requirements:
- Redis must be running with quotes being published
- FNO Feed must be running (launch_fno_feed.py or launch_fno_feed_subprocess.py)

Usage:
    python launch_buy_sell_visualizer.py
"""

if __name__ == '__main__':
    from dhan_trading.visualizers.buy_sell_pressure import main
    main()
