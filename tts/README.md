# VOXCAST — Real-Time Text-to-Speech

> Local GPU-accelerated TTS powered by **Kokoro-82M** · Word-by-word token streaming · 54 emotional voices · RTX 4060 optimized

---

## What This Is

VoxCast is a self-hosted, real-time text-to-speech web application that runs entirely on your local machine. Type any text, pick a voice, hit **SPEAK** — and watch each word light up on screen exactly as it is spoken, in sync with the audio.

No API keys. No per-character billing. No internet required after the one-time model download.

---

## Features

| Feature | Detail |
|---|---|
| **Engine** | Kokoro-82M (StyleTTS2 architecture, Apache 2.0) |
| **GPU** | RTX 4060 / any CUDA GPU — fp16, ~96× real-time |
| **Voices** | 54 expressive voices — US English, British English, male & female |
| **Streaming** | Word-by-word token highlight synced to audio playback |
| **Download UI** | Live progress bar during model download inside the browser |
| **Voice picker** | Filter by accent, gender, quality stars |
| **Speed control** | 0.5× to 2.0× |
| **GPU stats** | Live VRAM used / free / total display |
| **Presets** | 4 built-in sample texts to test voices quickly |
| **Zero cost** | Runs 100% locally after setup |

---

## Folder Structure

```
tts-app/
├── main.py            ← FastAPI server: Kokoro engine, WebSocket, SSE progress
├── index.html         ← Single-page frontend (dark UI, voice picker, transcript)
├── requirements.txt   ← Python dependencies
├── setup.bat          ← One-click Windows setup (PyTorch CUDA + all deps)
├── start_server.bat   ← One-click server launcher
└── README.md
```

---

## System Requirements

| Component | Minimum | Recommended |
|---|---|---|
| OS | Windows 10 64-bit | Windows 11 |
| Python | 3.10 | 3.11 or 3.12 |
| GPU | Any NVIDIA (CUDA 11.8+) | RTX 4060 8 GB |
| RAM | 8 GB | 16 GB |
| Disk | 1 GB free | 2 GB free |
| CUDA Toolkit | 11.8 | 12.1 |
| eSpeak-NG | Required | Required |

> **CPU fallback:** Kokoro works on CPU too — just slower (~4× real-time vs ~96× on RTX 4060).

---

## Quick Start

### Step 1 — Install eSpeak-NG

Kokoro uses eSpeak-NG for text-to-phoneme conversion. This must be installed **before** running setup.

1. Go to: https://github.com/espeak-ng/espeak-ng/releases
2. Download the latest `.msi` installer (e.g. `espeak-ng-X.XX-x64.msi`)
3. Run the installer — use the **default path**: `C:\Program Files\eSpeak NG\`
4. Verify it works — open a new Command Prompt and type:
   ```
   espeak-ng --version
   ```
   You should see a version number, not an error.

### Step 2 — Run Setup

Double-click **`setup.bat`** — it will:

- Create a Python virtual environment (`.venv`)
- Detect your CUDA version
- Install PyTorch with CUDA 12.1 support (correct for RTX 4060)
- Install FastAPI, Kokoro, uvicorn, soundfile, numpy
- Verify the GPU is detected and Kokoro imports cleanly

The setup output will show something like:
```
[OK] PyTorch 2.x.x+cu121
[OK] CUDA available: True
[OK] GPU: NVIDIA GeForce RTX 4060
[OK] Kokoro import successful
```

### Step 3 — Start the Server

Double-click **`start_server.bat`**

```
[INFO] Server starting on http://localhost:8000
```

### Step 4 — Open the App

Navigate to **http://localhost:8000** in Chrome or Edge.

### Step 5 — Load the Model

Click **⬇ DOWNLOAD & LOAD MODEL** in the sidebar.

- A progress bar shows download + GPU initialisation live
- The Kokoro model (~330 MB) is downloaded from Hugging Face on first run
- On subsequent runs it loads from cache — no re-download needed
- When the status shows **GPU READY · CUDA**, the model is live on your RTX 4060

### Step 6 — Speak

1. Pick a voice from the voice grid (filter by accent, gender, or stars)
2. Adjust speed (0.5× to 2.0×)
3. Type or paste text — or click a preset chip
4. Click **▶ SPEAK**

Each word glows as it is spoken. Hover any word to see its position index.

---

## Manual Setup (without setup.bat)

If you prefer to run commands yourself:

```bat
:: 1. Create and activate virtual environment
python -m venv .venv
.venv\Scripts\activate

:: 2. Install PyTorch with CUDA 12.1 (RTX 4060)
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121

:: 3. Install remaining dependencies
pip install fastapi "uvicorn[standard]" websockets kokoro>=0.9.4 soundfile numpy

:: 4. Start server
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

---

## Voices Reference

VoxCast includes 28 voices across US English and British English. A selection of the top-rated ones:

### American English — Female
| Voice ID | Name | Style | Stars |
|---|---|---|---|
| `af_heart` | Heart | Warm, expressive | ★★★★★ |
| `af_bella` | Bella | Smooth, confident | ★★★★★ |
| `af_nicole` | Nicole | Whispery, intimate | ★★★★ |
| `af_nova` | Nova | Energetic, dynamic | ★★★★ |
| `af_sarah` | Sarah | Natural, friendly | ★★★★ |

