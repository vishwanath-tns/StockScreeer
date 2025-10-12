import os, zipfile, hashlib, threading, traceback
from datetime import date
from pathlib import Path
import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL
from dotenv import load_dotenv
from tkinter import Tk, Label, Button, StringVar, filedialog, ttk, messagebox, Toplevel, Entry, Checkbutton, IntVar
from tkinter.scrolledtext import ScrolledText

# A/D reporting functions (includes new export function)
from reporting_adv_decl import compute_adv_decl, compute_range, plot_adv_decl, export_adv_decl_csv

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
    df.columns = [c.strip() for c in df.columns]
    missing = [c for c in COLMAP.keys() if c not in df.columns]
    if missing:
        raise ValueError(f"Missing columns {missing} in {path.name}")
    df = df[list(COLMAP.keys())].rename(columns=COLMAP)

    for s in ("symbol", "series"):
        df[s] = df[s].astype(str).str.strip()

    df["trade_date"] = pd.to_datetime(
        df["trade_date"].astype(str).str.strip(),
        dayfirst=True, errors="coerce"
    ).dt.date

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

    df = df.dropna(subset=["trade_date", "symbol", "series"])
    return df

def extract_single_trade_date(df: pd.DataFrame) -> date:
    uniq = pd.Series(df["trade_date"].unique()).dropna()
    if len(uniq) != 1:
        raise ValueError(f"Expected exactly 1 trade_date in file, found: {list(uniq)}")
    return pd.to_datetime(uniq.iloc[0]).date()

