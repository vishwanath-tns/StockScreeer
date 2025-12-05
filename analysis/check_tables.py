import sys
import os
import pandas as pd
from sqlalchemy import create_engine
from dotenv import load_dotenv

load_dotenv()

def list_yfinance_tables():
    host = os.getenv('MYSQL_HOST', 'localhost')
    user = os.getenv('MYSQL_USER', 'root')
    password = os.getenv('MYSQL_PASSWORD', '')
    port = int(os.getenv('MYSQL_PORT', 3306))
    database = os.getenv('MYSQL_DATABASE', 'marketdata')
    
    # URL encode password
    from urllib.parse import quote_plus
    pwd = quote_plus(password) if password else ''
    
    conn_str = f"mysql+mysqlconnector://{user}:{pwd}@{host}:{port}/{database}"
    engine = create_engine(conn_str)
    
    query = """
    SELECT table_name, table_rows, create_time 
    FROM information_schema.tables 
    WHERE table_schema = %s 
    AND table_name LIKE 'yfinance%'
    """
    
    try:
        df = pd.read_sql(query, engine, params=(database,))
        print(f"\nFound {len(df)} Yahoo Finance related tables:")
        print("="*60)
        print(df.to_string(index=False))
        print("="*60)
        
        # Also check column details for the main table
        if 'yfinance_daily_quotes' in df['table_name'].values:
            print("\nColumns in 'yfinance_daily_quotes':")
            col_query = """
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_schema = %s AND table_name = 'yfinance_daily_quotes'
            """
            cols = pd.read_sql(col_query, engine, params=(database,))
            print(cols.to_string(index=False))
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    list_yfinance_tables()
