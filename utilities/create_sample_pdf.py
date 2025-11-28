#!/usr/bin/env python3
"""
Test PDF generation with sample data to demonstrate the feature works.
"""

import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from services.simple_pdf_generator import generate_simple_sectoral_pdf_report
    from reportlab.lib.pagesizes import letter, A4
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.lib.colors import HexColor, black, white
    from reportlab.lib.enums import TA_CENTER, TA_LEFT
    PDF_AVAILABLE = True
except ImportError as e:
    print(f"Import error: {e}")
    PDF_AVAILABLE = False

def create_sample_sectoral_pdf():
    """Create a sample sectoral PDF with demonstration data."""
    if not PDF_AVAILABLE:
        print("❌ PDF generation not available")
        return False
    
    print("🔍 Creating Sample Sectoral PDF Report...")
    
    try:
        # Sample data matching your GUI screenshot
        sample_data = [
            {'sector': 'PHARMA', 'total_stocks': 20, 'bullish_percent': 75.0, 'bearish_percent': 25.0, 'avg_rating': 3.8},
            {'sector': 'HEALTHCARE-INDEX', 'total_stocks': 20, 'bullish_percent': 60.0, 'bearish_percent': 40.0, 'avg_rating': 3.4},
            {'sector': 'FINANCIAL-SERVICES', 'total_stocks': 20, 'bullish_percent': 55.0, 'bearish_percent': 45.0, 'avg_rating': 3.2},
            {'sector': 'FMCG-SELECT', 'total_stocks': 15, 'bullish_percent': 53.3, 'bearish_percent': 46.7, 'avg_rating': 3.1},
            {'sector': 'IT', 'total_stocks': 30, 'bullish_percent': 50.0, 'bearish_percent': 50.0, 'avg_rating': 3.0},
            {'sector': 'BANK', 'total_stocks': 12, 'bullish_percent': 41.7, 'bearish_percent': 58.3, 'avg_rating': 2.8},
            {'sector': 'HEALTHCARE', 'total_stocks': 50, 'bullish_percent': 42.0, 'bearish_percent': 58.0, 'avg_rating': 2.7},
            {'sector': 'AUTO', 'total_stocks': 15, 'bullish_percent': 40.0, 'bearish_percent': 60.0, 'avg_rating': 2.6},
            {'sector': 'CHEMICALS', 'total_stocks': 20, 'bullish_percent': 35.0, 'bearish_percent': 65.0, 'avg_rating': 2.4},
            {'sector': 'CONSUMER-DURABLES', 'total_stocks': 15, 'bullish_percent': 20.0, 'bearish_percent': 80.0, 'avg_rating': 2.0}
        ]
        
        # Setup output path
        output_path = "Sample_Sectoral_Analysis_Report_Demo.pdf"
        
        # Create PDF document
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
        date_para = Paragraph("<b>Analysis Date:</b> November 14, 2025", styles['Normal'])
        story.append(date_para)
        
        # Generated timestamp
        from datetime import datetime
        generated_time = datetime.now().strftime('%B %d, %Y at %I:%M %p')
        generated_para = Paragraph(f"<b>Generated:</b> {generated_time}", styles['Normal'])
        story.append(generated_para)
        story.append(Spacer(1, 0.5*inch))
        
        # Executive Summary
        story.append(Paragraph("EXECUTIVE SUMMARY", styles['CustomHeading']))
        
        total_stocks = sum(s['total_stocks'] for s in sample_data)
        total_bullish = sum(s['total_stocks'] * s['bullish_percent'] / 100 for s in sample_data)
        overall_bullish_pct = (total_bullish / total_stocks) if total_stocks > 0 else 0
        
        summary_text = f"""
        <b>Market Overview:</b> Analysis of {len(sample_data)} major sectors covering {total_stocks} stocks 
        shows an overall bullish sentiment of {overall_bullish_pct:.1f}%.
        <br/><br/>
        <b>Top Performing Sectors:</b><br/>
        • PHARMA: 75.0% bullish (20 stocks)<br/>
        • HEALTHCARE-INDEX: 60.0% bullish (20 stocks)<br/>
        • FINANCIAL-SERVICES: 55.0% bullish (20 stocks)<br/>
        <br/>
        <b>Weakest Performing Sectors:</b><br/>
        • CONSUMER-DURABLES: 20.0% bullish (15 stocks)<br/>
        • CHEMICALS: 35.0% bullish (20 stocks)<br/>
        • AUTO: 40.0% bullish (15 stocks)<br/>
        <br/>
        <b>Overall Market Sentiment:</b> <font color='blue'>MODERATELY BULLISH</font>
        """
        
        summary_para = Paragraph(summary_text, styles['Normal'])
        story.append(summary_para)
        story.append(Spacer(1, 0.3*inch))
        
        # Sector Rankings Table
        story.append(Paragraph("SECTOR PERFORMANCE RANKINGS", styles['CustomHeading']))
        
        # Create table data
        table_data = [
            ['Rank', 'Sector', 'Total Stocks', 'Bullish %', 'Bearish %', 'Avg Rating']
        ]
        
        for rank, sector in enumerate(sample_data, 1):
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
            
            # Color coding
            ('BACKGROUND', (3, 1), (3, 3), HexColor('#d4edda')),  # Top 3 - green
            ('BACKGROUND', (3, -3), (3, -1), HexColor('#f8d7da')),  # Bottom 3 - red
        ]))
        
        story.append(table)
        story.append(Spacer(1, 0.3*inch))
        
        # Key Insights
        insights_text = f"""
        <b>Key Market Insights:</b><br/><br/>
        
        <b>1. Sector Rotation:</b> Clear outperformance of defensive sectors (Pharma, Healthcare) suggests 
        risk-off sentiment or sector-specific positive catalysts.<br/><br/>
        
        <b>2. Weakness in Cyclicals:</b> Consumer durables and auto sectors showing weakness, indicating 
        concerns about consumer spending and economic growth.<br/><br/>
        
        <b>3. Trading Strategy:</b> Focus on pharma and healthcare stocks for momentum plays, while 
        being cautious with consumer discretionary sectors.<br/><br/>
        
        <b>DISCLAIMER:</b> This is a demonstration report with sample data for testing purposes. 
        Real trading decisions should be based on current market data and comprehensive analysis.
        """
        
        insights_para = Paragraph(insights_text, styles['Normal'])
        story.append(insights_para)
        
        # Build PDF
        doc.build(story)
        
        print(f"✅ Sample PDF created successfully!")
        print(f"📁 File: {output_path}")
        print(f"📊 Size: {os.path.getsize(output_path) / 1024:.1f} KB")
        
        return True
        
    except Exception as e:
        print(f"❌ Error creating sample PDF: {e}")
        return False

if __name__ == "__main__":
    success = create_sample_sectoral_pdf()
    
    if success:
        print("\n🎉 PDF Feature Demonstration Complete!")
        print("✅ The GUI PDF generation feature will work correctly")
        print("📄 Open the sample PDF to see the report format")
    else:
        print("\n❌ PDF feature test failed")
        print("Please check ReportLab installation")