#!/usr/bin/env python
"""
Generate PDF documentation for Stock Ratings System

Creates a comprehensive PDF explaining all rating components.
"""

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, cm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, ListFlowable, ListItem
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
from datetime import datetime
import os


def create_stock_ratings_pdf():
    """Create the Stock Ratings explanation PDF."""
    
    # Output path
    output_dir = os.path.dirname(os.path.abspath(__file__))
    output_path = os.path.join(output_dir, "Stock_Ratings_Explained.pdf")
    
    # Create document
    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        rightMargin=1*inch,
        leftMargin=1*inch,
        topMargin=1*inch,
        bottomMargin=1*inch
    )
    
    # Styles
    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        spaceAfter=30,
        alignment=TA_CENTER,
        textColor=colors.HexColor('#1a5276')
    )
    
    heading1_style = ParagraphStyle(
        'CustomH1',
        parent=styles['Heading1'],
        fontSize=18,
        spaceBefore=20,
        spaceAfter=12,
        textColor=colors.HexColor('#2874a6')
    )
    
    heading2_style = ParagraphStyle(
        'CustomH2',
        parent=styles['Heading2'],
        fontSize=14,
        spaceBefore=15,
        spaceAfter=8,
        textColor=colors.HexColor('#2e86ab')
    )
    
    body_style = ParagraphStyle(
        'CustomBody',
        parent=styles['Normal'],
        fontSize=11,
        spaceAfter=8,
        alignment=TA_JUSTIFY,
        leading=14
    )
    
    code_style = ParagraphStyle(
        'CodeStyle',
        parent=styles['Code'],
        fontSize=9,
        backColor=colors.HexColor('#f4f4f4'),
        borderColor=colors.HexColor('#cccccc'),
        borderWidth=1,
        borderPadding=5,
        leftIndent=20,
        spaceAfter=10
    )
    
    # Build content
    story = []
    
    # Title Page
    story.append(Spacer(1, 2*inch))
    story.append(Paragraph("Stock Ranking System", title_style))
    story.append(Paragraph("Complete Technical Documentation", styles['Heading2']))
    story.append(Spacer(1, 0.5*inch))
    story.append(Paragraph(f"Generated: {datetime.now().strftime('%B %d, %Y')}", styles['Normal']))
    story.append(Spacer(1, 1*inch))
    
    # Overview table
    overview_data = [
        ['Score', 'Range', 'Weight', 'Purpose'],
        ['RS Rating', '1-99', '25%', 'Relative strength vs market'],
        ['Momentum Score', '0-100', '25%', 'Price momentum across timeframes'],
        ['Trend Template', '0-8', '25%', "Mark Minervini's trend criteria"],
        ['Technical Score', '0-100', '25%', 'Technical indicator health'],
        ['Composite Score', '0-100', '-', 'Weighted average of above'],
    ]
    
    overview_table = Table(overview_data, colWidths=[1.5*inch, 0.8*inch, 0.7*inch, 2.5*inch])
    overview_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2874a6')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 11),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#f8f9fa')),
        ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#dee2e6')),
        ('FONTSIZE', (0, 1), (-1, -1), 10),
        ('TOPPADDING', (0, 1), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 8),
    ]))
    story.append(overview_table)
    
    story.append(PageBreak())
    
    # ===========================================
    # Section 1: RS Rating
    # ===========================================
    story.append(Paragraph("1. RS Rating (Relative Strength Rating)", heading1_style))
    
    story.append(Paragraph("<b>Purpose:</b> Measures how well a stock has performed relative to ALL other stocks in the universe over the past 12 months.", body_style))
    
    story.append(Paragraph("<b>Range:</b> 1 to 99 (percentile ranking)", body_style))
    
    story.append(Paragraph("Calculation Method:", heading2_style))
    
    rs_steps = [
        "Calculate 12-month price return for each stock",
        "Rank all stocks by their 12-month return (best to worst)",
        "Convert rank to percentile scale (1-99)"
    ]
    story.append(ListFlowable([ListItem(Paragraph(s, body_style)) for s in rs_steps], bulletType='1'))
    
    story.append(Paragraph("Formula:", heading2_style))
    story.append(Paragraph(
        "12-Month Return = ((Current Price - Price 12 months ago) / Price 12 months ago) × 100",
        code_style
    ))
    story.append(Paragraph(
        "RS Rating = (Stock's Rank / Total Stocks) × 99",
        code_style
    ))
    
    story.append(Paragraph("Interpretation:", heading2_style))
    rs_interpret = [
        ['RS Rating', 'Meaning'],
        ['99', 'Top 1% performer - Stock outperformed 99% of all stocks'],
        ['90', 'Top 10% performer - Excellent relative strength'],
        ['70', 'Top 30% performer - Good relative strength'],
        ['50', 'Median performer - Average'],
        ['30', 'Bottom 30% - Weak relative strength'],
        ['1', 'Bottom 1% - Worst performers'],
    ]
    rs_table = Table(rs_interpret, colWidths=[1*inch, 4.5*inch])
    rs_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#27ae60')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#dee2e6')),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#f8f9fa')),
    ]))
    story.append(rs_table)
    
    story.append(Paragraph("Example:", heading2_style))
    story.append(Paragraph(
        "If Stock A gained +45% in 12 months and ranks 50th out of 500 stocks, its RS Rating = (50/500) × 99 = 90",
        body_style
    ))
    
    story.append(PageBreak())
    
    # ===========================================
    # Section 2: Momentum Score
    # ===========================================
    story.append(Paragraph("2. Momentum Score", heading1_style))
    
    story.append(Paragraph("<b>Purpose:</b> Measures price momentum across multiple timeframes, giving more weight to medium-term performance while still considering short and long-term trends.", body_style))
    
    story.append(Paragraph("<b>Range:</b> 0 to 100 (normalized percentile)", body_style))
    
    story.append(Paragraph("Timeframes and Weights:", heading2_style))
    
    momentum_weights = [
        ['Timeframe', 'Trading Days', 'Weight', 'Rationale'],
        ['1 Week', '5 days', '5%', 'Short-term noise filter'],
        ['1 Month', '21 days', '15%', 'Recent momentum'],
        ['3 Months', '63 days', '30%', 'Primary momentum signal'],
        ['6 Months', '126 days', '30%', 'Primary momentum signal'],
        ['12 Months', '252 days', '20%', 'Long-term trend confirmation'],
    ]
    momentum_table = Table(momentum_weights, colWidths=[1*inch, 1*inch, 0.8*inch, 2.7*inch])
    momentum_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#e67e22')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#dee2e6')),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#fef9e7')),
    ]))
    story.append(momentum_table)
    
    story.append(Paragraph("Formula:", heading2_style))
    story.append(Paragraph(
        "Raw Score = (1W_return × 0.05) + (1M_return × 0.15) + (3M_return × 0.30) + (6M_return × 0.30) + (12M_return × 0.20)",
        code_style
    ))
    story.append(Paragraph(
        "Momentum Score = Percentile rank of Raw Score among all stocks (0-100)",
        code_style
    ))
    
    story.append(Paragraph("Example Calculation:", heading2_style))
    example_data = [
        ['Timeframe', 'Return', 'Weight', 'Contribution'],
        ['1 Week', '+2%', '× 0.05', '= 0.10'],
        ['1 Month', '+8%', '× 0.15', '= 1.20'],
        ['3 Months', '+15%', '× 0.30', '= 4.50'],
        ['6 Months', '+25%', '× 0.30', '= 7.50'],
        ['12 Months', '+40%', '× 0.20', '= 8.00'],
        ['Raw Score', '', '', '= 21.30'],
    ]
    example_table = Table(example_data, colWidths=[1.2*inch, 0.8*inch, 0.8*inch, 1.2*inch])
    example_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3498db')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#dee2e6')),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#d4edda')),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
    ]))
    story.append(example_table)
    
    story.append(Paragraph("If this raw score of 21.30 ranks in the top 15% of all stocks, Momentum Score = 85", body_style))
    
    story.append(PageBreak())
    
    # ===========================================
    # Section 3: Trend Template
    # ===========================================
    story.append(Paragraph("3. Trend Template Score (Minervini Criteria)", heading1_style))
    
    story.append(Paragraph("<b>Purpose:</b> Evaluates whether a stock is in a proper Stage 2 uptrend, based on Mark Minervini's 8-point checklist from 'Trade Like a Stock Market Wizard'.", body_style))
    
    story.append(Paragraph("<b>Range:</b> 0 to 8 (count of criteria met)", body_style))
    
    story.append(Paragraph("The 8 Criteria:", heading2_style))
    
    criteria_data = [
        ['#', 'Condition', 'What It Checks'],
        ['1', 'Price > 150-day SMA', 'Stock is above medium-term average'],
        ['2', 'Price > 200-day SMA', 'Stock is above long-term average'],
        ['3', '150-day SMA > 200-day SMA', 'Medium-term trend stronger than long-term'],
        ['4', '200-day SMA trending UP', 'Long-term trend is rising (checked over 30 days)'],
        ['5', '50-day SMA > 150-day SMA', 'Short-term trend above medium-term'],
        ['6', '50-day SMA > 200-day SMA', 'Short-term trend above long-term'],
        ['7', 'Price > 50-day SMA', 'Stock is above short-term average'],
        ['8', 'Price within 25% of 52-week high\nAND 30%+ above 52-week low', 'Near highs, far from lows'],
    ]
    criteria_table = Table(criteria_data, colWidths=[0.4*inch, 2*inch, 3.1*inch])
    criteria_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#9b59b6')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#dee2e6')),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#f5eef8')),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    story.append(criteria_table)
    
    story.append(Paragraph("Score Interpretation:", heading2_style))
    score_interpret = [
        ['Score', 'Assessment', 'Trading Implication'],
        ['8', 'Perfect Trend Template', 'Ideal breakout candidate - Stage 2 uptrend'],
        ['6-7', 'Strong Uptrend', 'Good candidate for momentum trading'],
        ['4-5', 'Moderate Trend', 'Developing - watch for improvement'],
        ['2-3', 'Weak Trend', 'Not recommended for long positions'],
        ['0-1', 'No Uptrend', 'Avoid or consider for short positions'],
    ]
    score_table = Table(score_interpret, colWidths=[0.6*inch, 1.8*inch, 3.1*inch])
    score_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#9b59b6')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#dee2e6')),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BACKGROUND', (0, 1), (0, 1), colors.HexColor('#27ae60')),
        ('TEXTCOLOR', (0, 1), (0, 1), colors.whitesmoke),
        ('BACKGROUND', (0, 2), (0, 2), colors.HexColor('#82e0aa')),
        ('BACKGROUND', (0, 3), (0, 3), colors.HexColor('#f9e79f')),
        ('BACKGROUND', (0, 4), (0, 4), colors.HexColor('#f5b7b1')),
        ('BACKGROUND', (0, 5), (0, 5), colors.HexColor('#e74c3c')),
        ('TEXTCOLOR', (0, 5), (0, 5), colors.whitesmoke),
    ]))
    story.append(score_table)
    
    story.append(Paragraph("Visual Representation of Perfect Score (8/8):", heading2_style))
    story.append(Paragraph("""
    A stock with a perfect trend template shows:
    • Price trading near 52-week highs (within 25%)
    • Price well above all moving averages
    • Moving averages "stacked" bullishly: 50 > 150 > 200
    • All moving averages trending upward
    • Price far above 52-week lows (30%+ above)
    """, body_style))
    
    story.append(PageBreak())
    
    # ===========================================
    # Section 4: Technical Score
    # ===========================================
    story.append(Paragraph("4. Technical Score", heading1_style))
    
    story.append(Paragraph("<b>Purpose:</b> Measures overall technical health by evaluating price position relative to key moving averages and their alignment.", body_style))
    
    story.append(Paragraph("<b>Range:</b> 0 to 100", body_style))
    
    story.append(Paragraph("Components (4 × 25 points each):", heading2_style))
    
    tech_components = [
        ['Component', 'Max Points', 'Description'],
        ['Price vs 50-SMA', '25', 'Short-term position relative to 50-day average'],
        ['Price vs 150-SMA', '25', 'Medium-term position relative to 150-day average'],
        ['Price vs 200-SMA', '25', 'Long-term position relative to 200-day average'],
        ['SMA Alignment', '25', 'Bonus for bullish moving average stack'],
        ['TOTAL', '100', ''],
    ]
    tech_table = Table(tech_components, colWidths=[1.5*inch, 1*inch, 3*inch])
    tech_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#16a085')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#dee2e6')),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#d4edda')),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
    ]))
    story.append(tech_table)
    
    story.append(Paragraph("Price vs SMA Scoring Logic:", heading2_style))
    story.append(Paragraph("""
    The scoring rewards stocks that are above their moving averages but penalizes those that are too extended:
    """, body_style))
    
    scoring_logic = [
        ['Position', 'Score (out of 25)'],
        ['10-20% above SMA', '25 points (optimal zone)'],
        ['0-10% above SMA', '12.5 to 25 points (increasing)'],
        ['20%+ above SMA', '25 down to 12.5 (overextended penalty)'],
        ['0-10% below SMA', '12.5 to 0 points'],
        ['10%+ below SMA', 'Near 0 points'],
    ]
    scoring_table = Table(scoring_logic, colWidths=[2*inch, 3.5*inch])
    scoring_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#16a085')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#dee2e6')),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
    ]))
    story.append(scoring_table)
    
    story.append(Paragraph("SMA Alignment Bonus (25 points max):", heading2_style))
    alignment_data = [
        ['Condition', 'Points'],
        ['50-day SMA > 150-day SMA', '+10 points (40%)'],
        ['150-day SMA > 200-day SMA', '+10 points (40%)'],
        ['50-day SMA > 200-day SMA', '+5 points (20%)'],
    ]
    align_table = Table(alignment_data, colWidths=[2.5*inch, 2*inch])
    align_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#16a085')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#dee2e6')),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
    ]))
    story.append(align_table)
    
    story.append(PageBreak())
    
    # ===========================================
    # Section 5: Composite Score
    # ===========================================
    story.append(Paragraph("5. Composite Score (Final Rating)", heading1_style))
    
    story.append(Paragraph("<b>Purpose:</b> Combines all four individual scores into a single comprehensive ranking number that captures relative strength, momentum, trend quality, and technical position.", body_style))
    
    story.append(Paragraph("<b>Range:</b> 0 to 100", body_style))
    
    story.append(Paragraph("Step 1: Normalize All Scores to 0-100", heading2_style))
    
    normalize_data = [
        ['Score', 'Original Range', 'Normalization'],
        ['RS Rating', '1-99', 'Use as-is (already 0-100 scale)'],
        ['Momentum Score', '0-100', 'Use as-is'],
        ['Trend Template', '0-8', '(Score ÷ 8) × 100'],
        ['Technical Score', '0-100', 'Use as-is'],
    ]
    norm_table = Table(normalize_data, colWidths=[1.5*inch, 1.2*inch, 2.8*inch])
    norm_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#c0392b')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#dee2e6')),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
    ]))
    story.append(norm_table)
    
    story.append(Paragraph("Step 2: Apply Equal Weights", heading2_style))
    story.append(Paragraph(
        "Composite = (RS × 0.25) + (Momentum × 0.25) + (Trend Template × 0.25) + (Technical × 0.25)",
        code_style
    ))
    
    story.append(Paragraph("Step 3: Rank All Stocks", heading2_style))
    story.append(Paragraph("Stocks are ranked by Composite Score from highest to lowest. Percentile is calculated based on rank.", body_style))
    
    story.append(Paragraph("Complete Example:", heading2_style))
    
    example_calc = [
        ['Score', 'Raw Value', 'Normalized', 'Weight', 'Contribution'],
        ['RS Rating', '85', '85', '× 0.25', '= 21.25'],
        ['Momentum', '72', '72', '× 0.25', '= 18.00'],
        ['Trend Template', '7/8', '87.5', '× 0.25', '= 21.88'],
        ['Technical', '68', '68', '× 0.25', '= 17.00'],
        ['COMPOSITE', '', '', '', '= 78.13'],
    ]
    example_calc_table = Table(example_calc, colWidths=[1.3*inch, 0.8*inch, 0.9*inch, 0.7*inch, 1*inch])
    example_calc_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#c0392b')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#dee2e6')),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#f5b7b1')),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
    ]))
    story.append(example_calc_table)
    
    story.append(Spacer(1, 0.3*inch))
    story.append(Paragraph("Composite Score Interpretation:", heading2_style))
    
    interpret_data = [
        ['Range', 'Assessment', 'Action'],
        ['90-100', 'Exceptional', 'Top-tier market leader - Prime buy candidate'],
        ['75-90', 'Strong', 'Quality stock - Good for breakout trades'],
        ['50-75', 'Average', 'Watch but don\'t chase - Wait for improvement'],
        ['25-50', 'Weak', 'Avoid for long positions'],
        ['0-25', 'Very Weak', 'Avoid or consider for short positions'],
    ]
    interpret_table = Table(interpret_data, colWidths=[1*inch, 1.2*inch, 3.3*inch])
    interpret_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2c3e50')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#dee2e6')),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BACKGROUND', (0, 1), (-1, 1), colors.HexColor('#27ae60')),
        ('TEXTCOLOR', (0, 1), (-1, 1), colors.whitesmoke),
        ('BACKGROUND', (0, 2), (-1, 2), colors.HexColor('#82e0aa')),
        ('BACKGROUND', (0, 3), (-1, 3), colors.HexColor('#f9e79f')),
        ('BACKGROUND', (0, 4), (-1, 4), colors.HexColor('#f5b7b1')),
        ('BACKGROUND', (0, 5), (-1, 5), colors.HexColor('#e74c3c')),
        ('TEXTCOLOR', (0, 5), (-1, 5), colors.whitesmoke),
    ]))
    story.append(interpret_table)
    
    story.append(PageBreak())
    
    # ===========================================
    # Summary Page
    # ===========================================
    story.append(Paragraph("Summary: How Scores Work Together", heading1_style))
    
    story.append(Paragraph("""
    The four component scores capture different aspects of stock quality:
    """, body_style))
    
    summary_bullets = [
        "<b>RS Rating</b> - Answers: 'Is this stock outperforming the market?' A stock with RS 90+ is beating 90% of all stocks.",
        "<b>Momentum Score</b> - Answers: 'Is the price momentum accelerating?' Weighs recent vs. long-term gains.",
        "<b>Trend Template</b> - Answers: 'Is the stock in a proper Stage 2 uptrend?' Uses Minervini's proven criteria.",
        "<b>Technical Score</b> - Answers: 'Is the stock in a healthy technical position?' Not too extended, proper MA alignment.",
    ]
    for bullet in summary_bullets:
        story.append(Paragraph(f"• {bullet}", body_style))
    
    story.append(Spacer(1, 0.3*inch))
    story.append(Paragraph("Why Equal Weights?", heading2_style))
    story.append(Paragraph("""
    The 25% equal weighting ensures no single factor dominates. A stock needs to be strong across multiple dimensions to rank highly. This prevents:
    """, body_style))
    
    prevent_bullets = [
        "A stock with great momentum but poor trend structure from ranking too high",
        "A stock with high RS but overextended technicals from ranking too high",
        "A one-dimensional strength from masking weaknesses",
    ]
    for bullet in prevent_bullets:
        story.append(Paragraph(f"• {bullet}", body_style))
    
    story.append(Spacer(1, 0.3*inch))
    story.append(Paragraph("Best Practices for Using Rankings:", heading2_style))
    
    practices = [
        "Focus on stocks with Composite Score > 75 for long positions",
        "Use Trend Template = 8 as a filter for breakout candidates",
        "Combine with volume analysis for confirmation",
        "Re-calculate daily after market close for fresh rankings",
        "Compare a stock's current rank to its historical rank for trend changes",
    ]
    story.append(ListFlowable([ListItem(Paragraph(p, body_style)) for p in practices], bulletType='bullet'))
    
    # Build PDF
    doc.build(story)
    
    print(f"✓ PDF created: {output_path}")
    return output_path


if __name__ == "__main__":
    create_stock_ratings_pdf()
