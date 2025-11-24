"""
NSE Block & Bulk Deals Sync - GUI Application

Downloads Block and Bulk Deals data from NSE with GUI for monitoring progress.
Includes anti-bot protection and rate limiting.
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
from datetime import datetime, timedelta
import threading
from typing import Optional
import sys
import os

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from block_bulk_deals.nse_deals_csv_downloader import (
    NSEDealsCSVDownloader as NSEDealsDownloader, 
    NSEDealsDatabase,
    get_trading_dates
)


class DealsDownloaderGUI:
    """GUI for NSE Block & Bulk Deals Downloader"""
    
    def __init__(self, root):
        self.root = root
        self.root.title("NSE Block & Bulk Deals Downloader")
        self.root.geometry("900x700")
        
        self.downloader = None
        self.database = None
        self.is_running = False
        
        self._create_widgets()
        
    def _create_widgets(self):
        """Create GUI widgets"""
        # Title
        title_frame = ttk.Frame(self.root, padding="10")
        title_frame.pack(fill=tk.X)
        
        title_label = ttk.Label(
            title_frame,
            text="NSE Block & Bulk Deals Downloader",
            font=("Arial", 16, "bold")
        )
        title_label.pack()
        
        subtitle = ttk.Label(
            title_frame,
            text="Download historical Block and Bulk Deals with anti-bot protection",
            font=("Arial", 9)
        )
        subtitle.pack()
        
        # Configuration Frame
        config_frame = ttk.LabelFrame(self.root, text="Download Configuration", padding="10")
        config_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # Date range
        date_row = ttk.Frame(config_frame)
        date_row.pack(fill=tk.X, pady=5)
        
        ttk.Label(date_row, text="From Date:").pack(side=tk.LEFT, padx=5)
        self.start_date = tk.StringVar(value=(datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d"))
        start_entry = ttk.Entry(date_row, textvariable=self.start_date, width=15)
        start_entry.pack(side=tk.LEFT, padx=5)
        
        ttk.Label(date_row, text="To Date:").pack(side=tk.LEFT, padx=5)
        self.end_date = tk.StringVar(value=datetime.now().strftime("%Y-%m-%d"))
        end_entry = ttk.Entry(date_row, textvariable=self.end_date, width=15)
        end_entry.pack(side=tk.LEFT, padx=5)
        
        # Deal type selection
        deal_type_row = ttk.Frame(config_frame)
        deal_type_row.pack(fill=tk.X, pady=5)
        
        ttk.Label(deal_type_row, text="Download:").pack(side=tk.LEFT, padx=5)
        
        self.download_block = tk.BooleanVar(value=True)
        ttk.Checkbutton(deal_type_row, text="Block Deals", variable=self.download_block).pack(side=tk.LEFT, padx=10)
        
        self.download_bulk = tk.BooleanVar(value=True)
        ttk.Checkbutton(deal_type_row, text="Bulk Deals", variable=self.download_bulk).pack(side=tk.LEFT, padx=10)
        
        # Rate limiting
        rate_row = ttk.Frame(config_frame)
        rate_row.pack(fill=tk.X, pady=5)
        
        ttk.Label(rate_row, text="Rate Limit (seconds):").pack(side=tk.LEFT, padx=5)
        self.rate_limit = tk.StringVar(value="2.0")
        rate_entry = ttk.Entry(rate_row, textvariable=self.rate_limit, width=10)
        rate_entry.pack(side=tk.LEFT, padx=5)
        
        ttk.Label(rate_row, text="(Time between requests - higher is safer)").pack(side=tk.LEFT, padx=5)
        
        # Skip existing
        skip_row = ttk.Frame(config_frame)
        skip_row.pack(fill=tk.X, pady=5)
        
        self.skip_existing = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            skip_row, 
            text="Skip dates already downloaded",
            variable=self.skip_existing
        ).pack(side=tk.LEFT, padx=5)
        
        # Control buttons
        button_frame = ttk.Frame(self.root, padding="10")
        button_frame.pack(fill=tk.X)
        
        self.start_button = ttk.Button(
            button_frame,
            text="Start Download",
            command=self._start_download
        )
        self.start_button.pack(side=tk.LEFT, padx=5)
        
        self.stop_button = ttk.Button(
            button_frame,
            text="Stop",
            command=self._stop_download,
            state=tk.DISABLED
        )
        self.stop_button.pack(side=tk.LEFT, padx=5)
        
        ttk.Button(
            button_frame,
            text="View Stats",
            command=self._show_stats
        ).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(
            button_frame,
            text="Clear Log",
            command=self._clear_log
        ).pack(side=tk.LEFT, padx=5)
        
        # Progress Frame
        progress_frame = ttk.LabelFrame(self.root, text="Progress", padding="10")
        progress_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self.progress_var = tk.StringVar(value="Ready")
        progress_label = ttk.Label(progress_frame, textvariable=self.progress_var)
        progress_label.pack()
        
        self.progressbar = ttk.Progressbar(progress_frame, mode='determinate')
        self.progressbar.pack(fill=tk.X, pady=5)
        
        # Stats Frame
        stats_frame = ttk.Frame(progress_frame)
        stats_frame.pack(fill=tk.X, pady=5)
        
        self.block_count = tk.StringVar(value="Block: 0")
        ttk.Label(stats_frame, textvariable=self.block_count).pack(side=tk.LEFT, padx=10)
        
        self.bulk_count = tk.StringVar(value="Bulk: 0")
        ttk.Label(stats_frame, textvariable=self.bulk_count).pack(side=tk.LEFT, padx=10)
        
        self.failed_count = tk.StringVar(value="Failed: 0")
        ttk.Label(stats_frame, textvariable=self.failed_count, foreground="red").pack(side=tk.LEFT, padx=10)
        
        # Log Frame
        log_frame = ttk.LabelFrame(self.root, text="Download Log", padding="10")
        log_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        self.log_text = scrolledtext.ScrolledText(
            log_frame,
            height=20,
            font=("Courier", 9)
        )
        self.log_text.pack(fill=tk.BOTH, expand=True)
        
    def _log(self, message: str):
        """Add message to log"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.insert(tk.END, f"[{timestamp}] {message}\n")
        self.log_text.see(tk.END)
        self.root.update_idletasks()
        
    def _clear_log(self):
        """Clear the log"""
        self.log_text.delete(1.0, tk.END)
        
    def _show_stats(self):
        """Show database statistics"""
        try:
            db = NSEDealsDatabase()
            stats = db.get_import_stats()
            
            msg = "=== Database Statistics ===\n\n"
            
            msg += "BLOCK DEALS:\n"
            block = stats['block_deals']
            msg += f"  Total Deals: {block['total_deals']:,}\n"
            msg += f"  Date Range: {block['earliest_date']} to {block['latest_date']}\n"
            msg += f"  Unique Symbols: {block['unique_symbols']:,}\n"
            msg += f"  Unique Clients: {block['unique_clients']:,}\n\n"
            
            msg += "BULK DEALS:\n"
            bulk = stats['bulk_deals']
            msg += f"  Total Deals: {bulk['total_deals']:,}\n"
            msg += f"  Date Range: {bulk['earliest_date']} to {bulk['latest_date']}\n"
            msg += f"  Unique Symbols: {bulk['unique_symbols']:,}\n"
            msg += f"  Unique Clients: {bulk['unique_clients']:,}\n"
            
            messagebox.showinfo("Database Statistics", msg)
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to get stats: {e}")
            
    def _start_download(self):
        """Start download in background thread"""
        if self.is_running:
            return
            
        # Validate inputs
        try:
            start = datetime.strptime(self.start_date.get(), "%Y-%m-%d")
            end = datetime.strptime(self.end_date.get(), "%Y-%m-%d")
            rate = float(self.rate_limit.get())
            
            if start > end:
                messagebox.showerror("Error", "Start date must be before end date")
                return
                
            if rate < 0.5:
                messagebox.showwarning("Warning", "Rate limit too low - using 0.5 seconds minimum")
                rate = 0.5
                
        except ValueError as e:
            messagebox.showerror("Error", f"Invalid input: {e}")
            return
            
        if not self.download_block.get() and not self.download_bulk.get():
            messagebox.showerror("Error", "Select at least one deal type")
            return
            
        # Confirm large date range
        days = (end - start).days
        if days > 365:
            confirm = messagebox.askyesno(
                "Confirm",
                f"This will download {days} days of data.\n"
                f"Estimated time: {days * rate / 60:.1f} minutes\n\n"
                "Continue?"
            )
            if not confirm:
                return
                
        # Start download
        self.is_running = True
        self.start_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.NORMAL)
        
        thread = threading.Thread(
            target=self._download_worker,
            args=(start, end, rate),
            daemon=True
        )
        thread.start()
        
    def _stop_download(self):
        """Stop the download"""
        self.is_running = False
        self._log("⏸️ Stopping download...")
        
    def _download_worker(self, start_date: datetime, end_date: datetime, rate_limit: float):
        """Worker thread for downloading deals"""
        try:
            # Initialize
            self.downloader = NSEDealsDownloader(rate_limit=rate_limit)
            self.database = NSEDealsDatabase()
            
            # Get trading dates
            dates = get_trading_dates(start_date, end_date)
            total_dates = len(dates)
            
            self._log(f"📅 Date range: {start_date.date()} to {end_date.date()}")
            self._log(f"📊 Total trading days: {total_dates}")
            self._log(f"⏱️ Rate limit: {rate_limit}s per request")
            self._log(f"🔄 Skip existing: {self.skip_existing.get()}")
            self._log("")
            
            # Get existing dates if skip enabled
            skip_block_dates = set()
            skip_bulk_dates = set()
            
            if self.skip_existing.get():
                if self.download_block.get():
                    skip_block_dates = self.database.get_imported_dates("BLOCK")
                    self._log(f"📋 Found {len(skip_block_dates)} existing BLOCK deal dates")
                    
                if self.download_bulk.get():
                    skip_bulk_dates = self.database.get_imported_dates("BULK")
                    self._log(f"📋 Found {len(skip_bulk_dates)} existing BULK deal dates")
                    
                self._log("")
            
            # Counters
            block_total = 0
            bulk_total = 0
            failed = 0
            
            # Download each date
            for idx, date in enumerate(dates, 1):
                if not self.is_running:
                    self._log("⏸️ Download stopped by user")
                    break
                    
                # Update progress
                progress = (idx / total_dates) * 100
                self.progressbar['value'] = progress
                self.progress_var.set(f"Processing {date.date()} ({idx}/{total_dates})")
                
                date_str = date.strftime("%d-%b-%Y")
                self._log(f"[{idx}/{total_dates}] {date_str}")
                
                # Download Block Deals
                if self.download_block.get():
                    if self.skip_existing.get() and date.date() in skip_block_dates:
                        self._log(f"  ⏭️ BLOCK: Skipped (already exists)")
                    else:
                        df = self.downloader.download_block_deals(date)
                        if df is not None:
                            if not df.empty:
                                new_records, _ = self.database.save_deals(df, "BLOCK")
                                block_total += new_records
                                self._log(f"  ✅ BLOCK: {new_records} deals saved")
                                self.database.log_import(date, "BLOCK", new_records, "SUCCESS")
                            else:
                                self._log(f"  ℹ️ BLOCK: No deals")
                                self.database.log_import(date, "BLOCK", 0, "NO_DATA")
                        else:
                            failed += 1
                            self._log(f"  ❌ BLOCK: Download failed")
                            self.database.log_import(date, "BLOCK", 0, "FAILED", "Download failed")
                
                # Download Bulk Deals
                if self.download_bulk.get():
                    if self.skip_existing.get() and date.date() in skip_bulk_dates:
                        self._log(f"  ⏭️ BULK: Skipped (already exists)")
                    else:
                        df = self.downloader.download_bulk_deals(date)
                        if df is not None:
                            if not df.empty:
                                new_records, _ = self.database.save_deals(df, "BULK")
                                bulk_total += new_records
                                self._log(f"  ✅ BULK: {new_records} deals saved")
                                self.database.log_import(date, "BULK", new_records, "SUCCESS")
                            else:
                                self._log(f"  ℹ️ BULK: No deals")
                                self.database.log_import(date, "BULK", 0, "NO_DATA")
                        else:
                            failed += 1
                            self._log(f"  ❌ BULK: Download failed")
                            self.database.log_import(date, "BULK", 0, "FAILED", "Download failed")
                
                # Update counters
                self.block_count.set(f"Block: {block_total:,}")
                self.bulk_count.set(f"Bulk: {bulk_total:,}")
                self.failed_count.set(f"Failed: {failed}")
                
            # Summary
            self._log("")
            self._log("=" * 60)
            self._log("📊 DOWNLOAD COMPLETE")
            self._log("=" * 60)
            self._log(f"Block Deals Downloaded: {block_total:,}")
            self._log(f"Bulk Deals Downloaded: {bulk_total:,}")
            self._log(f"Failed Requests: {failed}")
            self._log("=" * 60)
            
            self.progress_var.set("Download Complete!")
            self.progressbar['value'] = 100
            
        except Exception as e:
            self._log(f"❌ ERROR: {e}")
            messagebox.showerror("Error", f"Download failed: {e}")
            
        finally:
            # Cleanup
            if self.downloader:
                self.downloader.close()
                
            self.is_running = False
            self.start_button.config(state=tk.NORMAL)
            self.stop_button.config(state=tk.DISABLED)


def main():
    """Main entry point"""
    root = tk.Tk()
    app = DealsDownloaderGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
