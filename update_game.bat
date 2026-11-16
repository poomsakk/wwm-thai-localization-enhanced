@echo off
chcp 65001 >nul
setlocal
REM Run this after a game update, BEFORE build_mod.bat.
REM It backs up the new official Thai files and updates work\wwm.db without losing translations:
REM keys whose Chinese text was already translated keep their Thai; only new texts become "todo".
REM No AI is used here.

cd /d "%~dp0"
tasklist /FI "IMAGENAME eq wwm.exe" 2>nul | find /I "wwm.exe" >nul && (
    echo The game is running - close it first.
    pause
    exit /b 1
)

python -I tools\update_game.py check
if not errorlevel 1 (
    echo.
    pause
    exit /b 0
)

echo.
echo === Preview (nothing is changed yet) ===
python -I tools\update_game.py apply --dry-run || goto :err
echo.
choice /C YN /M "Apply this update to the backup and the database"
if errorlevel 2 exit /b 0

python -I tools\update_game.py apply || goto :err
echo.
echo Now run build_mod.bat to install the mod on the new game version.
pause
exit /b 0

:err
echo.
echo FAILED - see the message above. Nothing was replaced if it failed before "DB updated".
pause
exit /b 1
