#!/usr/bin/env python3
"""
Simple Historical Data Browser (Command Line)
Stable version for browsing collected planetary data
"""

import sys
import os
import sqlite3
from datetime import datetime, timedelta

# Add tools to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'tools'))

class SimpleDataBrowser:
    """
    Simple command-line browser for historical planetary data
    """
    
    def __init__(self, db_path: str = "historical_planetary_data.db"):
        self.db_path = db_path
        
        if not os.path.exists(db_path):
            print(f"❌ Database not found: {db_path}")
            print(f"💡 Run collection first: python simple_collector.py")
            sys.exit(1)
    
    def get_database_info(self):
        """Get database statistics"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("SELECT COUNT(*) FROM planetary_positions")
            total_count = cursor.fetchone()[0]
            
            if total_count == 0:
                print("📂 Database is empty")
                return False
            
            cursor.execute("SELECT MIN(timestamp), MAX(timestamp) FROM planetary_positions")
            date_range = cursor.fetchone()
            
            print(f"📊 Database Info:")
            print(f"   Records: {total_count:,}")
            print(f"   Period: {date_range[0]} to {date_range[1]}")
            
            # Calculate percentage if we know the expected total
            expected_total = 1051200  # 2 years of minutes
            percentage = (total_count / expected_total) * 100
            print(f"   Progress: {percentage:.1f}% of expected data")
            
            conn.close()
            return True
            
        except Exception as e:
            print(f"❌ Database error: {e}")
            return False
    
    def query_position(self, date_str: str, time_str: str = "00:00"):
        """Query position for specific date and time"""
        try:
            # Parse input
            if 'T' in date_str:
                target_datetime = datetime.fromisoformat(date_str)
            else:
                if time_str:
                    datetime_str = f"{date_str} {time_str}"
                else:
                    datetime_str = f"{date_str} 00:00"
                target_datetime = datetime.strptime(datetime_str, "%Y-%m-%d %H:%M")
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Try exact match first
            cursor.execute("SELECT * FROM planetary_positions WHERE timestamp = ?", 
                         (target_datetime.isoformat(),))\n            result = cursor.fetchone()\n            \n            if not result:\n                # Find nearest within 1 hour\n                print(f\"⚠️  Exact time not found, searching for nearest...\")\n                \n                cursor.execute(\"\"\"\n                SELECT *, ABS(julianday(timestamp) - julianday(?)) * 24 * 60 as diff_minutes\n                FROM planetary_positions \n                WHERE ABS(julianday(timestamp) - julianday(?)) * 24 * 60 <= 60\n                ORDER BY diff_minutes ASC LIMIT 1\n                \"\"\", (target_datetime.isoformat(), target_datetime.isoformat()))\n                \n                result = cursor.fetchone()\n                \n                if result:\n                    diff_minutes = result[-1]\n                    print(f\"🎯 Found nearest: {result[1]} ({diff_minutes:.1f} minutes difference)\")\n                else:\n                    print(f\"❌ No data found within 1 hour of {target_datetime}\")\n                    conn.close()\n                    return\n            \n            # Display results\n            print(f\"\\n🌟 Planetary Positions for {result[1]}\")\n            print(f\"{'='*60}\")\n            \n            planets = [\n                ('Sun', 7, 8), ('Moon', 9, 10), ('Mars', 11, 12),\n                ('Mercury', 13, 14), ('Jupiter', 15, 16), ('Venus', 17, 18),\n                ('Saturn', 19, 20), ('Rahu', 21, 22), ('Ketu', 23, 24)\n            ]\n            \n            for planet_name, lon_idx, sign_idx in planets:\n                longitude = result[lon_idx]\n                sign = result[sign_idx]\n                degree_in_sign = longitude % 30\n                \n                # Convert to DMS\n                deg = int(degree_in_sign)\n                min_float = (degree_in_sign - deg) * 60\n                min_val = int(min_float)\n                sec = (min_float - min_val) * 60\n                dms = f\"{deg:02d}° {min_val:02d}' {sec:04.1f}\\\"\"\n                \n                print(f\"{planet_name.ljust(8)}: {longitude:8.4f}° in {sign.ljust(12)} ({dms})\")\n            \n            print(f\"{'='*60}\")\n            conn.close()\n            \n        except Exception as e:\n            print(f\"❌ Query error: {e}\")\n    \n    def show_range(self, date_str: str, hours: int = 24):\n        \"\"\"Show planetary positions for a range of time\"\"\"\n        try:\n            start_datetime = datetime.strptime(date_str, \"%Y-%m-%d\")\n            end_datetime = start_datetime + timedelta(hours=hours)\n            \n            conn = sqlite3.connect(self.db_path)\n            cursor = conn.cursor()\n            \n            cursor.execute(\"\"\"\n            SELECT timestamp, sun_longitude, moon_longitude, mercury_longitude, \n                   venus_longitude, mars_longitude, jupiter_longitude, saturn_longitude\n            FROM planetary_positions \n            WHERE timestamp BETWEEN ? AND ?\n            ORDER BY timestamp ASC\n            LIMIT 100\n            \"\"\", (start_datetime.isoformat(), end_datetime.isoformat()))\n            \n            results = cursor.fetchall()\n            \n            if not results:\n                print(f\"❌ No data found for {date_str}\")\n                return\n            \n            print(f\"\\n📊 Planetary Movement - {date_str} ({len(results)} records)\")\n            print(f\"{'='*80}\")\n            print(f\"{'Time':<19} {'Sun':<8} {'Moon':<8} {'Mer':<8} {'Ven':<8} {'Mar':<8} {'Jup':<8} {'Sat':<8}\")\n            print(f\"{'-'*80}\")\n            \n            for row in results:\n                timestamp = row[0][:16]  # Remove seconds\n                values = [f\"{val:.1f}\" for val in row[1:8]]\n                print(f\"{timestamp:<19} {values[0]:<8} {values[1]:<8} {values[2]:<8} {values[3]:<8} {values[4]:<8} {values[5]:<8} {values[6]:<8}\")\n            \n            print(f\"{'-'*80}\")\n            conn.close()\n            \n        except Exception as e:\n            print(f\"❌ Range query error: {e}\")\n    \n    def interactive_mode(self):\n        \"\"\"Interactive browser mode\"\"\"\n        print(f\"\\n🔍 Interactive Browser Mode\")\n        print(f\"Commands:\")\n        print(f\"   q YYYY-MM-DD HH:MM    - Query specific date/time\")\n        print(f\"   r YYYY-MM-DD [hours]  - Show range (default 24 hours)\")\n        print(f\"   i                     - Database info\")\n        print(f\"   h                     - Show this help\")\n        print(f\"   exit                  - Exit browser\")\n        print(f\"\\n💡 Examples:\")\n        print(f\"   q 2024-01-01 12:00\")\n        print(f\"   r 2024-06-15 6\")\n        \n        while True:\n            try:\n                command = input(\"\\n> \").strip().lower()\n                \n                if command == \"exit\":\n                    break\n                elif command == \"h\":\n                    print(f\"Commands: q (query), r (range), i (info), h (help), exit\")\n                elif command == \"i\":\n                    self.get_database_info()\n                elif command.startswith(\"q \"):\n                    parts = command[2:].split()\n                    if len(parts) >= 1:\n                        date_part = parts[0]\n                        time_part = parts[1] if len(parts) > 1 else \"00:00\"\n                        self.query_position(date_part, time_part)\n                    else:\n                        print(\"Usage: q YYYY-MM-DD [HH:MM]\")\n                elif command.startswith(\"r \"):\n                    parts = command[2:].split()\n                    if len(parts) >= 1:\n                        date_part = parts[0]\n                        hours = int(parts[1]) if len(parts) > 1 else 24\n                        self.show_range(date_part, hours)\n                    else:\n                        print(\"Usage: r YYYY-MM-DD [hours]\")\n                elif command == \"\":\n                    continue\n                else:\n                    print(\"❌ Unknown command. Type 'h' for help.\")\n                    \n            except KeyboardInterrupt:\n                print(\"\\n👋 Goodbye!\")\n                break\n            except Exception as e:\n                print(f\"❌ Error: {e}\")\n\ndef main():\n    \"\"\"Main function\"\"\"\n    print(\"\"\"\n╔══════════════════════════════════════════════════════════════════════╗\n║           🔍 Simple Historical Planetary Data Browser                ║\n║                    Command Line Version                             ║\n╚══════════════════════════════════════════════════════════════════════╝\n\"\"\")\n    \n    browser = SimpleDataBrowser()\n    \n    if not browser.get_database_info():\n        return\n    \n    # Check command line arguments\n    if len(sys.argv) == 2:\n        # Single date query\n        browser.query_position(sys.argv[1])\n    elif len(sys.argv) == 3:\n        # Date and time query\n        browser.query_position(sys.argv[1], sys.argv[2])\n    else:\n        # Interactive mode\n        browser.interactive_mode()\n\nif __name__ == \"__main__\":\n    main()