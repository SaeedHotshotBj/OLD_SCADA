@echo off
setlocal
cd /d "%~dp0"

echo ========================================
echo          OLD SCADA EDGE
echo ========================================
echo.

where py >nul 2>&1
if errorlevel 1 (
    echo Python is not installed or not in PATH.
    pause
    exit /b 1
)

if not exist venv\Scripts\python.exe (
    echo Creating virtual environment...
    py -m venv venv
    if errorlevel 1 (
        echo Failed to create virtual environment.
        pause
        exit /b 1
    )
)

echo Installing requirements...
venv\Scripts\python.exe -m pip install -r requirements.txt
if errorlevel 1 (
    echo Failed to install requirements.
    pause
    exit /b 1
)

echo.
echo Starting Edge...
echo.
venv\Scripts\python.exe edge.py
pause
