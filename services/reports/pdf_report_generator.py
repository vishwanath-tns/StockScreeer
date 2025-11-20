"""
PDF Report Generator for Nifty 500 Momentum Analysis
===================================================

Generates professional PDF reports with top gainers/losers analysis
across multiple timeframes with customizable options.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import pandas as pd
import numpy as np
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional, Tuple
import logging
from pathlib import Path

# PDF generation imports
try:
    from reportlab.lib.pagesizes import letter, A4
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
    from reportlab.platypus import Image as RLImage
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
    REPORTLAB_AVAILABLE = True
except ImportError:
    print("ReportLab not available. Install with: pip install reportlab")
    REPORTLAB_AVAILABLE = False

# Database imports
try:
    from services.market_breadth_service import get_engine as get_database_engine
except ImportError:
    try:
        from db.connection import ensure_engine as get_database_engine
    except ImportError:
        print("Warning: Could not import database connection")
        get_database_engine = None

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PDFReportGenerator:
    """
    Generates professional PDF reports for momentum analysis
    """
    
    def __init__(self):
        self.engine = get_database_engine() if get_database_engine else None
        self.durations = ['12M', '9M', '6M', '3M', '1M', '1W']  # Higher TF first
        self.duration_names = {
            '1W': 'One Week',
            '1M': 'One Month', 
            '3M': 'Three Months',
            '6M': 'Six Months',
            '9M': 'Nine Months',
            '12M': 'Twelve Months'
        }
        
    def get_momentum_data(self, duration_filter: List[str] = None, 
                         sector_filter: List[str] = None) -> pd.DataFrame:
        """Get momentum data with optional filters"""
        try:
            # Base query with indices join for sector filtering
            if sector_filter:
                # When filtering by sectors, use the join with indices
                query = """
                SELECT DISTINCT
                    m.symbol,
                    m.duration_type as duration,
                    m.percentage_change as momentum_pct,
                    CASE 
                        WHEN m.percentage_change > 0 THEN 'UP'
                        WHEN m.percentage_change < 0 THEN 'DOWN' 
                        ELSE 'FLAT'
                    END as trend_direction,
                    m.calculation_date,
                    m.end_price as close_price,
                    m.end_date as trade_date,
                    ni.index_name as sector,
                    'Unknown' as industry
                FROM momentum_analysis m
                INNER JOIN nse_index_constituents nic ON m.symbol = nic.symbol
                INNER JOIN nse_indices ni ON nic.index_id = ni.id
                WHERE m.calculation_date >= %s
                AND ni.index_name IN ({})
                """.format(','.join(['%s'] * len(sector_filter)))
                
                params = [datetime.now() - timedelta(days=1)] + sector_filter
            else:
                # When not filtering by sectors, use simple query without joins
                query = """
                SELECT 
                    m.symbol,
                    m.duration_type as duration,
                    m.percentage_change as momentum_pct,
                    CASE 
                        WHEN m.percentage_change > 0 THEN 'UP'
                        WHEN m.percentage_change < 0 THEN 'DOWN' 
                        ELSE 'FLAT'
                    END as trend_direction,
                    m.calculation_date,
                    m.end_price as close_price,
                    m.end_date as trade_date,
                    'All Stocks' as sector,
                    'Unknown' as industry
                FROM momentum_analysis m
                WHERE m.calculation_date >= %s
                """
                
                params = [datetime.now() - timedelta(days=1)]
            
            # Add duration filter
            if duration_filter:
                placeholders = ','.join(['%s'] * len(duration_filter))
                query += f" AND m.duration_type IN ({placeholders})"
                params.extend(duration_filter)
            
            query += " ORDER BY m.duration_type, m.percentage_change DESC"
            
            with self.engine.connect() as conn:
                df = pd.read_sql(query, conn, params=tuple(params))
                
            # Remove any duplicates that might still exist (same symbol-duration)
            df = df.drop_duplicates(subset=['symbol', 'duration'], keep='first')
                
            return df
            
        except Exception as e:
            logger.error(f"Error fetching momentum data: {e}")
            return pd.DataFrame()
    
    def get_available_sectors(self) -> List[str]:
        """Get list of available indices/sectors"""
        try:
            query = """
            SELECT DISTINCT index_name
            FROM nse_indices 
            WHERE is_active = 1
            ORDER BY index_name
            """
            
            with self.engine.connect() as conn:
                df = pd.read_sql(query, conn)
                
            return df['index_name'].tolist()
            
        except Exception as e:
            logger.error(f"Error fetching indices: {e}")
            return []
    
    def generate_top_performers_report(self, 
                                     output_path: str,
                                     top_n: int = 10,
                                     duration_filter: List[str] = None,
                                     sector_filter: List[str] = None,
                                     include_charts: bool = True) -> bool:
        """
        Generate PDF report with top gainers and losers
        """
        if not REPORTLAB_AVAILABLE:
            logger.error("ReportLab not available for PDF generation")
            return False
            
        try:
            # Get data
            df = self.get_momentum_data(duration_filter, sector_filter)
            if df.empty:
                logger.error("No momentum data found")
                return False
            
            # Create PDF document
            doc = SimpleDocTemplate(output_path, pagesize=A4)
            story = []
            
            # Get styles
            styles = getSampleStyleSheet()
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Heading1'],
                fontSize=18,
                spaceAfter=30,
                alignment=TA_CENTER,
                textColor=colors.darkblue
            )
            
            heading_style = ParagraphStyle(
                'CustomHeading',
                parent=styles['Heading2'],
                fontSize=14,
                spaceAfter=15,
                textColor=colors.darkgreen
            )
            
            # Title page
            story.append(Paragraph("Nifty 500 Momentum Analysis Report", title_style))
            story.append(Spacer(1, 20))
            
            # Report metadata
            report_info = [
                f"Generated: {datetime.now().strftime('%B %d, %Y at %I:%M %p')}",
                f"Analysis Period: {', '.join(duration_filter) if duration_filter else 'All Durations'}",
                f"Sectors: {', '.join(sector_filter) if sector_filter else 'All Sectors'}",
                f"Top Performers: {top_n} gainers and {top_n} losers per duration"
            ]
            
            for info in report_info:
                story.append(Paragraph(info, styles['Normal']))
            
            story.append(Spacer(1, 30))
            
            # Executive Summary
            summary_data = self._generate_summary_stats(df)
            story.append(Paragraph("Executive Summary", heading_style))
            
            summary_table_data = [
                ['Metric', 'Value'],
                ['Total Stocks Analyzed', str(len(df['symbol'].unique()))],
                ['Total Records', str(len(df))],
                ['Durations Covered', str(len(df['duration'].unique()))],
                ['Date Range', f"{df['calculation_date'].min().strftime('%Y-%m-%d')} to {df['calculation_date'].max().strftime('%Y-%m-%d')}"]
            ]
            
            summary_table = Table(summary_table_data)
            summary_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            
            story.append(summary_table)
            story.append(PageBreak())
            
            # Generate reports for each duration (higher TF first)
            durations_to_process = duration_filter if duration_filter else self.durations
            
            for duration in durations_to_process:
                duration_data = df[df['duration'] == duration].copy()
                if duration_data.empty:
                    continue
                    
                story.extend(self._create_duration_section(duration, duration_data, top_n, styles))
                story.append(PageBreak())
            
            # Cross-duration analysis
            story.extend(self._create_cross_duration_analysis(df, styles, top_n))
            
            # Build PDF
            doc.build(story)
            logger.info(f"PDF report generated successfully: {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error generating PDF report: {e}")
            return False
    
    def _generate_summary_stats(self, df: pd.DataFrame) -> Dict:
        """Generate summary statistics for the report"""
        summary = {}
        
        for duration in df['duration'].unique():
            duration_data = df[df['duration'] == duration]['momentum_pct']
            summary[duration] = {
                'avg': duration_data.mean(),
                'median': duration_data.median(),
                'positive_count': (duration_data > 0).sum(),
                'negative_count': (duration_data < 0).sum(),
                'max': duration_data.max(),
                'min': duration_data.min()
            }
        
        return summary
    
    def _create_duration_section(self, duration: str, data: pd.DataFrame, 
                               top_n: int, styles) -> List:
        """Create a section for a specific duration"""
        section = []
        
        # Duration header
        duration_title = f"{self.duration_names.get(duration, duration)} Momentum Analysis"
        section.append(Paragraph(duration_title, styles['Heading1']))
        section.append(Spacer(1, 15))
        
        # Statistics summary
        stats_data = data['momentum_pct']
        avg_momentum = stats_data.mean()
        median_momentum = stats_data.median()
        positive_count = (stats_data > 0).sum()
        total_count = len(stats_data)
        
        stats_text = f"""
        Average Momentum: {avg_momentum:+.2f}%<br/>
        Median Momentum: {median_momentum:+.2f}%<br/>
        Positive Stocks: {positive_count}/{total_count} ({100*positive_count/total_count:.1f}%)<br/>
        Range: {stats_data.min():+.2f}% to {stats_data.max():+.2f}%
        """
        
        section.append(Paragraph(stats_text, styles['Normal']))
        section.append(Spacer(1, 20))
        
        # Top gainers
        top_gainers = data.nlargest(top_n, 'momentum_pct')
        section.append(Paragraph(f"Top {top_n} Gainers", styles['Heading2']))
        section.append(self._create_performance_table(top_gainers, is_gainers=True))
        section.append(Spacer(1, 20))
        
        # Top losers
        top_losers = data.nsmallest(top_n, 'momentum_pct')
        section.append(Paragraph(f"Top {top_n} Losers", styles['Heading2']))
        section.append(self._create_performance_table(top_losers, is_gainers=False))
        
        return section
    
    def _create_performance_table(self, data: pd.DataFrame, is_gainers: bool) -> Table:
        """Create a formatted table for top performers"""
        
        # Prepare table data
        table_data = [['Rank', 'Symbol', 'Momentum %', 'Price (Rs.)', 'Sector']]
        
        for idx, (_, row) in enumerate(data.iterrows(), 1):
            momentum_str = f"{row['momentum_pct']:+.2f}%"
            price_str = f"{row['close_price']:.2f}" if pd.notna(row['close_price']) else "N/A"
            sector_str = str(row['sector']) if pd.notna(row['sector']) else "Unknown"
            
            table_data.append([
                str(idx),
                str(row['symbol']),
                momentum_str,
                price_str,
                sector_str
            ])
        
        # Create table
        table = Table(table_data)
        
        # Color scheme
        header_color = colors.darkgreen if is_gainers else colors.darkred
        row_color = colors.lightgreen if is_gainers else colors.lightpink
        
        # Apply styling
        table.setStyle(TableStyle([
            # Header styling
            ('BACKGROUND', (0, 0), (-1, 0), header_color),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            
            # Data rows
            ('BACKGROUND', (0, 1), (-1, -1), row_color),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            
            # Align momentum column to right
            ('ALIGN', (2, 1), (2, -1), 'RIGHT'),
            ('ALIGN', (3, 1), (3, -1), 'RIGHT'),
        ]))
        
        return table
    
    def _create_cross_duration_analysis(self, df: pd.DataFrame, styles, top_n: int) -> List:
        """Create cross-duration analysis section"""
        section = []
        
        section.append(Paragraph("Cross-Duration Analysis", styles['Heading1']))
        section.append(Spacer(1, 15))
        
        # Find consistent performers across timeframes
        pivot_df = df.pivot(index='symbol', columns='duration', values='momentum_pct')
        
        # Multi-timeframe winners (positive in multiple periods)
        multi_positive = pivot_df[(pivot_df > 0).sum(axis=1) >= 3].copy()
        
        if not multi_positive.empty:
            multi_positive['positive_count'] = (multi_positive > 0).sum(axis=1)
            multi_positive['avg_momentum'] = multi_positive.mean(axis=1, skipna=True)
            multi_positive = multi_positive.sort_values('avg_momentum', ascending=False).head(min(top_n, 20))
            
            section.append(Paragraph("Consistent Multi-Timeframe Winners", styles['Heading2']))
            section.append(Paragraph("Stocks showing positive momentum in 3 or more timeframes", styles['Normal']))
            section.append(Spacer(1, 10))
            
            # Create table for consistent winners
            winner_table_data = [['Symbol', 'Positive TFs', 'Avg Momentum %'] + list(pivot_df.columns)]
            
            for symbol, row in multi_positive.iterrows():
                row_data = [
                    str(symbol),
                    str(int(row['positive_count'])),
                    f"{row['avg_momentum']:+.2f}%"
                ]
                
                # Add individual momentum values
                for duration in pivot_df.columns:
                    value = row[duration]
                    if pd.notna(value):
                        row_data.append(f"{value:+.2f}%")
                    else:
                        row_data.append("N/A")
                
                winner_table_data.append(row_data)
            
            winner_table = Table(winner_table_data)
            winner_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.darkgreen),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 9),
                ('FONTSIZE', (0, 1), (-1, -1), 8),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('BACKGROUND', (0, 1), (-1, -1), colors.lightgreen),
            ]))
            
            section.append(winner_table)
            section.append(Spacer(1, 20))
        
        # Sector analysis
        if 'sector' in df.columns:
            sector_analysis = df.groupby(['sector', 'duration'])['momentum_pct'].agg(['mean', 'count']).reset_index()
            top_sectors = sector_analysis.groupby('sector')['mean'].mean().sort_values(ascending=False).head(5)
            
            section.append(Paragraph("Top Performing Sectors", styles['Heading2']))
            
            sector_table_data = [['Rank', 'Sector', 'Average Momentum %']]
            for idx, (sector, avg_momentum) in enumerate(top_sectors.items(), 1):
                sector_table_data.append([
                    str(idx),
                    str(sector),
                    f"{avg_momentum:+.2f}%"
                ])
            
            sector_table = Table(sector_table_data)
            sector_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('BACKGROUND', (0, 1), (-1, -1), colors.lightblue),
            ]))
            
            section.append(sector_table)
        
        return section

def main():
    """Test the PDF generator"""
    generator = PDFReportGenerator()
    
    # Generate a sample report
    output_path = f"nifty500_momentum_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    
    success = generator.generate_top_performers_report(
        output_path=output_path,
        top_n=20,
        duration_filter=None,  # All durations
        sector_filter=None,    # All sectors
        include_charts=True
    )
    
    if success:
        print(f"[SUCCESS] PDF report generated: {output_path}")
    else:
        print("[ERROR] Failed to generate PDF report")

if __name__ == "__main__":
    main()