@echo off
setlocal

set "SCRIPT_DIR=%~dp0"
for %%I in ("%SCRIPT_DIR%..") do set "REPO_ROOT=%%~fI"

if not exist "%REPO_ROOT%\workspace\modules" mkdir "%REPO_ROOT%\workspace\modules"
if not exist "%USERPROFILE%\.apmatia" mkdir "%USERPROFILE%\.apmatia"
if not exist "%USERPROFILE%\.config\apmatia" mkdir "%USERPROFILE%\.config\apmatia"
if not exist "%USERPROFILE%\.local\share\apmatia" mkdir "%USERPROFILE%\.local\share\apmatia"

pushd "%REPO_ROOT%"
docker compose up --build
set "EXIT_CODE=%ERRORLEVEL%"
popd

exit /b %EXIT_CODE%
