"""
Real-Time Advance-Decline Calculator
=====================================

Calculates intraday advance/decline breadth metrics from real-time price data.
Maintains in-memory cache of stock statuses.
"""

from datetime import datetime
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)


class StockStatus:
    """Represents the current status of a single stock"""
    
    def __init__(self, symbol: str, ltp: float, prev_close: float, 
                 timestamp: datetime, volume: int = 0):
        self.symbol = symbol
        self.ltp = ltp
        self.prev_close = prev_close
        self.timestamp = timestamp
        self.volume = volume
        
        # Calculate change
        self.change = ltp - prev_close
        self.change_pct = (self.change / prev_close * 100) if prev_close > 0 else 0
        
        # Determine status
        if self.change > 0:
            self.status = 'ADVANCE'
        elif self.change < 0:
            self.status = 'DECLINE'
        else:
            self.status = 'UNCHANGED'
    
    def __repr__(self):
        return (f"StockStatus({self.symbol}, ltp={self.ltp:.2f}, "
                f"prev={self.prev_close:.2f}, status={self.status})")


class IntradayAdvDeclCalculator:
    """Calculate real-time advance-decline metrics"""
    
    def __init__(self):
        """Initialize calculator with empty cache"""
        self.stocks = {}  # symbol -> StockStatus
        self.last_update = None
        self.update_count = 0
    
    def update_stock(self, symbol: str, ltp: float, prev_close: float, 
                     timestamp: datetime, volume: int = 0) -> StockStatus:
        """
        Update a single stock's data
        
        Args:
            symbol: Stock symbol
            ltp: Last traded price
            prev_close: Previous day's close
            timestamp: Time of price update
            volume: Trading volume
            
        Returns:
            StockStatus object
        """
        status = StockStatus(symbol, ltp, prev_close, timestamp, volume)
        self.stocks[symbol] = status
        self.last_update = datetime.now()
        self.update_count += 1
        
        logger.debug(f"Updated {symbol}: {status.status} ({status.change_pct:+.2f}%)")
        
        return status
    
    def update_batch(self, data: Dict[str, Dict]) -> int:
        """
        Update multiple stocks from fetcher data
        
        Args:
            data: Dict from RealTimeDataFetcher with symbol -> {ltp, prev_close, ...}
            
        Returns:
            Number of stocks updated
        """
        updated = 0
        
        for symbol, info in data.items():
            ltp = info.get('ltp')
            prev_close = info.get('prev_close')
            timestamp = info.get('timestamp', datetime.now())
            volume = info.get('volume', 0)
            
            # Only update if we have required data
            if ltp is not None and prev_close is not None:
                self.update_stock(symbol, ltp, prev_close, timestamp, volume)
                updated += 1
            else:
                logger.warning(f"Skipping {symbol}: incomplete data (ltp={ltp}, prev_close={prev_close})")
        
        logger.info(f"Updated {updated}/{len(data)} stocks")
        
        return updated
    
    def calculate_breadth(self) -> Dict:
        """
        Calculate advance-decline breadth metrics
        
        Returns:
            Dict with counts, percentages, ratios, etc.
        """
        if not self.stocks:
            return {
                'total_stocks': 0,
                'advances': 0,
                'declines': 0,
                'unchanged': 0,
                'adv_pct': 0.0,
                'decl_pct': 0.0,
                'unch_pct': 0.0,
                'adv_decl_ratio': 0.0,
                'adv_decl_diff': 0,
                'last_update': None,
                'update_count': self.update_count
            }
        
        # Count statuses
        advances = sum(1 for s in self.stocks.values() if s.status == 'ADVANCE')
        declines = sum(1 for s in self.stocks.values() if s.status == 'DECLINE')
        unchanged = sum(1 for s in self.stocks.values() if s.status == 'UNCHANGED')
        total = len(self.stocks)
        
        # Calculate percentages
        adv_pct = (advances / total * 100) if total > 0 else 0
        decl_pct = (declines / total * 100) if total > 0 else 0
        unch_pct = (unchanged / total * 100) if total > 0 else 0
        
        # Calculate ratio
        adv_decl_ratio = (advances / declines) if declines > 0 else float('inf') if advances > 0 else 0
        
        # Calculate difference
        adv_decl_diff = advances - declines
        
        return {
            'total_stocks': total,
            'advances': advances,
            'declines': declines,
            'unchanged': unchanged,
            'adv_pct': round(adv_pct, 2),
            'decl_pct': round(decl_pct, 2),
            'unch_pct': round(unch_pct, 2),
            'adv_decl_ratio': round(adv_decl_ratio, 2) if adv_decl_ratio != float('inf') else None,
            'adv_decl_diff': adv_decl_diff,
            'last_update': self.last_update,
            'update_count': self.update_count,
            'market_sentiment': self._get_sentiment(adv_pct)
        }
    
    def _get_sentiment(self, adv_pct: float) -> str:
        """
        Determine market sentiment based on advance percentage
        
        Args:
            adv_pct: Percentage of advancing stocks
            
        Returns:
            Sentiment string
        """
        if adv_pct >= 70:
            return "STRONG BULLISH"
        elif adv_pct >= 60:
            return "BULLISH"
        elif adv_pct >= 55:
            return "SLIGHTLY BULLISH"
        elif adv_pct >= 45:
            return "NEUTRAL"
        elif adv_pct >= 40:
            return "SLIGHTLY BEARISH"
        elif adv_pct >= 30:
            return "BEARISH"
        else:
            return "STRONG BEARISH"
    
    def get_stock_status(self, symbol: str) -> Optional[StockStatus]:
        """
        Get status for a specific stock
        
        Args:
            symbol: Stock symbol
            
        Returns:
            StockStatus object or None if not found
        """
        return self.stocks.get(symbol)
    
    def get_top_gainers(self, n: int = 10) -> List[StockStatus]:
        """
        Get top N gainers by percentage change
        
        Args:
            n: Number of stocks to return
            
        Returns:
            List of StockStatus objects
        """
        gainers = [s for s in self.stocks.values() if s.status == 'ADVANCE']
        return sorted(gainers, key=lambda s: s.change_pct, reverse=True)[:n]
    
    def get_top_losers(self, n: int = 10) -> List[StockStatus]:
        """
        Get top N losers by percentage change
        
        Args:
            n: Number of stocks to return
            
        Returns:
            List of StockStatus objects
        """
        losers = [s for s in self.stocks.values() if s.status == 'DECLINE']
        return sorted(losers, key=lambda s: s.change_pct)[:n]
    
    def get_most_active(self, n: int = 10) -> List[StockStatus]:
        """
        Get most active stocks by volume
        
        Args:
            n: Number of stocks to return
            
        Returns:
            List of StockStatus objects
        """
        return sorted(self.stocks.values(), key=lambda s: s.volume, reverse=True)[:n]
    
    def clear_cache(self):
        """Clear all cached stock data"""
        self.stocks.clear()
        logger.info("Cache cleared")
    
    def get_cache_info(self) -> Dict:
        """
        Get information about the cache
        
        Returns:
            Dict with cache statistics
        """
        if not self.stocks:
            return {
                'size': 0,
                'last_update': None,
                'update_count': self.update_count
            }
        
        timestamps = [s.timestamp for s in self.stocks.values()]
        
        return {
            'size': len(self.stocks),
            'last_update': self.last_update,
            'update_count': self.update_count,
            'oldest_data': min(timestamps) if timestamps else None,
            'newest_data': max(timestamps) if timestamps else None
        }


