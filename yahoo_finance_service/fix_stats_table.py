#!/usr/bin/env python3
"""
Quick fix for symbol mapping statistics table
"""

import mysql.connector
import os
from dotenv import load_dotenv

load_dotenv()

try:
    conn = mysql.connector.connect(
        host=os.getenv('MYSQL_HOST', 'localhost'),
        port=int(os.getenv('MYSQL_PORT', 3306)),
        user=os.getenv('MYSQL_USER', 'root'),
        password=os.getenv('MYSQL_PASSWORD', ''),
        database='marketdata'
    )
    
    cursor = conn.cursor()
    
    # Drop and recreate the stats table
    cursor.execute('DROP TABLE IF EXISTS symbol_mapping_stats')
    
    create_stats_sql = """
        CREATE TABLE symbol_mapping_stats (
            id INT PRIMARY KEY AUTO_INCREMENT,
            total_nse_symbols INT DEFAULT 0 COMMENT 'Total symbols in NSE data',
            mapped_symbols INT DEFAULT 0 COMMENT 'Symbols with Yahoo Finance mappings',
            verified_symbols INT DEFAULT 0 COMMENT 'Mappings verified with API',
            failed_mappings INT DEFAULT 0 COMMENT 'Failed mapping attempts',
            coverage_percentage DECIMAL(6,3) DEFAULT 0.000 COMMENT 'Overall coverage percentage',
            last_validation_run TIMESTAMP NULL COMMENT 'Last time validations were run',
            notes TEXT COMMENT 'Additional notes about mapping status',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
        ) ENGINE=InnoDB COMMENT='Statistics tracking for NSE-Yahoo symbol mappings'
    """
    
    cursor.execute(create_stats_sql)
    
    # Insert initial record
    cursor.execute("""
        INSERT INTO symbol_mapping_stats 
        (total_nse_symbols, mapped_symbols, verified_symbols, failed_mappings, coverage_percentage, notes)
        VALUES (0, 0, 0, 0, 0.000, 'Initial setup - no mappings created yet')
    """)
    
    conn.commit()
    print("✅ Fixed symbol_mapping_stats table with correct data types")
    
    cursor.close()
    conn.close()
    
except Exception as e:
    print(f"❌ Error fixing table: {e}")