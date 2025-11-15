"""
Setup Index Tables
==================

Ensures the database tables for index management are properly structured.
"""

import sys
sys.path.append('.')

from reporting_adv_decl import engine
from sqlalchemy import text

def setup_index_tables():
    """
    Setup or update index-related tables
    """
    with engine().connect() as conn:
        
        # Create nse_indices table if it doesn't exist
        print("Setting up nse_indices table...")
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS nse_indices (
                id INT PRIMARY KEY AUTO_INCREMENT,
                index_code VARCHAR(50) NOT NULL UNIQUE,
                name VARCHAR(100) NOT NULL,
                category ENUM('MAIN', 'SECTORAL', 'THEMATIC') DEFAULT 'SECTORAL',
                sector VARCHAR(50) NULL,
                description TEXT NULL,
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                
                INDEX idx_category (category),
                INDEX idx_active (is_active),
                INDEX idx_code_name (index_code, name)
            )
        """))
        
        # Ensure nse_index_constituents has proper structure
        print("Setting up nse_index_constituents table...")
        
        # Check if table exists and get its structure
        try:
            result = conn.execute(text("DESCRIBE nse_index_constituents"))
            existing_columns = [row[0] for row in result.fetchall()]
            print(f"Existing columns: {existing_columns}")
            
            # Add missing columns if needed
            if 'company_name' not in existing_columns:
                print("Adding company_name column...")
                conn.execute(text("ALTER TABLE nse_index_constituents ADD COLUMN company_name VARCHAR(200) NULL"))
            
            if 'series' not in existing_columns:
                print("Adding series column...")  
                conn.execute(text("ALTER TABLE nse_index_constituents ADD COLUMN series VARCHAR(10) DEFAULT 'EQ'"))
                
            if 'isin_code' not in existing_columns:
                print("Adding isin_code column...")
                conn.execute(text("ALTER TABLE nse_index_constituents ADD COLUMN isin_code VARCHAR(20) NULL"))
            
            # Add useful indexes
            print("Adding indexes for performance...")
            try:
                conn.execute(text("CREATE INDEX idx_constituents_symbol ON nse_index_constituents(symbol)"))
            except:
                pass  # Index might already exist
                
            try:
                conn.execute(text("CREATE INDEX idx_constituents_index_symbol ON nse_index_constituents(index_id, symbol)"))
            except:
                pass  # Index might already exist
                
        except Exception as e:
            print(f"Error updating nse_index_constituents: {e}")
        
        # Create a view for easy access to latest constituents
        print("Creating view for latest constituents...")
        conn.execute(text("""
            CREATE OR REPLACE VIEW v_latest_constituents AS
            SELECT 
                ni.index_code,
                ni.index_name,
                ni.category,
                nc.symbol,
                nc.company_name,
                nc.series,
                nc.data_date
            FROM nse_indices ni
            JOIN nse_index_constituents nc ON ni.id = nc.index_id
            WHERE ni.is_active = 1
            AND nc.data_date = (
                SELECT MAX(data_date) 
                FROM nse_index_constituents nc2 
                WHERE nc2.index_id = nc.index_id
            )
        """))
        
        conn.commit()
        print("✅ Index tables setup completed successfully!")

if __name__ == "__main__":
    setup_index_tables()