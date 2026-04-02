@echo off
set "ROOT=%~dp0..\.."
cd /d "%ROOT%"
start "Grandpa Assistant Backend" cmd /k "cd /d %ROOT% && .venv\Scripts\python.exe backend\main.py"
call "%~dp0start_react_electron.cmd"
