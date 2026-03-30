@echo off
setlocal
cd /d "%~dp0frontend"
call npm install
if errorlevel 1 exit /b 1
call npm run desktop:build
endlocal
