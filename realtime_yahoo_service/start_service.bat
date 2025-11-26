@echo off
echo ========================================
echo Real-Time Yahoo Finance Service
echo ========================================
echo.

cd /d "%~dp0"
python main.py --config config\local_test.yaml

pause
