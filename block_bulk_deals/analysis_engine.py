"""
Block & Bulk Deals Analysis Engine

Comprehensive analysis of NSE Block and Bulk Deals data for investment decisions.
Analyzes patterns, trends, accumulation/distribution, and generates actionable insights.
"""

import os
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
import pandas as pd
import numpy as np
from sqlalchemy import create_engine, text
from urllib.parse import quote_plus
from dotenv import load_dotenv

load_dotenv()


class BlockBulkDealsAnalyzer:
    """Analyze Block & Bulk Deals for investment insights"""
    
    def __init__(self):
        """Initialize database connection"""
        self.engine = self._create_engine()
        
    def _create_engine(self):
        """Create SQLAlchemy engine"""
        password = quote_plus(os.getenv('MYSQL_PASSWORD', 'rajat123'))
        connection_string = (
            f"mysql+pymysql://{os.getenv('MYSQL_USER', 'root')}:"
            f"{password}@"
            f"{os.getenv('MYSQL_HOST', 'localhost')}:"
            f"{os.getenv('MYSQL_PORT', '3306')}/"
            f"{os.getenv('MYSQL_DB', 'marketdata')}?charset=utf8mb4"
        )
        return create_engine(connection_string, pool_pre_ping=True, pool_recycle=3600)
    
    # ============================================================================
    # 1. ACCUMULATION/DISTRIBUTION ANALYSIS
    # ============================================================================
    
    def analyze_accumulation_distribution(self, days: int = 90) -> pd.DataFrame:
        """
        Identify stocks showing strong accumulation or distribution patterns
        
        Returns: DataFrame with accumulation score, buy/sell ratio, key clients
        """
        cutoff_date = (datetime.now() - timedelta(days=days)).date()
        
        query = text("""
            SELECT 
                symbol,
                security_name,
                COUNT(*) as total_deals,
                SUM(CASE WHEN deal_type = 'BUY' THEN 1 ELSE 0 END) as buy_deals,
                SUM(CASE WHEN deal_type = 'SELL' THEN 1 ELSE 0 END) as sell_deals,
                SUM(CASE WHEN deal_type = 'BUY' THEN quantity ELSE 0 END) as buy_qty,
                SUM(CASE WHEN deal_type = 'SELL' THEN quantity ELSE 0 END) as sell_qty,
                SUM(CASE WHEN deal_type = 'BUY' THEN quantity * trade_price ELSE 0 END) / 10000000 as buy_value_cr,
                SUM(CASE WHEN deal_type = 'SELL' THEN quantity * trade_price ELSE 0 END) / 10000000 as sell_value_cr,
                COUNT(DISTINCT client_name) as unique_clients,
                MIN(trade_date) as first_deal,
                MAX(trade_date) as last_deal
            FROM (
                SELECT symbol, security_name, deal_type, quantity, trade_price, client_name, trade_date
                FROM nse_block_deals WHERE trade_date >= :cutoff
                UNION ALL
                SELECT symbol, security_name, deal_type, quantity, trade_price, client_name, trade_date
                FROM nse_bulk_deals WHERE trade_date >= :cutoff
            ) combined
            GROUP BY symbol, security_name
            HAVING total_deals >= 5
            ORDER BY total_deals DESC
        """)
        
        df = pd.read_sql(query, self.engine, params={'cutoff': cutoff_date})
        
        # Calculate accumulation metrics
        df['buy_sell_ratio'] = np.where(df['sell_deals'] > 0, 
                                         df['buy_deals'] / df['sell_deals'], 
                                         df['buy_deals'])
        df['qty_ratio'] = np.where(df['sell_qty'] > 0,
                                    df['buy_qty'] / df['sell_qty'],
                                    df['buy_qty'] / 1000)
        df['value_ratio'] = np.where(df['sell_value_cr'] > 0,
                                      df['buy_value_cr'] / df['sell_value_cr'],
                                      df['buy_value_cr'])
        
        # Accumulation score (0-100)
        df['accumulation_score'] = np.minimum(100, 
            (df['buy_sell_ratio'] * 30 + 
             df['qty_ratio'] * 30 + 
             df['value_ratio'] * 30 + 
             df['unique_clients'] * 10) / 100 * 100
        )
        
        # Signal
        df['signal'] = pd.cut(df['accumulation_score'], 
                               bins=[0, 40, 60, 100],
                               labels=['DISTRIBUTION', 'NEUTRAL', 'ACCUMULATION'])
        
        return df.sort_values('accumulation_score', ascending=False)
    
    # ============================================================================
    # 2. SMART MONEY TRACKING
    # ============================================================================
    
    def track_smart_money(self, days: int = 90) -> Dict[str, pd.DataFrame]:
        """
        Track activities of institutional investors, FIIs, and known smart money
        
        Returns: Dict with separate DataFrames for different investor types
        """
        cutoff_date = (datetime.now() - timedelta(days=days)).date()
        
        # Identify smart money patterns
        smart_money_patterns = [
            'MUTUAL FUND', 'GOLDMAN SACHS', 'MORGAN STANLEY', 'AZIM PREMJI',
            'ICICI PRUDENTIAL', 'HDFC', 'SBI', 'ADITYA BIRLA', 'RELIANCE',
            'JPMORGAN', 'BARCLAYS', 'CREDIT SUISSE', 'UBS', 'CITIGROUP'
        ]
        
        results = {}
        
        for pattern in smart_money_patterns:
            query = text("""
                SELECT 
                    client_name,
                    symbol,
                    security_name,
                    deal_type,
                    COUNT(*) as deals,
                    SUM(quantity) as total_qty,
                    SUM(quantity * trade_price) / 10000000 as value_cr,
                    MIN(trade_date) as first_trade,
                    MAX(trade_date) as last_trade,
                    DATEDIFF(MAX(trade_date), MIN(trade_date)) as days_active
                FROM (
                    SELECT client_name, symbol, security_name, deal_type, quantity, 
                           trade_price, trade_date
                    FROM nse_block_deals 
                    WHERE trade_date >= :cutoff AND client_name LIKE :pattern
                    UNION ALL
                    SELECT client_name, symbol, security_name, deal_type, quantity,
                           trade_price, trade_date
                    FROM nse_bulk_deals 
                    WHERE trade_date >= :cutoff AND client_name LIKE :pattern
                ) combined
                GROUP BY client_name, symbol, security_name, deal_type
                HAVING deals >= 2
                ORDER BY value_cr DESC
            """)
            
            df = pd.read_sql(query, self.engine, 
                           params={'cutoff': cutoff_date, 'pattern': f'%{pattern}%'})
            
            if not df.empty:
                results[pattern] = df
        
        return results
    
    # ============================================================================
    # 3. REPEATED BUYING PATTERNS
    # ============================================================================
    
    def find_repeated_buying(self, min_buys: int = 3, days: int = 90) -> pd.DataFrame:
        """
        Find stocks with repeated buying by same or multiple clients
        Strong accumulation signal
        """
        cutoff_date = (datetime.now() - timedelta(days=days)).date()
        
        query = text("""
            SELECT 
                symbol,
                security_name,
                client_name,
                COUNT(*) as buy_count,
                SUM(quantity) as total_qty,
                AVG(trade_price) as avg_price,
                MIN(trade_price) as min_price,
                MAX(trade_price) as max_price,
                SUM(quantity * trade_price) / 10000000 as total_value_cr,
                MIN(trade_date) as first_buy,
                MAX(trade_date) as last_buy,
                DATEDIFF(MAX(trade_date), MIN(trade_date)) as buying_period_days
            FROM (
                SELECT symbol, security_name, client_name, quantity, trade_price, trade_date
                FROM nse_block_deals 
                WHERE trade_date >= :cutoff AND deal_type = 'BUY'
                UNION ALL
                SELECT symbol, security_name, client_name, quantity, trade_price, trade_date
                FROM nse_bulk_deals 
                WHERE trade_date >= :cutoff AND deal_type = 'BUY'
            ) combined
            GROUP BY symbol, security_name, client_name
            HAVING buy_count >= :min_buys
            ORDER BY buy_count DESC, total_value_cr DESC
        """)
        
        df = pd.read_sql(query, self.engine, 
                        params={'cutoff': cutoff_date, 'min_buys': min_buys})
        
        # Calculate buying intensity
        df['buying_frequency'] = df['buy_count'] / (df['buying_period_days'] + 1)
        df['price_trend'] = ((df['max_price'] - df['min_price']) / df['min_price'] * 100).round(2)
        
        return df
    
    # ============================================================================
    # 4. SUDDEN SPIKE DETECTION
    # ============================================================================
    
    def detect_unusual_activity(self, lookback_days: int = 90, spike_days: int = 7) -> pd.DataFrame:
        """
        Detect unusual spikes in trading activity
        Compare recent activity vs historical baseline
        """
        cutoff_date = (datetime.now() - timedelta(days=lookback_days)).date()
        spike_date = (datetime.now() - timedelta(days=spike_days)).date()
        
        query = text("""
            SELECT 
                symbol,
                security_name,
                SUM(CASE WHEN trade_date >= :spike_date THEN 1 ELSE 0 END) as recent_deals,
                SUM(CASE WHEN trade_date < :spike_date THEN 1 ELSE 0 END) as historical_deals,
                SUM(CASE WHEN trade_date >= :spike_date THEN quantity * trade_price ELSE 0 END) / 10000000 as recent_value_cr,
                SUM(CASE WHEN trade_date < :spike_date THEN quantity * trade_price ELSE 0 END) / 10000000 as historical_value_cr,
                COUNT(DISTINCT CASE WHEN trade_date >= :spike_date THEN client_name END) as recent_clients,
                COUNT(DISTINCT CASE WHEN trade_date < :spike_date THEN client_name END) as historical_clients,
                MAX(trade_date) as last_deal_date
            FROM (
                SELECT symbol, security_name, quantity, trade_price, trade_date, client_name
                FROM nse_block_deals WHERE trade_date >= :cutoff
                UNION ALL
                SELECT symbol, security_name, quantity, trade_price, trade_date, client_name
                FROM nse_bulk_deals WHERE trade_date >= :cutoff
            ) combined
            GROUP BY symbol, security_name
            HAVING recent_deals > 0 AND historical_deals > 0
        """)
        
        df = pd.read_sql(query, self.engine, 
                        params={'cutoff': cutoff_date, 'spike_date': spike_date})
        
        # Calculate spike ratio
        df['deal_spike_ratio'] = (df['recent_deals'] / (spike_days + 1)) / (df['historical_deals'] / (lookback_days - spike_days + 1))
        df['value_spike_ratio'] = (df['recent_value_cr'] / (spike_days + 1)) / (df['historical_value_cr'] / (lookback_days - spike_days + 1))
        
        # Flag significant spikes (>2x normal activity)
        df['unusual_activity'] = np.where(
            (df['deal_spike_ratio'] > 2) | (df['value_spike_ratio'] > 2),
            'YES', 'NO'
        )
        
        return df[df['unusual_activity'] == 'YES'].sort_values('deal_spike_ratio', ascending=False)
    
    # ============================================================================
    # 5. PRICE MOMENTUM CORRELATION
    # ============================================================================
    
    def analyze_price_momentum(self, days: int = 90) -> pd.DataFrame:
        """
        Correlate block/bulk deals with price movements
        Requires bhav data for price analysis
        """
        cutoff_date = (datetime.now() - timedelta(days=days)).date()
        
        query = text("""
            SELECT 
                d.symbol,
                d.security_name,
                COUNT(DISTINCT d.trade_date) as deal_days,
                COUNT(*) as total_deals,
                SUM(CASE WHEN d.deal_type = 'BUY' THEN d.quantity * d.trade_price ELSE 0 END) / 10000000 as buy_value_cr,
                SUM(CASE WHEN d.deal_type = 'SELL' THEN d.quantity * d.trade_price ELSE 0 END) / 10000000 as sell_value_cr,
                MIN(b.close_price) as min_price,
                MAX(b.close_price) as max_price,
                (SELECT close_price FROM nse_equity_bhavcopy_full 
                 WHERE symbol = d.symbol AND trade_date >= :cutoff 
                 ORDER BY trade_date ASC LIMIT 1) as first_price,
                (SELECT close_price FROM nse_equity_bhavcopy_full 
                 WHERE symbol = d.symbol AND trade_date >= :cutoff 
                 ORDER BY trade_date DESC LIMIT 1) as last_price
            FROM (
                SELECT symbol, security_name, deal_type, quantity, trade_price, trade_date
                FROM nse_block_deals WHERE trade_date >= :cutoff
                UNION ALL
                SELECT symbol, security_name, deal_type, quantity, trade_price, trade_date
                FROM nse_bulk_deals WHERE trade_date >= :cutoff
            ) d
            LEFT JOIN nse_equity_bhavcopy_full b 
                ON d.symbol = b.symbol AND b.trade_date >= :cutoff
            GROUP BY d.symbol, d.security_name
            HAVING first_price IS NOT NULL AND last_price IS NOT NULL
        """)
        
        df = pd.read_sql(query, self.engine, params={'cutoff': cutoff_date})
        
        # Calculate returns and correlation
        df['price_change_pct'] = ((df['last_price'] - df['first_price']) / df['first_price'] * 100).round(2)
        df['volatility_pct'] = ((df['max_price'] - df['min_price']) / df['min_price'] * 100).round(2)
        df['net_position_cr'] = df['buy_value_cr'] - df['sell_value_cr']
        
        # Classify performance
        df['performance'] = pd.cut(df['price_change_pct'],
                                   bins=[-float('inf'), -10, 0, 10, float('inf')],
                                   labels=['SHARP_FALL', 'DECLINE', 'RISE', 'SHARP_RISE'])
        
        return df.sort_values('price_change_pct', ascending=False)
    
    # ============================================================================
    # 6. SECTOR-WISE ANALYSIS
    # ============================================================================
    
    def analyze_sector_trends(self, days: int = 90) -> pd.DataFrame:
        """
        Analyze deal patterns across sectors
        Identify which sectors are seeing accumulation/distribution
        """
        # Note: This requires sector mapping - simplified version here
        cutoff_date = (datetime.now() - timedelta(days=days)).date()
        
        query = text("""
            SELECT 
                LEFT(symbol, 
                    CASE 
                        WHEN symbol LIKE '%BANK%' THEN LENGTH('BANK')
                        WHEN symbol LIKE '%IT%' THEN LENGTH('IT')
                        WHEN symbol LIKE '%PHARMA%' THEN LENGTH('PHARMA')
                        ELSE 3
                    END
                ) as sector_hint,
                COUNT(DISTINCT symbol) as symbols_count,
                COUNT(*) as total_deals,
                SUM(CASE WHEN deal_type = 'BUY' THEN quantity * trade_price ELSE 0 END) / 10000000 as buy_value_cr,
                SUM(CASE WHEN deal_type = 'SELL' THEN quantity * trade_price ELSE 0 END) / 10000000 as sell_value_cr,
                COUNT(DISTINCT client_name) as unique_clients
            FROM (
                SELECT symbol, deal_type, quantity, trade_price, client_name
                FROM nse_block_deals WHERE trade_date >= :cutoff
                UNION ALL
                SELECT symbol, deal_type, quantity, trade_price, client_name
                FROM nse_bulk_deals WHERE trade_date >= :cutoff
            ) combined
            GROUP BY sector_hint
            HAVING total_deals >= 10
            ORDER BY total_deals DESC
        """)
        
        df = pd.read_sql(query, self.engine, params={'cutoff': cutoff_date})
        
        df['net_value_cr'] = df['buy_value_cr'] - df['sell_value_cr']
        df['sector_sentiment'] = np.where(df['net_value_cr'] > 0, 'POSITIVE', 'NEGATIVE')
        
        return df
    
    # ============================================================================
    # 7. CLIENT CONCENTRATION RISK
    # ============================================================================
    
    def analyze_client_concentration(self, symbol: str = None) -> pd.DataFrame:
        """
        Analyze concentration risk - is single client driving deals?
        High concentration = higher risk
        """
        if symbol:
            query = text("""
                SELECT 
                    client_name,
                    COUNT(*) as deals,
                    SUM(quantity) as total_qty,
                    SUM(quantity * trade_price) / 10000000 as value_cr,
                    SUM(CASE WHEN deal_type = 'BUY' THEN 1 ELSE 0 END) as buy_count,
                    SUM(CASE WHEN deal_type = 'SELL' THEN 1 ELSE 0 END) as sell_count
                FROM (
                    SELECT client_name, deal_type, quantity, trade_price
                    FROM nse_block_deals WHERE symbol = :symbol
                    UNION ALL
                    SELECT client_name, deal_type, quantity, trade_price
                    FROM nse_bulk_deals WHERE symbol = :symbol
                ) combined
                GROUP BY client_name
                ORDER BY value_cr DESC
            """)
            
            df = pd.read_sql(query, self.engine, params={'symbol': symbol})
        else:
            query = text("""
                SELECT 
                    symbol,
                    security_name,
                    COUNT(DISTINCT client_name) as unique_clients,
                    COUNT(*) as total_deals,
                    MAX(client_deals) as max_deals_by_single_client,
                    MAX(client_deals) * 100.0 / COUNT(*) as concentration_pct
                FROM (
                    SELECT 
                        symbol,
                        security_name,
                        client_name,
                        COUNT(*) as client_deals
                    FROM (
                        SELECT symbol, security_name, client_name
                        FROM nse_block_deals
                        UNION ALL
                        SELECT symbol, security_name, client_name
                        FROM nse_bulk_deals
                    ) all_deals
                    GROUP BY symbol, security_name, client_name
                ) client_stats
                GROUP BY symbol, security_name
                HAVING total_deals >= 5
                ORDER BY concentration_pct DESC
            """)
            
            df = pd.read_sql(query, self.engine)
        
        return df
    
    # ============================================================================
    # 8. TIMING ANALYSIS
    # ============================================================================
    
    def analyze_deal_timing(self, days: int = 90) -> pd.DataFrame:
        """
        Analyze when deals are happening - beginning/end of month, week patterns
        """
        cutoff_date = (datetime.now() - timedelta(days=days)).date()
        
        query = text("""
            SELECT 
                DAYNAME(trade_date) as day_of_week,
                DAY(trade_date) as day_of_month,
                COUNT(*) as deals,
                SUM(quantity * trade_price) / 10000000 as value_cr,
                COUNT(DISTINCT symbol) as unique_symbols
            FROM (
                SELECT trade_date, quantity, trade_price, symbol
                FROM nse_block_deals WHERE trade_date >= :cutoff
                UNION ALL
                SELECT trade_date, quantity, trade_price, symbol
                FROM nse_bulk_deals WHERE trade_date >= :cutoff
            ) combined
            GROUP BY day_of_week, day_of_month
            ORDER BY deals DESC
        """)
        
        df = pd.read_sql(query, self.engine, params={'cutoff': cutoff_date})
        
        return df
    
    # ============================================================================
    # 9. COMPREHENSIVE STOCK REPORT
    # ============================================================================
    
    def generate_stock_report(self, symbol: str, days: int = 180) -> Dict:
        """
        Generate comprehensive report for a single stock
        All deals, patterns, clients, price correlation
        """
        cutoff_date = (datetime.now() - timedelta(days=days)).date()
        
        report = {
            'symbol': symbol,
            'analysis_date': datetime.now().strftime('%Y-%m-%d'),
            'period_days': days
        }
        
        # All deals
        query_deals = text("""
            SELECT * FROM (
                SELECT 'BLOCK' as deal_category, trade_date, client_name, deal_type, 
                       quantity, trade_price, quantity * trade_price / 10000000 as value_cr
                FROM nse_block_deals WHERE symbol = :symbol AND trade_date >= :cutoff
                UNION ALL
                SELECT 'BULK' as deal_category, trade_date, client_name, deal_type,
                       quantity, trade_price, quantity * trade_price / 10000000 as value_cr
                FROM nse_bulk_deals WHERE symbol = :symbol AND trade_date >= :cutoff
            ) combined
            ORDER BY trade_date DESC
        """)
        report['all_deals'] = pd.read_sql(query_deals, self.engine, 
                                          params={'symbol': symbol, 'cutoff': cutoff_date})
        
        # Summary stats
        if not report['all_deals'].empty:
            df = report['all_deals']
            report['total_deals'] = len(df)
            report['buy_deals'] = len(df[df['deal_type'] == 'BUY'])
            report['sell_deals'] = len(df[df['deal_type'] == 'SELL'])
            report['unique_clients'] = df['client_name'].nunique()
            report['total_value_cr'] = df['value_cr'].sum()
            report['buy_value_cr'] = df[df['deal_type'] == 'BUY']['value_cr'].sum()
            report['sell_value_cr'] = df[df['deal_type'] == 'SELL']['value_cr'].sum()
            report['net_position_cr'] = report['buy_value_cr'] - report['sell_value_cr']
            
            # Top clients
            report['top_buyers'] = df[df['deal_type'] == 'BUY'].groupby('client_name')['value_cr'].sum().sort_values(ascending=False).head(5)
            report['top_sellers'] = df[df['deal_type'] == 'SELL'].groupby('client_name')['value_cr'].sum().sort_values(ascending=False).head(5)
        
        return report


