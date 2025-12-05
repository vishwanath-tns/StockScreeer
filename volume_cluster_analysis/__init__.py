"""
Volume Cluster Analysis Module

Analyzes volume patterns to understand which volume levels move stock prices.
Uses K-means clustering to identify volume regimes and measures price impact.

Key Components:
- data/: Data loading from MySQL database
- core/: Clustering algorithms and price impact analysis
- visualization/: Charts and reports

Usage:
    from volume_cluster_analysis import VolumeClusterAnalysis
    
    analysis = VolumeClusterAnalysis()
    result = analysis.analyze_stock('RELIANCE.NS')
    print(result['summary'])
"""

__version__ = '1.0.0'
__author__ = 'StockScreener Project'
