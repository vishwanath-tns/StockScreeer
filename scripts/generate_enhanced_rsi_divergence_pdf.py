"""
Enhanced PDF Generator for RSI Divergences - Grouped by Stock with Trading Table
===============================================================================

Features:
1. Groups multiple signals per stock into single charts
2. Comprehensive trading table with all buy/sell prices
3. Candlestick charts with multiple divergence points marked
4. RSI-9 indicator with all signal points
5. Summary statistics and trading recommendations
"""

import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.backends.backend_pdf import PdfPages
import numpy as np
import seaborn as sns
from matplotlib.patches import Rectangle
from datetime import datetime, timedelta
import reporting_adv_decl as rad
from sqlalchemy import text

# Set style for professional charts
plt.style.use('default')
sns.set_palette("husl")

def get_grouped_divergences_data(limit=15):
    """Get latest date divergences grouped by stock for EQ series"""
    engine = rad.engine()
    
    with engine.connect() as conn:
        # Get latest divergence date
        latest_date_result = conn.execute(text('''
            SELECT MAX(signal_date) as latest_date
            FROM nse_rsi_divergences
        ''')).fetchone()
        
        latest_date = latest_date_result[0]
        print(f"📅 Latest divergence date: {latest_date}")
        
        # Get mixed divergences (both bullish and bearish) for better verification
        # Get top Hidden Bullish signals
        bullish_query = text('''
            SELECT 
                d.symbol,
                COUNT(*) as signal_count,
                GROUP_CONCAT(DISTINCT d.signal_type ORDER BY d.signal_type) as signal_types,
                GROUP_CONCAT(d.curr_fractal_date ORDER BY d.id) as curr_fractal_dates,
                GROUP_CONCAT(d.curr_center_close ORDER BY d.id) as curr_center_closes,
                GROUP_CONCAT(d.curr_center_rsi ORDER BY d.id) as curr_center_rsis,
                GROUP_CONCAT(d.comp_fractal_date ORDER BY d.id) as comp_fractal_dates,
                GROUP_CONCAT(d.comp_center_close ORDER BY d.id) as comp_center_closes,
                GROUP_CONCAT(d.comp_center_rsi ORDER BY d.id) as comp_center_rsis,
                d.buy_above_price,
                d.sell_below_price,
                b.close_price as current_price,
                b.ttl_trd_qnty as volume,
                'bullish' as signal_category
            FROM nse_rsi_divergences d
            JOIN nse_equity_bhavcopy_full b ON d.symbol COLLATE utf8mb4_unicode_ci = b.symbol COLLATE utf8mb4_unicode_ci
            WHERE d.signal_date = :latest_date
                AND d.signal_type = 'Hidden Bullish Divergence'
                AND b.series = 'EQ'
                AND b.trade_date = (SELECT MAX(trade_date) FROM nse_equity_bhavcopy_full)
                AND EXISTS (
                    SELECT 1 FROM nse_rsi_daily r 
                    WHERE r.symbol COLLATE utf8mb4_unicode_ci = d.symbol COLLATE utf8mb4_unicode_ci
                    AND r.period = 9
                    AND r.trade_date >= DATE_SUB(:latest_date, INTERVAL 60 DAY)
                )
            GROUP BY d.symbol, d.buy_above_price, d.sell_below_price, b.close_price, b.ttl_trd_qnty
            ORDER BY b.ttl_trd_qnty DESC
            LIMIT :bullish_limit
        ''')
        
        # Get top Hidden Bearish signals  
        bearish_query = text('''
            SELECT 
                d.symbol,
                COUNT(*) as signal_count,
                GROUP_CONCAT(DISTINCT d.signal_type ORDER BY d.signal_type) as signal_types,
                GROUP_CONCAT(d.curr_fractal_date ORDER BY d.id) as curr_fractal_dates,
                GROUP_CONCAT(d.curr_center_close ORDER BY d.id) as curr_center_closes,
                GROUP_CONCAT(d.curr_center_rsi ORDER BY d.id) as curr_center_rsis,
                GROUP_CONCAT(d.comp_fractal_date ORDER BY d.id) as comp_fractal_dates,
                GROUP_CONCAT(d.comp_center_close ORDER BY d.id) as comp_center_closes,
                GROUP_CONCAT(d.comp_center_rsi ORDER BY d.id) as comp_center_rsis,
                d.buy_above_price,
                d.sell_below_price,
                b.close_price as current_price,
                b.ttl_trd_qnty as volume,
                'bearish' as signal_category
            FROM nse_rsi_divergences d
            JOIN nse_equity_bhavcopy_full b ON d.symbol COLLATE utf8mb4_unicode_ci = b.symbol COLLATE utf8mb4_unicode_ci
            WHERE d.signal_date = :latest_date
                AND d.signal_type = 'Hidden Bearish Divergence'
                AND b.series = 'EQ'
                AND b.trade_date = (SELECT MAX(trade_date) FROM nse_equity_bhavcopy_full)
                AND EXISTS (
                    SELECT 1 FROM nse_rsi_daily r 
                    WHERE r.symbol COLLATE utf8mb4_unicode_ci = d.symbol COLLATE utf8mb4_unicode_ci
                    AND r.period = 9
                    AND r.trade_date >= DATE_SUB(:latest_date, INTERVAL 60 DAY)
                )
            GROUP BY d.symbol, d.buy_above_price, d.sell_below_price, b.close_price, b.ttl_trd_qnty
            ORDER BY b.ttl_trd_qnty DESC
            LIMIT :bearish_limit
        ''')
        
        # Calculate limits for better mix
        bearish_limit = min(8, limit // 2)  # Up to 8 bearish signals
        bullish_limit = limit - bearish_limit  # Rest as bullish
        
        print(f"📊 Selecting {bullish_limit} bullish + {bearish_limit} bearish signals for better verification")
        
        # Get both types
        bullish_df = pd.read_sql(bullish_query, conn, params={
            'latest_date': latest_date, 
            'bullish_limit': bullish_limit
        })
        
        bearish_df = pd.read_sql(bearish_query, conn, params={
            'latest_date': latest_date, 
            'bearish_limit': bearish_limit
        })
        
        # Combine both dataframes
        divergences_df = pd.concat([bullish_df, bearish_df], ignore_index=True)
        
        print(f"📊 Found {len(bullish_df)} bullish + {len(bearish_df)} bearish = {len(divergences_df)} total stocks with divergences")
        
        # Get complete trading table data
        trading_table_query = text('''
            SELECT DISTINCT
                d.symbol,
                COUNT(*) as total_signals,
                GROUP_CONCAT(DISTINCT d.signal_type ORDER BY d.signal_type) as signal_types,
                d.buy_above_price,
                d.sell_below_price,
                b.close_price as current_price,
                b.ttl_trd_qnty as volume,
                CASE 
                    WHEN d.buy_above_price IS NOT NULL THEN 
                        ROUND(((d.buy_above_price - b.close_price) / b.close_price) * 100, 2)
                    WHEN d.sell_below_price IS NOT NULL THEN 
                        ROUND(((d.sell_below_price - b.close_price) / b.close_price) * 100, 2)
                    ELSE NULL
                END as distance_pct
            FROM nse_rsi_divergences d
            JOIN nse_equity_bhavcopy_full b ON d.symbol COLLATE utf8mb4_unicode_ci = b.symbol COLLATE utf8mb4_unicode_ci
            WHERE d.signal_date = :latest_date
                AND b.series = 'EQ'
                AND b.trade_date = (SELECT MAX(trade_date) FROM nse_equity_bhavcopy_full)
            GROUP BY d.symbol, d.buy_above_price, d.sell_below_price, b.close_price, b.ttl_trd_qnty
            ORDER BY b.ttl_trd_qnty DESC
        ''')
        
        trading_table_df = pd.read_sql(trading_table_query, conn, params={'latest_date': latest_date})
        
        return divergences_df, trading_table_df, latest_date

def get_stock_data(symbol, days_back=90):
    """Get price and RSI-9 data for charting"""
    engine = rad.engine()
    
    with engine.connect() as conn:
        # Get price data (OHLCV) - exclude weekends
        price_query = text('''
            SELECT trade_date, open_price, high_price, low_price, close_price, ttl_trd_qnty as volume
            FROM nse_equity_bhavcopy_full
            WHERE symbol COLLATE utf8mb4_unicode_ci = :symbol COLLATE utf8mb4_unicode_ci
                AND series = 'EQ'
                AND trade_date >= DATE_SUB((SELECT MAX(trade_date) FROM nse_equity_bhavcopy_full), INTERVAL :days_back DAY)
                AND DAYOFWEEK(trade_date) NOT IN (1, 7)  -- Exclude Sunday (1) and Saturday (7)
            ORDER BY trade_date
        ''')
        
        price_df = pd.read_sql(price_query, conn, params={'symbol': symbol, 'days_back': days_back})
        
        # Get RSI-9 data - exclude weekends
        rsi_query = text('''
            SELECT trade_date, rsi
            FROM nse_rsi_daily
            WHERE symbol COLLATE utf8mb4_unicode_ci = :symbol COLLATE utf8mb4_unicode_ci
                AND period = 9
                AND trade_date >= DATE_SUB((SELECT MAX(trade_date) FROM nse_rsi_daily), INTERVAL :days_back DAY)
                AND DAYOFWEEK(trade_date) NOT IN (1, 7)  -- Exclude Sunday (1) and Saturday (7)
            ORDER BY trade_date
        ''')
        
        rsi_df = pd.read_sql(rsi_query, conn, params={'symbol': symbol, 'days_back': days_back})
        
        return price_df, rsi_df

def create_candlestick_chart(ax, price_df, title="Price Chart"):
    """Create candlestick chart with even spacing for business days"""
    if price_df.empty:
        return
        
    # Convert to datetime and sort
    price_df = price_df.copy()
    price_df['trade_date'] = pd.to_datetime(price_df['trade_date'])
    price_df = price_df.sort_values('trade_date').reset_index(drop=True)
    
    # Create evenly spaced positions for business days
    n_days = len(price_df)
    positions = np.arange(n_days)
    
    # Create candlesticks with even spacing
    for i, (idx, row) in enumerate(price_df.iterrows()):
        x_pos = positions[i]
        open_price = float(row['open_price'])
        high = float(row['high_price'])
        low = float(row['low_price'])
        close = float(row['close_price'])
        
        # Color: green if close > open, red otherwise
        color = 'green' if close >= open_price else 'red'
        
        # Draw high-low line
        ax.plot([x_pos, x_pos], [low, high], color='black', linewidth=0.8, alpha=0.8)
        
        # Draw body rectangle
        body_height = abs(close - open_price)
        body_bottom = min(open_price, close)
        
        if body_height > 0:
            # Fixed width for even spacing
            rect = Rectangle((x_pos - 0.3, body_bottom), 
                           0.6, body_height,
                           facecolor=color, edgecolor='black', 
                           alpha=0.7, linewidth=0.5)
            ax.add_patch(rect)
        else:
            # Doji - draw horizontal line
            ax.plot([x_pos - 0.3, x_pos + 0.3], 
                   [close, close], color='black', linewidth=1.5)
    
    # Set custom x-axis labels with actual dates
    # Show every nth date to avoid overcrowding
    step = max(1, len(price_df) // 8)  # Show ~8 labels
    tick_positions = positions[::step]
    tick_labels = [price_df.iloc[i]['trade_date'].strftime('%b %d') for i in range(0, len(price_df), step)]
    
    ax.set_xticks(tick_positions)
    ax.set_xticklabels(tick_labels, rotation=45)
    
    ax.set_title(title, fontsize=12, fontweight='bold')
    ax.grid(True, alpha=0.3)
    ax.set_ylabel('Price (₹)', fontsize=10)
    
    # Return positions and dates for divergence plotting
    return positions, price_df['trade_date'].values

def parse_signal_data(stock_data):
    """Parse the grouped signal data into individual signals"""
    signals = []
    
    # Parse comma-separated values
    signal_types = stock_data['signal_types'].split(',') if stock_data['signal_types'] else []
    curr_dates = stock_data['curr_fractal_dates'].split(',') if stock_data['curr_fractal_dates'] else []
    curr_prices = [float(x) for x in stock_data['curr_center_closes'].split(',') if x] if stock_data['curr_center_closes'] else []
    curr_rsis = [float(x) for x in stock_data['curr_center_rsis'].split(',') if x] if stock_data['curr_center_rsis'] else []
    comp_dates = stock_data['comp_fractal_dates'].split(',') if stock_data['comp_fractal_dates'] else []
    comp_prices = [float(x) for x in stock_data['comp_center_closes'].split(',') if x] if stock_data['comp_center_closes'] else []
    comp_rsis = [float(x) for x in stock_data['comp_center_rsis'].split(',') if x] if stock_data['comp_center_rsis'] else []
    
    # Create individual signal objects
    for i in range(min(len(signal_types), len(curr_dates), len(curr_prices))):
        if i < len(comp_dates) and i < len(comp_prices) and i < len(comp_rsis):
            signals.append({
                'signal_type': signal_types[i].strip(),
                'curr_fractal_date': pd.to_datetime(curr_dates[i].strip()),
                'curr_center_close': curr_prices[i],
                'curr_center_rsi': curr_rsis[i] if i < len(curr_rsis) else 50,
                'comp_fractal_date': pd.to_datetime(comp_dates[i].strip()),
                'comp_center_close': comp_prices[i],
                'comp_center_rsi': comp_rsis[i]
            })
    
    return signals

def create_multi_divergence_chart(symbol, stock_data, price_df, rsi_df, fig_size=(14, 10)):
    """Create chart with multiple divergence signals for the same stock"""
    if price_df.empty or rsi_df.empty:
        return None
    
    # Create subplots: price (larger) and RSI (smaller)
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=fig_size, height_ratios=[3, 1], 
                                   gridspec_kw={'hspace': 0.3})
    
    # Convert dates and sort both dataframes
    price_df = price_df.copy()
    rsi_df = rsi_df.copy()
    price_df['trade_date'] = pd.to_datetime(price_df['trade_date'])
    rsi_df['trade_date'] = pd.to_datetime(rsi_df['trade_date'])
    price_df = price_df.sort_values('trade_date').reset_index(drop=True)
    rsi_df = rsi_df.sort_values('trade_date').reset_index(drop=True)
    
    # Create candlestick chart with even spacing
    signal_types_display = stock_data['signal_types'].replace(',', ' & ')
    chart_title = f"{symbol} - {signal_types_display} ({stock_data['signal_count']} signals)"
    
    positions, date_values = create_candlestick_chart(ax1, price_df, chart_title)
    
    # Create robust position mapping for date-based lookups
    date_to_position = {}
    position_to_date = {}
    
    for i, date in enumerate(date_values):
        date_normalized = pd.to_datetime(date).normalize()  # Remove time component
        date_to_position[date_normalized] = positions[i]
        position_to_date[positions[i]] = date_normalized
    
    # Parse individual signals
    signals = parse_signal_data(stock_data)
    
    # Plot all divergence points and lines on price chart
    for i, signal in enumerate(signals):
        # Color assignment based on specific signal types
        if signal['signal_type'] == 'Hidden Bullish Divergence':
            signal_color = 'green'
        elif signal['signal_type'] == 'Hidden Bearish Divergence':
            signal_color = 'red'
        else:
            # Fallback for any other signal types
            signal_color = 'green' if 'Bullish' in signal['signal_type'] else 'red'
        
        alpha = 0.7 - (i * 0.1)  # Slightly different opacity for multiple signals
        
        # Find positions for divergence dates with improved matching
        curr_date = pd.to_datetime(signal['curr_fractal_date']).normalize()
        comp_date = pd.to_datetime(signal['comp_fractal_date']).normalize()
        
        # Try exact match first, then closest match
        curr_pos = date_to_position.get(curr_date)
        comp_pos = date_to_position.get(comp_date)
        
        # If exact match not found, find closest date within reasonable range
        if curr_pos is None:
            min_diff = float('inf')
            for avail_date, pos in date_to_position.items():
                diff_days = abs((avail_date - curr_date).days)
                if diff_days <= 5 and diff_days < min_diff:  # Within 5 days
                    min_diff = diff_days
                    curr_pos = pos
        
        if comp_pos is None:
            min_diff = float('inf')
            for avail_date, pos in date_to_position.items():
                diff_days = abs((avail_date - comp_date).days)
                if diff_days <= 5 and diff_days < min_diff:  # Within 5 days
                    min_diff = diff_days
                    comp_pos = pos
        
        # Plot divergence points if positions found
        if curr_pos is not None:
            ax1.scatter([curr_pos], [signal['curr_center_close']], 
                       color=signal_color, s=120, marker='o', alpha=alpha, zorder=5, 
                       edgecolor='black', label=f"Signal {i+1} Current" if i < 3 else "")
        
        if comp_pos is not None:
            ax1.scatter([comp_pos], [signal['comp_center_close']], 
                       color=signal_color, s=120, marker='s', alpha=alpha, zorder=5, 
                       edgecolor='black', label=f"Signal {i+1} Comparison" if i < 3 else "")
        
        # Draw divergence line if both positions found
        if curr_pos is not None and comp_pos is not None:
            ax1.plot([comp_pos, curr_pos], 
                    [signal['comp_center_close'], signal['curr_center_close']], 
                    color=signal_color, linestyle='--', linewidth=1.5, alpha=alpha)
    
    # Add buy/sell levels if available
    if pd.notna(stock_data['buy_above_price']):
        ax1.axhline(y=stock_data['buy_above_price'], color='green', linestyle=':', 
                   alpha=0.8, linewidth=2, label=f"Buy Above: ₹{stock_data['buy_above_price']:.2f}")
    
    if pd.notna(stock_data['sell_below_price']):
        ax1.axhline(y=stock_data['sell_below_price'], color='red', linestyle=':', 
                   alpha=0.8, linewidth=2, label=f"Sell Below: ₹{stock_data['sell_below_price']:.2f}")
    
    # Add current price info
    current_price = stock_data['current_price']
    ax1.set_title(f"{symbol} - Multiple Divergence Signals\nCurrent: ₹{current_price:.2f} | Signals: {stock_data['signal_count']} | Volume: {stock_data['volume']:,}", 
                 fontsize=14, fontweight='bold')
    
    ax1.legend(loc='upper left', fontsize=9)
    
    # RSI Chart with matching positions
    # Merge RSI data with positions based on dates
    rsi_positions = []
    rsi_values = []
    
    for i, rsi_row in rsi_df.iterrows():
        rsi_date = pd.to_datetime(rsi_row['trade_date']).normalize()
        # Find matching position in price data
        rsi_pos = date_to_position.get(rsi_date)
        if rsi_pos is not None:
            rsi_positions.append(rsi_pos)
            rsi_values.append(rsi_row['rsi'])
    
    if rsi_positions:
        ax2.plot(rsi_positions, rsi_values, 'orange', linewidth=2, label='RSI-9')
        
        # Plot RSI divergence points using the same position mapping
        for i, signal in enumerate(signals):
            # Color assignment based on specific signal types (same as price chart)
            if signal['signal_type'] == 'Hidden Bullish Divergence':
                signal_color = 'green'
            elif signal['signal_type'] == 'Hidden Bearish Divergence':
                signal_color = 'red'
            else:
                # Fallback for any other signal types
                signal_color = 'green' if 'Bullish' in signal['signal_type'] else 'red'
            
            alpha = 0.7 - (i * 0.1)
            
            # Use the same positions found for price chart
            curr_date = pd.to_datetime(signal['curr_fractal_date']).normalize()
            comp_date = pd.to_datetime(signal['comp_fractal_date']).normalize()
            
            curr_rsi_pos = date_to_position.get(curr_date)
            comp_rsi_pos = date_to_position.get(comp_date)
            
            # If exact match not found, find closest (same logic as price chart)
            if curr_rsi_pos is None:
                min_diff = float('inf')
                for avail_date, pos in date_to_position.items():
                    diff_days = abs((avail_date - curr_date).days)
                    if diff_days <= 5 and diff_days < min_diff:
                        min_diff = diff_days
                        curr_rsi_pos = pos
            
            if comp_rsi_pos is None:
                min_diff = float('inf')
                for avail_date, pos in date_to_position.items():
                    diff_days = abs((avail_date - comp_date).days)
                    if diff_days <= 5 and diff_days < min_diff:
                        min_diff = diff_days
                        comp_rsi_pos = pos
            
            # Plot RSI divergence points
            if curr_rsi_pos is not None:
                ax2.scatter([curr_rsi_pos], [signal['curr_center_rsi']], 
                           color=signal_color, s=100, marker='o', alpha=alpha, zorder=5, edgecolor='black')
            
            if comp_rsi_pos is not None:
                ax2.scatter([comp_rsi_pos], [signal['comp_center_rsi']], 
                           color=signal_color, s=100, marker='s', alpha=alpha, zorder=5, edgecolor='black')
            
            # Draw RSI divergence line
            if curr_rsi_pos is not None and comp_rsi_pos is not None:
                ax2.plot([comp_rsi_pos, curr_rsi_pos], 
                        [signal['comp_center_rsi'], signal['curr_center_rsi']], 
                        color=signal_color, linestyle='--', linewidth=1.5, alpha=alpha)
    
    # RSI reference lines
    ax2.axhline(y=70, color='red', linestyle='-', alpha=0.5, label='Overbought (70)')
    ax2.axhline(y=30, color='green', linestyle='-', alpha=0.5, label='Oversold (30)')
    ax2.axhline(y=50, color='gray', linestyle=':', alpha=0.5, label='Midline (50)')
    
    ax2.set_title(f"RSI-9 with {len(signals)} Divergence Signals", fontsize=12)
    ax2.set_xlabel('Trading Days', fontsize=10)
    ax2.set_ylabel('RSI', fontsize=10)
    ax2.set_ylim(0, 100)
    ax2.legend(loc='upper left', fontsize=9)  # Changed from 'upper right' to 'upper left'
    ax2.grid(True, alpha=0.3)
    
    # Match x-axis for both charts
    if rsi_positions:
        ax2.set_xlim(ax1.get_xlim())
    
    plt.tight_layout()
    return fig

def create_trading_table_page(trading_table_df, latest_date):
    """Create a comprehensive trading table page"""
    fig, ax = plt.subplots(figsize=(14, 10))
    ax.axis('tight')
    ax.axis('off')
    
    # Prepare data for table
    table_data = []
    headers = ['Symbol', 'Signals', 'Signal Types', 'Current ₹', 'Buy Above ₹', 'Sell Below ₹', 'Distance %', 'Volume']
    
    for _, row in trading_table_df.head(50).iterrows():  # Show top 50
        buy_price = f"₹{row['buy_above_price']:.2f}" if pd.notna(row['buy_above_price']) else "-"
        sell_price = f"₹{row['sell_below_price']:.2f}" if pd.notna(row['sell_below_price']) else "-"
        distance = f"{row['distance_pct']:.1f}%" if pd.notna(row['distance_pct']) else "-"
        volume_str = f"{row['volume']:,.0f}" if row['volume'] >= 1000000 else f"{row['volume']:,.0f}"
        
        table_data.append([
            row['symbol'],
            str(int(row['total_signals'])),
            row['signal_types'][:20] + "..." if len(row['signal_types']) > 20 else row['signal_types'],
            f"₹{row['current_price']:.2f}",
            buy_price,
            sell_price,
            distance,
            volume_str
        ])
    
    # Create table with lower positioning to make room for title
    table = ax.table(cellText=table_data, colLabels=headers, loc='upper center', cellLoc='center')
    table.auto_set_font_size(False)
    table.set_fontsize(8)
    table.scale(1, 1.3)  # Reduced from 1.5 to make more compact

    # Style the table
    for i in range(len(headers)):
        table[(0, i)].set_facecolor('#4CAF50')
        table[(0, i)].set_text_props(weight='bold', color='white')

    # Color rows based on signal type
    for i, row in enumerate(trading_table_df.head(50).iterrows(), 1):
        _, data = row
        if 'Bullish' in str(data['signal_types']) and 'Bearish' not in str(data['signal_types']):
            color = '#E8F5E8'  # Light green for bullish only
        elif 'Bearish' in str(data['signal_types']) and 'Bullish' not in str(data['signal_types']):
            color = '#FFE8E8'  # Light red for bearish only
        else:
            color = '#FFF8E1'  # Light yellow for mixed signals
        
        for j in range(len(headers)):
            table[(i, j)].set_facecolor(color)

    # Position title much higher to avoid overlap
    plt.suptitle(f'RSI Divergence Trading Table - {latest_date}\nTop 50 EQ Series Stocks with Buy/Sell Levels', 
              fontsize=16, fontweight='bold', y=0.98)  # Moved higher from 0.95 to 0.98
    
    # Add some top margin to the axes to create space for title
    plt.subplots_adjust(top=0.88)  # Create space at top for title    # Add legend at bottom with more space from table
    legend_text = """
    Color Legend:
    🟢 Light Green: Bullish Signals Only    🔴 Light Red: Bearish Signals Only    🟡 Light Yellow: Mixed Signals
    
    Trading Guide:
    • Buy Above: Enter long position if price crosses above this level
    • Sell Below: Enter short position if price crosses below this level  
    • Distance %: Percentage distance from current price to trigger level
    """
    
    plt.figtext(0.02, 0.02, legend_text, fontsize=10, 
                bbox=dict(boxstyle="round,pad=0.5", facecolor="lightgray", alpha=0.8))
    
    return fig

def create_summary_page(divergences_df, trading_table_df, latest_date):
    """Create enhanced summary page with grouped statistics"""
    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(14, 10))
    
    # Signal count distribution per stock
    signal_counts = divergences_df['signal_count'].value_counts().sort_index()
    ax1.bar(signal_counts.index, signal_counts.values, color='skyblue', edgecolor='black', alpha=0.7)
    ax1.set_xlabel('Signals per Stock')
    ax1.set_ylabel('Number of Stocks')
    ax1.set_title('Signal Distribution\n(Signals per Stock)', fontsize=12, fontweight='bold')
    ax1.grid(True, alpha=0.3, axis='y')
    
    # Signal type distribution
    all_signal_types = []
    for types in divergences_df['signal_types']:
        if types:
            all_signal_types.extend([t.strip() for t in types.split(',')])
    
    signal_type_counts = pd.Series(all_signal_types).value_counts()
    colors = ['green' if 'Bullish' in idx else 'red' for idx in signal_type_counts.index]
    
    ax2.pie(signal_type_counts.values, labels=signal_type_counts.index, autopct='%1.1f%%', 
            colors=colors, startangle=90)
    ax2.set_title('Signal Types Distribution\n(All Signals)', fontsize=12, fontweight='bold')
    
    # Buy vs Sell opportunities
    buy_opportunities = trading_table_df[trading_table_df['buy_above_price'].notna()]
    sell_opportunities = trading_table_df[trading_table_df['sell_below_price'].notna()]
    
    opportunity_counts = [len(buy_opportunities), len(sell_opportunities)]
    opportunity_labels = [f'Buy Opportunities\n({len(buy_opportunities)} stocks)', 
                         f'Sell Opportunities\n({len(sell_opportunities)} stocks)']
    
    ax3.bar(opportunity_labels, opportunity_counts, color=['green', 'red'], alpha=0.7, edgecolor='black')
    ax3.set_ylabel('Number of Stocks')
    ax3.set_title('Trading Opportunities\n(Latest Date)', fontsize=12, fontweight='bold')
    ax3.grid(True, alpha=0.3, axis='y')
    
    # Volume distribution
    volume_bins = pd.cut(trading_table_df['volume'], bins=5, labels=['Very Low', 'Low', 'Medium', 'High', 'Very High'])
    volume_counts = volume_bins.value_counts()
    
    ax4.bar(volume_counts.index, volume_counts.values, color='purple', alpha=0.7, edgecolor='black')
    ax4.set_xlabel('Volume Category')
    ax4.set_ylabel('Number of Stocks')
    ax4.set_title('Volume Distribution\n(Trading Liquidity)', fontsize=12, fontweight='bold')
    ax4.grid(True, alpha=0.3, axis='y')
    plt.setp(ax4.xaxis.get_majorticklabels(), rotation=45)
    
    plt.suptitle(f'Enhanced RSI Divergences Summary - {latest_date}\nGrouped Analysis with Trading Table', 
                 fontsize=16, fontweight='bold', y=0.98)
    plt.tight_layout()
    
    return fig

