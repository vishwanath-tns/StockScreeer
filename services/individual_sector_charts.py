"""
Individual Sector Chart Generator
Generates separate detailed charts for each sector with trend analysis
"""
import os
import logging
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime, timedelta
import numpy as np
from .sectoral_trends_service import get_trends_for_charting

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def convert_decimal_columns(df):
    """Convert Decimal columns to float for proper pandas operations"""
    for col in df.columns:
        if col in ['bullish_percent', 'bearish_percent', 'daily_uptrend_percent', 
                   'weekly_uptrend_percent', 'avg_trend_rating']:
            try:
                df[col] = pd.to_numeric(df[col], errors='coerce')
            except:
                pass
    return df

def calculate_sector_metrics(df):
    """Calculate key metrics for a sector"""
    if df.empty:
        return {}
    
    # Ensure numeric columns
    df = convert_decimal_columns(df)
    
    # Sort by date
    df = df.sort_values('analysis_date')
    
    # Calculate metrics
    latest_bullish = df['bullish_percent'].iloc[-1] if not df.empty else 0
    latest_rating = df['avg_trend_rating'].iloc[-1] if not df.empty else 0
    
    metrics = {
        'total_days': len(df),
        'latest_bullish_percent': float(latest_bullish) if pd.notna(latest_bullish) else 0,
        'avg_bullish_percent': float(df['bullish_percent'].mean()) if not df['bullish_percent'].isna().all() else 0,
        'bullish_change': float(latest_bullish - df['bullish_percent'].iloc[0]) if len(df) > 1 and pd.notna(latest_bullish) and pd.notna(df['bullish_percent'].iloc[0]) else 0,
        'avg_rating': float(latest_rating) if pd.notna(latest_rating) else 0,
        'total_stocks': int(df['total_stocks'].iloc[-1]) if not df.empty else 0,
        'trend_direction': 'Improving' if latest_bullish > df['bullish_percent'].iloc[0] else 'Declining' if len(df) > 1 else 'Stable',
        'max_bullish': float(df['bullish_percent'].max()) if not df['bullish_percent'].isna().all() else 0,
        'min_bullish': float(df['bullish_percent'].min()) if not df['bullish_percent'].isna().all() else 0,
        'volatility': float(df['bullish_percent'].std()) if not df['bullish_percent'].isna().all() else 0
    }
    
    return metrics

def create_sector_chart(sector_code, sector_name, df, output_dir="charts/sectors"):
    """Create detailed chart for a single sector"""
    
    if df.empty:
        logger.warning(f"No data available for sector {sector_code}")
        return False, f"No data for {sector_code}"
    
    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)
    
    # Convert data types and sort by date
    df = convert_decimal_columns(df)
    df = df.sort_values('analysis_date')
    
    # Convert analysis_date to datetime
    df['analysis_date'] = pd.to_datetime(df['analysis_date'])
    
    # Calculate metrics
    metrics = calculate_sector_metrics(df)
    
    # Create figure with subplots
    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(16, 12))
    fig.suptitle(f'{sector_name} ({sector_code}) - Trend Analysis', fontsize=16, fontweight='bold')
    
    # Plot 1: Bullish Percent Trend
    ax1.plot(df['analysis_date'], df['bullish_percent'], linewidth=2, color='green', label='Bullish %', marker='o', markersize=4)
    ax1.plot(df['analysis_date'], df['bearish_percent'], linewidth=2, color='red', label='Bearish %', marker='s', markersize=4)
    ax1.fill_between(df['analysis_date'], df['bullish_percent'], alpha=0.2, color='green')
    ax1.fill_between(df['analysis_date'], df['bearish_percent'], alpha=0.2, color='red')
    ax1.set_title(f'Bullish vs Bearish Trends - {metrics["trend_direction"]}', fontweight='bold')
    ax1.set_ylabel('Percentage (%)')
    ax1.grid(True, alpha=0.3)
    ax1.legend()
    
    # Format x-axis
    ax1.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d'))
    ax1.xaxis.set_major_locator(mdates.WeekdayLocator(interval=1))
    plt.setp(ax1.xaxis.get_majorticklabels(), rotation=45)
    
    # Plot 2: Uptrend Analysis
    ax2.bar(df['analysis_date'], df['daily_uptrend_percent'], alpha=0.7, color='blue', label='Daily Uptrend %')
    ax2.bar(df['analysis_date'], df['weekly_uptrend_percent'], alpha=0.5, color='purple', label='Weekly Uptrend %')
    ax2.set_title('Technical Uptrend Percentages', fontweight='bold')
    ax2.set_ylabel('Uptrend Percentage (%)')
    ax2.grid(True, alpha=0.3)
    ax2.legend()
    
    # Format x-axis
    ax2.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d'))
    ax2.xaxis.set_major_locator(mdates.WeekdayLocator(interval=1))
    plt.setp(ax2.xaxis.get_majorticklabels(), rotation=45)
    
    # Plot 3: Trend Rating
    # Color bars based on rating (positive = green, negative = red)
    colors = ['green' if x >= 0 else 'red' for x in df['avg_trend_rating']]
    ax3.bar(df['analysis_date'], df['avg_trend_rating'], color=colors, alpha=0.7)
    ax3.set_title('Average Trend Rating', fontweight='bold')
    ax3.set_ylabel('Trend Rating')
    ax3.axhline(y=0, color='black', linestyle='-', alpha=0.5)
    ax3.grid(True, alpha=0.3)
    
    # Format x-axis
    ax3.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d'))
    ax3.xaxis.set_major_locator(mdates.WeekdayLocator(interval=1))
    plt.setp(ax3.xaxis.get_majorticklabels(), rotation=45)
    
    # Plot 4: Key Metrics Summary
    ax4.axis('off')
    
    # Create metrics text
    metrics_text = f"""
Key Metrics Summary:

Current Status:
• Bullish: {metrics['latest_bullish_percent']:.1f}%
• Change: {metrics['bullish_change']:+.1f}%
• Trend: {metrics['trend_direction']}

Performance Range:
• Best: {metrics['max_bullish']:.1f}% bullish
• Worst: {metrics['min_bullish']:.1f}% bullish
• Volatility: {metrics['volatility']:.1f}%

Market Metrics:
• Total Stocks: {metrics['total_stocks']:,}
• Avg Trend Rating: {metrics['avg_rating']:.2f}
• Analysis Period: {metrics['total_days']} days

Average Bullish: {metrics['avg_bullish_percent']:.1f}%
"""
    
    ax4.text(0.1, 0.9, metrics_text, fontsize=11, verticalalignment='top', 
             bbox=dict(boxstyle="round,pad=0.5", facecolor="lightgray", alpha=0.8))
    
    # Add performance indicator
    performance_color = 'green' if metrics['bullish_change'] >= 0 else 'red'
    performance_text = f"Trend Change: {metrics['bullish_change']:+.1f}%"
    ax4.text(0.1, 0.15, performance_text, fontsize=14, fontweight='bold', 
             color=performance_color, bbox=dict(boxstyle="round,pad=0.3", facecolor="white", alpha=0.8))
    
    # Tight layout
    plt.tight_layout()
    
    # Save chart
    filename = f"{sector_code}_{sector_name.replace(' ', '_').replace('&', 'and')}_analysis.png"
    filepath = os.path.join(output_dir, filename)
    
    try:
        plt.savefig(filepath, dpi=300, bbox_inches='tight', facecolor='white')
        plt.close()
        logger.info(f"Chart saved: {filepath}")
        return True, filepath
    except Exception as e:
        logger.error(f"Error saving chart for {sector_code}: {e}")
        plt.close()
        return False, str(e)

