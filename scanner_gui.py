"""scanner_gui.py

Simple Tk GUI to run the repository scanners:
- Accumulation scanner (delivery% trend)
- Swing candidates scanner (liquidity/momentum)
- Liquidity baseline compute & recent-scan

The GUI imports scanner modules and runs them in background threads, showing logs.
"""
import threading
import traceback
from datetime import datetime, date
import time
from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import pandas as pd
from sqlalchemy import text

LOG_MAX_LINES = 200


class ScannerGUI:
    def __init__(self, root):
        self.root = root
        root.title("Stock Screener - Scanners")

        nb = ttk.Notebook(root)
        nb.pack(fill="both", expand=True, padx=8, pady=8)

        self.accum_frame = ttk.Frame(nb)
        self.swing_frame = ttk.Frame(nb)
        self.liq_frame = ttk.Frame(nb)
        self.deliv_frame = ttk.Frame(nb)
        self.advdecl_frame = ttk.Frame(nb)
        self.candles_frame = ttk.Frame(nb)
        self.sma_frame = ttk.Frame(nb)
        self.strong_frame = ttk.Frame(nb)
        self.indices_frame = ttk.Frame(nb)
        self.rsi_frame = ttk.Frame(nb)

        nb.add(self.accum_frame, text="Accumulation Scanner")
        nb.add(self.swing_frame, text="Swing Scanner")
        nb.add(self.liq_frame, text="Liquidity Baseline & Scan")
        nb.add(self.deliv_frame, text="Delivery Count")
        nb.add(self.advdecl_frame, text="Adv/Decl Report")
        nb.add(self.candles_frame, text="Candles")
        nb.add(self.sma_frame, text="SMA Trends")
        nb.add(self.strong_frame, text="Strong Uptrend")
        nb.add(self.indices_frame, text="Indices Import")
        nb.add(self.rsi_frame, text="RSI Calculator")

        self._build_accum_tab()
        self._build_swing_tab()
        self._build_liq_tab()
        self._build_deliv_tab()
        self._build_advdecl_tab()
        self._build_candles_tab()
        self._build_sma_tab()
        self._build_strong_tab()
        self._build_indices_tab()
        self._build_rsi_tab()

        # sort state for treeviews
        self._sma_tree_sort_state = {}

        # Log area at bottom
        self.log = tk.Text(root, height=10, wrap="none")
        self.log.pack(fill="both", expand=False, padx=8, pady=(0,8))

    def append_log(self, msg: str):
        # Schedule UI update on the main thread to be thread-safe
        def _append():
            self.log.insert("end", msg + "\n")
            # cap lines
            lines = self.log.get("1.0", "end-1c").splitlines()
            if len(lines) > LOG_MAX_LINES:
                new = "\n".join(lines[-LOG_MAX_LINES:])
                self.log.delete("1.0", "end")
                self.log.insert("1.0", new)
            self.log.see("end")

        try:
            self.root.after(0, _append)
        except Exception:
            # fallback if root not available
            _append()

    # -------- Accumulation tab --------
    def _build_accum_tab(self):
        f = self.accum_frame
        ttk.Label(f, text="Date range (YYYY-MM-DD)").grid(row=0, column=0, sticky="w")
        self.acc_start = tk.StringVar(value="2025-08-01")
        self.acc_end = tk.StringVar(value="2025-10-10")
        ttk.Entry(f, textvariable=self.acc_start, width=12).grid(row=0, column=1)
        ttk.Entry(f, textvariable=self.acc_end, width=12).grid(row=0, column=2)

        ttk.Label(f, text="Series").grid(row=1, column=0, sticky="w")
        self.acc_series = tk.StringVar(value="EQ")
        ttk.Entry(f, textvariable=self.acc_series, width=8).grid(row=1, column=1)

        ttk.Label(f, text="Min days").grid(row=2, column=0, sticky="w")
        self.acc_min_days = tk.IntVar(value=15)
        ttk.Entry(f, textvariable=self.acc_min_days, width=8).grid(row=2, column=1)

        ttk.Label(f, text="Min slope (30d)").grid(row=2, column=2, sticky="w")
        self.acc_min_slope = tk.DoubleVar(value=0.5)
        ttk.Entry(f, textvariable=self.acc_min_slope, width=8).grid(row=2, column=3)

        ttk.Label(f, text="High thresh %").grid(row=3, column=0, sticky="w")
        self.acc_high_thresh = tk.DoubleVar(value=40.0)
        ttk.Entry(f, textvariable=self.acc_high_thresh, width=8).grid(row=3, column=1)

        ttk.Label(f, text="Plot top N").grid(row=3, column=2, sticky="w")
        self.acc_plot_top = tk.IntVar(value=0)
        ttk.Entry(f, textvariable=self.acc_plot_top, width=8).grid(row=3, column=3)

        ttk.Label(f, text="CSV out (optional)").grid(row=4, column=0, sticky="w")
        self.acc_out = tk.StringVar(value="")
        ttk.Entry(f, textvariable=self.acc_out, width=30).grid(row=4, column=1, columnspan=2)
        ttk.Button(f, text="Browse", command=lambda: self._browse(self.acc_out)).grid(row=4, column=3)

        ttk.Button(f, text="Run Accumulation Scan", command=self.run_accumulation).grid(row=5, column=0, pady=6)

    def run_accumulation(self):
        import scan_accumulation_by_delivery as scanner

        def worker():
            try:
                self.append_log("Starting accumulation scan...")
                start = self.acc_start.get(); end = self.acc_end.get()
                series = self.acc_series.get() or None
                res = scanner.scan(start=parse_date(start), end=parse_date(end), series=series,
                                   min_days=self.acc_min_days.get(), min_slope_30d=self.acc_min_slope.get(),
                                   high_thresh=self.acc_high_thresh.get(), roll_window=7)
                self.append_log(f"Found {len(res)} candidates")
                out = self.acc_out.get().strip()
                if out:
                    scanner.save_csv(res, out)
                    self.append_log(f"Wrote CSV: {out}")
                top = self.acc_plot_top.get()
                if top and res:
                    scanner.plot_top(res, parse_date(start), parse_date(end), top_n=top)
                    self.append_log(f"Saved plots for top {top} candidates")
            except Exception as e:
                self.append_log(f"Error: {e}")
                self.append_log(traceback.format_exc())

        threading.Thread(target=worker, daemon=True).start()

    # -------- Swing tab --------
    def _build_swing_tab(self):
        f = self.swing_frame
        ttk.Label(f, text="Date range (YYYY-MM-DD)").grid(row=0, column=0, sticky="w")
        self.swing_start = tk.StringVar(value="2025-08-01")
        self.swing_end = tk.StringVar(value="2025-10-10")
        ttk.Entry(f, textvariable=self.swing_start, width=12).grid(row=0, column=1)
        ttk.Entry(f, textvariable=self.swing_end, width=12).grid(row=0, column=2)

        ttk.Label(f, text="Series").grid(row=1, column=0, sticky="w")
        self.swing_series = tk.StringVar(value="EQ")
        ttk.Entry(f, textvariable=self.swing_series, width=8).grid(row=1, column=1)

        ttk.Label(f, text="Min turnover (lacs)").grid(row=2, column=0, sticky="w")
        self.swing_min_turn = tk.DoubleVar(value=5.0)
        ttk.Entry(f, textvariable=self.swing_min_turn, width=8).grid(row=2, column=1)

        ttk.Label(f, text="Min qty").grid(row=2, column=2, sticky="w")
        self.swing_min_qty = tk.IntVar(value=10000)
        ttk.Entry(f, textvariable=self.swing_min_qty, width=10).grid(row=2, column=3)

        ttk.Label(f, text="Min vol").grid(row=3, column=0, sticky="w")
        self.swing_min_vol = tk.DoubleVar(value=0.005)
        ttk.Entry(f, textvariable=self.swing_min_vol, width=8).grid(row=3, column=1)

        ttk.Label(f, text="Max vol").grid(row=3, column=2, sticky="w")
        self.swing_max_vol = tk.DoubleVar(value=0.06)
        ttk.Entry(f, textvariable=self.swing_max_vol, width=8).grid(row=3, column=3)

        self.swing_momentum = tk.BooleanVar(value=False)
        ttk.Checkbutton(f, text="Require last close > SMA20", variable=self.swing_momentum).grid(row=4, column=0, columnspan=2, sticky="w")

        ttk.Label(f, text="CSV out").grid(row=5, column=0, sticky="w")
        self.swing_out = tk.StringVar(value="")
        ttk.Entry(f, textvariable=self.swing_out, width=30).grid(row=5, column=1, columnspan=2)
        ttk.Button(f, text="Browse", command=lambda: self._browse(self.swing_out)).grid(row=5, column=3)

        ttk.Button(f, text="Run Swing Scan", command=self.run_swing).grid(row=6, column=0, pady=6)

    def run_swing(self):
        import scan_swing_candidates as scanner

        def worker():
            try:
                self.append_log("Starting swing scan...")
                start = self.swing_start.get(); end = self.swing_end.get()
                res = scanner.scan(start=parse_date(start), end=parse_date(end), series=self.swing_series.get() or None,
                                   min_turnover_lacs=self.swing_min_turn.get(), min_qty=self.swing_min_qty.get(),
                                   min_vol=self.swing_min_vol.get(), max_vol=self.swing_max_vol.get(), require_momentum=self.swing_momentum.get())
                self.append_log(f"Found {len(res)} swing candidates")
                out = self.swing_out.get().strip()
                if out:
                    scanner.save_csv(res, out)
                    self.append_log(f"Wrote CSV: {out}")
            except Exception as e:
                self.append_log(f"Error: {e}")
                self.append_log(traceback.format_exc())

        threading.Thread(target=worker, daemon=True).start()

    # -------- Liquidity baseline & scan tab --------
    def _build_liq_tab(self):
        f = self.liq_frame
        ttk.Label(f, text="Baseline range (YYYY-MM-DD)").grid(row=0, column=0, sticky="w")
        self.liq_base_start = tk.StringVar(value="2025-01-01")
        self.liq_base_end = tk.StringVar(value="2025-06-30")
        ttk.Entry(f, textvariable=self.liq_base_start, width=12).grid(row=0, column=1)
        ttk.Entry(f, textvariable=self.liq_base_end, width=12).grid(row=0, column=2)

        self.liq_update_baseline = tk.BooleanVar(value=False)
        ttk.Checkbutton(f, text="Recompute baseline (update symbol_liq_stats)", variable=self.liq_update_baseline).grid(row=1, column=0, columnspan=3, sticky="w")

        ttk.Label(f, text="Recent range (YYYY-MM-DD)").grid(row=2, column=0, sticky="w")
        self.liq_recent_start = tk.StringVar(value="2025-08-01")
        self.liq_recent_end = tk.StringVar(value="2025-10-10")
        ttk.Entry(f, textvariable=self.liq_recent_start, width=12).grid(row=2, column=1)
        ttk.Entry(f, textvariable=self.liq_recent_end, width=12).grid(row=2, column=2)

        ttk.Label(f, text="Qty multiplier").grid(row=3, column=0, sticky="w")
        self.liq_qty_mult = tk.DoubleVar(value=3.0)
        ttk.Entry(f, textvariable=self.liq_qty_mult, width=8).grid(row=3, column=1)

        ttk.Label(f, text="Turnover multiplier").grid(row=3, column=2, sticky="w")
        self.liq_turn_mult = tk.DoubleVar(value=3.0)
        ttk.Entry(f, textvariable=self.liq_turn_mult, width=8).grid(row=3, column=3)

        self.liq_compare_latest = tk.BooleanVar(value=False)
        ttk.Checkbutton(f, text="Compare latest single-day vs baseline", variable=self.liq_compare_latest).grid(row=4, column=0, columnspan=3, sticky="w")

        ttk.Label(f, text="CSV out").grid(row=4, column=0, sticky="w")
        self.liq_out = tk.StringVar(value="")
        ttk.Entry(f, textvariable=self.liq_out, width=30).grid(row=4, column=1, columnspan=2)
        ttk.Button(f, text="Browse", command=lambda: self._browse(self.liq_out)).grid(row=4, column=3)

        ttk.Button(f, text="Run Liquidity Baseline/Scan", command=self.run_liquidity).grid(row=5, column=0, pady=6)

    # -------- Delivery Count tab --------
    def _build_deliv_tab(self):
        f = self.deliv_frame
        ttk.Label(f, text="Date range (YYYY-MM-DD)").grid(row=0, column=0, sticky="w")
        self.deliv_start = tk.StringVar(value="2025-08-01")
        self.deliv_end = tk.StringVar(value="2025-10-10")
        ttk.Entry(f, textvariable=self.deliv_start, width=12).grid(row=0, column=1)
        ttk.Entry(f, textvariable=self.deliv_end, width=12).grid(row=0, column=2)

        ttk.Label(f, text="Series").grid(row=1, column=0, sticky="w")
        self.deliv_series = tk.StringVar(value="ALL")
        # combobox will be populated from DB; start with ALL
        self.deliv_series_cb = ttk.Combobox(f, textvariable=self.deliv_series, values=["ALL"], width=8, state="readonly")
        self.deliv_series_cb.grid(row=1, column=1)

        # load distinct series from the DB in a background thread and update combobox
        def _load_series():
            try:
                import scan_delivery_count as sdc
                from sqlalchemy import text
                eng = sdc.engine()
                with eng.connect() as conn:
                    rows = conn.execute(text("SELECT DISTINCT series FROM nse_equity_bhavcopy_full WHERE series IS NOT NULL ORDER BY series"))
                    vals = [r[0] for r in rows if r[0]]
                # ensure ALL is first
                vals = ["ALL"] + [v for v in vals if v != "ALL"]
                def _set():
                    try:
                        self.deliv_series_cb["values"] = vals
                        self.deliv_series.set("ALL")
                    except Exception:
                        pass
                self.root.after(0, _set)
            except Exception as e:
                # if DB unavailable, leave default ALL and log
                self.append_log(f"Could not load series list: {e}")

        threading.Thread(target=_load_series, daemon=True).start()

        ttk.Label(f, text="Delivery % threshold").grid(row=2, column=0, sticky="w")
        self.deliv_thresh = tk.DoubleVar(value=20.0)
        ttk.Entry(f, textvariable=self.deliv_thresh, width=8).grid(row=2, column=1)

        ttk.Button(f, text="Run Delivery Count", command=self.run_delivery_count).grid(row=3, column=0, pady=6)

        # Results treeview inside a frame with scrollbars so it expands with the window
        cols = ("symbol", "series", "days_over", "total_days", "pct")
        tree_frame = ttk.Frame(f)
        tree_frame.grid(row=4, column=0, columnspan=4, pady=6, sticky="nsew")
        # allow the tree area to expand when the parent resizes
        f.grid_rowconfigure(4, weight=1)
        f.grid_columnconfigure(0, weight=1)

        self.deliv_tree = ttk.Treeview(tree_frame, columns=cols, show="headings", height=12)
        for c in cols:
            self.deliv_tree.heading(c, text=c)
            # allow columns to stretch
            self.deliv_tree.column(c, width=100, anchor="w")

        # scrollbars
        vscroll = ttk.Scrollbar(tree_frame, orient="vertical", command=self.deliv_tree.yview)
        hscroll = ttk.Scrollbar(tree_frame, orient="horizontal", command=self.deliv_tree.xview)
        self.deliv_tree.configure(yscrollcommand=vscroll.set, xscrollcommand=hscroll.set)

        # layout inside the tree_frame
        tree_frame.grid_rowconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)
        self.deliv_tree.grid(row=0, column=0, sticky="nsew")
        vscroll.grid(row=0, column=1, sticky="ns")
        hscroll.grid(row=1, column=0, sticky="ew")

        # Auto-resize columns proportionally when the frame resizes
        def _on_treeframe_config(event):
            try:
                total_w = event.width
                # distribute width equally across columns
                col_w = max(50, int((total_w - 4) / max(1, len(cols))))
                for c in cols:
                    self.deliv_tree.column(c, width=col_w)
            except Exception:
                pass

        tree_frame.bind("<Configure>", _on_treeframe_config)

        ttk.Label(f, text="CSV out").grid(row=5, column=0, sticky="w")
        self.deliv_out = tk.StringVar(value="")
        ttk.Entry(f, textvariable=self.deliv_out, width=30).grid(row=5, column=1, columnspan=2)
        ttk.Button(f, text="Browse", command=lambda: self._browse(self.deliv_out)).grid(row=5, column=3)

    # -------- Adv/Decl Report tab --------
    def _build_advdecl_tab(self):
        f = self.advdecl_frame
        ttk.Label(f, text="Date range (YYYY-MM-DD)").grid(row=0, column=0, sticky="w")
        self.ad_start = tk.StringVar(value="2025-08-01")
        self.ad_end = tk.StringVar(value="2025-10-10")
        ttk.Entry(f, textvariable=self.ad_start, width=12).grid(row=0, column=1)
        ttk.Entry(f, textvariable=self.ad_end, width=12).grid(row=0, column=2)

        ttk.Label(f, text="Series").grid(row=1, column=0, sticky="w")
        self.ad_series = tk.StringVar(value="ALL")
        self.ad_series_cb = ttk.Combobox(f, textvariable=self.ad_series, values=["ALL"], width=12, state="readonly")
        self.ad_series_cb.grid(row=1, column=1)

        # load distinct series from DB in background and set combobox values
        def _load_ad_series():
            try:
                import reporting_adv_decl as rad
                from sqlalchemy import text
                eng = rad.engine()
                with eng.connect() as conn:
                    rows = conn.execute(text("SELECT DISTINCT series FROM nse_equity_bhavcopy_full WHERE series IS NOT NULL ORDER BY series"))
                    vals = [r[0] for r in rows if r[0]]
                vals = ["ALL"] + [v for v in vals if v != "ALL"]
                def _set():
                    try:
                        self.ad_series_cb["values"] = vals
                        self.ad_series.set("ALL")
                    except Exception:
                        pass
                self.root.after(0, _set)
            except Exception as e:
                self.append_log(f"Could not load Adv/Decl series list: {e}")

        threading.Thread(target=_load_ad_series, daemon=True).start()

        ttk.Label(f, text="Report type").grid(row=2, column=0, sticky="w")
        self.ad_report_type = tk.StringVar(value="counts")
        self.ad_report_cb = ttk.Combobox(f, textvariable=self.ad_report_type, values=["counts", "ratio", "both_ratios"], width=12, state="readonly")
        self.ad_report_cb.grid(row=2, column=1)

        ttk.Label(f, text="Save (optional)").grid(row=3, column=0, sticky="w")
        self.ad_out = tk.StringVar(value="")
        ttk.Entry(f, textvariable=self.ad_out, width=30).grid(row=3, column=1, columnspan=2)
        ttk.Button(f, text="Browse", command=lambda: self._browse(self.ad_out)).grid(row=3, column=3)

        self.ad_run_btn = ttk.Button(f, text="Show Report", command=self.run_adv_decl_report)
        self.ad_run_btn.grid(row=4, column=0, pady=6)

    # -------- Indices import tab --------
    def _build_indices_tab(self):
        f = self.indices_frame
        ttk.Label(f, text="Indices CSV folder").grid(row=0, column=0, sticky="w")
        self.idx_folder = tk.StringVar(value="")
        ttk.Entry(f, textvariable=self.idx_folder, width=50).grid(row=0, column=1, columnspan=2, sticky="w")
        ttk.Button(f, text="Browse", command=lambda: self._browse(self.idx_folder, folder=True)).grid(row=0, column=3)

        self.idx_combine = tk.BooleanVar(value=True)
        ttk.Checkbutton(f, text="Combine files before upsert (dedupe across files)", variable=self.idx_combine).grid(row=1, column=0, columnspan=3, sticky="w")

        self.idx_recurse = tk.BooleanVar(value=False)
        ttk.Checkbutton(f, text="Recurse subfolders", variable=self.idx_recurse).grid(row=2, column=0, columnspan=3, sticky="w")

        ttk.Label(f, text="Target table").grid(row=3, column=0, sticky="w")
        self.idx_table = tk.StringVar(value="indices_daily")
        ttk.Entry(f, textvariable=self.idx_table, width=20).grid(row=3, column=1, sticky="w")

        ttk.Button(f, text="Import Indices", command=self.run_import_indices).grid(row=4, column=0, pady=8)
        ttk.Label(f, text="BHAV Start (YYYY-MM-DD)").grid(row=4, column=1, sticky="e")
        self.bhav_start = tk.StringVar(value="2025-01-01")
        ttk.Entry(f, textvariable=self.bhav_start, width=12).grid(row=4, column=2, sticky="w")
        ttk.Label(f, text="BHAV End").grid(row=4, column=3, sticky="e")
        self.bhav_end = tk.StringVar(value=datetime.today().strftime('%Y-%m-%d'))
        ttk.Entry(f, textvariable=self.bhav_end, width=12).grid(row=4, column=4, sticky="w")

        # Relative Strength quick-run controls
        ttk.Label(f, text="RS: Index").grid(row=4, column=1, sticky="e")
        self.rs_index = tk.StringVar(value="NIFTY 50")
        ttk.Entry(f, textvariable=self.rs_index, width=18).grid(row=4, column=2, sticky="w")
        ttk.Label(f, text="As-of").grid(row=5, column=0, sticky="w")
        self.rs_asof = tk.StringVar(value=datetime.today().strftime('%Y-%m-%d'))
        ttk.Entry(f, textvariable=self.rs_asof, width=12).grid(row=5, column=1, sticky="w")
        ttk.Label(f, text="Lookback days").grid(row=5, column=2, sticky="w")
        self.rs_lookback = tk.IntVar(value=90)
        ttk.Entry(f, textvariable=self.rs_lookback, width=8).grid(row=5, column=3, sticky="w")
        ttk.Label(f, text="Limit (test)").grid(row=6, column=0, sticky="w")
        self.rs_limit = tk.IntVar(value=0)
        ttk.Entry(f, textvariable=self.rs_limit, width=8).grid(row=6, column=1, sticky="w")
        ttk.Button(f, text="Run RS Scan", command=self.run_rs_scan).grid(row=6, column=2, pady=6)
        # BHAV aggregation buttons
        ttk.Button(f, text="Aggregate BHAV (weekly)", command=lambda: self.run_aggregate_bhav('weekly')).grid(row=7, column=0, pady=6)
        ttk.Button(f, text="Aggregate BHAV (monthly)", command=lambda: self.run_aggregate_bhav('monthly')).grid(row=7, column=1, pady=6)

        # Results text area
        self.idx_results = tk.Text(f, height=10, wrap="none")
        self.idx_results.grid(row=5, column=0, columnspan=4, sticky="nsew")
        f.grid_rowconfigure(5, weight=1)
        f.grid_columnconfigure(1, weight=1)

    def _build_rsi_tab(self):
        f = self.rsi_frame
        ttk.Label(f, text="RSI period").grid(row=0, column=0, sticky="w")
        self.rsi_period = tk.IntVar(value=9)
        ttk.Entry(f, textvariable=self.rsi_period, width=6).grid(row=0, column=1, sticky="w")

        ttk.Label(f, text="Frequencies").grid(row=0, column=2, sticky="w")
        self.rsi_daily = tk.BooleanVar(value=True)
        self.rsi_weekly = tk.BooleanVar(value=True)
        self.rsi_monthly = tk.BooleanVar(value=True)
        ttk.Checkbutton(f, text="Daily", variable=self.rsi_daily).grid(row=0, column=3, sticky="w")
        ttk.Checkbutton(f, text="Weekly", variable=self.rsi_weekly).grid(row=0, column=4, sticky="w")
        ttk.Checkbutton(f, text="Monthly", variable=self.rsi_monthly).grid(row=0, column=5, sticky="w")

        ttk.Label(f, text="Workers").grid(row=1, column=0, sticky="w")
        self.rsi_workers = tk.IntVar(value=4)
        ttk.Entry(f, textvariable=self.rsi_workers, width=6).grid(row=1, column=1, sticky="w")

        ttk.Label(f, text="Start (YYYY-MM-DD)").grid(row=2, column=0, sticky="w")
        self.rsi_start = tk.StringVar(value="2025-01-01")
        ttk.Entry(f, textvariable=self.rsi_start, width=12).grid(row=2, column=1, sticky="w")

        ttk.Label(f, text="End (YYYY-MM-DD)").grid(row=2, column=2, sticky="w")
        self.rsi_end = tk.StringVar(value=datetime.today().strftime('%Y-%m-%d'))
        ttk.Entry(f, textvariable=self.rsi_end, width=12).grid(row=2, column=3, sticky="w")

        ttk.Button(f, text="Run RSI", command=self.run_rsi_calc).grid(row=3, column=0, pady=8)
        # Cancel and percent
        self.rsi_cancel_token = {'cancel': False}
        ttk.Button(f, text="Cancel RSI", command=lambda: self._cancel_rsi()).grid(row=3, column=1, pady=8)
        self.rsi_percent_lbl = ttk.Label(f, text="0%")
        self.rsi_percent_lbl.grid(row=3, column=2, sticky='w')

        # progress bar and results box
        self.rsi_progress = ttk.Progressbar(f, orient='horizontal', mode='determinate', length=400)
        self.rsi_progress.grid(row=4, column=0, columnspan=6, pady=(4,8), sticky='we')
        self.rsi_results = tk.Text(f, height=12, wrap='none')
        self.rsi_results.grid(row=5, column=0, columnspan=6, sticky='nsew')
        f.grid_rowconfigure(5, weight=1)
        f.grid_columnconfigure(5, weight=1)

        # RSI Cross scanner controls (80/20)
        ttk.Separator(f, orient='horizontal').grid(row=6, column=0, columnspan=6, sticky='ew', pady=6)
        ttk.Label(f, text='RSI Cross Scanner (80/20)').grid(row=7, column=0, sticky='w')
        ttk.Button(f, text='Run Incremental Cross Scan', command=self.run_rsi_cross_incremental).grid(row=7, column=1)
        ttk.Button(f, text='Run Full Cross Scan', command=self.run_rsi_cross_full).grid(row=7, column=2)
        ttk.Button(f, text='Cancel Cross Scan', command=self._cancel_rsi).grid(row=7, column=3)

        # reporting buttons
        ttk.Button(f, text='Latest Day (80_up)', command=lambda: self.show_latest_cross('80_up')).grid(row=8, column=0)
        ttk.Button(f, text='Last Week (80_up)', command=lambda: self.show_range_cross(days=7, cross_type='80_up')).grid(row=8, column=1)
        ttk.Button(f, text='Last Month (80_up)', command=lambda: self.show_range_cross(days=30, cross_type='80_up')).grid(row=8, column=2)
        # count crosses button
        ttk.Button(f, text='Count Crosses (window)', command=self.count_crosses_action).grid(row=8, column=3, padx=6)

        # quick filters: window days and top-N
        ttk.Label(f, text='Window days').grid(row=8, column=3, sticky='e')
        self.cross_window_days = tk.IntVar(value=365)
        ttk.Entry(f, textvariable=self.cross_window_days, width=6).grid(row=8, column=4, sticky='w')
        ttk.Label(f, text='Top N').grid(row=8, column=5, sticky='e')
        self.cross_top_n = tk.IntVar(value=0)
        ttk.Entry(f, textvariable=self.cross_top_n, width=6).grid(row=8, column=6, sticky='w')
        ttk.Button(f, text='Stocks above window highs', command=self.run_stocks_above_window).grid(row=8, column=7, padx=6)
        ttk.Button(f, text='Export CSV', command=self.export_cross_csv).grid(row=8, column=8, padx=6)

        # Treeview for cross report results (added 'diff' for breakout strength)
        cols = ("symbol", "trade_date", "period", "cross_type", "prev_rsi", "curr_rsi", "high", "created_at", "diff")
        tree_frame = ttk.Frame(f)
        tree_frame.grid(row=9, column=0, columnspan=6, sticky="nsew", pady=(6,0))
        f.grid_rowconfigure(9, weight=1)
        f.grid_columnconfigure(5, weight=1)

        self.cross_tree = ttk.Treeview(tree_frame, columns=cols, show="headings", height=12)
        for c in cols:
            self.cross_tree.heading(c, text=c, command=lambda _col=c: self._cross_tree_sort(_col))
            self.cross_tree.column(c, width=100, anchor="w")

        # double-click to open detail chart
        self.cross_tree.bind("<Double-1>", self._on_cross_row_double_click)

        vscroll = ttk.Scrollbar(tree_frame, orient="vertical", command=self.cross_tree.yview)
        hscroll = ttk.Scrollbar(tree_frame, orient="horizontal", command=self.cross_tree.xview)
        self.cross_tree.configure(yscrollcommand=vscroll.set, xscrollcommand=hscroll.set)
        tree_frame.grid_rowconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)
        self.cross_tree.grid(row=0, column=0, sticky="nsew")
        vscroll.grid(row=0, column=1, sticky="ns")
        hscroll.grid(row=1, column=0, sticky="ew")

    def run_rsi_calc(self):
        import rsi_calculator as rc

        def worker():
            try:
                period = int(self.rsi_period.get())
                freqs = []
                if self.rsi_daily.get(): freqs.append('daily')
                if self.rsi_weekly.get(): freqs.append('weekly')
                if self.rsi_monthly.get(): freqs.append('monthly')
                workers = max(1, int(self.rsi_workers.get()))
                start = self.rsi_start.get().strip() or None
                end = self.rsi_end.get().strip() or None

                eng = None
                try:
                    from import_nifty_index import build_engine
                    eng = build_engine()
                except Exception:
                    try:
                        eng = rc._ensure_engine()
                    except Exception:
                        eng = None

                if not eng:
                    self.append_log('No DB engine available for RSI compute; aborting')
                    return

                # progress callback
                total_holder = {'total': 0}

                def _progress(current, total, message):
                    try:
                        # set progress maximum once
                        if total_holder['total'] != total and total > 0:
                            total_holder['total'] = total
                            def _set_max():
                                try:
                                    self.rsi_progress['maximum'] = total
                                except Exception:
                                    pass
                            self.root.after(0, _set_max)

                        def _update():
                            try:
                                self.append_log(f"[RSI] {message}")
                                # update progressbar value
                                if total > 0:
                                    try:
                                        self.rsi_progress['value'] = current
                                        pct = int((current/total)*100)
                                        self.rsi_percent_lbl['text'] = f"{pct}%"
                                    except Exception:
                                        pass
                                # show message in results box
                                self.rsi_results.delete('1.0', 'end')
                                self.rsi_results.insert('end', f"{message}\nProcessed {current}/{total}\n")
                            except Exception:
                                pass
                        self.root.after(0, _update)
                    except Exception:
                        pass

                self.append_log(f"Starting RSI compute period={period} freqs={freqs} workers={workers} start={start} end={end}")
                # reset cancel token
                self.rsi_cancel_token['cancel'] = False
                rc.run_rsi(eng, period=period, freqs=freqs, workers=workers, progress_cb=_progress, start=start, end=end, cancel_token=self.rsi_cancel_token)
                self.append_log('RSI compute finished')
                def _done():
                    try:
                        self.rsi_results.insert('end', 'RSI compute finished\n')
                        self.rsi_progress['value'] = self.rsi_progress['maximum']
                        self.rsi_percent_lbl['text'] = '100%'
                    except Exception:
                        pass
                self.root.after(0, _done)
            except Exception as e:
                self.append_log(f"RSI compute error: {e}")
                self.append_log(traceback.format_exc())

        threading.Thread(target=worker, daemon=True).start()

    # -------- RSI cross scanner actions --------
    def run_rsi_cross_incremental(self):
        import rsi_cross_scanner as rcs

        def worker():
            try:
                eng = rcs._ensure_engine()
                period = int(self.rsi_period.get())
                as_of = self.rsi_end.get().strip() or None
                lookback = 30
                # reset cancel token
                self.rsi_cancel_token['cancel'] = False

                def _progress(c, t, m):
                    self.append_log(f"[Cross] {m}")
                    def _u():
                        try:
                            self.rsi_results.delete('1.0', 'end')
                            self.rsi_results.insert('end', f"{m}\n{c}/{t}\n")
                            if t > 0:
                                pct = int((c / t) * 100)
                                self.rsi_percent_lbl['text'] = f"{pct}%"
                        except Exception:
                            pass
                    self.root.after(0, _u)

                rcs.scan_incremental_and_upsert(eng, period=period, as_of=as_of, lookback_days=lookback, progress_cb=_progress, limit=0)
                self.append_log('[Cross] Incremental scan finished')
            except Exception as e:
                self.append_log(f"Cross scan error: {e}")
                self.append_log(traceback.format_exc())

        threading.Thread(target=worker, daemon=True).start()

    def run_rsi_cross_full(self):
        import rsi_cross_scanner as rcs

        def worker():
            try:
                eng = rcs._ensure_engine()
                period = int(self.rsi_period.get())
                as_of = self.rsi_end.get().strip() or None
                lookback = 365
                def _progress(c, t, m):
                    self.append_log(f"[Cross] {m}")
                    def _u():
                        try:
                            self.rsi_results.delete('1.0', 'end')
                            self.rsi_results.insert('end', f"{m}\n{c}/{t}\n")
                            if t > 0:
                                pct = int((c / t) * 100)
                                self.rsi_percent_lbl['text'] = f"{pct}%"
                        except Exception:
                            pass
                    self.root.after(0, _u)

                rcs.scan_and_upsert(eng, period=period, as_of=as_of, lookback_days=lookback, progress_cb=_progress, limit=0)
                self.append_log('[Cross] Full scan finished')
            except Exception as e:
                self.append_log(f"Cross scan error: {e}")
                self.append_log(traceback.format_exc())

        threading.Thread(target=worker, daemon=True).start()

    def count_crosses_action(self):
        """Handler to count RSI cross events per symbol in the configured window and show results."""
        import rsi_cross_scanner as rcs

        def worker():
            try:
                eng = rcs._ensure_engine()
                days = int(self.cross_window_days.get() or 365)
                period = int(self.rsi_period.get())
                as_of = self.rsi_end.get().strip() or None
                # call helper
                df = rcs.count_crosses_in_window(eng, as_of=as_of, days=days, period=period, cross_type=None)

                # show in text area
                def _show_text():
                    try:
                        self.rsi_results.delete('1.0', 'end')
                        if df.empty:
                            self.rsi_results.insert('end', 'No cross counts found')
                        else:
                            self.rsi_results.insert('end', df.to_string(index=False))
                    except Exception:
                        pass
                self.root.after(0, _show_text)

                # populate cross_tree with counts: map symbol->count into tree, put count into 'diff' column
                def _populate_tree():
                    try:
                        for i in self.cross_tree.get_children():
                            self.cross_tree.delete(i)
                        if df.empty:
                            return
                        for _, r in df.iterrows():
                            vals = (
                                r.get('symbol'),
                                pd.to_datetime(r.get('last_cross_date')).strftime('%Y-%m-%d') if pd.notna(r.get('last_cross_date')) else '',
                                '',
                                '',
                                '',
                                '',
                                None,
                                '',
                                int(r.get('cross_count')) if pd.notna(r.get('cross_count')) else 0,
                            )
                            self.cross_tree.insert('', 'end', values=vals)
                    except Exception as e:
                        self.append_log(f"Error populating tree for counts: {e}")
                self.root.after(0, _populate_tree)
            except Exception as e:
                self.append_log(f"Error counting crosses: {e}")
                self.append_log(traceback.format_exc())

        threading.Thread(target=worker, daemon=True).start()

    def show_latest_cross(self, cross_type='80_up'):
        import rsi_cross_scanner as rcs
        try:
            eng = rcs._ensure_engine()
            d = rcs.latest_cross_date(eng, cross_type=cross_type)
            if d is None:
                messagebox.showinfo('No data', 'No cross events found')
                return
            df = rcs.get_crosses_on_date(eng, d.isoformat(), cross_type=cross_type)
            # populate treeview
            try:
                for i in self.cross_tree.get_children():
                    self.cross_tree.delete(i)
                if df.empty:
                    return
                # ensure expected columns present
                for _, r in df.iterrows():
                    vals = (
                        r.get('symbol'),
                        pd.to_datetime(r.get('trade_date')).strftime('%Y-%m-%d') if pd.notna(r.get('trade_date')) else '',
                        int(r.get('period')) if pd.notna(r.get('period')) else None,
                        r.get('cross_type'),
                        float(r.get('prev_rsi')) if pd.notna(r.get('prev_rsi')) else None,
                        float(r.get('curr_rsi')) if pd.notna(r.get('curr_rsi')) else None,
                        float(r.get('high')) if pd.notna(r.get('high')) else None,
                        pd.to_datetime(r.get('created_at')).strftime('%Y-%m-%d %H:%M:%S') if pd.notna(r.get('created_at')) else ''
                    )
                    self.cross_tree.insert('', 'end', values=vals)
            except Exception:
                # fallback to text box on failure
                self.rsi_results.delete('1.0', 'end')
                self.rsi_results.insert('end', df.to_string(index=False))
        except Exception as e:
            self.append_log(f"Error showing latest cross: {e}")
            self.append_log(traceback.format_exc())

    def show_range_cross(self, days=7, cross_type='80_up'):
        import rsi_cross_scanner as rcs
        try:
            eng = rcs._ensure_engine()
            end = pd.to_datetime(self.rsi_end.get().strip() or pd.Timestamp.today()).date()
            start = end - pd.Timedelta(days=days)
            with eng.connect() as conn:
                q = text("SELECT * FROM nse_rsi_crosses WHERE trade_date BETWEEN :a AND :b AND cross_type = :ct ORDER BY trade_date DESC")
                rows = conn.execute(q, {"a": start.strftime('%Y-%m-%d'), "b": end.strftime('%Y-%m-%d'), "ct": cross_type}).fetchall()
            if not rows:
                # clear tree and show no results
                for i in self.cross_tree.get_children():
                    self.cross_tree.delete(i)
                return
            df = pd.DataFrame(rows, columns=[c for c in rows[0]._fields])
            # populate treeview
            for i in self.cross_tree.get_children():
                self.cross_tree.delete(i)
            for _, r in df.iterrows():
                vals = (
                    r.get('symbol'),
                    pd.to_datetime(r.get('trade_date')).strftime('%Y-%m-%d') if pd.notna(r.get('trade_date')) else '',
                    int(r.get('period')) if pd.notna(r.get('period')) else None,
                    r.get('cross_type'),
                    float(r.get('prev_rsi')) if pd.notna(r.get('prev_rsi')) else None,
                    float(r.get('curr_rsi')) if pd.notna(r.get('curr_rsi')) else None,
                    float(r.get('high')) if pd.notna(r.get('high')) else None,
                    pd.to_datetime(r.get('created_at')).strftime('%Y-%m-%d %H:%M:%S') if pd.notna(r.get('created_at')) else ''
                )
                self.cross_tree.insert('', 'end', values=vals)
        except Exception as e:
            self.append_log(f"Error showing range cross: {e}")
            self.append_log(traceback.format_exc())

    def run_stocks_above_window(self):
        import rsi_cross_scanner as rcs

        def worker():
            try:
                eng = rcs._ensure_engine()
                days = int(self.cross_window_days.get() or 365)
                topn = int(self.cross_top_n.get() or 0)
                as_of = self.rsi_end.get().strip() or None

                # UI: start indeterminate progress
                def _start_ui():
                    try:
                        self.rsi_results.delete('1.0', 'end')
                        self.rsi_results.insert('end', 'Running stocks above window highs...')
                        self.rsi_progress.configure(mode='indeterminate')
                        try:
                            self.rsi_progress.start(50)
                        except Exception:
                            pass
                    except Exception:
                        pass
                self.root.after(0, _start_ui)

                df = rcs.stocks_trading_above_cross_window(eng, as_of=as_of, days=days, period=int(self.rsi_period.get()), cross_type='80_up')

                # stop progress
                def _stop_ui():
                    try:
                        try:
                            self.rsi_progress.stop()
                        except Exception:
                            pass
                        self.rsi_progress.configure(mode='determinate')
                        self.rsi_progress['value'] = 0
                    except Exception:
                        pass
                self.root.after(0, _stop_ui)

                if df.empty:
                    # No results — attempt incremental scan fallback after user confirmation
                    def _prompt_and_run():
                        do_run = messagebox.askyesno('No results', 'No cross events found in the selected window. Run incremental cross scan now and retry?')
                        if not do_run:
                            for i in self.cross_tree.get_children():
                                self.cross_tree.delete(i)
                            self._last_cross_df = pd.DataFrame()
                            return

                        # run incremental scan (same worker thread) and provide progress updates
                        try:
                            def _scan_progress(cu, to, msg):
                                try:
                                    self.append_log(f"[Scan] {msg}")
                                    def _ui():
                                        try:
                                            self.rsi_results.delete('1.0', 'end')
                                            self.rsi_results.insert('end', f"{msg}\n{cu}/{to}\n")
                                        except Exception:
                                            pass
                                    self.root.after(0, _ui)
                                except Exception:
                                    pass

                            # run incremental scan; lookback_days=days
                            self.append_log('Starting incremental cross scan (fallback)...')
                            rcs.scan_incremental_and_upsert(eng, period=int(self.rsi_period.get()), as_of=as_of, lookback_days=days, progress_cb=_scan_progress)
                            self.append_log('Incremental scan (fallback) finished; re-querying results')
                        except Exception as e:
                            self.append_log(f"Fallback scan error: {e}")
                            self.append_log(traceback.format_exc())
                            return

                        # re-run the query after scan
                        try:
                            df2 = rcs.stocks_trading_above_cross_window(eng, as_of=as_of, days=days, period=int(self.rsi_period.get()), cross_type='80_up')
                            if df2.empty:
                                messagebox.showinfo('No results', 'No stocks found after incremental scan')
                                for i in self.cross_tree.get_children():
                                    self.cross_tree.delete(i)
                                self._last_cross_df = pd.DataFrame()
                                return
                            # apply top-N
                            if topn and topn > 0:
                                df2 = df2.head(topn)
                            df2['diff'] = pd.to_numeric(df2['asof_close'], errors='coerce') - pd.to_numeric(df2['max_cross_high'], errors='coerce')
                            self._last_cross_df = df2.copy()
                            # populate tree
                            for i in self.cross_tree.get_children():
                                self.cross_tree.delete(i)
                            for _, r in df2.iterrows():
                                vals = (
                                    r.get('symbol'),
                                    pd.to_datetime(r.get('last_cross_date')).strftime('%Y-%m-%d') if pd.notna(r.get('last_cross_date')) else '',
                                    '',
                                    '80_up',
                                    '',
                                    '',
                                    float(r.get('max_cross_high')) if pd.notna(r.get('max_cross_high')) else None,
                                    '',
                                    float(r.get('diff')) if pd.notna(r.get('diff')) else None,
                                )
                                self.cross_tree.insert('', 'end', values=vals)
                        except Exception as e:
                            self.append_log(f"Error re-querying after fallback scan: {e}")
                            self.append_log(traceback.format_exc())

                    self.root.after(0, _prompt_and_run)
                    return

                # apply top-N
                if topn and topn > 0:
                    df = df.head(topn)
                # compute diff column (asof_close - cross_high)
                df['diff'] = pd.to_numeric(df['asof_close'], errors='coerce') - pd.to_numeric(df['cross_high'], errors='coerce')

                # store for export
                self._last_cross_df = df.copy()

                # populate tree on main thread
                def _populate():
                    try:
                        for i in self.cross_tree.get_children():
                            self.cross_tree.delete(i)
                        for _, r in df.iterrows():
                            vals = (
                                r.get('symbol'),
                                pd.to_datetime(r.get('cross_date')).strftime('%Y-%m-%d') if pd.notna(r.get('cross_date')) else '',
                                '',
                                '80_up',
                                '',
                                '',
                                float(r.get('cross_high')) if pd.notna(r.get('cross_high')) else None,
                                '',
                                float(r.get('diff')) if pd.notna(r.get('diff')) else None,
                            )
                            self.cross_tree.insert('', 'end', values=vals)
                    except Exception as e:
                        self.append_log(f"Error populating tree: {e}")
                self.root.after(0, _populate)
            except Exception as e:
                self.append_log(f"Error running stocks above window highs: {e}")
                self.append_log(traceback.format_exc())

        threading.Thread(target=worker, daemon=True).start()

    def export_cross_csv(self):
        try:
            df = getattr(self, '_last_cross_df', None)
            if df is None or df.empty:
                messagebox.showinfo('No data', 'No results to export')
                return
            path = filedialog.asksaveasfilename(defaultextension='.csv', filetypes=[('CSV files','*.csv'),('All files','*.*')])
            if not path:
                return
            df.to_csv(path, index=False)
            messagebox.showinfo('Saved', f'Exported {len(df)} rows to {path}')
        except Exception as e:
            self.append_log(f"Error exporting CSV: {e}")
            self.append_log(traceback.format_exc())

    def _cross_tree_sort(self, col: str):
        # Toggle sort direction for column and reorder tree rows
        try:
            children = list(self.cross_tree.get_children(''))
            if not children:
                return
            # read column values
            vals = [(self.cross_tree.set(ch, col), ch) for ch in children]

            def _maybe_cast(v):
                # try date
                try:
                    return datetime.fromisoformat(v)
                except Exception:
                    pass
                try:
                    return float(v)
                except Exception:
                    pass
                return v.lower() if isinstance(v, str) else v

            # determine previous sort state
            prev = getattr(self, '_cross_tree_sort_state', {}).get(col, False)
            reverse = not prev
            vals.sort(key=lambda x: _maybe_cast(x[0]) if x[0] is not None else '', reverse=reverse)
            for idx, (_v, iid) in enumerate(vals):
                self.cross_tree.move(iid, '', idx)
            # update state
            self._cross_tree_sort_state = {col: reverse}
            # update headings to show arrow
            for c in self.cross_tree['columns']:
                txt = c
                if c == col:
                    txt = f"{c} {'▼' if reverse else '▲'}"
                try:
                    self.cross_tree.heading(c, text=txt, command=lambda _col=c: self._cross_tree_sort(_col))
                except Exception:
                    pass
        except Exception:
            pass

    def _on_cross_row_double_click(self, event):
        # identify selected item and open a detail window with a small price chart
        try:
            item = self.cross_tree.identify_row(event.y)
            if not item:
                return
            vals = self.cross_tree.item(item, 'values')
            if not vals:
                return
            symbol = vals[0]
            # open detail window in main thread
            def _open():
                try:
                    win = tk.Toplevel(self.root)
                    win.title(f"{symbol} - Price Detail")
                    win.geometry('600x400')
                    lbl = ttk.Label(win, text=f"Loading price chart for {symbol}...")
                    lbl.pack()

                    # fetch last 180 days of closes and plot
                    try:
                        import matplotlib
                        matplotlib.use('Agg')
                        import matplotlib.pyplot as plt
                        from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
                    except Exception:
                        lbl.config(text='matplotlib not available')
                        return

                    try:
                        eng = None
                        try:
                            eng = __import__('rsi_cross_scanner').rsi_cross_scanner._ensure_engine()
                        except Exception:
                            try:
                                from rsi_cross_scanner import _ensure_engine
                                eng = _ensure_engine()
                            except Exception:
                                eng = None
                        if not eng:
                            lbl.config(text='No DB engine available')
                            return

                        with eng.connect() as conn:
                            q = text("SELECT trade_date, close_price FROM nse_equity_bhavcopy_full WHERE symbol = :s AND trade_date <= :d ORDER BY trade_date DESC LIMIT 180")
                            rows = conn.execute(q, {"s": symbol, "d": self.rsi_end.get().strip() or date.today().strftime('%Y-%m-%d')}).fetchall()
                        if not rows:
                            lbl.config(text='No price data')
                            return
                        df = pd.DataFrame(rows, columns=['trade_date', 'close'])
                        df['trade_date'] = pd.to_datetime(df['trade_date'])
                        df = df.sort_values('trade_date')

                        fig, ax = plt.subplots(figsize=(6,3))
                        ax.plot(df['trade_date'], df['close'], label=symbol)
                        ax.set_title(f"{symbol} - last {len(df)} days")
                        ax.set_xlabel('Date')
                        ax.set_ylabel('Close')
                        ax.grid(True)
                        fig.autofmt_xdate()

                        canvas = FigureCanvasTkAgg(fig, master=win)
                        canvas.draw()
                        canvas.get_tk_widget().pack(fill='both', expand=True)
                    except Exception as pe:
                        lbl.config(text=f'Error plotting: {pe}')
                except Exception:
                    pass
            self.root.after(0, _open)
        except Exception:
            pass

    def _cancel_rsi(self):
        try:
            self.rsi_cancel_token['cancel'] = True
            self.append_log('RSI cancel requested')
        except Exception:
            pass

    def run_import_indices(self):
        import import_nifty_index as inj

        def worker():
            folder = self.idx_folder.get().strip()
            if not folder or not Path(folder).exists():
                self.append_log(f"Indices import: folder not found: {folder}")
                messagebox.showerror("Folder not found", f"Folder not found: {folder}")
                return

            upsert = True
            table = self.idx_table.get().strip() or "indices_daily"
            recurse = self.idx_recurse.get()
            combine = self.idx_combine.get()

            self.append_log(f"Starting indices import from: {folder} (combine={combine}, recurse={recurse})")
            # disable button on main thread
            self.root.after(0, lambda: self.append_log("Import running in background..."))

            eng = inj.build_engine()

            try:
                if combine:
                    # read all CSVs, normalise and concat, drop duplicates, then upsert once
                    files = []
                    if recurse:
                        for root, _, fns in __import__('os').walk(folder):
                            for fn in fns:
                                if fn.lower().endswith('.csv'):
                                    files.append(__import__('os').path.join(root, fn))
                    else:
                        for fn in __import__('os').listdir(folder):
                            if fn.lower().endswith('.csv'):
                                files.append(__import__('os').path.join(folder, fn))

                    if not files:
                        self.append_log("No CSV files found to import.")
                        return

                    dfs = []
                    for p in sorted(files):
                        try:
                            df = pd.read_csv(p, skip_blank_lines=True)
                            df = inj.normalise_columns(df)
                            # ensure index_name is set per-file so combined frame keeps provenance
                            try:
                                raw = Path(p).stem
                                idxname = inj.filename_to_index_name(raw)
                            except Exception:
                                idxname = "UNKNOWN"
                            df["index_name"] = idxname
                            dfs.append(df)
                            self.append_log(f"Parsed {len(df)} rows from {p}")
                        except Exception as e:
                            self.append_log(f"Failed to read {p}: {e}")

                    if not dfs:
                        self.append_log("No valid CSV data parsed.")
                        return

                    big = pd.concat(dfs, ignore_index=True)
                    # drop duplicates by (index_name, trade_date) when index_name present,
                    # otherwise fall back to trade_date only
                    if 'trade_date' in big.columns:
                        if 'index_name' in big.columns:
                            big = big.drop_duplicates(subset=['index_name', 'trade_date'], keep='last')
                        else:
                            big = big.drop_duplicates(subset=['trade_date'], keep='last')

                    self.append_log(f"Combined dataframe has {len(big)} unique dates. Upserting to {table}...")
                    inj.upsert_with_temp_table(eng, big, table=table)
                    self.append_log(f"Combined upsert complete: {len(big)} rows")
                    # show summary in results box
                    def _show():
                        self.idx_results.delete('1.0', 'end')
                        self.idx_results.insert('end', f"Imported {len(big)} unique rows from {len(files)} files.\n")
                    self.root.after(0, _show)
                else:
                    # import files one by one using module helper (it will upsert per-file safely)
                    summaries = inj.import_folder(folder, eng, table=table, upsert=upsert, recurse=recurse)
                    self.append_log(f"Imported {len(summaries)} files (see details)")
                    def _show2():
                        self.idx_results.delete('1.0', 'end')
                        for s in summaries:
                            self.idx_results.insert('end', str(s) + '\n')
                    self.root.after(0, _show2)
            except Exception as e:
                self.append_log(f"Import error: {e}")
                self.append_log(traceback.format_exc())

        threading.Thread(target=worker, daemon=True).start()

    def run_rs_scan(self):
        """Run the relative strength scanner in a background thread using scan_relative_strength.main()."""
        def worker():
            try:
                import scan_relative_strength as srs

                self.append_log(f"Starting RS preview: index={self.rs_index.get()} as-of={self.rs_asof.get()} lookback={self.rs_lookback.get()}")
                # compute preview top N
                topn = 20
                preview = srs.compute_relative_strength_preview(self.rs_index.get(), self.rs_asof.get(), self.rs_lookback.get(), top_n=topn)
                if preview.empty:
                    self.append_log("RS preview returned no rows")
                    return

                # show preview in results box
                def _show_preview():
                    try:
                        self.idx_results.delete('1.0', 'end')
                        self.idx_results.insert('end', f"Top {topn} symbols by RS:\n")
                        self.idx_results.insert('end', preview[['symbol','rs_value','stock_return','index_return']].to_string(index=False))
                    except Exception:
                        pass

                self.root.after(0, _show_preview)

                # ask user to confirm upsert
                do_upsert = messagebox.askyesno("Upsert RS results?", f"Upsert top {topn} RS rows to DB?")
                if not do_upsert:
                    self.append_log("User cancelled RS upsert")
                    return

                # upsert all preview rows (or full set) via the scanner's bulk compute + upsert
                self.append_log("Upserting RS preview rows to database...")
                # call main() with same params to compute & upsert full set (or limited set)
                import sys
                old_argv = sys.argv
                try:
                    sys.argv = [old_argv[0], '--index', self.rs_index.get(), '--as-of', self.rs_asof.get(), '--lookback', str(self.rs_lookback.get()), '--limit', str(self.rs_limit.get() or 0)]
                    srs.main()
                finally:
                    sys.argv = old_argv
                self.append_log("RS upsert completed")
            except Exception as e:
                self.append_log(f"RS scan error: {e}")
                self.append_log(traceback.format_exc())

        threading.Thread(target=worker, daemon=True).start()

    def run_aggregate_bhav(self, freq: str = 'weekly'):
        """Run BHAV aggregation (weekly or monthly) in a background thread.

        Defaults to aggregating the last 365 days up to today if no dates are provided.
        """
        def worker():
            try:
                import aggregate_bhav as ab
                eng = None
                try:
                    # prefer engine builder from import_nifty_index if present
                    from import_nifty_index import build_engine
                    eng = build_engine()
                except Exception:
                    try:
                        eng = ab._ensure_engine()
                    except Exception:
                        eng = None

                today = date.today()
                one_year_ago = today - pd.Timedelta(days=365)
                start = one_year_ago.strftime('%Y-%m-%d')
                end = today.strftime('%Y-%m-%d')

                if not eng:
                    self.append_log('No DB engine available for aggregation; aborting')
                    return

                self.append_log(f"Starting BHAV aggregation: freq={freq} start={start} end={end}")

                # progress callback to receive granular updates
                def _progress_cb(current, total, message):
                    try:
                        self.append_log(f"[agg] {message}")
                        # also update the results box with the last message
                        def _update_box():
                            try:
                                self.idx_results.delete('1.0', 'end')
                                self.idx_results.insert('end', f"{message}\nProcessed {current}/{total}\n")
                            except Exception:
                                pass
                        self.root.after(0, _update_box)
                    except Exception:
                        pass

                ab.run_aggregate(eng, start, end, freq=freq if freq in ('weekly','monthly') else 'both', progress_cb=_progress_cb)

                self.append_log("BHAV aggregation finished")
                def _show():
                    try:
                        self.idx_results.insert('end', f"Aggregation completed: {freq} {start}..{end}\n")
                    except Exception:
                        pass
                self.root.after(0, _show)
            except Exception as e:
                self.append_log(f"BHAV aggregation error: {e}")
                self.append_log(traceback.format_exc())

        threading.Thread(target=worker, daemon=True).start()

    def run_adv_decl_report(self):
        import reporting_adv_decl as rad

        def worker():
            # collect parameters in background thread
            start = self.ad_start.get(); end = self.ad_end.get()
            series_raw = self.ad_series.get() or ""
            series = [s.strip().upper() for s in series_raw.split(",") if s.strip()]
            if not series:
                series = None
            rpt = self.ad_report_type.get()
            out = self.ad_out.get().strip() or None

            # disable the button now
            self.root.after(0, lambda: self.ad_run_btn.configure(state="disabled"))
            self.append_log("Generating Advance/Decline report...")

            try:
                if out:
                    # background save: safe to run in worker thread
                    rad.plot_adv_decl(start=parse_date(start), end=parse_date(end), series=series or rad.DEFAULT_SERIES, save_path=out, report_type=rpt)
                    self.append_log("Advance/Decline report saved")
                    # re-enable button
                    self.root.after(0, lambda: self.ad_run_btn.configure(state="normal"))
                else:
                    # need to open the matplotlib GUI: run plot on the main thread
                    def _plot_on_main():
                        try:
                            rad.plot_adv_decl(start=parse_date(start), end=parse_date(end), series=series or rad.DEFAULT_SERIES, save_path=None, report_type=rpt)
                            self.append_log("Advance/Decline report displayed")
                        except Exception as e:
                            # If there are no cached rows, offer to compute them and retry
                            msg = str(e)
                            self.append_log(f"Error displaying report: {msg}")
                            self.append_log(traceback.format_exc())
                            if isinstance(e, RuntimeError) and "No cached rows" in msg:
                                # Ask user to compute cache now
                                do_compute = messagebox.askyesno("Compute A/D cache?", "No cached A/D data in the selected range/scope. Compute and cache now? This may take some time.")
                                if not do_compute:
                                    return

                                # modal progress window
                                progress_win = tk.Toplevel(self.root)
                                progress_win.title("Computing A/D cache")
                                progress_win.transient(self.root)
                                progress_win.grab_set()
                                ttk.Label(progress_win, text="Computing cache...").grid(row=0, column=0, padx=12, pady=8)
                                pb = ttk.Progressbar(progress_win, orient="horizontal", mode="determinate", length=400)
                                pb.grid(row=1, column=0, padx=12, pady=(0,8))
                                status_lbl = ttk.Label(progress_win, text="Starting...")
                                status_lbl.grid(row=2, column=0, padx=12, pady=(0,8))

                                def _progress_cb(current, total, dt):
                                    # schedule UI updates on main thread
                                    def _u():
                                        try:
                                            pb["maximum"] = total
                                            pb["value"] = current
                                            status_lbl["text"] = f"{current}/{total} — {dt}"
                                        except Exception:
                                            pass
                                    self.root.after(0, _u)

                                def _compute_and_plot():
                                    try:
                                        self.append_log("Computing A/D cache for selected range (interactive)...")
                                        rad.compute_range(parse_date(start), parse_date(end), series=series or rad.DEFAULT_SERIES, force=True, progress_cb=_progress_cb)
                                        self.append_log("Cache compute completed, displaying report...")
                                        # close progress window and plot on main thread
                                        def _close_and_plot():
                                            try:
                                                progress_win.grab_release()
                                                progress_win.destroy()
                                            except Exception:
                                                pass
                                            rad.plot_adv_decl(start=parse_date(start), end=parse_date(end), series=series or rad.DEFAULT_SERIES, save_path=None, report_type=rpt)
                                        self.root.after(0, _close_and_plot)
                                    except Exception as ce:
                                        self.append_log(f"Error computing cache: {ce}")
                                        self.append_log(traceback.format_exc())
                                        def _close():
                                            try:
                                                progress_win.grab_release()
                                                progress_win.destroy()
                                            except Exception:
                                                pass
                                        self.root.after(0, _close)

                                threading.Thread(target=_compute_and_plot, daemon=True).start()
                        finally:
                            self.ad_run_btn.configure(state="normal")

                    self.root.after(0, _plot_on_main)
            except Exception as e:
                self.append_log(f"Error generating report: {e}")
                self.append_log(traceback.format_exc())
                # ensure button re-enabled
                self.root.after(0, lambda: self.ad_run_btn.configure(state="normal"))

        threading.Thread(target=worker, daemon=True).start()

    # -------- Candles tab --------
    def _build_candles_tab(self):
        f = self.candles_frame
        ttk.Label(f, text="Symbol").grid(row=0, column=0, sticky="w")
        self.candle_symbol = tk.StringVar(value="")
        self.candle_sym_cb = ttk.Combobox(f, textvariable=self.candle_symbol, values=[""], width=12)
        self.candle_sym_cb.grid(row=0, column=1)

        ttk.Label(f, text="Date from").grid(row=0, column=2, sticky="w")
        self.candle_start = tk.StringVar(value="2025-08-01")
        ttk.Entry(f, textvariable=self.candle_start, width=12).grid(row=0, column=3)
        ttk.Label(f, text="Date to").grid(row=0, column=4, sticky="w")
        self.candle_end = tk.StringVar(value="2025-10-10")
        ttk.Entry(f, textvariable=self.candle_end, width=12).grid(row=0, column=5)

        ttk.Button(f, text="Plot", command=self.plot_candles_for_symbol).grid(row=0, column=6, padx=6)

        # plotting area
        plot_area = ttk.Frame(f)
        plot_area.grid(row=1, column=0, columnspan=8, sticky="nsew", padx=6, pady=6)
        f.grid_rowconfigure(1, weight=1)
        f.grid_columnconfigure(7, weight=1)

        # store reference for canvas
        self._candle_plot_area = plot_area

        # load symbols from DB
        def _load_symbols():
            try:
                import reporting_adv_decl as rad
                from sqlalchemy import text
                eng = rad.engine()
                with eng.connect() as conn:
                    rows = conn.execute(text("SELECT DISTINCT symbol FROM nse_equity_bhavcopy_full ORDER BY symbol"))
                    syms = [r[0] for r in rows if r[0]]
                def _set():
                    try:
                        self.candle_sym_cb["values"] = syms
                        if syms:
                            self.candle_symbol.set(syms[0])
                    except Exception:
                        pass
                self.root.after(0, _set)
            except Exception as e:
                self.append_log(f"Could not load symbol list: {e}")

        threading.Thread(target=_load_symbols, daemon=True).start()

    def _build_sma_tab(self):
        f = self.sma_frame
        ttk.Label(f, text="Short SMA").grid(row=0, column=0, sticky="w")
        self.sma_short = tk.IntVar(value=20)
        ttk.Entry(f, textvariable=self.sma_short, width=8).grid(row=0, column=1)

        ttk.Label(f, text="Long SMA").grid(row=0, column=2, sticky="w")
        self.sma_long = tk.IntVar(value=50)
        ttk.Entry(f, textvariable=self.sma_long, width=8).grid(row=0, column=3)

        ttk.Label(f, text="Since (YYYY-MM-DD)").grid(row=1, column=0, sticky="w")
        self.sma_since = tk.StringVar(value="2025-09-01")
        ttk.Entry(f, textvariable=self.sma_since, width=12).grid(row=1, column=1)

        ttk.Button(f, text="Run SMA Scan", command=self.run_sma_scan).grid(row=2, column=0, pady=6)
        ttk.Button(f, text="Compute moving averages (full)", command=self.run_full_compute).grid(row=2, column=1, pady=6)
        # Save CSV button (disabled until scan completes)
        self.sma_save_btn = ttk.Button(f, text="Save CSV", command=self._sma_save_csv, state="disabled")
        self.sma_save_btn.grid(row=2, column=2, pady=6)

        # results tree
        cols = ("symbol", "date", "sma_short", "sma_long", "momentum", "golden_cross")
        # keep cols for sorting header updates
        self._sma_cols = cols
        tree_frame = ttk.Frame(f)
        tree_frame.grid(row=3, column=0, columnspan=6, sticky="nsew", pady=6)
        f.grid_rowconfigure(3, weight=1)
        f.grid_columnconfigure(5, weight=1)

        self.sma_tree = ttk.Treeview(tree_frame, columns=cols, show="headings", height=12)
        for c in cols:
            # clickable heading to sort by column
            self.sma_tree.heading(c, text=c, command=lambda _col=c: self._sma_tree_sort(_col))
            self.sma_tree.column(c, width=100, anchor="w")
        v = ttk.Scrollbar(tree_frame, orient="vertical", command=self.sma_tree.yview)
        h = ttk.Scrollbar(tree_frame, orient="horizontal", command=self.sma_tree.xview)
        self.sma_tree.configure(yscrollcommand=v.set, xscrollcommand=h.set)
        tree_frame.grid_rowconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)
        self.sma_tree.grid(row=0, column=0, sticky="nsew")
        v.grid(row=0, column=1, sticky="ns")
        h.grid(row=1, column=0, sticky="ew")

    def _build_strong_tab(self):
        f = self.strong_frame
        ttk.Label(f, text="Since (YYYY-MM-DD)").grid(row=0, column=0, sticky="w")
        self.str_since = tk.StringVar(value="2025-09-01")
        ttk.Entry(f, textvariable=self.str_since, width=12).grid(row=0, column=1)

        ttk.Label(f, text="Min SMA20 % (10d)").grid(row=0, column=2, sticky="w")
        self.str_min_sma20_pct = tk.DoubleVar(value=3.0)
        ttk.Entry(f, textvariable=self.str_min_sma20_pct, width=8).grid(row=0, column=3)

        ttk.Label(f, text="Min vol ratio").grid(row=1, column=0, sticky="w")
        self.str_min_vol_ratio = tk.DoubleVar(value=1.2)
        ttk.Entry(f, textvariable=self.str_min_vol_ratio, width=8).grid(row=1, column=1)

        ttk.Button(f, text="Run Strong Uptrend", command=self.run_strong_uptrend).grid(row=2, column=0, pady=6)
        self.str_save_btn = ttk.Button(f, text="Save CSV", command=self._strong_save_csv, state="disabled")
        self.str_save_btn.grid(row=2, column=1, pady=6)
        ttk.Button(f, text="Run & Save CSV", command=self.run_strong_and_save).grid(row=2, column=2, pady=6)

        cols = ("symbol", "date", "close", "sma_5", "sma_20", "sma_50", "sma20_pct", "vol_ratio")
        tree_frame = ttk.Frame(f)
        tree_frame.grid(row=3, column=0, columnspan=6, sticky="nsew", pady=6)
        f.grid_rowconfigure(3, weight=1)
        f.grid_columnconfigure(5, weight=1)

        self.strong_tree = ttk.Treeview(tree_frame, columns=cols, show="headings", height=12)
        for c in cols:
            self.strong_tree.heading(c, text=c, command=lambda _col=c: self._sma_tree_sort(_col))
            self.strong_tree.column(c, width=100, anchor="w")
        v = ttk.Scrollbar(tree_frame, orient="vertical", command=self.strong_tree.yview)
        h = ttk.Scrollbar(tree_frame, orient="horizontal", command=self.strong_tree.xview)
        self.strong_tree.configure(yscrollcommand=v.set, xscrollcommand=h.set)
        tree_frame.grid_rowconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)
        self.strong_tree.grid(row=0, column=0, sticky="nsew")
        v.grid(row=0, column=1, sticky="ns")
        h.grid(row=1, column=0, sticky="ew")

    def run_sma_scan(self):
        import scan_moving_avg_trends as scanner

        def worker():
            try:
                self.append_log("Starting SMA scan...")
                short = self.sma_short.get(); long = self.sma_long.get()
                since = self.sma_since.get().strip() or None
                res = scanner.scan(short=short, long=long, since=since)
                # cache last results so Save CSV button can use them
                self._sma_last_results = res
                self.append_log(f"SMA scan found {len(res)} candidates")
                def _update():
                    try:
                        for i in self.sma_tree.get_children():
                            self.sma_tree.delete(i)
                        for r in res:
                            date_str = r['date'].isoformat() if hasattr(r['date'], 'isoformat') else str(r['date'])
                            self.sma_tree.insert('', 'end', values=(r['symbol'], date_str, f"{r['sma_short']:.2f}", f"{r['sma_long']:.2f}", str(r['momentum']), str(r['golden_cross'])))
                        # enable save button when results present
                        try:
                            if getattr(self, '_sma_last_results', None):
                                self.sma_save_btn.configure(state="normal")
                            else:
                                self.sma_save_btn.configure(state="disabled")
                        except Exception:
                            pass
                    except Exception:
                        pass
                self.root.after(0, _update)
            except Exception as e:
                self.append_log(f"Error in SMA scan: {e}")
                self.append_log(traceback.format_exc())

        threading.Thread(target=worker, daemon=True).start()

    def _sma_tree_sort(self, col: str):
        # Toggle sort order for column `col` and reorder tree rows.
        try:
            prev = self._sma_tree_sort_state.get(col, False)
            reverse = not prev
            # collect items and their column value
            items = [(self.sma_tree.set(i, col), i) for i in self.sma_tree.get_children('')]

            def _key(item):
                v = item[0]
                # try date
                try:
                    # ISO format expected
                    return datetime.fromisoformat(v)
                except Exception:
                    pass
                # try float
                try:
                    return float(v)
                except Exception:
                    pass
                # boolean strings
                if v in ('True', 'False'):
                    return v == 'True'
                return v.lower() if isinstance(v, str) else v

            items.sort(key=_key, reverse=reverse)
            for idx, (_, iid) in enumerate(items):
                self.sma_tree.move(iid, '', idx)

            # update sort state (only the active column kept)
            self._sma_tree_sort_state = {col: reverse}

            # update headings to show arrow on sorted column
            for c in self._sma_cols:
                txt = c
                if c == col:
                    txt = f"{c} {'▼' if reverse else '▲'}"
                try:
                    self.sma_tree.heading(c, text=txt, command=lambda _col=c: self._sma_tree_sort(_col))
                except Exception:
                    pass
        except Exception:
            pass

    def run_strong_uptrend(self):
        import strong_uptrend as su

        def worker():
            try:
                self.append_log("Starting Strong Uptrend scan...")
                since = self.str_since.get().strip() or None
                min_sma20_pct = float(self.str_min_sma20_pct.get()) / 100.0
                min_vol_ratio = float(self.str_min_vol_ratio.get())
                res = su.scan(min_avg_vol_ratio=min_vol_ratio, min_sma20_pct=min_sma20_pct, since=since)
                self._strong_last = res
                self.append_log(f"Strong uptrend scan found {len(res)} candidates")

                def _update():
                    try:
                        for i in self.strong_tree.get_children():
                            self.strong_tree.delete(i)
                        for r in res:
                            date_str = r['date'].isoformat() if hasattr(r['date'], 'isoformat') else str(r['date'])
                            self.strong_tree.insert('', 'end', values=(r['symbol'], date_str, f"{r['close']:.2f}", f"{r['sma_5']:.2f}", f"{r['sma_20']:.2f}", f"{r['sma_50']:.2f}", f"{r['sma20_pct']:.3f}", f"{r['vol_ratio']:.2f}"))
                        try:
                            if getattr(self, '_strong_last', None):
                                self.str_save_btn.configure(state='normal')
                            else:
                                self.str_save_btn.configure(state='disabled')
                        except Exception:
                            pass
                    except Exception:
                        pass

                self.root.after(0, _update)
            except Exception as e:
                self.append_log(f"Error running strong uptrend: {e}")
                self.append_log(traceback.format_exc())

        threading.Thread(target=worker, daemon=True).start()

    def _strong_save_csv(self):
        res = getattr(self, '_strong_last', None)
        if not res:
            messagebox.showinfo('No results', 'No results to save. Run scan first.')
            return
        p = filedialog.asksaveasfilename(defaultextension='.csv', filetypes=[('CSV','*.csv'), ('All','*')])
        if not p:
            return
        try:
            import csv
            keys = ['symbol','date','close','sma_5','sma_20','sma_50','sma20_pct','vol_ratio']
            with open(p, 'w', newline='', encoding='utf-8') as fh:
                w = csv.writer(fh)
                w.writerow(keys)
                for r in res:
                    w.writerow([r.get(k) for k in keys])
            self.append_log(f"Wrote strong uptrend CSV: {p}")
        except Exception as e:
            self.append_log(f"Error saving CSV: {e}")
            self.append_log(traceback.format_exc())

    def run_strong_and_save(self):
        # Prompt for filename and run the strong_uptrend scanner then save results to CSV (background)
        p = filedialog.asksaveasfilename(defaultextension='.csv', filetypes=[('CSV','*.csv'),('All','*')])
        if not p:
            return

        def worker(path):
            try:
                import strong_uptrend as su
                self.append_log(f"Running Strong Uptrend scan and writing CSV to {path}...")
                since = self.str_since.get().strip() or None
                min_sma20_pct = float(self.str_min_sma20_pct.get()) / 100.0
                min_vol_ratio = float(self.str_min_vol_ratio.get())
                res = su.scan(min_avg_vol_ratio=min_vol_ratio, min_sma20_pct=min_sma20_pct, since=since)
                # save CSV
                import csv
                keys = ['symbol','date','close','sma_5','sma_20','sma_50','sma_100','sma20_pct','vol_ratio']
                with open(path, 'w', newline='', encoding='utf-8') as fh:
                    w = csv.writer(fh)
                    w.writerow(keys)
                    for r in res:
                        row = [r.get(k) for k in keys]
                        if row[1] and hasattr(row[1], 'isoformat'):
                            row[1] = row[1].isoformat()
                        w.writerow(row)
                self.append_log(f"Wrote {len(res)} rows to {path}")
            except Exception as e:
                self.append_log(f"Error running+saving strong uptrend: {e}")
                self.append_log(traceback.format_exc())

        threading.Thread(target=lambda: worker(p), daemon=True).start()

    def run_full_compute(self):
        # modal progress window
        progress_win = tk.Toplevel(self.root)
        progress_win.title("Computing full moving averages")
        progress_win.transient(self.root)
        progress_win.grab_set()
        ttk.Label(progress_win, text="Computing moving averages for all symbols...").grid(row=0, column=0, padx=12, pady=8)
        pb = ttk.Progressbar(progress_win, orient="horizontal", mode="indeterminate", length=400)
        pb.grid(row=1, column=0, padx=12, pady=(0,8))
        status_lbl = ttk.Label(progress_win, text="Starting...")
        status_lbl.grid(row=2, column=0, padx=12, pady=(0,8))
        pb.start(50)

        def worker():
            try:
                import compute_moving_averages as cm
                # run full compute; this prints progress to stdout — capture nothing but log start/finish
                self.append_log("Starting full compute of moving averages (background)")
                cm.main([])
                self.append_log("Full compute completed")
            except Exception as e:
                self.append_log(f"Error computing moving averages: {e}")
                self.append_log(traceback.format_exc())
            finally:
                def _close():
                    try:
                        pb.stop()
                        progress_win.grab_release()
                        progress_win.destroy()
                    except Exception:
                        pass
                self.root.after(0, _close)

        threading.Thread(target=worker, daemon=True).start()

    def _sma_save_csv(self):
        # Save cached SMA results to CSV. Runs on main thread (invoked by button).
        res = getattr(self, '_sma_last_results', None)
        if not res:
            messagebox.showinfo("No results", "No SMA scan results to save. Run a scan first.")
            return
        p = filedialog.asksaveasfilename(defaultextension='.csv', filetypes=[('CSV','*.csv'), ('All','*')])
        if not p:
            return
        # write CSV
        try:
            import csv
            keys = ['symbol', 'date', 'sma_short', 'sma_long', 'momentum', 'golden_cross']
            with open(p, 'w', newline='', encoding='utf-8') as fh:
                writer = csv.writer(fh)
                writer.writerow(keys)
                for r in res:
                    writer.writerow([r.get(k) for k in keys])
            self.append_log(f"SMA results saved to {p}")
        except Exception as e:
            self.append_log(f"Error saving CSV: {e}")
            self.append_log(traceback.format_exc())

    def plot_candles_for_symbol(self):
        sym = self.candle_symbol.get().strip()
        if not sym:
            messagebox.showerror("No symbol", "Please select a symbol to plot")
            return
        start = parse_date(self.candle_start.get())
        end = parse_date(self.candle_end.get())

        # show small status label while loading
        status_lbl = ttk.Label(self._candle_plot_area, text="Loading...", anchor="center")
        # use pack because other children in this frame use pack
        status_lbl.pack(fill='both', expand=True)

        def worker():
            try:
                t0 = time.perf_counter()
                self.root.after(0, lambda: self.append_log(f"[candles] worker start: {datetime.utcnow().isoformat()}"))
                import mplfinance as mpf
                import pandas as pd
                from sqlalchemy import text
                import reporting_adv_decl as rad
                eng = rad.engine()
                q = text("SELECT trade_date as dt, open_price as Open, high_price as High, low_price as Low, close_price as Close, ttl_trd_qnty as Volume FROM nse_equity_bhavcopy_full WHERE symbol=:s AND trade_date BETWEEN :a AND :b ORDER BY trade_date")
                with eng.connect() as conn:
                    df = pd.read_sql(q, con=conn, params={"s": sym, "a": start, "b": end}, parse_dates=["dt"]) 
                t1 = time.perf_counter()
                self.root.after(0, lambda: self.append_log(f"[candles] DB fetch time: {t1-t0:.2f}s, rows={len(df)}"))
                if df.empty:
                    self.root.after(0, lambda: self.append_log(f"No data for {sym} in range"))
                    def _destroy_status():
                        try:
                            status_lbl.pack_forget()
                            status_lbl.destroy()
                        except Exception:
                            pass
                    self.root.after(0, _destroy_status)
                    return
                df = df.set_index("dt")

                # prepare data and create plotting widgets on main thread
                def _draw_on_main():
                    try:
                        t2 = time.perf_counter()
                        self.append_log(f"[candles] draw scheduled at {datetime.utcnow().isoformat()}, fetch->draw wait: {t2-t1:.2f}s")
                        # destroy status label
                        try:
                            status_lbl.destroy()
                        except Exception:
                            pass

                        # clear previous
                        for child in self._candle_plot_area.winfo_children():
                            child.destroy()

                        # control frame (zoom/pan)
                        ctl = ttk.Frame(self._candle_plot_area)
                        ctl.pack(fill='x')

                        # default window size (bars shown)
                        n_bars = len(df)
                        default_win = min(60, n_bars)
                        min_win = 5

                        # vars stored on self so callbacks can access
                        self._candle_df = df
                        self._candle_win = default_win
                        self._candle_start_idx = max(0, n_bars - default_win)

                        ttk.Label(ctl, text="Window (bars):").pack(side='left')
                        win_var = tk.IntVar(value=self._candle_win)
                        win_scale = ttk.Scale(ctl, from_=min_win, to=max(min_win, n_bars), orient='horizontal')
                        win_scale.set(self._candle_win)
                        win_scale.pack(side='left', fill='x', expand=True, padx=6)

                        ttk.Label(ctl, text="Pan:").pack(side='left')
                        pan_scale = ttk.Scale(ctl, from_=0, to=max(0, n_bars - self._candle_win), orient='horizontal')
                        pan_scale.set(self._candle_start_idx)
                        pan_scale.pack(side='left', fill='x', expand=True, padx=6)

                        from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
                        import matplotlib.dates as mdates
                        import numpy as np

                        canvas_holder = ttk.Frame(self._candle_plot_area)
                        canvas_holder.pack(fill='both', expand=True)

                        # create a single Figure/Canvas and reuse it to avoid creating many figures
                        import matplotlib.pyplot as plt
                        fig, ax = plt.subplots(figsize=(8, 4))
                        canvas = FigureCanvasTkAgg(fig, master=canvas_holder)
                        canvas.get_tk_widget().pack(fill='both', expand=True)
                        canvas.draw()

                        # state to be updated on each render
                        window_df = None
                        nums = None

                        # setup crosshair lines and annotation once
                        vline = ax.axvline(x=0, color='gray', linestyle='--', alpha=0.6, visible=False)
                        hline = ax.axhline(y=0, color='gray', linestyle='--', alpha=0.6, visible=False)
                        annot = ax.annotate('', xy=(0, 0), xytext=(15, 15), textcoords='offset points', bbox=dict(boxstyle='round', fc='w'))
                        annot.set_visible(False)

                        def render_window(start_idx=None, win_size=None):
                            # determine window
                            rs0 = time.perf_counter()
                            n = len(self._candle_df)
                            if win_size is None:
                                win_size = int(win_scale.get())
                            else:
                                win_scale.set(win_size)
                            if start_idx is None:
                                start_idx = int(pan_scale.get())
                            else:
                                pan_scale.set(start_idx)
                            start_idx = max(0, min(n - win_size, int(start_idx)))
                            end_idx = start_idx + int(win_size)
                            nonlocal window_df, nums
                            window_df = self._candle_df.iloc[start_idx:end_idx]
                            nums = mdates.date2num(window_df.index.to_pydatetime())

                            # clear axis and plot into existing ax
                            try:
                                ax.clear()
                                mpf.plot(window_df, type='candle', ax=ax, style='yahoo', volume=False, show_nontrading=False)
                            except Exception:
                                try:
                                    ax.clear()
                                    mpf.plot(window_df, type='candle', ax=ax, style='yahoo', volume=False, show_nontrading=False)
                                except Exception:
                                    pass

                            # store for event handlers
                            self._candle_fig = fig
                            self._candle_ax = ax
                            self._candle_canvas = canvas
                            self._candle_win = int(win_size)
                            self._candle_start_idx = int(start_idx)

                            # update crosshair lines to initial invisible state
                            vline.set_visible(False)
                            hline.set_visible(False)
                            annot.set_visible(False)

                            canvas.draw_idle()
                            rs1 = time.perf_counter()
                            # log render time
                            try:
                                self.append_log(f"[candles] render_window time: {rs1-rs0:.2f}s window={start_idx}:{end_idx} size={win_size}")
                            except Exception:
                                pass

                        # Debounce scheduling to avoid heavy repeated renders
                        self._candle_render_after_id = None
                        def schedule_render(start_idx=None, win_size=None, delay=150):
                            try:
                                if getattr(self, '_candle_render_after_id', None):
                                    try:
                                        self.root.after_cancel(self._candle_render_after_id)
                                    except Exception:
                                        pass
                                self._candle_render_after_id = self.root.after(delay, lambda: render_window(start_idx=start_idx, win_size=win_size))
                            except Exception:
                                # fallback immediate
                                render_window(start_idx=start_idx, win_size=win_size)

                        def _on_move(event):
                            if event.inaxes != ax:
                                if annot.get_visible():
                                    annot.set_visible(False)
                                    vline.set_visible(False)
                                    hline.set_visible(False)
                                    canvas.draw_idle()
                                return
                            try:
                                ex = event.xdata
                                if ex is None or window_df is None:
                                    return
                                # find nearest index in window_df
                                idx = int(np.argmin(np.abs(nums - ex)))
                                row = window_df.iloc[idx]
                                xnum = nums[idx]
                                y = event.ydata
                                # update crosshair
                                vline.set_xdata(xnum)
                                hline.set_ydata(y)
                                vline.set_visible(True)
                                hline.set_visible(True)
                                # annotation text with OHLCV
                                dt = window_df.index[idx].strftime('%Y-%m-%d')
                                txt = f"{dt}\nO: {row['Open']:.2f}\nH: {row['High']:.2f}\nL: {row['Low']:.2f}\nC: {row['Close']:.2f}\nV: {int(row['Volume'])}"
                                annot.xy = (xnum, row['Close'])
                                annot.set_text(txt)
                                annot.set_visible(True)
                                canvas.draw_idle()
                            except Exception:
                                pass

                        def _on_leave(event):
                            try:
                                annot.set_visible(False)
                                vline.set_visible(False)
                                hline.set_visible(False)
                                canvas.draw_idle()
                            except Exception:
                                pass

                        def _on_scroll(event):
                            # zoom in/out keeping cursor center
                            try:
                                if event.inaxes != ax:
                                    return
                                # current window size
                                cur_win = self._candle_win
                                if event.button == 'up':
                                    # zoom in
                                    new_win = max(min_win, int(cur_win * 0.8))
                                else:
                                    # zoom out
                                    new_win = min(n_bars, int(cur_win * 1.25))
                                # compute center index relative to full df
                                full_nums = mdates.date2num(self._candle_df.index.to_pydatetime())
                                center_idx = int(np.argmin(np.abs(full_nums - event.xdata)))
                                # compute new start
                                new_start = max(0, min(n_bars - new_win, center_idx - new_win // 2))
                                # set scales and re-render
                                # update scales but schedule render to avoid immediate heavy call
                                win_scale.set(new_win)
                                pan_scale.configure(to=max(0, n_bars - new_win))
                                schedule_render(start_idx=new_start, win_size=new_win, delay=50)
                            except Exception:
                                pass

                        # connect events
                        canvas.mpl_connect('motion_notify_event', _on_move)
                        canvas.mpl_connect('axes_leave_event', _on_leave)
                        canvas.mpl_connect('scroll_event', _on_scroll)

                        # callbacks for scales
                        def _on_win_change(val):
                            try:
                                new_win = max(min_win, int(float(val)))
                                pan_scale.configure(to=max(0, n_bars - new_win))
                                # adjust start if out of range
                                start = int(pan_scale.get())
                                max_start = max(0, n_bars - new_win)
                                if start > max_start:
                                    start = max_start
                                schedule_render(start_idx=start, win_size=new_win)
                            except Exception:
                                pass

                        def _on_pan_change(val):
                            try:
                                start = int(float(val))
                                schedule_render(start_idx=start, win_size=int(win_scale.get()))
                            except Exception:
                                pass

                        win_scale.configure(command=_on_win_change)
                        pan_scale.configure(command=_on_pan_change)

                        # initial render
                        render_window(start_idx=self._candle_start_idx, win_size=self._candle_win)
                    except Exception as e:
                        self.append_log(f"Error drawing candles: {e}")
                # schedule drawing on main thread
                self.root.after(0, _draw_on_main)
            except Exception as e:
                # log error on main thread and to console
                self.root.after(0, lambda: self.append_log(f"Error preparing candle data: {e}"))
                self.append_log(traceback.format_exc())

        threading.Thread(target=worker, daemon=True).start()

    def run_delivery_count(self):
        import scan_delivery_count as sdc

        def worker():
            try:
                # inform UI (scheduled) and clear the tree on the main thread
                self.append_log("Starting delivery-count scan...")
                def _clear_tree():
                    for i in self.deliv_tree.get_children():
                        self.deliv_tree.delete(i)
                self.root.after(0, _clear_tree)

                start = self.deliv_start.get(); end = self.deliv_end.get()
                series = self.deliv_series.get()
                if series == "ALL":
                    series = None
                thr = self.deliv_thresh.get()
                res = sdc.scan(start=parse_date(start), end=parse_date(end), series=series, threshold=thr)
                # schedule UI update with results on main thread
                def _update_ui():
                    self.append_log(f"Found {len(res)} symbols with delivery% > {thr}")
                    for r in res:
                        self.deliv_tree.insert("", "end", values=(r["symbol"], r["series"], r["days_over"], r["total_days"], f"{r['pct']:.2f}"))
                    out = self.deliv_out.get().strip()
                    if out:
                        try:
                            sdc.save_csv(res, out)
                            self.append_log(f"Wrote CSV: {out}")
                        except Exception as e:
                            self.append_log(f"CSV save error: {e}")

                self.root.after(0, _update_ui)
            except Exception as e:
                self.append_log(f"Error: {e}")
                self.append_log(traceback.format_exc())

        threading.Thread(target=worker, daemon=True).start()

    def run_liquidity(self):
        import liquidity_baseline_and_scan as lb

        def worker():
            try:
                self.append_log("Starting liquidity baseline/scan...")
                base_start = self.liq_base_start.get(); base_end = self.liq_base_end.get()
                recent_start = self.liq_recent_start.get(); recent_end = self.liq_recent_end.get()
                qty_mult = self.liq_qty_mult.get(); turn_mult = self.liq_turn_mult.get()
                eng = lb.engine()
                with eng.begin() as conn:
                    if self.liq_update_baseline.get():
                        cnt = lb.compute_and_upsert_baseline(conn, parse_date(base_start), parse_date(base_end))
                        self.append_log(f"Computed/upserted baseline for {cnt} symbols")
                    results = lb.scan_recent_vs_baseline(conn, parse_date(recent_start), parse_date(recent_end), qty_mult=qty_mult, turnover_mult=turn_mult, compare_latest=self.liq_compare_latest.get())
                self.append_log(f"Found {len(results)} spikes")
                out = self.liq_out.get().strip()
                if out:
                    lb.save_csv(results, out)
                    self.append_log(f"Wrote CSV: {out}")
            except Exception as e:
                self.append_log(f"Error: {e}")
                self.append_log(traceback.format_exc())

        threading.Thread(target=worker, daemon=True).start()

    def _browse(self, var: tk.StringVar, folder: bool = False):
        """Set `var` to a selected path. If folder=True opens a folder dialog, otherwise a save-as CSV dialog."""
        try:
            if folder:
                p = filedialog.askdirectory()
            else:
                p = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV files","*.csv"), ("All","*")])
            if p:
                var.set(p)
        except Exception:
            # ignore UI errors
            return


def parse_date(s: str) -> date:
    return datetime.strptime(s, "%Y-%m-%d").date()


if __name__ == "__main__":
    root = tk.Tk()
    try:
        import ctypes
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass
    app = ScannerGUI(root)
    root.mainloop()
