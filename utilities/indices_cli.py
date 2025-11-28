#!/usr/bin/env python3
"""
Command Line Interface for NSE Indices Management System
========================================================

This module provides a command-line interface for importing index files
and managing the indices database.
"""

import argparse
import sys
import os
from pathlib import Path
from datetime import date, datetime
import logging

# Add parent directory to path
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(parent_dir)

from indices_manager.importer import IndicesImporter
from indices_manager.api import indices_api
from indices_manager.models import ImportStatus


def setup_logging(verbose: bool = False):
    """Set up logging configuration"""
    level = logging.DEBUG if verbose else logging.INFO
    
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )


def import_file_command(args):
    """Import a single CSV file"""
    print(f"Importing file: {args.file}")
    
    if not os.path.exists(args.file):
        print(f"Error: File not found: {args.file}")
        return False
    
    importer = IndicesImporter()
    success = importer.import_csv_file(args.file, skip_duplicates=not args.force)
    
    if success:
        print(f"✅ Successfully imported: {args.file}")
        return True
    else:
        print(f"❌ Failed to import: {args.file}")
        return False


def import_directory_command(args):
    """Import all CSV files from a directory"""
    print(f"Importing files from directory: {args.directory}")
    
    if not os.path.exists(args.directory):
        print(f"Error: Directory not found: {args.directory}")
        return False
    
    importer = IndicesImporter()
    results = importer.import_directory(
        args.directory, 
        file_pattern=args.pattern,
        skip_duplicates=not args.force
    )
    
    if results['success']:
        print(f"✅ Import completed successfully")
        print(f"   Files processed: {results['files_processed']}")
        print(f"   Files imported: {results['files_imported']}")
        
        if results['files_skipped'] > 0:
            print(f"   Files skipped: {results['files_skipped']}")
        
        if results['failed_files']:
            print(f"   Failed files: {', '.join(results['failed_files'])}")
        
        if results['errors']:
            print("   Errors:")
            for error in results['errors']:
                print(f"     - {error}")
        
        return True
    else:
        print(f"❌ Import failed: {results.get('error', 'Unknown error')}")
        return False


def list_indices_command(args):
    """List all available indices"""
    try:
        indices = indices_api.get_all_indices(category=args.category, sector=args.sector)
        
        if not indices:
            print("No indices found.")
            return True
        
        print(f"Found {len(indices)} indices:")
        print("-" * 80)
        
        if args.format == 'table':
            # Table format
            print(f"{'Code':<25} {'Name':<35} {'Category':<12} {'Sector':<15}")
            print("-" * 80)
            
            for index in indices:
                sector = index.get('sector') or 'N/A'
                print(f"{index['index_code']:<25} {index['index_name']:<35} {index['category']:<12} {sector:<15}")
        
        elif args.format == 'detailed':
            # Detailed format
            for i, index in enumerate(indices, 1):
                print(f"{i}. {index['index_code']} - {index['index_name']}")
                print(f"   Category: {index['category']}")
                print(f"   Sector: {index.get('sector', 'N/A')}")
                print(f"   Created: {index['created_at']}")
                print(f"   Updated: {index['updated_at']}")
                print()
        
        else:  # simple format
            for index in indices:
                print(f"{index['index_code']:<25} - {index['index_name']}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error listing indices: {e}")
        return False


def show_status_command(args):
    """Show import status and data availability"""
    try:
        print("=== Import Status (Last 30 days) ===")
        
        status_df = indices_api.get_import_status(days=30)
        
        if status_df.empty:
            print("No recent imports found.")
        else:
            # Group by status
            status_counts = status_df.groupby('status').size()
            
            print(f"Total imports: {len(status_df)}")
            for status, count in status_counts.items():
                emoji = "✅" if status == ImportStatus.COMPLETED.value else "❌" if status == ImportStatus.FAILED.value else "⏳"
                print(f"  {emoji} {status}: {count}")
            
            # Show recent failures
            failed_imports = status_df[status_df['status'] == ImportStatus.FAILED.value]
            if not failed_imports.empty:
                print(f"\\n❌ Recent Failures:")
                for _, row in failed_imports.head(5).iterrows():
                    print(f"  - {row['filename']}: {row['error_message']}")
        
        print("\\n=== Data Availability ===")
        
        availability_df = indices_api.get_data_availability()
        
        if availability_df.empty:
            print("No data available.")
        else:
            print(f"{'Index Code':<25} {'Data Points':<12} {'Earliest':<12} {'Latest':<12} {'Days':<8}")
            print("-" * 70)
            
            for _, row in availability_df.head(10).iterrows():
                earliest = row['earliest_date'].strftime('%Y-%m-%d') if row['earliest_date'] else 'N/A'
                latest = row['latest_date'].strftime('%Y-%m-%d') if row['latest_date'] else 'N/A'
                days = int(row['date_range_days']) if row['date_range_days'] else 0
                
                print(f"{row['index_code']:<25} {row['data_points']:<12} {earliest:<12} {latest:<12} {days:<8}")
            
            if len(availability_df) > 10:
                print(f"... and {len(availability_df) - 10} more indices")
        
        return True
        
    except Exception as e:
        print(f"❌ Error showing status: {e}")
        return False


