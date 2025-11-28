#!/usr/bin/env python3
"""
Test the improved rating system with SBIN data.
"""

import reporting_adv_decl as rad
from sqlalchemy import text
import pandas as pd
from services.trends_service import get_rating_description

def test_sbin_with_new_ratings():
    """Test SBIN data with the new rating system."""
    engine = rad.engine()
    
    print("SBIN Trend Analysis with Improved Rating System")
    print("=" * 60)
    
    with engine.connect() as conn:
        # Get recent SBIN data
        sql = text("""
        SELECT trade_date, daily_trend, weekly_trend, monthly_trend, trend_rating
        FROM trend_analysis 
        WHERE symbol = 'SBIN'
        ORDER BY trade_date DESC
        LIMIT 15
        """)
        
        df = pd.read_sql(sql, con=conn)
        
        print("Recent SBIN Trend Data:")
        print("-" * 80)
        print(f"{'Date':<12} {'Daily':<6} {'Weekly':<7} {'Monthly':<8} {'Rating':<7} {'Category'}")
        print("-" * 80)
        
        for _, row in df.iterrows():
            rating_info = get_rating_description(row['trend_rating'])
            date_str = row['trade_date'].strftime('%Y-%m-%d')
            print(f"{date_str:<12} {row['daily_trend']:<6} {row['weekly_trend']:<7} "
                  f"{row['monthly_trend']:<8} {row['trend_rating']:<7} {rating_info['category']}")
        
        # Show rating distribution for SBIN
        dist_sql = text("""
        SELECT trend_rating, COUNT(*) as count
        FROM trend_analysis 
        WHERE symbol = 'SBIN'
        GROUP BY trend_rating 
        ORDER BY trend_rating
        """)
        
        dist_df = pd.read_sql(dist_sql, con=conn)
        
        print("\nSBIN Rating Distribution:")
        print("-" * 30)
        for _, row in dist_df.iterrows():
            rating_info = get_rating_description(row['trend_rating'])
            print(f"Rating {row['trend_rating']:>5}: {row['count']:>3} records ({rating_info['category']})")

if __name__ == "__main__":
    test_sbin_with_new_ratings()