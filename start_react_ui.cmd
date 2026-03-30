@echo off
cd /d "%~dp0"
start "Grandpa Assistant Backend" cmd /k "cd /d %~dp0 && .venv\Scripts\python.exe main.py"
start "Grandpa Assistant React UI" cmd /k "cd /d %~dp0frontend && npm run dev"
