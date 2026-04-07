@echo off
setlocal
set "ROOT=%~dp0..\.."

if /I "%~1"=="/?" goto :help
if /I "%~1"=="-h" goto :help
if /I "%~1"=="--help" goto :help

set "DESKTOP_SHORTCUT=%USERPROFILE%\Desktop\Grandpa Assistant.lnk"
set "STARTUP_SHORTCUT=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\Grandpa Assistant.lnk"
set "ICON_FILE=%ROOT%\frontend\assets\app-icon.ico"
set "APP_EXE="
for /f "usebackq delims=" %%V in (`powershell -NoProfile -Command "$pkg = Get-Content -Path '%ROOT%\frontend\package.json' -Raw | ConvertFrom-Json; $expected = Join-Path '%ROOT%\frontend\release' ('Grandpa Assistant ' + $pkg.version + '.exe'); if (Test-Path $expected) { Write-Output $expected } else { Get-ChildItem -Path '%ROOT%\frontend\release' -Filter 'Grandpa Assistant*.exe' | Sort-Object LastWriteTime -Descending | Select-Object -First 1 -ExpandProperty FullName }"`) do (
  set "APP_EXE=%%V"
)

if not defined APP_EXE (
  echo Portable app not found.
  echo Build it first with: build_react_desktop.cmd
  exit /b 1
)

call :create_shortcut "%DESKTOP_SHORTCUT%"
if errorlevel 1 exit /b 1

if /I "%~1"=="/startup-on" (
  call :create_shortcut "%STARTUP_SHORTCUT%"
  if errorlevel 1 exit /b 1
  echo Startup shortcut enabled.
  exit /b 0
)

if /I "%~1"=="/startup-off" (
  if exist "%STARTUP_SHORTCUT%" del "%STARTUP_SHORTCUT%"
  echo Startup shortcut disabled.
  exit /b 0
)

echo Desktop shortcut created.
echo Use /startup-on to add startup launch.
exit /b 0

:create_shortcut
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$shell = New-Object -ComObject WScript.Shell; " ^
  "$shortcut = $shell.CreateShortcut('%~1'); " ^
  "$shortcut.TargetPath = '%APP_EXE%'; " ^
  "$shortcut.WorkingDirectory = '%ROOT%\\frontend\\release'; " ^
  "$shortcut.IconLocation = '%ICON_FILE%'; " ^
  "$shortcut.Save()"
if errorlevel 1 (
  echo Could not create shortcut: %~1
  exit /b 1
)
exit /b 0

:help
echo Grandpa Assistant Portable Setup
echo.
echo Usage:
echo   setup_portable_desktop.cmd
echo   setup_portable_desktop.cmd /startup-on
echo   setup_portable_desktop.cmd /startup-off
echo.
echo What it does:
echo   - creates a Desktop shortcut for the built portable app
echo   - optionally adds or removes Startup launch
exit /b 0
