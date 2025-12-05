import sys
import os
import argparse
import pandas as pd
import numpy as np
from PyQt5 import QtWidgets, QtCore, QtGui
import pyqtgraph as pg

# Adjust path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from mean_reversion.data_access.data_loader import DatabaseLoader
from mean_reversion.core.strategies import StrategyRegistry

class CandlestickItem(pg.GraphicsObject):
    def __init__(self, data):
        pg.GraphicsObject.__init__(self)
        self.data = data  # data must have fields: time, open, close, min, max
        self.generatePicture()

    def generatePicture(self):
        self.picture = QtGui.QPicture()
        p = QtGui.QPainter(self.picture)
        p.setPen(pg.mkPen('w'))
        w = 0.4 # width of the bar (1.0 is full width)
        
        for (t, open, close, min, max) in self.data:
            p.drawLine(QtCore.QPointF(t, min), QtCore.QPointF(t, max))
            if open > close:
                p.setBrush(pg.mkBrush('r'))
            else:
                p.setBrush(pg.mkBrush('g'))
            p.drawRect(QtCore.QRectF(t-w, open, w*2, close-open))
        p.end()

    def paint(self, p, *args):
        p.drawPicture(0, 0, self.picture)

    def boundingRect(self):
        return QtCore.QRectF(self.picture.boundingRect())

class ChartViewer(QtWidgets.QWidget):
    def __init__(self, symbol, strategy_name='both'):
        super().__init__()
        self.symbol = symbol
        self.strategy_name = strategy_name
        self.initUI()
        self.loadData()

    def initUI(self):
        self.setWindowTitle(f"Chart Viewer: {self.symbol}")
        self.resize(1200, 800)
        
        layout = QtWidgets.QVBoxLayout()
        self.setLayout(layout)
        
        # Graphics Layout
        self.win = pg.GraphicsLayoutWidget()
        layout.addWidget(self.win)
        
        # Main Plot (Price)
        self.p1 = self.win.addPlot(row=0, col=0)
        self.p1.setLabel('left', 'Price')
        self.p1.showGrid(x=True, y=True)
        self.p1.setMouseEnabled(x=True, y=True)
        self.p1.setTitle(f"{self.symbol} - Price History")
        
        # RSI Plot
        self.p2 = self.win.addPlot(row=1, col=0)
        self.p2.setLabel('left', 'RSI')
        # User requested 0-100 to cover 40% of area.
        # Range = 100 / 0.4 = 250.
        # Center at 50 -> -75 to 175.
        self.p2.setYRange(-75, 175, padding=0)
        self.p2.setXLink(self.p1)
        self.p2.showGrid(x=True, y=True)
        
        # Set Row Stretch (65% Price, 35% RSI)
        self.win.ci.layout.setRowStretchFactor(0, 65)
        self.win.ci.layout.setRowStretchFactor(1, 35)
        
        # Add Lines to RSI
        self.p2.addLine(y=30, pen=pg.mkPen('g', style=QtCore.Qt.DashLine))
        self.p2.addLine(y=70, pen=pg.mkPen('r', style=QtCore.Qt.DashLine))
        self.p2.addLine(y=10, pen=pg.mkPen('g', width=2))
        self.p2.addLine(y=90, pen=pg.mkPen('r', width=2))

    def loadData(self):
        db = DatabaseLoader()
        df = db.fetch_data(self.symbol, days=365)
        
        if df.empty:
            print(f"No data for {self.symbol}")
            return
            
        data = []
        # Prepare data for Candlesticks
        # x axis needs index
        df = df.reset_index()
        dates_dict = {}
        
        for i, row in df.iterrows():
            data.append((i, row['open'], row['close'], row['low'], row['high']))
            dates_dict[i] = row['date'].strftime('%Y-%m-%d')
            
        candlestick = CandlestickItem(data)
        self.p1.addItem(candlestick)
        
        # Set x-axis tick formatter
        axis = self.p1.getAxis('bottom')
        axis.setTicks([
            [(i, dates_dict[i]) for i in range(0, len(df), 20)] 
        ])
        
        # Plot Indicators
        # Bollinger Bands
        sma20 = df['close'].rolling(20).mean()
        std20 = df['close'].rolling(20).std()
        upper_bb = sma20 + (2 * std20)
        lower_bb = sma20 - (2 * std20)
        
        self.p1.plot(sma20, pen=pg.mkPen('orange', width=1), name='SMA20')
        self.p1.plot(upper_bb, pen=pg.mkPen('gray', width=1), name='Upper BB')
        self.p1.plot(lower_bb, pen=pg.mkPen('blue', width=1), name='Lower BB')
        
        # Signals (Highlighting from strategy re-run)
        # We need to re-run strategy logic on each point to place arrows
        # Simplified: Loop through and check conditions
        
        brush_up = pg.mkBrush('g')
        brush_down = pg.mkBrush('r')
        
        spots = [] # Points for scatter plot
        
        # Calculate RSI
        rsi = StrategyRegistry.calculate_rsi(df['close'], 2)
        self.p2.plot(rsi, pen=pg.mkPen('m', width=1))
        
        for i in range(20, len(df)):
            close_price = df.iloc[i]['close']
            
            # Simple Signal Logic Visualizer (Replicating Strategy)
            
            # RSI Signals
            r = rsi.iloc[i]
            if r < 10:
                # Buy
                spots.append({'pos': (i, df.iloc[i]['low']), 'data': 1, 'brush': brush_up, 'symbol': 't1', 'size': 10})
            elif r > 90:
                # Sell
                spots.append({'pos': (i, df.iloc[i]['high']), 'data': 1, 'brush': brush_down, 'symbol': 't', 'size': 10})
                
            # BB Signals
            l_bb = lower_bb.iloc[i]
            u_bb = upper_bb.iloc[i]
            sma = sma20.iloc[i]
            
            if close_price < l_bb:
                 spots.append({'pos': (i, df.iloc[i]['low'] * 0.99), 'data': 1, 'brush': brush_up, 'symbol': 't1', 'size': 15})
            
            if close_price > sma:
                 # Only mark exit if we were low? Too complex for visualizer, just mark "exit zone"
                 spots.append({'pos': (i, df.iloc[i]['high'] * 1.01), 'data': 1, 'brush': pg.mkBrush('y'), 'symbol': 'o', 'size': 5})

        scatter = pg.ScatterPlotItem(spots=spots)
        self.p1.addItem(scatter)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--symbol', required=True)
    parser.add_argument('--strategy', default='both')
    args = parser.parse_args()
    
    app = QtWidgets.QApplication(sys.argv)
    viewer = ChartViewer(args.symbol, args.strategy)
    viewer.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()
