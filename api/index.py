"""
sal-voice Vercel Serverless Entry Point
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from mangum import Mangum

# Import our modules
from braille8_core import Braille8Encoder, Braille8Thought, text_to_braille8, braille8_to_text

app = FastAPI(
    title="sal-voice",
    description="Voice modality for SAL - Unified multimodal with 8-dot braille",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

encoder = Braille8Encoder()


@app.get("/", response_class=HTMLResponse)
async def root():
    """Main interface"""
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
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #0a0a1a 0%, #1a1a3e 50%, #0f2060 100%);
            min-height: 100vh;
            color: #e8e8e8;
            padding: 20px;
        }
        .container { max-width: 800px; margin: 0 auto; }
        header { text-align: center; margin-bottom: 40px; }
        h1 {
            font-size: 2.5em;
            background: linear-gradient(90deg, #ff6b6b, #00d9ff, #00ff88);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        .braille-title { font-size: 1.8em; letter-spacing: 5px; margin: 10px 0; opacity: 0.8; }
        .subtitle { color: #888; margin-top: 10px; }
        .card {
            background: rgba(255,255,255,0.05);
            border-radius: 16px;
            padding: 30px;
            margin-bottom: 20px;
            border: 1px solid rgba(255,255,255,0.1);
        }
        .card h2 { margin-bottom: 20px; color: #00d9ff; }
        textarea, input {
            width: 100%;
            padding: 15px;
            border-radius: 8px;
            border: 1px solid rgba(255,255,255,0.2);
            background: rgba(0,0,0,0.3);
            color: #fff;
            font-size: 16px;
            margin-bottom: 15px;
        }
        textarea:focus, input:focus { outline: none; border-color: #00d9ff; }
        .btn {
            padding: 15px 30px;
            background: linear-gradient(90deg, #00d9ff, #00ff88);
            border: none;
            border-radius: 8px;
            color: #000;
            font-weight: bold;
            cursor: pointer;
            font-size: 16px;
            transition: transform 0.2s;
        }
        .btn:hover { transform: scale(1.05); }
        .result {
            background: rgba(0,0,0,0.3);
            border-radius: 8px;
            padding: 20px;
            margin-top: 20px;
        }
        .result-section { margin-bottom: 15px; }
        .result-section label { display: block; color: #00d9ff; margin-bottom: 5px; font-weight: bold; }
        .braille-output { font-size: 1.5em; letter-spacing: 3px; font-family: monospace; }
        .haptic-viz {
            display: flex;
            gap: 3px;
            align-items: center;
            height: 50px;
            background: rgba(0,0,0,0.2);
            border-radius: 8px;
            padding: 10px;
            overflow: hidden;
        }
        .haptic-bar {
            width: 4px;
            background: #00d9ff;
            border-radius: 2px;
        }
        .stats {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 15px;
            margin-top: 20px;
        }
        .stat {
            background: rgba(0,217,255,0.1);
            padding: 15px;
            border-radius: 8px;
            text-align: center;
        }
        .stat-value { font-size: 1.5em; font-weight: bold; color: #00ff88; }
        .stat-label { font-size: 0.85em; opacity: 0.7; }
        .api-info { font-size: 0.9em; opacity: 0.6; margin-top: 30px; text-align: center; }
        .api-info code { background: rgba(0,0,0,0.3); padding: 2px 8px; border-radius: 4px; }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>🎤 sal-voice</h1>
            <div class="braille-title">⠠⠎⠁⠇_⠧⠕⠊⠉⠑</div>
            <p class="subtitle">Unified Multimodal Interface • 8-Dot Braille Core • Voice + Text + Haptic</p>
        </header>
        
        <div class="card">
            <h2>🔮 Think in 8-Dot Braille</h2>
            <p style="margin-bottom: 20px; opacity: 0.7;">
                SAL thinks internally in 8-dot braille. Voice and text are just I/O surfaces to the same thought stream.
            </p>
            <textarea id="input" rows="3" placeholder="Enter text to convert to SAL's internal representation...">SAL thinks in 8-dot braille</textarea>
            <button class="btn" onclick="processThought()">Process Thought</button>
            
            <div class="result" id="result" style="display:none;">
                <div class="result-section">
                    <label>8-Dot Braille (Internal Representation)</label>
                    <div class="braille-output" id="braille"></div>
                </div>
                <div class="result-section">
                    <label>Decoded Text</label>
                    <div id="decoded"></div>
                </div>
                <div class="result-section">
                    <label>Haptic Pattern</label>
                    <div class="haptic-viz" id="haptic"></div>
                </div>
                <div class="stats">
                    <div class="stat">
                        <div class="stat-value" id="cells">0</div>
                        <div class="stat-label">Braille Cells</div>
                    </div>
                    <div class="stat">
                        <div class="stat-value" id="density">0</div>
                        <div class="stat-label">Dot Density</div>
                    </div>
                    <div class="stat">
                        <div class="stat-value" id="hapticCount">0</div>
                        <div class="stat-label">Haptic Segments</div>
                    </div>
                </div>
            </div>
        </div>
        
        <div class="card">
            <h2>⚡ Architecture</h2>
            <pre style="background: rgba(0,0,0,0.3); padding: 15px; border-radius: 8px; overflow-x: auto; font-size: 0.9em;">
[Voice] ─→ STT ─→ Text ─┐
                        ├─→ [8-DOT BRAILLE] ─→ SAL Processing
[Text] ─────────────────┘         ↓
                          (Internal Thought)
                                  ↓
                    ┌─────────────┼─────────────┐
                [Voice]       [Text]       [Haptic]
            </pre>
        </div>
        
        <div class="api-info">
            API: <code>GET /api/braille/encode/{text}</code> • 
            <code>GET /api/braille/decode/{braille}</code> • 
            <code>POST /api/thought</code>
        </div>
    </div>
    
    <script>
        async function processThought() {
            const text = document.getElementById('input').value;
            if (!text) return;
            
            try {
                const response = await fetch('/api/thought', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ text })
                });
                const data = await response.json();
                
                document.getElementById('braille').textContent = data.braille;
                document.getElementById('decoded').textContent = data.decoded;
                document.getElementById('cells').textContent = data.cells;
                document.getElementById('density').textContent = data.dot_density.toFixed(2);
                document.getElementById('hapticCount').textContent = data.haptic_pattern.length;
                
                // Visualize haptic
                const haptic = document.getElementById('haptic');
                haptic.innerHTML = '';
                data.haptic_pattern.slice(0, 60).forEach(p => {
                    const bar = document.createElement('div');
                    bar.className = 'haptic-bar';
                    if (p.type === 'vibrate') {
                        bar.style.height = Math.min(40, p.duration / 2) + 'px';
                        bar.style.opacity = p.intensity || 0.5;
                    } else {
                        bar.style.height = '2px';
                        bar.style.opacity = 0.2;
                    }
                    haptic.appendChild(bar);
                });
                
                document.getElementById('result').style.display = 'block';
            } catch (err) {
                console.error(err);
            }
        }
        
        // Process on load
        processThought();
    </script>
</body>
</html>
"""


