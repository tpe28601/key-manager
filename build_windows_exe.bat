@echo off
setlocal EnableExtensions EnableDelayedExpansion
cd /d "%~dp0"

echo ============================================================
echo   Key Manager 1.2.2 - pywebview Windows Release Build
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

echo [Build] Building Windows single EXE without UPX...
"%PYTHON%" -m PyInstaller --noconfirm --clean key_manager.spec
if errorlevel 1 goto :failed

set "EXE=dist\KeyManager.exe"
if not exist "%EXE%" goto :failed

powershell -NoProfile -Command "$h=(Get-FileHash '%EXE%' -Algorithm SHA256).Hash; Set-Content -Encoding ascii '%EXE%.sha256' ($h + '  KeyManager.exe'); Write-Host ('[Build] SHA256: ' + $h)"
if errorlevel 1 goto :failed

for /f "usebackq delims=" %%S in (`powershell -NoProfile -Command "$f=Get-Item '%EXE%'; '{0:N1} MB' -f ($f.Length/1MB)"`) do set "EXE_SIZE=%%S"

echo.
echo [Build] SUCCESS
echo [Build] App: %CD%\%EXE%
echo [Build] Size: !EXE_SIZE!
echo [Build] SHA256 file: %CD%\%EXE%.sha256
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
