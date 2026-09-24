@echo off
setlocal
cd /d "%~dp0"
title Realtime Video Viewer

set "PORT=8765"

where py >nul 2>nul
if not errorlevel 1 goto USE_PY

where python >nul 2>nul
if not errorlevel 1 goto USE_PYTHON

echo.
echo [ERROR] Python was not found.
echo Install Python 3 and make sure "py" or "python" works in CMD.
echo.
pause
exit /b 1

:USE_PY
start "VideoViewerServer" /min py -m http.server %PORT% --bind 127.0.0.1
goto OPEN_BROWSER

:USE_PYTHON
start "VideoViewerServer" /min python -m http.server %PORT% --bind 127.0.0.1
goto OPEN_BROWSER

:OPEN_BROWSER
timeout /t 1 /nobreak >nul
start "" "http://127.0.0.1:%PORT%/index.html"
exit /b 0
