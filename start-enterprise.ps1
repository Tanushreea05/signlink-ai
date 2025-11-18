# SignLink AI - Enterprise Startup Script
# Starts the advanced enterprise version with all services

Write-Host "🚀 Starting SignLink AI Enterprise Platform..." -ForegroundColor Green
Write-Host "=================================================" -ForegroundColor Cyan

# Check if Python is available
if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Host "❌ Python not found. Please install Python 3.8+ first." -ForegroundColor Red
    exit 1
}

# Function to start service in background
function Start-Service {
    param($Name, $Path, $Command, $Port)
    
    Write-Host "🔧 Starting $Name..." -ForegroundColor Yellow
    
    # Check if port is already in use
    $portInUse = Get-NetTCPConnection -LocalPort $Port -ErrorAction SilentlyContinue
    if ($portInUse) {
        Write-Host "⚠️  Port $Port is already in use. Skipping $Name." -ForegroundColor Yellow
        return
    }
    
    # Start the service
    $processArgs = "-Command `"cd '$Path'; $Command`""
    Start-Process -FilePath "powershell" -ArgumentList $processArgs -WindowStyle Minimized
    Start-Sleep -Seconds 3
    
    # Verify service is running
    $serviceRunning = Get-NetTCPConnection -LocalPort $Port -ErrorAction SilentlyContinue
    if ($serviceRunning) {
        Write-Host "SUCCESS: $Name started successfully on port $Port" -ForegroundColor Green
    } else {
        Write-Host "ERROR: Failed to start $Name" -ForegroundColor Red
    }
}

# Create virtual environments if they don't exist
Write-Host "🔧 Setting up virtual environments..." -ForegroundColor Yellow

# Backend virtual environment
if (-not (Test-Path "backend\venv-advanced")) {
    Write-Host "Creating backend virtual environment..." -ForegroundColor Cyan
    Set-Location backend
    python -m venv venv-advanced
    .\venv-advanced\Scripts\activate
    pip install --upgrade pip
    pip install -r requirements-advanced.txt
    deactivate
    Set-Location ..
}

# ML virtual environment
if (-not (Test-Path "ml\venv-advanced")) {
    Write-Host "Creating ML virtual environment..." -ForegroundColor Cyan
    Set-Location ml
    python -m venv venv-advanced
    .\venv-advanced\Scripts\activate
    pip install --upgrade pip
    pip install -r requirements-advanced.txt
    deactivate
    Set-Location ..
}

Write-Host "✅ Virtual environments ready!" -ForegroundColor Green

# Start services
Write-Host "`n🚀 Starting Enterprise Services..." -ForegroundColor Green

# Start ML Server
Start-Service -Name "ML Server (Advanced)" -Path "$PWD\ml" -Command ".\venv-advanced\Scripts\python.exe advanced_server.py" -Port 8001

# Start Backend Server
Start-Service -Name "Backend (Advanced)" -Path "$PWD\backend" -Command ".\venv-advanced\Scripts\python.exe advanced_backend.py" -Port 8000

# Start Frontend Server
Start-Service -Name "Frontend (Advanced)" -Path "$PWD\advanced-frontend" -Command "python -m http.server 3000" -Port 3000

Write-Host "`n🎉 SignLink AI Enterprise Platform Started!" -ForegroundColor Green
Write-Host "=================================================" -ForegroundColor Cyan
Write-Host "🌐 Frontend (Advanced UI): http://localhost:3000" -ForegroundColor White
Write-Host "🔧 Backend API: http://localhost:8000" -ForegroundColor White
Write-Host "🧠 ML Server: http://localhost:8001" -ForegroundColor White
Write-Host "📊 Metrics: http://localhost:8000/metrics" -ForegroundColor White
Write-Host "📖 API Docs: http://localhost:8000/docs" -ForegroundColor White
Write-Host "`n🔥 Features:" -ForegroundColor Yellow
Write-Host "   • Multilingual ISL support (Indian English, Tamil)" -ForegroundColor White
Write-Host "   • Enterprise authentication & security" -ForegroundColor White
Write-Host "   • Real-time WebSocket communication" -ForegroundColor White
Write-Host "   • Advanced analytics & monitoring" -ForegroundColor White
Write-Host "   • Production-ready architecture" -ForegroundColor White
Write-Host "   • Comprehensive ISL vocabulary (50+ signs)" -ForegroundColor White

Write-Host "`n⚡ Quick Start:" -ForegroundColor Yellow
Write-Host "   1. Open http://localhost:3000 in your browser" -ForegroundColor White
Write-Host "   2. Register a new account" -ForegroundColor White
Write-Host "   3. Choose your preferred language (Indian English/Tamil)" -ForegroundColor White
Write-Host "   4. Click 'Test ML Server' to try ISL recognition" -ForegroundColor White
Write-Host "   5. Explore the vocabulary browser" -ForegroundColor White

Write-Host "`n🛑 To stop all services, close this window or press Ctrl+C" -ForegroundColor Red
Write-Host "=================================================" -ForegroundColor Cyan

# Keep script running
Write-Host "`nPress any key to stop all services..." -ForegroundColor Yellow
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")

# Cleanup (kill processes on ports)
Write-Host "`n🛑 Stopping services..." -ForegroundColor Red
Get-Process | Where-Object {$_.ProcessName -eq "python"} | Stop-Process -Force -ErrorAction SilentlyContinue
Write-Host "✅ All services stopped." -ForegroundColor Green
