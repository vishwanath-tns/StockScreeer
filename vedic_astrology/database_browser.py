#!/usr/bin/env python3
"""
Simple Database Browser for Planetary Positions
View tables, data structure, and query specific dates
"""

import sys
import os
import sqlite3
from datetime import datetime, timedelta

class DatabaseBrowser:
    """
    Simple command-line database browser
    """
    
    def __init__(self, db_path="planetary_positions.db"):
        self.db_path = db_path
        
    def show_tables(self):
        """Show all tables in the database"""
        if not os.path.exists(self.db_path):
            print(f"❌ Database not found: {self.db_path}")
            return False
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        print(f"\n🗄️  DATABASE: {self.db_path}")
        print("="*60)
        
        # List all tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        
        print(f"📋 TABLES ({len(tables)} total):")
        for table in tables:
            table_name = table[0]
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            count = cursor.fetchone()[0]
            print(f"   - {table_name} ({count:,} records)")
        
        conn.close()
        return True
    
    def show_table_structure(self, table_name="planetary_positions"):
        """Show structure of a specific table"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        print(f"\n🏗️  TABLE STRUCTURE: {table_name}")
        print("="*60)
        
        try:
            cursor.execute(f"PRAGMA table_info({table_name})")
            columns = cursor.fetchall()
            
            print("COLUMNS:")
            for col in columns:
                col_id, name, col_type, not_null, default, pk = col
                pk_text = " (PRIMARY KEY)" if pk else ""
                not_null_text = " NOT NULL" if not_null else ""
                default_text = f" DEFAULT {default}" if default else ""
                print(f"   {name:<20} {col_type:<12}{not_null_text}{default_text}{pk_text}")
            
            # Show indexes
            cursor.execute(f"PRAGMA index_list({table_name})")
            indexes = cursor.fetchall()
            
            if indexes:
                print(f"\nINDEXES:")
                for idx in indexes:
                    idx_name = idx[1]
                    cursor.execute(f"PRAGMA index_info({idx_name})")
                    idx_cols = [col[2] for col in cursor.fetchall()]
                    print(f"   - {idx_name}: {', '.join(idx_cols)}")
        
        except sqlite3.Error as e:
            print(f"❌ Error accessing table {table_name}: {e}")
        
        conn.close()
    
    def show_sample_data(self, table_name="planetary_positions", limit=5):
        """Show sample data from table"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        print(f"\n📋 SAMPLE DATA: {table_name} (latest {limit} records)")
        print("="*80)
        
        try:
            cursor.execute(f"SELECT * FROM {table_name} ORDER BY timestamp DESC LIMIT {limit}")
            rows = cursor.fetchall()
            
            if not rows:
                print("   (No data found)")
                conn.close()
                return
            
            # Get column names
            cursor.execute(f"PRAGMA table_info({table_name})")
            columns = [col[1] for col in cursor.fetchall()]
            
            # Show data
            for i, row in enumerate(rows, 1):
                print(f"\nRecord {i}:")
                for j, value in enumerate(row):
                    if j < len(columns):
                        col_name = columns[j]
                        if 'longitude' in col_name and value:
                            print(f"   {col_name:<20}: {value:.4f}°")
                        else:
                            print(f"   {col_name:<20}: {value}")
        
        except sqlite3.Error as e:
            print(f"❌ Error reading from {table_name}: {e}")
        
        conn.close()
    
    def show_date_range(self, table_name="planetary_positions"):
        """Show the date range of collected data"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        print(f"\n📅 DATE RANGE: {table_name}")
        print("="*60)
        
        try:
            cursor.execute(f"SELECT MIN(timestamp), MAX(timestamp), COUNT(*) FROM {table_name}")
            result = cursor.fetchone()
            
            if result[0]:
                min_date, max_date, count = result
                print(f"First record:  {min_date}")
                print(f"Last record:   {max_date}")
                print(f"Total records: {count:,}")
                
                # Calculate coverage
                start_time = datetime.fromisoformat(min_date)
                end_time = datetime.fromisoformat(max_date)
                total_minutes = int((end_time - start_time).total_seconds() / 60) + 1
                coverage = (count / total_minutes) * 100 if total_minutes > 0 else 0
                
                print(f"Time span:     {total_minutes:,} minutes")
                print(f"Coverage:      {coverage:.2f}%")
                
                if coverage < 100:
                    print(f"Missing:       {total_minutes - count:,} records")
            else:
                print("   (No data found)")
        
        except sqlite3.Error as e:
            print(f"❌ Error analyzing date range: {e}")
        
        conn.close()
    
    def query_specific_date(self, date_str, time_str="12:00"):
        """Query planetary positions for specific date/time"""
        try:
            # Parse date and time
            target_datetime = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
            
        except ValueError:
            print(f"❌ Invalid date/time format. Use: YYYY-MM-DD HH:MM")
            return
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        print(f"\n🔍 PLANETARY POSITIONS: {target_datetime}")
        print("="*60)
        
        # Query exact time
        cursor.execute("SELECT * FROM planetary_positions WHERE timestamp = ?", 
                      (target_datetime.isoformat(),))
        result = cursor.fetchone()
        
        if result:
            print("📅 Exact match found!")
            self.display_planetary_positions(result)
        else:
            # Find nearest time
            print("⚠️  Exact time not found, searching for nearest...")
            
            cursor.execute("""
                SELECT *, ABS(julianday(timestamp) - julianday(?)) * 24 * 60 as diff_minutes
                FROM planetary_positions 
                WHERE ABS(julianday(timestamp) - julianday(?)) * 24 * 60 <= 60
                ORDER BY diff_minutes ASC LIMIT 1
            """, (target_datetime.isoformat(), target_datetime.isoformat()))
            
            result = cursor.fetchone()
            
            if result:
                diff_minutes = result[-1]
                print(f"📍 Nearest record found ({diff_minutes:.1f} minutes difference)")
                self.display_planetary_positions(result[:-1])  # Exclude diff_minutes
            else:
                print("❌ No data found within 1 hour of requested time")
        
        conn.close()
    
    def display_planetary_positions(self, row):
        """Display planetary positions from database row"""
        if not row:
            return
        
        # Column mapping (based on our table structure)
        timestamp = row[1]  # timestamp column
        
        planets = [
            ('Sun', 7, 8, 9),           # longitude, sign, degree columns
            ('Moon', 10, 11, 12),
            ('Mercury', 13, 14, 15),
            ('Venus', 16, 17, 18),
            ('Mars', 19, 20, 21),
            ('Jupiter', 22, 23, 24),
            ('Saturn', 25, 26, 27)
        ]
        
        print(f"🕐 Time: {timestamp}")
        print("\n🪐 Planetary Positions:")
        
        for planet_name, lon_idx, sign_idx, deg_idx in planets:
            try:
                if lon_idx < len(row):
                    longitude = row[lon_idx]
                    sign = row[sign_idx] if sign_idx < len(row) else 'Unknown'
                    degree = row[deg_idx] if deg_idx < len(row) else 0
                    
                    if longitude is not None:
                        print(f"   {planet_name:<8}: {longitude:8.4f}° in {sign:<12} ({degree:5.2f}°)")
                    else:
                        print(f"   {planet_name:<8}: No data")
            except (IndexError, TypeError):
                print(f"   {planet_name:<8}: Data error")
    
    def interactive_browser(self):
        """Interactive command-line browser"""
        if not self.show_tables():
            return
        
        while True:
            print(f"\n🔍 DATABASE BROWSER MENU")
            print("-" * 40)
            print("1. Show table structure")
            print("2. Show sample data")
            print("3. Show date range")
            print("4. Query specific date/time")
            print("5. Show all tables")
            print("6. Exit")
            
            try:
                choice = input("\nEnter choice (1-6): ").strip()
                
                if choice == "1":
                    table = input("Enter table name (default: planetary_positions): ").strip()
                    if not table:
                        table = "planetary_positions"
                    self.show_table_structure(table)
                
                elif choice == "2":
                    table = input("Enter table name (default: planetary_positions): ").strip()
                    if not table:
                        table = "planetary_positions"
                    limit = input("Number of records (default: 5): ").strip()
                    limit = int(limit) if limit.isdigit() else 5
                    self.show_sample_data(table, limit)
                
                elif choice == "3":
                    table = input("Enter table name (default: planetary_positions): ").strip()
                    if not table:
                        table = "planetary_positions"
                    self.show_date_range(table)
                
                elif choice == "4":
                    date_str = input("Enter date (YYYY-MM-DD): ").strip()
                    time_str = input("Enter time (HH:MM, default: 12:00): ").strip()
                    if not time_str:
                        time_str = "12:00"
                    self.query_specific_date(date_str, time_str)
                
                elif choice == "5":
                    self.show_tables()
                
                elif choice == "6":
                    print("👋 Goodbye!")
                    break
                
                else:
                    print("❌ Invalid choice. Please enter 1-6.")
            
            except KeyboardInterrupt:
                print("\n👋 Goodbye!")
                break
            except Exception as e:
                print(f"❌ Error: {e}")

def main():
    """Main function"""
    print("""
╔══════════════════════════════════════════════════════════════════╗
║              🗄️  Planetary Database Browser v1.0                ║
║                    View Tables and Query Data                    ║
╚══════════════════════════════════════════════════════════════════╝
""")
    
    db_path = "planetary_positions.db"
    if len(sys.argv) > 1:
        db_path = sys.argv[1]
    
    browser = DatabaseBrowser(db_path)
    
    # Quick overview first
    if browser.show_tables():
        browser.show_date_range()
        browser.show_sample_data(limit=3)
    
    # Start interactive mode
    print(f"\n🚀 Starting interactive browser...")
    browser.interactive_browser()

if __name__ == "__main__":
    main()