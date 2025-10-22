"""Scan for RSI crossovers (period 9) and store events in DB.

Detects two types of events:
 - 80_up: previous RSI < 80 and current RSI >= 80
 - 20_down: previous RSI > 20 and current RSI <= 20

Provides upsert and query helpers.
"""
from __future__ import annotations

from datetime import datetime, date, timedelta
from typing import List, Optional

import pandas as pd
from sqlalchemy import text

try:
    from rsi_calculator import compute_rsi
except Exception:
    from rsi_calculator import compute_rsi

try:
    from import_nifty_index import build_engine
except Exception:
    build_engine = None


TABLE_SQL = '''
CREATE TABLE IF NOT EXISTS nse_rsi_crosses (
    symbol VARCHAR(20) NOT NULL,
    trade_date DATE NOT NULL,
    period INT NOT NULL,
    cross_type VARCHAR(16) NOT NULL,
    prev_rsi DOUBLE NULL,
    curr_rsi DOUBLE NULL,
    high DOUBLE NULL,
    created_at DATETIME NOT NULL,
    PRIMARY KEY (symbol, trade_date, period, cross_type)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
'''


def _ensure_engine():
    if build_engine:
        return build_engine()
    try:
        from import_nifty_index import build_engine as b2
        return b2()
    except Exception:
        raise RuntimeError('No engine builder available')


def fetch_bhav_range(conn, start: str, end: str, symbols: Optional[List[str]] = None) -> pd.DataFrame:
    """Fetch trade_date, symbol, close_price, high_price for range.
    Returns DataFrame with trade_date (datetime), symbol, close, high.
    """
    if symbols:
        q = text("SELECT trade_date, symbol, close_price, high_price FROM nse_equity_bhavcopy_full WHERE symbol IN :syms AND series = 'EQ' AND trade_date BETWEEN :a AND :b ORDER BY symbol, trade_date")
        rows = conn.execute(q, {"syms": tuple(symbols), "a": start, "b": end}).fetchall()
    else:
        q = text("SELECT trade_date, symbol, close_price, high_price FROM nse_equity_bhavcopy_full WHERE series = 'EQ' AND trade_date BETWEEN :a AND :b ORDER BY symbol, trade_date")
        rows = conn.execute(q, {"a": start, "b": end}).fetchall()

    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows, columns=["trade_date", "symbol", "close", "high"]) 
    df['trade_date'] = pd.to_datetime(df['trade_date'])
    df['close'] = pd.to_numeric(df['close'], errors='coerce')
    df['high'] = pd.to_numeric(df['high'], errors='coerce')
    df = df[df['trade_date'].notna() & df['symbol'].notna()]
    df = df.sort_values(['symbol', 'trade_date']).drop_duplicates(subset=['symbol', 'trade_date'], keep='last')
    return df


def find_crosses_for_symbol(df_sym: pd.DataFrame, period: int = 9) -> List[dict]:
    """Given df_sym with index trade_date and columns close, high, compute RSI and find cross events."""
    if df_sym.empty:
        return []
    closes = df_sym['close']
    rsi = compute_rsi(closes, period=period)
    # align rsi with closes
    res = []
    prev = rsi.shift(1)
    # 80_up: prev < 80 and rsi >= 80
    mask80 = (prev < 80) & (rsi >= 80)
    # 20_down: prev > 20 and rsi <= 20
    mask20 = (prev > 20) & (rsi <= 20)

    for dt in mask80[mask80].index:
        row = {
            'symbol': df_sym['symbol'].iloc[0],
            'trade_date': pd.to_datetime(dt).date(),
            'period': period,
            'cross_type': '80_up',
            'prev_rsi': float(prev.loc[dt]) if pd.notna(prev.loc[dt]) else None,
            'curr_rsi': float(rsi.loc[dt]) if pd.notna(rsi.loc[dt]) else None,
            'high': float(df_sym.loc[dt, 'high']) if dt in df_sym.index and pd.notna(df_sym.loc[dt, 'high']) else None,
            'created_at': datetime.utcnow()
        }
        res.append(row)

    for dt in mask20[mask20].index:
        row = {
            'symbol': df_sym['symbol'].iloc[0],
            'trade_date': pd.to_datetime(dt).date(),
            'period': period,
            'cross_type': '20_down',
            'prev_rsi': float(prev.loc[dt]) if pd.notna(prev.loc[dt]) else None,
            'curr_rsi': float(rsi.loc[dt]) if pd.notna(rsi.loc[dt]) else None,
            'high': float(df_sym.loc[dt, 'high']) if dt in df_sym.index and pd.notna(df_sym.loc[dt, 'high']) else None,
            'created_at': datetime.utcnow()
        }
        res.append(row)

    return res


