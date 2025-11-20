@echo off
REM Vedic Astrology Trading Reports Generator (Windows Batch)
REM Run this script to generate all trading reports at once

echo 🚀 GENERATING VEDIC ASTROLOGY TRADING REPORTS
echo ==============================================

REM Change to the trading tools directory
cd /d "D:\MyProjects\StockScreeer\vedic_astrology\trading_tools"

echo 📊 Generating market forecast...
python market_forecast.py

echo.
echo 📈 Generating trading strategies...
python trading_strategy.py

echo.
echo 📅 Generating weekly outlook...
python weekly_outlook.py

echo.
echo 📋 Displaying dashboard...
cd "..\reports"
python trading_dashboard.py

echo.
echo ✅ ALL REPORTS GENERATED SUCCESSFULLY!
echo 📁 Reports saved in: vedic_astrology/reports/
echo 🔄 Run this script daily for updated analysis

pause