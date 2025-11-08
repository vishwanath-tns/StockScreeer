"""Plotting helpers using Plotly for interactive charts."""
from __future__ import annotations

import pandas as pd
import plotly.graph_objs as go
from plotly.subplots import make_subplots


def make_price_volume_rsi_figure(
    ohlcv_df: pd.DataFrame,
    rsi_ser: pd.Series | None = None,
    fractal_high: float | None = None,
    fractal_low: float | None = None,
    fractal_date: str | None = None,
    compact: bool = True,
    rsi_period: int | None = None,
) -> go.Figure:
    """Return a Plotly Figure with price, volume and RSI subplots.

    If compact=True the x-axis will hide weekend gaps using Plotly rangebreaks so
    points remain spaced by real time while weekends are not shown.
    """
    fig = make_subplots(rows=3, cols=1, shared_xaxes=True, row_heights=[0.6, 0.2, 0.2])

    if ohlcv_df is None or ohlcv_df.empty:
        fig.add_annotation(text="No data", xref="paper", yref="paper", showarrow=False)
        return fig

    # Ensure index is datetimelike; accept strings or timestamps
    try:
        ohlcv_df = ohlcv_df.copy()
        ohlcv_df.index = pd.to_datetime(ohlcv_df.index, errors='coerce')
    except Exception:
        pass

    # Use actual datetimes for x; we'll apply rangebreaks to hide weekends when compact=True
    x = ohlcv_df.index

    # Price trace (lines+markers)
    if 'close' not in ohlcv_df.columns:
        raise ValueError("ohlcv_df must contain a 'close' column")
    fig.add_trace(
        go.Scatter(x=x, y=ohlcv_df['close'].values, mode='lines+markers', name='Close', line=dict(color='royalblue')),
        row=1, col=1,
    )

    # Volume (if present)
    vol_col = None
    for c in ('volume', 'Volume', 'ttl_trd_qnty'):
        if c in ohlcv_df.columns:
            vol_col = c
            break
    if vol_col is not None:
        fig.add_trace(go.Bar(x=x, y=ohlcv_df[vol_col].values, name='Volume', marker_color='#5f6a72', opacity=0.95), row=2, col=1)

    # RSI
    if rsi_ser is not None and not rsi_ser.empty:
        # ensure rsi index is datetime-like
        try:
            rsi_ser = rsi_ser.copy()
            rsi_ser.index = pd.to_datetime(rsi_ser.index, errors='coerce')
        except Exception:
            pass
        rx = rsi_ser.index
        fig.add_trace(go.Scatter(x=rx, y=rsi_ser.values, name='RSI', line=dict(color='orange')),
                      row=3, col=1)
        # add 70/30 lines
        fig.add_hline(y=70, line=dict(color='red', dash='dash'), row=3, col=1)
        fig.add_hline(y=30, line=dict(color='green', dash='dash'), row=3, col=1)

        # ensure RSI axis uses 0-100 range for visibility
        fig.update_yaxes(range=[0, 100], row=3, col=1)

    # Fractal level lines
    if fractal_high is not None:
        fig.add_hline(y=fractal_high, line=dict(color='green', dash='dot'), row=1, col=1)
    if fractal_low is not None:
        fig.add_hline(y=fractal_low, line=dict(color='red', dash='dot'), row=1, col=1)

    # Fractal date vertical line
    if fractal_date is not None:
        try:
            # expect fractal_date as YYYY-MM-DD or a parseable string
            xval = pd.to_datetime(fractal_date)
            fig.add_vline(x=xval, line=dict(color='magenta', dash='dash'))
        except Exception:
            pass

    # Apply axis formatting and optional weekend exclusion when compact=True
    fig.update_layout(height=800, template='plotly_white', margin=dict(l=40, r=20, t=60, b=80))
    # show border around price and volume subplots
    fig.update_xaxes(showline=True, linewidth=1, linecolor='black', row=1, col=1)
    fig.update_yaxes(showline=True, linewidth=1, linecolor='black', row=1, col=1)
    fig.update_xaxes(showline=True, linewidth=1, linecolor='black', row=2, col=1)
    fig.update_yaxes(showline=True, linewidth=1, linecolor='black', row=2, col=1)

    if compact:
        # remove weekend gaps and format ticks
        for row, col in ((1, 1), (2, 1), (3, 1)):
            fig.update_xaxes(rangebreaks=[dict(bounds=["sat", "mon"])], row=row, col=col)
            fig.update_xaxes(tickformat='%Y-%m-%d', tickangle=-45, row=row, col=col)

    # annotate RSI period/settings if provided
    if rsi_period is not None:
        fig.add_annotation(text=f"RSI period: {rsi_period}", xref='paper', yref='paper', x=0.99, y=0.02,
                           showarrow=False, font=dict(size=10), align='right')

    return fig
