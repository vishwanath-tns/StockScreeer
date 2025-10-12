import os, zipfile, hashlib, threading, traceback
from datetime import date
from pathlib import Path
import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL
from dotenv import load_dotenv
from tkinter import Tk, Label, Button, StringVar, filedialog, ttk, messagebox

# ------------ Config ------------
load_dotenv()
HOST = os.getenv("MYSQL_HOST", "127.0.0.1")
PORT = int(os.getenv("MYSQL_PORT", "3306"))
DB   = os.getenv("MYSQL_DB", "marketdata")
USER = os.getenv("MYSQL_USER", "root")
PWD  = os.getenv("MYSQL_PASSWORD", "")
BHAV_FOLDER = Path(os.getenv("BHAV_FOLDER", "."))
TABLE = "nse_equity_bhavcopy_full"
LOG_TABLE = "imports_log"

# File patterns to load
VALID_EXTS = (".csv", ".zip")

# ------------ DB Utils ------------
def engine():
    url = URL.create(
        drivername="mysql+pymysql",
        username=USER,
        password=PWD,
        host=HOST,
        port=PORT,
        database=DB,
        query={"charset": "utf8mb4"},
    )
    return create_engine(url, pool_pre_ping=True, pool_recycle=3600)

def already_imported(conn, trade_dt: date) -> bool:
    q = text(f"SELECT 1 FROM {LOG_TABLE} WHERE trade_date = :d LIMIT 1")
    return conn.execute(q, {"d": trade_dt}).first() is not None

def log_import(conn, trade_dt: date, file_name: str, checksum: str, rows: int):
    q = text(f"""
        INSERT INTO {LOG_TABLE}(trade_date, file_name, file_checksum, rows_loaded)
        VALUES(:d, :f, :c, :r)
        ON DUPLICATE KEY UPDATE 
          file_name = VALUES(file_name),
          file_checksum = VALUES(file_checksum),
          rows_loaded = VALUES(rows_loaded),
          loaded_at = CURRENT_TIMESTAMP
    """)
    conn.execute(q, {"d": trade_dt, "f": file_name, "c": checksum, "r": rows})

# ------------ Parsing ------------
COLMAP = {
    "SYMBOL": "symbol",
    "SERIES": "series",
    "DATE1": "trade_date",
    "PREV_CLOSE": "prev_close",
    "OPEN_PRICE": "open_price",
    "HIGH_PRICE": "high_price",
    "LOW_PRICE": "low_price",
    "LAST_PRICE": "last_price",
    "CLOSE_PRICE": "close_price",
    "AVG_PRICE": "avg_price",
    "TTL_TRD_QNTY": "ttl_trd_qnty",
    "TURNOVER_LACS": "turnover_lacs",
    "NO_OF_TRADES": "no_of_trades",
    "DELIV_QTY": "deliv_qty",
    "DELIV_PER": "deliv_per",
}

def md5_of_file(path: Path) -> str:
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()

def read_csv_from_zip(zp: Path) -> pd.DataFrame:
    with zipfile.ZipFile(zp, "r") as zf:
        csv_names = [n for n in zf.namelist() if n.lower().endswith(".csv")]
        if not csv_names:
            raise ValueError(f"No CSV found inside zip: {zp}")
        with zf.open(csv_names[0]) as f:
            return pd.read_csv(f)

def read_any(path: Path) -> pd.DataFrame:
    if path.suffix.lower() == ".zip":
        df = read_csv_from_zip(path)
    else:
        df = pd.read_csv(path)
    # strip headers and normalize
    df.columns = [c.strip() for c in df.columns]
    # assert columns exist
    missing = [c for c in COLMAP.keys() if c not in df.columns]
    if missing:
        raise ValueError(f"Missing columns {missing} in {path.name}")
    df = df[list(COLMAP.keys())].rename(columns=COLMAP)

    # clean strings
    for s in ("symbol", "series"):
        df[s] = df[s].astype(str).str.strip()

    # parse date like '10-Oct-2025'
    df["trade_date"] = pd.to_datetime(
        df["trade_date"].astype(str).str.strip(),
        dayfirst=True, errors="coerce"
    ).dt.date

    # numeric cleanups (DELIV_QTY/DELIV_PER can be blank/NA/'-')
    def to_int_or_null(x):
        if pd.isna(x): return None
        s = str(x).replace(",", "").strip()
        if s in ("", "-", "NA", "NaN"): return None
        try: return int(float(s))
        except: return None

    def to_float_or_null(x):
        if pd.isna(x): return None
        s = str(x).replace(",", "").strip()
        if s in ("", "-", "NA", "NaN"): return None
        try: return float(s)
        except: return None

    if "deliv_qty" in df:  df["deliv_qty"] = df["deliv_qty"].map(to_int_or_null)
    if "deliv_per" in df:  df["deliv_per"] = df["deliv_per"].map(to_float_or_null)

    # Drop bad rows
    df = df.dropna(subset=["trade_date", "symbol", "series"])
    return df

def extract_single_trade_date(df: pd.DataFrame) -> date:
    uniq = pd.Series(df["trade_date"].unique())
    uniq = uniq.dropna()
    if len(uniq) != 1:
        raise ValueError(f"Expected exactly 1 trade_date in file, found: {list(uniq)}")
    return pd.to_datetime(uniq.iloc[0]).date()

