#!/usr/bin/env python3
"""
Generate PDF Guide: Understanding Stock Rankings Distributions

This script creates a comprehensive PDF explaining how to interpret
the rankings data visualizations and what they mean for trading decisions.
"""

import sys
sys.path.insert(0, '.')

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, cm
from reportlab.lib.colors import HexColor, black, white
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, 
    PageBreak, ListFlowable, ListItem, Image
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
from datetime import datetime
from pathlib import Path


def create_styles():
    """Create custom styles for the PDF."""
    styles = getSampleStyleSheet()
    
    styles.add(ParagraphStyle(
        name='MainTitle',
        parent=styles['Heading1'],
        fontSize=24,
        spaceAfter=30,
        textColor=HexColor('#1a5276'),
        alignment=TA_CENTER,
    ))
    
    styles.add(ParagraphStyle(
        name='SectionTitle',
        parent=styles['Heading2'],
        fontSize=16,
        spaceBefore=20,
        spaceAfter=12,
        textColor=HexColor('#2874a6'),
        borderPadding=5,
    ))
    
    styles.add(ParagraphStyle(
        name='SubSection',
        parent=styles['Heading3'],
        fontSize=13,
        spaceBefore=15,
        spaceAfter=8,
        textColor=HexColor('#1e8449'),
    ))
    
    # Override the existing BodyText style
    styles['BodyText'].fontSize = 11
    styles['BodyText'].spaceBefore = 6
    styles['BodyText'].spaceAfter = 6
    styles['BodyText'].alignment = TA_JUSTIFY
    styles['BodyText'].leading = 16
    
    styles.add(ParagraphStyle(
        name='Highlight',
        parent=styles['Normal'],
        fontSize=11,
        spaceBefore=8,
        spaceAfter=8,
        backColor=HexColor('#eaf2f8'),
        borderPadding=10,
        leftIndent=10,
        rightIndent=10,
    ))
    
    styles.add(ParagraphStyle(
        name='BulletText',
        parent=styles['Normal'],
        fontSize=11,
        leftIndent=20,
        spaceBefore=4,
        spaceAfter=4,
    ))
    
    styles.add(ParagraphStyle(
        name='TableHeader',
        parent=styles['Normal'],
        fontSize=10,
        textColor=white,
        alignment=TA_CENTER,
    ))
    
    return styles


