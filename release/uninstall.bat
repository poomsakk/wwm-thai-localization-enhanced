@echo off
rem ================================================================
rem  WWM Thai mod - uninstall
rem  Puts the game's original Thai language files back from the backup.
rem  All logic is in wwm-thai.ps1 (plain text - open it in Notepad).
rem ================================================================
chcp 65001 >nul
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0wwm-thai.ps1" -Mode uninstall
echo.
pause
