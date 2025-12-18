"""
sal-voice - Voice Modality for SAL
FastAPI application with STT, TTS, and SCL integration
"""
import io
import asyncio
from pathlib import Path
from typing import Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, File, UploadFile, Form, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, StreamingResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from loguru import logger

from config import settings
from stt_engine import stt_engine
from tts_engine import tts_engine
from scl_bridge import scl_bridge


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    logger.info("⠠⠎⠁⠇_⠧⠕⠊⠉⠑ Starting up...")
    yield
    logger.info("⠠⠎⠁⠇_⠧⠕⠊⠉⠑ Shutting down...")
    await scl_bridge.close()


app = FastAPI(
    title="sal-voice",
    description="Voice modality for SAL (Semantic Accessibility Layer)",
    version="1.0.0",
    lifespan=lifespan
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static files
static_dir = Path(__file__).parent / "static"
static_dir.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=static_dir), name="static")


# --- Pydantic Models ---

class TTSRequest(BaseModel):
    text: str
    voice: Optional[str] = None
    rate: Optional[str] = None
    pitch: Optional[str] = None
    
class SCLRequest(BaseModel):
    text: str
    
class VoiceResponse(BaseModel):
    text: str
    braille: str
    scl: str
    language: str
    confidence: float


# --- API Endpoints ---

