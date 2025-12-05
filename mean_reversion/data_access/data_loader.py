import os
import mysql.connector
from sqlalchemy import create_engine
import pandas as pd
from dotenv import load_dotenv

load_dotenv()

class DatabaseLoader:
    def __init__(self):
        self.db_config = {
            'host': os.getenv('MYSQL_HOST', 'localhost'),
            'port': int(os.getenv('MYSQL_PORT', 3306)),
            'user': os.getenv('MYSQL_USER', 'root'),
            'password': os.getenv('MYSQL_PASSWORD', ''),
            'database': os.getenv('MYSQL_DATABASE', 'marketdata'),
            'charset': 'utf8mb4'
        }
        self._engine = None
        
    def get_engine(self):
        if self._engine is None:
            from urllib.parse import quote_plus
            password = quote_plus(self.db_config['password']) if self.db_config['password'] else ''
            conn_str = f"mysql+mysqlconnector://{self.db_config['user']}:{password}@{self.db_config['host']}:{self.db_config['port']}/{self.db_config['database']}"
            self._engine = create_engine(conn_str)
        return self._engine
    
    def fetch_data(self, symbol, days=365):
        """Fetch data for a single symbol"""
        # Ensure symbol format
        yahoo_symbol = f"{symbol}.NS" if not symbol.endswith(('.NS', '.BO')) else symbol
        
        query = """
            SELECT date, open, high, low, close, volume
            FROM yfinance_daily_quotes
            WHERE symbol = %s 
            ORDER BY date ASC
        """
        try:
            df = pd.read_sql(query, self.get_engine(), params=(yahoo_symbol,))
            if not df.empty:
                df['date'] = pd.to_datetime(df['date'])
                df.set_index('date', inplace=True)
            return df
        except Exception as e:
            # print(f"Error fetching {symbol}: {e}")
            return pd.DataFrame()
            
    def get_latest_date(self, symbol):
        """Get the date of the last candle"""
        # Simplified query for speed
        yahoo_symbol = f"{symbol}.NS" if not symbol.endswith(('.NS', '.BO')) else symbol
        query = "SELECT MAX(date) FROM yfinance_daily_quotes WHERE symbol = %s"
        try:
            with self.get_engine().connect() as conn:
                result = conn.execute(query, (yahoo_symbol,)).scalar()
            return result
        except:
            return None
