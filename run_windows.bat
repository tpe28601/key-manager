@echo off
setlocal
cd /d "%~dp0"
set "TB_ACTIVE_TOOL="
for /f "delims=" %%I in ('powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0Standalone-Update.ps1" -Action Resolve') do set "TB_ACTIVE_TOOL=%%I"
if defined TB_ACTIVE_TOOL (
    if not defined TB_KEY_MANAGER_VENV if exist "%~dp0.venv\Scripts\python.exe" set "TB_KEY_MANAGER_VENV=%~dp0.venv"
    call "%TB_ACTIVE_TOOL%\run_windows.bat" %*
    exit /b
)

set "TB_PYTHON="
for /f "delims=" %%I in ('powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0Standalone-Update.ps1" -Action Python') do set "TB_PYTHON=%%I"
if not defined TB_PYTHON (
    echo Key Manager requires compatible Python 3.11+ with pywebview, cryptography and bcrypt.
    echo Download the full package or install the missing requirements.
    pause
    exit /b 5
)
set "PYTHONPATH=%~dp0src;%~dp0runtime-deps"
"%TB_PYTHON%" -m key_manager.main
set "TB_RESULT=%ERRORLEVEL%"
if not "%TB_RESULT%"=="0" pause
exit /b %TB_RESULT%
