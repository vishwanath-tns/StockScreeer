"""Simple data client for chart_tool.

By default this tries to import scanner service functions directly from the repository
so the chart tool can be run locally without a separate REST server. If you prefer
process separation, implement a small REST wrapper in the scanner repo and set
REST_API_BASE in the environment.
"""
from __future__ import annotations

import os
from typing import Optional
from datetime import datetime

import pandas as pd
from dotenv import load_dotenv
from pathlib import Path

# Try to locate a .env in this package or parent folders (useful when running
# the chart tool from the `chart_tool` subfolder). If none found, load_dotenv
# will still pick up environment variables from the process environment.
here = Path(__file__).resolve().parent
env_file = None
for p in (here, here.parent, here.parent.parent):
    candidate = p / '.env'
    if candidate.exists():
        env_file = str(candidate)
        break
if env_file:
    load_dotenv(env_file)
    print(f"services_client: loaded .env from {env_file}")
else:
    # fallback to default behavior (look for .env in cwd)
    load_dotenv()

# Read REST base URL if provided. If set, the client will use HTTP requests to
# the scanner REST wrapper. Otherwise it will try direct import of scanner
# service functions.
REST_API_BASE = os.getenv('REST_API_BASE')

if REST_API_BASE:
    import requests
else:
    # Try to import scanner service functions. If this fails, the caller should either
    # set PYTHONPATH so the scanner package is importable, or run the REST wrapper.
    try:
        from services.fractals_service import fetch_price_and_rsi  # type: ignore
    except Exception:
        fetch_price_and_rsi = None  # type: ignore


