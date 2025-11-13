#!/usr/bin/env python3
"""
Enhanced RSI Divergence PDF Generator with Data Validation

Only generates charts for stocks with complete BHAV and RSI data.
Includes collation fixes for MySQL database queries.
"""

import os
import sys
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from sqlalchemy import text
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.backends.backend_pdf import PdfPages
import seaborn as sns

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import reporting_adv_decl as rad

# Configure matplotlib
plt.style.use('default')
sns.set_palette("husl")

class EnhancedRSIDivergencePDFGenerator:
    def __init__(self):
        self.engine = rad.engine()
        self.output_dir = "reports"
        
        # Ensure output directories exist
        os.makedirs(self.output_dir, exist_ok=True)
        
        # PDF styling
        self.colors = {
            'bullish': '#2E8B57',  # Sea Green
            'bearish': '#DC143C',  # Crimson
            'price': '#1f77b4',   # Blue
            'rsi': '#ff7f0e',     # Orange
            'background': '#f8f9fa'
        }
        
    def get_valid_divergences(self, limit=50):
        """Get divergences for stocks with complete BHAV and RSI data"""
        print("📊 Finding divergences with complete data...")
        
        with self.engine.connect() as conn:
            query = text("""
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
                    b.close_price as signal_close_price
                FROM nse_rsi_divergences d
                INNER JOIN nse_equity_bhavcopy_full b 
                    ON b.symbol COLLATE utf8mb4_unicode_ci = d.symbol COLLATE utf8mb4_unicode_ci 
                    AND b.trade_date = d.signal_date
                INNER JOIN nse_rsi_daily r 
                    ON r.symbol COLLATE utf8mb4_unicode_ci = d.symbol COLLATE utf8mb4_unicode_ci 
                    AND r.trade_date = d.signal_date 
                    AND r.period = 14
                WHERE d.signal_type LIKE '%Hidden%'
                ORDER BY d.signal_date DESC, d.symbol
                LIMIT :limit
            """)
            
            df = pd.read_sql(query, conn, params={'limit': limit})
            return df
    
    def get_stock_data(self, symbol, start_date, end_date):
        """Get historical price and RSI data for a stock with collation fix"""
        with self.engine.connect() as conn:
            # Get price data with collation
            price_query = text("""
                SELECT trade_date, close_price, open_price, high_price, low_price, ttl_trd_qnty
                FROM nse_equity_bhavcopy_full
                WHERE symbol COLLATE utf8mb4_unicode_ci = :symbol COLLATE utf8mb4_unicode_ci
                AND trade_date BETWEEN :start_date AND :end_date
                ORDER BY trade_date
            """)
            
            price_df = pd.read_sql(price_query, conn, params={
                'symbol': symbol, 
                'start_date': start_date, 
                'end_date': end_date
            })
            
            # Get RSI data with collation
            rsi_query = text("""
                SELECT trade_date, rsi
                FROM nse_rsi_daily
                WHERE symbol COLLATE utf8mb4_unicode_ci = :symbol COLLATE utf8mb4_unicode_ci
                AND period = 14
                AND trade_date BETWEEN :start_date AND :end_date
                ORDER BY trade_date
            """)
            
            rsi_df = pd.read_sql(rsi_query, conn, params={
                'symbol': symbol, 
                'start_date': start_date, 
                'end_date': end_date
            })
            
            # Merge price and RSI data
            if not price_df.empty and not rsi_df.empty:
                merged_df = pd.merge(price_df, rsi_df, on='trade_date', how='inner')
                merged_df['trade_date'] = pd.to_datetime(merged_df['trade_date'])
                return merged_df
            
            return pd.DataFrame()
    
    def create_stock_chart(self, symbol, divergence_row, stock_data):
        """Create enhanced price and RSI chart for a stock with divergence markings"""
        if stock_data.empty:
            return None
            
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 12), height_ratios=[3, 2])
        
        # Title with divergence info
        signal_type = divergence_row['signal_type']
        signal_date = pd.to_datetime(divergence_row['signal_date']).strftime('%Y-%m-%d')
        price = divergence_row['signal_close_price']
        
        fig.suptitle(f'{symbol} - {signal_type}\nSignal Date: {signal_date} | Price: ₹{price:.2f}', 
                    fontsize=16, fontweight='bold')
        
        # Price chart with candlestick-like appearance
        ax1.plot(stock_data['trade_date'], stock_data['close_price'], 
                color=self.colors['price'], linewidth=2, label='Close Price', alpha=0.8)
        
        # Add high-low range as fill
        ax1.fill_between(stock_data['trade_date'], 
                        stock_data['low_price'], 
                        stock_data['high_price'], 
                        alpha=0.2, color=self.colors['price'], label='Daily Range')
        
        # Mark divergence points
        curr_date = pd.to_datetime(divergence_row['curr_fractal_date'])
        comp_date = pd.to_datetime(divergence_row['comp_fractal_date'])
        signal_date_dt = pd.to_datetime(divergence_row['signal_date'])
        
        # Find closest data points
        curr_idx = stock_data[stock_data['trade_date'] <= curr_date].index
        comp_idx = stock_data[stock_data['trade_date'] <= comp_date].index
        signal_idx = stock_data[stock_data['trade_date'] <= signal_date_dt].index
        
        if len(curr_idx) > 0 and len(comp_idx) > 0:
            curr_point = stock_data.loc[curr_idx[-1]]
            comp_point = stock_data.loc[comp_idx[-1]]
            
            # Mark fractal points with larger markers
            ax1.scatter(curr_point['trade_date'], curr_point['close_price'], 
                       color='red', s=150, zorder=5, label='Current Fractal', 
                       marker='o', edgecolors='darkred', linewidth=2)
            ax1.scatter(comp_point['trade_date'], comp_point['close_price'], 
                       color='blue', s=150, zorder=5, label='Comparison Fractal',
                       marker='o', edgecolors='darkblue', linewidth=2)
            
            # Draw divergence line with annotation
            ax1.plot([comp_point['trade_date'], curr_point['trade_date']], 
                    [comp_point['close_price'], curr_point['close_price']], 
                    color='purple', linestyle='--', linewidth=3, alpha=0.8, 
                    label='Price Trend')
            
            # Add price change annotation
            price_change = curr_point['close_price'] - comp_point['close_price']
            price_change_pct = (price_change / comp_point['close_price']) * 100
            
            mid_date = comp_point['trade_date'] + (curr_point['trade_date'] - comp_point['trade_date']) / 2
            mid_price = (comp_point['close_price'] + curr_point['close_price']) / 2
            
            ax1.annotate(f'Price: {price_change_pct:+.1f}%', 
                        xy=(mid_date, mid_price), xytext=(10, 10),
                        textcoords='offset points', fontsize=10, fontweight='bold',
                        bbox=dict(boxstyle='round,pad=0.3', facecolor='purple', alpha=0.7, color='white'))
        
        # Mark signal date
        if len(signal_idx) > 0:
            signal_point = stock_data.loc[signal_idx[-1]]
            ax1.axvline(x=signal_point['trade_date'], color='orange', linestyle='-', 
                       linewidth=3, alpha=0.8, label=f'Signal Date')
        
        # Add buy/sell levels
        if pd.notna(divergence_row['buy_above_price']) and divergence_row['buy_above_price'] > 0:
            ax1.axhline(y=divergence_row['buy_above_price'], color='green', 
                       linestyle=':', alpha=0.8, linewidth=2,
                       label=f'Buy Above: ₹{divergence_row["buy_above_price"]:.2f}')
        
        if pd.notna(divergence_row['sell_below_price']) and divergence_row['sell_below_price'] > 0:
            ax1.axhline(y=divergence_row['sell_below_price'], color='red', 
                       linestyle=':', alpha=0.8, linewidth=2,
                       label=f'Sell Below: ₹{divergence_row["sell_below_price"]:.2f}')
        
        ax1.set_ylabel('Price (₹)', fontsize=12, fontweight='bold')
        ax1.set_title('Price Chart with Divergence Analysis', fontsize=14, fontweight='bold')
        ax1.grid(True, alpha=0.3)
        ax1.legend(loc='upper left', fontsize=10)
        
        # RSI chart
        ax2.plot(stock_data['trade_date'], stock_data['rsi'], 
                color=self.colors['rsi'], linewidth=2, label='RSI(14)', alpha=0.8)
        
        # RSI divergence points and analysis
        if len(curr_idx) > 0 and len(comp_idx) > 0:
            curr_rsi_point = stock_data.loc[curr_idx[-1]]
            comp_rsi_point = stock_data.loc[comp_idx[-1]]
            
            ax2.scatter(curr_rsi_point['trade_date'], curr_rsi_point['rsi'], 
                       color='red', s=150, zorder=5, marker='o', 
                       edgecolors='darkred', linewidth=2)
            ax2.scatter(comp_rsi_point['trade_date'], comp_rsi_point['rsi'], 
                       color='blue', s=150, zorder=5, marker='o',
                       edgecolors='darkblue', linewidth=2)
            
            # Draw RSI divergence line
            ax2.plot([comp_rsi_point['trade_date'], curr_rsi_point['trade_date']], 
                    [comp_rsi_point['rsi'], curr_rsi_point['rsi']], 
                    color='purple', linestyle='--', linewidth=3, alpha=0.8, 
                    label='RSI Trend')
            
            # Add RSI change annotation
            rsi_change = curr_rsi_point['rsi'] - comp_rsi_point['rsi']
            
            mid_date_rsi = comp_rsi_point['trade_date'] + (curr_rsi_point['trade_date'] - comp_rsi_point['trade_date']) / 2
            mid_rsi = (comp_rsi_point['rsi'] + curr_rsi_point['rsi']) / 2
            
            ax2.annotate(f'RSI: {rsi_change:+.1f}', 
                        xy=(mid_date_rsi, mid_rsi), xytext=(10, 10),
                        textcoords='offset points', fontsize=10, fontweight='bold',
                        bbox=dict(boxstyle='round,pad=0.3', facecolor='purple', alpha=0.7, color='white'))
        
        # Mark signal date on RSI
        if len(signal_idx) > 0:
            ax2.axvline(x=signal_point['trade_date'], color='orange', linestyle='-', 
                       linewidth=3, alpha=0.8)
        
        # RSI levels with better styling
        ax2.axhline(y=70, color='red', linestyle='-', alpha=0.6, linewidth=2, label='Overbought (70)')
        ax2.axhline(y=30, color='green', linestyle='-', alpha=0.6, linewidth=2, label='Oversold (30)')
        ax2.axhline(y=50, color='gray', linestyle='-', alpha=0.4, linewidth=1, label='Neutral (50)')
        
        # RSI zones
        ax2.fill_between(stock_data['trade_date'], 70, 100, alpha=0.1, color='red', label='Overbought Zone')
        ax2.fill_between(stock_data['trade_date'], 0, 30, alpha=0.1, color='green', label='Oversold Zone')
        
        ax2.set_ylabel('RSI', fontsize=12, fontweight='bold')
        ax2.set_xlabel('Date', fontsize=12, fontweight='bold')
        ax2.set_title('RSI(14) with Divergence Analysis', fontsize=14, fontweight='bold')
        ax2.set_ylim(0, 100)
        ax2.grid(True, alpha=0.3)
        ax2.legend(loc='upper left', fontsize=10)
        
        # Format dates
        for ax in [ax1, ax2]:
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d'))
            ax.xaxis.set_major_locator(mdates.WeekdayLocator(interval=1))
            plt.setp(ax.xaxis.get_majorticklabels(), rotation=45)
        
        plt.tight_layout()
        return fig
    
    def create_summary_page(self, pdf, valid_divergences):
        """Create enhanced summary page"""
        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(16, 12))
        
        # Summary statistics
        bullish_count = len(valid_divergences[valid_divergences['signal_type'].str.contains('Bullish')])
        bearish_count = len(valid_divergences[valid_divergences['signal_type'].str.contains('Bearish')])
        unique_stocks = valid_divergences['symbol'].nunique()
        
        fig.suptitle(f'RSI Hidden Divergences Analysis\n{len(valid_divergences)} signals from {unique_stocks} stocks', 
                    fontsize=20, fontweight='bold')
        
        # Divergence type distribution
        counts = [bullish_count, bearish_count]
        labels = ['Hidden Bullish', 'Hidden Bearish']
        colors = [self.colors['bullish'], self.colors['bearish']]
        
        wedges, texts, autotexts = ax1.pie(counts, labels=labels, colors=colors, autopct='%1.1f%%', 
                                          startangle=90, explode=(0.05, 0.05))
        ax1.set_title('Divergence Type Distribution', fontsize=14, fontweight='bold')
        
        # Recent signals timeline
        recent_signals = valid_divergences.groupby('signal_date').size().tail(10)
        ax2.bar(range(len(recent_signals)), recent_signals.values, 
               color=[self.colors['bullish'] if i % 2 == 0 else self.colors['bearish'] 
                     for i in range(len(recent_signals))], alpha=0.7)
        ax2.set_title('Recent Signal Activity', fontsize=14, fontweight='bold')
        ax2.set_ylabel('Number of Signals')
        ax2.set_xlabel('Recent Trading Days')
        ax2.set_xticks(range(len(recent_signals)))
        ax2.set_xticklabels([d.strftime('%m/%d') for d in recent_signals.index], rotation=45)
        
        # Top symbols by signal count
        top_symbols = valid_divergences['symbol'].value_counts().head(10)
        ax3.barh(range(len(top_symbols)), top_symbols.values, color=self.colors['price'], alpha=0.7)
        ax3.set_title('Most Active Stocks', fontsize=14, fontweight='bold')
        ax3.set_xlabel('Number of Signals')
        ax3.set_yticks(range(len(top_symbols)))
        ax3.set_yticklabels(top_symbols.index)
        
        # Summary table
        ax4.axis('tight')
        ax4.axis('off')
        
        table_data = [
            ['Total Signals', f'{len(valid_divergences):,}'],
            ['Hidden Bullish', f'{bullish_count:,}'],
            ['Hidden Bearish', f'{bearish_count:,}'],
            ['Unique Stocks', f'{unique_stocks:,}'],
            ['Date Range', f"{valid_divergences['signal_date'].min()} to {valid_divergences['signal_date'].max()}"],
            ['Avg Price Level', f"₹{valid_divergences['signal_close_price'].mean():.2f}"],
            ['Most Recent', f"{valid_divergences['signal_date'].max()}"]
        ]
        
        table = ax4.table(cellText=table_data,
                         colLabels=['Metric', 'Value'],
                         cellLoc='center',
                         loc='center',
                         bbox=[0.1, 0.2, 0.8, 0.6])
        
        table.auto_set_font_size(False)
        table.set_fontsize(12)
        table.scale(1, 2.5)
        
        # Style table
        for i in range(len(table_data)):
            table[(i+1, 0)].set_facecolor('#f0f0f0')
            table[(i+1, 1)].set_facecolor('#ffffff')
        
        ax4.set_title('Summary Statistics', fontsize=14, fontweight='bold')
        
        # Add generation info
        report_date = datetime.now().strftime('%Y-%m-%d %H:%M')
        fig.text(0.02, 0.02, f'Generated: {report_date} | Analysis includes only stocks with complete BHAV and RSI data', 
                fontsize=10, style='italic')
        
        plt.tight_layout()
        pdf.savefig(fig, bbox_inches='tight')
        plt.close(fig)
    
    def generate_pdf_report(self, max_stocks=25):
        """Generate enhanced PDF report with validated data"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        pdf_filename = os.path.join(self.output_dir, f'RSI_Hidden_Divergences_Enhanced_{timestamp}.pdf')
        
        print(f"🚀 Generating Enhanced RSI Divergence PDF Report...")
        print(f"📁 Output file: {pdf_filename}")
        
        # Get valid divergences with complete data
        valid_divergences = self.get_valid_divergences(limit=max_stocks)
        
        if valid_divergences.empty:
            print("❌ No valid divergences found with complete data!")
            return None
        
        print(f"✅ Found {len(valid_divergences)} valid divergences from {valid_divergences['symbol'].nunique()} unique stocks")
        
        with PdfPages(pdf_filename) as pdf:
            # Summary page
            self.create_summary_page(pdf, valid_divergences)
            
            # Individual stock pages
            for idx, (_, row) in enumerate(valid_divergences.iterrows()):
                symbol = row['symbol']
                signal_date = pd.to_datetime(row['signal_date'])
                
                print(f"📈 Processing {idx+1}/{len(valid_divergences)}: {symbol} ({row['signal_type']}) - {signal_date.strftime('%Y-%m-%d')}")
                
                # Get data for 3 months around signal date
                start_date = signal_date - timedelta(days=60)
                end_date = signal_date + timedelta(days=30)
                
                stock_data = self.get_stock_data(symbol, start_date, end_date)
                
                if not stock_data.empty:
                    fig = self.create_stock_chart(symbol, row, stock_data)
                    if fig:
                        pdf.savefig(fig, bbox_inches='tight')
                        plt.close(fig)
                else:
                    print(f"⚠️  No historical data available for {symbol}")
            
            # Add metadata
            d = pdf.infodict()
            d['Title'] = 'Enhanced RSI Hidden Divergences Report'
            d['Author'] = 'Stock Screener System'
            d['Subject'] = 'Technical Analysis - RSI Divergences with Complete Data'
            d['Keywords'] = 'RSI, Hidden Divergence, Technical Analysis, Stock Market'
            d['Creator'] = 'Enhanced RSI Divergence PDF Generator'
        
        print(f"✅ Enhanced PDF report generated successfully!")
        print(f"📁 File saved: {pdf_filename}")
        print(f"📊 Report contains: 1 summary + {len(valid_divergences)} validated stock charts")
        
        return pdf_filename

def main():
    """Main function to generate enhanced PDF report"""
    print("🚀 Starting Enhanced RSI Divergence PDF Report Generation...")
    
    generator = EnhancedRSIDivergencePDFGenerator()
    
    # Generate report with data validation
    pdf_file = generator.generate_pdf_report(max_stocks=25)
    
    if pdf_file:
        print(f"\n🎉 Enhanced report generation completed!")
        print(f"📁 PDF saved to: {pdf_file}")
        print(f"\n✨ Features included:")
        print(f"  • Only stocks with complete BHAV and RSI data")
        print(f"  • Enhanced charts with divergence analysis")
        print(f"  • Buy/Sell levels and price change annotations")
        print(f"  • RSI zones and trend analysis")
        print(f"  • Professional summary statistics")
        print(f"\n💡 To increase coverage, modify max_stocks parameter")
    else:
        print(f"\n❌ Report generation failed!")

if __name__ == "__main__":
    main()