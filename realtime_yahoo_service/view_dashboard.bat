@echo off
echo ========================================
echo Opening Service Dashboard...
echo ========================================
echo.

cd /d "%~dp0"
start dashboard.html

echo.
echo Dashboard opened in your default browser!
echo.
echo If the service is running, you should see:
echo   - Green "ONLINE" status
echo   - Live market data streaming
echo   - Real-time metrics updating
echo.
echo If you see "OFFLINE":
echo   - Make sure to start the service first
echo   - Run: start_service.bat
echo.
pause
