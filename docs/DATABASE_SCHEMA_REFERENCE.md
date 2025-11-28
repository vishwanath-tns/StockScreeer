# 📊 StockScreener Database Schema Reference

> **Database:** `marketdata` | **Engine:** MySQL/InnoDB | **Charset:** utf8mb4

---

## 📋 Table of Contents

1. [Core Market Data Tables](#1-core-market-data-tables)
2. [NSE BHAV Copy Tables](#2-nse-bhav-copy-tables)
3. [Advance-Decline Analysis Tables](#3-advance-decline-analysis-tables)
4. [Intraday & Real-Time Tables](#4-intraday--real-time-tables)
5. [Momentum Analysis Tables](#5-momentum-analysis-tables)
6. [Trend Analysis Tables](#6-trend-analysis-tables)
7. [Block & Bulk Deals Tables](#7-block--bulk-deals-tables)
8. [Vedic Astrology Tables](#8-vedic-astrology-tables)
9. [Symbol Mapping Tables](#9-symbol-mapping-tables)
10. [Entity Relationship Diagram](#10-entity-relationship-diagram)

---

## 1. Core Market Data Tables

### 📈 `yfinance_daily_quotes`
**Purpose:** Primary table storing daily OHLCV (Open, High, Low, Close, Volume) data from Yahoo Finance

| Column | Type | Description |
|--------|------|-------------|
| `id` | BIGINT PK | Auto-increment primary key |
| `symbol` | VARCHAR(20) | Stock/index symbol (e.g., RELIANCE.NS, ^NSEI) |
| `date` | DATE | Trading date |
| `open` | DECIMAL(15,4) | Opening price |
| `high` | DECIMAL(15,4) | Day's highest price |
| `low` | DECIMAL(15,4) | Day's lowest price |
| `close` | DECIMAL(15,4) | Closing price |
| `volume` | BIGINT | Total traded volume |
| `adj_close` | DECIMAL(15,4) | Adjusted close (for splits/dividends) |
| `timeframe` | VARCHAR(10) | Data timeframe ('Daily' default) |
| `source` | VARCHAR(20) | Data source ('Yahoo Finance') |
| `created_at` | TIMESTAMP | Record creation time |
| `updated_at` | TIMESTAMP | Last update time |

**Key Indexes:**
- `uk_symbol_date_timeframe` - Unique: Prevents duplicate entries
- `idx_symbol_date` - Fast symbol+date lookups
- `idx_date_desc` - Date-based queries

**Current Stats:** ~881,552 records, 1,049 symbols

---

### 📊 `yfinance_symbols`
**Purpose:** Symbol master table with NSE to Yahoo Finance mapping

| Column | Type | Description |
|--------|------|-------------|
| `id` | INT PK | Auto-increment primary key |
| `symbol` | VARCHAR(20) | NSE symbol (e.g., RELIANCE) |
| `yahoo_symbol` | VARCHAR(30) | Yahoo Finance symbol (e.g., RELIANCE.NS) |
| `name` | VARCHAR(100) | Company/index name |
| `market` | VARCHAR(20) | Market ('NSE', 'BSE') |
| `currency` | VARCHAR(5) | Currency ('INR') |
| `symbol_type` | ENUM | Type: 'INDEX', 'STOCK', 'ETF' |
| `is_active` | BOOLEAN | Active status flag |
| `created_at` | TIMESTAMP | Creation timestamp |

**Default Entries:**
- NIFTY → ^NSEI (NIFTY 50)
- BANKNIFTY → ^NSEBANK (Bank Nifty)
- SENSEX → ^BSESN (BSE Sensex)

---

### 📝 `yfinance_download_log`
**Purpose:** Track download activities and status

| Column | Type | Description |
|--------|------|-------------|
| `id` | BIGINT PK | Auto-increment primary key |
| `symbol` | VARCHAR(20) | Downloaded symbol |
| `start_date` | DATE | Download range start |
| `end_date` | DATE | Download range end |
| `timeframe` | VARCHAR(10) | Data timeframe |
| `records_downloaded` | INT | Number of new records |
| `records_updated` | INT | Number of updated records |
| `status` | ENUM | 'STARTED', 'COMPLETED', 'FAILED', 'PARTIAL' |
| `error_message` | TEXT | Error details if failed |
| `download_duration_ms` | INT | Time taken in milliseconds |
| `completed_at` | TIMESTAMP | Completion time |

---

## 2. NSE BHAV Copy Tables

### 📄 `nse_equity_bhavcopy_full`
**Purpose:** NSE official daily BHAV copy data (complete market data from NSE)

| Column | Type | Description |
|--------|------|-------------|
| `trade_date` | DATE PK | Trading date |
| `symbol` | VARCHAR(64) PK | Stock symbol |
| `series` | VARCHAR(8) PK | Trading series (EQ, BE, etc.) |
| `prev_close` | DECIMAL(12,4) | Previous day close |
| `open_price` | DECIMAL(12,4) | Opening price |
| `high_price` | DECIMAL(12,4) | Day's high |
| `low_price` | DECIMAL(12,4) | Day's low |
| `last_price` | DECIMAL(12,4) | Last traded price |
| `close_price` | DECIMAL(12,4) | Official closing price |
| `avg_price` | DECIMAL(12,4) | Volume weighted average |
| `ttl_trd_qnty` | BIGINT | Total traded quantity |
| `turnover_lacs` | DECIMAL(20,4) | Turnover in Lakhs |
| `no_of_trades` | BIGINT | Number of trades |
| `deliv_qty` | BIGINT | Delivery quantity |
| `deliv_per` | DECIMAL(6,2) | Delivery percentage |

**Primary Key:** `(trade_date, symbol, series)` - Composite key

---

### 📋 `imports_log`
**Purpose:** Track BHAV file imports to prevent duplicates

| Column | Type | Description |
|--------|------|-------------|
| `trade_date` | DATE PK | BHAV file date (one per file) |
| `file_name` | VARCHAR(255) | Original filename |
| `file_checksum` | CHAR(32) | MD5 hash of file |
| `rows_loaded` | INT | Number of rows imported |
| `loaded_at` | TIMESTAMP | Import timestamp |

---

## 3. Advance-Decline Analysis Tables

### 📊 `nifty500_advance_decline`
**Purpose:** Daily advance/decline/unchanged counts for Nifty 500 stocks

| Column | Type | Description |
|--------|------|-------------|
| `id` | INT PK | Auto-increment primary key |
| `trade_date` | DATE UNIQUE | Trading date |
| `advances` | INT | Count of advancing stocks |
| `declines` | INT | Count of declining stocks |
| `unchanged` | INT | Count of unchanged stocks |
| `total_stocks` | INT | Total stocks analyzed |
| `advance_pct` | DECIMAL(5,2) | Advance percentage |
| `decline_pct` | DECIMAL(5,2) | Decline percentage |
| `unchanged_pct` | DECIMAL(5,2) | Unchanged percentage |
| `advance_decline_ratio` | DECIMAL(10,4) | Advances ÷ Declines |
| `advance_decline_diff` | INT | Advances - Declines |
| `source` | VARCHAR(50) | Data source |
| `computed_at` | TIMESTAMP | Calculation timestamp |

**Market Sentiment Thresholds:**
- ≥70% advances = Very Bullish
- ≥55% advances = Bullish
- 45-55% = Neutral
- <45% = Bearish
- <30% = Very Bearish

---

## 4. Intraday & Real-Time Tables

### ⚡ `intraday_1min_candles`
**Purpose:** 1-minute OHLCV candle data for intraday analysis

| Column | Type | Description |
|--------|------|-------------|
| `id` | BIGINT PK | Auto-increment primary key |
| `poll_time` | DATETIME | When data was fetched |
| `trade_date` | DATE | Trading date |
| `symbol` | VARCHAR(50) | Stock symbol |
| `candle_timestamp` | DATETIME | Candle time (1-min interval) |
| `open_price` | DECIMAL(12,2) | Candle open |
| `high_price` | DECIMAL(12,2) | Candle high |
| `low_price` | DECIMAL(12,2) | Candle low |
| `close_price` | DECIMAL(12,2) | Candle close (LTP) |
| `volume` | BIGINT | Volume in this minute |
| `prev_close` | DECIMAL(12,2) | Previous day close |
| `change_amt` | DECIMAL(10,2) | Price change (computed) |
| `change_pct` | DECIMAL(8,2) | % change (computed) |
| `status` | ENUM | 'ADVANCE', 'DECLINE', 'UNCHANGED' (computed) |

**Unique Constraint:** `(poll_time, symbol, candle_timestamp)`

---

### 🔴 `realtime_market_data`
**Purpose:** Real-time streaming data from Yahoo Finance

| Column | Type | Description |
|--------|------|-------------|
| `id` | BIGINT PK | Auto-increment primary key |
| `symbol` | VARCHAR(50) | Stock/futures symbol |
| `series` | VARCHAR(10) | Market series |
| `trade_date` | DATE | Trading date |
| `prev_close` | DECIMAL(20,4) | Previous close |
| `open_price` | DECIMAL(20,4) | Open price |
| `high_price` | DECIMAL(20,4) | High price |
| `low_price` | DECIMAL(20,4) | Low price |
| `close_price` | DECIMAL(20,4) | Current/close price |
| `volume` | BIGINT | Volume |
| `timestamp` | BIGINT | Unix epoch timestamp |
| `data_source` | VARCHAR(50) | Source ('yahoo_finance') |

---

### 📈 `realtime_market_ticks`
**Purpose:** High-frequency tick data

| Column | Type | Description |
|--------|------|-------------|
| `id` | BIGINT PK | Auto-increment primary key |
| `symbol` | VARCHAR(50) | Symbol |
| `price` | DECIMAL(20,4) | Tick price |
| `volume` | BIGINT | Tick volume |
| `timestamp` | BIGINT | Unix epoch timestamp |
| `data_source` | VARCHAR(50) | Source |

---

## 5. Momentum Analysis Tables

### 🚀 `momentum_analysis`
**Purpose:** Multi-timeframe momentum calculations

| Column | Type | Description |
|--------|------|-------------|
| `id` | BIGINT PK | Auto-increment primary key |
| `symbol` | VARCHAR(50) | Stock symbol |
| `series` | VARCHAR(10) | Series (EQ) |
| `duration_type` | ENUM | '1W', '1M', '3M', '6M', '9M', '12M' |
| `duration_days` | INT | Actual trading days |
| `start_date` | DATE | Period start |
| `end_date` | DATE | Period end |
| `start_price` | DECIMAL(15,4) | Starting price |
| `end_price` | DECIMAL(15,4) | Ending price |
| `high_price` | DECIMAL(15,4) | Period high |
| `low_price` | DECIMAL(15,4) | Period low |
| `absolute_change` | DECIMAL(15,4) | Price change |
| `percentage_change` | DECIMAL(10,4) | % change |
| `avg_volume` | BIGINT | Average volume |
| `volume_surge_factor` | DECIMAL(8,4) | Volume vs average |
| `price_volatility` | DECIMAL(8,4) | Volatility measure |
| `percentile_rank` | DECIMAL(5,2) | Percentile rank |
| `sector_rank` | INT | Rank within sector |
| `overall_rank` | INT | Overall rank |

**Duration Mapping:**
- 1W = 7 days
- 1M = 30 days
- 3M = 90 days
- 6M = 180 days
- 9M = 270 days
- 12M = 365 days

---

### 📊 `momentum_rankings`
**Purpose:** Daily momentum leaderboards

| Column | Type | Description |
|--------|------|-------------|
| `id` | BIGINT PK | Auto-increment primary key |
| `calculation_date` | DATE | Calculation date |
| `duration_type` | ENUM | Duration period |
| `top_gainers` | JSON | Top gaining stocks |
| `top_losers` | JSON | Top losing stocks |
| `avg_gain` | DECIMAL(10,4) | Market average gain |
| `median_gain` | DECIMAL(10,4) | Median gain |
| `std_deviation` | DECIMAL(10,4) | Standard deviation |
| `total_stocks` | INT | Total analyzed |
| `positive_stocks` | INT | Gainers count |
| `negative_stocks` | INT | Losers count |
| `best_sector` | VARCHAR(100) | Top sector |
| `worst_sector` | VARCHAR(100) | Bottom sector |

---

## 6. Trend Analysis Tables

### 📈 `trend_analysis`
**Purpose:** Multi-timeframe trend direction analysis

| Column | Type | Description |
|--------|------|-------------|
| `id` | BIGINT PK | Auto-increment primary key |
| `symbol` | VARCHAR(64) | Stock symbol |
| `trade_date` | DATE | Analysis date |
| `daily_trend` | VARCHAR(10) | 'UP' or 'DOWN' |
| `weekly_trend` | VARCHAR(10) | 'UP' or 'DOWN' |
| `monthly_trend` | VARCHAR(10) | 'UP' or 'DOWN' |
| `trend_rating` | TINYINT | Rating from -3 to +3 |

**Trend Rating Scale:**
- +3 = Strong Bullish (All UP)
- +2 = Bullish (2 UP, 1 DOWN)
- +1 = Mildly Bullish
- 0 = Neutral
- -1 = Mildly Bearish
- -2 = Bearish (2 DOWN, 1 UP)
- -3 = Strong Bearish (All DOWN)

---

## 7. Block & Bulk Deals Tables

### 💰 `nse_block_deals`
**Purpose:** NSE Block deals (≥5 lakh shares per transaction)

| Column | Type | Description |
|--------|------|-------------|
| `id` | INT PK | Auto-increment primary key |
| `trade_date` | DATE | Deal date |
| `symbol` | VARCHAR(50) | Stock symbol |
| `security_name` | VARCHAR(255) | Full security name |
| `client_name` | VARCHAR(255) | Buyer/seller name |
| `deal_type` | VARCHAR(10) | 'BUY' or 'SELL' |
| `quantity` | BIGINT | Shares traded |
| `trade_price` | DECIMAL(15,4) | Trade price |
| `remarks` | VARCHAR(500) | Additional info |

---

### 📦 `nse_bulk_deals`
**Purpose:** NSE Bulk deals (≥0.5% of equity shares)

| Column | Type | Description |
|--------|------|-------------|
| `id` | INT PK | Auto-increment primary key |
| `trade_date` | DATE | Deal date |
| `symbol` | VARCHAR(50) | Stock symbol |
| `security_name` | VARCHAR(255) | Full security name |
| `client_name` | VARCHAR(255) | Buyer/seller name |
| `deal_type` | VARCHAR(10) | 'BUY' or 'SELL' |
| `quantity` | BIGINT | Shares traded |
| `trade_price` | DECIMAL(15,4) | Trade price |
| `remarks` | VARCHAR(500) | Additional info |

---

## 8. Vedic Astrology Tables

### 🌙 `planetary_positions`
**Purpose:** Minute-by-minute planetary position data for market astrology analysis

| Column | Type | Description |
|--------|------|-------------|
| `id` | BIGINT PK | Auto-increment primary key |
| `timestamp` | DATETIME UNIQUE | Exact timestamp |
| `year` | INT | Year |
| `month` | INT | Month |
| `day` | INT | Day |
| `hour` | INT | Hour |
| `minute` | INT | Minute |

**For each planet (Sun, Moon, Mercury, Venus, Mars, Jupiter, Saturn, Rahu, Ketu):**
| Column Pattern | Type | Description |
|----------------|------|-------------|
| `{planet}_longitude` | DECIMAL(10,6) | Longitude 0-360° |
| `{planet}_sign` | VARCHAR(20) | Zodiac sign name |
| `{planet}_degree` | DECIMAL(8,6) | Degrees within sign 0-30° |

**Zodiac Signs (30° each):**
- 0°-30°: Aries (Mesha)
- 30°-60°: Taurus (Vrishabha)
- 60°-90°: Gemini (Mithuna)
- 90°-120°: Cancer (Karka)
- 120°-150°: Leo (Simha)
- 150°-180°: Virgo (Kanya)
- 180°-210°: Libra (Tula)
- 210°-240°: Scorpio (Vrishchika)
- 240°-270°: Sagittarius (Dhanu)
- 270°-300°: Capricorn (Makara)
- 300°-330°: Aquarius (Kumbha)
- 330°-360°: Pisces (Meena)

**Data Stats:** ~1,575,362 records (3 years of minute-level data)
**Accuracy:** <0.02° verified against DrikPanchang

---

## 9. Symbol Mapping Tables

### 🔗 `nse_yahoo_symbol_map`
**Purpose:** Map NSE symbols to Yahoo Finance format

| Column | Type | Description |
|--------|------|-------------|
| `id` | INT PK | Auto-increment |
| `nse_symbol` | VARCHAR(50) UNIQUE | NSE symbol |
| `yahoo_symbol` | VARCHAR(50) | Yahoo symbol |
| `company_name` | VARCHAR(255) | Company name |
| `is_verified` | BOOLEAN | Verification status |
| `is_active` | BOOLEAN | Active status |

---

### ✅ `symbol_mapping_validation_log`
**Purpose:** Track symbol validation results

| Column | Type | Description |
|--------|------|-------------|
| `id` | INT PK | Auto-increment |
| `nse_symbol` | VARCHAR(50) | NSE symbol |
| `yahoo_symbol` | VARCHAR(50) | Yahoo symbol |
| `validation_status` | VARCHAR(20) | 'VALID', 'INVALID', 'ERROR' |
| `price_fetched` | DECIMAL(15,4) | Test price fetched |
| `error_message` | TEXT | Error details |

---

## 10. Entity Relationship Diagram

```
┌──────────────────────────────────────────────────────────────────┐
│                     CORE MARKET DATA                              │
├──────────────────────────────────────────────────────────────────┤
│  yfinance_symbols  ◄──────┐                                      │
│  (symbol master)          │                                      │
│                           │                                      │
│  yfinance_daily_quotes ───┘  (881K+ records)                     │
│  (daily OHLCV data)                                              │
│          │                                                        │
│          ▼                                                        │
│  nifty500_advance_decline                                         │
│  (breadth analysis)                                               │
└──────────────────────────────────────────────────────────────────┘
                    │
                    ▼
┌──────────────────────────────────────────────────────────────────┐
│                     NSE OFFICIAL DATA                             │
├──────────────────────────────────────────────────────────────────┤
│  nse_equity_bhavcopy_full ◄──── imports_log                      │
│  (NSE BHAV copy data)           (import tracking)                │
│          │                                                        │
│          ├────► nse_block_deals                                   │
│          │      (≥5 lakh shares)                                  │
│          │                                                        │
│          └────► nse_bulk_deals                                    │
│                 (≥0.5% equity)                                    │
└──────────────────────────────────────────────────────────────────┘
                    │
                    ▼
┌──────────────────────────────────────────────────────────────────┐
│                     ANALYSIS TABLES                               │
├──────────────────────────────────────────────────────────────────┤
│  trend_analysis          momentum_analysis                        │
│  (multi-TF trends)       (multi-period momentum)                 │
│          │                       │                                │
│          └───────┬───────────────┘                                │
│                  ▼                                                │
│          momentum_rankings                                        │
│          (daily leaderboards)                                     │
└──────────────────────────────────────────────────────────────────┘
                    │
                    ▼
┌──────────────────────────────────────────────────────────────────┐
│                     INTRADAY DATA                                 │
├──────────────────────────────────────────────────────────────────┤
│  intraday_1min_candles                                           │
│  (1-minute OHLCV)                                                │
│          │                                                        │
│          ├────► realtime_market_data                              │
│          │      (live quotes)                                     │
│          │                                                        │
│          └────► realtime_market_ticks                             │
│                 (tick-by-tick)                                    │
└──────────────────────────────────────────────────────────────────┘
                    │
                    ▼
┌──────────────────────────────────────────────────────────────────┐
│                     ASTROLOGY DATA                                │
├──────────────────────────────────────────────────────────────────┤
│  planetary_positions                                              │
│  (minute-level planetary data)                                    │
│  9 planets × 3 fields = 27 columns                               │
│  ~1.5M records (2023-2025)                                       │
└──────────────────────────────────────────────────────────────────┘
```

---

## 📌 Quick Reference

### Common Queries

```sql
-- Get latest stock prices
SELECT symbol, date, close, volume 
FROM yfinance_daily_quotes 
WHERE date = (SELECT MAX(date) FROM yfinance_daily_quotes)
ORDER BY volume DESC;

-- Check advance-decline for today
SELECT * FROM nifty500_advance_decline 
ORDER BY trade_date DESC LIMIT 7;

-- Get trending stocks
SELECT * FROM trend_analysis 
WHERE trend_rating = 3 
ORDER BY trade_date DESC;

-- Check recent block deals
SELECT * FROM nse_block_deals 
WHERE trade_date >= DATE_SUB(CURDATE(), INTERVAL 7 DAY)
ORDER BY quantity * trade_price DESC;
```

### Table Sizes (Approximate)
| Table | Records | Description |
|-------|---------|-------------|
| yfinance_daily_quotes | 881,552 | Main price data |
| planetary_positions | 1,575,362 | Astrology data |
| nse_equity_bhavcopy_full | Variable | NSE BHAV data |
| intraday_1min_candles | Variable | Intraday candles |

---

*Last Updated: November 28, 2025*
*Database: MySQL 8.0 / MariaDB*
