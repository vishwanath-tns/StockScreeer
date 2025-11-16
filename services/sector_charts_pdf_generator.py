"""
Sector Charts PDF Generator
Combines all individual sector charts into a comprehensive PDF report
"""
import os
import logging
from datetime import datetime, date
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, PageBreak, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.lib.utils import ImageReader
import glob
from .individual_sector_charts import generate_all_sector_charts, list_available_sectors

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def generate_sector_charts_pdf(filename="sector_charts_comprehensive.pdf", days_back=90, regenerate_charts=True):
    """
    Generate a comprehensive PDF with all sector charts
    
    Args:
        filename: Name of the PDF file to create
        days_back: Number of days of data to include in charts
        regenerate_charts: Whether to regenerate charts before creating PDF
        
    Returns:
        Tuple of (success, message)
    """
    
    try:
        logger.info(f"🔄 Generating comprehensive sector charts PDF for last {days_back} days...")
        
        # Ensure charts directory exists
        charts_dir = "charts/sectors"
        os.makedirs(charts_dir, exist_ok=True)
        
        # Regenerate charts if requested
        if regenerate_charts:
            logger.info("📊 Regenerating sector charts...")
            success, message = generate_all_sector_charts(days_back=days_back)
            if not success:
                return False, f"Failed to generate charts: {message}"
            logger.info("✅ Charts regenerated successfully")
        
        # Get list of chart files
        chart_files = glob.glob(os.path.join(charts_dir, "*.png"))
        if not chart_files:
            return False, "No chart files found. Please generate charts first."
        
        # Sort chart files for consistent ordering
        chart_files.sort()
        
        logger.info(f"📋 Found {len(chart_files)} chart files to include in PDF")
        
        # Setup PDF
        output_path = os.path.join("charts", filename)
        doc = SimpleDocTemplate(output_path, pagesize=A4, 
                              rightMargin=inch*0.5, leftMargin=inch*0.5,
                              topMargin=inch*0.75, bottomMargin=inch*0.5)
        
        # Define styles
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            textColor=colors.darkblue,
            spaceAfter=30,
            alignment=1  # Center alignment
        )
        
        subtitle_style = ParagraphStyle(
            'CustomSubtitle',
            parent=styles['Heading2'],
            fontSize=16,
            textColor=colors.darkgreen,
            spaceAfter=20,
            alignment=1
        )
        
        section_style = ParagraphStyle(
            'SectionHeader',
            parent=styles['Heading2'],
            fontSize=14,
            textColor=colors.black,
            spaceAfter=12,
            spaceBefore=20
        )
        
        body_style = ParagraphStyle(
            'CustomBody',
            parent=styles['Normal'],
            fontSize=11,
            spaceAfter=12,
            alignment=0
        )
        
        # Build story
        story = []
        
        # Title page
        story.append(Paragraph("📊 Comprehensive Sector Analysis Report", title_style))
        story.append(Spacer(1, 20))
        
        story.append(Paragraph(f"📅 Analysis Period: {days_back} Days", subtitle_style))
        story.append(Paragraph(f"📈 Generated: {datetime.now().strftime('%B %d, %Y at %I:%M %p')}", subtitle_style))
        story.append(Spacer(1, 30))
        
        # Executive Summary
        story.append(Paragraph("🎯 Executive Summary", section_style))
        
        summary_text = f"""
This comprehensive report presents detailed technical and fundamental analysis for {len(chart_files)} major market sectors 
over the past {days_back} trading days. Each sector chart provides:

<b>Key Analysis Components:</b>
• <b>Bullish vs Bearish Trends:</b> Visual comparison of sector momentum over time
• <b>Technical Uptrend Analysis:</b> Daily and weekly uptrend percentage tracking
• <b>Trend Rating Evolution:</b> Color-coded trend strength indicators
• <b>Performance Metrics:</b> Volatility, range, and key statistics

<b>Report Benefits:</b>
• Sector-by-sector investment decision support
• Trend identification and momentum analysis  
• Performance comparison across market segments
• Historical context for current market positioning

<b>Data Coverage:</b>
• Analysis Period: {(date.today() - date.today().replace(day=1)).days} days
• Market Sectors: {len(chart_files)} major indices
• Technical Indicators: Bullish/Bearish percentages, uptrend analysis, trend ratings
• Visual Format: High-resolution charts with comprehensive metrics
"""
        
        story.append(Paragraph(summary_text, body_style))
        story.append(PageBreak())
        
        # Table of Contents
        story.append(Paragraph("📋 Table of Contents", section_style))
        
        # Get sector names from available sectors
        available_sectors = list_available_sectors()
        sector_lookup = {code: name for code, name in available_sectors}
        
        toc_data = [["Sector", "Page"]]
        page_num = 3  # Starting page after title and TOC
        
        for chart_file in chart_files:
            # Extract sector code from filename
            basename = os.path.basename(chart_file)
            sector_code = basename.split('_')[0]
            sector_name = sector_lookup.get(sector_code, sector_code.replace('NIFTY-', '').replace('-', ' ').title())
            
            toc_data.append([f"{sector_name} ({sector_code})", str(page_num)])
            page_num += 1
        
        toc_table = Table(toc_data, colWidths=[4*inch, 1*inch])
        toc_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.lightblue),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('ALIGN', (1, 0), (1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('FONTSIZE', (0, 1), (-1, -1), 10),
        ]))
        
        story.append(toc_table)
        story.append(PageBreak())
        
        # Add each sector chart
        for i, chart_file in enumerate(chart_files, 1):
            try:
                # Extract sector information
                basename = os.path.basename(chart_file)
                sector_code = basename.split('_')[0]
                sector_name = sector_lookup.get(sector_code, sector_code.replace('NIFTY-', '').replace('-', ' ').title())
                
                # Section header
                story.append(Paragraph(f"📈 {sector_name} Analysis", section_style))
                story.append(Paragraph(f"Sector Code: {sector_code}", body_style))
                story.append(Spacer(1, 10))
                
                # Add chart image
                # Calculate image size to fit page nicely
                img_width = 7.5 * inch
                img_height = 5.6 * inch
                
                img = Image(chart_file, width=img_width, height=img_height)
                story.append(img)
                story.append(Spacer(1, 20))
                
                # Add page break except for last chart
                if i < len(chart_files):
                    story.append(PageBreak())
                    
                logger.info(f"📊 Added chart {i}/{len(chart_files)}: {sector_name}")
                
            except Exception as e:
                logger.warning(f"⚠️ Failed to add chart {chart_file}: {e}")
                continue
        
        # Final page with summary
        story.append(PageBreak())
        story.append(Paragraph("📊 Report Summary", section_style))
        
        final_summary = f"""
<b>Analysis Complete</b>

This comprehensive sector analysis report contains detailed charts for {len(chart_files)} major market sectors, 
providing insights into:

• <b>Market Trends:</b> Visual representation of bullish and bearish sentiment across sectors
• <b>Technical Strength:</b> Uptrend analysis showing sector momentum
• <b>Performance Metrics:</b> Key statistics for investment decision making
• <b>Historical Context:</b> {days_back}-day trend evolution and pattern recognition

<b>Next Steps:</b>
• Use sector performance rankings to identify investment opportunities
• Monitor trend changes and momentum shifts
• Compare sectors for portfolio diversification
• Track volatility and risk metrics across different market segments

<b>Report Generated:</b> {datetime.now().strftime('%B %d, %Y at %I:%M %p')}
<b>Data Period:</b> Last {days_back} trading days
<b>Total Sectors Analyzed:</b> {len(chart_files)} major market indices

For latest analysis and real-time data, regenerate this report with current market data.
"""
        
        story.append(Paragraph(final_summary, body_style))
        
        # Build PDF
        logger.info("📄 Building PDF document...")
        doc.build(story)
        
        # Check file size
        file_size = os.path.getsize(output_path) / 1024 / 1024  # MB
        
        success_message = f"""
✅ Sector Charts PDF Generated Successfully!

📄 File: {output_path}
📏 Size: {file_size:.1f} MB
📊 Charts: {len(chart_files)} sectors
📅 Period: {days_back} days
📈 Analysis: Comprehensive sector trends and metrics

The PDF contains:
• Executive summary and report overview
• Table of contents with page references
• Individual high-resolution chart for each sector
• Detailed metrics and performance indicators
• Professional formatting for presentations

Ready for analysis and sharing!
"""
        
        logger.info(f"✅ PDF generated successfully: {output_path}")
        return True, success_message
        
    except Exception as e:
        error_message = f"❌ Error generating sector charts PDF: {e}"
        logger.error(error_message)
        return False, error_message

