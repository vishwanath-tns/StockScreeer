"""
Composite Score Calculator

Combines all individual scores into a single composite score.

Default Weights:
- RS Rating:       25%
- Momentum Score:  25%
- Trend Template:  25%
- Technical Score: 25%
"""

from dataclasses import dataclass
from typing import Dict, Optional, Any


@dataclass
class CompositeResult:
    """Result of composite score calculation."""
    symbol: str
    composite_score: float
    rank: int = 0
    percentile: float = 0
    norm_rs_rating: float = 0
    norm_momentum: float = 0
    norm_trend_template: float = 0
    norm_technical: float = 0
    raw_rs_rating: float = 0
    raw_momentum: float = 0
    raw_trend_template: int = 0
    raw_technical: float = 0
    success: bool = True
    error: str = ""


class CompositeScoreService:
    """Combine individual scores into composite ranking."""
    
    DEFAULT_WEIGHTS = {
        "rs_rating": 0.25,
        "momentum": 0.25,
        "trend_template": 0.25,
        "technical": 0.25,
    }
    
    def __init__(self, weights: Optional[Dict[str, float]] = None):
        self.name = "Composite Score"
        self.score_type = "composite_score"
        self.weights = weights or self.DEFAULT_WEIGHTS.copy()
    
    def normalize_rs_rating(self, rs_rating: float) -> float:
        """Normalize RS Rating (1-99) to 0-100."""
        return min(100, max(0, rs_rating))
    
    def normalize_trend_template(self, score: int) -> float:
        """Normalize Trend Template (0-8) to 0-100."""
        return (score / 8) * 100
    
    def calculate_single(
        self, symbol: str, rs_rating: float, momentum_score: float,
        trend_template_score: int, technical_score: float
    ) -> CompositeResult:
        """Calculate composite score from individual scores."""
        try:
            norm_rs = self.normalize_rs_rating(rs_rating)
            norm_momentum = momentum_score
            norm_trend = self.normalize_trend_template(trend_template_score)
            norm_technical = technical_score
            
            composite = (
                norm_rs * self.weights["rs_rating"] +
                norm_momentum * self.weights["momentum"] +
                norm_trend * self.weights["trend_template"] +
                norm_technical * self.weights["technical"]
            )
            
            return CompositeResult(
                symbol=symbol, composite_score=round(composite, 2),
                norm_rs_rating=round(norm_rs, 2), norm_momentum=round(norm_momentum, 2),
                norm_trend_template=round(norm_trend, 2), norm_technical=round(norm_technical, 2),
                raw_rs_rating=rs_rating, raw_momentum=momentum_score,
                raw_trend_template=trend_template_score, raw_technical=technical_score,
            )
        except Exception as e:
            return CompositeResult(symbol=symbol, composite_score=0, success=False, error=str(e))
    
    def calculate_batch(
        self, scores_data: Dict[str, Dict[str, Any]]
    ) -> Dict[str, CompositeResult]:
        """Calculate composite scores for all stocks."""
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
        
        valid_scores.sort(key=lambda x: x[1], reverse=True)
        total = len(valid_scores)
        
        for rank, (symbol, _) in enumerate(valid_scores, start=1):
            results[symbol].rank = rank
            results[symbol].percentile = round((total - rank + 1) / total * 100, 1)
        
        return results
    
    def combine_calculator_results(
        self, rs_results: Dict[str, Any], momentum_results: Dict[str, Any],
        trend_results: Dict[str, Any], technical_results: Dict[str, Any]
    ) -> Dict[str, CompositeResult]:
        """Convenience method to combine results from individual calculators."""
        all_symbols = set()
        for results in [rs_results, momentum_results, trend_results, technical_results]:
            all_symbols.update(results.keys())
        
        scores_data = {}
        for symbol in all_symbols:
            scores_data[symbol] = {
                "rs_rating": getattr(rs_results.get(symbol), "rs_rating", 0),
                "momentum_score": getattr(momentum_results.get(symbol), "momentum_score", 0),
                "trend_template_score": getattr(trend_results.get(symbol), "score", 0),
                "technical_score": getattr(technical_results.get(symbol), "technical_score", 0),
            }
        
        return self.calculate_batch(scores_data)
