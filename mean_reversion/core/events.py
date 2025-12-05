from dataclasses import dataclass
from datetime import datetime

@dataclass
class MarketData:
    symbol: str
    date: datetime
    close: float
    open: float
    high: float
    low: float
    volume: int
    
@dataclass
class ScanResult:
    symbol: str
    last_price: float
    signal_type: str  # 'BUY', 'SELL', 'NEUTRAL'
    strategy_name: str # 'RSI', 'BB'
    confidence: float
    details: dict     # {'rsi': 25, 'bb_lower': 100, ...}
    timestamp: datetime
