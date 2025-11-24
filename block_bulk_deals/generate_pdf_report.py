"""
PDF Report Generator for Block & Bulk Deals Analysis

Generates comprehensive PDF reports with charts, tables, and insights
for investment decision making.
"""

import os
from datetime import datetime, timedelta
from typing import Dict, List
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend
import matplotlib.pyplot as plt
import seaborn as sns
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.patches import Rectangle
import warnings
warnings.filterwarnings('ignore')

from analysis_engine import BlockBulkDealsAnalyzer


class BlockBulkDealsPDFReport:
    """Generate comprehensive PDF reports for Block & Bulk Deals analysis"""
    
    def __init__(self):
        """Initialize analyzer and set plotting styles"""
        self.analyzer = BlockBulkDealsAnalyzer()
        
        # Set plotting style
        sns.set_style('whitegrid')
        plt.rcParams['figure.figsize'] = (11, 8.5)  # Letter size
        plt.rcParams['font.size'] = 9
        plt.rcParams['axes.titlesize'] = 11
        plt.rcParams['axes.labelsize'] = 9
        
    def generate_annual_report(self, output_file: str = None, days: int = 365):
        """
        Generate comprehensive annual PDF report
        
        Args:
            output_file: Path to output PDF (default: auto-generated)
            days: Number of days to analyze (default: 365)
        """
        if output_file is None:
            output_file = f"block_bulk_deals_report_{datetime.now().strftime('%Y%m%d')}.pdf"
        
        print(f"\n{'=' * 80}")
        print(f"GENERATING PDF REPORT: {output_file}")
        print(f"{'=' * 80}\n")
        
        with PdfPages(output_file) as pdf:
            # Page 1: Title Page
            self._create_title_page(pdf, days)
            
            # Page 2: Executive Summary
            self._create_executive_summary(pdf, days)
            
            # Page 3-4: Accumulation/Distribution Analysis
            self._create_accumulation_report(pdf, days)
            
            # Page 5-6: Smart Money Tracking
            self._create_smart_money_report(pdf, days)
            
            # Page 7: Repeated Buying Patterns
            self._create_repeated_buying_report(pdf, days)
            
            # Page 8: Unusual Activity Detection
            self._create_unusual_activity_report(pdf, days)
            
            # Page 9: Price Momentum Analysis
            self._create_price_momentum_report(pdf, days)
            
            # Page 10: Timing Analysis
            self._create_timing_analysis_report(pdf, days)
            
            # Page 11: Top Deals Summary
            self._create_top_deals_report(pdf, days)
            
            # Page 12: Investment Recommendations
            self._create_recommendations_page(pdf, days)
            
            # Metadata
            d = pdf.infodict()
            d['Title'] = f'Block & Bulk Deals Analysis Report ({days} days)'
            d['Author'] = 'Stock Screener Analysis Engine'
            d['Subject'] = 'NSE Block and Bulk Deals Investment Analysis'
            d['Keywords'] = 'NSE, Block Deals, Bulk Deals, Investment Analysis'
            d['CreationDate'] = datetime.now()
        
        print(f"\n✅ PDF Report generated: {output_file}")
        print(f"📄 Pages: 12 comprehensive analysis sections")
        print(f"{'=' * 80}\n")
        
        return output_file
    
    def _create_title_page(self, pdf: PdfPages, days: int):
        """Create title page"""
        fig = plt.figure(figsize=(8.5, 11))
        ax = fig.add_subplot(111)
        ax.axis('off')
        
        # Title
        ax.text(0.5, 0.85, 'BLOCK & BULK DEALS', 
               ha='center', va='top', fontsize=32, fontweight='bold',
               color='#1f77b4')
        ax.text(0.5, 0.78, 'COMPREHENSIVE INVESTMENT ANALYSIS', 
               ha='center', va='top', fontsize=18, fontweight='bold',
               color='#555555')
        
        # Period
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        ax.text(0.5, 0.70, f'Analysis Period', 
               ha='center', va='top', fontsize=14, fontweight='bold')
        ax.text(0.5, 0.66, f'{start_date.strftime("%B %d, %Y")} to {end_date.strftime("%B %d, %Y")}', 
               ha='center', va='top', fontsize=12)
        ax.text(0.5, 0.62, f'({days} days)', 
               ha='center', va='top', fontsize=10, style='italic', color='#666666')
        
        # Box with key info
        box_text = [
            "📊 WHAT'S INCLUDED:",
            "",
            "• Accumulation/Distribution Analysis",
            "• Smart Money Tracking (FII/DII)",
            "• Repeated Buying Patterns",
            "• Unusual Activity Detection",
            "• Price Momentum Correlation",
            "• Timing & Seasonality Analysis",
            "• Investment Recommendations",
            "",
            "🎯 DATA SOURCES:",
            "• NSE Block Deals (5L+ shares)",
            "• NSE Bulk Deals (≥0.5% equity)",
            "• Daily Bhav Copy (Price data)"
        ]
        
        y_pos = 0.50
        for line in box_text:
            if line.startswith('📊') or line.startswith('🎯'):
                ax.text(0.15, y_pos, line, fontsize=11, fontweight='bold', 
                       family='sans-serif')
            else:
                ax.text(0.15, y_pos, line, fontsize=10, family='monospace')
            y_pos -= 0.025
        
        # Footer
        ax.text(0.5, 0.10, f'Generated on: {datetime.now().strftime("%B %d, %Y at %I:%M %p")}',
               ha='center', va='top', fontsize=9, style='italic', color='#888888')
        ax.text(0.5, 0.06, 'For Investment Research Purposes Only',
               ha='center', va='top', fontsize=8, color='#888888')
        ax.text(0.5, 0.03, '© Stock Screener Analysis Engine',
               ha='center', va='top', fontsize=8, color='#AAAAAA')
        
        pdf.savefig(fig, bbox_inches='tight')
        plt.close()
    
    def _create_executive_summary(self, pdf: PdfPages, days: int):
        """Create executive summary page"""
        print("Generating executive summary...")
        
        fig = plt.figure(figsize=(8.5, 11))
        fig.suptitle('EXECUTIVE SUMMARY', fontsize=16, fontweight='bold', y=0.98)
        
        # Get data
        cutoff_date = (datetime.now() - timedelta(days=days)).date()
        
        # Query summary stats
        from sqlalchemy import text
        
        # Block deals summary
        query_block = text("""
            SELECT 
                COUNT(*) as total_deals,
                COUNT(DISTINCT symbol) as unique_symbols,
                COUNT(DISTINCT client_name) as unique_clients,
                SUM(quantity * trade_price) / 10000000 as total_value_cr,
                SUM(CASE WHEN deal_type = 'BUY' THEN quantity * trade_price ELSE 0 END) / 10000000 as buy_value_cr,
                SUM(CASE WHEN deal_type = 'SELL' THEN quantity * trade_price ELSE 0 END) / 10000000 as sell_value_cr
            FROM nse_block_deals WHERE trade_date >= :cutoff
        """)
        block_stats = pd.read_sql(query_block, self.analyzer.engine, 
                                  params={'cutoff': cutoff_date}).iloc[0]
        
        # Bulk deals summary
        query_bulk = text("""
            SELECT 
                COUNT(*) as total_deals,
                COUNT(DISTINCT symbol) as unique_symbols,
                COUNT(DISTINCT client_name) as unique_clients,
                SUM(quantity * trade_price) / 10000000 as total_value_cr,
                SUM(CASE WHEN deal_type = 'BUY' THEN quantity * trade_price ELSE 0 END) / 10000000 as buy_value_cr,
                SUM(CASE WHEN deal_type = 'SELL' THEN quantity * trade_price ELSE 0 END) / 10000000 as sell_value_cr
            FROM nse_bulk_deals WHERE trade_date >= :cutoff
        """)
        bulk_stats = pd.read_sql(query_bulk, self.analyzer.engine,
                                 params={'cutoff': cutoff_date}).iloc[0]
        
        # Create summary boxes
        ax1 = fig.add_subplot(3, 2, 1)
        self._create_stat_box(ax1, 'BLOCK DEALS', 
                             block_stats['total_deals'],
                             f"{block_stats['unique_symbols']} symbols\n"
                             f"{block_stats['unique_clients']} clients",
                             '#2E86AB')
        
        ax2 = fig.add_subplot(3, 2, 2)
        self._create_stat_box(ax2, 'BULK DEALS', 
                             bulk_stats['total_deals'],
                             f"{bulk_stats['unique_symbols']} symbols\n"
                             f"{bulk_stats['unique_clients']} clients",
                             '#A23B72')
        
        ax3 = fig.add_subplot(3, 2, 3)
        self._create_stat_box(ax3, 'BLOCK VALUE', 
                             f"₹{block_stats['total_value_cr']:.0f} Cr",
                             f"Buy: ₹{block_stats['buy_value_cr']:.0f} Cr\n"
                             f"Sell: ₹{block_stats['sell_value_cr']:.0f} Cr",
                             '#F18F01')
        
        ax4 = fig.add_subplot(3, 2, 4)
        self._create_stat_box(ax4, 'BULK VALUE', 
                             f"₹{bulk_stats['total_value_cr']:.0f} Cr",
                             f"Buy: ₹{bulk_stats['buy_value_cr']:.0f} Cr\n"
                             f"Sell: ₹{bulk_stats['sell_value_cr']:.0f} Cr",
                             '#C73E1D')
        
        # Key findings text
        ax5 = fig.add_subplot(3, 1, 3)
        ax5.axis('off')
        
        net_block = block_stats['buy_value_cr'] - block_stats['sell_value_cr']
        net_bulk = bulk_stats['buy_value_cr'] - bulk_stats['sell_value_cr']
        total_net = net_block + net_bulk
        
        findings = [
            "KEY FINDINGS:",
            "",
            f"• Total Deals: {int(block_stats['total_deals'] + bulk_stats['total_deals']):,} "
            f"({int(block_stats['total_deals']):,} block + {int(bulk_stats['total_deals']):,} bulk)",
            "",
            f"• Net Position: ₹{total_net:.0f} Cr "
            f"({'ACCUMULATION' if total_net > 0 else 'DISTRIBUTION'})",
            f"  - Block: ₹{net_block:.0f} Cr, Bulk: ₹{net_bulk:.0f} Cr",
            "",
            f"• Market Coverage: {int(block_stats['unique_symbols'] + bulk_stats['unique_symbols'])} unique symbols tracked",
            "",
            f"• Investor Base: {int(block_stats['unique_clients'] + bulk_stats['unique_clients'])} unique clients active",
            "",
            "• Sentiment: " + ('BULLISH - Net buying detected' if total_net > 0 else 
                             'BEARISH - Net selling detected' if total_net < 0 else 
                             'NEUTRAL - Balanced buying and selling'),
        ]
        
        y_pos = 0.9
        for line in findings:
            if line.startswith('KEY FINDINGS') or line.startswith('•'):
                weight = 'bold' if line.startswith('KEY') else 'normal'
                ax5.text(0.05, y_pos, line, fontsize=11, fontweight=weight, 
                        family='sans-serif', va='top')
            else:
                ax5.text(0.05, y_pos, line, fontsize=10, family='sans-serif', va='top')
            y_pos -= 0.08
        
        plt.tight_layout()
        pdf.savefig(fig, bbox_inches='tight')
        plt.close()
    
    def _create_stat_box(self, ax, title, value, subtitle, color):
        """Create a styled statistics box"""
        ax.axis('off')
        
        # Background rectangle
        rect = Rectangle((0.1, 0.2), 0.8, 0.6, 
                        facecolor=color, alpha=0.1, edgecolor=color, linewidth=2)
        ax.add_patch(rect)
        
        # Title
        ax.text(0.5, 0.75, title, ha='center', va='center',
               fontsize=11, fontweight='bold', color=color)
        
        # Value
        ax.text(0.5, 0.50, str(value), ha='center', va='center',
               fontsize=18, fontweight='bold', color='#333333')
        
        # Subtitle
        ax.text(0.5, 0.30, subtitle, ha='center', va='center',
               fontsize=8, color='#666666')
        
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
    
    def _create_accumulation_report(self, pdf: PdfPages, days: int):
        """Create accumulation/distribution analysis pages"""
        print("Analyzing accumulation patterns...")
        
        df = self.analyzer.analyze_accumulation_distribution(days=days)
        
        if df.empty:
            return
        
        # Page 1: Top accumulation stocks
        fig = plt.figure(figsize=(8.5, 11))
        fig.suptitle(f'ACCUMULATION/DISTRIBUTION ANALYSIS ({days} days)', 
                    fontsize=14, fontweight='bold', y=0.98)
        
        # Top 15 accumulation stocks
        ax1 = fig.add_subplot(2, 1, 1)
        top_accum = df.nlargest(15, 'accumulation_score')
        
        colors = ['#2E7D32' if x == 'ACCUMULATION' else '#D32F2F' if x == 'DISTRIBUTION' else '#FFA000' 
                 for x in top_accum['signal']]
        
        bars = ax1.barh(range(len(top_accum)), top_accum['accumulation_score'], color=colors)
        ax1.set_yticks(range(len(top_accum)))
        ax1.set_yticklabels(top_accum['symbol'], fontsize=8)
        ax1.set_xlabel('Accumulation Score', fontsize=10, fontweight='bold')
        ax1.set_title('Top 15 Stocks by Accumulation Score', fontsize=11, fontweight='bold')
        ax1.grid(axis='x', alpha=0.3)
        
        # Add value labels
        for i, (score, signal) in enumerate(zip(top_accum['accumulation_score'], top_accum['signal'])):
            ax1.text(score + 2, i, f'{score:.0f}', va='center', fontsize=7)
        
        # Distribution stocks
        ax2 = fig.add_subplot(2, 1, 2)
        top_dist = df.nsmallest(15, 'accumulation_score')
        
        colors_dist = ['#D32F2F' for _ in range(len(top_dist))]
        
        bars = ax2.barh(range(len(top_dist)), top_dist['accumulation_score'], color=colors_dist)
        ax2.set_yticks(range(len(top_dist)))
        ax2.set_yticklabels(top_dist['symbol'], fontsize=8)
        ax2.set_xlabel('Accumulation Score', fontsize=10, fontweight='bold')
        ax2.set_title('Top 15 Distribution Stocks (Selling Pressure)', fontsize=11, fontweight='bold')
        ax2.grid(axis='x', alpha=0.3)
        
        for i, score in enumerate(top_dist['accumulation_score']):
            ax2.text(score + 2, i, f'{score:.0f}', va='center', fontsize=7)
        
        plt.tight_layout()
        pdf.savefig(fig, bbox_inches='tight')
        plt.close()
        
        # Page 2: Detailed table
        fig = plt.figure(figsize=(8.5, 11))
        fig.suptitle('TOP ACCUMULATION STOCKS - DETAILED VIEW', 
                    fontsize=14, fontweight='bold', y=0.98)
        
        ax = fig.add_subplot(111)
        ax.axis('tight')
        ax.axis('off')
        
        # Select columns for table
        table_data = df.head(20)[['symbol', 'security_name', 'total_deals', 
                                   'buy_deals', 'sell_deals', 'buy_sell_ratio',
                                   'buy_value_cr', 'sell_value_cr', 
                                   'accumulation_score', 'signal']]
        
        # Format numbers
        table_data = table_data.copy()
        table_data['buy_sell_ratio'] = table_data['buy_sell_ratio'].round(2)
        table_data['buy_value_cr'] = table_data['buy_value_cr'].round(0).astype(int)
        table_data['sell_value_cr'] = table_data['sell_value_cr'].round(0).astype(int)
        table_data['accumulation_score'] = table_data['accumulation_score'].round(0).astype(int)
        
        # Rename columns
        table_data.columns = ['Symbol', 'Name', 'Deals', 'Buy', 'Sell', 
                             'B/S Ratio', 'Buy ₹Cr', 'Sell ₹Cr', 'Score', 'Signal']
        
        # Truncate name
        table_data['Name'] = table_data['Name'].str[:25]
        
        # Create table
        table = ax.table(cellText=table_data.values,
                        colLabels=table_data.columns,
                        cellLoc='center',
                        loc='center',
                        bbox=[0, 0, 1, 1])
        
        table.auto_set_font_size(False)
        table.set_fontsize(7)
        table.scale(1, 1.5)
        
        # Style header
        for i in range(len(table_data.columns)):
            table[(0, i)].set_facecolor('#4CAF50')
            table[(0, i)].set_text_props(weight='bold', color='white')
        
        # Color code signals
        for i in range(1, len(table_data) + 1):
            signal = table_data.iloc[i-1]['Signal']
            if signal == 'ACCUMULATION':
                table[(i, 9)].set_facecolor('#C8E6C9')
            elif signal == 'DISTRIBUTION':
                table[(i, 9)].set_facecolor('#FFCDD2')
        
        plt.tight_layout()
        pdf.savefig(fig, bbox_inches='tight')
        plt.close()
    
    def _create_smart_money_report(self, pdf: PdfPages, days: int):
        """Create smart money tracking pages"""
        print("Tracking smart money...")
        
        smart_money = self.analyzer.track_smart_money(days=days)
        
        if not smart_money:
            return
        
        # Combine all smart money data
        all_smart = []
        for pattern, df in smart_money.items():
            if not df.empty:
                df['investor_type'] = pattern
                all_smart.append(df)
        
        if not all_smart:
            return
        
        combined = pd.concat(all_smart, ignore_index=True)
        
        # Page 1: Smart money activity by investor type
        fig = plt.figure(figsize=(8.5, 11))
        fig.suptitle(f'SMART MONEY TRACKING ({days} days)', 
                    fontsize=14, fontweight='bold', y=0.98)
        
        # Top investors by value
        ax1 = fig.add_subplot(2, 1, 1)
        top_investors = combined.groupby('investor_type')['value_cr'].sum().sort_values(ascending=True).tail(10)
        
        colors = plt.cm.Set3(range(len(top_investors)))
        bars = ax1.barh(range(len(top_investors)), top_investors.values, color=colors)
        ax1.set_yticks(range(len(top_investors)))
        ax1.set_yticklabels(top_investors.index, fontsize=9)
        ax1.set_xlabel('Total Deal Value (₹ Crores)', fontsize=10, fontweight='bold')
        ax1.set_title('Top Smart Money Investors by Total Value', fontsize=11, fontweight='bold')
        ax1.grid(axis='x', alpha=0.3)
        
        for i, val in enumerate(top_investors.values):
            ax1.text(val + 100, i, f'₹{val:.0f}', va='center', fontsize=8)
        
        # Buy vs Sell by investor type
        ax2 = fig.add_subplot(2, 1, 2)
        
        buy_sell_data = combined.groupby(['investor_type', 'deal_type'])['value_cr'].sum().unstack(fill_value=0)
        buy_sell_data = buy_sell_data.sort_values('BUY', ascending=True).tail(10)
        
        x = np.arange(len(buy_sell_data))
        width = 0.35
        
        if 'BUY' in buy_sell_data.columns:
            ax2.barh(x - width/2, buy_sell_data['BUY'], width, label='BUY', color='#4CAF50')
        if 'SELL' in buy_sell_data.columns:
            ax2.barh(x + width/2, buy_sell_data['SELL'], width, label='SELL', color='#F44336')
        
        ax2.set_yticks(x)
        ax2.set_yticklabels(buy_sell_data.index, fontsize=8)
        ax2.set_xlabel('Deal Value (₹ Crores)', fontsize=10, fontweight='bold')
        ax2.set_title('Smart Money: Buy vs Sell Activity', fontsize=11, fontweight='bold')
        ax2.legend(loc='lower right')
        ax2.grid(axis='x', alpha=0.3)
        
        plt.tight_layout()
        pdf.savefig(fig, bbox_inches='tight')
        plt.close()
        
        # Page 2: Top stocks by smart money
        fig = plt.figure(figsize=(8.5, 11))
        fig.suptitle('TOP STOCKS BY SMART MONEY ACTIVITY', 
                    fontsize=14, fontweight='bold', y=0.98)
        
        ax = fig.add_subplot(111)
        ax.axis('tight')
        ax.axis('off')
        
        # Top stocks
        top_stocks = combined.groupby(['symbol', 'security_name', 'deal_type']).agg({
            'deals': 'sum',
            'value_cr': 'sum',
            'investor_type': 'count'
        }).reset_index()
        
        top_stocks_pivot = top_stocks.pivot_table(
            index=['symbol', 'security_name'],
            columns='deal_type',
            values='value_cr',
            aggfunc='sum',
            fill_value=0
        ).reset_index()
        
        if 'BUY' in top_stocks_pivot.columns and 'SELL' in top_stocks_pivot.columns:
            top_stocks_pivot['net'] = top_stocks_pivot['BUY'] - top_stocks_pivot['SELL']
            top_stocks_pivot = top_stocks_pivot.sort_values('net', ascending=False).head(20)
            
            table_data = top_stocks_pivot[['symbol', 'security_name', 'BUY', 'SELL', 'net']].copy()
            table_data.columns = ['Symbol', 'Security Name', 'Buy ₹Cr', 'Sell ₹Cr', 'Net ₹Cr']
            table_data['Security Name'] = table_data['Security Name'].str[:30]
            
            for col in ['Buy ₹Cr', 'Sell ₹Cr', 'Net ₹Cr']:
                table_data[col] = table_data[col].round(0).astype(int)
            
            table = ax.table(cellText=table_data.values,
                           colLabels=table_data.columns,
                           cellLoc='center',
                           loc='center',
                           bbox=[0, 0, 1, 1])
            
            table.auto_set_font_size(False)
            table.set_fontsize(7)
            table.scale(1, 1.8)
            
            # Style header
            for i in range(len(table_data.columns)):
                table[(0, i)].set_facecolor('#2196F3')
                table[(0, i)].set_text_props(weight='bold', color='white')
            
            # Color code net position
            for i in range(1, len(table_data) + 1):
                net_val = table_data.iloc[i-1]['Net ₹Cr']
                if net_val > 0:
                    table[(i, 4)].set_facecolor('#C8E6C9')
                elif net_val < 0:
                    table[(i, 4)].set_facecolor('#FFCDD2')
        
        plt.tight_layout()
        pdf.savefig(fig, bbox_inches='tight')
        plt.close()
    
    def _create_repeated_buying_report(self, pdf: PdfPages, days: int):
        """Create repeated buying patterns page"""
        print("Analyzing repeated buying patterns...")
        
        df = self.analyzer.find_repeated_buying(min_buys=3, days=days)
        
        if df.empty:
            return
        
        fig = plt.figure(figsize=(8.5, 11))
        fig.suptitle(f'REPEATED BUYING PATTERNS ({days} days)', 
                    fontsize=14, fontweight='bold', y=0.98)
        
        # Top repeated buyers chart
        ax1 = fig.add_subplot(2, 1, 1)
        
        top_repeat = df.nlargest(15, 'buy_count')
        
        colors = plt.cm.Greens(np.linspace(0.4, 0.9, len(top_repeat)))
        bars = ax1.barh(range(len(top_repeat)), top_repeat['buy_count'], color=colors)
        ax1.set_yticks(range(len(top_repeat)))
        ax1.set_yticklabels([f"{row['symbol']}\n({row['client_name'][:20]}...)" 
                            for _, row in top_repeat.iterrows()], fontsize=7)
        ax1.set_xlabel('Number of Buy Deals', fontsize=10, fontweight='bold')
        ax1.set_title('Top 15 Repeated Buying Instances', fontsize=11, fontweight='bold')
        ax1.grid(axis='x', alpha=0.3)
        
        for i, (cnt, val) in enumerate(zip(top_repeat['buy_count'], top_repeat['total_value_cr'])):
            ax1.text(cnt + 0.2, i, f'{int(cnt)} (₹{val:.0f}Cr)', va='center', fontsize=7)
        
        # Detailed table
        ax2 = fig.add_subplot(2, 1, 2)
        ax2.axis('tight')
        ax2.axis('off')
        
        table_data = df.head(15)[['symbol', 'client_name', 'buy_count', 'total_qty',
                                   'avg_price', 'total_value_cr', 'buying_period_days']].copy()
        
        table_data.columns = ['Symbol', 'Client', 'Buys', 'Qty', 'Avg Price', 'Value ₹Cr', 'Days']
        table_data['Client'] = table_data['Client'].str[:25]
        table_data['Avg Price'] = table_data['Avg Price'].round(2)
        table_data['Value ₹Cr'] = table_data['Value ₹Cr'].round(0).astype(int)
        
        table = ax2.table(cellText=table_data.values,
                         colLabels=table_data.columns,
                         cellLoc='center',
                         loc='center',
                         bbox=[0, 0.1, 1, 0.8])
        
        table.auto_set_font_size(False)
        table.set_fontsize(7)
        table.scale(1, 2)
        
        for i in range(len(table_data.columns)):
            table[(0, i)].set_facecolor('#66BB6A')
            table[(0, i)].set_text_props(weight='bold', color='white')
        
        plt.tight_layout()
        pdf.savefig(fig, bbox_inches='tight')
        plt.close()
    
    def _create_unusual_activity_report(self, pdf: PdfPages, days: int):
        """Create unusual activity detection page"""
        print("Detecting unusual activity...")
        
        df = self.analyzer.detect_unusual_activity(lookback_days=days, spike_days=7)
        
        if df.empty:
            # Create placeholder page
            fig = plt.figure(figsize=(8.5, 11))
            fig.suptitle(f'UNUSUAL ACTIVITY DETECTION ({days} days)', 
                        fontsize=14, fontweight='bold', y=0.98)
            ax = fig.add_subplot(111)
            ax.text(0.5, 0.5, 'No unusual activity detected in the analysis period',
                   ha='center', va='center', fontsize=12, style='italic')
            ax.axis('off')
            pdf.savefig(fig, bbox_inches='tight')
            plt.close()
            return
        
        fig = plt.figure(figsize=(8.5, 11))
        fig.suptitle(f'UNUSUAL ACTIVITY SPIKES (Last 7 days vs baseline)', 
                    fontsize=14, fontweight='bold', y=0.98)
        
        # Spike ratio chart
        ax1 = fig.add_subplot(2, 1, 1)
        
        top_spikes = df.nlargest(15, 'deal_spike_ratio')
        
        colors = ['#FF5722' if x > 5 else '#FF9800' if x > 3 else '#FFC107' 
                 for x in top_spikes['deal_spike_ratio']]
        
        bars = ax1.barh(range(len(top_spikes)), top_spikes['deal_spike_ratio'], color=colors)
        ax1.set_yticks(range(len(top_spikes)))
        ax1.set_yticklabels(top_spikes['symbol'], fontsize=8)
        ax1.set_xlabel('Activity Spike Ratio (Recent vs Historical)', fontsize=10, fontweight='bold')
        ax1.set_title('Top 15 Unusual Activity Spikes', fontsize=11, fontweight='bold')
        ax1.grid(axis='x', alpha=0.3)
        ax1.axvline(x=2, color='red', linestyle='--', alpha=0.5, label='2x baseline')
        ax1.legend()
        
        for i, val in enumerate(top_spikes['deal_spike_ratio']):
            ax1.text(val + 0.3, i, f'{val:.1f}x', va='center', fontsize=7)
        
        # Detailed table
        ax2 = fig.add_subplot(2, 1, 2)
        ax2.axis('tight')
        ax2.axis('off')
        
        table_data = df.head(15)[['symbol', 'recent_deals', 'historical_deals',
                                   'deal_spike_ratio', 'recent_value_cr',
                                   'value_spike_ratio', 'last_deal_date']].copy()
        
        table_data.columns = ['Symbol', 'Recent', 'Historical', 'Deal Spike',
                             'Recent ₹Cr', 'Value Spike', 'Last Date']
        table_data['Deal Spike'] = table_data['Deal Spike'].round(1)
        table_data['Recent ₹Cr'] = table_data['Recent ₹Cr'].round(0).astype(int)
        table_data['Value Spike'] = table_data['Value Spike'].round(1)
        table_data['Last Date'] = pd.to_datetime(table_data['Last Date']).dt.strftime('%Y-%m-%d')
        
        table = ax2.table(cellText=table_data.values,
                         colLabels=table_data.columns,
                         cellLoc='center',
                         loc='center',
                         bbox=[0, 0.1, 1, 0.8])
        
        table.auto_set_font_size(False)
        table.set_fontsize(7)
        table.scale(1, 2)
        
        for i in range(len(table_data.columns)):
            table[(0, i)].set_facecolor('#FF9800')
            table[(0, i)].set_text_props(weight='bold', color='white')
        
        plt.tight_layout()
        pdf.savefig(fig, bbox_inches='tight')
        plt.close()
    
    def _create_price_momentum_report(self, pdf: PdfPages, days: int):
        """Create price momentum analysis page"""
        print("Analyzing price momentum...")
        
        df = self.analyzer.analyze_price_momentum(days=days)
        
        if df.empty:
            return
        
        fig = plt.figure(figsize=(8.5, 11))
        fig.suptitle(f'PRICE MOMENTUM ANALYSIS ({days} days)', 
                    fontsize=14, fontweight='bold', y=0.98)
        
        # Performance distribution
        ax1 = fig.add_subplot(2, 2, 1)
        perf_counts = df['performance'].value_counts()
        colors_perf = {'SHARP_RISE': '#4CAF50', 'RISE': '#8BC34A', 
                      'DECLINE': '#FF9800', 'SHARP_FALL': '#F44336'}
        ax1.pie(perf_counts.values, labels=perf_counts.index, autopct='%1.1f%%',
               colors=[colors_perf.get(x, '#999999') for x in perf_counts.index])
        ax1.set_title('Performance Distribution', fontsize=10, fontweight='bold')
        
        # Top gainers with deals
        ax2 = fig.add_subplot(2, 2, 2)
        top_gainers = df.nlargest(10, 'price_change_pct')
        bars = ax2.barh(range(len(top_gainers)), top_gainers['price_change_pct'], 
                       color='#4CAF50')
        ax2.set_yticks(range(len(top_gainers)))
        ax2.set_yticklabels(top_gainers['symbol'], fontsize=7)
        ax2.set_xlabel('Price Change %', fontsize=9)
        ax2.set_title('Top 10 Gainers', fontsize=10, fontweight='bold')
        ax2.grid(axis='x', alpha=0.3)
        
        # Top losers with deals
        ax3 = fig.add_subplot(2, 2, 3)
        top_losers = df.nsmallest(10, 'price_change_pct')
        bars = ax3.barh(range(len(top_losers)), top_losers['price_change_pct'], 
                       color='#F44336')
        ax3.set_yticks(range(len(top_losers)))
        ax3.set_yticklabels(top_losers['symbol'], fontsize=7)
        ax3.set_xlabel('Price Change %', fontsize=9)
        ax3.set_title('Top 10 Losers', fontsize=10, fontweight='bold')
        ax3.grid(axis='x', alpha=0.3)
        
        # Scatter: Net position vs Price change
        ax4 = fig.add_subplot(2, 2, 4)
        scatter = ax4.scatter(df['net_position_cr'], df['price_change_pct'],
                            alpha=0.6, s=30, c=df['price_change_pct'],
                            cmap='RdYlGn', vmin=-30, vmax=30)
        ax4.axhline(y=0, color='gray', linestyle='--', alpha=0.5)
        ax4.axvline(x=0, color='gray', linestyle='--', alpha=0.5)
        ax4.set_xlabel('Net Position (₹ Cr)', fontsize=9)
        ax4.set_ylabel('Price Change %', fontsize=9)
        ax4.set_title('Position vs Price Movement', fontsize=10, fontweight='bold')
        ax4.grid(alpha=0.3)
        plt.colorbar(scatter, ax=ax4, label='Price %')
        
        plt.tight_layout()
        pdf.savefig(fig, bbox_inches='tight')
        plt.close()
    
    def _create_timing_analysis_report(self, pdf: PdfPages, days: int):
        """Create timing and seasonality analysis page"""
        print("Analyzing deal timing patterns...")
        
        df = self.analyzer.analyze_deal_timing(days=days)
        
        if df.empty:
            return
        
        fig = plt.figure(figsize=(8.5, 11))
        fig.suptitle(f'TIMING & SEASONALITY ANALYSIS ({days} days)', 
                    fontsize=14, fontweight='bold', y=0.98)
        
        # Day of week analysis
        ax1 = fig.add_subplot(2, 2, 1)
        day_stats = df.groupby('day_of_week')['deals'].sum().reindex(
            ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday'], fill_value=0)
        ax1.bar(range(len(day_stats)), day_stats.values, color='#2196F3')
        ax1.set_xticks(range(len(day_stats)))
        ax1.set_xticklabels(['Mon', 'Tue', 'Wed', 'Thu', 'Fri'], fontsize=8)
        ax1.set_ylabel('Number of Deals', fontsize=9)
        ax1.set_title('Deals by Day of Week', fontsize=10, fontweight='bold')
        ax1.grid(axis='y', alpha=0.3)
        
        # Day of month analysis
        ax2 = fig.add_subplot(2, 2, 2)
        day_month_stats = df.groupby('day_of_month')['deals'].sum().sort_index()
        ax2.plot(day_month_stats.index, day_month_stats.values, marker='o', 
                color='#FF9800', linewidth=2)
        ax2.set_xlabel('Day of Month', fontsize=9)
        ax2.set_ylabel('Number of Deals', fontsize=9)
        ax2.set_title('Deals by Day of Month', fontsize=10, fontweight='bold')
        ax2.grid(alpha=0.3)
        ax2.axvspan(1, 5, alpha=0.1, color='green', label='Start of month')
        ax2.axvspan(25, 31, alpha=0.1, color='red', label='End of month')
        ax2.legend(fontsize=7)
        
        # Value by day of week
        ax3 = fig.add_subplot(2, 2, 3)
        day_value = df.groupby('day_of_week')['value_cr'].sum().reindex(
            ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday'], fill_value=0)
        ax3.bar(range(len(day_value)), day_value.values, color='#4CAF50')
        ax3.set_xticks(range(len(day_value)))
        ax3.set_xticklabels(['Mon', 'Tue', 'Wed', 'Thu', 'Fri'], fontsize=8)
        ax3.set_ylabel('Deal Value (₹ Cr)', fontsize=9)
        ax3.set_title('Value by Day of Week', fontsize=10, fontweight='bold')
        ax3.grid(axis='y', alpha=0.3)
        
        # Summary stats text
        ax4 = fig.add_subplot(2, 2, 4)
        ax4.axis('off')
        
        busiest_day = day_stats.idxmax()
        busiest_dom = day_month_stats.idxmax()
        
        summary_text = [
            "TIMING INSIGHTS:",
            "",
            f"• Busiest day: {busiest_day}",
            f"  ({int(day_stats.max())} deals)",
            "",
            f"• Busiest day of month: {int(busiest_dom)}",
            f"  ({int(day_month_stats.max())} deals)",
            "",
            f"• Average deals/day: {int(df['deals'].mean())}",
            "",
            f"• Peak activity periods:",
            "  - Start of month (settlements)",
            "  - End of month (expiry)",
            "",
            "📌 Use timing insights for",
            "   entry/exit planning"
        ]
        
        y_pos = 0.9
        for line in summary_text:
            if line.startswith('TIMING') or line.startswith('•') or line.startswith('📌'):
                weight = 'bold' if line.startswith('TIMING') or line.startswith('📌') else 'normal'
                ax4.text(0.05, y_pos, line, fontsize=9, fontweight=weight, va='top')
            else:
                ax4.text(0.05, y_pos, line, fontsize=8, va='top')
            y_pos -= 0.06
        
        plt.tight_layout()
        pdf.savefig(fig, bbox_inches='tight')
        plt.close()
    
    def _create_top_deals_report(self, pdf: PdfPages, days: int):
        """Create top deals summary page"""
        print("Compiling top deals...")
        
        from sqlalchemy import text
        cutoff_date = (datetime.now() - timedelta(days=days)).date()
        
        # Top block deals
        query_top_block = text("""
            SELECT trade_date, symbol, security_name, client_name, deal_type,
                   quantity, trade_price, quantity * trade_price / 10000000 as value_cr
            FROM nse_block_deals 
            WHERE trade_date >= :cutoff
            ORDER BY value_cr DESC
            LIMIT 15
        """)
        top_block = pd.read_sql(query_top_block, self.analyzer.engine,
                               params={'cutoff': cutoff_date})
        
        # Top bulk deals
        query_top_bulk = text("""
            SELECT trade_date, symbol, security_name, client_name, deal_type,
                   quantity, trade_price, quantity * trade_price / 10000000 as value_cr
            FROM nse_bulk_deals 
            WHERE trade_date >= :cutoff
            ORDER BY value_cr DESC
            LIMIT 15
        """)
        top_bulk = pd.read_sql(query_top_bulk, self.analyzer.engine,
                              params={'cutoff': cutoff_date})
        
        fig = plt.figure(figsize=(8.5, 11))
        fig.suptitle(f'TOP DEALS SUMMARY ({days} days)', 
                    fontsize=14, fontweight='bold', y=0.98)
        
        # Top block deals table
        ax1 = fig.add_subplot(2, 1, 1)
        ax1.axis('tight')
        ax1.axis('off')
        ax1.set_title('Top 15 Block Deals by Value', fontsize=11, fontweight='bold', 
                     loc='left', pad=10)
        
        table_block = top_block[['trade_date', 'symbol', 'client_name', 'deal_type', 
                                'quantity', 'value_cr']].copy()
        table_block.columns = ['Date', 'Symbol', 'Client', 'Type', 'Quantity', 'Value ₹Cr']
        table_block['Date'] = pd.to_datetime(table_block['Date']).dt.strftime('%Y-%m-%d')
        table_block['Client'] = table_block['Client'].str[:30]
        table_block['Quantity'] = table_block['Quantity'].apply(lambda x: f'{int(x):,}')
        table_block['Value ₹Cr'] = table_block['Value ₹Cr'].round(0).astype(int)
        
        table1 = ax1.table(cellText=table_block.values,
                          colLabels=table_block.columns,
                          cellLoc='left',
                          loc='center',
                          bbox=[0, 0, 1, 1])
        
        table1.auto_set_font_size(False)
        table1.set_fontsize(6)
        table1.scale(1, 1.5)
        
        for i in range(len(table_block.columns)):
            table1[(0, i)].set_facecolor('#1976D2')
            table1[(0, i)].set_text_props(weight='bold', color='white')
        
        # Color code buy/sell
        for i in range(1, len(table_block) + 1):
            deal_type = table_block.iloc[i-1]['Type']
            if deal_type == 'BUY':
                table1[(i, 3)].set_facecolor('#C8E6C9')
            else:
                table1[(i, 3)].set_facecolor('#FFCDD2')
        
        # Top bulk deals table
        ax2 = fig.add_subplot(2, 1, 2)
        ax2.axis('tight')
        ax2.axis('off')
        ax2.set_title('Top 15 Bulk Deals by Value', fontsize=11, fontweight='bold', 
                     loc='left', pad=10)
        
        table_bulk = top_bulk[['trade_date', 'symbol', 'client_name', 'deal_type',
                               'quantity', 'value_cr']].copy()
        table_bulk.columns = ['Date', 'Symbol', 'Client', 'Type', 'Quantity', 'Value ₹Cr']
        table_bulk['Date'] = pd.to_datetime(table_bulk['Date']).dt.strftime('%Y-%m-%d')
        table_bulk['Client'] = table_bulk['Client'].str[:30]
        table_bulk['Quantity'] = table_bulk['Quantity'].apply(lambda x: f'{int(x):,}')
        table_bulk['Value ₹Cr'] = table_bulk['Value ₹Cr'].round(0).astype(int)
        
        table2 = ax2.table(cellText=table_bulk.values,
                          colLabels=table_bulk.columns,
                          cellLoc='left',
                          loc='center',
                          bbox=[0, 0, 1, 1])
        
        table2.auto_set_font_size(False)
        table2.set_fontsize(6)
        table2.scale(1, 1.5)
        
        for i in range(len(table_bulk.columns)):
            table2[(0, i)].set_facecolor('#7B1FA2')
            table2[(0, i)].set_text_props(weight='bold', color='white')
        
        for i in range(1, len(table_bulk) + 1):
            deal_type = table_bulk.iloc[i-1]['Type']
            if deal_type == 'BUY':
                table2[(i, 3)].set_facecolor('#C8E6C9')
            else:
                table2[(i, 3)].set_facecolor('#FFCDD2')
        
        plt.tight_layout()
        pdf.savefig(fig, bbox_inches='tight')
        plt.close()
    
    def _create_recommendations_page(self, pdf: PdfPages, days: int):
        """Create investment recommendations page"""
        print("Generating investment recommendations...")
        
        # Get data for recommendations
        accum_df = self.analyzer.analyze_accumulation_distribution(days=days)
        repeat_df = self.analyzer.find_repeated_buying(min_buys=3, days=days)
        
        fig = plt.figure(figsize=(8.5, 11))
        fig.suptitle('INVESTMENT RECOMMENDATIONS', 
                    fontsize=16, fontweight='bold', y=0.98)
        
        ax = fig.add_subplot(111)
        ax.axis('off')
        
        # Generate recommendations
        recommendations = []
        
        # Strong accumulation picks
        if not accum_df.empty:
            strong_accum = accum_df[accum_df['signal'] == 'ACCUMULATION'].head(5)
            if not strong_accum.empty:
                recommendations.append("🟢 STRONG ACCUMULATION (High Confidence)")
                recommendations.append("")
                for idx, row in strong_accum.iterrows():
                    recommendations.append(
                        f"  • {row['symbol']} - Score: {row['accumulation_score']:.0f}/100"
                    )
                    recommendations.append(
                        f"    Buy/Sell: {row['buy_deals']}/{row['sell_deals']}, "
                        f"Value: ₹{row['buy_value_cr']:.0f}Cr buy vs ₹{row['sell_value_cr']:.0f}Cr sell"
                    )
                recommendations.append("")
        
        # Repeated buying picks
        if not repeat_df.empty:
            strong_repeat = repeat_df.head(5)
            recommendations.append("🔄 CONSISTENT BUYING (Systematic Accumulation)")
            recommendations.append("")
            for idx, row in strong_repeat.iterrows():
                recommendations.append(
                    f"  • {row['symbol']} by {row['client_name'][:30]}"
                )
                recommendations.append(
                    f"    {int(row['buy_count'])} buys over {int(row['buying_period_days'])} days, "
                    f"Total: ₹{row['total_value_cr']:.0f}Cr"
                )
            recommendations.append("")
        
        # Distribution warnings
        if not accum_df.empty:
            strong_dist = accum_df[accum_df['signal'] == 'DISTRIBUTION'].head(5)
            if not strong_dist.empty:
                recommendations.append("🔴 AVOID - DISTRIBUTION DETECTED")
                recommendations.append("")
                for idx, row in strong_dist.iterrows():
                    recommendations.append(
                        f"  • {row['symbol']} - Score: {row['accumulation_score']:.0f}/100"
                    )
                    recommendations.append(
                        f"    Heavy selling: ₹{row['sell_value_cr']:.0f}Cr vs ₹{row['buy_value_cr']:.0f}Cr"
                    )
                recommendations.append("")
        
        # General guidelines
        recommendations.append("=" * 70)
        recommendations.append("INVESTMENT GUIDELINES:")
        recommendations.append("")
        recommendations.append("✓ POSITIVE SIGNALS:")
        recommendations.append("  • Accumulation score > 60")
        recommendations.append("  • Repeated buying by same client (3+ times)")
        recommendations.append("  • Smart money (FII/DII/MF) buying")
        recommendations.append("  • Net positive position (Buys > Sells)")
        recommendations.append("")
        recommendations.append("✗ NEGATIVE SIGNALS:")
        recommendations.append("  • Distribution score < 40")
        recommendations.append("  • Single client concentration (>80%)")
        recommendations.append("  • Smart money selling")
        recommendations.append("  • Unusual spike followed by price drop")
        recommendations.append("")
        recommendations.append("⚠️  RISK FACTORS:")
        recommendations.append("  • Block/bulk deals show intent, not guaranteed outcomes")
        recommendations.append("  • Always correlate with technical & fundamental analysis")
        recommendations.append("  • Watch for operator-driven activity (high concentration)")
        recommendations.append("  • Set stop losses - deals can reverse")
        recommendations.append("")
        recommendations.append("📊 BEST PRACTICES:")
        recommendations.append("  • Combine multiple signals for higher confidence")
        recommendations.append("  • Track smart money consistently, not one-off deals")
        recommendations.append("  • Wait for price confirmation before entry")
        recommendations.append("  • Monitor for follow-through in subsequent weeks")
        
        # Render recommendations
        y_pos = 0.95
        for line in recommendations:
            if line.startswith('🟢') or line.startswith('🔄') or line.startswith('🔴'):
                ax.text(0.05, y_pos, line, fontsize=11, fontweight='bold',
                       family='sans-serif', va='top')
                y_pos -= 0.030
            elif line.startswith('='):
                ax.text(0.05, y_pos, line, fontsize=9, family='monospace', va='top')
                y_pos -= 0.025
            elif line.startswith('✓') or line.startswith('✗') or line.startswith('⚠️') or line.startswith('📊'):
                ax.text(0.05, y_pos, line, fontsize=10, fontweight='bold',
                       family='sans-serif', va='top')
                y_pos -= 0.025
            elif line.startswith('  •'):
                ax.text(0.05, y_pos, line, fontsize=9, family='sans-serif', va='top')
                y_pos -= 0.023
            elif line.startswith('    '):
                ax.text(0.05, y_pos, line, fontsize=8, family='monospace',
                       color='#666666', va='top')
                y_pos -= 0.020
            elif line == "":
                y_pos -= 0.015
            else:
                ax.text(0.05, y_pos, line, fontsize=9, family='sans-serif', va='top')
                y_pos -= 0.023
        
        # Footer
        ax.text(0.5, 0.02, 'Past performance does not guarantee future results. Invest at your own risk.',
               ha='center', va='bottom', fontsize=7, style='italic', color='#888888')
        
        plt.tight_layout()
        pdf.savefig(fig, bbox_inches='tight')
        plt.close()


def main():
    """Generate PDF report"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Generate Block & Bulk Deals PDF Report')
    parser.add_argument('--days', type=int, default=365, 
                       help='Number of days to analyze (default: 365)')
    parser.add_argument('--output', type=str, default=None,
                       help='Output PDF filename (default: auto-generated)')
    
    args = parser.parse_args()
    
    reporter = BlockBulkDealsPDFReport()
    output_file = reporter.generate_annual_report(output_file=args.output, days=args.days)
    
    print(f"\n✅ Report saved to: {output_file}")
    print(f"📂 Open the file to view comprehensive analysis\n")


if __name__ == '__main__':
    main()
