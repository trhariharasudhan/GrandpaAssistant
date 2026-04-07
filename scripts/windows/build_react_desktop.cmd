@echo off
setlocal
set "ROOT=%~dp0..\.."
call "%ROOT%\scripts\windows\build_backend_exe.cmd"
if errorlevel 1 exit /b 1
call "%ROOT%\scripts\windows\check_assistant_health.cmd"
if errorlevel 1 exit /b 1
cd /d "%ROOT%\frontend"
if not exist "node_modules" (
  echo Frontend dependencies are missing. Installing them now...
  cmd /c npm install
  if errorlevel 1 exit /b 1
)
cmd /c npm run desktop:build
if errorlevel 1 exit /b 1
echo.
echo Desktop build complete.
for /f "usebackq delims=" %%V in (`powershell -NoProfile -Command "$pkg = Get-Content -Path '%ROOT%\frontend\package.json' -Raw | ConvertFrom-Json; $expected = Join-Path '%ROOT%\frontend\release' ('Grandpa Assistant ' + $pkg.version + '.exe'); if (Test-Path $expected) { Write-Output $expected } else { Get-ChildItem -Path '%ROOT%\frontend\release' -Filter 'Grandpa Assistant*.exe' | Sort-Object LastWriteTime -Descending | Select-Object -First 1 -ExpandProperty FullName }"`) do (
  echo Portable artifact: %%V
)
for /f "usebackq delims=" %%V in (`powershell -NoProfile -Command "Get-ChildItem -Path '%ROOT%\frontend\release' -Filter '*Setup*.exe' | Sort-Object LastWriteTime -Descending | Select-Object -First 1 -ExpandProperty FullName"`) do (
  echo Installer artifact: %%V
)
endlocal
