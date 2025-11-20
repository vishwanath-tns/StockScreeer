"""
PDF Report Generator for Vedic Astrology Trading Reports

This module generates PDF versions of all trading reports for professional presentation.
"""

import os
import sys
import json
import datetime
from pathlib import Path
import pandas as pd

# For PDF generation - install if not available
try:
    from reportlab.lib.pagesizes import letter, A4
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.lib.colors import black, blue, red, green, orange, grey
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
    REPORTLAB_AVAILABLE = True
except ImportError:
    print("ReportLab not available. Install with: pip install reportlab")
    REPORTLAB_AVAILABLE = False


class VedicTradingPDFGenerator:
    """Generate professional PDF reports from Vedic astrology trading data"""
    
    def __init__(self, reports_dir=None):
        if reports_dir is None:
            # Default to reports directory
            current_dir = Path(__file__).parent
            self.reports_dir = current_dir.parent / 'reports'
        else:
            self.reports_dir = Path(reports_dir)
        
        # Ensure reports directory exists
        self.reports_dir.mkdir(exist_ok=True)
        
        # PDF output directory
        self.pdf_dir = self.reports_dir / 'pdf_reports'
        self.pdf_dir.mkdir(exist_ok=True)
        
        if REPORTLAB_AVAILABLE:
            # Initialize PDF styles
            self.styles = getSampleStyleSheet()
            self.setup_custom_styles()
    
    def setup_custom_styles(self):
        """Setup custom PDF styles"""
        # Title style
        self.title_style = ParagraphStyle(
            'CustomTitle',
            parent=self.styles['Heading1'],
            fontSize=16,
            spaceAfter=20,
            alignment=TA_CENTER,
            textColor=blue
        )
        
        # Header style
        self.header_style = ParagraphStyle(
            'CustomHeader',
            parent=self.styles['Heading2'],
            fontSize=14,
            spaceAfter=12,
            textColor=black
        )
        
        # Subheader style
        self.subheader_style = ParagraphStyle(
            'CustomSubHeader',
            parent=self.styles['Heading3'],
            fontSize=12,
            spaceAfter=8,
            textColor=blue
        )
        
        # Alert style (red text)
        self.alert_style = ParagraphStyle(
            'AlertStyle',
            parent=self.styles['Normal'],
            fontSize=10,
            textColor=red,
            spaceAfter=6
        )
        
        # Success style (green text)
        self.success_style = ParagraphStyle(
            'SuccessStyle',
            parent=self.styles['Normal'],
            fontSize=10,
            textColor=green,
            spaceAfter=6
        )
        
        # Warning style (orange text)
        self.warning_style = ParagraphStyle(
            'WarningStyle',
            parent=self.styles['Normal'],
            fontSize=10,
            textColor=orange,
            spaceAfter=6
        )
    
    def generate_daily_strategy_pdf(self):
        """Generate PDF for daily trading strategy"""
        if not REPORTLAB_AVAILABLE:
            print("ReportLab not available for PDF generation")
            return None
        
        # Find today's strategy file
        today_str = datetime.date.today().strftime('%Y%m%d')
        json_file = self.reports_dir / f"daily_strategy_{today_str}.json"
        
        if not json_file.exists():
            print(f"Daily strategy file not found: {json_file}")
            return None
        
        # Load data
        with open(json_file, 'r') as f:
            data = json.load(f)
        
        # Create PDF
        pdf_file = self.pdf_dir / f"Daily_Trading_Strategy_{today_str}.pdf"
        doc = SimpleDocTemplate(str(pdf_file), pagesize=letter,
                              rightMargin=72, leftMargin=72,
                              topMargin=72, bottomMargin=18)
        
        # Build PDF content
        story = []
        
        # Title
        title = f"Daily Trading Strategy - {data.get('date', 'Unknown')}"
        story.append(Paragraph(title, self.title_style))
        story.append(Spacer(1, 20))
        
        # Moon Position Section
        story.append(Paragraph("Moon Position Analysis", self.header_style))
        moon_pos = data.get('moon_position', {})
        
        moon_data = [
            ['Moon Sign', moon_pos.get('sign', 'Unknown')],
            ['Element', moon_pos.get('element', 'Unknown')],
            ['Quality', moon_pos.get('quality', 'Unknown')],
            ['Degree', f"{moon_pos.get('degree', 'Unknown')}°"],
            ['Analysis Date', data.get('date', 'Unknown')]
        ]
        
        moon_table = Table(moon_data, colWidths=[2*inch, 3*inch])
        moon_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), black),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), 'white'),
            ('GRID', (0, 0), (-1, -1), 1, black)
        ]))
        
        story.append(moon_table)
        story.append(Spacer(1, 20))
        
        # How Moon Sign is Determined
        story.append(Paragraph("How Moon Sign is Determined", self.subheader_style))
        moon_explanation = f"""
        The current moon sign ({moon_pos.get('sign', 'Unknown')}) is calculated based on the Moon's position in the zodiac 
        at the time of analysis ({data.get('date', 'Unknown')}). 
        
        The Moon moves approximately 13 degrees per day through the zodiac, staying in each sign for about 2.5 days. 
        The Moon's current position determines:
        
        • Market volatility expectations (Element: {moon_pos.get('element', 'Unknown')})
        • Emotional market tendencies (Quality: {moon_pos.get('quality', 'Unknown')})
        • Sector preferences and trading approach
        • Risk levels and position sizing recommendations
        
        Today's Moon is at {moon_pos.get('degree', 'Unknown')}° in {moon_pos.get('sign', 'Unknown')}, 
        indicating {moon_pos.get('element', 'Unknown')} element dominance.
        """
        story.append(Paragraph(moon_explanation, self.styles['Normal']))
        story.append(Spacer(1, 15))
        
        # Market Outlook
        story.append(Paragraph("Market Outlook", self.header_style))
        market_outlook = data.get('market_outlook', {})
        
        outlook_text = f"""
        Overall Outlook: {market_outlook.get('overall_outlook', 'Unknown')}
        
        Volatility Expectation: {market_outlook.get('volatility_expectation', 'Unknown')}
        
        Price Expectation: {market_outlook.get('price_expectation', 'Unknown')}
        
        Recommended Approach: {market_outlook.get('recommended_approach', 'Unknown')}
        """
        story.append(Paragraph(outlook_text, self.styles['Normal']))
        story.append(Spacer(1, 15))
        
        # Key Alerts
        story.append(Paragraph("Key Alerts & Warnings", self.header_style))
        alerts = data.get('alerts_and_warnings', [])
        
        for i, alert in enumerate(alerts[:10], 1):
            alert_text = f"{i}. {alert}"
            if 'CAUTION' in alert or 'RISK' in alert:
                story.append(Paragraph(alert_text, self.alert_style))
            elif 'GOOD' in alert or 'FAVORABLE' in alert:
                story.append(Paragraph(alert_text, self.success_style))
            else:
                story.append(Paragraph(alert_text, self.warning_style))
        
        story.append(Spacer(1, 15))
        
        # Risk Management
        story.append(Paragraph("Risk Management Guidelines", self.header_style))
        risk_mgmt = data.get('risk_management', {})
        
        risk_data = [
            ['Risk Level', risk_mgmt.get('risk_level', 'Unknown')],
            ['Max Position Size', risk_mgmt.get('max_position_size', 'Unknown')],
            ['Stop Loss', risk_mgmt.get('stop_loss_recommendation', 'Unknown')],
            ['Profit Target', risk_mgmt.get('profit_target', 'Unknown')]
        ]
        
        risk_table = Table(risk_data, colWidths=[2*inch, 3*inch])
        risk_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), black),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), 'white'),
            ('GRID', (0, 0), (-1, -1), 1, black)
        ]))
        
        story.append(risk_table)
        story.append(Spacer(1, 20))
        
        # Stock Recommendations
        story.append(Paragraph("Stock Recommendations", self.header_style))
        recommendations = data.get('stock_recommendations', {})
        
        # Top Picks
        story.append(Paragraph("High Conviction Picks:", self.subheader_style))
        top_picks = recommendations.get('top_picks', [])
        for stock in top_picks[:8]:
            story.append(Paragraph(f"• {stock}", self.success_style))
        
        story.append(Spacer(1, 10))
        
        # Accumulation
        story.append(Paragraph("Accumulation Candidates:", self.subheader_style))
        accumulation = recommendations.get('accumulation_candidates', [])
        for stock in accumulation[:8]:
            story.append(Paragraph(f"• {stock}", self.styles['Normal']))
        
        story.append(Spacer(1, 10))
        
        # Momentum
        story.append(Paragraph("Momentum Plays:", self.subheader_style))
        momentum = recommendations.get('momentum_plays', [])
        for stock in momentum[:8]:
            story.append(Paragraph(f"• {stock}", self.warning_style))
        
        story.append(PageBreak())
        
        # Sector Strategy
        story.append(Paragraph("Sector Strategy", self.header_style))
        sector_strategy = data.get('sector_strategy', {})
        
        sector_text = f"""
        Primary Sectors: {', '.join(sector_strategy.get('primary_sectors', []))}
        
        Element Focus: {sector_strategy.get('element_focus', 'Unknown')}
        
        Rotation Strategy: {sector_strategy.get('rotation_strategy', 'Unknown')}
        
        Sector Performance Expectations:
        """
        story.append(Paragraph(sector_text, self.styles['Normal']))
        
        # Sector allocation table if available
        allocation = sector_strategy.get('sector_allocation', {})
        if allocation:
            alloc_data = [['Sector', 'Allocation']]
            for sector, percent in allocation.items():
                alloc_data.append([sector, percent])
            
            alloc_table = Table(alloc_data, colWidths=[3*inch, 2*inch])
            alloc_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), black),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 12),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), 'white'),
                ('GRID', (0, 0), (-1, -1), 1, black)
            ]))
            
            story.append(alloc_table)
        
        story.append(Spacer(1, 20))
        
        # Trading Tactics
        story.append(Paragraph("Trading Tactics", self.header_style))
        tactics = data.get('trading_tactics', {})
        
        tactics_text = f"""
        Primary Strategy: {tactics.get('primary_strategy', 'Unknown')}
        
        Entry Method: {tactics.get('entry_method', 'Unknown')}
        
        Exit Strategy: {tactics.get('exit_strategy', 'Unknown')}
        
        Ideal Holding Period: {tactics.get('ideal_holding_period', 'Unknown')}
        
        Special Considerations: {tactics.get('special_considerations', 'None specified')}
        """
        story.append(Paragraph(tactics_text, self.styles['Normal']))
        
        # Footer
        story.append(Spacer(1, 30))
        footer_text = f"""
        This report was generated on {datetime.datetime.now().strftime('%Y-%m-%d at %H:%M:%S')} 
        based on Vedic astrological analysis of Moon positions and market correlations.
        
        Disclaimer: This analysis is for educational purposes only and should not be considered 
        as financial advice. Please consult with qualified financial advisors before making 
        investment decisions.
        """
        story.append(Paragraph(footer_text, self.styles['Normal']))
        
        # Build PDF
        doc.build(story)
        print(f"[PDF] Daily strategy PDF generated: {pdf_file}")
        return pdf_file
    
    def generate_weekly_outlook_pdf(self):
        """Generate PDF for weekly market outlook"""
        if not REPORTLAB_AVAILABLE:
            print("ReportLab not available for PDF generation")
            return None
        
        # Find most recent weekly outlook file
        weekly_files = list(self.reports_dir.glob('Weekly_Market_Outlook_*.txt'))
        if not weekly_files:
            print("No weekly outlook file found")
            return None
        
        latest_weekly = max(weekly_files, key=os.path.getctime)
        
        # Read the text file
        with open(latest_weekly, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Create PDF
        filename = latest_weekly.stem + '.pdf'
        pdf_file = self.pdf_dir / filename
        
        doc = SimpleDocTemplate(str(pdf_file), pagesize=letter,
                              rightMargin=72, leftMargin=72,
                              topMargin=72, bottomMargin=18)
        
        # Build PDF content
        story = []
        
        # Title
        story.append(Paragraph("Weekly Market Outlook", self.title_style))
        story.append(Spacer(1, 20))
        
        # Convert text content to PDF paragraphs
        lines = content.split('\n')
        current_paragraph = []
        
        for line in lines:
            line = line.strip()
            
            if not line:
                if current_paragraph:
                    paragraph_text = ' '.join(current_paragraph)
                    story.append(Paragraph(paragraph_text, self.styles['Normal']))
                    story.append(Spacer(1, 6))
                    current_paragraph = []
            
            elif line.startswith('=') or line.startswith('-'):
                # Skip separator lines
                continue
                
            elif any(header in line for header in ['SUMMARY', 'OUTLOOK', 'SECTORS', 'RISK', 'TRADING']):
                # This is a header
                if current_paragraph:
                    paragraph_text = ' '.join(current_paragraph)
                    story.append(Paragraph(paragraph_text, self.styles['Normal']))
                    current_paragraph = []
                
                story.append(Spacer(1, 12))
                story.append(Paragraph(line, self.header_style))
                
            else:
                current_paragraph.append(line)
        
        # Add remaining paragraph
        if current_paragraph:
            paragraph_text = ' '.join(current_paragraph)
            story.append(Paragraph(paragraph_text, self.styles['Normal']))
        
        # Footer
        story.append(Spacer(1, 30))
        footer_text = f"""
        Generated on {datetime.datetime.now().strftime('%Y-%m-%d at %H:%M:%S')} 
        Source: {latest_weekly.name}
        """
        story.append(Paragraph(footer_text, self.styles['Normal']))
        
        # Build PDF
        doc.build(story)
        print(f"[PDF] Weekly outlook PDF generated: {pdf_file}")
        return pdf_file
    
    def generate_market_forecast_pdf(self):
        """Generate PDF for market forecast"""
        if not REPORTLAB_AVAILABLE:
            print("ReportLab not available for PDF generation")
            return None
        
        # Find today's forecast file
        today_str = datetime.date.today().strftime('%Y%m%d')
        json_file = self.reports_dir / f"market_forecast_{today_str}.json"
        
        if not json_file.exists():
            print(f"Market forecast file not found: {json_file}")
            return None
        
        # Load data
        with open(json_file, 'r') as f:
            data = json.load(f)
        
        # Create PDF
        pdf_file = self.pdf_dir / f"Market_Forecast_{today_str}.pdf"
        doc = SimpleDocTemplate(str(pdf_file), pagesize=letter,
                              rightMargin=72, leftMargin=72,
                              topMargin=72, bottomMargin=18)
        
        # Build PDF content
        story = []
        
        # Title
        title = f"4-Week Market Forecast - {data.get('forecast_date', 'Unknown')}"
        story.append(Paragraph(title, self.title_style))
        story.append(Spacer(1, 20))
        
        # Overall Outlook
        story.append(Paragraph("Overall Market Outlook", self.header_style))
        overall = data.get('overall_outlook', {})
        
        outlook_text = f"""
        Market Outlook: {overall.get('market_outlook', 'Unknown')}
        Average Volatility: {overall.get('overall_volatility', 'Unknown')}x
        Risk Percentage: {overall.get('risk_percentage', 'Unknown')}%
        Recommendation: {overall.get('recommendation', 'Unknown')}
        """
        story.append(Paragraph(outlook_text, self.styles['Normal']))
        story.append(Spacer(1, 15))
        
        # Best and challenging weeks
        story.append(Paragraph("Trading Opportunities", self.subheader_style))
        
        story.append(Paragraph("Best Weeks for Trading:", self.success_style))
        for week in overall.get('best_weeks', []):
            story.append(Paragraph(f"• {week}", self.styles['Normal']))
        
        story.append(Spacer(1, 10))
        
        story.append(Paragraph("Challenging Weeks (Caution Required):", self.alert_style))
        for week in overall.get('challenging_weeks', []):
            story.append(Paragraph(f"• {week}", self.styles['Normal']))
        
        story.append(PageBreak())
        
        # Weekly breakdown
        story.append(Paragraph("Weekly Breakdown", self.header_style))
        
        weekly_forecasts = data.get('weekly_forecasts', [])
        for i, week in enumerate(weekly_forecasts, 1):
            story.append(Paragraph(f"Week {i}: {week.get('week_period', 'Unknown')}", self.subheader_style))
            
            week_text = f"""
            Dominant Element: {week.get('dominant_element', 'Unknown')}
            Volatility: {week.get('volatility_analysis', {}).get('classification', 'Unknown')} 
            ({week.get('volatility_analysis', {}).get('average', 'Unknown')}x)
            Primary Strategy: {week.get('trading_strategy', {}).get('primary_strategy', 'Unknown')}
            Confidence Level: {week.get('confidence_level', 'Unknown')}
            """
            story.append(Paragraph(week_text, self.styles['Normal']))
            
            # Key alerts for this week
            if week.get('key_alerts'):
                story.append(Paragraph("Key Alerts:", self.warning_style))
                for alert in week.get('key_alerts', []):
                    story.append(Paragraph(f"• {alert}", self.styles['Normal']))
            
            story.append(Spacer(1, 15))
        
        # Trading calendar summary
        story.append(PageBreak())
        story.append(Paragraph("Trading Calendar Summary", self.header_style))
        
        # Load trading calendar if available
        calendar_file = self.reports_dir / f"trading_calendar_{today_str}.csv"
        if calendar_file.exists():
            try:
                df = pd.read_csv(calendar_file)
                
                # Create calendar table for next 14 days
                calendar_data = [['Date', 'Day', 'Moon Sign', 'Element', 'Risk Level', 'Action']]
                
                for _, row in df.head(14).iterrows():
                    calendar_data.append([
                        pd.to_datetime(row['Date']).strftime('%m/%d'),
                        row['Day'][:3],
                        row['Moon_Sign'],
                        row['Element'],
                        row['Risk_Level'],
                        row['Action']
                    ])
                
                calendar_table = Table(calendar_data, colWidths=[0.8*inch, 0.6*inch, 1.2*inch, 
                                                               0.8*inch, 1*inch, 1.5*inch])
                calendar_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), grey),
                    ('TEXTCOLOR', (0, 0), (-1, 0), black),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, 0), 10),
                    ('FONTSIZE', (0, 1), (-1, -1), 8),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                    ('BACKGROUND', (0, 1), (-1, -1), 'white'),
                    ('GRID', (0, 0), (-1, -1), 1, black)
                ]))
                
                story.append(calendar_table)
                
            except Exception as e:
                story.append(Paragraph(f"Error loading calendar data: {e}", self.alert_style))
        
        # Footer
        story.append(Spacer(1, 30))
        footer_text = f"""
        This forecast was generated on {datetime.datetime.now().strftime('%Y-%m-%d at %H:%M:%S')} 
        using Vedic astrological principles and historical market correlation analysis.
        
        Disclaimer: This forecast is for educational purposes only. Past performance does not 
        guarantee future results. Please conduct your own research before making investment decisions.
        """
        story.append(Paragraph(footer_text, self.styles['Normal']))
        
        # Build PDF
        doc.build(story)
        print(f"[PDF] Market forecast PDF generated: {pdf_file}")
        return pdf_file
    
    def generate_all_pdfs(self):
        """Generate all available PDFs"""
        generated_files = []
        
        print("[PDF] Generating all PDF reports...")
        
        # Daily strategy PDF
        try:
            daily_pdf = self.generate_daily_strategy_pdf()
            if daily_pdf:
                generated_files.append(daily_pdf)
        except Exception as e:
            print(f"[PDF ERROR] Daily strategy: {e}")
        
        # Weekly outlook PDF
        try:
            weekly_pdf = self.generate_weekly_outlook_pdf()
            if weekly_pdf:
                generated_files.append(weekly_pdf)
        except Exception as e:
            print(f"[PDF ERROR] Weekly outlook: {e}")
        
        # Market forecast PDF
        try:
            forecast_pdf = self.generate_market_forecast_pdf()
            if forecast_pdf:
                generated_files.append(forecast_pdf)
        except Exception as e:
            print(f"[PDF ERROR] Market forecast: {e}")
        
        print(f"[PDF] Generated {len(generated_files)} PDF reports")
        return generated_files


def main():
    """Test PDF generation"""
    if not REPORTLAB_AVAILABLE:
        print("ReportLab not available. Install with: pip install reportlab")
        return
    
    generator = VedicTradingPDFGenerator()
    generated_files = generator.generate_all_pdfs()
    
    print(f"\n[PDF] Generated files:")
    for file in generated_files:
        print(f"  - {file}")


if __name__ == "__main__":
    main()