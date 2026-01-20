@echo off
REM GENIE OPS - Development Startup Script
REM Starts backend and frontend servers in separate windows and opens the browser

echo Starting GENIE OPS Development Environment...
echo.

REM Get the directory where this batch file is located
set "PROJECT_ROOT=%~dp0"
cd /d "%PROJECT_ROOT%"

REM Check if backend venv exists
if not exist "backend\venv\Scripts\activate.bat" (
    echo ERROR: Virtual environment not found in backend\venv
    echo Please create it first with: cd backend ^&^& python -m venv venv
    pause
    exit /b 1
)

REM Check if node_modules exists in frontend
if not exist "frontend\node_modules" (
    echo WARNING: Frontend dependencies not installed.
    echo Installing frontend dependencies...
    cd frontend
    call npm install
    cd ..
) else (
    echo Checking frontend dependencies...
    cd frontend
    call npm install
    cd ..
)

REM Start Backend Server in a new window
echo Starting Backend Server (FastAPI)...
start "GENIE OPS - Backend Server" cmd /k "cd /d %PROJECT_ROOT%backend && venv\Scripts\activate && echo Backend Server Starting... && uvicorn app.main:app --reload --port 8000"

REM Wait a moment for backend to start
timeout /t 2 /nobreak >nul

REM Start Frontend Server in a new window
echo Starting Frontend Server (Vite)...
start "GENIE OPS - Frontend Server" cmd /k "cd /d %PROJECT_ROOT%frontend && echo Frontend Server Starting... && npm run dev"

REM Wait for servers to initialize
echo.
echo Waiting for servers to start...
timeout /t 5 /nobreak >nul

REM Open browser to frontend
echo Opening browser...
start http://localhost:5173

echo.
echo ========================================
echo Development servers started!
echo.
echo Backend API: http://localhost:8000
echo Backend Docs: http://localhost:8000/docs
echo Frontend: http://localhost:5173
echo.
echo Press any key to exit this window...
echo (The server windows will remain open)
echo ========================================
pause >nul
