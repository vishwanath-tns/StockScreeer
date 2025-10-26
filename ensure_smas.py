"""ensure_smas.py

Small CLI helper to ensure SMA columns exist and compute missing SMA windows
(using the existing helpers in minervini_screener and compute_moving_averages).

Usage examples:
    # ensure standard windows and compute for all symbols (may take long)
    python ensure_smas.py --windows 50 150 200 --limit 0

    # compute only for first 50 symbols
    python ensure_smas.py --windows 150 --limit 50

This script will print a short report and exit with code 0 on success.
"""

import argparse
from datetime import date

def main():
    p = argparse.ArgumentParser()
    p.add_argument('--windows', nargs='+', type=int, default=[50,150,200], help='SMA windows to ensure/compute')
    p.add_argument('--as-of', help='As-of date YYYY-MM-DD (optional)', default=None)
    p.add_argument('--limit', type=int, default=0, help='Limit number of symbols to process (0 = all)')
    args = p.parse_args()

    try:
        import minervini_screener as ms
    except Exception as e:
        print(f"Could not import minervini_screener: {e}")
        raise

    eng = ms.engine()
    conn = eng.connect()
    try:
        wins = sorted(list(set(args.windows)))
        as_of = None
        if args.as_of:
            import pandas as pd
            as_of = pd.to_datetime(args.as_of).date()

        print(f"Ensuring SMA columns for windows: {wins}")
        ensure_report = ms._ensure_sma_columns(conn, wins)
        print("Ensure report:")
        print(f"  existing_columns: {len(ensure_report.get('existing_columns', []))}")
        if ensure_report.get('added'):
            print(f"  added columns: {ensure_report['added']}")
        if ensure_report.get('errors'):
            print("  errors while adding columns:")
            for e in ensure_report.get('errors', []):
                print(f"    {e}")

        print(f"Computing missing SMAs (limit={args.limit})...")
        comp = ms.ensure_and_compute_smas(conn, wins, as_of=as_of, symbols=None, limit=args.limit)
        print(f"Computed for {len(comp.get('computed', []))} symbols")
        if comp.get('compute_errors'):
            print(f"Compute errors: {len(comp.get('compute_errors'))}")
            for ce in comp.get('compute_errors')[:10]:
                print(f"  {ce}")

        print('Done')
    finally:
        try:
            conn.close()
        except Exception:
            pass

if __name__ == '__main__':
    main()
