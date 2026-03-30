@echo off
cd /d "%~dp0"
start "Grandpa Assistant Backend" cmd /k "cd /d %~dp0 && .venv\Scripts\python.exe main.py"
call "%~dp0start_react_frontend.cmd"
