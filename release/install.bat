@echo off
rem ================================================================
rem  WWM Thai mod - install
rem  Checks the game version, backs up the 2 Thai language files,
rem  then installs the mod's Thai files. Changes nothing else.
rem  All logic is in wwm-thai.ps1 (plain text - open it in Notepad).
rem ================================================================
chcp 65001 >nul
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0wwm-thai.ps1" -Mode install
echo.
pause