def generate_enhanced_pdf_report(max_stocks=15):
    """Generate enhanced PDF with grouped signals and trading table"""
    try:
        print("🔍 Fetching grouped RSI divergences data...")
        divergences_df, trading_table_df, latest_date = get_grouped_divergences_data(limit=max_stocks)
        
        if divergences_df.empty:
            print("❌ No divergences found with complete data")
            return {
                'success': False,
                'error': 'No divergences found with complete data',
                'filename': None
            }
        
        pdf_filename = f"Enhanced_RSI_Divergences_Grouped_{latest_date.strftime('%Y%m%d')}_EQ_Series.pdf"
        
        print(f"📄 Generating enhanced PDF report: {pdf_filename}")
        print(f"📊 Including {len(divergences_df)} stocks with divergences...")
        print(f"📋 Trading table includes {len(trading_table_df)} stocks...")
        
    except Exception as e:
        print(f"❌ Error during data fetching: {str(e)}")
        return {
            'success': False,
            'error': f'Data fetching failed: {str(e)}',
            'filename': None
        }
    
    try:
        with PdfPages(pdf_filename) as pdf:
            # Create summary page
            print("📋 Creating enhanced summary page...")
            summary_fig = create_summary_page(divergences_df, trading_table_df, latest_date)
            pdf.savefig(summary_fig, bbox_inches='tight', dpi=150)
            plt.close(summary_fig)
            
            # Create trading table page
            print("📊 Creating comprehensive trading table...")
            trading_fig = create_trading_table_page(trading_table_df, latest_date)
            pdf.savefig(trading_fig, bbox_inches='tight', dpi=150)
            plt.close(trading_fig)
            
            # Create individual stock pages (grouped signals)
            successful_charts = 0
            for idx, (_, stock_data) in enumerate(divergences_df.iterrows()):
                symbol = stock_data['symbol']
                print(f"📈 Creating grouped chart for {symbol} ({idx+1}/{len(divergences_df)}) - {stock_data['signal_count']} signals...")
                
                try:
                    # Get chart data
                    price_df, rsi_df = get_stock_data(symbol, days_back=90)
                    
                    if not price_df.empty and not rsi_df.empty:
                        # Create chart with multiple signals
                        chart_fig = create_multi_divergence_chart(symbol, stock_data, price_df, rsi_df)
                        
                        if chart_fig:
                            pdf.savefig(chart_fig, bbox_inches='tight', dpi=150)
                            plt.close(chart_fig)
                            successful_charts += 1
                            print(f"✅ Chart created successfully for {symbol}")
                        else:
                            print(f"⚠️  Failed to create chart for {symbol}")
                    else:
                        print(f"⚠️  No chart data available for {symbol}")
                        
                except Exception as e:
                    print(f"❌ Error processing {symbol}: {e}")
                    continue
        
        print(f"\n✅ Enhanced PDF Report Generated Successfully!")
        print(f"📄 Filename: {pdf_filename}")
        print(f"📊 Total stocks with charts: {successful_charts}")
        print(f"📋 Trading table stocks: {len(trading_table_df)}")
        print(f"📅 Report Date: {latest_date}")
        
        # Print summary statistics
        total_signals = divergences_df['signal_count'].sum()
        unique_stocks = len(divergences_df)
        buy_opportunities = len(trading_table_df[trading_table_df['buy_above_price'].notna()])
        sell_opportunities = len(trading_table_df[trading_table_df['sell_below_price'].notna()])
        
        print(f"\n📈 Total Divergence Signals: {total_signals}")
        print(f"📊 Unique Stocks with Charts: {unique_stocks}")
        print(f"🟢 Buy Opportunities: {buy_opportunities}")
        print(f"🔴 Sell Opportunities: {sell_opportunities}")
        print(f"💼 EQ Series Stocks Only")
        print(f"📊 Features: Grouped Charts + Trading Table + RSI-9")
        
        # Return success information
        return {
            'success': True,
            'filename': pdf_filename,
            'total_stocks': successful_charts,
            'total_signals': total_signals,
            'buy_opportunities': buy_opportunities,
            'sell_opportunities': sell_opportunities
        }
        
    except Exception as e:
        print(f"❌ Error during PDF generation: {str(e)}")
        return {
            'success': False,
            'error': f'PDF generation failed: {str(e)}',
            'filename': pdf_filename if 'pdf_filename' in locals() else None
        }

if __name__ == "__main__":
    # Generate enhanced PDF with grouped signals and trading table
    generate_enhanced_pdf_report(max_stocks=15)