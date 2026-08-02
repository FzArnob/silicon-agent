@echo off
setlocal

set "ROOT_DIR=%~dp0"
cd /d "%ROOT_DIR%"

if "%~1"=="" goto :help

if /I "%~1"=="help" goto :help
if /I "%~1"=="setup" goto :setup
if /I "%~1"=="node-deps" goto :node_deps
if /I "%~1"=="py-deps" goto :py_deps
if /I "%~1"=="init-db" goto :init_db
if /I "%~1"=="backend" goto :backend
if /I "%~1"=="start" goto :start
if /I "%~1"=="all" goto :all

echo Unknown command: %~1
echo.
goto :help

:setup
call :node_deps || exit /b 1
call :py_deps || exit /b 1
echo Setup complete.
goto :eof

:node_deps
echo Installing Node dependencies...
call npm install
if errorlevel 1 exit /b 1
goto :eof

:py_deps
call :detect_python || exit /b 1
echo Installing Python dependencies...
call %PYTHON_CMD% -m pip install -r backend\requirements.txt
if errorlevel 1 exit /b 1
goto :eof

:init_db
call :detect_python || exit /b 1
echo Initializing SQLite database...
set "PYTHONPATH=%ROOT_DIR%"
call %PYTHON_CMD% -c "from backend.app.db import init_db, DATABASE_PATH; init_db(); print('Database ready at', DATABASE_PATH)"
if errorlevel 1 exit /b 1
goto :eof

:backend
call :detect_python || exit /b 1
echo Starting FastAPI backend on http://127.0.0.1:8000 ...
call %PYTHON_CMD% -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
goto :eof

:start
echo Starting desktop app...
call npm start
goto :eof

:all
call :setup || exit /b 1
call :init_db || exit /b 1
call :start
goto :eof

:detect_python
where py >nul 2>nul
if %errorlevel%==0 (
    set "PYTHON_CMD=py -3"
    goto :eof
)

where python >nul 2>nul
if %errorlevel%==0 (
    set "PYTHON_CMD=python"
    goto :eof
)

echo Python was not found in PATH.
exit /b 1

:help
echo Silicon Agent Desktop command runner
echo.
echo Usage:
echo   run.bat ^<command^>
echo.
echo Commands:
echo   help        Show this help message
echo   setup       Install Node and Python dependencies
echo   node-deps   Install Node dependencies (npm install)
echo   py-deps     Install Python dependencies (pip install -r backend\requirements.txt)
echo   init-db     Create or update the SQLite schema in data/app.db
echo   backend     Run the FastAPI backend only
echo   start       Run the Electron app (starts the backend automatically)
echo   all         setup + init-db + start
exit /b 0
