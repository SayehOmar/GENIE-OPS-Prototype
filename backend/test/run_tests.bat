@echo off
REM GENIE OPS - Automated Test Runner
REM Starts test server and runs submission workflow tests

echo ========================================
echo GENIE OPS - Test Runner
echo ========================================
echo.

REM Get the directory where this batch file is located
set "TEST_DIR=%~dp0"
set "PROJECT_ROOT=%TEST_DIR%..\.."
set "BACKEND_DIR=%TEST_DIR%.."
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

REM Check if pytest is installed
python -m pytest --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Installing pytest and dependencies...
    pip install pytest pytest-asyncio
    if %errorlevel% neq 0 (
        echo ERROR: Failed to install pytest
        pause
        exit /b 1
    )
)

REM Check if playwright is installed
python -c "import playwright" >nul 2>&1
if %errorlevel% neq 0 (
    echo Installing Playwright...
    pip install playwright
    if %errorlevel% neq 0 (
        echo ERROR: Failed to install playwright
        pause
        exit /b 1
    )
    echo Installing Playwright browsers...
    python -m playwright install chromium
)

REM Check if test server is running on port 8080
netstat -an | findstr ":8080" | findstr "LISTENING" >nul 2>&1
if %errorlevel% neq 0 (
    echo Test server not running. Starting test server...
    echo.
    echo Starting test server in background...
    REM Start server from backend/test directory
    start "GENIE OPS - Test Server" cmd /k "cd /d %TEST_DIR% && python -m http.server 8080"
    
    echo Waiting for test server to start...
    timeout /t 3 /nobreak >nul
    
    REM Verify server started
    netstat -an | findstr ":8080" | findstr "LISTENING" >nul 2>&1
    if %errorlevel% neq 0 (
        echo WARNING: Test server may not have started. Continuing anyway...
    ) else (
        echo Test server started successfully on port 8080
    )
) else (
    echo Test server is already running on port 8080
)

echo.
echo Opening test form in browser...
timeout /t 1 /nobreak >nul
start http://localhost:8080/test_form.html
timeout /t 2 /nobreak >nul
echo Test form opened. You can watch the browser automation fill the form.
echo.

echo.
echo ========================================
echo Running Tests
echo ========================================
echo.

REM Check if Ollama is available (optional)
ollama list >nul 2>&1
if %errorlevel% equ 0 (
    echo Ollama is available - AI tests will run
    set "AI_AVAILABLE=1"
) else (
    echo Ollama not available - AI tests will be skipped
    set "AI_AVAILABLE=0"
)

echo.
echo Running all tests...
echo.

REM Run tests with verbose output (venv should be activated)
cd "%BACKEND_DIR%"
python -m pytest test/test_submission.py -v --tb=short

set "TEST_RESULT=%errorlevel%"

echo.
echo ========================================
echo Test Results
echo ========================================
echo.

:test_loop
if %TEST_RESULT% equ 0 (
    echo All tests PASSED!
) else (
    echo Some tests FAILED. Check output above for details.
)

echo.
echo Test results saved. Check backend/storage/screenshots/ for screenshots.
echo Form analysis reports saved to backend/test/reports/
echo.
echo Opening test form...
timeout /t 2 /nobreak >nul
start http://localhost:8080/test_form.html

echo.
echo ========================================
echo Test Complete
echo ========================================
echo.
echo Type 'r' and press Enter to redo the tests, or any other key to exit...
set /p REDO="> "

if /i "%REDO%"=="r" (
    echo.
    echo Running tests again...
    echo.
    cd "%BACKEND_DIR%"
    python -m pytest test/test_submission.py -v --tb=short
    set "TEST_RESULT=%errorlevel%"
    echo.
    echo ========================================
    echo Test Results
    echo ========================================
    echo.
    goto :test_loop
)

echo.
echo Exiting...
timeout /t 1 /nobreak >nul