if __name__ == "__main__":
    # Test the calculator
    import logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    print("=" * 70)
    print("Real-Time Advance-Decline Calculator - Test")
    print("=" * 70)
    
    # Create calculator
    calc = IntradayAdvDeclCalculator()
    
    # Simulate some stock updates
    test_data = {
        'RELIANCE.NS': {'ltp': 2850.50, 'prev_close': 2840.00, 'timestamp': datetime.now(), 'volume': 1500000},
        'TCS.NS': {'ltp': 3450.25, 'prev_close': 3465.00, 'timestamp': datetime.now(), 'volume': 800000},
        'INFY.NS': {'ltp': 1625.75, 'prev_close': 1620.50, 'timestamp': datetime.now(), 'volume': 1200000},
        'HDFCBANK.NS': {'ltp': 1685.00, 'prev_close': 1690.25, 'timestamp': datetime.now(), 'volume': 900000},
        'ICICIBANK.NS': {'ltp': 1150.50, 'prev_close': 1145.00, 'timestamp': datetime.now(), 'volume': 2000000},
        'SBIN.NS': {'ltp': 785.25, 'prev_close': 790.00, 'timestamp': datetime.now(), 'volume': 3000000},
        'ITC.NS': {'ltp': 425.50, 'prev_close': 425.50, 'timestamp': datetime.now(), 'volume': 500000},
        'BHARTIARTL.NS': {'ltp': 1580.00, 'prev_close': 1575.75, 'timestamp': datetime.now(), 'volume': 700000},
    }
    
    print(f"\nUpdating {len(test_data)} stocks...")
    updated = calc.update_batch(test_data)
    print(f"✅ Updated {updated} stocks\n")
    
    # Calculate breadth
    breadth = calc.calculate_breadth()
    
    print("=" * 70)
    print("Market Breadth Summary:")
    print("=" * 70)
    print(f"Total Stocks: {breadth['total_stocks']}")
    print(f"Advances: {breadth['advances']} ({breadth['adv_pct']:.2f}%)")
    print(f"Declines: {breadth['declines']} ({breadth['decl_pct']:.2f}%)")
    print(f"Unchanged: {breadth['unchanged']} ({breadth['unch_pct']:.2f}%)")
    print(f"A/D Ratio: {breadth['adv_decl_ratio']}")
    print(f"A/D Difference: {breadth['adv_decl_diff']:+d}")
    print(f"Market Sentiment: {breadth['market_sentiment']}")
    print(f"Last Update: {breadth['last_update'].strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Show top gainers
    print("\n" + "=" * 70)
    print("Top Gainers:")
    print("=" * 70)
    for stock in calc.get_top_gainers(3):
        print(f"{stock.symbol}: ₹{stock.ltp:.2f} ({stock.change_pct:+.2f}%)")
    
    # Show top losers
    print("\n" + "=" * 70)
    print("Top Losers:")
    print("=" * 70)
    for stock in calc.get_top_losers(3):
        print(f"{stock.symbol}: ₹{stock.ltp:.2f} ({stock.change_pct:+.2f}%)")
    
    # Show most active
    print("\n" + "=" * 70)
    print("Most Active (by volume):")
    print("=" * 70)
    for stock in calc.get_most_active(3):
        print(f"{stock.symbol}: {stock.volume:,} shares")
    
    # Cache info
    print("\n" + "=" * 70)
    print("Cache Info:")
    print("=" * 70)
    cache_info = calc.get_cache_info()
    for key, value in cache_info.items():
        print(f"{key}: {value}")
    
    print("\n" + "=" * 70)
