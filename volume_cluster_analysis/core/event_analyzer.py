"""
Volume Event Analyzer - Analyzes every high volume occurrence and calculates forward returns.
"""

import pandas as pd
import numpy as np
from dataclasses import dataclass
from typing import List, Optional, Dict
from datetime import datetime
from sqlalchemy import create_engine, text
from urllib.parse import quote_plus
import os
from dotenv import load_dotenv


@dataclass
class VolumeEvent:
    """Represents a single high volume event with forward returns."""
    symbol: str
    event_date: datetime
    volume: int
    volume_quintile: str
    close_price: float
    prev_close: float
    day_return: float
    relative_volume: float
    
    # Forward returns (can be positive or negative)
    return_1d: Optional[float] = None
    return_1w: Optional[float] = None
    return_2w: Optional[float] = None
    return_3w: Optional[float] = None
    return_1m: Optional[float] = None
    
    # Prices after each period
    price_1d: Optional[float] = None
    price_1w: Optional[float] = None
    price_2w: Optional[float] = None
    price_3w: Optional[float] = None
    price_1m: Optional[float] = None


class VolumeEventAnalyzer:
    """Analyzes volume events and stores results in database."""
    
    PERIODS = {
        '1d': 1,
        '1w': 5,
        '2w': 10,
        '3w': 15,
        '1m': 21
    }
    
    QUINTILE_NAMES = ['Very Low', 'Low', 'Normal', 'High', 'Very High']
    
    # Ultra High threshold: relative volume >= 4x average
    ULTRA_HIGH_THRESHOLD = 4.0
    
    def __init__(self):
        load_dotenv()
        self.engine = self._create_engine()
    
    def _create_engine(self):
        """Create database engine with URL-encoded password."""
        password = quote_plus(os.getenv('MYSQL_PASSWORD', ''))
        host = os.getenv('MYSQL_HOST', 'localhost')
        port = os.getenv('MYSQL_PORT', '3306')
        db = os.getenv('MYSQL_DB', 'marketdata')
        user = os.getenv('MYSQL_USER', 'root')
        
        return create_engine(
            f'mysql+pymysql://{user}:{password}@{host}:{port}/{db}',
            pool_pre_ping=True
        )
    
    def get_stock_data(self, symbol: str, min_days: int = 252) -> Optional[pd.DataFrame]:
        """Fetch stock data from database."""
        query = """
            SELECT date as trade_date, open, high, low, close, volume
            FROM yfinance_daily_quotes
            WHERE symbol = :symbol
            AND timeframe = 'daily'
            ORDER BY date ASC
        """
        
        try:
            with self.engine.connect() as conn:
                df = pd.read_sql(text(query), conn, params={'symbol': symbol})
            
            if len(df) < min_days:
                return None
            
            df['trade_date'] = pd.to_datetime(df['trade_date'])
            df = df.sort_values('trade_date').reset_index(drop=True)
            
            # Calculate additional metrics
            df['prev_close'] = df['close'].shift(1)
            df['day_return'] = (df['close'] / df['prev_close'] - 1) * 100
            df['volume_ma_20'] = df['volume'].rolling(20).mean()
            df['relative_volume'] = df['volume'] / df['volume_ma_20']
            
            return df
            
        except Exception as e:
            print(f"Error fetching {symbol}: {e}")
            return None
    
    def analyze_stock(self, symbol: str, quintiles_to_track: List[str] = None) -> List[VolumeEvent]:
        """Analyze all volume events for a stock."""
        if quintiles_to_track is None:
            quintiles_to_track = ['High', 'Very High', 'Ultra High']
        
        df = self.get_stock_data(symbol)
        if df is None:
            return []
        
        df = df[df['volume'] > 0].copy()
        if len(df) < 100:
            return []
        
        try:
            df['quintile'] = pd.qcut(df['volume'], q=5, labels=self.QUINTILE_NAMES)
            # Add "Ultra High" as a new category before assignment
            df['quintile'] = df['quintile'].cat.add_categories(['Ultra High'])
            # Override to "Ultra High" if relative volume >= threshold
            df.loc[df['relative_volume'] >= self.ULTRA_HIGH_THRESHOLD, 'quintile'] = 'Ultra High'
        except ValueError:
            return []
        
        for period_name, days in self.PERIODS.items():
            df[f'return_{period_name}'] = (df['close'].shift(-days) / df['close'] - 1) * 100
            df[f'price_{period_name}'] = df['close'].shift(-days)
        
        df_events = df[df['quintile'].isin(quintiles_to_track)].copy()
        
        events = []
        for _, row in df_events.iterrows():
            event = VolumeEvent(
                symbol=symbol,
                event_date=row['trade_date'],
                volume=int(row['volume']),
                volume_quintile=row['quintile'],
                close_price=round(row['close'], 2),
                prev_close=round(row['prev_close'], 2) if pd.notna(row['prev_close']) else None,
                day_return=round(row['day_return'], 2) if pd.notna(row['day_return']) else None,
                relative_volume=round(row['relative_volume'], 2) if pd.notna(row['relative_volume']) else None,
                return_1d=round(row['return_1d'], 2) if pd.notna(row['return_1d']) else None,
                return_1w=round(row['return_1w'], 2) if pd.notna(row['return_1w']) else None,
                return_2w=round(row['return_2w'], 2) if pd.notna(row['return_2w']) else None,
                return_3w=round(row['return_3w'], 2) if pd.notna(row['return_3w']) else None,
                return_1m=round(row['return_1m'], 2) if pd.notna(row['return_1m']) else None,
                price_1d=round(row['price_1d'], 2) if pd.notna(row['price_1d']) else None,
                price_1w=round(row['price_1w'], 2) if pd.notna(row['price_1w']) else None,
                price_2w=round(row['price_2w'], 2) if pd.notna(row['price_2w']) else None,
                price_3w=round(row['price_3w'], 2) if pd.notna(row['price_3w']) else None,
                price_1m=round(row['price_1m'], 2) if pd.notna(row['price_1m']) else None,
            )
            events.append(event)
        
        return events
    
    def save_events_to_db(self, events: List[VolumeEvent]) -> int:
        """Save volume events to database."""
        if not events:
            return 0
        
        data = []
        for e in events:
            data.append({
                'symbol': e.symbol,
                'event_date': e.event_date,
                'volume': e.volume,
                'volume_quintile': e.volume_quintile,
                'close_price': e.close_price,
                'prev_close': e.prev_close,
                'day_return': e.day_return,
                'relative_volume': e.relative_volume,
                'return_1d': e.return_1d,
                'return_1w': e.return_1w,
                'return_2w': e.return_2w,
                'return_3w': e.return_3w,
                'return_1m': e.return_1m,
                'price_1d': e.price_1d,
                'price_1w': e.price_1w,
                'price_2w': e.price_2w,
                'price_3w': e.price_3w,
                'price_1m': e.price_1m,
            })
        
        df = pd.DataFrame(data)
        
        with self.engine.connect() as conn:
            symbol = events[0].symbol
            conn.execute(text("DELETE FROM volume_cluster_events WHERE symbol = :symbol"), 
                        {'symbol': symbol})
            df.to_sql('volume_cluster_events', conn, if_exists='append', index=False, method='multi')
            conn.commit()
        
        return len(events)
    
    def get_stock_events(self, symbol: str, quintile: str = None) -> pd.DataFrame:
        """Fetch stored events for a stock from database."""
        query = "SELECT * FROM volume_cluster_events WHERE symbol = :symbol"
        params = {'symbol': symbol}
        
        if quintile:
            query += " AND volume_quintile = :quintile"
            params['quintile'] = quintile
        
        query += " ORDER BY event_date DESC"
        
        with self.engine.connect() as conn:
            df = pd.read_sql(text(query), conn, params=params)
        
        return df
    
    def get_return_statistics(self, symbol: str, quintile: str = 'Very High') -> Dict:
        """Get return statistics for a stock high volume events."""
        df = self.get_stock_events(symbol, quintile)
        
        if df.empty:
            return {}
        
        stats = {
            'symbol': symbol,
            'quintile': quintile,
            'total_events': len(df),
        }
        
        periods = ['1d', '1w', '2w', '3w', '1m']
        for period in periods:
            col = f'return_{period}'
            if col in df.columns:
                valid_returns = df[col].dropna()
                if len(valid_returns) > 0:
                    stats[f'{period}_mean'] = round(valid_returns.mean(), 2)
                    stats[f'{period}_median'] = round(valid_returns.median(), 2)
                    stats[f'{period}_std'] = round(valid_returns.std(), 2)
                    stats[f'{period}_positive_pct'] = round((valid_returns > 0).mean() * 100, 1)
                    stats[f'{period}_negative_pct'] = round((valid_returns < 0).mean() * 100, 1)
                    stats[f'{period}_min'] = round(valid_returns.min(), 2)
                    stats[f'{period}_max'] = round(valid_returns.max(), 2)
        
        return stats
    
    def get_all_analyzed_symbols(self) -> List[str]:
        """Get list of all symbols that have been analyzed."""
        query = "SELECT DISTINCT symbol FROM volume_cluster_events ORDER BY symbol"
        with self.engine.connect() as conn:
            result = conn.execute(text(query))
            return [row[0] for row in result]


if __name__ == "__main__":
    analyzer = VolumeEventAnalyzer()
    events = analyzer.analyze_stock('RELIANCE.NS')
    print(f"Found {len(events)} high volume events for RELIANCE.NS")
    
    if events:
        count = analyzer.save_events_to_db(events)
        print(f"Saved {count} events to database")
        
        stats = analyzer.get_return_statistics('RELIANCE.NS', 'Very High')
        print("\nVery High Volume Statistics:")
        for k, v in stats.items():
            print(f"  {k}: {v}")
