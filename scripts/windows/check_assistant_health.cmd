@echo off
setlocal

set "ROOT=%~dp0..\.."
powershell -NoProfile -ExecutionPolicy Bypass -File "%ROOT%\scripts\windows\check_assistant_health.ps1"

endlocal
