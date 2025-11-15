#!/usr/bin/env python3
"""
PDF Report Generator for Sectoral Analysis
Generates comprehensive PDF reports of sectoral trend analysis.
"""

import os
import sys
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import pandas as pd

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from reportlab.lib.pagesizes import letter, A4
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.lib.colors import HexColor, black, white, green, red, blue, gray
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
    from reportlab.graphics.shapes import Drawing
    from reportlab.graphics.charts.barcharts import VerticalBarChart
    from reportlab.graphics.charts.piecharts import Pie
    from reportlab.lib import colors
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False
    print("⚠️ ReportLab not installed. Install with: pip install reportlab")

from services.market_breadth_service import get_sectoral_breadth, get_engine, get_sectoral_analysis_dates

class SectoralReportGenerator:
    """Generate comprehensive PDF reports for sectoral analysis."""
    
    def __init__(self):
        self.doc = None
        self.story = []
        self.styles = None
        self.engine = None
        
        if REPORTLAB_AVAILABLE:
            self.setup_styles()
    
    def setup_styles(self):
        """Setup custom styles for the PDF report."""
        self.styles = getSampleStyleSheet()
        
        # Custom title style
        self.styles.add(ParagraphStyle(
            name='CustomTitle',
            parent=self.styles['Title'],
            fontSize=24,
            spaceAfter=20,
            textColor=HexColor('#1f4e79'),
            alignment=TA_CENTER
        ))
        
        # Custom heading style
        self.styles.add(ParagraphStyle(
            name='CustomHeading',
            parent=self.styles['Heading1'],
            fontSize=16,
            spaceBefore=15,
            spaceAfter=10,
            textColor=HexColor('#2e75b6'),
            alignment=TA_LEFT
        ))
        
        # Custom subheading style
        self.styles.add(ParagraphStyle(
            name='CustomSubHeading',
            parent=self.styles['Heading2'],
            fontSize=14,
            spaceBefore=12,
            spaceAfter=8,
            textColor=HexColor('#548dd4'),
            alignment=TA_LEFT
        ))
        
        # Summary style
        self.styles.add(ParagraphStyle(
            name='Summary',
            parent=self.styles['Normal'],
            fontSize=11,
            spaceBefore=8,
            spaceAfter=8,
            textColor=HexColor('#444444')
        ))
        
        # Footer style
        self.styles.add(ParagraphStyle(
            name='Footer',
            parent=self.styles['Normal'],
            fontSize=8,
            textColor=HexColor('#888888'),
            alignment=TA_CENTER
        ))
    
    def generate_sectoral_report(self, analysis_date: str, output_path: Optional[str] = None) -> str:
        """Generate comprehensive sectoral analysis PDF report."""
        if not REPORTLAB_AVAILABLE:
            raise ImportError("ReportLab is required for PDF generation. Install with: pip install reportlab")
        
        # Setup output path
        if not output_path:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            date_str = analysis_date.replace('-', '')
            output_path = f"Sectoral_Analysis_Report_{date_str}_{timestamp}.pdf"
        
        # Initialize document
        self.doc = SimpleDocTemplate(
            output_path,
            pagesize=A4,
            rightMargin=72,
            leftMargin=72,
            topMargin=72,
            bottomMargin=72
        )
        
        self.story = []
        
        try:
            # Get database connection
            self.engine = get_engine()
            
            # Generate report sections
            self._add_title_page(analysis_date)
            self._add_executive_summary(analysis_date)
            self._add_sector_rankings(analysis_date)
            self._add_detailed_analysis(analysis_date)
            self._add_individual_sector_details(analysis_date)
            self._add_market_insights(analysis_date)
            self._add_footer_disclaimer()
            
            # Build PDF
            self.doc.build(self.story)
            
            return output_path
            
        except Exception as e:
            raise Exception(f"Failed to generate PDF report: {str(e)}")
    
    def _add_title_page(self, analysis_date: str):
        """Add title page to the report."""
        # Main title
        title = Paragraph("SECTORAL TREND ANALYSIS REPORT", self.styles['CustomTitle'])
        self.story.append(title)
        self.story.append(Spacer(1, 0.5*inch))
        
        # Analysis date
        date_formatted = datetime.strptime(analysis_date, '%Y-%m-%d').strftime('%B %d, %Y')
        date_para = Paragraph(f"<b>Analysis Date:</b> {date_formatted}", self.styles['Summary'])
        self.story.append(date_para)
        self.story.append(Spacer(1, 0.3*inch))
        
        # Generated timestamp
        generated_time = datetime.now().strftime('%B %d, %Y at %I:%M %p')
        generated_para = Paragraph(f"<b>Generated:</b> {generated_time}", self.styles['Summary'])
        self.story.append(generated_para)
        self.story.append(Spacer(1, 0.5*inch))
        
        # Report description
        description = """
        This comprehensive report provides detailed sectoral trend analysis based on technical indicators 
        and market momentum across major NSE sectoral indices. The analysis includes bullish/bearish 
        percentages, trend classifications, and actionable market insights.
        """
        desc_para = Paragraph(description, self.styles['Summary'])
        self.story.append(desc_para)
        self.story.append(PageBreak())
    
    def _add_executive_summary(self, analysis_date: str):
        """Add executive summary section."""
        self.story.append(Paragraph("EXECUTIVE SUMMARY", self.styles['CustomHeading']))
        
        try:
            # Get all major sectors data
            major_sectors = [
                'NIFTY-PHARMA', 'NIFTY-BANK', 'NIFTY-IT', 'NIFTY-AUTO',
                'NIFTY-FMCG', 'NIFTY-REALTY', 'NIFTY-METAL', 'NIFTY-ENERGY',
                'NIFTY-HEALTHCARE-INDEX', 'NIFTY-CONSUMER-DURABLES'
            ]
            
            sector_results = []
            total_stocks = 0
            total_bullish = 0
            
            for sector in major_sectors:
                try:
                    result = get_sectoral_breadth(sector, analysis_date=analysis_date)
                    if result.get('status') == 'success':
                        summary = result.get('summary', {})
                        sector_results.append({
                            'sector': sector.replace('NIFTY-', ''),
                            'total_stocks': summary.get('total_stocks', 0),
                            'bullish_percent': summary.get('bullish_percent', 0),
                            'bullish_count': summary.get('bullish_count', 0)
                        })
                        total_stocks += summary.get('total_stocks', 0)
                        total_bullish += summary.get('bullish_count', 0)
                except:
                    continue
            
            if sector_results:
                # Sort by bullish percentage
                sector_results.sort(key=lambda x: x['bullish_percent'], reverse=True)
                
                # Overall market sentiment
                overall_bullish_pct = (total_bullish / total_stocks * 100) if total_stocks > 0 else 0
                
                summary_text = f"""
                <b>Market Overview:</b> Analysis of {len(sector_results)} major sectors covering {total_stocks} stocks shows 
                an overall bullish sentiment of {overall_bullish_pct:.1f}%.
                <br/><br/>
                <b>Top Performing Sectors:</b>
                """
                
                for i, sector in enumerate(sector_results[:3]):
                    summary_text += f"<br/>• {sector['sector']}: {sector['bullish_percent']:.1f}% bullish ({sector['total_stocks']} stocks)"
                
                summary_text += f"<br/><br/><b>Weakest Performing Sectors:</b>"
                for i, sector in enumerate(sector_results[-3:]):
                    summary_text += f"<br/>• {sector['sector']}: {sector['bullish_percent']:.1f}% bullish ({sector['total_stocks']} stocks)"
                
                # Market sentiment interpretation
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
                
                summary_para = Paragraph(summary_text, self.styles['Summary'])
                self.story.append(summary_para)
                
        except Exception as e:
            error_para = Paragraph(f"Error generating executive summary: {str(e)}", self.styles['Summary'])
            self.story.append(error_para)
        
        self.story.append(Spacer(1, 0.3*inch))
    
    def _add_sector_rankings(self, analysis_date: str):
        """Add sector rankings table."""
        self.story.append(Paragraph("SECTOR PERFORMANCE RANKINGS", self.styles['CustomHeading']))
        
        try:
            # Get comprehensive sector data
            query = """
            SELECT 
                n.index_name as sector,
                COUNT(*) as total_stocks,
                SUM(CASE WHEN t.trend_rating >= 3 THEN 1 ELSE 0 END) as bullish_count,
                SUM(CASE WHEN t.trend_rating <= 2 THEN 1 ELSE 0 END) as bearish_count,
                ROUND(SUM(CASE WHEN t.trend_rating >= 3 THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 1) as bullish_pct,
                ROUND(AVG(t.trend_rating), 2) as avg_rating,
                SUM(CASE WHEN t.daily_trend = 'Uptrend' THEN 1 ELSE 0 END) as daily_uptrend_count,
                SUM(CASE WHEN t.weekly_trend = 'Uptrend' THEN 1 ELSE 0 END) as weekly_uptrend_count
            FROM trend_analysis t
            JOIN nse_index_constituents n ON t.symbol = n.symbol
            WHERE t.analysis_date = %s
            AND n.index_name IN (
                'NIFTY-PHARMA', 'NIFTY-BANK', 'NIFTY-IT', 'NIFTY-AUTO',
                'NIFTY-FMCG', 'NIFTY-REALTY', 'NIFTY-METAL', 'NIFTY-ENERGY',
                'NIFTY-HEALTHCARE-INDEX', 'NIFTY-CONSUMER-DURABLES',
                'NIFTY-FINANCIAL-SERVICES', 'NIFTY-COMMODITIES'
            )
            GROUP BY n.index_name
            ORDER BY bullish_pct DESC
            """
            
            with self.engine.connect() as conn:
                df = pd.read_sql(query, conn, params=[analysis_date])
                
                if not df.empty:
                    # Prepare table data
                    table_data = [
                        ['Rank', 'Sector', 'Total Stocks', 'Bullish %', 'Bearish %', 'Avg Rating', 'Daily Up', 'Weekly Up']
                    ]
                    
                    for rank, (_, row) in enumerate(df.iterrows(), 1):
                        sector_name = row['sector'].replace('NIFTY-', '')
                        daily_up_pct = (row['daily_uptrend_count'] / row['total_stocks'] * 100) if row['total_stocks'] > 0 else 0
                        weekly_up_pct = (row['weekly_uptrend_count'] / row['total_stocks'] * 100) if row['total_stocks'] > 0 else 0
                        
                        table_data.append([
                            str(rank),
                            sector_name,
                            str(row['total_stocks']),
                            f"{row['bullish_pct']:.1f}%",
                            f"{100-row['bullish_pct']:.1f}%",
                            f"{row['avg_rating']:.2f}",
                            f"{daily_up_pct:.1f}%",
                            f"{weekly_up_pct:.1f}%"
                        ])
                    
                    # Create table
                    table = Table(table_data, colWidths=[0.5*inch, 1.8*inch, 0.8*inch, 0.8*inch, 0.8*inch, 0.8*inch, 0.8*inch, 0.8*inch])
                    
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
                        ('BACKGROUND', (3, 1), (3, 3), HexColor('#d4edda')),  # Top 3 bullish % - green
                        ('BACKGROUND', (3, -3), (3, -1), HexColor('#f8d7da')), # Bottom 3 bullish % - red
                    ]))
                    
                    self.story.append(table)
                    
                else:
                    no_data_para = Paragraph("No sector ranking data available for the selected date.", self.styles['Summary'])
                    self.story.append(no_data_para)
                    
        except Exception as e:
            error_para = Paragraph(f"Error generating sector rankings: {str(e)}", self.styles['Summary'])
            self.story.append(error_para)
        
        self.story.append(Spacer(1, 0.3*inch))
    
    def _add_detailed_analysis(self, analysis_date: str):
        """Add detailed sector-wise analysis."""
        self.story.append(Paragraph("DETAILED SECTOR ANALYSIS", self.styles['CustomHeading']))
        
        # Top 3 and Bottom 3 sectors analysis
        try:
            sectors_info = self._get_top_bottom_sectors(analysis_date)
            
            if sectors_info['top_sectors']:
                self.story.append(Paragraph("Top Performing Sectors", self.styles['CustomSubHeading']))
                
                for i, sector_data in enumerate(sectors_info['top_sectors'][:3], 1):
                    sector_text = f"""
                    <b>{i}. {sector_data['sector'].replace('NIFTY-', '')}</b><br/>
                    • Bullish Percentage: {sector_data['bullish_pct']:.1f}%<br/>
                    • Total Stocks Analyzed: {sector_data['total_stocks']}<br/>
                    • Average Trend Rating: {sector_data['avg_rating']:.2f}/5<br/>
                    • Daily Uptrend: {(sector_data['daily_uptrend_count']/sector_data['total_stocks']*100):.1f}%<br/>
                    • Weekly Uptrend: {(sector_data['weekly_uptrend_count']/sector_data['total_stocks']*100):.1f}%
                    """
                    
                    self.story.append(Paragraph(sector_text, self.styles['Summary']))
                    self.story.append(Spacer(1, 0.1*inch))
                
                self.story.append(Spacer(1, 0.2*inch))
            
            if sectors_info['bottom_sectors']:
                self.story.append(Paragraph("Weakest Performing Sectors", self.styles['CustomSubHeading']))
                
                for i, sector_data in enumerate(sectors_info['bottom_sectors'][:3], 1):
                    sector_text = f"""
                    <b>{i}. {sector_data['sector'].replace('NIFTY-', '')}</b><br/>
                    • Bullish Percentage: {sector_data['bullish_pct']:.1f}%<br/>
                    • Total Stocks Analyzed: {sector_data['total_stocks']}<br/>
                    • Average Trend Rating: {sector_data['avg_rating']:.2f}/5<br/>
                    • Daily Uptrend: {(sector_data['daily_uptrend_count']/sector_data['total_stocks']*100):.1f}%<br/>
                    • Weekly Uptrend: {(sector_data['weekly_uptrend_count']/sector_data['total_stocks']*100):.1f}%
                    """
                    
                    self.story.append(Paragraph(sector_text, self.styles['Summary']))
                    self.story.append(Spacer(1, 0.1*inch))
                    
        except Exception as e:
            error_para = Paragraph(f"Error in detailed analysis: {str(e)}", self.styles['Summary'])
            self.story.append(error_para)
        
        self.story.append(Spacer(1, 0.3*inch))
    
    def _add_individual_sector_details(self, analysis_date: str):
        """Add individual sector stock details."""
        self.story.append(PageBreak())
        self.story.append(Paragraph("INDIVIDUAL SECTOR STOCK DETAILS", self.styles['CustomHeading']))
        
        major_sectors = ['NIFTY-PHARMA', 'NIFTY-BANK', 'NIFTY-IT', 'NIFTY-AUTO']
        
        for sector in major_sectors:
            try:
                self.story.append(Paragraph(f"{sector.replace('NIFTY-', '')} Sector Details", self.styles['CustomSubHeading']))
                
                # Get individual stock data for this sector
                query = """
                SELECT 
                    t.symbol,
                    t.trend_rating,
                    t.daily_trend,
                    t.weekly_trend,
                    t.close_price,
                    CASE 
                        WHEN t.trend_rating >= 4 THEN 'Strong Bullish'
                        WHEN t.trend_rating >= 3 THEN 'Bullish'
                        WHEN t.trend_rating <= 2 THEN 'Bearish'
                        ELSE 'Neutral'
                    END as classification
                FROM trend_analysis t
                JOIN nse_index_constituents n ON t.symbol = n.symbol
                WHERE n.index_name = %s
                AND t.analysis_date = %s
                ORDER BY t.trend_rating DESC, t.symbol
                LIMIT 10
                """
                
                with self.engine.connect() as conn:
                    df = pd.read_sql(query, conn, params=[sector, analysis_date])
                    
                    if not df.empty:
                        # Create stock details table
                        stock_table_data = [
                            ['Symbol', 'Rating', 'Daily Trend', 'Weekly Trend', 'Price', 'Classification']
                        ]
                        
                        for _, row in df.iterrows():
                            stock_table_data.append([
                                row['symbol'],
                                f"{row['trend_rating']:.1f}",
                                row['daily_trend'],
                                row['weekly_trend'],
                                f"₹{row['close_price']:.2f}",
                                row['classification']
                            ])
                        
                        stock_table = Table(stock_table_data, colWidths=[1.2*inch, 0.8*inch, 1.0*inch, 1.0*inch, 1.0*inch, 1.2*inch])
                        
                        stock_table.setStyle(TableStyle([
                            ('BACKGROUND', (0, 0), (-1, 0), HexColor('#548dd4')),
                            ('TEXTCOLOR', (0, 0), (-1, 0), white),
                            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                            ('FONTSIZE', (0, 0), (-1, 0), 9),
                            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
                            ('BACKGROUND', (0, 1), (-1, -1), white),
                            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                            ('FONTSIZE', (0, 1), (-1, -1), 8),
                            ('GRID', (0, 0), (-1, -1), 0.5, black),
                            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                        ]))
                        
                        self.story.append(stock_table)
                        self.story.append(Spacer(1, 0.2*inch))
                        
                    else:
                        no_stocks_para = Paragraph(f"No stock data available for {sector}", self.styles['Summary'])
                        self.story.append(no_stocks_para)
                        self.story.append(Spacer(1, 0.1*inch))
                        
            except Exception as e:
                error_para = Paragraph(f"Error getting {sector} details: {str(e)}", self.styles['Summary'])
                self.story.append(error_para)
    
    def _add_market_insights(self, analysis_date: str):
        """Add market insights and recommendations."""
        self.story.append(PageBreak())
        self.story.append(Paragraph("MARKET INSIGHTS & RECOMMENDATIONS", self.styles['CustomHeading']))
        
        insights_text = f"""
        <b>Key Market Observations for {analysis_date}:</b><br/><br/>
        
        <b>1. Sector Rotation Signals:</b><br/>
        The sectoral analysis reveals clear rotation patterns that can guide investment decisions. 
        Strong sectors with high bullish percentages indicate institutional buying interest.<br/><br/>
        
        <b>2. Risk Management:</b><br/>
        Sectors with low bullish percentages should be approached with caution. Consider reducing 
        exposure to weak sectors and increasing allocation to strong performers.<br/><br/>
        
        <b>3. Technical Momentum:</b><br/>
        Sectors with high daily and weekly uptrend percentages show strong technical momentum. 
        These are prime candidates for momentum-based strategies.<br/><br/>
        
        <b>4. Contrarian Opportunities:</b><br/>
        Extremely weak sectors (below 30% bullish) may present contrarian opportunities if 
        fundamentals remain strong. Monitor for reversal signals.<br/><br/>
        
        <b>Trading Recommendations:</b><br/>
        • <b>Bullish Sectors (>60%):</b> Consider increasing position sizes and momentum plays<br/>
        • <b>Neutral Sectors (40-60%):</b> Stock picking becomes crucial, focus on individual fundamentals<br/>
        • <b>Bearish Sectors (<40%):</b> Defensive approach, consider shorting opportunities or avoid new positions<br/><br/>
        
        <b>Important Disclaimers:</b><br/>
        This analysis is based on technical indicators and historical data. Past performance does not 
        guarantee future results. Always conduct your own research and consider consulting with financial 
        advisors before making investment decisions.
        """
        
        insights_para = Paragraph(insights_text, self.styles['Summary'])
        self.story.append(insights_para)
    
    def _add_footer_disclaimer(self):
        """Add footer disclaimer."""
        self.story.append(Spacer(1, 0.5*inch))
        
        disclaimer_text = """
        <b>DISCLAIMER:</b> This report is generated for informational purposes only and should not be considered as financial advice. 
        The analysis is based on technical indicators and may not reflect fundamental market conditions. 
        Trading and investment decisions should be made based on individual risk tolerance and comprehensive market analysis. 
        Generated by Stock Screener Sectoral Analysis Tool.
        """
        
        disclaimer_para = Paragraph(disclaimer_text, self.styles['Footer'])
        self.story.append(disclaimer_para)
    
    def _get_top_bottom_sectors(self, analysis_date: str) -> Dict:
        """Get top and bottom performing sectors."""
        try:
            query = """
            SELECT 
                n.index_name as sector,
                COUNT(*) as total_stocks,
                SUM(CASE WHEN t.trend_rating >= 3 THEN 1 ELSE 0 END) as bullish_count,
                ROUND(SUM(CASE WHEN t.trend_rating >= 3 THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 1) as bullish_pct,
                ROUND(AVG(t.trend_rating), 2) as avg_rating,
                SUM(CASE WHEN t.daily_trend = 'Uptrend' THEN 1 ELSE 0 END) as daily_uptrend_count,
                SUM(CASE WHEN t.weekly_trend = 'Uptrend' THEN 1 ELSE 0 END) as weekly_uptrend_count
            FROM trend_analysis t
            JOIN nse_index_constituents n ON t.symbol = n.symbol
            WHERE t.analysis_date = %s
            GROUP BY n.index_name
            HAVING COUNT(*) >= 5
            ORDER BY bullish_pct DESC
            """
            
            with self.engine.connect() as conn:
                df = pd.read_sql(query, conn, params=[analysis_date])
                
                if not df.empty:
                    sectors_list = df.to_dict('records')
                    return {
                        'top_sectors': sectors_list[:5],
                        'bottom_sectors': sectors_list[-5:][::-1]  # Reverse to show weakest first
                    }
                else:
                    return {'top_sectors': [], 'bottom_sectors': []}
                    
        except Exception as e:
            print(f"Error getting top/bottom sectors: {e}")
            return {'top_sectors': [], 'bottom_sectors': []}

