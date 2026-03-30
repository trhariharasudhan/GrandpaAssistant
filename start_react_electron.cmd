@echo off
cd /d "%~dp0frontend"
start "Grandpa Assistant React UI" cmd /k "cd /d %~dp0frontend && npm run dev"
timeout /t 4 /nobreak >nul
start "Grandpa Assistant Desktop" cmd /k "cd /d %~dp0frontend && npm run electron:dev"