def upsert_crosses(engine, df: pd.DataFrame):
    if df.empty:
        print('No cross rows to upsert')
        return
    with engine.begin() as conn:
        conn.execute(text(TABLE_SQL))
        tmp = 'tmp_nse_rsi_crosses'
        conn.execute(text(f"DROP TEMPORARY TABLE IF EXISTS {tmp}"))
        conn.execute(text(f"CREATE TEMPORARY TABLE {tmp} LIKE nse_rsi_crosses"))
        # dedupe
        if all(c in df.columns for c in ('symbol', 'trade_date', 'period', 'cross_type')):
            df = df.sort_values(['symbol', 'trade_date', 'period', 'cross_type']).drop_duplicates(subset=['symbol', 'trade_date', 'period', 'cross_type'], keep='last')
        df.to_sql(name=tmp, con=conn, if_exists='append', index=False, method='multi', chunksize=1000)
        cols = list(df.columns)
        col_list = ", ".join([f"`{c}`" for c in cols])
        select_list = col_list
        update_cols = [c for c in cols if c not in ('symbol', 'trade_date', 'period', 'cross_type')]
        update_list = ", ".join([f"`{c}`=VALUES(`{c}`)" for c in update_cols]) or 'created_at=created_at'
        insert_sql = f"INSERT INTO nse_rsi_crosses ({col_list}) SELECT {select_list} FROM {tmp} ON DUPLICATE KEY UPDATE {update_list};"
        conn.execute(text(insert_sql))
        print(f"Upserted {len(df)} rows into nse_rsi_crosses")


def scan_and_upsert(engine, period: int = 9, as_of: Optional[str] = None, lookback_days: int = 30, progress_cb=None, limit: int = 0):
    """Scan BHAV for the lookback window ending at as_of and upsert any RSI crossings found.

    as_of: 'YYYY-MM-DD' or None -> today
    lookback_days: number of days to fetch backward
    progress_cb(current, total, message) optional
    """
    if as_of:
        end = pd.to_datetime(as_of).date()
    else:
        end = date.today()
    start = end - timedelta(days=lookback_days)
    start_s = start.strftime('%Y-%m-%d')
    end_s = end.strftime('%Y-%m-%d')

    with engine.connect() as conn:
        df = fetch_bhav_range(conn, start_s, end_s)

    if df.empty:
        if progress_cb:
            progress_cb(0, 0, 'No BHAV rows found')
        return

    syms = sorted(df['symbol'].unique())
    if limit and limit > 0:
        syms = syms[:limit]
    total = len(syms)
    if progress_cb:
        progress_cb(0, total, f'Scanning {total} symbols for RSI crosses')

    all_rows = []
    for i, sym in enumerate(syms, start=1):
        g = df[df['symbol'] == sym].set_index('trade_date').sort_index()
        if g.empty:
            if progress_cb:
                progress_cb(i, total, f'No rows for {sym}')
            continue
        g['symbol'] = sym
        rows = find_crosses_for_symbol(g, period=period)
        if rows:
            all_rows.extend(rows)
        if progress_cb:
            progress_cb(i, total, f'Processed {sym} ({i}/{total})')

    if not all_rows:
        if progress_cb:
            progress_cb(total, total, 'No cross events found')
        return

    df_rows = pd.DataFrame(all_rows)
    # upsert
    upsert_crosses(engine, df_rows)
    if progress_cb:
        progress_cb(total, total, f'Upserted {len(df_rows)} cross events')


def last_cross_date_per_symbol(engine, period: int = 9, cross_type: Optional[str] = None) -> dict:
    """Return a dict symbol -> last_cross_date (date) for the given period and optional cross_type."""
    with engine.connect() as conn:
        if cross_type:
            q = text("SELECT symbol, MAX(trade_date) as d FROM nse_rsi_crosses WHERE period = :p AND cross_type = :ct GROUP BY symbol")
            rows = conn.execute(q, {"p": period, "ct": cross_type}).fetchall()
        else:
            q = text("SELECT symbol, MAX(trade_date) as d FROM nse_rsi_crosses WHERE period = :p GROUP BY symbol")
            rows = conn.execute(q, {"p": period}).fetchall()
    out = {}
    for r in rows:
        out[r[0]] = pd.to_datetime(r[1]).date() if r[1] is not None else None
    return out


