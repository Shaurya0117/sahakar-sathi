#!/bin/bash
# Sahakar Sathi - 1-Click Demo Launcher for macOS / Linux

echo "==================================================="
echo "  Starting Sahakar Sathi Demo for macOS"
echo "==================================================="
echo ""

# Trap to kill all background processes on exit (Ctrl+C)
trap "kill 0" EXIT

# 1. Setup & Start Backend
echo "[1/3] Setting up & starting Backend API (Port 8000)..."
cd backend || exit 1

if [ ! -f "venv/bin/activate" ]; then
    echo "Creating virtual environment for Mac..."
    rm -rf venv
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
    python scripts/seed_demo_data.py
else
    source venv/bin/activate
fi

# Ensure database is seeded
if [ ! -f "cooperative.db" ]; then
    echo "Seeding demo database..."
    python scripts/seed_demo_data.py
fi

uvicorn app.main:app --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!
cd ..

# 2. Setup & Start Frontend
echo "[2/3] Setting up & starting Frontend (Port 5173)..."
cd frontend || exit 1

if [ ! -d "node_modules" ]; then
    echo "Installing frontend packages..."
    npm install
fi

npm run dev -- --host 0.0.0.0 --port 5173 &
FRONTEND_PID=$!
cd ..

# 3. Open Web App
echo "[3/3] Opening browser..."
sleep 3
open "http://localhost:5173/login" 2>/dev/null || xdg-open "http://localhost:5173/login" 2>/dev/null || echo "Open http://localhost:5173/login in your browser"

echo ""
echo "==================================================="
echo "  Demo is LIVE at http://localhost:5173"
echo "  (Press Ctrl+C in this terminal when finished)"
echo "==================================================="
echo ""

wait
