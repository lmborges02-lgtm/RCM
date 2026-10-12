@echo off
cd /d "%~dp0"
where pythonw >nul 2>nul
if errorlevel 1 (
  echo Python 3 com tkinter nao encontrado. Instale Python 3 para Windows.
  pause
  exit /b 1
)
start "" pythonw "%~dp0monitor.py"
