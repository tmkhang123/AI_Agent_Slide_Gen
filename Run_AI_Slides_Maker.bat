@echo off
setlocal enabledelayedexpansion
title AI Slides Maker - GitHub Copilot Edition
color 0B

echo ============================================================
echo           WELCOME TO AI SLIDES MAKER AGENT
echo ============================================================
echo.

:: Path to the virtual environment python
set PYTHON_EXEC:\Users\longh\Desktop\AI_Slide_Agent_Maker\.venv\Scripts\python.exe
set SCRIPT_PATH=C:\Users\longh\Desktop\AI_Slide_Agent_Maker\main.py
set WATCHER_PATH=C:\Users\longh\Desktop\AI_Slide_Agent_Maker\watcher.py

:: Check if Python exists
if not exist "%PYTHON_EXE%" (
    echo [ERROR] Python environment not found at:
    echo "%PYTHON_EXE%"
    echo Please make sure the project setup is complete.
    pause
    exit /b
)

:MENU
cls
echo ============================================================
echo           WELCOME TO AI SLIDES MAKER AGENT
echo ============================================================
echo.
echo  [1] Create new slides from topic
echo  [2] Create slides from modified JSON file
echo  [3] Start WATCH MODE (Auto-update slide when JSON changes)
echo  [4] Exit
echo.
set /p OPT="Select an option (1-4): "

if "%OPT%"=="1" goto RUN_TOPIC
if "%OPT%"=="2" goto RUN_JSON
if "%OPT%"=="3" goto RUN_WATCH
if "%OPT%"=="4" exit /b
goto MENU

:RUN_TOPIC
echo.
"%PYTHON_EXE%" "%SCRIPT_PATH%"
goto AFTER_RUN

:RUN_JSON
:: ... existing JSON selection code ...
goto AFTER_RUN

:RUN_WATCH
echo.
"%PYTHON_EXE%" "%WATCHER_PATH%"
pause
goto MENU

:RUN_TOPIC
echo.
"%PYTHON_EXE%" "%SCRIPT_PATH%"
goto AFTER_RUN

:RUN_JSON
echo.
echo List of available JSON content files:
set count=0
for /f "delims=" %%f in ('dir /b *_content.json') do (
    set /a count+=1
    set "file_!count!=%%f"
    echo  [!count!] %%f
)

if %count%==0 (
    echo [ERROR] No JSON content files found.
    pause
    goto MENU
)

echo.
set /p JSON_CHOICE="Select a file number (1-%count%): "

:: Validate input and get filename
set "SELECTED_FILE=!file_%JSON_CHOICE%!"

if "!SELECTED_FILE!"=="" (
    echo [ERROR] Invalid selection.
    pause
    goto RUN_JSON
)

echo [*] Selected: !SELECTED_FILE!
"%PYTHON_EXE%" "%SCRIPT_PATH%" "!SELECTED_FILE!"
goto AFTER_RUN

:AFTER_RUN
echo.
echo ============================================================
echo [DONE] Processing complete.
echo ============================================================
echo.
set /p CHOICE="Do you want to continue? (y/n): "

if /i "%CHOICE%"=="y" goto MENU

echo.
echo Thank you for using AI Slides Maker! Goodbye.
pause
