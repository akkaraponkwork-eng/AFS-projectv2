@echo off
title AFS Setup
echo ==============================================
echo       AFS System - First Time Setup
echo ==============================================
echo.
echo 1. Checking Python Installation...
python --version >nul 2>&1
IF %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Python is not installed or not added to PATH.
    echo Please install Python 3.9+ from python.org and check "Add to PATH".
    pause
    exit /b
)
echo [OK] Python is installed.
echo.

echo 2. Setting up Virtual Environment (venv)...
IF NOT EXIST "venv\Scripts\activate.bat" (
    python -m venv venv
    echo [OK] Virtual Environment created.
) ELSE (
    echo [OK] Virtual Environment already exists.
)
echo.

echo 3. Activating Virtual Environment...
call venv\Scripts\activate
echo.

echo 4. Installing Python Dependencies...
pip install -r requirements.txt
echo [OK] Dependencies installed.
echo.

echo 5. Installing Playwright Browsers (This may take a few minutes)...
playwright install chromium
echo [OK] Playwright browsers installed.
echo.

echo ==============================================
echo   Setup Complete! You can now run start.bat
echo ==============================================
pause
