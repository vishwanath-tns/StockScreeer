@echo off
echo 🌙 Starting Vedic Astrology Trading Dashboard...
echo.

REM Check if reportlab is installed
python -c "import reportlab" 2>nul
if errorlevel 1 (
    echo ⚠️ Installing PDF dependencies...
    pip install reportlab
)

echo Starting GUI...
cd /d "D:\MyProjects\StockScreeer\vedic_astrology\gui"
python vedic_trading_gui.py

if errorlevel 1 (
    echo.
    echo ❌ Error starting the dashboard.
    echo Please check that Python is installed and all dependencies are available.
    echo.
    echo To install dependencies, run: install_dependencies.bat
    pause
) else (
    echo.
    echo ✅ Dashboard closed successfully.
)