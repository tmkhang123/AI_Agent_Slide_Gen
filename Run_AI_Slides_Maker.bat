@echo off
setlocal enabledelayedexpansion
title AI Slides Maker - 3 Agent Edition
color 0B

:: ============================================================
::  CAU HINH DUONG DAN  (sua PROJECT_DIR cho dung may cua ban)
:: ============================================================
set "PROJECT_DIR=C:\Users\longh\Desktop\AI_Slide_Agent_Maker"
set "PYTHON_EXE=%PROJECT_DIR%\.venv\Scripts\python.exe"
set "SCRIPT_PATH=%PROJECT_DIR%\main.py"
set "WATCHER_PATH=%PROJECT_DIR%\watcher.py"
set "PRODUCT_DIR=%PROJECT_DIR%\Product"

:: Kiem tra Python ton tai
if not exist "%PYTHON_EXE%" (
    echo [ERROR] Khong tim thay Python tai:
    echo    "%PYTHON_EXE%"
    echo Hay sua lai bien PROJECT_DIR o dau file .bat nay.
    pause
    exit /b
)

cd /d "%PROJECT_DIR%"

:MENU
cls
echo ============================================================
echo            AI SLIDES MAKER AGENT  (3-Agent)
echo ============================================================
echo.
echo  [1] Tao slide moi tu chu de
echo  [2] Tao lai slide tu file JSON da chinh
echo  [3] WATCH MODE (tu cap nhat slide khi JSON thay doi)
echo  [4] Thoat
echo.
set /p OPT="Chon mot tuy chon (1-4): "

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
echo.
echo Danh sach file noi dung JSON trong thu muc Product\:
set count=0
for /f "delims=" %%f in ('dir /b "%PRODUCT_DIR%\*_content.json" 2^>nul') do (
    set /a count+=1
    set "file_!count!=%%f"
    echo  [!count!] %%f
)

if %count%==0 (
    echo [ERROR] Khong tim thay file *_content.json trong Product\.
    pause
    goto MENU
)

echo.
set /p JSON_CHOICE="Chon so thu tu file (1-%count%): "

:: Lay ten file da chon
set "SELECTED_FILE=!file_%JSON_CHOICE%!"

if "!SELECTED_FILE!"=="" (
    echo [ERROR] Lua chon khong hop le.
    pause
    goto RUN_JSON
)

echo [*] Da chon: !SELECTED_FILE!
"%PYTHON_EXE%" "%SCRIPT_PATH%" "%PRODUCT_DIR%\!SELECTED_FILE!"
goto AFTER_RUN

:RUN_WATCH
echo.
echo [*] Bat dau WATCH MODE. Nhan Ctrl+C trong cua so nay de dung.
"%PYTHON_EXE%" "%WATCHER_PATH%"
pause
goto MENU

:AFTER_RUN
echo.
echo ============================================================
echo [DONE] Da xu ly xong.
echo ============================================================
echo.
set /p CHOICE="Ban co muon tiep tuc? (y/n): "

if /i "%CHOICE%"=="y" goto MENU

echo.
echo Cam on ban da su dung AI Slides Maker! Tam biet.
pause