### American English — Male
| Voice ID | Name | Style | Stars |
|---|---|---|---|
| `am_adam` | Adam | Deep, authoritative | ★★★★★ |
| `am_michael` | Michael | Rich, storytelling | ★★★★★ |
| `am_echo` | Echo | Resonant, clear | ★★★★ |
| `am_fenrir` | Fenrir | Bold, dramatic | ★★★★ |
| `am_onyx` | Onyx | Smooth, polished | ★★★★ |

### British English — Female
| Voice ID | Name | Style | Stars |
|---|---|---|---|
| `bf_emma` | Emma | Elegant, precise | ★★★★★ |
| `bf_isabella` | Isabella | Refined, warm | ★★★★ |
| `bf_alice` | Alice | Crisp, articulate | ★★★★ |

### British English — Male
| Voice ID | Name | Style | Stars |
|---|---|---|---|
| `bm_george` | George | Distinguished, deep | ★★★★★ |
| `bm_lewis` | Lewis | Conversational, warm | ★★★★ |
| `bm_daniel` | Daniel | Smooth, professional | ★★★★ |

---

## Architecture

### Audio Pipeline

```
Browser
  └─ User types text → clicks SPEAK
      └─ WebSocket sends { text, voice, speed }
          └─ FastAPI /ws/tts
              └─ _synthesise_blocking() runs in thread pool
                  └─ KPipeline(lang_code='a', device='cuda')
                      └─ yields (graphemes, phonemes, audio_np) per sentence
                          ├─ graphemes → word tokens with t_ms timestamps
                          │   └─ WS sends { type:"token", word, index, t_ms }
                          └─ audio_np → base64 PCM float32
                              └─ WS sends { type:"audio", b64, duration_ms }
                                  └─ Browser: AudioContext gapless buffer queue
                                      └─ setTimeout per word → DOM highlight
```

### GPU Optimization

- Model loaded once at startup, stays resident in VRAM
- Cast to **fp16** after load (`pipe.model.half().cuda()`) — halves VRAM use, doubles throughput
- **Warm-up pass** on load compiles CUDA kernels so first synthesis has no JIT delay
- Thread pool executor keeps the FastAPI event loop non-blocking during inference
- RTX 4060 8 GB VRAM comfortably fits Kokoro (uses ~1.5–2 GB) with room to spare

### Word Timing

Kokoro's generator yields one audio chunk per sentence. Word timing is derived by distributing the chunk duration proportionally across the grapheme words in that chunk. This gives accurate-enough synchronization for real-time word highlighting without requiring a forced alignment model.

### SSE Progress Stream

Model download and initialisation progress is streamed to the browser via Server-Sent Events (`/api/progress`). The progress bar updates live at each stage:

```
5%   Checking CUDA
15%  Importing Kokoro
20%  Downloading model weights  (Hugging Face Hub)
70%  Initialising pipeline on GPU
90%  Warm-up inference pass
100% Ready
```

---

## API Reference

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/` | Serves the frontend HTML |
| `GET` | `/api/status` | Model state, GPU info, voice list |
| `POST` | `/api/load` | Trigger background model download + load |
| `GET` | `/api/progress` | SSE stream of load progress `{pct, msg}` |
| `GET` | `/api/voices` | Full voice catalogue with metadata |
| `WS` | `/ws/tts` | Real-time TTS synthesis stream |

### WebSocket Message Format

**Client → Server:**
```json
{
  "text":  "The text you want spoken.",
  "voice": "af_heart",
  "speed": 1.0
}
```

**Server → Client (stream):**
```json
{ "type": "token", "word": "The",  "index": 0, "t_ms": 0,   "total": 6 }
{ "type": "token", "word": "text", "index": 1, "t_ms": 140, "total": 6 }
{ "type": "audio", "b64": "<base64 PCM float32>", "sample_rate": 24000, "duration_ms": 840 }
{ "type": "done" }
```

---

## Troubleshooting

### `ModuleNotFoundError: No module named 'kokoro'`
Run setup.bat again with the virtual environment activated, or:
```bat
.venv\Scripts\activate
pip install kokoro>=0.9.4
```

### `espeak-ng not found` / phonemizer error
eSpeak-NG is not installed or not in PATH.
1. Install from https://github.com/espeak-ng/espeak-ng/releases
2. Restart your terminal after installing
3. Verify with `espeak-ng --version`

### `CUDA available: False` after GPU install
1. Check CUDA version: `nvcc --version`
2. Reinstall PyTorch matching your CUDA version:
   - CUDA 11.8: `pip install torch --index-url https://download.pytorch.org/whl/cu118`
   - CUDA 12.1: `pip install torch --index-url https://download.pytorch.org/whl/cu121`
   - CUDA 12.4: `pip install torch --index-url https://download.pytorch.org/whl/cu124`

### `UnicodeDecodeError` on server start
The `open()` call in `main.py` already uses `encoding="utf-8"` — if you see this error, ensure you saved `index.html` as UTF-8 in your editor.

### Audio plays but words don't highlight
The AudioContext may be suspended (browser autoplay policy). Click anywhere on the page before hitting SPEAK to unblock it.

### Port 8000 already in use
```bat
uvicorn main:app --host 0.0.0.0 --port 8001 --reload
```
Then open http://localhost:8001

---

## License

| Component | License |
|---|---|
| Kokoro-82M model weights | Apache 2.0 |
| Kokoro inference code | MIT |
| eSpeak-NG | GPL v3 |
| This application code | MIT |
