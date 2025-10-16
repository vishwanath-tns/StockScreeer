# reporting_adv_decl.py
import os
from datetime import date
from typing import Iterable, Optional, Dict
import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL
from dotenv import load_dotenv
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

load_dotenv()

HOST = os.getenv("MYSQL_HOST", "127.0.0.1")
PORT = int(os.getenv("MYSQL_PORT", "3306"))
DB   = os.getenv("MYSQL_DB", "marketdata")
USER = os.getenv("MYSQL_USER", "root")
PWD  = os.getenv("MYSQL_PASSWORD", "")

BHAV_TABLE  = "nse_equity_bhavcopy_full"
CACHE_TABLE = "adv_decl_summary"
DEFAULT_SERIES = ("EQ", "BE", "BZ", "BL")

def engine():
    url = URL.create(
        drivername="mysql+pymysql",
        username=USER,
        password=PWD,
        host=HOST,
        port=int(PORT),
        database=DB,
        query={"charset": "utf8mb4"},
    )
    return create_engine(url, pool_pre_ping=True, pool_recycle=3600)

def _series_scope(series: Iterable[str]) -> str:
    return ",".join(sorted({s.strip().upper() for s in series}))

def is_cached(trade_dt: date, series: Iterable[str] = DEFAULT_SERIES) -> bool:
    scope = _series_scope(series)
    with engine().connect() as conn:
        row = conn.execute(
            text(f"SELECT 1 FROM {CACHE_TABLE} WHERE trade_date=:d AND series_scope=:s LIMIT 1"),
            {"d": trade_dt, "s": scope},
        ).first()
        return row is not None

def compute_adv_decl(trade_dt: date, series: Iterable[str] = DEFAULT_SERIES, force: bool = False) -> Dict:
    scope = _series_scope(series)
    if (not force) and is_cached(trade_dt, series):
        with engine().connect() as conn:
            row = conn.execute(
                text(f"""
                    SELECT advances, declines, unchanged, total, source_rows, computed_at
                    FROM {CACHE_TABLE}
                    WHERE trade_date=:d AND series_scope=:s
                """),
                {"d": trade_dt, "s": scope}
            ).mappings().first()
            return {"trade_date": trade_dt, "series_scope": scope, **dict(row)}

    series_list = sorted({s.strip().upper() for s in series})
    placeholders = ",".join([f":s{i}" for i in range(len(series_list))])
    params = {"d": trade_dt}
    params.update({f"s{i}": v for i, v in enumerate(series_list)})

    sql = f"""
        SELECT
          SUM(CASE WHEN close_price > prev_close THEN 1 ELSE 0 END) AS advances,
          SUM(CASE WHEN close_price < prev_close THEN 1 ELSE 0 END) AS declines,
          SUM(CASE WHEN close_price = prev_close THEN 1 ELSE 0 END) AS unchanged,
          COUNT(*) AS total
        FROM {BHAV_TABLE}
        WHERE trade_date = :d
          AND series IN ({placeholders})
          AND close_price IS NOT NULL
          AND prev_close  IS NOT NULL
    """

    eng = engine()
    with eng.begin() as conn:
        res = conn.execute(text(sql), params).mappings().first()
        if res is None or res["total"] is None:
            payload = {"advances": 0, "declines": 0, "unchanged": 0, "total": 0}
        else:
            payload = {k: int(res[k]) for k in ("advances", "declines", "unchanged", "total")}

        cnt_sql = f"""
            SELECT COUNT(*) AS c
            FROM {BHAV_TABLE}
            WHERE trade_date = :d AND series IN ({placeholders})
        """
        row_cnt = int(conn.execute(text(cnt_sql), params).scalar() or 0)

        upsert = f"""
            INSERT INTO {CACHE_TABLE}
                (trade_date, series_scope, advances, declines, unchanged, total, source_rows)
            VALUES
                (:d, :scope, :a, :de, :u, :t, :src)
            ON DUPLICATE KEY UPDATE
                advances=VALUES(advances),
                declines=VALUES(declines),
                unchanged=VALUES(unchanged),
                total=VALUES(total),
                source_rows=VALUES(source_rows),
                computed_at=CURRENT_TIMESTAMP
        """
        conn.execute(
            text(upsert),
            {"d": trade_dt, "scope": scope, "a": payload["advances"], "de": payload["declines"],
             "u": payload["unchanged"], "t": payload["total"], "src": row_cnt}
        )

    payload.update({"trade_date": trade_dt, "series_scope": scope, "source_rows": row_cnt})
    return payload

def compute_range(start: date, end: date, series: Iterable[str] = DEFAULT_SERIES, force: bool = False, progress_cb=None) -> pd.DataFrame:
    scope = _series_scope(series)
    eng = engine()
    with eng.connect() as conn:
        dates = conn.execute(
            text(f"""
                SELECT DISTINCT trade_date
                FROM {BHAV_TABLE}
                WHERE trade_date BETWEEN :a AND :b
                ORDER BY trade_date
            """),
            {"a": start, "b": end}
        ).scalars().all()
    rows = []
    total = len(dates)
    for i, d in enumerate(dates):
        rows.append(compute_adv_decl(d, series=series, force=force))
        if progress_cb:
            try:
                # call progress callback with (current_index, total, date)
                progress_cb(i + 1, total, d)
            except Exception:
                pass
    return pd.DataFrame(rows)

