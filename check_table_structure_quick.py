from sync_bhav_gui import engine
from sqlalchemy import text

conn = engine().connect()
result = conn.execute(text('DESCRIBE nse_yahoo_symbol_map'))
print('nse_yahoo_symbol_map Table Structure:')
print(f"{'Field':<30} {'Type':<30} {'Null':<10} {'Key':<10}")
print("-" * 90)
for row in result:
    print(f"{row[0]:<30} {row[1]:<30} {row[2]:<10} {row[3]:<10}")
conn.close()
