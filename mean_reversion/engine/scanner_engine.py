import multiprocessing
import queue
import time
from datetime import datetime
import sys
import pandas as pd

# Imports from sibling packages need path handling if running as script
# But we will run from root context usually
from mean_reversion.core.strategies import StrategyRegistry
from mean_reversion.data_access.data_loader import DatabaseLoader
from mean_reversion.core.events import ScanResult

def _worker(input_queue, output_queue):
    """
    Worker process to consume symbols and produce results
    """
    # Create DB connection per process
    db = DatabaseLoader()
    
    while True:
        try:
            task = input_queue.get(timeout=1) # 1s timeout to check for exit
            if task == "STOP":
                break
                
            symbol = task
            
            # Fetch data
            df = db.fetch_data(symbol, days=200)
            if df.empty or len(df) < 50:
                continue
                
            # Run strategies
            # 1. RSI
            rsi_sig, rsi_details = StrategyRegistry.analyze_rsi_strategy(df, symbol)
            if rsi_sig != 'NEUTRAL':
                result = ScanResult(
                    symbol=symbol,
                    last_price=rsi_details.get('price', df['close'].iloc[-1]),
                    signal_type=rsi_sig,
                    strategy_name='RSI(2)',
                    confidence=1.0, # Placeholder
                    details=rsi_details,
                    timestamp=rsi_details.get('date', datetime.now())
                )
                output_queue.put(result)
                
            # 2. Bollinger Bands
            bb_sig, bb_details = StrategyRegistry.analyze_bb_strategy(df, symbol)
            if bb_sig != 'NEUTRAL':
                result = ScanResult(
                    symbol=symbol,
                    last_price=bb_details.get('price', df['close'].iloc[-1]),
                    signal_type=bb_sig,
                    strategy_name='Bollinger',
                    confidence=1.0,
                    details=bb_details,
                    timestamp=bb_details.get('date', datetime.now())
                )
                output_queue.put(result)
                
        except queue.Empty:
            continue
        except Exception as e:
            # print(f"Worker Error {symbol}: {e}")
            pass

class ScannerEngine:
    def __init__(self, num_workers=4):
        self.num_workers = num_workers
        self.input_queue = multiprocessing.Queue()
        self.output_queue = multiprocessing.Queue()
        self.workers = []
        self.is_running = False
        
    def start(self, symbols):
        """Start the scanner with a list of symbols"""
        if self.is_running:
            return
            
        self.is_running = True
        
        # Populate Queue
        for s in symbols:
            self.input_queue.put(s)
            
        # Start Workers
        for _ in range(self.num_workers):
            p = multiprocessing.Process(target=_worker, args=(self.input_queue, self.output_queue))
            p.daemon = True
            p.start()
            self.workers.append(p)
            
    def stop(self):
        """Stop all workers"""
        self.is_running = False
        # Send stop signals
        for _ in range(len(self.workers)):
            self.input_queue.put("STOP")
            
        for p in self.workers:
            p.terminate()
            
        self.workers = []
        
    def get_results(self):
        """Yield results from queue without blocking"""
        results = []
        while True:
            try:
                # Get all available results
                res = self.output_queue.get_nowait()
                results.append(res)
            except queue.Empty:
                break
        return results
