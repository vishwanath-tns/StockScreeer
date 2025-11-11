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
import os

# Import the dashboard tab
from gui.tabs.dashboard import DashboardTab

LOG_MAX_LINES = 200


class ScannerGUI:
    def __init__(self, root):
        self.root = root
        root.title("Stock Screener - Scanners")
        # Improve tab visibility: larger, bold tab labels and extra padding
        try:
            style = ttk.Style()
            # Define a custom notebook/tab style so we can control borders/colours
            style.configure('Custom.TNotebook.Tab', font=('Segoe UI', 10, 'bold'), padding=[8, 6], borderwidth=1, relief='raised', background='#ececec')
            style.map('Custom.TNotebook.Tab',
                      background=[('selected', '#ffffff'), ('!selected', '#e9eef2')],
                      foreground=[('selected', 'black'), ('!selected', 'black')],
                      expand=[('selected', [1]), ('!selected', [0])])
            style.configure('Custom.TNotebook', background='#d0d0d0', borderwidth=0)
        except Exception:
            pass

        nb = ttk.Notebook(root, style='Custom.TNotebook')
        nb.pack(fill="both", expand=True, padx=8, pady=8)

        # Create dashboard frame first
        self.dashboard_frame = ttk.Frame(nb)
        
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
        self.most_active_frame = ttk.Frame(nb)
        self.trends_frame = ttk.Frame(nb)
        self.market_breadth_frame = ttk.Frame(nb)

        # Add dashboard tab first
        nb.add(self.dashboard_frame, text="Dashboard")
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
        nb.add(self.most_active_frame, text="Most Active")
        nb.add(self.trends_frame, text="Trend Analysis")
        nb.add(self.market_breadth_frame, text="Market Breadth")

        # Build dashboard tab first
        self._build_dashboard_tab()
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
        self._build_most_active_tab()
        self._build_52week_tab()
        self._build_52week_new_tab()
        self._build_minervini_tab()
        self._build_fractals_tab()
        self._build_bhav_export_tab()
        self._build_rsi_divergences_tab()
        self._build_trends_tab()
        self._build_market_breadth_tab()

        # sort state for treeviews
        self._sma_tree_sort_state = {}

        # Log area at bottom
        self.log = tk.Text(root, height=10, wrap="none")
        self.log.pack(fill="both", expand=False, padx=8, pady=(0,8))

        # Ensure app exits cleanly: intercept window close to attempt graceful shutdown
        try:
            root.protocol('WM_DELETE_WINDOW', self._on_app_close)
        except Exception:
            pass


    def append_log(self, msg: str):
        # Schedule UI update on the main thread to be thread-safe
        def _append():
            try:
                if hasattr(self, 'log') and self.log:
                    self.log.insert("end", msg + "\n")
                    # cap lines
                    lines = self.log.get("1.0", "end-1c").splitlines()
                    if len(lines) > LOG_MAX_LINES:
                        new = "\n".join(lines[-LOG_MAX_LINES:])
                        self.log.delete("1.0", "end")
                        self.log.insert("1.0", new)
                    self.log.see("end")
                else:
                    # Log widget not ready, print to console instead
                    print(f"LOG: {msg}")
            except Exception as e:
                # Fallback to console if GUI not available
                print(f"LOG: {msg} (GUI error: {e})")

        try:
            if hasattr(self, 'root') and self.root:
                self.root.after(0, _append)
            else:
                # Root not available, call directly
                _append()
        except Exception:
            # Root.after failed, call directly
            _append()

    def _on_app_close(self):
        """Attempt a graceful shutdown of background workers, then force-exit after a short delay.

        Many scanners spawn ThreadPoolExecutors which create non-daemon threads; when the
        Tk window is closed those threads can keep the process alive. We try to set common
        cancellation tokens and close matplotlib figures, then force-exit to ensure the
        process terminates.
        """
        try:
            self.append_log('Shutting down: requesting background tasks to cancel...')
        except Exception:
            pass
        # set known cancel tokens if present
        try:
            if hasattr(self, 'rsi_cancel_token') and isinstance(self.rsi_cancel_token, dict):
                self.rsi_cancel_token['cancel'] = True
        except Exception:
            pass
        try:
            if hasattr(self, '_fractals_cancel') and isinstance(self._fractals_cancel, dict):
                self._fractals_cancel['cancel'] = True
        except Exception:
            pass
        try:
            if hasattr(self, '_div_cancel') and isinstance(self._div_cancel, dict):
                self._div_cancel['cancel'] = True
        except Exception:
            pass
        try:
            if hasattr(self, '_bhav_cancel') and isinstance(self._bhav_cancel, dict):
                self._bhav_cancel['cancel'] = True
        except Exception:
            pass

        # try to close matplotlib figures
        try:
            import matplotlib.pyplot as _plt
            try:
                _plt.close('all')
            except Exception:
                pass
        except Exception:
            pass

        # destroy Tk root window and force process exit after short delay
        try:
            self.root.destroy()
        except Exception:
            pass
        try:
            # allow 0.5s for threads to notice cancel; then force exit
            self.root.after(500, lambda: os._exit(0))
        except Exception:
            # fallback immediate exit
            os._exit(0)

    # -------- Dashboard tab --------
    def _build_dashboard_tab(self):
        """Build the Dashboard tab."""
        try:
            # Create the dashboard tab directly in the existing frame
            dashboard_tab = DashboardTab(self.dashboard_frame)
            self.append_log("Dashboard tab initialized successfully")
        except Exception as e:
            # Fallback to a simple placeholder if import fails
            self.append_log(f"Error building dashboard tab: {e}")
            f = self.dashboard_frame
            ttk.Label(f, text=f"Dashboard tab failed to load: {e}").pack(padx=10, pady=10)

    # -------- Accumulation tab --------
    def _build_accum_tab(self):
        f = self.accum_frame
        ttk.Label(f, text="Date range (YYYY-MM-DD)").grid(row=0, column=0, sticky="w")
        self.acc_start = tk.StringVar(value="2025-08-01")
        self.acc_end = tk.StringVar(value="2025-10-10")
        ttk.Entry(f, textvariable=self.acc_start, width=12).grid(row=0, column=1)
    

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

    def _cancel_bhav_export(self):
        try:
            self._bhav_cancel['cancel'] = True
            self.append_log('BHAV export cancellation requested')
            try:
                self.root.after(0, lambda: self.bhav_status.set('Cancelling...'))
            except Exception:
                pass
        except Exception:
            pass

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
                        if hasattr(self, 'deliv_series_cb') and self.deliv_series_cb:
                            self.deliv_series_cb["values"] = vals
                            self.deliv_series.set("ALL")
                    except Exception:
                        pass
                try:
                    if hasattr(self, 'root') and self.root:
                        self.root.after(0, _set)
                    else:
                        _set()
                except Exception:
                    _set()
            except Exception as e:
                # if DB unavailable, leave default ALL and log
                self.append_log(f"Could not load series list: {e}")

        # Start background thread after a small delay to ensure GUI is ready
        def _start_load():
            threading.Thread(target=_load_series, daemon=True).start()
        
        if hasattr(self, 'root') and self.root:
            self.root.after(100, _start_load)  # Delay 100ms
        else:
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
                        if hasattr(self, 'ad_series_cb') and self.ad_series_cb:
                            self.ad_series_cb["values"] = vals
                            self.ad_series.set("ALL")
                    except Exception:
                        pass
                try:
                    if hasattr(self, 'root') and self.root:
                        self.root.after(0, _set)
                    else:
                        _set()
                except Exception:
                    _set()
            except Exception as e:
                self.append_log(f"Could not load Adv/Decl series list: {e}")

        # Start background thread after a small delay to ensure GUI is ready
        def _start_ad_load():
            threading.Thread(target=_load_ad_series, daemon=True).start()
        
        if hasattr(self, 'root') and self.root:
            self.root.after(200, _start_ad_load)  # Delay 200ms 
        else:
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

        # SMA50 counts buttons
        ttk.Button(f, text="Compute SMA50 Counts", command=self.run_sma50_scan).grid(row=8, column=0, pady=6)
        ttk.Button(f, text="Show SMA50 Counts Chart", command=self.show_sma50_counts_chart).grid(row=8, column=1, pady=6)

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

    def _build_fractals_tab(self):
        # Delegate building the Fractals tab to modular builder
        try:
            from gui.tabs.fractals import build_fractals_tab
            build_fractals_tab(self)
        except Exception:
            # fallback to original inline builder if import fails
            f = ttk.Frame(self.root.nametowidget('.!notebook')) if hasattr(self.root, 'nametowidget') else ttk.Frame()
            try:
                nb = None
                for child in self.root.winfo_children():
                    if isinstance(child, ttk.Notebook):
                        nb = child
                        break
                if nb is None:
                    nb = ttk.Notebook(self.root, style='Custom.TNotebook')
                    nb.pack(fill='both', expand=True)
                self.fractals_frame = ttk.Frame(nb)
                nb.add(self.fractals_frame, text='Fractals')
                f = self.fractals_frame
            except Exception:
                f = self.rsi_frame

            ttk.Label(f, text='Fractal RSI period').grid(row=0, column=0, sticky='w')
            self.frac_rsi_period = tk.IntVar(value=9)
            ttk.Entry(f, textvariable=self.frac_rsi_period, width=6).grid(row=0, column=1, sticky='w')

            ttk.Label(f, text='Workers').grid(row=0, column=2, sticky='w')
            self.frac_workers = tk.IntVar(value=4)
            ttk.Entry(f, textvariable=self.frac_workers, width=6).grid(row=0, column=3, sticky='w')

            ttk.Label(f, text='Days Back').grid(row=0, column=4, sticky='w')
            self.frac_days_back = tk.IntVar(value=30)
            ttk.Entry(f, textvariable=self.frac_days_back, width=6).grid(row=0, column=5, sticky='w')

            # Scan mode selection
            self.frac_scan_mode = tk.StringVar(value="optimized")
            ttk.Radiobutton(f, text="Quick Scan (Recent)", variable=self.frac_scan_mode, 
                           value="optimized").grid(row=1, column=0, sticky='w')
            ttk.Radiobutton(f, text="Full Scan (All History)", variable=self.frac_scan_mode, 
                           value="full").grid(row=1, column=1, columnspan=2, sticky='w')

            ttk.Button(f, text='Run Fractals Scan', command=self.run_fractals_scan).grid(row=2, column=0, pady=6)
            ttk.Button(f, text='Cancel Fractals', command=self._cancel_fractals).grid(row=2, column=1, pady=6)
            ttk.Button(f, text='Show Fractal Breaks', command=self.show_fractal_breaks).grid(row=2, column=2, pady=6)

            self.frac_progress = ttk.Progressbar(f, orient='horizontal', mode='determinate', length=400)
            self.frac_progress.grid(row=3, column=0, columnspan=6, pady=(4,8), sticky='we')
            self.frac_results = tk.Text(f, height=10, wrap='none')
            self.frac_results.grid(row=4, column=0, columnspan=6, sticky='nsew')
            f.grid_rowconfigure(4, weight=1)
            f.grid_columnconfigure(5, weight=1)

            # Treeview for fractals
            cols = ('symbol', 'fractal_date', 'fractal_type', 'fractal_high', 'fractal_low', 'center_rsi')
            tree_frame = ttk.Frame(f)
            tree_frame.grid(row=4, column=0, columnspan=6, sticky='nsew', pady=(6,0))
            f.grid_rowconfigure(4, weight=1)
            f.grid_columnconfigure(5, weight=1)

            self.frac_tree = ttk.Treeview(tree_frame, columns=cols, show='headings', height=12)
            for c in cols:
                self.frac_tree.heading(c, text=c)
                self.frac_tree.column(c, width=120, anchor='w')
            v = ttk.Scrollbar(tree_frame, orient='vertical', command=self.frac_tree.yview)
            h = ttk.Scrollbar(tree_frame, orient='horizontal', command=self.frac_tree.xview)
            self.frac_tree.configure(yscrollcommand=v.set, xscrollcommand=h.set)
            tree_frame.grid_rowconfigure(0, weight=1)
            tree_frame.grid_columnconfigure(0, weight=1)
            self.frac_tree.grid(row=0, column=0, sticky='nsew')
            v.grid(row=0, column=1, sticky='ns')
            h.grid(row=1, column=0, sticky='ew')

            self._fractals_cancel = {'cancel': False}

    def _build_rsi_divergences_tab(self):
        f = ttk.Frame(self.root.nametowidget('.!notebook')) if hasattr(self.root, 'nametowidget') else ttk.Frame()
        try:
            nb = self.root.nametowidget('.!notebook')
            nb.add(f, text='RSI Divergences')
        except Exception:
            pass

        ttk.Label(f, text='Compare last with past N fractals').grid(row=0, column=0, sticky='w')
        self.div_lookback = tk.IntVar(value=5)
        ttk.Entry(f, textvariable=self.div_lookback, width=6).grid(row=0, column=1, sticky='w')
        # SMA filter checkboxes (placed to the right)
        ttk.Label(f, text="SMA filters:").grid(row=0, column=4, sticky='w', padx=(12,0))
        self.div_sma_10 = tk.BooleanVar(value=False)
        self.div_sma_20 = tk.BooleanVar(value=False)
        self.div_sma_50 = tk.BooleanVar(value=False)
        ttk.Checkbutton(f, text='SMA10', variable=self.div_sma_10).grid(row=0, column=5, sticky='w')
        ttk.Checkbutton(f, text='SMA20', variable=self.div_sma_20).grid(row=0, column=6, sticky='w')
        ttk.Checkbutton(f, text='SMA50', variable=self.div_sma_50).grid(row=0, column=7, sticky='w')

        ttk.Label(f, text='Limit symbols (0=all)').grid(row=0, column=2, sticky='w')
        self.div_limit = tk.IntVar(value=0)
        ttk.Entry(f, textvariable=self.div_limit, width=6).grid(row=0, column=3, sticky='w')

        ttk.Button(f, text='Run Hidden Bullish Divergence Scan', command=self.run_divergence_scan).grid(row=1, column=0, pady=6)
        ttk.Button(f, text='Run Hidden Bearish Divergence Scan', command=self.run_divergence_scan_bearish).grid(row=1, column=1, pady=6)

        self.div_results = tk.Text(f, height=10, wrap='none')
        self.div_results.grid(row=2, column=0, columnspan=6, sticky='nsew')
        f.grid_rowconfigure(2, weight=1)
        f.grid_columnconfigure(5, weight=1)

        # treeview for signals
        cols = ('symbol', 'signal_date', 'signal_type', 'curr_center_close', 'curr_center_rsi', 'comp_fractal_date', 'comp_center_close', 'comp_center_rsi', 'buy_above_price', 'sell_below_price')
        tree_frame = ttk.Frame(f)
        tree_frame.grid(row=3, column=0, columnspan=6, sticky='nsew', pady=(6,0))
        f.grid_rowconfigure(3, weight=1)
        f.grid_columnconfigure(5, weight=1)

        self.div_tree = ttk.Treeview(tree_frame, columns=cols, show='headings', height=12)
        for c in cols:
            # make headings clickable for sorting
            def _make_sort(col):
                return lambda _col=col: self._sort_div_tree(_col)

            self.div_tree.heading(c, text=c, command=_make_sort(c))
            self.div_tree.column(c, width=120, anchor='w')
        v = ttk.Scrollbar(tree_frame, orient='vertical', command=self.div_tree.yview)
        h = ttk.Scrollbar(tree_frame, orient='horizontal', command=self.div_tree.xview)
        self.div_tree.configure(yscrollcommand=v.set, xscrollcommand=h.set)
        tree_frame.grid_rowconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)
        self.div_tree.grid(row=0, column=0, sticky='nsew')
        v.grid(row=0, column=1, sticky='ns')
        h.grid(row=1, column=0, sticky='ew')
        # open detail chart on double-click
        try:
            self.div_tree.bind("<Double-1>", self._on_divergence_row_double_click)
        except Exception:
            pass
        # sort state (column -> asc True/False) and currently-sorted column
        self._div_tree_sort_state = {}
        self._div_tree_sorted_col = None
        # cancel token for background divergence scans
        self._div_cancel = {'cancel': False}

    def _build_most_active_tab(self):
        """Build the Most Active tab: choose date and Top-N, show symbols ordered by turnover_lacs."""
        f = self.most_active_frame
        ttk.Label(f, text="As-of (YYYY-MM-DD, empty = latest)").grid(row=0, column=0, sticky="w")
        self.ma_asof = tk.StringVar(value="")
        ttk.Entry(f, textvariable=self.ma_asof, width=12).grid(row=0, column=1, sticky="w")

        ttk.Label(f, text="Top N").grid(row=0, column=2, sticky="w")
        self.ma_topn = tk.IntVar(value=20)
        ttk.Combobox(f, textvariable=self.ma_topn, values=[20,50,100,200], width=8).grid(row=0, column=3)

        ttk.Button(f, text="Show Most Active", command=self._show_most_active).grid(row=0, column=4, pady=6)

        # results treeview
        cols = ("symbol", "series", "trade_date", "close_price", "turnover_lacs", "ttl_trd_qnty")
        tree_frame = ttk.Frame(f)
        tree_frame.grid(row=1, column=0, columnspan=6, sticky="nsew", pady=(6,0))
        f.grid_rowconfigure(1, weight=1)
        f.grid_columnconfigure(0, weight=1)

        self.ma_tree = ttk.Treeview(tree_frame, columns=cols, show="headings", height=12)
        for c in cols:
            self.ma_tree.heading(c, text=c)
            self.ma_tree.column(c, width=120, anchor="w")

        # double-click to open detail chart
        try:
            self.ma_tree.bind("<Double-1>", self._on_most_active_row_double_click)
        except Exception:
            pass

        v = ttk.Scrollbar(tree_frame, orient="vertical", command=self.ma_tree.yview)
        h = ttk.Scrollbar(tree_frame, orient="horizontal", command=self.ma_tree.xview)
        self.ma_tree.configure(yscrollcommand=v.set, xscrollcommand=h.set)
        tree_frame.grid_rowconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)
        self.ma_tree.grid(row=0, column=0, sticky="nsew")
        v.grid(row=0, column=1, sticky="ns")
        h.grid(row=1, column=0, sticky="ew")

    def _show_most_active(self):
        """Query DB for top-N symbols by turnover_lacs for given date and populate the treeview."""
        def worker():
            try:
                import reporting_adv_decl as rad
                from sqlalchemy import text
                eng = rad.engine()
                asof = self.ma_asof.get().strip() or None
                topn = int(self.ma_topn.get() or 20)

                with eng.connect() as conn:
                    if not asof:
                        row = conn.execute(text("SELECT MAX(trade_date) FROM nse_equity_bhavcopy_full WHERE series='EQ'"))
                        latest = row.fetchone()[0]
                        if latest is None:
                            self.append_log('No trade_date found in BHAV table')
                            return
                        asof = pd.to_datetime(latest).strftime('%Y-%m-%d')

                    q = text("SELECT symbol, series, trade_date, close_price, turnover_lacs, ttl_trd_qnty FROM nse_equity_bhavcopy_full WHERE trade_date = :d AND series='EQ' ORDER BY turnover_lacs DESC LIMIT :n")
                    rows = conn.execute(q, {"d": asof, "n": topn}).fetchall()

                # schedule UI update
                def _populate():
                    try:
                        for i in self.ma_tree.get_children():
                            self.ma_tree.delete(i)
                        for r in rows:
                            # r: (symbol, series, trade_date, close_price, turnover_lacs, ttl_trd_qnty)
                            try:
                                dt = pd.to_datetime(r[2]).strftime('%Y-%m-%d')
                            except Exception:
                                dt = str(r[2])
                            vals = (r[0], r[1], dt, float(r[3]) if r[3] is not None else None, float(r[4]) if r[4] is not None else None, int(r[5]) if r[5] is not None else None)
                            self.ma_tree.insert('', 'end', values=vals)
                    except Exception as e:
                        self.append_log(f"Error populating Most Active tree: {e}")

                self.root.after(0, _populate)
            except Exception as e:
                import traceback
                tb = traceback.format_exc()
                self.append_log(f"Most Active error: {e}\n{tb}")

        threading.Thread(target=worker, daemon=True).start()

    def _sort_div_tree(self, col_name: str):
        """Sort the divergence Treeview by column. Toggles asc/desc on repeated clicks."""
        try:
            children = list(self.div_tree.get_children(''))
            if not children:
                return
            # get column index from defined columns
            cols = self.div_tree['columns']
            try:
                col_idx = list(cols).index(col_name)
            except ValueError:
                return

            # extract (item, value) pairs
            def _val(item):
                vals = self.div_tree.item(item, 'values') or []
                if col_idx < len(vals):
                    return vals[col_idx]
                return ''

            # determine current order and toggle
            asc = self._div_tree_sort_state.get(col_name, True)

            # update heading visuals: clear previous column indicator
            try:
                prev = self._div_tree_sorted_col
                if prev and prev != col_name:
                    try:
                        self.div_tree.heading(prev, text=prev)
                    except Exception:
                        pass
            except Exception:
                pass

            try:
                # attempt numeric sort where possible
                keyed = [(item, float(_val(item)) if _val(item) not in (None, '') else float('-inf')) for item in children]
            except Exception:
                # fallback to string sort
                keyed = [(item, str(_val(item)).lower() if _val(item) is not None else '') for item in children]

            keyed.sort(key=lambda x: x[1], reverse=not asc)

            # reinsert in sorted order
            for idx, (item, _) in enumerate(keyed):
                self.div_tree.move(item, '', idx)

            # toggle state
            self._div_tree_sort_state[col_name] = not asc
            # set visual indicator on this column
            try:
                arrow = '▲' if asc else '▼'
                self.div_tree.heading(col_name, text=f"{col_name} {arrow}")
                self._div_tree_sorted_col = col_name
            except Exception:
                pass
        except Exception:
            pass

    def _build_52week_tab(self):
        f = ttk.Frame(self.root.nametowidget('.!notebook')) if hasattr(self.root, 'nametowidget') else ttk.Frame()
        try:
            nb = self.root.nametowidget('.!notebook')
            nb.add(f, text='52 Week High/Low')
        except Exception:
            pass

        ttk.Label(f, text='Lookback days for recent 52-week hits (N)').grid(row=0, column=0, sticky='w')
        self.w52_lookback = tk.IntVar(value=30)
        ttk.Entry(f, textvariable=self.w52_lookback, width=6).grid(row=0, column=1, sticky='w')

        ttk.Button(f, text='Scan 52-week Highs (latest day)', command=lambda: self._run_52week_scan(mode='high', recent_n=0)).grid(row=1, column=0, pady=6)
        ttk.Button(f, text='Scan 52-week Lows (latest day)', command=lambda: self._run_52week_scan(mode='low', recent_n=0)).grid(row=1, column=1, pady=6)
        ttk.Button(f, text='Scan 52-week Highs/Lows (last N days)', command=lambda: self._run_52week_scan(mode='both', recent_n=self.w52_lookback.get())).grid(row=1, column=2, pady=6)
        ttk.Button(f, text='Upsert daily counts', command=self._upsert_daily_counts_gui).grid(row=1, column=3, pady=6)
        ttk.Button(f, text='Show counts chart', command=self._plot_daily_counts).grid(row=1, column=4, pady=6)
        ttk.Button(f, text='Backfill last 30 days counts', command=self._backfill_30_days_counts).grid(row=1, column=5, pady=6)
        ttk.Button(f, text='Backfill full counts', command=self._backfill_full_counts).grid(row=1, column=6, pady=6)

        self.w52_results = tk.Text(f, height=6, wrap='none')
        self.w52_results.grid(row=2, column=0, columnspan=6, sticky='nsew')
        f.grid_rowconfigure(2, weight=1)

        # progress bar for backfill operations
        self.w52_progress = ttk.Progressbar(f, orient='horizontal', mode='determinate', length=400)
        self.w52_progress.grid(row=4, column=0, columnspan=6, pady=(4,6), sticky='we')

        cols = ('symbol', 'type', 'signal_date', 'price', 'rsi')
        tree_frame = ttk.Frame(f)
        tree_frame.grid(row=3, column=0, columnspan=6, sticky='nsew', pady=(6,0))
        f.grid_rowconfigure(3, weight=1)
        f.grid_columnconfigure(5, weight=1)

        self.w52_tree = ttk.Treeview(tree_frame, columns=cols, show='headings', height=12)
        for c in cols:
            self.w52_tree.heading(c, text=c)
            self.w52_tree.column(c, width=100, anchor='w')
        v = ttk.Scrollbar(tree_frame, orient='vertical', command=self.w52_tree.yview)
        h = ttk.Scrollbar(tree_frame, orient='horizontal', command=self.w52_tree.xview)
        self.w52_tree.configure(yscrollcommand=v.set, xscrollcommand=h.set)
        tree_frame.grid_rowconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)
        self.w52_tree.grid(row=0, column=0, sticky='nsew')
        v.grid(row=0, column=1, sticky='ns')
        h.grid(row=1, column=0, sticky='ew')

        try:
            self.w52_tree.bind('<Double-1>', self._on_52week_row_double_click)
        except Exception:
            pass

        # chart area for daily counts
        self.w52_chart_frame = ttk.Frame(f)
        self.w52_chart_frame.grid(row=5, column=0, columnspan=6, sticky='nsew', pady=(6,0))
        f.grid_rowconfigure(5, weight=1)
        self.w52_counts_canvas = None

    def _build_52week_new_tab(self):
        f = ttk.Frame(self.root.nametowidget('.!notebook')) if hasattr(self.root, 'nametowidget') else ttk.Frame()
        try:
            nb = self.root.nametowidget('.!notebook')
            nb.add(f, text='52W Counts (New)')
        except Exception:
            pass

        ttk.Label(f, text='As-of (YYYY-MM-DD, empty = latest)').grid(row=0, column=0, sticky='w')
        self.w52v2_asof = tk.StringVar(value='')
        ttk.Entry(f, textvariable=self.w52v2_asof, width=12).grid(row=0, column=1, sticky='w')

        ttk.Label(f, text='Workers (parallel backfill)').grid(row=0, column=2, sticky='w')
        self.w52v2_workers = tk.IntVar(value=4)
        ttk.Entry(f, textvariable=self.w52v2_workers, width=6).grid(row=0, column=3, sticky='w')

        ttk.Button(f, text='Compute & Upsert (single day)', command=self._w52v2_compute_one).grid(row=1, column=0, pady=6)
        ttk.Button(f, text='Backfill last N days', command=self._w52v2_backfill_last_n).grid(row=1, column=1, pady=6)
        ttk.Button(f, text='Backfill full (all dates)', command=self._w52v2_backfill_full).grid(row=1, column=2, pady=6)

        self.w52v2_results = tk.Text(f, height=6, wrap='none')
        self.w52v2_results.grid(row=2, column=0, columnspan=6, sticky='nsew')
        f.grid_rowconfigure(2, weight=1)

        self.w52v2_progress = ttk.Progressbar(f, orient='horizontal', mode='determinate', length=400)
        self.w52v2_progress.grid(row=3, column=0, columnspan=6, pady=(4,6), sticky='we')

    def _w52v2_compute_one(self):
        def worker():
            try:
                import week52_v2 as wv
                import reporting_adv_decl as rad
                eng = rad.engine()
                asof = self.w52v2_asof.get().strip() or None
                import datetime
                ao = None
                if asof:
                    ao = datetime.datetime.strptime(asof, '%Y-%m-%d').date()
                with eng.connect() as conn:
                    res = wv.compute_and_upsert_counts(conn, as_of=ao) if hasattr(wv, 'compute_and_upsert_counts') else wv.compute_and_upsert_counts(eng, as_of=ao)
                msg = f"Upserted counts for {res['date']}: high={res['count_high']} low={res['count_low']}"
                self.append_log(msg)
                try:
                    self.w52v2_results.insert('end', msg + '\n')
                except Exception:
                    pass
            except Exception as e:
                import traceback
                tb = traceback.format_exc()
                self.append_log(f"52Wv2 compute error: {e}\n{tb}")
                try:
                    self.w52v2_results.insert('end', f"Error: {e}\n{tb}\n")
                except Exception:
                    pass

        threading.Thread(target=worker, daemon=True).start()

    def _w52v2_backfill_last_n(self):
        def worker():
            try:
                import week52_v2 as wv
                import reporting_adv_decl as rad
                eng = rad.engine()
                # prompt for N via existing lookback control if present, else default 30
                try:
                    n = int(self.w52_lookback.get())
                except Exception:
                    n = 30
                # get latest N dates
                with eng.connect() as conn:
                    rows = conn.execute(text("SELECT DISTINCT trade_date FROM nse_equity_bhavcopy_full WHERE series='EQ' ORDER BY trade_date DESC LIMIT :n"), {"n": n}).fetchall()
                    dates = [r[0] for r in rows]
                total = len(dates)
                attempted = succeeded = failed = 0
                for idx, d in enumerate(reversed(dates), start=1):
                    try:
                        with eng.connect() as conn:
                            res = wv.compute_and_upsert_counts(conn, as_of=d)
                        msg = f"Backfilled {idx}/{total}: {res['date']} -> high={res['count_high']} low={res['count_low']}"
                        attempted += 1
                        succeeded += 1
                    except Exception as e:
                        attempted += 1
                        failed += 1
                        msg = f"Backfill error for {d}: {e}"
                    self.append_log(msg)
                    try:
                        self.w52v2_results.insert('end', msg + '\n')
                    except Exception:
                        pass
                self.append_log('Backfill (last N) complete')
            except Exception as e:
                import traceback
                tb = traceback.format_exc()
                self.append_log(f"Backfill error: {e}\n{tb}")
        threading.Thread(target=worker, daemon=True).start()

    def _w52v2_backfill_full(self):
        def worker():
            try:
                import week52_v2 as wv
                import reporting_adv_decl as rad
                eng = rad.engine()
                workers = max(1, int(self.w52v2_workers.get() or 1))

                def progress(attempted, total):
                    try:
                        if total and total > 0:
                            self.w52v2_progress['maximum'] = total
                        self.w52v2_progress['value'] = attempted
                        self.append_log(f"Backfill progress: {attempted}/{total}")
                    except Exception:
                        pass

                res = wv.backfill_counts(eng, lookback_days=365, progress_cb=progress, parallel_workers=workers)
                msg = f"Backfill finished: attempted={res.get('attempted')} succeeded={res.get('succeeded')} failed={res.get('failed')}"
                self.append_log(msg)
                try:
                    self.w52v2_results.insert('end', msg + '\n')
                except Exception:
                    pass
            except Exception as e:
                import traceback
                tb = traceback.format_exc()
                self.append_log(f"Full backfill error: {e}\n{tb}")

        threading.Thread(target=worker, daemon=True).start()

    def _build_minervini_tab(self):
        f = ttk.Frame(self.root.nametowidget('.!notebook')) if hasattr(self.root, 'nametowidget') else ttk.Frame()
        try:
            nb = self.root.nametowidget('.!notebook')
            nb.add(f, text='Minervini Template')
        except Exception:
            pass

        ttk.Label(f, text='As-of (YYYY-MM-DD)').grid(row=0, column=0, sticky='w')
        self.min_asof = tk.StringVar(value='')
        ttk.Entry(f, textvariable=self.min_asof, width=12).grid(row=0, column=1, sticky='w')

        ttk.Label(f, text='RS Index').grid(row=0, column=2, sticky='w')
        self.min_rs_index = tk.StringVar(value='NIFTY 50')
        ttk.Entry(f, textvariable=self.min_rs_index, width=18).grid(row=0, column=3, sticky='w')

        ttk.Label(f, text='RS lookback days').grid(row=1, column=0, sticky='w')
        self.min_rs_lookback = tk.IntVar(value=252)
        ttk.Entry(f, textvariable=self.min_rs_lookback, width=8).grid(row=1, column=1, sticky='w')

        # Verbose option
        self.min_verbose = tk.BooleanVar(value=False)
        ttk.Checkbutton(f, text='Verbose (per-symbol)', variable=self.min_verbose).grid(row=1, column=4, sticky='w')

        ttk.Label(f, text='Limit (0=all)').grid(row=1, column=2, sticky='w')
        self.min_limit = tk.IntVar(value=0)
        ttk.Entry(f, textvariable=self.min_limit, width=8).grid(row=1, column=3, sticky='w')

        ttk.Button(f, text='Run Minervini Scan', command=self.run_minervini_scan).grid(row=2, column=0, pady=6)
        ttk.Label(f, text='CSV out').grid(row=2, column=1, sticky='w')
        self.min_out = tk.StringVar(value='')
        ttk.Entry(f, textvariable=self.min_out, width=30).grid(row=2, column=2, columnspan=2)
        ttk.Button(f, text='Browse', command=lambda: self._browse(self.min_out)).grid(row=2, column=4)
        # Ensure SMAs button
        ttk.Button(f, text='Ensure SMAs', command=self._ensure_smas_gui).grid(row=2, column=5, padx=6)

        # results area
        self.min_results = tk.Text(f, height=6, wrap='none')
        self.min_results.grid(row=3, column=0, columnspan=6, sticky='nsew')
        f.grid_rowconfigure(3, weight=1)

        cols = ('symbol', 'date', 'close', 'sma_50', 'sma_150', 'sma_200', 'rs_pct', '52w_low', '52w_high')
        tree_frame = ttk.Frame(f)
        tree_frame.grid(row=4, column=0, columnspan=6, sticky='nsew', pady=(6,0))
        f.grid_rowconfigure(4, weight=1)
        f.grid_columnconfigure(5, weight=1)

        self.min_tree = ttk.Treeview(tree_frame, columns=cols, show='headings', height=12)
        for c in cols:
            self.min_tree.heading(c, text=c)
            self.min_tree.column(c, width=110, anchor='w')
        v = ttk.Scrollbar(tree_frame, orient='vertical', command=self.min_tree.yview)
        h = ttk.Scrollbar(tree_frame, orient='horizontal', command=self.min_tree.xview)
        self.min_tree.configure(yscrollcommand=v.set, xscrollcommand=h.set)
        tree_frame.grid_rowconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)
        self.min_tree.grid(row=0, column=0, sticky='nsew')
        v.grid(row=0, column=1, sticky='ns')
        h.grid(row=1, column=0, sticky='ew')

        try:
            self.min_tree.bind('<Double-1>', self._on_minervini_row_double_click)
        except Exception:
            pass

    def run_minervini_scan(self):
        import minervini_screener as ms

        def worker():
            try:
                self.append_log('Starting Minervini scan...')
                asof = self.min_asof.get().strip() or None
                asof_arg = asof if asof else None
                limit = int(self.min_limit.get())
                lookback = int(self.min_rs_lookback.get())
                res = ms.screen_minervini(as_of=pd.to_datetime(asof_arg).date() if asof_arg else None,
                                         index_name=self.min_rs_index.get(), rs_lookback_days=lookback, limit=limit, verbose=self.min_verbose.get())
                if self.min_verbose.get():
                    df, vrows = res
                else:
                    df = res
                    vrows = []
                if df is None or df.empty:
                    self.append_log('Minervini: no candidates found')
                    # still display verbose logs if any
                    if vrows:
                        def _show_verbose():
                            try:
                                self.min_results.delete('1.0', 'end')
                                for vr in vrows:
                                    self.min_results.insert('end', f"{vr['symbol']}: {', '.join(vr['steps'])}\n")
                            except Exception:
                                pass
                        self.root.after(0, _show_verbose)
                    return
                # populate tree
                def _populate():
                    try:
                        for i in self.min_tree.get_children():
                            self.min_tree.delete(i)
                        for _, r in df.iterrows():
                            vals = (
                                r.get('symbol'),
                                pd.to_datetime(r.get('date')).strftime('%Y-%m-%d') if pd.notna(r.get('date')) else '',
                                float(r.get('close')) if pd.notna(r.get('close')) else None,
                                float(r.get('sma_50')) if pd.notna(r.get('sma_50')) else None,
                                float(r.get('sma_150')) if pd.notna(r.get('sma_150')) else None,
                                float(r.get('sma_200')) if pd.notna(r.get('sma_200')) else None,
                                float(r.get('rs_percentile')) if pd.notna(r.get('rs_percentile')) else None,
                                float(r.get('52w_low')) if pd.notna(r.get('52w_low')) else None,
                                float(r.get('52w_high')) if pd.notna(r.get('52w_high')) else None,
                            )
                            self.min_tree.insert('', 'end', values=vals)
                        # if verbose, append per-symbol logs below the tree
                        if vrows:
                            text_lines = []
                            for vr in vrows:
                                text_lines.append(f"{vr['symbol']}: {', '.join(vr['steps'])}")
                            self.min_results.delete('1.0', 'end')
                            self.min_results.insert('end', '\n'.join(text_lines))
                        out = self.min_out.get().strip()
                        if out:
                            df.to_csv(out, index=False)
                            self.append_log(f'Wrote CSV: {out}')
                    except Exception as e:
                        self.append_log(f'Error populating Minervini tree: {e}')
                self.root.after(0, _populate)
            except Exception as e:
                self.append_log(f'Minervini scan error: {e}')
                self.append_log(traceback.format_exc())

        threading.Thread(target=worker, daemon=True).start()

    def _ensure_smas_gui(self):
        """Run the SMA ensure helper and report results in the Minervini tab."""
        import minervini_screener as ms

        def worker():
            try:
                eng = ms.engine()
                with eng.connect() as conn:
                    # windows we'll ensure
                    wins = [50, 150, 200]
                    # first ensure columns, then compute missing rows
                    report = ms._ensure_sma_columns(conn, wins)
                    compute_report = ms.ensure_and_compute_smas(conn, wins, as_of=None, symbols=None, limit=0)

                # populate results
                msg_lines = []
                msg_lines.append(f"Existing columns: {', '.join(report.get('existing_columns', []))}")
                if report.get('added'):
                    msg_lines.append(f"Added columns: {', '.join(report['added'])}")
                if report.get('errors'):
                    for e in report['errors']:
                        msg_lines.append(f"Error adding {e.get('column')}: {e.get('error')}")
                # compute report
                msg_lines.append(f"Computed SMA for {len(compute_report.get('computed', []))} symbols")
                if compute_report.get('compute_errors'):
                    msg_lines.append(f"Compute errors: {len(compute_report.get('compute_errors', []))} (see log)")

                out = '\n'.join(msg_lines)
                def _ui():
                    try:
                        self.min_results.delete('1.0', 'end')
                        self.min_results.insert('end', out)
                        self.append_log('Ensure SMAs: done')
                    except Exception:
                        pass
                self.root.after(0, _ui)
            except Exception as e:
                self.append_log(f'Ensure SMAs error: {e}')

        threading.Thread(target=worker, daemon=True).start()

    def _on_minervini_row_double_click(self, event):
        try:
            item = self.min_tree.identify_row(event.y)
            if not item:
                return
            vals = self.min_tree.item(item, 'values')
            if not vals:
                return
            symbol = vals[0]
            date_s = vals[1]

            def _open():
                try:
                    win = tk.Toplevel(self.root)
                    win.title(f"{symbol} - Minervini Detail")
                    win.geometry('900x600')
                    lbl = ttk.Label(win, text=f"Loading chart for {symbol}...")
                    lbl.pack()

                    try:
                        import mplfinance as mpf
                        import matplotlib
                        # use the TkAgg backend for embedding in Tkinter so plots render interactively
                        try:
                            matplotlib.use('TkAgg')
                        except Exception:
                            # fallback to Agg if TkAgg unavailable
                            matplotlib.use('Agg')
                        import matplotlib.pyplot as plt
                        from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
                    except Exception:
                        lbl.config(text='mplfinance/matplotlib not available')
                        return

                    import reporting_adv_decl as rad
                    eng = rad.engine()
                    start = (pd.to_datetime(date_s) - pd.Timedelta(days=180)).strftime('%Y-%m-%d')
                    end = (pd.to_datetime(date_s) + pd.Timedelta(days=20)).strftime('%Y-%m-%d')
                    q = text("SELECT trade_date as dt, open_price as Open, high_price as High, low_price as Low, close_price as Close, ttl_trd_qnty as Volume FROM nse_equity_bhavcopy_full WHERE symbol = :s AND series = 'EQ' AND trade_date BETWEEN :a AND :b ORDER BY trade_date")
                    with eng.connect() as conn:
                        rows = conn.execute(q, {"s": symbol, "a": start, "b": end}).fetchall()
                    if not rows:
                        lbl.config(text='No price data for selected window')
                        return
                    df = pd.DataFrame(rows, columns=['dt','Open','High','Low','Close','Volume'])
                    df['dt'] = pd.to_datetime(df['dt'])
                    df = df.set_index('dt')

                    # compute RSI
                    period = 14
                    close = df['Close']
                    delta = close.diff()
                    up = delta.clip(lower=0)
                    down = -delta.clip(upper=0)
                    ma_up = up.ewm(span=period, adjust=False).mean()
                    ma_down = down.ewm(span=period, adjust=False).mean()
                    rsi = 100 - (100 / (1 + (ma_up / ma_down)))

                    # fetch SMA series for overlay if available
                    with eng.connect() as conn:
                        qmv = text("SELECT trade_date, sma_50, sma_150, sma_200 FROM moving_averages WHERE symbol = :s AND trade_date BETWEEN :a AND :b ORDER BY trade_date")
                        mvrows = conn.execute(qmv, {"s": symbol, "a": start, "b": end}).fetchall()
                    mv_df = pd.DataFrame(mvrows, columns=['trade_date','sma_50','sma_150','sma_200']) if mvrows else pd.DataFrame()
                    if not mv_df.empty:
                        mv_df['trade_date'] = pd.to_datetime(mv_df['trade_date'])
                        mv_df = mv_df.set_index('trade_date')

                    fig = mpf.figure(style='yahoo', figsize=(10, 6))
                    ax_price = fig.add_subplot(2,1,1)
                    ax_rsi = fig.add_subplot(2,1,2, sharex=ax_price)
                    try:
                        mpf.plot(df, type='candle', ax=ax_price, volume=False, show_nontrading=False)
                    except Exception:
                        ax_price.plot(df.index, df['Close'])

                    # plot SMA overlays if present
                    try:
                        if not mv_df.empty and 'sma_50' in mv_df.columns:
                            ax_price.plot(mv_df.index, mv_df['sma_50'], label='SMA50', color='tab:blue')
                        if not mv_df.empty and 'sma_150' in mv_df.columns:
                            ax_price.plot(mv_df.index, mv_df['sma_150'], label='SMA150', color='tab:green')
                        if not mv_df.empty and 'sma_200' in mv_df.columns:
                            ax_price.plot(mv_df.index, mv_df['sma_200'], label='SMA200', color='tab:purple')
                        ax_price.legend()
                    except Exception:
                        pass

                    ax_rsi.plot(df.index, rsi, color='tab:orange')
                    ax_rsi.set_ylim(0,100)
                    ax_rsi.axhline(80, color='red', linestyle='--', alpha=0.5)
                    ax_rsi.axhline(20, color='green', linestyle='--', alpha=0.5)

                    fig.autofmt_xdate()
                    canvas = FigureCanvasTkAgg(fig, master=win)
                    canvas.draw()
                    canvas.get_tk_widget().pack(fill='both', expand=True)
                    try:
                        plt.close(fig)
                    except Exception:
                        pass
                    lbl.destroy()
                except Exception as e:
                    self.append_log(f"Error opening Minervini chart: {e}")

            self.root.after(0, _open)
        except Exception:
            pass

    def _run_52week_scan(self, mode='high', recent_n=0):
        # mode: 'high', 'low', 'both'; recent_n: 0 for latest day only, >0 for last N days
        def worker():
            try:
                import reporting_adv_decl as rad
                eng = rad.engine()
                # determine latest trading day
                with eng.connect() as conn:
                    # derive latest BHAV date from EQ series only
                    drow = conn.execute(text("SELECT MAX(trade_date) FROM nse_equity_bhavcopy_full WHERE series='EQ'")).fetchone()
                    latest = drow[0]
                if not latest:
                    self.append_log('No trade_date found in BHAV')
                    return

                # build SQL to find 52-week highs/lows
                if recent_n and recent_n > 0:
                    # consider signals within last N days up to latest
                    start = (pd.to_datetime(latest) - pd.Timedelta(days=int(recent_n))).strftime('%Y-%m-%d')
                    date_cond = f"AND trade_date BETWEEN '{start}' AND '{pd.to_datetime(latest).strftime('%Y-%m-%d')}'"
                else:
                    # only latest day
                    date_cond = f"AND trade_date = '{pd.to_datetime(latest).strftime('%Y-%m-%d')}'"

                results = []
                with eng.connect() as conn:
                    # 52-week high = high_price >= rolling 252-day max of high_price (including today)
                    if mode in ('high', 'both'):
                        qh = text(f"SELECT b.symbol, b.trade_date, b.close_price, b.high_price FROM nse_equity_bhavcopy_full b JOIN (SELECT symbol, MAX(high_price) as max52 FROM (SELECT symbol, high_price, trade_date FROM nse_equity_bhavcopy_full WHERE trade_date BETWEEN DATE_SUB(:latest, INTERVAL 365 DAY) AND :latest) x GROUP BY symbol) m ON b.symbol = m.symbol AND b.high_price = m.max52 WHERE 1=1 {date_cond} ORDER BY b.symbol")
                        rows = conn.execute(qh, {"latest": pd.to_datetime(latest).strftime('%Y-%m-%d')}).fetchall()
                        for r in rows:
                            results.append({'symbol': r[0], 'type': '52W High', 'signal_date': pd.to_datetime(r[1]).date(), 'price': float(r[2]), 'rsi': None})
                    if mode in ('low', 'both'):
                        ql = text(f"SELECT b.symbol, b.trade_date, b.close_price, b.low_price FROM nse_equity_bhavcopy_full b JOIN (SELECT symbol, MIN(low_price) as min52 FROM (SELECT symbol, low_price, trade_date FROM nse_equity_bhavcopy_full WHERE trade_date BETWEEN DATE_SUB(:latest, INTERVAL 365 DAY) AND :latest) x GROUP BY symbol) m ON b.symbol = m.symbol AND b.low_price = m.min52 WHERE 1=1 {date_cond} ORDER BY b.symbol")
                        rows = conn.execute(ql, {"latest": pd.to_datetime(latest).strftime('%Y-%m-%d')}).fetchall()
                        for r in rows:
                            results.append({'symbol': r[0], 'type': '52W Low', 'signal_date': pd.to_datetime(r[1]).date(), 'price': float(r[2]), 'rsi': None})

                # fetch RSI for those symbols on signal date
                syms = sorted({r['symbol'] for r in results})
                if syms:
                    with eng.connect() as conn:
                        q = text("SELECT symbol, trade_date, rsi FROM nse_rsi_daily WHERE period = 14 AND symbol IN :syms")
                        rrows = conn.execute(q, {"syms": tuple(syms)}).fetchall()
                        rmap = {}
                        for rr in rrows:
                            rmap.setdefault(rr[0], {})[pd.to_datetime(rr[1]).date()] = float(rr[2]) if rr[2] is not None else None
                        for res in results:
                            res['rsi'] = rmap.get(res['symbol'], {}).get(res['signal_date'])

                # populate tree
                def _populate():
                    try:
                        for i in self.w52_tree.get_children():
                            self.w52_tree.delete(i)
                        for r in results:
                            vals = (r['symbol'], r['type'], r['signal_date'].strftime('%Y-%m-%d'), r['price'], r['rsi'])
                            self.w52_tree.insert('', 'end', values=vals)
                    except Exception as e:
                        self.append_log(f'Error populating 52-week tree: {e}')
                self.root.after(0, _populate)
            except Exception as e:
                self.append_log(f'52-week scan error: {e}')
                self.append_log(traceback.format_exc())

        import threading
        threading.Thread(target=worker, daemon=True).start()

    def _upsert_daily_counts_gui(self):
        def worker():
            try:
                # Use the newer week52_v2 implementation which opens fresh connections per write
                import week52_v2 as wv
                import reporting_adv_decl as rad
                eng = rad.engine()
                try:
                    res = wv.compute_and_upsert_counts(eng, as_of=None)
                    msg = f"Upserted daily counts for {res['date']}: high={res['count_high']}, low={res['count_low']}"
                    self.append_log(msg)
                except Exception as e:
                    import traceback
                    tb = traceback.format_exc()
                    msg = f"Upsert failed: {e}\n{tb}"
                    self.append_log(msg)
                def _ui():
                    try:
                        self.w52_results.insert('end', msg + '\n')
                    except Exception:
                        pass
                self.root.after(0, _ui)
            except Exception as e:
                self.append_log(f'Error upserting daily counts: {e}')
                self.append_log(traceback.format_exc())

        threading.Thread(target=worker, daemon=True).start()

    def _plot_daily_counts(self):
        try:
            import matplotlib
            try:
                matplotlib.use('TkAgg')
            except Exception:
                matplotlib.use('Agg')
            import matplotlib.pyplot as plt
            from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
        except Exception:
            self.append_log('matplotlib not available for plotting')
            return

        def worker():
            try:
                import reporting_adv_decl as rad
                eng = rad.engine()
                q = text('SELECT dt, count_high, count_low FROM daily_52w_counts ORDER BY dt')
                with eng.connect() as conn:
                    df = pd.read_sql(q, con=conn, parse_dates=['dt'])
                if df.empty:
                    self.append_log('No daily_52w_counts data to plot')
                    return

                fig, axes = plt.subplots(2, 1, figsize=(8,6), sharex=True)
                axes[0].plot(df['dt'], df['count_high'], label='52w Highs')
                axes[0].set_ylabel('count_high')
                axes[0].legend()
                axes[1].plot(df['dt'], df['count_low'], label='>=30% above 52w low', color='orange')
                axes[1].set_ylabel('count_low')
                axes[1].legend()

                def _ui():
                    try:
                        for w in self.w52_chart_frame.winfo_children():
                            w.destroy()
                        canvas = FigureCanvasTkAgg(fig, master=self.w52_chart_frame)
                        canvas.draw()
                        canvas.get_tk_widget().pack(fill='both', expand=True)
                        try:
                            plt.close(fig)
                        except Exception:
                            pass
                    except Exception as e:
                        self.append_log(f'Error embedding counts chart: {e}')
                self.root.after(0, _ui)
            except Exception as e:
                self.append_log(f'Plot daily counts error: {e}')
                self.append_log(traceback.format_exc())

        import threading
        threading.Thread(target=worker, daemon=True).start()

    def _backfill_30_days_counts(self):
        def worker():
            try:
                import reporting_adv_decl as rad
                import week52_scanner as w52
                eng = rad.engine()
                # determine available trading dates (use BHAV table)
                with eng.connect() as conn:
                    rows = conn.execute(text("SELECT DISTINCT trade_date FROM nse_equity_bhavcopy_full WHERE series='EQ' ORDER BY trade_date DESC LIMIT 60")).fetchall()
                    dates = [r[0] for r in rows]
                if not dates:
                    self.append_log('No BHAV dates found to backfill')
                    return
                # take last 30 available dates (most recent)
                dates = dates[:30]
                total = len(dates)
                for idx, d in enumerate(reversed(dates), start=1):
                    try:
                        with eng.connect() as conn:
                            res = w52.upsert_daily_52w_counts(conn, d)
                        msg = f"Backfilled {idx}/{total}: {res['date']} -> high={res['count_high']}, low={res['count_low']}"
                        self.append_log(msg)
                    except Exception as e:
                        import traceback
                        tb = traceback.format_exc()
                        msg = f"Backfill error for {d}: {e}\n{tb}"
                        self.append_log(msg)
                    try:
                        self.w52_results.insert('end', msg + '\n')
                    except Exception:
                        pass
                self.append_log('Backfill complete')
            except Exception as e:
                self.append_log(f'Backfill error: {e}')
                self.append_log(traceback.format_exc())

        import threading
        threading.Thread(target=worker, daemon=True).start()

    def _backfill_full_counts(self):
        """Backfill daily_52w_counts for all available BHAV trade dates using default lookback 365 days."""
        def worker():
            try:
                import reporting_adv_decl as rad
                import week52_scanner as w52
                eng = rad.engine()

                # progress callback: (attempted, total)
                def _progress(attempted, total):
                    try:
                        def _ui():
                            try:
                                # set maximum once
                                if total and total > 0:
                                    self.w52_progress['maximum'] = total
                                self.w52_progress['value'] = attempted
                                self.append_log(f"Backfill progress: {attempted}/{total}")
                                try:
                                    self.w52_results.insert('end', f"Progress: {attempted}/{total}\n")
                                except Exception:
                                    pass
                            except Exception:
                                pass
                        self.root.after(0, _ui)
                    except Exception:
                        pass

                with eng.connect() as conn:
                    self.append_log('Starting full backfill of daily 52-week counts (lookback_days=365)')
                    # ensure progress reset
                    def _reset():
                        try:
                            self.w52_progress['value'] = 0
                            self.w52_progress['maximum'] = 0
                        except Exception:
                            pass
                    self.root.after(0, _reset)

                    res = w52.backfill_daily_52w_counts_range(conn, lookback_days=365, progress_cb=_progress)

                msg = f"Backfill finished: attempted={res.get('attempted')} succeeded={res.get('succeeded')} failed={res.get('failed')}"
                self.append_log(msg)
                try:
                    self.w52_results.insert('end', msg + '\n')
                except Exception:
                    pass
                # ensure progressbar is full on completion
                def _done_ui():
                    try:
                        if res.get('attempted'):
                            self.w52_progress['value'] = res.get('attempted')
                            self.w52_progress['maximum'] = res.get('attempted')
                    except Exception:
                        pass
                self.root.after(0, _done_ui)
            except Exception as e:
                import traceback
                tb = traceback.format_exc()
                msg = f"Full backfill error: {e}\n{tb}"
                self.append_log(msg)
                try:
                    self.w52_results.insert('end', msg + '\n')
                except Exception:
                    pass

        import threading
        threading.Thread(target=worker, daemon=True).start()

    def _on_52week_row_double_click(self, event):
        try:
            item = self.w52_tree.identify_row(event.y)
            if not item:
                return
            vals = self.w52_tree.item(item, 'values')
            if not vals:
                return
            symbol = vals[0]
            typ = vals[1]
            date_s = vals[2]

            def _open():
                try:
                    win = tk.Toplevel(self.root)
                    win.title(f"{symbol} - 52W {typ} Detail")
                    win.geometry('900x600')
                    lbl = ttk.Label(win, text=f"Loading chart for {symbol}...")
                    lbl.pack()

                    try:
                        import mplfinance as mpf
                        import matplotlib
                        try:
                            matplotlib.use('TkAgg')
                        except Exception:
                            matplotlib.use('Agg')
                        import matplotlib.pyplot as plt
                        from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
                    except Exception:
                        lbl.config(text='mplfinance/matplotlib not available')
                        return

                    # fetch price window
                    import reporting_adv_decl as rad
                    eng = rad.engine()
                    start = (pd.to_datetime(date_s) - pd.Timedelta(days=180)).strftime('%Y-%m-%d')
                    end = (pd.to_datetime(date_s) + pd.Timedelta(days=20)).strftime('%Y-%m-%d')
                    q = text("SELECT trade_date as dt, open_price as Open, high_price as High, low_price as Low, close_price as Close, ttl_trd_qnty as Volume FROM nse_equity_bhavcopy_full WHERE symbol = :s AND series = 'EQ' AND trade_date BETWEEN :a AND :b ORDER BY trade_date")
                    with eng.connect() as conn:
                        rows = conn.execute(q, {"s": symbol, "a": start, "b": end}).fetchall()
                    if not rows:
                        lbl.config(text='No price data for selected window')
                        return
                    df = pd.DataFrame(rows, columns=['dt','Open','High','Low','Close','Volume'])
                    df['dt'] = pd.to_datetime(df['dt'])
                    df = df.set_index('dt')

                    # compute RSI
                    period = 14
                    close = df['Close']
                    delta = close.diff()
                    up = delta.clip(lower=0)
                    down = -delta.clip(upper=0)
                    ma_up = up.ewm(span=period, adjust=False).mean()
                    ma_down = down.ewm(span=period, adjust=False).mean()
                    rsi = 100 - (100 / (1 + (ma_up / ma_down)))

                    fig = mpf.figure(style='yahoo', figsize=(10, 6))
                    ax_price = fig.add_subplot(2,1,1)
                    ax_rsi = fig.add_subplot(2,1,2, sharex=ax_price)
                    try:
                        mpf.plot(df, type='candle', ax=ax_price, volume=False, show_nontrading=False)
                    except Exception:
                        ax_price.plot(df.index, df['Close'])
                    ax_rsi.plot(df.index, rsi, color='tab:orange')
                    ax_rsi.set_ylim(0,100)
                    ax_rsi.axhline(80, color='red', linestyle='--', alpha=0.5)
                    ax_rsi.axhline(20, color='green', linestyle='--', alpha=0.5)

                    # mark 52W level on price (use price from the tree row if present)
                    try:
                        price_level = float(vals[3])
                        ax_price.axhline(price_level, color='magenta', linestyle='--', alpha=0.8)
                        ax_price.annotate(f"{typ} {price_level}", xy=(pd.to_datetime(date_s), price_level), xytext=(5,5), textcoords='offset points', color='magenta')
                    except Exception:
                        pass

                    fig.autofmt_xdate()
                    canvas = FigureCanvasTkAgg(fig, master=win)
                    canvas.draw()
                    canvas.get_tk_widget().pack(fill='both', expand=True)
                    try:
                        plt.close(fig)
                    except Exception:
                        pass
                    lbl.destroy()
                except Exception as e:
                    self.append_log(f"Error opening 52-week chart: {e}")

            self.root.after(0, _open)
        except Exception:
            pass

    def _on_most_active_row_double_click(self, event):
        try:
            item = self.ma_tree.identify_row(event.y)
            if not item:
                return
            vals = self.ma_tree.item(item, 'values')
            if not vals:
                return
            symbol = vals[0]
            date_s = vals[2]

            def _open():
                try:
                    win = tk.Toplevel(self.root)
                    win.title(f"{symbol} - Most Active Detail")
                    win.geometry('1000x700')
                    lbl = ttk.Label(win, text=f"Loading chart for {symbol}...")
                    lbl.pack()

                    # plotting imports
                    try:
                        import mplfinance as mpf
                        import matplotlib
                        try:
                            matplotlib.use('TkAgg')
                        except Exception:
                            matplotlib.use('Agg')
                        import matplotlib.pyplot as plt
                        from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
                    except Exception:
                        lbl.config(text='mplfinance/matplotlib not available')
                        return

                    import reporting_adv_decl as rad
                    eng = rad.engine()

                    # prepare window around selected date
                    try:
                        as_dt = pd.to_datetime(date_s)
                    except Exception:
                        as_dt = pd.Timestamp.today()
                    start = (as_dt - pd.Timedelta(days=180)).strftime('%Y-%m-%d')
                    end = (as_dt + pd.Timedelta(days=20)).strftime('%Y-%m-%d')

                    q = text("SELECT trade_date as dt, open_price as Open, high_price as High, low_price as Low, close_price as Close, ttl_trd_qnty as Volume, turnover_lacs FROM nse_equity_bhavcopy_full WHERE symbol = :s AND series = 'EQ' AND trade_date BETWEEN :a AND :b ORDER BY trade_date")
                    with eng.connect() as conn:
                        rows = conn.execute(q, {"s": symbol, "a": start, "b": end}).fetchall()
                    if not rows:
                        lbl.config(text='No price data for selected window')
                        return

                    df = pd.DataFrame(rows, columns=['dt','Open','High','Low','Close','Volume','turnover_lacs'])
                    df['dt'] = pd.to_datetime(df['dt'])
                    df = df.set_index('dt')

                    # DEBUG: log raw dataframe shape, columns and a small sample to diagnose missing price data
                    try:
                        try:
                            cols = list(df.columns)
                        except Exception:
                            cols = None
                        self.append_log(f"[MostActivePlot] raw_rows={len(df)} columns={cols} index_dtype={getattr(df.index, 'dtype', type(df.index))} is_unique={getattr(df.index, 'is_unique', None)}")
                        try:
                            # show first few Close/turnover values (convert to Python types for logging)
                            sample = df.loc[:, [c for c in ('Close', 'turnover_lacs') if c in df.columns]].head(8)
                            s_close = sample['Close'].apply(lambda x: None if pd.isna(x) else float(x)).tolist() if 'Close' in sample.columns else []
                            s_turn = sample['turnover_lacs'].apply(lambda x: None if pd.isna(x) else float(x)).tolist() if 'turnover_lacs' in sample.columns else []
                            self.append_log(f"[MostActivePlot] sample_close={s_close} sample_turnover={s_turn}")
                            self.append_log(f"[MostActivePlot] non-null Close count={int(df['Close'].count()) if 'Close' in df.columns else 0}")
                        except Exception:
                            pass
                    except Exception:
                        pass

                    # compute RSI. Use period=9 as requested
                    period = 9
                    close = df['Close']
                    delta = close.diff()
                    up = delta.clip(lower=0)
                    down = -delta.clip(upper=0)
                    import numpy as np
                    if period and period > 0:
                        ma_up = up.ewm(span=period, adjust=False).mean()
                        ma_down = down.ewm(span=period, adjust=False).mean()
                    else:
                        # period <= 0 interpreted as no smoothing: use raw up/down values (equivalent to ewm span=1)
                        ma_up = up
                        ma_down = down

                    # avoid division by zero; compute RS and RSI safely
                    with np.errstate(divide='ignore', invalid='ignore'):
                        rs = ma_up / ma_down.replace({0: np.nan})
                        rsi = 100 - (100 / (1 + rs))
                        # when ma_down == 0 and ma_up > 0 -> RSI = 100; when ma_up == 0 -> RSI = 0
                        rsi = rsi.fillna(0)

                    # create figure with 3 rows: price (candles), turnover bar, RSI
                    fig = plt.figure(figsize=(10, 7))
                    gs = fig.add_gridspec(3, 1, height_ratios=[3, 1, 1], hspace=0.05)
                    ax_price = fig.add_subplot(gs[0, 0])
                    ax_turn = fig.add_subplot(gs[1, 0], sharex=ax_price)
                    ax_rsi = fig.add_subplot(gs[2, 0], sharex=ax_price)

                    try:
                        # Clean, robust plotting for price: try plot_df['Close'] then common fallbacks.
                        try:
                            df.index = pd.DatetimeIndex(df.index)
                        except Exception:
                            df.index = pd.to_datetime(df.index, errors='coerce')

                        plot_df = df.copy()
                        # select a close-like column safely (avoid Series truthiness with `or`)
                        try:
                            if 'Close' in plot_df.columns:
                                close_series = plot_df['Close']
                            elif 'close' in plot_df.columns:
                                close_series = plot_df['close']
                            else:
                                close_series = None
                        except Exception:
                            close_series = None
                        if close_series is not None:
                            plot_df['Close'] = pd.to_numeric(close_series, errors='coerce')
                        else:
                            plot_df['Close'] = pd.Series(dtype='float', index=plot_df.index)
                        plot_df = plot_df.dropna(subset=['Close']).sort_index()

                        try:
                            idx = plot_df.index
                            self.append_log(f"[MostActivePlot] line plot rows={len(plot_df)} index_dtype={getattr(idx, 'dtype', type(idx))} min={idx.min() if len(idx) else None} max={idx.max() if len(idx) else None} is_unique={idx.is_unique}")
                        except Exception:
                            pass

                        try:
                            if not plot_df.index.is_unique:
                                self.append_log('[MostActivePlot] Index not unique; collapsing duplicate dates by taking last')
                                plot_df = plot_df.groupby(plot_df.index).last().sort_index()
                                self.append_log(f"[MostActivePlot] after collapse rows={len(plot_df)}")
                        except Exception:
                            pass

                        # Plot using integer x positions so weekends/holidays do not create empty gaps
                        used_xs = False
                        try:
                            import numpy as np

                            if plot_df.empty:
                                # try fallback close column from original df
                                for col in ('Close', 'close', 'close_price', 'closePrice'):
                                    if col in df.columns:
                                        plot_df = pd.DataFrame({
                                            'Close': pd.to_numeric(df[col], errors='coerce'),
                                            'turnover_lacs': pd.to_numeric(df['turnover_lacs'], errors='coerce') if 'turnover_lacs' in df.columns else pd.Series(dtype='float')
                                        }, index=df.index).dropna(subset=['Close']).sort_index()
                                        break

                            if plot_df.empty:
                                ax_price.text(0.5, 0.5, 'No price data', transform=ax_price.transAxes, ha='center')
                            else:
                                # x positions for each available row (collapses weekends/holidays)
                                xs = np.arange(len(plot_df))
                                dates = plot_df.index
                                closes = plot_df['Close'].values
                                ax_price.plot(xs, closes, marker='o', linestyle='-', markersize=4, color='black')

                                # turnover bars (use available turnover column if present)
                                turns = None
                                if 'turnover_lacs' in plot_df.columns:
                                    turns_series = pd.to_numeric(plot_df['turnover_lacs'], errors='coerce')
                                elif 'turnover_lacs' in df.columns:
                                    turns_series = pd.to_numeric(df['turnover_lacs'], errors='coerce').reindex(plot_df.index)
                                else:
                                    turns_series = None

                                if turns_series is not None:
                                    # keep NaNs so we can color them gray; use 0 height for plotting
                                    turns_vals = turns_series.fillna(0).values
                                    # color NaN bars gray, others use blue
                                    try:
                                        colors = ['gray' if pd.isna(v) else 'tab:blue' for v in turns_series.values]
                                    except Exception:
                                        colors = 'tab:blue'
                                    ax_turn.bar(xs, turns_vals, color=colors, width=0.6)
                                    ax_turn.set_ylabel('turnover_lacs')
                                else:
                                    # fallback plot Volume if turnover not present
                                    if 'Volume' in plot_df.columns:
                                        vols = pd.to_numeric(plot_df['Volume'], errors='coerce').fillna(0).values
                                        ax_turn.bar(xs, vols, color='tab:blue', width=0.6)
                                        ax_turn.set_ylabel('qty')

                                # RSI: align to xs; rsi was computed from df (same index), reindex to plot_df
                                try:
                                    rsi_vals = rsi.reindex(plot_df.index).values
                                    ax_rsi.plot(xs, rsi_vals, color='tab:orange')
                                    ax_rsi.set_ylim(0, 100)
                                    ax_rsi.axhline(80, color='red', linestyle='--', alpha=0.5)
                                    ax_rsi.axhline(20, color='green', linestyle='--', alpha=0.5)
                                    ax_rsi.set_ylabel('RSI(9)')
                                except Exception:
                                    pass

                                # format x-axis with date labels at reasonable interval
                                try:
                                    import matplotlib.ticker as mticker
                                    # show up to 8 tick labels evenly spaced
                                    max_ticks = 8
                                    step = max(1, len(xs) // max_ticks)
                                    ticks = xs[::step]
                                    tick_labels = [d.strftime('%Y-%m-%d') for d in dates[::step]]
                                    ax_price.set_xticks(ticks)
                                    ax_price.set_xticklabels(tick_labels, rotation=45, ha='right')
                                except Exception:
                                    pass

                                ax_price.set_ylabel('Close')
                                ax_price.set_title(symbol)
                                used_xs = True
                        except Exception as e:
                            try:
                                self.append_log(f"Line plot failed for {symbol}: {e}")
                            except Exception:
                                pass
                    except Exception as e:
                        try:
                            self.append_log(f"Line plot failed for {symbol}: {e}")
                        except Exception:
                            pass
                        try:
                            # fallback: pick a close-like column safely
                            if 'Close' in df.columns:
                                col = pd.to_numeric(df['Close'], errors='coerce')
                            elif 'close' in df.columns:
                                col = pd.to_numeric(df['close'], errors='coerce')
                            elif 'close_price' in df.columns:
                                col = pd.to_numeric(df['close_price'], errors='coerce')
                            else:
                                col = None
                            if col is not None:
                                ax_price.plot(df.index, col, marker='o', linestyle='-', markersize=4)
                            else:
                                try:
                                    ax_price.text(0.5, 0.5, 'No price data', transform=ax_price.transAxes, ha='center')
                                except Exception:
                                    pass
                        except Exception:
                            try:
                                ax_price.text(0.5, 0.5, 'No price data', transform=ax_price.transAxes, ha='center')
                            except Exception:
                                pass
                    # show grid on price axis
                    try:
                        ax_price.grid(True, linestyle='--', alpha=0.5)
                    except Exception:
                        pass
                    # turnover bar chart (only if we didn't already draw using integer xs)
                    try:
                        if not used_xs:
                            if 'turnover_lacs' in df.columns:
                                ax_turn.bar(df.index, pd.to_numeric(df['turnover_lacs'], errors='coerce'), color='tab:blue')
                                ax_turn.set_ylabel('turnover_lacs')
                            else:
                                # fallback use Volume
                                ax_turn.bar(df.index, pd.to_numeric(df['Volume'], errors='coerce'), color='tab:blue')
                                ax_turn.set_ylabel('qty')
                            ax_turn.grid(True, linestyle='--', alpha=0.4)
                    except Exception:
                        pass

                    # RSI plot (only if not already plotted using integer xs)
                    try:
                        if not used_xs:
                            ax_rsi.plot(df.index, rsi, color='tab:orange')
                            ax_rsi.set_ylim(0, 100)
                            ax_rsi.axhline(80, color='red', linestyle='--', alpha=0.5)
                            ax_rsi.axhline(20, color='green', linestyle='--', alpha=0.5)
                            ax_rsi.set_ylabel('RSI(9)')
                            ax_rsi.grid(True, linestyle='--', alpha=0.4)
                    except Exception:
                        pass

                    # highlight the selected date with vertical lines across panels
                    try:
                        sel_dt = pd.to_datetime(date_s)
                        if used_xs:
                            # map selected datetime to integer x position if it's in plot_df
                            try:
                                pos = None
                                if sel_dt in plot_df.index:
                                    # find the integer position of sel_dt in the plotted dates
                                    pos = int(plot_df.index.get_indexer([sel_dt])[0])
                                if pos is not None and pos >= 0:
                                    for a in (ax_price, ax_turn, ax_rsi):
                                        a.axvline(pos, color='magenta', linestyle='--', alpha=0.8)
                            except Exception:
                                pass
                        else:
                            for a in (ax_price, ax_turn, ax_rsi):
                                a.axvline(sel_dt, color='magenta', linestyle='--', alpha=0.8)
                    except Exception:
                        pass

                    fig.autofmt_xdate()
                    canvas = FigureCanvasTkAgg(fig, master=win)
                    canvas.draw()
                    canvas.get_tk_widget().pack(fill='both', expand=True)
                    try:
                        plt.close(fig)
                    except Exception:
                        pass
                    lbl.destroy()
                except Exception as e:
                    self.append_log(f"Error opening Most Active chart: {e}")

            self.root.after(0, _open)
        except Exception:
            pass

    def run_divergence_scan(self):
        import rsi_divergences as rd

        def worker():
            try:
                eng = rd._ensure_engine()
                lookback = int(self.div_lookback.get())
                limit = int(self.div_limit.get())

                def _progress(c, t, m):
                    try:
                        self.append_log(f"[Divergence] {m}")
                        def _ui():
                            try:
                                self.div_results.delete('1.0', 'end')
                                self.div_results.insert('end', f"{m}\n{c}/{t}\n")
                            except Exception:
                                pass
                        self.root.after(0, _ui)
                    except Exception:
                        pass

                # collect SMA filters
                sma_filters = []
                try:
                    if self.div_sma_10.get(): sma_filters.append(10)
                    if self.div_sma_20.get(): sma_filters.append(20)
                    if self.div_sma_50.get(): sma_filters.append(50)
                except Exception:
                    sma_filters = []

                df = rd.scan_hidden_bullish_divergences(eng, lookback_fractals=lookback, progress_cb=_progress, limit=limit, sma_filters=sma_filters)
                if df is None or df.empty:
                    self.append_log('[Divergence] No signals found')
                    return
                # populate tree
                def _populate():
                    try:
                        for i in self.div_tree.get_children():
                            self.div_tree.delete(i)
                        for _, r in df.iterrows():
                            vals = (
                                r.get('symbol'),
                                pd.to_datetime(r.get('signal_date')).strftime('%Y-%m-%d') if pd.notna(r.get('signal_date')) else '',
                                r.get('signal_type'),
                                float(r.get('curr_center_close')) if pd.notna(r.get('curr_center_close')) else None,
                                float(r.get('curr_center_rsi')) if pd.notna(r.get('curr_center_rsi')) else None,
                                pd.to_datetime(r.get('comp_fractal_date')).strftime('%Y-%m-%d') if pd.notna(r.get('comp_fractal_date')) else '',
                                float(r.get('comp_center_close')) if pd.notna(r.get('comp_center_close')) else None,
                                float(r.get('comp_center_rsi')) if pd.notna(r.get('comp_center_rsi')) else None,
                                float(r.get('buy_above_price')) if pd.notna(r.get('buy_above_price')) else None,
                                float(r.get('sell_below_price')) if pd.notna(r.get('sell_below_price')) else None,
                            )
                            self.div_tree.insert('', 'end', values=vals)
                    except Exception as e:
                        self.append_log(f'Error populating divergence tree: {e}')
                self.root.after(0, _populate)
            except Exception as e:
                self.append_log(f'Error running divergence scan: {e}')
                self.append_log(traceback.format_exc())

        import threading
        threading.Thread(target=worker, daemon=True).start()

    def run_divergence_scan_bearish(self):
        import rsi_divergences as rd

        def worker():
            try:
                eng = rd._ensure_engine()
                lookback = int(self.div_lookback.get())
                limit = int(self.div_limit.get())

                def _progress(c, t, m):
                    try:
                        self.append_log(f"[Divergence-Bearish] {m}")
                        def _ui():
                            try:
                                self.div_results.delete('1.0', 'end')
                                self.div_results.insert('end', f"{m}\n{c}/{t}\n")
                            except Exception:
                                pass
                        self.root.after(0, _ui)
                    except Exception:
                        pass

                sma_filters = []
                try:
                    if self.div_sma_10.get(): sma_filters.append(10)
                    if self.div_sma_20.get(): sma_filters.append(20)
                    if self.div_sma_50.get(): sma_filters.append(50)
                except Exception:
                    sma_filters = []

                df = rd.scan_hidden_bearish_divergences(eng, lookback_fractals=lookback, progress_cb=_progress, limit=limit, sma_filters=sma_filters)
                if df is None or df.empty:
                    self.append_log('[Divergence-Bearish] No signals found')
                    return
                # populate tree
                def _populate():
                    try:
                        for i in self.div_tree.get_children():
                            self.div_tree.delete(i)
                        for _, r in df.iterrows():
                            vals = (
                                r.get('symbol'),
                                pd.to_datetime(r.get('signal_date')).strftime('%Y-%m-%d') if pd.notna(r.get('signal_date')) else '',
                                r.get('signal_type'),
                                float(r.get('curr_center_close')) if pd.notna(r.get('curr_center_close')) else None,
                                float(r.get('curr_center_rsi')) if pd.notna(r.get('curr_center_rsi')) else None,
                                pd.to_datetime(r.get('comp_fractal_date')).strftime('%Y-%m-%d') if pd.notna(r.get('comp_fractal_date')) else '',
                                float(r.get('comp_center_close')) if pd.notna(r.get('comp_center_close')) else None,
                                float(r.get('comp_center_rsi')) if pd.notna(r.get('comp_center_rsi')) else None,
                                float(r.get('buy_above_price')) if pd.notna(r.get('buy_above_price')) else None,
                                float(r.get('sell_below_price')) if pd.notna(r.get('sell_below_price')) else None,
                            )
                            self.div_tree.insert('', 'end', values=vals)
                    except Exception as e:
                        self.append_log(f'Error populating divergence tree (bearish): {e}')
                self.root.after(0, _populate)
            except Exception as e:
                self.append_log(f'Error running bearish divergence scan: {e}')
                self.append_log(traceback.format_exc())

        import threading
        threading.Thread(target=worker, daemon=True).start()

    def _cancel_fractals(self):
        try:
            self._fractals_cancel['cancel'] = True
            self.append_log('Fractals cancel requested')
        except Exception:
            pass

    def run_fractals_scan(self):
        import rsi_fractals as rf
        # Read tkinter-controlled parameters on the main thread before starting worker
        try:
            period = int(self.frac_rsi_period.get())
        except Exception:
            period = 9
        try:
            workers = max(1, int(self.frac_workers.get()))
        except Exception:
            workers = 4
        try:
            days_back = max(7, int(self.frac_days_back.get()))
        except Exception:
            days_back = 30
        
        scan_mode = self.frac_scan_mode.get()
        
        # reset cancel token on main thread
        try:
            self._fractals_cancel['cancel'] = False
        except Exception:
            self._fractals_cancel = {'cancel': False}

        def worker():
            try:
                eng = rf._ensure_engine()

                def _progress(c, t, m):
                    try:
                        # Enhanced logging with timestamp
                        import datetime
                        timestamp = datetime.datetime.now().strftime('%H:%M:%S')
                        self.append_log(f"[{timestamp}] [Fractal] {m}")
                        
                        def _ui():
                            try:
                                self.frac_results.delete('1.0', 'end')
                                
                                # Enhanced status display with better formatting
                                status_lines = []
                                
                                # Show current operation
                                status_lines.append(f"🔄 {m}")
                                
                                # Show progress if available
                                if t > 0:
                                    progress_pct = (c / t) * 100
                                    progress_bar = '█' * int(progress_pct / 5) + '░' * (20 - int(progress_pct / 5))
                                    status_lines.append(f"Progress: [{progress_bar}] {c}/{t} ({progress_pct:.1f}%)")
                                    
                                    # Update progress bar
                                    self.frac_progress['maximum'] = t
                                    self.frac_progress['value'] = c
                                else:
                                    status_lines.append("Initializing...")
                                
                                # Add scan details
                                if scan_mode == "optimized":
                                    status_lines.append(f"🚀 Quick Scan Mode (last {days_back} days)")
                                else:
                                    status_lines.append("📚 Full Historical Scan Mode")
                                
                                status_lines.append(f"⚙️ Workers: {workers} | RSI Period: {period}")
                                status_lines.append("")
                                status_lines.append(f"Time: {timestamp}")
                                
                                # Display all status lines
                                status_text = '\n'.join(status_lines)
                                self.frac_results.insert('end', status_text)
                                
                            except Exception as e:
                                # Fallback to simple display
                                self.frac_results.delete('1.0', 'end')
                                self.frac_results.insert('end', f"{m}\n{c}/{t}\n")
                        self.root.after(0, _ui)
                    except Exception:
                        pass

                # Use optimized scan by default, fall back to full scan if requested
                if scan_mode == "optimized":
                    self.append_log(f'[Fractal] Starting optimized scan (last {days_back} days)')
                    try:
                        rf.scan_and_upsert_fractals_optimized(eng, period=period, workers=workers, 
                                                             progress_cb=_progress, days_back=days_back)
                    except AttributeError:
                        # Fall back to original method if optimized version not available
                        self.append_log(f'[Fractal] Optimized scan not available, using full scan')
                        rf.scan_and_upsert_fractals(eng, period=period, workers=workers, progress_cb=_progress)
                else:
                    self.append_log('[Fractal] Starting full historical scan (this may take several minutes)')
                    rf.scan_and_upsert_fractals(eng, period=period, workers=workers, progress_cb=_progress)
                
                self.append_log('[Fractal] Scan finished')
                # load last N fractals into tree
                with eng.connect() as conn:
                    rows = conn.execute(text('SELECT * FROM nse_fractals ORDER BY fractal_date DESC LIMIT 1000')).fetchall()
                if not rows:
                    return
                df = pd.DataFrame(rows, columns=[c for c in rows[0]._fields])
                def _populate():
                    try:
                        for i in self.frac_tree.get_children():
                            self.frac_tree.delete(i)
                        for _, r in df.iterrows():
                            vals = (
                                r.get('symbol'),
                                pd.to_datetime(r.get('fractal_date')).strftime('%Y-%m-%d') if pd.notna(r.get('fractal_date')) else '',
                                r.get('fractal_type'),
                                float(r.get('fractal_high')) if pd.notna(r.get('fractal_high')) else None,
                                float(r.get('fractal_low')) if pd.notna(r.get('fractal_low')) else None,
                                float(r.get('center_rsi')) if pd.notna(r.get('center_rsi')) else None,
                            )
                            self.frac_tree.insert('', 'end', values=vals)
                    except Exception as e:
                        self.append_log(f'Error populating fractals tree: {e}')
                self.root.after(0, _populate)
            except Exception as e:
                self.append_log(f'Error running fractals scan: {e}')
                self.append_log(traceback.format_exc())

        threading.Thread(target=worker, daemon=True).start()

    def show_fractal_breaks(self):
        """Run fractal-breaks scan and show results in a Toplevel tree. Double-click a row to open chart."""
        # Use the service layer so GUI doesn't call DB modules directly
        try:
            from services.fractals_service import scan_fractal_breaks
        except Exception:
            scan_fractal_breaks = None

        def worker():
            try:
                df = None
                if scan_fractal_breaks is not None:
                    try:
                        df = scan_fractal_breaks()
                    except Exception:
                        df = None
                if df is None:
                    # fallback to direct module call
                    try:
                        import fractal_breaks as fb
                        eng = fb._ensure_engine()
                        df = fb.scan_fractal_breaks(eng)
                    except Exception:
                        df = None
                def _open():
                    try:
                        # Delegate UI construction to the fractals tab module
                        from gui.tabs.fractals import show_fractal_breaks_dialog
                        show_fractal_breaks_dialog(self, df)
                    except Exception as e:
                        self.append_log(f"[FractalBreaks] UI open error: {e}")
                # ensure pandas is available in this module scope
                import pandas as pd
                self.root.after(0, _open)
            except Exception as e:
                self.append_log(f"[FractalBreaks] Scan error: {e}")

        threading.Thread(target=worker, daemon=True).start()

    def _open_price_rsi_chart(self, symbol: str, days: int = 120, fractal_high=None, fractal_low=None, fractal_date=None):
        """Open a Toplevel showing price (close) and RSI for the given symbol over the last `days` days.

        Optional parameters fractal_high/fractal_low (floats) will be drawn as horizontal lines on the price chart.
        fractal_date (datetime.date) if provided will be marked with a vertical line.
        """
        import matplotlib.pyplot as plt
        from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
        # Prefer the tab's chart implementation (moved to gui.tabs.fractals) if available.
        try:
            from gui.tabs.fractals import open_price_rsi_chart as _open_in_tab
            _open_in_tab(self, symbol, days=days, fractal_high=fractal_high, fractal_low=fractal_low, fractal_date=fractal_date)
            return
        except Exception:
            # fall back to the legacy inline implementation below
            pass
        try:
            import rsi_fractals as rf
            eng = rf._ensure_engine()
        except Exception:
            try:
                import import_nifty_index as ini
                eng = ini.build_engine()
            except Exception:
                eng = None
        if eng is None:
            self.append_log('[FractalChart] No DB engine available')
            return

        def worker():
            try:
                with eng.connect() as conn:
                    # fetch recent OHLC
                    q = text("SELECT trade_date, close_price FROM nse_equity_bhavcopy_full WHERE symbol = :s AND series = 'EQ' ORDER BY trade_date DESC LIMIT :n")
                    rows = conn.execute(q, {"s": symbol, "n": days}).fetchall()
                if not rows:
                    self.append_log(f"[FractalChart] No BHAV rows for {symbol}")
                    return
                import pandas as pd
                df = pd.DataFrame(rows, columns=[c for c in rows[0]._fields])
                df['trade_date'] = pd.to_datetime(df['trade_date'])
                df = df.set_index('trade_date').sort_index()
                df['close'] = pd.to_numeric(df['close_price'], errors='coerce')

                # fetch RSI (period 9) from nse_rsi_daily
                with eng.connect() as conn:
                    q2 = text("SELECT trade_date, rsi FROM nse_rsi_daily WHERE symbol = :s AND period = :p AND trade_date BETWEEN :a AND :b ORDER BY trade_date")
                    a = df.index.min().strftime('%Y-%m-%d')
                    b = df.index.max().strftime('%Y-%m-%d')
                    rows2 = conn.execute(q2, {"s": symbol, "p": 9, "a": a, "b": b}).fetchall()
                rsi_df = pd.DataFrame(rows2, columns=[c for c in rows2[0]._fields]) if rows2 else pd.DataFrame()
                if not rsi_df.empty:
                    rsi_df['trade_date'] = pd.to_datetime(rsi_df['trade_date'])
                    rsi_df = rsi_df.set_index('trade_date').sort_index()

                # create figure
                fig, (ax_price, ax_rsi) = plt.subplots(2, 1, figsize=(8, 6), sharex=True, gridspec_kw={'height_ratios': [3, 1]})
                ax_price.plot(df.index, df['close'], marker='o', linestyle='-', color='black', label='Close')
                ax_price.set_ylabel('Close')
                ax_price.grid(True, linestyle='--', alpha=0.4)
                # mark fractal high/low if provided
                try:
                    added = False
                    if fractal_high is not None and not pd.isna(fractal_high):
                        ax_price.axhline(fractal_high, color='magenta', linestyle='--', alpha=0.9, label='Fractal High')
                        added = True
                    if fractal_low is not None and not pd.isna(fractal_low):
                        ax_price.axhline(fractal_low, color='gray', linestyle='--', alpha=0.9, label='Fractal Low')
                        added = True
                    # mark fractal date vertical line if present and within plotted range
                    if fractal_date is not None:
                        try:
                            # ensure fractal_date is a Timestamp or datetime.date compatible with index
                            fd = pd.to_datetime(fractal_date)
                            if fd in df.index:
                                ax_price.axvline(fd, color='purple', linestyle=':', alpha=0.7)
                                added = True
                        except Exception:
                            pass
                    if added:
                        try:
                            ax_price.legend(loc='upper left')
                        except Exception:
                            pass
                except Exception:
                    pass
                if not rsi_df.empty:
                    ax_rsi.plot(rsi_df.index, rsi_df['rsi'], color='tab:orange')
                    ax_rsi.set_ylim(0, 100)
                    ax_rsi.axhline(80, color='red', linestyle='--', alpha=0.5)
                    ax_rsi.axhline(20, color='green', linestyle='--', alpha=0.5)
                    ax_rsi.set_ylabel('RSI(9)')
                    ax_rsi.grid(True, linestyle='--', alpha=0.4)

                def _open():
                    try:
                        win = tk.Toplevel(self.root)
                        win.title(symbol + ' - Break Detail')
                        canvas = FigureCanvasTkAgg(fig, master=win)
                        canvas.draw()
                        canvas.get_tk_widget().pack(fill='both', expand=True)
                        try:
                            plt.close(fig)
                        except Exception:
                            pass
                    except Exception as e:
                        self.append_log(f"[FractalChart] UI error: {e}")

                self.root.after(0, _open)
            except Exception as e:
                self.append_log(f"[FractalChart] Error preparing chart for {symbol}: {e}")

        import threading
        threading.Thread(target=worker, daemon=True).start()

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

    def run_sma50_scan(self):
        """Run the SMA50 counts scan in a background thread and log progress to the indices results area."""
        import sma50_scanner as ss

        def worker():
            try:
                eng = ss._ensure_engine()

                def _progress(c, t, m):
                    try:
                        self.append_log(f"[SMA50] {m}")
                        def _ui():
                            try:
                                self.idx_results.delete('1.0', 'end')
                                self.idx_results.insert('end', f"{m}\n{c}/{t}\n")
                            except Exception:
                                pass
                        self.root.after(0, _ui)
                    except Exception:
                        pass

                start = self.bhav_start.get().strip() or None
                end = self.bhav_end.get().strip() or None
                self.append_log(f"[SMA50] Starting scan workers=8 start={start} end={end}")
                errors = ss.scan_and_upsert(eng, workers=8, progress_cb=_progress, start=start, end=end)
                self.append_log(f"[SMA50] Finished scan with {len(errors)} errors")
                def _done():
                    try:
                        self.idx_results.insert('end', f"Finished. Errors: {len(errors)}\n")
                    except Exception:
                        pass
                self.root.after(0, _done)
            except Exception as e:
                self.append_log(f"[SMA50] Scan error: {e}")
                self.append_log(traceback.format_exc())

        threading.Thread(target=worker, daemon=True).start()

    def show_sma50_counts_chart(self):
        """Open a Toplevel and show Nifty + SMA50 counts chart using sma50_scanner.plot_counts."""
        import sma50_scanner as ss
        import matplotlib.pyplot as plt
        from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

        def worker():
            try:
                eng = ss._ensure_engine()
                start = self.bhav_start.get().strip() or None
                end = self.bhav_end.get().strip() or None
                idx = self.rs_index.get().strip() or 'NIFTY 50'
                fig = ss.plot_counts(eng, start=start, end=end, index_name=idx)

                def _open():
                    try:
                        win = tk.Toplevel(self.root)
                        win.title(f"SMA50 Counts: {idx}")
                        canvas = FigureCanvasTkAgg(fig, master=win)
                        canvas.draw()
                        canvas.get_tk_widget().pack(fill='both', expand=True)
                        try:
                            plt.close(fig)
                        except Exception:
                            pass
                    except Exception as e:
                        self.append_log(f"[SMA50] Error showing chart: {e}")

                self.root.after(0, _open)
            except Exception as e:
                self.append_log(f"[SMA50] Chart error: {e}")

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
                        try:
                            matplotlib.use('TkAgg')
                        except Exception:
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
                            q = text("SELECT trade_date, close_price FROM nse_equity_bhavcopy_full WHERE symbol = :s AND series = 'EQ' AND trade_date <= :d ORDER BY trade_date DESC LIMIT 180")
                            rows = conn.execute(q, {"s": symbol, "d": self.rsi_end.get().strip() or date.today().strftime('%Y-%m-%d')}).fetchall()
                        if not rows:
                            lbl.config(text='No price data')
                            return
                        df = pd.DataFrame(rows, columns=['trade_date', 'close'])
                        df['trade_date'] = pd.to_datetime(df['trade_date'])
                        df = df.sort_values('trade_date')

                        # compute RSI(14)
                        period = 14
                        close = df['close'].sort_index() if 'trade_date' not in df.columns else df.sort_values('trade_date')['close']
                        # ensure index is datetime
                        try:
                            df['trade_date'] = pd.to_datetime(df['trade_date'])
                        except Exception:
                            pass
                        close = df['close']
                        delta = close.diff()
                        up = delta.clip(lower=0)
                        down = -delta.clip(upper=0)
                        ma_up = up.ewm(span=period, adjust=False).mean()
                        ma_down = down.ewm(span=period, adjust=False).mean()
                        rs = ma_up / ma_down
                        rsi = 100 - (100 / (1 + rs))

                        # create two subplots: price on top, RSI below
                        fig, (ax_price, ax_rsi) = plt.subplots(2, 1, figsize=(8, 6), sharex=True, gridspec_kw={'height_ratios': [3, 1]})
                        ax_price.plot(df['trade_date'], df['close'], label=symbol)
                        ax_price.set_title(f"{symbol} - last {len(df)} days")
                        ax_price.set_ylabel('Close')
                        ax_price.grid(True)

                        ax_rsi.plot(df['trade_date'], rsi, color='tab:orange', label='RSI(14)')
                        ax_rsi.set_ylim(0, 100)
                        ax_rsi.axhline(80, color='red', linestyle='--', alpha=0.7)
                        ax_rsi.axhline(20, color='green', linestyle='--', alpha=0.4)
                        ax_rsi.set_ylabel('RSI')

                        # find latest RSI 80-cross signal (crossing from below to >=80)
                        try:
                            cond = (rsi.shift(1) < 80) & (rsi >= 80)
                            sig_idxs = [i for i, v in enumerate(cond) if v]
                            if sig_idxs:
                                last_idx = sig_idxs[-1]
                                sig_date = df['trade_date'].iloc[last_idx]
                                sig_price = float(df['close'].iloc[last_idx])
                                sig_rsi = float(rsi.iloc[last_idx])
                                # mark on RSI
                                ax_rsi.scatter([sig_date], [sig_rsi], color='red', s=50, zorder=5)
                                ax_rsi.annotate(f"RSI80 {sig_rsi:.1f}", xy=(sig_date, sig_rsi), xytext=(5,5), textcoords='offset points', color='red')
                                # mark on price
                                ax_price.scatter([sig_date], [sig_price], color='red', s=60, zorder=5)
                                ax_price.annotate(f"RSI80 @ {sig_price:.2f}", xy=(sig_date, sig_price), xytext=(5,5), textcoords='offset points', color='red')
                                # draw horizontal line on price to show price level at signal
                                ax_price.axhline(sig_price, color='red', linestyle='--', alpha=0.5)
                        except Exception:
                            pass

                        fig.autofmt_xdate()

                        canvas = FigureCanvasTkAgg(fig, master=win)
                        canvas.draw()
                        canvas.get_tk_widget().pack(fill='both', expand=True)
                        try:
                            plt.close(fig)
                        except Exception:
                            pass
                        try:
                            plt.close(fig)
                        except Exception:
                            pass
                    except Exception as pe:
                        lbl.config(text=f'Error plotting: {pe}')
                except Exception:
                    pass
            self.root.after(0, _open)
        except Exception:
            pass

    def _on_divergence_row_double_click(self, event):
        # show candlestick + RSI and mark the current and comparison fractal dates
        try:
            item = self.div_tree.identify_row(event.y)
            if not item:
                return
            vals = self.div_tree.item(item, 'values')
            if not vals:
                return
            symbol = vals[0]
            # columns: ('symbol','signal_date','signal_type','curr_center_close','curr_center_rsi','comp_fractal_date',...)
            curr_date_s = vals[1]
            comp_date_s = vals[5]

            def _open():
                try:
                    win = tk.Toplevel(self.root)
                    win.title(f"{symbol} - Divergence Detail")
                    win.geometry('900x600')
                    lbl = ttk.Label(win, text=f"Loading chart for {symbol}...")
                    lbl.pack()

                    try:
                        import mplfinance as mpf
                        import matplotlib
                        try:
                            matplotlib.use('TkAgg')
                        except Exception:
                            matplotlib.use('Agg')
                        import matplotlib.pyplot as plt
                        from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
                    except Exception:
                        lbl.config(text='mplfinance/matplotlib not available')
                        return

                    # prepare date range around fractal dates
                    try:
                        a = parse_date(comp_date_s) if comp_date_s else None
                        b = parse_date(curr_date_s) if curr_date_s else None
                    except Exception:
                        a = None; b = None

                    # expand window: 90 days before earliest, 20 days after latest
                    try:
                        start = (a or b) - pd.Timedelta(days=90) if (a or b) else pd.Timestamp.today() - pd.Timedelta(days=180)
                        end = (b or a) + pd.Timedelta(days=20) if (b or a) else pd.Timestamp.today()
                        start_s = start.strftime('%Y-%m-%d')
                        end_s = end.strftime('%Y-%m-%d')
                    except Exception:
                        start_s = None; end_s = None

                    # fetch OHLCV
                    try:
                        import reporting_adv_decl as rad
                        from sqlalchemy import text
                        eng = rad.engine()
                    except Exception:
                        eng = None
                    if not eng:
                        lbl.config(text='No DB engine available')
                        return

                    q = text("SELECT trade_date as dt, open_price as Open, high_price as High, low_price as Low, close_price as Close, ttl_trd_qnty as Volume FROM nse_equity_bhavcopy_full WHERE symbol = :s AND series = 'EQ' AND trade_date BETWEEN :a AND :b ORDER BY trade_date")
                    with eng.connect() as conn:
                        rows = conn.execute(q, {"s": symbol, "a": start_s, "b": end_s}).fetchall()
                    if not rows:
                        lbl.config(text='No price data for selected window')
                        return

                    df = pd.DataFrame(rows, columns=['dt','Open','High','Low','Close','Volume'])
                    df['dt'] = pd.to_datetime(df['dt'])
                    df = df.set_index('dt')

                    # compute RSI (14)
                    period = 14
                    close = df['Close']
                    delta = close.diff()
                    up = delta.clip(lower=0)
                    down = -delta.clip(upper=0)
                    ma_up = up.ewm(span=period, adjust=False).mean()
                    ma_down = down.ewm(span=period, adjust=False).mean()
                    rs = ma_up / ma_down
                    rsi = 100 - (100 / (1 + rs))

                    # create figure with two subplots
                    fig = mpf.figure(style='yahoo', figsize=(10, 6))
                    ax_price = fig.add_subplot(2, 1, 1)
                    ax_rsi = fig.add_subplot(2, 1, 2, sharex=ax_price)

                    try:
                        mpf.plot(df, type='candle', ax=ax_price, volume=False, show_nontrading=False)
                    except Exception:
                        # fallback simpler plot
                        ax_price.plot(df.index, df['Close'], label=symbol)

                    ax_rsi.plot(df.index, rsi, color='tab:orange')
                    ax_rsi.set_ylim(0, 100)
                    ax_rsi.axhline(30, color='green', linestyle='--', alpha=0.5)
                    ax_rsi.axhline(70, color='red', linestyle='--', alpha=0.5)

                    # Overlay selected SMAs on the price chart. Prefer precomputed values from moving_averages,
                    # otherwise compute from the Close series.
                    try:
                        sma_windows = []
                        try:
                            if self.div_sma_10.get(): sma_windows.append(10)
                            if self.div_sma_20.get(): sma_windows.append(20)
                            if self.div_sma_50.get(): sma_windows.append(50)
                        except Exception:
                            sma_windows = []

                        if sma_windows:
                            # try reading moving_averages for this symbol and date range
                            try:
                                ma_cols = ', '.join([f'sma_{w}' for w in sma_windows])
                                qma = text(f"SELECT trade_date, {ma_cols} FROM moving_averages WHERE symbol = :s AND trade_date BETWEEN :a AND :b ORDER BY trade_date")
                                with eng.connect() as conn:
                                    ma_rows = conn.execute(qma, {"s": symbol, "a": start_s, "b": end_s}).fetchall()
                                if ma_rows:
                                    ma_df = pd.DataFrame(ma_rows, columns=['trade_date'] + [f'sma_{w}' for w in sma_windows])
                                    ma_df['trade_date'] = pd.to_datetime(ma_df['trade_date'])
                                    ma_df = ma_df.set_index('trade_date')
                                    # align to price df index (forward-fill missing)
                                    ma_df = ma_df.reindex(df.index, method='ffill')
                                    colors = {10: 'tab:blue', 20: 'tab:green', 50: 'tab:purple'}
                                    for w in sma_windows:
                                        col = f'sma_{w}'
                                        if col in ma_df.columns:
                                            ax_price.plot(ma_df.index, ma_df[col], label=f'SMA{w}', color=colors.get(w, None), linewidth=1.25)
                                else:
                                    raise Exception('no_ma')
                            except Exception:
                                # fallback: compute rolling SMA from Close
                                colors = {10: 'tab:blue', 20: 'tab:green', 50: 'tab:purple'}
                                for w in sma_windows:
                                    sma_series = df['Close'].rolling(window=w).mean()
                                    ax_price.plot(df.index, sma_series, label=f'SMA{w}', color=colors.get(w, None), linewidth=1.0, linestyle='--')
                            try:
                                ax_price.legend(loc='upper left')
                            except Exception:
                                pass
                    except Exception:
                        pass

                    # mark fractal dates
                    def _mark_date(dt_s, price_ax, rsi_ax, label, color='blue'):
                        try:
                            if not dt_s:
                                return
                            dt = pd.to_datetime(dt_s)
                            if dt not in df.index:
                                # find nearest
                                nearest = df.index.get_indexer([dt], method='nearest')
                                if len(nearest) and nearest[0] >= 0:
                                    dt = df.index[nearest[0]]
                                else:
                                    return
                            price = df.at[dt, 'Close']
                            rsi_val = float(rsi.loc[dt]) if dt in rsi.index else None
                            price_ax.scatter([dt], [price], color=color, s=60, zorder=5)
                            price_ax.annotate(label, xy=(dt, price), xytext=(5,5), textcoords='offset points', color=color)
                            if rsi_val is not None:
                                rsi_ax.scatter([dt], [rsi_val], color=color, s=40, zorder=5)
                                rsi_ax.annotate(f"{rsi_val:.1f}", xy=(dt, rsi_val), xytext=(5,5), textcoords='offset points', color=color)
                        except Exception:
                            pass

                    _mark_date(comp_date_s, ax_price, ax_rsi, 'comp', color='purple')
                    _mark_date(curr_date_s, ax_price, ax_rsi, 'curr', color='blue')

                    # draw connecting line on RSI between comp and curr (if both available)
                    try:
                        if comp_date_s and curr_date_s:
                            dtc = pd.to_datetime(comp_date_s)
                            dtt = pd.to_datetime(curr_date_s)
                            # find nearest available dates in df
                            idx_c = df.index.get_indexer([dtc], method='nearest')
                            idx_t = df.index.get_indexer([dtt], method='nearest')
                            if len(idx_c) and len(idx_t) and idx_c[0] >= 0 and idx_t[0] >= 0:
                                dta = df.index[idx_c[0]]
                                dtb = df.index[idx_t[0]]
                                if dta in rsi.index and dtb in rsi.index:
                                    rsi_a = float(rsi.loc[dta])
                                    rsi_b = float(rsi.loc[dtb])
                                    ax_rsi.plot([dta, dtb], [rsi_a, rsi_b], color='black', linestyle='-', linewidth=1.5, alpha=0.8)
                    except Exception:
                        pass

                    # draw connecting line on price between comp and curr (if both available)
                    try:
                        if comp_date_s and curr_date_s:
                            dtc = pd.to_datetime(comp_date_s)
                            dtt = pd.to_datetime(curr_date_s)
                            idx_c = df.index.get_indexer([dtc], method='nearest')
                            idx_t = df.index.get_indexer([dtt], method='nearest')
                            if len(idx_c) and len(idx_t) and idx_c[0] >= 0 and idx_t[0] >= 0:
                                dta = df.index[idx_c[0]]
                                dtb = df.index[idx_t[0]]
                                if dta in df.index and dtb in df.index:
                                    price_a = float(df.at[dta, 'Close'])
                                    price_b = float(df.at[dtb, 'Close'])
                                    ax_price.plot([dta, dtb], [price_a, price_b], color='black', linestyle='--', linewidth=1.25, alpha=0.8)
                    except Exception:
                        pass

                    fig.autofmt_xdate()

                    # embed in Tk
                    canvas = FigureCanvasTkAgg(fig, master=win)
                    canvas.draw()
                    canvas.get_tk_widget().pack(fill='both', expand=True)
                    try:
                        plt.close(fig)
                    except Exception:
                        pass
                    lbl.destroy()
                except Exception as e:
                    self.append_log(f"Error opening divergence chart: {e}")

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
                    rows = conn.execute(text("SELECT DISTINCT symbol FROM nse_equity_bhavcopy_full WHERE series = 'EQ' ORDER BY symbol"))
                    syms = [r[0] for r in rows if r[0]]
                def _set():
                    try:
                        if hasattr(self, 'candle_sym_cb') and self.candle_sym_cb:
                            self.candle_sym_cb["values"] = syms
                            if syms:
                                self.candle_symbol.set(syms[0])
                    except Exception:
                        pass
                try:
                    if hasattr(self, 'root') and self.root:
                        self.root.after(0, _set)
                    else:
                        _set()
                except Exception:
                    _set()
            except Exception as e:
                self.append_log(f"Could not load symbol list: {e}")

        # Start background thread after a small delay to ensure GUI is ready
        def _start_symbols_load():
            threading.Thread(target=_load_symbols, daemon=True).start()
        
        if hasattr(self, 'root') and self.root:
            self.root.after(300, _start_symbols_load)  # Delay 300ms 
        else:
            threading.Thread(target=_load_symbols, daemon=True).start()

    # -------- BHAV Export tab --------
    def _build_bhav_export_tab(self):
        f = ttk.Frame(self.root.nametowidget('.!notebook')) if hasattr(self.root, 'nametowidget') else ttk.Frame()
        try:
            # insert near the end
            nb = self.root.nametowidget('.!notebook')
            nb.add(f, text="BHAV Export")
        except Exception:
            pass

        ttk.Label(f, text="Series").grid(row=0, column=0, sticky="w")
        self.bhav_series = tk.StringVar(value="EQ")
        ttk.Entry(f, textvariable=self.bhav_series, width=8).grid(row=0, column=1)

        ttk.Label(f, text="Date from (YYYY-MM-DD)").grid(row=1, column=0, sticky="w")
        self.bhav_from = tk.StringVar(value="")
        ttk.Entry(f, textvariable=self.bhav_from, width=12).grid(row=1, column=1)
        ttk.Label(f, text="Date to (YYYY-MM-DD)").grid(row=1, column=2, sticky="w")
        self.bhav_to = tk.StringVar(value="")
        ttk.Entry(f, textvariable=self.bhav_to, width=12).grid(row=1, column=3)

        ttk.Label(f, text="Target folder").grid(row=2, column=0, sticky="w")
        self.bhav_folder = tk.StringVar(value="")
        ttk.Entry(f, textvariable=self.bhav_folder, width=40).grid(row=2, column=1, columnspan=2)
        ttk.Button(f, text="Browse", command=lambda: self._browse(self.bhav_folder)).grid(row=2, column=3)

        self.bhav_per_symbol = tk.BooleanVar(value=True)
        ttk.Checkbutton(f, text="Export one CSV per symbol (Symbol.csv)", variable=self.bhav_per_symbol).grid(row=3, column=0, columnspan=3, sticky="w")

        # progress bar and cancel
        self.bhav_progress = ttk.Progressbar(f, orient='horizontal', mode='determinate', length=400)
        self.bhav_progress.grid(row=4, column=0, columnspan=3, pady=(6,2))
        self.bhav_status = tk.StringVar(value="Idle")
        ttk.Label(f, textvariable=self.bhav_status).grid(row=4, column=3, sticky='w')

        self._bhav_cancel = {'cancel': False}
        ttk.Button(f, text="Run BHAV Export", command=self.run_bhav_export).grid(row=5, column=0, pady=8)
        ttk.Button(f, text="Cancel", command=self._cancel_bhav_export).grid(row=5, column=1, pady=8)

    def run_bhav_export(self):
        def worker():
            try:
                folder = self.bhav_folder.get().strip()
                if not folder:
                    messagebox.showerror("Folder required", "Please select a target folder to save BHAV CSVs")
                    return
                outp = Path(folder)
                outp.mkdir(parents=True, exist_ok=True)

                series = (self.bhav_series.get() or 'EQ').strip()
                dt_from = self.bhav_from.get().strip() or None
                dt_to = self.bhav_to.get().strip() or None

                # build query to fetch distinct symbols for the chosen series
                from sqlalchemy import create_engine
                try:
                    # prefer existing engine helper
                    from import_nifty_index import build_engine
                    eng = build_engine()
                except Exception:
                    try:
                        from rsi_cross_scanner import _ensure_engine
                        eng = _ensure_engine()
                    except Exception:
                        eng = None

                if not eng:
                    messagebox.showerror("DB engine", "No DB engine available to fetch BHAV data")
                    return

                self.append_log(f"Starting BHAV export (series={series}) to {folder}")
                with eng.connect() as conn:
                    # fetch symbols for the series
                    rows = conn.execute(text("SELECT DISTINCT symbol FROM nse_equity_bhavcopy_full WHERE series = :s ORDER BY symbol"), {"s": series}).fetchall()
                    syms = [r[0] for r in rows if r[0]]

                total = len(syms)
                self.append_log(f"Found {total} symbols for series {series}")
                # initialize progress
                try:
                    self.root.after(0, lambda: self.bhav_progress.configure(maximum=total, value=0))
                    self.root.after(0, lambda: self.bhav_status.set(f"0/{total}"))
                    self._bhav_cancel['cancel'] = False
                except Exception:
                    pass

                import csv
                with eng.connect() as conn:
                    for i, sym in enumerate(syms, start=1):
                        if self._bhav_cancel.get('cancel'):
                            self.append_log('BHAV export cancelled by user')
                            break
                        # fetch rows for symbol with optional date filters
                        q = "SELECT trade_date, symbol, series, open_price, high_price, low_price, close_price, ttl_trd_qnty FROM nse_equity_bhavcopy_full WHERE symbol = :s AND series = :ser"
                        params = {"s": sym, "ser": series}
                        if dt_from and dt_to:
                            q += " AND trade_date BETWEEN :a AND :b"
                            params.update({"a": dt_from, "b": dt_to})
                        elif dt_from:
                            q += " AND trade_date >= :a"
                            params.update({"a": dt_from})
                        elif dt_to:
                            q += " AND trade_date <= :b"
                            params.update({"b": dt_to})
                        q += " ORDER BY trade_date"

                        rows = conn.execute(text(q), params).fetchall()
                        if not rows:
                            continue
                        # write per-symbol CSV with requested column order
                        fname = outp.joinpath(f"{sym}.csv")
                        header = ["Symbol", "Date", "Series", "Open", "High", "Low", "Close", "ttl_traded_qnty"]
                        with open(fname, 'w', newline='', encoding='utf-8') as fh:
                            writer = csv.writer(fh)
                            writer.writerow(header)
                            for r in rows:
                                # r: (trade_date, symbol, series, open_price, high_price, low_price, close_price, ttl_trd_qnty)
                                dt = r[0]
                                symv = r[1]
                                serv = r[2]
                                op = r[3]
                                hi = r[4]
                                lo = r[5]
                                cl = r[6]
                                qty = r[7]
                                # format date as ISO (YYYY-MM-DD)
                                try:
                                    dts = pd.to_datetime(dt).date().isoformat()
                                except Exception:
                                    dts = str(dt)
                                writer.writerow([symv, dts, serv, op, hi, lo, cl, qty])

                        self.append_log(f"[{i}/{total}] Wrote {len(rows)} rows -> {fname}")
                        try:
                            self.root.after(0, lambda v=i: self.bhav_progress.configure(value=v))
                            self.root.after(0, lambda v=i, t=total: self.bhav_status.set(f"{v}/{t}"))
                        except Exception:
                            pass

                if not self._bhav_cancel.get('cancel'):
                    self.append_log("BHAV export completed")
                else:
                    self.append_log("BHAV export stopped (cancelled)")
            except Exception as e:
                self.append_log(f"BHAV export error: {e}")
                self.append_log(traceback.format_exc())

        threading.Thread(target=worker, daemon=True).start()

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
                q = text("SELECT trade_date as dt, open_price as Open, high_price as High, low_price as Low, close_price as Close, ttl_trd_qnty as Volume FROM nse_equity_bhavcopy_full WHERE symbol=:s AND series='EQ' AND trade_date BETWEEN :a AND :b ORDER BY trade_date")
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

    def _build_trends_tab(self):
        """Build the Trends Analysis tab using the modular trends tab."""
        try:
            from gui.tabs.trends import TrendsTab
            # Create the trends tab directly in the existing frame
            trends_tab = TrendsTab(self.trends_frame, self)
            self.append_log("Trends Analysis tab initialized successfully")
        except Exception as e:
            # Fallback to a simple placeholder if import fails
            self.append_log(f"Error building trends tab: {e}")
            f = self.trends_frame
            ttk.Label(f, text="Trends Analysis - Error Loading").pack(pady=20)
            ttk.Label(f, text=f"Error: {str(e)}").pack(pady=10)

    def _build_market_breadth_tab(self):
        """Build the Market Breadth Analysis tab."""
        try:
            from gui.tabs.market_breadth import MarketBreadthTab
            # Create the market breadth tab directly in the existing frame
            market_breadth_tab = MarketBreadthTab(self.market_breadth_frame)
            self.append_log("Market Breadth Analysis tab initialized successfully")
        except Exception as e:
            # Fallback to a simple placeholder if import fails
            self.append_log(f"Error building market breadth tab: {e}")
            f = self.market_breadth_frame
            ttk.Label(f, text="Market Breadth Analysis - Error Loading").pack(pady=20)
            ttk.Label(f, text=f"Error: {str(e)}").pack(pady=10)

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
