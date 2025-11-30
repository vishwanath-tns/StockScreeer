#!/usr/bin/env python3
"""
Parallel Historical Rankings Builder GUI

A graphical interface for building historical stock rankings
using parallel workers and Redis queue.

Features:
- Start/stop multiple workers
- Monitor worker status and throughput
- Real-time progress tracking
- Queue statistics

Usage:
    python -m ranking.parallel.parallel_gui
"""

import os
import sys
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime, date, timedelta
import threading
import subprocess
import time
import logging

# Add project root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from ranking.parallel.redis_manager import RedisManager, check_redis_available
from ranking.parallel.dispatcher import ParallelRankingsDispatcher
from ranking.parallel.job_models import BatchProgress

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ParallelRankingsGUI:
    """
    GUI for parallel historical rankings building.
    """
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Parallel Historical Rankings Builder")
        self.root.geometry("800x700")
        
        # State
        self.redis_available = False
        self.dispatcher: ParallelRankingsDispatcher = None
        self.worker_processes: list = []
        self.is_running = False
        self.monitor_thread = None
        
        self._create_ui()
        self._check_redis()
        self._start_monitoring()
    
    def _create_ui(self):
        """Create the GUI layout."""
        # Main container
        main = ttk.Frame(self.root, padding=10)
        main.pack(fill=tk.BOTH, expand=True)
        
        # Title
        title = ttk.Label(
            main,
            text="⚡ Parallel Historical Rankings Builder",
            font=("Segoe UI", 16, "bold")
        )
        title.pack(pady=(0, 10))
        
        # Redis status
        self.redis_status = ttk.Label(
            main,
            text="Checking Redis...",
            font=("Segoe UI", 10)
        )
        self.redis_status.pack(pady=(0, 10))
        
        # Create notebook for tabs
        notebook = ttk.Notebook(main)
        notebook.pack(fill=tk.BOTH, expand=True)
        
        # Tab 1: Build Options
        self._create_build_tab(notebook)
        
        # Tab 2: Workers
        self._create_workers_tab(notebook)
        
        # Tab 3: Queue Stats
        self._create_queue_tab(notebook)
    
    def _create_build_tab(self, notebook):
        """Create the build options tab."""
        tab = ttk.Frame(notebook, padding=10)
        notebook.add(tab, text="Build Options")
        
        # Options frame
        options = ttk.LabelFrame(tab, text="Configuration", padding=10)
        options.pack(fill=tk.X, pady=(0, 10))
        
        # Years
        row1 = ttk.Frame(options)
        row1.pack(fill=tk.X, pady=5)
        
        ttk.Label(row1, text="Years of history:").pack(side=tk.LEFT)
        self.years_var = tk.StringVar(value="3")
        ttk.Spinbox(row1, from_=1, to=5, width=5, textvariable=self.years_var).pack(side=tk.LEFT, padx=10)
        
        # Date range
        row2 = ttk.Frame(options)
        row2.pack(fill=tk.X, pady=5)
        
        ttk.Label(row2, text="Or specify dates:").pack(side=tk.LEFT)
        ttk.Label(row2, text="From:").pack(side=tk.LEFT, padx=(20, 5))
        self.start_var = tk.StringVar()
        ttk.Entry(row2, textvariable=self.start_var, width=12).pack(side=tk.LEFT)
        ttk.Label(row2, text="To:").pack(side=tk.LEFT, padx=(10, 5))
        self.end_var = tk.StringVar()
        ttk.Entry(row2, textvariable=self.end_var, width=12).pack(side=tk.LEFT)
        
        # Skip existing
        self.skip_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(options, text="Skip already calculated dates", variable=self.skip_var).pack(anchor=tk.W, pady=5)
        
        # Progress section
        progress_frame = ttk.LabelFrame(tab, text="Progress", padding=10)
        progress_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # Progress bar
        self.progress_var = tk.DoubleVar(value=0)
        self.progress_bar = ttk.Progressbar(progress_frame, variable=self.progress_var, maximum=100)
        self.progress_bar.pack(fill=tk.X, pady=(0, 10))
        
        # Stats grid
        stats = ttk.Frame(progress_frame)
        stats.pack(fill=tk.X)
        
        labels = [
            ("Status:", "status_var", "Ready"),
            ("Total Jobs:", "total_var", "0"),
            ("Completed:", "completed_var", "0"),
            ("Failed:", "failed_var", "0"),
            ("Rate:", "rate_var", "0 jobs/sec"),
            ("ETA:", "eta_var", "-"),
        ]
        
        for i, (label, var_name, default) in enumerate(labels):
            row = i // 3
            col = (i % 3) * 2
            ttk.Label(stats, text=label).grid(row=row, column=col, sticky=tk.W, padx=5)
            setattr(self, var_name, tk.StringVar(value=default))
            ttk.Label(stats, textvariable=getattr(self, var_name), font=("Segoe UI", 9, "bold")).grid(row=row, column=col+1, sticky=tk.W, padx=(0, 20))
        
        # Buttons
        btn_frame = ttk.Frame(tab)
        btn_frame.pack(fill=tk.X)
        
        self.start_btn = ttk.Button(btn_frame, text="▶ Start Build", command=self._start_build)
        self.start_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        self.stop_btn = ttk.Button(btn_frame, text="⏹ Stop", command=self._stop_build, state=tk.DISABLED)
        self.stop_btn.pack(side=tk.LEFT)
        
        ttk.Button(btn_frame, text="Clear Queue", command=self._clear_queue).pack(side=tk.RIGHT)
    
    def _create_workers_tab(self, notebook):
        """Create the workers management tab."""
        tab = ttk.Frame(notebook, padding=10)
        notebook.add(tab, text="Workers")
        
        # Worker controls
        controls = ttk.Frame(tab)
        controls.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(controls, text="Number of workers:").pack(side=tk.LEFT)
        self.num_workers_var = tk.StringVar(value="4")
        ttk.Spinbox(controls, from_=1, to=16, width=5, textvariable=self.num_workers_var).pack(side=tk.LEFT, padx=10)
        
        ttk.Button(controls, text="Start Workers", command=self._start_workers).pack(side=tk.LEFT, padx=5)
        ttk.Button(controls, text="Stop All Workers", command=self._stop_workers).pack(side=tk.LEFT, padx=5)
        
        # Workers list
        list_frame = ttk.LabelFrame(tab, text="Active Workers", padding=10)
        list_frame.pack(fill=tk.BOTH, expand=True)
        
        columns = ("worker_id", "hostname", "status", "jobs_completed", "last_heartbeat")
        self.workers_tree = ttk.Treeview(list_frame, columns=columns, show="headings", height=8)
        
        self.workers_tree.heading("worker_id", text="Worker ID")
        self.workers_tree.heading("hostname", text="Hostname")
        self.workers_tree.heading("status", text="Status")
        self.workers_tree.heading("jobs_completed", text="Jobs Done")
        self.workers_tree.heading("last_heartbeat", text="Last Heartbeat")
        
        self.workers_tree.column("worker_id", width=150)
        self.workers_tree.column("hostname", width=100)
        self.workers_tree.column("status", width=80)
        self.workers_tree.column("jobs_completed", width=80)
        self.workers_tree.column("last_heartbeat", width=150)
        
        scroll = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.workers_tree.yview)
        self.workers_tree.configure(yscrollcommand=scroll.set)
        
        self.workers_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Worker count label
        self.worker_count_var = tk.StringVar(value="0 workers active")
        ttk.Label(tab, textvariable=self.worker_count_var).pack(pady=(10, 0))
    
    def _create_queue_tab(self, notebook):
        """Create the queue statistics tab."""
        tab = ttk.Frame(notebook, padding=10)
        notebook.add(tab, text="Queue Stats")
        
        # Queue stats
        stats_frame = ttk.LabelFrame(tab, text="Queue Statistics", padding=10)
        stats_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.queue_stats = {}
        for label in ["Pending", "Processing", "Completed", "Failed"]:
            row = ttk.Frame(stats_frame)
            row.pack(fill=tk.X, pady=2)
            ttk.Label(row, text=f"{label}:", width=15).pack(side=tk.LEFT)
            var = tk.StringVar(value="0")
            self.queue_stats[label.lower()] = var
            ttk.Label(row, textvariable=var, font=("Segoe UI", 12, "bold")).pack(side=tk.LEFT)
        
        # Throughput
        throughput_frame = ttk.LabelFrame(tab, text="Throughput", padding=10)
        throughput_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.throughput_var = tk.StringVar(value="0 jobs/second")
        ttk.Label(throughput_frame, textvariable=self.throughput_var, font=("Segoe UI", 14, "bold")).pack()
        
        # Instructions
        instructions = ttk.LabelFrame(tab, text="Instructions", padding=10)
        instructions.pack(fill=tk.BOTH, expand=True)
        
        text = """
How to use the Parallel Rankings Builder:

1. Start Redis (required):
   - Install Redis: https://redis.io/download
   - Or use Docker: docker run -d -p 6379:6379 redis

2. Start Workers:
   - Go to "Workers" tab
   - Set number of workers (more = faster, but uses more CPU)
   - Click "Start Workers"

3. Start Build:
   - Go to "Build Options" tab
   - Set years of history (3 = recommended)
   - Check "Skip already calculated dates" for resume capability
   - Click "Start Build"

4. Monitor Progress:
   - Watch progress bar and statistics
   - Check "Queue Stats" for detailed numbers
   - Workers tab shows each worker's status

Tips:
- Use 4-8 workers for optimal performance
- Each worker uses ~500MB RAM
- Building 3 years takes ~1-2 hours with 4 workers
        """
        
        text_widget = tk.Text(instructions, height=15, wrap=tk.WORD)
        text_widget.insert(tk.END, text)
        text_widget.configure(state=tk.DISABLED)
        text_widget.pack(fill=tk.BOTH, expand=True)
    
    def _check_redis(self):
        """Check Redis availability."""
        self.redis_available = check_redis_available()
        
        if self.redis_available:
            self.redis_status.configure(text="✓ Redis connected", foreground="green")
            self.dispatcher = ParallelRankingsDispatcher()
        else:
            self.redis_status.configure(text="✗ Redis not available - Please start Redis first", foreground="red")
            self.start_btn.configure(state=tk.DISABLED)
    
    def _start_monitoring(self):
        """Start background monitoring thread."""
        def monitor_loop():
            while True:
                try:
                    if self.redis_available:
                        self._update_workers_list()
                        self._update_queue_stats()
                except Exception as e:
                    logger.debug(f"Monitor error: {e}")
                time.sleep(2)
        
        self.monitor_thread = threading.Thread(target=monitor_loop, daemon=True)
        self.monitor_thread.start()
    
    def _update_workers_list(self):
        """Update workers list in UI."""
        try:
            workers = self.dispatcher.get_active_workers()
            
            # Update tree
            for item in self.workers_tree.get_children():
                self.workers_tree.delete(item)
            
            for w in workers:
                self.workers_tree.insert("", tk.END, values=(
                    w.get("worker_id", ""),
                    w.get("hostname", ""),
                    w.get("status", ""),
                    w.get("jobs_completed", "0"),
                    w.get("last_heartbeat", "")[:19] if w.get("last_heartbeat") else ""
                ))
            
            self.worker_count_var.set(f"{len(workers)} workers active")
            
        except Exception as e:
            logger.debug(f"Error updating workers: {e}")
    
    def _update_queue_stats(self):
        """Update queue statistics and main progress display."""
        try:
            stats = self.dispatcher.redis.get_queue_stats()
            
            pending = stats.get("pending", 0)
            processing = stats.get("processing", 0)
            completed = stats.get("completed", 0)
            failed = stats.get("failed", 0)
            
            self.queue_stats["pending"].set(str(pending))
            self.queue_stats["processing"].set(str(processing))
            self.queue_stats["completed"].set(str(completed))
            self.queue_stats["failed"].set(str(failed))
            
            # Also update main progress display if jobs are running
            total = pending + processing + completed + failed
            if total > 0:
                self.total_var.set(str(total))
                self.completed_var.set(str(completed))
                self.failed_var.set(str(failed))
                
                # Calculate progress percentage
                done = completed + failed
                progress_pct = (done / total) * 100 if total > 0 else 0
                self.progress_var.set(progress_pct)
                
                # Update status based on state
                if pending > 0 or processing > 0:
                    self.status_var.set(f"Running ({processing} active)")
                elif done == total and total > 0:
                    self.status_var.set("Complete")
                else:
                    self.status_var.set("Ready")
            
        except Exception as e:
            logger.debug(f"Error updating queue stats: {e}")
    
    def _start_workers(self, show_message=True):
        """Start worker processes."""
        if not self.redis_available:
            messagebox.showerror("Error", "Redis is not available")
            return
        
        try:
            num_workers = int(self.num_workers_var.get())
        except ValueError:
            num_workers = 4
        
        # Get Python executable
        python_exe = sys.executable
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        
        # Start workers as background processes (no console windows)
        for i in range(num_workers):
            worker_id = f"gui-worker-{i+1}-{int(time.time())}"
            
            # Start worker process
            cmd = [python_exe, "-m", "ranking.parallel.worker", "--id", worker_id]
            
            # Start as hidden background process on Windows
            if sys.platform == "win32":
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                startupinfo.wShowWindow = subprocess.SW_HIDE
                proc = subprocess.Popen(
                    cmd,
                    startupinfo=startupinfo,
                    cwd=project_root,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
            else:
                proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
            self.worker_processes.append(proc)
            logger.info(f"Started worker {worker_id} (PID: {proc.pid})")
        
        if show_message:
            messagebox.showinfo("Workers Started", f"Started {num_workers} background worker processes.")
    
    def _stop_workers(self):
        """Stop all worker processes started by this GUI."""
        stopped = 0
        for proc in self.worker_processes:
            try:
                proc.terminate()
                stopped += 1
            except:
                pass
        
        self.worker_processes = []
        if stopped > 0:
            messagebox.showinfo("Workers Stopped", f"Stopped {stopped} worker processes.")
        else:
            messagebox.showinfo("Workers", "No GUI-started workers to stop.")
    
    def _start_build(self):
        """Start the build process."""
        if not self.redis_available:
            messagebox.showerror("Error", "Redis is not available")
            return
        
        # Check for workers - auto-start if none
        workers = self.dispatcher.get_active_workers()
        if not workers:
            self.status_var.set("Starting workers...")
            self.root.update()
            self._start_workers(show_message=False)
            time.sleep(3)  # Wait for workers to register
        
        # Get parameters
        try:
            years = int(self.years_var.get())
        except ValueError:
            years = 3
        
        start_date = self.start_var.get().strip() or None
        end_date = self.end_var.get().strip() or None
        skip_existing = self.skip_var.get()
        
        # Update UI
        self.is_running = True
        self.start_btn.configure(state=tk.DISABLED)
        self.stop_btn.configure(state=tk.NORMAL)
        self.status_var.set("Creating jobs...")
        
        # Start build thread
        thread = threading.Thread(
            target=self._run_build,
            args=(years, start_date, end_date, skip_existing),
            daemon=True
        )
        thread.start()
    
    def _run_build(self, years, start_date, end_date, skip_existing):
        """Run build in background thread."""
        try:
            def progress_cb(p: BatchProgress):
                self.root.after(0, lambda: self._update_progress(p))
            
            result = self.dispatcher.build_historical_rankings(
                years=years,
                start_date=start_date,
                end_date=end_date,
                skip_existing=skip_existing,
                progress_callback=progress_cb,
                wait_for_completion=True
            )
            
            self.root.after(0, lambda: self._build_complete(result))
            
        except Exception as e:
            logger.exception("Build error")
            self.root.after(0, lambda: self._build_error(str(e)))
    
    def _update_progress(self, p: BatchProgress):
        """Update progress display."""
        self.progress_var.set(p.progress_pct)
        self.total_var.set(str(p.total_jobs))
        self.completed_var.set(str(p.completed_jobs))
        self.failed_var.set(str(p.failed_jobs))
        self.rate_var.set(f"{p.jobs_per_second:.2f} jobs/sec")
        
        if p.eta_seconds > 0:
            eta_min = int(p.eta_seconds / 60)
            eta_sec = int(p.eta_seconds % 60)
            self.eta_var.set(f"{eta_min}m {eta_sec}s")
        else:
            self.eta_var.set("-")
        
        self.throughput_var.set(f"{p.jobs_per_second:.2f} jobs/second")
    
    def _build_complete(self, result):
        """Handle build completion."""
        self.is_running = False
        self.start_btn.configure(state=tk.NORMAL)
        self.stop_btn.configure(state=tk.DISABLED)
        self.status_var.set("Complete")
        self.progress_var.set(100)
        
        messagebox.showinfo(
            "Complete",
            f"Historical rankings build complete!\n\n"
            f"Completed: {result.get('completed', 0)}\n"
            f"Failed: {result.get('failed', 0)}\n"
            f"Time: {result.get('elapsed_seconds', 0):.1f}s"
        )
    
    def _build_error(self, error):
        """Handle build error."""
        self.is_running = False
        self.start_btn.configure(state=tk.NORMAL)
        self.stop_btn.configure(state=tk.DISABLED)
        self.status_var.set("Error")
        
        messagebox.showerror("Error", f"Build failed: {error}")
    
    def _stop_build(self):
        """Stop the build."""
        if self.dispatcher:
            self.dispatcher.stop()
        self.status_var.set("Stopping...")
    
    def _clear_queue(self):
        """Clear the job queue."""
        if self.dispatcher:
            self.dispatcher.cancel_pending_jobs()
            messagebox.showinfo("Queue Cleared", "All pending jobs have been cancelled.")
    
    def run(self):
        """Run the GUI."""
        # Handle window close
        def on_close():
            self._stop_workers()
            self.root.destroy()
        
        self.root.protocol("WM_DELETE_WINDOW", on_close)
        self.root.mainloop()


def main():
    """Main entry point."""
    gui = ParallelRankingsGUI()
    gui.run()


if __name__ == "__main__":
    main()
