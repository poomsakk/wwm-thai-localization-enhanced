@echo off
chcp 65001 >nul
REM Restore the game's original Thai locale files from backup\original
set "GAME="
for /f "delims=" %%G in ('python -I "%~dp0tools\config.py" game') do set "GAME=%%G"
if not defined GAME (
    echo Game folder not found - run setup.bat first.
    pause
    exit /b 1
)
set "BK=%~dp0backup\original"

copy /Y "%BK%\Package\translate_words_map_th" "%GAME%\Package\HD\oversea\locale\translate_words_map_th" || goto :err
if exist "%BK%\Package\translate_words_map_th_diff" copy /Y "%BK%\Package\translate_words_map_th_diff" "%GAME%\Package\HD\oversea\locale\translate_words_map_th_diff" || goto :err
copy /Y "%BK%\LocalData\translate_words_map_th_diff" "%GAME%\LocalData\Patch\HD\oversea\locale\translate_words_map_th_diff" || goto :err
echo.
echo Restored original Thai files.
pause
exit /b 0
:err
echo.
echo FAILED - is the game still running?
pause
exit /b 1
