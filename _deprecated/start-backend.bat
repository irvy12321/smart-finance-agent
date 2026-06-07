@echo off
echo ============================================
echo   Smart Finance Agent - Backend Server
echo ============================================
echo.

cd /d "%~dp0backend"

echo [1/3] Checking Python installation...
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.8+ from https://python.org
    pause
    exit /b 1
)
echo Python found!

echo.
echo [2/3] Installing Python dependencies...
pip install -r requirements.txt
if errorlevel 1 (
    echo WARNING: Some dependencies may have failed to install
    echo Continuing anyway...
)

echo.
echo [3/3] Starting FastAPI server...
echo.
echo Server will be available at:
echo   - API: http://localhost:8000
echo   - Swagger UI: http://localhost:8000/docs
echo   - ReDoc: http://localhost:8000/redoc
echo.
echo Press Ctrl+C to stop the server
echo.

python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

pause