#!/usr/bin/env python3
"""
Migrate trend_analysis table to support improved decimal ratings.
"""

import reporting_adv_decl as rad
from sqlalchemy import text

def migrate_trend_rating_column():
    """Alter the trend_rating column to support decimal values."""
    engine = rad.engine()
    
    print("Migrating trend_rating column to support decimal values...")
    print("Current: tinyint (-3 to +3)")
    print("New: decimal(4,1) (-10.0 to +10.0)")
    print()
    
    with engine.begin() as conn:
        # Alter the column to support decimals
        alter_sql = text("""
        ALTER TABLE trend_analysis 
        MODIFY COLUMN trend_rating DECIMAL(4,1) NOT NULL
        """)
        
        print("Executing migration...")
        conn.execute(alter_sql)
        print("✅ Column migration completed!")
        
        # Verify the change
        verify_sql = text("DESCRIBE trend_analysis")
        result = conn.execute(verify_sql)
        
        print("\nUpdated table structure:")
        for row in result:
            if row[0] == 'trend_rating':
                print(f"  {row[0]}: {row[1]} ✅")
            else:
                print(f"  {row[0]}: {row[1]}")

def test_new_rating_system():
    """Test the new rating system with actual data."""
    print("\n" + "="*50)
    print("Testing New Rating System")
    print("="*50)
    
    # Import the updated function
    from services.trends_service import calculate_trend_rating, get_rating_description
    
    test_cases = [
        ("UP", "UP", "UP"),
        ("DOWN", "UP", "UP"),
        ("UP", "DOWN", "DOWN"),
        ("DOWN", "DOWN", "DOWN"),
    ]
    
    print(f"{'Daily':<6} {'Weekly':<7} {'Monthly':<8} {'Rating':<7} {'Category'}")
    print("-" * 50)
    
    for daily, weekly, monthly in test_cases:
        rating = calculate_trend_rating(daily, weekly, monthly)
        desc = get_rating_description(rating)
        print(f"{daily:<6} {weekly:<7} {monthly:<8} {rating:<7} {desc['category']}")

if __name__ == "__main__":
    migrate_trend_rating_column()
    test_new_rating_system()