"""
Test suite for options methods in InstrumentSelector
=====================================================
Tests the new options selection methods:
- get_nifty_options()
- get_banknifty_options()
- get_stock_options()
- _get_atm_strike()
"""
import sys
import os
from datetime import date
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dhan_trading.market_feed.instrument_selector import InstrumentSelector


def test_atm_strike_calculation():
    """Test ATM strike calculation for various underlyings."""
    print("\n" + "="*60)
    print("TEST 1: ATM Strike Calculation")
    print("="*60)
    
    selector = InstrumentSelector()
    
    # Test various underlyings
    test_cases = [
        ("NIFTY", 100),
        ("BANKNIFTY", 100),
        ("FINNIFTY", 100),
        ("HINDUNILVR", 5),
        ("TCS", 5),
    ]
    
    for underlying, strike_interval in test_cases:
        atm = selector._get_atm_strike(underlying, strike_interval)
        if atm:
            print(f"  {underlying:15} ATM Strike: {atm:8.0f}")
        else:
            print(f"  {underlying:15} ATM Strike: NOT AVAILABLE (no quote data)")
    
    print()
    return True


def test_nifty_options():
    """Test Nifty options selection."""
    print("\n" + "="*60)
    print("TEST 2: Nifty Options Selection")
    print("="*60)
    
    selector = InstrumentSelector()
    
    # Get Nifty options with 20 strike offset
    options = selector.get_nifty_options(
        strike_offset_levels=20,
        expiries=[0],
        option_types=['CE', 'PE']
    )
    
    print(f"  Total options found: {len(options)}")
    
    if options:
        # Get stats
        strikes = set([opt['strike_price'] for opt in options])
        atm = sorted(strikes)[len(strikes)//2] if strikes else None
        ce_count = len([o for o in options if o['option_type'] == 'CE'])
        pe_count = len([o for o in options if o['option_type'] == 'PE'])
        expiries = set([opt['expiry_date'] for opt in options])
        
        print(f"  Unique strikes: {len(strikes)}")
        print(f"  Strike range: {min(strikes)} - {max(strikes)}")
        print(f"  CE options: {ce_count}")
        print(f"  PE options: {pe_count}")
        print(f"  Expiry dates: {expiries}")
        print(f"\n  Sample options:")
        for opt in options[:5]:
            print(f"    {opt['display_name']:30} {opt['option_type']} {opt['strike_price']:8.0f} {opt['expiry_date']}")
    else:
        print("  WARNING: No options found!")
    
    print()
    return len(options) > 0


def test_banknifty_options():
    """Test BankNifty options selection."""
    print("\n" + "="*60)
    print("TEST 3: BankNifty Options Selection")
    print("="*60)
    
    selector = InstrumentSelector()
    
    # Get BankNifty options with 20 strike offset, both expiries
    options = selector.get_banknifty_options(
        strike_offset_levels=20,
        expiries=[0, 1],
        option_types=['CE', 'PE']
    )
    
    print(f"  Total options found: {len(options)}")
    
    if options:
        # Get stats
        strikes = set([opt['strike_price'] for opt in options])
        ce_count = len([o for o in options if o['option_type'] == 'CE'])
        pe_count = len([o for o in options if o['option_type'] == 'PE'])
        expiries = set([opt['expiry_date'] for opt in options])
        
        print(f"  Unique strikes: {len(strikes)}")
        print(f"  Strike range: {min(strikes)} - {max(strikes)}")
        print(f"  CE options: {ce_count}")
        print(f"  PE options: {pe_count}")
        print(f"  Expiry dates: {len(expiries)} different ({expiries})")
        print(f"\n  Sample options:")
        for opt in options[:5]:
            print(f"    {opt['display_name']:30} {opt['option_type']} {opt['strike_price']:8.0f} {opt['expiry_date']}")
    else:
        print("  WARNING: No options found!")
    
    print()
    return len(options) > 0


def test_stock_options():
    """Test stock options selection."""
    print("\n" + "="*60)
    print("TEST 4: Stock Options Selection")
    print("="*60)
    
    selector = InstrumentSelector()
    
    # Test with Nifty 50 stocks from our list
    test_stocks = ['TCS', 'HINDUNILVR', 'INFY', 'KOTAKBANK', 'MARUTI']
    
    options = selector.get_stock_options(
        symbols=test_stocks,
        strike_offset_levels=5,
        expiries=[0, 1],
        option_types=['CE', 'PE']
    )
    
    print(f"  Test stocks: {test_stocks}")
    print(f"  Total options found: {len(options)}")
    
    if options:
        # Group by underlying
        by_underlying = {}
        for opt in options:
            sym = opt['underlying_symbol']
            if sym not in by_underlying:
                by_underlying[sym] = {'CE': [], 'PE': []}
            by_underlying[sym][opt['option_type']].append(opt)
        
        print(f"\n  Options by symbol:")
        for sym in sorted(by_underlying.keys()):
            ce_count = len(by_underlying[sym]['CE'])
            pe_count = len(by_underlying[sym]['PE'])
            total = ce_count + pe_count
            print(f"    {sym:15} CE: {ce_count:3d}  PE: {pe_count:3d}  Total: {total:3d}")
        
        print(f"\n  Sample options:")
        for opt in options[:10]:
            print(f"    {opt['display_name']:30} {opt['option_type']} {opt['strike_price']:8.0f} {opt['expiry_date']}")
    else:
        print("  WARNING: No options found!")
    
    print()
    return len(options) > 0


def test_multi_stock_coverage():
    """Test coverage across multiple stocks from CSV data."""
    print("\n" + "="*60)
    print("TEST 5: Multi-Stock Coverage (from FNO CSV)")
    print("="*60)
    
    selector = InstrumentSelector()
    
    # Stocks from the provided CSV with highest OI change
    csv_stocks = [
        'OFSS', 'HINDZINC', 'EICHERMOT', 'DIXON', 'KAYNES',
        'SUPREMEIND', 'ADANIGREEN', 'INDIGO', 'PERSISTENT', 'ASIANPAINT',
        'TRENT', 'IOC', 'DMART', 'HINDUNILVR'
    ]
    
    options = selector.get_stock_options(
        symbols=csv_stocks,
        strike_offset_levels=5,
        expiries=[0],
        option_types=['CE', 'PE']
    )
    
    print(f"  CSV Stocks tested: {len(csv_stocks)}")
    print(f"  Total options found: {len(options)}")
    
    if options:
        by_underlying = {}
        for opt in options:
            sym = opt['underlying_symbol']
            if sym not in by_underlying:
                by_underlying[sym] = 0
            by_underlying[sym] += 1
        
        print(f"\n  Coverage by stock:")
        for sym in sorted(by_underlying.keys(), key=lambda x: -by_underlying[x]):
            print(f"    {sym:15} {by_underlying[sym]:4d} options")
    
    print()
    return True


def test_data_structure():
    """Verify returned data structure."""
    print("\n" + "="*60)
    print("TEST 6: Data Structure Validation")
    print("="*60)
    
    selector = InstrumentSelector()
    
    # Get a small sample
    options = selector.get_banknifty_options(
        strike_offset_levels=5,
        expiries=[0]
    )
    
    if options:
        opt = options[0]
        print(f"  Sample option data structure:")
        for key in sorted(opt.keys()):
            print(f"    {key:25} = {opt[key]}")
        
        # Verify required fields
        required_fields = ['security_id', 'symbol', 'display_name', 'strike_price', 
                          'option_type', 'expiry_date', 'underlying_symbol', 'instrument']
        
        print(f"\n  Required fields validation:")
        all_present = True
        for field in required_fields:
            if field in opt:
                print(f"    {field:25} OK")
            else:
                print(f"    {field:25} MISSING!")
                all_present = False
        
        return all_present
    else:
        print("  WARNING: No options data to validate!")
        return False


def run_all_tests():
    """Run all tests and report results."""
    print("\n")
    print("*" * 60)
    print("INSTRUMENT SELECTOR OPTIONS METHODS TEST SUITE")
    print("*" * 60)
    
    tests = [
        ("ATM Strike Calculation", test_atm_strike_calculation),
        ("Nifty Options", test_nifty_options),
        ("BankNifty Options", test_banknifty_options),
        ("Stock Options", test_stock_options),
        ("Multi-Stock Coverage", test_multi_stock_coverage),
        ("Data Structure", test_data_structure),
    ]
    
    results = {}
    for test_name, test_func in tests:
        try:
            result = test_func()
            results[test_name] = "PASS" if result else "FAIL"
        except Exception as e:
            print(f"  ERROR in {test_name}: {e}")
            results[test_name] = "ERROR"
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    for test_name, result in results.items():
        status_icon = "✓" if result == "PASS" else "✗" if result == "FAIL" else "⚠"
        print(f"  {status_icon} {test_name:40} {result}")
    
    # Statistics
    passed = sum(1 for r in results.values() if r == "PASS")
    failed = sum(1 for r in results.values() if r == "FAIL")
    errors = sum(1 for r in results.values() if r == "ERROR")
    
    print(f"\n  Total: {passed} passed, {failed} failed, {errors} errors")
    
    print("\n" + "*" * 60)
    return failed == 0 and errors == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
