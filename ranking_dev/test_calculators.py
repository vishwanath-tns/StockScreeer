"""
Test Ranking System Components

Run this to verify all calculators work correctly.
Uses synthetic data - no database required.
"""

import sys
from datetime import date, timedelta
from typing import Dict
import pandas as pd
import numpy as np

# Add parent to path
sys.path.insert(0, ".")

from ranking_dev.rs_rating import RSRatingCalculator
from ranking_dev.momentum import MomentumScoreCalculator
from ranking_dev.trend_template import TrendTemplateCalculator
from ranking_dev.technical import TechnicalScoreCalculator
from ranking_dev.composite import CompositeScoreCalculator


def generate_test_data(num_stocks: int = 20) -> Dict[str, pd.DataFrame]:
    """
    Generate synthetic price data for testing.
    
    Creates stocks with varying trends:
    - Strong uptrend
    - Moderate uptrend
    - Sideways
    - Downtrend
    """
    np.random.seed(42)  # Reproducible
    today = date.today()
    data = {}
    
    for i in range(num_stocks):
        symbol = f"TEST{i+1:02d}"
        
        # Vary the trend
        if i < num_stocks * 0.25:
            # Strong uptrend (top 25%)
            trend = np.random.uniform(0.5, 1.0)
        elif i < num_stocks * 0.5:
            # Moderate uptrend
            trend = np.random.uniform(0.1, 0.4)
        elif i < num_stocks * 0.75:
            # Sideways
            trend = np.random.uniform(-0.1, 0.1)
        else:
            # Downtrend
            trend = np.random.uniform(-0.4, -0.1)
        
        # Generate 350 days of data
        dates = pd.date_range(end=today, periods=350, freq="D")
        start_price = 100
        
        # Create price series with trend + noise
        prices = []
        for j in range(350):
            noise = np.random.uniform(-0.02, 0.02)
            p = start_price * (1 + trend * j/350 + noise)
            prices.append(max(1, p))  # Ensure positive
        
        df = pd.DataFrame({
            "date": dates,
            "open": [p * 0.995 for p in prices],
            "high": [p * 1.02 for p in prices],
            "low": [p * 0.98 for p in prices],
            "close": prices,
            "volume": [np.random.randint(100000, 1000000) for _ in prices],
        })
        
        data[symbol] = df
    
    return data


def test_rs_rating():
    """Test RS Rating Calculator."""
    print("\n" + "="*60)
    print("TEST: RS Rating Calculator")
    print("="*60)
    
    calc = RSRatingCalculator()
    data = generate_test_data(20)
    today = date.today()
    
    results = calc.calculate_batch(data, today)
    
    # Verify
    successful = [r for r in results.values() if r.success]
    print(f"Successful calculations: {len(successful)}/{len(results)}")
    
    # Check ranking
    sorted_results = sorted(successful, key=lambda r: r.rank)
    
    print("\nTop 5 by RS Rating:")
    for r in sorted_results[:5]:
        print(f"  {r.symbol}: RS={r.rs_rating:.0f}, 12M Return={r.return_12m:+.1f}%, Rank={r.rank}")
    
    # Verify RS rating is 1-99
    for r in successful:
        assert 1 <= r.rs_rating <= 99, f"RS rating out of range: {r.rs_rating}"
    
    print("\n✓ RS Rating test passed")
    return True