def export_adv_decl_csv(save_path: str,
                        start: Optional[date] = None,
                        end: Optional[date] = None,
                        series: Iterable[str] = DEFAULT_SERIES) -> str:
    """
    Export cached Advance/Decline ratios to CSV.
    Includes trade_date, advances, declines, unchanged, total, and ratios.
    """
    scope = _series_scope(series)
    eng = engine()
    with eng.connect() as conn:
        if start is None or end is None:
            r = conn.execute(
                text(f"SELECT MIN(trade_date), MAX(trade_date) FROM {CACHE_TABLE} WHERE series_scope=:s"),
                {"s": scope}
            ).first()
            if not r or not r[0]:
                raise RuntimeError("No cached A/D data found. Compute first.")
            start = r[0] if start is None else start
            end   = r[1] if end   is None else end

        df = pd.read_sql(
            text(f"""
                SELECT trade_date, advances, declines, unchanged, total
                FROM {CACHE_TABLE}
                WHERE series_scope=:s AND trade_date BETWEEN :a AND :b
                ORDER BY trade_date
            """),
            con=conn,
            params={"s": scope, "a": start, "b": end},
            parse_dates=["trade_date"]
        )

    if df.empty:
        raise RuntimeError("No cached A/D data in selected range.")

    # Compute ratios
    df["adv_ratio"] = df["advances"] / df["total"]
    df["dec_ratio"] = df["declines"] / df["total"]
    df["breadth"]   = df["advances"] - df["declines"]

    df.to_csv(save_path, index=False, float_format="%.4f")
    return save_path

