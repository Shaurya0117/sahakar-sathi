@echo off
title Sahakar Sathi Demo Launcher
echo ===================================================
echo   Starting Sahakar Sathi - Presentation Demo
echo ===================================================
echo.

echo [1/3] Starting Backend API Server (Port 8000)...
start "Sahakar Sathi - Backend" cmd /k "cd backend && venv\Scripts\activate && uvicorn app.main:app --port 8000"

timeout /t 4 /nobreak >nul

echo [2/3] Starting Frontend Dev Server (Port 5173)...
start "Sahakar Sathi - Frontend" cmd /k "cd frontend && npm run dev -- --host 127.0.0.1 --port 5173"

timeout /t 4 /nobreak >nul

echo [3/3] Opening Web App in Browser...
start http://localhost:5173/login

echo.
echo ===================================================
echo   Demo is LIVE at http://localhost:5173
echo   (Keep the 2 command windows open during presentation)
echo ===================================================
pause
