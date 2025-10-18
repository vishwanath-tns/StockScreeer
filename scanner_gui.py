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

        nb.add(self.accum_frame, text="Accumulation Scanner")
        nb.add(self.swing_frame, text="Swing Scanner")
        nb.add(self.liq_frame, text="Liquidity Baseline & Scan")
        nb.add(self.deliv_frame, text="Delivery Count")
        nb.add(self.advdecl_frame, text="Adv/Decl Report")
        nb.add(self.candles_frame, text="Candles")
        nb.add(self.sma_frame, text="SMA Trends")
        nb.add(self.strong_frame, text="Strong Uptrend")

        self._build_accum_tab()
        self._build_swing_tab()
        self._build_liq_tab()
        self._build_deliv_tab()
        self._build_advdecl_tab()
        self._build_candles_tab()
        self._build_sma_tab()
        self._build_strong_tab()

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

    def _browse(self, var: tk.StringVar):
        p = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV files","*.csv"), ("All","*")])
        if p:
            var.set(p)


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
