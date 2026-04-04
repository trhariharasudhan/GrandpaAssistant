@echo off
setlocal

set "ROOT=%~dp0..\.."

if /I "%~1"=="/build" (
  powershell -NoProfile -ExecutionPolicy Bypass -File "%ROOT%\scripts\windows\final_release_check.ps1" -BuildDesktop
) else (
  powershell -NoProfile -ExecutionPolicy Bypass -File "%ROOT%\scripts\windows\final_release_check.ps1"
)

endlocal
