"""
Check available tables and find indices tables
"""
import os
from dotenv import load_dotenv
import pymysql

# Load environment variables
load_dotenv()

def check_tables():
    """Check available tables"""
    try:
        # Database connection
        connection = pymysql.connect(
            host=os.getenv('MYSQL_HOST', 'localhost'),
            port=int(os.getenv('MYSQL_PORT', 3306)),
            user=os.getenv('MYSQL_USER', 'root'),
            password=os.getenv('MYSQL_PASSWORD', ''),
            database=os.getenv('MYSQL_DB', 'stock_data'),
            charset='utf8mb4'
        )
        
        with connection.cursor() as cursor:
            # Get all tables
            cursor.execute("SHOW TABLES")
            all_tables = [table[0] for table in cursor.fetchall()]
            
            print("All tables:")
            for table in sorted(all_tables):
                print(f"  {table}")
            
            print("\nTables with 'index' or 'indic' or 'nifty':")
            index_tables = [t for t in all_tables if any(keyword in t.lower() for keyword in ['index', 'indic', 'nifty'])]
            for table in sorted(index_tables):
                print(f"  {table}")
                
            # Check structure of likely index tables
            for table in index_tables[:3]:  # Check first 3
                print(f"\nStructure of {table}:")
                cursor.execute(f"DESCRIBE {table}")
                columns = cursor.fetchall()
                for col in columns:
                    print(f"  {col[0]} ({col[1]})")
        
        connection.close()
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_tables()