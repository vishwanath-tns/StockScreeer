"""
Portfolio Manager - Core classes for portfolio tracking
"""

import json
import sqlite3
from datetime import datetime, date
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Optional, Any
from pathlib import Path
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class PortfolioType(str, Enum):
    """Type of portfolio based on strategy."""
    ACCUMULATION = "accumulation"      # From volume scanner BUY signals
    DISTRIBUTION = "distribution"      # Stocks to avoid/short
    VCP = "vcp"                        # VCP pattern stocks
    MOMENTUM = "momentum"              # Momentum strategy
    WATCHLIST = "watchlist"           # General watchlist
    CUSTOM = "custom"                  # User-defined


@dataclass
class Position:
    """A single position in a portfolio."""
    symbol: str
    entry_date: str                    # ISO format date
    entry_price: float
    quantity: int = 0
    current_price: float = 0.0
    stop_loss: Optional[float] = None
    target: Optional[float] = None
    notes: str = ""
    scanner_score: Optional[float] = None  # Score when added
    scanner_signal: str = ""           # e.g., "STRONG BUY"
    
    @property
    def market_value(self) -> float:
        return self.quantity * self.current_price if self.quantity > 0 else self.current_price
    
    @property
    def cost_basis(self) -> float:
        return self.quantity * self.entry_price if self.quantity > 0 else self.entry_price
    
    @property
    def pnl(self) -> float:
        """Profit/Loss in absolute terms."""
        return self.market_value - self.cost_basis
    
    @property
    def pnl_percent(self) -> float:
        """Profit/Loss as percentage."""
        if self.entry_price == 0:
            return 0.0
        return ((self.current_price - self.entry_price) / self.entry_price) * 100
    
    @property
    def hit_stop_loss(self) -> bool:
        if self.stop_loss is None:
            return False
        return self.current_price <= self.stop_loss
    
    @property
    def hit_target(self) -> bool:
        if self.target is None:
            return False
        return self.current_price >= self.target
    
    def to_dict(self) -> Dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'Position':
        return cls(**data)


