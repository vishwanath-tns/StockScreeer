# VCP (Volatility Contracting Patterns) Project - TODO List

## 📋 **Project Overview**
**Objective:** Implement Mark Minervini-style Volatility Contracting Pattern detection with backtesting validation
**Approach:** MVP with iterative development and testing at each phase
**Timeline:** 4-week MVP development with weekly iterations

## 📊 **Data Assessment Completed**
✅ **Database Analysis Done:**
- Duration: 22 months (Jan 2024 - Nov 2025), 463 trading days
- Coverage: 3,500+ symbols with good data density
- Schema: trade_date, symbol, OHLCV, prev_close, ttl_trd_qnty, turnover_lacs
- Major indices: RELIANCE, TCS, HDFCBANK, INFY, ICICIBANK, SBIN all have 460+ records

⚠️ **Key Issues Identified:**
- Non-split adjusted data (extreme gaps: 10x-40x price jumps detected)
- Need split detection and adjustment for accurate pattern analysis
- Current data sufficient for MVP, but consider importing more for better backtesting

## 🏗️ **Architecture Approved**
```
volatility_patterns/
├── __init__.py
├── data/
│   ├── __init__.py
│   ├── data_service.py          # Unified data interface (any timeframe)
│   ├── split_adjuster.py        # Split detection & adjustment
│   └── timeframe_converter.py   # Future: convert daily to other TFs
├── core/
│   ├── __init__.py
│   ├── technical_indicators.py  # ATR, BB, Volume indicators
│   ├── vcp_detector.py          # Main VCP detection algorithm
│   ├── pattern_criteria.py      # VCP validation rules
│   └── scoring_engine.py        # Pattern quality scoring
├── scanners/
│   ├── __init__.py
│   ├── historical_scanner.py    # Scan past data for VCPs
│   └── pattern_validator.py     # Validate detected patterns
├── analysis/
│   ├── __init__.py
│   └── performance_tracker.py   # Track post-pattern performance
└── tests/
    ├── __init__.py
    ├── test_data_service.py      # Unit tests for iteration 1
    └── test_vcp_detection.py     # VCP detection tests
```

## 🎯 **MVP Development Plan**

### **ITERATION 1A: Foundation & Data Service (Week 1)**

#### **TODO - High Priority:**

1. **Create Project Structure**
   - [ ] Create `volatility_patterns/` directory
   - [ ] Set up `__init__.py` files for all modules
   - [ ] Create basic module structure as per architecture

2. **Data Service Implementation**
   - [ ] Create `data/data_service.py` - Unified data interface
     - [ ] Function: `get_ohlcv_data(symbol, start_date, end_date, timeframe='1D')`
     - [ ] Function: `get_multiple_symbols_data(symbols_list, start_date, end_date)`
     - [ ] Function: `validate_data_integrity(data_df)`
     - [ ] Make timeframe-agnostic for future lower timeframes
   
3. **Split Detection & Adjustment**
   - [ ] Create `data/split_adjuster.py`
     - [ ] Function: `detect_potential_splits(data_df, gap_threshold=0.15)`
     - [ ] Function: `adjust_for_splits(data_df, split_dates_dict)`
     - [ ] Function: `flag_split_affected_periods(data_df)`
   
4. **Technical Indicators**
   - [ ] Create `core/technical_indicators.py`
     - [ ] Function: `calculate_atr(data_df, period=14)`
     - [ ] Function: `calculate_bollinger_bands(data_df, period=20, std_dev=2)`
     - [ ] Function: `calculate_volume_ma(data_df, period=50)`
     - [ ] Function: `calculate_price_range_compression(data_df, period=20)`

5. **Unit Testing**
   - [ ] Create `tests/test_data_service.py`
     - [ ] Test data fetching for RELIANCE (6 months, <2 seconds)
     - [ ] Test split detection accuracy (manual verification on 10 known splits)
     - [ ] Test technical indicators vs external benchmarks
   - [ ] Validate all functions with known good data

