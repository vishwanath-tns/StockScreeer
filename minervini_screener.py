"""minervini_screener.py

Screen stocks using Mark Minervini's 8-point Trend Template.

The screener prefers precomputed SMAs from `moving_averages`. If a required
SMA column (for example `sma_150`) is missing or contains NULLs for a symbol
on the target date, the screener will invoke helpers from
`compute_moving_averages.py` to compute and upsert the missing windows for
those symbols.

Usage (example):
    python minervini_screener.py --as-of 2025-10-17 --index "NIFTY 50" --limit 200

Outputs a CSV or prints results.
"""
from __future__ import annotations
import datetime
from typing import List
import pandas as pd
from sqlalchemy import text


def engine():
    import reporting_adv_decl as rad
    return rad.engine()


DEFAULT_52W_DAYS = 365


def _ensure_sma_columns(conn, windows: List[int]):
    # Ensure the moving_averages table has the requested sma_<w> columns.
    # If the table doesn't exist, try to create it using the helper. If it
    # exists but is missing columns, ALTER TABLE to add them (if allowed).
    try:
        import compute_moving_averages as cm
    except Exception:
        cm = None

    # First check if table exists and which columns it has
    try:
        q = text("SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'moving_averages'")
        rows = conn.execute(q).fetchall()
        existing = {r[0] for r in rows}
    except Exception:
        existing = set()

    # If table appears missing (no rows returned) and helper available, ask helper to create it
    if not existing and cm is not None:
        try:
            cm.ensure_table(conn, windows)
            # refresh
            rows = conn.execute(text("SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'moving_averages'")).fetchall()
            existing = {r[0] for r in rows}
        except Exception as e:
            print(f"Could not ensure moving_averages table via helper: {e}")

    # Now add any missing sma columns and collect a report
    report = {
        'existing_columns': sorted(list(existing)),
        'added': [],
        'errors': [],
        'created_table': False,
    }
    for w in windows:
        col = f"sma_{w}"
        if col in existing:
            continue
        try:
            alter_sql = text(f"ALTER TABLE moving_averages ADD COLUMN {col} DOUBLE NULL")
            conn.execute(alter_sql)
            report['added'].append(col)
            existing.add(col)
        except Exception as e:
            # Most likely permission error; capture and continue
            report['errors'].append({'column': col, 'error': str(e)})

    return report


def ensure_and_compute_smas(conn, windows: List[int], as_of: datetime.date | None = None, symbols: list[str] | None = None, limit: int = 0):
    """Ensure SMA columns exist and compute+upsert missing SMA rows per-symbol.

    Returns a report dict: includes 'ensure_report' from _ensure_sma_columns, 'computed' list and 'compute_errors'.
    """
    ensure_report = _ensure_sma_columns(conn, windows)

    # Build symbol list
    if symbols is None:
        rows = conn.execute(text("SELECT DISTINCT symbol FROM nse_equity_bhavcopy_full WHERE series = 'EQ' ORDER BY symbol")).fetchall()
        syms = [r[0] for r in rows]
    else:
        syms = list(symbols)
    if limit and limit > 0:
        syms = syms[:limit]

    computed = []
    compute_errors = []

    # import helper
    try:
        import compute_moving_averages as cm
    except Exception:
        cm = None

    for s in syms:
        try:
            need = False
            cols = ", ".join([f"sma_{w}" for w in windows])
            if as_of is not None:
                q = text(f"SELECT {cols} FROM moving_averages WHERE symbol=:s AND trade_date = :d")
                try:
                    row = conn.execute(q, {"s": s, "d": as_of}).fetchone()
                    if not row:
                        need = True
                    else:
                        if any(x is None for x in row):
                            need = True
                except Exception:
                    # table/columns may be missing -> we need compute
                    need = True
            else:
                q = text(f"SELECT {cols} FROM moving_averages WHERE symbol=:s ORDER BY trade_date DESC LIMIT 1")
                try:
                    row = conn.execute(q, {"s": s}).fetchone()
                    if not row or any(x is None for x in row):
                        need = True
                except Exception:
                    need = True

            if need:
                if cm is None:
                    compute_errors.append({"symbol": s, "error": "compute_moving_averages helper not available"})
                else:
                    try:
                        cm.compute_for_symbol(conn, s, windows)
                        computed.append(s)
                    except Exception as e:
                        compute_errors.append({"symbol": s, "error": str(e)})
        except Exception as e:
            compute_errors.append({"symbol": s, "error": str(e)})

    report = {
        'ensure_report': ensure_report,
        'computed': computed,
        'compute_errors': compute_errors,
    }
    return report


