#!/usr/bin/env python3
"""
Sectoral Trends Window
====================

Interactive window for displaying sectoral trend analysis over time.
Shows bullish/bearish percentages with interactive charts and sector selection.
"""

import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime, date, timedelta
import pandas as pd
from typing import List, Optional
import threading

try:
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    from matplotlib.figure import Figure
    import matplotlib.dates as mdates
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False

# Add parent directory to path
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.sectoral_trends_service import SectoralTrendsService, populate_trends_data

class SectoralTrendsWindow:
    """Interactive window for sectoral trends analysis."""
    
    def __init__(self, parent):
        self.parent = parent
        self.service = SectoralTrendsService()
        self.current_data = pd.DataFrame()
        
        self.setup_window()
        self.setup_widgets()
        self.load_initial_data()
    
    def setup_window(self):
        """Setup the main window."""
        self.window = tk.Toplevel(self.parent)
        self.window.title("📈 Sectoral Trends Analysis - Time Series")
        self.window.geometry("1200x800")
        self.window.minsize(1000, 600)
        
        # Make window modal
        self.window.transient(self.parent)
        self.window.grab_set()
        
        # Center window
        self.window.update_idletasks()
        x = (self.window.winfo_screenwidth() // 2) - (1200 // 2)
        y = (self.window.winfo_screenheight() // 2) - (800 // 2)
        self.window.geometry(f"1200x800+{x}+{y}")
    
    def setup_widgets(self):
        """Setup all GUI widgets."""
        main_frame = ttk.Frame(self.window)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Title
        title_label = ttk.Label(main_frame, 
                               text="📈 Sectoral Trends Analysis - Time Series",
                               font=('Arial', 16, 'bold'))
        title_label.pack(pady=(0, 10))
        
        # Control panel
        self.setup_control_panel(main_frame)
        
        # Chart area
        self.setup_chart_area(main_frame)
        
        # Status bar
        self.setup_status_bar(main_frame)
    
    def setup_control_panel(self, parent):
        """Setup control panel with filters and options."""
        control_frame = ttk.LabelFrame(parent, text="📊 Analysis Controls")
        control_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Top row - Data controls
        top_row = ttk.Frame(control_frame)
        top_row.pack(fill=tk.X, padx=10, pady=5)
        
        # Data status
        ttk.Label(top_row, text="Data Status:").grid(row=0, column=0, sticky=tk.W, padx=(0, 5))
        self.status_label = ttk.Label(top_row, text="Loading...", foreground="orange")
        self.status_label.grid(row=0, column=1, sticky=tk.W, padx=(0, 20))
        
        # Populate button
        ttk.Button(top_row, text="📥 Populate Data", 
                  command=self.populate_data).grid(row=0, column=2, padx=(0, 10))
        
        # Days selection
        ttk.Label(top_row, text="Days:").grid(row=0, column=3, sticky=tk.W, padx=(10, 5))
        self.days_var = tk.StringVar(value="30")
        days_combo = ttk.Combobox(top_row, textvariable=self.days_var, 
                                 values=["7", "15", "30", "45", "60", "90"], 
                                 width=8, state="readonly")
        days_combo.grid(row=0, column=4, padx=(0, 10))
        days_combo.bind('<<ComboboxSelected>>', self.on_days_changed)
        
        # Refresh button
        ttk.Button(top_row, text="🔄 Refresh", 
                  command=self.refresh_data).grid(row=0, column=5, padx=(0, 10))
        
        # Second row - Sector selection
        sector_row = ttk.Frame(control_frame)
        sector_row.pack(fill=tk.X, padx=10, pady=5)
        
        # Sector selection
        ttk.Label(sector_row, text="Select Sectors:").grid(row=0, column=0, sticky=tk.W, padx=(0, 10))
        
        # All sectors checkbox
        self.all_sectors_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(sector_row, text="All Sectors", 
                       variable=self.all_sectors_var,
                       command=self.toggle_all_sectors).grid(row=0, column=1, padx=(0, 20))
        
        # Individual sector checkboxes frame
        self.sectors_frame = ttk.Frame(sector_row)
        self.sectors_frame.grid(row=0, column=2, sticky=tk.W, columnspan=5)
        
        # Chart options
        options_row = ttk.Frame(control_frame)
        options_row.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Label(options_row, text="Chart Type:").grid(row=0, column=0, sticky=tk.W, padx=(0, 5))
        self.chart_type_var = tk.StringVar(value="Bullish %")
        chart_combo = ttk.Combobox(options_row, textvariable=self.chart_type_var,
                                  values=["Bullish %", "Bearish %", "Both %", "Daily Uptrend %", "Avg Rating"],
                                  width=15, state="readonly")
        chart_combo.grid(row=0, column=1, padx=(0, 20))
        chart_combo.bind('<<ComboboxSelected>>', self.on_chart_type_changed)
        
        # Update chart button
        ttk.Button(options_row, text="📊 Update Chart", 
                  command=self.update_chart).grid(row=0, column=2, padx=(0, 10))
        
        # Export button
        ttk.Button(options_row, text="💾 Export CSV", 
                  command=self.export_data).grid(row=0, column=3, padx=(0, 10))
    
    def setup_chart_area(self, parent):
        """Setup the matplotlib chart area."""
        chart_frame = ttk.LabelFrame(parent, text="📈 Trends Chart")
        chart_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        if not MATPLOTLIB_AVAILABLE:
            no_matplotlib_label = ttk.Label(chart_frame,
                                           text="⚠️ Matplotlib not available\\nInstall with: pip install matplotlib",
                                           justify=tk.CENTER,
                                           font=('Arial', 12))
            no_matplotlib_label.pack(expand=True)
            return
        
        # Create matplotlib figure
        self.fig = Figure(figsize=(12, 6), dpi=100)
        self.ax = self.fig.add_subplot(111)
        
        # Create canvas
        self.canvas = FigureCanvasTkAgg(self.fig, chart_frame)
        self.canvas.draw()
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Add toolbar
        toolbar_frame = ttk.Frame(chart_frame)
        toolbar_frame.pack(fill=tk.X, padx=10, pady=(0, 10))
        
        from matplotlib.backends.backend_tkagg import NavigationToolbar2Tk
        toolbar = NavigationToolbar2Tk(self.canvas, toolbar_frame)
        toolbar.update()
    
    def setup_status_bar(self, parent):
        """Setup status bar."""
        self.status_bar = ttk.Label(parent, text="Ready", relief=tk.SUNKEN, anchor=tk.W)
        self.status_bar.pack(fill=tk.X, side=tk.BOTTOM)
    
    def load_initial_data(self):
        """Load initial data and setup sectors."""
        try:
            # Get data summary
            summary = self.service.get_data_summary()
            
            if summary['total_records'] > 0:
                self.status_label.config(text=f"✅ {summary['total_records']} records", foreground="green")
                self.update_status(f"Data available: {summary['earliest_date']} to {summary['latest_date']}")
            else:
                self.status_label.config(text="❌ No data", foreground="red")
                self.update_status("No data available. Click 'Populate Data' to calculate trends.")
            
            # Setup sector checkboxes
            self.setup_sector_checkboxes()
            
            # Load initial chart if data exists
            if summary['total_records'] > 0:
                self.refresh_data()
            
        except Exception as e:
            self.update_status(f"Error loading initial data: {e}")
            messagebox.showerror("Error", f"Failed to load initial data: {e}")
    
    def setup_sector_checkboxes(self):
        """Setup sector selection checkboxes."""
        try:
            # Clear existing checkboxes
            for widget in self.sectors_frame.winfo_children():
                widget.destroy()
            
            # Get available sectors
            sectors = self.service.get_available_sectors()
            
            # Create checkboxes
            self.sector_vars = {}
            row = 0
            col = 0
            max_cols = 4
            
            for sector in sectors[:12]:  # Limit to 12 for UI space
                display_name = sector.replace('NIFTY-', '').replace('-', ' ')
                var = tk.BooleanVar()
                
                # Select first 3 sectors by default
                if len(self.sector_vars) < 3:
                    var.set(True)
                
                checkbox = ttk.Checkbutton(self.sectors_frame, text=display_name,
                                         variable=var, command=self.on_sector_selection_changed)
                checkbox.grid(row=row, column=col, sticky=tk.W, padx=5, pady=2)
                
                self.sector_vars[sector] = var
                
                col += 1
                if col >= max_cols:
                    col = 0
                    row += 1
                    
        except Exception as e:
            self.update_status(f"Error setting up sectors: {e}")
    
    def populate_data(self):
        """Populate trends data in background thread."""
        def populate_thread():
            try:
                self.update_status("📥 Populating trends data... This may take a few minutes.")
                
                # Get days to populate
                days = int(self.days_var.get())
                
                # Populate data
                stats = populate_trends_data(days)
                
                # Update UI on main thread
                self.window.after(0, lambda: self.on_populate_complete(stats))
                
            except Exception as e:
                self.window.after(0, lambda: self.on_populate_error(str(e)))
        
        # Start background thread
        thread = threading.Thread(target=populate_thread)
        thread.daemon = True
        thread.start()
    
    def on_populate_complete(self, stats):
        """Handle successful data population."""
        self.update_status(f"✅ Data populated: {stats['total_records']} records created")
        
        # Update data summary
        summary = self.service.get_data_summary()
        self.status_label.config(text=f"✅ {summary['total_records']} records", foreground="green")
        
        # Refresh the chart
        self.refresh_data()
        
        messagebox.showinfo("Success", 
                          f"Data populated successfully!\\n"
                          f"Records created: {stats['total_records']}\\n"
                          f"Dates processed: {stats['dates_processed']}")
    
    def on_populate_error(self, error):
        """Handle data population error."""
        self.update_status(f"❌ Population failed: {error}")
        messagebox.showerror("Error", f"Failed to populate data:\\n{error}")
    
    def refresh_data(self):
        """Refresh chart with current selections."""
        try:
            # Get selected sectors
            selected_sectors = self.get_selected_sectors()
            
            if not selected_sectors:
                self.update_status("⚠️ No sectors selected")
                return
            
            # Get days
            days = int(self.days_var.get())
            
            # Load data
            self.current_data = self.service.get_trends_data(
                sectors=selected_sectors, 
                days_back=days
            )
            
            if self.current_data.empty:
                self.update_status("❌ No data found for selected criteria")
                if MATPLOTLIB_AVAILABLE:
                    self.ax.clear()
                    self.ax.text(0.5, 0.5, 'No data available', 
                                ha='center', va='center', transform=self.ax.transAxes)
                    self.canvas.draw()
                return
            
            # Update chart
            self.update_chart()
            
            self.update_status(f"✅ Loaded {len(self.current_data)} records for {len(selected_sectors)} sectors")
            
        except Exception as e:
            self.update_status(f"Error refreshing data: {e}")
            messagebox.showerror("Error", f"Failed to refresh data: {e}")
    
    def get_selected_sectors(self) -> List[str]:
        """Get list of selected sectors."""
        selected = []
        for sector, var in self.sector_vars.items():
            if var.get():
                selected.append(sector)
        return selected
    
    def update_chart(self):
        """Update the matplotlib chart."""
        if not MATPLOTLIB_AVAILABLE or self.current_data.empty:
            return
            
        try:
            self.ax.clear()
            
            chart_type = self.chart_type_var.get()
            
            # Group by sector and plot
            colors = plt.cm.tab10(range(len(self.current_data['sector_code'].unique())))
            
            for i, (sector, group) in enumerate(self.current_data.groupby('sector_code')):
                sector_name = group['sector_name'].iloc[0]
                dates = pd.to_datetime(group['analysis_date'])
                
                if chart_type == "Bullish %":
                    self.ax.plot(dates, group['bullish_percent'], 
                               label=sector_name, color=colors[i], linewidth=2, marker='o', markersize=4)
                    self.ax.set_ylabel('Bullish %')
                    
                elif chart_type == "Bearish %":
                    self.ax.plot(dates, group['bearish_percent'], 
                               label=sector_name, color=colors[i], linewidth=2, marker='o', markersize=4)
                    self.ax.set_ylabel('Bearish %')
                    
                elif chart_type == "Both %":
                    self.ax.plot(dates, group['bullish_percent'], 
                               label=f"{sector_name} (Bull)", color=colors[i], linewidth=2, marker='o', markersize=3)
                    self.ax.plot(dates, group['bearish_percent'], 
                               label=f"{sector_name} (Bear)", color=colors[i], linewidth=2, 
                               linestyle='--', marker='s', markersize=3)
                    self.ax.set_ylabel('Percentage')
                    
                elif chart_type == "Daily Uptrend %":
                    self.ax.plot(dates, group['daily_uptrend_percent'], 
                               label=sector_name, color=colors[i], linewidth=2, marker='o', markersize=4)
                    self.ax.set_ylabel('Daily Uptrend %')
                    
                elif chart_type == "Avg Rating":
                    self.ax.plot(dates, group['avg_trend_rating'], 
                               label=sector_name, color=colors[i], linewidth=2, marker='o', markersize=4)
                    self.ax.set_ylabel('Average Trend Rating')
            
            # Format chart
            self.ax.set_title(f'Sectoral Trends - {chart_type} Over Time', fontsize=14, fontweight='bold')
            self.ax.set_xlabel('Date')
            self.ax.grid(True, alpha=0.3)
            self.ax.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
            
            # Format dates on x-axis
            self.ax.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d'))
            self.ax.xaxis.set_major_locator(mdates.DayLocator(interval=max(1, len(self.current_data['analysis_date'].unique()) // 10)))
            
            # Rotate x-axis labels
            plt.setp(self.ax.xaxis.get_majorticklabels(), rotation=45, ha='right')
            
            # Tight layout
            self.fig.tight_layout()
            
            # Draw
            self.canvas.draw()
            
        except Exception as e:
            self.update_status(f"Error updating chart: {e}")
    
    def toggle_all_sectors(self):
        """Toggle all sector selections."""
        select_all = self.all_sectors_var.get()
        for var in self.sector_vars.values():
            var.set(select_all)
        
        # Update chart
        self.refresh_data()
    
    def on_sector_selection_changed(self):
        """Handle sector selection change."""
        # Update all sectors checkbox
        selected_count = sum(1 for var in self.sector_vars.values() if var.get())
        total_count = len(self.sector_vars)
        
        if selected_count == total_count:
            self.all_sectors_var.set(True)
        elif selected_count == 0:
            self.all_sectors_var.set(False)
        
        # Auto-refresh if data exists
        if not self.current_data.empty:
            self.refresh_data()
    
    def on_days_changed(self, event=None):
        """Handle days selection change."""
        if not self.current_data.empty:
            self.refresh_data()
    
    def on_chart_type_changed(self, event=None):
        """Handle chart type change."""
        if not self.current_data.empty:
            self.update_chart()
    
    def export_data(self):
        """Export current data to CSV."""
        if self.current_data.empty:
            messagebox.showwarning("No Data", "No data to export")
            return
        
        try:
            from tkinter import filedialog
            
            filename = filedialog.asksaveasfilename(
                defaultextension=".csv",
                filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
                title="Export Sectoral Trends Data"
            )
            
            if filename:
                self.current_data.to_csv(filename, index=False)
                messagebox.showinfo("Success", f"Data exported to {filename}")
                
        except Exception as e:
            messagebox.showerror("Error", f"Failed to export data: {e}")
    
    def update_status(self, message):
        """Update status bar."""
        self.status_bar.config(text=message)
        self.window.update_idletasks()

def show_sectoral_trends(parent):
    """Show the sectoral trends window."""
    try:
        SectoralTrendsWindow(parent)
    except Exception as e:
        messagebox.showerror("Error", f"Failed to open sectoral trends window: {e}")

if __name__ == "__main__":
    # Test the window
    root = tk.Tk()
    root.withdraw()
    
    show_sectoral_trends(root)
    root.mainloop()