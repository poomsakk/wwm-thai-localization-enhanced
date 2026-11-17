@echo off
chcp 65001 >nul
setlocal
REM Build the Thai mod from all translated chunks and install it into the game.
REM No AI is used here - this only runs local Python tools.
REM   build_mod.bat          build and copy into the game
REM   build_mod.bat nocopy   build only (e.g. before make_release while the player kit is installed)

cd /d "%~dp0"
set "GAME="
for /f "delims=" %%G in ('python -I "%~dp0tools\config.py" game') do set "GAME=%%G"
if not defined GAME (
    echo Game folder not found - run setup.bat first.
    pause
    exit /b 1
)
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
echo [1/4] Importing translations changed in git (pull / merged PR), then finished chunks...
python -I tools\export_translations.py sync || goto :err
python -I tools\normalize_queue.py || goto :err
python -I tools\translate.py import-queue || goto :err

echo.
echo [2/4] Exporting all finished translations...
python -I tools\translate.py export-tsv work\build_patch.tsv || goto :err
REM Keep the git copy of the translations (translations\*.tsv) up to date.
python -I tools\export_translations.py export || goto :err

echo.
echo [3/4] Building the game files from the original backup...
if not exist work\build mkdir work\build
REM Since the 2026-11 game update the Thai text is split over the main file and its _diff.
for %%F in (translate_words_map_th translate_words_map_th_diff) do (
    if exist "backup\original\Package\%%F" (
        python -I tools\wwmloc.py patch "backup\original\Package\%%F" work\build_patch.tsv "work\build\%%F" || goto :err
        python -I tools\wwmloc.py verify "work\build\%%F" || goto :err
    )
)
REM Standalone (the game's own launcher) keeps its _diff in LocalData\Patch: build that variant too.
if exist "backup\original\LocalData\translate_words_map_th_diff" (
    python -I tools\wwmloc.py patch "backup\original\LocalData\translate_words_map_th_diff" work\build_patch.tsv "work\build\sa_translate_words_map_th_diff" || goto :err
    python -I tools\wwmloc.py verify "work\build\sa_translate_words_map_th_diff" || goto :err
)

echo.
if /i "%~1"=="nocopy" (
    echo [4/4] Skipped installing into the game ^(nocopy^) - files are in work\build
    goto :status
)
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
