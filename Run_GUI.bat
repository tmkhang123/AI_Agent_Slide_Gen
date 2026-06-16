@echo off
setlocal enabledelayedexpansion
title AI Slides Maker GUI
color 0B

:: Tu dong lay thu muc hien tai cua file bat
set "PROJECT_DIR=%~dp0"
set "PYTHON_EXE=%PROJECT_DIR%.venv\Scripts\python.exe"
set "APP_PATH=%PROJECT_DIR%gui_app.py"

if not exist "%PYTHON_EXE%" (
    echo [ERROR] Python environment not found. 
    echo Hay dam bao rang .venv da duoc khoi tao trong thu muc:
    echo %PROJECT_DIR%
    pause
    exit /b
)

echo Dang khoi dong giao dien AI Slides Maker...
"%PYTHON_EXE%" -m streamlit run "%APP_PATH%"

pause