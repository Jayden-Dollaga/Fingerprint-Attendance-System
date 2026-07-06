@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"

set PYTHON_CMD=python
%PYTHON_CMD% --version >nul 2>&1
if errorlevel 1 (
    set PYTHON_CMD=python3
    %PYTHON_CMD% --version >nul 2>&1
    if errorlevel 1 (
        echo Python is not installed or not on PATH.
        echo Install Python 3 and try again.
        pause
        exit /b 1
    )
)

echo Using %PYTHON_CMD% to install dependencies...
%PYTHON_CMD% -m pip install --quiet -r requirements.txt
if errorlevel 1 (
    echo Failed to install requirements.
    echo Please check your Python installation and requirements.txt.
    pause
    exit /b 1
)

echo Dependencies installed successfully.
pause
