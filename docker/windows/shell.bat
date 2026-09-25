@echo off
rem Double-click to run shell.ps1 (bypasses the PowerShell execution policy for this script only)
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0shell.ps1" %*
pause
