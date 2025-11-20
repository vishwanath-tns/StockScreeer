@echo off
echo Installing dependencies for Vedic Astrology Trading Dashboard...
echo.

echo Installing ReportLab for PDF generation...
pip install reportlab

echo.
echo Installing matplotlib for chart generation...
pip install matplotlib

echo.
echo Checking other dependencies...
pip install pandas numpy pytz

echo.
echo Installation complete!
echo.
echo You can now run:
echo   start_trading_dashboard.bat
echo.
echo Features available:
echo   - Trading reports and analysis
echo   - PDF report generation
echo   - Zodiac wheel charts
echo   - Moon position visualization
echo.
pause