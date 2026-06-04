"""
VOXCAST -- Real-Time Text-to-Speech Server
==========================================
FastAPI backend powered by Kokoro-82M TTS engine.

GPU note: We keep the model in float32 and use torch.autocast for fp16
math during inference. Never cast the whole model to .half() -- Kokoro
mixes nn.Embedding (must be float32) with linear layers, so a full
.half() cast causes "Input Float, parameter Half" dtype errors.
"""

import asyncio
import json
import re
import time
import uuid
import threading
import queue
import base64
import pathlib
from typing import Optional

import numpy as np
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse

BASE_DIR = pathlib.Path(__file__).parent

# ─────────────────────────────────────────────────────────────────────────────
# VOICE CATALOGUE
# ─────────────────────────────────────────────────────────────────────────────

VOICES = {
    # American English - Female
    "af_heart":   {"name": "Heart",    "lang": "en-us", "gender": "F", "style": "warm, expressive",    "stars": 5},
    "af_bella":   {"name": "Bella",    "lang": "en-us", "gender": "F", "style": "smooth, confident",   "stars": 5},
    "af_nicole":  {"name": "Nicole",   "lang": "en-us", "gender": "F", "style": "whispery, intimate",  "stars": 4},
    "af_aoede":   {"name": "Aoede",    "lang": "en-us", "gender": "F", "style": "bright, cheerful",    "stars": 4},
    "af_kore":    {"name": "Kore",     "lang": "en-us", "gender": "F", "style": "clear, professional", "stars": 4},
    "af_sarah":   {"name": "Sarah",    "lang": "en-us", "gender": "F", "style": "natural, friendly",   "stars": 4},
    "af_nova":    {"name": "Nova",     "lang": "en-us", "gender": "F", "style": "energetic, dynamic",  "stars": 4},
    "af_sky":     {"name": "Sky",      "lang": "en-us", "gender": "F", "style": "airy, calm",          "stars": 3},
    "af_alloy":   {"name": "Alloy",    "lang": "en-us", "gender": "F", "style": "versatile, neutral",  "stars": 3},
    "af_jessica": {"name": "Jessica",  "lang": "en-us", "gender": "F", "style": "conversational",      "stars": 3},
    "af_river":   {"name": "River",    "lang": "en-us", "gender": "F", "style": "flowing, melodic",    "stars": 3},
    # American English - Male
    "am_adam":    {"name": "Adam",     "lang": "en-us", "gender": "M", "style": "deep, authoritative", "stars": 5},
    "am_michael": {"name": "Michael",  "lang": "en-us", "gender": "M", "style": "rich, storytelling",  "stars": 5},
    "am_echo":    {"name": "Echo",     "lang": "en-us", "gender": "M", "style": "resonant, clear",     "stars": 4},
    "am_eric":    {"name": "Eric",     "lang": "en-us", "gender": "M", "style": "steady, trustworthy", "stars": 4},
    "am_fenrir":  {"name": "Fenrir",   "lang": "en-us", "gender": "M", "style": "bold, dramatic",      "stars": 4},
    "am_liam":    {"name": "Liam",     "lang": "en-us", "gender": "M", "style": "casual, relatable",   "stars": 3},
    "am_onyx":    {"name": "Onyx",     "lang": "en-us", "gender": "M", "style": "smooth, polished",    "stars": 4},
    "am_puck":    {"name": "Puck",     "lang": "en-us", "gender": "M", "style": "playful, witty",      "stars": 3},
    "am_santa":   {"name": "Santa",    "lang": "en-us", "gender": "M", "style": "warm, jovial",        "stars": 3},
    # British English - Female
    "bf_emma":    {"name": "Emma",     "lang": "en-gb", "gender": "F", "style": "elegant, precise",    "stars": 5},
    "bf_isabella":{"name": "Isabella", "lang": "en-gb", "gender": "F", "style": "refined, warm",       "stars": 4},
    "bf_alice":   {"name": "Alice",    "lang": "en-gb", "gender": "F", "style": "crisp, articulate",   "stars": 4},
    "bf_lily":    {"name": "Lily",     "lang": "en-gb", "gender": "F", "style": "soft, lyrical",       "stars": 3},
    # British English - Male
    "bm_george":  {"name": "George",   "lang": "en-gb", "gender": "M", "style": "distinguished, deep", "stars": 5},
    "bm_lewis":   {"name": "Lewis",    "lang": "en-gb", "gender": "M", "style": "conversational, warm","stars": 4},
    "bm_daniel":  {"name": "Daniel",   "lang": "en-gb", "gender": "M", "style": "smooth, professional","stars": 4},
    "bm_fable":   {"name": "Fable",    "lang": "en-gb", "gender": "M", "style": "narrative, dramatic", "stars": 3},
}

