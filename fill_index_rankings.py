#!/usr/bin/env python3
"""
Fill missing index rankings for sector rotation analysis.

This script calculates RS Rating, Momentum, Trend, Technical, and Composite scores
for indices that are missing historical rankings.
"""

import sys
sys.path.insert(0, '.')

import pandas as pd
import numpy as np
from datetime import datetime, date, timedelta
from sqlalchemy import text
from ranking.db.schema import get_ranking_engine

# Indices to calculate rankings for
INDICES_TO_FILL = [
    '^NSEI',           # Nifty 50
    '^NSEBANK',        # Bank Nifty  
    '^NSMIDCP',        # Nifty Midcap 100
    'NIFTY_FIN_SERVICE.NS',  # Nifty Financial Services
    'NIFTY_PVT_BANK.NS',     # Nifty Private Bank
]


def calculate_rs_rating(df: pd.DataFrame, benchmark_df: pd.DataFrame) -> float:
    """Calculate RS Rating (1-99) relative to benchmark (Nifty 50)."""
    if len(df) < 252 or len(benchmark_df) < 252:
        return 50.0  # Default if insufficient data
    
    # Calculate weighted returns
    periods = [(63, 0.4), (126, 0.2), (189, 0.2), (252, 0.2)]  # 3M, 6M, 9M, 12M
    
    stock_score = 0
    bench_score = 0
    
    for days, weight in periods:
        if len(df) > days and len(benchmark_df) > days:
            stock_ret = (df['close'].iloc[-1] / df['close'].iloc[-days] - 1) * 100
            bench_ret = (benchmark_df['close'].iloc[-1] / benchmark_df['close'].iloc[-days] - 1) * 100
            stock_score += stock_ret * weight
            bench_score += bench_ret * weight
    
    # Relative performance to RS Rating
    relative_perf = stock_score - bench_score
    rs_rating = 50 + (relative_perf * 2)  # Scale factor
    
    return max(1, min(99, rs_rating))


def calculate_momentum_score(df: pd.DataFrame) -> float:
    """Calculate momentum score (0-100) based on ROC."""
    if len(df) < 63:
        return 50.0
    
    current = df['close'].iloc[-1]
    scores = []
    
    # 1-week ROC
    if len(df) > 5:
        roc_1w = (current / df['close'].iloc[-6] - 1) * 100
        scores.append(50 + roc_1w * 5)
    
    # 1-month ROC
    if len(df) > 21:
        roc_1m = (current / df['close'].iloc[-22] - 1) * 100
        scores.append(50 + roc_1m * 2)
    
    # 3-month ROC
    if len(df) > 63:
        roc_3m = (current / df['close'].iloc[-64] - 1) * 100
        scores.append(50 + roc_3m * 1)
    
    if not scores:
        return 50.0
    
    # Weighted average with recency bias
    weights = [0.4, 0.35, 0.25][:len(scores)]
    momentum = sum(s * w for s, w in zip(scores, weights)) / sum(weights)
    
    return max(0, min(100, momentum))


def calculate_trend_score(df: pd.DataFrame) -> float:
    """Calculate trend template score (0-8 scaled to 0-100)."""
    if len(df) < 200:
        return 50.0
    
    current = df['close'].iloc[-1]
    ma20 = df['close'].rolling(20).mean().iloc[-1]
    ma50 = df['close'].rolling(50).mean().iloc[-1]
    ma150 = df['close'].rolling(150).mean().iloc[-1]
    ma200 = df['close'].rolling(200).mean().iloc[-1]
    
    score = 0
    
    # Price above MAs
    if current > ma50:
        score += 1
    if current > ma150:
        score += 1
    if current > ma200:
        score += 1
    
    # MA alignment
    if ma50 > ma150:
        score += 1
    if ma50 > ma200:
        score += 1
    if ma150 > ma200:
        score += 1
    
    # 200 MA trending up (compare to 20 days ago)
    if len(df) > 220:
        ma200_prev = df['close'].rolling(200).mean().iloc[-21]
        if ma200 > ma200_prev:
            score += 1
    
    # Price within 25% of 52-week high
    high_52w = df['high'].tail(252).max() if len(df) >= 252 else df['high'].max()
    if current >= high_52w * 0.75:
        score += 1
    
    # Scale 0-8 to 0-100
    return (score / 8) * 100


def calculate_technical_score(df: pd.DataFrame) -> float:
    """Calculate technical score based on RSI and price action."""
    if len(df) < 50:
        return 50.0
    
    score = 50.0
    
    # RSI
    delta = df['close'].diff()
    gain = delta.where(delta > 0, 0).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rs = gain / loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    current_rsi = rsi.iloc[-1]
    
    if pd.notna(current_rsi):
        if 50 <= current_rsi <= 70:
            score += 20  # Bullish but not overbought
        elif current_rsi > 70:
            score += 10  # Overbought
        elif 30 <= current_rsi < 50:
            score -= 10  # Neutral to bearish
        else:
            score -= 20  # Oversold
    
    # Volume trend (if available)
    if 'volume' in df.columns and df['volume'].iloc[-1] > 0:
        vol_avg = df['volume'].rolling(20).mean().iloc[-1]
        if df['volume'].iloc[-1] > vol_avg * 1.2:
            score += 10
    
    # Price momentum (close vs open trend)
    recent_closes = df['close'].tail(10)
    recent_opens = df['open'].tail(10) if 'open' in df.columns else recent_closes
    bullish_days = (recent_closes.values > recent_opens.values).sum()
    if bullish_days >= 6:
        score += 10
    elif bullish_days <= 3:
        score -= 10
    
    return max(0, min(100, score))


