"""RSI divergence scanners.

Currently implements hidden bullish divergence scanner:

- For each symbol, fetch bullish fractals (fractal_type='Bullish Fractal') ordered by date desc.
- Compare the latest bullish fractal with up to N past bullish fractals. If:
    latest.center_close > past.center_close AND latest.center_rsi < past.center_rsi
  then that's a hidden bullish divergence (price higher but RSI lower).

The scanner writes signals into `nse_rsi_divergences` with details of the current and past fractal.
"""
from datetime import datetime
from typing import List
import pandas as pd
from sqlalchemy import text

try:
    from import_nifty_index import build_engine
except Exception:
    build_engine = None

TABLE_SQL = '''
CREATE TABLE IF NOT EXISTS nse_rsi_divergences (
    id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL,
    signal_type VARCHAR(32) NOT NULL,
    signal_date DATE NOT NULL,
    curr_fractal_date DATE NULL,
    curr_center_close DOUBLE NULL,
    curr_fractal_high DOUBLE NULL,
    curr_fractal_low DOUBLE NULL,
    curr_center_rsi DOUBLE NULL,
    comp_fractal_date DATE NULL,
    comp_center_close DOUBLE NULL,
    comp_fractal_high DOUBLE NULL,
    comp_fractal_low DOUBLE NULL,
    comp_center_rsi DOUBLE NULL,
    buy_above_price DOUBLE NULL,
    sell_below_price DOUBLE NULL,
    created_at DATETIME NOT NULL,
    UNIQUE KEY uniq_sig (symbol, signal_date, signal_type, comp_fractal_date)
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


def ensure_divergences_table(engine):
    """Ensure `nse_rsi_divergences` exists and has expected columns.

    This will create the table if missing (using TABLE_SQL) and perform lightweight
    migrations to add commonly-missing columns like `comp_fractal_date` and
    `buy_above_price`. Errors are printed but do not raise.
    """
    try:
        with engine.begin() as conn:
            # create table if not exists
            conn.execute(text(TABLE_SQL))
            # inspect existing columns
            q = text(
                "SELECT column_name, data_type, character_maximum_length "
                "FROM information_schema.columns "
                "WHERE table_schema = DATABASE() AND table_name = 'nse_rsi_divergences'"
            )
            rows = conn.execute(q).fetchall()
            cols = {r[0]: r for r in rows}

            # expected additional columns and their SQL types
            expected = {
                'comp_fractal_date': 'DATE NULL',
                'buy_above_price': 'DOUBLE NULL',
                'curr_center_close': 'DOUBLE NULL',
                'comp_center_close': 'DOUBLE NULL',
                'sell_below_price': 'DOUBLE NULL',
            }

            for col, coldef in expected.items():
                if col not in cols:
                    try:
                        conn.execute(text(f"ALTER TABLE nse_rsi_divergences ADD COLUMN {col} {coldef}"))
                        print(f'Added column {col} to nse_rsi_divergences')
                    except Exception as e:
                        print(f'Failed to add column {col}: {e}')

            # ensure signal_type is at least VARCHAR(32)
            if 'signal_type' in cols:
                charlen = cols['signal_type'][2]
                try:
                    if charlen is None or (isinstance(charlen, int) and charlen < 32):
                        conn.execute(text("ALTER TABLE nse_rsi_divergences MODIFY signal_type VARCHAR(32) NOT NULL"))
                        print('Modified signal_type to VARCHAR(32)')
                except Exception as e:
                    print(f'Failed to modify signal_type length: {e}')
    except Exception as e:
        print(f'ensure_divergences_table failed: {e}')


def scan_hidden_bullish_divergences(engine, lookback_fractals: int = 5, progress_cb=None, limit: int = 0, sma_filters: List[int] = None) -> pd.DataFrame:
    """Scan `nse_fractals` for hidden bullish divergences.

    Returns a DataFrame of signal rows (but also upserts into DB).
    """
    # fetch bullish fractals
    with engine.connect() as conn:
        q = text("SELECT symbol, fractal_date, center_close, center_rsi, fractal_high, fractal_low FROM nse_fractals WHERE fractal_type = 'Bullish Fractal' ORDER BY symbol, fractal_date DESC")
        rows = conn.execute(q).fetchall()
    if not rows:
        if progress_cb:
            progress_cb(0, 0, 'No bullish fractals found')
        return pd.DataFrame()

    df = pd.DataFrame(rows, columns=[c for c in rows[0]._fields])
    df['fractal_date'] = pd.to_datetime(df['fractal_date'])

    syms = sorted(df['symbol'].unique())
    if limit and limit > 0:
        syms = syms[:limit]

    total = len(syms)
    if progress_cb:
        progress_cb(0, total, f'Scanning {total} symbols for hidden bullish divergences')

    signals: List[dict] = []

    for idx, sym in enumerate(syms, start=1):
        sdf = df[df['symbol'] == sym].sort_values('fractal_date', ascending=False).reset_index(drop=True)
        if sdf.shape[0] < 2:
            if progress_cb:
                progress_cb(idx, total, f'Skipping {sym} (not enough bullish fractals)')
            continue
        # SMA filters: prefer precomputed SMAs in `moving_averages`. If missing, compute once and upsert using compute_moving_averages.
        if sma_filters:
            try:
                latest_date = pd.to_datetime(sdf.loc[0, 'fractal_date']).date()
                windows = sorted(set(int(x) for x in sma_filters))
                sma_cols = [f'sma_{w}' for w in windows]

                def _check_ma_row(ma_row, latest_close):
                    # ma_row: pandas Series containing sma_x columns
                    for c in sma_cols:
                        if c not in ma_row or pd.isna(ma_row.get(c)):
                            return False
                        try:
                            if not (latest_close > float(ma_row.get(c))):
                                return False
                        except Exception:
                            return False
                    return True

                ok = False
                latest_close = float(sdf.loc[0, 'center_close'])
                # 1) try to read last available moving_averages row for symbol <= latest_date
                try:
                    with engine.connect() as conn:
                        q = text(f"SELECT trade_date, {', '.join(sma_cols)} FROM moving_averages WHERE symbol = :s AND trade_date <= :d ORDER BY trade_date DESC LIMIT 1")
                        ma_df = pd.read_sql(q, con=conn, params={"s": sym, "d": latest_date.strftime('%Y-%m-%d')}, parse_dates=['trade_date'])
                    if not ma_df.empty:
                        if _check_ma_row(ma_df.iloc[0], latest_close):
                            ok = True
                except Exception:
                    # moving_averages table may not exist or query failed — fall through to compute
                    ok = False

                # 2) if not ok, compute SMAs once for the symbol and upsert into moving_averages using the helper
                if not ok:
                    import compute_moving_averages as cma
                    # compute_for_symbol expects a Connection with moving_averages table present; run inside a transaction
                    with engine.begin() as conn:
                        # ensure table exists for requested windows
                        try:
                            cma.ensure_table(conn, windows)
                        except Exception:
                            pass
                        try:
                            cma.compute_for_symbol(conn, sym, windows)
                        except Exception:
                            # compute_for_symbol may fail if data missing; we'll fallback later
                            pass
                    # re-query moving_averages
                    try:
                        with engine.connect() as conn:
                            q2 = text(f"SELECT trade_date, {', '.join(sma_cols)} FROM moving_averages WHERE symbol = :s AND trade_date <= :d ORDER BY trade_date DESC LIMIT 1")
                            ma_df2 = pd.read_sql(q2, con=conn, params={"s": sym, "d": latest_date.strftime('%Y-%m-%d')}, parse_dates=['trade_date'])
                        if not ma_df2.empty and _check_ma_row(ma_df2.iloc[0], latest_close):
                            ok = True
                    except Exception:
                        ok = False
                # 3) fallback: if still not ok, compute from BHAV as before (in-memory)
                if not ok:
                    max_window = max(windows)
                    with engine.connect() as conn:
                        q = text("SELECT trade_date, close_price FROM nse_equity_bhavcopy_full WHERE symbol = :s AND series = 'EQ' AND trade_date <= :d ORDER BY trade_date DESC LIMIT :n")
                        rows = conn.execute(q, {"s": sym, "d": latest_date.strftime('%Y-%m-%d'), "n": max_window + 20}).fetchall()
                    if not rows or len(rows) < 1:
                        if progress_cb:
                            progress_cb(idx, total, f'Skipping {sym} (no price history for SMA)')
                        continue
                    closes = pd.Series([r[1] for r in rows], dtype='float')
                    closes = closes.iloc[::-1].reset_index(drop=True)
                    ok2 = True
                    for w in windows:
                        if len(closes) < w:
                            ok2 = False
                            break
                        sma_val = closes.rolling(window=w).mean().iloc[-1]
                        if not (latest_close > float(sma_val)):
                            ok2 = False
                            break
                    if not ok2:
                        if progress_cb:
                            progress_cb(idx, total, f'Skipping {sym} (SMA filters not satisfied)')
                        continue
            except Exception:
                if progress_cb:
                    progress_cb(idx, total, f'Skipping {sym} (SMA filter error)')
                continue
        # latest is index 0, compare with next up to lookback_fractals
        latest = sdf.loc[0]
        for j in range(1, min(1 + lookback_fractals, len(sdf))):
            past = sdf.loc[j]
            try:
                curr_close = float(latest['center_close']) if pd.notna(latest['center_close']) else None
                past_close = float(past['center_close']) if pd.notna(past['center_close']) else None
                curr_rsi = float(latest['center_rsi']) if pd.notna(latest['center_rsi']) else None
                past_rsi = float(past['center_rsi']) if pd.notna(past['center_rsi']) else None
            except Exception:
                continue
            # require numeric values
            if curr_close is None or past_close is None or curr_rsi is None or past_rsi is None:
                continue
            # hidden bullish divergence condition
            if (curr_close > past_close) and (curr_rsi < past_rsi):
                signals.append({
                    'symbol': sym,
                    'signal_type': 'Hidden Bullish Divergence',
                    'signal_date': pd.to_datetime(latest['fractal_date']).date(),
                    'curr_fractal_date': pd.to_datetime(latest['fractal_date']).date(),
                    'curr_center_close': curr_close,
                    'curr_fractal_high': float(latest['fractal_high']) if pd.notna(latest['fractal_high']) else None,
                    'curr_fractal_low': float(latest['fractal_low']) if pd.notna(latest['fractal_low']) else None,
                    'curr_center_rsi': curr_rsi,
                    'comp_fractal_date': pd.to_datetime(past['fractal_date']).date(),
                    'comp_center_close': past_close,
                    'comp_fractal_high': float(past['fractal_high']) if pd.notna(past['fractal_high']) else None,
                    'comp_fractal_low': float(past['fractal_low']) if pd.notna(past['fractal_low']) else None,
                    'comp_center_rsi': past_rsi,
                    'buy_above_price': float(latest['fractal_high']) if pd.notna(latest['fractal_high']) else None,
                    'created_at': datetime.utcnow()
                })
        if progress_cb:
            progress_cb(idx, total, f'Processed {sym} ({len(signals)} signals)')

    if not signals:
        if progress_cb:
            progress_cb(total, total, 'No hidden bullish divergences found')
        return pd.DataFrame()

    df_signals = pd.DataFrame(signals)
    # upsert into DB
    upsert_divergences(engine, df_signals)
    if progress_cb:
        progress_cb(total, total, f'Upserted {len(df_signals)} divergence signals')
    return df_signals


def scan_hidden_bearish_divergences(engine, lookback_fractals: int = 5, progress_cb=None, limit: int = 0, sma_filters: List[int] = None) -> pd.DataFrame:
    """Scan `nse_fractals` for hidden bearish divergences.

    Hidden bearish: price lower (center_close < past.center_close) but RSI higher (center_rsi > past.center_rsi).
    Returns DataFrame of signals and upserts them.
    """
    # fetch bullish fractals (we need bearish fractals i.e., Bearish Fractal)
    with engine.connect() as conn:
        q = text("SELECT symbol, fractal_date, center_close, center_rsi, fractal_high, fractal_low FROM nse_fractals WHERE fractal_type = 'Bearish Fractal' ORDER BY symbol, fractal_date DESC")
        rows = conn.execute(q).fetchall()
    if not rows:
        if progress_cb:
            progress_cb(0, 0, 'No bearish fractals found')
        return pd.DataFrame()

    df = pd.DataFrame(rows, columns=[c for c in rows[0]._fields])
    df['fractal_date'] = pd.to_datetime(df['fractal_date'])

    syms = sorted(df['symbol'].unique())
    if limit and limit > 0:
        syms = syms[:limit]

    total = len(syms)
    if progress_cb:
        progress_cb(0, total, f'Scanning {total} symbols for hidden bearish divergences')

    signals: List[dict] = []

    for idx, sym in enumerate(syms, start=1):
        sdf = df[df['symbol'] == sym].sort_values('fractal_date', ascending=False).reset_index(drop=True)
        if sdf.shape[0] < 2:
            if progress_cb:
                progress_cb(idx, total, f'Skipping {sym} (not enough bearish fractals)')
            continue
        # SMA filters: prefer precomputed SMAs in `moving_averages`. If missing, compute once and upsert using compute_moving_averages.
        if sma_filters:
            try:
                latest_date = pd.to_datetime(sdf.loc[0, 'fractal_date']).date()
                windows = sorted(set(int(x) for x in sma_filters))
                sma_cols = [f'sma_{w}' for w in windows]

                def _check_ma_row_bear(ma_row, latest_close):
                    for c in sma_cols:
                        if c not in ma_row or pd.isna(ma_row.get(c)):
                            return False
                        try:
                            if not (latest_close < float(ma_row.get(c))):
                                return False
                        except Exception:
                            return False
                    return True

                ok = False
                latest_close = float(sdf.loc[0, 'center_close'])
                try:
                    with engine.connect() as conn:
                        q = text(f"SELECT trade_date, {', '.join(sma_cols)} FROM moving_averages WHERE symbol = :s AND trade_date <= :d ORDER BY trade_date DESC LIMIT 1")
                        ma_df = pd.read_sql(q, con=conn, params={"s": sym, "d": latest_date.strftime('%Y-%m-%d')}, parse_dates=['trade_date'])
                    if not ma_df.empty:
                        if _check_ma_row_bear(ma_df.iloc[0], latest_close):
                            ok = True
                except Exception:
                    ok = False

                if not ok:
                    import compute_moving_averages as cma
                    with engine.begin() as conn:
                        try:
                            cma.ensure_table(conn, windows)
                        except Exception:
                            pass
                        try:
                            cma.compute_for_symbol(conn, sym, windows)
                        except Exception:
                            pass
                    try:
                        with engine.connect() as conn:
                            q2 = text(f"SELECT trade_date, {', '.join(sma_cols)} FROM moving_averages WHERE symbol = :s AND trade_date <= :d ORDER BY trade_date DESC LIMIT 1")
                            ma_df2 = pd.read_sql(q2, con=conn, params={"s": sym, "d": latest_date.strftime('%Y-%m-%d')}, parse_dates=['trade_date'])
                        if not ma_df2.empty and _check_ma_row_bear(ma_df2.iloc[0], latest_close):
                            ok = True
                    except Exception:
                        ok = False
                if not ok:
                    max_window = max(windows)
                    with engine.connect() as conn:
                        q = text("SELECT trade_date, close_price FROM nse_equity_bhavcopy_full WHERE symbol = :s AND series = 'EQ' AND trade_date <= :d ORDER BY trade_date DESC LIMIT :n")
                        rows = conn.execute(q, {"s": sym, "d": latest_date.strftime('%Y-%m-%d'), "n": max_window + 20}).fetchall()
                    if not rows or len(rows) < 1:
                        if progress_cb:
                            progress_cb(idx, total, f'Skipping {sym} (no price history for SMA)')
                        continue
                    closes = pd.Series([r[1] for r in rows], dtype='float')
                    closes = closes.iloc[::-1].reset_index(drop=True)
                    ok2 = True
                    for w in windows:
                        if len(closes) < w:
                            ok2 = False
                            break
                        sma_val = closes.rolling(window=w).mean().iloc[-1]
                        if not (latest_close < float(sma_val)):
                            ok2 = False
                            break
                    if not ok2:
                        if progress_cb:
                            progress_cb(idx, total, f'Skipping {sym} (SMA filters not satisfied)')
                        continue
            except Exception:
                if progress_cb:
                    progress_cb(idx, total, f'Skipping {sym} (SMA filter error)')
                continue
        latest = sdf.loc[0]
        for j in range(1, min(1 + lookback_fractals, len(sdf))):
            past = sdf.loc[j]
            try:
                curr_close = float(latest['center_close']) if pd.notna(latest['center_close']) else None
                past_close = float(past['center_close']) if pd.notna(past['center_close']) else None
                curr_rsi = float(latest['center_rsi']) if pd.notna(latest['center_rsi']) else None
                past_rsi = float(past['center_rsi']) if pd.notna(past['center_rsi']) else None
            except Exception:
                continue
            if curr_close is None or past_close is None or curr_rsi is None or past_rsi is None:
                continue
            # hidden bearish: price lower but RSI higher
            if (curr_close < past_close) and (curr_rsi > past_rsi):
                signals.append({
                    'symbol': sym,
                    'signal_type': 'Hidden Bearish Divergence',
                    'signal_date': pd.to_datetime(latest['fractal_date']).date(),
                    'curr_fractal_date': pd.to_datetime(latest['fractal_date']).date(),
                    'curr_center_close': curr_close,
                    'curr_fractal_high': float(latest['fractal_high']) if pd.notna(latest['fractal_high']) else None,
                    'curr_fractal_low': float(latest['fractal_low']) if pd.notna(latest['fractal_low']) else None,
                    'curr_center_rsi': curr_rsi,
                    'comp_fractal_date': pd.to_datetime(past['fractal_date']).date(),
                    'comp_center_close': past_close,
                    'comp_fractal_high': float(past['fractal_high']) if pd.notna(past['fractal_high']) else None,
                    'comp_fractal_low': float(past['fractal_low']) if pd.notna(past['fractal_low']) else None,
                    'comp_center_rsi': past_rsi,
                    'buy_above_price': None,
                    'sell_below_price': float(latest['fractal_low']) if pd.notna(latest['fractal_low']) else None,
                    'created_at': datetime.utcnow()
                })
        if progress_cb:
            progress_cb(idx, total, f'Processed {sym} ({len(signals)} signals)')

    if not signals:
        if progress_cb:
            progress_cb(total, total, 'No hidden bearish divergences found')
        return pd.DataFrame()

    df_signals = pd.DataFrame(signals)
    upsert_divergences(engine, df_signals)
    if progress_cb:
        progress_cb(total, total, f'Upserted {len(df_signals)} divergence signals')
    return df_signals


def upsert_divergences(engine, df: pd.DataFrame):
    if df is None or df.empty:
        print('No divergence signals to upsert')
        return
    # ensure table and migrations are applied before attempting temp table operations
    ensure_divergences_table(engine)
    tmp = 'tmp_nse_rsi_divergences'
    with engine.begin() as conn:
        conn.execute(text(f"DROP TEMPORARY TABLE IF EXISTS {tmp}"))
        try:
            conn.execute(text(f"CREATE TEMPORARY TABLE {tmp} LIKE nse_rsi_divergences"))
        except Exception as e:
            # If the base table doesn't exist or cannot be referenced (1146), try to create it.
            msg = str(e)
            if '1146' in msg or 'doesn\'t exist' in msg or 'nse_rsi_divergences' in msg:
                try:
                    conn.execute(text(TABLE_SQL))
                    # try again
                    conn.execute(text(f"CREATE TEMPORARY TABLE {tmp} LIKE nse_rsi_divergences"))
                except Exception as e2:
                    # surface a clearer error with the CREATE TABLE SQL so user can run it manually
                    raise RuntimeError(
                        "Could not create base table nse_rsi_divergences automatically. "
                        "Please run the following SQL in your database with sufficient privileges:\n\n"
                        f"{TABLE_SQL}\n\nUnderlying error: {e2}"
                    )
            else:
                raise
        # dedupe
        keycols = ['symbol', 'signal_date', 'signal_type', 'comp_fractal_date']
        if all(c in df.columns for c in keycols):
            df = df.sort_values(keycols).drop_duplicates(subset=keycols, keep='last')
        df.to_sql(name=tmp, con=conn, if_exists='append', index=False, method='multi', chunksize=2000)
        cols = list(df.columns)
        col_list = ', '.join([f'`{c}`' for c in cols])
        select_list = col_list
        update_cols = [c for c in cols if c not in keycols]
        update_list = ', '.join([f'`{c}`=VALUES(`{c}`)' for c in update_cols]) or 'created_at=created_at'
        insert_sql = f"INSERT INTO nse_rsi_divergences ({col_list}) SELECT {select_list} FROM {tmp} ON DUPLICATE KEY UPDATE {update_list};"
        conn.execute(text(insert_sql))
        print(f'Upserted {len(df)} divergence signals into nse_rsi_divergences')
