@echo off
set "ROOT=%~dp0..\.."
cd /d "%ROOT%"
start "Grandpa Assistant Backend" cmd /k "cd /d %ROOT% && .venv\Scripts\python.exe backend\main.py"
start "Grandpa Assistant React UI" cmd /k "cd /d %ROOT%\frontend && npm run dev"
