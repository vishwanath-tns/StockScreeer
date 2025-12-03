#!/usr/bin/env python3
"""
Volume Analysis Scanner
=======================

Scan Nifty 500 stocks for accumulation and distribution patterns.
Uses data from the marketdata MySQL database (no downloads required).

Usage:
    python volume_analysis_scanner.py                    # Scan all Nifty 500
    python volume_analysis_scanner.py --top 30           # Show top 30 results
    python volume_analysis_scanner.py --symbol RELIANCE  # Analyze single stock
    python volume_analysis_scanner.py --chart RELIANCE   # Generate chart
    python volume_analysis_scanner.py --export           # Export to CSV

Indicators Used:
    - OBV (On-Balance Volume) - Cumulative volume flow
    - A/D Line (Accumulation/Distribution) - Money flow based on close location  
    - CMF (Chaikin Money Flow) - 20-day money flow ratio
    - Volume patterns - Dry-up, surge, trend analysis

Scoring:
    - 75-100: Strong accumulation (institutional buying)
    - 55-74: Moderate accumulation
    - 45-54: Neutral
    - 25-44: Moderate distribution
    - 0-24: Strong distribution (institutional selling)
"""

import argparse
import logging
import sys
from datetime import datetime
from typing import Optional

from volume_analysis import VolumeScanner, AccumulationDetector, VolumeIndicators
from volume_analysis.visualization.volume_charts import VolumeChartGenerator
from volume_analysis.analysis.accumulation_detector import PhaseType, SignalStrength

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


def print_banner():
    """Print a nice banner."""
    print("""
╔══════════════════════════════════════════════════════════════════════════════╗
║                        📊 VOLUME ANALYSIS SCANNER                             ║
║                  Detect Accumulation & Distribution Patterns                  ║
╚══════════════════════════════════════════════════════════════════════════════╝
    """)


def scan_all_stocks(top_n: int = 20, export: bool = False, 
                    min_volume: int = 100000, min_price: float = 10.0):
    """
    Scan all Nifty 500 stocks and display results.
    
    Args:
        top_n: Number of top results to show
        export: Whether to export to CSV
        min_volume: Minimum average volume filter
        min_price: Minimum price filter
    """
    print(f"\n🔍 Scanning stocks from database...")
    print(f"   Filters: Min Volume = {min_volume:,}, Min Price = ₹{min_price}")
    print()
    
    scanner = VolumeScanner(
        lookback_days=90,
        min_volume=min_volume,
        min_price=min_price
    )
    
    # Progress callback
    start_time = datetime.now()
    
    def progress(current, total, symbol):
        elapsed = (datetime.now() - start_time).seconds
        pct = current / total * 100
        bar = "█" * int(pct / 5) + "░" * (20 - int(pct / 5))
        print(f"\r   [{bar}] {pct:.0f}% ({current}/{total}) - {symbol:<15} [{elapsed}s]", end="", flush=True)
    
    results = scanner.scan_nifty500(progress_callback=progress)
    
    print("\n")
    
    # Display results
    scanner.display_results(results, top_n=top_n)
    
    # Summary stats
    print("\n" + "=" * 80)
    print("📈 ANALYSIS SUMMARY")
    print("=" * 80)
    
    # Accumulation breakdown
    strong_acc = len([s for s in results.accumulation if s.strength == SignalStrength.STRONG])
    mod_acc = len([s for s in results.accumulation if s.strength == SignalStrength.MODERATE])
    weak_acc = len([s for s in results.accumulation if s.strength == SignalStrength.WEAK])
    
    # Distribution breakdown
    strong_dist = len([s for s in results.distribution if s.strength == SignalStrength.STRONG])
    mod_dist = len([s for s in results.distribution if s.strength == SignalStrength.MODERATE])
    weak_dist = len([s for s in results.distribution if s.strength == SignalStrength.WEAK])
    
    print(f"""
Accumulation Stocks: {len(results.accumulation)}
    Strong:   {strong_acc}  ████████
    Moderate: {mod_acc}  ████
    Weak:     {weak_acc}  ██

Distribution Stocks: {len(results.distribution)}
    Strong:   {strong_dist}  ████████
    Moderate: {mod_dist}  ████
    Weak:     {weak_dist}  ██

Neutral Stocks: {len(results.neutral)}
Failed/Filtered: {len(results.errors)}
    """)
    
    # Export if requested
    if export:
        filename = scanner.export_to_csv(results)
        print(f"\n✅ Results exported to: {filename}")
    
    return results


