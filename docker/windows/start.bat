@echo off
rem Double-click to run start.ps1 (bypasses the PowerShell execution policy for this script only)
rem Options can be passed through, e.g.:  start.bat -Launch diffbot   /   start.bat -Team blue -NoRviz
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0start.ps1" %*
pause
