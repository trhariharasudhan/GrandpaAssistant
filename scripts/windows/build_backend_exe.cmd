@echo off
setlocal
set "ROOT=%~dp0..\.."
powershell -NoProfile -ExecutionPolicy Bypass -File "%ROOT%\scripts\windows\build_backend_exe.ps1" %*
endlocal