def analyze_single_stock(symbol: str, show_details: bool = True):
    """
    Analyze a single stock in detail.
    
    Args:
        symbol: Stock symbol (e.g., 'RELIANCE' or 'RELIANCE.NS')
    """
    # Add .NS if not present
    if not symbol.endswith('.NS') and not symbol.endswith('.BO'):
        symbol = f"{symbol}.NS"
    
    print(f"\n🔍 Analyzing {symbol}...")
    print()
    
    scanner = VolumeScanner()
    signal = scanner.scan_symbol(symbol)
    
    if signal is None:
        print(f"❌ Could not analyze {symbol}. Check if data exists in database.")
        return None
    
    # Phase emoji
    phase_emoji = "🟢" if signal.phase == PhaseType.ACCUMULATION else \
                  "🔴" if signal.phase == PhaseType.DISTRIBUTION else "⚪"
    
    print("=" * 70)
    print(f"{phase_emoji} {symbol} - {signal.phase.value.upper()}")
    print("=" * 70)
    
    print(f"""
📊 OVERALL ASSESSMENT
────────────────────────────────────────────────────────────────────
Phase:       {signal.phase.value.upper()}
Strength:    {signal.strength.value.upper()}
Score:       {signal.score:.1f} / 100
────────────────────────────────────────────────────────────────────

📈 COMPONENT SCORES
────────────────────────────────────────────────────────────────────
OBV Score:          {signal.obv_score:.1f}  {'█' * int(signal.obv_score / 10)}
A/D Line Score:     {signal.ad_score:.1f}  {'█' * int(signal.ad_score / 10)}
CMF Score:          {signal.cmf_score:.1f}  {'█' * int(signal.cmf_score / 10)}
Volume Score:       {signal.volume_score:.1f}  {'█' * int(signal.volume_score / 10)}
Price Action Score: {signal.price_action_score:.1f}  {'█' * int(signal.price_action_score / 10)}
────────────────────────────────────────────────────────────────────
    """)
    
    if show_details and signal.details:
        print("📋 DETAILED ANALYSIS")
        print("────────────────────────────────────────────────────────────────────")
        
        # OBV details
        obv = signal.details.get('obv', {})
        if obv:
            print(f"\nOBV (On-Balance Volume):")
            print(f"  Trending: {'↑ UP (Bullish)' if obv.get('trending_up') else '↓ DOWN (Bearish)'}")
            print(f"  20-day Change: {obv.get('change_20d_pct', 0):.1f}%")
            if obv.get('divergence'):
                print(f"  ⚠️ Divergence: {obv.get('divergence')}")
        
        # CMF details
        cmf = signal.details.get('cmf', {})
        if cmf:
            cmf_val = cmf.get('current', 0)
            print(f"\nCMF (Chaikin Money Flow):")
            print(f"  Current: {cmf_val:.3f} {'(Buying Pressure)' if cmf_val > 0 else '(Selling Pressure)'}")
            print(f"  5-day Avg: {cmf.get('avg_5d', 0):.3f}")
            print(f"  20-day Avg: {cmf.get('avg_20d', 0):.3f}")
            print(f"  Trend: {'↑ Improving' if cmf.get('improving') else '↓ Deteriorating'}")
        
        # Volume details
        vol = signal.details.get('volume', {})
        if vol:
            print(f"\nVolume Patterns:")
            print(f"  Avg Volume Ratio: {vol.get('avg_volume_ratio', 0):.2f}x")
            print(f"  Volume Dry-up: {'Yes ⚡' if vol.get('has_dryup') else 'No'}")
            print(f"  Volume Surge: {'Yes 📈' if vol.get('has_surge') else 'No'}")
        
        # Price action
        price = signal.details.get('price_action', {})
        if price:
            print(f"\nPrice Action:")
            print(f"  Current Price: ₹{price.get('current_close', 0):.2f}")
            print(f"  Position in Range: {price.get('position_in_range', 0) * 100:.1f}%")
            print(f"  20-day Change: {price.get('change_20d_pct', 0):.1f}%")
            print(f"  Higher Lows: {'Yes ✓' if price.get('higher_lows') else 'No'}")
            print(f"  Lower Highs: {'Yes ✓' if price.get('lower_highs') else 'No'}")
    
    print()
    
    return signal


