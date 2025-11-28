#!/usr/bin/env python3
"""
Test all dashboard button links to verify scripts exist
"""

import os

# Get the base directory
BASE_DIR = os.path.dirname(__file__)

# All scripts referenced in the dashboard
SCRIPTS = {
    "Download Data Tab": [
        "yahoo_finance_service/yfinance_downloader_gui.py",
        "yahoo_finance_service/chart_visualizer.py",
        "yahoo_finance_service/bulk_stock_downloader.py",
        "check_and_update_daily_quotes.py",
        "quick_download_today.py",
        "quick_download_nifty500.py",
        "download_nifty500_bulk.py",
        "download_indices_data.py",
        "download_indices_today.py",
        "yahoo_finance_service/smart_download.py",
        "auto_map_nifty500_to_yahoo.py",
    ],
    "Diagnostics Tab": [
        "check_all_symbols_completeness.py",
        "check_nifty500_yesterday.py",
        "check_previous_close_coverage.py",
        "check_nifty500_coverage.py",
        "analyze_symbol_formats.py",
        "check_nifty500_symbol_mapping.py",
        "check_active_symbols.py",
        "find_optimal_symbol_list.py",
        "check_indices_tables.py",
        "check_indices.py",
        "check_data_size.py",
        "check_structures.py",
        "check_nifty_symbol.py",
        "check_yfinance_symbols.py",
        "test_chart_data.py",
    ],
    "Real-time Tab": [
        "realtime_adv_decl_dashboard.py",
        "intraday_adv_decl_viewer.py",
        "intraday_1min_viewer.py",
        "intraday_charts_viewer.py",
        # "realtime_yahoo_service/main.py",  # Special handler
        "check_service_status.py",
        # "realtime_yahoo_service/dashboard.html",  # Special handler
        "nifty500_adv_decl_calculator.py",
        "nifty500_adv_decl_visualizer.py",
        "test_market_breadth_integration.py",
    ],
    "Analysis Tab": [
        "yahoo_finance_service/chart_visualizer.py",  # duplicate
        "stock_chart_with_ratings.py",
        "launch_stock_charts.py",
        "nifty500_momentum_scanner.py",
        "scanner_gui.py",
        "vcp_market_scanner.py",
        "nifty500_momentum_report.py",
        "final_nifty50_sector_report.py",
        "demo_pdf_reports.py",
        "verify_data_accuracy.py",
        "quick_accuracy_check.py",
        "test_yfinance_connectivity.py",
    ],
    "Maintenance Tab": [
        "yahoo_finance_service/create_tables.py",
        "yahoo_finance_service/setup.py",
        "create_indices_tables.py",
        "create_nse_yahoo_symbol_mapping.py",
        "auto_map_nifty500_to_yahoo.py",  # duplicate
        "update_symbol_mappings.py",
        "auto_verify_symbols.py",
        "rebuild_intraday_data.py",
        "rebuild_intraday_full.py",
        "refetch_nifty_today.py",
    ],
    "Documentation": [
        "DUPLICATE_PREVENTION.md",
        "yahoo_finance_service/CHART_VISUALIZER_README.md",
        "REALTIME_DASHBOARD_HISTORY.md",
        "ENHANCED_MARKET_BREADTH_IMPLEMENTATION.md",
    ]
}

def main():
    """Test all script paths"""
    print("=" * 80)
    print("DASHBOARD LINK VALIDATION TEST")
    print("=" * 80)
    print()
    
    total_scripts = 0
    found_scripts = 0
    missing_scripts = []
    
    for category, scripts in SCRIPTS.items():
        print(f"\n{category}")
        print("-" * 80)
        
        for script in scripts:
            total_scripts += 1
            full_path = os.path.join(BASE_DIR, script)
            
            if os.path.exists(full_path):
                print(f"  ✓ {script}")
                found_scripts += 1
            else:
                print(f"  ✗ {script} - MISSING")
                missing_scripts.append(script)
    
    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Total scripts: {total_scripts}")
    print(f"Found: {found_scripts} ({found_scripts/total_scripts*100:.1f}%)")
    print(f"Missing: {len(missing_scripts)} ({len(missing_scripts)/total_scripts*100:.1f}%)")
    
    if missing_scripts:
        print("\n" + "=" * 80)
        print("MISSING SCRIPTS")
        print("=" * 80)
        for script in missing_scripts:
            print(f"  • {script}")
    
    print("\n" + "=" * 80)
    if len(missing_scripts) == 0:
        print("✓ ALL SCRIPTS FOUND - Dashboard links are valid!")
    else:
        print("⚠ Some scripts are missing - Dashboard may have broken links")
    print("=" * 80)

if __name__ == '__main__':
    main()
