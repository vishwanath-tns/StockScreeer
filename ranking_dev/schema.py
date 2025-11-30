"""
Database Schema Management for Ranking System

Creates and manages ranking tables in the database.
"""

import os
from pathlib import Path
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# Load environment
load_dotenv()


def get_ranking_engine():
    """Create SQLAlchemy engine for ranking operations."""
    host = os.getenv("MYSQL_HOST", "localhost")
    port = os.getenv("MYSQL_PORT", "3306")
    db = os.getenv("MYSQL_DB", "marketdata")
    user = os.getenv("MYSQL_USER", "root")
    password = os.getenv("MYSQL_PASSWORD", "")
    
    url = f"mysql+pymysql://{user}:{password}@{host}:{port}/{db}?charset=utf8mb4"
    return create_engine(url, pool_pre_ping=True, pool_recycle=3600)


def create_ranking_tables(engine=None):
    """
    Create ranking tables if they don't exist.
    
    Args:
        engine: SQLAlchemy engine. If None, creates one.
        
    Returns:
        dict with status of each table creation.
    """
    if engine is None:
        engine = get_ranking_engine()
    
    results = {}
    
    # Read SQL file
    sql_file = Path(__file__).parent / "schema.sql"
    if not sql_file.exists():
        # Fallback: inline SQL
        statements = _get_create_statements()
    else:
        with open(sql_file, "r") as f:
            sql_content = f.read()
        # Split by semicolon, filter empty
        statements = [s.strip() for s in sql_content.split(";") if s.strip() and not s.strip().startswith("--")]
    
    with engine.begin() as conn:
        for stmt in statements:
            if "CREATE TABLE" in stmt.upper():
                # Extract table name
                table_name = _extract_table_name(stmt)
                try:
                    conn.execute(text(stmt))
                    results[table_name] = "created"
                except Exception as e:
                    if "already exists" in str(e).lower():
                        results[table_name] = "exists"
                    else:
                        results[table_name] = f"error: {e}"
    
    return results


def _extract_table_name(sql: str) -> str:
    """Extract table name from CREATE TABLE statement."""
    import re
    match = re.search(r"CREATE TABLE\s+(?:IF NOT EXISTS\s+)?(\w+)", sql, re.IGNORECASE)
    return match.group(1) if match else "unknown"


def _get_create_statements() -> list:
    """Fallback inline CREATE statements."""
    return [
        """
        CREATE TABLE IF NOT EXISTS stock_rankings (
            id INT AUTO_INCREMENT PRIMARY KEY,
            symbol VARCHAR(20) NOT NULL,
            calculation_date DATE NOT NULL,
            rs_rating DECIMAL(5,2) DEFAULT 0,
            momentum_score DECIMAL(5,2) DEFAULT 0,
            trend_template_score TINYINT DEFAULT 0,
            technical_score DECIMAL(5,2) DEFAULT 0,
            composite_score DECIMAL(5,2) DEFAULT 0,
            rs_rank INT DEFAULT 0,
            momentum_rank INT DEFAULT 0,
            technical_rank INT DEFAULT 0,
            composite_rank INT DEFAULT 0,
            composite_percentile DECIMAL(5,2) DEFAULT 0,
            total_stocks_ranked INT DEFAULT 0,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            UNIQUE KEY uk_symbol_date (symbol, calculation_date),
            INDEX idx_date (calculation_date),
            INDEX idx_composite_rank (calculation_date, composite_rank)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """,
        """
        CREATE TABLE IF NOT EXISTS stock_rankings_history (
            id INT AUTO_INCREMENT PRIMARY KEY,
            symbol VARCHAR(20) NOT NULL,
            ranking_date DATE NOT NULL,
            rs_rating DECIMAL(5,2) DEFAULT 0,
            momentum_score DECIMAL(5,2) DEFAULT 0,
            trend_template_score TINYINT DEFAULT 0,
            technical_score DECIMAL(5,2) DEFAULT 0,
            composite_score DECIMAL(5,2) DEFAULT 0,
            composite_rank INT DEFAULT 0,
            composite_percentile DECIMAL(5,2) DEFAULT 0,
            total_stocks_ranked INT DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE KEY uk_symbol_ranking_date (symbol, ranking_date),
            INDEX idx_ranking_date (ranking_date),
            INDEX idx_symbol (symbol)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """,
    ]


def check_tables_exist(engine=None) -> dict:
    """Check if ranking tables exist."""
    if engine is None:
        engine = get_ranking_engine()
    
    tables = ["stock_rankings", "stock_rankings_history", "stock_trend_template_details"]
    results = {}
    
    with engine.connect() as conn:
        for table in tables:
            try:
                conn.execute(text(f"SELECT 1 FROM {table} LIMIT 1"))
                results[table] = True
            except:
                results[table] = False
    
    return results


if __name__ == "__main__":
    # Test schema creation
    print("Checking existing tables...")
    status = check_tables_exist()
    print(f"Tables exist: {status}")
    
    print("\nCreating tables...")
    results = create_ranking_tables()
    for table, status in results.items():
        print(f"  {table}: {status}")