def generate_chart(symbol: str, save_path: str = None, style: str = 'dark'):
    """
    Generate a volume analysis chart for a stock.
    
    Args:
        symbol: Stock symbol
        save_path: Path to save chart (optional)
        style: Chart style ('dark' or 'light')
    """
    # Add .NS if not present
    if not symbol.endswith('.NS') and not symbol.endswith('.BO'):
        symbol = f"{symbol}.NS"
    
    print(f"\n📊 Generating chart for {symbol}...")
    
    scanner = VolumeScanner()
    df = scanner.get_stock_data(symbol)
    
    if df is None or df.empty:
        print(f"❌ No data found for {symbol}")
        return
    
    detector = AccumulationDetector()
    signal = detector.analyze(df, symbol)
    
    if save_path is None:
        save_path = f"volume_chart_{symbol.replace('.', '_')}.png"
    
    chart_gen = VolumeChartGenerator(style=style)
    chart_gen.create_volume_analysis_chart(
        df,
        symbol=symbol,
        signal=signal,
        save_path=save_path,
        show=True
    )
    
    print(f"\n✅ Chart saved to: {save_path}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Volume Analysis Scanner - Detect Accumulation & Distribution Patterns",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python volume_analysis_scanner.py                    # Scan all stocks
  python volume_analysis_scanner.py --top 30           # Show top 30 results
  python volume_analysis_scanner.py --symbol RELIANCE  # Analyze RELIANCE
  python volume_analysis_scanner.py --chart TCS        # Generate chart for TCS
  python volume_analysis_scanner.py --export           # Export results to CSV
        """
    )
    
    parser.add_argument('--symbol', '-s', type=str, help='Analyze a single stock')
    parser.add_argument('--chart', '-c', type=str, help='Generate chart for a stock')
    parser.add_argument('--top', '-t', type=int, default=20, help='Number of top results to show')
    parser.add_argument('--export', '-e', action='store_true', help='Export results to CSV')
    parser.add_argument('--min-volume', type=int, default=100000, help='Minimum average volume')
    parser.add_argument('--min-price', type=float, default=10.0, help='Minimum stock price')
    parser.add_argument('--style', type=str, default='dark', choices=['dark', 'light'], 
                       help='Chart style')
    parser.add_argument('--quiet', '-q', action='store_true', help='Suppress banner')
    
    args = parser.parse_args()
    
    if not args.quiet:
        print_banner()
    
    try:
        if args.chart:
            # Generate chart
            generate_chart(args.chart, style=args.style)
        elif args.symbol:
            # Analyze single stock
            analyze_single_stock(args.symbol)
        else:
            # Scan all stocks
            scan_all_stocks(
                top_n=args.top,
                export=args.export,
                min_volume=args.min_volume,
                min_price=args.min_price
            )
            
    except KeyboardInterrupt:
        print("\n\n⚠️ Scan interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Error: {e}")
        raise


if __name__ == "__main__":
    main()
