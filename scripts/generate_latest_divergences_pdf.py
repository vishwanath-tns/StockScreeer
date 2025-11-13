"""
Generate PDF Report for Latest Date RSI Divergences (EQ Series Only)
================================================================

Creates a professional PDF report with:
1. Summary of latest date divergences
2. Individual stock charts (Price + RSI)
3. Divergence details and trading levels
4. Only EQ series stocks from latest divergence date
"""

import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.backends.backend_pdf import PdfPages
import reporting_adv_decl as rad
from sqlalchemy import text
from datetime import datetime, timedelta
import numpy as np
import seaborn as sns

# Set style for professional charts
plt.style.use('default')
sns.set_palette("husl")

def get_latest_divergences_data():
    """Get latest date divergences for EQ series stocks only"""
    engine = rad.engine()
    
    with engine.connect() as conn:
        # Get latest divergence date
        latest_date_result = conn.execute(text('''
            SELECT MAX(signal_date) as latest_date
            FROM nse_rsi_divergences
        ''')).fetchone()
        
        latest_date = latest_date_result[0]
        print(f"📅 Latest divergence date: {latest_date}")
        
        # Get latest divergences for EQ series stocks only
        divergences_query = text('''
            SELECT DISTINCT
                d.symbol,
                d.signal_date,
                d.signal_type,
                d.curr_center_rsi as rsi_value,
                d.curr_center_close as price_level,
                d.buy_above_price as buy_level,
                d.sell_below_price as sell_level,
                'Daily' as timeframe,
                b.close_price as current_price,
                b.prev_close,
                b.open_price,
                b.high_price,
                b.low_price,
                b.ttl_trd_qnty as volume
            FROM nse_rsi_divergences d
            JOIN nse_equity_bhavcopy_full b 
                ON d.symbol = b.symbol COLLATE utf8mb4_unicode_ci
            WHERE d.signal_date = :latest_date
                AND b.series = 'EQ'
                AND b.trade_date = (SELECT MAX(trade_date) FROM nse_equity_bhavcopy_full)
            ORDER BY d.signal_type, d.symbol
        ''')
        
        divergences_df = pd.read_sql(divergences_query, conn, params={'latest_date': latest_date})
        print(f"📊 Found {len(divergences_df)} EQ series stocks with divergences on {latest_date}")
        
        return divergences_df, latest_date

def get_stock_chart_data(symbol, days_back=60):
    """Get price and RSI data for charting"""
    engine = rad.engine()
    
    with engine.connect() as conn:
        # Get price data
        price_query = text('''
            SELECT trade_date, open_price, high_price, low_price, close_price, ttl_trd_qnty as volume
            FROM nse_equity_bhavcopy_full
            WHERE symbol = :symbol COLLATE utf8mb4_unicode_ci
                AND series = 'EQ'
                AND trade_date >= DATE_SUB((SELECT MAX(trade_date) FROM nse_equity_bhavcopy_full), INTERVAL :days_back DAY)
            ORDER BY trade_date
        ''')
        
        price_df = pd.read_sql(price_query, conn, params={'symbol': symbol, 'days_back': days_back})
        
        # Get RSI data
        rsi_query = text('''
            SELECT trade_date, rsi
            FROM nse_rsi_daily
            WHERE symbol = :symbol COLLATE utf8mb4_unicode_ci
                AND period = 14
                AND trade_date >= DATE_SUB((SELECT MAX(trade_date) FROM nse_equity_bhavcopy_full), INTERVAL :days_back DAY)
            ORDER BY trade_date
        ''')
        
        rsi_df = pd.read_sql(rsi_query, conn, params={'symbol': symbol, 'days_back': days_back})
        
        return price_df, rsi_df

