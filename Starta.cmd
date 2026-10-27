@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Installera programmet med Installera.ps1 forst. Se START_HAR.md.
  pause
  exit /b 1
)
".venv\Scripts\python.exe" app.py --open
if errorlevel 1 pause
