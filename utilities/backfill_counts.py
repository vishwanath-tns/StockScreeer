"""backfill_counts.py

Backfill daily_52w_counts for recent BHAV dates.

Usage:
    python backfill_counts.py --days 30

This script uses the same DB engine as the GUI (reporting_adv_decl.engine()).
It fetches the most recent distinct BHAV trade dates and calls
`week52_scanner.upsert_daily_52w_counts(conn, date)` for each date.
"""
import argparse
from sqlalchemy import text


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--days', type=int, default=30, help='Number of most recent BHAV dates to backfill')
    p.add_argument('--full', action='store_true', help='Backfill all dates where a full history window exists (uses --min-history-days)')
    p.add_argument('--min-history-days', type=int, default=365, help='Minimum prior days required to compute 52-week window (default 365)')
    args = p.parse_args()

    try:
        import reporting_adv_decl as rad
        import week52_scanner as w52
    except Exception as e:
        print(f"Missing modules: {e}")
        raise

    eng = rad.engine()
    conn = eng.connect()
    try:
        if args.full:
            print(f"Running full backfill using min-history-days={args.min_history_days} ...")
            summary = w52.backfill_daily_52w_counts_range(conn, min_history_days=args.min_history_days, progress_cb=None)
            print(f"Full backfill summary: attempted={summary['attempted']}, succeeded={summary['succeeded']}, failed={summary['failed']}")
            return

        rows = conn.execute(text("SELECT DISTINCT trade_date FROM nse_equity_bhavcopy_full WHERE series='EQ' ORDER BY trade_date DESC LIMIT :lim"), {"lim": max(60, args.days)}).fetchall()
        dates = [r[0] for r in rows][:args.days]
        if not dates:
            print('No BHAV dates found, aborting')
            return
        print(f'Backfilling {len(dates)} dates (most recent first)')
        for idx, d in enumerate(reversed(dates), start=1):
            try:
                print(f"Calling upsert for {d} ({idx}/{len(dates)})")
                res = w52.upsert_daily_52w_counts(conn, d)
                print(f"{idx}/{len(dates)} {res['date']}: high={res['count_high']}, low={res['count_low']}")
            except Exception as e:
                print(f"{idx}/{len(dates)} {d}: ERROR: {e}")
                try:
                    import traceback
                    traceback.print_exc()
                except Exception:
                    pass
    finally:
        try:
            conn.close()
        except Exception:
            pass

if __name__ == '__main__':
    main()
