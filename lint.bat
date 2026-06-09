@echo off
echo ========================================
echo Smart Finance Agent - Lint Runner
echo ========================================
echo.

echo [1/4] Installing backend lint dependencies...
cd backend
pip install ruff -q
if %errorlevel% neq 0 (
    echo Failed to install ruff
    exit /b 1
)
cd ..

echo.
echo [2/4] Running backend lint...
cd backend
ruff check .
if %errorlevel% neq 0 (
    echo Backend lint failed
    exit /b 1
)

ruff format --check .
if %errorlevel% neq 0 (
    echo Backend format check failed
    exit /b 1
)
cd ..

echo.
echo [3/4] Installing frontend lint dependencies...
cd frontend
call npm ci --silent
if %errorlevel% neq 0 (
    echo Failed to install frontend dependencies
    exit /b 1
)
cd ..

echo.
echo [4/4] Running frontend lint...
cd frontend
call npm run lint
if %errorlevel% neq 0 (
    echo Frontend lint failed
    exit /b 1
)
cd ..

echo.
echo ========================================
echo Lint passed successfully!
echo ========================================