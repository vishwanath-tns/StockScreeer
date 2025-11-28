@echo off
REM Launch real-time candlestick viewer using mplfinance
cd /d "%~dp0"
python realtime_candlestick_viewer.py
pause
