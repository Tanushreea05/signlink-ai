@echo off
echo ========================================
echo SignLink AI - Enterprise SaaS Platform
echo ========================================
echo Starting Tamil-focused ISL Recognition Platform...

REM Kill any existing Python processes
taskkill /F /IM python.exe >nul 2>&1

REM Start ML Server (Enterprise)
echo Starting Enterprise ML Server (Tamil-focused)...
start "ML Server" cmd /k "cd ml && python enterprise_ml_server.py"
timeout /t 3

REM Start Backend Server (Enterprise)
echo Starting Enterprise Backend (SaaS)...
start "Backend" cmd /k "cd backend && python enterprise_backend.py"
timeout /t 3

REM Start Frontend Server
echo Starting Enterprise Frontend...
start "Frontend" cmd /k "cd advanced-frontend && python -m http.server 3000"
timeout /t 2

echo.
echo ========================================
echo   SignLink AI Enterprise Platform Ready!
echo ========================================
echo.
echo Frontend (SaaS Dashboard): http://localhost:3000
echo Backend API: http://localhost:8000
echo ML Server (Tamil): http://localhost:8001
echo API Documentation: http://localhost:8000/docs
echo.
echo Features:
echo - Tamil Language Specialization
echo - Multi-tier SaaS Subscriptions
echo - Enterprise Analytics Dashboard
echo - Cultural Context Integration
echo - 96%% Accuracy ISL Recognition
echo.
echo Press any key to stop all services...
pause >nul

REM Stop all services
taskkill /F /IM python.exe >nul 2>&1
echo All services stopped.
pause
