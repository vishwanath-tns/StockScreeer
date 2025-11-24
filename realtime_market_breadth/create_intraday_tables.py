"""
Create Intraday Tables
======================

Creates database tables for storing real-time intraday data.
"""

import os
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Database configuration
DB_CONFIG = {
    'host': os.getenv('MYSQL_HOST', 'localhost'),
    'port': int(os.getenv('MYSQL_PORT', 3306)),
    'user': os.getenv('MYSQL_USER', 'root'),
    'password': os.getenv('MYSQL_PASSWORD', ''),
    'database': os.getenv('MYSQL_DB', 'marketdata'),
}

def get_db_engine():
    """Create database engine using URL.create to handle special characters"""
    url = URL.create(
        drivername="mysql+pymysql",
        username=DB_CONFIG['user'],
        password=DB_CONFIG['password'],
        host=DB_CONFIG['host'],
        port=DB_CONFIG['port'],
        database=DB_CONFIG['database'],
        query={"charset": "utf8mb4"}
    )
    
    return create_engine(
        url,
        pool_pre_ping=True,
        pool_recycle=3600,
        echo=False
    )


def create_tables():
    """Create intraday tables"""
    
    engine = get_db_engine()
    
    print("=" * 70)
    print("Creating Intraday Tables")
    print("=" * 70)
    
    # Read both SQL files
    sql_files = [
        'sql/intraday_tables_schema.sql',
        'sql/intraday_1min_candles_schema.sql'
    ]
    
    for sql_file_name in sql_files:
        sql_file = os.path.join(os.path.dirname(__file__), sql_file_name)
        
        if not os.path.exists(sql_file):
            print(f"⚠️  SQL file not found: {sql_file}")
            continue
        
        print(f"\nProcessing {sql_file_name}...")
        
        with open(sql_file, 'r', encoding='utf-8') as f:
            sql_content = f.read()
        
        # Split by semicolon and execute each statement
        statements = [s.strip() for s in sql_content.split(';') if s.strip()]
        
        with engine.begin() as conn:
            for i, statement in enumerate(statements, 1):
                # Skip comments and USE statements
                if statement.startswith('--') or statement.upper().startswith('USE'):
                    continue
                
                try:
                    # Extract object name for display
                    if 'CREATE TABLE' in statement.upper():
                        table_name = statement.split('TABLE')[1].split('(')[0].strip()
                        print(f"   Creating table: {table_name}")
                    elif 'CREATE OR REPLACE VIEW' in statement.upper():
                        view_name = statement.split('VIEW')[1].split('AS')[0].strip()
                        print(f"   Creating view: {view_name}")
                    
                    conn.execute(text(statement))
                    
                except Exception as e:
                    # Check if it's just a comment or empty
                    if statement.strip():
                        print(f"   ⚠️  Warning: {e}")
    
    # Verify tables exist
    print("\n" + "=" * 70)
    print("Verifying tables...")
    with engine.begin() as conn:
        result = conn.execute(text("""
            SELECT TABLE_NAME, TABLE_ROWS, TABLE_COMMENT
            FROM information_schema.TABLES
            WHERE TABLE_SCHEMA = DATABASE()
                AND TABLE_NAME IN ('intraday_advance_decline', 'intraday_stock_prices', 'intraday_1min_candles')
        """))
        
        tables = result.fetchall()
        
        if tables:
            print("\n✅ Tables verified:")
            for table in tables:
                print(f"   - {table[0]}: {table[1]} rows - {table[2]}")
        else:
            print("❌ Tables not found!")
            return False
    
    # Verify views
    print("\nVerifying views...")
    with engine.begin() as conn:
        result = conn.execute(text("""
            SELECT TABLE_NAME
            FROM information_schema.VIEWS
            WHERE TABLE_SCHEMA = DATABASE()
                AND TABLE_NAME LIKE 'v_%intraday%'
        """))
        
        views = result.fetchall()
        
        if views:
            print("\n✅ Views verified:")
            for view in views:
                print(f"   - {view[0]}")
        else:
            print("⚠️  No views found")
    
    print("\n" + "=" * 70)
    print("Database setup complete!")
    print("=" * 70)
    
    return True


if __name__ == "__main__":
    import sys
    
    try:
        success = create_tables()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
