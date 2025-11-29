"""
Base Calculator Interface

Abstract base class for all rating calculators.
Ensures consistent interface for testability and composability.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List
from datetime import date
import pandas as pd


@dataclass
class CalculatorResult:
    """
    Result from a rating calculator.
    
    Attributes:
        symbol: Stock symbol.
        score: Calculated score value.
        rank: Rank among all calculated stocks (1 = best).
        percentile: Percentile rank (99 = top 1%).
        details: Additional calculation details.
        success: Whether calculation succeeded.
        error_message: Error message if calculation failed.
    """
    symbol: str
    score: float = 0.0
    rank: int = 0
    percentile: float = 0.0
    details: Dict[str, Any] = field(default_factory=dict)
    success: bool = True
    error_message: str = ""
    
    @classmethod
    def failure(cls, symbol: str, error: str) -> "CalculatorResult":
        """Create a failed result."""
        return cls(
            symbol=symbol,
            success=False,
            error_message=error,
        )


class IRatingCalculator(ABC):
    """
    Abstract base class for rating calculators.
    
    All rating services must implement this interface.
    """
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Return the name of this calculator."""
        pass
    
    @property
    @abstractmethod
    def score_type(self) -> str:
        """Return the type of score this calculator produces."""
        pass
    
    @abstractmethod
    def calculate_single(
        self,
        symbol: str,
        data: pd.DataFrame,
        calculation_date: date,
    ) -> CalculatorResult:
        """
        Calculate score for a single stock.
        
        Args:
            symbol: Stock symbol.
            data: DataFrame with stock data.
            calculation_date: Date to calculate for.
            
        Returns:
            CalculatorResult with score and details.
        """
        pass
    
    @abstractmethod
    def calculate_batch(
        self,
        symbols: List[str],
        data: Dict[str, pd.DataFrame],
        calculation_date: date,
    ) -> Dict[str, CalculatorResult]:
        """
        Calculate scores for multiple stocks.
        
        This method also calculates ranks and percentiles
        relative to all stocks in the batch.
        
        Args:
            symbols: List of stock symbols.
            data: Dict mapping symbol to DataFrame.
            calculation_date: Date to calculate for.
            
        Returns:
            Dict mapping symbol to CalculatorResult.
        """
        pass
    
    def calculate_ranks(
        self,
        results: Dict[str, CalculatorResult],
        higher_is_better: bool = True,
    ) -> Dict[str, CalculatorResult]:
        """
        Calculate ranks and percentiles for a batch of results.
        
        Args:
            results: Dict mapping symbol to CalculatorResult.
            higher_is_better: If True, higher scores get better ranks.
            
        Returns:
            Updated results with ranks and percentiles.
        """
        # Filter successful results
        successful = {
            sym: res for sym, res in results.items() 
            if res.success and res.score > 0
        }
        
        if not successful:
            return results
        
        # Sort by score
        sorted_symbols = sorted(
            successful.keys(),
            key=lambda s: successful[s].score,
            reverse=higher_is_better,
        )
        
        total = len(sorted_symbols)
        
        # Assign ranks and percentiles
        for rank, symbol in enumerate(sorted_symbols, start=1):
            results[symbol].rank = rank
            # Percentile: 99 means top 1%, 1 means bottom 1%
            results[symbol].percentile = round(
                (total - rank + 1) / total * 100, 1
            )
        
        return results


class BaseCalculator(IRatingCalculator):
    """
    Base implementation with common functionality.
    
    Subclasses only need to implement calculate_single.
    """
    
    def calculate_batch(
        self,
        symbols: List[str],
        data: Dict[str, pd.DataFrame],
        calculation_date: date,
    ) -> Dict[str, CalculatorResult]:
        """
        Default batch implementation using calculate_single.
        
        Override for more efficient batch processing.
        """
        results = {}
        
        for symbol in symbols:
            if symbol not in data:
                results[symbol] = CalculatorResult.failure(
                    symbol, f"No data available for {symbol}"
                )
                continue
            
            try:
                result = self.calculate_single(
                    symbol, data[symbol], calculation_date
                )
                results[symbol] = result
            except Exception as e:
                results[symbol] = CalculatorResult.failure(
                    symbol, str(e)
                )
        
        # Calculate ranks and percentiles
        return self.calculate_ranks(results)
