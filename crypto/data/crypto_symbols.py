#!/usr/bin/env python3
"""
Top 100 Cryptocurrency Symbols
==============================

Curated list of top 100 cryptocurrencies by market cap for Yahoo Finance.

Categories:
- layer1: Base layer blockchains (BTC, ETH, SOL, etc.)
- layer2: Scaling solutions (MATIC, ARB, OP)
- defi: DeFi protocols (UNI, AAVE, MKR)
- exchange: Exchange tokens (BNB, CRO, FTT)
- meme: Meme coins (DOGE, SHIB, PEPE)
- stablecoin: Stablecoins (usually excluded from analysis)
- gaming: Gaming/Metaverse (AXS, SAND, MANA)
- infrastructure: Infrastructure (LINK, GRT, FIL)
- privacy: Privacy coins (XMR, ZEC)
- other: Other categories

Usage:
    from crypto.data.crypto_symbols import TOP_100_CRYPTOS, get_yahoo_symbols
"""

from typing import List, Dict, Tuple


# Top 100 Cryptocurrencies (as of late 2024/early 2025)
# Format: (symbol, yahoo_symbol, name, category, rank)
TOP_100_CRYPTOS: List[Tuple[str, str, str, str, int]] = [
    # Top 10 - Major Cryptocurrencies
    ("BTC", "BTC-USD", "Bitcoin", "layer1", 1),
    ("ETH", "ETH-USD", "Ethereum", "layer1", 2),
    ("BNB", "BNB-USD", "BNB", "exchange", 3),
    ("SOL", "SOL-USD", "Solana", "layer1", 4),
    ("XRP", "XRP-USD", "XRP", "layer1", 5),
    ("ADA", "ADA-USD", "Cardano", "layer1", 6),
    ("DOGE", "DOGE-USD", "Dogecoin", "meme", 7),
    ("AVAX", "AVAX-USD", "Avalanche", "layer1", 8),
    ("TRX", "TRX-USD", "TRON", "layer1", 9),
    ("DOT", "DOT-USD", "Polkadot", "layer1", 10),
    
    # 11-20
    ("LINK", "LINK-USD", "Chainlink", "infrastructure", 11),
    ("MATIC", "MATIC-USD", "Polygon", "layer2", 12),
    ("SHIB", "SHIB-USD", "Shiba Inu", "meme", 13),
    ("TON", "TON11419-USD", "Toncoin", "layer1", 14),
    ("LTC", "LTC-USD", "Litecoin", "layer1", 15),
    ("BCH", "BCH-USD", "Bitcoin Cash", "layer1", 16),
    ("ATOM", "ATOM-USD", "Cosmos", "layer1", 17),
    ("UNI", "UNI7083-USD", "Uniswap", "defi", 18),
    ("XLM", "XLM-USD", "Stellar", "layer1", 19),
    ("LEO", "LEO-USD", "UNUS SED LEO", "exchange", 20),
    
    # 21-30
    ("ETC", "ETC-USD", "Ethereum Classic", "layer1", 21),
    ("OKB", "OKB-USD", "OKB", "exchange", 22),
    ("XMR", "XMR-USD", "Monero", "privacy", 23),
    ("HBAR", "HBAR-USD", "Hedera", "layer1", 24),
    ("FIL", "FIL-USD", "Filecoin", "infrastructure", 25),
    ("APT", "APT21794-USD", "Aptos", "layer1", 26),
    ("CRO", "CRO-USD", "Cronos", "exchange", 27),
    ("ARB", "ARB11841-USD", "Arbitrum", "layer2", 28),
    ("MKR", "MKR-USD", "Maker", "defi", 29),
    ("VET", "VET-USD", "VeChain", "layer1", 30),
    
    # 31-40
    ("NEAR", "NEAR-USD", "NEAR Protocol", "layer1", 31),
    ("OP", "OP-USD", "Optimism", "layer2", 32),
    ("AAVE", "AAVE-USD", "Aave", "defi", 33),
    ("INJ", "INJ-USD", "Injective", "defi", 34),
    ("GRT", "GRT6719-USD", "The Graph", "infrastructure", 35),
    ("ALGO", "ALGO-USD", "Algorand", "layer1", 36),
    ("RUNE", "RUNE-USD", "THORChain", "defi", 37),
    ("STX", "STX4847-USD", "Stacks", "layer2", 38),
    ("FTM", "FTM-USD", "Fantom", "layer1", 39),
    ("EGLD", "EGLD-USD", "MultiversX", "layer1", 40),
    
    # 41-50
    ("IMX", "IMX10603-USD", "Immutable", "layer2", 41),
    ("THETA", "THETA-USD", "Theta Network", "infrastructure", 42),
    ("SAND", "SAND-USD", "The Sandbox", "gaming", 43),
    ("AXS", "AXS-USD", "Axie Infinity", "gaming", 44),
    ("MANA", "MANA-USD", "Decentraland", "gaming", 45),
    ("XTZ", "XTZ-USD", "Tezos", "layer1", 46),
    ("EOS", "EOS-USD", "EOS", "layer1", 47),
    ("FLOW", "FLOW-USD", "Flow", "layer1", 48),
    ("NEO", "NEO-USD", "Neo", "layer1", 49),
    ("KCS", "KCS-USD", "KuCoin Token", "exchange", 50),
    
    # 51-60
    ("KAVA", "KAVA-USD", "Kava", "defi", 51),
    ("GALA", "GALA-USD", "Gala", "gaming", 52),
    ("CHZ", "CHZ-USD", "Chiliz", "other", 53),
    ("SNX", "SNX-USD", "Synthetix", "defi", 54),
    ("ZEC", "ZEC-USD", "Zcash", "privacy", 55),
    ("CAKE", "CAKE-USD", "PancakeSwap", "defi", 56),
    ("CRV", "CRV-USD", "Curve DAO Token", "defi", 57),
    ("MINA", "MINA-USD", "Mina Protocol", "layer1", 58),
    ("XDC", "XDC-USD", "XDC Network", "layer1", 59),
    ("IOTA", "IOTA-USD", "IOTA", "infrastructure", 60),
    
    # 61-70
    ("FXS", "FXS-USD", "Frax Share", "defi", 61),
    ("LDO", "LDO-USD", "Lido DAO", "defi", 62),
    ("CFX", "CFX-USD", "Conflux", "layer1", 63),
    ("RPL", "RPL-USD", "Rocket Pool", "defi", 64),
    ("DASH", "DASH-USD", "Dash", "layer1", 65),
    ("APE", "APE18876-USD", "ApeCoin", "meme", 66),
    ("ENS", "ENS-USD", "Ethereum Name Service", "infrastructure", 67),
    ("COMP", "COMP-USD", "Compound", "defi", 68),
    ("1INCH", "1INCH-USD", "1inch", "defi", 69),
    ("DYDX", "DYDX-USD", "dYdX", "defi", 70),
    
    # 71-80
    ("GMT", "GMT-USD", "STEPN", "gaming", 71),
    ("LRC", "LRC-USD", "Loopring", "layer2", 72),
    ("ENJ", "ENJ-USD", "Enjin Coin", "gaming", 73),
    ("BAT", "BAT-USD", "Basic Attention Token", "infrastructure", 74),
    ("ZIL", "ZIL-USD", "Zilliqa", "layer1", 75),
    ("CELO", "CELO-USD", "Celo", "layer1", 76),
    ("ICX", "ICX-USD", "ICON", "layer1", 77),
    ("ONE", "ONE-USD", "Harmony", "layer1", 78),
    ("QTUM", "QTUM-USD", "Qtum", "layer1", 79),
    ("ANKR", "ANKR-USD", "Ankr", "infrastructure", 80),
    
    # 81-90
    ("MASK", "MASK-USD", "Mask Network", "infrastructure", 81),
    ("SUI", "SUI20947-USD", "Sui", "layer1", 82),
    ("SEI", "SEI-USD", "Sei", "layer1", 83),
    ("BLUR", "BLUR-USD", "Blur", "other", 84),
    ("WOO", "WOO-USD", "WOO Network", "defi", 85),
    ("ROSE", "ROSE-USD", "Oasis Network", "layer1", 86),
    ("SKL", "SKL-USD", "SKALE", "layer2", 87),
    ("GLM", "GLM-USD", "Golem", "infrastructure", 88),
    ("SSV", "SSV-USD", "SSV Network", "infrastructure", 89),
    ("AUDIO", "AUDIO-USD", "Audius", "other", 90),
    
    # 91-100
    ("YFI", "YFI-USD", "yearn.finance", "defi", 91),
    ("OSMO", "OSMO-USD", "Osmosis", "defi", 92),
    ("STORJ", "STORJ-USD", "Storj", "infrastructure", 93),
    ("RVN", "RVN-USD", "Ravencoin", "layer1", 94),
    ("SC", "SC-USD", "Siacoin", "infrastructure", 95),
    ("ZRX", "ZRX-USD", "0x", "defi", 96),
    ("WAVES", "WAVES-USD", "Waves", "layer1", 97),
    ("PEPE", "PEPE24478-USD", "Pepe", "meme", 98),
    ("FLOKI", "FLOKI-USD", "Floki", "meme", 99),
    ("BONK", "BONK-USD", "Bonk", "meme", 100),
]


