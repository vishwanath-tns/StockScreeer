"""Repository layer for trend analysis data operations."""
from typing import List, Optional, Tuple
import pandas as pd
from datetime import date, datetime
from sqlalchemy import text


def create_trend_table(engine) -> None:
    """Create the trend_analysis table if it doesn't exist."""
    sql = text("""
    CREATE TABLE IF NOT EXISTS trend_analysis (
      id              BIGINT      AUTO_INCREMENT PRIMARY KEY,
      symbol          VARCHAR(64) NOT NULL,
      trade_date      DATE        NOT NULL,
      daily_trend     VARCHAR(10) NOT NULL,
      weekly_trend    VARCHAR(10) NOT NULL,
      monthly_trend   VARCHAR(10) NOT NULL,
      trend_rating    TINYINT     NOT NULL,
      created_at      TIMESTAMP   NOT NULL DEFAULT CURRENT_TIMESTAMP,
      updated_at      TIMESTAMP   NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
      
      UNIQUE KEY uk_symbol_date (symbol, trade_date),
      KEY idx_trade_date (trade_date),
      KEY idx_trend_rating (trend_rating),
      KEY idx_daily_trend (daily_trend),
      KEY idx_weekly_trend (weekly_trend),
      KEY idx_monthly_trend (monthly_trend)
    )
    """)
    with engine.begin() as conn:
        conn.execute(sql)


def get_ohlc_data(engine, symbol: str, start_date: Optional[str] = None, end_date: Optional[str] = None) -> pd.DataFrame:
    """Fetch OHLC data for a symbol within date range."""
    conditions = ["symbol = :symbol", "series = 'EQ'"]
    params = {"symbol": symbol}
    
    if start_date:
        conditions.append("trade_date >= :start_date")
        params["start_date"] = start_date
    if end_date:
        conditions.append("trade_date <= :end_date")
        params["end_date"] = end_date
        
    where_clause = " AND ".join(conditions)
    
    sql = text(f"""
    SELECT trade_date, symbol, open_price, high_price, low_price, close_price, prev_close
    FROM nse_equity_bhavcopy_full 
    WHERE {where_clause}
    ORDER BY trade_date
    """)
    
    with engine.connect() as conn:
        return pd.read_sql(sql, con=conn, params=params, index_col='trade_date', parse_dates=['trade_date'])


def get_all_symbols(engine, trade_date: Optional[str] = None) -> List[str]:
    """Get all unique symbols, optionally for a specific trade date."""
    if trade_date:
        sql = text("SELECT DISTINCT symbol FROM nse_equity_bhavcopy_full WHERE trade_date = :trade_date AND series = 'EQ' ORDER BY symbol")
        params = {"trade_date": trade_date}
    else:
        sql = text("SELECT DISTINCT symbol FROM nse_equity_bhavcopy_full WHERE series = 'EQ' ORDER BY symbol")
        params = {}
    
    with engine.connect() as conn:
        df = pd.read_sql(sql, con=conn, params=params)
    return df['symbol'].tolist()


def get_latest_trade_date(engine) -> Optional[str]:
    """Get the most recent trade date in the database."""
    sql = text("SELECT MAX(trade_date) as max_date FROM nse_equity_bhavcopy_full")
    with engine.connect() as conn:
        df = pd.read_sql(sql, con=conn)
    max_date = df['max_date'].iloc[0]
    return max_date.strftime('%Y-%m-%d') if max_date else None


def get_all_trade_dates(engine) -> List[str]:
    """Get all unique trade dates in the database."""
    sql = text("SELECT DISTINCT trade_date FROM nse_equity_bhavcopy_full ORDER BY trade_date DESC")
    with engine.connect() as conn:
        df = pd.read_sql(sql, con=conn)
    return [d.strftime('%Y-%m-%d') for d in df['trade_date']]


def save_trend_analysis(engine, symbol: str, trade_date: str, daily_trend: str, weekly_trend: str, monthly_trend: str, trend_rating: int) -> None:
    """Save or update trend analysis for a symbol and date."""
    sql = text("""
    INSERT INTO trend_analysis (symbol, trade_date, daily_trend, weekly_trend, monthly_trend, trend_rating)
    VALUES (%s, %s, %s, %s, %s, %s)
    ON DUPLICATE KEY UPDATE
        daily_trend = VALUES(daily_trend),
        weekly_trend = VALUES(weekly_trend),
        monthly_trend = VALUES(monthly_trend),
        trend_rating = VALUES(trend_rating),
        updated_at = CURRENT_TIMESTAMP
    """)
    with engine.begin() as conn:
        conn.execute(sql, (symbol, trade_date, daily_trend, weekly_trend, monthly_trend, trend_rating))


