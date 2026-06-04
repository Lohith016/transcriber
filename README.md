# Voice Tools Suite

A collection of high-performance, locally-hosted AI voice applications built with FastAPI and WebSockets.

This repository contains two standalone projects:

## 1. [VOXSTREAM (Speech-to-Text)](./stt)
**Real-Time Whisper Transcription**
Local Whisper speech-to-text with a FastAPI WebSocket backend and a dark single-page frontend. Switch models live from the browser without restarting the server.
- **Engine**: faster-whisper
- **Features**: Live model switching, real-time token streaming, GPU acceleration.
- [Read the STT README](./stt/README.md) for setup and usage instructions.

## 2. [VOXCAST (Text-to-Speech)](./tts)
**Real-Time Text-to-Speech**
Local GPU-accelerated TTS powered by Kokoro-82M. Word-by-word token streaming, 54 emotional voices, optimized for RTX 4060 and other CUDA GPUs.
- **Engine**: Kokoro-82M (StyleTTS2 architecture)
- **Features**: 96x real-time generation, streaming audio, live word highlighting, zero API costs.
- [Read the TTS README](./tts/README.md) for setup and usage instructions.

---

## Repository Structure

```text
.
├── stt/                 ← VOXSTREAM (Real-time Speech-to-Text)
│   ├── main.py
│   ├── index.html
│   └── README.md
└── tts/                 ← VOXCAST (Real-time Text-to-Speech)
    ├── main.py
    ├── index.html
    └── README.md
```

## Getting Started

Each project is completely standalone with its own dependencies and setup scripts. Navigate to the respective directory to get started.

### For Speech-to-Text (Whisper)
```bash
cd stt
# Then follow the instructions in stt/README.md
```

### For Text-to-Speech (Kokoro)
```bash
cd tts
# Then follow the instructions in tts/README.md
```

## License

Both application servers and frontends are provided under the MIT License. The respective AI models (Whisper, Kokoro-82M) and their dependencies are subject to their own licenses (e.g., Apache 2.0).
