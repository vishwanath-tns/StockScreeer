"""
Portfolio Tracker - Automatic price updates and performance monitoring
"""

import logging
from datetime import datetime, date
from typing import Dict, List, Optional, Callable
import threading
import time

try:
    import yfinance as yf
    HAS_YFINANCE = True
except ImportError:
    HAS_YFINANCE = False

try:
    from sqlalchemy import create_engine, text
    HAS_SQLALCHEMY = True
except ImportError:
    HAS_SQLALCHEMY = False

from .portfolio_manager import PortfolioManager, Portfolio, Position, PortfolioType

logger = logging.getLogger(__name__)


class PortfolioTracker:
    """
    Automatic portfolio tracking with price updates.
    
    Usage:
        tracker = PortfolioTracker()
        
        # Create portfolio from volume scanner
        from volume_analysis import VolumeScanner
        scanner = VolumeScanner()
        results = scanner.scan_nifty500()
        
        tracker.create_accumulation_portfolio(results.accumulation[:15], "Top Accumulation Dec 2025")
        tracker.create_distribution_portfolio(results.distribution[:15], "Stocks to Avoid Dec 2025")
        
        # Update prices
        tracker.update_all_prices()
        
        # Show performance
        tracker.show_all_portfolios()
    """
    
    def __init__(self, db_path: str = "portfolios.db"):
        self.manager = PortfolioManager(db_path)
        self._update_thread = None
        self._stop_flag = False
    
    def _get_price_from_db(self, symbol: str) -> Optional[float]:
        """Get latest price from local database."""
        if not HAS_SQLALCHEMY:
            return None
        
        try:
            from dotenv import load_dotenv
            import os
            load_dotenv()
            
            db_url = f"mysql+pymysql://{os.getenv('MYSQL_USER', 'root')}:{os.getenv('MYSQL_PASSWORD', '')}@{os.getenv('MYSQL_HOST', 'localhost')}:{os.getenv('MYSQL_PORT', '3306')}/{os.getenv('MYSQL_DB', 'marketdata')}"
            engine = create_engine(db_url)
            
            with engine.connect() as conn:
                result = conn.execute(text("""
                    SELECT close FROM yfinance_daily_quotes 
                    WHERE symbol = :symbol 
                    ORDER BY date DESC LIMIT 1
                """), {"symbol": symbol})
                row = result.fetchone()
                if row:
                    return float(row[0])
        except Exception as e:
            logger.debug(f"DB lookup failed for {symbol}: {e}")
        
        return None
    
    def _get_price_from_yfinance(self, symbol: str) -> Optional[float]:
        """Get price from Yahoo Finance."""
        if not HAS_YFINANCE:
            return None
        
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.fast_info
            return info.last_price
        except Exception as e:
            logger.debug(f"YFinance lookup failed for {symbol}: {e}")
        
        return None
    
    def _get_price_data_from_yfinance(self, symbol: str) -> Dict[str, float]:
        """Get current price and previous close from Yahoo Finance."""
        if not HAS_YFINANCE:
            return {}
        
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.fast_info
            return {
                'current_price': info.last_price,
                'prev_close': info.previous_close if hasattr(info, 'previous_close') else info.last_price
            }
        except Exception as e:
            logger.debug(f"YFinance price data lookup failed for {symbol}: {e}")
        
        return {}
    
    def get_price(self, symbol: str) -> float:
        """Get current price for a symbol."""
        # Try database first (faster)
        price = self._get_price_from_db(symbol)
        if price:
            return price
        
        # Fallback to yfinance
        price = self._get_price_from_yfinance(symbol)
        return price or 0.0
    
    def get_prices_batch(self, symbols: List[str]) -> Dict[str, float]:
        """Get prices for multiple symbols."""
        prices = {}
        
        # Try database first
        if HAS_SQLALCHEMY:
            try:
                from dotenv import load_dotenv
                import os
                load_dotenv()
                
                db_url = f"mysql+pymysql://{os.getenv('MYSQL_USER', 'root')}:{os.getenv('MYSQL_PASSWORD', '')}@{os.getenv('MYSQL_HOST', 'localhost')}:{os.getenv('MYSQL_PORT', '3306')}/{os.getenv('MYSQL_DB', 'marketdata')}"
                engine = create_engine(db_url)
                
                with engine.connect() as conn:
                    # Get latest prices for all symbols
                    placeholders = ','.join([f"'{s}'" for s in symbols])
                    result = conn.execute(text(f"""
                        SELECT symbol, close FROM yfinance_daily_quotes 
                        WHERE symbol IN ({placeholders})
                        AND date = (SELECT MAX(date) FROM yfinance_daily_quotes WHERE symbol = yfinance_daily_quotes.symbol)
                    """))
                    for row in result:
                        prices[row[0]] = float(row[1])
            except Exception as e:
                logger.debug(f"Batch DB lookup failed: {e}")
        
        # Get remaining from yfinance
        missing = [s for s in symbols if s not in prices]
        if missing and HAS_YFINANCE:
            for symbol in missing:
                price = self._get_price_from_yfinance(symbol)
                if price:
                    prices[symbol] = price
        
        return prices
    
    def create_accumulation_portfolio(
        self,
        signals: List,
        name: str = None,
        max_positions: int = 20,
        min_score: float = 60
    ) -> Portfolio:
        """
        Create a portfolio from accumulation signals (BUY candidates).
        
        Args:
            signals: List of AccumulationSignal from volume scanner
            name: Portfolio name (auto-generated if None)
            max_positions: Maximum positions to include
            min_score: Minimum score threshold
        """
        if name is None:
            name = f"Accumulation {date.today().strftime('%Y-%m-%d')}"
        
        portfolio = self.manager.create_from_scanner(
            signals=signals,
            name=name,
            portfolio_type=PortfolioType.ACCUMULATION,
            max_positions=max_positions,
            min_score=min_score,
            get_price_func=self.get_price
        )
        
        logger.info(f"Created portfolio '{name}' with {len(portfolio.positions)} positions")
        return portfolio
    
    def create_distribution_portfolio(
        self,
        signals: List,
        name: str = None,
        max_positions: int = 20,
        max_score: float = 40
    ) -> Portfolio:
        """
        Create a portfolio from distribution signals (SELL/AVOID candidates).
        
        Args:
            signals: List of AccumulationSignal from volume scanner
            name: Portfolio name (auto-generated if None)
            max_positions: Maximum positions to include
            max_score: Maximum score threshold (lower = worse)
        """
        if name is None:
            name = f"Distribution {date.today().strftime('%Y-%m-%d')}"
        
        # Filter by max_score
        filtered = [s for s in signals if hasattr(s, 'score') and s.score <= max_score]
        
        portfolio = self.manager.create_from_scanner(
            signals=filtered,
            name=name,
            portfolio_type=PortfolioType.DISTRIBUTION,
            max_positions=max_positions,
            min_score=0,
            get_price_func=self.get_price
        )
        
        logger.info(f"Created portfolio '{name}' with {len(portfolio.positions)} positions")
        return portfolio
    
    def create_custom_portfolio(
        self,
        symbols: List[str],
        name: str,
        description: str = ""
    ) -> Portfolio:
        """Create a custom portfolio from a list of symbols."""
        portfolio = self.manager.create_portfolio(
            name=name,
            portfolio_type=PortfolioType.CUSTOM,
            description=description
        )
        
        for symbol in symbols:
            price = self.get_price(symbol)
            position = Position(
                symbol=symbol,
                entry_date=date.today().isoformat(),
                entry_price=price,
                current_price=price
            )
            portfolio.add_position(position)
        
        self.manager.save_portfolio(portfolio)
        return portfolio
    
    def update_all_prices(self):
        """Update prices for all positions in all portfolios."""
        all_symbols = set()
        for portfolio in self.manager.portfolios.values():
            for position in portfolio.positions:
                all_symbols.add(position.symbol)
        
        if not all_symbols:
            return
        
        # Get current prices (fast batch)
        prices = self.get_prices_batch(list(all_symbols))
        
        # Get price data with prev_close from yfinance for today's change
        price_data = {}
        if HAS_YFINANCE:
            for symbol in all_symbols:
                data = self._get_price_data_from_yfinance(symbol)
                if data:
                    price_data[symbol] = data
        
        for portfolio in self.manager.portfolios.values():
            for position in portfolio.positions:
                if position.symbol in prices:
                    position.current_price = prices[position.symbol]
                # Update prev_close for today's change tracking
                if position.symbol in price_data:
                    position.prev_close = price_data[position.symbol].get('prev_close', 0.0)
            self.manager.save_portfolio(portfolio)
        
        logger.info(f"Updated prices for {len(prices)} symbols")
    
    def record_daily_snapshot(self):
        """Record today's snapshot for all portfolios."""
        for name in self.manager.list_portfolios():
            self.manager.record_snapshot(name)
        logger.info("Recorded daily snapshots")
    
    def show_all_portfolios(self):
        """Display summary of all portfolios."""
        if not self.manager.portfolios:
            print("No portfolios found.")
            return
        
        print("\n" + "=" * 80)
        print("📊 PORTFOLIO PERFORMANCE SUMMARY")
        print("=" * 80)
        
        for name, portfolio in self.manager.portfolios.items():
            pnl_emoji = "🟢" if portfolio.total_pnl_percent > 0 else "🔴" if portfolio.total_pnl_percent < 0 else "⚪"
            print(f"\n{pnl_emoji} {name} ({portfolio.portfolio_type.value})")
            print(f"   Positions: {portfolio.total_positions} | P&L: {portfolio.total_pnl_percent:+.2f}% | Win Rate: {portfolio.win_rate:.0f}%")
            
            # Top 3 performers
            sorted_pos = sorted(portfolio.positions, key=lambda x: x.pnl_percent, reverse=True)
            if sorted_pos:
                print(f"   Top: {', '.join([f'{p.symbol}({p.pnl_percent:+.1f}%)' for p in sorted_pos[:3]])}")
            if len(sorted_pos) > 3:
                print(f"   Bottom: {', '.join([f'{p.symbol}({p.pnl_percent:+.1f}%)' for p in sorted_pos[-3:]])}")
    
    def show_portfolio(self, name: str):
        """Show detailed view of a portfolio."""
        self.manager.print_summary(name)
    
    def get_leaderboard(self) -> List[Dict]:
        """Get performance leaderboard across all portfolios."""
        all_positions = []
        
        for portfolio in self.manager.portfolios.values():
            for position in portfolio.positions:
                all_positions.append({
                    'symbol': position.symbol,
                    'portfolio': portfolio.name,
                    'entry_price': position.entry_price,
                    'current_price': position.current_price,
                    'pnl_percent': position.pnl_percent,
                    'signal': position.scanner_signal,
                    'score': position.scanner_score
                })
        
        # Sort by P&L
        all_positions.sort(key=lambda x: x['pnl_percent'], reverse=True)
        return all_positions
    
    def print_leaderboard(self, top_n: int = 20):
        """Print top performers across all portfolios."""
        leaderboard = self.get_leaderboard()
        
        print("\n" + "=" * 80)
        print("🏆 TOP PERFORMERS LEADERBOARD")
        print("=" * 80)
        print(f"{'Rank':<6} {'Symbol':<15} {'P&L %':>10} {'Portfolio':<25} {'Signal':<15}")
        print("-" * 80)
        
        for i, item in enumerate(leaderboard[:top_n], 1):
            emoji = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i:>2}."
            pnl_color = "🟢" if item['pnl_percent'] > 0 else "🔴"
            print(f"{emoji:<6} {item['symbol']:<15} {pnl_color}{item['pnl_percent']:>+9.2f}% {item['portfolio']:<25} {item['signal']:<15}")
        
        print("\n" + "-" * 80)
        print("🔻 WORST PERFORMERS")
        print("-" * 80)
        
        for i, item in enumerate(leaderboard[-top_n:], 1):
            print(f"{i:<6} {item['symbol']:<15} 🔴{item['pnl_percent']:>+9.2f}% {item['portfolio']:<25} {item['signal']:<15}")
    
    def delete_portfolio(self, name: str) -> bool:
        """Delete a portfolio."""
        return self.manager.delete_portfolio(name)
    
    def export_portfolio(self, name: str, format: str = "csv"):
        """Export a portfolio to file."""
        filename = f"{name.replace(' ', '_')}_{date.today()}.{format}"
        
        if format == "csv":
            self.manager.export_to_csv(name, filename)
        elif format == "json":
            self.manager.export_to_json(name, filename)
        
        print(f"Exported to {filename}")
        return filename
