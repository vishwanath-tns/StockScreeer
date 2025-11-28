#!/usr/bin/env python3
"""
Stock price chart with trend ratings indicator.
"""

import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.patches import Rectangle
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import reporting_adv_decl as rad
from sqlalchemy import text

def get_stock_data_with_ratings(symbol: str, days: int = 90) -> pd.DataFrame:
    """Get stock price data with trend ratings for charting."""
    engine = rad.engine()
    
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=days)
    
    with engine.connect() as conn:
        # Get price and rating data
        sql = text("""
        SELECT 
            p.trade_date,
            p.open_price,
            p.high_price,
            p.low_price,
            p.close_price,
            p.ttl_trd_qnty as volume,
            t.trend_rating,
            t.daily_trend,
            t.weekly_trend,
            t.monthly_trend
        FROM nse_equity_bhavcopy_full p
        LEFT JOIN trend_analysis t ON p.trade_date = t.trade_date AND p.symbol = t.symbol
        WHERE p.symbol = :symbol 
        AND p.series = 'EQ'
        AND p.trade_date >= :start_date
        AND p.trade_date <= :end_date
        ORDER BY p.trade_date
        """)
        
        df = pd.read_sql(sql, con=conn, params={
            'symbol': symbol,
            'start_date': start_date,
            'end_date': end_date
        })
        
        # Convert trade_date to datetime
        df['trade_date'] = pd.to_datetime(df['trade_date'])
        
        return df

def get_rating_color(rating):
    """Get color for rating based on value."""
    if pd.isna(rating):
        return 'gray'
    elif rating >= 8:
        return '#00AA00'  # Dark green - Very Bullish
    elif rating >= 5:
        return '#44CC44'  # Green - Bullish
    elif rating >= 2:
        return '#88DD88'  # Light green - Moderately Bullish
    elif rating >= -2:
        return '#FFAA00'  # Orange - Neutral/Mixed
    elif rating >= -5:
        return '#FF6666'  # Light red - Moderately Bearish
    elif rating >= -8:
        return '#CC3333'  # Red - Bearish
    else:
        return '#AA0000'  # Dark red - Very Bearish

def get_rating_label(rating):
    """Get descriptive label for rating."""
    if pd.isna(rating):
        return 'No Data'
    elif rating >= 8:
        return 'Very Bullish'
    elif rating >= 5:
        return 'Bullish'
    elif rating >= 2:
        return 'Mod. Bullish'
    elif rating >= -2:
        return 'Neutral'
    elif rating >= -5:
        return 'Mod. Bearish'
    elif rating >= -8:
        return 'Bearish'
    else:
        return 'Very Bearish'