# ------------ Upsert ------------
def upsert_bhav(conn, df: pd.DataFrame):
    conn.execute(text("DROP TEMPORARY TABLE IF EXISTS tmp_bhav;"))
    conn.execute(text("CREATE TEMPORARY TABLE tmp_bhav LIKE nse_equity_bhavcopy_full;"))

    df.to_sql(
        name="tmp_bhav",
        con=conn,   # same connection so temp table is visible
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
        root.title("NSE Bhav Sync + Reports")
        root.geometry("920x590")

        self.folder_text = StringVar(value=f"Folder: {BHAV_FOLDER}")
        Label(root, textvariable=self.folder_text).pack(padx=10, pady=(10, 4), anchor="w")

        self.pb = ttk.Progressbar(root, orient="horizontal", mode="determinate", length=880)
        self.pb.pack(padx=10, pady=6)

        self.log_box = ScrolledText(root, width=120, height=18, wrap="word")
        self.log_box.pack(padx=10, pady=6, fill="both", expand=True)
        self._append_sync("Ready.")

        btn_frame = ttk.Frame(root)
        btn_frame.pack(padx=10, pady=6, anchor="w")
        Button(btn_frame, text="Choose Folder", command=self.choose_folder).grid(row=0, column=0, padx=6)
        Button(btn_frame, text="Sync", command=self.run_sync).grid(row=0, column=1, padx=6)
        Button(btn_frame, text="Count Days", command=self.count_days).grid(row=0, column=2, padx=6)
        ttk.Separator(btn_frame, orient="vertical").grid(row=0, column=3, padx=12, sticky="ns")

        # Reporting buttons
        Button(btn_frame, text="Compute A/D (Day)", command=self.compute_ad_day_dialog).grid(row=0, column=4, padx=6)
        Button(btn_frame, text="Compute Range", command=self.compute_range_dialog).grid(row=0, column=5, padx=6)
        Button(btn_frame, text="Plot A/D", command=self.plot_ad_dialog).grid(row=0, column=6, padx=6)
        Button(btn_frame, text="Export A/D CSV", command=self.export_ad_dialog).grid(row=0, column=7, padx=6)  # ✅ NEW

    # Thread-safe logging
    def append_log(self, msg: str):
        self.root.after(0, lambda: self._append_sync(msg))

    def _append_sync(self, msg: str):
        self.log_box.configure(state="normal")
        self.log_box.insert("end", msg + "\n")
        self.log_box.see("end")
        content = self.log_box.get("1.0", "end")
        if content.count("\n") > 2000:
            self.log_box.delete("1.0", "200.0")
        self.log_box.configure(state="disabled")

    def set_progress(self, done, total):
        self.root.after(0, lambda: self._set_progress_sync(done, total))

    def _set_progress_sync(self, done, total):
        self.pb["maximum"] = max(total, 1)
        self.pb["value"] = done

    def choose_folder(self):
        global BHAV_FOLDER
        folder = filedialog.askdirectory(initialdir=str(BHAV_FOLDER))
        if folder:
            BHAV_FOLDER = Path(folder)
            self.folder_text.set(f"Folder: {BHAV_FOLDER}")
            self.append_log(f"Folder set to: {BHAV_FOLDER}")

    def run_sync(self):
        def worker():
            self.append_log("Starting sync …")
            processed, skipped, failed = sync_folder(self.set_progress, self.append_log)
            self.append_log(f"Done. Imported: {processed}, Skipped: {skipped}, Failed: {failed}")
            messagebox.showinfo("NSE Bhav Sync", f"Imported: {processed}\nSkipped: {skipped}\nFailed: {failed}")
        threading.Thread(target=worker, daemon=True).start()

    def count_days(self):
        try:
            eng = engine()
            with eng.connect() as conn:
                rows = conn.execute(text(f"SELECT DISTINCT trade_date FROM {TABLE} ORDER BY trade_date")).fetchall()
                days = [r[0] for r in rows]
                n = len(days)
                preview = ""
                if n:
                    preview = f"\nRange: {days[0]} → {days[-1]}"
                    sample = ", ".join(str(d) for d in days[:10])
                    if n > 10:
                        sample += ", …"
                    preview += f"\nSample: {sample}"
                msg = f"Distinct trading days present: {n}{preview}"
                self.append_log(msg)
                messagebox.showinfo("Days Present", msg)
        except Exception as e:
            self.append_log(f"Count Days failed: {e}")
            self.append_log(traceback.format_exc())
            messagebox.showerror("Days Present", f"Failed to count days:\n{e}")

    # ---------- A/D dialogs ----------
    def compute_ad_day_dialog(self):
        win = Toplevel(self.root)
        win.title("Compute A/D (One Day)")
        Label(win, text="Trade Date (YYYY-MM-DD):").grid(row=0, column=0, padx=8, pady=8, sticky="e")
        e_date = Entry(win, width=15); e_date.grid(row=0, column=1, padx=8, pady=8)
        Label(win, text="Force recompute:").grid(row=1, column=0, padx=8, pady=4, sticky="e")
        force_var = IntVar(value=0)
        Checkbutton(win, variable=force_var).grid(row=1, column=1, padx=8, pady=4, sticky="w")

        def run():
            val = e_date.get().strip()
            try:
                y, m, d = map(int, val.split("-"))
                dt = date(y, m, d)
            except Exception:
                messagebox.showerror("Invalid date", "Please enter date as YYYY-MM-DD")
                return
            win.destroy()
            threading.Thread(target=self._compute_ad_day_worker, args=(dt, bool(force_var.get())), daemon=True).start()

        Button(win, text="Compute", command=run).grid(row=2, column=0, columnspan=2, pady=10)

    def _compute_ad_day_worker(self, dt: date, force: bool):
        try:
            self.append_log(f"Computing A/D for {dt} (force={force}) …")
            res = compute_adv_decl(dt, force=force)
            self.append_log(f"A/D {dt}: Advances={res['advances']}, Declines={res['declines']}, Unchanged={res['unchanged']}, Total={res['total']}")
            messagebox.showinfo("Compute A/D", f"{dt}\nAdvances={res['advances']}\nDeclines={res['declines']}\nUnchanged={res['unchanged']}\nTotal={res['total']}")
        except Exception as e:
            self.append_log(f"Compute A/D failed: {e}")
            self.append_log(traceback.format_exc())
            messagebox.showerror("Compute A/D", f"Failed: {e}")

    def compute_range_dialog(self):
        win = Toplevel(self.root)
        win.title("Compute A/D Range")
        Label(win, text="Start (YYYY-MM-DD):").grid(row=0, column=0, padx=8, pady=6, sticky="e")
        e_start = Entry(win, width=15); e_start.grid(row=0, column=1, padx=8, pady=6)
        Label(win, text="End (YYYY-MM-DD):").grid(row=1, column=0, padx=8, pady=6, sticky="e")
        e_end = Entry(win, width=15); e_end.grid(row=1, column=1, padx=8, pady=6)
        Label(win, text="Force recompute:").grid(row=2, column=0, padx=8, pady=6, sticky="e")
        force_var = IntVar(value=0)
        Checkbutton(win, variable=force_var).grid(row=2, column=1, padx=8, pady=6, sticky="w")

        def run():
            try:
                y1, m1, d1 = map(int, e_start.get().strip().split("-"))
                y2, m2, d2 = map(int, e_end.get().strip().split("-"))
                d_start = date(y1, m1, d1); d_end = date(y2, m2, d2)
            except Exception:
                messagebox.showerror("Invalid date", "Use YYYY-MM-DD for both dates.")
                return
            win.destroy()
            threading.Thread(target=self._compute_range_worker, args=(d_start, d_end, bool(force_var.get())), daemon=True).start()

        Button(win, text="Compute Range", command=run).grid(row=3, column=0, columnspan=2, pady=10)

    def _compute_range_worker(self, d_start: date, d_end: date, force: bool):
        try:
            self.append_log(f"Computing A/D from {d_start} to {d_end} (force={force}) …")
            df = compute_range(d_start, d_end, force=force)
            self.append_log(f"Done. Cached {len(df)} days.")
            messagebox.showinfo("Compute Range", f"Computed/Cached: {len(df)} days")
        except Exception as e:
            self.append_log(f"Compute Range failed: {e}")
            self.append_log(traceback.format_exc())
            messagebox.showerror("Compute Range", f"Failed: {e}")

    def plot_ad_dialog(self):
        win = Toplevel(self.root)
        win.title("Plot A/D")
        Label(win, text="Start (YYYY-MM-DD, empty=auto):").grid(row=0, column=0, padx=8, pady=6, sticky="e")
        e_start = Entry(win, width=15); e_start.grid(row=0, column=1, padx=8, pady=6)
        Label(win, text="End (YYYY-MM-DD, empty=auto):").grid(row=1, column=0, padx=8, pady=6, sticky="e")
        e_end = Entry(win, width=15); e_end.grid(row=1, column=1, padx=8, pady=6)

        def run():
            s = e_start.get().strip()
            e = e_end.get().strip()
            d_start = None; d_end = None
            try:
                if s:
                    y1, m1, d1 = map(int, s.split("-"))
                    d_start = date(y1, m1, d1)
                if e:
                    y2, m2, d2 = map(int, e.split("-"))
                    d_end = date(y2, m2, d2)
            except Exception:
                messagebox.showerror("Invalid date", "Use YYYY-MM-DD or leave empty.")
                return
            win.destroy()
            threading.Thread(target=self._plot_worker, args=(d_start, d_end), daemon=True).start()

        Button(win, text="Plot", command=run).grid(row=2, column=0, columnspan=2, pady=10)

    def _plot_worker(self, d_start: date | None, d_end: date | None):
        try:
            self.append_log(f"Plotting A/D … range: {d_start} → {d_end}")
            plot_adv_decl(start=d_start, end=d_end)  # opens Matplotlib window
            self.append_log("Plot complete.")
        except Exception as e:
            self.append_log(f"Plot failed: {e}")
            self.append_log(traceback.format_exc())
            messagebox.showerror("Plot A/D", f"Failed: {e}")

    # ---------- Export A/D CSV ----------
    def export_ad_dialog(self):
        win = Toplevel(self.root)
        win.title("Export A/D CSV")
        Label(win, text="Start (YYYY-MM-DD, empty=auto):").grid(row=0, column=0, padx=8, pady=6, sticky="e")
        e_start = Entry(win, width=15); e_start.grid(row=0, column=1, padx=8, pady=6)
        Label(win, text="End (YYYY-MM-DD, empty=auto):").grid(row=1, column=0, padx=8, pady=6, sticky="e")
        e_end = Entry(win, width=15); e_end.grid(row=1, column=1, padx=8, pady=6)

        def run():
            s = e_start.get().strip()
            e = e_end.get().strip()
            d_start = None; d_end = None
            try:
                if s:
                    y1, m1, d1 = map(int, s.split("-"))
                    d_start = date(y1, m1, d1)
                if e:
                    y2, m2, d2 = map(int, e.split("-"))
                    d_end = date(y2, m2, d2)
            except Exception:
                messagebox.showerror("Invalid date", "Use YYYY-MM-DD or leave empty.")
                return

            # Ask where to save
            save_path = filedialog.asksaveasfilename(
                defaultextension=".csv",
                filetypes=[("CSV files", "*.csv")],
                initialfile="adv_decl.csv",
                title="Save Advance/Decline CSV"
            )
            if not save_path:
                return  # user cancelled
            win.destroy()
            threading.Thread(target=self._export_worker, args=(d_start, d_end, save_path), daemon=True).start()

        Button(win, text="Export CSV", command=run).grid(row=2, column=0, columnspan=2, pady=10)

    def _export_worker(self, d_start: date | None, d_end: date | None, save_path: str):
        try:
            self.append_log(f"Exporting A/D CSV → {save_path} (range: {d_start} → {d_end}) …")
            path = export_adv_decl_csv(save_path, start=d_start, end=d_end)
            self.append_log(f"Export complete: {path}")
            messagebox.showinfo("Export A/D CSV", f"Saved: {path}")
        except Exception as e:
            self.append_log(f"Export failed: {e}")
            self.append_log(traceback.format_exc())
            messagebox.showerror("Export A/D CSV", f"Failed: {e}")

if __name__ == "__main__":
    root = Tk()
    try:
        import ctypes
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass
    App(root)
    root.mainloop()
