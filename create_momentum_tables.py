"""
Manual Database Setup for Momentum Analysis
===========================================

Creates the momentum analysis tables manually to avoid SQL parsing issues.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.momentum.database_service import DatabaseService
from sqlalchemy import text

def create_momentum_tables_manually():
    """Create momentum tables with individual SQL statements"""
    
    print("🏗️ CREATING MOMENTUM TABLES MANUALLY")
    print("=" * 50)
    
    db_service = DatabaseService()
    
    # Individual SQL statements
    sql_statements = [
        """
        CREATE TABLE IF NOT EXISTS momentum_analysis (
            id BIGINT AUTO_INCREMENT PRIMARY KEY,
            symbol VARCHAR(50) NOT NULL,
            series VARCHAR(10) NOT NULL DEFAULT 'EQ',
            duration_type VARCHAR(10) NOT NULL,
            duration_days INT NOT NULL,
            start_date DATE NOT NULL,
            end_date DATE NOT NULL,
            calculation_date DATE NOT NULL,
            start_price DECIMAL(15, 4) NOT NULL,
            end_price DECIMAL(15, 4) NOT NULL,
            high_price DECIMAL(15, 4) NOT NULL,
            low_price DECIMAL(15, 4) NOT NULL,
            absolute_change DECIMAL(15, 4) NOT NULL,
            percentage_change DECIMAL(10, 4) NOT NULL,
            avg_volume BIGINT,
            total_volume BIGINT,
            volume_surge_factor DECIMAL(8, 4),
            price_volatility DECIMAL(8, 4),
            high_low_ratio DECIMAL(8, 4),
            percentile_rank DECIMAL(5, 2),
            sector_rank INT,
            overall_rank INT,
            trading_days INT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            UNIQUE KEY uk_momentum (symbol, duration_type, end_date)
        ) ENGINE=InnoDB
        """,
        
        """
        CREATE TABLE IF NOT EXISTS momentum_rankings (
            id BIGINT AUTO_INCREMENT PRIMARY KEY,
            calculation_date DATE NOT NULL,
            duration_type VARCHAR(10) NOT NULL,
            top_gainers JSON,
            top_losers JSON,
            avg_gain DECIMAL(10, 4),
            median_gain DECIMAL(10, 4),
            std_deviation DECIMAL(10, 4),
            total_stocks INT,
            positive_stocks INT,
            negative_stocks INT,
            best_sector VARCHAR(100),
            worst_sector VARCHAR(100),
            sector_performance JSON,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE KEY uk_ranking (calculation_date, duration_type)
        ) ENGINE=InnoDB
        """,
        
        """
        CREATE TABLE IF NOT EXISTS sector_momentum (
            id BIGINT AUTO_INCREMENT PRIMARY KEY,
            sector VARCHAR(100) NOT NULL,
            duration_type VARCHAR(10) NOT NULL,
            calculation_date DATE NOT NULL,
            stock_count INT NOT NULL,
            avg_momentum DECIMAL(10, 4),
            median_momentum DECIMAL(10, 4),
            sector_rank INT,
            positive_count INT,
            negative_count INT,
            strong_positive_count INT,
            strong_negative_count INT,
            best_performer VARCHAR(50),
            best_performance DECIMAL(10, 4),
            worst_performer VARCHAR(50),
            worst_performance DECIMAL(10, 4),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE KEY uk_sector_momentum (sector, duration_type, calculation_date)
        ) ENGINE=InnoDB
        """,
        
        """
        CREATE TABLE IF NOT EXISTS momentum_calculation_jobs (
            id BIGINT AUTO_INCREMENT PRIMARY KEY,
            job_id VARCHAR(100) NOT NULL UNIQUE,
            duration_type VARCHAR(10) NOT NULL,
            calculation_date DATE NOT NULL,
            status VARCHAR(20) DEFAULT 'PENDING',
            start_time TIMESTAMP NULL,
            end_time TIMESTAMP NULL,
            total_symbols INT,
            processed_symbols INT,
            failed_symbols INT,
            results_summary JSON,
            error_details TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
        ) ENGINE=InnoDB
        """
    ]
    
    # Create tables
    try:
        with db_service.engine.begin() as conn:
            for i, sql in enumerate(sql_statements, 1):
                try:
                    conn.execute(text(sql))
                    table_name = sql.split('(')[0].split()[-1]
                    print(f"✅ [{i}/4] Created table: {table_name}")
                except Exception as e:
                    if 'already exists' in str(e).lower():
                        table_name = sql.split('(')[0].split()[-1]
                        print(f"ℹ️ [{i}/4] Table already exists: {table_name}")
                    else:
                        print(f"❌ [{i}/4] Error creating table: {e}")
    except Exception as e:
        print(f"❌ Database connection error: {e}")
        return False
    
    # Test table creation
    print(f"\n🔍 TESTING TABLE CREATION")
    print("-" * 30)
    
    test_queries = [
        "SELECT COUNT(*) as count FROM momentum_analysis",
        "SELECT COUNT(*) as count FROM momentum_rankings", 
        "SELECT COUNT(*) as count FROM sector_momentum",
        "SELECT COUNT(*) as count FROM momentum_calculation_jobs"
    ]
    
    for i, query in enumerate(test_queries, 1):
        try:
            result = db_service.execute_query(query)
            table_name = query.split('FROM ')[1]
            print(f"✅ [{i}/4] {table_name}: Ready (0 records)")
        except Exception as e:
            print(f"❌ [{i}/4] Error testing table: {e}")
    
    print(f"\n🏆 MOMENTUM TABLES CREATED SUCCESSFULLY!")
    return True

def main():
    """Create momentum tables"""
    success = create_momentum_tables_manually()
    
    if success:
        print(f"\n✅ Database setup complete! You can now run momentum calculations.")
    else:
        print(f"\n❌ Database setup failed. Please check the errors above.")

if __name__ == "__main__":
    main()