def plot_adv_decl(start: Optional[date] = None,
                  end: Optional[date] = None,
                  series: Iterable[str] = DEFAULT_SERIES,
                  save_path: Optional[str] = None,
                  report_type: str = "counts"):
    scope = _series_scope(series)
    eng = engine()
    with eng.connect() as conn:
        if start is None or end is None:
            r = conn.execute(
                text(f"SELECT MIN(trade_date), MAX(trade_date) FROM {CACHE_TABLE} WHERE series_scope=:s"),
                {"s": scope}
            ).first()
            if not r or not r[0]:
                raise RuntimeError("No cached A/D data found. Compute first.")
            start = r[0] if start is None else start
            end   = r[1] if end is None else end

        df = pd.read_sql(
            text(f"""
                SELECT trade_date, advances, declines, unchanged, total
                FROM {CACHE_TABLE}
                WHERE series_scope=:s AND trade_date BETWEEN :a AND :b
                ORDER BY trade_date
            """),
            con=conn,
            params={"s": scope, "a": start, "b": end},
            parse_dates=["trade_date"]
        )

    if df.empty:
        raise RuntimeError("No cached rows in the requested range/scope.")

    df = df.set_index("trade_date")
    # Prefer a seaborn-like style if available, but don't crash if it's not
    try:
        plt.style.use('seaborn-whitegrid')
    except Exception:
        # style may not be installed (seaborn not available) — continue with defaults
        pass
    fig, ax = plt.subplots()
    # compute ratios
    df["adv_ratio"] = df["advances"] / df["total"]
    df["dec_ratio"] = df["declines"] / df["total"]

    # Plot according to report_type
    report_type = (report_type or "counts").lower()
    ratio_ax = None
    if report_type == "counts":
        # Plot with explicit markers so individual data points are visible
        ax.plot(
            df.index,
            df["advances"],
            label="Advances",
            marker="o",
            markersize=5,
            linestyle="-",
            linewidth=1.25,
            color="#2ca02c",  # green
            alpha=0.9,
            zorder=3,
        )
        ax.plot(
            df.index,
            df["declines"],
            label="Declines",
            marker="o",
            markersize=5,
            linestyle="-",
            linewidth=1.25,
            color="#d62728",  # red
            alpha=0.9,
            zorder=3,
        )
    elif report_type == "ratio":
        # single adv_ratio line on secondary axis as percent
        ratio_ax = ax.twinx()
        ratio_ax.plot(
            df.index,
            df["adv_ratio"] * 100.0,
            label="Adv Ratio (%)",
            marker="o",
            markersize=5,
            linestyle="-",
            linewidth=1.25,
            color="#1f77b4",
            alpha=0.9,
            zorder=3,
        )
        ratio_ax.set_ylabel("Adv Ratio (%)")
    elif report_type == "both_ratios":
        ratio_ax = ax.twinx()
        ratio_ax.plot(
            df.index,
            df["adv_ratio"] * 100.0,
            label="Adv Ratio (%)",
            marker="o",
            markersize=5,
            linestyle="-",
            linewidth=1.25,
            color="#1f77b4",
            alpha=0.9,
            zorder=3,
        )
        ratio_ax.plot(
            df.index,
            df["dec_ratio"] * 100.0,
            label="Dec Ratio (%)",
            marker="o",
            markersize=5,
            linestyle="-",
            linewidth=1.25,
            color="#ff7f0e",
            alpha=0.9,
            zorder=3,
        )
        ratio_ax.set_ylabel("Ratio (%)")
    else:
        raise ValueError("report_type must be one of: counts, ratio, both_ratios")
    # legends: include ratio axis legend if present
    if ratio_ax is not None:
        lines, labels = ax.get_legend_handles_labels()
        rlines, rlabels = ratio_ax.get_legend_handles_labels()
        ax.legend(lines + rlines, labels + rlabels)
    else:
        ax.legend()

    ax.set_title(f"Advance/Decline — {scope} — {start} to {end} ({report_type})")
    ax.set_xlabel("Date")
    ax.set_ylabel("Count")
    # show major and minor grid for readability
    ax.grid(which='major', linestyle='-', linewidth=0.6, alpha=0.8)
    ax.grid(which='minor', linestyle=':', linewidth=0.4, alpha=0.6)
    ax.minorticks_on()
    # Improve date label formatting and layout
    # Enable interactive hover showing full date (day-month-year)
    try:
        import mplcursors

        # include ratio axis lines too if present
        _lines = ax.lines[:]
        if ratio_ax is not None:
            _lines = _lines + ratio_ax.lines
        cursor = mplcursors.cursor(_lines, hover=True)

        def _format_val(y):
            try:
                yv = float(y)
                # If it's a ratio percent (we plotted ratio_ax as percent > 1), show with 2 decimals
                if abs(yv) <= 100 and not yv.is_integer():
                    return f"{yv:.2f}%" if yv <= 100 else f"{yv:.2f}"
                return f"{int(round(yv))}"
            except Exception:
                return str(y)

        @cursor.connect("add")
        def _on_add(sel):
            try:
                x, y = sel.target
                # Prefer pandas to format the x value if possible (removes time)
                try:
                    dt = pd.to_datetime(x).strftime("%Y-%m-%d")
                except Exception:
                    dt = mdates.num2date(x).strftime("%Y-%m-%d")
                val = _format_val(y)
                sel.annotation.set_text(f"{dt}\n{val}")
            except Exception:
                sel.annotation.set_text(str(sel.target))
    except Exception:
        # Fallback: simple annotation on mouse move
        annot = ax.annotate("", xy=(0, 0), xytext=(15, 15), textcoords="offset points",
                            bbox=dict(boxstyle="round", fc="w"))
        annot.set_visible(False)

        lines = ax.lines
        if ratio_ax is not None:
            lines = lines + ratio_ax.lines
        xdatas = [l.get_xdata() for l in lines]
        ydatas = [l.get_ydata() for l in lines]

        def _on_move(event):
            if event.inaxes != ax:
                return
            try:
                ex = event.xdata
                if ex is None:
                    if annot.get_visible():
                        annot.set_visible(False)
                        fig.canvas.draw_idle()
                    return
                # find nearest point among all lines
                nearest = None
                mindiff = float('inf')
                for li, (xs, ys) in enumerate(zip(xdatas, ydatas)):
                    if len(xs) == 0:
                        continue
                    # convert xs to numeric matplotlib dates
                    try:
                        nums = mdates.date2num(xs)
                    except Exception:
                        # xs may already be numeric
                        nums = xs
                    # find closest index
                    idx = int(min(range(len(nums)), key=lambda i: abs(nums[i] - ex)))
                    diff = abs(nums[idx] - ex)
                    if diff < mindiff:
                        mindiff = diff
                        nearest = (li, idx)
                # threshold: within a small fraction of a day
                if nearest and mindiff < 1.0:
                    li, idx = nearest
                    x = xdatas[li][idx]
                    y = ydatas[li][idx]
                    try:
                        try:
                            dt = pd.to_datetime(x).strftime("%Y-%m-%d")
                        except Exception:
                            dt = mdates.num2date(x).strftime("%Y-%m-%d")
                        # format value: if numeric and likely percent (ratio plotted on percent axis), format accordingly
                        try:
                            yv = float(y)
                            if not yv.is_integer():
                                valtxt = f"{yv:.2f}%" if abs(yv) <= 100 else f"{yv:.2f}"
                            else:
                                valtxt = f"{int(round(yv))}"
                        except Exception:
                            valtxt = str(y)
                        txt = f"{dt}\n{valtxt}"
                    except Exception:
                        txt = f"{x}\n{y}"
                    annot.xy = (x, y)
                    annot.set_text(txt)
                    annot.set_visible(True)
                    fig.canvas.draw_idle()
                else:
                    if annot.get_visible():
                        annot.set_visible(False)
                        fig.canvas.draw_idle()
            except Exception:
                pass

        fig.canvas.mpl_connect('motion_notify_event', _on_move)

    fig.autofmt_xdate()
    fig.tight_layout()
    if save_path:
        fig.savefig(save_path, bbox_inches="tight")
    else:
        plt.show()
