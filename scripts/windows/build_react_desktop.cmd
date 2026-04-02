@echo off
setlocal
set "ROOT=%~dp0..\.."
cd /d "%ROOT%\frontend"
call npm install
if errorlevel 1 exit /b 1
call npm run icons:generate
if errorlevel 1 exit /b 1
call npm run desktop:build
endlocal
