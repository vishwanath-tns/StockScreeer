#!/usr/bin/env python3
"""Test script for Index Rating Service."""
import sys
sys.path.insert(0, '.')

from ranking.services.index_rating_service import IndexRatingService, get_letter_rating

service = IndexRatingService()

print("Available indices:")
for symbol, name, count in service.get_available_indices():
    print(f"  {symbol}: {name} ({count} records)")

print()
print("="*80)
print("Sector Ratings (as of latest data):")
print("="*80)

try:
    ratings = service.calculate_ratings()
    
    header = f"{'Rank':<5} {'Sector':<20} {'RS':<6} {'Mom':<6} {'Trend':<6} {'Comp':<6} {'1W%':<8} {'1M%':<8} {'Rating'}"
    print(f"\n{header}")
    print("-" * 85)
    
    for i, r in enumerate(ratings, 1):
        letter = get_letter_rating(r.composite_score)
        print(f"{i:<5} {r.name:<20} {r.rs_rating:>5.1f} {r.momentum_score:>5.1f} "
              f"{r.trend_score:>5.1f} {r.composite_score:>5.1f} {r.return_1w:>7.2f}% "
              f"{r.return_1m:>7.2f}% {letter}")
    
    print("\n" + "="*80)
    analysis = service.get_sector_rotation_analysis()
    
    if analysis.get("leading_sectors"):
        print("\n🚀 LEADING SECTORS (Score >= 70):")
        for r in analysis["leading_sectors"]:
            print(f"  • {r.name}: {r.composite_score:.1f} (RS: {r.rs_rating:.0f}, 1M: {r.return_1m:+.1f}%)")
    
    if analysis.get("improving_sectors"):
        print("\n📈 IMPROVING SECTORS:")
        for r in analysis["improving_sectors"]:
            print(f"  • {r.name}: {r.composite_score:.1f} (RS: {r.rs_rating:.0f}, 1M: {r.return_1m:+.1f}%)")
    
    if analysis.get("lagging_sectors"):
        print("\n📉 LAGGING SECTORS (Score < 50):")
        for r in analysis["lagging_sectors"]:
            print(f"  • {r.name}: {r.composite_score:.1f} (RS: {r.rs_rating:.0f}, 1M: {r.return_1m:+.1f}%)")

except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
