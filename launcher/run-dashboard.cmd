@echo off
setlocal
set "LAUNCHER_DIR=%~dp0"
set "PYTHONW=%LAUNCHER_DIR%..\sidecar\.venv\Scripts\pythonw.exe"
if not exist "%PYTHONW%" (
  echo The sidecar Python environment is missing.
  echo Run: cd /d "%LAUNCHER_DIR%..\sidecar" ^&^& uv sync
  pause
  exit /b 1
)
start "Tortoise WoW Dashboard" "%PYTHONW%" "%LAUNCHER_DIR%main.py"

