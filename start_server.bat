@echo off
title VoxStream — Transcription Server
echo.
echo  ╔══════════════════════════════════════════╗
echo  ║   VOXSTREAM  —  Starting Server         ║
echo  ╚══════════════════════════════════════════╝
echo.

:: Activate venv if it exists
if exist ".venv\Scripts\activate.bat" (
    echo  [INFO] Activating virtual environment…
    call .venv\Scripts\activate.bat
)

:: Check uvicorn
where uvicorn >nul 2>&1
if errorlevel 1 (
    echo  [INFO] Installing dependencies…
    pip install -r requirements.txt
)

echo  [INFO] Starting server on http://localhost:8000
echo  [INFO] Press Ctrl+C to stop
echo.
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
pause
