# Stop Development Infrastructure Script for Windows 11
# Usage: .\scripts\stop-dev.ps1

Write-Host "==========================================================" -ForegroundColor Yellow
Write-Host "   Stopping Adaptive NewsSphere Infrastructure..." -ForegroundColor Yellow
Write-Host "==========================================================" -ForegroundColor Yellow

docker compose down

if ($LASTEXITCODE -eq 0) {
    Write-Host "[OK] All backend containers stopped gracefully and network deleted." -ForegroundColor Green
} else {
    Write-Warning "Docker Compose failed to stop containers cleanly."
}
