# Clankerblox - AI Roblox Game Builder - Startup Script
Write-Host ""
Write-Host "  ========================================" -ForegroundColor Cyan
Write-Host "   🎮 CLANKERBLOX - AI Game Builder 🎮" -ForegroundColor Magenta
Write-Host "  ========================================" -ForegroundColor Cyan
Write-Host ""

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $root

# Install Python deps
Write-Host "[1/3] Installing Python dependencies..." -ForegroundColor Yellow
pip install -r backend\requirements.txt --quiet 2>$null
Write-Host "      Done!" -ForegroundColor Green

# Start backend in background
Write-Host "[2/3] Starting Backend API server..." -ForegroundColor Yellow
$backend = Start-Process -FilePath "python" -ArgumentList "-m", "backend.main" -WorkingDirectory $root -PassThru -NoNewWindow
Write-Host "      Backend PID: $($backend.Id)" -ForegroundColor Green
Start-Sleep -Seconds 3

# Start frontend
Write-Host "[3/3] Starting Frontend dashboard..." -ForegroundColor Yellow
Set-Location "$root\frontend"
npm run dev

# Cleanup on exit
Write-Host "`nShutting down backend..." -ForegroundColor Yellow
Stop-Process -Id $backend.Id -Force -ErrorAction SilentlyContinue
Write-Host "Done!" -ForegroundColor Green
