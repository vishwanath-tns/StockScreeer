#!/usr/bin/env python3
"""
Sectoral Trends PDF Report Generator
==================================

Generates comprehensive PDF reports with multiple charts showing sectoral trends analysis,
90-day historical data, performance rankings, and sector predictions.
"""

import sys
import os
from datetime import datetime, date, timedelta
from typing import Dict, List, Tuple, Optional
import pandas as pd
import numpy as np
from io import BytesIO
import logging

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    import matplotlib
    matplotlib.use('Agg')  # Use non-interactive backend for PDF generation
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    from matplotlib.backends.backend_pdf import PdfPages
    import seaborn as sns
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False

try:
    from reportlab.lib.pagesizes import letter, A4
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak, Image
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False

from services.sectoral_trends_service import SectoralTrendsService

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SectoralTrendsPDFGenerator:
    """Generator for comprehensive sectoral trends PDF reports."""
    
    def __init__(self):
        self.service = SectoralTrendsService()
        self.styles = getSampleStyleSheet() if REPORTLAB_AVAILABLE else None
        self._setup_custom_styles()
    
    def _setup_custom_styles(self):
        """Setup custom paragraph styles for the report."""
        if not REPORTLAB_AVAILABLE:
            return
        
        # Title style
        self.title_style = ParagraphStyle(
            'CustomTitle',
            parent=self.styles['Title'],
            fontSize=24,
            textColor=colors.darkblue,
            alignment=TA_CENTER,
            spaceAfter=30
        )
        
        # Heading style
        self.heading_style = ParagraphStyle(
            'CustomHeading',
            parent=self.styles['Heading1'],
            fontSize=16,
            textColor=colors.darkgreen,
            spaceBefore=20,
            spaceAfter=10
        )
        
        # Subheading style
        self.subheading_style = ParagraphStyle(
            'CustomSubHeading',
            parent=self.styles['Heading2'],
            fontSize=14,
            textColor=colors.black,
            spaceBefore=15,
            spaceAfter=8
        )
        
        # Analysis style
        self.analysis_style = ParagraphStyle(
            'Analysis',
            parent=self.styles['Normal'],
            fontSize=11,
            textColor=colors.black,
            spaceBefore=5,
            spaceAfter=5,
            leftIndent=10
        )
        
        # Prediction style
        self.prediction_style = ParagraphStyle(
            'Prediction',
            parent=self.styles['Normal'],
            fontSize=12,
            textColor=colors.darkred,
            spaceBefore=10,
            spaceAfter=5,
            leftIndent=20
        )
    
    def generate_sectoral_trends_report(self, filename: Optional[str] = None, days_back: int = 90) -> Tuple[bool, str]:
        """
        Generate comprehensive sectoral trends PDF report.
        
        Args:
            filename: Output filename (auto-generated if None)
            days_back: Number of days of historical data to include
            
        Returns:
            Tuple of (success, result_message)
        """
        if not REPORTLAB_AVAILABLE or not MATPLOTLIB_AVAILABLE:
            return False, "Required libraries (reportlab, matplotlib) not available"
        
        try:
            # Generate filename if not provided
            if filename is None:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"sectoral_trends_report_{timestamp}.pdf"
            
            # Ensure charts directory exists
            os.makedirs("charts", exist_ok=True)
            filepath = os.path.join("charts", filename)
            
            # Get data
            logger.info(f"📊 Generating sectoral trends report for last {days_back} days...")
            
            # Load all sectoral data
            all_data = self.service.get_trends_data(sectors=None, days_back=days_back)
            
            if all_data.empty:
                return False, f"No sectoral trends data available for the last {days_back} days"
            
            # Analyze data
            analysis_results = self._analyze_sectoral_trends(all_data)
            
            # Generate charts
            chart_paths = self._generate_charts(all_data, days_back)
            
            # Create PDF document
            doc = SimpleDocTemplate(filepath, pagesize=A4)
            story = []
            
            # Build report content
            self._add_title_page(story, days_back, analysis_results)
            self._add_executive_summary(story, analysis_results)
            self._add_charts_section(story, chart_paths)
            self._add_sector_rankings(story, analysis_results)
            self._add_trend_analysis(story, analysis_results)
            self._add_predictions(story, analysis_results)
            self._add_appendix(story, analysis_results)
            
            # Build PDF
            doc.build(story)
            
            # Cleanup chart files
            self._cleanup_charts(chart_paths)
            
            logger.info(f"✅ Sectoral trends report generated: {filepath}")
            return True, f"Sectoral trends report saved: {filepath}"
            
        except Exception as e:
            logger.error(f"Failed to generate sectoral trends report: {e}")
            return False, f"Error generating report: {str(e)}"
    
    def _analyze_sectoral_trends(self, data: pd.DataFrame) -> Dict:
        """Analyze sectoral trends data and generate insights."""
        analysis = {}
        
        # Convert analysis_date to datetime for calculations
        data = data.copy()  # Work with a copy to avoid modifying original
        data['date'] = pd.to_datetime(data['analysis_date'])
        
        # Ensure all numeric columns are properly converted from Decimal to float
        numeric_columns = ['bullish_percent', 'bearish_percent', 'daily_uptrend_percent', 
                          'weekly_uptrend_percent', 'avg_trend_rating']
        for col in numeric_columns:
            if col in data.columns:
                # Convert Decimal objects to float
                data[col] = data[col].apply(lambda x: float(x) if x is not None else 0.0)
        
        # Basic statistics
        analysis['total_records'] = len(data)
        analysis['sectors_count'] = data['sector_code'].nunique()
        analysis['date_range'] = {
            'start': data['date'].min().date(),
            'end': data['date'].max().date(),
            'days': (data['date'].max() - data['date'].min()).days + 1
        }
        
        # Sector performance analysis
        latest_data = data[data['date'] == data['date'].max()].copy()
        earliest_data = data[data['date'] == data['date'].min()].copy()
        
        # Current sector standings
        if len(latest_data) > 0:
            current_performance = latest_data.sort_values('bullish_percent', ascending=False)
            analysis['top_bullish_sectors'] = current_performance[['sector_name', 'bullish_percent', 'bearish_percent']].head(5).to_dict('records')
            analysis['top_bearish_sectors'] = current_performance.sort_values('bearish_percent', ascending=False)[['sector_name', 'bullish_percent', 'bearish_percent']].head(5).to_dict('records')
        else:
            analysis['top_bullish_sectors'] = []
            analysis['top_bearish_sectors'] = []
        
        # Trend momentum analysis
        sector_momentum = []
        for sector in data['sector_code'].unique():
            sector_data = data[data['sector_code'] == sector].sort_values('date')
            if len(sector_data) >= 10:  # Need enough data points
                try:
                    # Convert Decimal objects to float for calculations
                    bullish_values = sector_data['bullish_percent'].apply(lambda x: float(x) if x is not None else 0.0)
                    weekly_values = sector_data['weekly_uptrend_percent'].apply(lambda x: float(x) if x is not None else 0.0)
                    
                    recent_trend = bullish_values.tail(10).mean()
                    earlier_trend = bullish_values.head(10).mean()
                    momentum = recent_trend - earlier_trend
                    
                    # Weekly uptrend momentum
                    recent_weekly = weekly_values.tail(10).mean()
                    earlier_weekly = weekly_values.head(10).mean()
                    weekly_momentum = recent_weekly - earlier_weekly
                    
                    sector_momentum.append({
                        'sector_code': sector,
                        'sector_name': sector_data['sector_name'].iloc[0],
                        'bullish_momentum': float(momentum) if not pd.isna(momentum) else 0.0,
                        'weekly_momentum': float(weekly_momentum) if not pd.isna(weekly_momentum) else 0.0,
                        'current_bullish': float(bullish_values.iloc[-1]) if not pd.isna(bullish_values.iloc[-1]) else 0.0,
                        'current_weekly_uptrend': float(weekly_values.iloc[-1]) if not pd.isna(weekly_values.iloc[-1]) else 0.0
                    })
                except Exception as e:
                    logger.warning(f"Error processing sector {sector} momentum: {e}")
                    continue
        
        momentum_df = pd.DataFrame(sector_momentum)
        
        # Ensure numeric columns
        numeric_columns = ['bullish_momentum', 'weekly_momentum', 'current_bullish', 'current_weekly_uptrend']
        for col in numeric_columns:
            if col in momentum_df.columns:
                momentum_df[col] = pd.to_numeric(momentum_df[col], errors='coerce').fillna(0)
        
        if len(momentum_df) > 0:
            analysis['strongest_momentum'] = momentum_df.nlargest(5, 'bullish_momentum')[['sector_name', 'bullish_momentum', 'current_bullish']].to_dict('records')
            analysis['weakest_momentum'] = momentum_df.nsmallest(5, 'bullish_momentum')[['sector_name', 'bullish_momentum', 'current_bullish']].to_dict('records')
        else:
            analysis['strongest_momentum'] = []
            analysis['weakest_momentum'] = []
        
        # Volatility analysis
        sector_volatility = []
        for sector in data['sector_code'].unique():
            sector_data = data[data['sector_code'] == sector]
            try:
                # Convert Decimal objects to float to avoid type issues
                bullish_values = sector_data['bullish_percent'].apply(lambda x: float(x) if x is not None else 0.0)
                volatility = float(bullish_values.std()) if not pd.isna(bullish_values.std()) else 0.0
                avg_bullish = float(bullish_values.mean()) if not pd.isna(bullish_values.mean()) else 0.0
                sector_volatility.append({
                    'sector_name': sector_data['sector_name'].iloc[0],
                    'volatility': volatility,
                    'avg_bullish': avg_bullish
                })
            except Exception as e:
                logger.warning(f"Error processing sector {sector} volatility: {e}")
                continue
        
        volatility_df = pd.DataFrame(sector_volatility)
        
        # Ensure numeric columns
        if len(volatility_df) > 0:
            volatility_df['volatility'] = pd.to_numeric(volatility_df['volatility'], errors='coerce').fillna(0)
            volatility_df['avg_bullish'] = pd.to_numeric(volatility_df['avg_bullish'], errors='coerce').fillna(0)
            
            analysis['most_stable'] = volatility_df.nsmallest(5, 'volatility')[['sector_name', 'volatility', 'avg_bullish']].to_dict('records')
            analysis['most_volatile'] = volatility_df.nlargest(5, 'volatility')[['sector_name', 'volatility', 'avg_bullish']].to_dict('records')
        else:
            analysis['most_stable'] = []
            analysis['most_volatile'] = []
        
        # Predictions based on trends
        analysis['predictions'] = self._generate_sector_predictions(momentum_df, volatility_df, latest_data)
        
        return analysis
    
    def _generate_sector_predictions(self, momentum_df: pd.DataFrame, volatility_df: pd.DataFrame, latest_data: pd.DataFrame) -> Dict:
        """Generate sector predictions based on trend analysis."""
        predictions = {}
        
        # Merge data for comprehensive analysis
        if len(momentum_df) > 0 and len(volatility_df) > 0 and len(latest_data) > 0:
            merged = momentum_df.merge(volatility_df, on='sector_name')
            merged = merged.merge(latest_data[['sector_name', 'bullish_percent', 'daily_uptrend_percent', 'weekly_uptrend_percent']], on='sector_name')
            
            # Ensure all values are numeric for analysis
            numeric_cols = ['bullish_percent', 'daily_uptrend_percent', 'weekly_uptrend_percent']
            for col in numeric_cols:
                if col in merged.columns:
                    merged[col] = merged[col].apply(lambda x: float(x) if x is not None else 0.0)
        else:
            merged = pd.DataFrame()  # Empty DataFrame if no data
        
        # Upcoming sectors (positive momentum + reasonable current levels)
        if len(merged) > 0:
            upcoming_criteria = (merged['bullish_momentum'] > 2) & (merged['current_bullish'] < 70) & (merged['weekly_momentum'] > 0)
            upcoming_sectors = merged[upcoming_criteria].sort_values('bullish_momentum', ascending=False)
            
            predictions['upcoming_sectors'] = upcoming_sectors[['sector_name', 'bullish_momentum', 'current_bullish', 'weekly_momentum']].head(3).to_dict('records')
            
            # Declining sectors (negative momentum)
            declining_criteria = (merged['bullish_momentum'] < -5) & (merged['weekly_momentum'] < -2)
            declining_sectors = merged[declining_criteria].sort_values('bullish_momentum')
            
            predictions['declining_sectors'] = declining_sectors[['sector_name', 'bullish_momentum', 'current_bullish', 'weekly_momentum']].head(3).to_dict('records')
            
            # Stable outperformers (high bullish % + low volatility)
            stable_criteria = (merged['current_bullish'] > 60) & (merged['volatility'] < 10)
            stable_outperformers = merged[stable_criteria].sort_values('current_bullish', ascending=False)
            
            predictions['stable_outperformers'] = stable_outperformers[['sector_name', 'current_bullish', 'volatility', 'bullish_momentum']].head(3).to_dict('records')
            
            # Recovery candidates (low current + positive momentum)
            recovery_criteria = (merged['current_bullish'] < 40) & (merged['bullish_momentum'] > 0) & (merged['weekly_momentum'] > 0)
            recovery_candidates = merged[recovery_criteria].sort_values('bullish_momentum', ascending=False)
            
            predictions['recovery_candidates'] = recovery_candidates[['sector_name', 'current_bullish', 'bullish_momentum', 'weekly_momentum']].head(3).to_dict('records')
        else:
            # No data available for predictions
            predictions['upcoming_sectors'] = []
            predictions['declining_sectors'] = []
            predictions['stable_outperformers'] = []
            predictions['recovery_candidates'] = []
        
        return predictions
    
    def _generate_charts(self, data: pd.DataFrame, days_back: int) -> List[str]:
        """Generate multiple charts for the report."""
        chart_paths = []
        
        # Set up plotting style
        try:
            plt.style.use('seaborn-v0_8-whitegrid')
        except OSError:
            # Fallback if seaborn style not available
            plt.style.use('default')
            plt.grid(True, alpha=0.3)
        colors = plt.cm.tab10(np.linspace(0, 1, 10))
        
        # Convert date column
        data['date'] = pd.to_datetime(data['analysis_date'])
        
        # Chart 1: Bullish Percentage Trends
        chart_paths.append(self._create_bullish_trends_chart(data))
        
        # Chart 2: Weekly Uptrend Comparison
        chart_paths.append(self._create_weekly_uptrend_chart(data))
        
        # Chart 3: Sector Performance Heatmap
        chart_paths.append(self._create_performance_heatmap(data))
        
        # Chart 4: Momentum Analysis
        chart_paths.append(self._create_momentum_chart(data))
        
        return chart_paths
    
    def _create_bullish_trends_chart(self, data: pd.DataFrame) -> str:
        """Create bullish percentage trends chart."""
        fig, ax = plt.subplots(figsize=(12, 8))
        
        # Plot trends for top 6 sectors
        sector_counts = data['sector_code'].value_counts()
        top_sectors = sector_counts.head(6).index
        
        colors = plt.cm.tab10(np.linspace(0, 1, len(top_sectors)))
        
        for i, sector in enumerate(top_sectors):
            sector_data = data[data['sector_code'] == sector].sort_values('date')
            sector_name = sector_data['sector_name'].iloc[0]
            ax.plot(sector_data['date'], sector_data['bullish_percent'], 
                   label=sector_name, linewidth=2, marker='o', markersize=4, color=colors[i])
        
        ax.set_title('Sectoral Bullish Percentage Trends (Top 6 Sectors)', fontsize=16, fontweight='bold', pad=20)
        ax.set_xlabel('Date', fontsize=12)
        ax.set_ylabel('Bullish %', fontsize=12)
        ax.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
        ax.grid(True, alpha=0.3)
        
        # Format dates
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d'))
        ax.xaxis.set_major_locator(mdates.WeekdayLocator(interval=1))
        plt.xticks(rotation=45)
        
        plt.tight_layout()
        
        chart_path = "charts/temp_bullish_trends.png"
        plt.savefig(chart_path, dpi=300, bbox_inches='tight')
        plt.close()
        
        return chart_path
    
    def _create_weekly_uptrend_chart(self, data: pd.DataFrame) -> str:
        """Create weekly uptrend comparison chart."""
        fig, ax = plt.subplots(figsize=(12, 8))
        
        # Get latest data for comparison
        latest_date = data['date'].max()
        latest_data = data[data['date'] == latest_date].sort_values('weekly_uptrend_percent', ascending=False)
        
        sectors = latest_data['sector_name'].head(10)
        weekly_values = latest_data['weekly_uptrend_percent'].head(10)
        daily_values = latest_data['daily_uptrend_percent'].head(10)
        
        x = np.arange(len(sectors))
        width = 0.35
        
        bars1 = ax.bar(x - width/2, weekly_values, width, label='Weekly Uptrend %', color='skyblue', alpha=0.8)
        bars2 = ax.bar(x + width/2, daily_values, width, label='Daily Uptrend %', color='lightcoral', alpha=0.8)
        
        ax.set_title('Current Sectoral Uptrend Comparison (Top 10 Sectors)', fontsize=16, fontweight='bold', pad=20)
        ax.set_xlabel('Sectors', fontsize=12)
        ax.set_ylabel('Uptrend %', fontsize=12)
        ax.set_xticks(x)
        ax.set_xticklabels(sectors, rotation=45, ha='right')
        ax.legend()
        ax.grid(True, alpha=0.3, axis='y')
        
        # Add value labels on bars
        for bar in bars1:
            height = bar.get_height()
            ax.annotate(f'{height:.1f}%', xy=(bar.get_x() + bar.get_width()/2, height),
                       xytext=(0, 3), textcoords="offset points", ha='center', va='bottom', fontsize=9)
        
        for bar in bars2:
            height = bar.get_height()
            ax.annotate(f'{height:.1f}%', xy=(bar.get_x() + bar.get_width()/2, height),
                       xytext=(0, 3), textcoords="offset points", ha='center', va='bottom', fontsize=9)
        
        plt.tight_layout()
        
        chart_path = "charts/temp_uptrend_comparison.png"
        plt.savefig(chart_path, dpi=300, bbox_inches='tight')
        plt.close()
        
        return chart_path
    
    def _create_performance_heatmap(self, data: pd.DataFrame) -> str:
        """Create sector performance heatmap."""
        # Prepare data for heatmap
        pivot_data = data.pivot_table(index='sector_name', columns='analysis_date', values='bullish_percent', aggfunc='mean')
        
        # Limit to recent dates and top sectors for readability
        recent_dates = sorted(pivot_data.columns)[-20:]  # Last 20 days
        top_sectors = pivot_data.mean(axis=1).nlargest(8).index  # Top 8 sectors
        
        heatmap_data = pivot_data.loc[top_sectors, recent_dates]
        
        fig, ax = plt.subplots(figsize=(14, 8))
        
        # Create heatmap
        sns.heatmap(heatmap_data, annot=True, fmt='.1f', cmap='RdYlGn', center=50,
                   ax=ax, cbar_kws={'label': 'Bullish %'})
        
        ax.set_title('Sector Performance Heatmap (Last 20 Days)', fontsize=16, fontweight='bold', pad=20)
        ax.set_xlabel('Date', fontsize=12)
        ax.set_ylabel('Sector', fontsize=12)
        
        # Format x-axis dates
        ax.set_xticklabels([pd.to_datetime(d).strftime('%m/%d') for d in recent_dates], rotation=45)
        
        plt.tight_layout()
        
        chart_path = "charts/temp_performance_heatmap.png"
        plt.savefig(chart_path, dpi=300, bbox_inches='tight')
        plt.close()
        
        return chart_path
    
    def _create_momentum_chart(self, data: pd.DataFrame) -> str:
        """Create momentum analysis scatter plot."""
        # Calculate momentum for each sector
        sector_momentum = []
        for sector in data['sector_code'].unique():
            sector_data = data[data['sector_code'] == sector].sort_values('date')
            if len(sector_data) >= 10:
                recent_avg = sector_data['bullish_percent'].tail(5).mean()
                earlier_avg = sector_data['bullish_percent'].head(5).mean()
                momentum = recent_avg - earlier_avg
                current_bullish = sector_data['bullish_percent'].iloc[-1]
                volatility = sector_data['bullish_percent'].std()
                
                sector_momentum.append({
                    'sector_name': sector_data['sector_name'].iloc[0],
                    'momentum': momentum,
                    'current_bullish': current_bullish,
                    'volatility': volatility
                })
        
        momentum_df = pd.DataFrame(sector_momentum)
        
        fig, ax = plt.subplots(figsize=(12, 8))
        
        # Create scatter plot
        scatter = ax.scatter(momentum_df['momentum'], momentum_df['current_bullish'],
                           s=momentum_df['volatility']*10, alpha=0.6, c=momentum_df['current_bullish'],
                           cmap='RdYlGn')
        
        # Add sector labels
        for i, row in momentum_df.iterrows():
            ax.annotate(row['sector_name'], (row['momentum'], row['current_bullish']),
                       xytext=(5, 5), textcoords='offset points', fontsize=9, alpha=0.8)
        
        ax.set_title('Sector Momentum vs Current Performance\n(Bubble size = Volatility)', 
                    fontsize=16, fontweight='bold', pad=20)
        ax.set_xlabel('Momentum (Recent vs Historical Bullish %)', fontsize=12)
        ax.set_ylabel('Current Bullish %', fontsize=12)
        ax.grid(True, alpha=0.3)
        
        # Add quadrant lines
        ax.axhline(y=50, color='gray', linestyle='--', alpha=0.5)
        ax.axvline(x=0, color='gray', linestyle='--', alpha=0.5)
        
        # Add colorbar
        cbar = plt.colorbar(scatter)
        cbar.set_label('Current Bullish %')
        
        plt.tight_layout()
        
        chart_path = "charts/temp_momentum_scatter.png"
        plt.savefig(chart_path, dpi=300, bbox_inches='tight')
        plt.close()
        
        return chart_path
    
    def _add_title_page(self, story: List, days_back: int, analysis: Dict):
        """Add title page to the report."""
        # Title
        title = Paragraph("Sectoral Trends Analysis Report", self.title_style)
        story.append(title)
        story.append(Spacer(1, 0.5*inch))
        
        # Subtitle
        subtitle = Paragraph(f"Comprehensive {days_back}-Day Market Analysis", self.subheading_style)
        story.append(subtitle)
        story.append(Spacer(1, 0.5*inch))
        
        # Report info
        report_date = datetime.now().strftime("%B %d, %Y")
        date_range = analysis['date_range']
        
        info_text = f"""
        <b>Report Generated:</b> {report_date}<br/>
        <b>Analysis Period:</b> {date_range['start']} to {date_range['end']} ({date_range['days']} days)<br/>
        <b>Sectors Analyzed:</b> {analysis['sectors_count']}<br/>
        <b>Total Data Points:</b> {analysis['total_records']}<br/>
        """
        
        info = Paragraph(info_text, self.analysis_style)
        story.append(info)
        story.append(PageBreak())
    
    def _add_executive_summary(self, story: List, analysis: Dict):
        """Add executive summary section."""
        story.append(Paragraph("Executive Summary", self.heading_style))
        
        # Key findings
        top_bullish = analysis['top_bullish_sectors'][0]
        strongest_momentum = analysis['strongest_momentum'][0] if analysis['strongest_momentum'] else {'sector_name': 'N/A'}
        
        summary_text = f"""
        This report analyzes sectoral trends across {analysis['sectors_count']} major sectors over {analysis['date_range']['days']} trading days.
        
        <b>Key Findings:</b><br/>
        • <b>Top Performing Sector:</b> {top_bullish['sector_name']} with {top_bullish['bullish_percent']:.1f}% bullish stocks<br/>
        • <b>Strongest Momentum:</b> {strongest_momentum['sector_name']} showing positive trend acceleration<br/>
        • <b>Market Breadth:</b> Analysis includes bullish/bearish percentages, uptrend momentum, and volatility metrics<br/>
        
        <b>Report Sections:</b><br/>
        1. Visual trend charts showing sector performance over time<br/>
        2. Sector rankings by various performance metrics<br/>
        3. Detailed trend analysis and momentum indicators<br/>
        4. Predictive insights for upcoming sector opportunities<br/>
        """
        
        story.append(Paragraph(summary_text, self.analysis_style))
        story.append(PageBreak())
    
    def _add_charts_section(self, story: List, chart_paths: List[str]):
        """Add charts section to the report."""
        story.append(Paragraph("Visual Trend Analysis", self.heading_style))
        
        chart_titles = [
            "Bullish Percentage Trends (Top 6 Sectors)",
            "Current Uptrend Comparison (Top 10 Sectors)", 
            "Performance Heatmap (Last 20 Days)",
            "Momentum vs Performance Analysis"
        ]
        
        for i, (chart_path, title) in enumerate(zip(chart_paths, chart_titles)):
            if os.path.exists(chart_path):
                story.append(Paragraph(f"{i+1}. {title}", self.subheading_style))
                
                # Add chart image
                img = Image(chart_path, width=7*inch, height=5*inch)
                story.append(img)
                story.append(Spacer(1, 0.3*inch))
                
                if i < len(chart_paths) - 1:
                    story.append(PageBreak())
    
    def _add_sector_rankings(self, story: List, analysis: Dict):
        """Add sector rankings section."""
        story.append(PageBreak())
        story.append(Paragraph("Sector Rankings & Performance Metrics", self.heading_style))
        
        # Top Bullish Sectors Table
        story.append(Paragraph("Top Bullish Sectors (Current)", self.subheading_style))
        
        bullish_data = [['Rank', 'Sector', 'Bullish %', 'Bearish %']]
        for i, sector in enumerate(analysis['top_bullish_sectors'], 1):
            bullish_data.append([
                str(i),
                sector['sector_name'],
                f"{sector['bullish_percent']:.1f}%",
                f"{sector['bearish_percent']:.1f}%"
            ])
        
        bullish_table = Table(bullish_data)
        bullish_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.darkgreen),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        story.append(bullish_table)
        story.append(Spacer(1, 0.3*inch))
        
        # Strongest Momentum Sectors
        story.append(Paragraph("Strongest Momentum Sectors", self.subheading_style))
        
        momentum_data = [['Rank', 'Sector', 'Momentum Score', 'Current Bullish %']]
        for i, sector in enumerate(analysis['strongest_momentum'], 1):
            momentum_data.append([
                str(i),
                sector['sector_name'],
                f"{sector['bullish_momentum']:+.1f}",
                f"{sector['current_bullish']:.1f}%"
            ])
        
        momentum_table = Table(momentum_data)
        momentum_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.lightblue),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        story.append(momentum_table)
    
    def _add_trend_analysis(self, story: List, analysis: Dict):
        """Add detailed trend analysis section."""
        story.append(PageBreak())
        story.append(Paragraph("Detailed Trend Analysis", self.heading_style))
        
        # Volatility Analysis
        story.append(Paragraph("Sector Stability Analysis", self.subheading_style))
        
        stability_text = f"""
        <b>Most Stable Sectors (Low Volatility):</b><br/>
        """
        
        for i, sector in enumerate(analysis['most_stable'], 1):
            stability_text += f"{i}. <b>{sector['sector_name']}</b> - Volatility: {sector['volatility']:.1f}, Avg Bullish: {sector['avg_bullish']:.1f}%<br/>"
        
        stability_text += f"""<br/>
        <b>Most Volatile Sectors:</b><br/>
        """
        
        for i, sector in enumerate(analysis['most_volatile'], 1):
            stability_text += f"{i}. <b>{sector['sector_name']}</b> - Volatility: {sector['volatility']:.1f}, Avg Bullish: {sector['avg_bullish']:.1f}%<br/>"
        
        story.append(Paragraph(stability_text, self.analysis_style))
        
        # Momentum Insights
        story.append(Spacer(1, 0.2*inch))
        story.append(Paragraph("Momentum Insights", self.subheading_style))
        
        momentum_text = """
        <b>Interpretation of Momentum Scores:</b><br/>
        • <b>Positive momentum (+)</b>: Sector showing improvement in bullish sentiment<br/>
        • <b>Negative momentum (-)</b>: Sector showing decline in bullish sentiment<br/>
        • <b>High volatility</b>: Sector experiencing significant sentiment swings<br/>
        • <b>Low volatility</b>: Sector showing consistent sentiment patterns<br/>
        """
        
        story.append(Paragraph(momentum_text, self.analysis_style))
    
    def _add_predictions(self, story: List, analysis: Dict):
        """Add sector predictions section."""
        story.append(PageBreak())
        story.append(Paragraph("Sector Predictions & Investment Insights", self.heading_style))
        
        predictions = analysis['predictions']
        
        # Upcoming Sectors
        if predictions['upcoming_sectors']:
            story.append(Paragraph("🚀 Upcoming Sectors (Strong Growth Potential)", self.subheading_style))
            
            upcoming_text = """
            Based on momentum analysis and current positioning, these sectors show strong potential for continued growth:<br/><br/>
            """
            
            for i, sector in enumerate(predictions['upcoming_sectors'], 1):
                upcoming_text += f"""
                <b>{i}. {sector['sector_name']}</b><br/>
                • Momentum Score: <b>{sector['bullish_momentum']:+.1f}</b><br/>
                • Current Bullish: <b>{sector['current_bullish']:.1f}%</b><br/>
                • Weekly Momentum: <b>{sector['weekly_momentum']:+.1f}</b><br/>
                <i>Analysis: Strong positive momentum with room for growth</i><br/><br/>
                """
            
            story.append(Paragraph(upcoming_text, self.prediction_style))
        
        # Stable Outperformers
        if predictions['stable_outperformers']:
            story.append(Spacer(1, 0.2*inch))
            story.append(Paragraph("⭐ Stable Outperformers (Consistent Performance)", self.subheading_style))
            
            stable_text = """
            These sectors maintain high bullish percentages with low volatility, indicating stable outperformance:<br/><br/>
            """
            
            for i, sector in enumerate(predictions['stable_outperformers'], 1):
                stable_text += f"""
                <b>{i}. {sector['sector_name']}</b><br/>
                • Current Bullish: <b>{sector['current_bullish']:.1f}%</b><br/>
                • Volatility: <b>{sector['volatility']:.1f}</b><br/>
                • Momentum: <b>{sector['bullish_momentum']:+.1f}</b><br/>
                <i>Analysis: Consistent high performance with low risk</i><br/><br/>
                """
            
            story.append(Paragraph(stable_text, self.prediction_style))
        
        # Recovery Candidates
        if predictions['recovery_candidates']:
            story.append(Spacer(1, 0.2*inch))
            story.append(Paragraph("📈 Recovery Candidates (Turnaround Potential)", self.subheading_style))
            
            recovery_text = """
            These sectors show positive momentum despite currently low bullish percentages, indicating potential turnaround:<br/><br/>
            """
            
            for i, sector in enumerate(predictions['recovery_candidates'], 1):
                recovery_text += f"""
                <b>{i}. {sector['sector_name']}</b><br/>
                • Current Bullish: <b>{sector['current_bullish']:.1f}%</b><br/>
                • Momentum: <b>{sector['bullish_momentum']:+.1f}</b><br/>
                • Weekly Momentum: <b>{sector['weekly_momentum']:+.1f}</b><br/>
                <i>Analysis: Early signs of recovery, potential value opportunity</i><br/><br/>
                """
            
            story.append(Paragraph(recovery_text, self.prediction_style))
        
        # Investment Strategy Summary
        story.append(Spacer(1, 0.3*inch))
        strategy_text = """
        <b>Investment Strategy Framework:</b><br/>
        • <b>Growth Strategy:</b> Focus on upcoming sectors with strong momentum<br/>
        • <b>Stability Strategy:</b> Invest in stable outperformers for consistent returns<br/>
        • <b>Value Strategy:</b> Consider recovery candidates for potential turnaround plays<br/>
        • <b>Risk Management:</b> Monitor volatility levels and momentum shifts<br/>
        """
        
        story.append(Paragraph(strategy_text, self.analysis_style))
    
    def _add_appendix(self, story: List, analysis: Dict):
        """Add appendix with methodology and data sources."""
        story.append(PageBreak())
        story.append(Paragraph("Appendix - Methodology & Data Sources", self.heading_style))
        
        methodology_text = f"""
        <b>Data Sources:</b><br/>
        • NSE equity market data from BHAV files<br/>
        • Technical trend analysis from moving averages and price patterns<br/>
        • Sectoral classification based on NIFTY index constituents<br/>
        
        <b>Analysis Methodology:</b><br/>
        • <b>Bullish Percentage:</b> Percentage of stocks in sector with positive trend ratings<br/>
        • <b>Momentum Calculation:</b> Difference between recent (last 5 days) and historical (first 5 days) averages<br/>
        • <b>Volatility Analysis:</b> Standard deviation of bullish percentages over the analysis period<br/>
        • <b>Trend Classification:</b> Based on daily, weekly, and monthly moving average patterns<br/>
        
        <b>Prediction Framework:</b><br/>
        • <b>Upcoming Sectors:</b> Positive momentum + room for growth (bullish % < 70%)<br/>
        • <b>Stable Outperformers:</b> High bullish % (>60%) + low volatility (<10)<br/>
        • <b>Recovery Candidates:</b> Low current bullish % (<40%) + positive momentum trends<br/>
        
        <b>Report Generation:</b><br/>
        • Generated on: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}<br/>
        • Analysis Period: {analysis['date_range']['start']} to {analysis['date_range']['end']}<br/>
        • Total Data Points: {analysis['total_records']} sector-day observations<br/>
        """
        
        story.append(Paragraph(methodology_text, self.analysis_style))
    
    def _cleanup_charts(self, chart_paths: List[str]):
        """Clean up temporary chart files."""
        for chart_path in chart_paths:
            try:
                if os.path.exists(chart_path):
                    os.remove(chart_path)
            except Exception as e:
                logger.warning(f"Failed to cleanup chart {chart_path}: {e}")

# Convenience function
def generate_sectoral_trends_pdf(filename: Optional[str] = None, days_back: int = 90) -> Tuple[bool, str]:
    """
    Generate sectoral trends PDF report.
    
    Args:
        filename: Output filename (auto-generated if None)
        days_back: Number of days of historical data to include (default 90)
        
    Returns:
        Tuple of (success, result_message)
    """
    generator = SectoralTrendsPDFGenerator()
    return generator.generate_sectoral_trends_report(filename, days_back)

if __name__ == "__main__":
    # Test the generator
    print("🔍 Testing Sectoral Trends PDF Generator")
    print("=" * 50)
    
    success, message = generate_sectoral_trends_pdf(days_back=90)
    
    if success:
        print(f"✅ {message}")
    else:
        print(f"❌ {message}")