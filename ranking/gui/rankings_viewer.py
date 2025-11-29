#!/usr/bin/env python3
"""
Stock Rankings Viewer GUI

A comprehensive GUI for viewing, filtering, and analyzing stock rankings.
Shows RS Rating, Momentum, Trend Template, Technical, and Composite scores.

Features:
- View latest rankings with sorting
- Filter by score thresholds
- Search by symbol
- View ranking history for individual stocks
- Export to CSV/Excel
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from datetime import datetime, date
import pandas as pd
import sys
import os

# Add project root for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from ranking.db.ranking_repository import RankingRepository
from ranking.db.schema import get_ranking_engine


class RankingsViewer:
    """
    GUI for viewing and analyzing stock rankings.
    
    Features:
    - Sortable table with all ranking metrics
    - Filter controls for each score type
    - Symbol search
    - Date selection for historical views
    - Export functionality
    """
    
    def __init__(self, root: tk.Tk = None, engine=None):
        """
        Initialize the rankings viewer.
        
        Args:
            root: Optional Tk root window. Creates new one if not provided.
            engine: Optional SQLAlchemy engine. Creates from env if not provided.
        """
        self.engine = engine or get_ranking_engine()
        self.repo = RankingRepository(self.engine)
        
        # Create or use root window
        self.is_standalone = root is None
        self.root = root or tk.Tk()
        
        if self.is_standalone:
            self.root.title("Stock Rankings Viewer")
            self.root.geometry("1400x800")
        
        # Data
        self.current_df = None
        self.available_dates = []
        self.sort_column = "composite_rank"
        self.sort_reverse = False
        
        # Build UI
        self._create_ui()
        
        # Load initial data
        self._load_available_dates()
        self._refresh_data()
    
    def _create_ui(self):
        """Create the main UI layout."""
        # Main container
        self.main_frame = ttk.Frame(self.root)
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Title
        title = ttk.Label(
            self.main_frame, 
            text="📊 Stock Rankings Viewer",
            font=("Segoe UI", 16, "bold")
        )
        title.pack(pady=(0, 10))
        
        # Create sections
        self._create_controls_section()
        self._create_filter_section()
        self._create_table_section()
        self._create_status_bar()
    
    def _create_controls_section(self):
        """Create top control bar."""
        controls = ttk.Frame(self.main_frame)
        controls.pack(fill=tk.X, pady=(0, 10))
        
        # Date selection
        ttk.Label(controls, text="Date:").pack(side=tk.LEFT, padx=(0, 5))
        
        self.date_var = tk.StringVar()
        self.date_combo = ttk.Combobox(
            controls, 
            textvariable=self.date_var,
            width=15,
            state="readonly"
        )
        self.date_combo.pack(side=tk.LEFT, padx=(0, 15))
        self.date_combo.bind("<<ComboboxSelected>>", lambda e: self._refresh_data())
        
        # Search
        ttk.Label(controls, text="Search:").pack(side=tk.LEFT, padx=(0, 5))
        
        self.search_var = tk.StringVar()
        self.search_var.trace("w", lambda *args: self._apply_filters())
        
        search_entry = ttk.Entry(controls, textvariable=self.search_var, width=15)
        search_entry.pack(side=tk.LEFT, padx=(0, 15))
        
        # Sort by
        ttk.Label(controls, text="Sort by:").pack(side=tk.LEFT, padx=(0, 5))
        
        self.sort_var = tk.StringVar(value="Composite Rank")
        sort_combo = ttk.Combobox(
            controls,
            textvariable=self.sort_var,
            values=[
                "Composite Rank", "Composite Score", 
                "RS Rating", "Momentum Score",
                "Trend Template", "Technical Score",
                "Symbol"
            ],
            width=15,
            state="readonly"
        )
        sort_combo.pack(side=tk.LEFT, padx=(0, 5))
        sort_combo.bind("<<ComboboxSelected>>", lambda e: self._apply_sort())
        
        # Ascending/Descending
        self.asc_var = tk.BooleanVar(value=True)
        asc_check = ttk.Checkbutton(
            controls, 
            text="Ascending", 
            variable=self.asc_var,
            command=self._apply_sort
        )
        asc_check.pack(side=tk.LEFT, padx=(0, 15))
        
        # Refresh button
        ttk.Button(
            controls, 
            text="🔄 Refresh", 
            command=self._refresh_data
        ).pack(side=tk.LEFT, padx=(0, 5))
        
        # Export button
        ttk.Button(
            controls, 
            text="📥 Export", 
            command=self._show_export_dialog
        ).pack(side=tk.LEFT)
    
    def _create_filter_section(self):
        """Create filter controls."""
        filter_frame = ttk.LabelFrame(self.main_frame, text="Filters")
        filter_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Create filter row
        filter_row = ttk.Frame(filter_frame)
        filter_row.pack(fill=tk.X, padx=10, pady=5)
        
        # Filter variables
        self.filter_vars = {}
        
        filters = [
            ("Min RS Rating:", "min_rs", 0, 99),
            ("Min Momentum:", "min_momentum", 0, 100),
            ("Min Trend Template:", "min_trend", 0, 8),
            ("Min Technical:", "min_technical", 0, 100),
            ("Min Composite:", "min_composite", 0, 100),
            ("Top N:", "top_n", 1, 500),
        ]
        
        for i, (label, key, min_val, max_val) in enumerate(filters):
            ttk.Label(filter_row, text=label).grid(row=0, column=i*2, padx=(10, 2), sticky="e")
            
            var = tk.StringVar(value="" if key != "top_n" else "100")
            self.filter_vars[key] = var
            
            entry = ttk.Entry(filter_row, textvariable=var, width=6)
            entry.grid(row=0, column=i*2+1, padx=(0, 10))
        
        # Apply button
        ttk.Button(
            filter_row, 
            text="Apply Filters", 
            command=self._apply_filters
        ).grid(row=0, column=len(filters)*2, padx=10)
        
        # Reset button
        ttk.Button(
            filter_row,
            text="Reset",
            command=self._reset_filters
        ).grid(row=0, column=len(filters)*2+1)
        
        # Preset filters
        preset_frame = ttk.Frame(filter_frame)
        preset_frame.pack(fill=tk.X, padx=10, pady=(0, 5))
        
        ttk.Label(preset_frame, text="Presets:").pack(side=tk.LEFT, padx=(0, 10))
        
        presets = [
            ("Top 50 Composite", {"top_n": "50"}),
            ("High RS (>80)", {"min_rs": "80"}),
            ("Trend Leaders (≥6)", {"min_trend": "6"}),
            ("Power Stocks", {"min_rs": "70", "min_trend": "6", "min_momentum": "60"}),
        ]
        
        for label, values in presets:
            ttk.Button(
                preset_frame,
                text=label,
                command=lambda v=values: self._apply_preset(v)
            ).pack(side=tk.LEFT, padx=2)
    
    def _create_table_section(self):
        """Create the main data table."""
        table_frame = ttk.Frame(self.main_frame)
        table_frame.pack(fill=tk.BOTH, expand=True)
        
        # Define columns
        columns = [
            ("rank", "Rank", 60),
            ("symbol", "Symbol", 100),
            ("rs_rating", "RS Rating", 80),
            ("momentum_score", "Momentum", 80),
            ("trend_template_score", "Trend (0-8)", 80),
            ("technical_score", "Technical", 80),
            ("composite_score", "Composite", 90),
            ("composite_percentile", "Percentile", 80),
        ]
        
        # Create treeview
        self.tree = ttk.Treeview(
            table_frame,
            columns=[c[0] for c in columns],
            show="headings",
            selectmode="browse"
        )
        
        # Configure columns
        for col_id, col_name, width in columns:
            self.tree.heading(col_id, text=col_name, command=lambda c=col_id: self._on_header_click(c))
            self.tree.column(col_id, width=width, anchor=tk.CENTER)
        
        # Symbol column left-aligned
        self.tree.column("symbol", anchor=tk.W)
        
        # Scrollbars
        v_scroll = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.tree.yview)
        h_scroll = ttk.Scrollbar(table_frame, orient=tk.HORIZONTAL, command=self.tree.xview)
        self.tree.configure(yscrollcommand=v_scroll.set, xscrollcommand=h_scroll.set)
        
        # Layout
        self.tree.grid(row=0, column=0, sticky="nsew")
        v_scroll.grid(row=0, column=1, sticky="ns")
        h_scroll.grid(row=1, column=0, sticky="ew")
        
        table_frame.grid_rowconfigure(0, weight=1)
        table_frame.grid_columnconfigure(0, weight=1)
        
        # Double-click to view history
        self.tree.bind("<Double-1>", self._on_row_double_click)
        
        # Color tags
        self.tree.tag_configure("top10", background="#d4edda")
        self.tree.tag_configure("top25", background="#e8f4ea")
        self.tree.tag_configure("bottom", background="#f8d7da")
    
    def _create_status_bar(self):
        """Create status bar at bottom."""
        self.status_var = tk.StringVar(value="Ready")
        
        status_bar = ttk.Frame(self.main_frame)
        status_bar.pack(fill=tk.X, pady=(10, 0))
        
        ttk.Label(
            status_bar, 
            textvariable=self.status_var,
            font=("Segoe UI", 9)
        ).pack(side=tk.LEFT)
        
        self.count_var = tk.StringVar(value="")
        ttk.Label(
            status_bar,
            textvariable=self.count_var,
            font=("Segoe UI", 9)
        ).pack(side=tk.RIGHT)
    
    # -------------------------------------------------------------------------
    # Data Loading
    # -------------------------------------------------------------------------
    
    def _load_available_dates(self):
        """Load list of available ranking dates."""
        try:
            self.available_dates = self.repo.get_available_dates()
            if self.available_dates:
                date_strs = [d.strftime("%Y-%m-%d") for d in self.available_dates]
                self.date_combo["values"] = date_strs
                self.date_var.set(date_strs[0])  # Most recent
        except Exception as e:
            self.status_var.set(f"Error loading dates: {e}")
    
    def _refresh_data(self):
        """Refresh data from database."""
        self.status_var.set("Loading data...")
        self.root.update_idletasks()
        
        try:
            # Get selected date
            date_str = self.date_var.get()
            if date_str:
                calc_date = datetime.strptime(date_str, "%Y-%m-%d").date()
                self.current_df = self.repo.get_rankings_for_date(calc_date)
            else:
                self.current_df = self.repo.get_latest_rankings(limit=1000)
            
            self._apply_filters()
            self.status_var.set(f"Data loaded: {len(self.current_df)} stocks")
            
        except Exception as e:
            self.status_var.set(f"Error: {e}")
            messagebox.showerror("Error", f"Failed to load data: {e}")
    
    def _apply_filters(self):
        """Apply all current filters to data."""
        if self.current_df is None or self.current_df.empty:
            self._update_table(pd.DataFrame())
            return
        
        df = self.current_df.copy()
        
        # Search filter
        search = self.search_var.get().upper().strip()
        if search:
            df = df[df["symbol"].str.contains(search, na=False)]
        
        # Score filters
        filter_map = {
            "min_rs": "rs_rating",
            "min_momentum": "momentum_score",
            "min_trend": "trend_template_score",
            "min_technical": "technical_score",
            "min_composite": "composite_score",
        }
        
        for filter_key, col_name in filter_map.items():
            val = self.filter_vars[filter_key].get().strip()
            if val:
                try:
                    min_val = float(val)
                    df = df[df[col_name] >= min_val]
                except ValueError:
                    pass
        
        # Top N filter
        top_n = self.filter_vars["top_n"].get().strip()
        if top_n:
            try:
                n = int(top_n)
                df = df.head(n)
            except ValueError:
                pass
        
        self._apply_sort(df)
    
    def _apply_sort(self, df: pd.DataFrame = None):
        """Apply current sort settings."""
        if df is None:
            df = self._get_filtered_df()
        
        if df is None or df.empty:
            self._update_table(pd.DataFrame())
            return
        
        # Map sort selection to column
        sort_map = {
            "Composite Rank": "composite_rank",
            "Composite Score": "composite_score",
            "RS Rating": "rs_rating",
            "Momentum Score": "momentum_score",
            "Trend Template": "trend_template_score",
            "Technical Score": "technical_score",
            "Symbol": "symbol",
        }
        
        sort_col = sort_map.get(self.sort_var.get(), "composite_rank")
        ascending = self.asc_var.get()
        
        # For ranks, ascending=True means best (lowest) first
        # For scores, ascending=False means best (highest) first
        if sort_col in ["composite_rank", "rs_rank", "momentum_rank", "technical_rank"]:
            df = df.sort_values(sort_col, ascending=ascending)
        else:
            df = df.sort_values(sort_col, ascending=ascending)
        
        self._update_table(df)
    
    def _get_filtered_df(self) -> pd.DataFrame:
        """Get currently filtered DataFrame."""
        if self.current_df is None:
            return pd.DataFrame()
        
        df = self.current_df.copy()
        
        # Apply same filters as _apply_filters but return df
        search = self.search_var.get().upper().strip()
        if search:
            df = df[df["symbol"].str.contains(search, na=False)]
        
        filter_map = {
            "min_rs": "rs_rating",
            "min_momentum": "momentum_score",
            "min_trend": "trend_template_score",
            "min_technical": "technical_score",
            "min_composite": "composite_score",
        }
        
        for filter_key, col_name in filter_map.items():
            val = self.filter_vars[filter_key].get().strip()
            if val:
                try:
                    min_val = float(val)
                    df = df[df[col_name] >= min_val]
                except ValueError:
                    pass
        
        top_n = self.filter_vars["top_n"].get().strip()
        if top_n:
            try:
                n = int(top_n)
                df = df.head(n)
            except ValueError:
                pass
        
        return df
    
    def _update_table(self, df: pd.DataFrame):
        """Update treeview with data."""
        # Clear existing
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        if df.empty:
            self.count_var.set("0 stocks")
            return
        
        # Add rows
        for idx, row in df.iterrows():
            rank = row.get("composite_rank", idx + 1)
            
            values = (
                int(rank) if pd.notna(rank) else "",
                row.get("symbol", ""),
                f"{row.get('rs_rating', 0):.0f}" if pd.notna(row.get('rs_rating')) else "",
                f"{row.get('momentum_score', 0):.1f}" if pd.notna(row.get('momentum_score')) else "",
                f"{row.get('trend_template_score', 0):.0f}" if pd.notna(row.get('trend_template_score')) else "",
                f"{row.get('technical_score', 0):.1f}" if pd.notna(row.get('technical_score')) else "",
                f"{row.get('composite_score', 0):.1f}" if pd.notna(row.get('composite_score')) else "",
                f"{row.get('composite_percentile', 0):.1f}%" if pd.notna(row.get('composite_percentile')) else "",
            )
            
            # Color based on rank
            if rank <= 10:
                tag = "top10"
            elif rank <= 25:
                tag = "top25"
            elif rank > len(df) - 10:
                tag = "bottom"
            else:
                tag = ""
            
            self.tree.insert("", tk.END, values=values, tags=(tag,) if tag else ())
        
        self.count_var.set(f"{len(df)} stocks")
    
    # -------------------------------------------------------------------------
    # Event Handlers
    # -------------------------------------------------------------------------
    
    def _on_header_click(self, column):
        """Handle column header click for sorting."""
        col_to_name = {
            "rank": "Composite Rank",
            "symbol": "Symbol",
            "rs_rating": "RS Rating",
            "momentum_score": "Momentum Score",
            "trend_template_score": "Trend Template",
            "technical_score": "Technical Score",
            "composite_score": "Composite Score",
            "composite_percentile": "Composite Rank",
        }
        
        sort_name = col_to_name.get(column, "Composite Rank")
        
        # Toggle direction if same column
        if self.sort_var.get() == sort_name:
            self.asc_var.set(not self.asc_var.get())
        else:
            self.sort_var.set(sort_name)
        
        self._apply_sort()
    
    def _on_row_double_click(self, event):
        """Handle double-click to view stock history."""
        selection = self.tree.selection()
        if not selection:
            return
        
        item = self.tree.item(selection[0])
        symbol = item["values"][1]  # Symbol is second column
        
        if symbol:
            self._show_history_window(symbol)
    
    def _apply_preset(self, values: dict):
        """Apply a filter preset."""
        # Reset all filters first
        for key in self.filter_vars:
            self.filter_vars[key].set("")
        
        # Apply preset values
        for key, value in values.items():
            if key in self.filter_vars:
                self.filter_vars[key].set(value)
        
        self._apply_filters()
    
    def _reset_filters(self):
        """Reset all filters to defaults."""
        for key in self.filter_vars:
            self.filter_vars[key].set("")
        self.filter_vars["top_n"].set("100")
        self.search_var.set("")
        self._apply_filters()
    
    # -------------------------------------------------------------------------
    # Export Functionality
    # -------------------------------------------------------------------------
    
    def _show_export_dialog(self):
        """Show export options dialog."""
        df = self._get_filtered_df()
        if df.empty:
            messagebox.showwarning("Export", "No data to export")
            return
        
        # Ask for file type
        filetypes = [
            ("CSV files", "*.csv"),
            ("Excel files", "*.xlsx"),
        ]
        
        filename = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=filetypes,
            initialfile=f"rankings_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        )
        
        if not filename:
            return
        
        try:
            if filename.endswith(".xlsx"):
                df.to_excel(filename, index=False, sheet_name="Rankings")
            else:
                df.to_csv(filename, index=False)
            
            messagebox.showinfo("Export", f"Successfully exported {len(df)} stocks to:\n{filename}")
            
        except Exception as e:
            messagebox.showerror("Export Error", f"Failed to export: {e}")
    
    def export_to_csv(self, filepath: str, filters: dict = None) -> bool:
        """
        Export rankings to CSV file.
        
        Args:
            filepath: Path to save CSV file.
            filters: Optional dict of filters to apply.
            
        Returns:
            True if successful.
        """
        try:
            if filters:
                for key, value in filters.items():
                    if key in self.filter_vars:
                        self.filter_vars[key].set(str(value))
            
            df = self._get_filtered_df()
            df.to_csv(filepath, index=False)
            return True
        except Exception as e:
            print(f"Export error: {e}")
            return False
    
    def export_to_excel(self, filepath: str, filters: dict = None) -> bool:
        """
        Export rankings to Excel file.
        
        Args:
            filepath: Path to save Excel file.
            filters: Optional dict of filters to apply.
            
        Returns:
            True if successful.
        """
        try:
            if filters:
                for key, value in filters.items():
                    if key in self.filter_vars:
                        self.filter_vars[key].set(str(value))
            
            df = self._get_filtered_df()
            df.to_excel(filepath, index=False, sheet_name="Rankings")
            return True
        except Exception as e:
            print(f"Export error: {e}")
            return False
    
    # -------------------------------------------------------------------------
    # History Window
    # -------------------------------------------------------------------------
    
    def _show_history_window(self, symbol: str):
        """Show ranking history for a symbol."""
        history_win = tk.Toplevel(self.root)
        history_win.title(f"Ranking History: {symbol}")
        history_win.geometry("800x400")
        
        # Get history data
        try:
            df = self.repo.get_ranking_history(symbol)
            
            if df.empty:
                ttk.Label(
                    history_win,
                    text=f"No history found for {symbol}",
                    font=("Segoe UI", 12)
                ).pack(pady=50)
                return
            
            # Create table
            frame = ttk.Frame(history_win)
            frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
            
            columns = [
                ("ranking_date", "Date", 100),
                ("rs_rating", "RS Rating", 80),
                ("momentum_score", "Momentum", 80),
                ("trend_template_score", "Trend", 60),
                ("technical_score", "Technical", 80),
                ("composite_score", "Composite", 80),
                ("composite_rank", "Rank", 60),
            ]
            
            tree = ttk.Treeview(
                frame,
                columns=[c[0] for c in columns],
                show="headings"
            )
            
            for col_id, col_name, width in columns:
                tree.heading(col_id, text=col_name)
                tree.column(col_id, width=width, anchor=tk.CENTER)
            
            # Scrollbar
            scroll = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=tree.yview)
            tree.configure(yscrollcommand=scroll.set)
            
            tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            scroll.pack(side=tk.RIGHT, fill=tk.Y)
            
            # Add data
            for _, row in df.iterrows():
                values = (
                    row.get("ranking_date", ""),
                    f"{row.get('rs_rating', 0):.0f}",
                    f"{row.get('momentum_score', 0):.1f}",
                    f"{row.get('trend_template_score', 0):.0f}",
                    f"{row.get('technical_score', 0):.1f}",
                    f"{row.get('composite_score', 0):.1f}",
                    int(row.get('composite_rank', 0)) if pd.notna(row.get('composite_rank')) else "",
                )
                tree.insert("", tk.END, values=values)
            
        except Exception as e:
            ttk.Label(
                history_win,
                text=f"Error loading history: {e}",
                font=("Segoe UI", 10)
            ).pack(pady=50)
    
    # -------------------------------------------------------------------------
    # Public API
    # -------------------------------------------------------------------------
    
    def get_top_stocks(self, n: int = 50, score_type: str = "composite_score") -> pd.DataFrame:
        """
        Get top N stocks by score.
        
        Args:
            n: Number of stocks.
            score_type: Score to rank by.
            
        Returns:
            DataFrame with top stocks.
        """
        return self.repo.get_top_stocks_by_score(score_type, n)
    
    def run(self):
        """Run the GUI (only for standalone mode)."""
        if self.is_standalone:
            self.root.mainloop()


def main():
    """Main entry point."""
    viewer = RankingsViewer()
    viewer.run()


if __name__ == "__main__":
    main()
