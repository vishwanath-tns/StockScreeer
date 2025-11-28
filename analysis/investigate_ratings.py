#!/usr/bin/env python3
"""
Investigate trend rating distribution in the database.
Check why certain ratings (like 0 and 2) might not appear.
"""

import reporting_adv_decl as rad
from sqlalchemy import text
import pandas as pd

def analyze_rating_distribution():
    """Analyze the distribution of trend ratings in the database."""
    engine = rad.engine()
    
    print("Analyzing Trend Rating Distribution")
    print("=" * 50)
    
    with engine.connect() as conn:
        # Overall rating distribution
        sql = text("""
        SELECT trend_rating, COUNT(*) as count, 
               ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM trend_analysis), 2) as percentage
        FROM trend_analysis 
        GROUP BY trend_rating 
        ORDER BY trend_rating
        """)
        
        df = pd.read_sql(sql, con=conn)
        print("Overall Rating Distribution:")
        print(df.to_string(index=False))
        print()
        
        # Check SBIN specifically
        sbin_sql = text("""
        SELECT trend_rating, COUNT(*) as count,
               daily_trend, weekly_trend, monthly_trend, COUNT(*) as combo_count
        FROM trend_analysis 
        WHERE symbol = 'SBIN'
        GROUP BY trend_rating, daily_trend, weekly_trend, monthly_trend
        ORDER BY trend_rating, combo_count DESC
        """)
        
        sbin_df = pd.read_sql(sbin_sql, con=conn)
        print("SBIN Rating Distribution with Trend Combinations:")
        print(sbin_df.to_string(index=False))
        print()
        
        # Check what combinations would give rating 0 and 2
        print("Expected Combinations for Missing Ratings:")
        print("Rating 0 combinations:")
        print("  UP + UP + DOWN = 1 + 1 - 1 = 1 (not 0)")
        print("  UP + DOWN + UP = 1 - 1 + 1 = 1 (not 0)")
        print("  DOWN + UP + UP = -1 + 1 + 1 = 1 (not 0)")
        print("  There are NO combinations that give 0 with UP/DOWN only!")
        print()
        
        print("Rating 2 combinations:")
        print("  UP + UP + UP = 1 + 1 + 1 = 3 (not 2)")
        print("  UP + UP + DOWN = 1 + 1 - 1 = 1 (not 2)")
        print("  There are NO combinations that give 2 with UP/DOWN only!")
        print()
        
        # Check if there are any NULL or other values
        null_check_sql = text("""
        SELECT 
            daily_trend, weekly_trend, monthly_trend, trend_rating, COUNT(*) as count
        FROM trend_analysis 
        WHERE daily_trend NOT IN ('UP', 'DOWN') 
           OR weekly_trend NOT IN ('UP', 'DOWN')
           OR monthly_trend NOT IN ('UP', 'DOWN')
           OR trend_rating NOT IN (-3, -2, -1, 1, 3)
        GROUP BY daily_trend, weekly_trend, monthly_trend, trend_rating
        """)
        
        null_df = pd.read_sql(null_check_sql, con=conn)
        print("Checking for unexpected values:")
        if not null_df.empty:
            print(null_df.to_string(index=False))
        else:
            print("No unexpected values found - all trends are UP/DOWN")
        print()
        
        # Check recent SBIN data
        recent_sbin_sql = text("""
        SELECT trade_date, daily_trend, weekly_trend, monthly_trend, trend_rating
        FROM trend_analysis 
        WHERE symbol = 'SBIN'
        ORDER BY trade_date DESC
        LIMIT 10
        """)
        
        recent_df = pd.read_sql(recent_sbin_sql, con=conn)
        print("Recent SBIN Trend Data:")
        print(recent_df.to_string(index=False))

def explain_mathematical_impossibility():
    """Explain why ratings 0 and 2 are mathematically impossible."""
    print("\n" + "=" * 60)
    print("MATHEMATICAL ANALYSIS: Why Ratings 0 and 2 Don't Exist")
    print("=" * 60)
    
    print("Current System: UP = +1, DOWN = -1")
    print("Only possible combinations with 3 trends:")
    print()
    
    combinations = [
        ("UP", "UP", "UP", 3),
        ("UP", "UP", "DOWN", 1),
        ("UP", "DOWN", "UP", 1),
        ("DOWN", "UP", "UP", 1),
        ("UP", "DOWN", "DOWN", -1),
        ("DOWN", "UP", "DOWN", -1),
        ("DOWN", "DOWN", "UP", -1),
        ("DOWN", "DOWN", "DOWN", -3),
    ]
    
    possible_ratings = set()
    print("All Possible Combinations:")
    for daily, weekly, monthly, rating in combinations:
        print(f"  {daily:4} + {weekly:4} + {monthly:4} = {rating:2}")
        possible_ratings.add(rating)
    
    print(f"\nPossible Ratings: {sorted(possible_ratings)}")
    print(f"Missing Ratings: {sorted(set([-2, 0, 2]) - possible_ratings)}")
    print()
    print("CONCLUSION: Ratings -2, 0, and 2 are mathematically IMPOSSIBLE")
    print("with the current UP/DOWN binary system!")

if __name__ == "__main__":
    analyze_rating_distribution()
    explain_mathematical_impossibility()