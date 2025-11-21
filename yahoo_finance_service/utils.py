"""
Utility functions for Yahoo Finance service
"""

import os
import sys
from datetime import datetime, date, timedelta
import logging

def setup_logging(log_level='INFO', log_file=None):
    """Setup logging configuration"""
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    
    if log_file:
        logging.basicConfig(
            level=getattr(logging, log_level),
            format=log_format,
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler(sys.stdout)
            ]
        )
    else:
        logging.basicConfig(
            level=getattr(logging, log_level),
            format=log_format,
            handlers=[logging.StreamHandler(sys.stdout)]
        )

def validate_date_range(start_date: date, end_date: date) -> bool:
    """Validate date range"""
    if start_date > end_date:
        raise ValueError("Start date must be before end date")
    
    if end_date > date.today():
        raise ValueError("End date cannot be in the future")
    
    if start_date < date(1990, 1, 1):
        raise ValueError("Start date too far in the past")
    
    return True

def get_market_days(start_date: date, end_date: date) -> int:
    """Estimate number of market days between two dates"""
    total_days = (end_date - start_date).days + 1
    
    # Rough estimate: 5/7 days are market days, minus holidays
    estimated_market_days = int(total_days * 5/7 * 0.95)  # 95% to account for holidays
    
    return max(1, estimated_market_days)

def format_number(num: int) -> str:
    """Format number with thousands separator"""
    return f"{num:,}"

def format_currency(amount: float, currency='INR') -> str:
    """Format currency amount"""
    if currency == 'INR':
        return f"₹{amount:,.2f}"
    else:
        return f"{amount:,.2f} {currency}"

def get_project_root() -> str:
    """Get project root directory"""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.dirname(current_dir)

def ensure_directory(path: str) -> str:
    """Ensure directory exists"""
    if not os.path.exists(path):
        os.makedirs(path)
    return path

def get_business_days_between(start_date: date, end_date: date) -> list:
    """Get list of business days between two dates"""
    business_days = []
    current_date = start_date
    
    while current_date <= end_date:
        # Monday is 0, Sunday is 6
        if current_date.weekday() < 5:  # Monday to Friday
            business_days.append(current_date)
        current_date += timedelta(days=1)
    
    return business_days