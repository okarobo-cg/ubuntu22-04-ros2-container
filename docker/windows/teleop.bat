@echo off
rem Double-click to run teleop.ps1 (bypasses the PowerShell execution policy for this script only)
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0teleop.ps1" %*
pause
