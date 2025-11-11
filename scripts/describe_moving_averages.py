import reporting_adv_decl as rad
from sqlalchemy import text

engine = rad.engine()
conn = engine.connect()
try:
    cols = conn.execute(text('SHOW COLUMNS FROM moving_averages')).fetchall()
    print('moving_averages columns:')
    for c in cols:
        print('  ', c)
except Exception as e:
    print('Error describing moving_averages:', e)
finally:
    conn.close()
