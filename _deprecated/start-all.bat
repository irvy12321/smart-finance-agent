@echo off
echo ============================================
echo   Smart Finance Agent - Start All Services
echo ============================================
echo.

echo This will start both backend and frontend servers.
echo.
echo Backend: http://localhost:8000
echo Frontend: http://localhost:3000
echo.
echo Press any key to continue...
pause >nul

echo.
echo [1/2] Starting Backend Server...
start "Smart Finance Backend" cmd /k "cd /d "%~dp0backend" && python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload"

echo Waiting for backend to initialize...
timeout /t 3 /nobreak >nul

echo.
echo [2/2] Starting Frontend Server...
start "Smart Finance Frontend" cmd /k "cd /d "%~dp0frontend" && npm run dev"

echo.
echo ============================================
echo   Both servers are starting!
echo ============================================
echo.
echo Backend: http://localhost:8000
echo Frontend: http://localhost:3000
echo.
echo Swagger UI: http://localhost:8000/docs
echo.
echo Close this window or press any key to exit...
pause >nul