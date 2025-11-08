"""Service layer for trend analysis business logic."""
from typing import Dict, List, Optional, Tuple
import pandas as pd
from datetime import datetime, date
from sqlalchemy import text
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

from db.connection import ensure_engine
from db.trends_repo import (
    create_trend_table, get_ohlc_data, get_all_symbols, get_latest_trade_date,
    get_all_trade_dates, save_trend_analysis, get_trend_analysis,
    get_weekly_candle, get_monthly_candle
)


def determine_candle_trend(open_price: float, close_price: float) -> str:
    """Determine if a candle is UP (green) or DOWN (red) based on open/close prices."""
    if close_price > open_price:
        return "UP"
    else:
        return "DOWN"


def calculate_trend_rating(daily_trend: str, weekly_trend: str, monthly_trend: str) -> float:
    """
    Calculate improved trend rating with weights and better scale.
    
    Weighting System:
    - Monthly trend: 50% weight (most important - long term direction)
    - Weekly trend: 30% weight (medium term momentum)  
    - Daily trend: 20% weight (short term noise)
    
    Returns: Float from -10.0 to +10.0
    """
    trend_values = {
        "UP": 1,
        "DOWN": -1,
        "SIDEWAYS": 0  # Future enhancement
    }
    
    daily_val = trend_values.get(daily_trend, 0)
    weekly_val = trend_values.get(weekly_trend, 0) 
    monthly_val = trend_values.get(monthly_trend, 0)
    
    # Apply weights (Monthly 50%, Weekly 30%, Daily 20%)
    weighted_score = (monthly_val * 0.5) + (weekly_val * 0.3) + (daily_val * 0.2)
    
    # Scale to -10 to +10 range for clarity
    numeric_rating = round(weighted_score * 10, 1)
    
    return numeric_rating


def get_rating_description(rating: float) -> dict:
    """Get category and description for a trend rating."""
    if rating >= 8:
        return {
            "category": "VERY BULLISH",
            "description": "Strong uptrend across all timeframes"
        }
    elif rating >= 5:
        return {
            "category": "BULLISH", 
            "description": "Solid uptrend with strong longer-term momentum"
        }
    elif rating >= 2:
        return {
            "category": "MODERATELY BULLISH",
            "description": "Generally positive with some mixed signals"
        }
    elif rating >= -2:
        return {
            "category": "NEUTRAL/MIXED",
            "description": "Conflicting signals across timeframes"
        }
    elif rating >= -5:
        return {
            "category": "MODERATELY BEARISH",
            "description": "Generally negative with some mixed signals"
        }
    elif rating >= -8:
        return {
            "category": "BEARISH",
            "description": "Solid downtrend with strong longer-term weakness"
        }
    else:
        return {
            "category": "VERY BEARISH",
            "description": "Strong downtrend across all timeframes"
        }


