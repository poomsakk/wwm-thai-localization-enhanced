@echo off
rem ================================================================
rem  WWM Thai mod - start the game with the Thai mod checked first
rem
rem  Steam : Steam > right-click the game > Properties > General > Launch Options:
rem              "<folder of this file>\play.bat" %command%
rem          Steam then runs this file with the game command (%*).
rem  The game's own launcher : open the game with the desktop shortcut
rem          "Where Winds Meet (Thai)" made by install.bat (runs this file with
rem          --game "<game folder>", so Steam + launcher installs on one PC both work).
rem
rem  1) wwm-thai.ps1 checks the Thai files: reinstalls them if they were
rem     overwritten, and checks GitHub for a newer mod version.
rem  2) The game starts - with exactly the command Steam gave (%*), or through
rem     Steam / the game's launcher when started from the shortcut.
rem  If step 1 fails for any reason, the game still starts normally.
rem  All logic is in wwm-thai.ps1 (plain text - open it in Notepad).
rem ================================================================
setlocal
chcp 65001 >nul
if "%~1"=="" (
    powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0wwm-thai.ps1" -Mode play
    exit /b
)
if /i "%~1"=="--game" (
    powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0wwm-thai.ps1" -Mode play -Game "%~2"
    exit /b
)
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0wwm-thai.ps1" -Mode play -GameExe "%~1"
%*
