@echo off
echo ============================================
echo   Smart Finance Agent - Frontend Server
echo ============================================
echo.

cd /d "%~dp0frontend"

echo [1/3] Checking Node.js installation...
node --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Node.js is not installed or not in PATH
    echo Please install Node.js 16+ from https://nodejs.org
    pause
    exit /b 1
)
echo Node.js found!

echo.
echo [2/3] Installing Node.js dependencies...
call npm install
if errorlevel 1 (
    echo ERROR: Failed to install dependencies
    pause
    exit /b 1
)

echo.
echo [3/3] Starting React development server...
echo.
echo Frontend will be available at:
echo   - http://localhost:5173
echo.
echo Make sure backend is running at http://localhost:8000
echo.
echo Press Ctrl+C to stop the server
echo.

call npm run dev

pause