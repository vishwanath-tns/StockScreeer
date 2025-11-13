"""
Simple PDF Generator for Stock Charts - BHAV Data Only Demo
=========================================================

Creates a PDF with 10 stocks showing Price charts only
Uses only BHAV data since RSI data appears to be empty
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

def get_sample_stocks():
    """Get 10 sample stocks with price data"""
    engine = rad.engine()
    
    with engine.connect() as conn:
        # Get top stocks by volume
        query = text('''
            SELECT symbol, 
                   close_price as current_price,
                   ttl_trd_qnty as volume,
                   open_price,
                   high_price,
                   low_price,
                   prev_close
            FROM nse_equity_bhavcopy_full
            WHERE series = 'EQ'
                AND trade_date = (SELECT MAX(trade_date) FROM nse_equity_bhavcopy_full)
                AND ttl_trd_qnty > 1000000
            ORDER BY ttl_trd_qnty DESC
            LIMIT 10
        ''')
        
        stocks_df = pd.read_sql(query, conn)
        print(f"📊 Found {len(stocks_df)} stocks with BHAV data")
        
        # Add mock divergence information for demo
        stocks_df['signal_date'] = '2025-11-10'
        stocks_df['signal_type'] = stocks_df.apply(
            lambda x: 'Bullish Signal' if x['current_price'] > x['prev_close'] else 'Bearish Signal', axis=1
        )
        stocks_df['price_change'] = stocks_df['current_price'] - stocks_df['prev_close']
        stocks_df['price_change_pct'] = (stocks_df['price_change'] / stocks_df['prev_close']) * 100
        stocks_df['buy_level'] = stocks_df['current_price'] * 1.02
        stocks_df['sell_level'] = stocks_df['current_price'] * 0.98
        
        return stocks_df

def get_stock_price_data(symbol, days_back=60):
    """Get price data for charting"""
    engine = rad.engine()
    
    with engine.connect() as conn:
        # Get price data
        price_query = text('''
            SELECT trade_date, open_price, high_price, low_price, close_price, ttl_trd_qnty as volume
            FROM nse_equity_bhavcopy_full
            WHERE symbol = :symbol
                AND series = 'EQ'
                AND trade_date >= DATE_SUB((SELECT MAX(trade_date) FROM nse_equity_bhavcopy_full), INTERVAL :days_back DAY)
            ORDER BY trade_date
        ''')
        
        price_df = pd.read_sql(price_query, conn, params={'symbol': symbol, 'days_back': days_back})
        
        return price_df

def create_stock_chart(symbol, stock_data, price_df, fig_size=(12, 6)):
    """Create price chart for a stock"""
    if price_df.empty:
        return None
        
    fig, ax = plt.subplots(1, 1, figsize=fig_size)
    
    # Convert dates
    price_df['trade_date'] = pd.to_datetime(price_df['trade_date'])
    
    # Price chart
    ax.plot(price_df['trade_date'], price_df['close_price'], 'b-', linewidth=2, label='Close Price')
    ax.fill_between(price_df['trade_date'], price_df['low_price'], price_df['high_price'], 
                    alpha=0.3, color='lightblue', label='Day Range')
    
    # Add current price point
    latest_date = price_df['trade_date'].iloc[-1]
    latest_price = price_df['close_price'].iloc[-1]
    
    signal_color = 'green' if 'Bullish' in stock_data['signal_type'] else 'red'
    signal_marker = '^' if 'Bullish' in stock_data['signal_type'] else 'v'
    
    ax.scatter([latest_date], [latest_price], color=signal_color, s=200, 
               marker=signal_marker, label=f"Current Signal", zorder=5)
    
    # Add buy/sell levels
    ax.axhline(y=stock_data['buy_level'], color='green', linestyle='--', 
               alpha=0.7, label=f"Buy Level: ₹{stock_data['buy_level']:.2f}")
    ax.axhline(y=stock_data['sell_level'], color='red', linestyle='--', 
               alpha=0.7, label=f"Sell Level: ₹{stock_data['sell_level']:.2f}")
    
    # Calculate and add moving averages
    if len(price_df) >= 20:
        price_df['sma_20'] = price_df['close_price'].rolling(window=20).mean()
        ax.plot(price_df['trade_date'], price_df['sma_20'], 'orange', 
               linestyle='--', alpha=0.7, label='SMA 20')
    
    if len(price_df) >= 50:
        price_df['sma_50'] = price_df['close_price'].rolling(window=50).mean()
        ax.plot(price_df['trade_date'], price_df['sma_50'], 'purple', 
               linestyle='--', alpha=0.7, label='SMA 50')
    
    price_change_color = 'green' if stock_data['price_change'] >= 0 else 'red'
    price_change_symbol = '+' if stock_data['price_change'] >= 0 else ''
    
    ax.set_title(f"{symbol} - {stock_data['signal_type']}\nCurrent: ₹{stock_data['current_price']:.2f} | Change: {price_change_symbol}₹{stock_data['price_change']:.2f} ({stock_data['price_change_pct']:.1f}%) | Volume: {stock_data['volume']:,}", 
                 fontsize=14, fontweight='bold')
    ax.set_ylabel('Price (₹)', fontsize=12)
    ax.set_xlabel('Date', fontsize=12)
    ax.legend(loc='upper left')
    ax.grid(True, alpha=0.3)
    
    # Format dates
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%b %d'))
    ax.xaxis.set_major_locator(mdates.WeekdayLocator(interval=1))
    
    plt.setp(ax.xaxis.get_majorticklabels(), rotation=45)
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
    ax1.set_title('Signal Types Distribution\n(Based on Daily Change)', fontsize=14, fontweight='bold')
    
    # Price change distribution
    ax2.hist(stocks_df['price_change_pct'], bins=8, alpha=0.7, color='blue', edgecolor='black')
    ax2.axvline(x=0, color='black', linestyle='--', label='No Change')
    ax2.set_title('Price Change % Distribution', fontsize=14, fontweight='bold')
    ax2.set_xlabel('Price Change (%)')
    ax2.set_ylabel('Frequency')
    ax2.legend()
    ax2.grid(True, alpha=0.3)
    
    # Price level distribution
    ax3.hist(stocks_df['current_price'], bins=8, alpha=0.7, color='purple', edgecolor='black')
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
    
    plt.suptitle('Stock Analysis Report - Top 10 EQ Series Stocks\nPrice Data Only (RSI Data Not Available)', 
                 fontsize=16, fontweight='bold', y=0.98)
    plt.tight_layout()
    
    return fig

def generate_pdf_report():
    """Generate PDF report with sample stocks"""
    print("🔍 Fetching sample stocks with BHAV data...")
    stocks_df = get_sample_stocks()
    
    if stocks_df.empty:
        print("❌ No stocks found")
        return
    
    pdf_filename = "Stock_Charts_BHAV_Only_Demo.pdf"
    
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
                price_df = get_stock_price_data(symbol, days_back=60)
                
                if not price_df.empty:
                    # Create chart
                    chart_fig = create_stock_chart(symbol, stock_data, price_df)
                    
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
        change_symbol = '+' if stock['price_change'] >= 0 else ''
        print(f"  {stock['symbol']}: ₹{stock['current_price']:.2f} ({change_symbol}{stock['price_change_pct']:.1f}%) | Vol: {stock['volume']:,}")

if __name__ == "__main__":
    generate_pdf_report()