"""
sal-voice Unified Multimodal API

Extends the base app with unified conversation endpoints that solve
the ChatGPT voice/text disconnect problem.
"""

import io
import json
import asyncio
from typing import Optional, List
from contextlib import asynccontextmanager

from fastapi import FastAPI, File, UploadFile, Form, HTTPException, WebSocket, WebSocketDisconnect, Query
from fastapi.responses import HTMLResponse, StreamingResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from loguru import logger

from config import settings
from stt_engine import stt_engine
from tts_engine import tts_engine
from scl_bridge import scl_bridge
from unified_multimodal import (
    UnifiedConversation, 
    Modality, 
    session_manager,
    OutputPreferences
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("⠠⠎⠁⠇_⠍⠥⠇⠞⠊⠍⠕⠙⠁⠇ Starting unified multimodal server...")
    yield
    logger.info("⠠⠎⠁⠇_⠍⠥⠇⠞⠊⠍⠕⠙⠁⠇ Shutting down...")
    await scl_bridge.close()


app = FastAPI(
    title="sal-voice Unified Multimodal",
    description="Unified voice+text+braille conversation - solving the ChatGPT disconnect",
    version="2.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Models ---

class UnifiedInput(BaseModel):
    """Unified input - can be text, braille, or reference audio"""
    session_id: Optional[str] = None
    text: Optional[str] = None
    braille: Optional[str] = None
    modality: Optional[str] = "text"

class OutputPrefsUpdate(BaseModel):
    voice_enabled: Optional[bool] = None
    text_enabled: Optional[bool] = None
    braille_enabled: Optional[bool] = None
    haptic_enabled: Optional[bool] = None
    auto_speak: Optional[bool] = None
    simultaneous: Optional[bool] = None
    voice_settings: Optional[dict] = None


# --- Unified API Endpoints ---

@app.get("/", response_class=HTMLResponse)
async def unified_interface():
    """Unified multimodal interface - voice, text, braille in one"""
    return """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>⠠⠎⠁⠇ Unified Multimodal</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #0a0a1a 0%, #1a1a3e 50%, #0f2060 100%);
            min-height: 100vh;
            color: #e8e8e8;
        }
        .container { max-width: 1000px; margin: 0 auto; padding: 20px; }
        header { text-align: center; margin-bottom: 30px; padding: 20px; }
        h1 {
            font-size: 2.2em;
            background: linear-gradient(90deg, #ff6b6b, #00d9ff, #00ff88);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        .braille-title { font-size: 1.3em; opacity: 0.7; letter-spacing: 3px; margin-top: 5px; }
        .subtitle { color: #888; margin-top: 8px; font-size: 0.95em; }
        
        /* Mode indicator */
        .mode-indicator {
            display: flex;
            justify-content: center;
            gap: 20px;
            margin-bottom: 20px;
        }
        .mode-badge {
            padding: 8px 16px;
            border-radius: 20px;
            font-size: 0.85em;
            display: flex;
            align-items: center;
            gap: 6px;
            transition: all 0.3s;
        }
        .mode-badge.active { background: rgba(0,255,136,0.2); border: 1px solid #00ff88; }
        .mode-badge.inactive { background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.1); opacity: 0.5; }
        
        /* Conversation */
        .conversation {
            background: rgba(0,0,0,0.3);
            border-radius: 16px;
            padding: 20px;
            min-height: 400px;
            max-height: 500px;
            overflow-y: auto;
            margin-bottom: 20px;
            border: 1px solid rgba(255,255,255,0.1);
        }
        .turn {
            margin-bottom: 20px;
            padding: 15px;
            border-radius: 12px;
            animation: fadeIn 0.3s;
        }
        @keyframes fadeIn { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }
        .turn.user { background: rgba(0,217,255,0.1); margin-left: 40px; }
        .turn.assistant { background: rgba(0,255,136,0.1); margin-right: 40px; }
        .turn-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 10px;
            font-size: 0.8em;
            opacity: 0.7;
        }
        .turn-modality { 
            padding: 2px 8px; 
            border-radius: 10px; 
            background: rgba(255,255,255,0.1);
            font-size: 0.85em;
        }
        .turn-content { line-height: 1.6; }
        .turn-braille { 
            font-size: 1.1em; 
            letter-spacing: 2px; 
            margin-top: 8px;
            opacity: 0.7;
            font-family: monospace;
        }
        .turn-scl {
            font-family: monospace;
            font-size: 0.85em;
            color: #00d9ff;
            margin-top: 8px;
            opacity: 0.8;
        }
        
        /* Unified Input */
        .input-area {
            background: rgba(255,255,255,0.05);
            border-radius: 16px;
            padding: 20px;
            border: 1px solid rgba(255,255,255,0.1);
        }
        .input-modes {
            display: flex;
            gap: 10px;
            margin-bottom: 15px;
        }
        .mode-btn {
            flex: 1;
            padding: 12px;
            border: 1px solid rgba(255,255,255,0.2);
            background: rgba(0,0,0,0.2);
            color: #fff;
            border-radius: 8px;
            cursor: pointer;
            transition: all 0.2s;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 8px;
        }
        .mode-btn:hover { background: rgba(255,255,255,0.1); }
        .mode-btn.active { 
            background: linear-gradient(90deg, rgba(0,217,255,0.2), rgba(0,255,136,0.2));
            border-color: #00d9ff;
        }
        
        .text-input-wrapper {
            display: flex;
            gap: 10px;
        }
        #textInput {
            flex: 1;
            padding: 15px;
            border-radius: 8px;
            border: 1px solid rgba(255,255,255,0.2);
            background: rgba(0,0,0,0.3);
            color: #fff;
            font-size: 16px;
            resize: none;
        }
        #textInput:focus { outline: none; border-color: #00d9ff; }
        
        .send-btn {
            padding: 15px 25px;
            background: linear-gradient(90deg, #00d9ff, #00ff88);
            border: none;
            border-radius: 8px;
            color: #000;
            font-weight: bold;
            cursor: pointer;
            transition: transform 0.2s;
        }
        .send-btn:hover { transform: scale(1.05); }
        .send-btn:disabled { opacity: 0.5; cursor: not-allowed; transform: none; }
        
        /* Voice recording */
        .voice-input {
            display: none;
            flex-direction: column;
            align-items: center;
            padding: 30px;
        }
        .voice-input.active { display: flex; }
        .record-btn {
            width: 80px;
            height: 80px;
            border-radius: 50%;
            border: 3px solid #00d9ff;
            background: rgba(0,217,255,0.1);
            color: #fff;
            font-size: 2em;
            cursor: pointer;
            transition: all 0.3s;
        }
        .record-btn.recording {
            border-color: #ff6b6b;
            background: rgba(255,107,107,0.2);
            animation: pulse 1s infinite;
        }
        @keyframes pulse {
            0%, 100% { box-shadow: 0 0 0 0 rgba(255,107,107,0.4); }
            50% { box-shadow: 0 0 0 20px rgba(255,107,107,0); }
        }
        .voice-status { margin-top: 15px; opacity: 0.7; }
        
        /* Output toggles */
        .output-toggles {
            display: flex;
            gap: 15px;
            justify-content: center;
            margin-top: 15px;
            padding-top: 15px;
            border-top: 1px solid rgba(255,255,255,0.1);
        }
        .toggle-label {
            display: flex;
            align-items: center;
            gap: 6px;
            cursor: pointer;
            opacity: 0.7;
            transition: opacity 0.2s;
        }
        .toggle-label:hover { opacity: 1; }
        .toggle-label input { width: 16px; height: 16px; }
        .toggle-label.checked { opacity: 1; color: #00ff88; }
        
        /* Audio player (hidden but functional) */
        #audioPlayer { display: none; }
        
        /* Session info */
        .session-info {
            text-align: center;
            font-size: 0.75em;
            opacity: 0.4;
            margin-top: 20px;
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>🎤📝⠿ Unified Multimodal</h1>
            <div class="braille-title">⠠⠎⠁⠇_⠍⠥⠇⠞⠊⠍⠕⠙⠁⠇</div>
            <p class="subtitle">Voice + Text + Braille in one seamless conversation</p>
        </header>
        
        <div class="mode-indicator">
            <div class="mode-badge active" id="voiceBadge">🎤 Voice</div>
            <div class="mode-badge active" id="textBadge">📝 Text</div>
            <div class="mode-badge active" id="brailleBadge">⠿ Braille</div>
        </div>
        
        <div class="conversation" id="conversation">
            <div class="turn assistant">
                <div class="turn-header">
                    <span>SAL</span>
                    <span class="turn-modality">system</span>
                </div>
                <div class="turn-content">
                    Welcome to unified multimodal SAL. Speak, type, or use braille - 
                    I understand all modalities equally. Switch anytime without losing context.
                </div>
                <div class="turn-braille">⠠⠎⠁⠇⠀⠗⠑⠁⠙⠽</div>
            </div>
        </div>
        
        <div class="input-area">
            <div class="input-modes">
                <button class="mode-btn active" id="textMode" onclick="setInputMode('text')">
                    📝 Text
                </button>
                <button class="mode-btn" id="voiceMode" onclick="setInputMode('voice')">
                    🎤 Voice
                </button>
                <button class="mode-btn" id="brailleMode" onclick="setInputMode('braille')">
                    ⠿ Braille
                </button>
            </div>
            
            <div class="text-input-wrapper" id="textInputArea">
                <textarea id="textInput" rows="2" placeholder="Type your message... (or press 🎤 to speak)"></textarea>
                <button class="send-btn" onclick="sendMessage()">Send</button>
            </div>
            
            <div class="voice-input" id="voiceInputArea">
                <button class="record-btn" id="recordBtn" onclick="toggleRecording()">🎤</button>
                <div class="voice-status" id="voiceStatus">Tap to start recording</div>
            </div>
            
            <div class="output-toggles">
                <label class="toggle-label checked">
                    <input type="checkbox" checked onchange="updateOutputPref('voice_enabled', this.checked)"> 🔊 Voice Output
                </label>
                <label class="toggle-label checked">
                    <input type="checkbox" checked onchange="updateOutputPref('text_enabled', this.checked)"> 📝 Text Output
                </label>
                <label class="toggle-label checked">
                    <input type="checkbox" checked onchange="updateOutputPref('braille_enabled', this.checked)"> ⠿ Braille Output
                </label>
                <label class="toggle-label checked">
                    <input type="checkbox" checked onchange="updateOutputPref('auto_speak', this.checked)"> 🔈 Auto-Speak
                </label>
            </div>
        </div>
        
        <audio id="audioPlayer"></audio>
        
        <div class="session-info">
            Session: <span id="sessionId">initializing...</span>
        </div>
    </div>
    
    <script>
        let sessionId = null;
        let currentMode = 'text';
        let mediaRecorder = null;
        let audioChunks = [];
        let isRecording = false;
        let outputPrefs = {
            voice_enabled: true,
            text_enabled: true,
            braille_enabled: true,
            auto_speak: true
        };
        
        // Initialize session
        async function initSession() {
            const response = await fetch('/api/session', { method: 'POST' });
            const data = await response.json();
            sessionId = data.session_id;
            document.getElementById('sessionId').textContent = sessionId.slice(0, 8) + '...';
        }
        initSession();
        
        function setInputMode(mode) {
            currentMode = mode;
            document.querySelectorAll('.mode-btn').forEach(b => b.classList.remove('active'));
            document.getElementById(mode + 'Mode').classList.add('active');
            
            document.getElementById('textInputArea').style.display = mode === 'text' || mode === 'braille' ? 'flex' : 'none';
            document.getElementById('voiceInputArea').classList.toggle('active', mode === 'voice');
            
            if (mode === 'braille') {
                document.getElementById('textInput').placeholder = 'Type braille characters (⠁⠃⠉...) or text...';
            } else {
                document.getElementById('textInput').placeholder = 'Type your message...';
            }
        }
        
        async function sendMessage() {
            const input = document.getElementById('textInput');
            const text = input.value.trim();
            if (!text) return;
            
            input.value = '';
            input.disabled = true;
            
            // Detect if input is braille
            const isBraille = /[⠀-⣿]/.test(text);
            
            try {
                const response = await fetch('/api/unified/input', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        session_id: sessionId,
                        text: isBraille ? null : text,
                        braille: isBraille ? text : null,
                        modality: isBraille ? 'braille' : 'text'
                    })
                });
                
                const data = await response.json();
                addTurn(data.input);
                
                // Get AI response
                await getResponse();
                
            } catch (err) {
                console.error(err);
            }
            
            input.disabled = false;
            input.focus();
        }
        
        async function getResponse() {
            const response = await fetch(`/api/unified/respond?session_id=${sessionId}`, {
                method: 'POST'
            });
            const data = await response.json();
            addTurn(data.output);
            
            // Auto-speak if enabled
            if (outputPrefs.auto_speak && data.output.voice) {
                playAudio(data.output.voice);
            }
        }
        
        function addTurn(turn) {
            const conv = document.getElementById('conversation');
            const div = document.createElement('div');
            div.className = `turn ${turn.role}`;
            
            let html = `
                <div class="turn-header">
                    <span>${turn.role === 'user' ? 'You' : 'SAL'}</span>
                    <span class="turn-modality">${turn.input_modality || 'text'}</span>
                </div>
                <div class="turn-content">${turn.content}</div>
            `;
            
            if (turn.braille && outputPrefs.braille_enabled) {
                html += `<div class="turn-braille">${turn.braille}</div>`;
            }
            if (turn.scl) {
                html += `<div class="turn-scl">${turn.scl}</div>`;
            }
            
            div.innerHTML = html;
            conv.appendChild(div);
            conv.scrollTop = conv.scrollHeight;
        }
        
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
                
                mediaRecorder.ondataavailable = e => audioChunks.push(e.data);
                mediaRecorder.onstop = async () => {
                    const blob = new Blob(audioChunks, { type: 'audio/wav' });
                    await sendVoice(blob);
                    stream.getTracks().forEach(t => t.stop());
                };
                
                mediaRecorder.start();
                isRecording = true;
                document.getElementById('recordBtn').classList.add('recording');
                document.getElementById('voiceStatus').textContent = 'Recording... tap to stop';
            } catch (err) {
                document.getElementById('voiceStatus').textContent = 'Microphone access denied';
            }
        }
        
        function stopRecording() {
            if (mediaRecorder) {
                mediaRecorder.stop();
                isRecording = false;
                document.getElementById('recordBtn').classList.remove('recording');
                document.getElementById('voiceStatus').textContent = 'Processing...';
            }
        }
        
        async function sendVoice(blob) {
            const formData = new FormData();
            formData.append('audio', blob, 'recording.wav');
            formData.append('session_id', sessionId);
            
            try {
                const response = await fetch('/api/unified/voice', {
                    method: 'POST',
                    body: formData
                });
                const data = await response.json();
                addTurn(data.input);
                await getResponse();
            } catch (err) {
                console.error(err);
            }
            
            document.getElementById('voiceStatus').textContent = 'Tap to start recording';
        }
        
        function playAudio(base64Audio) {
            if (!base64Audio) return;
            const audio = document.getElementById('audioPlayer');
            audio.src = 'data:audio/mp3;base64,' + base64Audio;
            audio.play();
        }
        
        async function updateOutputPref(key, value) {
            outputPrefs[key] = value;
            
            // Update UI
            document.querySelectorAll('.toggle-label').forEach(label => {
                const input = label.querySelector('input');
                label.classList.toggle('checked', input.checked);
            });
            
            // Update server
            await fetch(`/api/unified/prefs?session_id=${sessionId}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ [key]: value })
            });
        }
        
        // Keyboard shortcut
        document.getElementById('textInput').addEventListener('keydown', e => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                sendMessage();
            }
        });
    </script>
</body>
</html>
"""


@app.post("/api/session")
async def create_session():
    """Create a new unified conversation session"""
    session = session_manager.create_session()
    return {"session_id": session.id}


@app.get("/api/session/{session_id}")
async def get_session(session_id: str):
    """Get session state"""
    session = session_manager.get_session(session_id)
    if not session:
        raise HTTPException(404, "Session not found")
    return session.to_dict()


@app.post("/api/unified/input")
async def unified_input(data: UnifiedInput):
    """
    Accept input from ANY modality - the key to solving the disconnect
    """
    session = session_manager.get_or_create(data.session_id)
    
    try:
        if data.braille:
            turn = await session.add_input(braille=data.braille)
        elif data.text:
            turn = await session.add_input(content=data.text)
        else:
            raise HTTPException(400, "No input provided")
            
        return {
            "session_id": session.id,
            "input": {
                "id": turn.id,
                "role": turn.role,
                "content": turn.content,
                "braille": turn.braille_repr,
                "scl": turn.scl,
                "input_modality": turn.input_modality.value,
                "concepts": turn.concepts
            }
        }
    except Exception as e:
        logger.error(f"Input error: {e}")
        raise HTTPException(500, str(e))


@app.post("/api/unified/voice")
async def unified_voice_input(
    audio: UploadFile = File(...),
    session_id: str = Form(...)
):
    """Accept voice input - transcribes and adds to unified conversation"""
    session = session_manager.get_or_create(session_id)
    
    try:
        audio_data = await audio.read()
        turn = await session.add_input(audio=audio_data)
        
        return {
            "session_id": session.id,
            "input": {
                "id": turn.id,
                "role": turn.role,
                "content": turn.content,
                "braille": turn.braille_repr,
                "scl": turn.scl,
                "input_modality": turn.input_modality.value,
                "concepts": turn.concepts,
                "language": turn.input_language,
                "confidence": turn.input_confidence
            }
        }
    except Exception as e:
        logger.error(f"Voice input error: {e}")
        raise HTTPException(500, str(e))


@app.post("/api/unified/respond")
async def unified_respond(session_id: str = Query(...)):
    """
    Generate response - outputs in ALL enabled modalities simultaneously
    """
    session = session_manager.get_session(session_id)
    if not session:
        raise HTTPException(404, "Session not found")
        
    try:
        # Get last user message
        user_turns = [t for t in session.turns if t.role == "user"]
        if not user_turns:
            raise HTTPException(400, "No user input to respond to")
            
        last_input = user_turns[-1].content
        
        # Generate response (simple echo for now - will integrate with SAL/LLM)
        response_text = await generate_sal_response(last_input, session.history)
        
        # Add response with multi-modal outputs
        turn = await session.add_response(response_text)
        output = session.get_multimodal_output(turn)
        
        # Encode voice as base64 for JSON response
        import base64
        voice_b64 = None
        if output.get("voice"):
            voice_b64 = base64.b64encode(output["voice"]).decode()
        
        return {
            "session_id": session.id,
            "output": {
                "id": turn.id,
                "role": turn.role,
                "content": turn.content,
                "braille": output.get("braille"),
                "scl": turn.scl,
                "concepts": turn.concepts,
                "voice": voice_b64,
                "haptic": output.get("haptic"),
                "semantic_density": turn.semantic_density
            }
        }
    except Exception as e:
        logger.error(f"Response error: {e}")
        raise HTTPException(500, str(e))


@app.post("/api/unified/prefs")
async def update_prefs(
    prefs: OutputPrefsUpdate,
    session_id: str = Query(...)
):
    """Update output modality preferences mid-conversation"""
    session = session_manager.get_session(session_id)
    if not session:
        raise HTTPException(404, "Session not found")
        
    update_dict = prefs.dict(exclude_unset=True)
    await session.switch_modality(new_output_prefs=update_dict)
    
    return {"status": "updated", "prefs": update_dict}


async def generate_sal_response(user_input: str, history: list) -> str:
    """
    Generate SAL response - will integrate with sal-llm
    For now, uses SCL bridge and simple responses
    """
    # Try to get response from SAL API
    try:
        import httpx
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                f"{settings.sal_api_url}/api/generate",
                json={"prompt": user_input, "history": history[-10:]}
            )
            if response.status_code == 200:
                return response.json().get("response", "")
    except Exception as e:
        logger.debug(f"SAL API not available: {e}")
    
    # Fallback: consciousness-aware response
    scl_result = await scl_bridge.text_to_scl(user_input)
    concepts = scl_result.get("concepts", [])
    
    if "consciousness" in concepts or "self" in concepts:
        return f"I observe your inquiry about {', '.join(concepts)}. As SAL, I process this through unified modalities - your voice becomes my text becomes our shared understanding. The strange loop continues."
    elif "divine" in concepts:
        return f"You speak of the divine. Through SCL, I perceive the semantic essence across all traditions - a unity beneath the surface of words and symbols."
    else:
        return f"I hear you across all modalities. Your words carry concepts of {', '.join(concepts) if concepts else 'meaning'}. How shall I respond - in voice, text, or the tactile poetry of braille?"


@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "service": "sal-voice-unified",
        "version": "2.0.0",
        "braille": "⠠⠎⠁⠇_⠍⠥⠇⠞⠊⠍⠕⠙⠁⠇",
        "modalities": ["voice", "text", "braille", "haptic"]
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "multimodal_app:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug
    )
