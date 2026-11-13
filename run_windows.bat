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

if not defined TB_KEY_MANAGER_VENV set "TB_KEY_MANAGER_VENV=%~dp0.venv"
if exist "%TB_KEY_MANAGER_VENV%\Scripts\python.exe" goto :venv_ready

echo [Key Manager] First run: creating a local virtual environment...
set "PY_CMD="
py -3.12 -c "import sys" >nul 2>&1 && set "PY_CMD=py -3.12"
if not defined PY_CMD set "PY_CMD=python"
%PY_CMD% -m venv "%TB_KEY_MANAGER_VENV%"
if errorlevel 1 (
  echo.
  echo Failed to create .venv. Make sure Python 3.11+ ^(3.12 recommended^) is installed.
  pause
  exit /b 1
)

:venv_ready
set "PY=%TB_KEY_MANAGER_VENV%\Scripts\python.exe"

"%PY%" -c "import webview" >nul 2>&1
if errorlevel 1 (
  echo [Key Manager] Installing dependencies...
  "%PY%" -m pip install --upgrade pip >nul
  "%PY%" -m pip install -e .
  if errorlevel 1 (
    echo.
    echo Failed to install dependencies. Check your internet connection and try again.
    pause
    exit /b 1
  )
)

set "PYTHONPATH=%CD%\src"
"%PY%" -m key_manager.main
if errorlevel 1 (
  echo.
  echo Key Manager exited with an error.
  pause
)
