import os, traceback, pandas as pd
from pathlib import Path
from dotenv import load_dotenv

# try to find a .env file in this repo or parent folders (useful when env is stored outside)
here = Path(__file__).resolve().parent
env_file = None
for p in (here, here.parent, here.parent.parent):
    candidate = p / '.env'
    if candidate.exists():
        env_file = str(candidate)
        break
if env_file:
    load_dotenv(env_file)
    print(f"Loaded .env from: {env_file}")
else:
    print("No .env found in repo or parents; falling back to existing environment variables")

# make sure python process can import local scanner package by adding repo root to sys.path
import sys
repo_root = str((here.parent).resolve())
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)
    print(f"Inserted repo root into sys.path: {repo_root}")
else:
    print(f"Repo root already in sys.path: {repo_root}")
print("Running diagnostic: PYTHONPATH=", os.environ.get('PYTHONPATH'))
try:
    # import the scanner helper used by the REST API
    from services.fractals_service import fetch_price_and_rsi
    print("Imported services.fractals_service.fetch_price_and_rsi OK")
    # call the function exactly as the API does
    df, rsi = fetch_price_and_rsi('SBIN', days=5)
    print("fetch_price_and_rsi returned ohlcv rows:", 0 if df is None else len(df))
    if df is not None and not df.empty:
        print("Columns:", list(df.columns))
        print("Index dtype:", df.index.dtype)
        print("First 3 rows (as dict):")
        print(df.head(3).to_dict())
    else:
        print("No OHLCV rows returned (None or empty DataFrame).")
    print("RSI rows:", 0 if rsi is None else (len(rsi) if hasattr(rsi, '__len__') else 'unknown'))
except Exception:
    traceback.print_exc()
