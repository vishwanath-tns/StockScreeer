#!/usr/bin/env python3
"""
Design and test a better trend rating system.
"""

def calculate_improved_trend_rating(daily_trend: str, weekly_trend: str, monthly_trend: str) -> dict:
    """
    Calculate an improved trend rating with weights and clear descriptions.
    
    Weighting System:
    - Monthly trend: 50% weight (most important - long term direction)
    - Weekly trend: 30% weight (medium term momentum)  
    - Daily trend: 20% weight (short term noise)
    
    Returns:
    - numeric_rating: Float from -10 to +10
    - rating_category: String category
    - description: Detailed explanation
    """
    
    # Convert trends to numeric values
    trend_values = {"UP": 1, "DOWN": -1, "SIDEWAYS": 0}
    
    daily_val = trend_values.get(daily_trend, 0)
    weekly_val = trend_values.get(weekly_trend, 0) 
    monthly_val = trend_values.get(monthly_trend, 0)
    
    # Apply weights (total = 100%)
    weighted_score = (monthly_val * 0.5) + (weekly_val * 0.3) + (daily_val * 0.2)
    
    # Scale to -10 to +10 range for clarity
    numeric_rating = round(weighted_score * 10, 1)
    
    # Determine category and description
    if numeric_rating >= 8:
        category = "VERY BULLISH"
        description = "Strong uptrend across all timeframes"
    elif numeric_rating >= 5:
        category = "BULLISH" 
        description = "Solid uptrend with strong longer-term momentum"
    elif numeric_rating >= 2:
        category = "MODERATELY BULLISH"
        description = "Generally positive with some mixed signals"
    elif numeric_rating >= -2:
        category = "NEUTRAL/MIXED"
        description = "Conflicting signals across timeframes"
    elif numeric_rating >= -5:
        category = "MODERATELY BEARISH"
        description = "Generally negative with some mixed signals"
    elif numeric_rating >= -8:
        category = "BEARISH"
        description = "Solid downtrend with strong longer-term weakness"
    else:
        category = "VERY BEARISH"
        description = "Strong downtrend across all timeframes"
    
    # Add specific context based on trend combination
    context = _get_trend_context(daily_trend, weekly_trend, monthly_trend)
    
    return {
        'numeric_rating': numeric_rating,
        'category': category,
        'description': description,
        'context': context,
        'weights': {
            'monthly': f"{monthly_trend} (50%)",
            'weekly': f"{weekly_trend} (30%)", 
            'daily': f"{daily_trend} (20%)"
        }
    }

def _get_trend_context(daily: str, weekly: str, monthly: str) -> str:
    """Provide specific context based on trend combination."""
    
    if monthly == "UP" and weekly == "UP" and daily == "DOWN":
        return "Short-term pullback in strong uptrend - potential buying opportunity"
    elif monthly == "UP" and weekly == "DOWN" and daily == "UP":
        return "Mixed signals - long-term bullish but medium-term weakness emerging"
    elif monthly == "DOWN" and weekly == "UP" and daily == "UP":
        return "Short-term bounce in downtrend - likely temporary relief rally"
    elif monthly == "DOWN" and weekly == "DOWN" and daily == "UP":
        return "Minor bounce in established downtrend - caution advised"
    elif monthly == "UP" and weekly == "DOWN" and daily == "DOWN":
        return "Long-term uptrend under pressure - watch for trend change"
    elif monthly == "DOWN" and weekly == "UP" and daily == "DOWN":
        return "Consolidation phase - direction unclear"
    elif all(t == "UP" for t in [daily, weekly, monthly]):
        return "Strong bullish momentum across all timeframes"
    elif all(t == "DOWN" for t in [daily, weekly, monthly]):
        return "Strong bearish momentum across all timeframes"
    else:
        return "Mixed trend signals require careful analysis"

def test_improved_rating_system():
    """Test the improved rating system with various scenarios."""
    
    print("IMPROVED TREND RATING SYSTEM")
    print("=" * 60)
    print("Weighting: Monthly 50%, Weekly 30%, Daily 20%")
    print("Scale: -10 (Very Bearish) to +10 (Very Bullish)")
    print()
    
    test_scenarios = [
        ("UP", "UP", "UP", "Perfect bullish alignment"),
        ("DOWN", "DOWN", "DOWN", "Perfect bearish alignment"),
        ("DOWN", "UP", "UP", "Your original question scenario"),
        ("UP", "DOWN", "DOWN", "Opposite scenario"),
        ("UP", "UP", "DOWN", "Strong trend with daily pullback"),
        ("DOWN", "DOWN", "UP", "Strong downtrend with daily bounce"),
        ("UP", "DOWN", "UP", "Mixed medium-term signals"),
        ("DOWN", "UP", "DOWN", "Weekly strength in bearish context"),
    ]
    
    print("RATING SCENARIOS:")
    print("-" * 80)
    print(f"{'Daily':<6} {'Weekly':<7} {'Monthly':<8} {'Rating':<7} {'Category':<18} {'Scenario'}")
    print("-" * 80)
    
    for daily, weekly, monthly, scenario in test_scenarios:
        result = calculate_improved_trend_rating(daily, weekly, monthly)
        rating = result['numeric_rating']
        category = result['category']
        
        print(f"{daily:<6} {weekly:<7} {monthly:<8} {rating:<7} {category:<18} {scenario}")
    
    print("-" * 80)
    print()
    
    # Detailed example
    print("DETAILED EXAMPLE: Daily DOWN, Weekly UP, Monthly UP")
    print("-" * 50)
    result = calculate_improved_trend_rating("DOWN", "UP", "UP")
    
    print(f"Numeric Rating: {result['numeric_rating']}")
    print(f"Category: {result['category']}")
    print(f"Description: {result['description']}")
    print(f"Context: {result['context']}")
    print()
    print("Breakdown:")
    for timeframe, weight_info in result['weights'].items():
        print(f"  {timeframe.capitalize()}: {weight_info}")
    
    print()
    print("Calculation:")
    print("  Monthly UP (1) × 50% = +0.5")
    print("  Weekly UP (1) × 30% = +0.3")  
    print("  Daily DOWN (-1) × 20% = -0.2")
    print("  Total = 0.5 + 0.3 - 0.2 = +0.6")
    print("  Scaled = 0.6 × 10 = +6.0")

if __name__ == "__main__":
    test_improved_rating_system()