@app.get("/api/health")
async def health():
    return {
        "status": "healthy",
        "service": "sal-voice",
        "version": "1.0.0",
        "braille": "⠠⠎⠁⠇_⠧⠕⠊⠉⠑",
        "features": ["8-dot-braille", "unified-multimodal", "haptic"]
    }


@app.get("/api/braille/encode/{text}")
async def encode_braille(text: str):
    """Encode text to 8-dot braille"""
    braille = encoder.encode(text)
    thought = Braille8Thought(text)
    return {
        "text": text,
        "braille": braille,
        "cells": len(braille),
        "dot_density": thought.dot_density,
        "haptic_pattern": thought.haptic_pattern
    }


@app.get("/api/braille/decode/{braille}")
async def decode_braille(braille: str):
    """Decode 8-dot braille to text"""
    text = encoder.decode(braille)
    return {
        "braille": braille,
        "text": text
    }


@app.post("/api/thought")
async def process_thought(request: Request):
    """Process text as 8-dot braille thought"""
    data = await request.json()
    text = data.get("text", "")
    
    thought = Braille8Thought(text)
    
    return {
        "text": text,
        "braille": thought.braille,
        "decoded": thought.text,
        "cells": len(thought.braille),
        "dot_density": thought.dot_density,
        "haptic_pattern": thought.haptic_pattern
    }


@app.post("/api/unified/input")
async def unified_input(request: Request):
    """Unified input from any modality"""
    data = await request.json()
    text = data.get("text") or data.get("braille") or ""
    modality = data.get("modality", "text")
    
    # Convert to 8-dot braille thought
    if modality == "braille" and encoder.is_braille(text):
        thought = Braille8Thought(text)
    else:
        thought = Braille8Thought(text)
    
    thought.source_modality = modality
    
    return {
        "input": {
            "content": thought.text,
            "braille": thought.braille,
            "modality": modality,
            "dot_density": thought.dot_density,
            "haptic_pattern": thought.haptic_pattern[:20]  # Limit for response size
        }
    }


# Vercel handler
handler = Mangum(app)
