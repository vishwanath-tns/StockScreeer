"""
Market Hours Monitor
====================

Detects if NSE market is currently open.
Handles timezone (IST) and market holidays.
"""

from datetime import datetime, time, date
import pytz
import logging

logger = logging.getLogger(__name__)

# NSE market hours
MARKET_OPEN_TIME = time(9, 15)   # 9:15 AM IST
MARKET_CLOSE_TIME = time(15, 30)  # 3:30 PM IST

# NSE holidays 2025 (update annually)
NSE_HOLIDAYS_2025 = [
    date(2025, 1, 26),   # Republic Day
    date(2025, 3, 14),   # Holi
    date(2025, 3, 31),   # Id-Ul-Fitr
    date(2025, 4, 10),   # Mahavir Jayanti
    date(2025, 4, 14),   # Dr. Ambedkar Jayanti
    date(2025, 4, 18),   # Good Friday
    date(2025, 5, 1),    # Maharashtra Day
    date(2025, 8, 15),   # Independence Day
    date(2025, 8, 27),   # Ganesh Chaturthi
    date(2025, 10, 2),   # Gandhi Jayanti
    date(2025, 10, 21),  # Dussehra
    date(2025, 11, 1),   # Diwali - Laxmi Pujan
    date(2025, 11, 5),   # Guru Nanak Jayanti
    date(2025, 12, 25),  # Christmas
]


class MarketHoursMonitor:
    """Monitor NSE market hours and detect if market is open"""
    
    def __init__(self, timezone='Asia/Kolkata'):
        self.timezone = pytz.timezone(timezone)
        self.market_open = MARKET_OPEN_TIME
        self.market_close = MARKET_CLOSE_TIME
        self.holidays = NSE_HOLIDAYS_2025
        
    def get_current_time(self):
        """Get current time in IST"""
        return datetime.now(self.timezone)
    
    def is_weekend(self, dt=None):
        """Check if given date is weekend"""
        if dt is None:
            dt = self.get_current_time()
        return dt.weekday() >= 5  # Saturday=5, Sunday=6
    
    def is_holiday(self, dt=None):
        """Check if given date is NSE holiday"""
        if dt is None:
            dt = self.get_current_time()
        return dt.date() in self.holidays
    
    def is_trading_day(self, dt=None):
        """Check if given date is a trading day"""
        if dt is None:
            dt = self.get_current_time()
        return not (self.is_weekend(dt) or self.is_holiday(dt))
    
    def is_market_hours(self, dt=None):
        """Check if current time is within market hours"""
        if dt is None:
            dt = self.get_current_time()
        
        current_time = dt.time()
        return self.market_open <= current_time <= self.market_close
    
    def is_market_open(self, dt=None):
        """
        Check if market is currently open
        
        Returns:
            bool: True if market is open, False otherwise
        """
        if dt is None:
            dt = self.get_current_time()
        
        if not self.is_trading_day(dt):
            logger.debug(f"Not a trading day: {dt.date()}")
            return False
        
        if not self.is_market_hours(dt):
            logger.debug(f"Outside market hours: {dt.time()}")
            return False
        
        logger.debug(f"Market is OPEN at {dt}")
        return True
    
    def time_to_market_open(self, dt=None):
        """
        Calculate time remaining until market opens
        
        Returns:
            timedelta or None if market is open or already closed today
        """
        if dt is None:
            dt = self.get_current_time()
        
        if self.is_market_open(dt):
            return None  # Market already open
        
        # If after market close, return time to next trading day
        if dt.time() > self.market_close:
            # Find next trading day
            next_day = dt + timedelta(days=1)
            while not self.is_trading_day(next_day):
                next_day += timedelta(days=1)
            
            market_open_datetime = datetime.combine(
                next_day.date(), 
                self.market_open
            )
            market_open_datetime = self.timezone.localize(market_open_datetime)
            return market_open_datetime - dt
        
        # Before market open today
        if self.is_trading_day(dt):
            market_open_datetime = datetime.combine(
                dt.date(), 
                self.market_open
            )
            market_open_datetime = self.timezone.localize(market_open_datetime)
            return market_open_datetime - dt
        
        # Not a trading day, find next trading day
        next_day = dt + timedelta(days=1)
        while not self.is_trading_day(next_day):
            next_day += timedelta(days=1)
        
        market_open_datetime = datetime.combine(
            next_day.date(), 
            self.market_open
        )
        market_open_datetime = self.timezone.localize(market_open_datetime)
        return market_open_datetime - dt
    
    def time_to_market_close(self, dt=None):
        """
        Calculate time remaining until market closes
        
        Returns:
            timedelta or None if market is closed
        """
        if dt is None:
            dt = self.get_current_time()
        
        if not self.is_market_open(dt):
            return None  # Market not open
        
        market_close_datetime = datetime.combine(
            dt.date(), 
            self.market_close
        )
        market_close_datetime = self.timezone.localize(market_close_datetime)
        return market_close_datetime - dt
    
    def get_market_status(self):
        """
        Get comprehensive market status
        
        Returns:
            dict: Market status information
        """
        dt = self.get_current_time()
        is_open = self.is_market_open(dt)
        
        status = {
            'timestamp': dt,
            'is_open': is_open,
            'is_trading_day': self.is_trading_day(dt),
            'is_weekend': self.is_weekend(dt),
            'is_holiday': self.is_holiday(dt),
            'current_time': dt.time(),
            'market_open_time': self.market_open,
            'market_close_time': self.market_close,
        }
        
        if is_open:
            status['time_to_close'] = self.time_to_market_close(dt)
            status['status_text'] = 'MARKET OPEN'
        else:
            status['time_to_open'] = self.time_to_market_open(dt)
            if dt.time() > self.market_close:
                status['status_text'] = 'MARKET CLOSED (after hours)'
            elif dt.time() < self.market_open:
                status['status_text'] = 'MARKET CLOSED (before open)'
            else:
                status['status_text'] = 'MARKET CLOSED (holiday/weekend)'
        
        return status


