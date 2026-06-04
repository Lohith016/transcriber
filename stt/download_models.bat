@echo off
setlocal enabledelayedexpansion
title VoxStream — Whisper Model Downloader

:: ════════════════════════════════════════════════════════════════
::  VOXSTREAM — Whisper Model Downloader
::  Downloads all OpenAI Whisper models via faster-whisper
::  (which caches them in %USERPROFILE%\.cache\huggingface\hub)
::
::  Usage:
::    download_models.bat              — interactive menu
::    download_models.bat all          — download all models
::    download_models.bat tiny base    — download specific models
:: ════════════════════════════════════════════════════════════════

echo.
echo  ╔══════════════════════════════════════════════════════╗
echo  ║       VOXSTREAM  —  Whisper Model Downloader        ║
echo  ║       Uses faster-whisper ^(CTranslate2^)            ║
echo  ╚══════════════════════════════════════════════════════╝
echo.

:: ── Check Python ────────────────────────────────────────────────
where python >nul 2>&1
if errorlevel 1 (
    echo  [ERROR] Python not found. Install from https://python.org
    pause & exit /b 1
)
for /f "tokens=*" %%v in ('python --version 2^>^&1') do set PY_VER=%%v
echo  [OK] %PY_VER% found

:: ── Check / install faster-whisper ──────────────────────────────
echo.
echo  [INFO] Checking faster-whisper installation…
python -c "import faster_whisper" >nul 2>&1
if errorlevel 1 (
    echo  [INFO] Installing faster-whisper…
    pip install faster-whisper numpy --quiet
    if errorlevel 1 (
        echo  [ERROR] pip install failed. Run: pip install faster-whisper
        pause & exit /b 1
    )
    echo  [OK] faster-whisper installed
) else (
    echo  [OK] faster-whisper already installed
)

:: ── Model definitions ────────────────────────────────────────────
set "MODELS=tiny base small medium large-v2 large-v3"
set "SIZE_tiny=75 MB"
set "SIZE_base=142 MB"
set "SIZE_small=466 MB"
set "SIZE_medium=1.5 GB"
set "SIZE_large-v2=3.1 GB"
set "SIZE_large-v3=3.1 GB"

:: ── Parse command-line args ──────────────────────────────────────
if "%~1"=="" goto :MENU
if /i "%~1"=="all" goto :DOWNLOAD_ALL

:: Specific models from args
set "TO_DOWNLOAD="
:PARSE_ARGS
if "%~1"=="" goto :DO_DOWNLOAD
set "MODEL=%~1"
:: Validate
set "VALID=0"
for %%m in (%MODELS%) do if /i "%%m"=="%MODEL%" set "VALID=1"
if "!VALID!"=="0" (
    echo  [WARN] Unknown model '%MODEL%', skipping
) else (
    set "TO_DOWNLOAD=!TO_DOWNLOAD! %MODEL%"
)
shift
goto :PARSE_ARGS

:DO_DOWNLOAD
if "!TO_DOWNLOAD!"=="" ( echo  [ERROR] No valid models specified. & pause & exit /b 1 )
goto :RUN_DOWNLOADS

:: ── Interactive menu ─────────────────────────────────────────────
:MENU
echo  Available Whisper models:
echo.
echo    [1] tiny      — ~75 MB   — ~32x real-time   — basic quality
echo    [2] base      — ~142 MB  — ~16x real-time   — decent quality
echo    [3] small     — ~466 MB  — ~6x real-time    — good quality
echo    [4] medium    — ~1.5 GB  — ~2x real-time    — great quality
echo    [5] large-v2  — ~3.1 GB  — ~1x real-time    — excellent quality
echo    [6] large-v3  — ~3.1 GB  — ~1x real-time    — best quality ^(recommended^)
echo    [A] ALL       — Download all models ^(~9 GB total^)
echo    [Q] Quit
echo.
set /p CHOICE="  Enter choice (e.g. 6 or 1 3 6 or A): "

if /i "!CHOICE!"=="Q" exit /b 0
if /i "!CHOICE!"=="A" goto :DOWNLOAD_ALL

set "TO_DOWNLOAD="
for %%c in (!CHOICE!) do (
    if "%%c"=="1" set "TO_DOWNLOAD=!TO_DOWNLOAD! tiny"
    if "%%c"=="2" set "TO_DOWNLOAD=!TO_DOWNLOAD! base"
    if "%%c"=="3" set "TO_DOWNLOAD=!TO_DOWNLOAD! small"
    if "%%c"=="4" set "TO_DOWNLOAD=!TO_DOWNLOAD! medium"
    if "%%c"=="5" set "TO_DOWNLOAD=!TO_DOWNLOAD! large-v2"
    if "%%c"=="6" set "TO_DOWNLOAD=!TO_DOWNLOAD! large-v3"
)
if "!TO_DOWNLOAD!"=="" ( echo  [WARN] No valid selection. & goto :MENU )
goto :RUN_DOWNLOADS

:DOWNLOAD_ALL
set "TO_DOWNLOAD=%MODELS%"
goto :RUN_DOWNLOADS

:: ── Download loop ─────────────────────────────────────────────────
:RUN_DOWNLOADS
echo.
echo  ════════════════════════════════════════════════════════
echo   Downloading:!TO_DOWNLOAD!
echo  ════════════════════════════════════════════════════════
echo.

set "PASS=0"
set "FAIL=0"

for %%m in (!TO_DOWNLOAD!) do (
    echo.
    echo  ┌─────────────────────────────────────────────────────┐
    echo  │  Model : %%m
    echo  │  Size  : !SIZE_%%m!
    echo  └─────────────────────────────────────────────────────┘

    :: Run a Python snippet that loads the model (triggers HF download)
    python -c "
import sys
print(f'  [INFO] Downloading %%m from Hugging Face...')
try:
    from faster_whisper import WhisperModel
    # Download-only: load on CPU with int8 to minimise RAM
    model = WhisperModel('%%m', device='cpu', compute_type='int8', download_root=None)
    print('  [OK] %%m downloaded and cached successfully')
    del model
except Exception as e:
    print(f'  [ERROR] Failed: {e}', file=sys.stderr)
    sys.exit(1)
"
    if errorlevel 1 (
        echo  [FAIL] %%m download failed
        set /a FAIL+=1
    ) else (
        set /a PASS+=1
    )
)

:: ── Summary ─────────────────────────────────────────────────────
echo.
echo  ════════════════════════════════════════════════════════
echo   Download complete — !PASS! succeeded, !FAIL! failed
echo.
echo   Models are cached at:
echo     %%USERPROFILE%%\.cache\huggingface\hub
echo.
echo   Start the server with:
echo     uvicorn main:app --host 0.0.0.0 --port 8000 --reload
echo  ════════════════════════════════════════════════════════
echo.

pause
exit /b 0
