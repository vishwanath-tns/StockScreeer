"""Fractal scanner: detect 3-candle fractals (up and down) and persist to DB.

    A 3-candle fractal (center at i) is defined as:
    - Bearish fractal (swing high): center high > previous high and center high > next high
    - Bullish fractal (swing low): center low < previous low and center low < next low

For each fractal we store:
 - symbol
 - fractal_date (center candle date)
 - fractal_type (e.g. 'Bearish Fractal' or 'Bullish Fractal')
 - fractal_high, fractal_low (range covering the three candles)
 - center_rsi (RSI value of the center candle using provided period)
 - center_close (close price of the center candle)
 - created_at

Provides:
 - scan_symbol_for_fractals(df_sym, period=9) -> list[dict]
 - upsert_fractals(engine, df)
 - scan_and_upsert_fractals(engine, period=9, workers=4, progress_cb=None, limit=0)

"""
from __future__ import annotations

from datetime import datetime, date
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
CREATE TABLE IF NOT EXISTS nse_fractals (
    symbol VARCHAR(20) NOT NULL,
    fractal_date DATE NOT NULL,
    fractal_type VARCHAR(32) NOT NULL,
    fractal_high DOUBLE NULL,
    fractal_low DOUBLE NULL,
    center_rsi DOUBLE NULL,
    center_close DOUBLE NULL,
    created_at DATETIME NOT NULL,
    PRIMARY KEY (symbol, fractal_date, fractal_type)
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


def ensure_fractals_table(engine):
    """Ensure `nse_fractals` exists and has the expected columns.

    This will create the table if missing (using TABLE_SQL) and perform lightweight
    migrations if columns are missing or too-short (adds `center_close` and
    increases `fractal_type` to VARCHAR(32) if necessary).
    Operations are best-effort and any errors are printed but do not raise.
    """
    try:
        with engine.begin() as conn:
            # create table if not exists
            conn.execute(text(TABLE_SQL))
            # inspect existing columns
            q = text(
                "SELECT column_name, data_type, character_maximum_length "
                "FROM information_schema.columns "
                "WHERE table_schema = DATABASE() AND table_name = 'nse_fractals'"
            )
            rows = conn.execute(q).fetchall()
            cols = {r[0]: r for r in rows}

            # add center_close if missing
            if 'center_close' not in cols:
                try:
                    conn.execute(text("ALTER TABLE nse_fractals ADD COLUMN center_close DOUBLE NULL"))
                    print('Added column center_close to nse_fractals')
                except Exception as e:
                    print(f'Failed to add center_close column: {e}')

            # ensure fractal_type is at least VARCHAR(32)
            if 'fractal_type' in cols:
                charlen = cols['fractal_type'][2]
                try:
                    if charlen is None or (isinstance(charlen, int) and charlen < 32):
                        conn.execute(text("ALTER TABLE nse_fractals MODIFY fractal_type VARCHAR(32) NOT NULL"))
                        print('Modified fractal_type to VARCHAR(32)')
                except Exception as e:
                    print(f'Failed to modify fractal_type length: {e}')
    except Exception as e:
        # non-fatal; caller will attempt to proceed
        print(f'ensure_fractals_table failed: {e}')


def scan_symbol_for_fractals(df_sym: pd.DataFrame, period: int = 9, rsi_by_date: Optional[dict] = None) -> List[dict]:
    """Detect 3-candle fractals for a single symbol DataFrame.

    df_sym must contain columns: trade_date (datetime), high, low, close, and have unique index trade_date or be sorted.
    Returns list of dict rows ready to be converted to DataFrame and upserted.
    """
    if df_sym is None or df_sym.empty:
        return []
    # ensure sorted by trade_date and indexable by position
    df = df_sym.sort_values('trade_date').reset_index(drop=True).copy()
    # prefer using precomputed RSI values if provided (mapping date->rsi)
    if 'close' not in df.columns:
        return []
    use_db_rsi = rsi_by_date is not None
    if not use_db_rsi:
        # compute RSI for close series as fallback
        rsi = compute_rsi(df['close'], period=period)

    rows = []
    # iterate over middle candles
    for i in range(1, len(df) - 1):
        prev_h = df.at[i-1, 'high'] if pd.notna(df.at[i-1, 'high']) else None
        cur_h = df.at[i, 'high'] if pd.notna(df.at[i, 'high']) else None
        next_h = df.at[i+1, 'high'] if pd.notna(df.at[i+1, 'high']) else None
        prev_l = df.at[i-1, 'low'] if pd.notna(df.at[i-1, 'low']) else None
        cur_l = df.at[i, 'low'] if pd.notna(df.at[i, 'low']) else None
        next_l = df.at[i+1, 'low'] if pd.notna(df.at[i+1, 'low']) else None

        symbol = df.at[i, 'symbol'] if 'symbol' in df.columns else None
        center_date = pd.to_datetime(df.at[i, 'trade_date']).date()
        center_close_val = df.at[i, 'close'] if 'close' in df.columns else None

        # up fractal
        if prev_h is not None and cur_h is not None and next_h is not None and cur_h > prev_h and cur_h > next_h:
            fractal_high = max(prev_h, cur_h, next_h)
            fractal_low = min(df.at[i-1, 'low'], df.at[i, 'low'], df.at[i+1, 'low'])
            if use_db_rsi:
                # rsi_by_date keys are date objects or ISO strings; normalize
                key = pd.to_datetime(df.at[i, 'trade_date']).date()
                center_rsi = rsi_by_date.get(key)
            else:
                center_rsi = float(rsi.iloc[i]) if pd.notna(rsi.iloc[i]) else None
            rows.append({
                'symbol': symbol,
                'fractal_date': center_date,
                'fractal_type': 'Bearish Fractal',
                'fractal_high': float(fractal_high) if fractal_high is not None else None,
                'fractal_low': float(fractal_low) if fractal_low is not None else None,
                'center_rsi': center_rsi,
                'center_close': float(center_close_val) if center_close_val is not None else None,
                'created_at': datetime.utcnow()
            })

        # down fractal
        if prev_l is not None and cur_l is not None and next_l is not None and cur_l < prev_l and cur_l < next_l:
            fractal_high = max(df.at[i-1, 'high'], df.at[i, 'high'], df.at[i+1, 'high'])
            fractal_low = min(prev_l, cur_l, next_l)
            if use_db_rsi:
                key = pd.to_datetime(df.at[i, 'trade_date']).date()
                center_rsi = rsi_by_date.get(key)
            else:
                center_rsi = float(rsi.iloc[i]) if pd.notna(rsi.iloc[i]) else None
            rows.append({
                'symbol': symbol,
                'fractal_date': center_date,
                'fractal_type': 'Bullish Fractal',
                'fractal_high': float(fractal_high) if fractal_high is not None else None,
                'fractal_low': float(fractal_low) if fractal_low is not None else None,
                'center_rsi': center_rsi,
                'center_close': float(center_close_val) if center_close_val is not None else None,
                'created_at': datetime.utcnow()
            })

    return rows


def upsert_fractals(engine, df: pd.DataFrame):
    """Upsert fractal rows into nse_fractals table using temporary table pattern."""
    if df is None or df.empty:
        print('No fractals to upsert')
        return
    # Ensure base table and schema compatibility/migrations
    try:
        ensure_fractals_table(engine)
    except Exception:
        # ensure_fractals_table is best-effort; continue and let DB raise if fatal
        pass
    with engine.begin() as conn:
        tmp = 'tmp_nse_fractals'
        conn.execute(text(f"DROP TEMPORARY TABLE IF EXISTS {tmp}"))
        conn.execute(text(f"CREATE TEMPORARY TABLE {tmp} LIKE nse_fractals"))
        # dedupe on primary key
        if all(c in df.columns for c in ('symbol', 'fractal_date', 'fractal_type')):
            df = df.sort_values(['symbol', 'fractal_date', 'fractal_type']).drop_duplicates(subset=['symbol', 'fractal_date', 'fractal_type'], keep='last')
        df.to_sql(name=tmp, con=conn, if_exists='append', index=False, method='multi', chunksize=2000)
        cols = list(df.columns)
        col_list = ", ".join([f"`{c}`" for c in cols])
        select_list = col_list
        update_cols = [c for c in cols if c not in ('symbol', 'fractal_date', 'fractal_type')]
        update_list = ", ".join([f"`{c}`=VALUES(`{c}`)" for c in update_cols]) or 'created_at=created_at'
        insert_sql = f"INSERT INTO nse_fractals ({col_list}) SELECT {select_list} FROM {tmp} ON DUPLICATE KEY UPDATE {update_list};"
        conn.execute(text(insert_sql))
        print(f"Upserted {len(df)} fractal rows into nse_fractals")


def scan_and_upsert_fractals_optimized(engine, period: int = 9, workers: int = 4, progress_cb=None, limit: int = 0, days_back: int = 30):
    """Optimized fractal scan that only processes recent data to avoid performance issues.
    
    Args:
        engine: Database engine
        period: RSI period (default 9)
        workers: Number of parallel workers (default 4)  
        progress_cb: Progress callback function
        limit: Limit number of symbols (0 = no limit)
        days_back: Number of recent days to process (default 30)
    """
    # ensure table exists and migrations applied before running
    try:
        ensure_fractals_table(engine)
    except Exception:
        pass

    # Get cutoff date for recent data processing
    from datetime import datetime, timedelta
    cutoff_date = (datetime.now() - timedelta(days=days_back)).strftime('%Y-%m-%d')
    
    # Only fetch recent BHAV data to reduce memory usage
    with engine.connect() as conn:
        recent_query = text("""
            SELECT trade_date, symbol, close_price, high_price, low_price 
            FROM nse_equity_bhavcopy_full 
            WHERE series = 'EQ' AND trade_date >= :cutoff_date
            ORDER BY symbol, trade_date
        """)
        rows = conn.execute(recent_query, {"cutoff_date": cutoff_date}).fetchall()
    
    if not rows:
        if progress_cb:
            progress_cb(0, 0, f'No recent BHAV data found (last {days_back} days)')
        return

    df = pd.DataFrame(rows, columns=[c for c in rows[0]._fields])
    df = df.rename(columns={'close_price': 'close', 'high_price': 'high', 'low_price': 'low'})
    df['trade_date'] = pd.to_datetime(df['trade_date'])
    df['close'] = pd.to_numeric(df['close'], errors='coerce')
    df['high'] = pd.to_numeric(df['high'], errors='coerce')
    df['low'] = pd.to_numeric(df['low'], errors='coerce')
    df = df[df['symbol'].notna() & df['trade_date'].notna()]

    syms = sorted(df['symbol'].unique())
    if limit and limit > 0:
        syms = syms[:limit]
    total = len(syms)
    
    if progress_cb:
        progress_cb(0, total, f'Processing {total} symbols for recent fractals (last {days_back} days)')

    # Get historical context and RSI data efficiently with single connection
    extended_data = {}
    rsi_map = {}
    
    with engine.connect() as conn:
        # Batch fetch historical context for all symbols
        if progress_cb:
            progress_cb(0, total, f'Loading historical context for {total} symbols...')
            
        for i, sym in enumerate(syms):
            # Get last 100 days of data for proper fractal analysis context
            context_query = text("""
                SELECT trade_date, close_price, high_price, low_price 
                FROM nse_equity_bhavcopy_full 
                WHERE symbol = :symbol AND series = 'EQ'
                ORDER BY trade_date DESC 
                LIMIT 100
            """)
            ctx_rows = conn.execute(context_query, {"symbol": sym}).fetchall()
            if ctx_rows:
                ctx_df = pd.DataFrame(ctx_rows, columns=['trade_date', 'close', 'high', 'low'])
                ctx_df['trade_date'] = pd.to_datetime(ctx_df['trade_date'])
                ctx_df['close'] = pd.to_numeric(ctx_df['close'], errors='coerce')
                ctx_df['high'] = pd.to_numeric(ctx_df['high'], errors='coerce')
                ctx_df['low'] = pd.to_numeric(ctx_df['low'], errors='coerce')
                ctx_df = ctx_df.sort_values('trade_date')
                extended_data[sym] = ctx_df
            
            # Progress update every 50 symbols  
            if progress_cb and (i + 1) % 50 == 0:
                progress_cb(0, total, f'Loaded context for {i + 1}/{total} symbols...')
        
        # Batch fetch RSI data for recent period
        try:
            rsi_query = text("""
                SELECT symbol, trade_date, rsi 
                FROM nse_rsi_daily 
                WHERE period = :period AND trade_date >= :cutoff_date
            """)
            rsi_rows = conn.execute(rsi_query, {"period": period, "cutoff_date": cutoff_date}).fetchall()
            for r in rsi_rows:
                s = r[0]
                d = pd.to_datetime(r[1]).date()
                val = float(r[2]) if r[2] is not None else None
                rsi_map.setdefault(s, {})[d] = val
        except Exception:
            rsi_map = {}

    def _process_symbol_optimized(sym):
        """Process single symbol with extended context data for accurate fractal detection."""
        if sym not in extended_data:
            return []
        
        symbol_df = extended_data[sym].copy()
        symbol_df['symbol'] = sym
        return scan_symbol_for_fractals(symbol_df, period=period, rsi_by_date=rsi_map.get(sym))

    all_rows = []
    # Use ThreadPoolExecutor with connection management
    import concurrent.futures
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, min(workers, 8))) as ex:
        futures = {ex.submit(_process_symbol_optimized, s): s for s in syms}
        for i, fut in enumerate(concurrent.futures.as_completed(futures), start=1):
            sym = futures[fut]
            try:
                res = fut.result()
                if res:
                    # Filter to only include fractals from recent period
                    recent_fractals = []
                    for fractal in res:
                        fractal_date = pd.to_datetime(fractal.get('fractal_date'))
                        if fractal_date.date() >= pd.to_datetime(cutoff_date).date():
                            recent_fractals.append(fractal)
                    all_rows.extend(recent_fractals)
                    
                if progress_cb:
                    progress_cb(i, total, f'Processed {sym} ({i}/{total}) - Found {len(res) if res else 0} fractals')
            except Exception as e:
                if progress_cb:
                    progress_cb(i, total, f'Error processing {sym}: {e}')

    if not all_rows:
        if progress_cb:
            progress_cb(total, total, f'No new fractals found in last {days_back} days')
        return

    df_rows = pd.DataFrame(all_rows)
    
    # Remove duplicates before upserting
    if 'fractal_date' in df_rows.columns and 'symbol' in df_rows.columns:
        df_rows = df_rows.drop_duplicates(subset=['symbol', 'fractal_date', 'fractal_type'])
    
    upsert_fractals(engine, df_rows)
    if progress_cb:
        progress_cb(total, total, f'Upserted {len(df_rows)} new fractals (last {days_back} days)')


