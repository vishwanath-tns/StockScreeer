"""
Moon Cycles Wave Visualization

This script creates beautiful wave visualizations of moon cycles showing:
1. Lunar phase progression as a sine wave
2. Illumination percentage over time
3. Volatility patterns based on moon phases
4. Color-coded phases and important events
"""

import sys
import os
import datetime
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.patches import Rectangle
import pandas as pd

# Add the path to import vedic astrology modules
sys.path.append(os.path.join(os.path.dirname(__file__), 'calculations'))

from moon_cycle_analyzer import MoonCycleAnalyzer


def create_moon_wave_visualization(start_date, end_date, save_path=None):
    """
    Create comprehensive moon cycle wave visualization
    """
    analyzer = MoonCycleAnalyzer()
    
    # Get lunar data
    df = analyzer.get_lunar_data(start_date, end_date)
    
    if df.empty:
        print("No data found. Generating lunar calendar...")
        lunar_calendar = analyzer.generate_lunar_calendar(start_date, end_date)
        analyzer.save_lunar_calendar(lunar_calendar)
        df = analyzer.get_lunar_data(start_date, end_date)
    
    # Convert dates to datetime if they aren't already
    df['date'] = pd.to_datetime(df['date'])
    
    # Create figure with multiple subplots
    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(20, 12))
    fig.suptitle('Moon Cycles Wave Analysis - Vedic Astrology for Stock Market', 
                 fontsize=16, fontweight='bold')
    
    # 1. Main Lunar Phase Wave
    create_lunar_phase_wave(ax1, df)
    
    # 2. Illumination Percentage
    create_illumination_chart(ax2, df)
    
    # 3. Volatility Wave Pattern
    create_volatility_wave(ax3, df)
    
    # 4. Phase Distribution Pie Chart
    create_phase_distribution(ax4, df)
    
    plt.tight_layout()
    
    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        print(f"Moon wave visualization saved to: {save_path}")
    
    plt.show()
    
    return fig


def create_lunar_phase_wave(ax, df):
    """Create the main lunar phase wave visualization"""
    
    # Map phases to wave values (sine wave pattern)
    phase_to_wave = {
        'New Moon': 0,
        'Waxing Crescent': 0.25,
        'First Quarter': 0.5,
        'Waxing Gibbous': 0.75,
        'Full Moon': 1.0,
        'Waning Gibbous': 0.75,
        'Last Quarter': 0.5,
        'Waning Crescent': 0.25
    }
    
    # Calculate wave values
    df['wave_value'] = df['phase'].map(phase_to_wave)
    
    # Create smooth sine wave
    x_smooth = np.linspace(0, len(df), len(df) * 10)
    wave_smooth = np.interp(x_smooth, range(len(df)), df['wave_value'])
    dates_smooth = pd.date_range(df['date'].iloc[0], df['date'].iloc[-1], len(x_smooth))
    
    # Plot the wave
    ax.plot(dates_smooth, wave_smooth, 'b-', linewidth=3, alpha=0.8, label='Lunar Cycle Wave')
    ax.fill_between(dates_smooth, 0, wave_smooth, alpha=0.3, color='lightblue')
    
    # Add phase markers
    phase_colors = {
        'New Moon': 'black',
        'Full Moon': 'gold',
        'First Quarter': 'gray',
        'Last Quarter': 'gray'
    }
    
    for phase, color in phase_colors.items():
        phase_dates = df[df['phase'] == phase]['date']
        phase_values = df[df['phase'] == phase]['wave_value']
        ax.scatter(phase_dates, phase_values, c=color, s=100, zorder=5, 
                  label=f'{phase}', edgecolors='white', linewidth=1)
    
    ax.set_title('Lunar Phase Wave Pattern', fontweight='bold', fontsize=12)
    ax.set_ylabel('Lunar Phase Intensity')
    ax.set_ylim(0, 1.1)
    ax.grid(True, alpha=0.3)
    ax.legend(loc='upper right', fontsize=8)
    
    # Format x-axis
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
    ax.xaxis.set_major_locator(mdates.MonthLocator(interval=2))
    plt.setp(ax.xaxis.get_majorticklabels(), rotation=45)


