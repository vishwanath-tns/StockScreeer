"""
Market Data Correlation Engine for Moon-Zodiac Analysis

This module correlates actual market data with Moon's zodiac positions
to validate and quantify the astrological influences on price movements.

Author: Stock Screener with Vedic Astrology Integration
"""

import sys
import os
import datetime
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple, Any
import matplotlib.pyplot as plt
import seaborn as sns
from scipy import stats
import warnings
warnings.filterwarnings('ignore')

# Import database connection
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from sync_bhav_gui import engine

# Import zodiac analyzer
from moon_zodiac_analyzer import MoonZodiacAnalyzer


class MarketZodiacCorrelator:
    """Correlates market data with Moon zodiac positions"""
    
    def __init__(self):
        self.zodiac_analyzer = MoonZodiacAnalyzer()
        self.db_engine = engine()
    
    def get_market_data(self, start_date: datetime.date, 
                       end_date: datetime.date, symbols: List[str] = None) -> pd.DataFrame:
        """Get market data from database"""
        
        if symbols:
            # Use a simpler query with specific symbols
            symbol_list = "', '".join(symbols)
            query = f"""
            SELECT 
                trade_date,
                symbol,
                open_price,
                high_price,
                low_price,
                close_price,
                ttl_trd_qnty as volume,
                turnover_lacs * 100000 as turnover
            FROM nse_equity_bhavcopy_full 
            WHERE trade_date BETWEEN '{start_date}' AND '{end_date}'
            AND symbol IN ('{symbol_list}')
            AND series = 'EQ'
            ORDER BY trade_date, symbol
            """
        else:
            query = f"""
            SELECT 
                trade_date,
                symbol,
                open_price,
                high_price,
                low_price,
                close_price,
                ttl_trd_qnty as volume,
                turnover_lacs * 100000 as turnover
            FROM nse_equity_bhavcopy_full 
            WHERE trade_date BETWEEN '{start_date}' AND '{end_date}'
            AND series = 'EQ'
            ORDER BY trade_date, symbol
            LIMIT 10000
            """
        
        try:
            with self.db_engine.connect() as conn:
                df = pd.read_sql(query, conn)
            
            if df.empty:
                print(f"No market data found for period {start_date} to {end_date}")
                return pd.DataFrame()
            
            # Calculate additional metrics
            df['price_change'] = df['close_price'] - df['open_price']
            df['price_change_pct'] = (df['price_change'] / df['open_price']) * 100
            df['volatility'] = ((df['high_price'] - df['low_price']) / df['open_price']) * 100
            df['gap'] = df.groupby('symbol')['open_price'].pct_change() * 100
            
            return df
            
        except Exception as e:
            print(f"Error fetching market data: {e}")
            return pd.DataFrame()
    
    def calculate_market_indices(self, market_data: pd.DataFrame) -> pd.DataFrame:
        """Calculate daily market indices from individual stock data"""
        
        if market_data.empty:
            return pd.DataFrame()
        
        # Daily aggregations
        daily_stats = market_data.groupby('trade_date').agg({
            'price_change_pct': ['mean', 'median', 'std', 'count'],
            'volatility': ['mean', 'median', 'max'],
            'volume': 'sum',
            'turnover': 'sum',
            'symbol': 'nunique'
        }).round(4)
        
        # Flatten column names
        daily_stats.columns = ['_'.join(col).strip() for col in daily_stats.columns.values]
        daily_stats = daily_stats.reset_index()
        
        # Rename columns for clarity
        column_mapping = {
            'price_change_pct_mean': 'avg_price_change',
            'price_change_pct_median': 'median_price_change',
            'price_change_pct_std': 'price_volatility',
            'price_change_pct_count': 'stocks_traded',
            'volatility_mean': 'avg_intraday_volatility',
            'volatility_median': 'median_volatility',
            'volatility_max': 'max_volatility',
            'volume_sum': 'total_volume',
            'turnover_sum': 'total_turnover',
            'symbol_nunique': 'unique_stocks'
        }
        
        daily_stats = daily_stats.rename(columns=column_mapping)
        
        # Calculate advance/decline ratios
        advances = market_data[market_data['price_change_pct'] > 0].groupby('trade_date').size()
        declines = market_data[market_data['price_change_pct'] < 0].groupby('trade_date').size()
        unchanged = market_data[market_data['price_change_pct'] == 0].groupby('trade_date').size()
        
        ad_ratio = advances / (advances + declines)
        ad_ratio = ad_ratio.fillna(0.5)  # Handle cases with no data
        
        # Merge advance/decline data
        ad_df = pd.DataFrame({
            'trade_date': ad_ratio.index,
            'advance_decline_ratio': ad_ratio.values,
            'advancing_stocks': advances.reindex(ad_ratio.index, fill_value=0).values,
            'declining_stocks': declines.reindex(ad_ratio.index, fill_value=0).values,
            'unchanged_stocks': unchanged.reindex(ad_ratio.index, fill_value=0).values
        })
        
        # Merge with daily stats
        daily_stats = pd.merge(daily_stats, ad_df, on='trade_date', how='left')
        
        return daily_stats
    
    def correlate_with_zodiac(self, start_date: datetime.date, 
                             end_date: datetime.date, 
                             symbols: List[str] = None) -> pd.DataFrame:
        """Correlate market data with Moon zodiac positions"""
        
        print(f"Fetching market data from {start_date} to {end_date}...")
        
        # Get market data
        market_data = self.get_market_data(start_date, end_date, symbols)
        
        if market_data.empty:
            return pd.DataFrame()
        
        # Calculate daily market indices
        daily_market = self.calculate_market_indices(market_data)
        
        print(f"Analyzing zodiac positions for {len(daily_market)} trading days...")
        
        # Get zodiac analysis for each day
        zodiac_data = []
        
        for _, row in daily_market.iterrows():
            trade_date = row['trade_date']
            date_time = datetime.datetime.combine(trade_date, datetime.time(12, 0))
            
            zodiac_analysis = self.zodiac_analyzer.get_moon_zodiac_influence(date_time)
            
            if "error" not in zodiac_analysis:
                influence = self.zodiac_analyzer.zodiac_influences[zodiac_analysis['moon_sign']]
                
                zodiac_data.append({
                    'trade_date': trade_date,
                    'moon_sign': zodiac_analysis['moon_sign'],
                    'moon_degree': zodiac_analysis['moon_degree'],
                    'element': influence.element,
                    'quality': influence.quality,
                    'ruling_planet': influence.ruling_planet,
                    'predicted_volatility': influence.volatility_factor,
                    'risk_level': influence.risk_level,
                    'market_tendency': influence.market_tendency
                })
        
        # Convert to DataFrame and merge
        zodiac_df = pd.DataFrame(zodiac_data)
        
        if zodiac_df.empty:
            print("No zodiac data available")
            return pd.DataFrame()
        
        # Merge market data with zodiac data
        correlation_df = pd.merge(daily_market, zodiac_df, on='trade_date', how='inner')
        
        return correlation_df
    
    def analyze_correlations(self, correlation_df: pd.DataFrame) -> Dict[str, Any]:
        """Analyze statistical correlations between zodiac and market data"""
        
        if correlation_df.empty:
            return {"error": "No correlation data available"}
        
        results = {}
        
        # Zodiac sign analysis
        sign_analysis = correlation_df.groupby('moon_sign').agg({
            'avg_price_change': ['mean', 'std', 'count'],
            'price_volatility': ['mean', 'std'],
            'avg_intraday_volatility': ['mean', 'std'],
            'advance_decline_ratio': ['mean', 'std'],
            'total_volume': 'mean'
        }).round(4)
        
        results['zodiac_sign_analysis'] = sign_analysis.to_dict()
        
        # Element analysis
        element_analysis = correlation_df.groupby('element').agg({
            'avg_price_change': 'mean',
            'price_volatility': 'mean',
            'avg_intraday_volatility': 'mean',
            'advance_decline_ratio': 'mean'
        }).round(4)
        
        results['element_analysis'] = element_analysis.to_dict()
        
        # Statistical correlations
        numeric_cols = ['avg_price_change', 'price_volatility', 'avg_intraday_volatility', 
                       'advance_decline_ratio', 'predicted_volatility']
        
        # Create numeric encoding for categorical variables
        correlation_df['sign_numeric'] = pd.Categorical(correlation_df['moon_sign']).codes
        correlation_df['element_numeric'] = pd.Categorical(correlation_df['element']).codes
        correlation_df['quality_numeric'] = pd.Categorical(correlation_df['quality']).codes
        
        # Correlation matrix
        corr_vars = numeric_cols + ['sign_numeric', 'element_numeric', 'quality_numeric']
        correlation_matrix = correlation_df[corr_vars].corr().round(4)
        
        results['correlation_matrix'] = correlation_matrix.to_dict()
        
        # Specific hypothesis tests
        results['hypothesis_tests'] = self._test_zodiac_hypotheses(correlation_df)
        
        # Volatility prediction accuracy
        results['volatility_prediction'] = self._analyze_volatility_prediction(correlation_df)
        
        return results
    
    def _test_zodiac_hypotheses(self, df: pd.DataFrame) -> Dict[str, Dict]:
        """Test specific astrological hypotheses"""
        
        tests = {}
        
        # Test 1: Fire signs vs others volatility
        fire_signs = ['Aries', 'Leo', 'Sagittarius']
        fire_data = df[df['moon_sign'].isin(fire_signs)]['price_volatility']
        non_fire_data = df[~df['moon_sign'].isin(fire_signs)]['price_volatility']
        
        if len(fire_data) > 5 and len(non_fire_data) > 5:
            t_stat, p_value = stats.ttest_ind(fire_data, non_fire_data)
            tests['fire_signs_volatility'] = {
                'hypothesis': 'Fire signs have higher volatility',
                'fire_mean': fire_data.mean(),
                'non_fire_mean': non_fire_data.mean(),
                't_statistic': t_stat,
                'p_value': p_value,
                'significant': p_value < 0.05,
                'result': 'Confirmed' if (fire_data.mean() > non_fire_data.mean() and p_value < 0.05) else 'Not confirmed'
            }
        
        # Test 2: Water signs emotional extremes
        water_signs = ['Cancer', 'Scorpio', 'Pisces']
        water_data = df[df['moon_sign'].isin(water_signs)]['price_volatility']
        non_water_data = df[~df['moon_sign'].isin(water_signs)]['price_volatility']
        
        if len(water_data) > 5 and len(non_water_data) > 5:
            t_stat, p_value = stats.ttest_ind(water_data, non_water_data)
            tests['water_signs_emotions'] = {
                'hypothesis': 'Water signs show emotional extremes (higher volatility)',
                'water_mean': water_data.mean(),
                'non_water_mean': non_water_data.mean(),
                't_statistic': t_stat,
                'p_value': p_value,
                'significant': p_value < 0.05,
                'result': 'Confirmed' if (water_data.mean() > non_water_data.mean() and p_value < 0.05) else 'Not confirmed'
            }
        
        # Test 3: Earth signs stability
        earth_signs = ['Taurus', 'Virgo', 'Capricorn']
        earth_data = df[df['moon_sign'].isin(earth_signs)]['price_volatility']
        non_earth_data = df[~df['moon_sign'].isin(earth_signs)]['price_volatility']
        
        if len(earth_data) > 5 and len(non_earth_data) > 5:
            t_stat, p_value = stats.ttest_ind(earth_data, non_earth_data)
            tests['earth_signs_stability'] = {
                'hypothesis': 'Earth signs have lower volatility (more stable)',
                'earth_mean': earth_data.mean(),
                'non_earth_mean': non_earth_data.mean(),
                't_statistic': t_stat,
                'p_value': p_value,
                'significant': p_value < 0.05,
                'result': 'Confirmed' if (earth_data.mean() < non_earth_data.mean() and p_value < 0.05) else 'Not confirmed'
            }
        
        return tests
    
    def _analyze_volatility_prediction(self, df: pd.DataFrame) -> Dict[str, float]:
        """Analyze accuracy of volatility predictions"""
        
        if 'predicted_volatility' not in df.columns or 'price_volatility' not in df.columns:
            return {"error": "Missing volatility data"}
        
        # Correlation between predicted and actual volatility
        pred_corr = df['predicted_volatility'].corr(df['price_volatility'])
        
        # Mean absolute error
        mae = np.mean(np.abs(df['predicted_volatility'] - df['price_volatility']))
        
        # Directional accuracy (whether prediction was directionally correct)
        avg_volatility = df['price_volatility'].mean()
        pred_direction = df['predicted_volatility'] > 1.0  # Above normal
        actual_direction = df['price_volatility'] > avg_volatility
        directional_accuracy = (pred_direction == actual_direction).mean()
        
        return {
            'correlation_coefficient': pred_corr,
            'mean_absolute_error': mae,
            'directional_accuracy': directional_accuracy,
            'prediction_interpretation': self._interpret_prediction_accuracy(pred_corr, directional_accuracy)
        }
    
    def _interpret_prediction_accuracy(self, correlation: float, directional_accuracy: float) -> str:
        """Interpret prediction accuracy results"""
        
        if correlation > 0.3 and directional_accuracy > 0.6:
            return "Strong predictive power - Zodiac positions show significant correlation with volatility"
        elif correlation > 0.15 and directional_accuracy > 0.55:
            return "Moderate predictive power - Some correlation observed"
        elif directional_accuracy > 0.55:
            return "Directional value - Good at predicting volatility direction"
        else:
            return "Limited predictive power - Further analysis needed"
    
    def create_correlation_visualization(self, correlation_df: pd.DataFrame, 
                                       save_path: str = None):
        """Create comprehensive correlation visualizations"""
        
        if correlation_df.empty:
            print("No data available for visualization")
            return
        
        # Create figure with multiple subplots
        fig = plt.figure(figsize=(20, 16))
        
        # 1. Volatility by Zodiac Sign (top left)
        ax1 = plt.subplot(3, 3, 1)
        sign_volatility = correlation_df.groupby('moon_sign')['price_volatility'].mean().sort_values(ascending=False)
        colors = plt.cm.RdYlBu_r(np.linspace(0, 1, len(sign_volatility)))
        
        bars = ax1.bar(sign_volatility.index, sign_volatility.values, color=colors)
        ax1.set_title('Average Market Volatility by Moon Sign', fontweight='bold')
        ax1.set_ylabel('Volatility (%)')
        plt.setp(ax1.xaxis.get_majorticklabels(), rotation=45, ha='right')
        
        # Add value labels on bars
        for bar in bars:
            height = bar.get_height()
            ax1.text(bar.get_x() + bar.get_width()/2., height,
                    f'{height:.2f}%', ha='center', va='bottom', fontsize=9)
        
        # 2. Element Analysis (top center)
        ax2 = plt.subplot(3, 3, 2)
        element_data = correlation_df.groupby('element').agg({
            'avg_price_change': 'mean',
            'price_volatility': 'mean'
        })
        
        x = np.arange(len(element_data))
        width = 0.35
        
        ax2.bar(x - width/2, element_data['avg_price_change'], width, 
               label='Avg Price Change (%)', alpha=0.8)
        ax2.bar(x + width/2, element_data['price_volatility'], width, 
               label='Volatility (%)', alpha=0.8)
        
        ax2.set_title('Performance by Element', fontweight='bold')
        ax2.set_xlabel('Element')
        ax2.set_xticks(x)
        ax2.set_xticklabels(element_data.index)
        ax2.legend()
        ax2.grid(True, alpha=0.3)
        
        # 3. Predicted vs Actual Volatility (top right)
        ax3 = plt.subplot(3, 3, 3)
        ax3.scatter(correlation_df['predicted_volatility'], correlation_df['price_volatility'], 
                   alpha=0.6, c='purple')
        
        # Add trend line
        z = np.polyfit(correlation_df['predicted_volatility'], correlation_df['price_volatility'], 1)
        p = np.poly1d(z)
        ax3.plot(correlation_df['predicted_volatility'], p(correlation_df['predicted_volatility']), 
                "r--", alpha=0.8, linewidth=2)
        
        ax3.set_xlabel('Predicted Volatility Factor')
        ax3.set_ylabel('Actual Market Volatility (%)')
        ax3.set_title('Predicted vs Actual Volatility', fontweight='bold')
        ax3.grid(True, alpha=0.3)
        
        # Add correlation coefficient
        corr = correlation_df['predicted_volatility'].corr(correlation_df['price_volatility'])
        ax3.text(0.05, 0.95, f'Correlation: {corr:.3f}', transform=ax3.transAxes,
                bbox=dict(boxstyle="round,pad=0.3", facecolor="yellow", alpha=0.7))
        
        # 4. Advance/Decline by Sign (middle left)
        ax4 = plt.subplot(3, 3, 4)
        ad_data = correlation_df.groupby('moon_sign')['advance_decline_ratio'].mean().sort_values()
        colors = ['red' if x < 0.5 else 'green' for x in ad_data.values]
        
        ax4.barh(ad_data.index, ad_data.values, color=colors, alpha=0.7)
        ax4.axvline(x=0.5, color='black', linestyle='--', alpha=0.5, label='Neutral (50%)')
        ax4.set_title('Advance/Decline Ratio by Moon Sign', fontweight='bold')
        ax4.set_xlabel('Advance/Decline Ratio')
        ax4.legend()
        
        # 5. Time Series (middle center - span 2 columns)
        ax5 = plt.subplot(3, 3, (5, 6))
        ax5.plot(correlation_df['trade_date'], correlation_df['avg_price_change'], 
                'b-', alpha=0.7, label='Avg Price Change (%)')
        ax5.fill_between(correlation_df['trade_date'], 
                        correlation_df['avg_price_change'] - correlation_df['price_volatility'],
                        correlation_df['avg_price_change'] + correlation_df['price_volatility'],
                        alpha=0.2, color='blue')
        
        ax5_twin = ax5.twinx()
        ax5_twin.plot(correlation_df['trade_date'], correlation_df['predicted_volatility'], 
                     'r-', alpha=0.8, label='Predicted Volatility Factor')
        
        ax5.set_title('Market Performance vs Zodiac Predictions Over Time', fontweight='bold')
        ax5.set_ylabel('Price Change (%)', color='blue')
        ax5_twin.set_ylabel('Predicted Volatility Factor', color='red')
        ax5.legend(loc='upper left')
        ax5_twin.legend(loc='upper right')
        ax5.grid(True, alpha=0.3)
        
        # 6. Risk Level Distribution (bottom left)
        ax6 = plt.subplot(3, 3, 7)
        risk_data = correlation_df['risk_level'].value_counts()
        colors = ['green', 'yellow', 'orange', 'red', 'darkred'][:len(risk_data)]
        
        wedges, texts, autotexts = ax6.pie(risk_data.values, labels=risk_data.index, 
                                          autopct='%1.1f%%', colors=colors, startangle=90)
        ax6.set_title('Risk Level Distribution', fontweight='bold')
        
        # 7. Correlation Heatmap (bottom center)
        ax7 = plt.subplot(3, 3, 8)
        corr_data = correlation_df[['avg_price_change', 'price_volatility', 'advance_decline_ratio', 
                                   'predicted_volatility']].corr()
        
        im = ax7.imshow(corr_data.values, cmap='RdBu_r', aspect='auto', vmin=-1, vmax=1)
        ax7.set_xticks(range(len(corr_data.columns)))
        ax7.set_yticks(range(len(corr_data.columns)))
        ax7.set_xticklabels([col.replace('_', '\n') for col in corr_data.columns], rotation=45, ha='right')
        ax7.set_yticklabels([col.replace('_', '\n') for col in corr_data.columns])
        ax7.set_title('Correlation Matrix', fontweight='bold')
        
        # Add correlation values to heatmap
        for i in range(len(corr_data.columns)):
            for j in range(len(corr_data.columns)):
                ax7.text(j, i, f'{corr_data.iloc[i, j]:.2f}', ha='center', va='center',
                        color='white' if abs(corr_data.iloc[i, j]) > 0.5 else 'black')
        
        # 8. Quality Analysis (bottom right)
        ax8 = plt.subplot(3, 3, 9)
        quality_data = correlation_df.groupby('quality').agg({
            'avg_price_change': 'mean',
            'price_volatility': 'mean'
        })
        
        x = np.arange(len(quality_data))
        width = 0.35
        
        ax8.bar(x - width/2, quality_data['avg_price_change'], width, 
               label='Avg Price Change (%)', alpha=0.8, color='blue')
        ax8.bar(x + width/2, quality_data['price_volatility'], width, 
               label='Volatility (%)', alpha=0.8, color='orange')
        
        ax8.set_title('Performance by Quality (Cardinal/Fixed/Mutable)', fontweight='bold')
        ax8.set_xlabel('Quality')
        ax8.set_xticks(x)
        ax8.set_xticklabels(quality_data.index)
        ax8.legend()
        ax8.grid(True, alpha=0.3)
        
        plt.tight_layout(pad=2.0)
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"Correlation analysis saved to: {save_path}")
        
        plt.show()
        return fig