def scan_and_upsert_fractals(engine, period: int = 9, workers: int = 4, progress_cb=None, limit: int = 0):
    """Scan BHAV for all symbols and upsert fractals found.

    This function fetches full BHAV history and processes each symbol in parallel.
    progress_cb(current, total, message) is called if provided.
    """
    # ensure table exists and migrations applied before running
    try:
        ensure_fractals_table(engine)
    except Exception:
        pass

    # fetch full bhav
    with engine.connect() as conn:
        rows = conn.execute(text("SELECT trade_date, symbol, close_price, high_price, low_price FROM nse_equity_bhavcopy_full WHERE series = 'EQ' ORDER BY symbol, trade_date")).fetchall()
    if not rows:
        if progress_cb:
            progress_cb(0, 0, 'No BHAV rows found')
        return

    df = pd.DataFrame(rows, columns=[c for c in rows[0]._fields])
    df = df.rename(columns={'close_price': 'close', 'high_price': 'high', 'low_price': 'low', 'trade_date': 'trade_date'})
    df['trade_date'] = pd.to_datetime(df['trade_date'])
    df['close'] = pd.to_numeric(df['close'], errors='coerce')
    df['high'] = pd.to_numeric(df['high'], errors='coerce')
    df['low'] = pd.to_numeric(df['low'], errors='coerce')
    df = df[df['symbol'].notna() & df['trade_date'].notna()]

    syms = sorted(df['symbol'].unique())
    if limit and limit > 0:
        syms = syms[:limit]
    total = len(syms)
    if progress_cb:
        progress_cb(0, total, f'Scanning {total} symbols for fractals')

    import concurrent.futures

    # fetch precomputed daily RSI for all symbols (for the given period) to avoid recomputing
    rsi_map = {}
    try:
        with _ensure_engine().connect() as conn:
            # select symbol, trade_date, rsi from nse_rsi_daily where period = :p and symbol in (...)
            syms_tuple = tuple(syms)
            q = text("SELECT symbol, trade_date, rsi FROM nse_rsi_daily WHERE period = :p AND symbol IN :syms")
            rows = conn.execute(q, {"p": period, "syms": syms_tuple}).fetchall()
            for r in rows:
                s = r[0]
                d = pd.to_datetime(r[1]).date()
                val = float(r[2]) if r[2] is not None else None
                rsi_map.setdefault(s, {})[d] = val
    except Exception:
        # if any error occurs, proceed without DB RSI (fallback to compute)
        rsi_map = {}

    def _process(sym):
        g = df[df['symbol'] == sym].sort_values('trade_date')
        if g.empty:
            return []
        g['symbol'] = sym
        return scan_symbol_for_fractals(g, period=period, rsi_by_date=rsi_map.get(sym))

    all_rows = []
    # Use ThreadPoolExecutor to avoid multiprocessing pickling issues when running inside GUIs
    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, workers)) as ex:
        futures = {ex.submit(_process, s): s for s in syms}
        for i, fut in enumerate(concurrent.futures.as_completed(futures), start=1):
            sym = futures[fut]
            try:
                res = fut.result()
                if res:
                    all_rows.extend(res)
                if progress_cb:
                    progress_cb(i, total, f'Processed {sym} ({i}/{total})')
            except Exception as e:
                # continue processing other symbols; report error via progress_cb
                if progress_cb:
                    progress_cb(i, total, f'Error processing {sym}: {e}')

    if not all_rows:
        if progress_cb:
            progress_cb(total, total, 'No fractals found')
        return

    df_rows = pd.DataFrame(all_rows)
    upsert_fractals(engine, df_rows)
    if progress_cb:
        progress_cb(total, total, f'Upserted {len(df_rows)} fractals')