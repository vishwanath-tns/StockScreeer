#!/usr/bin/env python3
"""
Rankings Export Module

Provides comprehensive export functionality for stock rankings.
Supports multiple formats (CSV, Excel, JSON) with filtering and formatting options.

Features:
- Export to CSV, Excel, JSON
- Apply filters before export
- Multiple preset export templates
- Scheduled/automated exports
- Email integration (optional)
"""

import os
from datetime import datetime, date
from typing import Optional, List, Dict, Any
from pathlib import Path
import pandas as pd

from ..db.ranking_repository import RankingRepository
from ..db.schema import get_ranking_engine


class RankingsExporter:
    """
    Export rankings to various formats with filtering options.
    
    Supports:
    - CSV exports (lightweight)
    - Excel exports (formatted with multiple sheets)
    - JSON exports (for API/web consumption)
    """
    
    def __init__(self, engine=None, output_dir: str = None):
        """
        Initialize exporter.
        
        Args:
            engine: SQLAlchemy engine. Creates from env if not provided.
            output_dir: Default output directory. Uses 'exports/' if not provided.
        """
        self.engine = engine or get_ranking_engine()
        self.repo = RankingRepository(self.engine)
        
        # Set default output directory
        if output_dir:
            self.output_dir = Path(output_dir)
        else:
            project_root = Path(__file__).parent.parent.parent
            self.output_dir = project_root / "exports" / "rankings"
        
        # Create output directory if needed
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    # -------------------------------------------------------------------------
    # Export Methods
    # -------------------------------------------------------------------------
    
    def export_csv(
        self,
        filepath: str = None,
        calculation_date: date = None,
        filters: Dict[str, Any] = None,
        columns: List[str] = None,
    ) -> str:
        """
        Export rankings to CSV file.
        
        Args:
            filepath: Output file path. Auto-generates if not provided.
            calculation_date: Date to export. Uses latest if not provided.
            filters: Optional filters to apply.
            columns: Optional list of columns to include.
            
        Returns:
            Path to exported file.
        """
        df = self._get_filtered_data(calculation_date, filters)
        
        if columns:
            df = df[[c for c in columns if c in df.columns]]
        
        if filepath is None:
            date_str = calculation_date.strftime("%Y%m%d") if calculation_date else "latest"
            filepath = self.output_dir / f"rankings_{date_str}.csv"
        
        df.to_csv(filepath, index=False)
        return str(filepath)
    
    def export_excel(
        self,
        filepath: str = None,
        calculation_date: date = None,
        include_sheets: List[str] = None,
    ) -> str:
        """
        Export rankings to Excel with multiple sheets.
        
        Args:
            filepath: Output file path. Auto-generates if not provided.
            calculation_date: Date to export. Uses latest if not provided.
            include_sheets: List of sheets to include. Options:
                - "all_rankings": Full rankings table
                - "top_50": Top 50 by composite score
                - "trend_leaders": Stocks with trend_template >= 6
                - "rs_leaders": Stocks with RS >= 80
                - "summary": Summary statistics
                
        Returns:
            Path to exported file.
        """
        if include_sheets is None:
            include_sheets = ["all_rankings", "top_50", "trend_leaders", "summary"]
        
        # Get data
        all_data = self._get_filtered_data(calculation_date, None)
        
        if filepath is None:
            date_str = calculation_date.strftime("%Y%m%d") if calculation_date else "latest"
            filepath = self.output_dir / f"rankings_{date_str}.xlsx"
        
        with pd.ExcelWriter(filepath, engine="openpyxl") as writer:
            # All rankings
            if "all_rankings" in include_sheets:
                all_data.to_excel(writer, sheet_name="All Rankings", index=False)
            
            # Top 50
            if "top_50" in include_sheets:
                top_50 = all_data.nsmallest(50, "composite_rank")
                top_50.to_excel(writer, sheet_name="Top 50", index=False)
            
            # Trend leaders (>=6 conditions)
            if "trend_leaders" in include_sheets:
                trend_leaders = all_data[all_data["trend_template_score"] >= 6]
                trend_leaders = trend_leaders.sort_values("composite_rank")
                trend_leaders.to_excel(writer, sheet_name="Trend Leaders", index=False)
            
            # RS leaders (>=80)
            if "rs_leaders" in include_sheets:
                rs_leaders = all_data[all_data["rs_rating"] >= 80]
                rs_leaders = rs_leaders.sort_values("rs_rating", ascending=False)
                rs_leaders.to_excel(writer, sheet_name="RS Leaders", index=False)
            
            # Power stocks (multiple criteria)
            if "power_stocks" in include_sheets:
                power = all_data[
                    (all_data["rs_rating"] >= 70) &
                    (all_data["trend_template_score"] >= 6) &
                    (all_data["momentum_score"] >= 60)
                ]
                power = power.sort_values("composite_rank")
                power.to_excel(writer, sheet_name="Power Stocks", index=False)
            
            # Summary statistics
            if "summary" in include_sheets:
                summary = self._create_summary(all_data, calculation_date)
                summary.to_excel(writer, sheet_name="Summary", index=False)
        
        return str(filepath)
    
    def export_json(
        self,
        filepath: str = None,
        calculation_date: date = None,
        filters: Dict[str, Any] = None,
        orient: str = "records",
    ) -> str:
        """
        Export rankings to JSON.
        
        Args:
            filepath: Output file path. Auto-generates if not provided.
            calculation_date: Date to export. Uses latest if not provided.
            filters: Optional filters to apply.
            orient: JSON orientation (records, index, columns, etc.)
            
        Returns:
            Path to exported file.
        """
        df = self._get_filtered_data(calculation_date, filters)
        
        if filepath is None:
            date_str = calculation_date.strftime("%Y%m%d") if calculation_date else "latest"
            filepath = self.output_dir / f"rankings_{date_str}.json"
        
        df.to_json(filepath, orient=orient, indent=2, date_format="iso")
        return str(filepath)
    
    # -------------------------------------------------------------------------
    # Preset Exports
    # -------------------------------------------------------------------------
    
    def export_top_n(
        self,
        n: int = 50,
        score_type: str = "composite_score",
        format: str = "csv",
        filepath: str = None,
    ) -> str:
        """
        Export top N stocks by a specific score.
        
        Args:
            n: Number of stocks.
            score_type: Score to rank by.
            format: Output format (csv, excel, json).
            filepath: Output path. Auto-generates if not provided.
            
        Returns:
            Path to exported file.
        """
        df = self.repo.get_top_stocks_by_score(score_type, n)
        
        if filepath is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            ext = "xlsx" if format == "excel" else format
            filepath = self.output_dir / f"top_{n}_{score_type}_{timestamp}.{ext}"
        
        if format == "csv":
            df.to_csv(filepath, index=False)
        elif format == "excel":
            df.to_excel(filepath, index=False)
        elif format == "json":
            df.to_json(filepath, orient="records", indent=2)
        
        return str(filepath)
    
    def export_watchlist(
        self,
        min_composite_percentile: float = 80,
        min_trend: int = 5,
        format: str = "csv",
        filepath: str = None,
    ) -> str:
        """
        Export a watchlist of strong stocks.
        
        Args:
            min_composite_percentile: Minimum percentile.
            min_trend: Minimum trend template score.
            format: Output format.
            filepath: Output path.
            
        Returns:
            Path to exported file.
        """
        filters = {
            "min_composite_percentile": min_composite_percentile,
            "min_trend_template": min_trend,
        }
        
        df = self._get_filtered_data(None, filters)
        
        if filepath is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            ext = "xlsx" if format == "excel" else format
            filepath = self.output_dir / f"watchlist_{timestamp}.{ext}"
        
        # Select watchlist columns
        watchlist_cols = [
            "symbol", "composite_rank", "composite_score", "rs_rating",
            "momentum_score", "trend_template_score", "technical_score"
        ]
        df = df[[c for c in watchlist_cols if c in df.columns]]
        
        if format == "csv":
            df.to_csv(filepath, index=False)
        elif format == "excel":
            df.to_excel(filepath, index=False)
        elif format == "json":
            df.to_json(filepath, orient="records", indent=2)
        
        return str(filepath)
    
    def export_daily_report(
        self,
        calculation_date: date = None,
        output_dir: str = None,
    ) -> Dict[str, str]:
        """
        Generate comprehensive daily export (multiple files).
        
        Args:
            calculation_date: Date for report. Uses latest if not provided.
            output_dir: Output directory. Uses default if not provided.
            
        Returns:
            Dict mapping file type to path.
        """
        out_dir = Path(output_dir) if output_dir else self.output_dir
        date_str = calculation_date.strftime("%Y%m%d") if calculation_date else datetime.now().strftime("%Y%m%d")
        
        # Create dated subfolder
        report_dir = out_dir / date_str
        report_dir.mkdir(parents=True, exist_ok=True)
        
        exported_files = {}
        
        # Full Excel report
        exported_files["excel_full"] = self.export_excel(
            filepath=str(report_dir / f"full_report_{date_str}.xlsx"),
            calculation_date=calculation_date,
            include_sheets=["all_rankings", "top_50", "trend_leaders", "rs_leaders", "power_stocks", "summary"]
        )
        
        # Top 50 CSV
        exported_files["csv_top50"] = self.export_top_n(
            n=50,
            format="csv",
            filepath=str(report_dir / f"top_50_{date_str}.csv")
        )
        
        # Watchlist CSV
        exported_files["csv_watchlist"] = self.export_watchlist(
            min_composite_percentile=70,
            min_trend=5,
            format="csv",
            filepath=str(report_dir / f"watchlist_{date_str}.csv")
        )
        
        # JSON for web/API
        exported_files["json_all"] = self.export_json(
            filepath=str(report_dir / f"rankings_{date_str}.json"),
            calculation_date=calculation_date
        )
        
        return exported_files
    
    # -------------------------------------------------------------------------
    # Helper Methods
    # -------------------------------------------------------------------------
    
    def _get_filtered_data(
        self,
        calculation_date: date = None,
        filters: Dict[str, Any] = None,
    ) -> pd.DataFrame:
        """Get filtered rankings data."""
        if calculation_date:
            df = self.repo.get_rankings_for_date(calculation_date)
        else:
            df = self.repo.get_latest_rankings(limit=1000)
        
        if filters and not df.empty:
            if "min_rs_rating" in filters:
                df = df[df["rs_rating"] >= filters["min_rs_rating"]]
            if "min_momentum_score" in filters:
                df = df[df["momentum_score"] >= filters["min_momentum_score"]]
            if "min_trend_template" in filters:
                df = df[df["trend_template_score"] >= filters["min_trend_template"]]
            if "min_technical_score" in filters:
                df = df[df["technical_score"] >= filters["min_technical_score"]]
            if "min_composite_score" in filters:
                df = df[df["composite_score"] >= filters["min_composite_score"]]
            if "min_composite_percentile" in filters:
                df = df[df["composite_percentile"] >= filters["min_composite_percentile"]]
            if "symbols" in filters:
                df = df[df["symbol"].isin(filters["symbols"])]
        
        return df
    
    def _create_summary(self, df: pd.DataFrame, calc_date: date = None) -> pd.DataFrame:
        """Create summary statistics DataFrame."""
        if df.empty:
            return pd.DataFrame()
        
        summary_data = [
            {"Metric": "Report Date", "Value": str(calc_date or datetime.now().date())},
            {"Metric": "Total Stocks", "Value": len(df)},
            {"Metric": "Avg Composite Score", "Value": f"{df['composite_score'].mean():.2f}"},
            {"Metric": "Avg RS Rating", "Value": f"{df['rs_rating'].mean():.2f}"},
            {"Metric": "Avg Momentum Score", "Value": f"{df['momentum_score'].mean():.2f}"},
            {"Metric": "Stocks with Trend >= 6", "Value": len(df[df['trend_template_score'] >= 6])},
            {"Metric": "Stocks with RS >= 80", "Value": len(df[df['rs_rating'] >= 80])},
            {"Metric": "Stocks with Momentum >= 70", "Value": len(df[df['momentum_score'] >= 70])},
        ]
        
        return pd.DataFrame(summary_data)
    
    def list_exports(self) -> List[Dict[str, Any]]:
        """List all exported files in output directory."""
        exports = []
        
        for f in self.output_dir.rglob("*"):
            if f.is_file() and f.suffix in [".csv", ".xlsx", ".json"]:
                exports.append({
                    "name": f.name,
                    "path": str(f),
                    "size": f.stat().st_size,
                    "modified": datetime.fromtimestamp(f.stat().st_mtime),
                    "type": f.suffix[1:].upper(),
                })
        
        return sorted(exports, key=lambda x: x["modified"], reverse=True)


def main():
    """Demo export functionality."""
    print("=== Rankings Exporter Demo ===\n")
    
    exporter = RankingsExporter()
    
    # Export top 50
    print("Exporting top 50 stocks...")
    try:
        path = exporter.export_top_n(n=50, format="csv")
        print(f"  ✓ Saved to: {path}")
    except Exception as e:
        print(f"  ✗ Error: {e}")
    
    # Export watchlist
    print("\nExporting watchlist...")
    try:
        path = exporter.export_watchlist(min_composite_percentile=70, min_trend=5)
        print(f"  ✓ Saved to: {path}")
    except Exception as e:
        print(f"  ✗ Error: {e}")
    
    print("\n=== Done ===")


if __name__ == "__main__":
    main()