def generate_sectoral_pdf_report(analysis_date: str, output_path: Optional[str] = None) -> Tuple[bool, str]:
    """
    Generate sectoral analysis PDF report.
    
    Args:
        analysis_date: Date for analysis (YYYY-MM-DD format)
        output_path: Optional custom output path
        
    Returns:
        Tuple of (success, message/path)
    """
    if not REPORTLAB_AVAILABLE:
        return False, "ReportLab library not installed. Please install with: pip install reportlab"
    
    try:
        generator = SectoralReportGenerator()
        output_file = generator.generate_sectoral_report(analysis_date, output_path)
        return True, output_file
    except Exception as e:
        return False, f"Error generating PDF report: {str(e)}"

# Test function
def test_pdf_generation():
    """Test PDF generation with sample data."""
    if not REPORTLAB_AVAILABLE:
        print("❌ ReportLab not installed. Install with: pip install reportlab")
        return False
    
    try:
        print("🔍 Testing PDF generation...")
        success, result = generate_sectoral_pdf_report("2025-11-14")
        
        if success:
            print(f"✅ PDF generated successfully: {result}")
            return True
        else:
            print(f"❌ PDF generation failed: {result}")
            return False
            
    except Exception as e:
        print(f"❌ Test error: {e}")
        return False

if __name__ == "__main__":
    test_pdf_generation()