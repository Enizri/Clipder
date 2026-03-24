@echo off
echo ====================================
echo   Clipder Pro - FastAPI + React
echo ====================================
echo.

:: Start Backend in new window
echo Starting Backend (FastAPI on port 8000)...
start "Clipder Backend" cmd /k "cd /d %~dp0 && uv run uvicorn main:app --reload --host 0.0.0.0 --port 8000"

:: Wait a bit for backend
timeout /t 3 /nobreak >nul

:: Start Frontend
echo Starting Frontend (React on port 3000)...
cd /d %~dp0\frontend
start "Clipder Frontend" cmd /k "npm run dev"

echo.
echo ====================================
echo   Servers Starting...
echo   Backend: http://localhost:8000
echo   Frontend: http://localhost:3000
echo ====================================