def scan_incremental_and_upsert(engine, period: int = 9, as_of: Optional[str] = None, lookback_days: int = 30, progress_cb=None, limit: int = 0, cross_type: Optional[str] = None):
    """Scan only days after the last recorded cross per symbol and upsert new events.

    If a symbol has no previous cross, a lookback window is used.
    """
    # determine window
    if as_of:
        end = pd.to_datetime(as_of).date()
    else:
        end = date.today()
    start_default = end - timedelta(days=lookback_days)

    # fetch last cross dates per symbol
    last_dates = last_cross_date_per_symbol(engine, period=period, cross_type=cross_type)

    # fetch all BHAV rows for the full historical window covering any symbols that need lookback
    # We'll fetch from start_default to end and then slice per symbol
    with engine.connect() as conn:
        df = fetch_bhav_range(conn, start_default.strftime('%Y-%m-%d'), end.strftime('%Y-%m-%d'))

    if df.empty:
        if progress_cb:
            progress_cb(0, 0, 'No BHAV rows found')
        return

    syms = sorted(df['symbol'].unique())
    if limit and limit > 0:
        syms = syms[:limit]
    total = len(syms)
    if progress_cb:
        progress_cb(0, total, f'Incremental scan for {total} symbols')

    all_rows = []
    for i, sym in enumerate(syms, start=1):
        last = last_dates.get(sym)
        g = df[df['symbol'] == sym].set_index('trade_date').sort_index()
        if last is not None:
            # select rows strictly after last
            g2 = g[g.index.date > last]
        else:
            g2 = g
        if g2.empty:
            if progress_cb:
                progress_cb(i, total, f'No new rows for {sym}')
            continue
        g2['symbol'] = sym
        rows = find_crosses_for_symbol(g2, period=period)
        if rows:
            all_rows.extend(rows)
        if progress_cb:
            progress_cb(i, total, f'Processed {sym} ({i}/{total})')

    if not all_rows:
        if progress_cb:
            progress_cb(total, total, 'No new cross events found')
        return

    df_rows = pd.DataFrame(all_rows)
    upsert_crosses(engine, df_rows)
    if progress_cb:
        progress_cb(total, total, f'Upserted {len(df_rows)} new cross events')


def latest_cross_date(engine, cross_type: Optional[str] = None) -> Optional[date]:
    with engine.connect() as conn:
        if cross_type:
            q = text("SELECT MAX(trade_date) FROM nse_rsi_crosses WHERE cross_type = :ct")
            r = conn.execute(q, {"ct": cross_type}).scalar()
        else:
            q = text("SELECT MAX(trade_date) FROM nse_rsi_crosses")
            r = conn.execute(q).scalar()
        if r is None:
            return None
        return pd.to_datetime(r).date()


def get_crosses_on_date(engine, dt: str, cross_type: Optional[str] = None) -> pd.DataFrame:
    with engine.connect() as conn:
        if cross_type:
            q = text("SELECT * FROM nse_rsi_crosses WHERE trade_date = :d AND cross_type = :ct")
            rows = conn.execute(q, {"d": dt, "ct": cross_type}).fetchall()
        else:
            q = text("SELECT * FROM nse_rsi_crosses WHERE trade_date = :d")
            rows = conn.execute(q, {"d": dt}).fetchall()
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows, columns=[c for c in rows[0]._fields])
    return df


def stocks_trading_above_cross(engine, as_of: Optional[str] = None, cross_type: str = '80_up') -> pd.DataFrame:
    """Return symbols whose latest crossover (of cross_type) has high < today's close (as_of)."""
    if as_of is None:
        as_of = date.today().strftime('%Y-%m-%d')
        q = text("""
        SELECT c.symbol, c.trade_date as cross_date, c.high as cross_high, b.close_price as asof_close
        FROM nse_rsi_crosses c
        JOIN (
            SELECT symbol, close_price FROM nse_equity_bhavcopy_full WHERE series = 'EQ' AND trade_date = :asof
        ) b ON b.symbol = c.symbol
    WHERE c.cross_type = :ct
      AND c.trade_date = (
         SELECT MAX(trade_date) FROM nse_rsi_crosses cx WHERE cx.symbol = c.symbol AND cx.cross_type = c.cross_type
      )
    """)
    with engine.connect() as conn:
        rows = conn.execute(q, {"asof": as_of, "ct": cross_type}).fetchall()
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows, columns=[c for c in rows[0]._fields])
    # filter where asof_close > cross_high
    df = df[pd.to_numeric(df['asof_close'], errors='coerce') > pd.to_numeric(df['cross_high'], errors='coerce')]
    return df


