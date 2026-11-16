@echo off
chcp 65001 >nul
cd /d "%~dp0"
python -I tools\progress.py
echo.
pause
