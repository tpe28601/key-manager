@echo off
setlocal
cd /d "%~dp0"
if exist ".venv\Scripts\python.exe" (
  set "PY=.venv\Scripts\python.exe"
) else (
  py -3.12 -c "import sys" >nul 2>&1 && set "PY=py -3.12"
  if not defined PY set "PY=python"
)
set "PYTHONPATH=%CD%\src"
%PY% -m key_manager.main
if errorlevel 1 (
  echo.
  echo Key Manager exited with an error.
  pause
)
