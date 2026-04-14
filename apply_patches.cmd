@echo off
setlocal

set "SCRIPT_DIR=%~dp0"

if "%~1"=="" (
    powershell -NoProfile -ExecutionPolicy Bypass -File "%SCRIPT_DIR%apply_patches.ps1"
) else (
    powershell -NoProfile -ExecutionPolicy Bypass -File "%SCRIPT_DIR%apply_patches.ps1" -Repo "%~1"
)

exit /b %ERRORLEVEL%
