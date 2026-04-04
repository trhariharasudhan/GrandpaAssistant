@echo off
setlocal

set "ROOT=%~dp0..\.."
powershell -NoProfile -ExecutionPolicy Bypass -File "%ROOT%\scripts\windows\watch_hardware_changes.ps1"

endlocal
