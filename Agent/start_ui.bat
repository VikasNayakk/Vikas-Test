@echo off
setlocal
cd /d "%~dp0"
py Index.py
if errorlevel 1 (
  echo.
  echo Failed to start UI. Check Python installation and dependencies.
  pause
)
