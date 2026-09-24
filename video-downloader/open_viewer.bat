@echo off
setlocal EnableExtensions
cd /d "%~dp0"
title Realtime Video Viewer

echo.
set /p "VIDEO_URL=Video URL: "
if not defined VIDEO_URL (
  echo.
  echo [ERROR] URL is empty.
  pause
  exit /b 1
)

set "PORT="
for /f %%P in ('powershell -NoProfile -Command "$l=[System.Net.Sockets.TcpListener]::new([System.Net.IPAddress]::Loopback,0);$l.Start();$p=$l.LocalEndpoint.Port;$l.Stop();Write-Output $p"') do set "PORT=%%P"
if not defined PORT set "PORT=8765"

set "ENCODED_URL="
for /f "usebackq delims=" %%U in (`powershell -NoProfile -Command "[uri]::EscapeDataString($env:VIDEO_URL)"`) do set "ENCODED_URL=%%U"

if not defined ENCODED_URL (
  echo.
  echo [ERROR] Could not encode URL.
  pause
  exit /b 1
)

where py >nul 2>nul
if not errorlevel 1 goto USE_PY

where python >nul 2>nul
if not errorlevel 1 goto USE_PYTHON

echo.
echo [ERROR] Python was not found.
echo Install Python 3 and make sure py or python works in CMD.
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
start "" "http://127.0.0.1:%PORT%/index.html?url=%ENCODED_URL%"
exit /b 0
