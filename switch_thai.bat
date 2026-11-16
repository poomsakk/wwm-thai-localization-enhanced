@echo off
chcp 65001 >nul
setlocal
REM Switch the Thai text of Where Winds Meet between the original and our translation.
REM Close the game before switching (the game reads the file when it starts).

set "GAME=D:\steam\steamapps\common\Where Winds Meet"
set "TARGET=%GAME%\Package\HD\oversea\locale\translate_words_map_th"
set "ORIG=%~dp0backup\original\Package\translate_words_map_th"
set "MOD=%~dp0work\build\translate_words_map_th"
REM since the 2026-11 game update the text is also in the _diff file next to it
set "TARGET_D=%TARGET%_diff"
set "ORIG_D=%ORIG%_diff"
set "MOD_D=%MOD%_diff"

tasklist /FI "IMAGENAME eq wwm.exe" 2>nul | find /I "wwm.exe" >nul && (
    echo The game is running - close it first.
    pause
    exit /b 1
)

REM Never copy files from an older game version over a newer one.
python -I "%~dp0tools\update_game.py" check >nul
if errorlevel 1 (
    python -I "%~dp0tools\update_game.py" check
    echo.
    echo The game was updated and backup\original is from the OLD version.
    echo Switching now would break the game text. Run update_game.bat, then build_mod.bat first.
    pause
    exit /b 1
)

REM Detect the current version by file size (instant; the two files differ in size).
for %%A in ("%TARGET%") do set "SZ_T=%%~zA"
for %%A in ("%MOD%") do set "SZ_M=%%~zA"
for %%A in ("%ORIG%") do set "SZ_O=%%~zA"
set "NOW=unknown (game update?)"
if "%SZ_T%"=="%SZ_M%" set "NOW=MOD (our translation)"
if "%SZ_T%"=="%SZ_O%" set "NOW=ORIGINAL (official Thai)"

echo.
echo   Current Thai text: %NOW%
echo.
echo   [1] MOD - our translation
echo   [2] ORIGINAL - official Thai
echo   [Q] Quit
echo.
choice /C 12Q /N /M "Choose: "
if errorlevel 3 exit /b 0
if errorlevel 2 (copy /Y "%ORIG%" "%TARGET%" >nul & if exist "%ORIG_D%" copy /Y "%ORIG_D%" "%TARGET_D%" >nul) & echo Switched to ORIGINAL. & goto :done
if errorlevel 1 (copy /Y "%MOD%" "%TARGET%" >nul & if exist "%MOD_D%" copy /Y "%MOD_D%" "%TARGET_D%" >nul) & echo Switched to MOD. & goto :done
:done
echo Start the game to see the change.
pause
