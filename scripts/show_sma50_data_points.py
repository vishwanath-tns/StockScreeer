import reporting_adv_decl as rad
from sqlalchemy import text

engine = rad.engine()
with engine.connect() as conn:
    print('=== SMA 50 COUNT DATA POINTS ===')
    print('Date\t\tAbove 50\tBelow 50\tTotal\t\t% Above')
    print('=' * 70)
    
    # Get all data points ordered by date
    result = conn.execute(text('''
        SELECT trade_date, above_count, below_count, total_count, pct_above
        FROM sma50_counts 
        ORDER BY trade_date DESC
    ''')).fetchall()
    
    for row in result:
        trade_date, above_count, below_count, total_count, pct_above = row
        print(f'{trade_date}\t{above_count:,}\t\t{below_count:,}\t\t{total_count:,}\t\t{pct_above}%')
    
    print(f'\nTotal data points: {len(result)}')