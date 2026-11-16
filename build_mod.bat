@echo off
chcp 65001 >nul
setlocal
REM Build the Thai mod from all translated chunks and install it into the game.
REM No AI is used here - this only runs local Python tools.

cd /d "%~dp0"
set "GAME=D:\steam\steamapps\common\Where Winds Meet"
set "LOC=%GAME%\Package\HD\oversea\locale"

echo [0/4] Checking for a game update...
python -I tools\update_game.py check
if errorlevel 1 (
    echo.
    echo The game was updated. Run update_game.bat first, then run build_mod.bat again.
    pause
    exit /b 1
)

echo.
echo [1/4] Importing finished chunk translations (work\queue\NNNN.out.tsv)...
python -I tools\normalize_queue.py || goto :err
python -I tools\translate.py import-queue || goto :err

echo.
echo [2/4] Exporting all finished translations...
python -I tools\translate.py export-tsv work\build_patch.tsv || goto :err
REM Keep the git copy of the translations (translations\*.tsv) up to date.
python -I tools\export_translations.py export || goto :err

echo.
echo [3/4] Building the game files from the original backup...
REM Since the 2026-11 game update the Thai text is split over the main file and its _diff.
for %%F in (translate_words_map_th translate_words_map_th_diff) do (
    if exist "backup\original\Package\%%F" (
        python -I tools\wwmloc.py patch "backup\original\Package\%%F" work\build_patch.tsv "work\build\%%F" || goto :err
        python -I tools\wwmloc.py verify "work\build\%%F" || goto :err
    )
)

echo.
echo [4/4] Installing into the game...
tasklist /FI "IMAGENAME eq wwm.exe" 2>nul | find /I "wwm.exe" >nul && (
    echo The game is running - close it, then run switch_thai.bat and choose [1] MOD.
    goto :status
)
for %%F in (translate_words_map_th translate_words_map_th_diff) do (
    if exist "backup\original\Package\%%F" copy /Y "work\build\%%F" "%LOC%\%%F" >nul || goto :err
)
echo Installed. Start the game to see it.

:status
echo.
python -I tools\translate.py queue-status
echo.
pause
exit /b 0

:err
echo.
echo FAILED - see the message above.
pause
exit /b 1
