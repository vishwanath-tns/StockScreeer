#!/usr/bin/env python3
"""
DrikPanchang Validation Tool
Compares PyJHora calculations against DrikPanchang reference data
Professional accuracy validation for Vedic astrology calculations
"""

import sys
import os
sys.path.append('../tools')

from pyjhora_calculator import ProfessionalAstrologyCalculator
from datetime import datetime
import re
from typing import Dict, List, Tuple
import pandas as pd

class DrikPanchangValidator:
    """
    Professional validation tool comparing PyJHora vs DrikPanchang
    """
    
    def __init__(self):
        self.calculator = ProfessionalAstrologyCalculator()
        self.reference_data = self.parse_drikpanchang_reference()
        self.validation_results = []
        
    def parse_drikpanchang_reference(self) -> Dict:
        """
        Parse the DrikPanchang reference data from your screenshot
        Data for November 20, 2025
        """
        reference = {
            'date': '2025-11-20',
            'location': 'Delhi',  # Assuming Delhi based on our tests
            
            # Planetary positions from your DrikPanchang screenshot
            # Converting to absolute longitude (0-360°)
            'planets': {
                'Lagna': {
                    'longitude': 240 + 18 + 4/60 + 14/3600,  # Dhanu (Sagittarius) = 240° + 18°04'14"
                    'sign': 'Dhanu',  # Sagittarius
                    'nakshatra': 'P Ashadha',
                    'pada': 2,
                    'lord': 'Shukra, Mangal'
                },
                'Surya': {  # Sun - 03° Vish 52' 54"
                    'longitude': 210 + 3 + 52/60 + 54/3600,  # Vrishchika (Scorpio) = 210° + 3°52'54"
                    'sign': 'Vrishchika',  # Scorpio  
                    'nakshatra': 'Anuradha',
                    'pada': 1,
                    'lord': 'Shani, Shani'
                },
                'Chandra': {  # Moon - 02° Vish 54' 10"
                    'longitude': 210 + 2 + 54/60 + 10/3600,  # Vrishchika (Scorpio) = 210° + 2°54'10"
                    'sign': 'Vrishchika',  # Scorpio
                    'nakshatra': 'Vishakha',
                    'pada': 4,
                    'lord': 'Guru, Rahu'
                },
                'Mangal': {  # Mars - 17° Vish 06' 22"
                    'longitude': 210 + 17 + 6/60 + 22/3600,  # Vrishchika (Scorpio) = 210° + 17°06'22"
                    'sign': 'Vrishchika',  # Scorpio
                    'nakshatra': 'Jyeshtha',
                    'pada': 1,
                    'lord': 'Budha, Budha'
                },
                'Budha': {  # Mercury - 04° Vish 21' 07"
                    'longitude': 210 + 4 + 21/60 + 7/3600,  # Vrishchika (Scorpio) = 210° + 4°21'07"
                    'sign': 'Vrishchika',  # Scorpio
                    'nakshatra': 'Anuradha',
                    'pada': 1,
                    'lord': 'Shani, Shani'
                },
                'Guru': {  # Jupiter - 00° Kark 48' 22"
                    'longitude': 90 + 0 + 48/60 + 22/3600,  # Karkata (Cancer) = 90° + 0°48'22"
                    'sign': 'Karkata',  # Cancer
                    'nakshatra': 'Punarvasu',
                    'pada': 4,
                    'lord': 'Guru, Mangal'
                },
                'Shukra': {  # Venus - 22° Tula 23' 25"
                    'longitude': 180 + 22 + 23/60 + 25/3600,  # Tula (Libra) = 180° + 22°23'25"
                    'sign': 'Tula',  # Libra
                    'nakshatra': 'Vishakha',
                    'pada': 1,
                    'lord': 'Guru, Shani'
                },
                'Shani': {  # Saturn - 00° Meen 59' 19"
                    'longitude': 330 + 0 + 59/60 + 19/3600,  # Meena (Pisces) = 330° + 0°59'19"
                    'sign': 'Meena',  # Pisces
                    'nakshatra': 'P Bhadrapada',
                    'pada': 4,
                    'lord': 'Guru, Mangal'
                },
                'Rahu': {  # 20° Kumb 09' 27"
                    'longitude': 300 + 20 + 9/60 + 27/3600,  # Kumbha (Aquarius) = 300° + 20°09'27"
                    'sign': 'Kumbha',  # Aquarius
                    'nakshatra': 'P Bhadrapada',
                    'pada': 1,
                    'lord': 'Guru, Guru'
                },
                'Ketu': {  # 20° Simh 09' 27"
                    'longitude': 120 + 20 + 9/60 + 27/3600,  # Simha (Leo) = 120° + 20°09'27"
                    'sign': 'Simha',  # Leo
                    'nakshatra': 'P Phalguni',
                    'pada': 3,
                    'lord': 'Shukra, Guru'
                }
            }
        }
        
        return reference
    
    def parse_dms_to_decimal(self, dms_string: str) -> float:
        """
        Parse degrees-minutes-seconds string to decimal degrees
        Example: "03° Vish 52' 54\"" -> convert to decimal
        """
        try:
            # Extract the degree, minute, second values
            # Pattern: "03° Vish 52' 54\""
            
            # First extract the degree part
            degree_match = re.search(r'(\d+)°', dms_string)
            if not degree_match:
                return 0.0
            
            degrees = int(degree_match.group(1))
            
            # Extract minutes
            minute_match = re.search(r"(\d+)'", dms_string)
            minutes = int(minute_match.group(1)) if minute_match else 0
            
            # Extract seconds
            second_match = re.search(r'(\d+)"', dms_string)
            seconds = int(second_match.group(1)) if second_match else 0
            
            # Determine sign offset based on sign name
            sign_offsets = {
                'Mesh': 0,     'Vribha': 30,   'Mithun': 60,   'Kark': 90,
                'Simh': 120,   'Kanya': 150,   'Tula': 180,    'Vish': 210,
                'Dhan': 240,   'Maka': 270,    'Kumb': 300,    'Meen': 330
            }
            
            # Find sign name in the string
            sign_offset = 0
            for sign, offset in sign_offsets.items():
                if sign in dms_string:
                    sign_offset = offset
                    break
            
            # Convert to decimal
            decimal_degrees = degrees + minutes/60.0 + seconds/3600.0
            total_longitude = sign_offset + decimal_degrees
            
            return total_longitude
            
        except Exception as e:
            print(f"Error parsing DMS string '{dms_string}': {e}")
            return 0.0
    
    def get_our_calculations(self, test_date: datetime = None) -> Dict:
        """Get our PyJHora calculations for comparison"""
        if test_date is None:
            # Use November 20, 2025 to match DrikPanchang reference
            test_date = datetime(2025, 11, 20, 5, 30, 0)  # 5:30 AM IST
        
        try:
            astro_data = self.calculator.get_complete_analysis(test_date)
            
            # Add nakshatra calculation for each planet
            if 'planetary_positions' in astro_data:
                for planet_name, planet_data in astro_data['planetary_positions'].items():
                    longitude = planet_data.get('longitude', 0)
                    nakshatra_info = self.calculate_nakshatra_from_longitude(longitude)
                    planet_data.update(nakshatra_info)
            
            return astro_data
        except Exception as e:
            print(f"Error getting our calculations: {e}")
            return {}
    
    def calculate_nakshatra_from_longitude(self, longitude: float) -> Dict:
        """Calculate nakshatra and pada from longitude"""
        try:
            # Nakshatra calculation: Each nakshatra is 13.333... degrees
            nakshatra_span = 360 / 27  # 13.333... degrees per nakshatra
            
            # Normalize longitude to 0-360
            longitude = longitude % 360
            
            # Calculate nakshatra number (1-27)
            nakshatra_number = int(longitude / nakshatra_span) + 1
            
            # Calculate position within nakshatra for pada (1-4)
            position_in_nakshatra = (longitude % nakshatra_span)
            pada_span = nakshatra_span / 4  # Each nakshatra has 4 padas
            pada = int(position_in_nakshatra / pada_span) + 1
            
            # Nakshatra names (27 total)
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
                'pada': pada,
                'position_in_nakshatra_degrees': position_in_nakshatra
            }
            
        except Exception as e:
            print(f"Error calculating nakshatra for longitude {longitude}: {e}")
            return {
                'nakshatra': 'Unknown',
                'nakshatra_number': 0,
                'pada': 0,
                'position_in_nakshatra_degrees': 0
            }
    
    def compare_planetary_positions(self) -> List[Dict]:
        """
        Compare planetary positions between PyJHora and DrikPanchang
        """
        print("🔍 COMPARING PLANETARY POSITIONS: PYJHORA vs DRIKPANCHANG")
        print("=" * 70)
        
        # Get our calculations - use exact date from DrikPanchang reference
        test_date = datetime(2025, 11, 20, 5, 30, 0)  # 5:30 AM IST for accurate Lagna
        print(f"📅 Test Date: {test_date}")
        our_data = self.get_our_calculations(test_date)
        
        if not our_data:
            print("❌ Failed to get our calculations")
            return []
            
        print(f"📍 Our raw planetary data keys: {list(our_data.keys())}")
        if 'planetary_positions' in our_data:
            print(f"🌟 Available planets: {list(our_data['planetary_positions'].keys())}")
        
        our_planets = our_data.get('planetary_positions', {})
        our_ascendant = our_data.get('ascendant', {})
        
        # Comparison results
        comparisons = []
        
        # Planet mapping between our names and DrikPanchang names
        planet_mapping = {
            'Surya': 'Sun',
            'Chandra': 'Moon', 
            'Mangal': 'Mars',
            'Budha': 'Mercury',
            'Guru': 'Jupiter',
            'Shukra': 'Venus',
            'Shani': 'Saturn',
            'Rahu': 'Rahu',
            'Ketu': 'Ketu'
        }
        
        print(f"{'Planet':<12} {'DrikPanchang':<15} {'PyJHora':<15} {'Difference':<12} {'Status':<8}")
        print("-" * 70)
        
        # Compare main planets
        for dp_name, our_name in planet_mapping.items():
            if dp_name in self.reference_data['planets'] and our_name in our_planets:
                dp_long = self.reference_data['planets'][dp_name]['longitude']
                our_long = our_planets[our_name]['longitude']
                
                # Calculate difference in degrees
                diff_degrees = abs(dp_long - our_long)
                
                # Handle 360° wraparound
                if diff_degrees > 180:
                    diff_degrees = 360 - diff_degrees
                
                # Convert to arcseconds for precision
                diff_arcseconds = diff_degrees * 3600
                
                # Determine status
                if diff_arcseconds <= 3.6:  # Within 0.01 degrees
                    status = "✅ PASS"
                elif diff_arcseconds <= 18:  # Within 0.05 degrees
                    status = "⚠️ WARN"
                else:
                    status = "❌ FAIL"
                
                print(f"{our_name:<12} {dp_long:>13.4f}° {our_long:>13.4f}° {diff_degrees:>10.4f}° {status}")
                
                # Store detailed comparison
                comparison = {
                    'planet': our_name,
                    'drikpanchang_longitude': dp_long,
                    'pyjhora_longitude': our_long,
                    'difference_degrees': diff_degrees,
                    'difference_arcseconds': diff_arcseconds,
                    'status': status,
                    'drikpanchang_nakshatra': self.reference_data['planets'][dp_name]['nakshatra'],
                    'pyjhora_nakshatra': our_planets[our_name].get('nakshatra', 'Unknown'),
                    'drikpanchang_pada': self.reference_data['planets'][dp_name]['pada'],
                    'pyjhora_pada': our_planets[our_name].get('pada', 0)
                }
                
                comparisons.append(comparison)
        
        # Compare Ascendant (Lagna) if available
        if our_ascendant and 'Lagna' in self.reference_data['planets']:
            dp_asc = self.reference_data['planets']['Lagna']['longitude']
            our_asc = our_ascendant.get('longitude', 0)
            
            diff_degrees = abs(dp_asc - our_asc)
            if diff_degrees > 180:
                diff_degrees = 360 - diff_degrees
            
            diff_arcseconds = diff_degrees * 3600
            
            if diff_arcseconds <= 3.6:
                status = "✅ PASS"
            elif diff_arcseconds <= 18:
                status = "⚠️ WARN"
            else:
                status = "❌ FAIL"
            
            print(f"{'Ascendant':<12} {dp_asc:>13.4f}° {our_asc:>13.4f}° {diff_degrees:>10.4f}° {status}")
            
            comparison = {
                'planet': 'Ascendant',
                'drikpanchang_longitude': dp_asc,
                'pyjhora_longitude': our_asc,
                'difference_degrees': diff_degrees,
                'difference_arcseconds': diff_arcseconds,
                'status': status,
                'drikpanchang_nakshatra': self.reference_data['planets']['Lagna']['nakshatra'],
                'pyjhora_nakshatra': our_ascendant.get('nakshatra', 'Unknown'),
                'drikpanchang_pada': self.reference_data['planets']['Lagna']['pada'],
                'pyjhora_pada': our_ascendant.get('pada', 0)
            }
            
            comparisons.append(comparison)
        
        return comparisons
    
    def compare_nakshatras(self) -> List[Dict]:
        """Compare nakshatra assignments"""
        print("\n🌟 COMPARING NAKSHATRA ASSIGNMENTS")
        print("=" * 60)
        
        # Get our calculations with proper date and time
        test_date = datetime(2025, 11, 20, 5, 30, 0)  # 5:30 AM IST for proper Lagna calculation 
        print(f"📅 Test Date for Nakshatra comparison: {test_date}")
        our_data = self.get_our_calculations(test_date)
        
        if not our_data:
            print("❌ Failed to get our calculations for nakshatras")
            return []
            
        our_planets = our_data.get('planetary_positions', {})
        print(f"🌟 Our planets for nakshatra check: {list(our_planets.keys())}")
        
        # Debug: Check what data we have for one planet
        if our_planets:
            sample_planet = list(our_planets.keys())[0]
            print(f"🔍 Sample planet data for {sample_planet}: {our_planets[sample_planet]}")
        
        nakshatra_comparisons = []
        
        planet_mapping = {
            'Surya': 'Sun',
            'Chandra': 'Moon',
            'Mangal': 'Mars',
            'Budha': 'Mercury',
            'Guru': 'Jupiter',
            'Shukra': 'Venus',
            'Shani': 'Saturn',
            'Rahu': 'Rahu',
            'Ketu': 'Ketu'
        }
        
        print(f"{'Planet':<12} {'DrikPanchang':<15} {'PyJHora':<15} {'Pada DP':<8} {'Pada PyJ':<8} {'Match':<8}")
        print("-" * 75)
        
        for dp_name, our_name in planet_mapping.items():
            if dp_name in self.reference_data['planets'] and our_name in our_planets:
                dp_nak = self.reference_data['planets'][dp_name]['nakshatra']
                our_nak = our_planets[our_name].get('nakshatra', 'Unknown')
                dp_pada = self.reference_data['planets'][dp_name]['pada']
                our_pada = our_planets[our_name].get('pada', 0)
                
                # Simplify nakshatra names for comparison
                dp_nak_simple = dp_nak.replace('P ', '').replace('U ', '')
                our_nak_simple = our_nak.replace('Purva ', '').replace('Uttara ', '')
                
                match = "✅" if dp_nak_simple.lower() in our_nak_simple.lower() else "❌"
                
                print(f"{our_name:<12} {dp_nak:<15} {our_nak:<15} {dp_pada:<8} {our_pada:<8} {match}")
                
                nakshatra_comparisons.append({
                    'planet': our_name,
                    'drikpanchang_nakshatra': dp_nak,
                    'pyjhora_nakshatra': our_nak,
                    'drikpanchang_pada': dp_pada,
                    'pyjhora_pada': our_pada,
                    'match': match == "✅"
                })
        
        return nakshatra_comparisons
    
    def generate_accuracy_report(self) -> Dict:
        """Generate comprehensive accuracy report"""
        print("\n📊 ACCURACY ANALYSIS REPORT")
        print("=" * 50)
        
        # Get comparison results
        planetary_comparisons = self.compare_planetary_positions()
        nakshatra_comparisons = self.compare_nakshatras()
        
        # Calculate statistics
        total_planets = len(planetary_comparisons)
        passed_planets = len([c for c in planetary_comparisons if 'PASS' in c['status']])
        warned_planets = len([c for c in planetary_comparisons if 'WARN' in c['status']])
        failed_planets = len([c for c in planetary_comparisons if 'FAIL' in c['status']])
        
        avg_difference = sum(c['difference_arcseconds'] for c in planetary_comparisons) / total_planets if total_planets > 0 else 0
        max_difference = max((c['difference_arcseconds'] for c in planetary_comparisons), default=0)
        min_difference = min((c['difference_arcseconds'] for c in planetary_comparisons), default=0)
        
        nakshatra_matches = sum(1 for c in nakshatra_comparisons if c['match'])
        nakshatra_total = len(nakshatra_comparisons)
        
        # Display statistics
        print(f"Planetary Position Accuracy:")
        print(f"  Total planets compared: {total_planets}")
        print(f"  Passed (≤0.01°): {passed_planets} ({passed_planets/total_planets*100:.1f}%)")
        print(f"  Warnings (≤0.05°): {warned_planets} ({warned_planets/total_planets*100:.1f}%)")
        print(f"  Failed (>0.05°): {failed_planets} ({failed_planets/total_planets*100:.1f}%)")
        print(f"  Average difference: {avg_difference:.2f} arcseconds")
        print(f"  Maximum difference: {max_difference:.2f} arcseconds")
        print(f"  Minimum difference: {min_difference:.2f} arcseconds")
        
        print(f"\nNakshatra Assignment Accuracy:")
        print(f"  Correct assignments: {nakshatra_matches}/{nakshatra_total} ({nakshatra_matches/nakshatra_total*100:.1f}%)")
        
        # Overall grade
        overall_accuracy = (passed_planets + warned_planets) / total_planets * 100 if total_planets > 0 else 0
        
        if overall_accuracy >= 95:
            grade = "A+"
        elif overall_accuracy >= 90:
            grade = "A"
        elif overall_accuracy >= 85:
            grade = "B+"
        elif overall_accuracy >= 80:
            grade = "B"
        else:
            grade = "C"
        
        print(f"\nOVERALL ACCURACY GRADE: {grade} ({overall_accuracy:.1f}%)")
        
        report = {
            'total_planets': total_planets,
            'passed_planets': passed_planets,
            'warned_planets': warned_planets,
            'failed_planets': failed_planets,
            'avg_difference_arcseconds': avg_difference,
            'max_difference_arcseconds': max_difference,
            'min_difference_arcseconds': min_difference,
            'nakshatra_matches': nakshatra_matches,
            'nakshatra_total': nakshatra_total,
            'overall_accuracy_percent': overall_accuracy,
            'accuracy_grade': grade,
            'planetary_comparisons': planetary_comparisons,
            'nakshatra_comparisons': nakshatra_comparisons
        }
        
        return report
    
    def save_validation_results(self, report: Dict, filename: str = None):
        """Save validation results to CSV file"""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"drikpanchang_validation_{timestamp}.csv"
        
        try:
            # Create DataFrame from planetary comparisons
            df = pd.DataFrame(report['planetary_comparisons'])
            
            # Save to CSV
            df.to_csv(filename, index=False)
            print(f"\n💾 Validation results saved to: {filename}")
            
            # Also save summary
            summary_filename = filename.replace('.csv', '_summary.txt')
            with open(summary_filename, 'w') as f:
                f.write("DRIKPANCHANG VALIDATION SUMMARY\n")
                f.write("=" * 40 + "\n")
                f.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"Overall Grade: {report['accuracy_grade']}\n")
                f.write(f"Overall Accuracy: {report['overall_accuracy_percent']:.1f}%\n")
                f.write(f"Average Difference: {report['avg_difference_arcseconds']:.2f} arcseconds\n")
                f.write(f"Max Difference: {report['max_difference_arcseconds']:.2f} arcseconds\n")
                f.write(f"Planetary Positions: {report['passed_planets']}/{report['total_planets']} passed\n")
                f.write(f"Nakshatra Assignments: {report['nakshatra_matches']}/{report['nakshatra_total']} correct\n")
            
            print(f"📋 Summary saved to: {summary_filename}")
            
        except Exception as e:
            print(f"❌ Error saving results: {e}")