def generate_all_sector_charts(days_back=90):
    """Generate individual charts for all sectors"""
    
    logger.info(f"🔄 Generating individual sector charts for last {days_back} days...")
    
    try:
        # Get sectoral trends data
        trends_df = get_trends_for_charting(days_back=days_back)
        
        if trends_df.empty:
            return False, "No sectoral trends data available"
        
        # Ensure numeric columns are properly converted
        trends_df = convert_decimal_columns(trends_df)
        
        logger.info(f"Processing {len(trends_df)} records for sector charts")
        
        # Get unique sectors
        sectors = trends_df['sector_code'].unique()
        
        results = []
        successful_charts = 0
        
        for sector_code in sectors:
            # Get sector data
            sector_df = trends_df[trends_df['sector_code'] == sector_code].copy()
            
            # Get sector name (use first occurrence)
            sector_name = sector_df['sector_name'].iloc[0] if not sector_df.empty else sector_code
            
            # Generate chart
            success, result = create_sector_chart(sector_code, sector_name, sector_df)
            
            if success:
                successful_charts += 1
                results.append(f"✅ {sector_name}: {result}")
            else:
                results.append(f"❌ {sector_name}: {result}")
        
        summary = f"""
📈 Sector Charts Generation Complete!

Successfully generated: {successful_charts}/{len(sectors)} charts
Charts saved in: charts/sectors/

Results:
""" + "\n".join(results)
        
        logger.info(f"🎯 Generated {successful_charts}/{len(sectors)} sector charts")
        return True, summary
        
    except Exception as e:
        error_msg = f"Error generating sector charts: {e}"
        logger.error(error_msg)
        return False, error_msg

def generate_sector_chart_by_code(sector_code, days_back=90):
    """Generate chart for a specific sector"""
    
    logger.info(f"🔄 Generating chart for sector {sector_code} (last {days_back} days)...")
    
    try:
        # Get sectoral trends data
        trends_df = get_trends_for_charting(days_back=days_back)
        
        if trends_df.empty:
            return False, f"No data available for sector {sector_code}"
        
        # Ensure numeric columns are properly converted
        trends_df = convert_decimal_columns(trends_df)
        
        # Filter for specific sector
        sector_df = trends_df[trends_df['sector_code'] == sector_code].copy()
        
        if sector_df.empty:
            return False, f"No data found for sector {sector_code}"
        
        # Get sector name
        sector_name = sector_df['sector_name'].iloc[0]
        
        # Generate chart
        success, result = create_sector_chart(sector_code, sector_name, sector_df)
        
        if success:
            return True, f"✅ Chart generated for {sector_name}: {result}"
        else:
            return False, f"❌ Failed to generate chart for {sector_name}: {result}"
            
    except Exception as e:
        error_msg = f"Error generating chart for {sector_code}: {e}"
        logger.error(error_msg)
        return False, error_msg

def list_available_sectors():
    """List all available sectors in the database"""
    
    try:
        # Get recent data to see available sectors
        trends_df = get_trends_for_charting(days_back=30)
        
        if trends_df.empty:
            return []
        
        # Get unique sectors with names
        sectors = trends_df[['sector_code', 'sector_name']].drop_duplicates().sort_values('sector_name')
        
        return [(row['sector_code'], row['sector_name']) for _, row in sectors.iterrows()]
        
    except Exception as e:
        logger.error(f"Error listing sectors: {e}")
        return []

if __name__ == "__main__":
    # Test the chart generation
    print("Testing individual sector chart generation...")
    
    # Generate all sector charts
    success, message = generate_all_sector_charts(days_back=90)
    print(f"Success: {success}")
    print(f"Result: {message}")