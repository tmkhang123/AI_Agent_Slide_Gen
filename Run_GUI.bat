@echo off
setlocal enabledelayedexpansion
title AI Slides Maker GUI
color 0B

set PYTHON_EXE="d:\Data\File for Google Drive real\Project\AI_Agent_Slides_Maker\AI_Slide_Agent_Maker\.venv\Scripts\python.exe"
set APP_PATH=d:\Data\File for Google Drive real\Project\AI_Agent_Slides_Maker\AI_Slide_Agent_Maker\gui_app.py

if not exist "%PYTHON_EXE%" (
    echo [ERROR] Python environment not found. 
    pause
    exit /b
)

echo Dang khoi dong giao dien AI Slides Maker...
"%PYTHON_EXE%" -m streamlit run "%APP_PATH%"

pause