@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve the main voice interface"""
    return """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>⠠⠎⠁⠇ sal-voice</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
            min-height: 100vh;
            color: #e8e8e8;
            padding: 20px;
        }
        .container {
            max-width: 900px;
            margin: 0 auto;
        }
        header {
            text-align: center;
            margin-bottom: 40px;
        }
        h1 {
            font-size: 2.5em;
            margin-bottom: 10px;
            background: linear-gradient(90deg, #00d9ff, #00ff88);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        .braille-title {
            font-size: 1.5em;
            opacity: 0.7;
            letter-spacing: 5px;
        }
        .subtitle {
            color: #888;
            margin-top: 10px;
        }
        .card {
            background: rgba(255,255,255,0.05);
            border-radius: 16px;
            padding: 30px;
            margin-bottom: 20px;
            border: 1px solid rgba(255,255,255,0.1);
        }
        .card h2 {
            margin-bottom: 20px;
            display: flex;
            align-items: center;
            gap: 10px;
        }
        .btn {
            padding: 15px 30px;
            border: none;
            border-radius: 8px;
            font-size: 16px;
            cursor: pointer;
            transition: all 0.3s;
            display: inline-flex;
            align-items: center;
            gap: 10px;
        }
        .btn-primary {
            background: linear-gradient(90deg, #00d9ff, #00ff88);
            color: #1a1a2e;
            font-weight: bold;
        }
        .btn-primary:hover { transform: scale(1.05); }
        .btn-primary:disabled {
            opacity: 0.5;
            cursor: not-allowed;
            transform: none;
        }
        .btn-secondary {
            background: rgba(255,255,255,0.1);
            color: #fff;
        }
        .btn-secondary:hover { background: rgba(255,255,255,0.2); }
        .recording {
            animation: pulse 1s infinite;
        }
        @keyframes pulse {
            0%, 100% { box-shadow: 0 0 0 0 rgba(255,0,0,0.4); }
            50% { box-shadow: 0 0 0 20px rgba(255,0,0,0); }
        }
        textarea, input {
            width: 100%;
            padding: 15px;
            border-radius: 8px;
            border: 1px solid rgba(255,255,255,0.2);
            background: rgba(0,0,0,0.3);
            color: #fff;
            font-size: 16px;
            margin-bottom: 15px;
            resize: vertical;
        }
        textarea:focus, input:focus {
            outline: none;
            border-color: #00d9ff;
        }
        .result {
            background: rgba(0,0,0,0.3);
            border-radius: 8px;
            padding: 20px;
            margin-top: 20px;
            display: none;
        }
        .result.active { display: block; }
        .result-section {
            margin-bottom: 15px;
        }
        .result-section label {
            display: block;
            color: #00d9ff;
            margin-bottom: 5px;
            font-weight: bold;
        }
        .result-section .value {
            font-family: monospace;
            word-break: break-all;
        }
        .braille-output {
            font-size: 1.5em;
            letter-spacing: 3px;
        }
        .status {
            padding: 10px 20px;
            border-radius: 8px;
            margin-top: 10px;
            display: none;
        }
        .status.active { display: block; }
        .status.success { background: rgba(0,255,136,0.2); color: #00ff88; }
        .status.error { background: rgba(255,0,0,0.2); color: #ff6b6b; }
        .status.processing { background: rgba(0,217,255,0.2); color: #00d9ff; }
        .controls {
            display: flex;
            gap: 10px;
            flex-wrap: wrap;
        }
        .audio-player {
            width: 100%;
            margin-top: 15px;
        }
        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
        }
        .haptic-viz {
            height: 60px;
            background: rgba(0,0,0,0.3);
            border-radius: 8px;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 3px;
            padding: 10px;
            overflow: hidden;
        }
        .haptic-bar {
            width: 4px;
            background: #00d9ff;
            border-radius: 2px;
            transition: height 0.1s;
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>🎤 sal-voice</h1>
            <div class="braille-title">⠠⠎⠁⠇_⠧⠕⠊⠉⠑</div>
            <p class="subtitle">Voice Modality for the Semantic Accessibility Layer</p>
        </header>
        
        <div class="grid">
            <!-- Speech to Text -->
            <div class="card">
                <h2>🎙️ Speech to Text</h2>
                <div class="controls">
                    <button id="recordBtn" class="btn btn-primary" onclick="toggleRecording()">
                        <span id="recordIcon">🎤</span>
                        <span id="recordText">Start Recording</span>
                    </button>
                    <input type="file" id="audioFile" accept="audio/*" style="display:none" onchange="uploadAudio(this)">
                    <button class="btn btn-secondary" onclick="document.getElementById('audioFile').click()">
                        📁 Upload Audio
                    </button>
                </div>
                <div id="sttStatus" class="status"></div>
                <div id="sttResult" class="result">
                    <div class="result-section">
                        <label>Transcription</label>
                        <div class="value" id="transcription"></div>
                    </div>
                    <div class="result-section">
                        <label>Braille</label>
                        <div class="value braille-output" id="sttBraille"></div>
                    </div>
                    <div class="result-section">
                        <label>Language</label>
                        <div class="value" id="sttLanguage"></div>
                    </div>
                </div>
            </div>
            
            <!-- Text to Speech -->
            <div class="card">
                <h2>🔊 Text to Speech</h2>
                <textarea id="ttsInput" rows="4" placeholder="Enter text to speak..."></textarea>
                <div class="controls">
                    <button class="btn btn-primary" onclick="synthesizeSpeech()">
                        🔊 Speak
                    </button>
                    <select id="voiceSelect" class="btn btn-secondary" style="padding: 10px;">
                        <option value="en-US-AriaNeural">Aria (US)</option>
                        <option value="en-US-GuyNeural">Guy (US)</option>
                        <option value="en-GB-SoniaNeural">Sonia (UK)</option>
                        <option value="nl-NL-ColetteNeural">Colette (NL)</option>
                        <option value="de-DE-KatjaNeural">Katja (DE)</option>
                        <option value="es-ES-ElviraNeural">Elvira (ES)</option>
                    </select>
                </div>
                <div id="ttsStatus" class="status"></div>
                <audio id="audioPlayer" class="audio-player" controls style="display:none"></audio>
            </div>
        </div>
        
        <!-- Voice to SCL -->
        <div class="card">
            <h2>🔮 Voice to SCL Translation</h2>
            <textarea id="sclInput" rows="3" placeholder="Enter text or use voice recording above..."></textarea>
            <button class="btn btn-primary" onclick="translateToSCL()">
                🔮 Translate to SCL
            </button>
            <div id="sclStatus" class="status"></div>
            <div id="sclResult" class="result">
                <div class="result-section">
                    <label>SCL Encoding</label>
                    <div class="value" id="sclEncoding"></div>
                </div>
                <div class="result-section">
                    <label>Semantic Density Score</label>
                    <div class="value" id="sclSDS"></div>
                </div>
                <div class="result-section">
                    <label>Concepts</label>
                    <div class="value" id="sclConcepts"></div>
                </div>
                <div class="result-section">
                    <label>Braille</label>
                    <div class="value braille-output" id="sclBraille"></div>
                </div>
                <div class="result-section">
                    <label>Haptic Pattern</label>
                    <div class="haptic-viz" id="hapticViz"></div>
                </div>
            </div>
        </div>
    </div>
    
    <script>
        let mediaRecorder = null;
        let audioChunks = [];
        let isRecording = false;
        
        async function toggleRecording() {
            if (isRecording) {
                stopRecording();
            } else {
                await startRecording();
            }
        }
        
        async function startRecording() {
            try {
                const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
                mediaRecorder = new MediaRecorder(stream);
                audioChunks = [];
                
                mediaRecorder.ondataavailable = (e) => audioChunks.push(e.data);
                mediaRecorder.onstop = async () => {
                    const audioBlob = new Blob(audioChunks, { type: 'audio/wav' });
                    await processAudio(audioBlob);
                    stream.getTracks().forEach(t => t.stop());
                };
                
                mediaRecorder.start();
                isRecording = true;
                document.getElementById('recordBtn').classList.add('recording');
                document.getElementById('recordIcon').textContent = '⏹️';
                document.getElementById('recordText').textContent = 'Stop Recording';
                showStatus('sttStatus', 'Recording...', 'processing');
            } catch (err) {
                showStatus('sttStatus', 'Microphone access denied', 'error');
            }
        }
        
        function stopRecording() {
            if (mediaRecorder && isRecording) {
                mediaRecorder.stop();
                isRecording = false;
                document.getElementById('recordBtn').classList.remove('recording');
                document.getElementById('recordIcon').textContent = '🎤';
                document.getElementById('recordText').textContent = 'Start Recording';
            }
        }
        
        async function uploadAudio(input) {
            if (input.files.length > 0) {
                await processAudio(input.files[0]);
            }
        }
        
        async function processAudio(audioBlob) {
            showStatus('sttStatus', 'Transcribing...', 'processing');
            
            const formData = new FormData();
            formData.append('audio', audioBlob, 'recording.wav');
            
            try {
                const response = await fetch('/api/stt', {
                    method: 'POST',
                    body: formData
                });
                const data = await response.json();
                
                if (response.ok) {
                    document.getElementById('transcription').textContent = data.text;
                    document.getElementById('sttBraille').textContent = data.braille || '';
                    document.getElementById('sttLanguage').textContent = 
                        `${data.language} (${(data.language_probability * 100).toFixed(1)}% confidence)`;
                    document.getElementById('sttResult').classList.add('active');
                    document.getElementById('sclInput').value = data.text;
                    showStatus('sttStatus', 'Transcription complete!', 'success');
                } else {
                    showStatus('sttStatus', data.detail || 'Transcription failed', 'error');
                }
            } catch (err) {
                showStatus('sttStatus', 'Error: ' + err.message, 'error');
            }
        }
        
        async function synthesizeSpeech() {
            const text = document.getElementById('ttsInput').value.trim();
            if (!text) {
                showStatus('ttsStatus', 'Please enter text', 'error');
                return;
            }
            
            showStatus('ttsStatus', 'Synthesizing...', 'processing');
            
            try {
                const voice = document.getElementById('voiceSelect').value;
                const response = await fetch('/api/tts', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ text, voice })
                });
                
                if (response.ok) {
                    const audioBlob = await response.blob();
                    const audioUrl = URL.createObjectURL(audioBlob);
                    const player = document.getElementById('audioPlayer');
                    player.src = audioUrl;
                    player.style.display = 'block';
                    player.play();
                    showStatus('ttsStatus', 'Playing audio', 'success');
                } else {
                    const data = await response.json();
                    showStatus('ttsStatus', data.detail || 'Synthesis failed', 'error');
                }
            } catch (err) {
                showStatus('ttsStatus', 'Error: ' + err.message, 'error');
            }
        }
        
        async function translateToSCL() {
            const text = document.getElementById('sclInput').value.trim();
            if (!text) {
                showStatus('sclStatus', 'Please enter text', 'error');
                return;
            }
            
            showStatus('sclStatus', 'Translating to SCL...', 'processing');
            
            try {
                const response = await fetch('/api/voice-to-scl', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ text })
                });
                const data = await response.json();
                
                if (response.ok) {
                    document.getElementById('sclEncoding').textContent = data.scl;
                    document.getElementById('sclSDS').textContent = data.semantic_density;
                    document.getElementById('sclConcepts').textContent = (data.concepts || []).join(', ');
                    document.getElementById('sclBraille').textContent = data.braille;
                    document.getElementById('sclResult').classList.add('active');
                    
                    // Visualize haptic pattern
                    visualizeHaptic(data.haptic_pattern || []);
                    
                    showStatus('sclStatus', 'Translation complete!', 'success');
                } else {
                    showStatus('sclStatus', data.detail || 'Translation failed', 'error');
                }
            } catch (err) {
                showStatus('sclStatus', 'Error: ' + err.message, 'error');
            }
        }
        
        function visualizeHaptic(pattern) {
            const viz = document.getElementById('hapticViz');
            viz.innerHTML = '';
            
            pattern.slice(0, 50).forEach(p => {
                const bar = document.createElement('div');
                bar.className = 'haptic-bar';
                if (p.type === 'vibrate') {
                    bar.style.height = `${Math.min(50, p.duration / 2)}px`;
                    bar.style.opacity = p.intensity || 0.5;
                } else {
                    bar.style.height = '2px';
                    bar.style.opacity = 0.2;
                }
                viz.appendChild(bar);
            });
        }
        
        function showStatus(id, message, type) {
            const el = document.getElementById(id);
            el.textContent = message;
            el.className = 'status active ' + type;
        }
    </script>
