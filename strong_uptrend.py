"""strong_uptrend.py

Scanner that finds strong uptrending stocks using moving averages + SMA slope + volume confirmation.

Usage: python strong_uptrend.py --since 2025-09-01
"""
from datetime import date
from sqlalchemy import text
import pandas as pd


def engine():
    import reporting_adv_decl as rad
    return rad.engine()


def avg_volume(conn, symbol, end_date, days=10):
    q = text("""SELECT trade_date, ttl_trd_qnty as volume
                FROM nse_equity_bhavcopy_full
                WHERE symbol = :s AND trade_date <= :d
                ORDER BY trade_date DESC
                LIMIT :n""")
    df = pd.read_sql(q, con=conn, params={"s": symbol, "d": end_date, "n": days}, parse_dates=["trade_date"])
    if df.empty:
        return None
    return df['volume'].mean()


def last_close(conn, symbol, date_):
    q = text("""SELECT close_price FROM nse_equity_bhavcopy_full
                WHERE symbol=:s AND trade_date<=:d ORDER BY trade_date DESC LIMIT 1""")
    r = conn.execute(q, {"s": symbol, "d": date_}).fetchone()
    return float(r[0]) if r and r[0] is not None else None


def scan(min_avg_vol_ratio=1.2, min_sma20_pct=0.03, since: date | None = None, symbols=None):
    eng = engine()
    with eng.connect() as conn:
        params = {}
        q = "SELECT trade_date, symbol, sma_5, sma_20, sma_50, sma_100 FROM moving_averages"
        if since:
            q += " WHERE trade_date >= :since"
            params['since'] = since
        df = pd.read_sql(text(q), con=conn, params=params, parse_dates=["trade_date"])

    if df.empty:
        return []

    out = []
    for sym, g in df.groupby('symbol'):
        g = g.sort_values('trade_date')
        if len(g) < 5:
            continue
        last = g.iloc[-1]
        if pd.isna(last[['sma_5', 'sma_20', 'sma_50']]).any():
            continue
        # alignment
        sma100 = last.get('sma_100')
        if sma100 is None or pd.isna(sma100):
            sma100 = -1e12
        if not (last['sma_5'] > last['sma_20'] > last['sma_50'] > sma100):
            continue

        with eng.connect() as conn:
            close = last_close(conn, sym, last['trade_date'].date())
            if close is None:
                continue
            if not (close > last['sma_20'] and close > last['sma_50']):
                continue
            prev_idx = max(0, len(g) - 11)
            sma20_10 = g.iloc[prev_idx]['sma_20']
            if pd.isna(sma20_10) or sma20_10 <= 0:
                continue
            sma20_pct = (last['sma_20'] - sma20_10) / sma20_10
            if sma20_pct < min_sma20_pct:
                continue
            sma5_3 = g.iloc[max(0, len(g)-4)]['sma_5']
            if pd.isna(sma5_3) or last['sma_5'] <= sma5_3:
                continue
            avg10 = avg_volume(conn, sym, last['trade_date'].date(), days=10)
            avg50 = avg_volume(conn, sym, last['trade_date'].date(), days=50)
            if avg10 is None or avg50 is None:
                continue
            vol_ratio = (avg10 / (avg50 + 1e-9))
            if vol_ratio < min_avg_vol_ratio:
                continue

        out.append({
            'symbol': sym,
            'date': last['trade_date'].date(),
            'close': float(close),
            'sma_5': float(last['sma_5']),
            'sma_20': float(last['sma_20']),
            'sma_50': float(last['sma_50']),
            'sma_100': float(last.get('sma_100')) if not pd.isna(last.get('sma_100')) else None,
            'sma20_pct': float(sma20_pct),
            'vol_ratio': float(vol_ratio)
        })

    return out


if __name__ == '__main__':
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument('--since', help='YYYY-MM-DD', default=None)
    p.add_argument('--out', help='Path to CSV output file (optional)', default=None)
    args = p.parse_args()
    since = pd.to_datetime(args.since).date() if args.since else None
    res = scan(since=since)
    # If output path provided, write CSV
    def save_csv(results, path):
        import csv
        keys = ['symbol','date','close','sma_5','sma_20','sma_50','sma_100','sma20_pct','vol_ratio']
        with open(path, 'w', newline='', encoding='utf-8') as fh:
            w = csv.writer(fh)
            w.writerow(keys)
            for r in results:
                row = [r.get(k) for k in keys]
                # ensure date is ISO string
                if row[1] and hasattr(row[1], 'isoformat'):
                    row[1] = row[1].isoformat()
                w.writerow(row)

    if args.out:
        save_csv(res, args.out)
        print(f"Wrote {len(res)} rows to {args.out}")
    else:
        for r in res:
            print(r)
