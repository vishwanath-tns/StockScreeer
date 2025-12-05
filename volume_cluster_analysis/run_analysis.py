import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from data.data_loader import VolumeDataLoader, NIFTY_50_SYMBOLS
from core.clustering import VolumeClustering
from core.price_impact import PriceImpactAnalyzer

def analyze_stock(symbol):
    print(f'Analyzing {symbol}...')
    loader = VolumeDataLoader()
    df = loader.get_stock_data(symbol)
    if df is None or len(df) < 100:
        print(f'Insufficient data for {symbol}')
        return None
    
    clustering = VolumeClustering()
    result = clustering.cluster_volumes(df, symbol=symbol)
    print(result.summary())
    
    analyzer = PriceImpactAnalyzer(df, result)
    print(analyzer.generate_impact_summary())
    return result

if __name__ == '__main__':
    symbol = sys.argv[1] if len(sys.argv) > 1 else 'RELIANCE.NS'
    analyze_stock(symbol)
