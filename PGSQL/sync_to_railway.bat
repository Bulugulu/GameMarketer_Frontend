@echo off
setlocal enabledelayedexpansion

echo ================================================
echo Railway Database Synchronization Script
echo ================================================
echo.

REM Check if Python is available
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Python is not available in PATH
    echo Please install Python or add it to your PATH
    pause
    exit /b 1
)

REM Check if pg_dump is available
pg_dump --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: pg_dump is not available in PATH
    echo Please install PostgreSQL client tools or add them to your PATH
    echo You can download them from: https://www.postgresql.org/download/windows/
    pause
    exit /b 1
)

REM Check if psql is available
psql --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: psql is not available in PATH
    echo Please install PostgreSQL client tools or add them to your PATH
    pause
    exit /b 1
)

REM Check if .env.local exists
if not exist "..\\.env.local" (
    echo ERROR: .env.local file not found in project root
    echo Please ensure your .env.local file exists with DATABASE_PUBLIC_URL and PG_* variables
    pause
    exit /b 1
)

echo All prerequisites check passed!
echo.
echo This script will:
echo - Dump your local PostgreSQL database
echo - Upload it to Railway
echo - Verify the synchronization
echo.
set /p confirm="Do you want to continue? (y/N): "
if /i not "%confirm%"=="y" (
    echo Operation cancelled.
    pause
    exit /b 0
)

echo.
echo Starting database synchronization...
echo.

REM Run the Python script
python railway_db_sync.py

if %errorlevel% equ 0 (
    echo.
    echo ================================================
    echo Database synchronization completed successfully!
    echo ================================================
) else (
    echo.
    echo ================================================
    echo Database synchronization failed!
    echo ================================================
    echo Please check the error messages above.
)

echo.
pause 