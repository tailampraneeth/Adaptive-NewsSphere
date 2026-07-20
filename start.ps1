# Adaptive NewsSphere - Full Stack Startup Script
# Run this from PowerShell: .\start.ps1

$Root = Split-Path -Parent $MyInvocation.MyCommand.Definition

Write-Host ""
Write-Host "=======================================================================" -ForegroundColor Cyan
Write-Host "          Adaptive NewsSphere - Full Stack Startup" -ForegroundColor Cyan
Write-Host "=======================================================================" -ForegroundColor Cyan
Write-Host ""

# ── Step 0: Copy .env if missing ──────────────────────────────────────────────
if (-not (Test-Path "$Root\.env")) {
    Write-Host "[INFO] .env not found. Copying from .env.example..." -ForegroundColor Yellow
    Copy-Item "$Root\.env.example" "$Root\.env"
}

# ── Step 1: Start Docker Compose ───────────────────────────────────────────────
Write-Host "[1/4] Starting Docker containers (PostgreSQL, Qdrant, Redis)..." -ForegroundColor Yellow
Set-Location $Root
docker compose up -d
if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERROR] Docker Compose failed. Is Docker Desktop running?" -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}
Write-Host "[OK] Docker containers are running." -ForegroundColor Green

# ── Step 2: Run Alembic Migrations ────────────────────────────────────────────
Write-Host ""
Write-Host "[2/4] Running database migrations..." -ForegroundColor Yellow
Set-Location "$Root\backend"
& "$Root\.venv\Scripts\alembic.exe" upgrade head
if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERROR] Alembic migrations failed." -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}
Write-Host "[OK] Database migrations applied." -ForegroundColor Green

# ── Step 3: Launch Backend in a new PowerShell window ─────────────────────────
Write-Host ""
Write-Host "[3/4] Launching FastAPI backend on http://localhost:8080 ..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList @(
    "-NoExit",
    "-Command",
    "Set-Location '$Root\backend'; Write-Host 'Starting FastAPI backend...' -ForegroundColor Cyan; & '$Root\.venv\Scripts\uvicorn.exe' app.main:app --reload --host 127.0.0.1 --port 8080"
)
Write-Host "[OK] Backend window opened. Waiting 5 seconds for server to boot..." -ForegroundColor Green
Start-Sleep -Seconds 5

# ── Step 4: Launch Frontend in a new PowerShell window ────────────────────────
Write-Host ""
Write-Host "[4/4] Launching Vite frontend on http://localhost:3000 ..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList @(
    "-NoExit",
    "-Command",
    "Set-Location '$Root\frontend'; Write-Host 'Installing npm packages...' -ForegroundColor Cyan; npm install; Write-Host 'Starting Vite dev server...' -ForegroundColor Cyan; npm run dev"
)
Write-Host "[OK] Frontend window opened." -ForegroundColor Green

# ── Done ──────────────────────────────────────────────────────────────────────
Write-Host ""
Write-Host "=======================================================================" -ForegroundColor Cyan
Write-Host "  All services are starting up!" -ForegroundColor Green
Write-Host ""
Write-Host "  Frontend  ->  http://localhost:3000" -ForegroundColor White
Write-Host "  Backend   ->  http://localhost:8080" -ForegroundColor White
Write-Host "  API Docs  ->  http://localhost:8080/docs" -ForegroundColor White
Write-Host ""
Write-Host "  Demo login credentials (password: password123):" -ForegroundColor White
Write-Host "    Cold user : cold@test.com" -ForegroundColor White
Write-Host "    Warm user : warm@test.com" -ForegroundColor White
Write-Host "=======================================================================" -ForegroundColor Cyan
Write-Host ""
