@echo off
rem Double-click to run check_env.ps1 (bypasses the PowerShell execution policy for this script only)
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0check_env.ps1" %*
pause
