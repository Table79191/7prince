@echo off
setlocal
cd /d "%~dp0"
title Realtime Video Viewer

where py >nul 2>nul
if %errorlevel%==0 (
  py serve_viewer.py
  exit /b %errorlevel%
)

where python >nul 2>nul
if %errorlevel%==0 (
  python serve_viewer.py
  exit /b %errorlevel%
)

echo Python 3 is required to launch the local HTTP viewer.
echo Install Python, then run this file again.
pause
exit /b 1
