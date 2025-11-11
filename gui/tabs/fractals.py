"""Fractals tab UI helpers

Small, focused UI helpers used by scanner_gui to show fractal-break results
and to open a price+RSI chart. Business logic (DB access, calculation) lives in
services.fractals_service which this module imports.
"""
from __future__ import annotations

import threading
import gc
import atexit
import tkinter as tk
from tkinter import ttk
from typing import Optional

import pandas as pd
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.pyplot as plt

from services.fractals_service import fetch_price_and_rsi


# ensure matplotlib figures are closed at process exit as a safety net
try:
    atexit.register(lambda: (plt.close('all'), gc.collect()))
except Exception:
    pass

    # Attach/initialize the expected attributes used elsewhere.
    if not hasattr(app, 'frac_rsi_period'):
        app.frac_rsi_period = tk.IntVar(value=9)
    if not hasattr(app, 'frac_workers'):
        app.frac_workers = tk.IntVar(value=4)
    if not hasattr(app, 'frac_progress'):
        app.frac_progress = ttk.Progressbar(f, orient='horizontal', mode='determinate', length=400)
        app.frac_progress.grid(row=2, column=0, columnspan=6, pady=(4,8), sticky='we')
    if not hasattr(app, 'frac_results'):
        app.frac_results = tk.Text(f, height=10, wrap='none')
        app.frac_results.grid(row=3, column=0, columnspan=6, sticky='nsew')

    # minimal controls
    try:
        ttk.Label(f, text='Fractal RSI period').grid(row=0, column=0, sticky='w')
        ttk.Entry(f, textvariable=app.frac_rsi_period, width=6).grid(row=0, column=1, sticky='w')
    except Exception:
        pass

    try:
        ttk.Label(f, text='Workers').grid(row=0, column=2, sticky='w')
        ttk.Entry(f, textvariable=app.frac_workers, width=6).grid(row=0, column=3, sticky='w')
    except Exception:
        pass

    try:
        ttk.Button(f, text='Run Fractals Scan', command=getattr(app, 'run_fractals_scan', lambda: None)).grid(row=1, column=0, pady=6)
        ttk.Button(f, text='Cancel Fractals', command=getattr(app, '_cancel_fractals', lambda: None)).grid(row=1, column=1, pady=6)
        ttk.Button(f, text='Show Fractal Breaks', command=getattr(app, 'show_fractal_breaks', lambda: None)).grid(row=1, column=2, pady=6)
    except Exception:
        pass

    # Treeview for fractals (scaffold only)
    cols = ('symbol', 'fractal_date', 'fractal_type', 'fractal_high', 'fractal_low', 'center_rsi')
    tree_frame = ttk.Frame(f)
    tree_frame.grid(row=4, column=0, columnspan=6, sticky='nsew', pady=(6,0))
    f.grid_rowconfigure(4, weight=1)
    f.grid_columnconfigure(5, weight=1)

    app.frac_tree = ttk.Treeview(tree_frame, columns=cols, show='headings', height=12)
    for c in cols:
        app.frac_tree.heading(c, text=c)
        app.frac_tree.column(c, width=120, anchor='w')
    v = ttk.Scrollbar(tree_frame, orient='vertical', command=app.frac_tree.yview)
    h = ttk.Scrollbar(tree_frame, orient='horizontal', command=app.frac_tree.xview)
    app.frac_tree.configure(yscrollcommand=v.set, xscrollcommand=h.set)
    tree_frame.grid_rowconfigure(0, weight=1)
    tree_frame.grid_columnconfigure(0, weight=1)
    app.frac_tree.grid(row=0, column=0, sticky='nsew')
    v.grid(row=0, column=1, sticky='ns')
    h.grid(row=1, column=0, sticky='ew')

    app._fractals_cancel = {'cancel': False}

    # Ensure layout rows/cols are configured
    try:
        f.grid_rowconfigure(3, weight=1)
        f.grid_columnconfigure(5, weight=1)
    except Exception:
        pass


