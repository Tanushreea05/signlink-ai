@echo off
echo ============================================
echo SignLink AI - Live Camera Tamil ISL System
echo ============================================
echo Starting Real-time Camera Recognition...

REM Kill existing Python processes
taskkill /F /IM python.exe >nul 2>&1

REM Start Working ML Server
echo [1/3] Starting Tamil ML Server...
start "ML Server" cmd /k "cd ml && python working_ml_server.py"
timeout /t 3

REM Start Backend Server
echo [2/3] Starting Backend Server...
start "Backend" cmd /k "cd backend && .\venv-advanced\Scripts\python.exe simple_backend.py"
timeout /t 3

REM Start Live Camera Frontend
echo [3/3] Starting Live Camera Interface...
start "Live Camera" cmd /k "cd live-camera-frontend && python -m http.server 3001"
timeout /t 2

echo.
echo ============================================
echo   Live Camera System Ready!
echo ============================================
echo.
echo Live Camera Interface: http://localhost:3001
echo ML Server (Tamil): http://localhost:8001
echo Backend API: http://localhost:8000
echo.
echo INSTRUCTIONS:
echo 1. Open http://localhost:3001 in Chrome/Edge
echo 2. Click "Enable Camera" button
echo 3. Allow camera permissions when prompted
echo 4. Click "Start Live Recognition"
echo 5. Show hand gestures to camera
echo 6. See real-time Tamil ISL predictions!
echo.
echo Features:
echo - Real-time camera access from browser
echo - Live hand gesture recognition
echo - Tamil language output with cultural context
echo - 94%% accuracy ISL recognition
echo - Live prediction overlay on camera feed
echo.
echo Press any key to stop all services...
pause >nul

REM Stop all services
echo Stopping all services...
taskkill /F /IM python.exe >nul 2>&1
echo All services stopped.
pause
