"""
Setup NSE Block & Bulk Deals Database Tables

Creates all required tables in the marketdata database.
"""

import os
import sys
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from urllib.parse import quote_plus

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

load_dotenv()

def get_engine():
    """Create database engine"""
    password = quote_plus(os.getenv('MYSQL_PASSWORD', 'rajat123'))
    connection_string = (
        f"mysql+pymysql://{os.getenv('MYSQL_USER', 'root')}:"
        f"{password}@"
        f"{os.getenv('MYSQL_HOST', 'localhost')}:"
        f"{os.getenv('MYSQL_PORT', '3306')}/"
        f"{os.getenv('MYSQL_DB', 'marketdata')}?charset=utf8mb4"
    )
    
    return create_engine(connection_string, pool_pre_ping=True, pool_recycle=3600)

def main():
    """Setup database tables"""
    print("=" * 80)
    print("NSE Block & Bulk Deals - Database Setup")
    print("=" * 80)
    
    # Read SQL file
    sql_file = os.path.join(os.path.dirname(__file__), 'setup_tables.sql')
    
    if not os.path.exists(sql_file):
        print(f"❌ Error: {sql_file} not found")
        return 1
        
    print(f"\n📄 Reading SQL file: {sql_file}")
    
    with open(sql_file, 'r', encoding='utf-8') as f:
        sql_content = f.read()
    
    # Get engine
    print("🔌 Connecting to database...")
    engine = get_engine()
    
    # Execute SQL directly (no splitting - let MySQL handle it)
    print("📋 Executing SQL statements...")
    print("\n" + "=" * 80)
    
    with engine.begin() as conn:
        try:
            # Remove USE statement
            sql_cleaned = sql_content.replace('USE marketdata;', '')
            
            # Execute CREATE TABLE statements individually
            import re
            
            # Find all CREATE TABLE statements
            create_patterns = [
                r'CREATE TABLE IF NOT EXISTS (\w+)',
                r'CREATE OR REPLACE VIEW (\w+)'
            ]
            
            for pattern in create_patterns:
                for match in re.finditer(pattern, sql_cleaned):
                    table_name = match.group(1)
                    print(f"✅ Creating: {table_name}")
            
            # Split by major statement boundaries
            statements = re.split(r';\s*(?=CREATE|--)', sql_cleaned)
            
            for statement in statements:
                statement = statement.strip()
                if not statement or statement.startswith('--') or len(statement) < 10:
                    continue
                    
                try:
                    conn.execute(text(statement + ';'))
                except Exception as e:
                    if "already exists" not in str(e).lower():
                        print(f"  ⚠️ Warning: {str(e)[:80]}")
                        
        except Exception as e:
            print(f"❌ Error executing SQL: {e}")
    
    # Verify tables
    print("\n" + "=" * 80)
    print("Verifying tables...")
    print("=" * 80)
    
    with engine.connect() as conn:
        # Check nse_block_deals
        result = conn.execute(text("SELECT COUNT(*) FROM nse_block_deals"))
        block_count = result.scalar()
        print(f"✅ nse_block_deals: {block_count:,} records")
        
        # Check nse_bulk_deals
        result = conn.execute(text("SELECT COUNT(*) FROM nse_bulk_deals"))
        bulk_count = result.scalar()
        print(f"✅ nse_bulk_deals: {bulk_count:,} records")
        
        # Check import log
        result = conn.execute(text("SELECT COUNT(*) FROM block_bulk_deals_import_log"))
        log_count = result.scalar()
        print(f"✅ block_bulk_deals_import_log: {log_count:,} records")
    
    print("\n" + "=" * 80)
    print("✅ Database setup complete!")
    print("=" * 80)
    print("\nNext steps:")
    print("  1. Run GUI: python block_bulk_deals/sync_deals_gui.py")
    print("  2. Or CLI: python block_bulk_deals/sync_deals_cli.py --help")
    print("=" * 80)
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
