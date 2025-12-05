"""
FNO File Parser
Parses NSE F&O bhavcopy files (futures and options)
"""

import os
import re
import hashlib
from datetime import datetime, date
from typing import Tuple, Optional, Dict
import pandas as pd


# Column mapping from file to database
FUTURES_COLMAP = {
    'CONTRACT_D': 'contract_descriptor',
    'PREVIOUS_S': 'previous_close',
    'OPEN_PRICE': 'open_price',
    'HIGH_PRICE': 'high_price',
    'LOW_PRICE': 'low_price',
    'CLOSE_PRIC': 'close_price',
    'SETTLEMENT': 'settlement_price',
    'NET_CHANGE': 'net_change_pct',
    'OI_NO_CON': 'open_interest',
    'TRADED_QUA': 'traded_quantity',
    'TRD_NO_CON': 'number_of_trades',
    'TRADED_VAL': 'traded_value'
}

OPTIONS_COLMAP = {
    'CONTRACT_D': 'contract_descriptor',
    'PREVIOUS_S': 'previous_close',
    'OPEN_PRICE': 'open_price',
    'HIGH_PRICE': 'high_price',
    'LOW_PRICE': 'low_price',
    'CLOSE_PRIC': 'close_price',
    'SETTLEMENT': 'settlement_price',
    'NET_CHANGE': 'net_change_pct',
    'OI_NO_CON': 'open_interest',
    'TRADED_QUA': 'traded_quantity',
    'TRD_NO_CON': 'number_of_trades',
    'UNDRLNG_ST': 'underlying_price',
    'NOTIONAL_V': 'notional_value',
    'PREMIUM_TR': 'premium_traded'
}


def md5_of_file(filepath: str) -> str:
    """Calculate MD5 checksum of a file."""
    hash_md5 = hashlib.md5()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()


def parse_date_from_filename(filename: str) -> Optional[date]:
    """
    Extract trade date from filename.
    Format: fo031225.csv -> 03-Dec-2025
    Format: op031225.csv -> 03-Dec-2025
    """
    basename = os.path.basename(filename)
    # Remove extension and prefix (fo or op)
    match = re.search(r'[fo|op](\d{6})', basename.lower())
    if match:
        date_str = match.group(1)  # DDMMYY
        try:
            day = int(date_str[0:2])
            month = int(date_str[2:4])
            year = int(date_str[4:6]) + 2000  # Assuming 20xx
            return date(year, month, day)
        except ValueError:
            pass
    return None


def parse_contract_descriptor(contract: str) -> Dict:
    """
    Parse the contract descriptor to extract symbol, expiry, option type, strike.
    
    Examples:
    - FUTSTKADANIENSOL24-FEB-2026 -> {symbol: ADANIENSOL, expiry: 24-Feb-2026, type: FUT}
    - OPTSTKADANIENSOL27-JAN-2026PE1000 -> {symbol: ADANIENSOL, expiry: 27-Jan-2026, type: PE, strike: 1000}
    - FUTIDXNIFTY30-DEC-2025 -> {symbol: NIFTY, expiry: 30-Dec-2025, type: FUT, instrument: INDEX}
    - OPTIDXNIFTY04-DEC-2025CE24600 -> {symbol: NIFTY, expiry: 04-Dec-2025, type: CE, strike: 24600}
    """
    result = {
        'symbol': None,
        'expiry_date': None,
        'option_type': None,
        'strike_price': None,
        'instrument_type': None
    }
    
    if not contract:
        return result
    
    contract = contract.strip()
    
    # Determine instrument type (FUTIDX/OPTIDX for index, FUTSTK/OPTSTK for stock)
    if contract.startswith('FUTIDX') or contract.startswith('OPTIDX'):
        result['instrument_type'] = 'FUTIDX' if contract.startswith('FUT') else 'OPTIDX'
        prefix_len = 6
    elif contract.startswith('FUTSTK') or contract.startswith('OPTSTK'):
        result['instrument_type'] = 'FUTSTK' if contract.startswith('FUT') else 'OPTSTK'
        prefix_len = 6
    else:
        return result
    
    remaining = contract[prefix_len:]
    
    # Parse based on whether it's futures or options
    is_option = contract.startswith('OPT')
    
    if is_option:
        # Options: SYMBOL + DATE + (CE/PE) + STRIKE
        # Find CE or PE position
        ce_pos = remaining.rfind('CE')
        pe_pos = remaining.rfind('PE')
        
        if ce_pos > 0:
            opt_pos = ce_pos
            result['option_type'] = 'CE'
        elif pe_pos > 0:
            opt_pos = pe_pos
            result['option_type'] = 'PE'
        else:
            return result
        
        # Strike is after option type
        strike_str = remaining[opt_pos + 2:]
        try:
            result['strike_price'] = float(strike_str)
        except ValueError:
            pass
        
        # Symbol and date before option type
        symbol_date = remaining[:opt_pos]
    else:
        # Futures: SYMBOL + DATE
        symbol_date = remaining
    
    # Parse symbol and expiry date
    # Date format: DD-MMM-YYYY (e.g., 30-DEC-2025)
    date_pattern = r'(\d{2}-[A-Z]{3}-\d{4})$'
    match = re.search(date_pattern, symbol_date)
    
    if match:
        date_str = match.group(1)
        result['symbol'] = symbol_date[:match.start()]
        
        try:
            result['expiry_date'] = datetime.strptime(date_str, '%d-%b-%Y').date()
        except ValueError:
            pass
    
    return result


