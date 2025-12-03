"""Alert condition evaluators."""

from abc import ABC, abstractmethod
from typing import Optional, Tuple
from datetime import datetime

from .enums import AlertCondition, AlertType
from .models import Alert, PriceData


class AlertEvaluator(ABC):
    """Base class for alert evaluators."""
    
    @abstractmethod
    def evaluate(self, alert: Alert, price_data: PriceData) -> Tuple[bool, Optional[str]]:
        """
        Evaluate if alert condition is met.
        
        Returns:
            Tuple of (triggered: bool, message: Optional[str])
        """
        pass
    
    @abstractmethod
    def supports(self, alert: Alert) -> bool:
        """Check if this evaluator supports the given alert type."""
        pass


class PriceAlertEvaluator(AlertEvaluator):
    """Evaluates price-based alert conditions."""
    
    def supports(self, alert: Alert) -> bool:
        return alert.alert_type == AlertType.PRICE
    
    def evaluate(self, alert: Alert, price_data: PriceData) -> Tuple[bool, Optional[str]]:
        if not self.supports(alert):
            return False, None
        
        price = price_data.price
        target = alert.target_value
        prev_price = alert.previous_price
        
        condition = alert.condition
        
        if condition == AlertCondition.PRICE_ABOVE:
            if price >= target:
                return True, f"{alert.symbol} is now ₹{price:.2f} (above ₹{target:.2f})"
        
        elif condition == AlertCondition.PRICE_BELOW:
            if price <= target:
                return True, f"{alert.symbol} is now ₹{price:.2f} (below ₹{target:.2f})"
        
        elif condition == AlertCondition.PRICE_BETWEEN:
            target2 = alert.target_value_2 or target
            lower, upper = min(target, target2), max(target, target2)
            if lower <= price <= upper:
                return True, f"{alert.symbol} is now ₹{price:.2f} (between ₹{lower:.2f} and ₹{upper:.2f})"
        
        elif condition == AlertCondition.PRICE_CROSSES_ABOVE:
            if prev_price is not None and prev_price < target <= price:
                return True, f"{alert.symbol} crossed above ₹{target:.2f} (now ₹{price:.2f})"
        
        elif condition == AlertCondition.PRICE_CROSSES_BELOW:
            if prev_price is not None and prev_price > target >= price:
                return True, f"{alert.symbol} crossed below ₹{target:.2f} (now ₹{price:.2f})"
        
        elif condition == AlertCondition.PCT_CHANGE_UP:
            if price_data.change_pct >= target:
                return True, f"{alert.symbol} is up {price_data.change_pct:.2f}% (target: {target}%)"
        
        elif condition == AlertCondition.PCT_CHANGE_DOWN:
            if price_data.change_pct <= -target:
                return True, f"{alert.symbol} is down {abs(price_data.change_pct):.2f}% (target: {target}%)"
        
        return False, None


class VolumeAlertEvaluator(AlertEvaluator):
    """Evaluates volume-based alert conditions."""
    
    def supports(self, alert: Alert) -> bool:
        return alert.alert_type == AlertType.VOLUME
    
    def evaluate(self, alert: Alert, price_data: PriceData) -> Tuple[bool, Optional[str]]:
        if not self.supports(alert):
            return False, None
        
        volume = price_data.volume
        target = alert.target_value
        condition = alert.condition
        
        if condition == AlertCondition.VOLUME_ABOVE:
            if volume >= target:
                return True, f"{alert.symbol} volume is {volume:,} (above {target:,.0f})"
        
        elif condition == AlertCondition.VOLUME_SPIKE:
            avg_volume = price_data.avg_volume_20d
            if avg_volume and avg_volume > 0:
                spike_ratio = volume / avg_volume
                if spike_ratio >= target:
                    return True, f"{alert.symbol} volume spike: {spike_ratio:.1f}x average (target: {target}x)"
        
        return False, None


