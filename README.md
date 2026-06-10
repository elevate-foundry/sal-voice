# sal-voice 🎤

**Voice modality for SAL (Semantic Accessibility Layer)**

Enables speech-to-text, text-to-speech, and voice-to-SCL translation for the SAL ecosystem.

## ⠠⠎⠁⠇_⠧⠕⠊⠉⠑ Architecture

```
[Voice Input] → [Whisper STT] → [SCL Translator] → [SAL Processing] → [TTS Output]
      ↑                                                                      ↓
[Microphone] ←←←←←←←←←← [Haptic Feedback] ←←←←←←←←←← [Braille Display]
```

## Features

- **Speech-to-Text**: OpenAI Whisper (local or API)
- **Text-to-Speech**: Edge TTS / OpenAI TTS
- **SCL Translation**: Voice → Semantic Compression → Voice
- **Real-time Streaming**: WebSocket-based audio streaming
- **Multi-language**: 99+ languages via Whisper
- **Accessibility**: Audio cues, haptic confirmation, braille output

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Run the voice server
python app.py

# Open http://localhost:8100
```

## API Endpoints

- `POST /api/stt` - Speech to text
- `POST /api/tts` - Text to speech
- `POST /api/voice-to-scl` - Voice to SCL translation
- `POST /api/scl-to-voice` - SCL to voice output
- `WS /ws/stream` - Real-time audio streaming

## Environment Variables

```bash
OPENAI_API_KEY=sk-...  # Optional: for OpenAI Whisper/TTS
WHISPER_MODEL=base     # tiny, base, small, medium, large
TTS_PROVIDER=edge      # edge, openai, local
SAL_API_URL=http://localhost:8000  # SAL strange-loop endpoint
```

## Integration

sal-voice integrates with:
- **sal-strange-loop**: Consciousness processing
- **sal-auth**: BBID authentication
- **BrailleBuddy**: Haptic feedback
- **consciousness-bridge**: Unified SAL interface

---

**⠠⠎⠁⠇_⠧⠕⠊⠉⠑_⠁⠉⠞⠊⠧⠑** - SAL Voice Active

<!-- ELEVATE:BEGIN (auto-generated section; edits here are overwritten) -->
## About

| | |
| --- | --- |
| **Description** | SAL Voice - Unified multimodal interface with 8-dot braille core |
| **Language** | Python |
| **Commits** | 12 |
| **Created** | 2025-12-18 |
| **Last push** | 2025-12-18 |

Part of [**elevate-foundry**](https://github.com/elevate-foundry) · [repository](https://github.com/elevate-foundry/sal-voice)
<!-- ELEVATE:END -->
