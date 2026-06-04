@echo off
setlocal enabledelayedexpansion
title VoxCast — Setup

echo.
echo  =====================================================
echo    VOXCAST -- TTS Setup for Windows
echo    Kokoro-82M  RTX GPU  CUDA 12.1
echo  =====================================================
echo.

:: ── Check Python ──────────────────────────────────────
where python >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found. Install from https://python.org
    goto :FAIL
)
for /f "tokens=*" %%v in ('python --version 2^>^&1') do echo [OK] %%v

:: ── Create venv ───────────────────────────────────────
if not exist ".venv" (
    echo [INFO] Creating virtual environment...
    python -m venv .venv
)
echo [INFO] Activating virtual environment...
call .venv\Scripts\activate.bat

:: ── Upgrade pip ───────────────────────────────────────
echo [INFO] Upgrading pip...
python -m pip install --upgrade pip --quiet
echo [OK] pip upgraded

:: ── Check eSpeak-NG ───────────────────────────────────
echo.
echo [INFO] Checking eSpeak-NG...
set "ESPEAK_EXE=C:\Program Files\eSpeak NG\espeak-ng.exe"
if exist "!ESPEAK_EXE!" (
    echo [OK] eSpeak-NG found
) else (
    echo.
    echo [WARN] eSpeak-NG NOT found at default path.
    echo        Kokoro needs it for text-to-phoneme conversion.
    echo.
    echo        Download installer from:
    echo        https://github.com/espeak-ng/espeak-ng/releases
    echo        Install to: C:\Program Files\eSpeak NG\
    echo.
    echo        You can continue setup now and install eSpeak-NG later,
    echo        but Kokoro will fail to run without it.
    echo.
    pause
)

:: ── Install PyTorch 2.5 CUDA 12.1 ─────────────────────
echo.
echo [INFO] Installing PyTorch 2.5.1 with CUDA 12.1...
echo [INFO] This downloads ~2.5 GB -- please wait...
echo.
pip install torch==2.5.1+cu121 torchvision==0.20.1+cu121 torchaudio==2.5.1+cu121 --index-url https://download.pytorch.org/whl/cu121
echo [OK] PyTorch install command finished

:: ── Verify torch ──────────────────────────────────────
echo.
echo [INFO] Verifying PyTorch...
python -c "import torch; print('[OK] PyTorch', torch.__version__); print('[OK] CUDA:', torch.cuda.is_available()); print('[OK] GPU:', torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'None (CPU mode)')"
if errorlevel 1 (
    echo [ERROR] PyTorch import failed. Trying CPU-only fallback...
    pip install torch torchvision torchaudio
    python -c "import torch; print('[OK] PyTorch CPU', torch.__version__)"
    if errorlevel 1 goto :FAIL
)

:: ── Install transformers pinned to 4.x ────────────────
echo.
echo [INFO] Installing transformers 4.x (pinned -- do not upgrade to 5.x)...
pip install "transformers>=4.41.0,<5.0.0"
echo [OK] transformers installed

:: ── Install remaining dependencies ────────────────────
echo.
echo [INFO] Installing FastAPI, Kokoro, uvicorn, audio libs...
pip install "fastapi>=0.110.0" "uvicorn[standard]>=0.29.0" websockets "kokoro>=0.9.4" soundfile "numpy>=1.26.0"
echo [OK] Dependencies installed

:: ── Verify Kokoro ─────────────────────────────────────
echo.
echo [INFO] Verifying Kokoro import...
python -c "from kokoro import KPipeline; print('[OK] Kokoro import successful')"
if errorlevel 1 (
    echo.
    echo [WARN] Kokoro import failed. Trying transformers downgrade to 4.44.2...
    pip install "transformers==4.44.2"
    python -c "from kokoro import KPipeline; print('[OK] Kokoro import successful after fix')"
    if errorlevel 1 (
        echo.
        echo [ERROR] Kokoro still failing. Common causes:
        echo         1. eSpeak-NG not installed -- see above
        echo         2. Wrong transformers version -- try manually:
        echo            pip install transformers==4.44.2
        goto :FAIL
    )
)

:: ── Final summary ─────────────────────────────────────
echo.
echo [INFO] Full environment summary:
python -c "
import torch, transformers
print(f'  PyTorch     : {torch.__version__}')
print(f'  CUDA        : {torch.cuda.is_available()}')
print(f'  GPU         : {torch.cuda.get_device_name(0) if torch.cuda.is_available() else \"CPU only\"}')
if torch.cuda.is_available():
    gb = torch.cuda.get_device_properties(0).total_memory / 1024**3
    print(f'  VRAM        : {gb:.1f} GB')
print(f'  transformers: {transformers.__version__}')
"

echo.
echo  =====================================================
echo    Setup complete!
echo    Run start_server.bat to launch VoxCast.
echo    Then open http://localhost:8000
echo  =====================================================
echo.
pause
exit /b 0

:FAIL
echo.
echo [ERROR] Setup did not complete. See messages above.
echo         Close this window, fix the issue, and run setup.bat again.
echo.
pause
exit /b 1