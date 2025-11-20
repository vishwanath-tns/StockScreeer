"""
Get and Print Moon Cycles for 2024-2025

This script retrieves the list of moon cycles (lunar phases, nakshatras, etc.)
for the years 2024 and 2025 from the MySQL database using the MoonCycleAnalyzer.
If the data is missing, it will generate and save it automatically.
"""

import sys
import os
import datetime

# Add the path to import vedic astrology modules
sys.path.append(os.path.join(os.path.dirname(__file__), 'calculations'))

from moon_cycle_analyzer import MoonCycleAnalyzer

# Set the date range
start_date = datetime.date(2024, 1, 1)
end_date = datetime.date(2025, 12, 31)

print("=== Moon Cycles 2024-2025 ===")
print(f"Fetching lunar data from {start_date} to {end_date}")

try:
    analyzer = MoonCycleAnalyzer()  # Uses MySQL connection from environment
    
    df = analyzer.get_lunar_data(start_date, end_date)
    
    if df.empty:
        print("No data found in database for 2024-2025. Generating and saving...")
        lunar_calendar = analyzer.generate_lunar_calendar(start_date, end_date)
        success = analyzer.save_lunar_calendar(lunar_calendar)
        if success:
            print("Data saved successfully!")
            df = analyzer.get_lunar_data(start_date, end_date)
        else:
            print("Failed to save data to database.")
            exit(1)
    
    print(f"\nTotal records found: {len(df)}")
    print("\nFirst 10 records:")
    print(df[['date', 'phase', 'nakshatra', 'illumination', 'volatility_score', 'suggested_strategy']].head(10))
    
    print("\nPhase distribution:")
    phase_counts = df['phase'].value_counts()
    for phase, count in phase_counts.items():
        print(f"  {phase}: {count} days")
    
    print("\nNakshatra distribution:")
    nakshatra_counts = df['nakshatra'].value_counts().head(5)
    for nakshatra, count in nakshatra_counts.items():
        print(f"  {nakshatra}: {count} days")
    
    # Export to CSV
    csv_file = os.path.join(os.path.dirname(__file__), 'moon_cycles_2024_2025.csv')
    df.to_csv(csv_file, index=False)
    print(f"\nData exported to: {csv_file}")
    
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
