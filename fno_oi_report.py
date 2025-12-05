import os
import sys
from datetime import datetime, date
from typing import List
import pandas as pd
from urllib.parse import quote_plus
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()

DB_CONFIG = {
    'host': os.getenv('MYSQL_HOST', 'localhost'),
    'port': int(os.getenv('MYSQL_PORT', 3306)),
    'user': os.getenv('MYSQL_USER', 'root'),
    'password': os.getenv('MYSQL_PASSWORD', ''),
    'database': 'fno_marketdata'
}

def run_report():
    encoded_password = quote_plus(DB_CONFIG['password'])
    connection_string = f"mysql+pymysql://{DB_CONFIG['user']}:{encoded_password}@{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']}?charset=utf8mb4"
    engine = create_engine(connection_string, pool_pre_ping=True)
    
    with engine.connect() as conn:
        dates = [row[0] for row in conn.execute(text("SELECT DISTINCT trade_date FROM nse_futures ORDER BY trade_date DESC")).fetchall()]
    
    print("=" * 80)
    print("FNO CUMULATIVE OI ANALYSIS REPORT")
    print("=" * 80)
    print(f"Dates: {dates}")
    
    if len(dates) < 2:
        print("Need at least 2 days of data")
        return
    
    query = '''
    SELECT f.trade_date, f.symbol, f.instrument_type, f.close_price, f.open_interest
    FROM nse_futures f
    WHERE f.expiry_date = (
        SELECT MIN(expiry_date) FROM nse_futures f2 
        WHERE f2.symbol = f.symbol AND f2.trade_date = f.trade_date AND f2.expiry_date >= f2.trade_date
    )
    ORDER BY f.symbol, f.trade_date
    '''
    
    with engine.connect() as conn:
        df = pd.read_sql(query, conn)
    
    print(f"\nTotal Records: {len(df)}")
    print(f"Symbols: {df['symbol'].nunique()}")
    
    results = []
    for symbol in df['symbol'].unique():
        sym_df = df[df['symbol'] == symbol].sort_values('trade_date')
        if len(sym_df) < 2:
            continue
        
        first = sym_df.iloc[0]
        last = sym_df.iloc[-1]
        
        price_chg = last['close_price'] - first['close_price']
        price_pct = (price_chg / first['close_price'] * 100) if first['close_price'] > 0 else 0
        oi_chg = last['open_interest'] - first['open_interest']
        oi_pct = (oi_chg / first['open_interest'] * 100) if first['open_interest'] > 0 else 0
        
        if price_chg > 0 and oi_chg > 0:
            interp = 'LONG_BUILDUP'
        elif price_chg < 0 and oi_chg > 0:
            interp = 'SHORT_BUILDUP'
        elif price_chg < 0 and oi_chg < 0:
            interp = 'LONG_UNWINDING'
        else:
            interp = 'SHORT_COVERING'
        
        results.append({
            'symbol': symbol,
            'instrument_type': first['instrument_type'],
            'price_pct': round(price_pct, 2),
            'oi_pct': round(oi_pct, 2),
            'oi_change': int(oi_chg),
            'interpretation': interp
        })
    
    result_df = pd.DataFrame(results)
    stocks = result_df[result_df['instrument_type'] == 'FUTSTK']
    indices = result_df[result_df['instrument_type'] == 'FUTIDX']
    
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    for interp in ['LONG_BUILDUP', 'SHORT_BUILDUP', 'LONG_UNWINDING', 'SHORT_COVERING']:
        cnt = len(result_df[result_df['interpretation'] == interp])
        print(f"{interp}: {cnt}")
    
    print("\n" + "=" * 80)
    print("INDEX FUTURES")
    print("=" * 80)
    for _, row in indices.iterrows():
        print(f"{row['symbol']}: {row['interpretation']} | Price: {row['price_pct']:+.2f}% | OI: {row['oi_pct']:+.2f}% ({row['oi_change']:+,})")
    
    print("\n" + "=" * 80)
    print("LONG BUILDUP (Price UP + OI UP) - BULLISH")
    print("=" * 80)
    lb = stocks[stocks['interpretation'] == 'LONG_BUILDUP'].sort_values('oi_pct', ascending=False).head(25)
    print(f"{'Symbol':<15} {'Price%':>10} {'OI%':>10} {'OI Change':>15}")
    print("-" * 55)
    for _, row in lb.iterrows():
        print(f"{row['symbol']:<15} {row['price_pct']:>+9.2f}% {row['oi_pct']:>+9.2f}% {row['oi_change']:>+14,}")
    
    print("\n" + "=" * 80)
    print("SHORT BUILDUP (Price DOWN + OI UP) - BEARISH")
    print("=" * 80)
    sb = stocks[stocks['interpretation'] == 'SHORT_BUILDUP'].sort_values('oi_pct', ascending=False).head(25)
    print(f"{'Symbol':<15} {'Price%':>10} {'OI%':>10} {'OI Change':>15}")
    print("-" * 55)
    for _, row in sb.iterrows():
        print(f"{row['symbol']:<15} {row['price_pct']:>+9.2f}% {row['oi_pct']:>+9.2f}% {row['oi_change']:>+14,}")
    
    print("\n" + "=" * 80)
    print("LONG UNWINDING (Price DOWN + OI DOWN) - WEAK")
    print("=" * 80)
    lu = stocks[stocks['interpretation'] == 'LONG_UNWINDING'].sort_values('oi_pct').head(25)
    print(f"{'Symbol':<15} {'Price%':>10} {'OI%':>10} {'OI Change':>15}")
    print("-" * 55)
    for _, row in lu.iterrows():
        print(f"{row['symbol']:<15} {row['price_pct']:>+9.2f}% {row['oi_pct']:>+9.2f}% {row['oi_change']:>+14,}")
    
    print("\n" + "=" * 80)
    print("SHORT COVERING (Price UP + OI DOWN) - RECOVERY")
    print("=" * 80)
    sc = stocks[stocks['interpretation'] == 'SHORT_COVERING'].sort_values('price_pct', ascending=False).head(25)
    print(f"{'Symbol':<15} {'Price%':>10} {'OI%':>10} {'OI Change':>15}")
    print("-" * 55)
    for _, row in sc.iterrows():
        print(f"{row['symbol']:<15} {row['price_pct']:>+9.2f}% {row['oi_pct']:>+9.2f}% {row['oi_change']:>+14,}")

if __name__ == "__main__":
    run_report()