def get_all_symbols() -> List[str]:
    """Get list of base symbols (BTC, ETH, etc.)."""
    return [crypto[0] for crypto in TOP_100_CRYPTOS]


def get_yahoo_symbols() -> List[str]:
    """Get list of Yahoo Finance symbols (BTC-USD, ETH-USD, etc.)."""
    return [crypto[1] for crypto in TOP_100_CRYPTOS]


def get_symbols_by_category(category: str) -> List[Tuple[str, str, str]]:
    """Get symbols filtered by category.
    
    Args:
        category: One of layer1, layer2, defi, exchange, meme, gaming, infrastructure, privacy, other
        
    Returns:
        List of (symbol, yahoo_symbol, name) tuples
    """
    return [(c[0], c[1], c[2]) for c in TOP_100_CRYPTOS if c[3] == category]


def get_symbol_info(symbol: str) -> Dict:
    """Get detailed info for a specific symbol.
    
    Args:
        symbol: Base symbol (BTC) or Yahoo symbol (BTC-USD)
        
    Returns:
        Dictionary with symbol details or None if not found
    """
    symbol = symbol.upper()
    for crypto in TOP_100_CRYPTOS:
        if crypto[0] == symbol or crypto[1] == symbol:
            return {
                "symbol": crypto[0],
                "yahoo_symbol": crypto[1],
                "name": crypto[2],
                "category": crypto[3],
                "rank": crypto[4]
            }
    return None


