@echo off
SETLOCAL EnableDelayedExpansion

:: Ensure we are in the script's directory
pushd "%~dp0"

echo ====================================================
echo NetworkTools-V3 Environment Setup
echo ====================================================

:: Check if venv exists
IF EXIST venv (
    echo [INFO] Existing venv found.
    set /p del_venv="Do you want to delete and recreate the virtual environment? (y/n): "
    if /I "!del_venv!"=="y" (
        echo [INFO] Deleting existing venv...
        rmdir /s /q venv
    )
)

:: Create venv if it doesn't exist
IF NOT EXIST "venv\Scripts\python.exe" (
    echo [INFO] Creating new virtual environment in %CD%\venv...
    python -m venv venv
    if %ERRORLEVEL% NEQ 0 (
        echo [ERROR] Failed to create virtual environment.
        pause
        exit /b %ERRORLEVEL%
    )
)

:: Install dependencies
echo [INFO] Activating virtual environment...
call venv\Scripts\activate.bat

echo [INFO] Upgrading pip...
python -m pip install --upgrade pip

echo [INFO] Installing dependencies from requirements.txt...
python -m pip install -r requirements.txt --upgrade
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Failed to install dependencies.
    pause
    exit /b %ERRORLEVEL%
)

:: Use the venv python specifically for init
echo [INFO] Initializing database...
venv\Scripts\python.exe run.py --init-only
if %ERRORLEVEL% NEQ 0 (
    echo [WARNING] Database initialization failed.
)

echo ====================================================
echo [SUCCESS] Environment setup complete.
echo You can now run the application with: python run.py
echo ====================================================
pause
