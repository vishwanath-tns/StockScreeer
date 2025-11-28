"""sync_bhav_cli.py

Small CLI wrapper around sync_folder in sync_bhav_gui.

Usage:
    python sync_bhav_cli.py [--dry-run] [--quarantine <path>] [--list-files]

Options:
    --dry-run        : Parse files and report counts but do not write to DB or move files
    --quarantine DIR : Directory to move failing files into (defaults to <BHAV_FOLDER>/quarantine)
    --limit N        : Only process the N most recent files (helpful for testing)
"""
import argparse
from pathlib import Path
import sys

def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument('--dry-run', action='store_true', help='Parse files and report upsert counts but do not write to DB')
    p.add_argument('--quarantine', type=str, default=None, help='Path to quarantine folder for failing files')
    p.add_argument('--quarantine-on', type=str, default='all', choices=['all','parsing','db','none'], help='Which error types to quarantine (all, parsing, db, none)')
    p.add_argument('--limit', type=int, default=0, help='Limit to N most recent files (0 = all)')
    args = p.parse_args(argv)

    try:
        import sync_bhav_gui as s
    except Exception as e:
        print('Failed to import sync_bhav_gui:', e)
        raise

    qdir = Path(args.quarantine) if args.quarantine else None

    # discover files (optionally limit)
    files = list(s.discover_files(s.BHAV_FOLDER))
    files_sorted = sorted(files)
    if args.limit and args.limit > 0:
        files_sorted = files_sorted[-args.limit:]

    print(f"Found {len(files_sorted)} files to process (dry-run={args.dry_run})")

    # call sync_folder with dry_run/quarantine
    processed, skipped, failed = s.sync_folder(progress_cb=None, log_cb=print, dry_run=args.dry_run, quarantine_dir=qdir, quarantine_on=args.quarantine_on)
    print(f"Finished. Imported: {processed}, Skipped: {skipped}, Failed: {failed}")

if __name__ == '__main__':
    main()
