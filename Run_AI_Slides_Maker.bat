@echo off
setlocal enabledelayedexpansion
title AI Slides Maker - GitHub Copilot Edition
color 0B

echo ============================================================
echo           WELCOME TO AI SLIDES MAKER AGENT
echo ============================================================
echo.

:: Path to the virtual environment python
set PYTHON_EXE=d:\Data\File for Google Drive real\Project\AI_Agent_Slides_Maker\.venv\Scripts\python.exe
set SCRIPT_PATH=d:\Data\File for Google Drive real\Project\AI_Agent_Slides_Maker\main.py

:: Check if Python exists
if not exist "%PYTHON_EXE%" (
    echo [ERROR] Python environment not found at:
    echo "%PYTHON_EXE%"
    echo Please make sure the project setup is complete.
    pause
    exit /b
)

:RUN
cls
echo ============================================================
echo           WELCOME TO AI SLIDES MAKER AGENT
echo ============================================================
echo.
echo [*] Working Directory: %CD%
echo.

:: Run the AI program
"%PYTHON_EXE%" "%SCRIPT_PATH%"

echo.
echo ============================================================
echo [DONE] Processing complete.
echo ============================================================
echo.
set /p CHOICE="Do you want to create another presentation? (y/n): "

if /i "%CHOICE%"=="y" goto RUN

echo.
echo Thank you for using AI Slides Maker! Goodbye.
pause
