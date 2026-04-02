@echo off
set "ROOT=%~dp0..\.."
cd /d "%ROOT%\frontend"
start "Grandpa Assistant React UI" cmd /k "cd /d %ROOT%\frontend && npm run dev"
timeout /t 4 /nobreak >nul
start "" http://127.0.0.1:4173