# ─────────────────────────────────────────────────────────────────────────────
# MODEL STATE
# ─────────────────────────────────────────────────────────────────────────────

class ModelState:
    def __init__(self):
        self.pipeline     = None
        self.device       = "cpu"
        self.loading      = False
        self.loaded       = False
        self.error        = None
        self.progress     = 0
        self.progress_msg = "Not loaded"
        self._lock        = threading.Lock()
        self._progress_q  = queue.Queue(maxsize=100)

    def push_progress(self, pct: int, msg: str):
        self.progress     = pct
        self.progress_msg = msg
        try:
            self._progress_q.put_nowait({"pct": pct, "msg": msg})
        except queue.Full:
            pass

    def status_dict(self):
        gpu_info = {}
        try:
            import torch
            if torch.cuda.is_available():
                props = torch.cuda.get_device_properties(0)
                used  = torch.cuda.memory_allocated(0) / 1024**3
                total = props.total_memory / 1024**3
                gpu_info = {
                    "name":       props.name,
                    "vram_total": round(total, 1),
                    "vram_used":  round(used, 2),
                    "vram_free":  round(total - used, 2),
                }
        except Exception:
            pass
        return {
            "loaded":       self.loaded,
            "loading":      self.loading,
            "error":        self.error,
            "device":       self.device,
            "progress":     self.progress,
            "progress_msg": self.progress_msg,
            "gpu":          gpu_info,
            "voices":       VOICES,
        }


model_state = ModelState()


# ─────────────────────────────────────────────────────────────────────────────
# MODEL LOADER
# ─────────────────────────────────────────────────────────────────────────────

def _load_kokoro_thread():
    try:
        model_state.push_progress(5, "Checking CUDA...")

        import torch
        if torch.cuda.is_available():
            model_state.device = "cuda"
            gpu_name = torch.cuda.get_device_properties(0).name
            print(f"[TTS] GPU detected: {gpu_name}")
        else:
            model_state.device = "cpu"
            print("[TTS] No GPU found, using CPU")

        model_state.push_progress(20, "Downloading Kokoro model weights...")

        from kokoro import KPipeline

        model_state.push_progress(70, "Initialising pipeline on GPU...")

        # ── DTYPE STRATEGY ──────────────────────────────────────────────────
        # Keep the model in float32. Kokoro has nn.Embedding layers that must
        # stay float32, and casting the whole model with .half() causes:
        #   "Input Float, parameter Half" dtype mismatch errors.
        #
        # Instead we use torch.autocast which applies fp16 math only to ops
        # that are safe for it (GEMM, conv) while leaving embeddings in fp32.
        # This gives ~same speed benefit as .half() with zero dtype errors.
        # ────────────────────────────────────────────────────────────────────
        pipe = KPipeline(lang_code='a', device=model_state.device)

        model_state.push_progress(90, "Warming up GPU (first inference)...")

        # Warm-up: run one short inference so CUDA kernels compile now,
        # not on the first real user request.
        if model_state.device == "cuda":
            import torch
            with torch.autocast(device_type="cuda", dtype=torch.float16):
                for _, _, _ in pipe("Hello.", voice="af_heart"):
                    break
        else:
            for _, _, _ in pipe("Hello.", voice="af_heart"):
                break

        with model_state._lock:
            model_state.pipeline = pipe
            model_state.loaded   = True
            model_state.loading  = False

        model_state.push_progress(100, "Ready")
        print("[TTS] Kokoro loaded and ready.")

    except Exception as e:
        model_state.error   = str(e)
        model_state.loading = False
        model_state.push_progress(-1, f"Error: {e}")
        print(f"[TTS] Load error: {e}")


def trigger_load():
    if model_state.loading or model_state.loaded:
        return {"ok": False, "msg": "Already loading or loaded"}
    model_state.loading  = True
    model_state.error    = None
    model_state.progress = 0
    model_state.push_progress(1, "Starting...")
    t = threading.Thread(target=_load_kokoro_thread, daemon=True)
    t.start()
    return {"ok": True, "msg": "Load started"}


