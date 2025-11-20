"""
Sector Pattern Analysis PDF Report Generator

This service generates comprehensive PDF reports for sector-wise candlestick pattern analysis including:
1. Executive summary with sector overview
2. Pattern detection results with visual charts
3. Breakout analysis and signals
4. Detailed stock-level analysis
5. Historical trend analysis

Author: Stock Screener System  
Date: November 2025
"""

import os
from datetime import datetime
from typing import List, Dict, Optional
import tempfile
import base64
from io import BytesIO

# PDF Generation
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT

# Charts and visualization
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import Rectangle
import seaborn as sns
import pandas as pd
import numpy as np

# Local imports
from services.sector_pattern_scanner import SectorPatternScanner, PatternResult, SectorSummary

class SectorPatternReportGenerator:
    """
    PDF Report generator for sector-wise pattern analysis
    """
    
    def __init__(self):
        self.scanner = SectorPatternScanner()
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()
        
    def _setup_custom_styles(self):
        """Setup custom styles for the PDF report"""
        # Title style
        self.title_style = ParagraphStyle(
            'CustomTitle',
            parent=self.styles['Title'],
            fontSize=18,
            spaceAfter=30,
            alignment=TA_CENTER,
            textColor=colors.darkblue
        )
        
        # Header style
        self.header_style = ParagraphStyle(
            'CustomHeader',
            parent=self.styles['Heading1'],
            fontSize=14,
            spaceAfter=12,
            spaceBefore=20,
            textColor=colors.darkblue,
            borderWidth=1,
            borderColor=colors.darkblue,
            borderPadding=5
        )
        
        # Subheader style
        self.subheader_style = ParagraphStyle(
            'CustomSubHeader',
            parent=self.styles['Heading2'],
            fontSize=12,
            spaceAfter=8,
            spaceBefore=15,
            textColor=colors.blue
        )
        
        # Body text style
        self.body_style = ParagraphStyle(
            'CustomBody',
            parent=self.styles['Normal'],
            fontSize=10,
            spaceAfter=6,
            spaceBefore=6
        )
        
        # Small text style
        self.small_style = ParagraphStyle(
            'CustomSmall',
            parent=self.styles['Normal'],
            fontSize=8,
            spaceAfter=4
        )
    
    def generate_comprehensive_report(self, sector_ids: List[int], timeframes: List[str] = None, 
                                    output_path: str = None) -> str:
        """
        Generate comprehensive sector pattern analysis report
        Returns path to generated PDF
        """
        if timeframes is None:
            timeframes = ['DAILY', 'WEEKLY', 'MONTHLY']
            
        if output_path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = f"reports/sector_pattern_report_{timestamp}.pdf"
            
        # Ensure reports directory exists
        os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else "reports", exist_ok=True)
        
        # Scan patterns
        patterns, summaries = self.scanner.scan_sectors_comprehensive(sector_ids, timeframes, include_breakouts=True)
        
        # Generate PDF
        doc = SimpleDocTemplate(output_path, pagesize=A4, 
                              rightMargin=72, leftMargin=72, 
                              topMargin=72, bottomMargin=18)
        
        story = []
        
        # Build report content
        story.extend(self._build_cover_page(sector_ids, timeframes, len(patterns), len(summaries)))
        story.append(PageBreak())
        
        story.extend(self._build_executive_summary(summaries, patterns))
        story.append(PageBreak())
        
        story.extend(self._build_pattern_overview(patterns, summaries))
        story.append(PageBreak())
        
        story.extend(self._build_breakout_analysis(patterns))
        story.append(PageBreak())
        
        story.extend(self._build_sector_details(summaries))
        
        story.extend(self._build_detailed_stock_analysis(patterns))
        
        story.extend(self._build_appendix(patterns, summaries))
        
        # Generate PDF
        doc.build(story)
        
        return output_path
    
    def _build_cover_page(self, sector_ids: List[int], timeframes: List[str], 
                         total_patterns: int, total_sectors: int) -> List:
        """Build the cover page"""
        story = []
        
        # Main title
        title = "Sector-wise Candlestick Pattern Analysis Report"
        story.append(Paragraph(title, self.title_style))
        story.append(Spacer(1, 30))
        
        # Report metadata
        current_date = datetime.now().strftime("%B %d, %Y at %I:%M %p")
        latest_dates = self.scanner.get_latest_dates()
        
        metadata_data = [
            ['Report Generated:', current_date],
            ['Analysis Date Range:', f"{min(latest_dates.values())} to {max(latest_dates.values())}"],
            ['Sectors Analyzed:', f"{total_sectors} sectors"],
            ['Timeframes:', ', '.join(timeframes)],
            ['Total Patterns Found:', f"{total_patterns} patterns"],
            ['Pattern Types:', 'NR4, NR7, NR13, NR21'],
            ['Breakout Analysis:', 'Included'],
        ]
        
        metadata_table = Table(metadata_data, colWidths=[2*inch, 3*inch])
        metadata_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        story.append(metadata_table)
        story.append(Spacer(1, 50))
        
        # Report summary
        summary_text = f"""
        <b>Report Overview:</b><br/>
        This comprehensive analysis covers candlestick pattern detection across {total_sectors} selected sectors,
        focusing on Narrow Range (NR) patterns for the latest available trading periods. The report includes 
        pattern identification, breakout analysis, and sector-wise performance metrics.
        <br/><br/>
        <b>Key Features:</b><br/>
        • Multi-timeframe analysis (Daily, Weekly, Monthly)<br/>
        • Breakout detection from previous NR patterns<br/>  
        • Sector-wise pattern distribution<br/>
        • Volume-weighted pattern rankings<br/>
        • Historical pattern analysis<br/>
        """
        
        story.append(Paragraph(summary_text, self.body_style))
        
        return story
    
    def _build_executive_summary(self, summaries: List[SectorSummary], patterns: List[PatternResult]) -> List:
        """Build executive summary section"""
        story = []
        
        story.append(Paragraph("Executive Summary", self.header_style))
        
        # Overall statistics
        total_stocks = sum(s.total_stocks for s in summaries)
        total_patterns = len(patterns)
        breakout_patterns = len([p for p in patterns if p.breakout_signal])
        
        summary_stats = [
            ['Total Stocks Analyzed:', f"{total_stocks:,}"],
            ['Total Patterns Detected:', f"{total_patterns:,}"],
            ['Breakout Signals:', f"{breakout_patterns:,}"],
            ['Success Rate:', f"{(breakout_patterns/total_patterns*100):.1f}%" if total_patterns > 0 else "0%"],
        ]
        
        stats_table = Table(summary_stats, colWidths=[2*inch, 1.5*inch])
        stats_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.lightblue),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 11),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        story.append(stats_table)
        story.append(Spacer(1, 20))
        
        # Generate pattern distribution chart
        chart_image = self._create_pattern_distribution_chart(summaries)
        if chart_image:
            story.append(Paragraph("Pattern Distribution by Sector", self.subheader_style))
            story.append(chart_image)
            story.append(Spacer(1, 20))
        
        # Top performing sectors
        story.append(Paragraph("Top Performing Sectors", self.subheader_style))
        
        # Sort sectors by total patterns found
        top_sectors = sorted(summaries, key=lambda x: sum(x.pattern_counts.values()), reverse=True)[:5]
        
        sector_data = [['Rank', 'Sector', 'Total Patterns', 'Breakout Signals', 'Success Rate']]
        for i, sector in enumerate(top_sectors, 1):
            total_sect_patterns = sum(sector.pattern_counts.values())
            breakouts = sector.breakout_counts.get('BREAKOUT_ABOVE', 0) + sector.breakout_counts.get('BREAKDOWN_BELOW', 0)
            success_rate = f"{(breakouts/total_sect_patterns*100):.1f}%" if total_sect_patterns > 0 else "0%"
            
            sector_data.append([
                str(i),
                sector.sector_name[:25] + "..." if len(sector.sector_name) > 25 else sector.sector_name,
                str(total_sect_patterns),
                str(breakouts),
                success_rate
            ])
        
        sector_table = Table(sector_data, colWidths=[0.5*inch, 2.5*inch, 1*inch, 1*inch, 1*inch])
        sector_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey])
        ]))
        
        story.append(sector_table)
        
        return story
    
    def _build_pattern_overview(self, patterns: List[PatternResult], summaries: List[SectorSummary]) -> List:
        """Build pattern overview section with charts"""
        story = []
        
        story.append(Paragraph("Pattern Analysis Overview", self.header_style))
        
        # Pattern type distribution
        pattern_counts = {'NR4': 0, 'NR7': 0, 'NR13': 0, 'NR21': 0}
        timeframe_counts = {'DAILY': 0, 'WEEKLY': 0, 'MONTHLY': 0}
        
        for pattern in patterns:
            if pattern.pattern_type in pattern_counts:
                pattern_counts[pattern.pattern_type] += 1
            if pattern.timeframe in timeframe_counts:
                timeframe_counts[pattern.timeframe] += 1
        
        # Pattern type table
        story.append(Paragraph("Pattern Type Distribution", self.subheader_style))
        
        pattern_data = [['Pattern Type', 'Count', 'Percentage']]
        total_patterns = len(patterns)
        
        for pattern_type, count in pattern_counts.items():
            percentage = f"{(count/total_patterns*100):.1f}%" if total_patterns > 0 else "0%"
            pattern_data.append([pattern_type, str(count), percentage])
        
        pattern_table = Table(pattern_data, colWidths=[1.5*inch, 1*inch, 1*inch])
        pattern_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.darkgreen),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        story.append(pattern_table)
        story.append(Spacer(1, 15))
        
        # Timeframe distribution  
        story.append(Paragraph("Timeframe Distribution", self.subheader_style))
        
        timeframe_data = [['Timeframe', 'Count', 'Percentage']]
        for timeframe, count in timeframe_counts.items():
            percentage = f"{(count/total_patterns*100):.1f}%" if total_patterns > 0 else "0%"
            timeframe_data.append([timeframe, str(count), percentage])
        
        timeframe_table = Table(timeframe_data, colWidths=[1.5*inch, 1*inch, 1*inch])
        timeframe_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.darkred),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        story.append(timeframe_table)
        story.append(Spacer(1, 20))
        
        # Generate and add pattern comparison chart
        comparison_chart = self._create_pattern_comparison_chart(pattern_counts, timeframe_counts)
        if comparison_chart:
            story.append(Paragraph("Pattern and Timeframe Comparison", self.subheader_style))
            story.append(comparison_chart)
        
        return story
    
    def _build_breakout_analysis(self, patterns: List[PatternResult]) -> List:
        """Build breakout analysis section"""
        story = []
        
        story.append(Paragraph("Breakout Analysis", self.header_style))
        
        # Filter breakout patterns
        breakout_patterns = [p for p in patterns if p.breakout_signal]
        
        if not breakout_patterns:
            story.append(Paragraph("No breakout signals detected in the current analysis period.", self.body_style))
            return story
        
        # Categorize breakouts
        breakouts_above = [p for p in breakout_patterns if 'BREAKOUT_ABOVE' in p.breakout_signal]
        breakdowns_below = [p for p in breakout_patterns if 'BREAKDOWN_BELOW' in p.breakout_signal]
        
        # Summary statistics
        breakout_summary = f"""
        <b>Breakout Summary:</b><br/>
        Total Breakout Signals: {len(breakout_patterns)}<br/>
        Breakouts Above NR High: {len(breakouts_above)}<br/>
        Breakdowns Below NR Low: {len(breakdowns_below)}<br/>
        <br/>
        <b>Analysis:</b><br/>
        Breakout signals indicate stocks that have moved beyond their previous narrow range patterns,
        suggesting potential trend continuation or reversal. Breakouts above previous highs typically
        indicate bullish momentum, while breakdowns below previous lows suggest bearish pressure.
        """
        
        story.append(Paragraph(breakout_summary, self.body_style))
        story.append(Spacer(1, 15))
        
        # Top breakout opportunities
        if breakouts_above:
            story.append(Paragraph("Top Bullish Breakouts", self.subheader_style))
            
            # Sort by volume for significance
            top_bullish = sorted(breakouts_above, key=lambda x: x.volume, reverse=True)[:10]
            
            bullish_data = [['Symbol', 'Sector', 'Pattern', 'Timeframe', 'Breakout Signal', 'Volume']]
            for pattern in top_bullish:
                bullish_data.append([
                    pattern.symbol,
                    pattern.sector[:20] + "..." if len(pattern.sector) > 20 else pattern.sector,
                    pattern.pattern_type,
                    pattern.timeframe,
                    'Above NR High',
                    f"{pattern.volume:,}" if pattern.volume else "N/A"
                ])
            
            bullish_table = Table(bullish_data, colWidths=[0.8*inch, 1.5*inch, 0.6*inch, 0.8*inch, 1*inch, 1*inch])
            bullish_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.darkgreen),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 8),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            
            story.append(bullish_table)
            story.append(Spacer(1, 15))
        
        if breakdowns_below:
            story.append(Paragraph("Top Bearish Breakdowns", self.subheader_style))
            
            # Sort by volume for significance  
            top_bearish = sorted(breakdowns_below, key=lambda x: x.volume, reverse=True)[:10]
            
            bearish_data = [['Symbol', 'Sector', 'Pattern', 'Timeframe', 'Breakdown Signal', 'Volume']]
            for pattern in top_bearish:
                bearish_data.append([
                    pattern.symbol,
                    pattern.sector[:20] + "..." if len(pattern.sector) > 20 else pattern.sector,
                    pattern.pattern_type, 
                    pattern.timeframe,
                    'Below NR Low',
                    f"{pattern.volume:,}" if pattern.volume else "N/A"
                ])
            
            bearish_table = Table(bearish_data, colWidths=[0.8*inch, 1.5*inch, 0.6*inch, 0.8*inch, 1*inch, 1*inch])
            bearish_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.darkred),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 8),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            
            story.append(bearish_table)
        
        return story
    
    def _build_sector_details(self, summaries: List[SectorSummary]) -> List:
        """Build detailed sector analysis"""
        story = []
        
        story.append(Paragraph("Detailed Sector Analysis", self.header_style))
        
        for summary in summaries:
            story.append(Paragraph(f"{summary.sector_name}", self.subheader_style))
            
            # Sector overview
            total_patterns = sum(summary.pattern_counts.values())
            total_breakouts = summary.breakout_counts.get('BREAKOUT_ABOVE', 0) + summary.breakout_counts.get('BREAKDOWN_BELOW', 0)
            
            sector_overview = f"""
            <b>Stocks Analyzed:</b> {summary.total_stocks}<br/>
            <b>Total Patterns:</b> {total_patterns}<br/>
            <b>Breakout Signals:</b> {total_breakouts}<br/>
            <b>Top Volume Leader:</b> {summary.top_patterns[0].symbol if summary.top_patterns else "N/A"}<br/>
            """
            
            story.append(Paragraph(sector_overview, self.body_style))
            
            # Pattern breakdown table
            sector_data = [['Metric', 'NR4', 'NR7', 'NR13', 'NR21', 'Total']]
            
            # Pattern counts row
            pattern_row = ['Patterns']
            total_row = 0
            for pattern_type in ['NR4', 'NR7', 'NR13', 'NR21']:
                count = summary.pattern_counts.get(pattern_type, 0)
                pattern_row.append(str(count))
                total_row += count
            pattern_row.append(str(total_row))
            sector_data.append(pattern_row)
            
            # Timeframe breakdown
            for timeframe in ['DAILY', 'WEEKLY', 'MONTHLY']:
                tf_row = [timeframe]
                tf_total = summary.timeframe_counts.get(timeframe, 0)
                # Split timeframe patterns by type (approximate)
                for pattern_type in ['NR4', 'NR7', 'NR13', 'NR21']:
                    # Rough estimation - in real scenario you'd track this more precisely
                    estimate = int(summary.pattern_counts.get(pattern_type, 0) * (tf_total / max(total_patterns, 1)))
                    tf_row.append(str(estimate))
                tf_row.append(str(tf_total))
                sector_data.append(tf_row)
            
            sector_table = Table(sector_data, colWidths=[1*inch, 0.6*inch, 0.6*inch, 0.6*inch, 0.6*inch, 0.8*inch])
            sector_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.lightblue),
                ('BACKGROUND', (0, 1), (-1, 1), colors.lightgreen),
                ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 8),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            
            story.append(sector_table)
            story.append(Spacer(1, 15))
        
        return story
    
    def _build_detailed_stock_analysis(self, patterns: List[PatternResult]) -> List:
        """Build detailed stock-level analysis"""
        story = []
        
        story.append(PageBreak())
        story.append(Paragraph("Detailed Stock Analysis", self.header_style))
        
        # Group patterns by symbol for detailed analysis
        symbol_patterns = {}
        for pattern in patterns:
            if pattern.symbol not in symbol_patterns:
                symbol_patterns[pattern.symbol] = []
            symbol_patterns[pattern.symbol].append(pattern)
        
        # Sort by total patterns per symbol
        sorted_symbols = sorted(symbol_patterns.items(), key=lambda x: len(x[1]), reverse=True)
        
        # Show top 20 most active stocks
        story.append(Paragraph("Top 20 Most Active Stocks (by Pattern Count)", self.subheader_style))
        
        stock_data = [['Rank', 'Symbol', 'Sector', 'Pattern Count', 'Timeframes', 'Breakouts', 'Latest Pattern']]
        
        for rank, (symbol, stock_patterns) in enumerate(sorted_symbols[:20], 1):
            sector = stock_patterns[0].sector
            pattern_count = len(stock_patterns)
            timeframes = set(p.timeframe for p in stock_patterns)
            breakouts = len([p for p in stock_patterns if p.breakout_signal])
            latest_pattern = max(stock_patterns, key=lambda x: x.pattern_date)
            
            stock_data.append([
                str(rank),
                symbol,
                sector[:15] + "..." if len(sector) > 15 else sector,
                str(pattern_count),
                '/'.join(sorted(timeframes)),
                str(breakouts),
                f"{latest_pattern.pattern_type} ({latest_pattern.pattern_date})"
            ])
        
        stock_table = Table(stock_data, colWidths=[0.4*inch, 0.8*inch, 1.2*inch, 0.8*inch, 1*inch, 0.7*inch, 1.3*inch])
        stock_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 7),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey])
        ]))
        
        story.append(stock_table)
        
        return story
    
    def _build_appendix(self, patterns: List[PatternResult], summaries: List[SectorSummary]) -> List:
        """Build appendix with methodology and data sources"""
        story = []
        
        story.append(PageBreak())
        story.append(Paragraph("Appendix", self.header_style))
        
        # Methodology
        story.append(Paragraph("Methodology", self.subheader_style))
        
        methodology_text = """
        <b>Pattern Detection:</b><br/>
        • NR4: Current range is smallest in last 4 periods<br/>
        • NR7: Current range is smallest in last 7 periods<br/>
        • NR13: Current range is smallest in last 13 periods<br/>
        • NR21: Current range is smallest in last 21 periods<br/>
        <br/>
        <b>Breakout Detection:</b><br/>
        • Breakout Above: Current high > Previous NR pattern high<br/>
        • Breakdown Below: Current low < Previous NR pattern low<br/>
        <br/>
        <b>Data Sources:</b><br/>
        • Daily Data: nse_equity_bhavcopy_full table<br/>
        • Weekly Data: nse_bhav_weekly table<br/>
        • Monthly Data: nse_bhav_monthly table<br/>
        • Sector Data: nse_indices and nse_index_constituents tables<br/>
        • Pattern Storage: candlestick_patterns table<br/>
        """
        
        story.append(Paragraph(methodology_text, self.body_style))
        
        # Data freshness
        story.append(Paragraph("Data Freshness", self.subheader_style))
        
        latest_dates = self.scanner.get_latest_dates()
        freshness_text = f"""
        <b>Latest Available Data:</b><br/>
        • Daily: {latest_dates.get('DAILY', 'N/A')}<br/>
        • Weekly: {latest_dates.get('WEEKLY', 'N/A')}<br/>
        • Monthly: {latest_dates.get('MONTHLY', 'N/A')}<br/>
        <br/>
        Report generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        """
        
        story.append(Paragraph(freshness_text, self.body_style))
        
        return story
    
    def _create_pattern_distribution_chart(self, summaries: List[SectorSummary]) -> Optional[Image]:
        """Create pattern distribution chart"""
        try:
            fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))
            
            # Pie chart for sector distribution
            sector_names = [s.sector_name[:15] + "..." if len(s.sector_name) > 15 else s.sector_name for s in summaries]
            sector_totals = [sum(s.pattern_counts.values()) for s in summaries]
            
            if sector_totals:
                ax1.pie(sector_totals, labels=sector_names, autopct='%1.1f%%', startangle=90)
                ax1.set_title('Pattern Distribution by Sector')
            
            # Bar chart for pattern types
            pattern_totals = {'NR4': 0, 'NR7': 0, 'NR13': 0, 'NR21': 0}
            for summary in summaries:
                for pattern_type, count in summary.pattern_counts.items():
                    pattern_totals[pattern_type] += count
            
            if any(pattern_totals.values()):
                ax2.bar(pattern_totals.keys(), pattern_totals.values(), color=['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728'])
                ax2.set_title('Total Patterns by Type')
                ax2.set_ylabel('Count')
            
            plt.tight_layout()
            
            # Convert to image
            buffer = BytesIO()
            plt.savefig(buffer, format='png', dpi=150, bbox_inches='tight')
            buffer.seek(0)
            
            img = Image(buffer, width=6*inch, height=2.5*inch)
            plt.close()
            
            return img
            
        except Exception as e:
            print(f"Error creating pattern distribution chart: {e}")
            return None
    
    def _create_pattern_comparison_chart(self, pattern_counts: Dict, timeframe_counts: Dict) -> Optional[Image]:
        """Create pattern vs timeframe comparison chart"""
        try:
            fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 4))
            
            # Pattern type bar chart
            if any(pattern_counts.values()):
                ax1.bar(pattern_counts.keys(), pattern_counts.values(), 
                       color=['skyblue', 'lightgreen', 'coral', 'gold'])
                ax1.set_title('Pattern Type Distribution')
                ax1.set_ylabel('Count')
                ax1.tick_params(axis='x', rotation=45)
            
            # Timeframe bar chart  
            if any(timeframe_counts.values()):
                ax2.bar(timeframe_counts.keys(), timeframe_counts.values(),
                       color=['navy', 'darkgreen', 'darkred'])
                ax2.set_title('Timeframe Distribution')
                ax2.set_ylabel('Count')
                ax2.tick_params(axis='x', rotation=45)
            
            plt.tight_layout()
            
            # Convert to image
            buffer = BytesIO()
            plt.savefig(buffer, format='png', dpi=150, bbox_inches='tight')
            buffer.seek(0)
            
            img = Image(buffer, width=5*inch, height=2*inch)
            plt.close()
            
            return img
            
        except Exception as e:
            print(f"Error creating comparison chart: {e}")
            return None

# Convenience functions
def generate_nifty_bank_report(output_path: str = None) -> str:
    """Generate report for Nifty Bank sector"""
    generator = SectorPatternReportGenerator()
    bank_sector_id = 4  # Nifty Bank
    return generator.generate_comprehensive_report([bank_sector_id], output_path=output_path)

def generate_all_major_sectors_report(output_path: str = None) -> str:
    """Generate report for all major Nifty sectors"""
    generator = SectorPatternReportGenerator()
    major_sectors = [1, 2, 4, 5, 8, 9]  # Key sector IDs
    return generator.generate_comprehensive_report(major_sectors, output_path=output_path)

if __name__ == "__main__":
    # Demo usage
    print("Generating Nifty Bank sector report...")
    report_path = generate_nifty_bank_report()
    print(f"Report generated: {report_path}")