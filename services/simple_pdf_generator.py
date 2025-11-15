#!/usr/bin/env python3
"""
Simplified PDF Report Generator for Sectoral Analysis
A more robust version that handles database connection issues gracefully.
"""

import os
import sys
from datetime import datetime, date
from typing import Dict, List, Optional, Tuple
import pandas as pd

# Add current directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from reportlab.lib.pagesizes import letter, A4
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.lib.colors import HexColor, black, white, green, red, blue, gray
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False

from services.market_breadth_service import get_sectoral_breadth

def generate_simple_sectoral_pdf_report(analysis_date: str, output_path: Optional[str] = None) -> Tuple[bool, str]:
    """
    Generate a simplified sectoral analysis PDF report.
    This version uses the GUI functions directly to avoid database issues.
    """
    if not REPORTLAB_AVAILABLE:
        return False, "ReportLab library not installed. Please install with: pip install reportlab"
    
    try:
        # Setup output path in reports folder
        if not output_path:
            # Create reports directory if it doesn't exist
            reports_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "reports", "sectoral_analysis")
            os.makedirs(reports_dir, exist_ok=True)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            date_str = analysis_date.replace('-', '')
            filename = f"Sectoral_Analysis_Report_{date_str}_{timestamp}.pdf"
            output_path = os.path.join(reports_dir, filename)
        
        # Initialize document
        doc = SimpleDocTemplate(
            output_path,
            pagesize=A4,
            rightMargin=72,
            leftMargin=72,
            topMargin=72,
            bottomMargin=72
        )
        
        # Setup styles
        styles = getSampleStyleSheet()
        
        # Custom styles
        styles.add(ParagraphStyle(
            name='CustomTitle',
            parent=styles['Title'],
            fontSize=20,
            spaceAfter=20,
            textColor=HexColor('#1f4e79'),
            alignment=TA_CENTER
        ))
        
        styles.add(ParagraphStyle(
            name='CustomHeading',
            parent=styles['Heading1'],
            fontSize=14,
            spaceBefore=15,
            spaceAfter=10,
            textColor=HexColor('#2e75b6')
        ))
        
        story = []
        
        # Title page
        title = Paragraph("SECTORAL TREND ANALYSIS REPORT", styles['CustomTitle'])
        story.append(title)
        story.append(Spacer(1, 0.5*inch))
        
        # Analysis date
        date_formatted = datetime.strptime(analysis_date, '%Y-%m-%d').strftime('%B %d, %Y')
        date_para = Paragraph(f"<b>Analysis Date:</b> {date_formatted}", styles['Normal'])
        story.append(date_para)
        
        # Generated timestamp
        generated_time = datetime.now().strftime('%B %d, %Y at %I:%M %p')
        generated_para = Paragraph(f"<b>Generated:</b> {generated_time}", styles['Normal'])
        story.append(generated_para)
        story.append(Spacer(1, 0.5*inch))
        
        # Get sectoral data using GUI functions
        major_sectors = [
            'NIFTY-PHARMA', 'NIFTY-BANK', 'NIFTY-IT', 'NIFTY-AUTO',
            'NIFTY-FMCG', 'NIFTY-REALTY', 'NIFTY-METAL', 'NIFTY-ENERGY',
            'NIFTY-HEALTHCARE-INDEX', 'NIFTY-CONSUMER-DURABLES'
        ]
        
        # Convert analysis_date string to date object
        try:
            if isinstance(analysis_date, str):
                analysis_date_obj = datetime.strptime(analysis_date, '%Y-%m-%d').date()
            else:
                analysis_date_obj = analysis_date
        except ValueError:
            # If date parsing fails, use None to get latest date
            analysis_date_obj = None
        
        sector_results = []
        successful_sectors = 0
        
        for sector in major_sectors:
            try:
                result = get_sectoral_breadth(sector, analysis_date=analysis_date_obj)
                if result and result.get('success') == True:
                    # Extract summary data from the result structure
                    breadth_summary = result.get('breadth_summary', {})
                    technical_breadth = result.get('technical_breadth', {})
                    sector_results.append({
                        'sector': sector.replace('NIFTY-', ''),
                        'total_stocks': result.get('total_stocks', 0),
                        'bullish_count': breadth_summary.get('bullish_count', 0),
                        'bearish_count': breadth_summary.get('bearish_count', 0),
                        'bullish_percent': breadth_summary.get('bullish_percent', 0),
                        'bearish_percent': breadth_summary.get('bearish_percent', 0),
                        'avg_rating': result.get('rating_percentages', {}).get('Very Bullish', 0),
                        'daily_uptrend_percent': technical_breadth.get('daily_uptrend_percent', 0),
                        'weekly_uptrend_percent': technical_breadth.get('weekly_uptrend_percent', 0)
                    })
                    successful_sectors += 1
            except Exception as e:
                print(f"Error getting data for {sector}: {e}")
                continue
        
        if not sector_results:
            return False, "No sectoral data could be retrieved for the selected date"
        
        # Sort by bullish percentage
        sector_results.sort(key=lambda x: x['bullish_percent'], reverse=True)
        
        # Executive Summary
        story.append(Paragraph("EXECUTIVE SUMMARY", styles['CustomHeading']))
        
        total_stocks = sum(s['total_stocks'] for s in sector_results)
        total_bullish = sum(s['bullish_count'] for s in sector_results)
        overall_bullish_pct = (total_bullish / total_stocks * 100) if total_stocks > 0 else 0
        
        summary_text = f"""
        <b>Market Overview:</b> Analysis of {successful_sectors} major sectors covering {total_stocks} stocks 
        shows an overall bullish sentiment of {overall_bullish_pct:.1f}%.
        <br/><br/>
        <b>Top Performing Sectors:</b><br/>
        """
        
        # Add top 3 sectors
        for sector in sector_results[:3]:
            summary_text += f"• {sector['sector']}: {sector['bullish_percent']:.1f}% bullish ({sector['total_stocks']} stocks)<br/>"
        
        summary_text += f"<br/><b>Weakest Performing Sectors:</b><br/>"
        # Add bottom 3 sectors
        for sector in sector_results[-3:]:
            summary_text += f"• {sector['sector']}: {sector['bullish_percent']:.1f}% bullish ({sector['total_stocks']} stocks)<br/>"
        
        # Market sentiment
        if overall_bullish_pct >= 60:
            sentiment = "STRONG BULLISH"
            color = "green"
        elif overall_bullish_pct >= 50:
            sentiment = "MODERATELY BULLISH" 
            color = "blue"
        elif overall_bullish_pct >= 40:
            sentiment = "MIXED/NEUTRAL"
            color = "orange"
        else:
            sentiment = "BEARISH"
            color = "red"
        
        summary_text += f"<br/><br/><b>Overall Market Sentiment:</b> <font color='{color}'>{sentiment}</font>"
        
        summary_para = Paragraph(summary_text, styles['Normal'])
        story.append(summary_para)
        story.append(Spacer(1, 0.3*inch))
        
        # Sector Rankings Table
        story.append(Paragraph("SECTOR PERFORMANCE RANKINGS", styles['CustomHeading']))
        
        # Create table data
        table_data = [
            ['Rank', 'Sector', 'Total Stocks', 'Bullish %', 'Bearish %', 'Avg Rating']
        ]
        
        for rank, sector in enumerate(sector_results, 1):
            table_data.append([
                str(rank),
                sector['sector'],
                str(sector['total_stocks']),
                f"{sector['bullish_percent']:.1f}%",
                f"{sector['bearish_percent']:.1f}%",
                f"{sector['avg_rating']:.2f}"
            ])
        
        # Create table
        table = Table(table_data, colWidths=[0.5*inch, 2.2*inch, 1.0*inch, 1.0*inch, 1.0*inch, 1.0*inch])
        
        # Table styling
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), HexColor('#2e75b6')),
            ('TEXTCOLOR', (0, 0), (-1, 0), white),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), white),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('GRID', (0, 0), (-1, -1), 1, black),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            
            # Color coding for performance
            ('BACKGROUND', (3, 1), (3, 3), HexColor('#d4edda')),  # Top 3 - green
            ('BACKGROUND', (3, -3), (3, -1), HexColor('#f8d7da')),  # Bottom 3 - red
        ]))
        
        story.append(table)
        story.append(Spacer(1, 0.3*inch))
        
        # Add detailed sector breakdown
        story.append(PageBreak())
        story.append(Paragraph("DETAILED SECTOR STOCK ANALYSIS", styles['CustomHeading']))
        story.append(Spacer(1, 0.3*inch))
        
        # Create detailed analysis for each sector
        for sector_data in sector_results[:5]:  # Top 5 sectors only for PDF space
            sector_name = sector_data['sector']
            sector_code = f"NIFTY-{sector_name}" if not sector_name.startswith('NIFTY') else sector_name
            
            # Get detailed stock data for this sector
            sector_result = get_sectoral_breadth(sector_code, analysis_date=analysis_date_obj)
            if sector_result and sector_result.get('success'):
                sector_df = sector_result.get('sector_data')
                
                if sector_df is not None and not sector_df.empty:
                    # Sector header
                    sector_header = Paragraph(f"<b>{sector_name} SECTOR</b>", styles['Heading2'])
                    story.append(sector_header)
                    story.append(Spacer(1, 0.2*inch))
                    
                    # Create stock table
                    stock_headers = ['Symbol', 'Trend Rating', 'Daily Trend', 'Weekly Trend', 'Monthly Trend', 'Category']
                    stock_data = [stock_headers]
                    
                    # Sort by trend rating (descending)
                    sector_df_sorted = sector_df.sort_values('trend_rating', ascending=False)
                    
                    for _, row in sector_df_sorted.iterrows():
                        rating = row.get('trend_rating', 0)
                        symbol = row.get('symbol', 'N/A')
                        daily = row.get('daily_trend', 'N/A')
                        weekly = row.get('weekly_trend', 'N/A')  
                        monthly = row.get('monthly_trend', 'N/A')
                        category = row.get('trend_category', 'N/A')
                        
                        stock_data.append([
                            str(symbol),
                            f"{rating:.1f}" if isinstance(rating, (int, float)) else str(rating),
                            str(daily),
                            str(weekly),
                            str(monthly),
                            str(category)
                        ])
                    
                    # Create stock table
                    stock_table = Table(stock_data, colWidths=[1.2*inch, 1*inch, 0.8*inch, 0.8*inch, 0.8*inch, 1*inch])
                    stock_table.setStyle(TableStyle([
                        ('BACKGROUND', (0, 0), (-1, 0), HexColor('#2c3e50')),
                        ('TEXTCOLOR', (0, 0), (-1, 0), white),
                        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                        ('FONTSIZE', (0, 0), (-1, 0), 9),
                        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                        ('FONTSIZE', (0, 1), (-1, -1), 8),
                        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
                        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [white, HexColor('#f8f9fa')]),
                        ('GRID', (0, 0), (-1, -1), 0.5, HexColor('#dee2e6')),
                        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                    ]))
                    
                    # Color code by trend rating
                    for i, row in enumerate(sector_df_sorted.itertuples(), start=1):
                        rating = getattr(row, 'trend_rating', 0)
                        if rating >= 6:
                            stock_table.setStyle(TableStyle([('BACKGROUND', (5, i), (5, i), HexColor('#d4edda'))]))  # Green for very bullish
                        elif rating >= 3:
                            stock_table.setStyle(TableStyle([('BACKGROUND', (5, i), (5, i), HexColor('#fff3cd'))]))  # Yellow for bullish
                        else:
                            stock_table.setStyle(TableStyle([('BACKGROUND', (5, i), (5, i), HexColor('#f8d7da'))]))  # Red for bearish
                    
                    story.append(stock_table)
                    story.append(Spacer(1, 0.3*inch))
        
        # Key Insights
        story.append(PageBreak())
        story.append(Paragraph("KEY INSIGHTS & RECOMMENDATIONS", styles['CustomHeading']))
        
        insights_text = f"""
        <b>Market Analysis for {date_formatted}:</b><br/><br/>
        
        <b>1. Top Performing Sector:</b> {sector_results[0]['sector']} ({sector_results[0]['bullish_percent']:.1f}% bullish)<br/>
        This sector shows strong institutional interest with {sector_results[0]['bullish_count']} out of {sector_results[0]['total_stocks']} stocks in bullish trend.<br/><br/>
        
        <b>2. Weakest Performing Sector:</b> {sector_results[-1]['sector']} ({sector_results[-1]['bullish_percent']:.1f}% bullish)<br/>
        Only {sector_results[-1]['bullish_count']} out of {sector_results[-1]['total_stocks']} stocks show bullish momentum. Consider caution or contrarian opportunities.<br/><br/>
        
        <b>3. Overall Market Sentiment:</b> {sentiment}<br/>
        With {overall_bullish_pct:.1f}% of stocks across major sectors showing bullish trends, the market sentiment is {sentiment.lower()}.<br/><br/>
        
        <b>Trading Recommendations:</b><br/>
        • <b>Strong Sectors (>60% bullish):</b> Consider momentum strategies and position building<br/>
        • <b>Neutral Sectors (40-60% bullish):</b> Stock-specific analysis recommended<br/>
        • <b>Weak Sectors (<40% bullish):</b> Defensive approach or contrarian opportunities<br/><br/>
        
        <b>Risk Management:</b><br/>
        Diversify across sector strength levels and monitor for rotation signals. Strong sectors may continue momentum, while weak sectors could present value opportunities if fundamentals are sound.<br/><br/>
        
        <b>DISCLAIMER:</b> This analysis is based on technical indicators and historical data. Past performance does not guarantee future results. Always conduct thorough research and consider professional financial advice before making investment decisions.
        """
        
        insights_para = Paragraph(insights_text, styles['Normal'])
        story.append(insights_para)
        
        # Build PDF
        doc.build(story)
        
        return True, output_path
        
    except Exception as e:
        return False, f"Failed to generate PDF report: {str(e)}"

# Update the main function to use the simplified generator
def generate_sectoral_pdf_report(analysis_date: str, output_path: Optional[str] = None) -> Tuple[bool, str]:
    """Main function to generate sectoral PDF report."""
    return generate_simple_sectoral_pdf_report(analysis_date, output_path)

if __name__ == "__main__":
    # Test the simplified version
    success, result = generate_simple_sectoral_pdf_report("2025-11-14")
    if success:
        print(f"✅ Simplified PDF generated: {result}")
    else:
        print(f"❌ Error: {result}")