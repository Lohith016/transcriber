# VOXSTREAM — Real-Time Whisper Transcription

Local Whisper speech-to-text with a FastAPI WebSocket backend and a
dark single-page frontend. Switch models live from the browser without
restarting the server.

---

## Folder Structure

```
speech-transcriber/
├── main.py                ← FastAPI server + WhisperProvider
├── index.html             ← Single-page frontend (model switcher + transcript)
├── requirements.txt       ← Python dependencies
├── download_models.bat    ← Windows: interactive Whisper model downloader
├── start_server.bat       ← Windows: one-click server launcher
└── README.md
```

---

## Quick Start (Windows)

### Step 1 — Install Python 3.10+
Download from https://python.org — tick **"Add to PATH"** during install.

### Step 2 — Create virtual environment & install deps

```bat
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

Or just double-click `start_server.bat` — it does this automatically.

### Step 3 — Download Whisper models

Double-click **`download_models.bat`** and pick which models to download.

```
Available models:
  [1] tiny      ~75 MB    fastest, basic quality
  [2] base      ~142 MB   fast, decent quality
  [3] small     ~466 MB   balanced
  [4] medium    ~1.5 GB   great quality
  [5] large-v2  ~3.1 GB   excellent
  [6] large-v3  ~3.1 GB   best (recommended)
  [A] ALL       ~9 GB     download everything
```

Models are cached at `%USERPROFILE%\.cache\huggingface\hub` —
you only need to download once.

### Step 4 — Start the server

```bat
start_server.bat
```
or
```bat
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### Step 5 — Open the app

Navigate to **http://localhost:8000**

1. Click a model card to select it (e.g. `large-v3`)
2. Click **⬇ LOAD SELECTED MODEL** — the server loads it in the background
3. Wait for the status bar to show **✓ large-v3 ready**
4. Click **▶ START TRANSCRIBING** — allow microphone access
5. Speak — tokens appear in real time, updating interim → final

---

## How Model Switching Works

```
Browser                          Server
  │                                │
  │  POST /api/models/large-v3/load │
  ├────────────────────────────────►│  WhisperProvider.load_model()
  │                                 │  └─ thread: WhisperModel('large-v3')
  │  GET /api/models (poll 1.2s)    │     (downloads if not cached)
  ├────────────────────────────────►│
  │◄── { loading: true }  ──────────┤
  │  ... (polls until ready) ...    │
  │◄── { loaded_model: "large-v3" } ┤  model ready
  │  UI enables START button        │
```

You can switch models between sessions. While recording, the current
model keeps processing. After stopping, selecting and loading a new
model takes effect for the next session.

---

## Audio Pipeline

```
Mic → getUserMedia (16kHz mono)
  └─ ScriptProcessorNode (960 samples = 60 ms)
      └─ Float32 → Int16
          └─ WebSocket.send(ArrayBuffer)
              └─ FastAPI /ws/transcribe
                  └─ Per-session rolling buffer (up to 30 s)
                      └─ faster-whisper (runs every 3 s of audio)
                          └─ Word-level timestamps → Token objects
                              └─ WebSocket.send(JSON)
                                  └─ DOM token renderer
```

**Why 3-second chunks?**
Whisper is a sequence-to-sequence model — it needs a full audio window
to produce accurate results. The server accumulates 3 seconds, then runs
inference, giving you a good balance of latency vs accuracy. Tokens from
the previous window are marked `is_final=true`; the newest window emits
`is_final=false` (interim) tokens that update as more audio arrives.

---

## GPU Acceleration

If you have an NVIDIA GPU:

```bat
pip install torch --index-url https://download.pytorch.org/whl/cu121
```

Then install cuDNN (faster-whisper will auto-detect CUDA at startup
and switch to `float16` compute, giving ~5-10x speed-up over CPU).

---

## Adding a Real Language Filter

By default Whisper auto-detects the language. To force a specific language,
edit `main.py` in `_run_whisper`:

```python
segments, info = model.transcribe(
    audio,
    language="en",   # force English (or "hi", "ta", "fr", etc.)
    ...
)
```