def _compute_missing_smas_for_symbols(conn, symbols: List[str], windows: List[int]):
    """Compute and upsert SMA windows for a list of symbols using helper.

    This is intentionally conservative: call the compute helper per-symbol so
    we reuse existing logic in compute_moving_averages which uses a temp table
    + bulk upsert.
    """
    import compute_moving_averages as cm
    for s in symbols:
        try:
            cm.compute_for_symbol(conn, s, windows)
        except Exception as e:
            print(f"Error computing SMAs for {s}: {e}")


def _fetch_moving_averages(conn, as_of: datetime.date, windows: List[int]) -> pd.DataFrame:
    cols = ", ".join([f"sma_{w}" for w in windows])
    q = f"SELECT trade_date, symbol, {cols} FROM moving_averages WHERE trade_date = :d"
    df = pd.read_sql(text(q), con=conn, params={"d": as_of}, parse_dates=["trade_date"]) if True else pd.DataFrame()
    return df


def _get_latest_date(conn) -> datetime.date:
    # Use only series='EQ' rows when deriving the latest trading date
    q = text("SELECT MAX(trade_date) FROM nse_equity_bhavcopy_full WHERE series='EQ'")
    r = conn.execute(q).scalar()
    if r is None:
        return datetime.date.today()
    if isinstance(r, datetime.datetime):
        return r.date()
    return r


