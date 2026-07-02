@echo off
chcp 65001 >nul 2>&1

:: Force Python to use UTF-8
set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1

title Robot Arm Web Server

echo ========================================
echo   Robot Arm Vision System - Starting...
echo ========================================
echo.

cd /d "%~dp0"

:: Activate venv
call .venv\Scripts\activate.bat 2>nul
if errorlevel 1 (
    echo [ERROR] Virtual environment not found!
    echo Please make sure .venv folder exists.
    pause
    exit /b 1
)

echo [OK] Virtual environment activated
echo [OK] Starting web server...
echo.
echo Browser will open: http://localhost:5000
echo Press Ctrl+C to stop the server
echo ========================================
echo.

:: Open browser after short delay
start "" http://localhost:5000

:: Start the server
python web_server.py

pause
