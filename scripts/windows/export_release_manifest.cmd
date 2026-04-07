@echo off
setlocal

set "ROOT=%~dp0..\.."
powershell -NoProfile -ExecutionPolicy Bypass -File "%ROOT%\scripts\windows\export_release_manifest.ps1"

endlocal