def stocks_trading_above_cross_window(engine, as_of: Optional[str] = None, days: int = 365, period: int = 9, cross_type: str = '80_up') -> pd.DataFrame:
    """Return symbols whose as_of close is greater than the maximum 'high' recorded for the given cross_type in the last `days` days.

    The function returns DataFrame with columns: symbol, last_cross_date, max_cross_high, asof_close.
    Uses SQL to compute per-symbol max cross high in the window and joins with as-of close.
    """
    if as_of is None:
        as_of = date.today().strftime('%Y-%m-%d')

        # window start/end
        end_dt = pd.to_datetime(as_of).date()
        start_dt = end_dt - timedelta(days=days)

        # Return rows for each cross event in the window where the as-of close is greater
        # than the cross event's high. This allows matching any cross candle, not just the max.
        q = text("""
        SELECT c.symbol, c.trade_date as cross_date, c.high as cross_high, b.close_price as asof_close
        FROM nse_rsi_crosses c
        JOIN (
            SELECT symbol, close_price FROM nse_equity_bhavcopy_full WHERE series = 'EQ' AND trade_date = :asof
        ) b ON b.symbol COLLATE utf8mb4_unicode_ci = c.symbol COLLATE utf8mb4_unicode_ci
        WHERE c.cross_type = :ct
            AND c.period = :p
            AND c.trade_date BETWEEN :a AND :b
            AND CAST(b.close_price AS DECIMAL(18,6)) > CAST(c.high AS DECIMAL(18,6))
        ORDER BY (CAST(b.close_price AS DECIMAL(18,6)) - CAST(c.high AS DECIMAL(18,6))) DESC
        """)

    params = {
        "ct": cross_type,
        "p": period,
        "a": start_dt.strftime('%Y-%m-%d'),
        "b": end_dt.strftime('%Y-%m-%d'),
        "asof": as_of,
    }

    with engine.connect() as conn:
        rows = conn.execute(q, params).fetchall()

    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows, columns=[c for c in rows[0]._fields])
    # coerce numeric and add diff
    if 'cross_high' in df.columns:
        df['cross_high'] = pd.to_numeric(df['cross_high'], errors='coerce')
    if 'asof_close' in df.columns:
        df['asof_close'] = pd.to_numeric(df['asof_close'], errors='coerce')
    df['diff'] = df['asof_close'] - df['cross_high']
    return df


def count_crosses_in_window(engine, as_of: Optional[str] = None, days: int = 365, period: int = 9, cross_type: Optional[str] = None) -> pd.DataFrame:
    """Return number of cross events per symbol in the lookback window.

    Returns a DataFrame with columns: symbol, cross_count, last_cross_date (datetime.date)
    Ordered by cross_count desc, then last_cross_date desc.
    If cross_type is None, counts all cross types; otherwise filters by the provided type.
    """
    if as_of is None:
        as_of = date.today().strftime('%Y-%m-%d')

    end_dt = pd.to_datetime(as_of).date()
    start_dt = end_dt - timedelta(days=days)

    if cross_type:
        q = text("""
        SELECT symbol, COUNT(*) as cross_count, MAX(trade_date) as last_cross_date
        FROM nse_rsi_crosses
        WHERE period = :p AND cross_type = :ct AND trade_date BETWEEN :a AND :b
        GROUP BY symbol
        ORDER BY cross_count DESC, last_cross_date DESC
        """)
        params = {"p": period, "ct": cross_type, "a": start_dt.strftime('%Y-%m-%d'), "b": end_dt.strftime('%Y-%m-%d')}
    else:
        q = text("""
        SELECT symbol, COUNT(*) as cross_count, MAX(trade_date) as last_cross_date
        FROM nse_rsi_crosses
        WHERE period = :p AND trade_date BETWEEN :a AND :b
        GROUP BY symbol
        ORDER BY cross_count DESC, last_cross_date DESC
        """)
        params = {"p": period, "a": start_dt.strftime('%Y-%m-%d'), "b": end_dt.strftime('%Y-%m-%d')}

    with engine.connect() as conn:
        rows = conn.execute(q, params).fetchall()

    if not rows:
        return pd.DataFrame(columns=['symbol', 'cross_count', 'last_cross_date'])

    df = pd.DataFrame(rows, columns=[c for c in rows[0]._fields])
    # normalize types
    df['cross_count'] = pd.to_numeric(df['cross_count'], errors='coerce').fillna(0).astype(int)
    df['last_cross_date'] = pd.to_datetime(df['last_cross_date']).dt.date
    return df


if __name__ == '__main__':
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument('--period', type=int, default=9)
    p.add_argument('--lookback', type=int, default=30)
    p.add_argument('--as-of', dest='as_of')
    p.add_argument('--limit', type=int, default=0)
    args = p.parse_args()

    eng = _ensure_engine()

    def _print(c, t, m):
        print(f"{c}/{t}: {m}")

    scan_and_upsert(eng, period=args.period, as_of=args.as_of, lookback_days=args.lookback, progress_cb=_print, limit=args.limit)
