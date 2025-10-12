## Quick intent

Help a coding assistant be productive quickly in this repo by documenting the app entrypoints, data flows, environment expectations, and small examples taken directly from the code.

## Where to start

- Primary script: `sync_bhav_gui.py` — single-file app that contains the full pipeline: file discovery -> parsing -> upsert to MySQL -> simple Tk GUI.
- Dependencies: see `requirements.txt` (pandas, sqlalchemy, pymysql, python-dotenv, tqdm).

## Big picture / architecture

- Input: BHAV files (CSV or ZIP that contains one CSV). The repo contains a sample `bhav_data/sec_bhavdata_full_10102025.csv`.
- Parsing: `read_any()` opens CSV or extracts CSV from a ZIP, trims headers, enforces a required column set and normalises names via `COLMAP`.
- Validation: `extract_single_trade_date()` enforces that each file contains exactly one trade date. Bad files raise exceptions and are counted as failures.
- DB flow: `engine()` builds a SQLAlchemy engine from env vars. `sync_folder()` opens a transaction (`eng.begin()`) and for each file:
  - computes MD5 (`md5_of_file`) for logging
  - parses DF, extracts `trade_date`
  - checks `imports_log` via `already_imported()` to skip duplicates
  - writes into a temporary table (`CREATE TEMPORARY TABLE tmp_bhav LIKE nse_equity_bhavcopy_full`), uses `pandas.DataFrame.to_sql(..., method="multi", chunksize=5000)` to bulk load, then runs an `INSERT ... ON DUPLICATE KEY UPDATE` upsert into `nse_equity_bhavcopy_full`

## Important conventions & invariants (discoverable in code)

- Env vars (loaded via python-dotenv at import time): `MYSQL_HOST`, `MYSQL_PORT`, `MYSQL_DB`, `MYSQL_USER`, `MYSQL_PASSWORD`, `BHAV_FOLDER`. Defaults are shown at top of `sync_bhav_gui.py`.
- Database expectations:
  - Table `nse_equity_bhavcopy_full` must exist and have the target columns used by `COLMAP` (trade_date, symbol, series, prev_close, open_price, ...). The upsert uses ON DUPLICATE KEY UPDATE, so the table must have an appropriate unique key (e.g. trade_date+symbol+series) for dedup/upsert semantics to work.
  - Table `imports_log` must exist and have a UNIQUE/PRIMARY key on `trade_date` (used by `log_import()` with ON DUPLICATE KEY UPDATE).
- File formats supported: `.csv` or `.zip` containing a CSV. Only the first CSV inside a ZIP is read.
- Date parsing: pandas with dayfirst=True; input like `10-Oct-2025` is expected. Rows missing `trade_date`, `symbol` or `series` are dropped.
- Numeric cleaning: `deliv_qty` and `deliv_per` are coerced via helper functions that accept `-`, `NA`, `NaN` or empty values.

## Typical developer workflows / commands (Windows PowerShell)

- Install deps (from repo root):

    python -m pip install -r requirements.txt

- Start the GUI and run a sync manually (uses `.env` if present). To change `BHAV_FOLDER` set the environment variable before launching. Example:

    $env:BHAV_FOLDER = 'D:\\MyProjects\\StockScreeer\\bhav_data'; python sync_bhav_gui.py

- Run headless from Python REPL (useful for debugging parsing/upsert):

    python -c "from sync_bhav_gui import sync_folder; sync_folder()"

Notes: `BHAV_FOLDER` is read at module import time (python-dotenv loads `.env` when the module imports). Set the env var or `.env` before running the script if you want a different folder.

## Patterns to follow when editing the code

- Use the provided `engine()` helper to create SQLAlchemy engines (it sets pool_pre_ping and pool_recycle).
- When writing DataFrame to DB, reuse the connection's engine (`conn.engine`) so `df.to_sql(..., con=conn.engine, ...)` is used — this is the pattern used in `upsert_bhav()` to avoid transactional issues.
- When adding parsing logic preserve the existing column mapping `COLMAP` and the contract that each file contains exactly one `trade_date`.

## Examples from the code (copy/paste friendly)

- Column mapping (partial):
  - `"SYMBOL" -> "symbol"`, `"DATE1" -> "trade_date"`, `"CLOSE_PRICE" -> "close_price"` (see `COLMAP` in `sync_bhav_gui.py`).
- MD5 checksum to detect file identity: `md5_of_file(path)` — used for `imports_log.file_checksum`.
- Bulk load then upsert pattern:
  - `CREATE TEMPORARY TABLE tmp_bhav LIKE nse_equity_bhavcopy_full;`
  - `df.to_sql(name="tmp_bhav", con=conn.engine, if_exists="append", method="multi", chunksize=5000)`
  - `INSERT INTO nse_equity_bhavcopy_full ... SELECT ... FROM tmp_bhav ON DUPLICATE KEY UPDATE ...`

## Debugging tips

- If sync fails for a file, stack trace is appended to the GUI log; run `sync_folder(log_cb=print)` from REPL to get the same logs in the console.
- Schema mismatches are the most common runtime issue: verify `nse_equity_bhavcopy_full` columns and unique keys match the upsert SQL and `tmp_bhav` expectations.

## What this file should NOT do (observed constraints)

- There is no automated test harness or CI in the repo. Avoid changing behaviour without manual verification.
- The script assumes MySQL (driver `mysql+pymysql`) and UTF8MB4 charset.

---
If you'd like, I can iterate: add quick schema migration SQL examples, a small headless CLI wrapper, or unit tests for parsing helpers (recommended next steps). Tell me which area you want expanded.
