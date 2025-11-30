"""
Composite Score Calculator

Combines all individual scores into a single composite score.

Default Weights:
- RS Rating:       25%
- Momentum Score:  25%
- Trend Template:  25%
- Technical Score: 25%

All input scores normalized to 0-100 before weighting.
Output: 0-100 composite score.
"""

from dataclasses import dataclass, field
from datetime import date
from typing import Dict, Optional, Any


@dataclass
class CompositeResult:
    """Result of composite score calculation."""
    symbol: str
    composite_score: float  # 0-100
    rank: int = 0
    percentile: float = 0
    # Normalized component scores (0-100)
    norm_rs_rating: float = 0
    norm_momentum: float = 0
    norm_trend_template: float = 0
    norm_technical: float = 0
    # Raw inputs
    raw_rs_rating: float = 0
    raw_momentum: float = 0
    raw_trend_template: int = 0
    raw_technical: float = 0
    success: bool = True
    error: str = ""


class CompositeScoreCalculator:
    """
    Combine individual scores into composite ranking.
    
    Accepts results from other calculators and produces
    a single weighted composite score.
    """
    
    DEFAULT_WEIGHTS = {
        "rs_rating": 0.25,
        "momentum": 0.25,
        "trend_template": 0.25,
        "technical": 0.25,
    }
    
    def __init__(self, weights: Optional[Dict[str, float]] = None):
        """
        Initialize with optional custom weights.
        
        Args:
            weights: Dict of component name to weight. Must sum to 1.0.
        """
        self.name = "Composite Score"
        self.score_type = "composite_score"
        self.weights = weights or self.DEFAULT_WEIGHTS.copy()
        
        # Validate weights
        total = sum(self.weights.values())
        if abs(total - 1.0) > 0.001:
            raise ValueError(f"Weights must sum to 1.0, got {total}")
    
    def normalize_rs_rating(self, rs_rating: float) -> float:
        """
        Normalize RS Rating (1-99) to 0-100.
        
        RS Rating is already on 1-99 scale, just scale to 0-100.
        """
        return min(100, max(0, rs_rating))
    
    def normalize_trend_template(self, score: int) -> float:
        """
        Normalize Trend Template (0-8) to 0-100.
        """
        return (score / 8) * 100
    
    def calculate_single(
        self,
        symbol: str,
        rs_rating: float,
        momentum_score: float,
        trend_template_score: int,
        technical_score: float,
    ) -> CompositeResult:
        """
        Calculate composite score from individual scores.
        
        All input scores should already be on their native scales:
        - rs_rating: 1-99
        - momentum_score: 0-100
        - trend_template_score: 0-8
        - technical_score: 0-100
        """
        try:
            # Normalize to 0-100
            norm_rs = self.normalize_rs_rating(rs_rating)
            norm_momentum = momentum_score  # Already 0-100
            norm_trend = self.normalize_trend_template(trend_template_score)
            norm_technical = technical_score  # Already 0-100
            
            # Calculate weighted composite
            composite = (
                norm_rs * self.weights["rs_rating"] +
                norm_momentum * self.weights["momentum"] +
                norm_trend * self.weights["trend_template"] +
                norm_technical * self.weights["technical"]
            )
            
            return CompositeResult(
                symbol=symbol,
                composite_score=round(composite, 2),
                norm_rs_rating=round(norm_rs, 2),
                norm_momentum=round(norm_momentum, 2),
                norm_trend_template=round(norm_trend, 2),
                norm_technical=round(norm_technical, 2),
                raw_rs_rating=rs_rating,
                raw_momentum=momentum_score,
                raw_trend_template=trend_template_score,
                raw_technical=technical_score,
            )
            
        except Exception as e:
            return CompositeResult(
                symbol=symbol,
                composite_score=0,
                success=False,
                error=str(e)
            )
    
    def calculate_batch(
        self,
        scores_data: Dict[str, Dict[str, Any]],
    ) -> Dict[str, CompositeResult]:
        """
        Calculate composite scores for all stocks.
        
        Args:
            scores_data: Dict mapping symbol to dict with:
                - rs_rating: float
                - momentum_score: float
                - trend_template_score: int
                - technical_score: float
        
        Returns:
            Dict mapping symbol to CompositeResult with ranks.
        """
        results = {}
        valid_scores = []
        
        for symbol, scores in scores_data.items():
            result = self.calculate_single(
                symbol=symbol,
                rs_rating=scores.get("rs_rating", 0),
                momentum_score=scores.get("momentum_score", 0),
                trend_template_score=scores.get("trend_template_score", 0),
                technical_score=scores.get("technical_score", 0),
            )
            results[symbol] = result
            if result.success:
                valid_scores.append((symbol, result.composite_score))
        
        # Rank by composite score
        valid_scores.sort(key=lambda x: x[1], reverse=True)
        total = len(valid_scores)
        
        for rank, (symbol, _) in enumerate(valid_scores, start=1):
            results[symbol].rank = rank
            results[symbol].percentile = round((total - rank + 1) / total * 100, 1)
        
        return results
    
    def combine_calculator_results(
        self,
        rs_results: Dict[str, Any],
        momentum_results: Dict[str, Any],
        trend_results: Dict[str, Any],
        technical_results: Dict[str, Any],
    ) -> Dict[str, CompositeResult]:
        """
        Convenience method to combine results from individual calculators.
        
        Each *_results is a dict mapping symbol to result object
        with the appropriate score attribute.
        """
        # Get all symbols
        all_symbols = set()
        for results in [rs_results, momentum_results, trend_results, technical_results]:
            all_symbols.update(results.keys())
        
        # Build combined data
        scores_data = {}
        for symbol in all_symbols:
            scores_data[symbol] = {
                "rs_rating": getattr(rs_results.get(symbol), "rs_rating", 0),
                "momentum_score": getattr(momentum_results.get(symbol), "momentum_score", 0),
                "trend_template_score": getattr(trend_results.get(symbol), "score", 0),
                "technical_score": getattr(technical_results.get(symbol), "technical_score", 0),
            }
        
        return self.calculate_batch(scores_data)


# Standalone test
if __name__ == "__main__":
    calc = CompositeScoreCalculator()
    
    # Test data simulating results from other calculators
    test_data = {
        "STOCK1": {"rs_rating": 95, "momentum_score": 88, "trend_template_score": 8, "technical_score": 92},
        "STOCK2": {"rs_rating": 80, "momentum_score": 75, "trend_template_score": 6, "technical_score": 78},
        "STOCK3": {"rs_rating": 50, "momentum_score": 45, "trend_template_score": 4, "technical_score": 55},
        "STOCK4": {"rs_rating": 30, "momentum_score": 35, "trend_template_score": 2, "technical_score": 40},
        "STOCK5": {"rs_rating": 10, "momentum_score": 15, "trend_template_score": 0, "technical_score": 20},
    }
    
    results = calc.calculate_batch(test_data)
    
    print("Composite Score Results:")
    print("-" * 90)
    print(f"{'Symbol':10} | {'Composite':>9} | {'Rank':>4} | {'%ile':>5} | "
          f"{'RS':>5} | {'Mom':>5} | {'Trend':>5} | {'Tech':>5}")
    print("-" * 90)
    
    for symbol, r in sorted(results.items(), key=lambda x: x[1].composite_score, reverse=True):
        print(f"{symbol:10} | {r.composite_score:9.2f} | {r.rank:4} | {r.percentile:5.1f} | "
              f"{r.norm_rs_rating:5.1f} | {r.norm_momentum:5.1f} | "
              f"{r.norm_trend_template:5.1f} | {r.norm_technical:5.1f}")
