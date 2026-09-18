@echo off
setlocal
cd /d "%~dp0"

if exist ".venv\Scripts\python.exe" goto :venv_ready

echo [Key Manager] First run: creating a local virtual environment...
set "PY_CMD="
py -3.12 -c "import sys" >nul 2>&1 && set "PY_CMD=py -3.12"
if not defined PY_CMD set "PY_CMD=python"
%PY_CMD% -m venv .venv
if errorlevel 1 (
  echo.
  echo Failed to create .venv. Make sure Python 3.11+ ^(3.12 recommended^) is installed.
  pause
  exit /b 1
)

:venv_ready
set "PY=.venv\Scripts\python.exe"

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
