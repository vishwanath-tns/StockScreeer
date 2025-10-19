#!/usr/bin/env python3
"""Import index CSV(s) into MySQL.

Usage examples (PowerShell):

# set DB env vars or create a .env file with MYSQL_* entries
$env:MYSQL_HOST = 'localhost'; $env:MYSQL_PORT = '3306'; $env:MYSQL_DB = 'market'; $env:MYSQL_USER = 'root'; $env:MYSQL_PASSWORD = 'pass'; python .\import_nifty_index.py --file 'C:\path\to\index.csv'

The script supports creating the target table (if missing) with --create-table and uses a temporary table + INSERT ... ON DUPLICATE KEY UPDATE to perform an upsert.
"""
from __future__ import annotations

import argparse
import os
import re
import sys
from typing import Optional, Dict, Any, List, Tuple
from pathlib import Path

import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from dotenv import load_dotenv
from urllib.parse import quote_plus


COL_MAP = {
    # source column (case-insensitive, with spaces) -> target column
    "date": "trade_date",
    "open": "open",
    "high": "high",
    "low": "low",
    "close": "close",
    "shares traded": "shares_traded",
    "turnover (₹ cr)": "turnover_cr",
    "turnover (rs cr)": "turnover_cr",
}


def filename_to_index_name(stem: str) -> str:
    """Derive a clean index name from a file stem by removing trailing "from-to" date ranges.

    Examples:
      'NIFTY 50-18-10-2024-to-18-10-2025' -> 'NIFTY 50'
      'NIFTY_50 18-10-2024 to 18-10-2025' -> 'NIFTY_50'
    """
    if not stem:
        return stem
    s = stem.strip()
    # remove common trailing date-range patterns like ' -DD-MM-YYYY-to-DD-MM-YYYY' or ' DD-MM-YYYY to DD-MM-YYYY'
    s2 = re.sub(
        r"(?i)\s*[-_]*\d{1,2}[-_.]\d{1,2}[-_.]\d{2,4}\s*(?:to|-to-|_to_|\s+to\s+)\s*\d{1,2}[-_.]\d{1,2}[-_.]\d{2,4}$",
        "",
        s,
    ).strip()
    # strip trailing separators
    s2 = re.sub(r"[\s_\-]+$", "", s2).strip()
    return s2 or s


def build_engine() -> Engine:
    host = os.getenv("MYSQL_HOST", "localhost")
    port = os.getenv("MYSQL_PORT", "3306")
    db = os.getenv("MYSQL_DB", "market")
    user = os.getenv("MYSQL_USER", "root")
    password = os.getenv("MYSQL_PASSWORD", "")
    # URL-encode user/password to safely include special characters (e.g. @)
    user_q = quote_plus(user)
    pw_q = quote_plus(password)
    url = f"mysql+pymysql://{user_q}:{pw_q}@{host}:{port}/{db}?charset=utf8mb4"
    return create_engine(url, pool_pre_ping=True)


def normalise_columns(df: pd.DataFrame) -> pd.DataFrame:
    # strip and lowercase column names
    df = df.copy()
    df.columns = [re.sub(r"\s+", " ", c).strip().lower() for c in df.columns]

    # map columns using COL_MAP (fallback to lowercased names)
    rename = {}
    for c in df.columns:
        if c in COL_MAP:
            rename[c] = COL_MAP[c]
        else:
            # try to match a prefix like 'date ' or 'turnover'
            for k in COL_MAP:
                if c.startswith(k):
                    rename[c] = COL_MAP[k]
                    break

    df = df.rename(columns=rename)

    # parse date
    if "trade_date" in df.columns:
        df["trade_date"] = pd.to_datetime(df["trade_date"], dayfirst=True, errors="coerce")

    # numeric cleaning helper
    def clean_numeric(s: pd.Series):
        return (
            s.astype(str)
            .str.replace(r"[^0-9.\-]", "", regex=True)
            .replace(["", "nan", "na", "naN"], pd.NA)
            .astype("float64")
        )

    for col in ("open", "high", "low", "close", "shares_traded", "turnover_cr"):
        if col in df.columns:
            df[col] = clean_numeric(df[col])

    # drop rows without a valid trade_date
    df = df[df["trade_date"].notna()]

    # keep only the columns we care about (if present)
    keep = ["trade_date", "open", "high", "low", "close", "shares_traded", "turnover_cr"]
    df = df[[c for c in keep if c in df.columns]]

    # ensure trade_date is a date (no time)
    df["trade_date"] = pd.to_datetime(df["trade_date"]).dt.date

    # drop duplicates on trade_date, keep last
    if "trade_date" in df.columns:
        df = df.drop_duplicates(subset=["trade_date"], keep="last")

    return df


CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS indices_daily (
    index_name VARCHAR(64) NOT NULL,
    trade_date DATE NOT NULL,
    `open` DOUBLE NULL,
    `high` DOUBLE NULL,
    `low` DOUBLE NULL,
    `close` DOUBLE NULL,
    shares_traded BIGINT NULL,
    turnover_cr DOUBLE NULL,
    PRIMARY KEY (index_name, trade_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
"""


def upsert_with_temp_table(engine: Engine, df: pd.DataFrame, table: str = "indices_daily") -> None:
    if df.empty:
        print("No rows to import. Exiting.")
        return

    cols = list(df.columns)
    # ensure index_name column exists (required by target schema)
    if "index_name" not in cols:
        df = df.copy()
        df["index_name"] = "UNKNOWN"
        cols = list(df.columns)
    # start transaction and use same connection for to_sql and SQL statements
    with engine.begin() as conn:
        # ensure target table exists
        conn.execute(text(CREATE_TABLE_SQL))

        # create a temporary table like the destination
        tmp_name = "tmp_indices_import"
        conn.execute(text(f"DROP TEMPORARY TABLE IF EXISTS {tmp_name}"))
        conn.execute(text(f"CREATE TEMPORARY TABLE {tmp_name} LIKE {table}"))

        # use pandas to_sql with the active connection's engine
        # pandas 1.4+ accepts SQLAlchemy Connection as 'con'
        df.to_sql(name=tmp_name, con=conn, if_exists="append", index=False, method="multi", chunksize=1000)

        # build column lists for insert
        col_list = ", ".join([f"`{c}`" for c in cols])
        select_list = col_list
        # avoid updating the primary key pair (index_name, trade_date)
        update_cols = [c for c in cols if c not in ("index_name", "trade_date")]
        update_list = ", ".join([f"`{c}`=VALUES(`{c}`)" for c in update_cols]) or "trade_date=trade_date"

        insert_sql = f"INSERT INTO {table} ({col_list}) SELECT {select_list} FROM {tmp_name} ON DUPLICATE KEY UPDATE {update_list};"
        conn.execute(text(insert_sql))

        print(f"Upserted {len(df)} rows into {table} (via {tmp_name})")


def import_file(path: str, engine: Engine, table: str = "indices_daily", upsert: bool = True, index_name: Optional[str] = None) -> Dict[str, Any]:
    """Import a single CSV file. Returns a summary dict."""
    if not os.path.exists(path):
        return {"file": path, "ok": False, "reason": "not found"}

    try:
        df = pd.read_csv(path, skip_blank_lines=True)
    except Exception as e:
        return {"file": path, "ok": False, "reason": f"read error: {e}"}

    df = normalise_columns(df)

    # derive index_name from filename if not provided
    if index_name is None:
        try:
            raw = Path(path).stem
            index_name = filename_to_index_name(raw)
        except Exception:
            index_name = "UNKNOWN"

    # ensure index_name column exists
    df["index_name"] = index_name

    if df.empty:
        return {"file": path, "ok": True, "rows": 0}

    try:
        if upsert:
            upsert_with_temp_table(engine, df, table=table)
        else:
            with engine.begin() as conn:
                df.to_sql(name=table, con=conn, if_exists="append", index=False, method="multi", chunksize=1000)
        return {"file": path, "ok": True, "rows": len(df)}
    except Exception as e:
        return {"file": path, "ok": False, "reason": f"db error: {e}"}


def import_folder(folder: str, engine: Engine, table: str = "indices_daily", upsert: bool = True, recurse: bool = False) -> List[Dict[str, Any]]:
    """Import all CSV files from a folder. Returns list of per-file summaries."""
    files: List[str] = []
    if recurse:
        for root, _, filenames in os.walk(folder):
            for fn in filenames:
                if fn.lower().endswith(".csv"):
                    files.append(os.path.join(root, fn))
    else:
        for fn in os.listdir(folder):
            if fn.lower().endswith(".csv"):
                files.append(os.path.join(folder, fn))

    summaries: List[Dict[str, Any]] = []
    for f in sorted(files):
        # derive index name from filename
        try:
            raw = Path(f).stem
            idx = filename_to_index_name(raw)
        except Exception:
            idx = None
        summaries.append(import_file(f, engine, table=table, upsert=upsert, index_name=idx))

    return summaries


def main(argv: Optional[list[str]] = None) -> int:
    p = argparse.ArgumentParser(description="Import index CSV into MySQL indices_daily table")
    p.add_argument("--file", "-f", required=True, help="Path to the CSV file to import")
    p.add_argument("--table", default="indices_daily", help="Target table name")
    p.add_argument("--create-table", action="store_true", help="Create target table if it doesn't exist")
    p.add_argument("--no-upsert", action="store_true", help="Do not upsert; just append (useful for dry run)")
    args = p.parse_args(argv)

    load_dotenv()

    csv_path = args.file
    if not os.path.exists(csv_path):
        print(f"File not found: {csv_path}")
        return 2

    print(f"Reading {csv_path} ...")
    df = pd.read_csv(csv_path, skip_blank_lines=True)
    df = normalise_columns(df)
    print(f"Parsed {len(df)} rows, columns: {list(df.columns)}")

    engine = build_engine()

    if args.create_table:
        with engine.begin() as conn:
            conn.execute(text(CREATE_TABLE_SQL))
        print("Created target table (if it did not exist)")

    if args.no_upsert:
        # simple append
        with engine.begin() as conn:
            df.to_sql(name=args.table, con=conn, if_exists="append", index=False, method="multi", chunksize=1000)
        print(f"Appended {len(df)} rows to {args.table}")
    else:
        upsert_with_temp_table(engine, df, table=args.table)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
