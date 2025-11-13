"""
Advanced PDF Generator for RSI Divergences with Candlestick Charts
================================================================

Features:
1. Candlestick price charts with divergence points marked
2. RSI-9 indicator below price chart
3. Divergence lines connecting fractal points on both price and RSI
4. Professional styling with proper legends
5. Latest date divergences only for EQ series stocks
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

def get_latest_divergences_with_data(limit=10):
    """Get latest date divergences for EQ series stocks with available data"""
    engine = rad.engine()
    
    with engine.connect() as conn:
        # Get latest divergence date
        latest_date_result = conn.execute(text('''
            SELECT MAX(signal_date) as latest_date
            FROM nse_rsi_divergences
        ''')).fetchone()
        
        latest_date = latest_date_result[0]
        print(f"📅 Latest divergence date: {latest_date}")
        
        # Get divergences with complete data for EQ series stocks
        divergences_query = text('''
            SELECT DISTINCT
                d.symbol,
                d.signal_type,
                d.signal_date,
                d.curr_fractal_date,
                d.curr_center_close,
                d.curr_center_rsi,
                d.comp_fractal_date, 
                d.comp_center_close,
                d.comp_center_rsi,
                d.buy_above_price,
                d.sell_below_price,
                b.close_price as current_price,
                b.ttl_trd_qnty as volume
            FROM nse_rsi_divergences d
            JOIN nse_equity_bhavcopy_full b ON d.symbol COLLATE utf8mb4_unicode_ci = b.symbol COLLATE utf8mb4_unicode_ci
            WHERE d.signal_date = :latest_date
                AND b.series = 'EQ'
                AND b.trade_date = (SELECT MAX(trade_date) FROM nse_equity_bhavcopy_full)
                AND EXISTS (
                    SELECT 1 FROM nse_rsi_daily r 
                    WHERE r.symbol COLLATE utf8mb4_unicode_ci = d.symbol COLLATE utf8mb4_unicode_ci
                    AND r.period = 9
                    AND r.trade_date >= DATE_SUB(:latest_date, INTERVAL 60 DAY)
                )
            ORDER BY b.ttl_trd_qnty DESC, d.signal_type
            LIMIT :limit
        ''')
        
        divergences_df = pd.read_sql(divergences_query, conn, params={
            'latest_date': latest_date, 
            'limit': limit
        })
        
        print(f"📊 Found {len(divergences_df)} divergences with complete data")
        return divergences_df, latest_date

def get_stock_data(symbol, days_back=90):
    """Get price and RSI-9 data for charting"""
    engine = rad.engine()
    
    with engine.connect() as conn:
        # Get price data (OHLCV)
        price_query = text('''
            SELECT trade_date, open_price, high_price, low_price, close_price, ttl_trd_qnty as volume
            FROM nse_equity_bhavcopy_full
            WHERE symbol COLLATE utf8mb4_unicode_ci = :symbol COLLATE utf8mb4_unicode_ci
                AND series = 'EQ'
                AND trade_date >= DATE_SUB((SELECT MAX(trade_date) FROM nse_equity_bhavcopy_full), INTERVAL :days_back DAY)
            ORDER BY trade_date
        ''')
        
        price_df = pd.read_sql(price_query, conn, params={'symbol': symbol, 'days_back': days_back})
        
        # Get RSI-9 data
        rsi_query = text('''
            SELECT trade_date, rsi
            FROM nse_rsi_daily
            WHERE symbol COLLATE utf8mb4_unicode_ci = :symbol COLLATE utf8mb4_unicode_ci
                AND period = 9
                AND trade_date >= DATE_SUB((SELECT MAX(trade_date) FROM nse_rsi_daily), INTERVAL :days_back DAY)
            ORDER BY trade_date
        ''')
        
        rsi_df = pd.read_sql(rsi_query, conn, params={'symbol': symbol, 'days_back': days_back})
        
        return price_df, rsi_df

def create_candlestick_chart(ax, price_df, title="Price Chart"):
    """Create candlestick chart on given axis"""
    # Convert to datetime
    price_df['trade_date'] = pd.to_datetime(price_df['trade_date'])
    
    # Create candlesticks
    for idx, row in price_df.iterrows():
        date = row['trade_date']
        open_price = row['open_price']
        high = row['high_price']
        low = row['low_price']
        close = row['close_price']
        
        # Color: green if close > open, red otherwise
        color = 'green' if float(close) >= float(open_price) else 'red'
        
        # Draw high-low line
        ax.plot([date, date], [float(low), float(high)], color='black', linewidth=0.8, alpha=0.8)
        
        # Draw body rectangle
        body_height = abs(float(close) - float(open_price))
        body_bottom = min(float(open_price), float(close))
        
        if body_height > 0:
            rect = Rectangle((date - timedelta(hours=8), body_bottom), 
                           timedelta(hours=16), body_height,
                           facecolor=color, edgecolor='black', 
                           alpha=0.7, linewidth=0.5)
            ax.add_patch(rect)
        else:
            # Doji - draw horizontal line
            ax.plot([date - timedelta(hours=8), date + timedelta(hours=8)], 
                   [float(close), float(close)], color='black', linewidth=1.5)
    
    ax.set_title(title, fontsize=12, fontweight='bold')
    ax.grid(True, alpha=0.3)
    ax.set_ylabel('Price (₹)', fontsize=10)

def create_divergence_chart(symbol, divergence_data, price_df, rsi_df, fig_size=(14, 10)):
    """Create comprehensive chart with price candlesticks, RSI, and divergence markings"""
    if price_df.empty or rsi_df.empty:
        return None
    
    # Create subplots: price (larger) and RSI (smaller)
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=fig_size, height_ratios=[3, 1], 
                                   gridspec_kw={'hspace': 0.3})
    
    # Convert dates
    price_df['trade_date'] = pd.to_datetime(price_df['trade_date'])
    rsi_df['trade_date'] = pd.to_datetime(rsi_df['trade_date'])
    
    # Create candlestick chart
    create_candlestick_chart(ax1, price_df, f"{symbol} - {divergence_data['signal_type']}")
    
    # Mark divergence points on price chart
    curr_fractal_date = pd.to_datetime(divergence_data['curr_fractal_date'])
    comp_fractal_date = pd.to_datetime(divergence_data['comp_fractal_date'])
    curr_price = divergence_data['curr_center_close']
    comp_price = divergence_data['comp_center_close']
    
    # Color based on divergence type
    signal_color = 'green' if 'Bullish' in divergence_data['signal_type'] else 'red'
    
    # Plot divergence points on price chart
    ax1.scatter([curr_fractal_date], [curr_price], color=signal_color, s=150, 
               marker='o', label='Current Fractal', zorder=5, edgecolor='black')
    ax1.scatter([comp_fractal_date], [comp_price], color=signal_color, s=150, 
               marker='s', label='Comparison Fractal', zorder=5, edgecolor='black')
    
    # Draw divergence line on price chart
    ax1.plot([comp_fractal_date, curr_fractal_date], [comp_price, curr_price], 
             color=signal_color, linestyle='--', linewidth=2, alpha=0.8, label='Price Trend')
    
    # Add buy/sell levels if available
    if pd.notna(divergence_data['buy_above_price']):
        ax1.axhline(y=divergence_data['buy_above_price'], color='green', linestyle=':', 
                   alpha=0.7, label=f"Buy Above: ₹{divergence_data['buy_above_price']:.2f}")
    
    if pd.notna(divergence_data['sell_below_price']):
        ax1.axhline(y=divergence_data['sell_below_price'], color='red', linestyle=':', 
                   alpha=0.7, label=f"Sell Below: ₹{divergence_data['sell_below_price']:.2f}")
    
    # Add current price info
    current_price = divergence_data['current_price']
    ax1.set_title(f"{symbol} - {divergence_data['signal_type']}\nCurrent: ₹{current_price:.2f} | Volume: {divergence_data['volume']:,}", 
                 fontsize=14, fontweight='bold')
    
    ax1.legend(loc='upper left', fontsize=9)
    
    # RSI Chart
    ax2.plot(rsi_df['trade_date'], rsi_df['rsi'], 'orange', linewidth=2, label='RSI-9')
    ax2.axhline(y=70, color='red', linestyle='-', alpha=0.5, label='Overbought (70)')
    ax2.axhline(y=30, color='green', linestyle='-', alpha=0.5, label='Oversold (30)')
    ax2.axhline(y=50, color='gray', linestyle=':', alpha=0.5, label='Midline (50)')
    
    # Mark divergence points on RSI chart
    curr_rsi = divergence_data['curr_center_rsi']
    comp_rsi = divergence_data['comp_center_rsi']
    
    ax2.scatter([curr_fractal_date], [curr_rsi], color=signal_color, s=120, 
               marker='o', zorder=5, edgecolor='black')
    ax2.scatter([comp_fractal_date], [comp_rsi], color=signal_color, s=120, 
               marker='s', zorder=5, edgecolor='black')
    
    # Draw divergence line on RSI chart
    ax2.plot([comp_fractal_date, curr_fractal_date], [comp_rsi, curr_rsi], 
             color=signal_color, linestyle='--', linewidth=2, alpha=0.8)
    
    ax2.set_title(f"RSI-9 Divergence | Current: {curr_rsi:.1f} vs Comparison: {comp_rsi:.1f}", fontsize=12)
    ax2.set_xlabel('Date', fontsize=10)
    ax2.set_ylabel('RSI', fontsize=10)
    ax2.set_ylim(0, 100)
    ax2.legend(loc='upper right', fontsize=9)
    ax2.grid(True, alpha=0.3)
    
    # Format dates
    ax1.xaxis.set_major_formatter(mdates.DateFormatter('%b %d'))
    ax2.xaxis.set_major_formatter(mdates.DateFormatter('%b %d'))
    ax1.xaxis.set_major_locator(mdates.WeekdayLocator(interval=2))
    ax2.xaxis.set_major_locator(mdates.WeekdayLocator(interval=2))
    
    plt.setp(ax1.xaxis.get_majorticklabels(), rotation=45)
    plt.setp(ax2.xaxis.get_majorticklabels(), rotation=45)
    
    plt.tight_layout()
    return fig

def create_summary_page(divergences_df, latest_date):
    """Create summary page with divergence statistics"""
    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(14, 10))
    
    # Signal type distribution
    signal_counts = divergences_df['signal_type'].value_counts()
    colors = ['green' if 'Bullish' in idx else 'red' for idx in signal_counts.index]
    
    wedges, texts, autotexts = ax1.pie(signal_counts.values, labels=signal_counts.index, 
                                      autopct='%1.1f%%', colors=colors, startangle=90)
    ax1.set_title(f'RSI Divergences Distribution\n{latest_date} (EQ Series)', 
                  fontsize=14, fontweight='bold')
    
    # RSI scatter plot - current vs comparison
    ax2.scatter(divergences_df['comp_center_rsi'], divergences_df['curr_center_rsi'], 
               c=['green' if 'Bullish' in sig else 'red' for sig in divergences_df['signal_type']], 
               alpha=0.7, s=80)
    ax2.plot([0, 100], [0, 100], 'k--', alpha=0.5, label='No Divergence Line')
    ax2.set_xlabel('Comparison RSI')
    ax2.set_ylabel('Current RSI')
    ax2.set_title('RSI Divergence Analysis', fontsize=14, fontweight='bold')
    ax2.grid(True, alpha=0.3)
    ax2.legend()
    ax2.set_xlim(0, 100)
    ax2.set_ylim(0, 100)
    
    # Price levels distribution
    price_data = []
    labels = []
    for _, row in divergences_df.iterrows():
        price_data.append(row['curr_center_close'])
        price_data.append(row['comp_center_close'])
        labels.extend([f"{row['symbol']} Current", f"{row['symbol']} Comparison"])
    
    ax3.hist(divergences_df['current_price'], bins=10, alpha=0.7, color='blue', 
             edgecolor='black', label='Current Prices')
    ax3.set_xlabel('Price (₹)')
    ax3.set_ylabel('Frequency')
    ax3.set_title('Current Price Distribution', fontsize=14, fontweight='bold')
    ax3.grid(True, alpha=0.3)
    ax3.legend()
    
    # Volume analysis
    top_volume = divergences_df.nlargest(10, 'volume')
    colors = ['green' if 'Bullish' in signal else 'red' for signal in top_volume['signal_type']]
    
    bars = ax4.barh(range(len(top_volume)), top_volume['volume'], color=colors, alpha=0.7)
    ax4.set_yticks(range(len(top_volume)))
    ax4.set_yticklabels([f"{row['symbol']}" for _, row in top_volume.iterrows()])
    ax4.set_xlabel('Volume')
    ax4.set_title('Stocks by Trading Volume', fontsize=14, fontweight='bold')
    ax4.grid(True, alpha=0.3, axis='x')
    
    # Add volume values as text
    for i, (_, row) in enumerate(top_volume.iterrows()):
        ax4.text(row['volume'], i, f" {row['volume']:,.0f}", 
                va='center', fontsize=8)
    
    plt.suptitle(f'RSI Divergences Report - {latest_date}\nCandlestick Charts with RSI-9 Analysis', 
                 fontsize=16, fontweight='bold', y=0.98)
    plt.tight_layout()
    
    return fig

def generate_advanced_pdf_report(max_stocks=10):
    """Generate advanced PDF with candlestick charts and RSI divergences"""
    print("🔍 Fetching latest RSI divergences data...")
    divergences_df, latest_date = get_latest_divergences_with_data(limit=max_stocks)
    
    if divergences_df.empty:
        print("❌ No divergences found with complete data")
        return
    
    pdf_filename = f"RSI_Divergences_Candlestick_{latest_date.strftime('%Y%m%d')}_EQ_Series.pdf"
    
    print(f"📄 Generating advanced PDF report: {pdf_filename}")
    print(f"📊 Including {len(divergences_df)} stocks with divergences...")
    
    with PdfPages(pdf_filename) as pdf:
        # Create summary page
        print("📋 Creating summary page...")
        summary_fig = create_summary_page(divergences_df, latest_date)
        pdf.savefig(summary_fig, bbox_inches='tight', dpi=150)
        plt.close(summary_fig)
        
        # Create individual stock pages
        successful_charts = 0
        for idx, (_, divergence_data) in enumerate(divergences_df.iterrows()):
            symbol = divergence_data['symbol']
            print(f"📈 Creating divergence chart for {symbol} ({idx+1}/{len(divergences_df)})...")
            
            try:
                # Get chart data
                price_df, rsi_df = get_stock_data(symbol, days_back=90)
                
                if not price_df.empty and not rsi_df.empty:
                    # Create chart
                    chart_fig = create_divergence_chart(symbol, divergence_data, price_df, rsi_df)
                    
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
    
    print(f"\n✅ Advanced PDF Report Generated Successfully!")
    print(f"📄 Filename: {pdf_filename}")
    print(f"📊 Total divergences processed: {len(divergences_df)}")
    print(f"📈 Successful charts: {successful_charts}")
    print(f"📅 Report Date: {latest_date}")
    
    # Print divergence summary
    bullish_count = len(divergences_df[divergences_df['signal_type'].str.contains('Bullish')])
    bearish_count = len(divergences_df[divergences_df['signal_type'].str.contains('Bearish')])
    
    print(f"\n📈 Hidden Bullish Divergences: {bullish_count}")
    print(f"📉 Hidden Bearish Divergences: {bearish_count}")
    print(f"💼 EQ Series Stocks Only")
    print(f"📊 Features: Candlestick Charts + RSI-9 + Divergence Lines")
    
    # Print stock details
    print(f"\n📋 Stocks with divergences:")
    for _, stock in divergences_df.iterrows():
        print(f"  {stock['symbol']}: {stock['signal_type']} | ₹{stock['current_price']:.2f} | Vol: {stock['volume']:,}")

if __name__ == "__main__":
    # Generate advanced PDF with candlestick charts and RSI divergences
    generate_advanced_pdf_report(max_stocks=10)