def generate_quick_sector_charts_pdf(sectors=None, filename="quick_sector_charts.pdf", days_back=30):
    """
    Generate a quick PDF with selected sectors
    
    Args:
        sectors: List of sector codes to include (None for all)
        filename: Name of the PDF file
        days_back: Number of days of data
        
    Returns:
        Tuple of (success, message)
    """
    
    try:
        logger.info(f"🚀 Generating quick sector charts PDF...")
        
        # If specific sectors requested, generate only those charts
        if sectors:
            from .individual_sector_charts import generate_sector_chart_by_code
            
            charts_dir = "charts/sectors"
            os.makedirs(charts_dir, exist_ok=True)
            
            for sector in sectors:
                success, result = generate_sector_chart_by_code(sector, days_back=days_back)
                if not success:
                    logger.warning(f"⚠️ Failed to generate chart for {sector}: {result}")
        
        # Generate PDF with existing charts
        return generate_sector_charts_pdf(filename=filename, days_back=days_back, regenerate_charts=False)
        
    except Exception as e:
        error_message = f"❌ Error generating quick sector charts PDF: {e}"
        logger.error(error_message)
        return False, error_message

if __name__ == "__main__":
    # Test the PDF generation
    print("Testing sector charts PDF generation...")
    
    # Generate comprehensive PDF
    success, message = generate_sector_charts_pdf(
        filename="sector_charts_comprehensive_90day.pdf", 
        days_back=90,
        regenerate_charts=True
    )
    
    print(f"Success: {success}")
    print(f"Message: {message}")