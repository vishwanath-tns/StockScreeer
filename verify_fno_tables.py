#!/usr/bin/env python
"""Quick verification script for FNO tables."""

from dhan_trading.db_setup import get_engine
from sqlalchemy import inspect, text

engine = get_engine('dhan_trading')
inspector = inspect(engine)

print("\n" + "="*70)
print("FNO DATABASE TABLES VERIFICATION")
print("="*70)

tables = ['dhan_fno_quotes', 'dhan_options_quotes', 'dhan_fno_metadata', 'dhan_fno_feed_log']

for table_name in tables:
    cols = inspector.get_columns(table_name)
    print(f"\n✅ {table_name}: {len(cols)} columns")
    print(f"   {'Column':<35} {'Type':<20}")
    print(f"   {'-'*55}")
    for col in cols[:8]:
        print(f"   {col['name']:<35} {str(col['type']):<20}")
    if len(cols) > 8:
        print(f"   ... and {len(cols)-8} more columns")

# Check row counts
print(f"\n" + "="*70)
print("CURRENT ROW COUNTS")
print("="*70)

with engine.connect() as conn:
    for table_name in tables:
        result = conn.execute(text(f"SELECT COUNT(*) as cnt FROM {table_name}"))
        count = result.fetchone()[0]
        print(f"  {table_name:<35} {count:>10,} rows")

print("\n✅ All FNO tables verified and ready!")
print("="*70 + "\n")