def show_data_command(args):
    """Show index data"""
    try:
        if args.constituents:
            # Show constituents
            print(f"=== Constituents for {args.index_code} ===")
            
            df = indices_api.get_index_constituents(args.index_code, active_only=True)
            
            if df.empty:
                print("No constituents data found.")
                return True
            
            data_date = df['data_date'].iloc[0]
            print(f"Data Date: {data_date}")
            print(f"Total Constituents: {len(df)}")
            print()
            
            # Show top performers
            print("Top 10 Gainers:")
            top_gainers = df.nlargest(10, 'change_percent')[['symbol', 'close_price', 'change_percent', 'weight_percent']]
            for _, row in top_gainers.iterrows():
                print(f"  {row['symbol']:<15} {row['close_price']:>8.2f} {row['change_percent']:>6.2f}% (Weight: {row['weight_percent']:>5.2f}%)")
            
            print("\\nTop 10 Losers:")
            top_losers = df.nsmallest(10, 'change_percent')[['symbol', 'close_price', 'change_percent', 'weight_percent']]
            for _, row in top_losers.iterrows():
                print(f"  {row['symbol']:<15} {row['close_price']:>8.2f} {row['change_percent']:>6.2f}% (Weight: {row['weight_percent']:>5.2f}%)")
        
        else:
            # Show index data
            print(f"=== Index Data for {args.index_code} ===")
            
            # Latest data
            latest = indices_api.get_latest_index_data(args.index_code)
            
            if not latest:
                print("No index data found.")
                return True
            
            print(f"Date: {latest['data_date']}")
            print(f"Close: {latest['close_value']:,.2f}")
            print(f"Change: {latest['change_points']:+,.2f} ({latest['change_percent']:+.2f}%)")
            print(f"Volume: {latest['volume']:,}")
            print(f"Value (Cr): {latest['value_crores']:,.2f}")
            print(f"52W High: {latest['week52_high']:,.2f}")
            print(f"52W Low: {latest['week52_low']:,.2f}")
            
            # Performance
            performance = indices_api.get_index_performance(args.index_code)
            
            if performance:
                print("\\nPerformance:")
                for period, perf in performance.items():
                    if perf is not None:
                        print(f"  {period}: {perf:+.2f}%")
        
        return True
        
    except Exception as e:
        print(f"❌ Error showing data: {e}")
        return False


def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description='NSE Indices Management System CLI',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Import a single file
  python indices_cli.py import file data/NIFTY-50.csv
  
  # Import all CSV files from a directory
  python indices_cli.py import dir indices/
  
  # List all indices
  python indices_cli.py list indices
  
  # List sectoral indices
  python indices_cli.py list indices --category SECTORAL
  
  # Show system status
  python indices_cli.py status
  
  # Show latest data for NIFTY-50
  python indices_cli.py show NIFTY-50
  
  # Show NIFTY-50 constituents
  python indices_cli.py show NIFTY-50 --constituents
        """
    )
    
    parser.add_argument('-v', '--verbose', action='store_true',
                       help='Enable verbose logging')
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Import commands
    import_parser = subparsers.add_parser('import', help='Import index data')
    import_subparsers = import_parser.add_subparsers(dest='import_type', help='Import type')
    
    # Import file command
    file_parser = import_subparsers.add_parser('file', help='Import a single CSV file')
    file_parser.add_argument('file', help='Path to CSV file')
    file_parser.add_argument('--force', action='store_true',
                            help='Force import even if file was already imported')
    
    # Import directory command
    dir_parser = import_subparsers.add_parser('dir', help='Import all CSV files from directory')
    dir_parser.add_argument('directory', help='Path to directory containing CSV files')
    dir_parser.add_argument('--pattern', default='*.csv',
                           help='File pattern to match (default: *.csv)')
    dir_parser.add_argument('--force', action='store_true',
                           help='Force import even if files were already imported')
    
    # List commands
    list_parser = subparsers.add_parser('list', help='List data')
    list_subparsers = list_parser.add_subparsers(dest='list_type', help='List type')
    
    # List indices command
    indices_parser = list_subparsers.add_parser('indices', help='List available indices')
    indices_parser.add_argument('--category', choices=['MAIN', 'SECTORAL', 'THEMATIC'],
                               help='Filter by category')
    indices_parser.add_argument('--sector', help='Filter by sector')
    indices_parser.add_argument('--format', choices=['simple', 'table', 'detailed'],
                               default='table', help='Output format')
    
    # Status command
    subparsers.add_parser('status', help='Show import status and data availability')
    
    # Show data command
    show_parser = subparsers.add_parser('show', help='Show index data')
    show_parser.add_argument('index_code', help='Index code (e.g., NIFTY-50)')
    show_parser.add_argument('--constituents', action='store_true',
                           help='Show index constituents instead of index data')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    # Set up logging
    setup_logging(args.verbose)
    
    try:
        # Route to appropriate command
        if args.command == 'import':
            if args.import_type == 'file':
                success = import_file_command(args)
            elif args.import_type == 'dir':
                success = import_directory_command(args)
            else:
                print("Error: Please specify import type (file or dir)")
                return 1
        
        elif args.command == 'list':
            if args.list_type == 'indices':
                success = list_indices_command(args)
            else:
                print("Error: Please specify list type (indices)")
                return 1
        
        elif args.command == 'status':
            success = show_status_command(args)
        
        elif args.command == 'show':
            success = show_data_command(args)
        
        else:
            print(f"Error: Unknown command: {args.command}")
            return 1
        
        return 0 if success else 1
        
    except KeyboardInterrupt:
        print("\\n⚠️  Operation cancelled by user")
        return 1
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())