def show_fractal_breaks_dialog(app: object, df: pd.DataFrame) -> None:
    """Open a modal Toplevel showing fractal-break rows in a Treeview.

    Double-clicking a row will call open_price_rsi_chart(...) with the
    symbol and fractal metadata from that row.
    """
    root = getattr(app, "root", app)
    # If caller didn't pass a DataFrame, or it's empty, try to load from DB
    if df is None or df.empty:
        try:
            from services.fractals_service import scan_fractal_breaks
            df = scan_fractal_breaks()
        except Exception:
            df = pd.DataFrame()

    if df is None or df.empty:
        tk.messagebox.showinfo("Fractals", "No fractal break rows to show.")
        return

    root = getattr(app, "root", app)
    top = tk.Toplevel(root)
    top.title("Fractal Breaks")
    top.geometry("900x500")

    # Summary labels (Buys / Sells / Total / Sentiment) placed at top of dialog
    try:
        summary_frame = ttk.Frame(top)
        summary_frame.pack(fill=tk.X, padx=6, pady=(6, 0))
        buy_lbl = ttk.Label(summary_frame, text='Buys: 0')
        buy_lbl.pack(side=tk.LEFT, padx=(2, 8))
        sell_lbl = ttk.Label(summary_frame, text='Sells: 0')
        sell_lbl.pack(side=tk.LEFT, padx=(2, 8))
        total_lbl = ttk.Label(summary_frame, text='Total: 0')
        total_lbl.pack(side=tk.LEFT, padx=(2, 8))
        sentiment_lbl = ttk.Label(summary_frame, text='Sentiment: Neutral')
        sentiment_lbl.pack(side=tk.LEFT, padx=(2, 8))
    except Exception:
        # fall back silently if label creation fails
        buy_lbl = sell_lbl = total_lbl = sentiment_lbl = None

    frame = ttk.Frame(top)
    frame.pack(fill=tk.BOTH, expand=True)

    # Preferred columns (may vary depending on repository schema)
    cols = [
        "symbol",
        "series",
        "break_date",
        "fractal_date",
        "fractal_type",
        "fractal_high",
        "fractal_low",
        "close_price",
        "break_type",
        "sentiment",
        "rsi",
    ]

    tree = ttk.Treeview(frame, columns=cols, show="headings")
    for c in cols:
        tree.heading(c, text=c)
        tree.column(c, width=120, anchor=tk.CENTER)

    # color rows by sentiment: bullish -> light green, bearish -> light red
    try:
        tree.tag_configure('buy', background='#dff0d8')   # light green
        tree.tag_configure('sell', background='#f2dede')  # light red
    except Exception:
        pass

    vsb = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=tree.yview)
    hsb = ttk.Scrollbar(frame, orient=tk.HORIZONTAL, command=tree.xview)
    tree.configure(yscroll=vsb.set, xscroll=hsb.set)

    tree.grid(row=0, column=0, sticky=tk.NSEW)
    vsb.grid(row=0, column=1, sticky=tk.NS)
    hsb.grid(row=1, column=0, sticky=tk.EW)
    frame.rowconfigure(0, weight=1)
    frame.columnconfigure(0, weight=1)

    display_df = df.copy()
    # remove duplicate signals: prefer uniqueness by symbol+fractal_date+fractal_type if available
    try:
        dedup_keys = [k for k in ("symbol", "fractal_date", "fractal_type", "break_date") if k in display_df.columns]
        if dedup_keys:
            before = len(display_df)
            display_df = display_df.drop_duplicates(subset=dedup_keys, keep='first')
            after = len(display_df)
            try:
                # schedule small log entry on main thread if app has append_log
                root.after(0, lambda: getattr(app, 'append_log', lambda *_: None)(f"Fractal breaks: removed {before-after} duplicate rows"))
            except Exception:
                pass
    except Exception:
        pass
    # Ensure datetime columns are parsed for display
    for dcol in ("break_date", "fractal_date", "trade_date"):
        if dcol in display_df.columns:
            try:
                display_df[dcol] = pd.to_datetime(display_df[dcol], errors='coerce')
            except Exception:
                pass

    def on_double_click(event: tk.Event) -> None:
        sel = tree.selection()
        if not sel:
            return
        item = sel[0]
        vals = tree.item(item, "values")
        # Mapping by cols order
        sym = vals[0]
        # locate indices for fractal_high/low/date
        # we used cols list above; defensive lookup
        col_index = {c: i for i, c in enumerate(cols)}
        fractal_high = None
        fractal_low = None
        fractal_date = None
        fractal_type = None
        try:
            if 'fractal_high' in col_index:
                fractal_high = vals[col_index['fractal_high']]
            if 'fractal_low' in col_index:
                fractal_low = vals[col_index['fractal_low']]
            if 'fractal_date' in col_index:
                fractal_date = vals[col_index['fractal_date']]
            if 'fractal_type' in col_index:
                fractal_type = vals[col_index['fractal_type']]
        except Exception:
            pass
        # Open chart
        try:
            fh = float(fractal_high) if fractal_high not in ("", None, 'None') else None
        except Exception:
            fh = None
        try:
            fl = float(fractal_low) if fractal_low not in ("", None, 'None') else None
        except Exception:
            fl = None
        open_price_rsi_chart(
            app,
            sym,
            days=180,
            fractal_high=fh,
            fractal_low=fl,
            fractal_date=str(fractal_date) if fractal_date is not None else None,
        )

    tree.bind("<Double-1>", on_double_click)

    # Insert rows and compute summary counts
    buy_count = 0
    sell_count = 0
    total = 0
    for _, row in display_df.iterrows():
        vals = []
        for c in cols:
            v = row.get(c, "")
            if pd.isna(v):
                v = ""
            # format datetimes
            if c in ("break_date", "fractal_date") and v not in ("", None):
                try:
                    v = pd.to_datetime(v).strftime('%Y-%m-%d')
                except Exception:
                    v = str(v)
            vals.append(str(v))
        # determine sentiment and tag from break_type or fractal relation to close
        bt = (row.get('break_type') or row.get('break') or row.get('signal') or '')
        tag = None
        sentiment = ''
        try:
            if isinstance(bt, str) and bt.strip():
                bt_u = bt.strip().upper()
                if bt_u.startswith('BUY') or bt_u == 'B':
                    tag = 'buy'
                    sentiment = 'Bullish'
                    buy_count += 1
                elif bt_u.startswith('SELL') or bt_u == 'S':
                    tag = 'sell'
                    sentiment = 'Bearish'
                    sell_count += 1
        except Exception:
            pass

        # if sentiment still unknown, infer from fractal_high/low vs close_price
        if not sentiment:
            try:
                cp = row.get('close_price')
                fh = row.get('fractal_high')
                fl = row.get('fractal_low')
                # coerce to float where possible
                cpv = float(cp) if pd.notna(cp) else None
                fhv = float(fh) if pd.notna(fh) else None
                flv = float(fl) if pd.notna(fl) else None
                if fhv is not None and cpv is not None and cpv > fhv:
                    sentiment = 'Bullish'
                    tag = 'buy'
                    buy_count += 1
                elif flv is not None and cpv is not None and cpv < flv:
                    sentiment = 'Bearish'
                    tag = 'sell'
                    sell_count += 1
                else:
                    sentiment = 'Neutral'
            except Exception:
                sentiment = 'Neutral'
        total += 1
        # insert sentiment into the correct column position
        # ensure vals length matches cols
        # replace or append sentiment value at the sentiment column index
        try:
            sidx = cols.index('sentiment')
            # ensure list large enough
            while len(vals) <= sidx:
                vals.append('')
            vals[sidx] = sentiment
        except Exception:
            # if anything fails, append
            vals.append(sentiment)

        try:
            if tag:
                tree.insert('', 'end', values=vals, tags=(tag,))
            else:
                tree.insert('', 'end', values=vals)
        except Exception:
            tree.insert('', 'end', values=vals)

    # update summary labels
    try:
        buy_lbl.config(text=f'Buys: {buy_count}')
        sell_lbl.config(text=f'Sells: {sell_count}')
        total_lbl.config(text=f'Total: {total}')
        sent = 'Bullish' if buy_count > sell_count else ('Bearish' if sell_count > buy_count else 'Neutral')
        sentiment_lbl.config(text=f'Sentiment: {sent}')
    except Exception:
        pass

    # Simple close button
    btn = ttk.Button(top, text="Close", command=top.destroy)
    btn.pack(side=tk.BOTTOM, pady=6)


