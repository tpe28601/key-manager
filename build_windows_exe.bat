@echo off
setlocal EnableExtensions EnableDelayedExpansion
cd /d "%~dp0"

echo ============================================================
echo   Key Manager 1.0.0 - pywebview Windows Build
echo ============================================================

set "PY_CMD="
py -3.12 -c "import sys; print(sys.executable)" >nul 2>&1 && set "PY_CMD=py -3.12"
if not defined PY_CMD python -c "import sys; print(sys.executable)" >nul 2>&1 && set "PY_CMD=python"

if not defined PY_CMD (
  echo [Build] Python 3.12 was not found. Trying winget...
  where winget >nul 2>&1 || goto :no_python
  winget install --id Python.Python.3.12 -e --source winget --accept-package-agreements --accept-source-agreements
  if errorlevel 1 goto :no_python
  set "PY_CMD=py -3.12"
)

if not exist ".build-venv\Scripts\python.exe" (
  echo [Build] Creating virtual environment...
  %PY_CMD% -m venv .build-venv
  if errorlevel 1 goto :failed
)

set "PYTHON=.build-venv\Scripts\python.exe"
echo [Build] Installing build dependencies...
"%PYTHON%" -m pip install --upgrade pip
"%PYTHON%" -m pip install -e ".[build]"
if errorlevel 1 goto :failed

if exist build rmdir /s /q build
if exist dist rmdir /s /q dist

echo [Build] Building compact single EXE...
"%PYTHON%" -m PyInstaller --noconfirm --clean key_manager.spec
if errorlevel 1 goto :failed

if not exist "dist\KeyManager.exe" goto :failed
for /f "usebackq delims=" %%S in (`powershell -NoProfile -Command "$f=Get-Item 'dist\KeyManager.exe'; '{0:N1} MB' -f ($f.Length/1MB)"`) do set "EXE_SIZE=%%S"

echo.
echo [Build] SUCCESS
echo [Build] Output: %CD%\dist\KeyManager.exe
echo [Build] Size: !EXE_SIZE!
echo [Build] Runtime prerequisite: Git for Windows + Microsoft Edge WebView2
echo.
start "" explorer.exe "%CD%\dist"
pause
exit /b 0

:no_python
echo [Build] Could not find or install Python 3.12.
goto :failed

:failed
echo.
echo [Build] FAILED. Review the messages above.
pause
exit /b 1
