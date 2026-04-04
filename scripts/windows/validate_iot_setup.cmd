@echo off
setlocal

set "ROOT=%~dp0..\.."
powershell -NoProfile -ExecutionPolicy Bypass -File "%ROOT%\scripts\windows\validate_iot_setup.ps1"

endlocal
