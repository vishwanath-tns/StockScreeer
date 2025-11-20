#!/usr/bin/env python3
"""
Fixed Historical Planetary Data System Launcher
Improved error handling, proper close functionality, and stability

Usage:
    python launch_historical_system_fixed.py
"""

import sys
import os
import tkinter as tk
from tkinter import ttk, messagebox
from pathlib import Path
import threading
import traceback

class SafeHistoricalSystemLauncher:
    """
    Improved launcher with proper error handling and close functionality
    """
    
    def __init__(self):
        self.root = None
        self.setup_gui()
        
    def setup_gui(self):
        """Setup launcher GUI with error handling"""
        try:
            self.root = tk.Tk()
            self.root.title("Historical Planetary Data System Launcher")
            self.root.geometry("600x500")
            self.root.resizable(False, False)
            
            # Add proper close handling
            self.root.protocol("WM_DELETE_WINDOW", self.on_close)
            
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
                                     text="2-Year Planetary Position Collection & Browser\\n2024-01-01 to 2026-01-01 (Every Minute)",
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
                                         command=self.safe_start_collection, state=tk.NORMAL)
            self.collect_btn.pack(side=tk.LEFT, padx=(0, 10))
            
            self.collect_progress_btn = ttk.Button(collection_buttons, text="📊 Collection with Progress",
                                                  command=self.safe_start_collection_with_progress)
            self.collect_progress_btn.pack(side=tk.LEFT)
            
            # Browser section
            browser_frame = ttk.LabelFrame(buttons_frame, text="Data Browser", padding="15")
            browser_frame.pack(fill=tk.X, pady=(0, 15))
            
            ttk.Label(browser_frame, 
                     text="Browse collected planetary positions by date and time",
                     font=("Arial", 10)).pack(anchor=tk.W, pady=(0, 10))
            
            self.browser_btn = ttk.Button(browser_frame, text="🔍 Open Data Browser",
                                         command=self.safe_start_browser)
            self.browser_btn.pack(anchor=tk.W)
            
            # Quick test section
            test_frame = ttk.LabelFrame(buttons_frame, text="Quick Test", padding="15")
            test_frame.pack(fill=tk.X, pady=(0, 15))
            
            ttk.Label(test_frame, 
                     text="Test system components without full collection",
                     font=("Arial", 10)).pack(anchor=tk.W, pady=(0, 10))
            
            test_buttons = ttk.Frame(test_frame)
            test_buttons.pack(fill=tk.X)
            
            ttk.Button(test_buttons, text="🧮 Test Calculator",
                      command=self.test_calculator).pack(side=tk.LEFT, padx=(0, 10))
            ttk.Button(test_buttons, text="🗄️ Test Database",
                      command=self.test_database).pack(side=tk.LEFT, padx=(0, 10))
            ttk.Button(test_buttons, text="🔍 Quick Sample",
                      command=self.quick_sample).pack(side=tk.LEFT)
            
            # Control buttons
            control_frame = ttk.Frame(main_frame)
            control_frame.pack(fill=tk.X, pady=(20, 0))
            
            ttk.Button(control_frame, text="📋 Open Documentation",
                      command=self.open_documentation).pack(side=tk.LEFT, padx=(0, 10))
            ttk.Button(control_frame, text="🔄 Refresh Status",
                      command=self.check_database_status).pack(side=tk.LEFT, padx=(0, 10))
            ttk.Button(control_frame, text="❌ Close",
                      command=self.on_close).pack(side=tk.RIGHT)
            
            # Check database status on startup
            self.root.after(100, self.check_database_status)  # Delay initial check
            
        except Exception as e:
            print(f"GUI setup error: {e}")
            self.show_error("GUI Setup Error", f"Failed to setup interface: {e}")
    
    def on_close(self):
        """Handle window close event safely"""
        try:
            if self.root:
                self.root.quit()
                self.root.destroy()
        except Exception as e:
            print(f"Close error: {e}")
        finally:
            import sys
            sys.exit(0)
    
    def show_error(self, title, message):
        """Show error message safely"""
        try:
            if self.root:
                messagebox.showerror(title, str(message)[:300] + "..." if len(str(message)) > 300 else str(message))
            else:
                print(f"ERROR - {title}: {message}")
        except:
            print(f"ERROR - {title}: {message}")
    
    def check_database_status(self):
        """Check current database status safely"""
        try:
            self.db_status_label.config(text="🔄 Checking database...")
            self.root.update()
            
            db_path = "historical_planetary_data.db"
            
            if os.path.exists(db_path):
                import sqlite3
                conn = sqlite3.connect(db_path, timeout=5.0)
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
                        text=f"📊 Database: {count:,} records ({percentage:.1f}%)", 
                        foreground="blue"
                    )
                    self.browser_btn.config(state=tk.NORMAL)
                else:
                    cursor.execute("SELECT MIN(timestamp), MAX(timestamp) FROM planetary_positions")
                    date_range = cursor.fetchone()
                    self.db_status_label.config(
                        text=f"✅ Database complete: {count:,} records", 
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
            error_msg = f"Database check failed: {str(e)[:50]}..."
            self.db_status_label.config(text=f"❌ {error_msg}", foreground="red")
            print(f"Database check error: {e}")
    
    def safe_start_collection(self):
        """Start data collection safely"""
        try:
            # Confirm action
            result = messagebox.askyesno(
                "Start Data Collection",
                "This will collect planetary positions for every minute from 2024-2026.\\n\\n"
                "This may take several hours to complete.\\n\\n"
                "The collection can be paused and resumed.\\n\\n"
                "Do you want to continue?",
                icon='question'
            )
            
            if result:
                # Launch collection in new process
                import subprocess
                subprocess.Popen([
                    sys.executable, "historical_planetary_app.py", "collect"
                ], cwd=os.path.dirname(__file__))
                
                messagebox.showinfo(
                    "Collection Started", 
                    "Data collection started in background.\\n\\n"
                    "You can close this launcher and check progress later.\\n\\n"
                    "The browser will become available as data is collected."
                )
                
                # Refresh status after delay
                self.root.after(3000, self.check_database_status)
                
        except Exception as e:
            self.show_error("Collection Start Error", f"Failed to start collection: {e}")
    
    def safe_start_collection_with_progress(self):
        """Start collection with progress GUI safely"""
        try:
            import subprocess
            subprocess.Popen([
                sys.executable, "historical_planetary_app.py", "progress"
            ], cwd=os.path.dirname(__file__))
            
        except Exception as e:
            self.show_error("Progress Collection Error", f"Failed to start progress collection: {e}")
    
    def safe_start_browser(self):
        """Start data browser safely"""
        try:
            import subprocess
            subprocess.Popen([
                sys.executable, "historical_planetary_app.py", "browser"
            ], cwd=os.path.dirname(__file__))
            
        except Exception as e:
            self.show_error("Browser Start Error", f"Failed to start browser: {e}")
    
    def test_calculator(self):
        """Test the calculator component"""
        try:
            # Add tools to path
            sys.path.append(os.path.join(os.path.dirname(__file__), 'tools'))
            
            from pyjhora_calculator import ProfessionalAstrologyCalculator
            from datetime import datetime
            
            calc = ProfessionalAstrologyCalculator()
            positions = calc.get_planetary_positions(datetime.now())
            
            result_text = "✅ Calculator Test Results:\\n\\n"
            for planet, data in positions.items():
                result_text += f"{planet}: {data['longitude']:.2f}° in {data['sign']}\\n"
            
            messagebox.showinfo("Calculator Test", result_text)
            
        except Exception as e:
            self.show_error("Calculator Test Error", f"Calculator test failed: {e}")
    
    def test_database(self):
        """Test database operations"""
        try:
            import sqlite3
            from datetime import datetime
            
            test_db = "test_db.db"
            
            # Clean up old test
            if os.path.exists(test_db):
                os.remove(test_db)
            
            # Create test database
            conn = sqlite3.connect(test_db)
            cursor = conn.cursor()
            
            cursor.execute('''
            CREATE TABLE test_table (
                id INTEGER PRIMARY KEY,
                timestamp DATETIME,
                data TEXT
            )
            ''')
            
            cursor.execute("INSERT INTO test_table (timestamp, data) VALUES (?, ?)",
                          (datetime.now().isoformat(), "Test data"))
            
            conn.commit()
            
            cursor.execute("SELECT * FROM test_table")
            result = cursor.fetchone()
            
            conn.close()
            os.remove(test_db)
            
            if result:
                messagebox.showinfo("Database Test", "✅ Database test successful!\\n\\nSQLite operations working correctly.")
            else:
                messagebox.showerror("Database Test", "❌ Database test failed - no data returned")
                
        except Exception as e:
            self.show_error("Database Test Error", f"Database test failed: {e}")
    
    def quick_sample(self):
        """Generate a quick sample of data"""
        try:
            sys.path.append(os.path.join(os.path.dirname(__file__), 'tools'))
            
            from pyjhora_calculator import ProfessionalAstrologyCalculator
            from datetime import datetime, timedelta
            
            calc = ProfessionalAstrologyCalculator()
            
            # Generate sample for next few minutes
            sample_text = "🌟 Quick Sample Data:\\n\\n"
            
            for i in range(3):
                sample_time = datetime.now() + timedelta(minutes=i)
                positions = calc.get_planetary_positions(sample_time)
                
                sample_text += f"📅 {sample_time.strftime('%H:%M')}:\\n"
                sample_text += f"  Sun: {positions['Sun']['longitude']:.2f}° in {positions['Sun']['sign']}\\n"
                sample_text += f"  Moon: {positions['Moon']['longitude']:.2f}° in {positions['Moon']['sign']}\\n"
                sample_text += f"  Mars: {positions['Mars']['longitude']:.2f}° in {positions['Mars']['sign']}\\n\\n"
            
            # Show in new window
            sample_window = tk.Toplevel(self.root)
            sample_window.title("Quick Sample Data")
            sample_window.geometry("400x300")
            
            text_widget = tk.Text(sample_window, wrap=tk.WORD, padx=10, pady=10)
            text_widget.insert(tk.END, sample_text)
            text_widget.config(state=tk.DISABLED)
            text_widget.pack(fill=tk.BOTH, expand=True)
            
            ttk.Button(sample_window, text="Close", 
                      command=sample_window.destroy).pack(pady=10)
            
        except Exception as e:
            self.show_error("Sample Generation Error", f"Failed to generate sample: {e}")
    
    def open_documentation(self):
        """Open documentation file"""
        try:
            doc_file = "HISTORICAL_SYSTEM_GUIDE.md"
            if os.path.exists(doc_file):
                import subprocess
                if sys.platform.startswith('win'):
                    subprocess.Popen(['notepad.exe', doc_file])
                else:
                    subprocess.Popen(['xdg-open', doc_file])
            else:
                messagebox.showinfo("Documentation", 
                                   "Documentation file not found.\\n\\n"
                                   "Please check HISTORICAL_SYSTEM_GUIDE.md")
        except Exception as e:
            self.show_error("Documentation Error", f"Failed to open documentation: {e}")
    
    def run(self):
        """Start the launcher with comprehensive error handling"""
        try:
            if not self.root:
                raise Exception("GUI not properly initialized")
                
            self.root.mainloop()
            
        except KeyboardInterrupt:
            print("\\nApplication interrupted by user")
            self.on_close()
        except Exception as e:
            print(f"Application error: {e}")
            traceback.print_exc()
            try:
                self.show_error("Application Error", f"An error occurred: {e}")
            except:
                pass
            self.on_close()

def main():
    """Main function with comprehensive error handling"""
    try:
        print("🌟 Starting Historical Planetary Data System Launcher...")
        launcher = SafeHistoricalSystemLauncher()
        launcher.run()
        
    except Exception as e:
        print(f"Failed to start launcher: {e}")
        traceback.print_exc()
        
        try:
            import tkinter as tk
            from tkinter import messagebox
            root = tk.Tk()
            root.withdraw()
            messagebox.showerror("Startup Error", 
                               f"Failed to start application:\\n{str(e)[:200]}...")
            root.destroy()
        except:
            print("Failed to show error dialog")
            pass
        
        import sys
        sys.exit(1)

if __name__ == "__main__":
    main()