def generate_pdf():
    """Generate the rankings guide PDF."""
    output_path = Path("reports/Rankings_Distribution_Guide.pdf")
    output_path.parent.mkdir(exist_ok=True)
    
    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=A4,
        rightMargin=0.75*inch,
        leftMargin=0.75*inch,
        topMargin=0.75*inch,
        bottomMargin=0.75*inch
    )
    
    styles = create_styles()
    story = []
    
    # =========================================================================
    # TITLE PAGE
    # =========================================================================
    story.append(Spacer(1, 2*inch))
    story.append(Paragraph("📊 Understanding Stock Rankings", styles['MainTitle']))
    story.append(Paragraph("A Complete Guide to Distribution Analysis", styles['SectionTitle']))
    story.append(Spacer(1, 0.5*inch))
    story.append(Paragraph(
        f"Generated: {datetime.now().strftime('%B %d, %Y')}",
        ParagraphStyle('Date', parent=styles['Normal'], alignment=TA_CENTER, textColor=HexColor('#666666'))
    ))
    story.append(Spacer(1, 1*inch))
    
    # Quick summary box
    summary_text = """
    <b>What This Report Covers:</b><br/><br/>
    • RS Rating (1-99): Relative Strength vs market<br/>
    • Momentum Score (0-100): Price momentum indicators<br/>
    • Trend Template (0-8): Mark Minervini's trend criteria<br/>
    • Technical Score (0-100): RSI and price action quality<br/>
    • Composite Score (0-100): Weighted overall rating<br/>
    • Score Correlations: How metrics relate to each other
    """
    story.append(Paragraph(summary_text, styles['Highlight']))
    
    story.append(PageBreak())
    
    # =========================================================================
    # RS RATING SECTION
    # =========================================================================
    story.append(Paragraph("1. RS Rating (Relative Strength) - Scale: 1 to 99", styles['SectionTitle']))
    
    story.append(Paragraph(
        """The RS Rating measures how a stock's price performance compares to all other stocks 
        in the universe over the past 12 months. A rating of 99 means the stock outperformed 
        99% of all stocks, while a rating of 1 means it underperformed 99% of stocks.""",
        styles['BodyText']
    ))
    
    story.append(Paragraph("How It's Calculated:", styles['SubSection']))
    story.append(Paragraph(
        """RS Rating uses a weighted average of returns over multiple periods:<br/>
        • 3-month return: 40% weight (most recent performance)<br/>
        • 6-month return: 20% weight<br/>
        • 9-month return: 20% weight<br/>
        • 12-month return: 20% weight<br/><br/>
        Stocks are then ranked from 1-99 based on this weighted performance.""",
        styles['BodyText']
    ))
    
    story.append(Paragraph("Interpreting the Distribution:", styles['SubSection']))
    
    # RS Rating interpretation table
    rs_data = [
        ['RS Range', 'Interpretation', 'Action'],
        ['80-99', 'Market Leaders - Top performers', 'Prime buy candidates'],
        ['60-79', 'Above Average - Outperforming', 'Worth watching'],
        ['40-59', 'Average - In line with market', 'Neutral'],
        ['20-39', 'Below Average - Underperforming', 'Avoid or short'],
        ['1-19', 'Laggards - Worst performers', 'Strong avoid'],
    ]
    
    rs_table = Table(rs_data, colWidths=[1.2*inch, 2.5*inch, 1.8*inch])
    rs_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), HexColor('#2874a6')),
        ('TEXTCOLOR', (0, 0), (-1, 0), white),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, 1), HexColor('#d4efdf')),
        ('BACKGROUND', (0, 2), (-1, 2), HexColor('#e8f6f3')),
        ('BACKGROUND', (0, 4), (-1, 4), HexColor('#fadbd8')),
        ('BACKGROUND', (0, 5), (-1, 5), HexColor('#f5b7b1')),
        ('GRID', (0, 0), (-1, -1), 1, HexColor('#cccccc')),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 1), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 8),
    ]))
    story.append(rs_table)
    story.append(Spacer(1, 0.2*inch))
    
    story.append(Paragraph(
        """<b>Your Distribution (Mean: 50.1):</b> A mean around 50 is expected and healthy - 
        it indicates the ranking system is properly calibrated. The relatively flat distribution 
        across all scores shows good diversification in the market with stocks at all performance levels.""",
        styles['Highlight']
    ))
    
    story.append(PageBreak())
    
    # =========================================================================
    # MOMENTUM SCORE SECTION
    # =========================================================================
    story.append(Paragraph("2. Momentum Score - Scale: 0 to 100", styles['SectionTitle']))
    
    story.append(Paragraph(
        """The Momentum Score captures the rate of change in a stock's price over multiple 
        timeframes. Unlike RS Rating which compares to other stocks, Momentum Score measures 
        the absolute strength of price movement.""",
        styles['BodyText']
    ))
    
    story.append(Paragraph("Components of Momentum Score:", styles['SubSection']))
    story.append(Paragraph(
        """• <b>Short-term ROC (1 week):</b> 40% weight - Captures immediate momentum<br/>
        • <b>Medium-term ROC (1 month):</b> 35% weight - Recent trend strength<br/>
        • <b>Longer-term ROC (3 months):</b> 25% weight - Sustained momentum<br/><br/>
        Positive ROC adds to the score, negative ROC reduces it.""",
        styles['BodyText']
    ))
    
    story.append(Paragraph("Interpreting the Distribution:", styles['SubSection']))
    
    mom_data = [
        ['Score Range', 'Market Condition', 'Trading Implication'],
        ['70-100', 'Strong upward momentum', 'Trend following works well'],
        ['50-69', 'Positive but moderate', 'Selective buying'],
        ['40-49', 'Neutral/consolidating', 'Wait for direction'],
        ['20-39', 'Negative momentum', 'Defensive positioning'],
        ['0-19', 'Strong downward momentum', 'Avoid longs, consider shorts'],
    ]
    
    mom_table = Table(mom_data, colWidths=[1.2*inch, 2*inch, 2.3*inch])
    mom_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), HexColor('#2874a6')),
        ('TEXTCOLOR', (0, 0), (-1, 0), white),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, 1), HexColor('#d4efdf')),
        ('BACKGROUND', (0, 4), (-1, 4), HexColor('#fadbd8')),
        ('BACKGROUND', (0, 5), (-1, 5), HexColor('#f5b7b1')),
        ('GRID', (0, 0), (-1, -1), 1, HexColor('#cccccc')),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 1), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 8),
    ]))
    story.append(mom_table)
    story.append(Spacer(1, 0.2*inch))
    
    story.append(Paragraph(
        """<b>Your Distribution (Mean: 44.9):</b> A mean below 50 indicates the overall market 
        has slightly negative momentum. The distribution shows most stocks clustered in the 
        30-50 range, suggesting a consolidating or mildly bearish market environment. 
        The peak around 40-50 indicates many stocks are in a wait-and-see phase.""",
        styles['Highlight']
    ))
    
    story.append(PageBreak())
    
    # =========================================================================
    # TREND TEMPLATE SECTION
    # =========================================================================
    story.append(Paragraph("3. Trend Template Score - Scale: 0 to 8", styles['SectionTitle']))
    
    story.append(Paragraph(
        """The Trend Template is based on Mark Minervini's SEPA methodology (Specific Entry Point 
        Analysis). It checks 8 criteria that define a stock in a proper Stage 2 uptrend - the 
        ideal stage for buying growth stocks.""",
        styles['BodyText']
    ))
    
    story.append(Paragraph("The 8 Criteria Checked:", styles['SubSection']))
    
    criteria_text = """
    <b>Price Position (3 points):</b><br/>
    1. Price above 50-day MA (+1)<br/>
    2. Price above 150-day MA (+1)<br/>
    3. Price above 200-day MA (+1)<br/><br/>
    
    <b>Moving Average Alignment (3 points):</b><br/>
    4. 50-day MA above 150-day MA (+1)<br/>
    5. 50-day MA above 200-day MA (+1)<br/>
    6. 150-day MA above 200-day MA (+1)<br/><br/>
    
    <b>Trend Strength (2 points):</b><br/>
    7. 200-day MA trending up vs 20 days ago (+1)<br/>
    8. Price within 25% of 52-week high (+1)
    """
    story.append(Paragraph(criteria_text, styles['BodyText']))
    
    story.append(Paragraph("Interpreting the Scores:", styles['SubSection']))
    
    trend_data = [
        ['Score', 'Stage', 'Description', 'Action'],
        ['8', 'Perfect Stage 2', 'All criteria met - ideal uptrend', 'Strong Buy Zone'],
        ['6-7', 'Strong Uptrend', 'Most criteria met', 'Good Buy Candidates'],
        ['4-5', 'Emerging/Weakening', 'Mixed signals', 'Watch & Wait'],
        ['2-3', 'Stage 3 or 4', 'Trend breakdown starting', 'Avoid/Reduce'],
        ['0-1', 'Stage 4 Decline', 'Confirmed downtrend', 'Do Not Buy'],
    ]
    
    trend_table = Table(trend_data, colWidths=[0.7*inch, 1.3*inch, 2*inch, 1.5*inch])
    trend_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), HexColor('#2874a6')),
        ('TEXTCOLOR', (0, 0), (-1, 0), white),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, 1), HexColor('#abebc6')),
        ('BACKGROUND', (0, 2), (-1, 2), HexColor('#d4efdf')),
        ('BACKGROUND', (0, 4), (-1, 4), HexColor('#fadbd8')),
        ('BACKGROUND', (0, 5), (-1, 5), HexColor('#f5b7b1')),
        ('GRID', (0, 0), (-1, -1), 1, HexColor('#cccccc')),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 1), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 8),
    ]))
    story.append(trend_table)
    story.append(Spacer(1, 0.2*inch))
    
    story.append(Paragraph(
        """<b>Your Distribution:</b> The histogram shows a bimodal pattern with peaks at both 
        low (0-2) and high (7-8) scores. This is a healthy market structure showing:<br/>
        • ~175 stocks with score 8 (perfect uptrends) - Your prime hunting ground<br/>
        • Many stocks at 0-2 (downtrends) - Clear stocks to avoid<br/>
        • Fewer stocks in the middle - Less ambiguity<br/><br/>
        <b>Key Insight:</b> Focus your attention on the ~175 stocks with score 7-8. These are 
        in confirmed Stage 2 uptrends and are the best candidates for momentum trades.""",
        styles['Highlight']
    ))
    
    story.append(PageBreak())
    
    # =========================================================================
    # TECHNICAL SCORE SECTION
    # =========================================================================
    story.append(Paragraph("4. Technical Score - Scale: 0 to 100", styles['SectionTitle']))
    
    story.append(Paragraph(
        """The Technical Score combines RSI (Relative Strength Index) analysis with price 
        action quality. It helps identify stocks with favorable technical setups for 
        entry points.""",
        styles['BodyText']
    ))
    
    story.append(Paragraph("Components:", styles['SubSection']))
    story.append(Paragraph(
        """• <b>RSI Position (base 50):</b><br/>
        &nbsp;&nbsp;- RSI 50-70: +20 points (bullish but not overbought)<br/>
        &nbsp;&nbsp;- RSI > 70: +10 points (overbought, reduced score)<br/>
        &nbsp;&nbsp;- RSI 30-50: -10 points (neutral to bearish)<br/>
        &nbsp;&nbsp;- RSI < 30: -20 points (oversold)<br/><br/>
        • <b>Volume Trend:</b> +10 if current volume > 20-day average × 1.2<br/>
        • <b>Price Action:</b> +10 if 6+ of last 10 days closed higher than open""",
        styles['BodyText']
    ))
    
    story.append(Paragraph("Interpreting the Distribution:", styles['SubSection']))
    story.append(Paragraph(
        """<b>Your Distribution (Mean: 54.3):</b> The bimodal distribution with peaks around 
        20-30 and 80-90 shows a polarized market:<br/><br/>
        • <b>Left peak (20-30):</b> Stocks with poor technicals - oversold or in downtrends<br/>
        • <b>Right peak (80-90):</b> Stocks with strong technicals - good RSI and price action<br/><br/>
        <b>Trading Implication:</b> The market is split between leaders and laggards. 
        Focus on the right tail (70+) for long positions. The stocks in the left tail 
        may present mean-reversion opportunities but carry higher risk.""",
        styles['Highlight']
    ))
    
    story.append(PageBreak())
    
    # =========================================================================
    # COMPOSITE SCORE SECTION
    # =========================================================================
    story.append(Paragraph("5. Composite Score - Scale: 0 to 100", styles['SectionTitle']))
    
    story.append(Paragraph(
        """The Composite Score is a weighted combination of all individual metrics, providing 
        a single number to rank stocks. This is your primary screening metric.""",
        styles['BodyText']
    ))
    
    story.append(Paragraph("Weighting Formula:", styles['SubSection']))
    story.append(Paragraph(
        """<b>Composite = (RS × 0.30) + (Momentum × 0.25) + (Trend × 0.25) + (Technical × 0.20)</b><br/><br/>
        • RS Rating: 30% - Emphasizes relative performance<br/>
        • Momentum: 25% - Price velocity matters<br/>
        • Trend Template: 25% - Proper trend structure essential<br/>
        • Technical: 20% - Entry timing refinement""",
        styles['BodyText']
    ))
    
    story.append(Paragraph("Letter Grades:", styles['SubSection']))
    
    grade_data = [
        ['Score', 'Grade', 'Meaning', 'Typical Count'],
        ['90-100', 'A+ ⭐', 'Elite performers - Top 5%', '~40 stocks'],
        ['80-89', 'A', 'Excellent - Strong buys', '~80 stocks'],
        ['70-79', 'B+', 'Good - Watchlist worthy', '~100 stocks'],
        ['60-69', 'B', 'Above average', '~120 stocks'],
        ['50-59', 'C+', 'Average', '~150 stocks'],
        ['40-49', 'C', 'Below average', '~120 stocks'],
        ['30-39', 'D', 'Poor', '~100 stocks'],
        ['0-29', 'F', 'Avoid', '~90 stocks'],
    ]
    
    grade_table = Table(grade_data, colWidths=[0.9*inch, 0.8*inch, 2*inch, 1.3*inch])
    grade_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), HexColor('#2874a6')),
        ('TEXTCOLOR', (0, 0), (-1, 0), white),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, 1), HexColor('#82e0aa')),
        ('BACKGROUND', (0, 2), (-1, 2), HexColor('#abebc6')),
        ('BACKGROUND', (0, 3), (-1, 3), HexColor('#d4efdf')),
        ('BACKGROUND', (0, 6), (-1, 6), HexColor('#fadbd8')),
        ('BACKGROUND', (0, 7), (-1, 7), HexColor('#f1948a')),
        ('BACKGROUND', (0, 8), (-1, 8), HexColor('#e74c3c')),
        ('TEXTCOLOR', (0, 8), (-1, 8), white),
        ('GRID', (0, 0), (-1, -1), 1, HexColor('#cccccc')),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 1), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 8),
    ]))
    story.append(grade_table)
    story.append(Spacer(1, 0.2*inch))
    
    story.append(Paragraph(
        """<b>Your Distribution (Mean: 51.4):</b> The distribution shows a roughly normal 
        pattern centered around 50, which is expected. Key observations:<br/><br/>
        • Most stocks cluster in the 40-60 range (average performers)<br/>
        • Right tail (70+) contains your best opportunities<br/>
        • Left tail (<30) contains stocks to avoid<br/><br/>
        <b>Strategy:</b> Focus screening on Composite Score ≥ 70 (grades B+ or better). 
        This typically narrows your universe from 761 stocks to ~150-200 actionable candidates.""",
        styles['Highlight']
    ))
    
    story.append(PageBreak())
    
    # =========================================================================
    # CORRELATION MATRIX SECTION
    # =========================================================================
    story.append(Paragraph("6. Score Correlations Heatmap", styles['SectionTitle']))
    
    story.append(Paragraph(
        """The correlation matrix shows how the different metrics relate to each other. 
        Values range from 0 (no correlation) to 1 (perfect correlation).""",
        styles['BodyText']
    ))
    
    story.append(Paragraph("Reading the Heatmap:", styles['SubSection']))
    
    corr_data = [
        ['Pair', 'Correlation', 'Interpretation'],
        ['RS ↔ Momentum', '0.84', 'Strong link - outperformers have momentum'],
        ['RS ↔ Trend', '0.82', 'Strong link - RS aligns with proper trends'],
        ['Momentum ↔ Trend', '0.81', 'Strong link - momentum confirms trends'],
        ['Trend ↔ Composite', '0.97', 'Very strong - trend drives overall score'],
        ['RS ↔ Technical', '0.74', 'Moderate - RS partially independent'],
        ['Tech ↔ Composite', '0.95', 'Very strong - technicals matter for composite'],
    ]
    
    corr_table = Table(corr_data, colWidths=[1.6*inch, 1.1*inch, 2.8*inch])
    corr_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), HexColor('#2874a6')),
        ('TEXTCOLOR', (0, 0), (-1, 0), white),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('ALIGN', (2, 1), (2, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('GRID', (0, 0), (-1, -1), 1, HexColor('#cccccc')),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 1), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 8),
    ]))
    story.append(corr_table)
    story.append(Spacer(1, 0.2*inch))
    
    story.append(Paragraph(
        """<b>Key Insights from Correlations:</b><br/><br/>
        1. <b>All metrics are positively correlated (0.74-0.97)</b> - The system is internally 
        consistent. Strong stocks tend to be strong across all dimensions.<br/><br/>
        2. <b>Trend has highest correlation with Composite (0.97)</b> - This confirms that 
        trend structure is the most important factor in the overall ranking.<br/><br/>
        3. <b>Technical has lowest correlation with RS (0.74)</b> - This means Technical Score 
        adds unique information not captured by RS alone. A stock can have high RS but 
        poor near-term technicals (overbought), or vice versa.<br/><br/>
        4. <b>No negative correlations</b> - All factors move together, reinforcing the 
        concept that true leaders are strong across multiple dimensions.""",
        styles['Highlight']
    ))
    
    story.append(PageBreak())
    
    # =========================================================================
    # PRACTICAL TRADING GUIDE
    # =========================================================================
    story.append(Paragraph("7. Practical Trading Application", styles['SectionTitle']))
    
    story.append(Paragraph("Screening Workflow:", styles['SubSection']))
    story.append(Paragraph(
        """<b>Step 1: Primary Filter (Composite Score)</b><br/>
        Start with Composite ≥ 70 to narrow from 761 stocks to ~150-200<br/><br/>
        
        <b>Step 2: Trend Confirmation</b><br/>
        Require Trend Template ≥ 6 (Stage 2 uptrend confirmed)<br/><br/>
        
        <b>Step 3: Relative Strength Check</b><br/>
        Prefer RS ≥ 70 (top 30% performers)<br/><br/>
        
        <b>Step 4: Entry Timing</b><br/>
        Use Technical Score to time entries - look for pullbacks to support with 
        Technical Score recovering from 50-60 back toward 70+<br/><br/>
        
        <b>Step 5: Momentum Confirmation</b><br/>
        Momentum ≥ 60 confirms the move has velocity""",
        styles['BodyText']
    ))
    
    story.append(Paragraph("Market Condition Signals:", styles['SubSection']))
    
    market_data = [
        ['Indicator', 'Bullish Market', 'Bearish Market'],
        ['Mean RS Rating', '> 55', '< 45'],
        ['Mean Momentum', '> 55', '< 45'],
        ['Stocks with Trend ≥ 6', '> 40%', '< 25%'],
        ['Mean Composite', '> 55', '< 45'],
    ]
    
    market_table = Table(market_data, colWidths=[2*inch, 1.7*inch, 1.7*inch])
    market_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), HexColor('#2874a6')),
        ('TEXTCOLOR', (0, 0), (-1, 0), white),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (1, 1), (1, -1), HexColor('#d4efdf')),
        ('BACKGROUND', (2, 1), (2, -1), HexColor('#fadbd8')),
        ('GRID', (0, 0), (-1, -1), 1, HexColor('#cccccc')),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 1), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 8),
    ]))
    story.append(market_table)
    story.append(Spacer(1, 0.3*inch))
    
    story.append(Paragraph(
        """<b>Current Market Reading (Your Data):</b><br/>
        • RS Mean: 50.1 → Neutral (neither bullish nor bearish overall)<br/>
        • Momentum Mean: 44.9 → Slightly bearish undertone<br/>
        • ~175 stocks with Trend = 8 → ~23% in perfect uptrends (borderline)<br/>
        • Composite Mean: 51.4 → Neutral<br/><br/>
        <b>Interpretation:</b> The market is in a mixed/consolidation phase. Be selective 
        and focus only on the strongest stocks (Composite ≥ 75). This is not a market 
        where you buy average stocks - only leaders will work.""",
        styles['Highlight']
    ))
    
    story.append(PageBreak())
    
    # =========================================================================
    # QUICK REFERENCE CARD
    # =========================================================================
    story.append(Paragraph("Quick Reference Card", styles['SectionTitle']))
    
    ref_data = [
        ['Metric', 'Range', 'Buy Zone', 'Avoid Zone', 'Weight'],
        ['RS Rating', '1-99', '≥ 70', '< 40', '30%'],
        ['Momentum', '0-100', '≥ 60', '< 40', '25%'],
        ['Trend Template', '0-8', '≥ 6', '< 4', '25%'],
        ['Technical', '0-100', '≥ 65', '< 40', '20%'],
        ['Composite', '0-100', '≥ 70 (B+)', '< 50 (C)', '100%'],
    ]
    
    ref_table = Table(ref_data, colWidths=[1.3*inch, 0.9*inch, 1*inch, 1*inch, 0.9*inch])
    ref_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), HexColor('#1a5276')),
        ('TEXTCOLOR', (0, 0), (-1, 0), white),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTNAME', (0, 1), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (2, 1), (2, -1), HexColor('#d4efdf')),
        ('BACKGROUND', (3, 1), (3, -1), HexColor('#fadbd8')),
        ('GRID', (0, 0), (-1, -1), 1, HexColor('#cccccc')),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 1), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 10),
    ]))
    story.append(ref_table)
    story.append(Spacer(1, 0.5*inch))
    
    # Final tips
    story.append(Paragraph("Final Trading Tips", styles['SubSection']))
    story.append(Paragraph(
        """1. <b>Buy the best, forget the rest</b> - Only buy stocks with Composite ≥ 70 
        AND Trend ≥ 6. This alone filters out 70% of stocks.<br/><br/>
        
        2. <b>Sector rotation matters</b> - Use the Sector Rotation tab to find which 
        sectors are leading. Focus your stock picks within leading sectors.<br/><br/>
        
        3. <b>Watch for divergences</b> - If a stock has high RS but falling Momentum, 
        the trend may be exhausting. If Momentum is rising but RS is low, it may be 
        an emerging leader.<br/><br/>
        
        4. <b>Time entries with Technical Score</b> - Even great stocks have pullbacks. 
        Wait for Technical Score to dip to 50-60 and then recover before buying.<br/><br/>
        
        5. <b>Monitor daily</b> - Rankings change daily. A stock at Composite 80 today 
        could drop to 60 next week if momentum fades.""",
        styles['BodyText']
    ))
    
    # Build PDF
    doc.build(story)
    print(f"✅ PDF generated: {output_path.absolute()}")
    return output_path


if __name__ == "__main__":
    pdf_path = generate_pdf()
    
    # Open the PDF
    import subprocess
    subprocess.Popen(['start', '', str(pdf_path)], shell=True)
