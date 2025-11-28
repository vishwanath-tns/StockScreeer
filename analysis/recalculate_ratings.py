#!/usr/bin/env python3
"""
Recalculate all existing trend ratings using the improved system.
"""

import reporting_adv_decl as rad
from sqlalchemy import text
from services.trends_service import calculate_trend_rating
import pandas as pd

def recalculate_all_ratings():
    """Recalculate all existing ratings with the new system."""
    engine = rad.engine()
    
    print("Recalculating all trend ratings with improved system...")
    print("This will update all existing records to use the new -10 to +10 scale")
    print()
    
    with engine.begin() as conn:
        # Get all existing records
        select_sql = text("""
        SELECT id, daily_trend, weekly_trend, monthly_trend, trend_rating as old_rating
        FROM trend_analysis
        ORDER BY id
        """)
        
        print("Fetching existing records...")
        df = pd.read_sql(select_sql, con=conn)
        print(f"Found {len(df)} records to update")
        
        if len(df) == 0:
            print("No records to update")
            return
        
        # Calculate new ratings
        print("Calculating new ratings...")
        df['new_rating'] = df.apply(
            lambda row: calculate_trend_rating(
                row['daily_trend'], 
                row['weekly_trend'], 
                row['monthly_trend']
            ), axis=1
        )
        
        # Show some examples of the change
        print("\nSample rating changes:")
        print("ID      Old Rating  New Rating  Trends")
        print("-" * 50)
        sample_df = df.head(10)
        for _, row in sample_df.iterrows():
            trends = f"{row['daily_trend']}/{row['weekly_trend']}/{row['monthly_trend']}"
            print(f"{row['id']:<8} {row['old_rating']:<11} {row['new_rating']:<11} {trends}")
        
        # Update all records in batches
        print(f"\nUpdating {len(df)} records...")
        batch_size = 1000
        updated_count = 0
        
        for i in range(0, len(df), batch_size):
            batch = df.iloc[i:i+batch_size]
            
            # Build batch update
            for _, row in batch.iterrows():
                update_sql = text("""
                UPDATE trend_analysis 
                SET trend_rating = :new_rating 
                WHERE id = :record_id
                """)
                
                conn.execute(update_sql, {
                    'new_rating': row['new_rating'],
                    'record_id': row['id']
                })
                updated_count += 1
            
            print(f"  Updated {min(updated_count, len(df))}/{len(df)} records...")
        
        print(f"✅ Successfully updated {updated_count} records!")
        
        # Verify the update
        print("\nVerifying update...")
        verify_sql = text("""
        SELECT 
            trend_rating,
            COUNT(*) as count,
            ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM trend_analysis), 1) as percentage
        FROM trend_analysis 
        GROUP BY trend_rating 
        ORDER BY trend_rating
        """)
        
        result_df = pd.read_sql(verify_sql, con=conn)
        print("\nNew Rating Distribution:")
        print(result_df.to_string(index=False))

if __name__ == "__main__":
    recalculate_all_ratings()