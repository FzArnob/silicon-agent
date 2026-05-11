@echo off
setlocal

cd /d "%~dp0"

:: --- Check Python ---
where python >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python not found in PATH. Please install Python first.
    pause
    exit /b 1
)

:: --- Check & install playwright ---
python -c "import playwright" >nul 2>&1
if %errorlevel% neq 0 (
    echo [SETUP] Installing playwright...
    pip install playwright
    if %errorlevel% neq 0 (
        echo [ERROR] Failed to install playwright.
        pause
        exit /b 1
    )
    echo [SETUP] Installing playwright browsers...
    python -m playwright install chromium
    if %errorlevel% neq 0 (
        echo [ERROR] Failed to install playwright browsers.
        pause
        exit /b 1
    )
) else (
    echo [OK] playwright already installed.
)

:: --- Get Brave path ---
if exist "%~dp0brave_path.txt" (
    set /p BRAVE_PATH=<"%~dp0brave_path.txt"
    echo [OK] Using saved Brave path: !BRAVE_PATH!
) else (
    set BRAVE_PATH=
)

setlocal enabledelayedexpansion

if exist "%~dp0brave_path.txt" (
    set /p BRAVE_PATH=<"%~dp0brave_path.txt"
) else (
    set BRAVE_PATH=
)

if not defined BRAVE_PATH (
    set /p BRAVE_PATH="Enter full path to brave.exe (e.g. C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe): "
    echo !BRAVE_PATH!>"%~dp0brave_path.txt"
    echo [SAVED] Path saved to brave_path.txt for next time.
)

if not exist "!BRAVE_PATH!" (
    echo [ERROR] brave.exe not found at: !BRAVE_PATH!
    del "%~dp0brave_path.txt" >nul 2>&1
    pause
    exit /b 1
)

:: --- Check if port 9222 is already in use ---
netstat -ano | findstr ":9222" >nul 2>&1
if %errorlevel% equ 0 (
    echo [OK] Port 9222 already active, skipping Brave launch.
) else (
    echo [START] Launching Brave with remote debugging on port 9222...
    start "" "!BRAVE_PATH!" --remote-debugging-port=9222 --remote-debugging-address=127.0.0.1
)

:: --- Wait for CDP endpoint to be ready ---
echo [WAIT] Waiting for Brave CDP endpoint...
set RETRIES=0
:wait_loop
if !RETRIES! geq 30 (
    echo [ERROR] Brave CDP endpoint not available after 30 seconds.
    pause
    exit /b 1
)
python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:9222/json/version', timeout=2)" >nul 2>&1
if %errorlevel% equ 0 (
    echo [OK] Brave CDP endpoint ready.
    goto :run_session
)
set /a RETRIES+=1
timeout /t 1 /nobreak >nul
goto :wait_loop

:run_session
:: --- Run the session ---
echo [RUN] Starting session...
python start_session.py

endlocal
pause