def fill_index_rankings():
    """Calculate and fill rankings for missing indices."""
    engine = get_ranking_engine()
    
    print("="*70)
    print("FILLING INDEX RANKINGS")
    print("="*70)
    
    # Get Nifty 50 data as benchmark (for RS calculation)
    with engine.connect() as conn:
        nifty_df = pd.read_sql(text("""
            SELECT date, open, high, low, close, volume
            FROM yfinance_indices_daily_quotes
            WHERE symbol = '^NSEI'
            ORDER BY date
        """), conn)
    
    nifty_df['date'] = pd.to_datetime(nifty_df['date'])
    print(f"Loaded Nifty 50 benchmark: {len(nifty_df)} records")
    print()
    
    for symbol in INDICES_TO_FILL:
        print(f"Processing {symbol}...")
        
        # Get price data
        with engine.connect() as conn:
            df = pd.read_sql(text("""
                SELECT date, open, high, low, close, volume
                FROM yfinance_indices_daily_quotes
                WHERE symbol = :symbol
                ORDER BY date
            """), conn, params={'symbol': symbol})
            
            # Get existing ranking dates
            existing = pd.read_sql(text("""
                SELECT ranking_date FROM stock_rankings_history
                WHERE symbol = :symbol
            """), conn, params={'symbol': symbol})
        
        if df.empty:
            print(f"  No price data for {symbol}")
            continue
        
        df['date'] = pd.to_datetime(df['date'])
        existing_dates = set(pd.to_datetime(existing['ranking_date']).dt.date) if not existing.empty else set()
        
        print(f"  Price data: {len(df)} records")
        print(f"  Existing rankings: {len(existing_dates)} dates")
        
        # Calculate rankings for each date (need at least 252 days of history)
        records_to_insert = []
        dates_processed = 0
        
        for i in range(252, len(df)):
            current_date = df['date'].iloc[i].date()
            
            # Skip if already exists
            if current_date in existing_dates:
                continue
            
            # Get data up to this date
            hist_df = df.iloc[:i+1].copy()
            
            # Get corresponding Nifty data
            nifty_hist = nifty_df[nifty_df['date'] <= df['date'].iloc[i]].copy()
            
            if len(hist_df) < 252 or len(nifty_hist) < 252:
                continue
            
            # Calculate scores
            rs_rating = calculate_rs_rating(hist_df, nifty_hist)
            momentum_score = calculate_momentum_score(hist_df)
            trend_score = calculate_trend_score(hist_df)
            technical_score = calculate_technical_score(hist_df)
            
            # Composite score (weighted average)
            composite_score = (
                rs_rating * 0.30 +
                momentum_score * 0.25 +
                trend_score * 0.25 +
                technical_score * 0.20
            )
            
            records_to_insert.append({
                'symbol': symbol,
                'ranking_date': current_date,
                'rs_rating': round(rs_rating, 2),
                'momentum_score': round(momentum_score, 2),
                'trend_template_score': round(trend_score / 100 * 8, 1),  # Scale back to 0-8
                'technical_score': round(technical_score, 2),
                'composite_score': round(composite_score, 2),
                'composite_rank': 0,  # Will be calculated separately
                'composite_percentile': 0,
            })
            
            dates_processed += 1
            
            if dates_processed % 100 == 0:
                print(f"    Processed {dates_processed} dates...")
        
        # Insert records
        if records_to_insert:
            print(f"  Inserting {len(records_to_insert)} new ranking records...")
            
            insert_df = pd.DataFrame(records_to_insert)
            
            with engine.begin() as conn:
                for _, row in insert_df.iterrows():
                    conn.execute(text("""
                        INSERT INTO stock_rankings_history 
                        (symbol, ranking_date, rs_rating, momentum_score, trend_template_score,
                         technical_score, composite_score, composite_rank, composite_percentile)
                        VALUES (:symbol, :ranking_date, :rs_rating, :momentum_score, :trend_template_score,
                                :technical_score, :composite_score, :composite_rank, :composite_percentile)
                        ON DUPLICATE KEY UPDATE
                        rs_rating = VALUES(rs_rating),
                        momentum_score = VALUES(momentum_score),
                        trend_template_score = VALUES(trend_template_score),
                        technical_score = VALUES(technical_score),
                        composite_score = VALUES(composite_score)
                    """), row.to_dict())
            
            print(f"  ✅ Inserted {len(records_to_insert)} records for {symbol}")
        else:
            print(f"  ✅ No new records needed for {symbol}")
        
        print()
    
    print("="*70)
    print("COMPLETE!")
    print("="*70)
    
    # Verify
    with engine.connect() as conn:
        for symbol in INDICES_TO_FILL:
            result = conn.execute(text("""
                SELECT COUNT(*) as cnt, MIN(ranking_date) as earliest, MAX(ranking_date) as latest
                FROM stock_rankings_history
                WHERE symbol = :symbol
            """), {'symbol': symbol}).fetchone()
            print(f"{symbol}: {result[0]} rankings ({result[1]} to {result[2]})")


if __name__ == "__main__":
    fill_index_rankings()