@dataclass
class Portfolio:
    """A portfolio containing multiple positions."""
    name: str
    portfolio_type: PortfolioType = PortfolioType.CUSTOM
    created_date: str = field(default_factory=lambda: datetime.now().isoformat())
    positions: List[Position] = field(default_factory=list)
    description: str = ""
    is_active: bool = True
    
    @property
    def total_positions(self) -> int:
        return len(self.positions)
    
    @property
    def total_value(self) -> float:
        return sum(p.market_value for p in self.positions)
    
    @property
    def total_cost(self) -> float:
        return sum(p.cost_basis for p in self.positions)
    
    @property
    def total_pnl(self) -> float:
        return sum(p.pnl for p in self.positions)
    
    @property
    def total_pnl_percent(self) -> float:
        if self.total_cost == 0:
            return 0.0
        return (self.total_pnl / self.total_cost) * 100
    
    @property
    def winners(self) -> List[Position]:
        return [p for p in self.positions if p.pnl_percent > 0]
    
    @property
    def losers(self) -> List[Position]:
        return [p for p in self.positions if p.pnl_percent < 0]
    
    @property
    def win_rate(self) -> float:
        if not self.positions:
            return 0.0
        return (len(self.winners) / len(self.positions)) * 100
    
    @property
    def avg_gain(self) -> float:
        if not self.winners:
            return 0.0
        return sum(p.pnl_percent for p in self.winners) / len(self.winners)
    
    @property
    def avg_loss(self) -> float:
        if not self.losers:
            return 0.0
        return sum(p.pnl_percent for p in self.losers) / len(self.losers)
    
    def add_position(self, position: Position):
        """Add a position to the portfolio."""
        # Check if symbol already exists
        existing = next((p for p in self.positions if p.symbol == position.symbol), None)
        if existing:
            logger.warning(f"{position.symbol} already in portfolio, updating...")
            self.positions.remove(existing)
        self.positions.append(position)
    
    def remove_position(self, symbol: str) -> Optional[Position]:
        """Remove a position from the portfolio."""
        position = next((p for p in self.positions if p.symbol == symbol), None)
        if position:
            self.positions.remove(position)
        return position
    
    def get_position(self, symbol: str) -> Optional[Position]:
        """Get a position by symbol."""
        return next((p for p in self.positions if p.symbol == symbol), None)
    
    def to_dict(self) -> Dict:
        return {
            'name': self.name,
            'portfolio_type': self.portfolio_type.value,
            'created_date': self.created_date,
            'positions': [p.to_dict() for p in self.positions],
            'description': self.description,
            'is_active': self.is_active,
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'Portfolio':
        positions = [Position.from_dict(p) for p in data.get('positions', [])]
        return cls(
            name=data['name'],
            portfolio_type=PortfolioType(data.get('portfolio_type', 'custom')),
            created_date=data.get('created_date', datetime.now().isoformat()),
            positions=positions,
            description=data.get('description', ''),
            is_active=data.get('is_active', True),
        )


class PortfolioManager:
    """
    Manage multiple portfolios with persistence.
    
    Usage:
        manager = PortfolioManager()
        
        # Create from scanner results
        manager.create_from_scanner(scan_results.accumulation[:10], "Top Accumulation")
        
        # Update prices
        manager.update_all_prices()
        
        # View performance
        for portfolio in manager.portfolios:
            print(f"{portfolio.name}: {portfolio.total_pnl_percent:.2f}%")
    """
    
    def __init__(self, db_path: str = "portfolios.db"):
        self.db_path = Path(db_path)
        self.portfolios: Dict[str, Portfolio] = {}
        self._init_db()
        self._load_portfolios()
    
    def _init_db(self):
        """Initialize SQLite database."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS portfolios (
                    name TEXT PRIMARY KEY,
                    data TEXT NOT NULL,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS portfolio_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    portfolio_name TEXT,
                    date TEXT,
                    total_value REAL,
                    total_pnl REAL,
                    total_pnl_percent REAL,
                    positions_count INTEGER,
                    win_rate REAL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            # Create equity curve table for detailed daily tracking
            conn.execute("""
                CREATE TABLE IF NOT EXISTS portfolio_equity_curve (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    portfolio_name TEXT NOT NULL,
                    trade_date TEXT NOT NULL,
                    total_value REAL,
                    total_cost REAL,
                    total_pnl REAL,
                    total_pnl_percent REAL,
                    positions_count INTEGER,
                    winners_count INTEGER,
                    losers_count INTEGER,
                    win_rate REAL,
                    avg_gain REAL,
                    avg_loss REAL,
                    best_performer TEXT,
                    best_pnl_percent REAL,
                    worst_performer TEXT,
                    worst_pnl_percent REAL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(portfolio_name, trade_date)
                )
            """)
            # Create index for faster queries
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_equity_curve_portfolio_date 
                ON portfolio_equity_curve(portfolio_name, trade_date)
            """)
            conn.commit()
    
    def _load_portfolios(self):
        """Load all portfolios from database."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT name, data FROM portfolios")
            for name, data in cursor.fetchall():
                try:
                    portfolio_dict = json.loads(data)
                    self.portfolios[name] = Portfolio.from_dict(portfolio_dict)
                except Exception as e:
                    logger.error(f"Error loading portfolio {name}: {e}")
    
    def save_portfolio(self, portfolio: Portfolio):
        """Save a portfolio to database."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT OR REPLACE INTO portfolios (name, data, updated_at) VALUES (?, ?, ?)",
                (portfolio.name, json.dumps(portfolio.to_dict()), datetime.now().isoformat())
            )
            conn.commit()
        self.portfolios[portfolio.name] = portfolio
    
    def delete_portfolio(self, name: str) -> bool:
        """Delete a portfolio."""
        if name in self.portfolios:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("DELETE FROM portfolios WHERE name = ?", (name,))
                conn.commit()
            del self.portfolios[name]
            return True
        return False
    
    def create_portfolio(
        self,
        name: str,
        portfolio_type: PortfolioType = PortfolioType.CUSTOM,
        description: str = ""
    ) -> Portfolio:
        """Create a new empty portfolio."""
        portfolio = Portfolio(
            name=name,
            portfolio_type=portfolio_type,
            description=description
        )
        self.save_portfolio(portfolio)
        return portfolio
    
    def create_from_scanner(
        self,
        signals: List[Any],  # List of AccumulationSignal
        name: str,
        portfolio_type: PortfolioType = PortfolioType.ACCUMULATION,
        max_positions: int = 20,
        min_score: float = 0,
        get_price_func=None
    ) -> Portfolio:
        """
        Create a portfolio from scanner results.
        
        Args:
            signals: List of AccumulationSignal from volume scanner
            name: Name for the portfolio
            portfolio_type: Type of portfolio
            max_positions: Maximum number of positions
            min_score: Minimum score to include
            get_price_func: Optional function to get current price
        """
        portfolio = Portfolio(
            name=name,
            portfolio_type=portfolio_type,
            description=f"Created from {portfolio_type.value} scanner on {date.today()}"
        )
        
        for signal in signals[:max_positions]:
            if hasattr(signal, 'score') and signal.score < min_score:
                continue
            
            symbol = signal.symbol if hasattr(signal, 'symbol') else str(signal)
            score = signal.score if hasattr(signal, 'score') else 0
            strength = signal.strength.value if hasattr(signal, 'strength') else ""
            
            # Get entry price
            entry_price = 0.0
            if get_price_func:
                try:
                    entry_price = get_price_func(symbol)
                except:
                    pass
            
            # Determine signal text
            if portfolio_type == PortfolioType.ACCUMULATION:
                if score >= 70:
                    signal_text = "STRONG BUY"
                elif score >= 60:
                    signal_text = "BUY"
                else:
                    signal_text = "WATCH"
            elif portfolio_type == PortfolioType.DISTRIBUTION:
                if score <= 30:
                    signal_text = "STRONG SELL"
                elif score <= 40:
                    signal_text = "SELL"
                else:
                    signal_text = "AVOID"
            else:
                signal_text = strength.upper() if strength else ""
            
            position = Position(
                symbol=symbol,
                entry_date=date.today().isoformat(),
                entry_price=entry_price,
                current_price=entry_price,
                scanner_score=score,
                scanner_signal=signal_text,
                notes=f"Added from {portfolio_type.value} scanner"
            )
            portfolio.add_position(position)
        
        self.save_portfolio(portfolio)
        return portfolio
    
    def update_prices(self, portfolio_name: str, price_dict: Dict[str, float]):
        """Update prices for a portfolio."""
        if portfolio_name not in self.portfolios:
            return
        
        portfolio = self.portfolios[portfolio_name]
        for position in portfolio.positions:
            if position.symbol in price_dict:
                position.current_price = price_dict[position.symbol]
        
        self.save_portfolio(portfolio)
    
    def update_all_prices(self, get_prices_func=None):
        """
        Update prices for all portfolios.
        
        Args:
            get_prices_func: Function that takes list of symbols and returns dict of prices
        """
        if not get_prices_func:
            # Default: use yfinance
            try:
                import yfinance as yf
                
                def get_prices_func(symbols):
                    prices = {}
                    for symbol in symbols:
                        try:
                            ticker = yf.Ticker(symbol)
                            info = ticker.fast_info
                            prices[symbol] = info.last_price
                        except:
                            pass
                    return prices
            except ImportError:
                logger.error("yfinance not installed")
                return
        
        # Collect all unique symbols
        all_symbols = set()
        for portfolio in self.portfolios.values():
            for position in portfolio.positions:
                all_symbols.add(position.symbol)
        
        if not all_symbols:
            return
        
        # Get prices
        prices = get_prices_func(list(all_symbols))
        
        # Update all portfolios
        for portfolio in self.portfolios.values():
            for position in portfolio.positions:
                if position.symbol in prices:
                    position.current_price = prices[position.symbol]
            self.save_portfolio(portfolio)
    
    def record_snapshot(self, portfolio_name: str):
        """Record a historical snapshot of portfolio performance."""
        if portfolio_name not in self.portfolios:
            return
        
        portfolio = self.portfolios[portfolio_name]
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO portfolio_history 
                (portfolio_name, date, total_value, total_pnl, total_pnl_percent, positions_count, win_rate)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                portfolio_name,
                date.today().isoformat(),
                portfolio.total_value,
                portfolio.total_pnl,
                portfolio.total_pnl_percent,
                portfolio.total_positions,
                portfolio.win_rate
            ))
            conn.commit()
    
    def record_equity_curve(self, portfolio_name: str, trade_date: str = None):
        """
        Record detailed equity curve data point for a portfolio.
        
        Args:
            portfolio_name: Name of the portfolio
            trade_date: Date string (ISO format), defaults to today
        """
        if portfolio_name not in self.portfolios:
            return False
        
        portfolio = self.portfolios[portfolio_name]
        if trade_date is None:
            trade_date = date.today().isoformat()
        
        # Find best and worst performers
        best_performer = ""
        best_pnl = 0.0
        worst_performer = ""
        worst_pnl = 0.0
        
        if portfolio.positions:
            sorted_by_pnl = sorted(portfolio.positions, key=lambda p: p.pnl_percent, reverse=True)
            if sorted_by_pnl:
                best = sorted_by_pnl[0]
                best_performer = best.symbol
                best_pnl = best.pnl_percent
                
                worst = sorted_by_pnl[-1]
                worst_performer = worst.symbol
                worst_pnl = worst.pnl_percent
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO portfolio_equity_curve 
                (portfolio_name, trade_date, total_value, total_cost, total_pnl, 
                 total_pnl_percent, positions_count, winners_count, losers_count,
                 win_rate, avg_gain, avg_loss, best_performer, best_pnl_percent,
                 worst_performer, worst_pnl_percent)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                portfolio_name,
                trade_date,
                portfolio.total_value,
                portfolio.total_cost,
                portfolio.total_pnl,
                portfolio.total_pnl_percent,
                portfolio.total_positions,
                len(portfolio.winners),
                len(portfolio.losers),
                portfolio.win_rate,
                portfolio.avg_gain,
                portfolio.avg_loss,
                best_performer,
                best_pnl,
                worst_performer,
                worst_pnl
            ))
            conn.commit()
        
        logger.info(f"Recorded equity curve for {portfolio_name}: {trade_date} = {portfolio.total_pnl_percent:.2f}%")
        return True
    
    def record_all_equity_curves(self, trade_date: str = None):
        """Record equity curve data for all portfolios."""
        for portfolio_name in self.portfolios:
            self.record_equity_curve(portfolio_name, trade_date)
    
    def get_equity_curve(self, portfolio_name: str, days: int = None) -> List[Dict]:
        """
        Get equity curve data for a portfolio.
        
        Args:
            portfolio_name: Name of the portfolio
            days: Number of days to retrieve (None = all data)
        
        Returns:
            List of dicts with equity curve data points
        """
        with sqlite3.connect(self.db_path) as conn:
            if days:
                cursor = conn.execute("""
                    SELECT trade_date, total_value, total_cost, total_pnl, total_pnl_percent,
                           positions_count, winners_count, losers_count, win_rate,
                           avg_gain, avg_loss, best_performer, best_pnl_percent,
                           worst_performer, worst_pnl_percent
                    FROM portfolio_equity_curve
                    WHERE portfolio_name = ?
                    ORDER BY trade_date DESC
                    LIMIT ?
                """, (portfolio_name, days))
            else:
                cursor = conn.execute("""
                    SELECT trade_date, total_value, total_cost, total_pnl, total_pnl_percent,
                           positions_count, winners_count, losers_count, win_rate,
                           avg_gain, avg_loss, best_performer, best_pnl_percent,
                           worst_performer, worst_pnl_percent
                    FROM portfolio_equity_curve
                    WHERE portfolio_name = ?
                    ORDER BY trade_date ASC
                """, (portfolio_name,))
            
            results = []
            for row in cursor.fetchall():
                results.append({
                    'trade_date': row[0],
                    'total_value': row[1],
                    'total_cost': row[2],
                    'total_pnl': row[3],
                    'total_pnl_percent': row[4],
                    'positions_count': row[5],
                    'winners_count': row[6],
                    'losers_count': row[7],
                    'win_rate': row[8],
                    'avg_gain': row[9],
                    'avg_loss': row[10],
                    'best_performer': row[11],
                    'best_pnl_percent': row[12],
                    'worst_performer': row[13],
                    'worst_pnl_percent': row[14]
                })
            
            return results
    
    def get_history(self, portfolio_name: str, days: int = 30) -> List[Dict]:
        """Get historical performance data."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT date, total_value, total_pnl, total_pnl_percent, positions_count, win_rate
                FROM portfolio_history
                WHERE portfolio_name = ?
                ORDER BY date DESC
                LIMIT ?
            """, (portfolio_name, days))
            
            return [
                {
                    'date': row[0],
                    'total_value': row[1],
                    'total_pnl': row[2],
                    'total_pnl_percent': row[3],
                    'positions_count': row[4],
                    'win_rate': row[5]
                }
                for row in cursor.fetchall()
            ]
    
    def get_portfolio(self, name: str) -> Optional[Portfolio]:
        """Get a portfolio by name."""
        return self.portfolios.get(name)
    
    def list_portfolios(self) -> List[str]:
        """List all portfolio names."""
        return list(self.portfolios.keys())
    
    def export_to_csv(self, portfolio_name: str, filepath: str):
        """Export portfolio to CSV."""
        import csv
        
        portfolio = self.portfolios.get(portfolio_name)
        if not portfolio:
            return
        
        with open(filepath, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                'Symbol', 'Entry Date', 'Entry Price', 'Current Price', 
                'P&L %', 'Score', 'Signal', 'Notes'
            ])
            for p in portfolio.positions:
                writer.writerow([
                    p.symbol, p.entry_date, p.entry_price, p.current_price,
                    f"{p.pnl_percent:.2f}", p.scanner_score, p.scanner_signal, p.notes
                ])
    
    def export_to_json(self, portfolio_name: str, filepath: str):
        """Export portfolio to JSON."""
        portfolio = self.portfolios.get(portfolio_name)
        if not portfolio:
            return
        
        with open(filepath, 'w') as f:
            json.dump(portfolio.to_dict(), f, indent=2)
    
    def print_summary(self, portfolio_name: str = None):
        """Print summary of portfolios."""
        portfolios = [self.portfolios[portfolio_name]] if portfolio_name else list(self.portfolios.values())
        
        for portfolio in portfolios:
            print(f"\n{'='*60}")
            print(f"📊 {portfolio.name} ({portfolio.portfolio_type.value})")
            print(f"{'='*60}")
            print(f"Created: {portfolio.created_date[:10]}")
            print(f"Positions: {portfolio.total_positions}")
            print(f"Total P&L: {portfolio.total_pnl_percent:+.2f}%")
            print(f"Win Rate: {portfolio.win_rate:.1f}%")
            print(f"Avg Gain: {portfolio.avg_gain:+.2f}%")
            print(f"Avg Loss: {portfolio.avg_loss:+.2f}%")
            print()
            print(f"{'Symbol':<15} {'Entry':>10} {'Current':>10} {'P&L %':>10} {'Signal':<15}")
            print("-" * 60)
            
            # Sort by P&L
            sorted_positions = sorted(portfolio.positions, key=lambda x: x.pnl_percent, reverse=True)
            for p in sorted_positions:
                pnl_color = "🟢" if p.pnl_percent > 0 else "🔴" if p.pnl_percent < 0 else "⚪"
                print(f"{p.symbol:<15} {p.entry_price:>10.2f} {p.current_price:>10.2f} {pnl_color}{p.pnl_percent:>+9.2f}% {p.scanner_signal:<15}")