def open_price_rsi_chart(
    app: object,
    symbol: str,
    days: int = 120,
    fractal_high: Optional[float] = None,
    fractal_low: Optional[float] = None,
    fractal_date: Optional[str] = None,
) -> None:
    """Fetch price and RSI in background and show a matplotlib chart.

    This spawns a background thread to avoid blocking the main Tk loop.
    The service function `fetch_price_and_rsi` should return a tuple
    (ohlcv_df, rsi_df). If fetching fails, an error messagebox is shown.
    """
    root = getattr(app, "root", app)

    def worker() -> None:
        try:
            ohlcv_df, rsi_df = fetch_price_and_rsi(symbol, days=days)
        except Exception as e:
            error_msg = str(e)  # Capture the error message in a local variable
            root.after(0, lambda msg=error_msg: tk.messagebox.showerror("Chart error", msg))
            return

        if ohlcv_df is None or ohlcv_df.empty:
            root.after(0, lambda: tk.messagebox.showinfo("Chart", "No price data"))
            return

        # Log fetched sizes to app log (safely schedule on main thread)
        try:
            rows = len(ohlcv_df) if ohlcv_df is not None else 0
            rsi_rows = len(rsi_df) if (rsi_df is not None) else 0
            root.after(0, lambda: getattr(app, 'append_log', lambda *_: None)(f"plot_df fetched: {rows} price rows, {rsi_rows} rsi rows for {symbol}"))
        except Exception:
            pass

        # schedule figure creation and UI embedding on main thread to avoid
        # Matplotlib/Tkinter thread-safety issues
        def create_and_show():
            # This runs on the main Tk thread (scheduled via root.after).
            try:
                # pick a close-like column robustly
                close_col = None
                for cand in ("close", "Close", "close_price", "ClosePrice", "Close_Price", "closePrice"):
                    if cand in ohlcv_df.columns:
                        close_col = cand
                        break
                if close_col is None:
                    numcols = [c for c in ohlcv_df.columns if pd.api.types.is_numeric_dtype(ohlcv_df[c])]
                    for c in numcols:
                        if 'close' in c.lower():
                            close_col = c
                            break
                    if close_col is None and numcols:
                        close_col = numcols[0]

                # prepare series
                try:
                    ohlcv_idx = pd.to_datetime(ohlcv_df.index)
                except Exception:
                    ohlcv_idx = ohlcv_df.index
                close_series = pd.to_numeric(ohlcv_df[close_col], errors='coerce') if close_col is not None else pd.to_numeric(ohlcv_df.iloc[:, 0], errors='coerce')
                close_series.index = ohlcv_idx
                close_series = close_series.sort_index()

                rsi_ser = None
                if rsi_df is not None and not rsi_df.empty and 'rsi' in rsi_df.columns:
                    try:
                        rsi_ser = pd.to_numeric(rsi_df['rsi'], errors='coerce')
                        rsi_ser.index = pd.to_datetime(rsi_df.index)
                        rsi_ser = rsi_ser.sort_index()
                    except Exception:
                        rsi_ser = None

                vol_ser = None
                try:
                    if 'Volume' in ohlcv_df.columns:
                        vol_ser = pd.to_numeric(ohlcv_df['Volume'].astype(str), errors='coerce')
                        vol_ser.index = pd.to_datetime(ohlcv_df.index)
                        vol_ser = vol_ser.sort_index()
                    elif 'ttl_trd_qnty' in ohlcv_df.columns:
                        vol_ser = pd.to_numeric(ohlcv_df['ttl_trd_qnty'].astype(str), errors='coerce')
                        vol_ser.index = pd.to_datetime(ohlcv_df.index)
                        vol_ser = vol_ser.sort_index()
                except Exception:
                    vol_ser = None

                # sizing heuristics
                npts = len(close_series)
                fig_w = max(10, min(64, int(npts / 3) + 6)) if npts else 12
                msize = min(10, max(3, int(300 / max(10, npts)))) if npts else 6
                bar_w = 0.6 if npts > 200 else (0.8 if npts > 100 else 1.0)

                fig = plt.Figure(figsize=(fig_w, 6))
                gs = fig.add_gridspec(3, 1, height_ratios=(3, 1, 1), hspace=0.05)
                ax_price = fig.add_subplot(gs[0, 0])
                ax_vol = fig.add_subplot(gs[1, 0], sharex=ax_price)
                ax_rsi = fig.add_subplot(gs[2, 0], sharex=ax_price)

                if close_series.empty:
                    ax_price.text(0.5, 0.5, 'No price data', transform=ax_price.transAxes, ha='center')
                else:
                    try:
                        import numpy as np
                    except Exception:
                        np = None
                    xs = np.arange(len(close_series)) if np is not None else list(range(len(close_series)))
                    dates = list(close_series.index)
                    closes = close_series.values

                    ax_price.plot(xs, closes, color='tab:blue', linewidth=1.2, label='Close')
                    try:
                        ax_price.scatter(xs, closes, s=(msize ** 2), facecolors='tab:blue', edgecolors='k', zorder=3)
                    except Exception:
                        ax_price.plot(xs, closes, marker='o', markersize=msize, linestyle='-', color='tab:blue')

                    if vol_ser is not None and not vol_ser.empty:
                        try:
                            vol_aligned = vol_ser.reindex(close_series.index, method='nearest', tolerance=pd.Timedelta('1D'))
                        except Exception:
                            vol_aligned = vol_ser.reindex(close_series.index).fillna(0)
                        try:
                            ax_vol.bar(xs, vol_aligned.values, width=bar_w, color='tab:gray')
                            ax_vol.set_ylabel('Volume')
                        except Exception:
                            ax_vol.set_visible(False)
                    else:
                        ax_vol.set_visible(False)

                    if rsi_ser is not None and not rsi_ser.empty:
                        try:
                            rsi_aligned = rsi_ser.reindex(close_series.index, method='nearest', tolerance=pd.Timedelta('1D'))
                        except Exception:
                            rsi_aligned = rsi_ser.reindex(close_series.index).fillna(method='ffill')
                        try:
                            ax_rsi.plot(xs, rsi_aligned.values, color='tab:orange')
                            ax_rsi.axhline(70, color='red', linestyle='--', linewidth=0.5)
                            ax_rsi.axhline(30, color='green', linestyle='--', linewidth=0.5)
                            ax_rsi.set_ylim(0, 100)
                            ax_rsi.set_ylabel('RSI')
                        except Exception:
                            ax_rsi.set_visible(False)
                    else:
                        ax_rsi.set_visible(False)

                    try:
                        max_ticks = 8
                        step = max(1, len(xs) // max_ticks)
                        ticks = xs[::step]
                        tick_labels = [d.strftime('%Y-%m-%d') for d in dates[::step]]
                        ax_price.set_xticks(ticks)
                        ax_price.set_xticklabels(tick_labels, rotation=45, ha='right')
                    except Exception:
                        pass

                    ax_price.set_ylabel('Price')
                    ax_price.set_title(symbol)
                    ax_price.grid(True, linestyle='--', alpha=0.4)

                    if fractal_date:
                        try:
                            frac_dt = pd.to_datetime(fractal_date)
                            pos_arr = close_series.index.get_indexer([frac_dt], method='nearest')
                            pos = int(pos_arr[0]) if len(pos_arr) and pos_arr[0] != -1 else None
                            if pos is not None:
                                ax_price.axvline(pos, color='magenta', linestyle='--', alpha=0.8)
                        except Exception:
                            pass

                    try:
                        if fractal_high is not None:
                            ax_price.axhline(fractal_high, color='green', linestyle='--', linewidth=1.0, label='Fractal high')
                        if fractal_low is not None:
                            ax_price.axhline(fractal_low, color='red', linestyle='--', linewidth=1.0, label='Fractal low')
                    except Exception:
                        pass
                    try:
                        ax_price.legend(loc='upper left')
                    except Exception:
                        pass

                fig.autofmt_xdate()

            except Exception as e:
                # show error and log
                try:
                    if hasattr(app, 'append_log'):
                        app.append_log(f"chart build error for {symbol}: {e}")
                except Exception:
                    pass
                try:
                    tk.messagebox.showerror("Chart error", str(e))
                except Exception:
                    pass
                return

            # embed the figure into a Tk window
            try:
                win = tk.Toplevel(root)
                win.title(f"{symbol} chart")
                # maximize on open: prefer native maximize on Windows (zoomed),
                # fallback to fullscreen if zoomed isn't supported.
                try:
                    win.state('zoomed')
                except Exception:
                    try:
                        win.attributes('-fullscreen', True)
                    except Exception:
                        pass
                canvas = FigureCanvasTkAgg(fig, master=win)
                canvas.draw()
                canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

                def _on_close_win():
                    try:
                        # if we set fullscreen, try to exit it before destroying
                        try:
                            win.attributes('-fullscreen', False)
                        except Exception:
                            pass
                        try:
                            win.state('normal')
                        except Exception:
                            pass
                    except Exception:
                        pass
                    try:
                        canvas.get_tk_widget().pack_forget()
                        canvas.get_tk_widget().destroy()
                    except Exception:
                        pass
                    try:
                        plt.close(fig)
                    except Exception:
                        pass
                    try:
                        gc.collect()
                    except Exception:
                        pass
                    try:
                        win.destroy()
                    except Exception:
                        pass

                btn_close = ttk.Button(win, text='Close', command=_on_close_win)
                btn_close.pack(side=tk.BOTTOM, pady=4)
                try:
                    win.protocol('WM_DELETE_WINDOW', _on_close_win)
                except Exception:
                    pass
            except Exception as e:
                try:
                    if hasattr(app, 'append_log'):
                        app.append_log(f"chart embed error for {symbol}: {e}")
                except Exception:
                    pass
                try:
                    tk.messagebox.showerror('Chart error', str(e))
                except Exception:
                    pass

        root.after(0, create_and_show)

    thread = threading.Thread(target=worker, daemon=True)
    thread.start()
