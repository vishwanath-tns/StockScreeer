"""
Setup candlestick pattern database tables
"""
import os
from dotenv import load_dotenv
import pymysql

def setup_pattern_tables():
    """Create candlestick pattern tables"""
    load_dotenv()
    
    try:
        # Connect to database
        connection = pymysql.connect(
            host=os.getenv('MYSQL_HOST', 'localhost'),
            port=int(os.getenv('MYSQL_PORT', 3306)),
            user=os.getenv('MYSQL_USER', 'root'),
            password=os.getenv('MYSQL_PASSWORD', ''),
            database=os.getenv('MYSQL_DB', 'stock_data'),
            charset='utf8mb4'
        )
        
        # Read schema file
        with open('db/candlestick_patterns_schema.sql', 'r') as f:
            schema = f.read()
        
        cursor = connection.cursor()
        
        # Execute each statement
        statements = [stmt.strip() for stmt in schema.split(';') if stmt.strip()]
        
        for stmt in statements:
            try:
                cursor.execute(stmt)
                print(f"✅ Executed: {stmt[:50]}...")
            except Exception as e:
                if "already exists" in str(e):
                    print(f"⚠️  Table already exists: {stmt[:30]}...")
                else:
                    print(f"❌ Error: {e}")
        
        connection.commit()
        print("\n🎉 Candlestick pattern database setup completed!")
        
        # Verify tables created
        cursor.execute("SHOW TABLES LIKE '%pattern%'")
        tables = cursor.fetchall()
        print(f"📊 Pattern-related tables: {[table[0] for table in tables]}")
        
        connection.close()
        
    except Exception as e:
        print(f"❌ Setup failed: {e}")

if __name__ == "__main__":
    setup_pattern_tables()