def create_stock_chart(symbol, divergence_data, price_df, rsi_df, fig_size=(12, 8)):
    """Create combined price and RSI chart for a stock"""
    if price_df.empty or rsi_df.empty:
        return None
        
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=fig_size, height_ratios=[2, 1])
    
    # Convert dates
    price_df['trade_date'] = pd.to_datetime(price_df['trade_date'])
    rsi_df['trade_date'] = pd.to_datetime(rsi_df['trade_date'])
    
    # Price chart (candlestick-style)
    ax1.plot(price_df['trade_date'], price_df['close_price'], 'b-', linewidth=2, label='Close Price')
    ax1.fill_between(price_df['trade_date'], price_df['low_price'], price_df['high_price'], 
                     alpha=0.3, color='lightblue', label='Day Range')
    
    # Add divergence signal point
    signal_date = pd.to_datetime(divergence_data['signal_date'])
    signal_price = divergence_data['price_level']
    
    signal_color = 'green' if 'Bullish' in divergence_data['signal_type'] else 'red'
    signal_marker = '^' if 'Bullish' in divergence_data['signal_type'] else 'v'
    
    ax1.scatter([signal_date], [signal_price], color=signal_color, s=200, 
                marker=signal_marker, label=f"Divergence Signal", zorder=5)
    
    # Add buy/sell levels if available
    if pd.notna(divergence_data['buy_level']):
        ax1.axhline(y=divergence_data['buy_level'], color='green', linestyle='--', 
                   alpha=0.7, label=f"Buy Level: ₹{divergence_data['buy_level']:.2f}")
    
    if pd.notna(divergence_data['sell_level']):
        ax1.axhline(y=divergence_data['sell_level'], color='red', linestyle='--', 
                   alpha=0.7, label=f"Sell Level: ₹{divergence_data['sell_level']:.2f}")
    
    ax1.set_title(f"{symbol} - {divergence_data['signal_type']}\nSignal Date: {divergence_data['signal_date']} | Current Price: ₹{divergence_data['current_price']:.2f}", 
                 fontsize=14, fontweight='bold')
    ax1.set_ylabel('Price (₹)', fontsize=12)
    ax1.legend(loc='upper left')
    ax1.grid(True, alpha=0.3)
    
    # RSI chart
    ax2.plot(rsi_df['trade_date'], rsi_df['rsi'], 'orange', linewidth=2)
    ax2.axhline(y=70, color='red', linestyle='-', alpha=0.5, label='Overbought (70)')
    ax2.axhline(y=30, color='green', linestyle='-', alpha=0.5, label='Oversold (30)')
    ax2.axhline(y=50, color='gray', linestyle=':', alpha=0.5)
    
    # Add RSI signal point
    ax2.scatter([signal_date], [divergence_data['rsi_value']], color=signal_color, 
               s=150, marker=signal_marker, zorder=5)
    
    ax2.set_title(f"RSI (14) - Signal RSI: {divergence_data['rsi_value']:.1f}", fontsize=12)
    ax2.set_xlabel('Date', fontsize=12)
    ax2.set_ylabel('RSI', fontsize=12)
    ax2.set_ylim(0, 100)
    ax2.legend(loc='upper right')
    ax2.grid(True, alpha=0.3)
    
    # Format dates
    ax1.xaxis.set_major_formatter(mdates.DateFormatter('%b %d'))
    ax2.xaxis.set_major_formatter(mdates.DateFormatter('%b %d'))
    
    plt.xticks(rotation=45)
    plt.tight_layout()
    
    return fig

def create_summary_page(divergences_df, latest_date):
    """Create summary page with statistics"""
    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(12, 10))
    
    # Count by signal type
    signal_counts = divergences_df['signal_type'].value_counts()
    colors = ['green' if 'Bullish' in idx else 'red' for idx in signal_counts.index]
    
    ax1.pie(signal_counts.values, labels=signal_counts.index, autopct='%1.1f%%', 
            colors=colors, startangle=90)
    ax1.set_title(f'Divergence Types Distribution\n({latest_date})', fontsize=14, fontweight='bold')
    
    # RSI value distribution
    ax2.hist(divergences_df['rsi_value'], bins=20, alpha=0.7, color='orange', edgecolor='black')
    ax2.axvline(x=30, color='green', linestyle='--', label='Oversold (30)')
    ax2.axvline(x=70, color='red', linestyle='--', label='Overbought (70)')
    ax2.set_title('RSI Value Distribution', fontsize=14, fontweight='bold')
    ax2.set_xlabel('RSI Value')
    ax2.set_ylabel('Frequency')
    ax2.legend()
    ax2.grid(True, alpha=0.3)
    
    # Price level distribution
    ax3.hist(divergences_df['current_price'], bins=20, alpha=0.7, color='blue', edgecolor='black')
    ax3.set_title('Current Price Distribution', fontsize=14, fontweight='bold')
    ax3.set_xlabel('Price (₹)')
    ax3.set_ylabel('Frequency')
    ax3.grid(True, alpha=0.3)
    
    # Top stocks by volume
    top_volume = divergences_df.nlargest(10, 'volume')[['symbol', 'volume', 'signal_type']]
    colors = ['green' if 'Bullish' in signal else 'red' for signal in top_volume['signal_type']]
    
    ax4.barh(range(len(top_volume)), top_volume['volume'], color=colors)
    ax4.set_yticks(range(len(top_volume)))
    ax4.set_yticklabels(top_volume['symbol'])
    ax4.set_title('Top 10 Stocks by Volume', fontsize=14, fontweight='bold')
    ax4.set_xlabel('Volume')
    ax4.grid(True, alpha=0.3, axis='x')
    
    plt.suptitle(f'RSI Divergences Report - {latest_date}\nEQ Series Stocks Only', 
                 fontsize=16, fontweight='bold', y=0.98)
    plt.tight_layout()
    
    return fig

