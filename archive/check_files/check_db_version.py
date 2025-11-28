from sync_bhav_gui import engine
from sqlalchemy import text

conn = engine().connect()
result = conn.execute(text('SELECT VERSION()'))
version = result.scalar()
print(f"\nDatabase Version: {version}")

# Check database name
result = conn.execute(text('SELECT DATABASE()'))
db_name = result.scalar()
print(f"Current Database: {db_name}")

# Check connection details
print(f"\nConnection URL: {conn.engine.url}")

conn.close()