def test_momentum():
    """Test Momentum Score Calculator."""
    print("\n" + "="*60)
    print("TEST: Momentum Score Calculator")
    print("="*60)
    
    calc = MomentumScoreCalculator()
    data = generate_test_data(20)
    today = date.today()
    
    results = calc.calculate_batch(data, today)
    
    successful = [r for r in results.values() if r.success]
    print(f"Successful calculations: {len(successful)}/{len(results)}")
    
    sorted_results = sorted(successful, key=lambda r: r.rank)
    
    print("\nTop 5 by Momentum Score:")
    for r in sorted_results[:5]:
        print(f"  {r.symbol}: Score={r.momentum_score:.1f}, Rank={r.rank}")
        print(f"    Returns: 1W={r.return_1w:+.1f}%, 1M={r.return_1m:+.1f}%, "
              f"3M={r.return_3m:+.1f}%, 6M={r.return_6m:+.1f}%, 12M={r.return_12m:+.1f}%")
    
    # Verify momentum score is 0-100
    for r in successful:
        assert 0 <= r.momentum_score <= 100, f"Momentum score out of range: {r.momentum_score}"
    
    print("\n✓ Momentum Score test passed")
    return True


def test_trend_template():
    """Test Trend Template Calculator."""
    print("\n" + "="*60)
    print("TEST: Trend Template Calculator")
    print("="*60)
    
    calc = TrendTemplateCalculator()
    data = generate_test_data(20)
    today = date.today()
    
    results = calc.calculate_batch(data, today)
    
    successful = [r for r in results.values() if r.success]
    print(f"Successful calculations: {len(successful)}/{len(results)}")
    
    sorted_results = sorted(successful, key=lambda r: r.score, reverse=True)
    
    print("\nTop 5 by Trend Template:")
    for r in sorted_results[:5]:
        passed = [c.name for c in r.conditions if c.passed]
        print(f"  {r.symbol}: Score={r.score}/8, Rank={r.rank}")
        print(f"    Price=${r.price:.2f}, 50SMA=${r.sma_50:.2f}, "
              f"150SMA=${r.sma_150:.2f}, 200SMA=${r.sma_200:.2f}")
        print(f"    Passed: {', '.join(passed[:4])}...")
    
    # Verify score is 0-8
    for r in successful:
        assert 0 <= r.score <= 8, f"Trend template score out of range: {r.score}"
    
    print("\n✓ Trend Template test passed")
    return True


def test_technical():
    """Test Technical Score Calculator."""
    print("\n" + "="*60)
    print("TEST: Technical Score Calculator")
    print("="*60)
    
    calc = TechnicalScoreCalculator()
    data = generate_test_data(20)
    today = date.today()
    
    results = calc.calculate_batch(data, today)
    
    successful = [r for r in results.values() if r.success]
    print(f"Successful calculations: {len(successful)}/{len(results)}")
    
    sorted_results = sorted(successful, key=lambda r: r.technical_score, reverse=True)
    
    print("\nTop 5 by Technical Score:")
    for r in sorted_results[:5]:
        print(f"  {r.symbol}: Score={r.technical_score:.1f}, Rank={r.rank}")
        print(f"    Components: 50SMA={r.score_vs_50sma:.1f}, 150SMA={r.score_vs_150sma:.1f}, "
              f"200SMA={r.score_vs_200sma:.1f}, Align={r.score_alignment:.1f}")
    
    # Verify score is 0-100
    for r in successful:
        assert 0 <= r.technical_score <= 100, f"Technical score out of range: {r.technical_score}"
    
    print("\n✓ Technical Score test passed")
    return True


def test_composite():
    """Test Composite Score Calculator."""
    print("\n" + "="*60)
    print("TEST: Composite Score Calculator")
    print("="*60)
    
    calc = CompositeScoreCalculator()
    
    # Test with known values
    test_data = {
        "BEST": {"rs_rating": 99, "momentum_score": 100, "trend_template_score": 8, "technical_score": 100},
        "GOOD": {"rs_rating": 80, "momentum_score": 75, "trend_template_score": 6, "technical_score": 80},
        "AVG": {"rs_rating": 50, "momentum_score": 50, "trend_template_score": 4, "technical_score": 50},
        "POOR": {"rs_rating": 20, "momentum_score": 25, "trend_template_score": 2, "technical_score": 20},
        "WORST": {"rs_rating": 1, "momentum_score": 0, "trend_template_score": 0, "technical_score": 0},
    }
    
    results = calc.calculate_batch(test_data)
    
    print("Results:")
    for symbol, r in sorted(results.items(), key=lambda x: x[1].composite_score, reverse=True):
        print(f"  {symbol}: Composite={r.composite_score:.1f}, Rank={r.rank}, Percentile={r.percentile:.0f}")
    
    # Verify ranking order
    assert results["BEST"].rank == 1, "BEST should be rank 1"
    assert results["WORST"].rank == 5, "WORST should be rank 5"
    
    # Verify score range
    for r in results.values():
        assert 0 <= r.composite_score <= 100, f"Composite score out of range: {r.composite_score}"
    
    print("\n✓ Composite Score test passed")
    return True


