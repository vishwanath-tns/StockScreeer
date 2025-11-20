"""
Momentum Calculator Service
==========================

High-performance service for calculating stock momentum across multiple time durations.
Calculates percentage gains/losses and stores results in database for efficient retrieval.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import pandas as pd
import numpy as np
from datetime import date, timedelta, datetime
from typing import Dict, List, Optional, Tuple, Union
from dataclasses import dataclass
from enum import Enum
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
import uuid
from tqdm import tqdm

from volatility_patterns.data.data_service import DataService
from services.momentum.database_service import DatabaseService

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MomentumDuration(Enum):
    """Supported momentum duration types"""
    ONE_WEEK = "1W"
    ONE_MONTH = "1M"
    THREE_MONTHS = "3M"
    SIX_MONTHS = "6M"
    NINE_MONTHS = "9M"
    TWELVE_MONTHS = "12M"
    
    @property
    def days(self) -> int:
        """Get the number of days for the duration"""
        duration_days = {
            "1W": 7,
            "1M": 30,
            "3M": 90,
            "6M": 180,
            "9M": 270,
            "12M": 365
        }
        return duration_days[self.value]
    
    @property
    def description(self) -> str:
        """Get human-readable description"""
        descriptions = {
            "1W": "1 Week",
            "1M": "1 Month", 
            "3M": "3 Months",
            "6M": "6 Months",
            "9M": "9 Months",
            "12M": "12 Months"
        }
        return descriptions[self.value]

@dataclass
class MomentumResult:
    """Result of momentum calculation for a stock"""
    symbol: str
    series: str
    duration_type: str
    duration_days: int
    start_date: date
    end_date: date
    start_price: float
    end_price: float
    high_price: float
    low_price: float
    absolute_change: float
    percentage_change: float
    avg_volume: int
    total_volume: int
    volume_surge_factor: float
    price_volatility: float
    high_low_ratio: float
    trading_days: int
    calculation_date: date
    
    @property
    def is_positive(self) -> bool:
        """Check if momentum is positive"""
        return self.percentage_change > 0
    
    @property
    def momentum_strength(self) -> str:
        """Classify momentum strength"""
        pct = abs(self.percentage_change)
        if pct >= 50:
            return "Extreme"
        elif pct >= 25:
            return "Very Strong"
        elif pct >= 15:
            return "Strong"
        elif pct >= 10:
            return "Moderate"
        elif pct >= 5:
            return "Weak"
        else:
            return "Minimal"

class MomentumCalculator:
    """High-performance momentum calculator with database persistence"""
    
    def __init__(self, data_service: DataService = None, db_service: DatabaseService = None):
        self.data_service = data_service or DataService()
        self.db_service = db_service or DatabaseService()
        self.supported_durations = list(MomentumDuration)
        
    def calculate_momentum_batch(
        self, 
        symbols: List[str], 
        durations: List[MomentumDuration],
        end_date: date = None,
        batch_size: int = 10,
        max_workers: int = 4
    ) -> Dict[str, List[MomentumResult]]:
        """
        Calculate momentum for multiple symbols and durations efficiently
        
        Args:
            symbols: List of stock symbols
            durations: List of momentum durations to calculate
            end_date: End date for calculations (default: today)
            batch_size: Number of symbols to process in each batch
            max_workers: Number of threads for parallel processing
            
        Returns:
            Dictionary mapping symbols to their momentum results
        """
        if end_date is None:
            end_date = date.today()
            
        # Create job tracking
        job_id = str(uuid.uuid4())
        logger.info(f"[*] Starting momentum calculation batch {job_id}")
        logger.info(f"[*] Symbols: {len(symbols)}, Durations: {len(durations)}")
        
        results = {}
        total_combinations = len(symbols) * len(durations)
        completed_combinations = 0
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all symbol-duration combinations
            future_to_params = {}
            
            for symbol in symbols:
                for duration in durations:
                    future = executor.submit(
                        self._calculate_single_momentum, 
                        symbol, duration, end_date
                    )
                    future_to_params[future] = (symbol, duration)
            
            # Process completed futures with progress bar
            with tqdm(total=total_combinations, desc="Calculating momentum") as pbar:
                for future in as_completed(future_to_params):
                    symbol, duration = future_to_params[future]
                    
                    try:
                        result = future.result()
                        if result:
                            if symbol not in results:
                                results[symbol] = []
                            results[symbol].append(result)
                            
                        completed_combinations += 1
                        pbar.update(1)
                        pbar.set_postfix(
                            symbol=symbol, 
                            duration=duration.value,
                            success=len(results)
                        )
                        
                    except Exception as e:
                        logger.error(f"[ERROR] Failed {symbol} {duration.value}: {e}")
                        completed_combinations += 1
                        pbar.update(1)
        
        logger.info(f"[OK] Momentum calculation complete: {len(results)}/{len(symbols)} symbols")
        return results
    
    def _calculate_single_momentum(
        self, 
        symbol: str, 
        duration: MomentumDuration, 
        end_date: date
    ) -> Optional[MomentumResult]:
        """Calculate momentum for a single symbol and duration"""
        
        try:
            # Calculate start date with buffer for trading days
            start_date = end_date - timedelta(days=duration.days + 30)
            
            # Get price data
            data = self.data_service.get_ohlcv_data(symbol, start_date, end_date)
            
            if data is None or len(data) < 2:
                logger.warning(f"[WARNING] Insufficient data for {symbol} {duration.value}")
                return None
            
            # Filter trading days and ensure data quality
            data = self._filter_trading_data(data)
            
            if len(data) < 2:
                logger.warning(f"[WARNING] Insufficient trading data for {symbol} {duration.value}")
                return None
            
            # Find the actual start date (closest to target duration)
            target_start_date = end_date - timedelta(days=duration.days)
            actual_start_idx = self._find_closest_date_index(data, target_start_date)
            actual_end_idx = len(data) - 1
            
            if actual_start_idx is None or actual_start_idx >= actual_end_idx:
                logger.warning(f"[WARNING] Cannot find valid date range for {symbol} {duration.value}")
                return None
            
            # Extract price points
            start_row = data.iloc[actual_start_idx]
            end_row = data.iloc[actual_end_idx]
            
            start_price = float(start_row['close'])
            end_price = float(end_row['close'])
            
            # Calculate price metrics for the duration period
            period_data = data.iloc[actual_start_idx:actual_end_idx + 1]
            high_price = float(period_data['high'].max())
            low_price = float(period_data['low'].min())
            
            # Calculate momentum metrics
            absolute_change = end_price - start_price
            percentage_change = (absolute_change / start_price) * 100
            
            # Volume metrics
            avg_volume = int(period_data['volume'].mean())
            total_volume = int(period_data['volume'].sum())
            
            # Volume surge factor (current vs historical average)
            if len(data) > len(period_data):
                historical_data = data.iloc[:actual_start_idx]
                if len(historical_data) > 0:
                    historical_avg_volume = historical_data['volume'].mean()
                    volume_surge_factor = avg_volume / historical_avg_volume if historical_avg_volume > 0 else 1.0
                else:
                    volume_surge_factor = 1.0
            else:
                volume_surge_factor = 1.0
            
            # Volatility metrics
            price_volatility = float(period_data['close'].pct_change().std() * np.sqrt(252) * 100)
            high_low_ratio = (high_price / low_price) if low_price > 0 else 1.0
            
            # Create result
            result = MomentumResult(
                symbol=symbol,
                series='EQ',  # Default series
                duration_type=duration.value,
                duration_days=duration.days,
                start_date=start_row['date'].date() if hasattr(start_row['date'], 'date') else start_row['date'],
                end_date=end_row['date'].date() if hasattr(end_row['date'], 'date') else end_row['date'],
                start_price=start_price,
                end_price=end_price,
                high_price=high_price,
                low_price=low_price,
                absolute_change=absolute_change,
                percentage_change=percentage_change,
                avg_volume=avg_volume,
                total_volume=total_volume,
                volume_surge_factor=volume_surge_factor,
                price_volatility=price_volatility if not pd.isna(price_volatility) else 0.0,
                high_low_ratio=high_low_ratio,
                trading_days=len(period_data),
                calculation_date=date.today()
            )
            
            return result
            
        except Exception as e:
            logger.error(f"[ERROR] Error calculating momentum for {symbol} {duration.value}: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def _filter_trading_data(self, data: pd.DataFrame) -> pd.DataFrame:
        """Filter and clean trading data"""
        if data is None or len(data) == 0:
            return data
        
        # Convert date column if needed
        if 'date' in data.columns:
            data['date'] = pd.to_datetime(data['date'])
        
        # Remove weekends
        data = data[data['date'].dt.dayofweek < 5].copy()
        
        # Remove rows with zero volume or invalid prices
        data = data[
            (data['volume'] > 0) & 
            (data['close'] > 0) & 
            (data['open'] > 0) &
            (data['high'] > 0) &
            (data['low'] > 0)
        ].copy()
        
        # Sort by date
        data = data.sort_values('date').reset_index(drop=True)
        
        return data
    
    def _find_closest_date_index(self, data: pd.DataFrame, target_date: date) -> Optional[int]:
        """Find the index of the closest available trading date"""
        if data is None or len(data) == 0:
            return None
            
        data['date'] = pd.to_datetime(data['date'])
        target_datetime = pd.to_datetime(target_date)
        
        # Find dates on or after target date
        valid_indices = data[data['date'] >= target_datetime].index
        
        if len(valid_indices) > 0:
            return valid_indices[0]
        
        # If no dates after target, return the last available date
        return len(data) - 1
    
    def store_momentum_results(self, results: Dict[str, List[MomentumResult]]) -> int:
        """
        Store momentum calculation results in database
        
        Args:
            results: Dictionary of momentum results by symbol
            
        Returns:
            Number of records stored
        """
        if not results:
            return 0
        
        # Flatten results into list
        all_results = []
        for symbol_results in results.values():
            all_results.extend(symbol_results)
        
        if not all_results:
            return 0
        
        logger.info(f"[SAVE] Storing {len(all_results)} momentum results to database")
        
        # Convert to DataFrame for bulk insert
        df_data = []
        for result in all_results:
            df_data.append({
                'symbol': result.symbol,
                'series': result.series,
                'duration_type': result.duration_type,
                'duration_days': result.duration_days,
                'start_date': result.start_date,
                'end_date': result.end_date,
                'calculation_date': result.calculation_date,
                'start_price': result.start_price,
                'end_price': result.end_price,
                'high_price': result.high_price,
                'low_price': result.low_price,
                'absolute_change': result.absolute_change,
                'percentage_change': result.percentage_change,
                'avg_volume': result.avg_volume,
                'total_volume': result.total_volume,
                'volume_surge_factor': result.volume_surge_factor,
                'price_volatility': result.price_volatility,
                'high_low_ratio': result.high_low_ratio,
                'trading_days': result.trading_days
            })
        
        df = pd.DataFrame(df_data)
        
        # Use replace to handle duplicates (ON DUPLICATE KEY UPDATE equivalent)
        try:
            stored_count = self.db_service.bulk_upsert_dataframe(
                df, 
                'momentum_analysis',
                unique_columns=['symbol', 'duration_type', 'end_date']
            )
            
            logger.info(f"[OK] Successfully stored {stored_count} momentum records")
            return stored_count
            
        except Exception as e:
            logger.error(f"[ERROR] Error storing momentum results: {e}")
            import traceback
            traceback.print_exc()
            return 0
    
    def get_symbol_momentum(
        self, 
        symbol: str, 
        durations: List[MomentumDuration] = None,
        calculation_date: date = None
    ) -> List[MomentumResult]:
        """
        Retrieve stored momentum data for a symbol
        
        Args:
            symbol: Stock symbol
            durations: List of durations to retrieve (default: all)
            calculation_date: Specific calculation date (default: latest)
            
        Returns:
            List of momentum results
        """
        if durations is None:
            durations = list(MomentumDuration)
        
        duration_values = [d.value for d in durations]
        
        query = """
        SELECT * FROM momentum_analysis 
        WHERE symbol = %s 
        AND duration_type IN ({})
        """.format(','.join(['%s'] * len(duration_values)))
        
        params = [symbol] + duration_values
        
        if calculation_date:
            query += " AND calculation_date = %s"
            params.append(calculation_date)
        else:
            query += " AND calculation_date = (SELECT MAX(calculation_date) FROM momentum_analysis WHERE symbol = %s)"
            params.append(symbol)
        
        query += " ORDER BY duration_days"
        
        try:
            data = self.db_service.execute_query(query, tuple(params))
            
            results = []
            for row in data:
                result = MomentumResult(
                    symbol=row['symbol'],
                    series=row['series'],
                    duration_type=row['duration_type'],
                    duration_days=row['duration_days'],
                    start_date=row['start_date'],
                    end_date=row['end_date'],
                    start_price=float(row['start_price']),
                    end_price=float(row['end_price']),
                    high_price=float(row['high_price']),
                    low_price=float(row['low_price']),
                    absolute_change=float(row['absolute_change']),
                    percentage_change=float(row['percentage_change']),
                    avg_volume=int(row['avg_volume']) if row['avg_volume'] else 0,
                    total_volume=int(row['total_volume']) if row['total_volume'] else 0,
                    volume_surge_factor=float(row['volume_surge_factor']) if row['volume_surge_factor'] else 1.0,
                    price_volatility=float(row['price_volatility']) if row['price_volatility'] else 0.0,
                    high_low_ratio=float(row['high_low_ratio']) if row['high_low_ratio'] else 1.0,
                    trading_days=int(row['trading_days']),
                    calculation_date=row['calculation_date']
                )
                results.append(result)
            
            return results
            
        except Exception as e:
            logger.error(f"[ERROR] Error retrieving momentum for {symbol}: {e}")
            return []

def main():
    """Test the momentum calculator"""
    
    print("[*] MOMENTUM CALCULATOR TEST")
    print("=" * 50)
    
    # Test with a few symbols
    test_symbols = ['RELIANCE', 'INFY', 'TCS', 'HDFCBANK', 'ICICIBANK']
    test_durations = [MomentumDuration.ONE_WEEK, MomentumDuration.ONE_MONTH, MomentumDuration.THREE_MONTHS]
    
    calculator = MomentumCalculator()
    
    print(f"[*] Testing with {len(test_symbols)} symbols and {len(test_durations)} durations")
    
    # Calculate momentum
    results = calculator.calculate_momentum_batch(
        symbols=test_symbols,
        durations=test_durations,
        max_workers=2
    )
    
    # Display results
    print(f"\n[OK] CALCULATION RESULTS")
    print("-" * 30)
    
    for symbol, symbol_results in results.items():
        print(f"\n[*] {symbol}:")
        for result in symbol_results:
            print(f"   {result.duration_type}: {result.percentage_change:+.2f}% "
                  f"(Rs.{result.start_price:.2f} -> Rs.{result.end_price:.2f})")
    
    # Store results
    if results:
        stored_count = calculator.store_momentum_results(results)
        print(f"\n💾 Stored {stored_count} records to database")
    
    print(f"\n🏆 MOMENTUM CALCULATOR TEST COMPLETE!")

if __name__ == "__main__":
    main()