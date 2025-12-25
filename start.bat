@echo off
title CORA-GO
cd /d "%~dp0"

echo ========================================
echo   CORA-GO - Mobile AI Assistant
echo   Unity Lab AI + AI-Ministries + TheREV
echo ========================================
echo.

echo [1] Interactive Mode
echo [2] Worker Mode
echo [3] Sentinel Mode
echo [4] System Status
echo [5] Launch Web (start local server)
echo [6] List Bots
echo [7] Exit
echo.

set /p choice="Select option: "

if "%choice%"=="1" py -3.12 cora_go.py
if "%choice%"=="2" py -3.12 cora_go.py -p worker
if "%choice%"=="3" py -3.12 cora_go.py --sentinel
if "%choice%"=="4" py -3.12 cora_go.py --status
if "%choice%"=="5" (
    echo Starting web server on http://localhost:8080
    cd web
    py -3.12 -m http.server 8080
)
if "%choice%"=="6" py -3.12 cora_go.py --bots
if "%choice%"=="7" exit

pause
