"""
Check table structures for joining
"""
import os
from dotenv import load_dotenv
import pymysql

# Load environment variables
load_dotenv()

def check_structures():
    """Check table structures"""
    try:
        connection = pymysql.connect(
            host=os.getenv('MYSQL_HOST', 'localhost'),
            port=int(os.getenv('MYSQL_PORT', 3306)),
            user=os.getenv('MYSQL_USER', 'root'),
            password=os.getenv('MYSQL_PASSWORD', ''),
            database=os.getenv('MYSQL_DB', 'stock_data'),
            charset='utf8mb4'
        )
        
        with connection.cursor() as cursor:
            # Check momentum_analysis
            cursor.execute("DESCRIBE momentum_analysis")
            print("momentum_analysis structure:")
            for col in cursor.fetchall():
                print(f"  {col[0]} ({col[1]})")
            
            # Check nse_index_constituents 
            cursor.execute("DESCRIBE nse_index_constituents")
            print("\nnse_index_constituents structure:")
            for col in cursor.fetchall()[:10]:  # First 10 columns
                print(f"  {col[0]} ({col[1]})")
            
            # Sample data from momentum_analysis
            cursor.execute("SELECT symbol, duration_type, percentage_change FROM momentum_analysis LIMIT 3")
            print("\nSample momentum_analysis data:")
            for row in cursor.fetchall():
                print(f"  {row}")
                
            # Sample data from nse_index_constituents
            cursor.execute("SELECT index_id, symbol, company_name FROM nse_index_constituents LIMIT 3")
            print("\nSample nse_index_constituents data:")
            for row in cursor.fetchall():
                print(f"  {row}")
        
        connection.close()
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_structures()