@echo off
setlocal
cd /d "%~dp0"

where node >nul 2>nul
if errorlevel 1 (
  echo [ERROR] Node.js was not found in PATH.
  pause
  exit /b 1
)

if not exist "node_modules\playwright" (
  echo Installing dependencies...
  call npm install
  if errorlevel 1 (
    echo [ERROR] npm install failed.
    pause
    exit /b 1
  )
)

echo Starting or attaching to the dedicated local Chrome session...
call npm run namuwiki
set "EXITCODE=%ERRORLEVEL%"

echo.
if "%EXITCODE%"=="0" (
  echo [OK] The target page was classified as reachable.
) else (
  echo [INFO] The site still requires normal browser verification or access was blocked.
  echo Keep the Chrome window open and complete any normal site verification shown there, then run this file again.
)

pause
exit /b %EXITCODE%
