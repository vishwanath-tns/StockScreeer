#!/usr/bin/env python3
"""
Planetary Position Viewer GUI
Display planetary positions from MySQL database for any date/time

Features:
- Date/time picker for 6-month range (Jan-June 2024)
- Complete planetary position display
- Zodiac sign information
- Professional format for verification
- Export functionality for comparison
"""

import tkinter as tk
from tkinter import ttk, messagebox
from tkinter import font as tkfont
from datetime import datetime, timedelta
import pymysql
import os
from dotenv import load_dotenv
import csv

# Load environment variables
load_dotenv()

class PlanetaryPositionViewer:
    def __init__(self, root):
        self.root = root
        self.root.title("🌟 Planetary Position Viewer - Database Browser")
        self.root.geometry("1200x800")
        self.root.configure(bg='#1a1a2e')
        
        # MySQL connection config
        self.mysql_config = {
            'host': os.getenv('MYSQL_HOST', 'localhost'),
            'port': int(os.getenv('MYSQL_PORT', 3306)),
            'user': os.getenv('MYSQL_USER', 'root'),
            'password': os.getenv('MYSQL_PASSWORD', ''),
            'database': os.getenv('MYSQL_DB', 'stock_screener'),
            'charset': 'utf8mb4'
        }
        
        # Color scheme
        self.colors = {
            'bg': '#1a1a2e',
            'card': '#16213e',
            'accent': '#0f3460',
            'primary': '#e94560',
            'text': '#ffffff',
            'secondary': '#a8a8a8',
            'success': '#2ecc71',
            'warning': '#f39c12'
        }
        
        # Fonts
        self.fonts = {
            'title': ('Segoe UI', 16, 'bold'),
            'subtitle': ('Segoe UI', 12, 'bold'),
            'body': ('Segoe UI', 10),
            'small': ('Segoe UI', 9),
            'mono': ('Consolas', 10)
        }
        
        self.setup_ui()
        self.test_database_connection()
        self.load_current_time()
    
    def setup_ui(self):
        """Setup the user interface"""
        
        # Main frame
        main_frame = tk.Frame(self.root, bg=self.colors['bg'])
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Title
        title_frame = tk.Frame(main_frame, bg=self.colors['bg'])
        title_frame.pack(fill=tk.X, pady=(0, 20))
        
        title_label = tk.Label(
            title_frame,
            text="🌟 Planetary Position Viewer",
            font=self.fonts['title'],
            bg=self.colors['bg'],
            fg=self.colors['text']
        )
        title_label.pack(side=tk.LEFT)
        
        subtitle_label = tk.Label(
            title_frame,
            text="Database Browser • Jan-June 2024 • Verify with DrikPanchang & J.Hora",
            font=self.fonts['small'],
            bg=self.colors['bg'],
            fg=self.colors['secondary']
        )
        subtitle_label.pack(side=tk.RIGHT)
        
        # Control panel
        self.setup_control_panel(main_frame)
        
        # Display panel
        self.setup_display_panel(main_frame)
        
        # Status bar
        self.setup_status_bar(main_frame)
    
    def setup_control_panel(self, parent):
        """Setup date/time selection controls"""
        
        control_frame = tk.Frame(parent, bg=self.colors['card'], relief=tk.RAISED, bd=2)
        control_frame.pack(fill=tk.X, pady=(0, 20))
        
        # Control title
        control_title = tk.Label(
            control_frame,
            text="📅 Select Date & Time",
            font=self.fonts['subtitle'],
            bg=self.colors['card'],
            fg=self.colors['text']
        )
        control_title.pack(pady=10)
        
        # Date and time controls
        datetime_frame = tk.Frame(control_frame, bg=self.colors['card'])
        datetime_frame.pack(pady=(0, 15))
        
        # Date selection
        date_frame = tk.Frame(datetime_frame, bg=self.colors['card'])
        date_frame.pack(side=tk.LEFT, padx=20)
        
        tk.Label(date_frame, text="Date:", font=self.fonts['body'], 
                bg=self.colors['card'], fg=self.colors['text']).pack()
        
        # Year
        year_frame = tk.Frame(date_frame, bg=self.colors['card'])
        year_frame.pack(pady=5)
        tk.Label(year_frame, text="Year:", font=self.fonts['small'], 
                bg=self.colors['card'], fg=self.colors['secondary']).pack(side=tk.LEFT)
        self.year_var = tk.StringVar(value="2024")
        year_combo = ttk.Combobox(year_frame, textvariable=self.year_var, 
                                 values=["2024"], width=8, state="readonly")
        year_combo.pack(side=tk.LEFT, padx=(5, 0))
        
        # Month
        month_frame = tk.Frame(date_frame, bg=self.colors['card'])
        month_frame.pack(pady=5)
        tk.Label(month_frame, text="Month:", font=self.fonts['small'], 
                bg=self.colors['card'], fg=self.colors['secondary']).pack(side=tk.LEFT)
        self.month_var = tk.StringVar(value="1")
        month_combo = ttk.Combobox(month_frame, textvariable=self.month_var, 
                                  values=[str(i) for i in range(1, 7)], width=8, state="readonly")
        month_combo.pack(side=tk.LEFT, padx=(5, 0))
        month_combo.bind('<<ComboboxSelected>>', self.on_month_change)
        
        # Day
        day_frame = tk.Frame(date_frame, bg=self.colors['card'])
        day_frame.pack(pady=5)
        tk.Label(day_frame, text="Day:", font=self.fonts['small'], 
                bg=self.colors['card'], fg=self.colors['secondary']).pack(side=tk.LEFT)
        self.day_var = tk.StringVar(value="1")
        self.day_combo = ttk.Combobox(day_frame, textvariable=self.day_var, 
                                     values=[str(i) for i in range(1, 32)], width=8, state="readonly")
        self.day_combo.pack(side=tk.LEFT, padx=(5, 0))
        
        # Time selection
        time_frame = tk.Frame(datetime_frame, bg=self.colors['card'])
        time_frame.pack(side=tk.LEFT, padx=20)
        
        tk.Label(time_frame, text="Time:", font=self.fonts['body'], 
                bg=self.colors['card'], fg=self.colors['text']).pack()
        
        # Hour
        hour_frame = tk.Frame(time_frame, bg=self.colors['card'])
        hour_frame.pack(pady=5)
        tk.Label(hour_frame, text="Hour:", font=self.fonts['small'], 
                bg=self.colors['card'], fg=self.colors['secondary']).pack(side=tk.LEFT)
        self.hour_var = tk.StringVar(value="12")
        hour_combo = ttk.Combobox(hour_frame, textvariable=self.hour_var, 
                                 values=[f"{i:02d}" for i in range(24)], width=8, state="readonly")
        hour_combo.pack(side=tk.LEFT, padx=(5, 0))
        
        # Minute
        minute_frame = tk.Frame(time_frame, bg=self.colors['card'])
        minute_frame.pack(pady=5)
        tk.Label(minute_frame, text="Minute:", font=self.fonts['small'], 
                bg=self.colors['card'], fg=self.colors['secondary']).pack(side=tk.LEFT)
        self.minute_var = tk.StringVar(value="00")
        minute_combo = ttk.Combobox(minute_frame, textvariable=self.minute_var, 
                                   values=[f"{i:02d}" for i in range(60)], width=8, state="readonly")
        minute_combo.pack(side=tk.LEFT, padx=(5, 0))
        
        # Buttons
        button_frame = tk.Frame(datetime_frame, bg=self.colors['card'])
        button_frame.pack(side=tk.LEFT, padx=20)
        
        tk.Label(button_frame, text="Actions:", font=self.fonts['body'], 
                bg=self.colors['card'], fg=self.colors['text']).pack()
        
        load_button = tk.Button(
            button_frame,
            text="🔍 Load Positions",
            command=self.load_planetary_positions,
            bg=self.colors['primary'],
            fg=self.colors['text'],
            font=self.fonts['body'],
            relief=tk.FLAT,
            padx=15,
            pady=5
        )
        load_button.pack(pady=5)
        
        export_button = tk.Button(
            button_frame,
            text="📤 Export CSV",
            command=self.export_positions,
            bg=self.colors['success'],
            fg=self.colors['text'],
            font=self.fonts['body'],
            relief=tk.FLAT,
            padx=15,
            pady=5
        )
        export_button.pack(pady=5)
        
        # Quick selection buttons
        quick_frame = tk.Frame(control_frame, bg=self.colors['card'])
        quick_frame.pack(pady=(0, 15))
        
        tk.Label(quick_frame, text="🚀 Quick Select:", font=self.fonts['small'], 
                bg=self.colors['card'], fg=self.colors['secondary']).pack()
        
        quick_buttons = tk.Frame(quick_frame, bg=self.colors['card'])
        quick_buttons.pack(pady=5)
        
        quick_times = [
            ("Now", self.set_current_time),
            ("Jan 1", lambda: self.set_quick_date(1, 1)),
            ("Mar 15", lambda: self.set_quick_date(3, 15)),
            ("Jun 30", lambda: self.set_quick_date(6, 30))
        ]
        
        for text, command in quick_times:
            btn = tk.Button(
                quick_buttons,
                text=text,
                command=command,
                bg=self.colors['accent'],
                fg=self.colors['text'],
                font=self.fonts['small'],
                relief=tk.FLAT,
                padx=10,
                pady=3
            )
            btn.pack(side=tk.LEFT, padx=5)
    
    def setup_display_panel(self, parent):
        """Setup planetary position display panel"""
        
        display_frame = tk.Frame(parent, bg=self.colors['card'], relief=tk.RAISED, bd=2)
        display_frame.pack(fill=tk.BOTH, expand=True)
        
        # Display title
        display_title = tk.Label(
            display_frame,
            text="🌍 Planetary Positions",
            font=self.fonts['subtitle'],
            bg=self.colors['card'],
            fg=self.colors['text']
        )
        display_title.pack(pady=10)
        
        # Create notebook for tabs
        self.notebook = ttk.Notebook(display_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=20, pady=(0, 20))
        
        # Position display tab
        self.setup_position_tab()
        
        # Raw data tab
        self.setup_raw_data_tab()
        
        # Verification tab
        self.setup_verification_tab()
    
    def setup_position_tab(self):
        """Setup the main position display tab"""
        
        position_frame = tk.Frame(self.notebook, bg=self.colors['bg'])
        self.notebook.add(position_frame, text="🪐 Positions")
        
        # Selected time display
        time_display_frame = tk.Frame(position_frame, bg=self.colors['card'], relief=tk.RAISED, bd=1)
        time_display_frame.pack(fill=tk.X, padx=20, pady=20)
        
        self.selected_time_label = tk.Label(
            time_display_frame,
            text="Selected Time: Please select a date and time",
            font=self.fonts['subtitle'],
            bg=self.colors['card'],
            fg=self.colors['warning']
        )
        self.selected_time_label.pack(pady=10)
        
        # Planets display
        planets_frame = tk.Frame(position_frame, bg=self.colors['bg'])
        planets_frame.pack(fill=tk.BOTH, expand=True, padx=20)
        
        # Create planet cards in a grid
        self.planet_cards = {}
        planets = [
            ('Sun', '☉', self.colors['warning']),
            ('Moon', '☽', self.colors['secondary']),
            ('Mercury', '☿', self.colors['success']),
            ('Venus', '♀', self.colors['primary']),
            ('Mars', '♂', '#e74c3c'),
            ('Jupiter', '♃', '#9b59b6'),
            ('Saturn', '♄', '#34495e')
        ]
        
        for i, (planet, symbol, color) in enumerate(planets):
            row = i // 3
            col = i % 3
            
            card_frame = tk.Frame(planets_frame, bg=color, relief=tk.RAISED, bd=2)
            card_frame.grid(row=row, column=col, padx=10, pady=10, sticky='nsew')
            
            # Configure grid weights
            planets_frame.grid_rowconfigure(row, weight=1)
            planets_frame.grid_columnconfigure(col, weight=1)
            
            # Planet header
            header_frame = tk.Frame(card_frame, bg=color)
            header_frame.pack(fill=tk.X, pady=5)
            
            symbol_label = tk.Label(header_frame, text=symbol, font=('Segoe UI', 20), 
                                   bg=color, fg='white')
            symbol_label.pack(side=tk.LEFT, padx=10)
            
            name_label = tk.Label(header_frame, text=planet, font=self.fonts['subtitle'], 
                                 bg=color, fg='white')
            name_label.pack(side=tk.LEFT)
            
            # Planet data
            data_frame = tk.Frame(card_frame, bg='white')
            data_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=(0, 5))
            
            self.planet_cards[planet.lower()] = {
                'longitude': tk.Label(data_frame, text="Longitude: --", font=self.fonts['body'], bg='white'),
                'sign': tk.Label(data_frame, text="Sign: --", font=self.fonts['body'], bg='white'),
                'degree': tk.Label(data_frame, text="Degree in Sign: --", font=self.fonts['body'], bg='white')
            }
            
            self.planet_cards[planet.lower()]['longitude'].pack(anchor='w', padx=10, pady=2)
            self.planet_cards[planet.lower()]['sign'].pack(anchor='w', padx=10, pady=2)
            self.planet_cards[planet.lower()]['degree'].pack(anchor='w', padx=10, pady=2)
    
    def setup_raw_data_tab(self):
        """Setup raw data display tab"""
        
        raw_frame = tk.Frame(self.notebook, bg=self.colors['bg'])
        self.notebook.add(raw_frame, text="📊 Raw Data")
        
        # Raw data text widget
        text_frame = tk.Frame(raw_frame, bg=self.colors['bg'])
        text_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Scrollable text widget
        text_widget_frame = tk.Frame(text_frame, bg=self.colors['card'])
        text_widget_frame.pack(fill=tk.BOTH, expand=True)
        
        self.raw_data_text = tk.Text(
            text_widget_frame,
            font=self.fonts['mono'],
            bg='#2c2c54',
            fg='#ffffff',
            wrap=tk.WORD,
            state=tk.DISABLED
        )
        
        scrollbar = ttk.Scrollbar(text_widget_frame, orient=tk.VERTICAL, command=self.raw_data_text.yview)
        self.raw_data_text.configure(yscrollcommand=scrollbar.set)
        
        self.raw_data_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    
    def setup_verification_tab(self):
        """Setup verification comparison tab"""
        
        verify_frame = tk.Frame(self.notebook, bg=self.colors['bg'])
        self.notebook.add(verify_frame, text="✅ Verification")
        
        # Instructions
        instructions = tk.Label(
            verify_frame,
            text="📝 Verification Guide:\n\n" +
                 "1. Select date/time and load positions\n" +
                 "2. Compare with DrikPanchang (https://www.drikpanchang.com/)\n" +
                 "3. Compare with Jagannatha Hora software\n" +
                 "4. Export CSV for detailed analysis\n" +
                 "5. Note any discrepancies for improvement",
            font=self.fonts['body'],
            bg=self.colors['bg'],
            fg=self.colors['text'],
            justify=tk.LEFT
        )
        instructions.pack(pady=20, padx=20)
        
        # Verification results
        self.verification_frame = tk.Frame(verify_frame, bg=self.colors['card'], relief=tk.RAISED, bd=2)
        self.verification_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        verify_title = tk.Label(
            self.verification_frame,
            text="🔍 Verification Results",
            font=self.fonts['subtitle'],
            bg=self.colors['card'],
            fg=self.colors['text']
        )
        verify_title.pack(pady=10)
        
        self.verification_text = tk.Text(
            self.verification_frame,
            font=self.fonts['mono'],
            bg='#2c2c54',
            fg='#ffffff',
            wrap=tk.WORD,
            state=tk.DISABLED,
            height=15
        )
        self.verification_text.pack(fill=tk.BOTH, expand=True, padx=20, pady=(0, 20))
    
    def setup_status_bar(self, parent):
        """Setup status bar"""
        
        status_frame = tk.Frame(parent, bg=self.colors['accent'], relief=tk.SUNKEN, bd=1)
        status_frame.pack(fill=tk.X, pady=(20, 0))
        
        self.status_label = tk.Label(
            status_frame,
            text="Ready • Select date/time and load planetary positions",
            font=self.fonts['small'],
            bg=self.colors['accent'],
            fg=self.colors['text']
        )
        self.status_label.pack(side=tk.LEFT, padx=10, pady=5)
        
        self.db_status_label = tk.Label(
            status_frame,
            text="Database: Disconnected",
            font=self.fonts['small'],
            bg=self.colors['accent'],
            fg=self.colors['secondary']
        )
        self.db_status_label.pack(side=tk.RIGHT, padx=10, pady=5)
    
    def test_database_connection(self):
        """Test database connection on startup"""
        try:
            conn = pymysql.connect(**self.mysql_config)
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM planetary_positions")
            count = cursor.fetchone()[0]
            conn.close()
            
            self.db_status_label.config(
                text=f"Database: Connected ({count:,} records)",
                fg=self.colors['success']
            )
            self.status_label.config(text=f"Ready • Database connected with {count:,} records")
            
        except Exception as e:
            self.db_status_label.config(
                text=f"Database: Error - {str(e)[:30]}...",
                fg=self.colors['primary']
            )
            self.status_label.config(text="Database connection failed")
    
    def on_month_change(self, event=None):
        """Update days when month changes"""
        try:
            month = int(self.month_var.get())
            year = int(self.year_var.get())
            
            if month == 2:
                days = 29 if year % 4 == 0 else 28
            elif month in [4, 6, 9, 11]:
                days = 30
            else:
                days = 31
            
            # Limit to available data range
            if month == 6:  # June - only up to 30th
                days = 30
            
            self.day_combo['values'] = [str(i) for i in range(1, days + 1)]
            
            # Reset day to 1 if current day is invalid
            current_day = int(self.day_var.get())
            if current_day > days:
                self.day_var.set("1")
                
        except ValueError:
            pass
    
    def load_current_time(self):
        """Load current time (within available range)"""
        # Set to a time within our data range
        self.year_var.set("2024")
        self.month_var.set("3")
        self.day_var.set("15")
        self.hour_var.set("12")
        self.minute_var.set("00")
        self.on_month_change()
    
    def set_current_time(self):
        """Set to a representative time"""
        self.load_current_time()
        self.load_planetary_positions()
    
    def set_quick_date(self, month, day):
        """Set quick date"""
        self.month_var.set(str(month))
        self.day_var.set(str(day))
        self.hour_var.set("12")
        self.minute_var.set("00")
        self.on_month_change()
        self.load_planetary_positions()
    
    def load_planetary_positions(self):
        """Load planetary positions from database"""
        try:
            # Get selected datetime
            year = int(self.year_var.get())
            month = int(self.month_var.get())
            day = int(self.day_var.get())
            hour = int(self.hour_var.get())
            minute = int(self.minute_var.get())
            
            selected_datetime = datetime(year, month, day, hour, minute)
            
            # Connect to database
            conn = pymysql.connect(**self.mysql_config)
            cursor = conn.cursor()
            
            # Query planetary positions
            query = """
            SELECT * FROM planetary_positions 
            WHERE timestamp = %s
            """
            
            cursor.execute(query, (selected_datetime,))
            result = cursor.fetchone()
            
            if result:
                self.display_planetary_positions(result, selected_datetime)
                self.status_label.config(text=f"Loaded positions for {selected_datetime}")
            else:
                self.clear_positions()
                self.status_label.config(text=f"No data found for {selected_datetime}")
                messagebox.showwarning("No Data", f"No planetary position data found for {selected_datetime}")
            
            conn.close()
            
        except Exception as e:
            self.status_label.config(text=f"Error loading positions: {e}")
            messagebox.showerror("Database Error", f"Failed to load positions:\n{e}")
    
    def display_planetary_positions(self, data, selected_datetime):
        """Display planetary positions in the GUI"""
        
        # Update selected time label
        formatted_time = selected_datetime.strftime("%A, %B %d, %Y at %I:%M %p")
        self.selected_time_label.config(
            text=f"Selected Time: {formatted_time}",
            fg=self.colors['success']
        )
        
        # Column mapping from database
        columns = [
            'id', 'timestamp', 'year', 'month', 'day', 'hour', 'minute',
            'sun_longitude', 'sun_sign', 'sun_degree',
            'moon_longitude', 'moon_sign', 'moon_degree',
            'mercury_longitude', 'mercury_sign', 'mercury_degree',
            'venus_longitude', 'venus_sign', 'venus_degree',
            'mars_longitude', 'mars_sign', 'mars_degree',
            'jupiter_longitude', 'jupiter_sign', 'jupiter_degree',
            'saturn_longitude', 'saturn_sign', 'saturn_degree',
            'rahu_longitude', 'rahu_sign', 'rahu_degree',
            'ketu_longitude', 'ketu_sign', 'ketu_degree',
            'created_at', 'updated_at'
        ]
        
        # Create data dictionary
        data_dict = dict(zip(columns, data))
        
        # Update planet cards
        planets = ['sun', 'moon', 'mercury', 'venus', 'mars', 'jupiter', 'saturn']
        
        for planet in planets:
            if planet in self.planet_cards:
                longitude = data_dict.get(f'{planet}_longitude', 0)
                sign = data_dict.get(f'{planet}_sign', 'Unknown')
                degree = data_dict.get(f'{planet}_degree', 0)
                
                if longitude is not None:
                    self.planet_cards[planet]['longitude'].config(
                        text=f"Longitude: {longitude:.4f}°"
                    )
                    self.planet_cards[planet]['sign'].config(
                        text=f"Sign: {sign}"
                    )
                    self.planet_cards[planet]['degree'].config(
                        text=f"Degree in Sign: {degree:.4f}°"
                    )
                else:
                    self.planet_cards[planet]['longitude'].config(text="Longitude: No data")
                    self.planet_cards[planet]['sign'].config(text="Sign: No data")
                    self.planet_cards[planet]['degree'].config(text="Degree: No data")
        
        # Update raw data display
        self.update_raw_data_display(data_dict, selected_datetime)
        
        # Update verification display
        self.update_verification_display(data_dict, selected_datetime)
    
    def update_raw_data_display(self, data_dict, selected_datetime):
        """Update raw data display"""
        
        self.raw_data_text.config(state=tk.NORMAL)
        self.raw_data_text.delete(1.0, tk.END)
        
        raw_text = f"""
PLANETARY POSITIONS - RAW DATABASE DATA
{'='*60}

Query Time: {selected_datetime}
Database ID: {data_dict.get('id', 'N/A')}
Created At: {data_dict.get('created_at', 'N/A')}

PLANETARY LONGITUDES (Degrees)
{'='*60}
Sun      : {data_dict.get('sun_longitude', 0):.6f}° in {data_dict.get('sun_sign', 'Unknown')} ({data_dict.get('sun_degree', 0):.6f}°)
Moon     : {data_dict.get('moon_longitude', 0):.6f}° in {data_dict.get('moon_sign', 'Unknown')} ({data_dict.get('moon_degree', 0):.6f}°)
Mercury  : {data_dict.get('mercury_longitude', 0):.6f}° in {data_dict.get('mercury_sign', 'Unknown')} ({data_dict.get('mercury_degree', 0):.6f}°)
Venus    : {data_dict.get('venus_longitude', 0):.6f}° in {data_dict.get('venus_sign', 'Unknown')} ({data_dict.get('venus_degree', 0):.6f}°)
Mars     : {data_dict.get('mars_longitude', 0):.6f}° in {data_dict.get('mars_sign', 'Unknown')} ({data_dict.get('mars_degree', 0):.6f}°)
Jupiter  : {data_dict.get('jupiter_longitude', 0):.6f}° in {data_dict.get('jupiter_sign', 'Unknown')} ({data_dict.get('jupiter_degree', 0):.6f}°)
Saturn   : {data_dict.get('saturn_longitude', 0):.6f}° in {data_dict.get('saturn_sign', 'Unknown')} ({data_dict.get('saturn_degree', 0):.6f}°)
Rahu     : {data_dict.get('rahu_longitude', 0):.6f}° in {data_dict.get('rahu_sign', 'Unknown')} ({data_dict.get('rahu_degree', 0):.6f}°)
Ketu     : {data_dict.get('ketu_longitude', 0):.6f}° in {data_dict.get('ketu_sign', 'Unknown')} ({data_dict.get('ketu_degree', 0):.6f}°)

ZODIAC SIGN MAPPING
{'='*60}
Aries (0-30°), Taurus (30-60°), Gemini (60-90°), Cancer (90-120°)
Leo (120-150°), Virgo (150-180°), Libra (180-210°), Scorpio (210-240°)
Sagittarius (240-270°), Capricorn (270-300°), Aquarius (300-330°), Pisces (330-360°)

VERIFICATION NOTES
{'='*60}
- Compare longitudes with DrikPanchang
- Verify signs and degrees with Jagannatha Hora
- Check time zone consistency (should be UTC/GMT)
- Note any discrepancies for improvement

DATABASE METADATA
{'='*60}
Year: {data_dict.get('year', 'N/A')}
Month: {data_dict.get('month', 'N/A')}
Day: {data_dict.get('day', 'N/A')}
Hour: {data_dict.get('hour', 'N/A')}
Minute: {data_dict.get('minute', 'N/A')}
"""
        
        self.raw_data_text.insert(1.0, raw_text)
        self.raw_data_text.config(state=tk.DISABLED)
    
    def update_verification_display(self, data_dict, selected_datetime):
        """Update verification display"""
        
        self.verification_text.config(state=tk.NORMAL)
        self.verification_text.delete(1.0, tk.END)
        
        verification_text = f"""
VERIFICATION CHECKLIST - {selected_datetime}
{'='*60}

✅ DATABASE VERIFICATION:
   ✓ Record found in MySQL database
   ✓ Timestamp: {selected_datetime}
   ✓ Database ID: {data_dict.get('id', 'N/A')}

🌐 DRIK PANCHANG COMPARISON:
   Website: https://www.drikpanchang.com/
   
   Instructions:
   1. Go to DrikPanchang website
   2. Navigate to Panchang → Planetary Positions
   3. Set date: {selected_datetime.strftime('%B %d, %Y')}
   4. Set time: {selected_datetime.strftime('%I:%M %p')}
   5. Compare longitude values below:
   
   OUR DATA vs DRIK PANCHANG:
   Sun     : {data_dict.get('sun_longitude', 0):.4f}° vs [ Enter DrikPanchang value ]
   Moon    : {data_dict.get('moon_longitude', 0):.4f}° vs [ Enter DrikPanchang value ]
   Mercury : {data_dict.get('mercury_longitude', 0):.4f}° vs [ Enter DrikPanchang value ]
   Venus   : {data_dict.get('venus_longitude', 0):.4f}° vs [ Enter DrikPanchang value ]
   Mars    : {data_dict.get('mars_longitude', 0):.4f}° vs [ Enter DrikPanchang value ]
   Jupiter : {data_dict.get('jupiter_longitude', 0):.4f}° vs [ Enter DrikPanchang value ]
   Saturn  : {data_dict.get('saturn_longitude', 0):.4f}° vs [ Enter DrikPanchang value ]

🖥️  JAGANNATHA HORA COMPARISON:
   Software: Jagannatha Hora (desktop software)
   
   Instructions:
   1. Open Jagannatha Hora software
   2. Set date/time: {selected_datetime.strftime('%B %d, %Y %I:%M %p')}
   3. View planetary positions
   4. Compare with values above
   5. Note any discrepancies

📊 ACCURACY EXPECTATIONS:
   ✓ Longitude accuracy: ±0.1° (6 arcminutes)
   ✓ Sign accuracy: Should match exactly
   ✓ Degree in sign: ±0.1°
   ✓ Time zone: Verify UTC consistency

💡 NOTES:
   - Small differences (< 0.1°) are normal due to calculation methods
   - Large differences (> 1°) indicate potential issues
   - Check time zone settings if major discrepancies exist
   - Document any patterns or systematic errors
"""
        
        self.verification_text.insert(1.0, verification_text)
        self.verification_text.config(state=tk.DISABLED)
    
    def clear_positions(self):
        """Clear all position displays"""
        
        self.selected_time_label.config(
            text="Selected Time: Please select a date and time",
            fg=self.colors['warning']
        )
        
        # Clear planet cards
        for planet in self.planet_cards:
            self.planet_cards[planet]['longitude'].config(text="Longitude: --")
            self.planet_cards[planet]['sign'].config(text="Sign: --")
            self.planet_cards[planet]['degree'].config(text="Degree in Sign: --")
        
        # Clear raw data
        self.raw_data_text.config(state=tk.NORMAL)
        self.raw_data_text.delete(1.0, tk.END)
        self.raw_data_text.insert(1.0, "No data loaded. Please select a date/time and click 'Load Positions'.")
        self.raw_data_text.config(state=tk.DISABLED)
        
        # Clear verification
        self.verification_text.config(state=tk.NORMAL)
        self.verification_text.delete(1.0, tk.END)
        self.verification_text.insert(1.0, "No data loaded for verification.")
        self.verification_text.config(state=tk.DISABLED)
    
    def export_positions(self):
        """Export current positions to CSV"""
        try:
            # Get selected datetime
            year = int(self.year_var.get())
            month = int(self.month_var.get())
            day = int(self.day_var.get())
            hour = int(self.hour_var.get())
            minute = int(self.minute_var.get())
            
            selected_datetime = datetime(year, month, day, hour, minute)
            
            # Connect to database
            conn = pymysql.connect(**self.mysql_config)
            cursor = conn.cursor()
            
            # Query data
            cursor.execute("SELECT * FROM planetary_positions WHERE timestamp = %s", (selected_datetime,))
            result = cursor.fetchone()
            
            if result:
                # Get column names
                cursor.execute("DESCRIBE planetary_positions")
                columns = [col[0] for col in cursor.fetchall()]
                
                # Create filename
                filename = f"planetary_positions_{selected_datetime.strftime('%Y%m%d_%H%M')}.csv"
                
                # Write CSV
                with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
                    writer = csv.writer(csvfile)
                    writer.writerow(columns)
                    writer.writerow(result)
                
                messagebox.showinfo("Export Success", f"Data exported to: {filename}")
                self.status_label.config(text=f"Data exported to {filename}")
            else:
                messagebox.showwarning("No Data", "No data to export. Please load positions first.")
            
            conn.close()
            
        except Exception as e:
            messagebox.showerror("Export Error", f"Failed to export data:\n{e}")

def main():
    """Main function"""
    root = tk.Tk()
    app = PlanetaryPositionViewer(root)
    root.mainloop()

if __name__ == "__main__":
    main()