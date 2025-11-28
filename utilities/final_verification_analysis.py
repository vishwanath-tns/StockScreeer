"""
Final verification analysis script
"""
import mysql.connector
import os
from dotenv import load_dotenv

load_dotenv()

def main():
    conn = mysql.connector.connect(
        host=os.getenv('MYSQL_HOST', 'localhost'),
        port=int(os.getenv('MYSQL_PORT', '3306')),
        database=os.getenv('MYSQL_DB', 'MarketData'),
        user=os.getenv('MYSQL_USER', 'root'),
        password=os.getenv('MYSQL_PASSWORD', 'admin')
    )
    cursor = conn.cursor()

    print('=== COMPREHENSIVE VERIFICATION ANALYSIS ===')

    # Get total symbols in nse_index_constituents
    cursor.execute('SELECT COUNT(*) FROM nse_index_constituents')
    total_nse = cursor.fetchone()[0]
    print(f'Total symbols in nse_index_constituents: {total_nse}')

    # Get filtered symbols (excluding indices)
    cursor.execute("""
        SELECT COUNT(DISTINCT symbol) FROM nse_index_constituents 
        WHERE symbol NOT LIKE "%NIFTY%" 
        AND symbol NOT LIKE "%INDEX%" 
        AND symbol NOT LIKE "%MIDCAP%" 
        AND symbol NOT LIKE "%SMALLCAP%"
    """)
    filtered_nse = cursor.fetchone()[0]
    print(f'Filtered NSE symbols (stocks only): {filtered_nse}')

    # Get mapped symbols
    cursor.execute('SELECT COUNT(*) FROM nse_yahoo_symbol_map WHERE is_active = 1')
    total_mapped = cursor.fetchone()[0]
    print(f'Total mapped symbols: {total_mapped}')

    # Get verified symbols
    cursor.execute('SELECT COUNT(*) FROM nse_yahoo_symbol_map WHERE is_active = 1 AND is_verified = 1')
    verified_mapped = cursor.fetchone()[0]
    print(f'Verified mapped symbols: {verified_mapped}')

    # Get failed symbols
    cursor.execute('SELECT COUNT(*) FROM nse_yahoo_symbol_map WHERE is_active = 1 AND is_verified = 0')
    failed_mapped = cursor.fetchone()[0]
    print(f'Failed mapped symbols: {failed_mapped}')

    # Calculate success rate
    if filtered_nse > 0:
        success_rate = (verified_mapped / filtered_nse) * 100
        print(f'Success rate: {success_rate:.1f}%')

    # Sample of successfully mapped symbols
    print(f'\n=== SAMPLE VERIFIED MAPPINGS ===')
    cursor.execute("""
        SELECT nse_symbol, yahoo_symbol, sector 
        FROM nse_yahoo_symbol_map 
        WHERE is_active = 1 AND is_verified = 1 
        ORDER BY created_at DESC 
        LIMIT 10
    """)
    for row in cursor.fetchall():
        print(f'{row[0]} -> {row[1]} ({row[2]})')

    # Check for unmapped symbols
    print(f'\n=== UNMAPPED SYMBOLS CHECK ===')
    cursor.execute("""
        SELECT COUNT(*) FROM nse_index_constituents n
        LEFT JOIN nse_yahoo_symbol_map m ON n.symbol = m.nse_symbol AND m.is_active = 1
        WHERE m.nse_symbol IS NULL
        AND n.symbol NOT LIKE "%NIFTY%" 
        AND n.symbol NOT LIKE "%INDEX%" 
        AND n.symbol NOT LIKE "%MIDCAP%" 
        AND n.symbol NOT LIKE "%SMALLCAP%"
    """)
    unmapped_count = cursor.fetchone()[0]
    print(f'Truly unmapped symbols: {unmapped_count}')

    if unmapped_count > 0:
        cursor.execute("""
            SELECT DISTINCT n.symbol FROM nse_index_constituents n
            LEFT JOIN nse_yahoo_symbol_map m ON n.symbol = m.nse_symbol AND m.is_active = 1
            WHERE m.nse_symbol IS NULL
            AND n.symbol NOT LIKE "%NIFTY%" 
            AND n.symbol NOT LIKE "%INDEX%" 
            AND n.symbol NOT LIKE "%MIDCAP%" 
            AND n.symbol NOT LIKE "%SMALLCAP%"
            LIMIT 10
        """)
        print('Sample unmapped symbols:')
        for row in cursor.fetchall():
            print(f'  {row[0]}')

    # Check sector distribution
    print(f'\n=== SECTOR DISTRIBUTION ===')
    cursor.execute("""
        SELECT sector, COUNT(*) as count 
        FROM nse_yahoo_symbol_map 
        WHERE is_active = 1 AND is_verified = 1 AND sector != ''
        GROUP BY sector 
        ORDER BY count DESC
        LIMIT 10
    """)
    for row in cursor.fetchall():
        print(f'{row[0]}: {row[1]} symbols')

    cursor.close()
    conn.close()

if __name__ == "__main__":
    main()