# ------------ Upsert ------------
def upsert_bhav(conn, df: pd.DataFrame):
    # Defensive: ensure a clean temporary table in this session
    conn.execute(text("DROP TEMPORARY TABLE IF EXISTS tmp_bhav;"))
    conn.execute(text("CREATE TEMPORARY TABLE tmp_bhav LIKE nse_equity_bhavcopy_full;"))

    # Use the SAME connection so temp table is visible
    df.to_sql(
        name="tmp_bhav",
        con=conn,
        if_exists="append",
        index=False,
        method="multi",
        chunksize=5000,
    )

    upsert_sql = f"""
    INSERT INTO {TABLE} (
      trade_date, symbol, series, prev_close, open_price, high_price, low_price,
      last_price, close_price, avg_price, ttl_trd_qnty, turnover_lacs,
      no_of_trades, deliv_qty, deliv_per
    )
    SELECT trade_date, symbol, series, prev_close, open_price, high_price, low_price,
           last_price, close_price, avg_price, ttl_trd_qnty, turnover_lacs,
           no_of_trades, deliv_qty, deliv_per
    FROM tmp_bhav
    ON DUPLICATE KEY UPDATE
      prev_close   = VALUES(prev_close),
      open_price   = VALUES(open_price),
      high_price   = VALUES(high_price),
      low_price    = VALUES(low_price),
      last_price   = VALUES(last_price),
      close_price  = VALUES(close_price),
      avg_price    = VALUES(avg_price),
      ttl_trd_qnty = VALUES(ttl_trd_qnty),
      turnover_lacs= VALUES(turnover_lacs),
      no_of_trades = VALUES(no_of_trades),
      deliv_qty    = VALUES(deliv_qty),
      deliv_per    = VALUES(deliv_per);
    """
    conn.execute(text(upsert_sql))

    # Clean up explicitly (good hygiene even though session ends per file)
    conn.execute(text("DROP TEMPORARY TABLE IF EXISTS tmp_bhav;"))

# ------------ Scanner ------------
def discover_files(folder: Path):
    for p in folder.glob("*"):
        if p.is_file() and p.suffix.lower() in VALID_EXTS:
            yield p

def sync_folder(progress_cb=None, log_cb=None):
    eng = engine()
    processed = skipped = failed = 0
    files = list(discover_files(BHAV_FOLDER))
    total = len(files)
    if progress_cb: progress_cb(0, total)

    # New DB session per file — avoids lingering temp tables
    for idx, path in enumerate(sorted(files)):
        try:
            checksum = md5_of_file(path)
            df = read_any(path)
            trade_dt = extract_single_trade_date(df)

            with eng.begin() as conn:
                if already_imported(conn, trade_dt):
                    skipped += 1
                    if log_cb: log_cb(f"Skip {path.name}: {trade_dt} already imported")
                else:
                    upsert_bhav(conn, df)
                    log_import(conn, trade_dt, path.name, checksum, len(df))
                    processed += 1
                    if log_cb: log_cb(f"OK   {path.name}: {trade_dt} rows={len(df):,}")
        except Exception as e:
            failed += 1
            if log_cb:
                log_cb(f"FAIL {path.name}: {e}")
                log_cb(traceback.format_exc())
        if progress_cb: progress_cb(idx + 1, total)

    return processed, skipped, failed

# ------------ GUI ------------
class App:
    def __init__(self, root):
        self.root = root
        root.title("NSE Bhav Sync")
        self.status = StringVar(value=f"Folder: {BHAV_FOLDER}")
        Label(root, textvariable=self.status).pack(padx=10, pady=6)

        self.pb = ttk.Progressbar(root, orient="horizontal", mode="determinate", length=400)
        self.pb.pack(padx=10, pady=6)

        self.log = StringVar(value="")
        self.log_label = Label(root, textvariable=self.log, justify="left", anchor="w")
        self.log_label.pack(padx=10, pady=6)

        frm = ttk.Frame(root)
        frm.pack(padx=10, pady=6)
        Button(frm, text="Choose Folder", command=self.choose_folder).grid(row=0, column=0, padx=6)
        Button(frm, text="Sync", command=self.run_sync).grid(row=0, column=1, padx=6)

    def choose_folder(self):
        global BHAV_FOLDER
        folder = filedialog.askdirectory(initialdir=str(BHAV_FOLDER))
        if folder:
            BHAV_FOLDER = Path(folder)
            self.status.set(f"Folder: {BHAV_FOLDER}")

    def set_progress(self, done, total):
        self.pb["maximum"] = max(total, 1)
        self.pb["value"] = done
        self.root.update_idletasks()

    def append_log(self, msg):
        prev = self.log.get()
        new = (prev + "\n" + msg).strip()
        self.log.set("\n".join(new.splitlines()[-15:]))

    def run_sync(self):
        def worker():
            self.append_log("Starting sync …")
            processed, skipped, failed = sync_folder(self.set_progress, self.append_log)
            self.append_log(f"Done. Imported: {processed}, Skipped: {skipped}, Failed: {failed}")
            messagebox.showinfo("NSE Bhav Sync", f"Imported: {processed}\nSkipped: {skipped}\nFailed: {failed}")
        threading.Thread(target=worker, daemon=True).start()

if __name__ == "__main__":
    root = Tk()
    try:
        import ctypes
        ctypes.windll.shcore.SetProcessDpiAwareness(1)  # nicer scaling on Windows
    except Exception:
        pass
    App(root)
    root.mainloop()
