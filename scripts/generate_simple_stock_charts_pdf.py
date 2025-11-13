"""
Simple PDF Generator for Stock Charts with RSI Divergences - Demo Version
========================================================================

Creates a PDF with 10 sample stocks showing Price + RSI charts
Focuses on stocks with complete data availability
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

def get_sample_stocks_with_data():
    """Get 10 sample stocks that have both price and RSI data"""
    engine = rad.engine()
    
    with engine.connect() as conn:
        # Get stocks that definitely exist in both tables
        query = text('''
            SELECT DISTINCT b.symbol, 
                   b.close_price as current_price,
                   b.ttl_trd_qnty as volume,
                   r.rsi as current_rsi
            FROM nse_equity_bhavcopy_full b
            JOIN nse_rsi_daily r ON b.symbol COLLATE utf8mb4_unicode_ci = r.symbol COLLATE utf8mb4_unicode_ci
            WHERE b.series = 'EQ'
                AND r.period = 14
                AND b.trade_date = (SELECT MAX(trade_date) FROM nse_equity_bhavcopy_full)
                AND r.trade_date = (SELECT MAX(trade_date) FROM nse_rsi_daily)
                AND b.ttl_trd_qnty > 1000000
            ORDER BY b.ttl_trd_qnty DESC
            LIMIT 10
        ''')
        
        stocks_df = pd.read_sql(query, conn)
        print(f"📊 Found {len(stocks_df)} stocks with complete data")
        
        # Add mock divergence information for demo
        stocks_df['signal_date'] = '2025-11-07'
        stocks_df['signal_type'] = stocks_df['current_rsi'].apply(
            lambda x: 'Hidden Bullish Divergence' if x < 50 else 'Hidden Bearish Divergence'
        )
        stocks_df['rsi_value'] = stocks_df['current_rsi']
        stocks_df['price_level'] = stocks_df['current_price']
        stocks_df['buy_level'] = stocks_df['current_price'] * 1.02
        stocks_df['sell_level'] = stocks_df['current_price'] * 0.98
        
        return stocks_df

def get_stock_chart_data(symbol, days_back=60):
    """Get price and RSI data for charting"""
    engine = rad.engine()
    
    with engine.connect() as conn:
        # Get price data
        price_query = text('''
            SELECT trade_date, open_price, high_price, low_price, close_price, ttl_trd_qnty as volume
            FROM nse_equity_bhavcopy_full
            WHERE symbol COLLATE utf8mb4_unicode_ci = :symbol COLLATE utf8mb4_unicode_ci
                AND series = 'EQ'
                AND trade_date >= DATE_SUB((SELECT MAX(trade_date) FROM nse_equity_bhavcopy_full), INTERVAL :days_back DAY)
            ORDER BY trade_date
        ''')
        
        price_df = pd.read_sql(price_query, conn, params={'symbol': symbol, 'days_back': days_back})
        
        # Get RSI data
        rsi_query = text('''
            SELECT trade_date, rsi
            FROM nse_rsi_daily
            WHERE symbol COLLATE utf8mb4_unicode_ci = :symbol COLLATE utf8mb4_unicode_ci
                AND period = 14
                AND trade_date >= DATE_SUB((SELECT MAX(trade_date) FROM nse_rsi_daily), INTERVAL :days_back DAY)
            ORDER BY trade_date
        ''')
        
        rsi_df = pd.read_sql(rsi_query, conn, params={'symbol': symbol, 'days_back': days_back})
        
        return price_df, rsi_df

def create_stock_chart(symbol, stock_data, price_df, rsi_df, fig_size=(12, 8)):
    """Create combined price and RSI chart for a stock"""
    if price_df.empty or rsi_df.empty:
        return None
        
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=fig_size, height_ratios=[2, 1])
    
    # Convert dates
    price_df['trade_date'] = pd.to_datetime(price_df['trade_date'])
    rsi_df['trade_date'] = pd.to_datetime(rsi_df['trade_date'])
    
    # Price chart (line chart)
    ax1.plot(price_df['trade_date'], price_df['close_price'], 'b-', linewidth=2, label='Close Price')
    ax1.fill_between(price_df['trade_date'], price_df['low_price'], price_df['high_price'], 
                     alpha=0.3, color='lightblue', label='Day Range')
    
    # Add current price point
    latest_date = price_df['trade_date'].iloc[-1]
    latest_price = price_df['close_price'].iloc[-1]
    
    signal_color = 'green' if 'Bullish' in stock_data['signal_type'] else 'red'
    signal_marker = '^' if 'Bullish' in stock_data['signal_type'] else 'v'
    
    ax1.scatter([latest_date], [latest_price], color=signal_color, s=200, 
                marker=signal_marker, label=f"Current Signal", zorder=5)
    
    # Add buy/sell levels
    ax1.axhline(y=stock_data['buy_level'], color='green', linestyle='--', 
               alpha=0.7, label=f"Buy Level: ₹{stock_data['buy_level']:.2f}")
    ax1.axhline(y=stock_data['sell_level'], color='red', linestyle='--', 
               alpha=0.7, label=f"Sell Level: ₹{stock_data['sell_level']:.2f}")
    
    ax1.set_title(f"{symbol} - {stock_data['signal_type']}\nCurrent Price: ₹{stock_data['current_price']:.2f} | Volume: {stock_data['volume']:,}", 
                 fontsize=14, fontweight='bold')
    ax1.set_ylabel('Price (₹)', fontsize=12)
    ax1.legend(loc='upper left')
    ax1.grid(True, alpha=0.3)
    
    # RSI chart
    ax2.plot(rsi_df['trade_date'], rsi_df['rsi'], 'orange', linewidth=2, label='RSI (14)')
    ax2.axhline(y=70, color='red', linestyle='-', alpha=0.5, label='Overbought (70)')
    ax2.axhline(y=30, color='green', linestyle='-', alpha=0.5, label='Oversold (30)')
    ax2.axhline(y=50, color='gray', linestyle=':', alpha=0.5, label='Midline (50)')
    
    # Add current RSI point
    latest_rsi = rsi_df['rsi'].iloc[-1]
    ax2.scatter([latest_date], [latest_rsi], color=signal_color, 
               s=150, marker=signal_marker, zorder=5)
    
    ax2.set_title(f"RSI (14) - Current RSI: {stock_data['rsi_value']:.1f}", fontsize=12)
    ax2.set_xlabel('Date', fontsize=12)
    ax2.set_ylabel('RSI', fontsize=12)
    ax2.set_ylim(0, 100)
    ax2.legend(loc='upper right')
    ax2.grid(True, alpha=0.3)
    
    # Format dates
    ax1.xaxis.set_major_formatter(mdates.DateFormatter('%b %d'))
    ax2.xaxis.set_major_formatter(mdates.DateFormatter('%b %d'))
    ax1.xaxis.set_major_locator(mdates.WeekdayLocator(interval=1))
    ax2.xaxis.set_major_locator(mdates.WeekdayLocator(interval=1))
    
    plt.setp(ax1.xaxis.get_majorticklabels(), rotation=45)
    plt.setp(ax2.xaxis.get_majorticklabels(), rotation=45)
    plt.tight_layout()
    
    return fig

def create_summary_page(stocks_df):
    """Create summary page with statistics"""
    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(12, 10))
    
    # Count by signal type
    signal_counts = stocks_df['signal_type'].value_counts()
    colors = ['green' if 'Bullish' in idx else 'red' for idx in signal_counts.index]
    
    ax1.pie(signal_counts.values, labels=signal_counts.index, autopct='%1.1f%%', 
            colors=colors, startangle=90)
    ax1.set_title('Signal Types Distribution\n(Demo Data)', fontsize=14, fontweight='bold')
    
    # RSI value distribution
    ax2.hist(stocks_df['rsi_value'], bins=8, alpha=0.7, color='orange', edgecolor='black')
    ax2.axvline(x=30, color='green', linestyle='--', label='Oversold (30)')
    ax2.axvline(x=70, color='red', linestyle='--', label='Overbought (70)')
    ax2.set_title('RSI Value Distribution', fontsize=14, fontweight='bold')
    ax2.set_xlabel('RSI Value')
    ax2.set_ylabel('Frequency')
    ax2.legend()
    ax2.grid(True, alpha=0.3)
    
    # Price level distribution
    ax3.hist(stocks_df['current_price'], bins=8, alpha=0.7, color='blue', edgecolor='black')
    ax3.set_title('Current Price Distribution', fontsize=14, fontweight='bold')
    ax3.set_xlabel('Price (₹)')
    ax3.set_ylabel('Frequency')
    ax3.grid(True, alpha=0.3)
    
    # Stocks by volume
    stocks_sorted = stocks_df.sort_values('volume', ascending=True)
    colors = ['green' if 'Bullish' in signal else 'red' for signal in stocks_sorted['signal_type']]
    
    ax4.barh(range(len(stocks_sorted)), stocks_sorted['volume'], color=colors)
    ax4.set_yticks(range(len(stocks_sorted)))
    ax4.set_yticklabels(stocks_sorted['symbol'])
    ax4.set_title('Stocks by Volume', fontsize=14, fontweight='bold')
    ax4.set_xlabel('Volume')
    ax4.grid(True, alpha=0.3, axis='x')
    
    plt.suptitle('Stock Analysis Report - Top 10 EQ Series Stocks\nDemo with Real Price & RSI Data', 
                 fontsize=16, fontweight='bold', y=0.98)
    plt.tight_layout()
    
    return fig

def generate_pdf_report():
    """Generate PDF report with sample stocks"""
    print("🔍 Fetching sample stocks with complete data...")
    stocks_df = get_sample_stocks_with_data()
    
    if stocks_df.empty:
        print("❌ No stocks found")
        return
    
    pdf_filename = "Sample_Stock_Charts_with_RSI_Demo.pdf"
    
    print(f"📄 Generating PDF report: {pdf_filename}")
    print(f"📊 Including {len(stocks_df)} stocks...")
    
    with PdfPages(pdf_filename) as pdf:
        # Create summary page
        print("📋 Creating summary page...")
        summary_fig = create_summary_page(stocks_df)
        pdf.savefig(summary_fig, bbox_inches='tight', dpi=150)
        plt.close(summary_fig)
        
        # Create individual stock pages
        successful_charts = 0
        for idx, (_, stock_data) in enumerate(stocks_df.iterrows()):
            symbol = stock_data['symbol']
            print(f"📈 Creating chart for {symbol} ({idx+1}/{len(stocks_df)})...")
            
            try:
                # Get chart data
                price_df, rsi_df = get_stock_chart_data(symbol, days_back=60)
                
                if not price_df.empty and not rsi_df.empty:
                    # Create chart
                    chart_fig = create_stock_chart(symbol, stock_data, price_df, rsi_df)
                    
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
    
    print(f"\n✅ PDF Report Generated Successfully!")
    print(f"📄 Filename: {pdf_filename}")
    print(f"📊 Total stocks processed: {len(stocks_df)}")
    print(f"📈 Successful charts: {successful_charts}")
    
    # Print stock details
    print(f"\n📋 Stocks included:")
    for _, stock in stocks_df.iterrows():
        print(f"  {stock['symbol']}: ₹{stock['current_price']:.2f} | RSI: {stock['rsi_value']:.1f} | Vol: {stock['volume']:,}")

if __name__ == "__main__":
    generate_pdf_report()