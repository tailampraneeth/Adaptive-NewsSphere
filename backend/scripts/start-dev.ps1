# Start Development Infrastructure Script for Windows 11
# Usage: .\scripts\start-dev.ps1

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "   ADAPTIVE NEWSSPHERE: DEVELOPMENT ENVIRONMENT STARTUP" -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

# 1. Check if Docker is installed and running
Write-Host "[1/5] Checking Docker Desktop status..." -ForegroundColor Yellow
$dockerCheck = Get-Command docker -ErrorAction SilentlyContinue
if (-not $dockerCheck) {
    Write-Error "Docker CLI command not found. Please install Docker Desktop."
    Exit 1
}

$dockerInfo = docker info 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "[!] Docker daemon is not running. Attempting to launch Docker Desktop..." -ForegroundColor Magenta
    Start-Process "C:\Program Files\Docker\Docker\Docker Desktop.exe" -ErrorAction SilentlyContinue
    
    # Wait and poll for Docker daemon startup (up to 60 seconds)
    $attempts = 0
    do {
        Start-Sleep -Seconds 3
        $dockerInfo = docker info 2>$null
        $attempts++
        Write-Host "Waiting for Docker daemon to initialize... ($($attempts*3)s)" -ForegroundColor Gray
    } while ($LASTEXITCODE -ne 0 -and $attempts -lt 20)

    if ($LASTEXITCODE -ne 0) {
        Write-Error "Failed to start Docker daemon. Please open Docker Desktop manually."
        Exit 1
    }
}
Write-Host "[OK] Docker Desktop is running." -ForegroundColor Green

# 2. Detect Port 5433 Conflict (Docker PostgreSQL Port)
Write-Host "[2/5] Detecting Port 5433 status..." -ForegroundColor Yellow
$portConn = Get-NetTCPConnection -LocalPort 5433 -ErrorAction SilentlyContinue
if ($portConn) {
    Write-Host "[WARNING] Port 5433 is currently occupied!" -ForegroundColor Red
    Write-Error "Cannot start Docker Postgres container while host port 5433 is busy. Exiting."
    Exit 1
}
Write-Host "[OK] Port 5433 is free. Proceeding to Docker Compose." -ForegroundColor Green

# 3. Start Docker Compose
Write-Host "[3/5] Starting backend services via Docker Compose..." -ForegroundColor Yellow
docker compose up -d
if ($LASTEXITCODE -ne 0) {
    Write-Error "Docker Compose failed to start services. Check logs."
    Exit 1
}

# 4. Wait for Health Checks
Write-Host "[4/5] Waiting for container health checks..." -ForegroundColor Yellow
$attempts = 0
$maxAttempts = 30
$allHealthy = $false

do {
    Start-Sleep -Seconds 2
    
    # Internal health checks for Postgres and Redis
    $postgresHealth = (docker inspect --format='{{.State.Health.Status}}' ans-postgres 2>$null)
    $redisHealth = (docker inspect --format='{{.State.Health.Status}}' ans-redis 2>$null)
    
    # External HTTP health check for Qdrant (since its container is distroless)
    $qdrantHealth = "starting"
    $qdrantState = (docker inspect --format='{{.State.Status}}' ans-qdrant 2>$null)
    if ($qdrantState -eq "running") {
        try {
            $response = Invoke-RestMethod -Uri "http://localhost:6333/readyz" -Method Get -TimeoutSec 2 2>$null
            if ($response -like "*ready*") {
                $qdrantHealth = "healthy"
            }
        } catch {
            $qdrantHealth = "starting"
        }
    } else {
        $qdrantHealth = "stopped"
    }
    
    Write-Host "Current Status -> Postgres: [$postgresHealth] | Redis: [$redisHealth] | Qdrant: [$qdrantHealth]" -ForegroundColor Gray
    
    if ($postgresHealth -eq "healthy" -and $redisHealth -eq "healthy" -and $qdrantHealth -eq "healthy") {
        $allHealthy = $true
    }
    
    $attempts++
} while (-not $allHealthy -and $attempts -lt $maxAttempts)

if (-not $allHealthy) {
    Write-Error "Services failed to reach healthy status within the timeout period."
    Exit 1
}
Write-Host "[OK] All backend services are healthy and operational!" -ForegroundColor Green

# 5. Run Database Migrations
Write-Host "[5/5] Executing Alembic database migrations..." -ForegroundColor Yellow
$origDir = Get-Location
Set-Location "$PSScriptRoot\.."

# Check if virtual environment is available in workspace root (..\.venv) or current backend folder (.\.venv)
if (Test-Path "..\.venv\Scripts\python.exe") {
    $env:PYTHONPATH = "."
    ..\.venv\Scripts\python -m alembic upgrade head
} elseif (Test-Path ".\.venv\Scripts\python.exe") {
    $env:PYTHONPATH = "."
    .\.venv\Scripts\python -m alembic upgrade head
} else {
    Write-Host "[!] Virtual environment not found at .\.venv or ..\.venv. Skipping migrations." -ForegroundColor Yellow
}
Set-Location $origDir

Write-Host "==========================================================" -ForegroundColor Green
Write-Host "   SETUP COMPLETE - ADAPTIVE NEWSSPHERE ONLINE" -ForegroundColor Green
Write-Host "==========================================================" -ForegroundColor Green
Write-Host "  FastAPI Endpoint : http://localhost:8000" -ForegroundColor Cyan
Write-Host "  PostgreSQL Host  : localhost:5433 (User: developer, DB: newssphere)" -ForegroundColor Cyan
Write-Host "  Redis Cache      : localhost:6379" -ForegroundColor Cyan
Write-Host "  Qdrant Search    : http://localhost:6333" -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Green