def generate_pdf_report(max_stocks=50):
    """Generate comprehensive PDF report for latest divergences"""
    print("🔍 Fetching latest divergences data...")
    divergences_df, latest_date = get_latest_divergences_data()
    
    if divergences_df.empty:
        print("❌ No divergences found for latest date")
        return
    
    # Limit number of stocks for PDF size management
    if len(divergences_df) > max_stocks:
        print(f"📝 Limiting to top {max_stocks} stocks by volume...")
        divergences_df = divergences_df.nlargest(max_stocks, 'volume')
    
    # Sort by signal type and volume for better organization
    divergences_df = divergences_df.sort_values(['signal_type', 'volume'], ascending=[True, False])
    
    pdf_filename = f"RSI_Divergences_Latest_{latest_date.strftime('%Y%m%d')}_EQ_Series.pdf"
    
    print(f"📄 Generating PDF report: {pdf_filename}")
    print(f"📊 Including {len(divergences_df)} stocks...")
    
    with PdfPages(pdf_filename) as pdf:
        # Create summary page
        print("📋 Creating summary page...")
        summary_fig = create_summary_page(divergences_df, latest_date)
        pdf.savefig(summary_fig, bbox_inches='tight')
        plt.close(summary_fig)
        
        # Create individual stock pages
        successful_charts = 0
        for idx, (_, row) in enumerate(divergences_df.iterrows()):
            symbol = row['symbol']
            print(f"📈 Creating chart for {symbol} ({idx+1}/{len(divergences_df)})...")
            
            try:
                # Get chart data
                price_df, rsi_df = get_stock_chart_data(symbol, days_back=60)
                
                if not price_df.empty and not rsi_df.empty:
                    # Create chart
                    chart_fig = create_stock_chart(symbol, row, price_df, rsi_df)
                    
                    if chart_fig:
                        pdf.savefig(chart_fig, bbox_inches='tight')
                        plt.close(chart_fig)
                        successful_charts += 1
                    else:
                        print(f"⚠️  Failed to create chart for {symbol}")
                else:
                    print(f"⚠️  No data available for {symbol}")
                    
            except Exception as e:
                print(f"❌ Error processing {symbol}: {e}")
                continue
    
    print(f"\n✅ PDF Report Generated Successfully!")
    print(f"📄 Filename: {pdf_filename}")
    print(f"📊 Total stocks processed: {len(divergences_df)}")
    print(f"📈 Successful charts: {successful_charts}")
    print(f"📅 Report Date: {latest_date}")
    
    # Print summary statistics
    bullish_count = len(divergences_df[divergences_df['signal_type'].str.contains('Bullish')])
    bearish_count = len(divergences_df[divergences_df['signal_type'].str.contains('Bearish')])
    
    print(f"\n📈 Hidden Bullish Divergences: {bullish_count}")
    print(f"📉 Hidden Bearish Divergences: {bearish_count}")
    print(f"💼 EQ Series Stocks Only")
    print(f"📍 Latest Date Focus: {latest_date}")

if __name__ == "__main__":
    # Generate PDF for latest divergences (max 10 stocks for testing)
    generate_pdf_report(max_stocks=10)