def create_illumination_chart(ax, df):
    """Create illumination percentage chart"""
    
    # Color gradient based on illumination
    colors = plt.cm.YlOrRd(df['illumination'] / 100)
    
    ax.plot(df['date'], df['illumination'], 'r-', linewidth=2, alpha=0.8)
    ax.fill_between(df['date'], 0, df['illumination'], alpha=0.4, color='orange')
    
    # Add scatter points colored by illumination
    scatter = ax.scatter(df['date'], df['illumination'], c=df['illumination'], 
                        cmap='YlOrRd', s=20, alpha=0.7)
    
    ax.set_title('Moon Illumination Percentage', fontweight='bold', fontsize=12)
    ax.set_ylabel('Illumination %')
    ax.set_ylim(0, 105)
    ax.grid(True, alpha=0.3)
    
    # Add colorbar
    cbar = plt.colorbar(scatter, ax=ax)
    cbar.set_label('Illumination %', fontsize=10)
    
    # Format x-axis
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
    ax.xaxis.set_major_locator(mdates.MonthLocator(interval=2))
    plt.setp(ax.xaxis.get_majorticklabels(), rotation=45)


def create_volatility_wave(ax, df):
    """Create volatility wave pattern"""
    
    # Color mapping for volatility levels
    volatility_colors = []
    for vol in df['volatility_score']:
        if vol <= 0.8:
            volatility_colors.append('green')  # Low volatility
        elif vol <= 1.1:
            volatility_colors.append('yellow')  # Medium volatility
        else:
            volatility_colors.append('red')  # High volatility
    
    # Plot volatility wave
    ax.plot(df['date'], df['volatility_score'], 'purple', linewidth=2, alpha=0.8)
    
    # Fill areas with different colors based on volatility
    ax.fill_between(df['date'], 0.5, df['volatility_score'], 
                   where=(df['volatility_score'] <= 0.8), 
                   color='green', alpha=0.3, label='Low Volatility (≤0.8)')
    
    ax.fill_between(df['date'], 0.5, df['volatility_score'], 
                   where=((df['volatility_score'] > 0.8) & (df['volatility_score'] <= 1.1)), 
                   color='yellow', alpha=0.3, label='Medium Volatility (0.8-1.1)')
    
    ax.fill_between(df['date'], 0.5, df['volatility_score'], 
                   where=(df['volatility_score'] > 1.1), 
                   color='red', alpha=0.3, label='High Volatility (>1.1)')
    
    ax.set_title('Market Volatility Wave (Based on Lunar Phases)', fontweight='bold', fontsize=12)
    ax.set_ylabel('Volatility Multiplier')
    ax.set_ylim(0.5, 1.6)
    ax.grid(True, alpha=0.3)
    ax.legend(fontsize=8)
    
    # Format x-axis
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
    ax.xaxis.set_major_locator(mdates.MonthLocator(interval=2))
    plt.setp(ax.xaxis.get_majorticklabels(), rotation=45)


def create_phase_distribution(ax, df):
    """Create phase distribution pie chart"""
    
    phase_counts = df['phase'].value_counts()
    colors = ['gold', 'lightblue', 'gray', 'orange', 'red', 'purple', 'green', 'pink']
    
    wedges, texts, autotexts = ax.pie(phase_counts.values, 
                                     labels=phase_counts.index, 
                                     autopct='%1.1f%%',
                                     colors=colors,
                                     startangle=90)
    
    ax.set_title('Lunar Phase Distribution', fontweight='bold', fontsize=12)
    
    # Enhance text
    for text in texts:
        text.set_fontsize(10)
    for autotext in autotexts:
        autotext.set_color('white')
        autotext.set_fontweight('bold')
        autotext.set_fontsize(9)


