@echo off
setlocal
set "ROOT=%~dp0..\.."
powershell -NoProfile -ExecutionPolicy Bypass -File "%ROOT%\scripts\windows\build_standalone_app.ps1" %*
endlocal
