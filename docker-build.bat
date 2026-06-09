@echo off
chcp 65001 >nul 2>&1
REM =============================================
REM  Smart Finance Agent - Docker Build & Run
REM =============================================

echo.
echo ========================================
echo   Smart Finance Agent - Docker Build
echo ========================================
echo.

REM Check Docker
docker --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Docker is not installed or not in PATH
    echo Please install Docker from https://docker.com
    pause
    exit /b 1
)
echo [OK] Docker found

REM Check Docker Compose
docker compose version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Docker Compose is not available
    pause
    exit /b 1
)
echo [OK] Docker Compose found

echo.
echo ========================================
echo   Building Images...
echo ========================================
echo.

REM Build backend image
echo [1/2] Building backend image...
docker compose build backend
if errorlevel 1 (
    echo [ERROR] Backend build failed
    pause
    exit /b 1
)
echo [OK] Backend image built

REM Build frontend image
echo [2/2] Building frontend image...
docker compose build frontend
if errorlevel 1 (
    echo [ERROR] Frontend build failed
    pause
    exit /b 1
)
echo [OK] Frontend image built

echo.
echo ========================================
echo   Build Complete!
echo ========================================
echo.
echo To start the services, run:
echo   docker compose up -d
echo.
echo To view logs:
echo   docker compose logs -f
echo.
echo To stop services:
echo   docker compose down
echo.
echo ========================================
pause
