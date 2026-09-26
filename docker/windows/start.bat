@echo off
rem Double-click to run start.ps1 (bypasses the PowerShell execution policy for this script only)
rem Options can be passed through, e.g.:  start.bat -Gpu   /   start.bat -Display vcxsrv
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0start.ps1" %*
pause
