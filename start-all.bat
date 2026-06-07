@echo off
REM =============================================
REM  Smart Finance Agent - Start All Services
REM =============================================

echo.
echo ========================================
echo   Smart Finance Agent - Starting...
echo ========================================
echo.

REM Start Backend (FastAPI)
echo [1/2] Starting Backend (FastAPI on :8000)...
start "SFA-Backend" cmd /k "cd /d %~dp0backend && python -m uvicorn app.main:app --reload --port 8000"

REM Wait for backend to initialize
timeout /t 3 /nobreak >nul

REM Start Frontend (Vite)
echo [2/2] Starting Frontend (Vite on :3000)...
start "SFA-Frontend" cmd /k "cd /d %~dp0frontend && npm run dev"

echo.
echo ========================================
echo   Services Starting...
echo   Backend:  http://localhost:8000
echo   Frontend: http://localhost:3000
echo   API Docs: http://localhost:8000/docs
echo ========================================
echo.
pause