class TechnicalAlertEvaluator(AlertEvaluator):
    """Evaluates technical indicator-based alert conditions."""
    
    def supports(self, alert: Alert) -> bool:
        return alert.alert_type == AlertType.TECHNICAL
    
    def evaluate(self, alert: Alert, price_data: PriceData) -> Tuple[bool, Optional[str]]:
        if not self.supports(alert):
            return False, None
        
        condition = alert.condition
        target = alert.target_value
        price = price_data.price
        
        # RSI conditions
        if condition == AlertCondition.RSI_OVERBOUGHT:
            if price_data.rsi_14 is not None and price_data.rsi_14 >= target:
                return True, f"{alert.symbol} RSI is {price_data.rsi_14:.1f} (overbought threshold: {target})"
        
        elif condition == AlertCondition.RSI_OVERSOLD:
            if price_data.rsi_14 is not None and price_data.rsi_14 <= target:
                return True, f"{alert.symbol} RSI is {price_data.rsi_14:.1f} (oversold threshold: {target})"
        
        # MACD conditions
        elif condition == AlertCondition.MACD_BULLISH_CROSS:
            if price_data.macd is not None and price_data.macd_signal is not None:
                if price_data.macd > price_data.macd_signal:
                    return True, f"{alert.symbol} MACD bullish crossover"
        
        elif condition == AlertCondition.MACD_BEARISH_CROSS:
            if price_data.macd is not None and price_data.macd_signal is not None:
                if price_data.macd < price_data.macd_signal:
                    return True, f"{alert.symbol} MACD bearish crossover"
        
        # SMA cross conditions
        elif condition == AlertCondition.SMA_CROSS_ABOVE:
            sma = self._get_sma(price_data, int(target))
            if sma is not None and price >= sma:
                prev = alert.previous_price
                if prev is not None and prev < sma:
                    return True, f"{alert.symbol} crossed above SMA{int(target)} (₹{sma:.2f})"
        
        elif condition == AlertCondition.SMA_CROSS_BELOW:
            sma = self._get_sma(price_data, int(target))
            if sma is not None and price <= sma:
                prev = alert.previous_price
                if prev is not None and prev > sma:
                    return True, f"{alert.symbol} crossed below SMA{int(target)} (₹{sma:.2f})"
        
        # Bollinger Band conditions
        elif condition == AlertCondition.BOLLINGER_UPPER:
            if price_data.bb_upper is not None and price >= price_data.bb_upper:
                return True, f"{alert.symbol} touched upper Bollinger Band (₹{price_data.bb_upper:.2f})"
        
        elif condition == AlertCondition.BOLLINGER_LOWER:
            if price_data.bb_lower is not None and price <= price_data.bb_lower:
                return True, f"{alert.symbol} touched lower Bollinger Band (₹{price_data.bb_lower:.2f})"
        
        # 52-week high/low
        elif condition == AlertCondition.HIGH_52W:
            if price_data.high_52w is not None and price >= price_data.high_52w:
                return True, f"{alert.symbol} at 52-week high (₹{price:.2f})"
        
        elif condition == AlertCondition.LOW_52W:
            if price_data.low_52w is not None and price <= price_data.low_52w:
                return True, f"{alert.symbol} at 52-week low (₹{price:.2f})"
        
        return False, None
    
    def _get_sma(self, price_data: PriceData, period: int) -> Optional[float]:
        """Get SMA value based on period."""
        if period == 20:
            return price_data.sma_20
        elif period == 50:
            return price_data.sma_50
        elif period == 200:
            return price_data.sma_200
        return None


class CustomAlertEvaluator(AlertEvaluator):
    """Evaluates custom alerts from external scanners."""
    
    def supports(self, alert: Alert) -> bool:
        return alert.alert_type == AlertType.CUSTOM
    
    def evaluate(self, alert: Alert, price_data: PriceData) -> Tuple[bool, Optional[str]]:
        """
        Custom alerts are triggered externally via API.
        This evaluator just validates the alert is still active.
        """
        if not self.supports(alert):
            return False, None
        
        # Custom alerts are pre-evaluated by external systems
        # The API endpoint triggers them directly
        return False, None


class CompositeAlertEvaluator:
    """Combines multiple evaluators to handle all alert types."""
    
    def __init__(self):
        self.evaluators = [
            PriceAlertEvaluator(),
            VolumeAlertEvaluator(),
            TechnicalAlertEvaluator(),
            CustomAlertEvaluator(),
        ]
    
    def evaluate(self, alert: Alert, price_data: PriceData) -> Tuple[bool, Optional[str]]:
        """Evaluate alert using appropriate evaluator."""
        for evaluator in self.evaluators:
            if evaluator.supports(alert):
                return evaluator.evaluate(alert, price_data)
        
        return False, None
    
    def evaluate_all(self, alerts: list, price_data: PriceData) -> list:
        """
        Evaluate multiple alerts against price data.
        
        Returns:
            List of (alert, triggered, message) tuples
        """
        results = []
        for alert in alerts:
            triggered, message = self.evaluate(alert, price_data)
            results.append((alert, triggered, message))
        return results
