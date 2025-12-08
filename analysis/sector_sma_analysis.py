"""
Sector SMA Breadth Analysis
===========================
Analyzes % stocks above SMA by sector to identify:
1. Which sectors are leading/lagging during market turns
2. Relative strength of sectors
3. Stocks that lead sector recovery (first to cross above SMA)

Key Insights:
- When overall market % above 50 SMA is trending down:
  - Sectors with HIGHER % above SMA are showing relative strength (defensive/leaders)
  - Sectors with LOWER % above SMA are weak (avoid or short candidates)
  
- When market forms a TROUGH (% above SMA bottoms):
  - Sectors that bottom FIRST and start recovering are leaders
  - Stocks within leading sectors that cross above SMA first = potential leaders
  
- When market forms a TOP (% above SMA peaks):
  - Sectors that peak FIRST and start declining are weakening
  - Exit these sectors first
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from sqlalchemy import create_engine, text
from urllib.parse import quote_plus
import os
from dotenv import load_dotenv

load_dotenv()


def get_engine():
    """Create database engine."""
    password = quote_plus(os.getenv('MYSQL_PASSWORD', ''))
    return create_engine(
        f"mysql+pymysql://{os.getenv('MYSQL_USER')}:{password}"
        f"@{os.getenv('MYSQL_HOST')}:{os.getenv('MYSQL_PORT')}/{os.getenv('MYSQL_DB')}",
        pool_pre_ping=True,
        pool_recycle=3600
    )


def get_sector_stocks(engine, index_name='NIFTY500'):
    """Get stocks with their sector/industry mapping."""
    query = f"""
        SELECT symbol, industry 
        FROM nse_index_constituents 
        WHERE index_name = '{index_name}'
    """
    return pd.read_sql(query, engine)


def get_stock_sma_data(engine, symbols, sma_period=50, start_date='2024-01-01'):
    """Get SMA data for stocks.
    
    Note: yfinance_daily_ma uses .NS suffix for symbols, so we convert.
    """
    # Add .NS suffix for yfinance table
    symbols_ns = [f"{s}.NS" for s in symbols]
    symbols_str = "', '".join(symbols_ns)
    sma_col = f'sma_{sma_period}'
    
    query = f"""
        SELECT date, REPLACE(symbol, '.NS', '') as symbol, close, {sma_col}
        FROM yfinance_daily_ma
        WHERE symbol IN ('{symbols_str}')
        AND date >= '{start_date}'
        AND {sma_col} IS NOT NULL
        ORDER BY date, symbol
    """
    return pd.read_sql(query, engine, parse_dates=['date'])


def calculate_sector_breadth(engine, index_name='NIFTY500', sma_period=50, 
                            start_date='2024-01-01', log_cb=print):
    """
    Calculate % stocks above SMA for each sector.
    
    Returns DataFrame with columns:
    - date
    - sector (industry)
    - pct_above: % of stocks in sector above SMA
    - stocks_above: count above SMA
    - total_stocks: total stocks in sector
    """
    log_cb(f"Loading sector mapping for {index_name}...")
    sector_df = get_sector_stocks(engine, index_name)
    
    if sector_df.empty:
        log_cb("ERROR: No sector data found!")
        return pd.DataFrame()
    
    log_cb(f"Found {len(sector_df)} stocks across {sector_df['industry'].nunique()} sectors")
    
    # Get SMA data
    log_cb(f"Loading SMA-{sma_period} data...")
    sma_df = get_stock_sma_data(engine, sector_df['symbol'].tolist(), sma_period, start_date)
    
    if sma_df.empty:
        log_cb("ERROR: No SMA data found!")
        return pd.DataFrame()
    
    log_cb(f"Loaded {len(sma_df)} rows for {sma_df['symbol'].nunique()} symbols")
    
    # Merge with sector info
    sma_df = sma_df.merge(sector_df, on='symbol', how='left')
    
    # Calculate above/below SMA
    sma_col = f'sma_{sma_period}'
    sma_df['above_sma'] = (sma_df['close'] > sma_df[sma_col]).astype(int)
    
    # Group by date and sector
    sector_breadth = sma_df.groupby(['date', 'industry']).agg(
        stocks_above=('above_sma', 'sum'),
        total_stocks=('symbol', 'count')
    ).reset_index()
    
    sector_breadth['pct_above'] = (sector_breadth['stocks_above'] / sector_breadth['total_stocks'] * 100).round(2)
    sector_breadth = sector_breadth.rename(columns={'industry': 'sector'})
    
    log_cb(f"Calculated breadth for {len(sector_breadth)} sector-date combinations")
    
    return sector_breadth


def calculate_sector_relative_strength(sector_breadth_df, market_breadth_df):
    """
    Calculate relative strength of each sector vs overall market.
    
    RS = Sector % Above SMA - Market % Above SMA
    
    Positive RS = sector is stronger than market
    Negative RS = sector is weaker than market
    """
    # Merge sector with market data
    merged = sector_breadth_df.merge(
        market_breadth_df[['date', 'pct_above']].rename(columns={'pct_above': 'market_pct_above'}),
        on='date',
        how='left'
    )
    
    merged['relative_strength'] = merged['pct_above'] - merged['market_pct_above']
    
    return merged


def find_sector_leaders_at_trough(sector_breadth_df, market_breadth_df, trough_date):
    """
    Find sectors that show relative strength at market troughs.
    
    At troughs, sectors with:
    - Higher % above SMA than market average = defensive/strong
    - Already recovering (rising from their own trough) = leaders
    """
    # Get data around the trough (5 days before and after)
    trough_window = sector_breadth_df[
        (sector_breadth_df['date'] >= trough_date - timedelta(days=10)) &
        (sector_breadth_df['date'] <= trough_date + timedelta(days=10))
    ].copy()
    
    if trough_window.empty:
        return pd.DataFrame()
    
    # Calculate RS
    rs_df = calculate_sector_relative_strength(trough_window, market_breadth_df)
    
    # Get RS at trough date and after
    trough_rs = rs_df[rs_df['date'] == trough_date].copy()
    
    if trough_rs.empty:
        # Try nearest date
        nearest_date = rs_df['date'].unique()[len(rs_df['date'].unique())//2]
        trough_rs = rs_df[rs_df['date'] == nearest_date].copy()
    
    return trough_rs.sort_values('relative_strength', ascending=False)


def find_leading_stocks_in_sector(engine, sector, sma_period=50, 
                                   lookback_days=20, log_cb=print):
    """
    Find stocks in a sector that crossed above SMA recently.
    These are potential leaders as they're showing early strength.
    
    Returns stocks sorted by:
    1. How recently they crossed above SMA (more recent = better)
    2. How far above SMA they are (higher = stronger momentum)
    """
    # Get stocks in sector
    sector_stocks = pd.read_sql(f"""
        SELECT symbol FROM nse_index_constituents 
        WHERE index_name = 'NIFTY500' AND industry = '{sector}'
    """, engine)
    
    if sector_stocks.empty:
        return pd.DataFrame()
    
    # Add .NS suffix for yfinance table
    symbols = [f"{s}.NS" for s in sector_stocks['symbol'].tolist()]
    symbols_str = "', '".join(symbols)
    sma_col = f'sma_{sma_period}'
    
    # Get recent data
    query = f"""
        SELECT date, REPLACE(symbol, '.NS', '') as symbol, close, {sma_col}
        FROM yfinance_daily_ma
        WHERE symbol IN ('{symbols_str}')
        AND date >= DATE_SUB(CURDATE(), INTERVAL {lookback_days} DAY)
        AND {sma_col} IS NOT NULL
        ORDER BY symbol, date
    """
    df = pd.read_sql(query, engine, parse_dates=['date'])
    
    if df.empty:
        return pd.DataFrame()
    
    # Find crossover events
    results = []
    for symbol in df['symbol'].unique():
        stock_df = df[df['symbol'] == symbol].sort_values('date')
        if len(stock_df) < 2:
            continue
        
        stock_df['above_sma'] = stock_df['close'] > stock_df[sma_col]
        stock_df['prev_above'] = stock_df['above_sma'].shift(1)
        
        # Find bullish crossovers (False -> True)
        crossovers = stock_df[(stock_df['above_sma'] == True) & (stock_df['prev_above'] == False)]
        
        if not crossovers.empty:
            last_cross = crossovers.iloc[-1]
            latest = stock_df.iloc[-1]
            
            # Calculate distance from SMA
            pct_above_sma = ((latest['close'] - latest[sma_col]) / latest[sma_col] * 100)
            
            results.append({
                'symbol': symbol,
                'cross_date': last_cross['date'],
                'days_since_cross': (latest['date'] - last_cross['date']).days,
                'current_price': latest['close'],
                'sma_value': latest[sma_col],
                'pct_above_sma': round(pct_above_sma, 2),
                'still_above': latest['above_sma']
            })
    
    if not results:
        return pd.DataFrame()
    
    result_df = pd.DataFrame(results)
    # Sort by: still above SMA, days since cross (ascending), pct above (descending)
    result_df = result_df[result_df['still_above'] == True].sort_values(
        ['days_since_cross', 'pct_above_sma'], 
        ascending=[True, False]
    )
    
    return result_df


def get_sector_summary(engine, date=None, sma_period=50, log_cb=print):
    """
    Get current sector breadth summary.
    Shows which sectors are strongest/weakest right now.
    """
    if date is None:
        date = datetime.now().strftime('%Y-%m-%d')
    
    sector_breadth = calculate_sector_breadth(
        engine, 'NIFTY500', sma_period, 
        start_date=(datetime.strptime(date, '%Y-%m-%d') - timedelta(days=5)).strftime('%Y-%m-%d'),
        log_cb=log_cb
    )
    
    if sector_breadth.empty:
        return pd.DataFrame()
    
    # Get latest date data
    latest_date = sector_breadth['date'].max()
    latest = sector_breadth[sector_breadth['date'] == latest_date].copy()
    
    # Sort by % above SMA
    latest = latest.sort_values('pct_above', ascending=False)
    
    return latest


def analyze_sector_rotation(engine, start_date='2024-01-01', sma_period=50, log_cb=print):
    """
    Full sector rotation analysis.
    
    Returns:
    - sector_breadth: Daily breadth by sector
    - sector_summary: Current rankings
    - sector_momentum: Change in breadth over time
    """
    log_cb("=" * 60)
    log_cb("SECTOR ROTATION ANALYSIS")
    log_cb("=" * 60)
    
    # Calculate breadth
    sector_breadth = calculate_sector_breadth(engine, 'NIFTY500', sma_period, start_date, log_cb)
    
    if sector_breadth.empty:
        return None, None, None
    
    # Current rankings
    log_cb("\nCalculating current sector rankings...")
    latest_date = sector_breadth['date'].max()
    sector_summary = sector_breadth[sector_breadth['date'] == latest_date].sort_values('pct_above', ascending=False)
    
    log_cb(f"\n📊 SECTOR RANKINGS as of {latest_date.strftime('%Y-%m-%d')}:")
    log_cb("-" * 50)
    for _, row in sector_summary.iterrows():
        bar = "█" * int(row['pct_above'] / 5)
        log_cb(f"{row['sector'][:25]:<25} {row['pct_above']:>6.1f}% {bar}")
    
    # Calculate momentum (change over last 5 days)
    log_cb("\nCalculating sector momentum...")
    dates = sorted(sector_breadth['date'].unique())
    if len(dates) >= 5:
        recent_date = dates[-1]
        past_date = dates[-5]
        
        recent = sector_breadth[sector_breadth['date'] == recent_date][['sector', 'pct_above']]
        past = sector_breadth[sector_breadth['date'] == past_date][['sector', 'pct_above']]
        
        momentum = recent.merge(past, on='sector', suffixes=('_now', '_5d_ago'))
        momentum['momentum'] = momentum['pct_above_now'] - momentum['pct_above_5d_ago']
        momentum = momentum.sort_values('momentum', ascending=False)
        
        log_cb(f"\n📈 SECTOR MOMENTUM (5-day change):")
        log_cb("-" * 50)
        for _, row in momentum.iterrows():
            direction = "↑" if row['momentum'] > 0 else "↓" if row['momentum'] < 0 else "→"
            log_cb(f"{row['sector'][:25]:<25} {direction} {row['momentum']:>+6.1f}%")
    else:
        momentum = pd.DataFrame()
    
    return sector_breadth, sector_summary, momentum


def save_sector_breadth_to_db(engine, sector_breadth_df, log_cb=print):
    """Save sector breadth data to database."""
    if sector_breadth_df.empty:
        log_cb("No data to save")
        return
    
    # Create table if not exists
    create_table_sql = """
        CREATE TABLE IF NOT EXISTS sector_sma_breadth (
            id INT AUTO_INCREMENT PRIMARY KEY,
            date DATE NOT NULL,
            sector VARCHAR(100) NOT NULL,
            sma_period INT NOT NULL DEFAULT 50,
            pct_above DECIMAL(5,2),
            stocks_above INT,
            total_stocks INT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE KEY uk_date_sector_sma (date, sector, sma_period)
        )
    """
    
    with engine.begin() as conn:
        conn.execute(text(create_table_sql))
        
        # Upsert data
        for _, row in sector_breadth_df.iterrows():
            upsert_sql = """
                INSERT INTO sector_sma_breadth (date, sector, pct_above, stocks_above, total_stocks)
                VALUES (:date, :sector, :pct_above, :stocks_above, :total_stocks)
                ON DUPLICATE KEY UPDATE 
                    pct_above = VALUES(pct_above),
                    stocks_above = VALUES(stocks_above),
                    total_stocks = VALUES(total_stocks)
            """
            conn.execute(text(upsert_sql), {
                'date': row['date'],
                'sector': row['sector'],
                'pct_above': row['pct_above'],
                'stocks_above': int(row['stocks_above']),
                'total_stocks': int(row['total_stocks'])
            })
    
    log_cb(f"Saved {len(sector_breadth_df)} sector breadth records to database")


# ============================================================================
# STOCK PICKER FUNCTIONS
# ============================================================================

def find_recovery_leaders(engine, sma_period=50, lookback_days=10, log_cb=print):
    """
    Find stocks that have recently crossed above SMA.
    These are potential leaders in a recovering market.
    
    Prioritizes:
    1. Stocks in sectors with highest % above SMA (strong sectors)
    2. Recent crossovers (showing new strength)
    3. Higher % above SMA (stronger momentum)
    """
    log_cb("=" * 60)
    log_cb("FINDING RECOVERY LEADERS")
    log_cb("=" * 60)
    
    # Get sector rankings
    sector_summary = get_sector_summary(engine, sma_period=sma_period, log_cb=lambda x: None)
    
    if sector_summary.empty:
        log_cb("Could not get sector data")
        return pd.DataFrame()
    
    # Get top 5 sectors by % above SMA
    top_sectors = sector_summary.head(5)['sector'].tolist()
    log_cb(f"\n🏆 Top 5 Sectors by Breadth:")
    for s in top_sectors:
        pct = sector_summary[sector_summary['sector'] == s]['pct_above'].values[0]
        log_cb(f"  • {s}: {pct:.1f}%")
    
    # Find leading stocks in each top sector
    all_leaders = []
    for sector in top_sectors:
        log_cb(f"\n📊 Scanning {sector}...")
        leaders = find_leading_stocks_in_sector(engine, sector, sma_period, lookback_days, lambda x: None)
        
        if not leaders.empty:
            leaders['sector'] = sector
            sector_pct = sector_summary[sector_summary['sector'] == sector]['pct_above'].values[0]
            leaders['sector_breadth'] = sector_pct
            all_leaders.append(leaders)
            log_cb(f"   Found {len(leaders)} recent crossovers")
    
    if not all_leaders:
        log_cb("\nNo recent crossovers found in top sectors")
        return pd.DataFrame()
    
    result = pd.concat(all_leaders, ignore_index=True)
    
    # Sort by sector breadth, then days since cross, then pct above
    result = result.sort_values(
        ['sector_breadth', 'days_since_cross', 'pct_above_sma'],
        ascending=[False, True, False]
    )
    
    log_cb(f"\n🎯 TOP RECOVERY CANDIDATES:")
    log_cb("-" * 70)
    for i, row in result.head(20).iterrows():
        log_cb(f"{row['symbol']:<12} | {row['sector'][:20]:<20} | "
               f"Cross: {row['days_since_cross']:>2}d ago | "
               f"+{row['pct_above_sma']:.1f}% above SMA")
    
    return result


def find_weak_stocks_to_avoid(engine, sma_period=50, log_cb=print):
    """
    Find stocks in weak sectors that are below SMA.
    These should be avoided or could be short candidates.
    """
    log_cb("=" * 60)
    log_cb("FINDING WEAK STOCKS TO AVOID")
    log_cb("=" * 60)
    
    # Get sector rankings
    sector_summary = get_sector_summary(engine, sma_period=sma_period, log_cb=lambda x: None)
    
    if sector_summary.empty:
        return pd.DataFrame()
    
    # Get bottom 5 sectors
    weak_sectors = sector_summary.tail(5)['sector'].tolist()
    log_cb(f"\n⚠️ Weakest 5 Sectors:")
    for s in weak_sectors:
        pct = sector_summary[sector_summary['sector'] == s]['pct_above'].values[0]
        log_cb(f"  • {s}: {pct:.1f}%")
    
    # Find stocks below SMA in weak sectors
    all_weak = []
    for sector in weak_sectors:
        sector_stocks = pd.read_sql(f"""
            SELECT symbol FROM nse_index_constituents 
            WHERE index_name = 'NIFTY500' AND industry = '{sector}'
        """, engine)
        
        if sector_stocks.empty:
            continue
        
        # Add .NS suffix for yfinance table
        symbols = [f"{s}.NS" for s in sector_stocks['symbol'].tolist()]
        symbols_str = "', '".join(symbols)
        sma_col = f'sma_{sma_period}'
        
        # Get latest data
        query = f"""
            SELECT REPLACE(m.symbol, '.NS', '') as symbol, m.close, m.{sma_col},
                   ((m.close - m.{sma_col}) / m.{sma_col} * 100) as pct_from_sma
            FROM yfinance_daily_ma m
            INNER JOIN (
                SELECT symbol, MAX(date) as max_date
                FROM yfinance_daily_ma
                WHERE symbol IN ('{symbols_str}')
                GROUP BY symbol
            ) latest ON m.symbol = latest.symbol AND m.date = latest.max_date
            WHERE m.close < m.{sma_col}
            ORDER BY pct_from_sma ASC
        """
        weak_stocks = pd.read_sql(query, engine)
        
        if not weak_stocks.empty:
            weak_stocks['sector'] = sector
            sector_pct = sector_summary[sector_summary['sector'] == sector]['pct_above'].values[0]
            weak_stocks['sector_breadth'] = sector_pct
            all_weak.append(weak_stocks)
    
    if not all_weak:
        return pd.DataFrame()
    
    result = pd.concat(all_weak, ignore_index=True)
    result = result.sort_values('pct_from_sma', ascending=True)
    
    log_cb(f"\n❌ WEAKEST STOCKS TO AVOID:")
    log_cb("-" * 70)
    for i, row in result.head(20).iterrows():
        log_cb(f"{row['symbol']:<12} | {row['sector'][:20]:<20} | "
               f"{row['pct_from_sma']:.1f}% below SMA")
    
    return result


def get_sector_stocks_detail(engine, sector, sma_periods=[5, 10, 20, 50, 100, 150, 200], log_cb=print):
    """
    Get detailed stock information for a sector.
    
    Returns DataFrame with:
    - symbol, company_name
    - current price, each SMA value
    - % distance from each SMA
    - days above/below each SMA (consecutive)
    """
    # Get stocks in sector
    sector_stocks = pd.read_sql(f"""
        SELECT symbol, company_name FROM nse_index_constituents 
        WHERE index_name = 'NIFTY500' AND industry = '{sector}'
    """, engine)
    
    if sector_stocks.empty:
        return pd.DataFrame()
    
    # Add .NS suffix for yfinance table
    symbols = [f"{s}.NS" for s in sector_stocks['symbol'].tolist()]
    symbols_str = "', '".join(symbols)
    
    # Build SMA columns dynamically
    sma_cols = ', '.join([f'sma_{p}' for p in sma_periods])
    
    # Get latest data with all SMAs
    query = f"""
        SELECT REPLACE(m.symbol, '.NS', '') as symbol, m.date, m.close, {sma_cols}
        FROM yfinance_daily_ma m
        INNER JOIN (
            SELECT symbol, MAX(date) as max_date
            FROM yfinance_daily_ma
            WHERE symbol IN ('{symbols_str}')
            GROUP BY symbol
        ) latest ON m.symbol = latest.symbol AND m.date = latest.max_date
    """
    df = pd.read_sql(query, engine, parse_dates=['date'])
    
    if df.empty:
        return pd.DataFrame()
    
    # Merge with company names
    df = df.merge(sector_stocks, on='symbol', how='left')
    
    # Calculate % from each SMA
    for p in sma_periods:
        sma_col = f'sma_{p}'
        if sma_col in df.columns:
            df[f'pct_from_sma_{p}'] = ((df['close'] - df[sma_col]) / df[sma_col] * 100).round(2)
            df[f'above_sma_{p}'] = df['close'] > df[sma_col]
    
    # Now calculate days above each SMA (need historical data)
    for p in sma_periods:
        df[f'days_above_sma_{p}'] = 0
    
    # Get historical data to count consecutive days
    hist_query = f"""
        SELECT REPLACE(symbol, '.NS', '') as symbol, date, close, {sma_cols}
        FROM yfinance_daily_ma
        WHERE symbol IN ('{symbols_str}')
        AND date >= DATE_SUB(CURDATE(), INTERVAL 250 DAY)
        ORDER BY symbol, date
    """
    hist_df = pd.read_sql(hist_query, engine, parse_dates=['date'])
    
    if not hist_df.empty:
        for symbol in df['symbol'].unique():
            stock_hist = hist_df[hist_df['symbol'] == symbol].sort_values('date', ascending=False)
            if stock_hist.empty:
                continue
            
            for p in sma_periods:
                sma_col = f'sma_{p}'
                if sma_col not in stock_hist.columns:
                    continue
                
                # Count consecutive days above/below SMA from today
                days_count = 0
                is_above = None
                
                for _, row in stock_hist.iterrows():
                    if pd.isna(row[sma_col]):
                        break
                    
                    current_above = row['close'] > row[sma_col]
                    
                    if is_above is None:
                        is_above = current_above
                    
                    if current_above == is_above:
                        days_count += 1
                    else:
                        break
                
                # Negative if below SMA
                if is_above == False:
                    days_count = -days_count
                
                df.loc[df['symbol'] == symbol, f'days_above_sma_{p}'] = days_count
    
    # Sort by % from SMA 50 (or first available)
    sort_col = 'pct_from_sma_50' if 'pct_from_sma_50' in df.columns else f'pct_from_sma_{sma_periods[0]}'
    df = df.sort_values(sort_col, ascending=False)
    
    return df


if __name__ == "__main__":
    engine = get_engine()
    
    # Run full analysis
    sector_breadth, sector_summary, momentum = analyze_sector_rotation(
        engine, start_date='2024-01-01', sma_period=50
    )
    
    print("\n" + "=" * 60)
    
    # Find recovery leaders
    leaders = find_recovery_leaders(engine, sma_period=50)
    
    print("\n" + "=" * 60)
    
    # Find weak stocks
    weak = find_weak_stocks_to_avoid(engine, sma_period=50)
