@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"

echo.
echo ============================================
echo  RazziPT Server Launcher
echo ============================================
echo.

REM Kill any existing process on port 8000
echo Cleaning up previous server instances...
for /f "tokens=5" %%a in ('netstat -ano ^| find ":8000" ^| find "LISTENING"') do (
    taskkill /F /PID %%a >nul 2>&1
)

timeout /t 1 /nobreak >nul

echo Starting RazziPT Server...
echo.
echo The server will run on: http://localhost:8000
echo.
echo ✨ Features:
echo   - Chat with AI personalities
echo   - Dark/Light mode support  
echo   - Secure authentication
echo   - Memory management
echo.
echo Press CTRL+C to stop the server.
echo ============================================
echo.

python main.py

if errorlevel 1 (
    echo.
    echo ❌ Error: Server failed to start
    echo.
    echo Troubleshooting:
    echo 1. Make sure Python is installed
    echo 2. Run: pip install -r requirements.txt
    echo 3. Check that all files are in the correct location
    echo.
    pause
)
