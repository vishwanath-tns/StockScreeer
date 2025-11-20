"""
Check indices for sector filtering
"""
import os
from dotenv import load_dotenv
import pymysql

# Load environment variables
load_dotenv()

def check_indices():
    """Check available indices"""
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
            # Check nse_indices structure
            cursor.execute("DESCRIBE nse_indices")
            print("nse_indices structure:")
            for col in cursor.fetchall():
                print(f"  {col[0]} ({col[1]})")
            
            # Get distinct index names
            cursor.execute("SELECT DISTINCT index_name FROM nse_indices ORDER BY index_name")
            indices = [row[0] for row in cursor.fetchall()]
            
            print(f"\nAvailable indices ({len(indices)}):")
            for i, index in enumerate(indices):
                print(f"  {i+1:2d}. {index}")
                if i >= 20:  # Limit to first 20
                    print(f"  ... and {len(indices) - 20} more")
                    break
        
        connection.close()
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_indices()