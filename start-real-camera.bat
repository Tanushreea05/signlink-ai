@echo off
echo ================================================
echo SignLink AI - Real Camera MediaPipe Tamil ISL
echo ================================================
echo Starting Real-time Hand Gesture Recognition...

REM Kill existing processes
taskkill /F /IM python.exe >nul 2>&1

REM Start Tamil ML Server
echo [1/3] Starting Tamil ML Server with Real Camera Support...
start "Tamil ML Server" cmd /k "cd ml && python working_ml_server.py"
timeout /t 3

REM Start Backend Server
echo [2/3] Starting Backend Server...
start "Backend Server" cmd /k "cd backend && .\venv-advanced\Scripts\python.exe simple_backend.py"
timeout /t 3

REM Start Enhanced Frontend with MediaPipe
echo [3/3] Starting MediaPipe Camera Frontend...
start "MediaPipe Frontend" cmd /k "cd advanced-frontend && python -m http.server 3000"
timeout /t 2

echo.
echo ================================================
echo   Real Camera System Ready!
echo ================================================
echo.
echo MediaPipe Camera Interface: http://localhost:3000
echo Tamil ML Server: http://localhost:8001
echo Backend API: http://localhost:8000
echo.
echo REAL-TIME FEATURES:
echo ✓ MediaPipe Hand Detection
echo ✓ Live Camera Feed
echo ✓ Real-time Tamil ISL Recognition
echo ✓ Hand Landmark Visualization
echo ✓ Live Prediction Overlays
echo ✓ Cultural Context Display
echo.
echo HOW TO USE:
echo 1. Open http://localhost:3000 in Chrome/Edge
echo 2. Click "Start Camera" button
echo 3. Allow camera permissions
echo 4. See real-time hand detection with green lines
echo 5. Hand gestures automatically recognized
echo 6. Tamil predictions appear on screen
echo.
echo TAMIL SIGNS SUPPORTED:
echo - வணக்கம் (VANAKKAM) - Traditional greeting
echo - அம்மா (AMMA) - Mother
echo - அப்பா (APPA) - Father  
echo - தண்ணீர் (THANNI) - Water
echo - சாப்பாடு (SAAPADU) - Food
echo - சந்தோஷம் (SANDOSHAM) - Happiness
echo - நன்றி (NANDRI) - Thank you
echo.
echo Press any key to stop all services...
pause >nul

REM Stop all services
echo Stopping all services...
taskkill /F /IM python.exe >nul 2>&1
echo All services stopped.
pause
