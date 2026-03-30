@echo off
cd /d "%~dp0"
start "Grandpa Assistant Backend" cmd /k "cd /d %~dp0 && .venv\Scripts\python.exe main.py"
start "Grandpa Assistant Frontend Dev Server" cmd /k "cd /d %~dp0frontend && npm run dev"
timeout /t 4 /nobreak >nul
start "Grandpa Assistant Desktop" cmd /k "cd /d %~dp0frontend && npm run electron:dev"