#### **Success Criteria for 1A:**
- [ ] Pull 6 months of data for RELIANCE in <2 seconds
- [ ] Correctly identify 90%+ of obvious split events
- [ ] Calculate ATR(14) and BB(20,2) matching external tools (TradingView, etc.)
- [ ] Pass all unit tests

### **ITERATION 1B: Basic VCP Detection (Week 2)**

#### **TODO - VCP Core Logic:**

1. **VCP Detection Algorithm**
   - [ ] Create `core/vcp_detector.py`
     - [ ] Function: `detect_vcp_pattern(data_df, symbol)`
     - [ ] Function: `validate_prior_uptrend(data_df, min_gain_52w=0.30)`
     - [ ] Function: `check_volatility_contraction(data_df, atr_periods=14)`
     - [ ] Function: `analyze_volume_patterns(data_df, volume_ma_period=50)`

2. **Pattern Criteria Definition**
   - [ ] Create `core/pattern_criteria.py`
     - [ ] Class: `VCPCriteria` with configurable parameters
     - [ ] Prior uptrend: 30%+ gain in 52 weeks
     - [ ] Volatility contraction: ATR declining over 4-8 weeks
     - [ ] Volume dry-up: Volume below 50-day MA during contractions
     - [ ] Base duration: 4-12 weeks of consolidation
     - [ ] Progressive tightening: Daily ranges getting smaller

3. **Quality Scoring System**
   - [ ] Create `core/scoring_engine.py`
     - [ ] Function: `calculate_vcp_score(pattern_data, criteria)`
     - [ ] Score components: trend strength, contraction quality, volume behavior
     - [ ] Output: 0-100 VCP quality rating

4. **Pattern Validation Testing**
   - [ ] Create `tests/test_vcp_detection.py`
     - [ ] Test on 10 manually identified VCP examples
     - [ ] Test on 10 obvious non-VCP patterns
     - [ ] Validate scoring accuracy vs visual inspection

#### **Success Criteria for 1B:**
- [ ] Detect 5-10 VCP patterns per month in NIFTY 50
- [ ] <20% false positive rate vs manual visual inspection
- [ ] Pattern scoring correlates with subsequent performance

### **ITERATION 1C: Historical Scanner & Backtesting (Week 3)**

#### **TODO - Backtesting Framework:**

1. **Historical Pattern Scanner**
   - [ ] Create `scanners/historical_scanner.py`
     - [ ] Function: `scan_historical_vcps(symbols_list, start_date, end_date)`
     - [ ] Function: `batch_process_symbols(symbols_batch, scan_params)`
     - [ ] Function: `export_detected_patterns(patterns_list, output_format='csv')`

2. **Performance Tracking**
   - [ ] Create `analysis/performance_tracker.py`
     - [ ] Function: `track_post_pattern_performance(pattern_date, symbol, periods=[30,60,90])`
     - [ ] Function: `calculate_win_rates(pattern_results)`
     - [ ] Function: `compare_vs_benchmark(vcp_results, benchmark_results)`
     - [ ] Function: `generate_performance_report(all_results)`

3. **Backtesting Validation**
   - [ ] Scan 2024-2025 data for VCP patterns on NIFTY 50
   - [ ] Track subsequent 30/60/90-day performance
   - [ ] Calculate win rates, average gains/losses, max drawdowns
   - [ ] Compare against random entry and buy-and-hold strategies

#### **Success Criteria for 1C:**
- [ ] 60%+ win rate on detected VCP patterns (10%+ gains within 3 months)
- [ ] Max 5% average loss on failed patterns
- [ ] Beat buy-and-hold by 5%+ annually (risk-adjusted)

### **ITERATION 1D: Parameter Optimization & Refinement (Week 4)**

#### **TODO - Optimization:**

