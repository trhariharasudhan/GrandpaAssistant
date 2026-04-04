@echo off
setlocal

set "ROOT=%~dp0..\.."
set "PYTHON_EXE=%ROOT%\.python311\python.exe"
if not exist "%PYTHON_EXE%" set "PYTHON_EXE=%ROOT%\.venv\Scripts\python.exe"
if not exist "%PYTHON_EXE%" set "PYTHON_EXE=python"

powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "Start-Process -Verb RunAs -FilePath '%PYTHON_EXE%' -ArgumentList '\"%ROOT%\backend\main.py\" --text' -WorkingDirectory '%ROOT%'"

if errorlevel 1 (
  echo Could not request administrator launch.
  pause
)

endlocal
