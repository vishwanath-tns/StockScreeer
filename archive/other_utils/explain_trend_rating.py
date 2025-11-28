#!/usr/bin/env python3
"""
Test and explain the current trend rating system.
"""

from services.trends_service import calculate_trend_rating

def test_trend_rating_scenarios():
    """Test various trend combinations to show the rating system."""
    print("Current Trend Rating System:")
    print("=" * 50)
    print("Rating Scale: -3 (most bearish) to +3 (most bullish)")
    print("Each trend contributes: UP = +1, DOWN = -1")
    print("Formula: daily + weekly + monthly = rating")
    print()
    
    scenarios = [
        ("UP", "UP", "UP", "All trends bullish"),
        ("DOWN", "DOWN", "DOWN", "All trends bearish"),
        ("DOWN", "UP", "UP", "Daily down, weekly & monthly up (your scenario)"),
        ("UP", "DOWN", "DOWN", "Daily up, weekly & monthly down"),
        ("UP", "UP", "DOWN", "Daily & weekly up, monthly down"),
        ("DOWN", "DOWN", "UP", "Daily & weekly down, monthly up"),
        ("UP", "DOWN", "UP", "Mixed signals - daily & monthly up"),
        ("DOWN", "UP", "DOWN", "Mixed signals - only weekly up"),
    ]
    
    print("Test Results:")
    print("-" * 80)
    print(f"{'Daily':<8} {'Weekly':<8} {'Monthly':<8} {'Rating':<8} {'Description'}")
    print("-" * 80)
    
    for daily, weekly, monthly, description in scenarios:
        rating = calculate_trend_rating(daily, weekly, monthly)
        print(f"{daily:<8} {weekly:<8} {monthly:<8} {rating:<8} {description}")
    
    print("-" * 80)
    print()
    print("Rating Interpretation:")
    print("  +3: Strongly Bullish (all timeframes up)")
    print("  +2: Bullish (2 up, 1 down)")
    print("  +1: Moderately Bullish (2 up, 1 down)")
    print("   0: Neutral (mixed signals)")
    print("  -1: Moderately Bearish (1 up, 2 down)")
    print("  -2: Bearish (1 up, 2 down)")
    print("  -3: Strongly Bearish (all timeframes down)")
    print()
    
    # Answer the specific question
    print("ANSWER TO YOUR QUESTION:")
    print("If Daily=DOWN, Weekly=UP, Monthly=UP:")
    rating = calculate_trend_rating("DOWN", "UP", "UP")
    print(f"Rating = {rating} (Moderately Bullish)")
    print("Interpretation: Despite short-term weakness, medium and long-term trends are positive")

if __name__ == "__main__":
    test_trend_rating_scenarios()