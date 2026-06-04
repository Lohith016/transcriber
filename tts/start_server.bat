@echo off
title VoxCast — TTS Server
echo.
echo  ╔══════════════════════════════════════════╗
echo  ║   VOXCAST — Starting TTS Server         ║
echo  ║   http://localhost:8000                 ║
echo  ╚══════════════════════════════════════════╝
echo.

if exist ".venv\Scripts\activate.bat" call .venv\Scripts\activate.bat

where uvicorn >nul 2>&1
if errorlevel 1 ( echo [ERROR] Run setup.bat first! & pause & exit /b 1 )

echo  [INFO] Server starting on http://localhost:8000
echo  [INFO] Open your browser and click "DOWNLOAD ^& LOAD MODEL"
echo  [INFO] Press Ctrl+C to stop
echo.
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
pause