if __name__ == '__main__':
    analyzer = BlockBulkDealsAnalyzer()
    
    print("=" * 80)
    print("BLOCK & BULK DEALS ANALYSIS ENGINE")
    print("=" * 80)
    
    # Test accumulation analysis
    print("\n1. TOP 10 ACCUMULATION STOCKS (Last 90 days):")
    df_accum = analyzer.analyze_accumulation_distribution(days=90)
    print(df_accum[['symbol', 'security_name', 'total_deals', 'buy_sell_ratio', 
                    'accumulation_score', 'signal']].head(10).to_string(index=False))
    
    # Test repeated buying
    print("\n2. REPEATED BUYING PATTERNS:")
    df_repeat = analyzer.find_repeated_buying(min_buys=3, days=90)
    print(df_repeat[['symbol', 'client_name', 'buy_count', 'total_value_cr', 
                     'buying_frequency']].head(10).to_string(index=False))
    
    # Test unusual activity
    print("\n3. UNUSUAL ACTIVITY (Last 7 days vs baseline):")
    df_spike = analyzer.detect_unusual_activity(lookback_days=90, spike_days=7)
    if not df_spike.empty:
        print(df_spike[['symbol', 'recent_deals', 'deal_spike_ratio', 
                        'value_spike_ratio']].head(10).to_string(index=False))
    else:
        print("No unusual activity detected")
    
    print("\n" + "=" * 80)
    print("Analysis engine ready for PDF report generation!")
