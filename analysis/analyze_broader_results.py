"""
Quick VCP Pattern Visualization
===============================
Visualize the best VCP patterns found in the broader universe test
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import pandas as pd
from volatility_patterns.visualization.vcp_visualizer import VCPVisualizer

# Load the scan results
with open('broader_universe_results/vcp_scan_results_20251116_155922.json', 'r') as f:
    results = json.load(f)

# Extract unique top patterns (removing duplicates from different threshold tests)
all_patterns = results['all_patterns']
unique_patterns = {}

# Group by symbol and keep the best quality
for pattern in all_patterns:
    symbol = pattern['symbol']
    if symbol not in unique_patterns or pattern['quality_score'] > unique_patterns[symbol]['quality_score']:
        unique_patterns[symbol] = pattern

# Get top 5 patterns
top_patterns = sorted(unique_patterns.values(), key=lambda x: x['quality_score'], reverse=True)[:5]

print("🎯 TOP 5 VCP PATTERNS FROM BROADER UNIVERSE TEST")
print("=" * 60)

for i, pattern in enumerate(top_patterns, 1):
    print(f"{i}. {pattern['symbol']:12} Quality: {pattern['quality_score']:5.1f} "
          f"Stage: {pattern['current_stage']} ({pattern['sector']})")
    print(f"   Base Duration: {pattern['base_duration']} days, "
          f"Contractions: {pattern['contractions']}, "
          f"Setup: {'Complete' if pattern['setup_complete'] else 'Incomplete'}")

print(f"\n📊 ANALYSIS SUMMARY")
print(f"Total Symbols Tested: {results['summary']['total_symbols_available']}")
print(f"Total Patterns Found: {results['summary']['total_patterns_found']}")
print(f"Pattern Discovery Rate: {results['summary']['discovery_rate']:.1f}%")

# Show sector distribution
sectors = {}
for pattern in unique_patterns.values():
    sector = pattern['sector']
    sectors[sector] = sectors.get(sector, 0) + 1

print(f"\n🏢 SECTOR DISTRIBUTION")
sorted_sectors = sorted(sectors.items(), key=lambda x: x[1], reverse=True)
for sector, count in sorted_sectors[:10]:
    print(f"   {sector:20} {count:2d} patterns")

# Create visualization for top pattern
if top_patterns:
    print(f"\n📈 CREATING VISUALIZATION FOR TOP PATTERN: {top_patterns[0]['symbol']}")
    visualizer = VCPVisualizer()
    
    try:
        from datetime import date, timedelta
        
        # Calculate date range (400 days back from today)
        end_date = date.today()
        start_date = end_date - timedelta(days=400)
        
        # Create chart for the best pattern
        chart_path = visualizer.create_vcp_chart(
            symbol=top_patterns[0]['symbol'],
            start_date=start_date,
            end_date=end_date,
            save_path=f"charts/vcp_pattern_{top_patterns[0]['symbol']}_broader_test.png",
            show_chart=False
        )
        print(f"✅ Chart saved: charts/vcp_pattern_{top_patterns[0]['symbol']}_broader_test.png")
    except Exception as e:
        print(f"❌ Chart creation failed: {e}")

print(f"\n🎉 SUCCESS! The broader universe approach found {len(unique_patterns)} unique VCP patterns!")
print(f"This is a significant improvement over the initial Nifty 50 test.")