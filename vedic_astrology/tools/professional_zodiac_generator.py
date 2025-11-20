"""
Enhanced Zodiac Wheel Generator with PyJHora Swiss Ephemeris Backend

This module upgrades our zodiac wheel system to use professional-grade
PyJHora calculations with Swiss Ephemeris backend for accuracy matching
Drik Panchang and other professional astrological software.

Key Improvements:
- Swiss Ephemeris planetary positions (replaces our previous calculations)
- Professional Panchanga calculations
- Accurate Rahu/Ketu positions 
- Sidereal zodiac with proper ayanamsa
- Enhanced visual display with professional data

Author: AI Assistant
Date: November 20, 2025
"""

import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.patches import FancyBboxPatch, Circle
import numpy as np
from datetime import datetime
import math
import os

# Import our professional PyJHora calculator
from pyjhora_calculator import ProfessionalAstrologyCalculator

class ProfessionalZodiacWheelGenerator:
    """
    Professional Zodiac Wheel Generator using PyJHora Swiss Ephemeris backend.
    
    This class generates accurate zodiac wheels with planetary positions
    calculated using the same Swiss Ephemeris backend used by professional
    astrological software like Drik Panchang.
    """
    
    def __init__(self):
        """Initialize the professional zodiac wheel generator."""
        # Initialize PyJHora calculator with default Mumbai location
        self.astro_calc = ProfessionalAstrologyCalculator()
        
        # Enhanced zodiac sign data with Sanskrit names
        self.zodiac_signs = [
            {"name": "Aries", "sanskrit": "Mesha", "symbol": "♈", "element": "Fire", "color": "#FF6B6B"},
            {"name": "Taurus", "sanskrit": "Vrishabha", "symbol": "♉", "element": "Earth", "color": "#4ECDC4"},
            {"name": "Gemini", "sanskrit": "Mithuna", "symbol": "♊", "element": "Air", "color": "#45B7D1"},
            {"name": "Cancer", "sanskrit": "Karkata", "symbol": "♋", "element": "Water", "color": "#96CEB4"},
            {"name": "Leo", "sanskrit": "Simha", "symbol": "♌", "element": "Fire", "color": "#FFEAA7"},
            {"name": "Virgo", "sanskrit": "Kanya", "symbol": "♍", "element": "Earth", "color": "#DDA0DD"},
            {"name": "Libra", "sanskrit": "Tula", "symbol": "♎", "element": "Air", "color": "#98D8C8"},
            {"name": "Scorpio", "sanskrit": "Vrishchika", "symbol": "♏", "element": "Water", "color": "#F7DC6F"},
            {"name": "Sagittarius", "sanskrit": "Dhanus", "symbol": "♐", "element": "Fire", "color": "#BB8FCE"},
            {"name": "Capricorn", "sanskrit": "Makara", "symbol": "♑", "element": "Earth", "color": "#85C1E9"},
            {"name": "Aquarius", "sanskrit": "Kumbha", "symbol": "♒", "element": "Air", "color": "#F8C471"},
            {"name": "Pisces", "sanskrit": "Meena", "symbol": "♓", "element": "Water", "color": "#82E0AA"}
        ]
        
        # Enhanced planet data with Sanskrit names and symbols
        self.planet_info = {
            'Sun': {"sanskrit": "Surya", "symbol": "☉", "color": "#FFD700", "size": 120},
            'Moon': {"sanskrit": "Chandra", "symbol": "☽", "color": "#C0C0C0", "size": 100},
            'Mercury': {"sanskrit": "Budha", "symbol": "☿", "color": "#FFA500", "size": 60},
            'Venus': {"sanskrit": "Shukra", "symbol": "♀", "color": "#FF69B4", "size": 80},
            'Mars': {"sanskrit": "Mangal", "symbol": "♂", "color": "#FF4500", "size": 70},
            'Jupiter': {"sanskrit": "Guru", "symbol": "♃", "color": "#4169E1", "size": 100},
            'Saturn': {"sanskrit": "Shani", "symbol": "♄", "color": "#800080", "size": 90},
            'Rahu': {"sanskrit": "Rahu", "symbol": "☊", "color": "#8B4513", "size": 70},
            'Ketu': {"sanskrit": "Ketu", "symbol": "☋", "color": "#696969", "size": 70}
        }
    
    def create_professional_zodiac_wheel(self, date_time: datetime = None, 
                                      location_name: str = "Mumbai",
                                      latitude: float = 19.0760,
                                      longitude: float = 72.8777,
                                      timezone_hours: float = 5.5) -> str:
        """
        Create a professional zodiac wheel with PyJHora Swiss Ephemeris calculations.
        
        Args:
            date_time: Date and time for calculations (default: current time)
            location_name: Name of location
            latitude: Latitude in degrees
            longitude: Longitude in degrees  
            timezone_hours: Timezone offset from UTC
            
        Returns:
            Path to the generated zodiac wheel image
        """
        if date_time is None:
            date_time = datetime.now()
        
        # Update calculator with specified location
        self.astro_calc = ProfessionalAstrologyCalculator(
            location_name, latitude, longitude, timezone_hours
        )
        
        # Get professional astrological data using PyJHora
        astro_data = self.astro_calc.get_complete_analysis(date_time)
        planetary_positions = astro_data['planetary_positions']
        panchanga = astro_data['panchanga']
        moon_phase = astro_data.get('moon_phase', {})
        
        # Create the figure
        fig, ax = plt.subplots(figsize=(12, 12))
        ax.set_xlim(-6, 6)
        ax.set_ylim(-6, 6)
        ax.set_aspect('equal')
        ax.axis('off')
        
        # Draw the zodiac wheel background
        self._draw_zodiac_wheel_background(ax)
        
        # Plot planets using Swiss Ephemeris positions
        self._plot_professional_planets(ax, planetary_positions)
        
        # Add professional information panel
        self._add_professional_info_panel(ax, date_time, astro_data, panchanga, moon_phase)
        
        # Add title with calculation engine info
        plt.suptitle(f'Professional Zodiac Wheel - PyJHora Swiss Ephemeris\n'
                    f'{date_time.strftime("%Y-%m-%d %H:%M")} - {location_name}', 
                    fontsize=14, fontweight='bold', y=0.95)
        
        # Save the chart
        output_dir = os.path.dirname(os.path.dirname(__file__))  # Go up to vedic_astrology
        charts_dir = os.path.join(output_dir, 'charts')
        os.makedirs(charts_dir, exist_ok=True)
        
        timestamp = date_time.strftime("%Y%m%d_%H%M%S")
        filename = f"professional_zodiac_wheel_{timestamp}.png"
        filepath = os.path.join(charts_dir, filename)
        
        plt.savefig(filepath, dpi=300, bbox_inches='tight', facecolor='white')
        plt.close()
        
        print(f"Professional zodiac wheel created: {filepath}")
        return filepath
    
    def _draw_zodiac_wheel_background(self, ax):
        """Draw the zodiac wheel background with enhanced design."""
        # Draw outer circle
        outer_circle = Circle((0, 0), 5, fill=False, linewidth=2, color='black')
        ax.add_patch(outer_circle)
        
        # Draw inner circle for planets
        inner_circle = Circle((0, 0), 3.5, fill=False, linewidth=1, color='gray')
        ax.add_patch(inner_circle)
        
        # Draw zodiac sign sectors
        for i, sign in enumerate(self.zodiac_signs):
            start_angle = i * 30
            end_angle = (i + 1) * 30
            
            # Create sector wedge
            wedge = patches.Wedge((0, 0), 5, start_angle, end_angle, 
                                width=1.5, facecolor=sign['color'], alpha=0.3,
                                edgecolor='black', linewidth=1)
            ax.add_patch(wedge)
            
            # Add sign symbol and name
            angle_mid = math.radians(start_angle + 15)
            x_text = 4.2 * math.cos(angle_mid)
            y_text = 4.2 * math.sin(angle_mid)
            
            # Sign symbol
            ax.text(x_text, y_text, sign['symbol'], fontsize=16, fontweight='bold',
                   ha='center', va='center', color='black')
            
            # Sign name (Sanskrit)
            x_name = 3.7 * math.cos(angle_mid)
            y_name = 3.7 * math.sin(angle_mid)
            ax.text(x_name, y_name, sign['sanskrit'][:4], fontsize=8, 
                   ha='center', va='center', color='darkblue', fontweight='bold')
    
    def _plot_professional_planets(self, ax, planetary_positions):
        """Plot planets using professional PyJHora positions."""
        for planet_name, position_data in planetary_positions.items():
            if planet_name in self.planet_info:
                longitude = position_data['longitude']
                
                # Convert longitude to position on wheel
                # In astrology, 0° Aries is at 3 o'clock position
                angle_rad = math.radians(90 - longitude)  # Convert to standard math coordinates
                
                # Position planet on the wheel
                radius = 3.0  # Inside the zodiac ring
                x = radius * math.cos(angle_rad)
                y = radius * math.sin(angle_rad)
                
                planet_info = self.planet_info[planet_name]
                
                # Draw planet circle
                planet_circle = Circle((x, y), 0.15, facecolor=planet_info['color'], 
                                     edgecolor='black', linewidth=2, alpha=0.8)
                ax.add_patch(planet_circle)
                
                # Add planet symbol
                ax.text(x, y, planet_info['symbol'], fontsize=12, fontweight='bold',
                       ha='center', va='center', color='white')
                
                # Add degree label
                degree_text = f"{longitude:.1f}°"
                ax.text(x, y-0.35, degree_text, fontsize=6, ha='center', va='center',
                       bbox=dict(boxstyle="round,pad=0.2", facecolor='white', alpha=0.8))
                
                # Add Sanskrit name
                ax.text(x, y+0.35, planet_info['sanskrit'][:4], fontsize=6, 
                       ha='center', va='center', fontweight='bold', color='darkred')
    
    def _add_professional_info_panel(self, ax, date_time, astro_data, panchanga, moon_phase):
        """Add professional information panel with PyJHora data."""
        # Create info box
        info_box = FancyBboxPatch((-6, -6), 12, 1.5, boxstyle="round,pad=0.1", 
                                 facecolor='lightblue', alpha=0.8, edgecolor='black')
        ax.add_patch(info_box)
        
        # Title
        ax.text(0, -5.2, 'Professional Astrological Data (PyJHora Swiss Ephemeris)', 
               fontsize=10, fontweight='bold', ha='center', va='center')
        
        # Panchanga information
        panchanga_text = (
            f"Tithi: {panchanga.get('tithi', {}).get('number', 'N/A')} | "
            f"Nakshatra: {panchanga.get('nakshatra', {}).get('number', 'N/A')} | "
            f"Yoga: {panchanga.get('yoga', {}).get('number', 'N/A')} | "
            f"Karana: {panchanga.get('karana', {}).get('number', 'N/A')}"
        )
        ax.text(0, -5.6, panchanga_text, fontsize=8, ha='center', va='center')
        
        # Moon phase and calculation engine
        moon_info = moon_phase.get('phase_name', 'Unknown')
        engine_info = astro_data.get('calculation_engine', 'PyJHora Swiss Ephemeris')
        
        footer_text = f"Moon Phase: {moon_info} | Engine: {engine_info}"
        ax.text(0, -5.9, footer_text, fontsize=7, ha='center', va='center', 
               style='italic', color='darkblue')

def test_professional_zodiac_wheel():
    """Test the professional zodiac wheel generator."""
    print("=== Testing Professional Zodiac Wheel Generator ===")
    
    generator = ProfessionalZodiacWheelGenerator()
    
    # Create wheel for current date/time
    test_date = datetime(2025, 11, 20, 12, 0)
    
    print(f"Generating professional zodiac wheel for {test_date}")
    chart_path = generator.create_professional_zodiac_wheel(date_time=test_date)
    
    print(f"✅ SUCCESS: Professional zodiac wheel created at {chart_path}")
    print("🎯 Now using PyJHora Swiss Ephemeris for professional accuracy!")
    
    return chart_path

if __name__ == "__main__":
    test_professional_zodiac_wheel()