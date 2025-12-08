"""
Create Swing Trade Portfolios by Rating
=======================================
Creates portfolios grouped by star rating:
- Swing Long - Rate 5 (best long setups)
- Swing Long - Rate 4
- Swing Long - Rate 3
- Swing Short - Rate 5 (best short setups)
- Swing Short - Rate 4
etc.
"""

import sys
sys.path.insert(0, '.')
import pandas as pd
from datetime import date
from analysis.sector_sma_analysis import get_engine, get_sector_summary, get_sector_stocks_detail
from portfolio.portfolio_manager import PortfolioManager, Portfolio, Position, PortfolioType


def calc_long_score(row, breadth):
    """Calculate score for long candidates (0-100)."""
    s = min(25, (breadth / 60) * 25)  # Sector strength
    
    # Fresh crossover bonus
    days = row.get('days_above_sma_50', 0)
    if days > 0:
        s += max(0, 25 - (days - 1) * 1.5)
    
    # Entry proximity
    pct_50 = row.get('pct_from_sma_50', 0)
    if pct_50 > 0:
        if pct_50 <= 2:
            s += 25
        elif pct_50 <= 5:
            s += 25 - (pct_50 - 2) * 3.3
        elif pct_50 <= 10:
            s += 15 - (pct_50 - 5) * 2
        else:
            s += max(0, 5 - (pct_50 - 10) * 0.5)
    
    # Trend confirmation (above SMA200)
    pct_200 = row.get('pct_from_sma_200', 0)
    if pct_200 > 0:
        s += min(25, 15 + min(10, pct_200))
    elif pct_200 > -5:
        s += 10 + pct_200
    else:
        s += max(0, 5 + pct_200 / 2)
    
    return round(s, 1)


def calc_short_score(row, breadth):
    """Calculate score for short candidates (0-100)."""
    s = max(0, 25 - (breadth / 2))  # Sector weakness
    
    # Persistent downtrend
    days = row.get('days_above_sma_50', 0)
    if days < 0:
        s += min(25, abs(days) * 0.4)
    
    # Breakdown magnitude
    pct_50 = row.get('pct_from_sma_50', 0)
    if pct_50 < 0:
        s += min(25, abs(pct_50) * 0.8)
    
    # Trend confirmation (below SMA200)
    pct_200 = row.get('pct_from_sma_200', 0)
    if pct_200 < 0:
        s += min(25, 10 + abs(pct_200) * 0.5)
    elif pct_200 < 5:
        s += max(0, 5 - pct_200)
    
    return round(s, 1)


def get_stars(score):
    """Convert score to star rating."""
    if score >= 80:
        return 5
    elif score >= 65:
        return 4
    elif score >= 50:
        return 3
    elif score >= 35:
        return 2
    elif score >= 20:
        return 1
    else:
        return 0


