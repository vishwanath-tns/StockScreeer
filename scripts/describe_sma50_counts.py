import reporting_adv_decl as rad
from sqlalchemy import text

engine = rad.engine()
conn = engine.connect()
try:
    cols = conn.execute(text('SHOW COLUMNS FROM sma50_counts')).fetchall()
    print('sma50_counts columns:')
    for c in cols:
        print('  ', c)
except Exception as e:
    print('Error describing sma50_counts:', e)
finally:
    conn.close()
