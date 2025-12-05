import numpy as np
import pandas as pd
from typing import Tuple, List, Dict, Optional
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)

@dataclass
class VolumeCluster:
    cluster_id: int
    name: str
    min_volume: int
    max_volume: int
    mean_volume: float
    median_volume: float
    std_volume: float
    count: int
    percentage: float

@dataclass
class ClusteringResult:
    symbol: str
    total_days: int
    date_range: Tuple[str, str]
    n_clusters: int
    clusters: List[VolumeCluster]
    cluster_labels: np.ndarray
    silhouette_score: float
    inertia: float
    
    def summary(self):
        lines = [f"\n{'='*60}", f"Volume Clustering: {self.symbol}", f"{'='*60}",
                 f"Period: {self.date_range[0]} to {self.date_range[1]}",
                 f"Days: {self.total_days:,}", f"Clusters: {self.n_clusters}",
                 f"Silhouette: {self.silhouette_score:.3f}", "\nCluster Details:", "-"*60]
        for c in sorted(self.clusters, key=lambda x: x.mean_volume):
            lines.append(f"  {c.name:12} | Avg: {c.mean_volume:>12,.0f} | Days: {c.count:>5} ({c.percentage:>5.1f}%)")
        return "\n".join(lines)

class VolumeClustering:
    CLUSTER_NAMES = {
        2: ["Low", "High"], 3: ["Low", "Normal", "High"],
        4: ["Very Low", "Low", "High", "Very High"],
        5: ["Very Low", "Low", "Normal", "High", "Very High"]
    }
    
    def __init__(self, max_clusters=6, random_state=42):
        self.max_clusters = max_clusters
        self.random_state = random_state
    
    def find_optimal_clusters(self, volumes):
        log_volumes = np.log1p(volumes).reshape(-1, 1)
        scores = {}
        for k in range(2, self.max_clusters + 1):
            kmeans = KMeans(n_clusters=k, random_state=self.random_state, n_init=10)
            labels = kmeans.fit_predict(log_volumes)
            scores[k] = silhouette_score(log_volumes, labels)
        return max(scores, key=scores.get), scores
    
    def cluster_volumes(self, df, n_clusters=None, symbol="UNKNOWN"):
        volumes = df['volume'].values
        log_volumes = np.log1p(volumes).reshape(-1, 1)
        if n_clusters is None:
            n_clusters, _ = self.find_optimal_clusters(volumes)
        kmeans = KMeans(n_clusters=n_clusters, random_state=self.random_state, n_init=10)
        labels = kmeans.fit_predict(log_volumes)
        sil_score = silhouette_score(log_volumes, labels)
        
        clusters = []
        for i in range(n_clusters):
            mask = labels == i
            cv = volumes[mask]
            clusters.append(VolumeCluster(cluster_id=i, name=f"C{i}", min_volume=int(cv.min()),
                max_volume=int(cv.max()), mean_volume=float(cv.mean()), median_volume=float(np.median(cv)),
                std_volume=float(cv.std()), count=int(mask.sum()), percentage=float(mask.sum()/len(volumes)*100)))
        
        clusters.sort(key=lambda x: x.mean_volume)
        names = self.CLUSTER_NAMES.get(n_clusters, [f"C{i}" for i in range(n_clusters)])
        id_to_sorted = {c.cluster_id: i for i, c in enumerate(clusters)}
        sorted_labels = np.array([id_to_sorted[l] for l in labels])
        for i, c in enumerate(clusters):
            c.name = names[i]
            c.cluster_id = i
        
        return ClusteringResult(symbol=symbol, total_days=len(volumes),
            date_range=(str(df.index.min().date()), str(df.index.max().date())),
            n_clusters=n_clusters, clusters=clusters, cluster_labels=sorted_labels,
            silhouette_score=sil_score, inertia=kmeans.inertia_)

class ConsecutiveClusterAnalyzer:
    @staticmethod
    def find_consecutive_runs(labels):
        runs = []
        if len(labels) == 0:
            return runs
        start_idx, current = 0, labels[0]
        for i in range(1, len(labels)):
            if labels[i] != current:
                runs.append({'cluster_id': int(current), 'start_idx': start_idx, 'end_idx': i-1, 'length': i-start_idx})
                start_idx, current = i, labels[i]
        runs.append({'cluster_id': int(current), 'start_idx': start_idx, 'end_idx': len(labels)-1, 'length': len(labels)-start_idx})
        return runs