def screen_minervini(as_of: datetime.date | None = None, index_name: str = "NIFTY 50", rs_lookback_days: int = 252, limit: int = 0, use_trading_days_for_52w: bool = False, verbose: bool = False) -> pd.DataFrame:
    """Run the Minervini 8-point template scan and return a DataFrame of matches.

    The checks implemented (by number):
    1. close > sma_150 and close > sma_200
    2. sma_150 > sma_200
    3. sma_200 trending up over last ~21 trading days (compare sma_200 now vs ~21 days ago)
    4. sma_50 > sma_150 and sma_50 > sma_200
    5. close > sma_50
    6. close >= 1.30 * 52w_low
    7. close >= 0.75 * 52w_high
    8. relative strength percentile >= 70 (computed across symbols for rs_lookback_days)

    Returns DataFrame with columns: symbol, date, close, sma_50, sma_150, sma_200, rs_percentile, 52w_low, 52w_high
    """
    # ensure output containers exist even if an early exception occurs
    rows_out = []
    verbose_rows = []

    eng = engine()
    conn = eng.connect()
    try:
        if as_of is None:
            as_of = _get_latest_date(conn)

        windows = [50, 150, 200]
        # Ensure the SMA columns exist
        _ensure_sma_columns(conn, [5, 10, 20, 50, 100, 150, 200])

        # Try to load moving averages for as_of
        try:
            mv = _fetch_moving_averages(conn, as_of, windows)
        except Exception as e:
            print(f"Error fetching moving_averages for {as_of}: {e}")
            mv = pd.DataFrame()

        # If some symbols missing SMA values, compute per-symbol
        symbols_needed = []
        if mv.empty:
            # nothing present for this date (maybe table uses trading dates). We'll attempt to compute for top symbols list later.
            pass
        else:
            # find symbols with NA in any required sma
            na_mask = mv[[f"sma_{w}" for w in windows]].isna().any(axis=1)
            symbols_needed = mv.loc[na_mask, 'symbol'].tolist()

        # If we didn't find mv rows (or found missing SMAs), compute for all symbols or for the subset
        if symbols_needed:
            print(f"Computing missing SMA windows for {len(symbols_needed)} symbols...")
            _compute_missing_smas_for_symbols(conn, symbols_needed, windows)
            mv = _fetch_moving_averages(conn, as_of, windows)

        # If still empty, fall back to reading the latest available moving_averages rows per symbol
        if mv.empty:
            q = text("SELECT m.trade_date, m.symbol, m.sma_50, m.sma_150, m.sma_200 FROM moving_averages m JOIN (SELECT symbol, MAX(trade_date) as t FROM moving_averages GROUP BY symbol) t ON m.symbol=t.symbol AND m.trade_date=t.t")
            try:
                mv = pd.read_sql(q, con=conn, parse_dates=["trade_date"])
            except Exception as e:
                print(f"Error fetching latest moving_averages per symbol: {e}")
                mv = pd.DataFrame()

        # If mv is an empty DataFrame, use None to indicate no in-memory mv table available
        if mv is not None and mv.empty:
            mv = None

        # Build base symbol list
        if limit and mv is not None:
            syms = mv['symbol'].unique().tolist()[:limit]
        elif mv is not None:
            syms = mv['symbol'].unique().tolist()
        else:
            # fallback: list symbols from BHAV
            rows = conn.execute(text("SELECT DISTINCT symbol FROM nse_equity_bhavcopy_full WHERE series = 'EQ' ORDER BY symbol"))
            syms = [r[0] for r in rows]
            if limit:
                    syms = syms[:limit]

            rows_out = []
            verbose_rows = []
            # Precompute RS for candidate symbols (to get percentile). We'll compute RS in bulk using existing helper if available.
            rs_map = {}
            try:
                import scan_relative_strength as srs
                # compute RS in bulk for our symbol list
                df_rs = srs.compute_relative_strength_bulk(conn, index_name, as_of, rs_lookback_days, symbols=syms)
                if not df_rs.empty:
                    # rank into percentile 0..100
                    df_rs['rs_rank_pct'] = df_rs['rs_value'].rank(pct=True) * 100
                    rs_map = df_rs.set_index('symbol')['rs_rank_pct'].to_dict()
            except Exception:
                # fallback: empty map
                rs_map = {}

            for sym in syms:
                try:
                    sym_steps = []
                    # get moving averages row for symbol (if mv in-memory provided)
                    last = None
                    if mv is not None:
                        sub = mv[mv['symbol'] == sym]
                        if not sub.empty:
                            last = sub.iloc[0]
                    if last is None:
                        # attempt to read latest row for symbol
                        q = text("SELECT trade_date, symbol, sma_50, sma_150, sma_200 FROM moving_averages WHERE symbol=:s ORDER BY trade_date DESC LIMIT 1")
                        row = pd.read_sql(q, con=conn, params={"s": sym}, parse_dates=["trade_date"]) or pd.DataFrame()
                        if row.empty:
                            # no moving averages available; skip symbol
                            sym_steps.append('no moving_averages row found')
                            if verbose:
                                verbose_rows.append({'symbol': sym, 'steps': sym_steps})
                            continue
                        last = row.iloc[0]

                    # fetch close as of date (nearest <= as_of)
                    q_close = text("SELECT close_price FROM nse_equity_bhavcopy_full WHERE symbol=:s AND series='EQ' AND trade_date <= :d ORDER BY trade_date DESC LIMIT 1")
                    r = conn.execute(q_close, {"s": sym, "d": as_of}).fetchone()
                    if not r or r[0] is None:
                        continue
                    close = float(r[0])

                    sma50 = float(last.get('sma_50')) if not pd.isna(last.get('sma_50')) else None
                    sma150 = float(last.get('sma_150')) if not pd.isna(last.get('sma_150')) else None
                    sma200 = float(last.get('sma_200')) if not pd.isna(last.get('sma_200')) else None

                    # Rule 1 & 2
                    if sma150 is None or sma200 is None:
                        sym_steps.append('missing sma150/sma200')
                        if verbose:
                            verbose_rows.append({'symbol': sym, 'steps': sym_steps})
                        continue
                    sym_steps.append(f'sma150={sma150}, sma200={sma200}')
                    if not (close > sma150 and close > sma200):
                        sym_steps.append(f'close {close} not > sma150/sma200')
                        if verbose:
                            verbose_rows.append({'symbol': sym, 'steps': sym_steps})
                        continue
                    if not (sma150 > sma200):
                        sym_steps.append('sma150 <= sma200')
                        if verbose:
                            verbose_rows.append({'symbol': sym, 'steps': sym_steps})
                        continue

                    # Rule 3: sma200 trending up over last ~21 available rows
                    q_hist = text("SELECT trade_date, sma_200 FROM moving_averages WHERE symbol=:s AND sma_200 IS NOT NULL AND trade_date <= :d ORDER BY trade_date DESC LIMIT 30")
                    h = pd.read_sql(q_hist, con=conn, params={"s": sym, "d": as_of}, parse_dates=["trade_date"]) if True else pd.DataFrame()
                    if len(h) >= 22:
                        h = h.sort_values('trade_date')
                        if h.iloc[-1]['sma_200'] <= h.iloc[-22]['sma_200']:
                            sym_steps.append('sma200 not trending up')
                            if verbose:
                                verbose_rows.append({'symbol': sym, 'steps': sym_steps})
                            continue
                    else:
                        # not enough history to evaluate trend; skip
                        sym_steps.append('not enough sma200 history')
                        if verbose:
                            verbose_rows.append({'symbol': sym, 'steps': sym_steps})
                        continue

                    # Rule 4 & 5
                    if sma50 is None:
                        sym_steps.append('missing sma50')
                        if verbose:
                            verbose_rows.append({'symbol': sym, 'steps': sym_steps})
                        continue
                    if not (sma50 > sma150 and sma50 > sma200):
                        sym_steps.append('sma50 not > sma150/sma200')
                        if verbose:
                            verbose_rows.append({'symbol': sym, 'steps': sym_steps})
                        continue
                    if not (close > sma50):
                        sym_steps.append('close not > sma50')
                        if verbose:
                            verbose_rows.append({'symbol': sym, 'steps': sym_steps})
                        continue
                    sym_steps.append('passed SMA checks')

                    # Rule 6 & 7: 52-week low/high
                    lookback_days = DEFAULT_52W_DAYS
                    q_52 = text("SELECT MIN(close_price), MAX(close_price) FROM nse_equity_bhavcopy_full WHERE symbol=:s AND trade_date BETWEEN :a AND :b AND series='EQ'")
                    start = as_of - datetime.timedelta(days=lookback_days)
                    r52 = conn.execute(q_52, {"s": sym, "a": start, "b": as_of}).fetchone()
                    if not r52 or r52[0] is None:
                        continue
                    low52, high52 = float(r52[0]), float(r52[1])
                    if not (close >= 1.30 * low52):
                        sym_steps.append(f'close {close} < 1.30*52wlow {1.30*low52}')
                        if verbose:
                            verbose_rows.append({'symbol': sym, 'steps': sym_steps})
                        continue
                    if not (close >= 0.75 * high52):
                        sym_steps.append(f'close {close} < 0.75*52whigh {0.75*high52}')
                        if verbose:
                            verbose_rows.append({'symbol': sym, 'steps': sym_steps})
                        continue
                    sym_steps.append(f'52w low/high ok (low={low52}, high={high52})')

                    # Rule 8: RS percentile
                    rs_pct = rs_map.get(sym)
                    if rs_pct is None:
                        # if RS not computed for symbol, skip
                        sym_steps.append('no RS value')
                        if verbose:
                            verbose_rows.append({'symbol': sym, 'steps': sym_steps})
                        continue
                    if rs_pct < 70.0:
                        sym_steps.append(f'rs_pct {rs_pct} < 70')
                        if verbose:
                            verbose_rows.append({'symbol': sym, 'steps': sym_steps})
                        continue
                    sym_steps.append(f'rs_pct={rs_pct}')

                    rows_out.append({
                        'symbol': sym,
                        'date': as_of,
                        'close': close,
                        'sma_50': sma50,
                        'sma_150': sma150,
                        'sma_200': sma200,
                        'rs_percentile': rs_pct,
                        '52w_low': low52,
                        '52w_high': high52,
                    })
                    if verbose:
                        verbose_rows.append({'symbol': sym, 'steps': sym_steps + ['PASSED']})
                except Exception as e:
                    print(f"Error evaluating {sym}: {e}")
                    if verbose:
                        verbose_rows.append({'symbol': sym, 'steps': [f'EXCEPTION: {e}']})

    finally:
        try:
            conn.close()
        except Exception:
            pass

    df_out = pd.DataFrame(rows_out)
    if not df_out.empty:
        df_out = df_out.sort_values(by=['rs_percentile', 'close'], ascending=[False, False])
    # attach verbose list as attribute when requested
    if verbose:
        # return both df and verbose_rows in a tuple for the caller
        return df_out, verbose_rows
    return df_out


def main():
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument('--as-of', help='As-of date YYYY-MM-DD (default: latest BHAV date)', default=None)
    p.add_argument('--index', help='Index name for RS calculation', default='NIFTY 50')
    p.add_argument('--lookback', type=int, default=252, help='RS lookback days')
    p.add_argument('--limit', type=int, default=0, help='Limit number of symbols to process')
    p.add_argument('--out', help='CSV output path', default=None)
    args = p.parse_args()
    as_of = pd.to_datetime(args.as_of).date() if args.as_of else None
    df = screen_minervini(as_of=as_of, index_name=args.index, rs_lookback_days=args.lookback, limit=args.limit)
    if args.out:
        df.to_csv(args.out, index=False)
        print(f"Wrote {len(df)} rows to {args.out}")
    else:
        print(df.to_string(index=False))


if __name__ == '__main__':
    main()
