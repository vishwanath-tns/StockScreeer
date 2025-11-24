"""
NSE Block & Bulk Deals Sync - CLI Application

Command-line interface for downloading Block and Bulk Deals data.
"""

import argparse
import sys
import os
from datetime import datetime, timedelta

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from block_bulk_deals.nse_deals_csv_downloader import (
    NSEDealsCSVDownloader as NSEDealsDownloader,
    NSEDealsDatabase,
    get_trading_dates
)


def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description='Download NSE Block & Bulk Deals data',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Download last 30 days
  python sync_deals_cli.py --days 30
  
  # Download specific date range
  python sync_deals_cli.py --from 2024-01-01 --to 2024-12-31
  
  # Download only block deals with higher rate limit
  python sync_deals_cli.py --days 90 --block-only --rate-limit 3.0
  
  # Download bulk deals for last year
  python sync_deals_cli.py --days 365 --bulk-only
  
  # Download 5 years (will take ~4-5 hours)
  python sync_deals_cli.py --years 5 --rate-limit 2.5
        """
    )
    
    # Date range options
    date_group = parser.add_mutually_exclusive_group(required=True)
    date_group.add_argument(
        '--days',
        type=int,
        help='Download last N days'
    )
    date_group.add_argument(
        '--years',
        type=int,
        help='Download last N years'
    )
    date_group.add_argument(
        '--from',
        dest='start_date',
        type=str,
        help='Start date (YYYY-MM-DD)'
    )
    
    parser.add_argument(
        '--to',
        dest='end_date',
        type=str,
        help='End date (YYYY-MM-DD), required with --from'
    )
    
    # Deal type options
    deal_group = parser.add_mutually_exclusive_group()
    deal_group.add_argument(
        '--block-only',
        action='store_true',
        help='Download only Block Deals'
    )
    deal_group.add_argument(
        '--bulk-only',
        action='store_true',
        help='Download only Bulk Deals'
    )
    
    # Other options
    parser.add_argument(
        '--rate-limit',
        type=float,
        default=2.0,
        help='Seconds between requests (default: 2.0, recommended: 2.5-3.0 for large downloads)'
    )
    
    parser.add_argument(
        '--skip-existing',
        action='store_true',
        default=True,
        help='Skip dates already downloaded (default: True)'
    )
    
    parser.add_argument(
        '--force',
        action='store_true',
        help='Re-download even if data exists'
    )
    
    parser.add_argument(
        '--stats',
        action='store_true',
        help='Show database statistics and exit'
    )
    
    args = parser.parse_args()
    
    # Show stats and exit
    if args.stats:
        show_stats()
        return 0
    
    # Validate date range
    if args.start_date:
        if not args.end_date:
            parser.error("--to is required when using --from")
        try:
            start_date = datetime.strptime(args.start_date, "%Y-%m-%d")
            end_date = datetime.strptime(args.end_date, "%Y-%m-%d")
        except ValueError:
            parser.error("Invalid date format. Use YYYY-MM-DD")
    elif args.days:
        end_date = datetime.now()
        start_date = end_date - timedelta(days=args.days)
    elif args.years:
        end_date = datetime.now()
        start_date = end_date - timedelta(days=args.years * 365)
    else:
        parser.error("Specify date range with --days, --years, or --from/--to")
    
    if start_date > end_date:
        parser.error("Start date must be before end date")
    
    # Validate rate limit
    if args.rate_limit < 0.5:
        print("⚠️  Warning: Rate limit too low, using minimum 0.5 seconds")
        args.rate_limit = 0.5
    
    # Skip existing override
    skip_existing = args.skip_existing and not args.force
    
    # Determine deal types
    download_block = not args.bulk_only
    download_bulk = not args.block_only
    
    # Print configuration
    print("=" * 80)
    print("NSE BLOCK & BULK DEALS DOWNLOADER")
    print("=" * 80)
    print(f"Date Range: {start_date.date()} to {end_date.date()}")
    print(f"Deal Types: {'BLOCK' if download_block else ''} {'BULK' if download_bulk else ''}")
    print(f"Rate Limit: {args.rate_limit}s per request")
    print(f"Skip Existing: {skip_existing}")
    
    # Get trading dates
    dates = get_trading_dates(start_date, end_date)
    total_dates = len(dates)
    
    print(f"Trading Days: {total_dates}")
    
    # Estimate time
    requests_per_date = (1 if download_block else 0) + (1 if download_bulk else 0)
    estimated_time = total_dates * requests_per_date * args.rate_limit / 60
    print(f"Estimated Time: {estimated_time:.1f} minutes")
    
    # Confirm if large download
    if total_dates > 100:
        print("\n⚠️  This is a large download!")
        response = input("Continue? (y/n): ")
        if response.lower() != 'y':
            print("Aborted.")
            return 0
    
    print("=" * 80)
    print()
    
    # Initialize
    downloader = NSEDealsDownloader(rate_limit=args.rate_limit)
    database = NSEDealsDatabase()
    
    # Get existing dates if skip enabled
    skip_block_dates = set()
    skip_bulk_dates = set()
    
    if skip_existing:
        if download_block:
            skip_block_dates = database.get_imported_dates("BLOCK")
            print(f"📋 Found {len(skip_block_dates)} existing BLOCK deal dates")
            
        if download_bulk:
            skip_bulk_dates = database.get_imported_dates("BULK")
            print(f"📋 Found {len(skip_bulk_dates)} existing BULK deal dates")
            
        print()
    
    # Counters
    block_total = 0
    bulk_total = 0
    failed = 0
    
    # Download
    try:
        for idx, date in enumerate(dates, 1):
            date_str = date.strftime("%d-%b-%Y")
            print(f"[{idx:4d}/{total_dates}] {date_str}", end="")
            
            # Block deals
            if download_block:
                if skip_existing and date.date() in skip_block_dates:
                    print(" | BLOCK: ⏭️", end="")
                else:
                    df = downloader.download_block_deals(date)
                    if df is not None:
                        if not df.empty:
                            new_records, _ = database.save_deals(df, "BLOCK")
                            block_total += new_records
                            print(f" | BLOCK: ✅ {new_records:3d}", end="")
                            database.log_import(date, "BLOCK", new_records, "SUCCESS")
                        else:
                            print(" | BLOCK: --", end="")
                            database.log_import(date, "BLOCK", 0, "NO_DATA")
                    else:
                        failed += 1
                        print(" | BLOCK: ❌", end="")
                        database.log_import(date, "BLOCK", 0, "FAILED", "Download failed")
            
            # Bulk deals
            if download_bulk:
                if skip_existing and date.date() in skip_bulk_dates:
                    print(" | BULK: ⏭️", end="")
                else:
                    df = downloader.download_bulk_deals(date)
                    if df is not None:
                        if not df.empty:
                            new_records, _ = database.save_deals(df, "BULK")
                            bulk_total += new_records
                            print(f" | BULK: ✅ {new_records:3d}", end="")
                            database.log_import(date, "BULK", new_records, "SUCCESS")
                        else:
                            print(" | BULK: --", end="")
                            database.log_import(date, "BULK", 0, "NO_DATA")
                    else:
                        failed += 1
                        print(" | BULK: ❌", end="")
                        database.log_import(date, "BULK", 0, "FAILED", "Download failed")
            
            print()  # Newline
            
            # Progress update every 50 dates
            if idx % 50 == 0:
                print(f"    Progress: {idx}/{total_dates} ({idx*100/total_dates:.1f}%) | "
                      f"Block: {block_total:,} | Bulk: {bulk_total:,} | Failed: {failed}")
                print()
        
        # Summary
        print()
        print("=" * 80)
        print("DOWNLOAD COMPLETE")
        print("=" * 80)
        print(f"Block Deals: {block_total:,}")
        print(f"Bulk Deals: {bulk_total:,}")
        print(f"Failed: {failed}")
        print("=" * 80)
        
        return 0
        
    except KeyboardInterrupt:
        print("\n\n⏸️ Download interrupted by user")
        print(f"Block Deals Downloaded: {block_total:,}")
        print(f"Bulk Deals Downloaded: {bulk_total:,}")
        return 1
        
    except Exception as e:
        print(f"\n\n❌ Error: {e}")
        return 1
        
    finally:
        downloader.close()


def show_stats():
    """Show database statistics"""
    try:
        database = NSEDealsDatabase()
        stats = database.get_import_stats()
        
        print("=" * 80)
        print("DATABASE STATISTICS")
        print("=" * 80)
        
        print("\n📊 BLOCK DEALS:")
        block = stats['block_deals']
        print(f"  Total Deals: {block['total_deals']:,}")
        if block['total_deals'] > 0:
            print(f"  Date Range: {block['earliest_date']} to {block['latest_date']}")
            print(f"  Unique Symbols: {block['unique_symbols']:,}")
            print(f"  Unique Clients: {block['unique_clients']:,}")
        
        print("\n📊 BULK DEALS:")
        bulk = stats['bulk_deals']
        print(f"  Total Deals: {bulk['total_deals']:,}")
        if bulk['total_deals'] > 0:
            print(f"  Date Range: {bulk['earliest_date']} to {bulk['latest_date']}")
            print(f"  Unique Symbols: {bulk['unique_symbols']:,}")
            print(f"  Unique Clients: {bulk['unique_clients']:,}")
        
        print("\n" + "=" * 80)
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