def test_integration():
    """Test full integration of all calculators."""
    print("\n" + "="*60)
    print("TEST: Full Integration")
    print("="*60)
    
    data = generate_test_data(30)
    today = date.today()
    
    # Run all calculators
    rs_calc = RSRatingCalculator()
    mom_calc = MomentumScoreCalculator()
    trend_calc = TrendTemplateCalculator()
    tech_calc = TechnicalScoreCalculator()
    comp_calc = CompositeScoreCalculator()
    
    print("Running calculators...")
    rs_results = rs_calc.calculate_batch(data, today)
    mom_results = mom_calc.calculate_batch(data, today)
    trend_results = trend_calc.calculate_batch(data, today)
    tech_results = tech_calc.calculate_batch(data, today)
    
    # Combine for composite
    scores_data = {}
    for symbol in data.keys():
        scores_data[symbol] = {
            "rs_rating": rs_results[symbol].rs_rating if rs_results[symbol].success else 0,
            "momentum_score": mom_results[symbol].momentum_score if mom_results[symbol].success else 0,
            "trend_template_score": trend_results[symbol].score if trend_results[symbol].success else 0,
            "technical_score": tech_results[symbol].technical_score if tech_results[symbol].success else 0,
        }
    
    comp_results = comp_calc.calculate_batch(scores_data)
    
    # Show top 10
    sorted_symbols = sorted(
        comp_results.keys(),
        key=lambda s: comp_results[s].composite_score,
        reverse=True
    )
    
    print("\nTop 10 Stocks (Integrated):")
    print("-" * 80)
    print(f"{'Symbol':10} | {'Composite':>9} | {'RS':>4} | {'Mom':>5} | {'Trend':>5} | {'Tech':>5} | {'Rank':>4}")
    print("-" * 80)
    
    for symbol in sorted_symbols[:10]:
        rs = rs_results[symbol]
        mom = mom_results[symbol]
        trend = trend_results[symbol]
        tech = tech_results[symbol]
        comp = comp_results[symbol]
        
        print(f"{symbol:10} | {comp.composite_score:9.2f} | {rs.rs_rating:4.0f} | "
              f"{mom.momentum_score:5.1f} | {trend.score:5d} | {tech.technical_score:5.1f} | {comp.rank:4d}")
    
    print("\n✓ Integration test passed")
    return True


def main():
    """Run all tests."""
    print("="*60)
    print("RANKING SYSTEM COMPONENT TESTS")
    print("="*60)
    
    tests = [
        ("RS Rating", test_rs_rating),
        ("Momentum Score", test_momentum),
        ("Trend Template", test_trend_template),
        ("Technical Score", test_technical),
        ("Composite Score", test_composite),
        ("Integration", test_integration),
    ]
    
    passed = 0
    failed = 0
    
    for name, test_func in tests:
        try:
            if test_func():
                passed += 1
        except Exception as e:
            print(f"\n✗ {name} test FAILED: {e}")
            import traceback
            traceback.print_exc()
            failed += 1
    
    print("\n" + "="*60)
    print(f"RESULTS: {passed} passed, {failed} failed")
    print("="*60)
    
    return failed == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
