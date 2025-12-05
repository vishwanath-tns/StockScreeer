import numpy as np
import pandas as pd
from typing import List, Tuple
from dataclasses import dataclass
from .clustering import ClusteringResult, ConsecutiveClusterAnalyzer

@dataclass
class PriceImpact:
    cluster_id: int
    cluster_name: str
    avg_return: float
    median_return: float
    positive_days_pct: float
    next_day_avg_return: float
    five_day_avg_return: float
    count: int

@dataclass
class ConsecutiveDayImpact:
    cluster_id: int
    cluster_name: str
    consecutive_days: int
    avg_period_return: float
    avg_next_day_return: float
    next_day_positive_pct: float
    occurrences: int

class PriceImpactAnalyzer:
    def __init__(self, df, cluster_result):
        self.df = df.copy()
        self.cluster_result = cluster_result
        self.df['cluster'] = cluster_result.cluster_labels
        self.df['cluster_name'] = self.df['cluster'].map({c.cluster_id: c.name for c in cluster_result.clusters})
        self.df['next_day_return'] = self.df['returns'].shift(-1)
        self.df['next_5day_return'] = self.df['close'].pct_change(5).shift(-5)
    
    def analyze_cluster_impact(self):
        impacts = []
        for cluster in self.cluster_result.clusters:
            mask = self.df['cluster'] == cluster.cluster_id
            cdf = self.df[mask]
            ret = cdf['returns'].dropna()
            nd = cdf['next_day_return'].dropna()
            fd = cdf['next_5day_return'].dropna()
            impacts.append(PriceImpact(
                cluster_id=cluster.cluster_id, cluster_name=cluster.name,
                avg_return=float(ret.mean()*100) if len(ret)>0 else 0,
                median_return=float(ret.median()*100) if len(ret)>0 else 0,
                positive_days_pct=float((ret>0).mean()*100) if len(ret)>0 else 0,
                next_day_avg_return=float(nd.mean()*100) if len(nd)>0 else 0,
                five_day_avg_return=float(fd.mean()*100) if len(fd)>0 else 0,
                count=len(cdf)
            ))
        return impacts
    
    def analyze_consecutive_impact(self, max_consecutive=5):
        analyzer = ConsecutiveClusterAnalyzer()
        runs = analyzer.find_consecutive_runs(self.cluster_result.cluster_labels)
        impacts = []
        for cluster in self.cluster_result.clusters:
            cluster_runs = [r for r in runs if r['cluster_id'] == cluster.cluster_id]
            for consec in range(1, max_consecutive + 1):
                matching = [r for r in cluster_runs if r['length'] >= consec]
                if not matching:
                    continue
                period_rets, next_rets = [], []
                for run in matching:
                    end_idx = min(run['start_idx'] + consec - 1, run['end_idx'])
                    if run['start_idx'] < len(self.df):
                        start_close = self.df.iloc[run['start_idx']]['close']
                        end_close = self.df.iloc[end_idx]['close']
                        period_rets.append(end_close/start_close - 1)
                        post_idx = end_idx + 1
                        if post_idx < len(self.df):
                            next_rets.append(self.df.iloc[post_idx]['returns'])
                if period_rets:
                    impacts.append(ConsecutiveDayImpact(
                        cluster_id=cluster.cluster_id, cluster_name=cluster.name,
                        consecutive_days=consec, avg_period_return=float(np.mean(period_rets)*100),
                        avg_next_day_return=float(np.mean(next_rets)*100) if next_rets else 0,
                        next_day_positive_pct=float(np.mean([r>0 for r in next_rets])*100) if next_rets else 0,
                        occurrences=len(matching)
                    ))
        return impacts
    
    def generate_impact_summary(self):
        ci = self.analyze_cluster_impact()
        lines = [f"\n{'='*60}", f"Price Impact: {self.cluster_result.symbol}", f"{'='*60}"]
        lines.append(f"{'Cluster':<12} {'Avg%':>8} {'Med%':>8} {'Up%':>8} {'Next%':>8} {'5D%':>8}")
        lines.append("-"*56)
        for i in sorted(ci, key=lambda x: x.cluster_id):
            lines.append(f"{i.cluster_name:<12} {i.avg_return:>8.2f} {i.median_return:>8.2f} {i.positive_days_pct:>8.1f} {i.next_day_avg_return:>8.2f} {i.five_day_avg_return:>8.2f}")
        return "\n".join(lines)
    
    def to_dataframe(self):
        ci = self.analyze_cluster_impact()
        cdf = pd.DataFrame([{'cluster_id': i.cluster_id, 'cluster_name': i.cluster_name,
            'avg_return_pct': i.avg_return, 'positive_days_pct': i.positive_days_pct,
            'next_day_avg_return': i.next_day_avg_return, 'five_day_avg_return': i.five_day_avg_return,
            'count': i.count} for i in ci])
        consec = self.analyze_consecutive_impact()
        consec_df = pd.DataFrame([{'cluster_id': i.cluster_id, 'cluster_name': i.cluster_name,
            'consecutive_days': i.consecutive_days, 'avg_next_day_return': i.avg_next_day_return,
            'next_day_positive_pct': i.next_day_positive_pct, 'occurrences': i.occurrences} for i in consec])
        return cdf, consec_df