def _normalize_ohlcv(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    # index -> datetime
    try:
        df.index = pd.to_datetime(df.index)
    except Exception:
        pass
    df = df.sort_index()
    # normalize close column name
    for cand in ("close", "Close", "close_price", "ClosePrice", "Close_Price"):
        if cand in df.columns:
            df = df.rename(columns={cand: "close"})
            break
    # normalize volume
    for cand in ("volume", "Volume", "ttl_trd_qnty"):
        if cand in df.columns and cand != 'volume':
            df = df.rename(columns={cand: 'volume'})
            break
    # coerce numeric where applicable
    for col in df.columns:
        if df[col].dtype == object:
            try:
                df[col] = pd.to_numeric(df[col], errors='coerce')
            except Exception:
                pass
    return df


def get_ohlcv(symbol: str, days: Optional[int] = None, start: Optional[str] = None, end: Optional[str] = None) -> pd.DataFrame:
    """Return OHLCV DataFrame for symbol.

    Preferred shape: DatetimeIndex and columns at least ['close'] and optionally 'open','high','low','volume'.
    """
    if REST_API_BASE:
        # call REST endpoint
        params = {'symbol': symbol}
        if days:
            params['days'] = int(days)
        if start:
            params['start'] = start
        if end:
            params['end'] = end
        url = f"{REST_API_BASE.rstrip('/')}/api/ohlcv"
        r = requests.get(url, params=params, timeout=30)
        # provide a clearer error message containing the server's response body
        if not r.ok:
            try:
                err = r.json()
            except Exception:
                err = r.text
            raise RuntimeError(f"REST API error {r.status_code}: {err}")
        j = r.json()
        data = j.get('data', [])
        if not data:
            return pd.DataFrame()
        df = pd.DataFrame(data)
        # choose a sensible date column for the index. The server may include
        # multiple date-like columns (date, dt, trade_date). Prefer a column
        # that parses to datetimes; fall back to existing 'date' if parseable.
        date_candidates = [c for c in ('date', 'trade_date', 'dt') if c in df.columns]
        chosen = None
        for c in date_candidates:
            try:
                parsed = pd.to_datetime(df[c], errors='coerce')
                if parsed.notna().sum() >= max(1, len(df) // 2):
                    chosen = c
                    df[c] = parsed
                    break
            except Exception:
                continue
        if chosen is None and 'date' in df.columns:
            # last resort: try to parse 'date' as-is
            try:
                parsed = pd.to_datetime(df['date'], errors='coerce')
                if parsed.notna().any():
                    chosen = 'date'
                    df['date'] = parsed
            except Exception:
                pass

        if chosen is not None:
            df = df.set_index(chosen)
        else:
            # leave as-is (will be handled by normalizer)
            df = df
        # parse index and coerce numerics
        try:
            df.index = pd.to_datetime(df.index, errors='coerce')
        except Exception:
            pass
        return _normalize_ohlcv(df)

    if fetch_price_and_rsi is None:
        raise RuntimeError("Cannot import scanner services; ensure the scanner project root is on PYTHONPATH or set up the REST API.")

    # The scanner's fetch_price_and_rsi returns (ohlcv_df, rsi_df)
    ohlcv_df, _ = fetch_price_and_rsi(symbol, days=days)
    if ohlcv_df is None:
        return pd.DataFrame()
    return _normalize_ohlcv(ohlcv_df)


def get_rsi(symbol: str, period: int = 14, days: Optional[int] = None, start: Optional[str] = None, end: Optional[str] = None) -> pd.Series:
    """Return RSI series indexed by date. Uses the same fetch_price_and_rsi if available."""
    if REST_API_BASE:
        params = {'symbol': symbol, 'period': int(period)}
        if days:
            params['days'] = int(days)
        url = f"{REST_API_BASE.rstrip('/')}/api/rsi"
        r = requests.get(url, params=params, timeout=30)
        if not r.ok:
            try:
                err = r.json()
            except Exception:
                err = r.text
            raise RuntimeError(f"REST API error {r.status_code}: {err}")
        j = r.json()
        data = j.get('data', [])
        if not data:
            return pd.Series(dtype='float')
        df = pd.DataFrame(data)
        # choose date-like column for index
        date_candidates = [c for c in ('date', 'trade_date', 'dt') if c in df.columns]
        chosen = None
        for c in date_candidates:
            try:
                parsed = pd.to_datetime(df[c], errors='coerce')
                if parsed.notna().sum() >= max(1, len(df) // 2):
                    chosen = c
                    df[c] = parsed
                    break
            except Exception:
                continue
        if chosen is None and 'date' in df.columns:
            try:
                parsed = pd.to_datetime(df['date'], errors='coerce')
                if parsed.notna().any():
                    chosen = 'date'
                    df['date'] = parsed
            except Exception:
                pass

        if chosen is not None:
            df = df.set_index(chosen)
        try:
            df.index = pd.to_datetime(df.index, errors='coerce')
        except Exception:
            pass

        # pick RSI column (common names) or fallback to first numeric column
        rsi_col = None
        for cand in ('rsi', 'RSI', 'value'):
            if cand in df.columns:
                rsi_col = cand
                break
        if rsi_col is not None:
            s = pd.to_numeric(df[rsi_col], errors='coerce')
        else:
            # first numeric column
            numeric_cols = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
            if numeric_cols:
                s = pd.to_numeric(df[numeric_cols[0]], errors='coerce')
            else:
                s = pd.Series(dtype='float')
        s.index = df.index
        return s.sort_index()

    if fetch_price_and_rsi is None:
        raise RuntimeError("Cannot import scanner services; ensure the scanner project root is on PYTHONPATH or set up the REST API.")
    _ohlcv, rsi_df = fetch_price_and_rsi(symbol, days=days, period=period)
    if rsi_df is None or rsi_df.empty:
        return pd.Series(dtype='float')
    try:
        s = pd.to_numeric(rsi_df['rsi'], errors='coerce') if 'rsi' in rsi_df.columns else pd.to_numeric(rsi_df.iloc[:, 0], errors='coerce')
        s.index = pd.to_datetime(rsi_df.index)
        s = s.sort_index()
    except Exception:
        s = pd.Series(dtype='float')
    return s


def get_scan_results(scan_name: Optional[str] = None) -> pd.DataFrame:
    """Placeholder: in future call scanner to list scan results / fractal breaks.

    For now, this will raise unless you implement a scanner-side function that
    returns the needed DataFrame.
    """
    if REST_API_BASE:
        url = f"{REST_API_BASE.rstrip('/')}/api/fractal_breaks"
        r = requests.get(url, timeout=30)
        if not r.ok:
            try:
                err = r.json()
            except Exception:
                err = r.text
            raise RuntimeError(f"REST API error {r.status_code}: {err}")
        j = r.json()
        data = j.get('data', [])
        if not data:
            return pd.DataFrame()
        df = pd.DataFrame(data)
        try:
            df['fractal_date'] = pd.to_datetime(df['fractal_date'], errors='coerce')
        except Exception:
            pass
        return df
    raise NotImplementedError("get_scan_results is not implemented for direct import; add implementation or use REST API")
