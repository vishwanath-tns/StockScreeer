#!/usr/bin/env python3
"""
Simple Sectoral Trends PDF Report Generator
==========================================

Generates comprehensive PDF reports with multiple charts showing sectoral trends analysis.
"""

import sys
import os
from datetime import datetime, date, timedelta
from typing import Dict, List, Tuple, Optional
import logging

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    import pandas as pd
    import numpy as np
    from decimal import Decimal
    import matplotlib
    matplotlib.use('Agg')  # Non-interactive backend
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    from reportlab.lib.pagesizes import A4
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Image, Table, TableStyle
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER, TA_LEFT
    DEPENDENCIES_AVAILABLE = True
except ImportError as e:
    DEPENDENCIES_AVAILABLE = False
    print(f"Missing dependencies: {e}")

from services.sectoral_trends_service import SectoralTrendsService

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def convert_decimal_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Convert Decimal columns to float for proper pandas operations."""
    df_copy = df.copy()
    for col in df_copy.columns:
        if df_copy[col].dtype == 'object':
            # Check if column contains Decimal objects
            sample_val = df_copy[col].dropna().iloc[0] if not df_copy[col].dropna().empty else None
            if isinstance(sample_val, Decimal):
                df_copy[col] = df_copy[col].apply(lambda x: float(x) if x is not None else 0.0)
    return df_copy

def generate_sectoral_trends_pdf_simple(filename: Optional[str] = None, days_back: int = 90) -> Tuple[bool, str]:
    """
    Generate a comprehensive sectoral trends PDF report.
    
    Args:
        filename: Output filename (auto-generated if None)
        days_back: Number of days of historical data to include
        
    Returns:
        Tuple of (success, result_message)
    """
    if not DEPENDENCIES_AVAILABLE:
        return False, "Required libraries not available. Please install matplotlib, reportlab, and pandas."
    
    try:
        # Generate filename if not provided
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"sectoral_trends_report_{timestamp}.pdf"
        
        # Ensure charts directory exists
        os.makedirs("charts", exist_ok=True)
        filepath = os.path.join("charts", filename)
        
        logger.info(f"Generating sectoral trends report for last {days_back} days...")
        
        # Get data
        service = SectoralTrendsService()
        raw_data = service.get_trends_data(sectors=None, days_back=days_back)
        
        if raw_data.empty:
            return False, f"No sectoral trends data available for the last {days_back} days"
        
        # Convert Decimal columns to float
        data = convert_decimal_columns(raw_data)
        
        # Convert date column
        data['date'] = pd.to_datetime(data['analysis_date'])
        
        logger.info(f"Processing {len(data)} records for {data['sector_code'].nunique()} sectors")
        
        # Generate analysis
        analysis = analyze_trends(data)
        
        # Generate charts
        chart_paths = generate_charts(data)
        
        # Create PDF
        create_pdf_report(filepath, analysis, chart_paths, days_back)
        
        # Cleanup charts
        cleanup_charts(chart_paths)
        
        logger.info(f"Sectoral trends report generated: {filepath}")
        return True, f"Report saved: {filepath}"
        
    except Exception as e:
        logger.error(f"Failed to generate report: {e}")
        return False, f"Error: {str(e)}"

def analyze_trends(data: pd.DataFrame) -> Dict:
    """Analyze the sectoral trends data."""
    analysis = {}
    
    # Basic info
    analysis['total_records'] = len(data)
    analysis['sectors_count'] = data['sector_code'].nunique()
    analysis['date_range'] = {
        'start': data['date'].min().date(),
        'end': data['date'].max().date(),
        'days': (data['date'].max() - data['date'].min()).days + 1
    }
    
    # Current performance (latest date)
    latest_data = data[data['date'] == data['date'].max()]
    
    # Top performers
    top_bullish = latest_data.nlargest(5, 'bullish_percent')[['sector_name', 'bullish_percent', 'bearish_percent']]
    analysis['top_bullish_sectors'] = top_bullish.to_dict('records')
    
    # Momentum calculation
    momentum_results = []
    for sector in data['sector_code'].unique():
        sector_data = data[data['sector_code'] == sector].sort_values('date')
        if len(sector_data) >= 10:
            recent_bullish = sector_data['bullish_percent'].tail(5).mean()
            earlier_bullish = sector_data['bullish_percent'].head(5).mean()
            momentum = recent_bullish - earlier_bullish
            
            momentum_results.append({
                'sector_name': sector_data['sector_name'].iloc[0],
                'momentum': momentum,
                'current_bullish': sector_data['bullish_percent'].iloc[-1],
                'volatility': sector_data['bullish_percent'].std()
            })
    
    if momentum_results:
        momentum_df = pd.DataFrame(momentum_results)
        analysis['strongest_momentum'] = momentum_df.nlargest(3, 'momentum')[['sector_name', 'momentum', 'current_bullish']].to_dict('records')
        analysis['most_stable'] = momentum_df.nsmallest(3, 'volatility')[['sector_name', 'volatility', 'current_bullish']].to_dict('records')
    else:
        analysis['strongest_momentum'] = []
        analysis['most_stable'] = []
    
    # Predictions
    analysis['predictions'] = generate_predictions(momentum_results, latest_data)
    
    return analysis

def generate_predictions(momentum_results: List[Dict], latest_data: pd.DataFrame) -> Dict:
    """Generate sector predictions based on analysis."""
    predictions = {
        'upcoming_sectors': [],
        'stable_outperformers': [],
        'recovery_candidates': []
    }
    
    if not momentum_results:
        return predictions
    
    momentum_df = pd.DataFrame(momentum_results)
    latest_dict = {row['sector_name']: row for _, row in latest_data.iterrows()}
    
    for _, row in momentum_df.iterrows():
        sector_name = row['sector_name']
        momentum = row['momentum']
        current_bullish = row['current_bullish']
        volatility = row['volatility']
        
        # Get latest data for this sector
        latest_info = latest_dict.get(sector_name, {})
        weekly_uptrend = latest_info.get('weekly_uptrend_percent', 0)
        
        # Upcoming sectors: positive momentum, room to grow
        if momentum > 2 and current_bullish < 70 and weekly_uptrend > 50:
            predictions['upcoming_sectors'].append({
                'sector_name': sector_name,
                'momentum': momentum,
                'current_bullish': current_bullish,
                'weekly_uptrend': weekly_uptrend
            })
        
        # Stable outperformers: high bullish % with low volatility
        if current_bullish > 60 and volatility < 10:
            predictions['stable_outperformers'].append({
                'sector_name': sector_name,
                'current_bullish': current_bullish,
                'volatility': volatility,
                'momentum': momentum
            })
        
        # Recovery candidates: low current but positive momentum
        if current_bullish < 40 and momentum > 0:
            predictions['recovery_candidates'].append({
                'sector_name': sector_name,
                'current_bullish': current_bullish,
                'momentum': momentum,
                'recovery_potential': momentum / max(1, abs(current_bullish - 50))
            })
    
    # Sort and limit predictions
    predictions['upcoming_sectors'] = sorted(predictions['upcoming_sectors'], 
                                           key=lambda x: x['momentum'], reverse=True)[:3]
    predictions['stable_outperformers'] = sorted(predictions['stable_outperformers'], 
                                                key=lambda x: x['current_bullish'], reverse=True)[:3]
    predictions['recovery_candidates'] = sorted(predictions['recovery_candidates'], 
                                              key=lambda x: x['momentum'], reverse=True)[:3]
    
    return predictions

def generate_charts(data: pd.DataFrame) -> List[str]:
    """Generate charts for the report."""
    chart_paths = []
    
    # Chart 1: Bullish percentage trends for top 6 sectors
    plt.figure(figsize=(12, 8))
    
    top_sectors = data.groupby('sector_code')['bullish_percent'].mean().nlargest(6).index
    colors = plt.cm.tab10(np.linspace(0, 1, len(top_sectors)))
    
    for i, sector in enumerate(top_sectors):
        sector_data = data[data['sector_code'] == sector].sort_values('date')
        sector_name = sector_data['sector_name'].iloc[0]
        plt.plot(sector_data['date'], sector_data['bullish_percent'], 
                label=sector_name, linewidth=2, marker='o', markersize=4, color=colors[i])
    
    plt.title('Sectoral Bullish Percentage Trends (Top 6 Sectors)', fontsize=16, fontweight='bold')
    plt.xlabel('Date')
    plt.ylabel('Bullish %')
    plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
    plt.grid(True, alpha=0.3)
    plt.xticks(rotation=45)
    plt.tight_layout()
    
    chart1_path = "charts/temp_bullish_trends.png"
    plt.savefig(chart1_path, dpi=300, bbox_inches='tight')
    plt.close()
    chart_paths.append(chart1_path)
    
    # Chart 2: Current sector comparison
    plt.figure(figsize=(14, 8))
    
    latest_data = data[data['date'] == data['date'].max()].sort_values('bullish_percent', ascending=False)
    sectors = latest_data['sector_name'].head(10)
    bullish_values = latest_data['bullish_percent'].head(10)
    
    bars = plt.bar(sectors, bullish_values, color='skyblue', alpha=0.8)
    plt.title('Current Sectoral Bullish Percentage (Top 10)', fontsize=16, fontweight='bold')
    plt.xlabel('Sectors')
    plt.ylabel('Bullish %')
    plt.xticks(rotation=45, ha='right')
    plt.grid(True, alpha=0.3, axis='y')
    
    # Add value labels
    for bar in bars:
        height = bar.get_height()
        plt.annotate(f'{height:.1f}%', xy=(bar.get_x() + bar.get_width()/2, height),
                    xytext=(0, 3), textcoords="offset points", ha='center', va='bottom')
    
    plt.tight_layout()
    
    chart2_path = "charts/temp_current_comparison.png"
    plt.savefig(chart2_path, dpi=300, bbox_inches='tight')
    plt.close()
    chart_paths.append(chart2_path)
    
    return chart_paths

def create_pdf_report(filepath: str, analysis: Dict, chart_paths: List[str], days_back: int):
    """Create the PDF report."""
    doc = SimpleDocTemplate(filepath, pagesize=A4)
    styles = getSampleStyleSheet()
    story = []
    
    # Title style
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Title'],
        fontSize=24,
        textColor=colors.darkblue,
        alignment=TA_CENTER,
        spaceAfter=30
    )
    
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading1'],
        fontSize=16,
        textColor=colors.darkgreen,
        spaceBefore=20,
        spaceAfter=10
    )
    
    # Title page
    story.append(Paragraph("Sectoral Trends Analysis Report", title_style))
    story.append(Spacer(1, 0.5*inch))
    
    subtitle = f"Comprehensive {days_back}-Day Market Analysis"
    story.append(Paragraph(subtitle, styles['Heading2']))
    story.append(Spacer(1, 0.5*inch))
    
    # Report info
    report_info = f"""
    <b>Report Generated:</b> {datetime.now().strftime('%B %d, %Y')}<br/>
    <b>Analysis Period:</b> {analysis['date_range']['start']} to {analysis['date_range']['end']}<br/>
    <b>Sectors Analyzed:</b> {analysis['sectors_count']}<br/>
    <b>Total Data Points:</b> {analysis['total_records']}<br/>
    """
    story.append(Paragraph(report_info, styles['Normal']))
    story.append(PageBreak())
    
    # Executive Summary
    story.append(Paragraph("Executive Summary", heading_style))
    
    if analysis['top_bullish_sectors']:
        top_sector = analysis['top_bullish_sectors'][0]
        summary_text = f"""
        This report analyzes sectoral trends across {analysis['sectors_count']} major sectors over {analysis['date_range']['days']} trading days.
        
        <b>Key Findings:</b><br/>
        • <b>Top Performing Sector:</b> {top_sector['sector_name']} with {top_sector['bullish_percent']:.1f}% bullish stocks<br/>
        • <b>Analysis Period:</b> {analysis['date_range']['days']} trading days<br/>
        • <b>Data Coverage:</b> {analysis['total_records']} sector-day observations<br/>
        """
        story.append(Paragraph(summary_text, styles['Normal']))
    
    story.append(PageBreak())
    
    # Charts section
    story.append(Paragraph("Visual Trend Analysis", heading_style))
    
    chart_titles = [
        "Bullish Percentage Trends (Top 6 Sectors)",
        "Current Sectoral Performance (Top 10)"
    ]
    
    for i, (chart_path, title) in enumerate(zip(chart_paths, chart_titles)):
        if os.path.exists(chart_path):
            story.append(Paragraph(f"{i+1}. {title}", styles['Heading2']))
            img = Image(chart_path, width=7*inch, height=5*inch)
            story.append(img)
            story.append(Spacer(1, 0.3*inch))
            if i < len(chart_paths) - 1:
                story.append(PageBreak())
    
    # Sector Rankings
    story.append(PageBreak())
    story.append(Paragraph("Sector Performance Rankings", heading_style))
    
    # Top Bullish Sectors Table
    story.append(Paragraph("Top Bullish Sectors", styles['Heading2']))
    
    if analysis['top_bullish_sectors']:
        table_data = [['Rank', 'Sector', 'Bullish %', 'Bearish %']]
        for i, sector in enumerate(analysis['top_bullish_sectors'], 1):
            table_data.append([
                str(i),
                sector['sector_name'],
                f"{sector['bullish_percent']:.1f}%",
                f"{sector['bearish_percent']:.1f}%"
            ])
        
        table = Table(table_data)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.darkgreen),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        story.append(table)
        story.append(Spacer(1, 0.3*inch))
    
    # Predictions
    story.append(PageBreak())
    story.append(Paragraph("Sector Predictions & Investment Insights", heading_style))
    
    predictions = analysis['predictions']
    
    if predictions['upcoming_sectors']:
        story.append(Paragraph("🚀 Upcoming Sectors (Growth Potential)", styles['Heading2']))
        pred_text = "Based on momentum analysis, these sectors show strong growth potential:<br/><br/>"
        
        for i, sector in enumerate(predictions['upcoming_sectors'], 1):
            pred_text += f"""
            <b>{i}. {sector['sector_name']}</b><br/>
            • Momentum Score: <b>{sector['momentum']:+.1f}</b><br/>
            • Current Bullish: <b>{sector['current_bullish']:.1f}%</b><br/><br/>
            """
        
        story.append(Paragraph(pred_text, styles['Normal']))
    
    if predictions['stable_outperformers']:
        story.append(Paragraph("⭐ Stable Outperformers", styles['Heading2']))
        stable_text = "Sectors with consistent high performance:<br/><br/>"
        
        for i, sector in enumerate(predictions['stable_outperformers'], 1):
            stable_text += f"""
            <b>{i}. {sector['sector_name']}</b><br/>
            • Current Bullish: <b>{sector['current_bullish']:.1f}%</b><br/>
            • Volatility: <b>{sector['volatility']:.1f}</b><br/><br/>
            """
        
        story.append(Paragraph(stable_text, styles['Normal']))
    
    # Build PDF
    doc.build(story)

def cleanup_charts(chart_paths: List[str]):
    """Remove temporary chart files."""
    for chart_path in chart_paths:
        try:
            if os.path.exists(chart_path):
                os.remove(chart_path)
        except Exception as e:
            logger.warning(f"Failed to cleanup {chart_path}: {e}")

if __name__ == "__main__":
    print("Testing Simple Sectoral Trends PDF Generator")
    print("=" * 50)
    
    success, message = generate_sectoral_trends_pdf_simple(
        filename="sectoral_trends_comprehensive_90day.pdf", 
        days_back=90
    )
    
    if success:
        print(f"✅ {message}")
    else:
        print(f"❌ {message}")