def get_trend_analysis(engine, trade_date: Optional[str] = None, limit: Optional[int] = None) -> pd.DataFrame:
    """Fetch trend analysis results, optionally filtered by date."""
    conditions = []
    params = {}
    
    if trade_date:
        conditions.append("trade_date = :trade_date")
        params["trade_date"] = trade_date
    
    where_clause = " WHERE " + " AND ".join(conditions) if conditions else ""
    limit_clause = f" LIMIT {limit}" if limit else ""
    
    sql = text(f"""
    SELECT symbol, trade_date, daily_trend, weekly_trend, monthly_trend, trend_rating, created_at, updated_at
    FROM trend_analysis{where_clause}
    ORDER BY trend_rating DESC, symbol{limit_clause}
    """)
    
    with engine.connect() as conn:
        return pd.read_sql(sql, con=conn, params=params, parse_dates=['trade_date', 'created_at', 'updated_at'])


def get_weekly_candle(engine, symbol: str, trade_date: str) -> Optional[Tuple[float, float, float, float]]:
    """Get weekly OHLC for the week containing the given trade_date."""
    # Get the week's data (Monday to Friday) 
    sql = text("""
    SELECT 
        (SELECT open_price FROM nse_equity_bhavcopy_full 
         WHERE symbol = :symbol AND series = 'EQ'
         AND WEEK(trade_date, 1) = WEEK(:trade_date1, 1) 
         AND YEAR(trade_date) = YEAR(:trade_date2)
         ORDER BY trade_date ASC LIMIT 1) as week_open,
        MAX(high_price) as week_high, 
        MIN(low_price) as week_low,
        (SELECT close_price FROM nse_equity_bhavcopy_full 
         WHERE symbol = :symbol AND series = 'EQ'
         AND WEEK(trade_date, 1) = WEEK(:trade_date1, 1) 
         AND YEAR(trade_date) = YEAR(:trade_date2)
         ORDER BY trade_date DESC LIMIT 1) as week_close
    FROM nse_equity_bhavcopy_full 
    WHERE symbol = :symbol AND series = 'EQ'
    AND WEEK(trade_date, 1) = WEEK(:trade_date1, 1) 
    AND YEAR(trade_date) = YEAR(:trade_date2)
    """)
    with engine.connect() as conn:
        df = pd.read_sql(sql, con=conn, params={"symbol": symbol, "trade_date1": trade_date, "trade_date2": trade_date})
    if df.empty or df['week_open'].iloc[0] is None:
        return None
    return (df['week_open'].iloc[0], df['week_high'].iloc[0], 
            df['week_low'].iloc[0], df['week_close'].iloc[0])


def get_monthly_candle(engine, symbol: str, trade_date: str) -> Optional[Tuple[float, float, float, float]]:
    """Get monthly OHLC for the month containing the given trade_date."""
    sql = text("""
    SELECT 
        (SELECT open_price FROM nse_equity_bhavcopy_full 
         WHERE symbol = :symbol AND series = 'EQ'
         AND MONTH(trade_date) = MONTH(:trade_date1) 
         AND YEAR(trade_date) = YEAR(:trade_date2)
         ORDER BY trade_date ASC LIMIT 1) as month_open,
        MAX(high_price) as month_high, 
        MIN(low_price) as month_low,
        (SELECT close_price FROM nse_equity_bhavcopy_full 
         WHERE symbol = :symbol AND series = 'EQ'
         AND MONTH(trade_date) = MONTH(:trade_date1) 
         AND YEAR(trade_date) = YEAR(:trade_date2)
         ORDER BY trade_date DESC LIMIT 1) as month_close
    FROM nse_equity_bhavcopy_full 
    WHERE symbol = :symbol AND series = 'EQ'
    AND MONTH(trade_date) = MONTH(:trade_date1) 
    AND YEAR(trade_date) = YEAR(:trade_date2)
    """)
    with engine.connect() as conn:
        df = pd.read_sql(sql, con=conn, params={"symbol": symbol, "trade_date1": trade_date, "trade_date2": trade_date})
    if df.empty or df['month_open'].iloc[0] is None:
        return None
    return (df['month_open'].iloc[0], df['month_high'].iloc[0], 
            df['month_low'].iloc[0], df['month_close'].iloc[0])