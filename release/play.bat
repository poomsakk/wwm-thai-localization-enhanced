@echo off
rem ================================================================
rem  WWM Thai mod - Steam launcher
rem  Steam > right-click the game > Properties > General > Launch Options:
rem      "<folder of this file>\play.bat" %command%
rem
rem  1) wwm-thai.ps1 checks the Thai files: reinstalls them if Steam
rem     overwrote them, and checks GitHub for a newer mod version.
rem  2) Then the game starts with exactly the command Steam gave (%*).
rem  If step 1 fails for any reason, the game still starts normally.
rem  All logic is in wwm-thai.ps1 (plain text - open it in Notepad).
rem ================================================================
setlocal
if "%~1"=="" (
    echo This file is started by Steam. Put this line in Steam Launch Options:
    echo     "%~f0" %%command%%
    pause
    exit /b 1
)
chcp 65001 >nul
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0wwm-thai.ps1" -Mode play -GameExe "%~1"
%*
