#!/usr/bin/env python3
"""
Fix Database Schema for Planetary Positions
Adds missing degree columns to match collector expectations
"""

import sqlite3
import os

def fix_database_schema(db_path="planetary_positions.db"):
    """
    Update the database schema to include degree columns
    """
    if not os.path.exists(db_path):
        print(f"❌ Database not found: {db_path}")
        return False
    
    print(f"🔧 Fixing database schema: {db_path}")
    
    # Backup current data
    backup_path = f"{db_path}.backup"
    print(f"📋 Creating backup: {backup_path}")
    
    # Copy database
    import shutil
    shutil.copy2(db_path, backup_path)
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Check current schema
        cursor.execute("PRAGMA table_info(planetary_positions)")
        existing_columns = [col[1] for col in cursor.fetchall()]
        print(f"📊 Current columns: {len(existing_columns)} found")
        
        # Columns to add
        new_columns = [
            "sun_degree REAL",
            "moon_degree REAL", 
            "mercury_degree REAL",
            "venus_degree REAL",
            "mars_degree REAL", 
            "jupiter_degree REAL",
            "saturn_degree REAL",
            "rahu_degree REAL",
            "ketu_degree REAL"
        ]
        
        # Add missing columns
        added_count = 0
        for column_def in new_columns:
            column_name = column_def.split()[0]
            if column_name not in existing_columns:
                try:
                    cursor.execute(f"ALTER TABLE planetary_positions ADD COLUMN {column_def}")
                    print(f"✅ Added column: {column_name}")
                    added_count += 1
                except sqlite3.Error as e:
                    print(f"⚠️  Could not add {column_name}: {e}")
        
        # Update existing records with degree values
        if added_count > 0:
            print(f"\n🔄 Updating existing records with degree values...")
            
            # Calculate degrees from longitudes for existing records
            update_sql = """
            UPDATE planetary_positions 
            SET 
                sun_degree = sun_longitude - (CAST(sun_longitude/30 AS INTEGER) * 30),
                moon_degree = moon_longitude - (CAST(moon_longitude/30 AS INTEGER) * 30),
                mercury_degree = mercury_longitude - (CAST(mercury_longitude/30 AS INTEGER) * 30),
                venus_degree = venus_longitude - (CAST(venus_longitude/30 AS INTEGER) * 30),
                mars_degree = mars_longitude - (CAST(mars_longitude/30 AS INTEGER) * 30),
                jupiter_degree = jupiter_longitude - (CAST(jupiter_longitude/30 AS INTEGER) * 30),
                saturn_degree = saturn_longitude - (CAST(saturn_longitude/30 AS INTEGER) * 30),
                rahu_degree = 0,
                ketu_degree = 0
            WHERE sun_degree IS NULL
            """
            
            cursor.execute(update_sql)
            updated_count = cursor.rowcount
            print(f"✅ Updated {updated_count} existing records")
        
        # Show final schema
        cursor.execute("PRAGMA table_info(planetary_positions)")
        final_columns = cursor.fetchall()
        
        print(f"\n🏗️  FINAL SCHEMA:")
        print(f"📊 Total columns: {len(final_columns)}")
        for col in final_columns:
            col_id, name, col_type, not_null, default, pk = col
            pk_text = " (PRIMARY KEY)" if pk else ""
            print(f"   {name:<20} {col_type:<12}{pk_text}")
        
        # Show record count
        cursor.execute("SELECT COUNT(*) FROM planetary_positions")
        count = cursor.fetchone()[0]
        print(f"\n📈 Records preserved: {count:,}")
        
        conn.commit()
        conn.close()
        
        print(f"\n✅ Database schema updated successfully!")
        print(f"📋 Backup available at: {backup_path}")
        return True
        
    except Exception as e:
        print(f"❌ Error updating schema: {e}")
        conn.rollback()
        conn.close()
        
        # Restore backup
        print(f"🔄 Restoring backup...")
        shutil.copy2(backup_path, db_path)
        return False

def show_updated_info(db_path="planetary_positions.db"):
    """Show information about the updated database"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print(f"\n📊 UPDATED DATABASE INFO")
    print("="*60)
    
    # Sample record
    cursor.execute("SELECT * FROM planetary_positions ORDER BY id DESC LIMIT 1")
    record = cursor.fetchone()
    
    if record:
        cursor.execute("PRAGMA table_info(planetary_positions)")
        columns = [col[1] for col in cursor.fetchall()]
        
        print("🔍 Sample record (latest):")
        for i, value in enumerate(record):
            if i < len(columns):
                col_name = columns[i]
                if 'longitude' in col_name or 'degree' in col_name:
                    if value is not None:
                        print(f"   {col_name:<20}: {value:.4f}°")
                    else:
                        print(f"   {col_name:<20}: NULL")
                else:
                    print(f"   {col_name:<20}: {value}")
    
    conn.close()

if __name__ == "__main__":
    print("""
╔══════════════════════════════════════════════════════════════════╗
║              🔧 Database Schema Fixer v1.0                      ║
║                  Add Missing Degree Columns                     ║
╚══════════════════════════════════════════════════════════════════╝
""")
    
    if fix_database_schema():
        show_updated_info()
        print(f"\n🚀 Ready for data collection!")
        print(f"💡 Run responsive_collector.py to continue collecting data")
    else:
        print(f"\n❌ Schema update failed!")
        print(f"💡 Check the backup file and try again")