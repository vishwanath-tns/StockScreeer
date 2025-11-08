#!/usr/bin/env python3
"""
Clear demonstration of the trend rating calculation.
"""

def show_calculation_step_by_step():
    """Show exactly how UP + UP + DOWN = +1"""
    print("Trend Rating Calculation - Step by Step")
    print("=" * 50)
    print()
    
    print("Current System Values:")
    print("  UP   = +1")
    print("  DOWN = -1")
    print()
    
    print("Calculation for: UP + UP + DOWN")
    print("-" * 30)
    print("Daily trend:   UP   = +1")
    print("Weekly trend:  UP   = +1") 
    print("Monthly trend: DOWN = -1")
    print("-" * 30)
    print("Total rating = (+1) + (+1) + (-1)")
    print("             = +2 - 1")
    print("             = +1")
    print()
    
    # Verify with the actual function
    from services.trends_service import calculate_trend_rating
    
    rating = calculate_trend_rating("UP", "UP", "DOWN")
    print(f"Verification with actual function: {rating}")
    print()
    
    print("All Possible Combinations:")
    print("-" * 50)
    
    combinations = [
        ("UP", "UP", "UP"),
        ("UP", "UP", "DOWN"),
        ("UP", "DOWN", "UP"),
        ("DOWN", "UP", "UP"),
        ("UP", "DOWN", "DOWN"),
        ("DOWN", "UP", "DOWN"),
        ("DOWN", "DOWN", "UP"),
        ("DOWN", "DOWN", "DOWN"),
    ]
    
    for daily, weekly, monthly in combinations:
        rating = calculate_trend_rating(daily, weekly, monthly)
        daily_val = 1 if daily == "UP" else -1
        weekly_val = 1 if weekly == "UP" else -1
        monthly_val = 1 if monthly == "UP" else -1
        
        print(f"{daily:4} + {weekly:4} + {monthly:4} = "
              f"({daily_val:+2}) + ({weekly_val:+2}) + ({monthly_val:+2}) = {rating:+2}")

if __name__ == "__main__":
    show_calculation_step_by_step()