# Convenience functions
_monitor = MarketHoursMonitor()

def is_market_open():
    """Quick check if market is currently open"""
    return _monitor.is_market_open()

def get_market_status():
    """Get current market status"""
    return _monitor.get_market_status()


if __name__ == "__main__":
    # Test the monitor
    import logging
    logging.basicConfig(level=logging.DEBUG)
    
    from datetime import timedelta
    
    monitor = MarketHoursMonitor()
    
    print("=" * 60)
    print("NSE Market Hours Monitor - Test")
    print("=" * 60)
    
    status = monitor.get_market_status()
    
    print(f"\nCurrent Time (IST): {status['timestamp'].strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Day of Week: {status['timestamp'].strftime('%A')}")
    print(f"\nMarket Status: {status['status_text']}")
    print(f"Is Trading Day: {status['is_trading_day']}")
    print(f"Is Weekend: {status['is_weekend']}")
    print(f"Is Holiday: {status['is_holiday']}")
    print(f"\nMarket Hours: {status['market_open_time']} - {status['market_close_time']}")
    
    if status['is_open']:
        print(f"\n✅ Market is OPEN")
        print(f"Time to close: {status['time_to_close']}")
    else:
        print(f"\n❌ Market is CLOSED")
        if 'time_to_open' in status:
            print(f"Time to open: {status['time_to_open']}")
    
    print("\n" + "=" * 60)
    print("Testing various times:")
    print("=" * 60)
    
    # Test different times
    test_times = [
        (9, 0),   # Before open
        (9, 15),  # Market open
        (12, 0),  # Mid-day
        (15, 30), # Market close
        (16, 0),  # After close
    ]
    
    today = monitor.get_current_time().date()
    for hour, minute in test_times:
        test_dt = datetime.combine(today, time(hour, minute))
        test_dt = monitor.timezone.localize(test_dt)
        
        is_open = monitor.is_market_open(test_dt)
        status_icon = "✅" if is_open else "❌"
        print(f"{status_icon} {test_dt.time()}: {'OPEN' if is_open else 'CLOSED'}")
