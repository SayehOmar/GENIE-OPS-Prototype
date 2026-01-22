@echo off
REM GENIE OPS - Submission Processor
REM Interactive launcher for processing submissions

echo ========================================
echo GENIE OPS - Submission Processor
echo ========================================
echo.

REM Get the directory where this batch file is located
set "SCRIPTS_DIR=%~dp0"
set "BACKEND_DIR=%SCRIPTS_DIR%.."
set "PROJECT_ROOT=%SCRIPTS_DIR%..\.."
cd /d "%PROJECT_ROOT%"

REM Check if venv exists and activate it
if exist "%BACKEND_DIR%\venv\Scripts\activate.bat" (
    echo Activating virtual environment...
    call "%BACKEND_DIR%\venv\Scripts\activate.bat"
) else (
    echo WARNING: Virtual environment not found at %BACKEND_DIR%\venv
    echo Continuing with system Python...
)

REM Check if Python is available
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Python is not installed or not in PATH
    pause
    exit /b 1
)

REM Check database connection (optional - script will handle errors)
echo.
echo Checking database connection...
cd "%BACKEND_DIR%"
python -c "import sys; sys.path.insert(0, '.'); from app.db.session import SessionLocal; db = SessionLocal(); db.close(); print('OK')" >nul 2>&1
if %errorlevel% neq 0 (
    echo WARNING: Could not verify database connection.
    echo The script will attempt to connect when needed.
    echo Make sure PostgreSQL is running and DATABASE_URL is correct in .env
    echo.
)

echo.
echo Starting submission processor...
echo.

REM Run the CLI script (will show interactive menu if no args)
cd "%BACKEND_DIR%"
python scripts/submit.py %*

if %errorlevel% neq 0 (
    echo.
    echo ERROR: Submission processor exited with error code %errorlevel%
    pause
    exit /b %errorlevel%
)

echo.
echo ========================================
echo Processing Complete
echo ========================================
echo.
pause
