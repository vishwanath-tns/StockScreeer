#!/usr/bin/env python3
"""
Populate Volume Events Database
Analyzes all Nifty 50 stocks and stores high volume events in database.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.event_analyzer import VolumeEventAnalyzer
from data.data_loader import NIFTY_50_SYMBOLS
from sqlalchemy import text
from tqdm import tqdm


def create_table_if_not_exists(engine):
    """Create the volume_cluster_events table if it doesn't exist."""
    create_sql = """
    CREATE TABLE IF NOT EXISTS volume_cluster_events (
        id INT AUTO_INCREMENT PRIMARY KEY,
        symbol VARCHAR(50) NOT NULL,
        event_date DATE NOT NULL,
        volume BIGINT NOT NULL,
        volume_quintile VARCHAR(20) NOT NULL,
        close_price DECIMAL(12, 2),
        prev_close DECIMAL(12, 2),
        day_return DECIMAL(8, 2),
        relative_volume DECIMAL(8, 2),
        return_1d DECIMAL(8, 2),
        return_1w DECIMAL(8, 2),
        return_2w DECIMAL(8, 2),
        return_3w DECIMAL(8, 2),
        return_1m DECIMAL(8, 2),
        price_1d DECIMAL(12, 2),
        price_1w DECIMAL(12, 2),
        price_2w DECIMAL(12, 2),
        price_3w DECIMAL(12, 2),
        price_1m DECIMAL(12, 2),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE KEY uk_symbol_date (symbol, event_date),
        INDEX idx_symbol (symbol),
        INDEX idx_event_date (event_date),
        INDEX idx_quintile (volume_quintile)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """
    
    with engine.connect() as conn:
        conn.execute(text(create_sql))
        conn.commit()
    print("✓ Table volume_cluster_events ready")


def populate_all_stocks(symbols=None, quintiles=None):
    """Analyze and store events for all stocks."""
    if symbols is None:
        symbols = NIFTY_50_SYMBOLS
    
    if quintiles is None:
        quintiles = ['High', 'Very High']
    
    analyzer = VolumeEventAnalyzer()
    
    # Create table if not exists
    create_table_if_not_exists(analyzer.engine)
    
    total_events = 0
    success_count = 0
    
    print(f"\nAnalyzing {len(symbols)} stocks for volume events...")
    print(f"Tracking quintiles: {quintiles}\n")
    
    for symbol in tqdm(symbols, desc="Processing"):
        try:
            events = analyzer.analyze_stock(symbol, quintiles_to_track=quintiles)
            if events:
                count = analyzer.save_events_to_db(events)
                total_events += count
                success_count += 1
        except Exception as e:
            print(f"\n✗ Error processing {symbol}: {e}")
    
    print(f"\n{'='*50}")
    print(f"SUMMARY")
    print(f"{'='*50}")
    print(f"Stocks processed: {success_count}/{len(symbols)}")
    print(f"Total events stored: {total_events:,}")
    print(f"Average events per stock: {total_events/success_count:.0f}" if success_count > 0 else "N/A")
    
    return total_events


def get_stats():
    """Print statistics about stored events."""
    analyzer = VolumeEventAnalyzer()
    
    query = """
    SELECT 
        volume_quintile,
        COUNT(*) as events,
        COUNT(DISTINCT symbol) as stocks,
        ROUND(AVG(return_1m), 2) as avg_1m_return,
        ROUND(SUM(CASE WHEN return_1m > 0 THEN 1 ELSE 0 END) * 100.0 / 
              SUM(CASE WHEN return_1m IS NOT NULL THEN 1 ELSE 0 END), 1) as win_rate
    FROM volume_cluster_events
    GROUP BY volume_quintile
    ORDER BY CASE volume_quintile 
        WHEN 'Very Low' THEN 1 WHEN 'Low' THEN 2 WHEN 'Normal' THEN 3 
        WHEN 'High' THEN 4 WHEN 'Very High' THEN 5 END
    """
    
    import pandas as pd
    with analyzer.engine.connect() as conn:
        df = pd.read_sql(text(query), conn)
    
    print("\nVolume Event Statistics:")
    print("="*60)
    print(df.to_string(index=False))


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Populate volume events database')
    parser.add_argument('--stats', action='store_true', help='Show statistics only')
    parser.add_argument('--symbol', type=str, help='Analyze single symbol')
    args = parser.parse_args()
    
    if args.stats:
        get_stats()
    elif args.symbol:
        populate_all_stocks(symbols=[args.symbol])
        get_stats()
    else:
        populate_all_stocks()
        get_stats()