# ─────────────────────────────────────────────────────────────────────────────
# TEXT TOKENISER
# ─────────────────────────────────────────────────────────────────────────────

def tokenize_text(text: str) -> list:
    tokens = []
    for m in re.finditer(r'\S+', text):
        word   = m.group()
        is_end = bool(re.search(r'[.!?]+$', word))
        tokens.append({
            "word":            word,
            "index":           len(tokens),
            "is_sentence_end": is_end,
            "char_start":      m.start(),
            "char_end":        m.end(),
        })
    return tokens


# ─────────────────────────────────────────────────────────────────────────────
# SYNTHESIS ENGINE
# ─────────────────────────────────────────────────────────────────────────────

SAMPLE_RATE = 24000  # Kokoro native output sample rate

def _synthesise_blocking(text: str, voice: str, speed: float, out_q: queue.Queue):
    """
    Runs in a thread pool executor.
    Uses torch.autocast for fp16 math on GPU while keeping parameters in fp32.
    Streams token + audio events into out_q.
    """
    try:
        with model_state._lock:
            pipe = model_state.pipeline
        if pipe is None:
            out_q.put({"type": "error", "msg": "Model not loaded"})
            return

        all_tokens  = tokenize_text(text)
        total_words = len(all_tokens)
        words_done  = 0
        t_cursor_ms = 0

        # Determine lang_code from voice prefix
        lang_code = 'b' if voice.startswith('b') else 'a'

        # Create a fresh pipeline with the correct lang_code if needed
        # (re-use existing pipe if lang matches, otherwise create a temp one)
        if (lang_code == 'a' and not voice.startswith('b')) or \
           (lang_code == 'b' and voice.startswith('b')):
            active_pipe = pipe
        else:
            from kokoro import KPipeline
            active_pipe = KPipeline(lang_code=lang_code, device=model_state.device)

        import torch
        use_autocast = (model_state.device == "cuda")

        def run_inference():
            if use_autocast:
                with torch.autocast(device_type="cuda", dtype=torch.float16):
                    yield from active_pipe(text, voice=voice, speed=speed)
            else:
                yield from active_pipe(text, voice=voice, speed=speed)

        results = run_inference()

        for res in results:
            # Handle both backward compatibility unpacking and Result object
            if isinstance(res, tuple):
                graphemes, phonemes, audio_np = res
                m_tokens = None
            else:
                graphemes = res.graphemes
                phonemes = res.phonemes
                audio_np = res.audio
                m_tokens = getattr(res, "tokens", None)

            t_cursor_ms = 0
            if audio_np is None or len(audio_np) == 0:
                continue

            # Always ensure float32 numpy output for consistent PCM encoding
            audio_np = np.array(audio_np, dtype=np.float32)

            chunk_ms    = int(len(audio_np) / SAMPLE_RATE * 1000)
            chunk_words = [w for w in (graphemes or "").split() if w]
            if not chunk_words:
                chunk_words = [""]

            chunk_words_count = len(chunk_words) if chunk_words else 1
            peek_tokens = all_tokens[words_done : words_done + chunk_words_count]

            if m_tokens and len(m_tokens) > 0:
                m_idx = 0
                for tok in peek_tokens:
                    tok_w = tok["word"].lower().strip(",.!?\"'()[]{}:;")
                    assigned_ts = None
                    
                    if tok_w:
                        search_idx = m_idx
                        while search_idx < len(m_tokens):
                            mt = m_tokens[search_idx]
                            mt_w = getattr(mt, "text", "").lower().strip(",.!?\"'()[]{}:;")
                            if mt_w and (mt_w in tok_w or tok_w in mt_w):
                                assigned_ts = getattr(mt, "start_ts", None)
                                m_idx = search_idx + 1
                                break
                            search_idx += 1
                    
                    if assigned_ts is not None:
                        t_ms = int(assigned_ts * 1000)
                        t_cursor_ms = t_ms
                    else:
                        t_ms = t_cursor_ms
                        
                    out_q.put({
                        "type":  "token",
                        "word":  tok["word"],
                        "index": tok["index"],
                        "t_ms":  t_ms,
                        "total": total_words,
                    })
                    words_done += 1
            else:
                # Fallback to proportional calculation
                total_chars = sum(len(tok["word"]) + 1 for tok in peek_tokens)
                ms_per_char = chunk_ms / max(total_chars, 1)

                for _ in chunk_words:
                    if words_done < total_words:
                        tok = all_tokens[words_done]
                        out_q.put({
                            "type":  "token",
                            "word":  tok["word"],
                            "index": tok["index"],
                            "t_ms":  t_cursor_ms,
                            "total": total_words,
                        })
                        t_cursor_ms += int((len(tok["word"]) + 1) * ms_per_char)
                        words_done  += 1

            # Encode PCM float32 as base64 for browser AudioContext
            pcm_bytes = audio_np.tobytes()
            out_q.put({
                "type":        "audio",
                "b64":         base64.b64encode(pcm_bytes).decode(),
                "sample_rate": SAMPLE_RATE,
                "duration_ms": chunk_ms,
            })

        # Emit any remaining tokens not covered by grapheme chunks
        while words_done < total_words:
            tok = all_tokens[words_done]
            out_q.put({
                "type":  "token",
                "word":  tok["word"],
                "index": tok["index"],
                "t_ms":  t_cursor_ms,
                "total": total_words,
            })
            words_done += 1

        out_q.put({"type": "done"})

    except Exception as e:
        out_q.put({"type": "error", "msg": str(e)})
        print(f"[TTS] Synthesis error: {e}")


