-- Table to store trend analysis results
USE marketdata;

CREATE TABLE IF NOT EXISTS trend_analysis (
  id              BIGINT      AUTO_INCREMENT PRIMARY KEY,
  symbol          VARCHAR(64) NOT NULL,
  trade_date      DATE        NOT NULL,
  daily_trend     VARCHAR(10) NOT NULL,    -- 'UP' or 'DOWN'
  weekly_trend    VARCHAR(10) NOT NULL,    -- 'UP' or 'DOWN'  
  monthly_trend   VARCHAR(10) NOT NULL,    -- 'UP' or 'DOWN'
  trend_rating    TINYINT     NOT NULL,    -- -3 to +3
  created_at      TIMESTAMP   NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at      TIMESTAMP   NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  
  UNIQUE KEY uk_symbol_date (symbol, trade_date),
  KEY idx_trade_date (trade_date),
  KEY idx_trend_rating (trend_rating),
  KEY idx_daily_trend (daily_trend),
  KEY idx_weekly_trend (weekly_trend),
  KEY idx_monthly_trend (monthly_trend)
);