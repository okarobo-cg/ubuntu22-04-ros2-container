@echo off
rem Double-click to run stop.ps1 (bypasses the PowerShell execution policy for this script only)
rem Options can be passed through, e.g.:  stop.bat -Remove
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0stop.ps1" %*
pause