def test_market_correlation():
    """Test market correlation analysis"""
    print("=== Market-Zodiac Correlation Analysis ===")
    
    correlator = MarketZodiacCorrelator()
    
    # Define analysis period
    start_date = datetime.date(2025, 1, 1)
    end_date = datetime.date(2025, 11, 15)  # Up to current data
    
    # Popular stocks for analysis
    test_symbols = ['RELIANCE', 'TCS', 'INFY', 'HDFCBANK', 'ICICIBANK', 'SBIN', 'LT', 'BHARTIARTL']
    
    print(f"Analyzing correlation from {start_date} to {end_date}")
    print(f"Sample stocks: {', '.join(test_symbols)}")
    
    # Get correlation data
    correlation_df = correlator.correlate_with_zodiac(start_date, end_date, test_symbols)
    
    if correlation_df.empty:
        print("No correlation data available")
        return
    
    print(f"\nSuccessfully analyzed {len(correlation_df)} trading days")
    
    # Perform statistical analysis
    analysis_results = correlator.analyze_correlations(correlation_df)
    
    if "error" not in analysis_results:
        print(f"\nVOLATILITY PREDICTION RESULTS:")
        vol_pred = analysis_results.get('volatility_prediction', {})
        if 'correlation_coefficient' in vol_pred:
            print(f"Correlation Coefficient: {vol_pred['correlation_coefficient']:.4f}")
            print(f"Directional Accuracy: {vol_pred['directional_accuracy']:.1%}")
            print(f"Interpretation: {vol_pred['prediction_interpretation']}")
        
        print(f"\nHYPOTHESIS TEST RESULTS:")
        hypothesis_tests = analysis_results.get('hypothesis_tests', {})
        for test_name, test_result in hypothesis_tests.items():
            print(f"\n{test_name.replace('_', ' ').title()}:")
            print(f"  Hypothesis: {test_result['hypothesis']}")
            print(f"  Result: {test_result['result']}")
            print(f"  P-value: {test_result['p_value']:.4f}")
            print(f"  Statistically Significant: {test_result['significant']}")
        
        # Save results to CSV
        csv_path = os.path.join(os.path.dirname(__file__), 'market_zodiac_correlation.csv')
        correlation_df.to_csv(csv_path, index=False)
        print(f"\nCorrelation data saved to: {csv_path}")
        
        # Create visualization
        viz_path = os.path.join(os.path.dirname(__file__), 'market_zodiac_analysis.png')
        correlator.create_correlation_visualization(correlation_df, viz_path)
    
    print("\nMarket correlation analysis completed!")


if __name__ == "__main__":
    test_market_correlation()