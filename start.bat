@echo off
title CORA-GO
cd /d "%~dp0"

echo ========================================
echo   CORA-GO - Mobile AI Assistant
echo   Unity Lab AI + AI-Ministries + TheREV
echo ========================================
echo.
echo   INTERFACES:
echo   [1] LOCAL GUI   - Tkinter app (full window, waveform, stats)
echo   [2] LOCAL WEB   - Browser interface (mobile-style tabs)
echo   [3] LOCAL CLI   - Text mode in terminal
echo.
echo   TOOLS:
echo   [4] System Status
echo   [5] List Bots
echo   [6] Sentinel Mode (audio monitoring)
echo.
echo   [0] Exit
echo.

set /p choice="Select option: "

if "%choice%"=="1" py -3.12 anchor\main.py
if "%choice%"=="2" (
    echo Starting web server on http://localhost:8080
    echo Opening browser...
    start "" http://localhost:8080
    pushd web
    py -3.12 -m http.server 8080
    popd
)
if "%choice%"=="3" py -3.12 cora_go.py
if "%choice%"=="4" py -3.12 cora_go.py --status
if "%choice%"=="5" py -3.12 cora_go.py --bots
if "%choice%"=="6" py -3.12 cora_go.py --sentinel
if "%choice%"=="0" exit

pause
