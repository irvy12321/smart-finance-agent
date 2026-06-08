@echo off
chcp 65001 >nul 2>&1
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
echo [OK] Python found

REM Check Node.js
node --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Node.js is not installed or not in PATH
    echo Please install Node.js 20+ from https://nodejs.org
    pause
    exit /b 1
)
echo [OK] Node.js found

REM Check .env file
if not exist "%~dp0backend\.env" (
    echo [WARNING] backend\.env not found!
    if exist "%~dp0backend\.env.example" (
        echo [INFO] Copying from .env.example...
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
echo [OK] .env file exists

echo.
echo ========================================
echo   Installing Dependencies...
echo ========================================
echo.

REM Install backend dependencies
echo [1/2] Installing backend dependencies...
cd /d "%~dp0backend"
pip install -r requirements.txt -q 2>nul
if errorlevel 1 (
    echo [WARNING] Some backend dependencies may have failed to install
) else (
    echo [OK] Backend dependencies installed
)

REM Install frontend dependencies
echo [2/2] Installing frontend dependencies...
cd /d "%~dp0frontend"
if not exist "node_modules" (
    call npm install --silent
    echo [OK] Frontend dependencies installed
) else (
    echo [OK] Frontend dependencies already installed
)

echo.
echo ========================================
echo   Starting Services...
echo ========================================
echo.

REM Kill existing processes on ports 8000 and 3000
echo [INFO] Checking for existing processes...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :8000 ^| findstr LISTENING') do (
    echo [INFO] Killing process on port 8000 (PID: %%a)
    taskkill /F /PID %%a >nul 2>&1
)
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :3000 ^| findstr LISTENING') do (
    echo [INFO] Killing process on port 3000 (PID: %%a)
    taskkill /F /PID %%a >nul 2>&1
)

REM Start Backend (FastAPI)
echo [1/2] Starting Backend (FastAPI on :8000)...
cd /d "%~dp0backend"
start "SFA-Backend" cmd /k "title Smart Finance Agent - Backend && python -m uvicorn app.main:app --reload --port 8000"

REM Wait for backend to be ready
echo [2/2] Waiting for backend to be ready...
set /a "retries=0"
set /a "max_retries=30"

:wait_backend
timeout /t 2 /nobreak >nul
set /a "retries+=1"

REM Check if backend is responding
curl -s http://localhost:8000/ping >nul 2>&1
if not errorlevel 1 (
    echo [OK] Backend is ready!
    goto :backend_ready
)

if %retries% geq %max_retries% (
    echo [WARNING] Backend may still be starting after %max_retries% attempts
    echo [INFO] Continuing anyway... Check the backend window for errors
    goto :backend_ready
)

echo [INFO] Waiting for backend... (attempt %retries%/%max_retries%)
goto :wait_backend

:backend_ready

REM Start Frontend (Vite)
echo [1/1] Starting Frontend (Vite on :3000)...
cd /d "%~dp0frontend"
start "SFA-Frontend" cmd /k "title Smart Finance Agent - Frontend && npm run dev"

echo.
echo ========================================
echo   Services Started!
echo ========================================
echo.
echo   Backend:  http://localhost:8000
echo   Frontend: http://localhost:3000
echo   API Docs: http://localhost:8000/docs
echo.
echo ========================================
echo.
echo Press any key to open the browser...
pause >nul
start http://localhost:3000
