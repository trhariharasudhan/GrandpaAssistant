@echo off
setlocal

set "ROOT=%~dp0..\.."
set "PYTHON_EXE=%ROOT%\.python311\python.exe"
if not exist "%PYTHON_EXE%" set "PYTHON_EXE=%ROOT%\.venv\Scripts\python.exe"
if not exist "%PYTHON_EXE%" set "PYTHON_EXE=python"

cd /d "%ROOT%"
echo Starting Grandpa Assistant in text console mode...
"%PYTHON_EXE%" -u "%ROOT%\main.py" --text

if errorlevel 1 (
  echo.
  echo Startup failed. Check backend\logs\main_startup_error.log
  pause
)

endlocal
