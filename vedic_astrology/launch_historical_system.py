#!/usr/bin/env python3
"""
Historical Planetary Data System Launcher
Easy access to data collection and browsing

Usage:
    python launch_historical_system.py
"""

import sys
import os
import tkinter as tk
from tkinter import ttk, messagebox
from pathlib import Path

class HistoricalSystemLauncher:
    """
    Main launcher for the historical planetary data system
    """
    
    def __init__(self):
        self.setup_gui()
        
    def setup_gui(self):
        """Setup launcher GUI"""
        self.root = tk.Tk()
        self.root.title("Historical Planetary Data System Launcher")
        self.root.geometry("600x500")
        self.root.resizable(False, False)
        
        # Configure style
        style = ttk.Style()
        style.theme_use('clam')
        
        # Main frame
        main_frame = ttk.Frame(self.root, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Header
        header_label = ttk.Label(main_frame, 
                                text="🌟 Historical Planetary Data System",
                                font=("Arial", 18, "bold"))
        header_label.pack(pady=(0, 20))
        
        subtitle_label = ttk.Label(main_frame, 
                                 text="2-Year Planetary Position Collection & Browser\n2024-01-01 to 2026-01-01 (Every Minute)",
                                 font=("Arial", 11),
                                 foreground="gray")
        subtitle_label.pack(pady=(0, 30))
        
        # Database status
        self.status_frame = ttk.LabelFrame(main_frame, text="Database Status", padding="10")
        self.status_frame.pack(fill=tk.X, pady=(0, 20))
        
        self.db_status_label = ttk.Label(self.status_frame, text="🔄 Checking database...")
        self.db_status_label.pack()
        
        # Action buttons
        buttons_frame = ttk.Frame(main_frame)
        buttons_frame.pack(fill=tk.X, pady=(0, 20))
        
        # Collection section
        collection_frame = ttk.LabelFrame(buttons_frame, text="Data Collection", padding="15")
        collection_frame.pack(fill=tk.X, pady=(0, 15))
        
        ttk.Label(collection_frame, 
                 text="Collect planetary positions for every minute from 2024-2026",
                 font=("Arial", 10)).pack(anchor=tk.W, pady=(0, 10))
        
        collection_buttons = ttk.Frame(collection_frame)
        collection_buttons.pack(fill=tk.X)
        
        self.collect_btn = ttk.Button(collection_buttons, text="🚀 Start Collection",
                                     command=self.start_collection, state=tk.NORMAL)
        self.collect_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        self.collect_progress_btn = ttk.Button(collection_buttons, text="📊 Collection with Progress",
                                              command=self.start_collection_with_progress)
        self.collect_progress_btn.pack(side=tk.LEFT)
        
        # Browser section
        browser_frame = ttk.LabelFrame(buttons_frame, text="Data Browser", padding="15")
        browser_frame.pack(fill=tk.X, pady=(0, 15))
        
        ttk.Label(browser_frame, 
                 text="Browse collected planetary positions by date and time",
                 font=("Arial", 10)).pack(anchor=tk.W, pady=(0, 10))
        
        self.browser_btn = ttk.Button(browser_frame, text="🔍 Open Data Browser",
                                     command=self.start_browser)
        self.browser_btn.pack(anchor=tk.W)
        
        # Info section
        info_frame = ttk.LabelFrame(main_frame, text="System Information", padding="10")
        info_frame.pack(fill=tk.BOTH, expand=True)
        
        info_text = """
📊 Collection Details:
• Period: January 1, 2024 to January 1, 2026
• Frequency: Every minute (1,051,200 records total)
• Data: All 9 planets with signs, degrees, and positions
• Storage: SQLite database with optimized indexing
• Resume: Supports pausing and resuming collection

🔍 Browser Features:
• Date and time picker for any moment
• Planetary position display with DMS notation
• Navigation controls (previous/next day/hour)
• Range view showing multiple hours of data
• Fast searching with optimized database queries

⚡ Performance:
• Collection: ~100-500 records per second
• Storage: ~2-5 MB per day of data
• Browser: Instant queries with SQLite indexing
        """
        
        info_label = ttk.Label(info_frame, text=info_text, justify=tk.LEFT, 
                              font=("Consolas", 9))
        info_label.pack(anchor=tk.W)
        
        # Add proper close handling
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        
        # Check database status on startup
        self.check_database_status()
    
    def on_close(self):
        """Handle window close event"""
        try:
            self.root.quit()
            self.root.destroy()
        except:
            import sys
            sys.exit(0)
    
    def check_database_status(self):
        """Check current database status"""
        try:
            db_path = "historical_planetary_data.db"
            
            if os.path.exists(db_path):
                import sqlite3
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()
                
                cursor.execute("SELECT COUNT(*) FROM planetary_positions")
                count = cursor.fetchone()[0]
                
                if count == 0:
                    self.db_status_label.config(text="📂 Database created, no data yet", foreground="orange")
                    self.browser_btn.config(state=tk.DISABLED)
                elif count < 1000000:  # Less than expected total
                    cursor.execute("SELECT MIN(timestamp), MAX(timestamp) FROM planetary_positions")
                    date_range = cursor.fetchone()
                    percentage = (count / 1051200) * 100  # Approximate total
                    self.db_status_label.config(
                        text=f"📊 Database: {count:,} records ({percentage:.1f}%) | {date_range[0]} to {date_range[1]}", 
                        foreground="blue"
                    )
                    self.browser_btn.config(state=tk.NORMAL)
                else:
                    cursor.execute("SELECT MIN(timestamp), MAX(timestamp) FROM planetary_positions")
                    date_range = cursor.fetchone()
                    self.db_status_label.config(
                        text=f"✅ Database complete: {count:,} records | {date_range[0]} to {date_range[1]}", 
                        foreground="green"
                    )
                    self.browser_btn.config(state=tk.NORMAL)
                    self.collect_btn.config(text="✅ Collection Complete", state=tk.DISABLED)
                    self.collect_progress_btn.config(state=tk.DISABLED)
                
                conn.close()
            else:
                self.db_status_label.config(text="📂 No database found - ready to collect", foreground="orange")
                self.browser_btn.config(state=tk.DISABLED)
                
        except Exception as e:
            self.db_status_label.config(text=f"❌ Database check failed: {str(e)[:50]}...", foreground="red")
            print(f"Database check error: {e}")
    
    def start_collection(self):
        """Start data collection"""
        try:
            import subprocess
            
            # Confirm action
            result = messagebox.askyesno(
                "Start Data Collection",
                "This will collect planetary positions for every minute from 2024-2026.\n\n"
                "This may take several hours to complete.\n\n"
                "The collection can be paused and resumed.\n\n"
                "Do you want to continue?",
                icon='question'
            )
            
            if result:
                # Launch collection in new window
                subprocess.Popen([
                    sys.executable, "historical_planetary_app.py", "collect"
                ], cwd=os.path.dirname(__file__))
                
                messagebox.showinfo(
                    "Collection Started", 
                    "Data collection started in background.\n\n"
                    "You can close this launcher and check progress later.\n\n"
                    "The browser will become available as data is collected."
                )
                
                # Refresh status after delay
                self.root.after(2000, self.check_database_status)
                
        except Exception as e:
            messagebox.showerror("Error", f"Failed to start collection:\n{e}")
    
    def start_collection_with_progress(self):
        """Start collection with progress GUI"""
        try:
            import subprocess
            
            # Launch collection with progress GUI
            subprocess.Popen([
                sys.executable, "historical_planetary_app.py", "progress"
            ], cwd=os.path.dirname(__file__))
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to start collection:\n{e}")
    
    def start_browser(self):
        """Start data browser"""
        try:
            import subprocess
            
            # Launch browser
            subprocess.Popen([
                sys.executable, "historical_planetary_app.py", "browser"
            ], cwd=os.path.dirname(__file__))
            
        except Exception as e:
            error_msg = f"Failed to start browser:\n{str(e)[:200]}..."
            messagebox.showerror("Error", error_msg)
            print(f"Browser start error: {e}")
    
    def run(self):
        """Start the launcher with error handling"""
        try:
            self.root.mainloop()
        except KeyboardInterrupt:
            print("\nApplication interrupted by user")
            self.on_close()
        except Exception as e:
            print(f"Application error: {e}")
            try:
                messagebox.showerror("Application Error", f"An error occurred:\n{str(e)[:200]}...")
            except:
                pass
            self.on_close()

def main():
    """Main function with error handling"""
    try:
        launcher = HistoricalSystemLauncher()
        launcher.run()
    except Exception as e:
        print(f"Failed to start launcher: {e}")
        try:
            import tkinter as tk
            from tkinter import messagebox
            root = tk.Tk()
            root.withdraw()
            messagebox.showerror("Startup Error", f"Failed to start application:\n{str(e)[:200]}...")
            root.destroy()
        except:
            pass
        import sys
        sys.exit(1)

if __name__ == "__main__":
    main()