def main():
    """Main validation function"""
    print("🌟 DRIKPANCHANG VALIDATION TOOL")
    print("=" * 50)
    print("Comparing PyJHora vs DrikPanchang for Nov 20, 2025")
    print("=" * 50)
    
    # Initialize validator
    validator = DrikPanchangValidator()
    
    # Run comprehensive validation
    report = validator.generate_accuracy_report()
    
    # Save results
    validator.save_validation_results(report)
    
    # Final assessment
    print("\n" + "=" * 50)
    print("🎯 VALIDATION COMPLETE")
    print("=" * 50)
    
    if report['accuracy_grade'] in ['A+', 'A']:
        print("🎉 EXCELLENT ACCURACY! PyJHora calculations are professional-grade.")
    elif report['accuracy_grade'] in ['B+', 'B']:
        print("✅ GOOD ACCURACY! Minor discrepancies within acceptable range.")
    else:
        print("⚠️ ACCURACY NEEDS IMPROVEMENT. Review calculation methods.")
    
    print(f"📊 Overall Grade: {report['accuracy_grade']}")
    print(f"🎯 Accuracy: {report['overall_accuracy_percent']:.1f}%")
    print(f"📐 Avg Difference: {report['avg_difference_arcseconds']:.2f} arcseconds")

if __name__ == "__main__":
    main()