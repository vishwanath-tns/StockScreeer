"""
Zodiac Wheel Chart Generator for Vedic Astrology Trading

This module creates visual zodiac wheel charts showing current Moon position
and other planetary positions for trading analysis.
"""

import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np
import math
import datetime
import os
import sys
from pathlib import Path

# Add parent directories to path
current_dir = Path(__file__).parent
parent_dir = current_dir.parent
sys.path.append(str(parent_dir))
sys.path.append(str(parent_dir / 'calculations'))

from core_calculator import VedicAstrologyCalculator


class ZodiacWheelGenerator:
    """Generate zodiac wheel charts with planetary positions"""
    
    def __init__(self):
        self.calculator = VedicAstrologyCalculator()
        
        # Zodiac signs in order (starting from Aries at 0°)
        self.zodiac_signs = [
            'Aries', 'Taurus', 'Gemini', 'Cancer', 
            'Leo', 'Virgo', 'Libra', 'Scorpio',
            'Sagittarius', 'Capricorn', 'Aquarius', 'Pisces'
        ]
        
        # Zodiac symbols
        self.zodiac_symbols = [
            '♈', '♉', '♊', '♋', '♌', '♍', 
            '♎', '♏', '♐', '♑', '♒', '♓'
        ]
        
        # Element colors
        self.element_colors = {
            'Fire': '#FF4444',      # Red
            'Earth': '#8B4513',     # Brown  
            'Air': '#4169E1',       # Blue
            'Water': '#00CED1'      # Cyan
        }
        
        # Sign elements
        self.sign_elements = {
            'Aries': 'Fire', 'Leo': 'Fire', 'Sagittarius': 'Fire',
            'Taurus': 'Earth', 'Virgo': 'Earth', 'Capricorn': 'Earth',
            'Gemini': 'Air', 'Libra': 'Air', 'Aquarius': 'Air',
            'Cancer': 'Water', 'Scorpio': 'Water', 'Pisces': 'Water'
        }
    
    def create_zodiac_wheel(self, date=None, save_path=None):
        """Create a zodiac wheel chart with current Moon position"""
        
        if date is None:
            date = datetime.date.today()
        
        # Get current Moon position using available methods
        date_time = datetime.datetime.combine(date, datetime.time(9, 0))  # Market time
        astro_data = self.calculator.get_daily_astro_summary(date_time)
        nakshatra_data = self.calculator.get_current_nakshatra(date_time)
        
        # Extract moon information
        moon_sign = self._determine_moon_sign_from_nakshatra(nakshatra_data)
        moon_degree = self._estimate_moon_degree(nakshatra_data)
        
        # Create figure
        fig, ax = plt.subplots(1, 1, figsize=(12, 12))
        ax.set_xlim(-1.5, 1.5)
        ax.set_ylim(-1.5, 1.5)
        ax.set_aspect('equal')
        ax.axis('off')
        
        # Draw outer circle (zodiac wheel)
        outer_circle = plt.Circle((0, 0), 1.3, fill=False, linewidth=3, color='black')
        ax.add_patch(outer_circle)
        
        # Draw inner circle
        inner_circle = plt.Circle((0, 0), 0.8, fill=False, linewidth=2, color='gray')
        ax.add_patch(inner_circle)
        
        # Draw zodiac sign divisions
        for i in range(12):
            angle = i * 30 - 90  # Start from top (Aries)
            x1 = 0.8 * np.cos(np.radians(angle))
            y1 = 0.8 * np.sin(np.radians(angle))
            x2 = 1.3 * np.cos(np.radians(angle))
            y2 = 1.3 * np.sin(np.radians(angle))
            ax.plot([x1, x2], [y1, y2], 'k-', linewidth=1)
        
        # Add zodiac signs and symbols
        for i, (sign, symbol) in enumerate(zip(self.zodiac_signs, self.zodiac_symbols)):
            angle = i * 30 - 75  # Center of each sign
            
            # Sign position
            x = 1.1 * np.cos(np.radians(angle))
            y = 1.1 * np.sin(np.radians(angle))
            
            # Element color
            element = self.sign_elements[sign]
            color = self.element_colors[element]
            
            # Add sign symbol
            ax.text(x, y, symbol, ha='center', va='center', 
                   fontsize=20, fontweight='bold', color=color)
            
            # Add sign name
            x_name = 1.05 * np.cos(np.radians(angle))
            y_name = 1.05 * np.sin(np.radians(angle))
            ax.text(x_name, y_name - 0.08, sign[:3], ha='center', va='center', 
                   fontsize=10, fontweight='bold', color='black')
        
        # Calculate Moon position on wheel
        # Find sign index
        sign_index = self.zodiac_signs.index(moon_sign)
        
        # Calculate angle within the sign (0-30 degrees)
        degree_in_sign = moon_degree % 30
        
        # Total angle from Aries 0° (adjusting for wheel orientation)
        total_angle = (sign_index * 30 + degree_in_sign) - 90
        
        # Moon position
        moon_radius = 0.95
        moon_x = moon_radius * np.cos(np.radians(total_angle))
        moon_y = moon_radius * np.sin(np.radians(total_angle))
        
        # Draw Moon symbol and position
        moon_circle = plt.Circle((moon_x, moon_y), 0.06, color='gold', linewidth=2, 
                                edgecolor='darkgoldenrod', alpha=0.9)
        ax.add_patch(moon_circle)
        
        # Moon symbol
        ax.text(moon_x, moon_y, '🌙', ha='center', va='center', fontsize=16)
        
        # Moon degree label
        ax.text(moon_x, moon_y - 0.12, f"{moon_degree:.1f}°", 
               ha='center', va='center', fontsize=8, fontweight='bold',
               bbox=dict(boxstyle="round,pad=0.3", facecolor='lightyellow', alpha=0.8))
        
        # Highlight current sign
        sign_start_angle = sign_index * 30 - 90
        sign_end_angle = (sign_index + 1) * 30 - 90
        
        # Create highlighted arc for current moon sign
        theta1 = np.radians(sign_start_angle)
        theta2 = np.radians(sign_end_angle)
        
        arc = patches.Wedge((0, 0), 1.3, np.degrees(theta1), np.degrees(theta2),
                           width=0.5, facecolor=self.element_colors[self.sign_elements[moon_sign]], 
                           alpha=0.3, edgecolor='black', linewidth=2)
        ax.add_patch(arc)
        
        # Add title
        title_text = f"Moon Position - {date.strftime('%Y-%m-%d')}"
        ax.text(0, 1.45, title_text, ha='center', va='center', 
               fontsize=16, fontweight='bold', color='darkblue')
        
        # Add Moon details box
        moon_info = f"""Moon in {moon_sign}
{moon_degree:.1f}° {self.sign_elements[moon_sign]} Element
{nakshatra_data.get('quality', 'Unknown')} Quality"""
        
        ax.text(-1.4, -1.2, moon_info, ha='left', va='center', 
               fontsize=12, fontweight='bold',
               bbox=dict(boxstyle="round,pad=0.5", facecolor='lightblue', alpha=0.8))
        
        # Add element legend
        legend_y = 1.2
        ax.text(1.1, legend_y, "Elements:", ha='left', va='center', 
               fontsize=12, fontweight='bold')
        
        for i, (element, color) in enumerate(self.element_colors.items()):
            y_pos = legend_y - 0.15 * (i + 1)
            ax.plot([1.1], [y_pos], 'o', color=color, markersize=8)
            ax.text(1.15, y_pos, element, ha='left', va='center', fontsize=10)
        
        # Add degree markers
        for degree in range(0, 360, 30):
            angle = degree - 90
            x1 = 1.25 * np.cos(np.radians(angle))
            y1 = 1.25 * np.sin(np.radians(angle))
            x2 = 1.3 * np.cos(np.radians(angle))
            y2 = 1.3 * np.sin(np.radians(angle))
            ax.plot([x1, x2], [y1, y2], 'k-', linewidth=2)
            
            # Degree labels
            x_label = 1.35 * np.cos(np.radians(angle))
            y_label = 1.35 * np.sin(np.radians(angle))
            ax.text(x_label, y_label, f"{degree}°", ha='center', va='center', 
                   fontsize=8, color='gray')
        
        # Add center point
        center_circle = plt.Circle((0, 0), 0.03, color='black')
        ax.add_patch(center_circle)
        
        plt.tight_layout()
        
        # Save the chart
        if save_path is None:
            # Default save path
            charts_dir = current_dir.parent / 'reports' / 'charts'
            charts_dir.mkdir(parents=True, exist_ok=True)
            save_path = charts_dir / f"zodiac_wheel_{date.strftime('%Y%m%d')}.png"
        
        plt.savefig(save_path, dpi=300, bbox_inches='tight', 
                   facecolor='white', edgecolor='none')
        
        print(f"[CHART] Zodiac wheel saved: {save_path}")
        return save_path
    
    def create_detailed_wheel_with_planets(self, date=None, save_path=None):
        """Create detailed wheel with multiple planetary positions"""
        
        if date is None:
            date = datetime.date.today()
        
        # Get planetary and moon information using available methods
        date_time = datetime.datetime.combine(date, datetime.time(9, 0))  # Market time
        astro_data = self.calculator.get_daily_astro_summary(date_time)
        nakshatra_data = self.calculator.get_current_nakshatra(date_time)
        moon_phase_data = self.calculator.get_moon_phase(date_time)
        
        # Determine moon position
        moon_sign = self._determine_moon_sign_from_nakshatra(nakshatra_data)
        moon_degree = self._estimate_moon_degree(nakshatra_data)
        
        # Create figure
        fig, ax = plt.subplots(1, 1, figsize=(14, 14))
        ax.set_xlim(-1.6, 1.6)
        ax.set_ylim(-1.6, 1.6)
        ax.set_aspect('equal')
        ax.axis('off')
        
        # Draw multiple concentric circles
        circles = [1.4, 1.2, 1.0, 0.8, 0.6]
        for radius in circles:
            circle = plt.Circle((0, 0), radius, fill=False, linewidth=1, 
                               color='lightgray' if radius != 1.2 else 'black')
            ax.add_patch(circle)
        
        # Draw zodiac divisions with enhanced styling
        for i in range(12):
            angle = i * 30 - 90
            # Outer division lines
            x1 = 0.6 * np.cos(np.radians(angle))
            y1 = 0.6 * np.sin(np.radians(angle))
            x2 = 1.4 * np.cos(np.radians(angle))
            y2 = 1.4 * np.sin(np.radians(angle))
            ax.plot([x1, x2], [y1, y2], 'k-', linewidth=1.5)
            
            # Add 5-degree subdivision marks
            for sub_degree in range(5, 30, 5):
                sub_angle = angle + sub_degree
                sx1 = 1.15 * np.cos(np.radians(sub_angle))
                sy1 = 1.15 * np.sin(np.radians(sub_angle))
                sx2 = 1.2 * np.cos(np.radians(sub_angle))
                sy2 = 1.2 * np.sin(np.radians(sub_angle))
                ax.plot([sx1, sx2], [sy1, sy2], 'gray', linewidth=0.5)
        
        # Enhanced zodiac signs
        for i, (sign, symbol) in enumerate(zip(self.zodiac_signs, self.zodiac_symbols)):
            angle = i * 30 - 75
            
            # Sign background
            sign_start = i * 30 - 90
            sign_end = (i + 1) * 30 - 90
            arc_bg = patches.Wedge((0, 0), 1.2, sign_start, sign_end,
                                  width=0.2, facecolor=self.element_colors[self.sign_elements[sign]], 
                                  alpha=0.2, edgecolor='none')
            ax.add_patch(arc_bg)
            
            # Sign symbol position
            x = 1.3 * np.cos(np.radians(angle))
            y = 1.3 * np.sin(np.radians(angle))
            
            ax.text(x, y, symbol, ha='center', va='center', 
                   fontsize=24, fontweight='bold', 
                   color=self.element_colors[self.sign_elements[sign]])
            
            # Sign name
            ax.text(x, y - 0.1, sign, ha='center', va='center', 
                   fontsize=9, fontweight='bold', color='black')
            
            # Degree markers
            degree_angle = i * 30 - 90
            dx = 1.45 * np.cos(np.radians(degree_angle))
            dy = 1.45 * np.sin(np.radians(degree_angle))
            ax.text(dx, dy, f"{i * 30}°", ha='center', va='center', 
                   fontsize=8, color='darkblue', fontweight='bold')
        
        # Enhanced Moon position
        moon_sign = moon_data['sign']
        moon_degree = moon_data['degree']
        sign_index = self.zodiac_signs.index(moon_sign)
        degree_in_sign = moon_degree % 30
        total_angle = (sign_index * 30 + degree_in_sign) - 90
        
        # Moon on outer ring
        moon_radius = 1.1
        moon_x = moon_radius * np.cos(np.radians(total_angle))
        moon_y = moon_radius * np.sin(np.radians(total_angle))
        
        # Enhanced Moon symbol
        moon_bg = plt.Circle((moon_x, moon_y), 0.08, color='gold', linewidth=3, 
                            edgecolor='orange', alpha=0.9)
        ax.add_patch(moon_bg)
        
        ax.text(moon_x, moon_y, '🌙', ha='center', va='center', fontsize=20)
        
        # Moon degree and details
        moon_label = f"☽ {moon_degree:.1f}°\n{moon_sign}\n{moon_phase_data['phase'][:3]}"
        ax.text(moon_x, moon_y - 0.18, moon_label, ha='center', va='center', 
               fontsize=8, fontweight='bold',
               bbox=dict(boxstyle="round,pad=0.4", facecolor='lightyellow', 
                        edgecolor='orange', alpha=0.9))
        
        # Highlight current moon sign with enhanced styling
        sign_arc = patches.Wedge((0, 0), 1.2, sign_index * 30 - 90, (sign_index + 1) * 30 - 90,
                                width=0.4, facecolor=self.element_colors[self.sign_elements[moon_sign]], 
                                alpha=0.4, edgecolor='black', linewidth=2)
        ax.add_patch(sign_arc)
        
        # Enhanced title
        title_text = f"Vedic Astrology Chart - {date.strftime('%B %d, %Y')}"
        ax.text(0, 1.55, title_text, ha='center', va='center', 
               fontsize=18, fontweight='bold', color='darkblue')
        
        # Comprehensive information panel
        info_text = f"""Current Lunar Position:
        
☽ Moon: {moon_degree:.1f}° in {moon_sign}
🜃 Element: {self.sign_elements[moon_sign]}
🌙 Phase: {moon_phase_data['phase']}
📊 Illumination: {moon_phase_data['illumination']:.1f}%
🔄 Age: {moon_phase_data['age']:.1f} days

Market Implications:
• Volatility: {self._get_volatility_for_sign(moon_sign)}
• Trading Style: {self._get_trading_style_for_element(self.sign_elements[moon_sign])}
• Risk Level: {self._get_risk_level_for_sign(moon_sign)}"""
        
        ax.text(-1.55, 0.3, info_text, ha='left', va='top', 
               fontsize=10, fontweight='normal',
               bbox=dict(boxstyle="round,pad=0.8", facecolor='lightcyan', 
                        edgecolor='darkblue', alpha=0.9))
        
        # Element legend with enhanced styling
        legend_x, legend_y = 1.0, -0.8
        ax.text(legend_x, legend_y, "Elements & Trading:", ha='center', va='center', 
               fontsize=12, fontweight='bold', color='darkblue')
        
        element_info = {
            'Fire': '♈♌♐ - Momentum Trading',
            'Earth': '♉♍♑ - Value Investing', 
            'Air': '♊♎♒ - Trend Following',
            'Water': '♋♏♓ - Contrarian Plays'
        }
        
        for i, (element, info) in enumerate(element_info.items()):
            y_pos = legend_y - 0.15 * (i + 1)
            # Element indicator
            ax.plot([legend_x - 0.4], [y_pos], 's', color=self.element_colors[element], 
                   markersize=10, markeredgecolor='black')
            ax.text(legend_x - 0.2, y_pos, info, ha='left', va='center', fontsize=9)
        
        plt.tight_layout()
        
        # Save enhanced chart
        if save_path is None:
            charts_dir = current_dir.parent / 'reports' / 'charts'
            charts_dir.mkdir(parents=True, exist_ok=True)
            save_path = charts_dir / f"detailed_zodiac_wheel_{date.strftime('%Y%m%d')}.png"
        
        plt.savefig(save_path, dpi=300, bbox_inches='tight', 
                   facecolor='white', edgecolor='none')
        
        print(f"[CHART] Detailed zodiac wheel saved: {save_path}")
        return save_path
    
    def _get_volatility_for_sign(self, sign):
        """Get volatility description for a zodiac sign"""
        volatility_map = {
            'Aries': 'High (1.2x)', 'Taurus': 'Low (0.8x)', 'Gemini': 'Medium (1.0x)',
            'Cancer': 'Medium-High (1.1x)', 'Leo': 'High (1.2x)', 'Virgo': 'Low (0.7x)',
            'Libra': 'Medium (1.0x)', 'Scorpio': 'Very High (1.5x)', 'Sagittarius': 'High (1.2x)',
            'Capricorn': 'Very Low (0.6x)', 'Aquarius': 'Medium (1.0x)', 'Pisces': 'Medium-High (1.1x)'
        }
        return volatility_map.get(sign, 'Medium (1.0x)')
    
    def _get_trading_style_for_element(self, element):
        """Get trading style for an element"""
        style_map = {
            'Fire': 'Momentum, Breakouts',
            'Earth': 'Value, Accumulation',
            'Air': 'Trend Following',
            'Water': 'Contrarian, Emotional'
        }
        return style_map.get(element, 'Balanced')
    
    def _get_risk_level_for_sign(self, sign):
        """Get risk level for a zodiac sign"""
        if sign in ['Scorpio', 'Aries']:
            return 'Very High'
        elif sign in ['Leo', 'Sagittarius', 'Cancer', 'Pisces']:
            return 'High'
        elif sign in ['Gemini', 'Libra', 'Aquarius']:
            return 'Medium'
        else:  # Taurus, Virgo, Capricorn
            return 'Low'
    
    def _determine_moon_sign_from_nakshatra(self, nakshatra_data):
        """Determine zodiac sign from nakshatra data"""
        # Mapping from nakshatras to zodiac signs
        nakshatra_to_sign = {
            'Ashwini': 'Aries', 'Bharani': 'Aries',
            'Krittika': 'Aries',  # Part Aries, part Taurus - simplified
            'Rohini': 'Taurus', 'Mrigashirsha': 'Taurus',
            'Ardra': 'Gemini', 'Punarvasu': 'Gemini',
            'Pushya': 'Cancer', 'Ashlesha': 'Cancer',
            'Magha': 'Leo', 'Purva Phalguni': 'Leo', 'Uttara Phalguni': 'Leo',
            'Hasta': 'Virgo', 'Chitra': 'Virgo',
            'Swati': 'Libra', 'Vishakha': 'Libra',
            'Anuradha': 'Scorpio', 'Jyeshtha': 'Scorpio',
            'Mula': 'Sagittarius', 'Purva Ashadha': 'Sagittarius', 'Uttara Ashadha': 'Sagittarius',
            'Shravana': 'Capricorn', 'Dhanishta': 'Capricorn',
            'Shatabhisha': 'Aquarius', 'Purva Bhadrapada': 'Aquarius',
            'Uttara Bhadrapada': 'Pisces', 'Revati': 'Pisces'
        }
        
        current_nakshatra = nakshatra_data.get('name', 'Ashwini')
        return nakshatra_to_sign.get(current_nakshatra, 'Aries')
    
    def _estimate_moon_degree(self, nakshatra_data):
        """Estimate moon degree from nakshatra data"""
        # Each nakshatra spans 13.33 degrees
        # This is a simplified estimation
        nakshatra_degrees = {
            'Ashwini': 6.67, 'Bharani': 20, 'Krittika': 3.33,  # Krittika spans two signs
            'Rohini': 16.67, 'Mrigashirsha': 30, 
            'Ardra': 13.33, 'Punarvasu': 26.67,
            'Pushya': 10, 'Ashlesha': 23.33,
            'Magha': 6.67, 'Purva Phalguni': 20, 'Uttara Phalguni': 3.33,
            'Hasta': 16.67, 'Chitra': 30,
            'Swati': 13.33, 'Vishakha': 26.67,
            'Anuradha': 10, 'Jyeshtha': 23.33,
            'Mula': 6.67, 'Purva Ashadha': 20, 'Uttara Ashadha': 3.33,
            'Shravana': 16.67, 'Dhanishta': 30,
            'Shatabhisha': 13.33, 'Purva Bhadrapada': 26.67,
            'Uttara Bhadrapada': 10, 'Revati': 23.33
        }
        
        current_nakshatra = nakshatra_data.get('name', 'Ashwini')
        return nakshatra_degrees.get(current_nakshatra, 15.0)
    
    def display_chart(self, chart_path):
        """Display the generated chart"""
        try:
            if os.path.exists(chart_path):
                os.startfile(str(chart_path))  # Windows
                return True
        except Exception as e:
            print(f"[ERROR] Could not display chart: {e}")
            return False


def main():
    """Test the zodiac wheel generator"""
    generator = ZodiacWheelGenerator()
    
    print("[CHART] Generating zodiac wheel charts...")
    
    # Generate basic wheel
    basic_chart = generator.create_zodiac_wheel()
    
    # Generate detailed wheel
    detailed_chart = generator.create_detailed_wheel_with_planets()
    
    print(f"[CHART] Charts generated:")
    print(f"  Basic: {basic_chart}")
    print(f"  Detailed: {detailed_chart}")
    
    # Try to display the detailed chart
    generator.display_chart(detailed_chart)


if __name__ == "__main__":
    main()