def create_stock_chart_with_ratings(symbol: str, days: int = 90, save_path: str = None):
    """Create a stock chart with trend ratings indicator (no weekend gaps)."""
    
    print(f"Creating chart for {symbol} ({days} days)...")
    
    # Get data
    df = get_stock_data_with_ratings(symbol, days)
    
    if df.empty:
        print(f"No data found for {symbol}")
        return None
    
    print(f"Found {len(df)} data points")
    
    # Filter valid price data and sort by date
    valid_data = df.dropna(subset=['open_price', 'high_price', 'low_price', 'close_price']).copy()
    valid_data = valid_data.sort_values('trade_date').reset_index(drop=True)
    
    if valid_data.empty:
        print(f"No valid OHLC data for {symbol}")
        return None
    
    # Set up the figure with two subplots
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 10), 
                                   gridspec_kw={'height_ratios': [3, 1]})
    
    # Create continuous x-axis positions (0, 1, 2, 3...) to avoid weekend gaps
    x_positions = np.arange(len(valid_data))
    candle_width = 0.8
    
    # Upper chart - Stock Price (Candlestick-style) without gaps
    ax1.set_title(f'{symbol} - Stock Price with Trend Ratings (No Weekend Gaps)', fontsize=16, fontweight='bold')
    
    print(f"Plotting {len(valid_data)} candlesticks continuously...")
    
    # Plot candlestick chart using continuous positions
    for i, (idx, row) in enumerate(valid_data.iterrows()):
        x_pos = x_positions[i]
        open_price = row['open_price']
        high_price = row['high_price']
        low_price = row['low_price']
        close_price = row['close_price']
        
        # Determine candle color
        is_bullish = close_price >= open_price
        color = '#00AA00' if is_bullish else '#FF3333'
        edge_color = '#006600' if is_bullish else '#AA0000'
        
        # Plot high-low line (wick)
        ax1.plot([x_pos, x_pos], [low_price, high_price], color='black', linewidth=1, alpha=0.8)
        
        # Plot open-close rectangle (body)
        body_height = abs(close_price - open_price)
        body_bottom = min(open_price, close_price)
        
        if body_height > 0:
            rect = Rectangle((x_pos - candle_width/2, body_bottom), candle_width, body_height,
                           facecolor=color, edgecolor=edge_color, linewidth=1, alpha=0.9)
            ax1.add_patch(rect)
        else:
            # Doji candle
            ax1.plot([x_pos - candle_width/2, x_pos + candle_width/2], 
                     [close_price, close_price], color=edge_color, linewidth=2)
    
    # Format price chart
    ax1.set_ylabel('Price (₹)', fontsize=12)
    ax1.grid(True, alpha=0.3)
    
    # Custom x-axis labels (show every 5th date to avoid crowding)
    step = max(1, len(valid_data) // 10)
    tick_positions = x_positions[::step]
    tick_labels = [valid_data.iloc[i]['trade_date'].strftime('%Y-%m-%d') 
                   for i in range(0, len(valid_data), step)]
    
    ax1.set_xticks(tick_positions)
    ax1.set_xticklabels(tick_labels, rotation=45, ha='right')
    ax1.set_xlim(-0.5, len(valid_data) - 0.5)
    
    # Format price axis
    ax1.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'₹{x:.1f}'))
    
    # Lower chart - Trend Ratings (synchronized with price chart)
    ax2.set_title('Trend Ratings (-10 to +10)', fontsize=12)
    
    # Plot ratings using the same continuous positions
    ratings_data = []
    rating_positions = []
    
    for i, (idx, row) in enumerate(valid_data.iterrows()):
        if pd.notna(row.get('trend_rating')):
            ratings_data.append(row['trend_rating'])
            rating_positions.append(i)
    
    if ratings_data:
        ax2.plot(rating_positions, ratings_data, 
                color='purple', linewidth=3, marker='o', markersize=5, 
                label='Trend Rating', markerfacecolor='white', markeredgewidth=2)
        
        # Add color background for rating zones
        for i, rating in enumerate(ratings_data):
            x_pos = rating_positions[i]
            color = get_rating_color(rating)
            ax2.bar(x_pos, 22, bottom=-11, color=color, alpha=0.15, 
                   width=0.8, edgecolor='none')
    
    # Add horizontal lines for rating zones
    rating_zones = [
        (8, 'Very Bullish', '#00AA00'),
        (5, 'Bullish', '#44CC44'),
        (2, 'Mod. Bullish', '#88DD88'),
        (0, 'Neutral', '#FFAA00'),
        (-2, 'Neutral', '#FFAA00'),
        (-5, 'Mod. Bearish', '#FF6666'),
        (-8, 'Bearish', '#CC3333')
    ]
    
    for rating, label, color in rating_zones:
        ax2.axhline(y=rating, color=color, linestyle='--', alpha=0.5, linewidth=1)
        ax2.text(df['trade_date'].iloc[-1], rating, f'  {rating}', 
                verticalalignment='center', fontsize=9, alpha=0.7)
    
    ax2.set_ylabel('Rating', fontsize=12)
    ax2.set_ylim(-11, 11)
    ax2.grid(True, alpha=0.3)
    ax2.legend(loc='upper left')
    
    # Synchronize x-axis between both charts
    ax2.set_xticks(tick_positions)
    ax2.set_xticklabels(tick_labels, rotation=45, ha='right')
    ax2.set_xlim(-0.5, len(valid_data) - 0.5)
    
    # Add summary statistics
    if ratings_data:
        avg_rating = np.mean(ratings_data)
        latest_rating = ratings_data[-1]
        latest_price = valid_data['close_price'].iloc[-1]
        
        # Add text box with summary
        summary_text = f"""Latest: ₹{latest_price:.1f}
Rating: {latest_rating:.1f} ({get_rating_label(latest_rating)})
Avg Rating: {avg_rating:.1f}
Period: {days} days"""
        
        ax1.text(0.02, 0.98, summary_text, transform=ax1.transAxes, 
                verticalalignment='top', bbox=dict(boxstyle='round', facecolor='lightblue', alpha=0.8),
                fontsize=10)
    
    plt.tight_layout()
    
    # Save or show
    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        print(f"Chart saved to: {save_path}")
    else:
        plt.show()
    
    return fig

def create_multiple_stock_charts(symbols: list, days: int = 90):
    """Create charts for multiple stocks."""
    for symbol in symbols:
        print(f"\nCreating chart for {symbol}...")
        try:
            save_path = f"charts/{symbol}_trend_chart.png"
            create_stock_chart_with_ratings(symbol, days, save_path)
        except Exception as e:
            print(f"Error creating chart for {symbol}: {e}")

def test_charting():
    """Test the charting functionality."""
    print("Testing Stock Chart with Trend Ratings")
    print("=" * 50)
    
    # Create charts directory
    import os
    os.makedirs('charts', exist_ok=True)
    
    # Test with popular stocks
    test_symbols = ['RELIANCE', 'TCS', 'SBIN', 'INFY']
    
    for symbol in test_symbols:
        print(f"\nTesting {symbol}...")
        try:
            # Create chart (will display)
            fig = create_stock_chart_with_ratings(symbol, days=60)
            if fig:
                # Also save to file
                save_path = f"charts/{symbol}_trend_chart.png"
                fig.savefig(save_path, dpi=300, bbox_inches='tight')
                print(f"Chart saved: {save_path}")
                plt.close(fig)  # Close to prevent memory issues
        except Exception as e:
            print(f"Error with {symbol}: {e}")

if __name__ == "__main__":
    test_charting()