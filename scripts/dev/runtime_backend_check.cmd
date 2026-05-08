@echo off
setlocal
cd /d "%~dp0..\.."

if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" "scripts\dev\runtime_backend_check.py"
) else (
    python "scripts\dev\runtime_backend_check.py"
)

set CHECK_EXIT=%ERRORLEVEL%
echo.
if "%CHECK_EXIT%"=="0" (
    echo Runtime backend check PASS.
) else (
    echo Runtime backend check FAIL.
)
echo.
pause
exit /b %CHECK_EXIT%