def parse_futures_file(filepath: str) -> Tuple[pd.DataFrame, date]:
    """
    Parse futures bhavcopy file.
    Returns DataFrame and trade date.
    """
    trade_date = parse_date_from_filename(filepath)
    if not trade_date:
        raise ValueError(f"Cannot determine trade date from filename: {filepath}")
    
    # Read CSV
    df = pd.read_csv(filepath)
    
    # Rename columns
    df = df.rename(columns=FUTURES_COLMAP)
    
    # Parse contract descriptor
    parsed = df['contract_descriptor'].apply(parse_contract_descriptor)
    df['symbol'] = parsed.apply(lambda x: x['symbol'])
    df['expiry_date'] = parsed.apply(lambda x: x['expiry_date'])
    df['instrument_type'] = parsed.apply(lambda x: x['instrument_type'])
    
    # Clean numeric columns
    numeric_cols = ['previous_close', 'open_price', 'high_price', 'low_price', 
                    'close_price', 'settlement_price', 'net_change_pct', 
                    'open_interest', 'traded_quantity', 'number_of_trades', 'traded_value']
    
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    
    # Convert to appropriate types
    df['open_interest'] = df['open_interest'].astype(int)
    df['traded_quantity'] = df['traded_quantity'].astype(int)
    df['number_of_trades'] = df['number_of_trades'].astype(int)
    
    # Filter out rows with invalid symbols
    df = df[df['symbol'].notna() & (df['symbol'] != '')]
    
    # Select final columns
    final_cols = ['contract_descriptor', 'symbol', 'expiry_date', 'instrument_type',
                  'previous_close', 'open_price', 'high_price', 'low_price',
                  'close_price', 'settlement_price', 'net_change_pct',
                  'open_interest', 'traded_quantity', 'number_of_trades', 'traded_value']
    
    df = df[[col for col in final_cols if col in df.columns]]
    
    return df, trade_date


def parse_options_file(filepath: str) -> Tuple[pd.DataFrame, date]:
    """
    Parse options bhavcopy file.
    Returns DataFrame and trade date.
    """
    trade_date = parse_date_from_filename(filepath)
    if not trade_date:
        raise ValueError(f"Cannot determine trade date from filename: {filepath}")
    
    # Read CSV
    df = pd.read_csv(filepath)
    
    # Rename columns
    df = df.rename(columns=OPTIONS_COLMAP)
    
    # Parse contract descriptor
    parsed = df['contract_descriptor'].apply(parse_contract_descriptor)
    df['symbol'] = parsed.apply(lambda x: x['symbol'])
    df['expiry_date'] = parsed.apply(lambda x: x['expiry_date'])
    df['option_type'] = parsed.apply(lambda x: x['option_type'])
    df['strike_price'] = parsed.apply(lambda x: x['strike_price'])
    df['instrument_type'] = parsed.apply(lambda x: x['instrument_type'])
    
    # Clean numeric columns
    numeric_cols = ['previous_close', 'open_price', 'high_price', 'low_price',
                    'close_price', 'settlement_price', 'net_change_pct',
                    'open_interest', 'traded_quantity', 'number_of_trades',
                    'underlying_price', 'notional_value', 'premium_traded']
    
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    
    # Convert to appropriate types
    df['open_interest'] = df['open_interest'].astype(int)
    df['traded_quantity'] = df['traded_quantity'].astype(int)
    df['number_of_trades'] = df['number_of_trades'].astype(int)
    
    # Filter out rows with invalid symbols
    df = df[df['symbol'].notna() & (df['symbol'] != '')]
    df = df[df['option_type'].notna()]
    
    # Select final columns
    final_cols = ['contract_descriptor', 'symbol', 'expiry_date', 'option_type', 
                  'strike_price', 'instrument_type',
                  'previous_close', 'open_price', 'high_price', 'low_price',
                  'close_price', 'settlement_price', 'net_change_pct',
                  'open_interest', 'traded_quantity', 'number_of_trades',
                  'underlying_price', 'notional_value', 'premium_traded']
    
    df = df[[col for col in final_cols if col in df.columns]]
    
    return df, trade_date


def detect_file_type(filepath: str) -> Optional[str]:
    """Detect if file is futures or options based on filename."""
    basename = os.path.basename(filepath).lower()
    if basename.startswith('fo') and basename.endswith('.csv'):
        return 'futures'
    elif basename.startswith('op') and basename.endswith('.csv'):
        return 'options'
    return None


def find_fno_files(folder_path: str) -> Dict[str, str]:
    """
    Find futures and options files in a folder.
    Returns dict with 'futures' and 'options' keys pointing to file paths.
    """
    result = {'futures': None, 'options': None}
    
    if not os.path.isdir(folder_path):
        return result
    
    for filename in os.listdir(folder_path):
        if not filename.lower().endswith('.csv'):
            continue
        
        filepath = os.path.join(folder_path, filename)
        file_type = detect_file_type(filepath)
        
        if file_type:
            result[file_type] = filepath
    
    return result


if __name__ == "__main__":
    # Test parsing
    test_contracts = [
        "FUTSTKADANIENSOL24-FEB-2026",
        "FUTIDXNIFTY30-DEC-2025",
        "OPTSTKADANIENSOL27-JAN-2026PE1000",
        "OPTIDXNIFTY04-DEC-2025CE24600",
        "OPTIDXBANKNIFTY04-DEC-2025PE52000"
    ]
    
    print("Testing contract descriptor parsing:")
    print("-" * 60)
    for contract in test_contracts:
        result = parse_contract_descriptor(contract)
        print(f"{contract}")
        print(f"  -> {result}")
        print()
