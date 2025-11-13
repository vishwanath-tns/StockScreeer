#!/usr/bin/env python3
"""
RSI Divergence PDF Report Generator

Generates comprehensive PDF reports for Hidden Bullish and Hidden Bearish RSI Divergences
including price charts, RSI charts, and divergence analysis.

Features:
- Summary statistics and overview
- Individual stock charts with price and RSI
- Divergence details with buy/sell levels
- Professional PDF formatting
- Batch processing for all divergences

Usage:
    python scripts/generate_rsi_divergence_pdf.py
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

# Configure matplotlib for better charts
plt.style.use('default')
sns.set_palette("husl")

class RSIDivergencePDFGenerator:
    def __init__(self):
        self.engine = rad.engine()
        self.output_dir = "reports"
        self.chart_dir = "charts"
        
        # Ensure output directories exist
        os.makedirs(self.output_dir, exist_ok=True)
        os.makedirs(self.chart_dir, exist_ok=True)
        
        # PDF styling
        self.colors = {
            'bullish': '#2E8B57',  # Sea Green
            'bearish': '#DC143C',  # Crimson
            'price': '#1f77b4',   # Blue
            'rsi': '#ff7f0e',     # Orange
            'background': '#f8f9fa'
        }
        
    def get_divergence_summary(self):
        """Get summary statistics for all hidden divergences"""
        print("📊 Gathering divergence summary...")
        
        with self.engine.connect() as conn:
            query = text("""
                SELECT 
                    signal_type,
                    COUNT(*) as total_signals,
                    COUNT(DISTINCT symbol) as unique_stocks,
                    MIN(signal_date) as earliest_date,
                    MAX(signal_date) as latest_date,
                    AVG(curr_center_rsi) as avg_rsi,
                    AVG(curr_center_close) as avg_price
                FROM nse_rsi_divergences 
                WHERE signal_type LIKE '%Hidden%'
                GROUP BY signal_type
                ORDER BY signal_type
            """)
            
            df = pd.read_sql(query, conn)
            return df
    
    def get_divergence_details(self, limit=None):
        """Get detailed divergence data for chart generation"""
        print("📈 Gathering divergence details...")
        
        with self.engine.connect() as conn:
            query = text("""
                SELECT 
                    symbol,
                    signal_type,
                    signal_date,
                    curr_fractal_date,
                    curr_center_close,
                    curr_center_rsi,
                    comp_fractal_date,
                    comp_center_close,
                    comp_center_rsi,
                    buy_above_price,
                    sell_below_price
                FROM nse_rsi_divergences 
                WHERE signal_type LIKE '%Hidden%'
                ORDER BY signal_date DESC, symbol
                """ + (f" LIMIT {limit}" if limit else ""))
            
            df = pd.read_sql(query, conn)
            return df
    
    def get_stock_data(self, symbol, start_date, end_date):
        """Get historical price and RSI data for a stock"""
        with self.engine.connect() as conn:
            # Get price data
            price_query = text("""
                SELECT trade_date, close_price, open_price, high_price, low_price, ttl_trd_qnty
                FROM nse_equity_bhavcopy_full
                WHERE symbol = :symbol 
                AND trade_date BETWEEN :start_date AND :end_date
                ORDER BY trade_date
            """)
            
            price_df = pd.read_sql(price_query, conn, params={
                'symbol': symbol, 
                'start_date': start_date, 
                'end_date': end_date
            })
            
            # Get RSI data
            rsi_query = text("""
                SELECT trade_date, rsi
                FROM nse_rsi_daily
                WHERE symbol = :symbol 
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
        """Create price and RSI chart for a stock with divergence markings"""
        if stock_data.empty:
            return None
            
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10), height_ratios=[3, 2])
        fig.suptitle(f'{symbol} - {divergence_row["signal_type"]}', fontsize=16, fontweight='bold')
        
        # Price chart
        ax1.plot(stock_data['trade_date'], stock_data['close_price'], 
                color=self.colors['price'], linewidth=1.5, label='Close Price')
        
        # Mark divergence points
        curr_date = pd.to_datetime(divergence_row['curr_fractal_date'])
        comp_date = pd.to_datetime(divergence_row['comp_fractal_date'])
        signal_date = pd.to_datetime(divergence_row['signal_date'])
        
        # Find closest data points
        curr_idx = stock_data[stock_data['trade_date'] <= curr_date].index
        comp_idx = stock_data[stock_data['trade_date'] <= comp_date].index
        signal_idx = stock_data[stock_data['trade_date'] <= signal_date].index
        
        if len(curr_idx) > 0 and len(comp_idx) > 0:
            curr_point = stock_data.loc[curr_idx[-1]]
            comp_point = stock_data.loc[comp_idx[-1]]
            
            # Mark fractal points
            ax1.scatter(curr_point['trade_date'], curr_point['close_price'], 
                       color='red', s=100, zorder=5, label='Current Fractal')
            ax1.scatter(comp_point['trade_date'], comp_point['close_price'], 
                       color='blue', s=100, zorder=5, label='Comparison Fractal')
            
            # Draw divergence line
            ax1.plot([comp_point['trade_date'], curr_point['trade_date']], 
                    [comp_point['close_price'], curr_point['close_price']], 
                    color='purple', linestyle='--', linewidth=2, alpha=0.7, label='Price Trend')
        
        # Add buy/sell levels
        if pd.notna(divergence_row['buy_above_price']):
            ax1.axhline(y=divergence_row['buy_above_price'], color='green', 
                       linestyle=':', alpha=0.8, label=f'Buy Above: ₹{divergence_row["buy_above_price"]:.2f}')
        
        if pd.notna(divergence_row['sell_below_price']):
            ax1.axhline(y=divergence_row['sell_below_price'], color='red', 
                       linestyle=':', alpha=0.8, label=f'Sell Below: ₹{divergence_row["sell_below_price"]:.2f}')
        
        ax1.set_ylabel('Price (₹)', fontsize=12)
        ax1.set_title('Price Chart', fontsize=14)
        ax1.grid(True, alpha=0.3)
        ax1.legend(loc='upper left')
        
        # RSI chart
        ax2.plot(stock_data['trade_date'], stock_data['rsi'], 
                color=self.colors['rsi'], linewidth=1.5, label='RSI(14)')
        
        # RSI divergence points
        if len(curr_idx) > 0 and len(comp_idx) > 0:
            curr_rsi_point = stock_data.loc[curr_idx[-1]]
            comp_rsi_point = stock_data.loc[comp_idx[-1]]
            
            ax2.scatter(curr_rsi_point['trade_date'], curr_rsi_point['rsi'], 
                       color='red', s=100, zorder=5)
            ax2.scatter(comp_rsi_point['trade_date'], comp_rsi_point['rsi'], 
                       color='blue', s=100, zorder=5)
            
            # Draw RSI divergence line
            ax2.plot([comp_rsi_point['trade_date'], curr_rsi_point['trade_date']], 
                    [comp_rsi_point['rsi'], curr_rsi_point['rsi']], 
                    color='purple', linestyle='--', linewidth=2, alpha=0.7, label='RSI Trend')
        
        # RSI levels
        ax2.axhline(y=70, color='red', linestyle='-', alpha=0.5, label='Overbought (70)')
        ax2.axhline(y=30, color='green', linestyle='-', alpha=0.5, label='Oversold (30)')
        ax2.axhline(y=50, color='gray', linestyle='-', alpha=0.3, label='Neutral (50)')
        
        ax2.set_ylabel('RSI', fontsize=12)
        ax2.set_xlabel('Date', fontsize=12)
        ax2.set_title('RSI(14) Chart', fontsize=14)
        ax2.set_ylim(0, 100)
        ax2.grid(True, alpha=0.3)
        ax2.legend(loc='upper left')
        
        # Format dates
        for ax in [ax1, ax2]:
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
            ax.xaxis.set_major_locator(mdates.WeekdayLocator(interval=2))
            plt.setp(ax.xaxis.get_majorticklabels(), rotation=45)
        
        plt.tight_layout()
        return fig
    
    def create_summary_page(self, pdf, summary_df, total_stocks):
        """Create summary page for the PDF report"""
        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(16, 12))
        fig.suptitle('RSI Hidden Divergences - Summary Report', fontsize=20, fontweight='bold')
        
        # Divergence count chart
        divergence_counts = summary_df['total_signals']
        colors = [self.colors['bullish'] if 'Bullish' in t else self.colors['bearish'] 
                 for t in summary_df['signal_type']]
        
        bars = ax1.bar(range(len(summary_df)), divergence_counts, color=colors, alpha=0.7)
        ax1.set_xticks(range(len(summary_df)))
        ax1.set_xticklabels(summary_df['signal_type'], rotation=45)
        ax1.set_title('Divergence Signals Count', fontsize=14, fontweight='bold')
        ax1.set_ylabel('Number of Signals')
        
        # Add count labels on bars
        for bar, count in zip(bars, divergence_counts):
            height = bar.get_height()
            ax1.text(bar.get_x() + bar.get_width()/2., height + 10,
                    f'{int(count):,}', ha='center', va='bottom', fontweight='bold')
        
        # Unique stocks chart
        unique_stocks = summary_df['unique_stocks']
        bars2 = ax2.bar(range(len(summary_df)), unique_stocks, color=colors, alpha=0.7)
        ax2.set_xticks(range(len(summary_df)))
        ax2.set_xticklabels(summary_df['signal_type'], rotation=45)
        ax2.set_title('Unique Stocks with Divergences', fontsize=14, fontweight='bold')
        ax2.set_ylabel('Number of Stocks')
        
        # Add count labels
        for bar, count in zip(bars2, unique_stocks):
            height = bar.get_height()
            ax2.text(bar.get_x() + bar.get_width()/2., height + 2,
                    f'{int(count):,}', ha='center', va='bottom', fontweight='bold')
        
        # RSI distribution
        avg_rsi = summary_df['avg_rsi']
        bars3 = ax3.bar(range(len(summary_df)), avg_rsi, color=colors, alpha=0.7)
        ax3.set_xticks(range(len(summary_df)))
        ax3.set_xticklabels(summary_df['signal_type'], rotation=45)
        ax3.set_title('Average RSI at Divergence', fontsize=14, fontweight='bold')
        ax3.set_ylabel('Average RSI Value')
        ax3.set_ylim(0, 100)
        
        # Add RSI labels
        for bar, rsi in zip(bars3, avg_rsi):
            height = bar.get_height()
            ax3.text(bar.get_x() + bar.get_width()/2., height + 1,
                    f'{rsi:.1f}', ha='center', va='bottom', fontweight='bold')
        
        # Summary table
        ax4.axis('tight')
        ax4.axis('off')
        
        table_data = []
        for _, row in summary_df.iterrows():
            table_data.append([
                row['signal_type'].replace(' Divergence', ''),
                f"{int(row['total_signals']):,}",
                f"{int(row['unique_stocks']):,}",
                f"{row['avg_rsi']:.1f}",
                f"₹{row['avg_price']:,.0f}",
                row['latest_date'].strftime('%Y-%m-%d')
            ])
        
        table = ax4.table(cellText=table_data,
                         colLabels=['Divergence Type', 'Total Signals', 'Unique Stocks', 
                                  'Avg RSI', 'Avg Price', 'Latest Date'],
                         cellLoc='center',
                         loc='center',
                         bbox=[0.0, 0.3, 1.0, 0.6])
        
        table.auto_set_font_size(False)
        table.set_fontsize(11)
        table.scale(1, 2)
        
        # Color code the table
        for i, row_data in enumerate(table_data):
            color = self.colors['bullish'] if 'Bullish' in row_data[0] else self.colors['bearish']
            for j in range(len(row_data)):
                table[(i+1, j)].set_facecolor(color)
                table[(i+1, j)].set_text_props(weight='bold', color='white')
        
        ax4.set_title('Summary Statistics', fontsize=14, fontweight='bold')
        
        # Add report info
        report_date = datetime.now().strftime('%Y-%m-%d %H:%M')
        fig.text(0.02, 0.02, f'Generated on: {report_date} | Total Stocks Analyzed: {total_stocks:,}', 
                fontsize=10, style='italic')
        
        plt.tight_layout()
        pdf.savefig(fig, bbox_inches='tight')
        plt.close(fig)
    
    def generate_pdf_report(self, max_stocks=50):
        """Generate comprehensive PDF report"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        pdf_filename = os.path.join(self.output_dir, f'RSI_Hidden_Divergences_{timestamp}.pdf')
        
        print(f"🔄 Generating RSI Divergence PDF Report...")
        print(f"📁 Output file: {pdf_filename}")
        
        # Get data
        summary_df = self.get_divergence_summary()
        details_df = self.get_divergence_details(limit=max_stocks)
        
        total_signals = summary_df['total_signals'].sum()
        total_stocks = summary_df['unique_stocks'].sum()
        
        print(f"📊 Report scope: {total_signals:,} divergence signals from {total_stocks:,} unique stocks")
        print(f"📈 Generating charts for top {min(max_stocks, len(details_df))} recent divergences...")
        
        with PdfPages(pdf_filename) as pdf:
            # Summary page
            self.create_summary_page(pdf, summary_df, total_stocks)
            
            # Individual stock pages
            for idx, (_, row) in enumerate(details_df.iterrows()):
                symbol = row['symbol']
                signal_date = pd.to_datetime(row['signal_date'])
                
                print(f"📈 Processing {idx+1}/{len(details_df)}: {symbol} ({row['signal_type']})")
                
                # Get data for 6 months around signal date
                start_date = signal_date - timedelta(days=90)
                end_date = signal_date + timedelta(days=30)
                
                stock_data = self.get_stock_data(symbol, start_date, end_date)
                
                if not stock_data.empty:
                    fig = self.create_stock_chart(symbol, row, stock_data)
                    if fig:
                        pdf.savefig(fig, bbox_inches='tight')
                        plt.close(fig)
                else:
                    print(f"⚠️  No data available for {symbol}")
            
            # Add metadata
            d = pdf.infodict()
            d['Title'] = 'RSI Hidden Divergences Report'
            d['Author'] = 'Stock Screener System'
            d['Subject'] = 'Technical Analysis - RSI Divergences'
            d['Keywords'] = 'RSI, Divergence, Technical Analysis, Stock Market'
            d['Creator'] = 'RSI Divergence PDF Generator'
        
        print(f"✅ PDF report generated successfully!")
        print(f"📁 File saved: {pdf_filename}")
        print(f"📊 Report contains: 1 summary + {len(details_df)} stock charts")
        
        return pdf_filename

def main():
    """Main function to generate PDF report"""
    print("🚀 Starting RSI Divergence PDF Report Generation...")
    
    generator = RSIDivergencePDFGenerator()
    
    # Generate report (limit to 50 stocks for reasonable file size)
    pdf_file = generator.generate_pdf_report(max_stocks=50)
    
    print(f"\n🎉 Report generation completed!")
    print(f"📁 PDF saved to: {pdf_file}")
    print(f"\n💡 To generate more stocks, increase max_stocks parameter")
    print(f"💡 To open the PDF: explorer {pdf_file.replace('/', os.sep)}")

if __name__ == "__main__":
    main()