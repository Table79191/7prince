@echo off
setlocal EnableExtensions DisableDelayedExpansion
cd /d "%~dp0"
title Realtime Video Viewer

if not exist "index.html" (
  echo.
  echo [ERROR] index.html was not found.
  echo Put this BAT file in the same folder as index.html.
  echo Folder: %CD%
  echo.
  pause
  exit /b 1
)

echo.
set /p "VIDEO_URL=Video URL: "
if not defined VIDEO_URL (
  echo.
  echo [ERROR] URL is empty.
  pause
  exit /b 1
)

where py >nul 2>nul
if not errorlevel 1 (
  set "PYEXE=py"
  goto GOT_PYTHON
)

where python >nul 2>nul
if not errorlevel 1 (
  set "PYEXE=python"
  goto GOT_PYTHON
)

echo.
echo [ERROR] Python was not found.
echo Install Python 3, then run this BAT again.
echo.
pause
exit /b 1

:GOT_PYTHON
set "PORT="
for /f %%P in ('powershell -NoProfile -Command "$l=[Net.Sockets.TcpListener]::new([Net.IPAddress]::Loopback,0);$l.Start();$p=$l.LocalEndpoint.Port;$l.Stop();$p"') do set "PORT=%%P"
if not defined PORT set "PORT=8765"

set "ENCODED_URL="
for /f "usebackq delims=" %%U in (`powershell -NoProfile -Command "[Uri]::EscapeDataString($env:VIDEO_URL)"`) do set "ENCODED_URL=%%U"

if not defined ENCODED_URL (
  echo.
  echo [ERROR] URL encoding failed.
  pause
  exit /b 1
)

set "LOGFILE=%TEMP%\realtime_video_viewer_%PORT%.log"
del /q "%LOGFILE%" >nul 2>nul

echo.
echo Starting local server on 127.0.0.1:%PORT% ...

if /i "%PYEXE%"=="py" (
  start "RealtimeVideoViewerServer" /min cmd /c "cd /d ""%CD%"" && py -m http.server %PORT% --bind 127.0.0.1 > ""%LOGFILE%"" 2>&1"
) else (
  start "RealtimeVideoViewerServer" /min cmd /c "cd /d ""%CD%"" && python -m http.server %PORT% --bind 127.0.0.1 > ""%LOGFILE%"" 2>&1"
)

set "READY="
for /L %%I in (1,1,20) do (
  powershell -NoProfile -Command "try { $r=Invoke-WebRequest -UseBasicParsing -TimeoutSec 1 'http://127.0.0.1:%PORT%/index.html'; if($r.StatusCode -ge 200 -and $r.StatusCode -lt 500){exit 0}else{exit 1} } catch { exit 1 }" >nul 2>nul
  if not errorlevel 1 (
    set "READY=1"
    goto SERVER_READY
  )
  >nul ping 127.0.0.1 -n 2
)

:SERVER_READY
if not defined READY (
  echo.
  echo [ERROR] Local server did not start.
  echo.
  if exist "%LOGFILE%" (
    echo ----- server log -----
    type "%LOGFILE%"
    echo ----------------------
  ) else (
    echo No server log was created.
  )
  echo.
  echo Try this command manually:
  echo %PYEXE% -m http.server %PORT% --bind 127.0.0.1
  echo.
  pause
  exit /b 1
)

echo Server is ready.
start "" "http://127.0.0.1:%PORT%/index.html?url=%ENCODED_URL%"
exit /b 0
