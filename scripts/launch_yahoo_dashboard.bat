@echo off
REM Yahoo Finance Dashboard Launcher
REM Quick launch script for the Yahoo Finance Features Dashboard

echo ====================================
echo   Yahoo Finance Dashboard Launcher
echo ====================================
echo.
echo Starting dashboard...
echo.

python yahoo_finance_dashboard.py

if errorlevel 1 (
    echo.
    echo ERROR: Failed to launch dashboard
    echo.
    echo Possible issues:
    echo 1. Python not installed or not in PATH
    echo 2. Required packages not installed
    echo.
    echo To fix:
    echo   pip install -r requirements.txt
    echo.
    pause
    exit /b 1
)