1. **Parameter Testing**
   - [ ] Test different ATR periods (5, 10, 14, 21 days)
   - [ ] Vary BB squeeze thresholds (10%, 15%, 20% percentiles)
   - [ ] Adjust volume contraction requirements
   - [ ] Optimize pattern duration windows (4-8 vs 6-12 weeks)

2. **Market Condition Analysis**
   - [ ] Analyze VCP performance in bull vs bear markets
   - [ ] Test sector rotation impacts on pattern success
   - [ ] Evaluate volatility regime effects

3. **Final Validation**
   - [ ] Out-of-sample testing on 2025 data
   - [ ] Cross-validation with different time periods
   - [ ] Sensitivity analysis on key parameters

## 🔬 **Key Research Questions to Answer**

### **Iteration 1A Questions:**
- [ ] Does split adjustment significantly improve pattern detection accuracy?
- [ ] Are our technical indicators accurate vs external benchmarks (±1% tolerance)?
- [ ] What's the optimal data fetching performance for real-time scanning?

### **Iteration 1B Questions:**
- [ ] How many VCP patterns do we detect per month in NIFTY 100?
- [ ] What's the false positive rate vs manual visual inspection?
- [ ] Which VCP criteria are most/least important for subsequent success?

### **Iteration 1C Questions:**
- [ ] What's the actual win rate of detected VCP patterns?
- [ ] How does VCP performance vary by market conditions (bull/bear/sideways)?
- [ ] Should we adjust detection criteria based on backtesting results?

### **Iteration 1D Questions:**
- [ ] Which parameter combinations give the best risk-adjusted returns?
- [ ] How sensitive is the strategy to parameter changes?
- [ ] What's the optimal balance between pattern frequency and quality?

## ⚙️ **Configuration Decisions Needed**

### **Before Starting Implementation:**
- [ ] **Test Universe:** NIFTY 50, NIFTY 100, or broader set? (Recommend: Start with NIFTY 50)
- [ ] **Split Handling:** Full adjustment or flag-and-skip approach? (Recommend: Flag and adjust)
- [ ] **Performance Benchmark:** Buy-and-hold, momentum strategies, or market index? (Recommend: All three)
- [ ] **Detection Threshold:** Conservative (fewer, higher quality) vs aggressive (more patterns)? (Recommend: Start conservative)

### **Database Considerations:**
- [ ] Import more historical data? Current 22 months vs 3+ years for better backtesting
- [ ] Create separate VCP results table for pattern storage
- [ ] Set up performance tracking tables for backtesting results

## 📝 **Implementation Notes**

### **Design Principles:**
1. **Timeframe Agnostic:** All functions should work with any timeframe (1D, 1H, 15m, etc.)
2. **Data Source Agnostic:** Abstract data layer for easy switching between NSE/other sources
3. **Modular Architecture:** Each component independently testable and replaceable
4. **Split Awareness:** Handle corporate actions properly throughout the pipeline
5. **Performance First:** Optimize for real-time scanning of large universes

### **Code Quality Requirements:**
- [ ] Comprehensive unit tests (>80% coverage)
- [ ] Detailed docstrings with examples
- [ ] Type hints for all function parameters
- [ ] Logging for debugging and monitoring
- [ ] Configuration files for easy parameter adjustment

## 🚀 **Next Steps When Ready to Start**

1. **Read this TODO list completely**
2. **Set up development environment**
3. **Create the basic project structure**
4. **Start with Iteration 1A - Data Service layer**
5. **Test each component thoroughly before moving to next iteration**

## 📞 **Questions to Clarify Before Implementation**

- [ ] Preferred test universe size for initial development?
- [ ] Should we implement paper trading simulation alongside backtesting?
- [ ] Any specific external benchmarks for technical indicator validation?
- [ ] Preference for configuration management (JSON, YAML, database)?

---

**Project Created:** November 16, 2025
**Status:** Ready for Implementation
**Next Action:** Start with Iteration 1A - Foundation & Data Service

**Remember:** This is an MVP with iterative testing. Each iteration should be fully validated before proceeding to the next phase.