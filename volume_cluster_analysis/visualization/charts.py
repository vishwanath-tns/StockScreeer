"""
Volume Cluster Visualization Charts
Provides matplotlib-based visualizations for volume cluster analysis.
"""

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
import pandas as pd
from typing import List, Optional, Dict, Tuple

# Color scheme for volume clusters
CLUSTER_COLORS = {
    'Very Low': '#2196F3',   # Blue
    'Low': '#4CAF50',        # Green
    'Normal': '#FFC107',     # Amber
    'High': '#FF9800',       # Orange
    'Very High': '#F44336',  # Red
}


def get_cluster_color(cluster_name: str) -> str:
    """Get color for a cluster name."""
    return CLUSTER_COLORS.get(cluster_name, '#9E9E9E')


class VolumeClusterVisualizer:
    """Visualizer for volume cluster analysis results."""
    
    def __init__(self, figsize: Tuple[int, int] = (14, 10)):
        self.figsize = figsize
        self.style = 'seaborn-v0_8-whitegrid'
    
    def plot_volume_distribution(self, df: pd.DataFrame, cluster_result, 
                                  ax: Optional[plt.Axes] = None) -> plt.Axes:
        """Plot volume distribution with cluster colors."""
        if ax is None:
            fig, ax = plt.subplots(figsize=(10, 6))
        
        volumes = df['volume'].values
        labels = cluster_result.cluster_labels
        
        for cluster in cluster_result.clusters:
            mask = labels == cluster.cluster_id
            cluster_volumes = volumes[mask]
            ax.hist(cluster_volumes, bins=30, alpha=0.6, 
                   label=f'{cluster.name} ({cluster.count})',
                   color=get_cluster_color(cluster.name))
        
        ax.set_xlabel('Volume')
        ax.set_ylabel('Frequency')
        ax.set_title(f'{cluster_result.symbol} - Volume Distribution by Cluster')
        ax.legend()
        ax.ticklabel_format(style='plain', axis='x')
        
        return ax
    
    def plot_log_volume_distribution(self, df: pd.DataFrame, cluster_result,
                                      ax: Optional[plt.Axes] = None) -> plt.Axes:
        """Plot log-transformed volume distribution."""
        if ax is None:
            fig, ax = plt.subplots(figsize=(10, 6))
        
        log_volumes = np.log1p(df['volume'].values)
        labels = cluster_result.cluster_labels
        
        for cluster in cluster_result.clusters:
            mask = labels == cluster.cluster_id
            cluster_log_volumes = log_volumes[mask]
            ax.hist(cluster_log_volumes, bins=30, alpha=0.6,
                   label=f'{cluster.name}',
                   color=get_cluster_color(cluster.name))
        
        ax.set_xlabel('Log(Volume + 1)')
        ax.set_ylabel('Frequency')
        ax.set_title(f'{cluster_result.symbol} - Log Volume Distribution')
        ax.legend()
        
        return ax
    
    def plot_volume_time_series(self, df: pd.DataFrame, cluster_result,
                                 ax: Optional[plt.Axes] = None,
                                 last_n_days: int = 252) -> plt.Axes:
        """Plot volume time series with cluster coloring."""
        if ax is None:
            fig, ax = plt.subplots(figsize=(14, 6))
        
        plot_df = df.tail(last_n_days).copy()
        plot_labels = cluster_result.cluster_labels[-last_n_days:]
        
        # Map labels to colors
        cluster_name_map = {c.cluster_id: c.name for c in cluster_result.clusters}
        colors = [get_cluster_color(cluster_name_map.get(l, 'Normal')) for l in plot_labels]
        
        ax.bar(range(len(plot_df)), plot_df['volume'].values, color=colors, alpha=0.7)
        
        # Add moving average line
        if 'volume_ma_20' in plot_df.columns:
            ax.plot(range(len(plot_df)), plot_df['volume_ma_20'].values, 
                   color='black', linewidth=1.5, label='20-day MA')
        
        ax.set_xlabel('Days')
        ax.set_ylabel('Volume')
        ax.set_title(f'{cluster_result.symbol} - Volume Time Series (Last {last_n_days} Days)')
        
        # Create legend
        patches = [mpatches.Patch(color=get_cluster_color(c.name), label=c.name, alpha=0.7)
                  for c in cluster_result.clusters]
        ax.legend(handles=patches, loc='upper right')
        
        return ax
    
    def plot_price_with_volume_clusters(self, df: pd.DataFrame, cluster_result,
                                         ax: Optional[plt.Axes] = None,
                                         last_n_days: int = 252) -> plt.Axes:
        """Plot price chart with volume cluster overlay."""
        if ax is None:
            fig, ax = plt.subplots(figsize=(14, 6))
        
        plot_df = df.tail(last_n_days).copy()
        plot_labels = cluster_result.cluster_labels[-last_n_days:]
        
        # Plot price line
        ax.plot(range(len(plot_df)), plot_df['close'].values, color='black', linewidth=1)
        
        # Highlight high volume days
        cluster_name_map = {c.cluster_id: c.name for c in cluster_result.clusters}
        
        for i, (idx, row) in enumerate(plot_df.iterrows()):
            cluster_name = cluster_name_map.get(plot_labels[i], 'Normal')
            if cluster_name in ['High', 'Very High']:
                color = get_cluster_color(cluster_name)
                ax.axvline(x=i, color=color, alpha=0.3, linewidth=1)
        
        ax.set_xlabel('Days')
        ax.set_ylabel('Price')
        ax.set_title(f'{cluster_result.symbol} - Price with High Volume Days Highlighted')
        
        return ax
    
    def plot_cluster_returns(self, impact_results: List, 
                              ax: Optional[plt.Axes] = None) -> plt.Axes:
        """Plot average returns by volume cluster."""
        if ax is None:
            fig, ax = plt.subplots(figsize=(10, 6))
        
        clusters = [i.cluster_name for i in impact_results]
        avg_returns = [i.avg_return for i in impact_results]
        colors = [get_cluster_color(name) for name in clusters]
        
        bars = ax.bar(clusters, avg_returns, color=colors, alpha=0.7, edgecolor='black')
        
        ax.axhline(y=0, color='black', linestyle='--', linewidth=1)
        ax.set_xlabel('Volume Cluster')
        ax.set_ylabel('Average Return (%)')
        ax.set_title('Average Daily Return by Volume Cluster')
        
        # Add value labels
        for bar, val in zip(bars, avg_returns):
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height,
                   f'{val:.2f}%', ha='center', va='bottom' if height >= 0 else 'top')
        
        return ax
    
    def plot_next_day_returns(self, impact_results: List,
                               ax: Optional[plt.Axes] = None) -> plt.Axes:
        """Plot next day returns following each volume cluster."""
        if ax is None:
            fig, ax = plt.subplots(figsize=(10, 6))
        
        clusters = [i.cluster_name for i in impact_results]
        next_day_returns = [i.next_day_avg_return for i in impact_results]
        colors = [get_cluster_color(name) for name in clusters]
        
        bars = ax.bar(clusters, next_day_returns, color=colors, alpha=0.7, edgecolor='black')
        
        ax.axhline(y=0, color='black', linestyle='--', linewidth=1)
        ax.set_xlabel('Volume Cluster')
        ax.set_ylabel('Next Day Avg Return (%)')
        ax.set_title('Average Next Day Return Following Each Volume Cluster')
        
        for bar, val in zip(bars, next_day_returns):
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height,
                   f'{val:.2f}%', ha='center', va='bottom' if height >= 0 else 'top')
        
        return ax
    
    def plot_positive_day_percentage(self, impact_results: List,
                                      ax: Optional[plt.Axes] = None) -> plt.Axes:
        """Plot percentage of positive return days by cluster."""
        if ax is None:
            fig, ax = plt.subplots(figsize=(10, 6))
        
        clusters = [i.cluster_name for i in impact_results]
        positive_pct = [i.positive_days_pct for i in impact_results]
        colors = [get_cluster_color(name) for name in clusters]
        
        bars = ax.bar(clusters, positive_pct, color=colors, alpha=0.7, edgecolor='black')
        
        ax.axhline(y=50, color='black', linestyle='--', linewidth=1, label='50% baseline')
        ax.set_xlabel('Volume Cluster')
        ax.set_ylabel('Positive Days (%)')
        ax.set_title('Percentage of Positive Return Days by Volume Cluster')
        ax.set_ylim(0, 100)
        
        for bar, val in zip(bars, positive_pct):
            ax.text(bar.get_x() + bar.get_width()/2., bar.get_height() + 1,
                   f'{val:.1f}%', ha='center', va='bottom')
        
        return ax
    
    def create_summary_dashboard(self, df: pd.DataFrame, cluster_result, 
                                  impact_results: List,
                                  save_path: Optional[str] = None) -> plt.Figure:
        """Create a comprehensive dashboard with all visualizations."""
        fig = plt.figure(figsize=(16, 12))
        
        # Volume distribution
        ax1 = fig.add_subplot(2, 3, 1)
        self.plot_log_volume_distribution(df, cluster_result, ax1)
        
        # Volume time series
        ax2 = fig.add_subplot(2, 3, 2)
        self.plot_volume_time_series(df, cluster_result, ax2, last_n_days=120)
        
        # Price with volume overlay
        ax3 = fig.add_subplot(2, 3, 3)
        self.plot_price_with_volume_clusters(df, cluster_result, ax3, last_n_days=120)
        
        # Cluster returns
        ax4 = fig.add_subplot(2, 3, 4)
        self.plot_cluster_returns(impact_results, ax4)
        
        # Next day returns
        ax5 = fig.add_subplot(2, 3, 5)
        self.plot_next_day_returns(impact_results, ax5)
        
        # Positive day percentage
        ax6 = fig.add_subplot(2, 3, 6)
        self.plot_positive_day_percentage(impact_results, ax6)
        
        fig.suptitle(f'{cluster_result.symbol} - Volume Cluster Analysis Dashboard', 
                    fontsize=14, fontweight='bold')
        fig.tight_layout(rect=[0, 0, 1, 0.96])
        
        if save_path:
            fig.savefig(save_path, dpi=150, bbox_inches='tight')
            print(f'Dashboard saved to {save_path}')
        
        return fig
    
    def plot_consecutive_impact_heatmap(self, consecutive_impacts: List,
                                         ax: Optional[plt.Axes] = None) -> plt.Axes:
        """Plot heatmap of returns for consecutive high volume days."""
        if ax is None:
            fig, ax = plt.subplots(figsize=(10, 6))
        
        # Organize data into matrix
        df_data = pd.DataFrame([{
            'cluster': i.cluster_name,
            'days': i.consecutive_days,
            'return': i.avg_next_day_return
        } for i in consecutive_impacts])
        
        if df_data.empty:
            ax.text(0.5, 0.5, 'No consecutive impact data', ha='center', va='center')
            return ax
        
        pivot = df_data.pivot(index='cluster', columns='days', values='return')
        
        im = ax.imshow(pivot.values, cmap='RdYlGn', aspect='auto')
        
        ax.set_xticks(range(len(pivot.columns)))
        ax.set_xticklabels([f'{d} days' for d in pivot.columns])
        ax.set_yticks(range(len(pivot.index)))
        ax.set_yticklabels(pivot.index)
        
        ax.set_xlabel('Consecutive Days')
        ax.set_ylabel('Volume Cluster')
        ax.set_title('Next Day Return After Consecutive Volume Days')
        
        plt.colorbar(im, ax=ax, label='Avg Next Day Return (%)')
        
        # Add value annotations
        for i in range(len(pivot.index)):
            for j in range(len(pivot.columns)):
                val = pivot.iloc[i, j]
                if pd.notna(val):
                    ax.text(j, i, f'{val:.2f}%', ha='center', va='center', 
                           color='white' if abs(val) > 0.5 else 'black', fontsize=9)
        
        return ax


if __name__ == '__main__':
    # Test visualization
    print("Volume Cluster Visualizer loaded successfully")
    print(f"Available colors: {CLUSTER_COLORS}")
