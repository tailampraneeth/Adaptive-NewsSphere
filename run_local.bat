@echo off
echo =======================================================================
echo               Adaptive NewsSphere - Local Startup Helper
echo =======================================================================
echo.
echo [1/4] Checking Docker containers status...
docker compose up -d
if %errorlevel% neq 0 (
    echo.
    echo [WARNING] Docker Daemon is not running or Docker Desktop is closed.
    echo Please start Docker Desktop and ensure it is fully running to connect to
    echo PostgreSQL, Redis, and Qdrant.
    echo.
    pause
    exit /b %errorlevel%
)

echo.
echo [2/4] Running Alembic database migrations...
cd backend
call ..\.venv\Scripts\alembic upgrade head
if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Alembic migrations failed. Check database logs.
    cd ..
    pause
    exit /b %errorlevel%
)

echo.
echo [3/4] Launching FastAPI backend server in background...
start cmd /k "title FastAPI Backend && cd .. && .venv\Scripts\python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8080"

echo.
echo [4/4] Starting Vite frontend server...
cd ../frontend
echo Installing Node modules...
call npm install
echo Booting dev server...
call npm run dev

cd ..