def analyze_symbol_trend_with_conn(symbol: str, trade_date: str, conn) -> Optional[Dict]:
    """Analyze trend for a single symbol on a specific date using existing connection."""
    # Get daily candle data
    daily_sql = text("""
    SELECT trade_date, symbol, open_price, high_price, low_price, close_price, prev_close
    FROM nse_equity_bhavcopy_full 
    WHERE symbol = :symbol AND series = 'EQ' AND trade_date = :trade_date
    ORDER BY trade_date
    """)
    daily_data = pd.read_sql(daily_sql, con=conn, params={"symbol": symbol, "trade_date": trade_date}, 
                           index_col='trade_date', parse_dates=['trade_date'])
    if daily_data.empty:
        return None
    
    daily_row = daily_data.iloc[0]
    daily_open = daily_row['open_price']
    daily_close = daily_row['close_price']
    daily_trend = determine_candle_trend(daily_open, daily_close)
    
    # Get weekly candle using connection
    weekly_sql = text("""
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
    weekly_df = pd.read_sql(weekly_sql, con=conn, params={"symbol": symbol, "trade_date1": trade_date, "trade_date2": trade_date})
    if weekly_df.empty or weekly_df['week_open'].iloc[0] is None:
        return None
    
    weekly_open = weekly_df['week_open'].iloc[0]
    weekly_close = weekly_df['week_close'].iloc[0]
    weekly_trend = determine_candle_trend(weekly_open, weekly_close)
    
    # Get monthly candle using connection
    monthly_sql = text("""
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
    monthly_df = pd.read_sql(monthly_sql, con=conn, params={"symbol": symbol, "trade_date1": trade_date, "trade_date2": trade_date})
    if monthly_df.empty or monthly_df['month_open'].iloc[0] is None:
        return None
    
    monthly_open = monthly_df['month_open'].iloc[0]
    monthly_close = monthly_df['month_close'].iloc[0]
    monthly_trend = determine_candle_trend(monthly_open, monthly_close)
    
    # Calculate rating
    trend_rating = calculate_trend_rating(daily_trend, weekly_trend, monthly_trend)
    
    return {
        'symbol': symbol,
        'trade_date': trade_date,
        'daily_trend': daily_trend,
        'weekly_trend': weekly_trend,
        'monthly_trend': monthly_trend,
        'trend_rating': trend_rating,
        'daily_open': daily_open,
        'daily_close': daily_close,
        'weekly_open': weekly_open,
        'weekly_close': weekly_close,
        'monthly_open': monthly_open,
        'monthly_close': monthly_close
    }


def save_trend_analysis_with_conn(conn, symbol: str, trade_date: str, daily_trend: str, weekly_trend: str, monthly_trend: str, trend_rating: int) -> None:
    """Save or update trend analysis for a symbol and date using existing connection."""
    sql = text("""
    INSERT INTO trend_analysis (symbol, trade_date, daily_trend, weekly_trend, monthly_trend, trend_rating)
    VALUES (:symbol, :trade_date, :daily_trend, :weekly_trend, :monthly_trend, :trend_rating)
    ON DUPLICATE KEY UPDATE
        daily_trend = VALUES(daily_trend),
        weekly_trend = VALUES(weekly_trend),
        monthly_trend = VALUES(monthly_trend),
        trend_rating = VALUES(trend_rating),
        updated_at = CURRENT_TIMESTAMP
    """)
    conn.execute(sql, {
        "symbol": symbol,
        "trade_date": trade_date, 
        "daily_trend": daily_trend,
        "weekly_trend": weekly_trend,
        "monthly_trend": monthly_trend,
        "trend_rating": trend_rating
    })
    conn.commit()


def analyze_symbol_trend(symbol: str, trade_date: str, engine=None) -> Optional[Dict]:
    """Analyze trend for a single symbol on a specific date."""
    if engine is None:
        # Use the working engine from reporting_adv_decl instead of ensure_engine
        import reporting_adv_decl as rad
        engine = rad.engine()
    
    # Get daily candle data
    daily_data = get_ohlc_data(engine, symbol, trade_date, trade_date)
    if daily_data.empty:
        return None
    
    daily_row = daily_data.iloc[0]
    daily_open = daily_row['open_price']
    daily_close = daily_row['close_price']
    daily_trend = determine_candle_trend(daily_open, daily_close)
    
    # Get weekly candle
    weekly_ohlc = get_weekly_candle(engine, symbol, trade_date)
    if weekly_ohlc is None:
        return None
    
    weekly_open, _, _, weekly_close = weekly_ohlc
    weekly_trend = determine_candle_trend(weekly_open, weekly_close)
    
    # Get monthly candle
    monthly_ohlc = get_monthly_candle(engine, symbol, trade_date)
    if monthly_ohlc is None:
        return None
    
    monthly_open, _, _, monthly_close = monthly_ohlc
    monthly_trend = determine_candle_trend(monthly_open, monthly_close)
    
    # Calculate rating
    trend_rating = calculate_trend_rating(daily_trend, weekly_trend, monthly_trend)
    
    return {
        'symbol': symbol,
        'trade_date': trade_date,
        'daily_trend': daily_trend,
        'weekly_trend': weekly_trend,
        'monthly_trend': monthly_trend,
        'trend_rating': trend_rating,
        'daily_open': daily_open,
        'daily_close': daily_close,
        'weekly_open': weekly_open,
        'weekly_close': weekly_close,
        'monthly_open': monthly_open,
        'monthly_close': monthly_close
    }


def scan_current_day_trends(engine=None) -> pd.DataFrame:
    """Scan trends for all symbols on the latest trade date."""
    if engine is None:
        # Use the working engine from reporting_adv_decl instead of ensure_engine
        import reporting_adv_decl as rad
        engine = rad.engine()
    
    # Ensure table exists
    create_trend_table(engine)
    
    latest_date = get_latest_trade_date(engine)
    if not latest_date:
        return pd.DataFrame()
    
    symbols = get_all_symbols(engine, latest_date)
    results = []
    
    # Use a single connection for all operations to avoid connection pool issues
    with engine.connect() as conn:
        for symbol in symbols:
            try:
                trend_data = analyze_symbol_trend_with_conn(symbol, latest_date, conn)
                if trend_data:
                    # Save to database using the same connection
                    save_trend_analysis_with_conn(
                        conn, symbol, latest_date,
                        trend_data['daily_trend'],
                        trend_data['weekly_trend'],
                        trend_data['monthly_trend'],
                        trend_data['trend_rating']
                    )
                    results.append(trend_data)
            except Exception as e:
                print(f"Error analyzing {symbol}: {e}")
                continue
    
    return pd.DataFrame(results)


def process_date_batch(engine, trade_date: str, symbols: List[str], progress_callback=None) -> int:
    """Process a batch of symbols for a specific trade date in parallel."""
    processed_count = 0
    
    # Create a fresh connection for this thread
    with engine.connect() as conn:
        for symbol in symbols:
            try:
                trend_data = analyze_symbol_trend_with_conn(symbol, trade_date, conn)
                if trend_data:
                    save_trend_analysis_with_conn(
                        conn, symbol, trade_date,
                        trend_data['daily_trend'],
                        trend_data['weekly_trend'],
                        trend_data['monthly_trend'],
                        trend_data['trend_rating']
                    )
                    processed_count += 1
            except Exception as e:
                if progress_callback:
                    progress_callback(f"Error analyzing {symbol} on {trade_date}: {e}")
                continue
    
    return processed_count


def scan_all_historical_trends_parallel(engine=None, progress_callback=None, max_workers=4) -> int:
    """Scan trends for all symbols across all available trade dates using parallel processing."""
    if engine is None:
        # Use the working engine from reporting_adv_decl instead of ensure_engine
        import reporting_adv_decl as rad
        engine = rad.engine()
    
    # Ensure table exists
    create_trend_table(engine)
    
    trade_dates = get_all_trade_dates(engine)
    total_processed = 0
    
    start_time = time.time()
    
    if progress_callback:
        progress_callback(f"Starting parallel processing with {max_workers} workers for {len(trade_dates)} trade dates...")
    
    # Process dates in parallel
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all date processing tasks
        future_to_date = {}
        
        for i, trade_date in enumerate(trade_dates):
            # Get symbols for this date
            with engine.connect() as conn:
                symbols_sql = text("SELECT DISTINCT symbol FROM nse_equity_bhavcopy_full WHERE trade_date = :trade_date AND series = 'EQ' ORDER BY symbol")
                symbols_df = pd.read_sql(symbols_sql, con=conn, params={"trade_date": trade_date})
                symbols = symbols_df['symbol'].tolist()
            
            if symbols:  # Only process if there are symbols for this date
                # Split symbols into smaller batches for better parallel distribution
                batch_size = max(50, len(symbols) // max_workers)  # At least 50 symbols per batch
                symbol_batches = [symbols[i:i + batch_size] for i in range(0, len(symbols), batch_size)]
                
                for batch_idx, symbol_batch in enumerate(symbol_batches):
                    future = executor.submit(process_date_batch, engine, trade_date, symbol_batch, progress_callback)
                    future_to_date[future] = (trade_date, batch_idx + 1, len(symbol_batches), len(symbol_batch))
        
        # Collect results as they complete
        completed_dates = set()
        for future in as_completed(future_to_date):
            trade_date, batch_num, total_batches, batch_size = future_to_date[future]
            try:
                batch_processed = future.result()
                total_processed += batch_processed
                
                # Update progress
                if trade_date not in completed_dates and progress_callback:
                    progress_callback(f"Completed {trade_date} (batch {batch_num}/{total_batches}, {batch_size} symbols, {batch_processed} processed)")
                
                # Mark date as completed when all batches are done
                if batch_num == total_batches:
                    completed_dates.add(trade_date)
                    
            except Exception as e:
                if progress_callback:
                    progress_callback(f"Error processing batch for {trade_date}: {e}")
    
    elapsed_time = time.time() - start_time
    if progress_callback:
        progress_callback(f"Parallel processing completed! Processed {total_processed} records in {elapsed_time:.2f} seconds")
        progress_callback(f"Average rate: {total_processed / elapsed_time:.2f} records/second")
    
    return total_processed


def scan_all_historical_trends(engine=None, progress_callback=None) -> int:
    """Scan trends for all symbols across all available trade dates."""
    if engine is None:
        # Use the working engine from reporting_adv_decl instead of ensure_engine
        import reporting_adv_decl as rad
        engine = rad.engine()
    
    # Ensure table exists
    create_trend_table(engine)
    
    trade_dates = get_all_trade_dates(engine)
    total_processed = 0
    
    # Use a single connection for all operations to avoid connection pool issues
    with engine.connect() as conn:
        for i, trade_date in enumerate(trade_dates):
            if progress_callback:
                progress_callback(f"Processing {trade_date} ({i+1}/{len(trade_dates)})")
            
            # Get symbols for this date using direct SQL to avoid multiple connections
            symbols_sql = text("SELECT DISTINCT symbol FROM nse_equity_bhavcopy_full WHERE trade_date = :trade_date AND series = 'EQ' ORDER BY symbol")
            symbols_df = pd.read_sql(symbols_sql, con=conn, params={"trade_date": trade_date})
            symbols = symbols_df['symbol'].tolist()
            
            for symbol in symbols:
                try:
                    trend_data = analyze_symbol_trend_with_conn(symbol, trade_date, conn)
                    if trend_data:
                        save_trend_analysis_with_conn(
                            conn, symbol, trade_date,
                            trend_data['daily_trend'],
                            trend_data['weekly_trend'],
                            trend_data['monthly_trend'],
                            trend_data['trend_rating']
                        )
                        total_processed += 1
                except Exception as e:
                    print(f"Error analyzing {symbol} on {trade_date}: {e}")
                    continue
    
    return total_processed


def get_trend_results(trade_date: Optional[str] = None, limit: Optional[int] = None, engine=None) -> pd.DataFrame:
    """Get trend analysis results from database."""
    if engine is None:
        # Use the working engine from reporting_adv_decl instead of ensure_engine
        import reporting_adv_decl as rad
        engine = rad.engine()
    
    return get_trend_analysis(engine, trade_date, limit)


def get_trend_summary_stats(engine=None) -> Dict:
    """Get summary statistics about trend analysis results."""
    if engine is None:
        # Use the working engine from reporting_adv_decl instead of ensure_engine
        import reporting_adv_decl as rad
        engine = rad.engine()
    
    sql = text("""
    SELECT 
        COUNT(*) as total_records,
        COUNT(DISTINCT symbol) as unique_symbols,
        COUNT(DISTINCT trade_date) as unique_dates,
        AVG(trend_rating) as avg_rating,
        MIN(trend_rating) as min_rating,
        MAX(trend_rating) as max_rating,
        SUM(CASE WHEN trend_rating > 0 THEN 1 ELSE 0 END) as positive_ratings,
        SUM(CASE WHEN trend_rating < 0 THEN 1 ELSE 0 END) as negative_ratings,
        SUM(CASE WHEN trend_rating = 0 THEN 1 ELSE 0 END) as neutral_ratings
    FROM trend_analysis
    """)
    
    with engine.connect() as conn:
        df = pd.read_sql(sql, con=conn)
    return df.iloc[0].to_dict() if not df.empty else {}


def get_stock_trend_analysis(symbol: str, engine=None) -> pd.DataFrame:
    """Get trend analysis results for a specific stock symbol."""
    if engine is None:
        # Use the working engine from reporting_adv_decl instead of ensure_engine
        import reporting_adv_decl as rad
        engine = rad.engine()
    
    sql = text("""
    SELECT trade_date, symbol, daily_trend, weekly_trend, monthly_trend, 
           trend_rating, created_at
    FROM trend_analysis 
    WHERE symbol = :symbol
    ORDER BY trade_date DESC
    LIMIT 1000
    """)
    
    with engine.connect() as conn:
        df = pd.read_sql(sql, con=conn, params={'symbol': symbol})
    return df


def scan_historical_trends_for_range(start_date: date, end_date: date, engine=None) -> pd.DataFrame:
    """Scan historical trends for a specific date range."""
    if engine is None:
        # Use the working engine from reporting_adv_decl instead of ensure_engine
        import reporting_adv_decl as rad
        engine = rad.engine()
    
    print(f"Starting historical trend analysis for date range: {start_date} to {end_date}")
    
    # Get all trade dates in the range
    sql = text("""
    SELECT DISTINCT trade_date 
    FROM nse_equity_bhavcopy_full 
    WHERE trade_date >= :start_date AND trade_date <= :end_date
    ORDER BY trade_date
    """)
    
    with engine.connect() as conn:
        dates_df = pd.read_sql(sql, con=conn, params={
            'start_date': start_date.strftime('%Y-%m-%d'),
            'end_date': end_date.strftime('%Y-%m-%d')
        })
    
    if dates_df.empty:
        print(f"No trading data found for date range {start_date} to {end_date}")
        return pd.DataFrame()
    
    trade_dates = dates_df['trade_date'].tolist()
    print(f"Found {len(trade_dates)} trading dates in range")
    
    # Use single connection for bulk processing
    with engine.begin() as conn:
        total_processed = 0
        
        for i, trade_date in enumerate(trade_dates, 1):
            trade_date_str = trade_date.strftime('%Y-%m-%d') if hasattr(trade_date, 'strftime') else str(trade_date)
            
            print(f"Processing date {i}/{len(trade_dates)}: {trade_date_str}")
            
            # Check if already processed (duplicate prevention)
            existing_sql = text("""
            SELECT COUNT(*) as count 
            FROM trend_analysis 
            WHERE trade_date = :trade_date
            """)
            
            existing_result = conn.execute(existing_sql, {'trade_date': trade_date_str}).fetchone()
            if existing_result and existing_result.count > 0:
                print(f"  Skipping {trade_date_str} - already processed")
                continue
            
            # Get symbols for this date
            symbols_sql = text("""
            SELECT DISTINCT symbol 
            FROM nse_equity_bhavcopy_full 
            WHERE trade_date = :trade_date
            AND series = 'EQ'
            ORDER BY symbol
            """)
            
            symbols_df = pd.read_sql(symbols_sql, con=conn.connection, params={'trade_date': trade_date_str})
            symbols = symbols_df['symbol'].tolist()
            
            if not symbols:
                print(f"  No symbols found for {trade_date_str}")
                continue
            
            # Process symbols for this date
            date_processed = 0
            for symbol in symbols:
                try:
                    trend_result = analyze_symbol_trend_with_conn(symbol, trade_date_str, conn)
                    if trend_result:
                        date_processed += 1
                        total_processed += 1
                except Exception as e:
                    print(f"  Error processing {symbol} for {trade_date_str}: {e}")
                    continue
            
            print(f"  Processed {date_processed} symbols for {trade_date_str}")
    
    print(f"Historical trend analysis completed. Total records processed: {total_processed}")
    
    # Return results for the date range
    return get_trend_analysis_for_range(start_date, end_date, engine)


def get_trend_analysis_for_range(start_date: date, end_date: date, engine=None) -> pd.DataFrame:
    """Get trend analysis results for a date range."""
    if engine is None:
        # Use the working engine from reporting_adv_decl instead of ensure_engine
        import reporting_adv_decl as rad
        engine = rad.engine()
    
    sql = text("""
    SELECT trade_date, symbol, daily_trend, weekly_trend, monthly_trend, 
           trend_rating, created_at
    FROM trend_analysis 
    WHERE trade_date >= :start_date AND trade_date <= :end_date
    ORDER BY trade_date DESC, trend_rating DESC
    LIMIT 5000
    """)
    
    with engine.connect() as conn:
        df = pd.read_sql(sql, con=conn, params={
            'start_date': start_date.strftime('%Y-%m-%d'),
            'end_date': end_date.strftime('%Y-%m-%d')
        })
    return df