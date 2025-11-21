"""
Yahoo Finance API client for downloading stock market data
"""

import yfinance as yf
import pandas as pd
from datetime import datetime, date, timedelta
from typing import List, Optional, Dict, Any
import time
import logging
from decimal import Decimal
import sys
import os

# Add current directory to path for local imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config import YFinanceConfig
from models import DailyQuote

# Setup logging
logging.basicConfig(level=YFinanceConfig.LOG_LEVEL)
logger = logging.getLogger(__name__)

class YahooFinanceClient:
    """Client for Yahoo Finance API operations"""
    
    def __init__(self):
        self.config = YFinanceConfig()
        self.symbol_mapping = self.config.get_symbol_mapping()
    
    def get_yahoo_symbol(self, symbol: str) -> str:
        """Convert our symbol to Yahoo Finance symbol"""
        return self.symbol_mapping.get(symbol, symbol)
    
    def download_daily_data(self, symbol: str, start_date: date, end_date: date) -> List[DailyQuote]:
        """
        Download daily data for a symbol from Yahoo Finance
        
        Args:
            symbol: Stock symbol (e.g., 'NIFTY')
            start_date: Start date for data
            end_date: End date for data
            
        Returns:
            List of DailyQuote objects
        """
        yahoo_symbol = self.get_yahoo_symbol(symbol)
        quotes = []
        
        try:
            logger.info(f"Downloading data for {symbol} ({yahoo_symbol}) from {start_date} to {end_date}")
            
            # Create ticker object
            ticker = yf.Ticker(yahoo_symbol)
            
            # Download data with retries
            data = self._download_with_retry(ticker, start_date, end_date)
            
            if data.empty:
                logger.warning(f"No data returned for {yahoo_symbol}")
                return quotes
            
            # Convert to our data model
            for date_idx, row in data.iterrows():
                try:
                    quote_date = date_idx.date() if hasattr(date_idx, 'date') else date_idx
                    
                    quote = DailyQuote(
                        symbol=symbol,
                        date=quote_date,
                        open=self._safe_decimal(row.get('Open')),
                        high=self._safe_decimal(row.get('High')),
                        low=self._safe_decimal(row.get('Low')),
                        close=self._safe_decimal(row.get('Close')),
                        volume=self._safe_int(row.get('Volume')),
                        adj_close=self._safe_decimal(row.get('Adj Close')),
                        timeframe='Daily'
                    )
                    
                    quotes.append(quote)
                    
                except Exception as e:
                    logger.error(f"Error processing quote for {quote_date}: {e}")
                    continue
            
            logger.info(f"Successfully downloaded {len(quotes)} quotes for {symbol}")
            return quotes
            
        except Exception as e:
            logger.error(f"Error downloading data for {symbol}: {e}")
            raise
    
    def _download_with_retry(self, ticker, start_date: date, end_date: date) -> pd.DataFrame:
        """Download data with retry logic"""
        for attempt in range(self.config.MAX_RETRIES):
            try:
                data = ticker.history(
                    start=start_date,
                    end=end_date + timedelta(days=1),  # Include end date
                    interval="1d",
                    auto_adjust=False,
                    prepost=False
                )
                return data
                
            except Exception as e:
                logger.warning(f"Download attempt {attempt + 1} failed: {e}")
                if attempt < self.config.MAX_RETRIES - 1:
                    time.sleep(self.config.RETRY_DELAY * (attempt + 1))
                else:
                    raise
    
    def _safe_decimal(self, value: Any) -> Optional[Decimal]:
        """Safely convert value to Decimal"""
        if pd.isna(value) or value is None:
            return None
        try:
            return Decimal(str(float(value)))
        except (ValueError, TypeError):
            return None
    
    def _safe_int(self, value: Any) -> Optional[int]:
        """Safely convert value to int"""
        if pd.isna(value) or value is None:
            return None
        try:
            return int(float(value))
        except (ValueError, TypeError):
            return None
    
    def get_latest_quote(self, symbol: str) -> Optional[DailyQuote]:
        """Get the latest quote for a symbol"""
        try:
            end_date = date.today()
            start_date = end_date - timedelta(days=7)  # Get last week's data
            
            quotes = self.download_daily_data(symbol, start_date, end_date)
            
            if quotes:
                return max(quotes, key=lambda x: x.date)
            
        except Exception as e:
            logger.error(f"Error getting latest quote for {symbol}: {e}")
        
        return None
    
    def validate_symbol(self, symbol: str) -> bool:
        """Validate if symbol exists and has data"""
        try:
            yahoo_symbol = self.get_yahoo_symbol(symbol)
            ticker = yf.Ticker(yahoo_symbol)
            
            # Try to get recent data
            data = ticker.history(period="5d")
            return not data.empty
            
        except Exception as e:
            logger.error(f"Error validating symbol {symbol}: {e}")
            return False
    
    def get_symbol_info(self, symbol: str) -> Dict[str, Any]:
        """Get basic information about a symbol"""
        try:
            yahoo_symbol = self.get_yahoo_symbol(symbol)
            ticker = yf.Ticker(yahoo_symbol)
            
            info = ticker.info
            return {
                'symbol': symbol,
                'yahoo_symbol': yahoo_symbol,
                'name': info.get('shortName', info.get('longName', symbol)),
                'currency': info.get('currency', 'INR'),
                'market': info.get('exchange', 'NSE'),
                'sector': info.get('sector', ''),
                'industry': info.get('industry', ''),
                'market_cap': info.get('marketCap')
            }
            
        except Exception as e:
            logger.error(f"Error getting symbol info for {symbol}: {e}")
            return {
                'symbol': symbol,
                'yahoo_symbol': self.get_yahoo_symbol(symbol),
                'name': symbol,
                'currency': 'INR',
                'market': 'NSE'
            }