def create_annual_moon_calendar(year=2025):
    """Create a full year moon calendar visualization"""
    
    start_date = datetime.date(year, 1, 1)
    end_date = datetime.date(year, 12, 31)
    
    analyzer = MoonCycleAnalyzer()
    df = analyzer.get_lunar_data(start_date, end_date)
    
    if df.empty:
        print(f"Generating {year} lunar calendar...")
        lunar_calendar = analyzer.generate_lunar_calendar(start_date, end_date)
        analyzer.save_lunar_calendar(lunar_calendar)
        df = analyzer.get_lunar_data(start_date, end_date)
    
    # Create calendar grid
    fig, ax = plt.subplots(figsize=(16, 10))
    
    df['date'] = pd.to_datetime(df['date'])
    df['day_of_year'] = df['date'].dt.dayofyear
    
    # Create circular moon calendar
    angles = np.linspace(0, 2*np.pi, len(df), endpoint=False)
    
    # Map phases to sizes and colors
    phase_to_size = {
        'New Moon': 50, 'Waxing Crescent': 100, 'First Quarter': 150,
        'Waxing Gibbous': 200, 'Full Moon': 250, 'Waning Gibbous': 200,
        'Last Quarter': 150, 'Waning Crescent': 100
    }
    
    phase_to_color = {
        'New Moon': 'black', 'Waxing Crescent': 'lightblue', 'First Quarter': 'blue',
        'Waxing Gibbous': 'orange', 'Full Moon': 'gold', 'Waning Gibbous': 'orange',
        'Last Quarter': 'blue', 'Waning Crescent': 'lightblue'
    }
    
    # Convert to polar coordinates
    radius = df['illumination'] / 10 + 1  # Scale radius based on illumination
    x = radius * np.cos(angles)
    y = radius * np.sin(angles)
    
    # Plot points
    for i, row in df.iterrows():
        size = phase_to_size.get(row['phase'], 100)
        color = phase_to_color.get(row['phase'], 'gray')
        ax.scatter(x[i], y[i], s=size, c=color, alpha=0.7, edgecolors='white')
    
    # Add month labels
    for month in range(1, 13):
        month_data = df[df['date'].dt.month == month]
        if not month_data.empty:
            idx = month_data.index[0]
            angle = angles[idx]
            label_x = 12 * np.cos(angle)
            label_y = 12 * np.sin(angle)
            ax.text(label_x, label_y, datetime.date(year, month, 1).strftime('%b'), 
                   ha='center', va='center', fontweight='bold', fontsize=10)
    
    ax.set_xlim(-15, 15)
    ax.set_ylim(-15, 15)
    ax.set_aspect('equal')
    ax.axis('off')
    ax.set_title(f'{year} Lunar Calendar - Circular View', fontsize=16, fontweight='bold')
    
    # Add legend
    legend_elements = [plt.scatter([], [], s=phase_to_size[phase], c=color, 
                                 label=phase, alpha=0.7, edgecolors='white')
                      for phase, color in phase_to_color.items()]
    ax.legend(handles=legend_elements, loc='upper right', bbox_to_anchor=(1.2, 1))
    
    plt.tight_layout()
    
    # Save circular calendar
    save_path = os.path.join(os.path.dirname(__file__), f'moon_calendar_{year}_circular.png')
    plt.savefig(save_path, dpi=300, bbox_inches='tight')
    print(f"Circular moon calendar saved to: {save_path}")
    
    plt.show()
    
    return fig


def main():
    """Main function to create all visualizations"""
    print("=== Creating Moon Cycles Wave Visualizations ===")
    
    # Create 2024-2025 wave analysis
    start_date = datetime.date(2024, 1, 1)
    end_date = datetime.date(2025, 12, 31)
    
    save_path = os.path.join(os.path.dirname(__file__), 'moon_cycles_wave_2024_2025.png')
    
    print("Creating comprehensive wave analysis...")
    fig1 = create_moon_wave_visualization(start_date, end_date, save_path)
    
    # Create 2025 circular calendar
    print("Creating 2025 circular moon calendar...")
    fig2 = create_annual_moon_calendar(2025)
    
    print("All visualizations completed!")
    
    return fig1, fig2


if __name__ == "__main__":
    main()