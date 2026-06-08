@echo off
REM =============================================
REM  Smart Finance Agent - Start All Services
REM =============================================

echo.
echo ========================================
echo   Smart Finance Agent - Starting...
echo ========================================
echo.

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not installed or not in PATH
    echo Please install Python 3.11+ from https://python.org
    pause
    exit /b 1
)

REM Check Node.js
node --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Node.js is not installed or not in PATH
    echo Please install Node.js 20+ from https://nodejs.org
    pause
    exit /b 1
)

REM Check .env file
if not exist "%~dp0backend\.env" (
    echo [WARNING] backend\.env not found!
    echo Copying from .env.example...
    if exist "%~dp0backend\.env.example" (
        copy "%~dp0backend\.env.example" "%~dp0backend\.env" >nul
        echo [INFO] Please edit backend\.env and set your API keys
        echo        Then run this script again.
        pause
        exit /b 1
    ) else (
        echo [ERROR] No .env.example found. Please create backend\.env with your API keys.
        pause
        exit /b 1
    )
)

REM Install backend dependencies
echo [1/4] Installing backend dependencies...
cd /d "%~dp0backend"
pip install -r requirements.txt -q 2>nul
if errorlevel 1 (
    echo [WARNING] Some backend dependencies may have failed to install
    echo [INFO] Trying to continue anyway...
)

REM Install frontend dependencies
echo [2/4] Installing frontend dependencies...
cd /d "%~dp0frontend"
if not exist "node_modules" (
    echo [INFO] Running npm install...
    call npm install
) else (
    echo [INFO] node_modules exists, skipping npm install
)

REM Start Backend (FastAPI)
echo [3/4] Starting Backend (FastAPI on :8000)...
start "SFA-Backend" cmd /k "cd /d %~dp0backend && python -m uvicorn app.main:app --reload --port 8000"

REM Wait for backend health check
echo [4/4] Waiting for backend to be ready...
set /a "retries=0"
:health_check
timeout /t 2 /nobreak >nul
curl -s http://localhost:8000/ping >nul 2>&1
if errorlevel 1 (
    set /a "retries+=1"
    if %retries% geq 15 (
        echo [WARNING] Backend may still be starting. Continuing...
        goto :backend_ready
    )
    echo [INFO] Waiting for backend... (attempt %retries%/15)
    goto :health_check
)
echo [INFO] Backend is ready!

:backend_ready
REM Start Frontend (Vite)
echo [5/5] Starting Frontend (Vite on :3000)...
start "SFA-Frontend" cmd /k "cd /d %~dp0frontend && npm run dev"

echo.
echo ========================================
echo   Services Starting...
echo   Backend:  http://localhost:8000
echo   Frontend: http://localhost:3000
echo   API Docs: http://localhost:8000/docs
echo ========================================
echo.
echo.
echo ========================================
echo   Quick Test Commands:
echo   curl http://localhost:8000/ping
echo   curl -X POST http://localhost:8000/api/task/create -H "Content-Type: application/json" -d "{\"query\": \"AAPL stock analysis\", \"priority\": 1}"
echo ========================================
echo.
echo Press any key to open the browser...
pause >nul
start http://localhost:3000
