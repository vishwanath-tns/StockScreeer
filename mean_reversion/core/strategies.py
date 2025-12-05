import pandas as pd
import numpy as np

class StrategyRegistry:
    """Registry for all strategies"""
    
    @staticmethod
    def calculate_rsi(series, period=2):
        delta = series.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs))

    @staticmethod
    def analyze_rsi_strategy(df, symbol):
        """
        RSI(2) Mean Reversion Analysis
        Returns: (signal, details)
        """
        if len(df) < 20:
            return 'NEUTRAL', {}
            
        rsi = StrategyRegistry.calculate_rsi(df['close'], 2)
        current_rsi = rsi.iloc[-1]
        
        # Check Buy (Oversold)
        if current_rsi < 10:
            return 'BUY', {'rsi': round(current_rsi, 2), 'threshold': 10, 'date': df.index[-1]}
            
        # Check Sell (Overbought)
        sma5 = df['close'].rolling(5).mean().iloc[-1]
        close = df['close'].iloc[-1]
        
        if current_rsi > 90 or close > sma5:
            return 'SELL', {'rsi': round(current_rsi, 2), 'threshold': 90, 'sma5': round(sma5, 2), 'date': df.index[-1]}
            
        return 'NEUTRAL', {'rsi': round(current_rsi, 2), 'date': df.index[-1]}

    @staticmethod
    def analyze_bb_strategy(df, symbol):
        """
        Bollinger Band Mean Reversion Analysis
        Returns: (signal, details)
        """
        if len(df) < 30:
            return 'NEUTRAL', {}
            
        sma20 = df['close'].rolling(20).mean()
        std20 = df['close'].rolling(20).std()
        upper = sma20 + (2 * std20)
        lower = sma20 - (2 * std20)
        
        current_price = df['close'].iloc[-1]
        current_lower = lower.iloc[-1]
        current_upper = upper.iloc[-1]
        current_sma = sma20.iloc[-1]
        
        # Buy: Close < Lower Band
        if current_price < current_lower:
            dist_pct = ((current_lower - current_price) / current_price) * 100
            return 'BUY', {
                'price': round(current_price, 2), 
                'lower_bb': round(current_lower, 2),
                'dist_pct': round(dist_pct, 2),
                'date': df.index[-1]
            }
            
        # Sell: Close > SMA 20
        if current_price > current_sma:
            return 'SELL', {
                'price': round(current_price, 2),
                'sma20': round(current_sma, 2),
                'date': df.index[-1]
            }
            
        return 'NEUTRAL', {
            'price': round(current_price, 2),
            'lower_bb': round(current_lower, 2),
            'percent_b': round((current_price - current_lower) / (current_upper - current_lower), 2),
            'date': df.index[-1]
        }
