#!/usr/bin/env python3
"""
Updated DrikPanchang Validation Tool
Using the detailed reference data from your latest DrikPanchang screenshot
November 20, 2025 - Complete planetary positions with precise coordinates
"""

import sys
import os
sys.path.append('../tools')

from pyjhora_calculator import ProfessionalAstrologyCalculator
from datetime import datetime
import pandas as pd
from typing import Dict, List

class UpdatedDrikPanchangValidator:
    """
    Updated validation tool with precise DrikPanchang reference data
    """
    
    def __init__(self):
        self.calculator = ProfessionalAstrologyCalculator()
        self.reference_data = self.parse_detailed_drikpanchang_reference()
        
    def parse_detailed_drikpanchang_reference(self) -> Dict:
        """
        Parse the latest real-time DrikPanchang reference data from your screenshot
        November 20, 2025 - Current live positions with precise coordinates
        """
        reference = {
            'date': '2025-11-20',
            'location': 'India (DrikPanchang Real-time)',
            'planets': {
                'Lagna': {
                    'dms': "23° Dhan 26' 13\"",
                    'longitude': 240 + 23 + 26/60 + 13/3600,  # 263.437°
                    'nakshatra': 'P Ashadha',
                    'pada': 4,
                    'lords': ['Shukra', 'Shani']
                },
                'Sun': {  # Surya
                    'dms': "03° Vish 53' 50\"",
                    'longitude': 210 + 3 + 53/60 + 50/3600,  # 213.897°
                    'nakshatra': 'Anuradha',
                    'pada': 1,
                    'lords': ['Shani', 'Shani']
                },
                'Moon': {  # Chandra
                    'dms': "03° Vish 05' 05\"",
                    'longitude': 210 + 3 + 5/60 + 5/3600,  # 213.085°
                    'nakshatra': 'Vishakha', 
                    'pada': 4,
                    'lords': ['Guru', 'Rahu']
                },
                'Mars': {  # Mangal
                    'dms': "17° Vish 07' 03\"",
                    'longitude': 210 + 17 + 7/60 + 3/3600,  # 227.118°
                    'nakshatra': 'Jyeshtha',
                    'pada': 1, 
                    'lords': ['Budha', 'Budha']
                },
                'Mercury': {  # Budha
                    'dms': "04° Vish 19' 52\"",
                    'longitude': 210 + 4 + 19/60 + 52/3600,  # 214.331°
                    'nakshatra': 'Anuradha',
                    'pada': 1,
                    'lords': ['Shani', 'Shani']
                },
                'Jupiter': {  # Guru
                    'dms': "00° Kark 48' 20\"",
                    'longitude': 90 + 0 + 48/60 + 20/3600,  # 90.806°
                    'nakshatra': 'Punarvasu', 
                    'pada': 4,
                    'lords': ['Guru', 'Mangal']
                },
                'Venus': {  # Shukra
                    'dms': "22° Tula 24' 35\"",
                    'longitude': 180 + 22 + 24/60 + 35/3600,  # 202.410°
                    'nakshatra': 'Vishakha',
                    'pada': 1,
                    'lords': ['Guru', 'Shani']
                },
                'Saturn': {  # Shani
                    'dms': "00° Meen 59' 19\"",
                    'longitude': 330 + 0 + 59/60 + 19/3600,  # 330.989°
                    'nakshatra': 'P Bhadrapada',
                    'pada': 4,
                    'lords': ['Guru', 'Mangal']
                },
                'Rahu': {
                    'dms': "20° Kumb 09' 24\"", 
                    'longitude': 300 + 20 + 9/60 + 24/3600,  # 320.157°
                    'nakshatra': 'P Bhadrapada',
                    'pada': 1,
                    'lords': ['Guru', 'Guru']
                },
                'Ketu': {
                    'dms': "20° Simh 09' 24\"",
                    'longitude': 120 + 20 + 9/60 + 24/3600,  # 140.157°
                    'nakshatra': 'P Phalguni',
                    'pada': 3,
                    'lords': ['Shukra', 'Guru']
                },
                'True_Rahu': {  # Spashth Rahu
                    'dms': "21° Kumb 13' 19\"",
                    'longitude': 300 + 21 + 13/60 + 19/3600,  # 321.222°
                    'nakshatra': 'P Bhadrapada',
                    'pada': 1,
                    'lords': ['Guru', 'Guru']
                },
                'True_Ketu': {  # Spashth Ketu
                    'dms': "21° Simh 13' 19\"",
                    'longitude': 120 + 21 + 13/60 + 19/3600,  # 141.222°
                    'nakshatra': 'P Phalguni', 
                    'pada': 3,
                    'lords': ['Shukra', 'Guru']
                }
            }
        }
        
        return reference
    
    def calculate_nakshatra_from_longitude(self, longitude: float) -> Dict:
        """Calculate nakshatra and pada from longitude"""
        nakshatra_span = 360 / 27  # 13.333... degrees per nakshatra
        longitude = longitude % 360
        
        nakshatra_number = int(longitude / nakshatra_span) + 1
        position_in_nakshatra = (longitude % nakshatra_span)
        pada_span = nakshatra_span / 4
        pada = int(position_in_nakshatra / pada_span) + 1
        
        nakshatra_names = [
            "Ashwini", "Bharani", "Krittika", "Rohini", "Mrigashira", "Ardra", "Punarvasu",
            "Pushya", "Ashlesha", "Magha", "Purva Phalguni", "Uttara Phalguni", "Hasta",
            "Chitra", "Swati", "Vishakha", "Anuradha", "Jyeshtha", "Mula", "Purva Ashadha",
            "Uttara Ashadha", "Shravana", "Dhanishta", "Shatabhisha", "Purva Bhadrapada",
            "Uttara Bhadrapada", "Revati"
        ]
        
        nakshatra_name = nakshatra_names[nakshatra_number - 1] if 1 <= nakshatra_number <= 27 else "Unknown"
        
        return {
            'nakshatra': nakshatra_name,
            'nakshatra_number': nakshatra_number,
            'pada': pada
        }
    
    def run_comprehensive_validation(self):
        """Run comprehensive validation against updated DrikPanchang data"""
        print("🌟 UPDATED DRIKPANCHANG VALIDATION")
        print("=" * 70)
        print("Reference: DrikPanchang Nov 20, 2025 - REAL-TIME Current Positions")
        print("=" * 70)
        
        # Get current calculations - use current time for real-time comparison
        test_date = datetime.now().replace(second=0, microsecond=0)  # Current time, rounded to minute
        
        try:
            astro_data = self.calculator.get_complete_analysis(test_date)
            our_positions = astro_data.get('planetary_positions', {})
            
            print(f"📅 Test Date: {test_date}")
            print(f"🧮 Calculation Engine: {astro_data.get('calculation_engine', 'Unknown')}")
            print(f"📍 Location: {astro_data.get('location', 'Unknown')}")
            print()
            
        except Exception as e:
            print(f"❌ Error getting calculations: {e}")
            return
        
        # Enhanced nakshatra calculations
        for planet, data in our_positions.items():
            nakshatra_info = self.calculate_nakshatra_from_longitude(data['longitude'])
            data.update(nakshatra_info)
        
        # Planetary position comparison
        print("🪐 DETAILED PLANETARY POSITION COMPARISON")
        print(f"{'Planet':<10} {'DrikPanchang':<12} {'Our Calc':<12} {'Diff(°)':<8} {'Diff(arcsec)':<12} {'Status':<8}")
        print("-" * 75)
        
        results = []
        planet_mapping = {
            'Sun': 'Sun',
            'Moon': 'Moon', 
            'Mars': 'Mars',
            'Mercury': 'Mercury',
            'Jupiter': 'Jupiter',
            'Venus': 'Venus',
            'Saturn': 'Saturn',
            'Rahu': 'Rahu',
            'Ketu': 'Ketu'
        }
        
        for dp_name, our_name in planet_mapping.items():
            if dp_name in self.reference_data['planets'] and our_name in our_positions:
                dp_data = self.reference_data['planets'][dp_name]
                our_data = our_positions[our_name]
                
                dp_long = dp_data['longitude']
                our_long = our_data['longitude']
                
                # Calculate difference
                diff_degrees = abs(dp_long - our_long)
                if diff_degrees > 180:
                    diff_degrees = 360 - diff_degrees
                
                # Convert to arcseconds for precision
                diff_arcseconds = diff_degrees * 3600
                
                # Status based on professional standards
                if diff_arcseconds <= 36:  # 0.01° = 36 arcseconds
                    status = "✅ EXCEL"
                elif diff_arcseconds <= 180:  # 0.05° = 180 arcseconds  
                    status = "✅ GOOD"
                elif diff_arcseconds <= 3600:  # 1.0° = 3600 arcseconds
                    status = "⚠️ FAIR"
                else:
                    status = "❌ POOR"
                
                print(f"{our_name:<10} {dp_long:>10.4f}° {our_long:>10.4f}° {diff_degrees:>6.4f} {diff_arcseconds:>6.1f} {status}")
                
                results.append({
                    'planet': our_name,
                    'drikpanchang_longitude': dp_long,
                    'our_longitude': our_long,
                    'difference_degrees': diff_degrees,
                    'difference_arcseconds': diff_arcseconds,
                    'status': status
                })
        
        print()
        
        # Nakshatra comparison
        print("🌟 NAKSHATRA & PADA COMPARISON")
        print(f"{'Planet':<10} {'DrikPanchang':<15} {'Our Calc':<15} {'DP Pada':<8} {'Our Pada':<8} {'Match':<6}")
        print("-" * 75)
        
        nakshatra_results = []
        
        for dp_name, our_name in planet_mapping.items():
            if dp_name in self.reference_data['planets'] and our_name in our_positions:
                dp_data = self.reference_data['planets'][dp_name]
                our_data = our_positions[our_name]
                
                dp_nak = dp_data['nakshatra']
                dp_pada = dp_data['pada']
                our_nak = our_data['nakshatra']
                our_pada = our_data['pada']
                
                # Normalize nakshatra names for comparison
                dp_nak_norm = dp_nak.replace('P ', 'Purva ').replace('U ', 'Uttara ')
                our_nak_norm = our_nak
                
                # Check for match
                if dp_nak_norm.lower() == our_nak_norm.lower():
                    nak_match = "✅"
                elif any(word in our_nak_norm.lower() for word in dp_nak_norm.lower().split()):
                    nak_match = "⚠️"
                else:
                    nak_match = "❌"
                
                pada_match = "✅" if dp_pada == our_pada else "❌"
                overall_match = "✅" if nak_match == "✅" and pada_match == "✅" else nak_match
                
                print(f"{our_name:<10} {dp_nak:<15} {our_nak:<15} {dp_pada:<8} {our_pada:<8} {overall_match}")
                
                nakshatra_results.append({
                    'planet': our_name,
                    'dp_nakshatra': dp_nak,
                    'our_nakshatra': our_nak,
                    'dp_pada': dp_pada,
                    'our_pada': our_pada,
                    'nakshatra_match': nak_match == "✅",
                    'pada_match': pada_match == "✅",
                    'overall_match': overall_match == "✅"
                })
        
        print()
        
        # Statistical summary
        print("📊 VALIDATION STATISTICS")
        print("=" * 40)
        
        total_planets = len(results)
        excellent = len([r for r in results if 'EXCEL' in r['status']])
        good = len([r for r in results if 'GOOD' in r['status']])
        fair = len([r for r in results if 'FAIR' in r['status']])
        poor = len([r for r in results if 'POOR' in r['status']])
        
        avg_diff_arcsec = sum(r['difference_arcseconds'] for r in results) / total_planets if results else 0
        max_diff_arcsec = max((r['difference_arcseconds'] for r in results), default=0)
        min_diff_arcsec = min((r['difference_arcseconds'] for r in results), default=0)
        
        nakshatra_matches = sum(1 for r in nakshatra_results if r['overall_match'])
        pada_matches = sum(1 for r in nakshatra_results if r['pada_match'])
        
        print(f"Planetary Position Accuracy:")
        print(f"  Excellent (≤0.01°): {excellent}/{total_planets} ({excellent/total_planets*100:.1f}%)")
        print(f"  Good (≤0.05°): {good}/{total_planets} ({good/total_planets*100:.1f}%)")
        print(f"  Fair (≤1.0°): {fair}/{total_planets} ({fair/total_planets*100:.1f}%)")
        print(f"  Poor (>1.0°): {poor}/{total_planets} ({poor/total_planets*100:.1f}%)")
        print(f"  Average difference: {avg_diff_arcsec:.1f} arcseconds")
        print(f"  Maximum difference: {max_diff_arcsec:.1f} arcseconds")
        print(f"  Minimum difference: {min_diff_arcsec:.1f} arcseconds")
        
        print(f"\nNakshatra & Pada Accuracy:")
        print(f"  Complete matches: {nakshatra_matches}/{len(nakshatra_results)} ({nakshatra_matches/len(nakshatra_results)*100:.1f}%)")
        print(f"  Pada matches: {pada_matches}/{len(nakshatra_results)} ({pada_matches/len(nakshatra_results)*100:.1f}%)")
        
        # Overall grade
        professional_accuracy = (excellent + good) / total_planets * 100 if total_planets > 0 else 0
        
        if professional_accuracy >= 90:
            grade = "A+ (Professional)"
        elif professional_accuracy >= 80:
            grade = "A (Excellent)"
        elif professional_accuracy >= 70:
            grade = "B+ (Very Good)"
        elif professional_accuracy >= 60:
            grade = "B (Good)"
        else:
            grade = "C (Needs Improvement)"
        
        print(f"\nOVERALL GRADE: {grade}")
        print(f"Professional Accuracy: {professional_accuracy:.1f}%")
        
        # Save detailed results
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        results_df = pd.DataFrame(results)
        results_df.to_csv(f"detailed_validation_{timestamp}.csv", index=False)
        print(f"\n💾 Detailed results saved to: detailed_validation_{timestamp}.csv")
        
        return results, nakshatra_results

def main():
    """Main validation function"""
    print("🌟 UPDATED DRIKPANCHANG VALIDATION TOOL")
    print("Using REAL-TIME planetary positions from your latest DrikPanchang screenshot")
    print("November 20, 2025 - Live current positions with arcsecond precision")
    print()
    
    validator = UpdatedDrikPanchangValidator()
    planetary_results, nakshatra_results = validator.run_comprehensive_validation()
    
    print("\n" + "=" * 70)
    print("🎯 VALIDATION COMPLETE")
    print("=" * 70)
    print("This validation uses your precise DrikPanchang reference data")
    print("with degrees, minutes, and seconds accuracy for all planets.")

if __name__ == "__main__":
    main()