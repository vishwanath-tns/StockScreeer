import sys
import os
import pandas as pd
from sqlalchemy import create_engine
from dotenv import load_dotenv

load_dotenv()

def inspect_data():
    host = os.getenv('MYSQL_HOST', 'localhost')
    user = os.getenv('MYSQL_USER', 'root')
    password = os.getenv('MYSQL_PASSWORD', '')
    port = int(os.getenv('MYSQL_PORT', 3306))
    database = os.getenv('MYSQL_DATABASE', 'marketdata')
    
    from urllib.parse import quote_plus
    pwd = quote_plus(password) if password else ''
    
    conn_str = f"mysql+mysqlconnector://{user}:{pwd}@{host}:{port}/{database}"
    engine = create_engine(conn_str)
    
    print("Inspecting 'yfinance_daily_quotes' (Stocks)...")
    print("="*60)
    
    # Sample Data
    query_sample = "SELECT * FROM yfinance_daily_quotes ORDER BY date DESC LIMIT 5"
    df_sample = pd.read_sql(query_sample, engine)
    print("Last 5 records inserted:")
    print(df_sample.to_string(index=False))
    
    # Null Check
    print("\nChecking for Nulls in critical columns (Open/Close/Date):")
    query_nulls = """
    SELECT COUNT(*) as null_records 
    FROM yfinance_daily_quotes 
    WHERE open IS NULL OR close IS NULL OR date IS NULL
    """
    nulls = pd.read_sql(query_nulls, engine).iloc[0]['null_records']
    print(f"Records with Null OHLC: {nulls}")
    
    print("\n" + "="*60)
    print("Inspecting 'yfinance_indices_daily_quotes' (Indices)...")
    
    # Sample Data
    query_indices = "SELECT * FROM yfinance_indices_daily_quotes ORDER BY date DESC LIMIT 5"
    df_indices = pd.read_sql(query_indices, engine)
    print("Last 5 records inserted:")
    print(df_indices.to_string(index=False))

if __name__ == "__main__":
    inspect_data()
