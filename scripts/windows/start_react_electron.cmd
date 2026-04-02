@echo off
set "ROOT=%~dp0..\.."
cd /d "%ROOT%\frontend"
start "Grandpa Assistant React UI" cmd /k "cd /d %ROOT%\frontend && npm run dev"
timeout /t 4 /nobreak >nul
start "Grandpa Assistant Desktop" cmd /k "cd /d %ROOT%\frontend && npm run electron:dev"
