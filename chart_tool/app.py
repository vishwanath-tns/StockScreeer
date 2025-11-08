"""Minimal Dash app to demo charting using scanner data."""
from __future__ import annotations

import os
from datetime import datetime

from dash import Dash, dcc, html, Input, Output, State
import pandas as pd

from services_client import get_ohlcv, get_rsi
from plotting import make_price_volume_rsi_figure

app = Dash(__name__)
app.layout = html.Div([
    html.H2("Chart Tool (Demo)"),
    html.Div([
        html.Label("Symbol:"),
        dcc.Input(id='symbol-input', value='SBIN', type='text'),
        html.Label("Start:"),
        dcc.DatePickerRange(id='date-range', start_date=None, end_date=None),
        html.Button('Plot', id='plot-btn')
    ], style={'display':'flex', 'gap':'8px', 'alignItems':'center'}),
    dcc.Loading(dcc.Graph(id='chart'), type='default'),
    html.Div(id='err', style={'color':'red'})
])


@app.callback(
    Output('chart', 'figure'),
    Output('err', 'children'),
    Input('plot-btn', 'n_clicks'),
    State('symbol-input', 'value'),
    State('date-range', 'start_date'),
    State('date-range', 'end_date'),
)
def update_chart(n_clicks, symbol, start_date, end_date):
    if not n_clicks:
        return {}, ''
    if not symbol:
        return {}, 'Please enter a symbol'
    try:
        # days is optional; when start/end provided, callers can handle them
        ohlcv = get_ohlcv(symbol)
        rsi_period = 14
        rsi = get_rsi(symbol, period=rsi_period)
        fig = make_price_volume_rsi_figure(ohlcv, rsi, compact=True, rsi_period=rsi_period)
        return fig, ''
    except Exception as e:
        return {}, str(e)


if __name__ == '__main__':
    # helpful PYTHONPATH hint when running locally
    if os.getenv('PYTHONPATH') is None:
        print('Ensure the scanner repo root is on PYTHONPATH if direct imports are used.')
    # dash v2+: use app.run instead of app.run_server
    try:
        app.run(debug=True, host='127.0.0.1', port=8050)
    except Exception:
        # fallback to older API name if present
        try:
            app.run_server(debug=True)
        except Exception as e:
            print('Failed to start Dash app:', e)
