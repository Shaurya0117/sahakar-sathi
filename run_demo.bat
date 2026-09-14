@echo off
title Sahakar Sathi Demo Launcher
echo ===================================================
echo   Starting Sahakar Sathi Setup and Demo Launcher
echo ===================================================
echo.

:: 1. Setup Backend
echo [1/3] Checking Backend Python Environment...
cd backend

if not exist "venv\Scripts\activate.bat" (
    echo [SETUP] Virtual environment not found. Creating venv...
    python -m venv venv
    call venv\Scripts\activate.bat
    echo [SETUP] Installing backend dependencies...
    pip install -r requirements.txt
    if not exist "cooperative.db" (
        echo [SETUP] Seeding demo database...
        python scripts\seed_demo_data.py
    )
) else (
    call venv\Scripts\activate.bat
)

echo Starting Backend Server on port 8000...
start "Sahakar Sathi - Backend" cmd /k "venv\Scripts\activate && uvicorn app.main:app --port 8000"
cd ..

timeout /t 3 /nobreak >nul

:: 2. Setup Frontend
echo.
echo [2/3] Checking Frontend Dependencies...
cd frontend

if not exist "node_modules\" (
    echo [SETUP] Installing frontend node_modules (first-time only)...
    call npm install
)

echo Starting Frontend Server on port 5173...
start "Sahakar Sathi - Frontend" cmd /k "npm run dev -- --host 0.0.0.0 --port 5173"
cd ..

timeout /t 3 /nobreak >nul

:: 3. Open Browser
echo.
echo [3/3] Opening Web App in Browser...
start http://localhost:5173/login

echo.
echo ===================================================
echo   Demo is LIVE at http://localhost:5173
echo   (Keep the 2 command windows open during demo)
echo ===================================================
pause
