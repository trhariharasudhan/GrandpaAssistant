@echo off
setlocal
set "ROOT=%~dp0..\.."
call "%ROOT%\scripts\windows\check_assistant_health.cmd"
if errorlevel 1 exit /b 1
cd /d "%ROOT%\frontend"
call npm install
if errorlevel 1 exit /b 1
call npm run icons:generate
if errorlevel 1 exit /b 1
call npm run desktop:build
if errorlevel 1 exit /b 1
echo.
echo Desktop build complete.
for %%F in ("%ROOT%\frontend\release\Grandpa Assistant*.exe") do (
  echo Portable artifact: %%~fF
  goto :done
)
:done
endlocal
