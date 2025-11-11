import reporting_adv_decl as rad
from sqlalchemy import text

engine = rad.engine()
with engine.begin() as conn:
    print('1) Ensure sma50_counts table exists...')
    conn.execute(text('''
    CREATE TABLE IF NOT EXISTS sma50_counts (
        trade_date DATE PRIMARY KEY,
        above_count INT,
        below_count INT,
        na_count INT,
        total_count INT,
        pct_above DECIMAL(5,1),
        last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
    ) ENGINE=InnoDB;
    '''))
    print('  OK')

    print('\n2) Aggregating counts from moving_averages and upserting...')
    upsert_sql = '''
    INSERT INTO sma50_counts (trade_date, above_count, below_count, na_count, total_count, pct_above)
    SELECT
        m.trade_date,
        SUM(CASE WHEN m.sma_50 IS NOT NULL AND b.close_price IS NOT NULL AND b.close_price > m.sma_50 THEN 1 ELSE 0 END) AS above_count,
        SUM(CASE WHEN m.sma_50 IS NOT NULL AND b.close_price IS NOT NULL AND b.close_price < m.sma_50 THEN 1 ELSE 0 END) AS below_count,
        SUM(CASE WHEN m.sma_50 IS NULL OR b.close_price IS NULL THEN 1 ELSE 0 END) AS na_count,
        SUM(CASE WHEN m.sma_50 IS NOT NULL AND b.close_price IS NOT NULL THEN 1 ELSE 0 END) AS total_count,
        ROUND(100 * SUM(CASE WHEN m.sma_50 IS NOT NULL AND b.close_price IS NOT NULL AND b.close_price > m.sma_50 THEN 1 ELSE 0 END) / NULLIF(SUM(CASE WHEN m.sma_50 IS NOT NULL AND b.close_price IS NOT NULL THEN 1 ELSE 0 END),0), 1) AS pct_above
    FROM moving_averages m
        LEFT JOIN nse_equity_bhavcopy_full b
            ON m.trade_date = b.trade_date AND m.symbol COLLATE utf8mb4_unicode_ci = b.symbol COLLATE utf8mb4_unicode_ci
    GROUP BY m.trade_date
    ON DUPLICATE KEY UPDATE
        above_count = VALUES(above_count),
        below_count = VALUES(below_count),
        na_count = VALUES(na_count),
        total_count = VALUES(total_count),
        pct_above = VALUES(pct_above);
    '''
    conn.execute(text(upsert_sql))
    print('  Aggregation & upsert executed')

    print('\n3) Verification: number of distinct trade_dates in sma50_counts and sample rows')
    total_dates = conn.execute(text('SELECT COUNT(DISTINCT trade_date) FROM sma50_counts')).fetchone()[0]
    min_max = conn.execute(text('SELECT MIN(trade_date), MAX(trade_date) FROM sma50_counts')).fetchone()
    print(f'  sma50_counts dates: {total_dates}  range: {min_max[0]} to {min_max[1]}')

    # Show how many of the BHAV trading dates we covered
    bhav_dates = conn.execute(text('SELECT COUNT(DISTINCT trade_date) FROM nse_equity_bhavcopy_full')).fetchone()[0]
    print(f'  bhav trading dates: {bhav_dates}')
    print(f'  coverage: {total_dates/bhav_dates*100:.1f}%')

    print('\n  Recent sma50_counts rows:')
    rows = conn.execute(text('SELECT trade_date, above_count, below_count, total_count, pct_above FROM sma50_counts ORDER BY trade_date DESC LIMIT 8')).fetchall()
    for r in rows:
        print(f'   {r[0]} | above={r[1]} below={r[2]} total={r[3]} pct_above={r[4]}%')

print('\nDone')