# ─────────────────────────────────────────────────────────────────────────────
# FASTAPI APPLICATION
# ─────────────────────────────────────────────────────────────────────────────

app = FastAPI(title="VoxCast -- Kokoro TTS")

with open(BASE_DIR / "index.html", encoding="utf-8") as f:
    HTML = f.read()


@app.get("/", response_class=HTMLResponse)
async def root():
    return HTMLResponse(HTML)


@app.get("/api/status")
async def api_status():
    return JSONResponse(model_state.status_dict())


@app.post("/api/load")
async def api_load():
    return JSONResponse(trigger_load())


@app.get("/api/progress")
async def api_progress():
    """SSE stream: sends {pct, msg} events during model load."""
    async def event_stream():
        loop = asyncio.get_event_loop()
        while True:
            try:
                item = await loop.run_in_executor(
                    None,
                    lambda: model_state._progress_q.get(timeout=30)
                )
                yield f"data: {json.dumps(item)}\n\n"
                if item["pct"] in (100, -1):
                    break
            except Exception:
                break
    return StreamingResponse(event_stream(), media_type="text/event-stream")


@app.get("/api/voices")
async def api_voices():
    return JSONResponse({"voices": VOICES})


@app.websocket("/ws/tts")
async def ws_tts(websocket: WebSocket):
    """
    Client sends:  {"text": "...", "voice": "af_heart", "speed": 1.0}
    Server emits:
      {"type": "token",  "word": "Hello", "index": 0, "t_ms": 0,  "total": 5}
      {"type": "audio",  "b64": "<base64 pcm float32>", "sample_rate": 24000, "duration_ms": 480}
      {"type": "done"}
      {"type": "error",  "msg": "..."}
    """
    await websocket.accept()
    try:
        while True:
            raw = await websocket.receive_text()
            req = json.loads(raw)

            if req.get("type") == "ping":
                await websocket.send_text(json.dumps({"type": "pong"}))
                continue

            text  = req.get("text", "").strip()
            voice = req.get("voice", "af_heart")
            speed = float(req.get("speed", 1.0))

            if not text:
                await websocket.send_text(json.dumps({"type": "error", "msg": "Empty text"}))
                continue

            if not model_state.loaded:
                await websocket.send_text(json.dumps({"type": "error", "msg": "Model not loaded yet"}))
                continue

            out_q: queue.Queue = queue.Queue(maxsize=128)
            loop = asyncio.get_event_loop()

            synth_task = loop.run_in_executor(
                None, _synthesise_blocking, text, voice, speed, out_q
            )

            while True:
                try:
                    item = await loop.run_in_executor(
                        None, lambda: out_q.get(timeout=60)
                    )
                except Exception:
                    break

                await websocket.send_text(json.dumps(item))

                if item["type"] in ("done", "error"):
                    break

            await synth_task

    except WebSocketDisconnect:
        pass
    except Exception as e:
        try:
            await websocket.send_text(json.dumps({"type": "error", "msg": str(e)}))
        except Exception:
            pass