def get_categories() -> List[str]:
    """Get list of all categories."""
    return list(set(crypto[3] for crypto in TOP_100_CRYPTOS))


def get_category_counts() -> Dict[str, int]:
    """Get count of cryptos per category."""
    counts = {}
    for crypto in TOP_100_CRYPTOS:
        cat = crypto[3]
        counts[cat] = counts.get(cat, 0) + 1
    return counts


def symbol_to_yahoo(symbol: str) -> str:
    """Convert base symbol to Yahoo Finance format.
    
    Args:
        symbol: Base symbol like BTC
        
    Returns:
        Yahoo symbol like BTC-USD
    """
    info = get_symbol_info(symbol)
    return info["yahoo_symbol"] if info else f"{symbol}-USD"


def yahoo_to_symbol(yahoo_symbol: str) -> str:
    """Convert Yahoo symbol to base symbol.
    
    Args:
        yahoo_symbol: Yahoo symbol like BTC-USD
        
    Returns:
        Base symbol like BTC
    """
    info = get_symbol_info(yahoo_symbol)
    return info["symbol"] if info else yahoo_symbol.split("-")[0]


# Quick lookup dictionaries
SYMBOL_TO_YAHOO = {c[0]: c[1] for c in TOP_100_CRYPTOS}
YAHOO_TO_SYMBOL = {c[1]: c[0] for c in TOP_100_CRYPTOS}
SYMBOL_TO_NAME = {c[0]: c[2] for c in TOP_100_CRYPTOS}


if __name__ == "__main__":
    # Print summary
    print("🪙 Top 100 Cryptocurrencies for Analysis")
    print("=" * 60)
    
    print(f"\nTotal: {len(TOP_100_CRYPTOS)} cryptocurrencies")
    
    print("\n📊 By Category:")
    for cat, count in sorted(get_category_counts().items(), key=lambda x: -x[1]):
        print(f"  {cat}: {count}")
    
    print("\n🔝 Top 10:")
    for crypto in TOP_100_CRYPTOS[:10]:
        print(f"  {crypto[4]:2}. {crypto[0]:6} - {crypto[2]:20} ({crypto[3]})")
    
    print("\n📝 Sample Yahoo symbols:")
    print(f"  {', '.join(get_yahoo_symbols()[:10])}")
