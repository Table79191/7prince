@echo off
setlocal
cd /d "%~dp0"
title Video Downloader

where py >nul 2>nul
if %errorlevel%==0 (
  set "PY=py"
) else (
  where python >nul 2>nul
  if %errorlevel%==0 (
    set "PY=python"
  ) else (
    echo Python 3 is required.
    echo Install Python from https://www.python.org/downloads/
    pause
    exit /b 1
  )
)

if not exist ".venv\Scripts\python.exe" (
  echo [1/3] Creating local environment...
  %PY% -m venv .venv || goto :fail
)

echo [2/3] Updating downloader...
".venv\Scripts\python.exe" -m pip install --disable-pip-version-check -q --upgrade -r requirements.txt || goto :fail

echo [3/3] Start
echo.
".venv\Scripts\python.exe" video_downloader.py
set "EXITCODE=%errorlevel%"

echo.
if not "%EXITCODE%"=="0" (
  echo Download failed. Read the error above.
)
pause
exit /b %EXITCODE%

:fail
echo.
echo Setup failed.
pause
exit /b 1
