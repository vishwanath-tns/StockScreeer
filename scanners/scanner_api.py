"""Small REST wrapper for scanner services.

Run with:
    uvicorn scanner_api:app --reload

This exposes lightweight endpoints used by chart_tool when REST_API_BASE is set.
"""
from __future__ import annotations

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional
import pandas as pd
import traceback
import datetime
from pathlib import Path


def _log_exception(exc: Exception) -> None:
    """Append full traceback for exc to scanner_api_errors.log in the repo root."""
    try:
        repo_dir = Path(__file__).resolve().parent
        log_path = repo_dir / 'scanner_api_errors.log'
        with open(log_path, 'a', encoding='utf8') as fh:
            fh.write('\n--- %s ---\n' % datetime.datetime.now().isoformat())
            traceback.print_exc(file=fh)
    except Exception:
        # best-effort logging; don't raise from the logger itself
        pass


# Expose the log location on import so the running server prints it to stdout
try:
    _repo_dir = Path(__file__).resolve().parent
    _log_path = _repo_dir / 'scanner_api_errors.log'
    print(f"scanner_api loaded; error log: {_log_path}")
except Exception:
    pass

# Print masked DB env info to help debugging which env the server process sees
try:
    import os
    db_user = os.getenv('MYSQL_USER')
    db_host = os.getenv('MYSQL_HOST')
    pwd_set = 'YES' if os.getenv('MYSQL_PASSWORD') else 'NO'
    print(f"DB env (masked): user={db_user}, host={db_host}, password_set={pwd_set}")
except Exception:
    pass

app = FastAPI(title="StockScreeer Scanner API")
# Allow local origins; in production restrict this
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Import scanner service functions lazily so this module can be imported even if
# scanner internals change. These functions are expected to exist in the repo.
try:
    from services.fractals_service import fetch_price_and_rsi, scan_fractal_breaks  # type: ignore
except Exception:
    fetch_price_and_rsi = None  # type: ignore
    scan_fractal_breaks = None  # type: ignore


def _df_to_json_records(df: pd.DataFrame):
    if df is None:
        return []
    df2 = df.copy()
    try:
        # ensure index is date string
        df2.index = pd.to_datetime(df2.index)
        df2 = df2.reset_index().rename(columns={'index': 'date'})
        df2['date'] = df2['date'].dt.strftime('%Y-%m-%d')
    except Exception:
        df2 = df2.reset_index().rename(columns={'index': 'date'})
        df2['date'] = df2['date'].astype(str)
    # convert Decimal and numpy types to native Python using to_dict then normalize
    records = df2.to_dict(orient='records')
    # normalize common non-JSON-native types (Decimal, numpy types)
    from decimal import Decimal
    import numpy as np

    def normalize_value(v):
        if isinstance(v, Decimal):
            try:
                return float(v)
            except Exception:
                return str(v)
        if isinstance(v, (np.integer,)):
            return int(v)
        if isinstance(v, (np.floating,)):
            return float(v)
        if isinstance(v, (np.bool_)):
            return bool(v)
        return v

    normalized = []
    for rec in records:
        nr = {k: normalize_value(v) for k, v in rec.items()}
        normalized.append(nr)
    return normalized


@app.get('/api/ohlcv')
def api_ohlcv(symbol: str = Query(..., min_length=1), days: Optional[int] = Query(None, ge=1)):
    if fetch_price_and_rsi is None:
        raise HTTPException(status_code=500, detail='Scanner services not importable')
    try:
        ohlcv_df, _ = fetch_price_and_rsi(symbol, days=days)
    except Exception as e:
        _log_exception(e)
        raise HTTPException(status_code=500, detail=str(e))
    return {'symbol': symbol, 'data': _df_to_json_records(ohlcv_df)}


@app.get('/api/rsi')
def api_rsi(symbol: str = Query(..., min_length=1), period: int = Query(14, ge=1), days: Optional[int] = Query(None, ge=1)):
    if fetch_price_and_rsi is None:
        raise HTTPException(status_code=500, detail='Scanner services not importable')
    try:
        _ohlcv, rsi_df = fetch_price_and_rsi(symbol, days=days)
    except Exception as e:
        _log_exception(e)
        raise HTTPException(status_code=500, detail=str(e))
    if rsi_df is None:
        return {'symbol': symbol, 'data': []}
    # ensure column 'rsi' exists or take first numeric column
    df = rsi_df.copy()
    if 'rsi' not in df.columns and df.shape[1] > 0:
        df.columns = ['rsi'] + list(df.columns[1:])
    return {'symbol': symbol, 'data': _df_to_json_records(df)}


@app.get('/api/fractal_breaks')
def api_fractal_breaks():
    if scan_fractal_breaks is None:
        raise HTTPException(status_code=500, detail='scanner scan_fractal_breaks not importable')
    try:
        df = scan_fractal_breaks()
    except Exception as e:
        _log_exception(e)
        raise HTTPException(status_code=500, detail=str(e))
    return {'data': _df_to_json_records(df)}


if __name__ == '__main__':
    import uvicorn
    uvicorn.run('scanner_api:app', host='127.0.0.1', port=5000, reload=True)
