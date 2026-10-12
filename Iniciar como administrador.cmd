@echo off
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0iniciar-admin.ps1"
if errorlevel 1 pause
