@echo off
chcp 65001 >nul
setlocal
REM One-time setup after `git clone` (or after reinstalling Windows / the game).
REM Needs: Python 3.10+ ("Add python.exe to PATH" ticked when installing) and the game installed.
cd /d "%~dp0"

python --version >nul 2>&1 || (
    echo Python was not found. Install Python 3.10 or newer from https://www.python.org/downloads/
    echo and tick "Add python.exe to PATH" in the installer, then run setup.bat again.
    pause
    exit /b 1
)

echo Installing Python packages (requirements.txt)...
python -m pip install --disable-pip-version-check -q -r requirements.txt || goto :err

python -I tools\setup_project.py || goto :err
echo.
pause
exit /b 0

:err
echo.
echo FAILED - see the message above.
pause
exit /b 1
