#!/usr/bin/env python3
"""
Historical Rankings Builder GUI

A graphical interface for building historical stock rankings.
This is a one-time operation for backtesting purposes.

Usage:
    python -m ranking.historical.historical_rankings_gui
    
    # Or directly:
    python ranking/historical/historical_rankings_gui.py
"""

import os
import sys
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime, date, timedelta
import threading
import logging

# Add project root for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from ranking.historical.historical_rankings_builder import HistoricalRankingsBuilder, BuildProgress

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class HistoricalRankingsGUI:
    """
    GUI for building historical stock rankings.
    """
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Historical Rankings Builder")
        self.root.geometry("600x500")
        self.root.resizable(True, True)
        
        # Builder
        self.builder = None
        self.build_thread = None
        self.is_running = False
        
        self._create_ui()
    
    def _create_ui(self):
        """Create the GUI layout."""
        # Main container
        main = ttk.Frame(self.root, padding=10)
        main.pack(fill=tk.BOTH, expand=True)
        
        # Title
        title = ttk.Label(
            main,
            text="📊 Historical Rankings Builder",
            font=("Segoe UI", 16, "bold")
        )
        title.pack(pady=(0, 15))
        
        # Description
        desc = ttk.Label(
            main,
            text="Build historical stock rankings for backtesting.\n"
                 "This is a one-time operation that may take several hours.",
            justify=tk.CENTER,
            foreground="gray"
        )
        desc.pack(pady=(0, 15))
        
        # Options frame
        options = ttk.LabelFrame(main, text="Build Options", padding=10)
        options.pack(fill=tk.X, pady=(0, 15))
        
        # Years selection
        years_frame = ttk.Frame(options)
        years_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(years_frame, text="Years of history:").pack(side=tk.LEFT)
        
        self.years_var = tk.StringVar(value="3")
        years_spin = ttk.Spinbox(
            years_frame,
            from_=1,
            to=5,
            width=5,
            textvariable=self.years_var
        )
        years_spin.pack(side=tk.LEFT, padx=10)
        
        # Date range (optional override)
        date_frame = ttk.Frame(options)
        date_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(date_frame, text="Or specify dates:").pack(side=tk.LEFT)
        
        ttk.Label(date_frame, text="From:").pack(side=tk.LEFT, padx=(20, 5))
        self.start_var = tk.StringVar()
        start_entry = ttk.Entry(date_frame, textvariable=self.start_var, width=12)
        start_entry.pack(side=tk.LEFT)
        
        ttk.Label(date_frame, text="To:").pack(side=tk.LEFT, padx=(10, 5))
        self.end_var = tk.StringVar()
        end_entry = ttk.Entry(date_frame, textvariable=self.end_var, width=12)
        end_entry.pack(side=tk.LEFT)
        
        ttk.Label(date_frame, text="(YYYY-MM-DD)", foreground="gray").pack(side=tk.LEFT, padx=10)
        
        # Skip existing checkbox
        self.skip_var = tk.BooleanVar(value=True)
        skip_check = ttk.Checkbutton(
            options,
            text="Skip dates already in history (resume mode)",
            variable=self.skip_var
        )
        skip_check.pack(anchor=tk.W, pady=5)
        
        # Progress section
        progress_frame = ttk.LabelFrame(main, text="Progress", padding=10)
        progress_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 15))
        
        # Progress bar
        self.progress_var = tk.DoubleVar(value=0)
        self.progress_bar = ttk.Progressbar(
            progress_frame,
            variable=self.progress_var,
            maximum=100
        )
        self.progress_bar.pack(fill=tk.X, pady=(0, 10))
        
        # Status labels
        status_grid = ttk.Frame(progress_frame)
        status_grid.pack(fill=tk.X)
        
        self.status_var = tk.StringVar(value="Ready")
        ttk.Label(status_grid, text="Status:").grid(row=0, column=0, sticky=tk.W)
        ttk.Label(status_grid, textvariable=self.status_var, font=("Segoe UI", 9, "bold")).grid(row=0, column=1, sticky=tk.W, padx=10)
        
        self.current_date_var = tk.StringVar(value="-")
        ttk.Label(status_grid, text="Current date:").grid(row=1, column=0, sticky=tk.W)
        ttk.Label(status_grid, textvariable=self.current_date_var).grid(row=1, column=1, sticky=tk.W, padx=10)
        
        self.progress_text_var = tk.StringVar(value="0 / 0")
        ttk.Label(status_grid, text="Progress:").grid(row=2, column=0, sticky=tk.W)
        ttk.Label(status_grid, textvariable=self.progress_text_var).grid(row=2, column=1, sticky=tk.W, padx=10)
        
        self.eta_var = tk.StringVar(value="-")
        ttk.Label(status_grid, text="ETA:").grid(row=3, column=0, sticky=tk.W)
        ttk.Label(status_grid, textvariable=self.eta_var).grid(row=3, column=1, sticky=tk.W, padx=10)
        
        self.stats_var = tk.StringVar(value="-")
        ttk.Label(status_grid, text="Stats:").grid(row=4, column=0, sticky=tk.W)
        ttk.Label(status_grid, textvariable=self.stats_var).grid(row=4, column=1, sticky=tk.W, padx=10)
        
        # Log area
        log_frame = ttk.Frame(progress_frame)
        log_frame.pack(fill=tk.BOTH, expand=True, pady=(10, 0))
        
        self.log_text = tk.Text(log_frame, height=6, state=tk.DISABLED)
        log_scroll = ttk.Scrollbar(log_frame, command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=log_scroll.set)
        
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        log_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Buttons
        btn_frame = ttk.Frame(main)
        btn_frame.pack(fill=tk.X)
        
        self.start_btn = ttk.Button(
            btn_frame,
            text="▶ Start Build",
            command=self._start_build
        )
        self.start_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        self.stop_btn = ttk.Button(
            btn_frame,
            text="⏹ Stop",
            command=self._stop_build,
            state=tk.DISABLED
        )
        self.stop_btn.pack(side=tk.LEFT)
        
        ttk.Button(
            btn_frame,
            text="Close",
            command=self.root.destroy
        ).pack(side=tk.RIGHT)
    
    def _log(self, message: str):
        """Add message to log."""
        self.log_text.configure(state=tk.NORMAL)
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.insert(tk.END, f"[{timestamp}] {message}\n")
        self.log_text.see(tk.END)
        self.log_text.configure(state=tk.DISABLED)
    
    def _update_progress(self, progress: BuildProgress):
        """Update progress display."""
        if progress.total_dates > 0:
            pct = (progress.completed_dates + progress.skipped_dates) / progress.total_dates * 100
            self.progress_var.set(pct)
            self.progress_text_var.set(
                f"{progress.completed_dates} / {progress.total_dates} "
                f"(skipped: {progress.skipped_dates}, failed: {progress.failed_dates})"
            )
        
        if progress.current_date:
            self.current_date_var.set(str(progress.current_date))
        
        self.eta_var.set(progress.eta_str if progress.eta_str else "-")
        
        rate = progress.dates_per_second
        if rate > 0:
            self.stats_var.set(f"{rate:.2f} dates/sec")
    
    def _start_build(self):
        """Start the build process."""
        if self.is_running:
            return
        
        # Get parameters
        try:
            years = int(self.years_var.get())
        except ValueError:
            years = 3
        
        start_date = self.start_var.get().strip() or None
        end_date = self.end_var.get().strip() or None
        skip_existing = self.skip_var.get()
        
        # Validate dates if provided
        if start_date:
            try:
                datetime.strptime(start_date, "%Y-%m-%d")
            except ValueError:
                messagebox.showerror("Error", "Invalid start date format. Use YYYY-MM-DD")
                return
        
        if end_date:
            try:
                datetime.strptime(end_date, "%Y-%m-%d")
            except ValueError:
                messagebox.showerror("Error", "Invalid end date format. Use YYYY-MM-DD")
                return
        
        # Confirm
        if not messagebox.askyesno(
            "Confirm",
            f"This will build historical rankings for {years} years.\n"
            f"This may take several hours.\n\nContinue?"
        ):
            return
        
        # Update UI
        self.is_running = True
        self.start_btn.configure(state=tk.DISABLED)
        self.stop_btn.configure(state=tk.NORMAL)
        self.status_var.set("Initializing...")
        self.progress_var.set(0)
        
        self._log("Starting historical rankings build...")
        
        # Create builder
        self.builder = HistoricalRankingsBuilder()
        
        # Start build thread
        self.build_thread = threading.Thread(
            target=self._run_build,
            args=(years, start_date, end_date, skip_existing),
            daemon=True
        )
        self.build_thread.start()
        
        # Start progress monitor
        self._monitor_progress()
    
    def _run_build(self, years, start_date, end_date, skip_existing):
        """Run the build in a background thread."""
        try:
            def progress_cb(p: BuildProgress):
                # Schedule UI update on main thread
                self.root.after(0, lambda: self._update_progress(p))
            
            self.status_var.set("Building...")
            
            result = self.builder.build(
                years=years,
                start_date=start_date,
                end_date=end_date,
                skip_existing=skip_existing,
                progress_callback=progress_cb
            )
            
            # Complete
            self.root.after(0, lambda: self._build_complete(result))
            
        except Exception as e:
            logger.exception("Build error")
            self.root.after(0, lambda: self._build_error(str(e)))
    
    def _monitor_progress(self):
        """Monitor build progress."""
        if not self.is_running:
            return
        
        if self.builder and self.builder.progress:
            self._update_progress(self.builder.progress)
        
        # Check again in 500ms
        self.root.after(500, self._monitor_progress)
    
    def _build_complete(self, result):
        """Handle build completion."""
        self.is_running = False
        self.start_btn.configure(state=tk.NORMAL)
        self.stop_btn.configure(state=tk.DISABLED)
        
        self.status_var.set("Complete")
        self.progress_var.set(100)
        
        self._log(f"Build complete!")
        self._log(f"  Processed: {result.get('processed', 0)}")
        self._log(f"  Skipped: {result.get('skipped', 0)}")
        self._log(f"  Failed: {result.get('failed', 0)}")
        self._log(f"  Elapsed: {result.get('elapsed_seconds', 0):.1f}s")
        
        messagebox.showinfo(
            "Complete",
            f"Historical rankings build complete!\n\n"
            f"Processed: {result.get('processed', 0)}\n"
            f"Skipped: {result.get('skipped', 0)}\n"
            f"Failed: {result.get('failed', 0)}"
        )
    
    def _build_error(self, error: str):
        """Handle build error."""
        self.is_running = False
        self.start_btn.configure(state=tk.NORMAL)
        self.stop_btn.configure(state=tk.DISABLED)
        
        self.status_var.set("Error")
        self._log(f"Error: {error}")
        
        messagebox.showerror("Error", f"Build failed: {error}")
    
    def _stop_build(self):
        """Stop the build process."""
        if self.builder:
            self.builder.stop()
            self._log("Stop requested...")
            self.status_var.set("Stopping...")
    
    def run(self):
        """Run the GUI."""
        self.root.mainloop()


def main():
    """Main entry point."""
    gui = HistoricalRankingsGUI()
    gui.run()


if __name__ == "__main__":
    main()