</body>
</html>
"""


@app.get("/health")
async def health():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "sal-voice",
        "version": "1.0.0",
        "braille": "⠠⠎⠁⠇_⠧⠕⠊⠉⠑"
    }


@app.post("/api/stt")
async def speech_to_text(
    audio: UploadFile = File(...),
    language: Optional[str] = Form(None)
):
    """
    Convert speech to text using Whisper
    """
    try:
        audio_data = await audio.read()
        result = await stt_engine.transcribe(audio_data, language=language)
        return result
    except Exception as e:
        logger.error(f"STT error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/tts")
async def text_to_speech(request: TTSRequest):
    """
    Convert text to speech
    """
    try:
        audio_data = await tts_engine.synthesize(
            text=request.text,
            voice=request.voice,
            rate=request.rate,
            pitch=request.pitch
        )
        return StreamingResponse(
            io.BytesIO(audio_data),
            media_type="audio/mpeg",
            headers={"Content-Disposition": "attachment; filename=speech.mp3"}
        )
    except Exception as e:
        logger.error(f"TTS error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/voice-to-scl")
async def voice_to_scl(request: SCLRequest):
    """
    Translate text to SCL
    """
    try:
        # Create mock transcription for text input
        transcription = {
            "text": request.text,
            "language": "en",
            "language_probability": 1.0,
            "segments": [],
            "duration": 0
        }
        result = await scl_bridge.voice_to_scl(transcription)
        return result
    except Exception as e:
        logger.error(f"SCL translation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/scl-to-voice")
async def scl_to_voice(request: SCLRequest):
    """
    Convert SCL back to voice
    """
    try:
        text = await scl_bridge.scl_to_text(request.text)
        audio_data = await tts_engine.synthesize(text)
        return StreamingResponse(
            io.BytesIO(audio_data),
            media_type="audio/mpeg"
        )
    except Exception as e:
        logger.error(f"SCL to voice error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/voices")
async def list_voices(language: Optional[str] = None):
    """
    List available TTS voices
    """
    try:
        voices = await tts_engine.list_voices(language)
        return {"voices": voices}
    except Exception as e:
        logger.error(f"Voice list error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.websocket("/ws/stream")
async def websocket_stream(websocket: WebSocket):
    """
    WebSocket endpoint for real-time audio streaming
    """
    await websocket.accept()
    logger.info("WebSocket connection established")
    
    try:
        while True:
            # Receive audio chunk
            data = await websocket.receive_bytes()
            
            # Process audio (simplified - would need proper buffering)
            result = await stt_engine.transcribe(data)
            
            # Send transcription back
            await websocket.send_json({
                "type": "transcription",
                "text": result.get("text", ""),
                "braille": result.get("braille", ""),
                "partial": True
            })
            
    except WebSocketDisconnect:
        logger.info("WebSocket disconnected")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        await websocket.close()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug
    )
