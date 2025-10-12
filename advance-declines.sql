-- Run once
USE marketdata;

-- Stores per-day Advance/Decline counts so we don't recompute repeatedly
CREATE TABLE IF NOT EXISTS adv_decl_summary (
  trade_date     DATE         NOT NULL,
  series_scope   VARCHAR(64)  NOT NULL DEFAULT 'EQ,BE,BZ,BL',  -- which series were included
  advances       INT          NOT NULL,
  declines       INT          NOT NULL,
  unchanged      INT          NOT NULL,
  total          INT          NOT NULL,
  source_rows    INT          NULL,       -- number of rows seen in source table
  computed_at    TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
  note           VARCHAR(255) NULL,
  CONSTRAINT pk_adv_decl PRIMARY KEY (trade_date, series_scope),
  KEY idx_adv_decl_date (trade_date)
);
