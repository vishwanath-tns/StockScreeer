-- DB + user (if not already created)
CREATE DATABASE IF NOT EXISTS marketdata
  CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

CREATE USER IF NOT EXISTS 'md_user'@'%' IDENTIFIED BY 'strong_password';
GRANT ALL PRIVILEGES ON marketdata.* TO 'md_user'@'%';
FLUSH PRIVILEGES;

USE marketdata;

-- Main bhav table (as tailored to your file)
CREATE TABLE IF NOT EXISTS nse_equity_bhavcopy_full (
  trade_date     DATE         NOT NULL,
  symbol         VARCHAR(64)  NOT NULL,
  series         VARCHAR(8)   NOT NULL,
  prev_close     DECIMAL(12,4)     NULL,
  open_price     DECIMAL(12,4)     NULL,
  high_price     DECIMAL(12,4)     NULL,
  low_price      DECIMAL(12,4)     NULL,
  last_price     DECIMAL(12,4)     NULL,
  close_price    DECIMAL(12,4)     NULL,
  avg_price      DECIMAL(12,4)     NULL,
  ttl_trd_qnty   BIGINT            NULL,
  turnover_lacs  DECIMAL(20,4)     NULL,
  no_of_trades   BIGINT            NULL,
  deliv_qty      BIGINT            NULL,
  deliv_per      DECIMAL(6,2)      NULL,
  CONSTRAINT pk_bhav_full PRIMARY KEY (trade_date, symbol, series),
  KEY idx_symbol_date (symbol, trade_date),
  KEY idx_series (series)
);

-- Imports tracking — prevents reloading the same date again
CREATE TABLE IF NOT EXISTS imports_log (
  trade_date   DATE        NOT NULL PRIMARY KEY, -- one bhav date per file
  file_name    VARCHAR(255) NOT NULL,
  file_checksum CHAR(32)    NOT NULL,            -- md5 of file contents
  rows_loaded  INT          NOT NULL,
  loaded_at    TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP
);
