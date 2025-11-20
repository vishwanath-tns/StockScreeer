"""
Momentum Reporting Service
========================

Comprehensive reporting system for momentum analysis with multiple report types and formats.
Provides various momentum analysis reports including top performers, sector analysis, 
comparative studies, and trend identification.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import pandas as pd
import numpy as np
from datetime import date, timedelta, datetime
from typing import Dict, List, Optional, Tuple, Any, Union
from dataclasses import dataclass
from enum import Enum
import logging
import json
from decimal import Decimal

from services.momentum.momentum_calculator import MomentumCalculator, MomentumDuration, MomentumResult
from services.momentum.database_service import DatabaseService

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ReportFormat(Enum):
    """Supported report output formats"""
    CONSOLE = "console"
    CSV = "csv"
    JSON = "json"
    HTML = "html"
    MARKDOWN = "markdown"

class ReportType(Enum):
    """Available momentum report types"""
    TOP_PERFORMERS = "top_performers"
    MOMENTUM_SUMMARY = "momentum_summary"
    CROSS_DURATION_ANALYSIS = "cross_duration_analysis"
    MOMENTUM_HEATMAP = "momentum_heatmap"
    STRENGTH_DISTRIBUTION = "strength_distribution"
    VOLUME_MOMENTUM_CORRELATION = "volume_momentum_correlation"
    COMPARATIVE_ANALYSIS = "comparative_analysis"

@dataclass
class ReportConfig:
    """Configuration for momentum reports"""
    report_type: ReportType
    duration_types: List[MomentumDuration]
    top_n: int = 20
    calculation_date: Optional[date] = None
    output_format: ReportFormat = ReportFormat.CONSOLE
    output_file: Optional[str] = None
    include_negative: bool = True
    min_trading_days: int = 5

@dataclass
class MomentumSummary:
    """Summary statistics for momentum analysis"""
    duration_type: str
    calculation_date: date
    total_stocks: int
    positive_count: int
    negative_count: int
    avg_momentum: float
    median_momentum: float
    std_deviation: float
    max_gain: float
    max_loss: float
    strong_positive: int  # > 10%
    strong_negative: int  # < -10%
    
    @property
    def positive_ratio(self) -> float:
        """Percentage of stocks with positive momentum"""
        return (self.positive_count / self.total_stocks * 100) if self.total_stocks > 0 else 0
    
    @property
    def market_sentiment(self) -> str:
        """Qualitative assessment of market sentiment"""
        if self.positive_ratio >= 80:
            return "Very Bullish"
        elif self.positive_ratio >= 65:
            return "Bullish"
        elif self.positive_ratio >= 50:
            return "Neutral Positive"
        elif self.positive_ratio >= 35:
            return "Neutral Negative"
        elif self.positive_ratio >= 20:
            return "Bearish"
        else:
            return "Very Bearish"

class MomentumReportingService:
    """Comprehensive momentum reporting service"""
    
    def __init__(self):
        self.db_service = DatabaseService()
        self.calculator = MomentumCalculator()
        
    def generate_report(self, config: ReportConfig) -> str:
        """
        Generate momentum report based on configuration
        
        Args:
            config: Report configuration
            
        Returns:
            Report content as string
        """
        logger.info(f"📊 Generating {config.report_type.value} report")
        
        # Get report data based on type
        if config.report_type == ReportType.TOP_PERFORMERS:
            data = self._generate_top_performers_data(config)
            content = self._format_top_performers_report(data, config)
        elif config.report_type == ReportType.MOMENTUM_SUMMARY:
            data = self._generate_momentum_summary_data(config)
            content = self._format_momentum_summary_report(data, config)
        elif config.report_type == ReportType.CROSS_DURATION_ANALYSIS:
            data = self._generate_cross_duration_data(config)
            content = self._format_cross_duration_report(data, config)
        elif config.report_type == ReportType.MOMENTUM_HEATMAP:
            data = self._generate_heatmap_data(config)
            content = self._format_heatmap_report(data, config)
        elif config.report_type == ReportType.STRENGTH_DISTRIBUTION:
            data = self._generate_strength_distribution_data(config)
            content = self._format_strength_distribution_report(data, config)
        elif config.report_type == ReportType.VOLUME_MOMENTUM_CORRELATION:
            data = self._generate_volume_correlation_data(config)
            content = self._format_volume_correlation_report(data, config)
        elif config.report_type == ReportType.COMPARATIVE_ANALYSIS:
            data = self._generate_comparative_analysis_data(config)
            content = self._format_comparative_analysis_report(data, config)
        else:
            raise ValueError(f"Unsupported report type: {config.report_type}")
        
        # Save to file if specified
        if config.output_file:
            self._save_report_to_file(content, config.output_file, config.output_format)
            logger.info(f"💾 Report saved to: {config.output_file}")
        
        return content
    
    def _get_momentum_data(self, config: ReportConfig) -> List[Dict[str, Any]]:
        """Retrieve momentum data from database based on config"""
        
        calculation_date = config.calculation_date or self.db_service.get_latest_calculation_date()
        
        if not calculation_date:
            logger.error("❌ No momentum data found in database")
            return []
        
        duration_values = [d.value for d in config.duration_types] if config.duration_types else None
        
        # Build query
        query = """
        SELECT 
            symbol, duration_type, duration_days, start_date, end_date, 
            calculation_date, start_price, end_price, percentage_change,
            avg_volume, total_volume, volume_surge_factor, 
            price_volatility, trading_days
        FROM momentum_analysis 
        WHERE calculation_date = %s
        """
        
        params = [calculation_date]
        
        if duration_values:
            query += f" AND duration_type IN ({','.join(['%s'] * len(duration_values))})"
            params.extend(duration_values)
        
        if config.min_trading_days > 0:
            query += " AND trading_days >= %s"
            params.append(config.min_trading_days)
        
        query += " ORDER BY duration_type, percentage_change DESC"
        
        data = self.db_service.execute_query(query, tuple(params))
        logger.info(f"📈 Retrieved {len(data)} momentum records")
        
        return data
    
    def _generate_top_performers_data(self, config: ReportConfig) -> Dict[str, Any]:
        """Generate data for top performers report"""
        
        data = self._get_momentum_data(config)
        
        if not data:
            return {"error": "No data available"}
        
        # Group by duration
        duration_groups = {}
        for record in data:
            duration = record['duration_type']
            if duration not in duration_groups:
                duration_groups[duration] = []
            duration_groups[duration].append(record)
        
        # Get top performers for each duration
        top_performers = {}
        for duration, records in duration_groups.items():
            # Sort by percentage change
            sorted_records = sorted(records, key=lambda x: float(x['percentage_change']), reverse=True)
            
            top_gainers = sorted_records[:config.top_n]
            top_losers = sorted_records[-config.top_n:] if config.include_negative else []
            
            top_performers[duration] = {
                "gainers": top_gainers,
                "losers": list(reversed(top_losers)),
                "total_count": len(records)
            }
        
        return {
            "top_performers": top_performers,
            "config": {
                "include_negative": config.include_negative,
                "top_n": config.top_n
            },
            "generated_at": datetime.now()
        }
    
    def _generate_momentum_summary_data(self, config: ReportConfig) -> Dict[str, Any]:
        """Generate data for momentum summary report"""
        
        data = self._get_momentum_data(config)
        
        if not data:
            return {"error": "No data available"}
        
        # Group by duration and calculate summary statistics
        duration_summaries = {}
        
        for duration in set(record['duration_type'] for record in data):
            duration_data = [record for record in data if record['duration_type'] == duration]
            
            if not duration_data:
                continue
            
            percentages = [float(record['percentage_change']) for record in duration_data]
            
            positive_count = sum(1 for p in percentages if p > 0)
            negative_count = sum(1 for p in percentages if p < 0)
            strong_positive = sum(1 for p in percentages if p > 10)
            strong_negative = sum(1 for p in percentages if p < -10)
            
            summary = MomentumSummary(
                duration_type=duration,
                calculation_date=duration_data[0]['calculation_date'],
                total_stocks=len(percentages),
                positive_count=positive_count,
                negative_count=negative_count,
                avg_momentum=np.mean(percentages),
                median_momentum=np.median(percentages),
                std_deviation=np.std(percentages),
                max_gain=max(percentages),
                max_loss=min(percentages),
                strong_positive=strong_positive,
                strong_negative=strong_negative
            )
            
            duration_summaries[duration] = summary
        
        return {
            "summaries": duration_summaries,
            "config": config,
            "generated_at": datetime.now()
        }
    
    def _generate_cross_duration_data(self, config: ReportConfig) -> Dict[str, Any]:
        """Generate data for cross duration analysis"""
        
        data = self._get_momentum_data(config)
        
        if not data:
            return {"error": "No data available"}
        
        # Create cross-duration matrix for each symbol
        symbol_momentum = {}
        
        for record in data:
            symbol = record['symbol']
            duration = record['duration_type']
            momentum = float(record['percentage_change'])
            
            if symbol not in symbol_momentum:
                symbol_momentum[symbol] = {}
            
            symbol_momentum[symbol][duration] = momentum
        
        # Analyze momentum consistency across durations
        consistent_performers = []
        for symbol, momentums in symbol_momentum.items():
            if len(momentums) >= 2:  # At least 2 durations
                values = list(momentums.values())
                
                # Check for consistent direction
                all_positive = all(v > 0 for v in values)
                all_negative = all(v < 0 for v in values)
                
                if all_positive or all_negative:
                    avg_momentum = np.mean(values)
                    momentum_range = max(values) - min(values)
                    
                    consistent_performers.append({
                        "symbol": symbol,
                        "momentums": momentums,
                        "avg_momentum": avg_momentum,
                        "momentum_range": momentum_range,
                        "consistent_direction": "positive" if all_positive else "negative",
                        "strength": "strong" if abs(avg_momentum) > 5 else "moderate"
                    })
        
        # Sort by average momentum strength
        consistent_performers.sort(key=lambda x: abs(x["avg_momentum"]), reverse=True)
        
        return {
            "cross_duration_data": symbol_momentum,
            "consistent_performers": consistent_performers[:config.top_n],
            "config": config,
            "generated_at": datetime.now()
        }
    
    def _generate_heatmap_data(self, config: ReportConfig) -> Dict[str, Any]:
        """Generate data for momentum heatmap"""
        
        data = self._get_momentum_data(config)
        
        if not data:
            return {"error": "No data available"}
        
        # Create heatmap matrix
        symbols = sorted(set(record['symbol'] for record in data))
        durations = sorted(set(record['duration_type'] for record in data))
        
        # Create matrix
        heatmap_matrix = []
        for symbol in symbols[:config.top_n]:  # Limit to top N for readability
            row = []
            symbol_data = [r for r in data if r['symbol'] == symbol]
            
            for duration in durations:
                duration_record = next((r for r in symbol_data if r['duration_type'] == duration), None)
                momentum = float(duration_record['percentage_change']) if duration_record else None
                row.append(momentum)
            
            heatmap_matrix.append(row)
        
        return {
            "heatmap_matrix": heatmap_matrix,
            "symbols": symbols[:config.top_n],
            "durations": durations,
            "config": config,
            "generated_at": datetime.now()
        }
    
    def _generate_strength_distribution_data(self, config: ReportConfig) -> Dict[str, Any]:
        """Generate data for momentum strength distribution analysis"""
        
        data = self._get_momentum_data(config)
        
        if not data:
            return {"error": "No data available"}
        
        # Define strength categories
        strength_categories = {
            "Extreme Positive": (50, 1000),
            "Very Strong Positive": (25, 50),
            "Strong Positive": (15, 25),
            "Moderate Positive": (5, 15),
            "Weak Positive": (0, 5),
            "Weak Negative": (-5, 0),
            "Moderate Negative": (-15, -5),
            "Strong Negative": (-25, -15),
            "Very Strong Negative": (-50, -25),
            "Extreme Negative": (-1000, -50)
        }
        
        # Analyze distribution by duration
        duration_distributions = {}
        
        for duration in set(record['duration_type'] for record in data):
            duration_data = [record for record in data if record['duration_type'] == duration]
            
            distribution = {}
            for category, (min_val, max_val) in strength_categories.items():
                count = sum(1 for record in duration_data 
                           if min_val < float(record['percentage_change']) <= max_val)
                distribution[category] = {
                    "count": count,
                    "percentage": (count / len(duration_data) * 100) if duration_data else 0
                }
            
            duration_distributions[duration] = distribution
        
        return {
            "strength_distributions": duration_distributions,
            "strength_categories": strength_categories,
            "config": config,
            "generated_at": datetime.now()
        }
    
    def _generate_volume_correlation_data(self, config: ReportConfig) -> Dict[str, Any]:
        """Generate data for volume-momentum correlation analysis"""
        
        data = self._get_momentum_data(config)
        
        if not data:
            return {"error": "No data available"}
        
        # Analyze volume correlation by duration
        correlations = {}
        
        for duration in set(record['duration_type'] for record in data):
            duration_data = [record for record in data if record['duration_type'] == duration]
            
            # Filter records with valid volume data
            valid_data = [r for r in duration_data if r['volume_surge_factor'] is not None]
            
            if len(valid_data) < 5:  # Need minimum data points for correlation
                continue
            
            momentums = [float(r['percentage_change']) for r in valid_data]
            volume_factors = [float(r['volume_surge_factor']) for r in valid_data]
            
            # Calculate correlation
            correlation = np.corrcoef(momentums, volume_factors)[0, 1]
            
            # Categorize high volume momentum stocks
            high_volume_momentum = []
            for record in valid_data:
                momentum = float(record['percentage_change'])
                volume_factor = float(record['volume_surge_factor'])
                
                if abs(momentum) > 5 and volume_factor > 1.5:  # High momentum with high volume
                    high_volume_momentum.append({
                        "symbol": record['symbol'],
                        "momentum": momentum,
                        "volume_factor": volume_factor,
                        "quality_score": abs(momentum) * volume_factor
                    })
            
            # Sort by quality score
            high_volume_momentum.sort(key=lambda x: x["quality_score"], reverse=True)
            
            correlations[duration] = {
                "correlation": correlation,
                "sample_size": len(valid_data),
                "high_volume_momentum": high_volume_momentum[:config.top_n]
            }
        
        return {
            "volume_correlations": correlations,
            "config": config,
            "generated_at": datetime.now()
        }
    
    def _generate_comparative_analysis_data(self, config: ReportConfig) -> Dict[str, Any]:
        """Generate data for comparative analysis across timeframes"""
        
        data = self._get_momentum_data(config)
        
        if not data:
            return {"error": "No data available"}
        
        # Compare short-term vs long-term momentum
        short_term = ['1W', '1M']
        long_term = ['3M', '6M', '9M', '12M']
        
        comparative_analysis = {
            "short_vs_long_correlation": {},
            "momentum_leaders": {},
            "trend_consistency": {}
        }
        
        # Group data by symbol
        symbol_data = {}
        for record in data:
            symbol = record['symbol']
            if symbol not in symbol_data:
                symbol_data[symbol] = {}
            symbol_data[symbol][record['duration_type']] = float(record['percentage_change'])
        
        # Analyze momentum leaders in each category
        for symbol, momentums in symbol_data.items():
            short_momentums = [momentums.get(d) for d in short_term if d in momentums]
            long_momentums = [momentums.get(d) for d in long_term if d in momentums]
            
            if short_momentums and long_momentums:
                short_avg = np.mean([m for m in short_momentums if m is not None])
                long_avg = np.mean([m for m in long_momentums if m is not None])
                
                comparative_analysis["momentum_leaders"][symbol] = {
                    "short_term_avg": short_avg,
                    "long_term_avg": long_avg,
                    "momentum_difference": short_avg - long_avg,
                    "trend_alignment": "aligned" if (short_avg > 0) == (long_avg > 0) else "divergent"
                }
        
        return {
            "comparative_analysis": comparative_analysis,
            "config": config,
            "generated_at": datetime.now()
        }
    
    def _format_top_performers_report(self, data: Dict[str, Any], config: ReportConfig) -> str:
        """Format top performers report"""
        
        if "error" in data:
            return f"❌ Error: {data['error']}"
        
        if config.output_format == ReportFormat.CONSOLE:
            return self._format_top_performers_console(data)
        elif config.output_format == ReportFormat.CSV:
            return self._format_top_performers_csv(data)
        elif config.output_format == ReportFormat.JSON:
            return self._format_top_performers_json(data)
        elif config.output_format == ReportFormat.MARKDOWN:
            return self._format_top_performers_markdown(data)
        else:
            return self._format_top_performers_console(data)
    
    def _format_top_performers_console(self, data: Dict[str, Any]) -> str:
        """Format top performers report for console output"""
        
        lines = []
        lines.append("🏆 TOP MOMENTUM PERFORMERS REPORT")
        lines.append("=" * 60)
        lines.append(f"Generated: {data['generated_at'].strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("")
        
        for duration, performers in data['top_performers'].items():
            lines.append(f"📊 {duration} MOMENTUM ({performers['total_count']} stocks)")
            lines.append("-" * 40)
            
            if performers['gainers']:
                lines.append("🚀 TOP GAINERS:")
                for i, stock in enumerate(performers['gainers'][:10], 1):
                    momentum = float(stock['percentage_change'])
                    lines.append(f"  {i:2d}. {stock['symbol']:<12} {momentum:+7.2f}% "
                               f"(₹{float(stock['start_price']):.2f} → ₹{float(stock['end_price']):.2f}) "
                               f"[{stock['trading_days']} days]")
            
            if performers['losers'] and data.get('config', {}).get('include_negative', True):
                lines.append("")
                lines.append("📉 TOP LOSERS:")
                for i, stock in enumerate(performers['losers'][:10], 1):
                    momentum = float(stock['percentage_change'])
                    lines.append(f"  {i:2d}. {stock['symbol']:<12} {momentum:+7.2f}% "
                               f"(₹{float(stock['start_price']):.2f} → ₹{float(stock['end_price']):.2f}) "
                               f"[{stock['trading_days']} days]")
            
            lines.append("")
        
        return "\n".join(lines)
    
    def _format_momentum_summary_report(self, data: Dict[str, Any], config: ReportConfig) -> str:
        """Format momentum summary report"""
        
        if "error" in data:
            return f"❌ Error: {data['error']}"
        
        if config.output_format == ReportFormat.CONSOLE:
            return self._format_momentum_summary_console(data)
        else:
            return self._format_momentum_summary_console(data)  # Default to console
    
    def _format_momentum_summary_console(self, data: Dict[str, Any]) -> str:
        """Format momentum summary report for console output"""
        
        lines = []
        lines.append("📈 MOMENTUM SUMMARY REPORT")
        lines.append("=" * 60)
        lines.append(f"Generated: {data['generated_at'].strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("")
        
        for duration, summary in data['summaries'].items():
            lines.append(f"⏱️  {duration} MOMENTUM SUMMARY")
            lines.append("-" * 30)
            lines.append(f"📅 Analysis Date: {summary.calculation_date}")
            lines.append(f"📊 Total Stocks: {summary.total_stocks}")
            lines.append(f"📈 Positive: {summary.positive_count} ({summary.positive_ratio:.1f}%)")
            lines.append(f"📉 Negative: {summary.negative_count} ({100-summary.positive_ratio:.1f}%)")
            lines.append(f"🎯 Market Sentiment: {summary.market_sentiment}")
            lines.append("")
            lines.append(f"📏 Statistics:")
            lines.append(f"   Average: {summary.avg_momentum:+.2f}%")
            lines.append(f"   Median:  {summary.median_momentum:+.2f}%")
            lines.append(f"   Std Dev: {summary.std_deviation:.2f}%")
            lines.append(f"   Range:   {summary.max_loss:.2f}% to {summary.max_gain:.2f}%")
            lines.append("")
            lines.append(f"💪 Strength Distribution:")
            lines.append(f"   Strong Positive (>10%):  {summary.strong_positive} stocks")
            lines.append(f"   Strong Negative (<-10%): {summary.strong_negative} stocks")
            lines.append("")
        
        return "\n".join(lines)
    
    def _format_cross_duration_report(self, data: Dict[str, Any], config: ReportConfig) -> str:
        """Format cross duration analysis report"""
        
        if "error" in data:
            return f"❌ Error: {data['error']}"
        
        lines = []
        lines.append("🔄 CROSS-DURATION MOMENTUM ANALYSIS")
        lines.append("=" * 60)
        lines.append(f"Generated: {data['generated_at'].strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("")
        
        lines.append("🎯 CONSISTENT MOMENTUM PERFORMERS")
        lines.append("-" * 40)
        
        for i, performer in enumerate(data['consistent_performers'][:15], 1):
            lines.append(f"{i:2d}. {performer['symbol']:<12} "
                        f"({performer['consistent_direction'].upper()}) "
                        f"Avg: {performer['avg_momentum']:+.2f}% "
                        f"Range: {performer['momentum_range']:.2f}%")
            
            # Show momentum across durations
            momentum_str = "    "
            for duration in ['1W', '1M', '3M', '6M', '9M', '12M']:
                if duration in performer['momentums']:
                    momentum_str += f"{duration}: {performer['momentums'][duration]:+.1f}%  "
            lines.append(momentum_str)
            lines.append("")
        
        return "\n".join(lines)
    
    def _format_heatmap_report(self, data: Dict[str, Any], config: ReportConfig) -> str:
        """Format momentum heatmap report"""
        
        if "error" in data:
            return f"❌ Error: {data['error']}"
        
        lines = []
        lines.append("🔥 MOMENTUM HEATMAP ANALYSIS")
        lines.append("=" * 60)
        lines.append(f"Generated: {data['generated_at'].strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("")
        
        # Create text-based heatmap
        durations = data['durations']
        symbols = data['symbols']
        matrix = data['heatmap_matrix']
        
        # Header
        header = "Symbol".ljust(12)
        for duration in durations:
            header += duration.center(8)
        lines.append(header)
        lines.append("-" * len(header))
        
        # Data rows
        for i, symbol in enumerate(symbols):
            row = symbol.ljust(12)
            for j, momentum in enumerate(matrix[i]):
                if momentum is not None:
                    # Color coding with text symbols
                    if momentum > 10:
                        cell = f"🔥{momentum:+4.1f}".center(8)
                    elif momentum > 5:
                        cell = f"🚀{momentum:+4.1f}".center(8)
                    elif momentum > 0:
                        cell = f"📈{momentum:+4.1f}".center(8)
                    elif momentum > -5:
                        cell = f"📉{momentum:+4.1f}".center(8)
                    elif momentum > -10:
                        cell = f"⬇️{momentum:+4.1f}".center(8)
                    else:
                        cell = f"🔴{momentum:+4.1f}".center(8)
                else:
                    cell = "N/A".center(8)
                row += cell
            lines.append(row)
        
        lines.append("")
        lines.append("Legend:")
        lines.append("🔥 >10%  🚀 5-10%  📈 0-5%  📉 0 to -5%  ⬇️ -5 to -10%  🔴 <-10%")
        
        return "\n".join(lines)
    
    def _format_strength_distribution_report(self, data: Dict[str, Any], config: ReportConfig) -> str:
        """Format strength distribution report"""
        
        if "error" in data:
            return f"❌ Error: {data['error']}"
        
        lines = []
        lines.append("💪 MOMENTUM STRENGTH DISTRIBUTION")
        lines.append("=" * 60)
        lines.append(f"Generated: {data['generated_at'].strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("")
        
        for duration, distribution in data['strength_distributions'].items():
            lines.append(f"📊 {duration} STRENGTH DISTRIBUTION")
            lines.append("-" * 35)
            
            for category, stats in distribution.items():
                if stats['count'] > 0:
                    bar_length = int(stats['percentage'] / 2)  # Scale for display
                    bar = "█" * bar_length
                    lines.append(f"{category:<20} {stats['count']:3d} stocks ({stats['percentage']:5.1f}%) {bar}")
            lines.append("")
        
        return "\n".join(lines)
    
    def _format_volume_correlation_report(self, data: Dict[str, Any], config: ReportConfig) -> str:
        """Format volume correlation report"""
        
        if "error" in data:
            return f"❌ Error: {data['error']}"
        
        lines = []
        lines.append("📊 VOLUME-MOMENTUM CORRELATION ANALYSIS")
        lines.append("=" * 60)
        lines.append(f"Generated: {data['generated_at'].strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("")
        
        for duration, analysis in data['volume_correlations'].items():
            lines.append(f"⏱️  {duration} VOLUME CORRELATION")
            lines.append("-" * 30)
            lines.append(f"📈 Correlation: {analysis['correlation']:.3f}")
            lines.append(f"📊 Sample Size: {analysis['sample_size']}")
            lines.append("")
            
            if analysis['high_volume_momentum']:
                lines.append("🎯 HIGH QUALITY MOMENTUM (High Volume + High Movement):")
                for i, stock in enumerate(analysis['high_volume_momentum'][:10], 1):
                    lines.append(f"  {i:2d}. {stock['symbol']:<12} "
                               f"Momentum: {stock['momentum']:+6.2f}% "
                               f"Volume Factor: {stock['volume_factor']:.2f}x "
                               f"Quality: {stock['quality_score']:.1f}")
            lines.append("")
        
        return "\n".join(lines)
    
    def _format_comparative_analysis_report(self, data: Dict[str, Any], config: ReportConfig) -> str:
        """Format comparative analysis report"""
        
        if "error" in data:
            return f"❌ Error: {data['error']}"
        
        lines = []
        lines.append("🔄 COMPARATIVE MOMENTUM ANALYSIS")
        lines.append("=" * 60)
        lines.append(f"Generated: {data['generated_at'].strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("")
        
        # Analyze momentum leaders
        leaders = data['comparative_analysis']['momentum_leaders']
        
        # Sort by momentum difference
        aligned_leaders = [(symbol, stats) for symbol, stats in leaders.items() 
                          if stats['trend_alignment'] == 'aligned']
        divergent_leaders = [(symbol, stats) for symbol, stats in leaders.items() 
                            if stats['trend_alignment'] == 'divergent']
        
        aligned_leaders.sort(key=lambda x: abs(x[1]['short_term_avg']), reverse=True)
        divergent_leaders.sort(key=lambda x: abs(x[1]['momentum_difference']), reverse=True)
        
        lines.append("🎯 ALIGNED MOMENTUM LEADERS (Short & Long Term Same Direction)")
        lines.append("-" * 55)
        for symbol, stats in aligned_leaders[:10]:
            direction = "📈" if stats['short_term_avg'] > 0 else "📉"
            lines.append(f"{direction} {symbol:<12} "
                        f"Short: {stats['short_term_avg']:+6.2f}% "
                        f"Long: {stats['long_term_avg']:+6.2f}% "
                        f"Diff: {stats['momentum_difference']:+6.2f}%")
        
        lines.append("")
        lines.append("⚡ DIVERGENT MOMENTUM PATTERNS (Short vs Long Term)")
        lines.append("-" * 45)
        for symbol, stats in divergent_leaders[:10]:
            lines.append(f"🔄 {symbol:<12} "
                        f"Short: {stats['short_term_avg']:+6.2f}% "
                        f"Long: {stats['long_term_avg']:+6.2f}% "
                        f"Diff: {stats['momentum_difference']:+6.2f}%")
        
        return "\n".join(lines)
    
    def _format_top_performers_csv(self, data: Dict[str, Any]) -> str:
        """Format top performers report as CSV"""
        
        lines = []
        lines.append("Duration,Type,Rank,Symbol,Momentum%,StartPrice,EndPrice,TradingDays")
        
        for duration, performers in data['top_performers'].items():
            # Gainers
            for i, stock in enumerate(performers['gainers'], 1):
                lines.append(f"{duration},Gainer,{i},{stock['symbol']},"
                           f"{float(stock['percentage_change']):.2f},"
                           f"{float(stock['start_price']):.2f},"
                           f"{float(stock['end_price']):.2f},"
                           f"{stock['trading_days']}")
            
            # Losers
            for i, stock in enumerate(performers['losers'], 1):
                lines.append(f"{duration},Loser,{i},{stock['symbol']},"
                           f"{float(stock['percentage_change']):.2f},"
                           f"{float(stock['start_price']):.2f},"
                           f"{float(stock['end_price']):.2f},"
                           f"{stock['trading_days']}")
        
        return "\n".join(lines)
    
    def _format_top_performers_json(self, data: Dict[str, Any]) -> str:
        """Format top performers report as JSON"""
        
        # Convert Decimal objects to float for JSON serialization
        def convert_decimals(obj):
            if isinstance(obj, Decimal):
                return float(obj)
            elif isinstance(obj, dict):
                return {k: convert_decimals(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [convert_decimals(item) for item in obj]
            elif isinstance(obj, datetime):
                return obj.isoformat()
            return obj
        
        json_data = convert_decimals(data)
        return json.dumps(json_data, indent=2, default=str)
    
    def _format_top_performers_markdown(self, data: Dict[str, Any]) -> str:
        """Format top performers report as Markdown"""
        
        lines = []
        lines.append("# 🏆 Top Momentum Performers Report")
        lines.append("")
        lines.append(f"**Generated:** {data['generated_at'].strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("")
        
        for duration, performers in data['top_performers'].items():
            lines.append(f"## 📊 {duration} Momentum ({performers['total_count']} stocks)")
            lines.append("")
            
            if performers['gainers']:
                lines.append("### 🚀 Top Gainers")
                lines.append("")
                lines.append("| Rank | Symbol | Momentum% | Price Change | Trading Days |")
                lines.append("|------|--------|-----------|--------------|--------------|")
                
                for i, stock in enumerate(performers['gainers'][:10], 1):
                    momentum = float(stock['percentage_change'])
                    start_price = float(stock['start_price'])
                    end_price = float(stock['end_price'])
                    lines.append(f"| {i} | {stock['symbol']} | {momentum:+.2f}% | "
                               f"₹{start_price:.2f} → ₹{end_price:.2f} | {stock['trading_days']} |")
                lines.append("")
            
            if performers['losers'] and data.get('config', {}).get('include_negative', True):
                lines.append("### 📉 Top Losers")
                lines.append("")
                lines.append("| Rank | Symbol | Momentum% | Price Change | Trading Days |")
                lines.append("|------|--------|-----------|--------------|--------------|")
                
                for i, stock in enumerate(performers['losers'][:10], 1):
                    momentum = float(stock['percentage_change'])
                    start_price = float(stock['start_price'])
                    end_price = float(stock['end_price'])
                    lines.append(f"| {i} | {stock['symbol']} | {momentum:+.2f}% | "
                               f"₹{start_price:.2f} → ₹{end_price:.2f} | {stock['trading_days']} |")
                lines.append("")
        
        return "\n".join(lines)
    
    def _save_report_to_file(self, content: str, filename: str, format_type: ReportFormat):
        """Save report content to file"""
        
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(content)
        except Exception as e:
            logger.error(f"❌ Error saving report to {filename}: {e}")

def main():
    """Test the momentum reporting service"""
    
    print("📊 MOMENTUM REPORTING SERVICE TEST")
    print("=" * 50)
    
    # Initialize reporting service
    reporting_service = MomentumReportingService()
    
    # Test different report types
    test_configs = [
        ReportConfig(
            report_type=ReportType.TOP_PERFORMERS,
            duration_types=[MomentumDuration.ONE_WEEK, MomentumDuration.ONE_MONTH],
            top_n=10,
            output_format=ReportFormat.CONSOLE
        ),
        ReportConfig(
            report_type=ReportType.MOMENTUM_SUMMARY,
            duration_types=[MomentumDuration.ONE_WEEK, MomentumDuration.ONE_MONTH],
            output_format=ReportFormat.CONSOLE
        ),
        ReportConfig(
            report_type=ReportType.CROSS_DURATION_ANALYSIS,
            duration_types=[MomentumDuration.ONE_WEEK, MomentumDuration.ONE_MONTH],
            top_n=10,
            output_format=ReportFormat.CONSOLE
        )
    ]
    
    # Generate reports
    for i, config in enumerate(test_configs, 1):
        print(f"\n[{i}/{len(test_configs)}] Generating {config.report_type.value} report...")
        
        try:
            report = reporting_service.generate_report(config)
            print("\n" + report)
            print("\n" + "="*80)
        except Exception as e:
            print(f"❌ Error generating report: {e}")
            import traceback
            traceback.print_exc()
    
    print(f"\n🏆 MOMENTUM REPORTING SERVICE TEST COMPLETE!")

if __name__ == "__main__":
    main()