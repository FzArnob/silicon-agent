@echo off
setlocal

set "ROOT_DIR=%~dp0"
cd /d "%ROOT_DIR%"

if "%~1"=="" goto :help

if /I "%~1"=="help" goto :help
if /I "%~1"=="setup" goto :setup
if /I "%~1"=="build" goto :setup
if /I "%~1"=="node-deps" goto :node_deps
if /I "%~1"=="py-deps" goto :py_deps
if /I "%~1"=="init-db" goto :init_db
if /I "%~1"=="import-csv" goto :import_csv
if /I "%~1"=="backend" goto :backend
if /I "%~1"=="electron" goto :electron
if /I "%~1"=="dev" goto :dev
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
echo [1/1] Installing Node dependencies...
call npm install
if errorlevel 1 exit /b 1
goto :eof

:py_deps
call :detect_python || exit /b 1
echo [1/1] Installing Python dependencies...
call %PYTHON_CMD% -m pip install -r backend\requirements.txt
if errorlevel 1 exit /b 1
goto :eof

:init_db
call :detect_python || exit /b 1
echo Initializing SQLite database...
call %PYTHON_CMD% -c "from backend.app.db import init_db; init_db(); print('Database initialized at backend/data/app.db')"
if errorlevel 1 exit /b 1
goto :eof

:import_csv
call :detect_python || exit /b 1
echo Importing CSV files into SQLite...
call %PYTHON_CMD% backend\scripts\import_csv_to_sqlite.py
if errorlevel 1 exit /b 1
goto :eof

:backend
call :detect_python || exit /b 1
echo Starting FastAPI backend on http://127.0.0.1:8000 ...
call %PYTHON_CMD% -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
goto :eof

:electron
echo Starting Electron app...
call npm run start
goto :eof

:dev
echo Starting desktop dev mode (Electron + backend launcher)...
call npm run dev
goto :eof

:all
call :setup || exit /b 1
call :init_db || exit /b 1
call :import_csv || exit /b 1
echo All prep steps complete.
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
echo   build       Alias for setup
echo   node-deps   Install Node dependencies (npm install)
echo   py-deps     Install Python dependencies (pip install -r backend\requirements.txt)
echo   init-db     Create or update SQLite schema in backend/data/app.db
echo   import-csv  Import legacy monthly CSV data into SQLite
echo   backend     Run FastAPI backend only
echo   electron    Run Electron app (uses npm start)
echo   dev         Run desktop dev mode (npm run dev)
echo   all         setup + init-db + import-csv
exit /b 0