def create_swing_portfolios():
    """Main function to create swing trade portfolios."""
    engine = get_engine()
    print("Getting sector rankings...")
    
    sector_summary = get_sector_summary(engine, sma_period=50, log_cb=lambda x: None)
    if sector_summary.empty:
        print("No sector data!")
        return
    
    mid = len(sector_summary) // 2
    strong_sectors = sector_summary.head(mid)['sector'].tolist()
    weak_sectors = sector_summary.tail(mid)['sector'].tolist()
    
    print(f"Strong sectors: {strong_sectors[:3]}...")
    print(f"Weak sectors: {weak_sectors[:3]}...")
    
    # Collect all candidates
    all_longs = []
    all_shorts = []
    
    print("\nScanning strong sectors for long candidates...")
    for sector in strong_sectors:
        df = get_sector_stocks_detail(engine, sector, sma_periods=[50, 200], log_cb=lambda x: None)
        if df.empty:
            continue
        
        breadth = sector_summary[sector_summary['sector'] == sector]['pct_above'].values[0]
        
        for _, row in df.iterrows():
            pct_50 = row.get('pct_from_sma_50', 0)
            pct_200 = row.get('pct_from_sma_200', 0)
            days_50 = row.get('days_above_sma_50', 0)
            
            if pd.isna(pct_50) or pd.isna(pct_200):
                continue
            
            # Long criteria: fresh crossover or pullback to SMA50
            is_fresh_cross = 0 < days_50 <= 15 and 0 < pct_50 < 10
            is_pullback = 0 < pct_50 < 5 and pct_200 > 0 and days_50 > 0
            
            if is_fresh_cross or is_pullback:
                score = calc_long_score(row, breadth)
                all_longs.append({
                    'symbol': row['symbol'],
                    'sector': sector,
                    'price': row['close'],
                    'pct50': pct_50,
                    'days': days_50,
                    'pct200': pct_200,
                    'score': score,
                    'stars': get_stars(score)
                })
    
    print("Scanning weak sectors for short candidates...")
    for sector in weak_sectors:
        df = get_sector_stocks_detail(engine, sector, sma_periods=[50, 200], log_cb=lambda x: None)
        if df.empty:
            continue
        
        breadth = sector_summary[sector_summary['sector'] == sector]['pct_above'].values[0]
        
        for _, row in df.iterrows():
            pct_50 = row.get('pct_from_sma_50', 0)
            pct_200 = row.get('pct_from_sma_200', 0)
            days_50 = row.get('days_above_sma_50', 0)
            
            if pd.isna(pct_50) or pd.isna(pct_200):
                continue
            
            # Short criteria: below both SMAs with persistent weakness
            if pct_50 < -5 and pct_200 < 0 and days_50 < -5:
                score = calc_short_score(row, breadth)
                all_shorts.append({
                    'symbol': row['symbol'],
                    'sector': sector,
                    'price': row['close'],
                    'pct50': pct_50,
                    'days': days_50,
                    'pct200': pct_200,
                    'score': score,
                    'stars': get_stars(score)
                })
    
    longs_df = pd.DataFrame(all_longs).sort_values('score', ascending=False)
    shorts_df = pd.DataFrame(all_shorts).sort_values('score', ascending=False)
    
    print(f"\nFound {len(longs_df)} long candidates")
    print(f"Found {len(shorts_df)} short candidates")
    
    # Create portfolio manager
    manager = PortfolioManager(db_path='portfolios.db')
    today = date.today().isoformat()
    
    # Delete existing swing portfolios
    deleted = []
    for name in list(manager.portfolios.keys()):
        if 'Swing' in name and ('Long' in name or 'Short' in name):
            manager.delete_portfolio(name)
            deleted.append(name)
    
    if deleted:
        print(f"\nDeleted {len(deleted)} existing swing portfolios")
    
    print("\n" + "="*60)
    print("CREATING PORTFOLIOS")
    print("="*60)
    
    # Create Long portfolios by rating
    for star_rating in [5, 4, 3, 2, 1]:
        group = longs_df[longs_df['stars'] == star_rating]
        if len(group) == 0:
            continue
        
        portfolio_name = f'Swing Long - Rate {star_rating}'
        portfolio = Portfolio(
            name=portfolio_name,
            portfolio_type=PortfolioType.MOMENTUM,
            description=f'Long candidates rated {star_rating} stars (Created: {today})'
        )
        
        for _, row in group.iterrows():
            position = Position(
                symbol=row['symbol'],
                entry_date=today,
                entry_price=row['price'],
                current_price=row['price'],
                scanner_score=row['score'],
                scanner_signal=f'{star_rating} STAR LONG',
                notes=f"Sector: {row['sector']}, SMA50: {row['pct50']:+.1f}%, Days: {row['days']}"
            )
            portfolio.add_position(position)
        
        manager.save_portfolio(portfolio)
        symbols = ', '.join(group['symbol'].head(5).tolist())
        more = f"... +{len(group)-5} more" if len(group) > 5 else ""
        print(f"\n✅ {portfolio_name} ({len(group)} positions)")
        print(f"   Top: {symbols}{more}")
    
    # Create Short portfolios by rating
    for star_rating in [5, 4, 3, 2, 1]:
        group = shorts_df[shorts_df['stars'] == star_rating]
        if len(group) == 0:
            continue
        
        portfolio_name = f'Swing Short - Rate {star_rating}'
        portfolio = Portfolio(
            name=portfolio_name,
            portfolio_type=PortfolioType.DISTRIBUTION,
            description=f'Short candidates rated {star_rating} stars (Created: {today})'
        )
        
        for _, row in group.iterrows():
            position = Position(
                symbol=row['symbol'],
                entry_date=today,
                entry_price=row['price'],
                current_price=row['price'],
                scanner_score=row['score'],
                scanner_signal=f'{star_rating} STAR SHORT',
                notes=f"Sector: {row['sector']}, SMA50: {row['pct50']:+.1f}%, Days: {row['days']}"
            )
            portfolio.add_position(position)
        
        manager.save_portfolio(portfolio)
        symbols = ', '.join(group['symbol'].head(5).tolist())
        more = f"... +{len(group)-5} more" if len(group) > 5 else ""
        print(f"\n✅ {portfolio_name} ({len(group)} positions)")
        print(f"   Top: {symbols}{more}")
    
    # Print summary
    print("\n" + "="*60)
    print("PORTFOLIO SUMMARY")
    print("="*60)
    
    swing_portfolios = [(name, pf) for name, pf in sorted(manager.portfolios.items()) if 'Swing' in name]
    
    total_long = 0
    total_short = 0
    
    for name, pf in swing_portfolios:
        print(f"  {name}: {pf.total_positions} positions")
        if 'Long' in name:
            total_long += pf.total_positions
        else:
            total_short += pf.total_positions
    
    print(f"\n  Total Long positions: {total_long}")
    print(f"  Total Short positions: {total_short}")
    print(f"  Total portfolios created: {len(swing_portfolios)}")
    
    print("\n✅ Done! Open Portfolio Manager GUI to view portfolios.")


if __name__ == "__main__":
    create_swing_portfolios()
