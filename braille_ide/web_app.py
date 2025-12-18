"""
SAL 8-Dot Braille IDE Web Application

Beautiful web interface for the braille-substrate IDE.
"""

from flask import Flask, render_template_string, request, jsonify, send_from_directory, Response
from flask_cors import CORS
import sys
import os
import asyncio
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent))

from core import BrailleIDE, BrailleProject, BrailleFile, get_ide
from editor import BrailleCodeEditor
from interface import BrailleInterface, get_file_icon
from syntax import BrailleSyntaxHighlighter, TokenType
from completion import BrailleCodeCompletion, CompletionContext
from output import BrailleOutputRenderer, OutputType
from braille8_code import Language
from sal_integration import SALClient, sal_client, check_sal_available
from sal_cascade import SALCascade, sal_cascade
from graph_store import (
    get_store, get_graph_store, GraphStore, Node, Relationship,
    NodeType, RelationType, create_project_node, create_file_node,
    create_task_node, link_task_to_file
)

app = Flask(__name__)
CORS(app)

# Global instances
ide = get_ide()
interface = BrailleInterface()
highlighter = BrailleSyntaxHighlighter()
completion_engine = BrailleCodeCompletion()
output_renderer = BrailleOutputRenderer()
graph_store = get_store()  # Graph database

# Helper to run async functions
def run_async(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()

# Web interface HTML
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="description" content="SAL - The most accessible AI-powered coding environment. Screen reader optimized, braille native.">
    <title>⠎⠁⠇ SAL 8-Dot Braille IDE - Accessibility First</title>
    <link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;600&family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-primary: #0d1117;
            --bg-secondary: #161b22;
            --bg-tertiary: #21262d;
            --border-color: #30363d;
            --text-primary: #e6edf3;
            --text-secondary: #8b949e;
            --accent-blue: #58a6ff;
            --accent-green: #3fb950;
            --accent-purple: #a371f7;
            --accent-orange: #d29922;
            --accent-red: #f85149;
            --braille-highlight: #79c0ff;
        }
        
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Inter', system-ui, sans-serif;
            background: var(--bg-primary);
            color: var(--text-primary);
            height: 100vh;
            overflow: hidden;
        }
        
        .ide-container {
            display: grid;
            grid-template-rows: 48px 1fr 32px;
            height: 100vh;
        }
        
        /* Header */
        .header {
            background: var(--bg-secondary);
            border-bottom: 1px solid var(--border-color);
            display: flex;
            align-items: center;
            padding: 0 16px;
            gap: 16px;
        }
        
        .logo {
            display: flex;
            align-items: center;
            gap: 8px;
            font-weight: 600;
        }
        
        .logo-braille {
            font-size: 24px;
            color: var(--accent-blue);
        }
        
        .menu-bar {
            display: flex;
            gap: 4px;
        }
        
        .menu-item {
            padding: 6px 12px;
            border-radius: 6px;
            cursor: pointer;
            display: flex;
            align-items: center;
            gap: 6px;
            font-size: 13px;
            transition: background 0.15s;
        }
        
        .menu-item:hover {
            background: var(--bg-tertiary);
        }
        
        .menu-braille {
            font-size: 16px;
            color: var(--accent-purple);
        }
        
        /* Main content */
        .main-content {
            display: grid;
            grid-template-columns: 240px 1fr 300px;
            overflow: hidden;
        }
        
        /* Sidebar */
        .sidebar {
            background: var(--bg-secondary);
            border-right: 1px solid var(--border-color);
            display: flex;
            flex-direction: column;
        }
        
        .sidebar-header {
            padding: 12px 16px;
            font-size: 11px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            color: var(--text-secondary);
            border-bottom: 1px solid var(--border-color);
        }
        
        .file-tree {
            flex: 1;
            overflow-y: auto;
            padding: 8px;
        }
        
        .file-item {
            display: flex;
            align-items: center;
            gap: 8px;
            padding: 6px 8px;
            border-radius: 6px;
            cursor: pointer;
            font-size: 13px;
            transition: background 0.15s;
        }
        
        .file-item:hover {
            background: var(--bg-tertiary);
        }
        
        .file-item.active {
            background: var(--bg-tertiary);
            border-left: 2px solid var(--accent-blue);
        }
        
        .file-icon {
            color: var(--accent-orange);
            font-size: 14px;
        }
        
        /* Editor */
        .editor-area {
            display: flex;
            flex-direction: column;
            overflow: hidden;
        }
        
        .editor-tabs {
            display: flex;
            background: var(--bg-secondary);
            border-bottom: 1px solid var(--border-color);
            overflow-x: auto;
        }
        
        .editor-tab {
            padding: 10px 16px;
            font-size: 13px;
            border-right: 1px solid var(--border-color);
            cursor: pointer;
            display: flex;
            align-items: center;
            gap: 8px;
            white-space: nowrap;
        }
        
        .editor-tab.active {
            background: var(--bg-primary);
            border-bottom: 2px solid var(--accent-blue);
        }
        
        .editor-content {
            flex: 1;
            display: grid;
            grid-template-rows: 1fr 200px;
            overflow: hidden;
        }
        
        .code-editor {
            display: flex;
            overflow: hidden;
        }
        
        .line-numbers {
            padding: 16px 8px;
            background: var(--bg-secondary);
            border-right: 1px solid var(--border-color);
            font-family: 'JetBrains Mono', monospace;
            font-size: 13px;
            color: var(--text-secondary);
            text-align: right;
            user-select: none;
            min-width: 50px;
        }
        
        .code-area {
            flex: 1;
            padding: 16px;
            overflow: auto;
            font-family: 'JetBrains Mono', monospace;
            font-size: 14px;
            line-height: 1.6;
        }
        
        .code-input {
            width: 100%;
            height: 100%;
            background: transparent;
            border: none;
            color: var(--text-primary);
            font-family: inherit;
            font-size: inherit;
            line-height: inherit;
            resize: none;
            outline: none;
        }
        
        /* Braille display */
        .braille-display {
            padding: 16px;
            background: var(--bg-tertiary);
            border-radius: 8px;
            margin: 8px;
            font-size: 20px;
            letter-spacing: 2px;
            color: var(--braille-highlight);
            min-height: 60px;
            font-family: 'Segoe UI Symbol', sans-serif;
        }
        
        /* Output panel */
        .output-panel {
            background: var(--bg-secondary);
            border-top: 1px solid var(--border-color);
            display: flex;
            flex-direction: column;
        }
        
        .output-header {
            padding: 8px 16px;
            font-size: 12px;
            font-weight: 600;
            border-bottom: 1px solid var(--border-color);
            display: flex;
            align-items: center;
            gap: 8px;
        }
        
        .output-content {
            flex: 1;
            overflow-y: auto;
            padding: 12px 16px;
            font-family: 'JetBrains Mono', monospace;
            font-size: 12px;
        }
        
        .output-line {
            padding: 2px 0;
        }
        
        .output-line.error {
            color: var(--accent-red);
        }
        
        .output-line.success {
            color: var(--accent-green);
        }
        
        .output-line.system {
            color: var(--text-secondary);
        }
        
        /* Right panel */
        .right-panel {
            background: var(--bg-secondary);
            border-left: 1px solid var(--border-color);
            display: flex;
            flex-direction: column;
        }
        
        .panel-section {
            border-bottom: 1px solid var(--border-color);
        }
        
        .panel-header {
            padding: 12px 16px;
            font-size: 12px;
            font-weight: 600;
            display: flex;
            align-items: center;
            justify-content: space-between;
        }
        
        .panel-content {
            padding: 12px 16px;
        }
        
        /* Completions */
        .completion-list {
            max-height: 200px;
            overflow-y: auto;
        }
        
        .completion-item {
            padding: 6px 8px;
            border-radius: 4px;
            cursor: pointer;
            display: flex;
            align-items: center;
            gap: 8px;
            font-size: 13px;
        }
        
        .completion-item:hover, .completion-item.selected {
            background: var(--bg-tertiary);
        }
        
        .completion-icon {
            width: 20px;
            height: 20px;
            border-radius: 4px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 11px;
            font-weight: 600;
        }
        
        .completion-icon.keyword { background: var(--accent-purple); }
        .completion-icon.function { background: var(--accent-blue); }
        .completion-icon.type { background: var(--accent-green); }
        .completion-icon.snippet { background: var(--accent-orange); }
        
        /* Accessibility */
        .sr-only {
            position: absolute;
            width: 1px;
            height: 1px;
            padding: 0;
            margin: -1px;
            overflow: hidden;
            clip: rect(0, 0, 0, 0);
            border: 0;
        }
        
        .skip-link {
            position: absolute;
            left: -9999px;
            z-index: 9999;
            padding: 8px 16px;
            background: var(--accent-blue);
            color: white;
            text-decoration: none;
            border-radius: 4px;
        }
        
        .skip-link:focus {
            left: 8px;
            top: 8px;
        }
        
        :focus-visible {
            outline: 2px solid var(--accent-blue);
            outline-offset: 2px;
        }
        
        @media (prefers-contrast: high) {
            :root {
                --bg-primary: #000;
                --text-primary: #fff;
                --border-color: #fff;
            }
        }
        
        @media (prefers-reduced-motion: reduce) {
            * { animation: none !important; transition: none !important; }
        }
        
        /* Status bar */
        .status-bar {
            background: var(--bg-secondary);
            border-top: 1px solid var(--border-color);
            display: flex;
            align-items: center;
            padding: 0 16px;
            font-size: 12px;
            color: var(--text-secondary);
            gap: 16px;
        }
        
        .status-item {
            display: flex;
            align-items: center;
            gap: 4px;
        }
        
        .status-braille {
            color: var(--accent-blue);
        }
        
        /* Command palette */
        .command-palette {
            position: fixed;
            top: 100px;
            left: 50%;
            transform: translateX(-50%);
            width: 500px;
            background: var(--bg-secondary);
            border: 1px solid var(--border-color);
            border-radius: 12px;
            box-shadow: 0 20px 40px rgba(0,0,0,0.5);
            display: none;
            z-index: 1000;
        }
        
        .command-palette.active {
            display: block;
        }
        
        .command-input {
            width: 100%;
            padding: 16px;
            background: transparent;
            border: none;
            border-bottom: 1px solid var(--border-color);
            color: var(--text-primary);
            font-size: 16px;
            outline: none;
        }
        
        .command-results {
            max-height: 300px;
            overflow-y: auto;
        }
        
        .command-item {
            padding: 12px 16px;
            cursor: pointer;
            display: flex;
            align-items: center;
            gap: 12px;
        }
        
        .command-item:hover {
            background: var(--bg-tertiary);
        }
        
        /* Syntax highlighting colors */
        .token-keyword { color: #ff7b72; }
        .token-builtin { color: #ffa657; }
        .token-type { color: #79c0ff; }
        .token-string { color: #a5d6ff; }
        .token-number { color: #79c0ff; }
        .token-comment { color: #8b949e; font-style: italic; }
        .token-function { color: #d2a8ff; }
        .token-operator { color: #ff7b72; }
        
        /* Buttons */
        .btn {
            padding: 8px 16px;
            border-radius: 6px;
            border: 1px solid var(--border-color);
            background: var(--bg-tertiary);
            color: var(--text-primary);
            cursor: pointer;
            font-size: 13px;
            transition: all 0.15s;
        }
        
        .btn:hover {
            background: var(--bg-secondary);
            border-color: var(--accent-blue);
        }
        
        .btn-primary {
            background: var(--accent-blue);
            border-color: var(--accent-blue);
            color: white;
        }
        
        .btn-primary:hover {
            background: #4c9aed;
        }
        
        /* Language selector */
        .language-selector {
            padding: 4px 8px;
            background: var(--bg-tertiary);
            border: 1px solid var(--border-color);
            border-radius: 4px;
            color: var(--text-primary);
            font-size: 12px;
        }
        
        /* Braille mode toggle */
        .braille-toggle {
            display: flex;
            align-items: center;
            gap: 8px;
            padding: 8px 12px;
            background: var(--bg-tertiary);
            border-radius: 6px;
        }
        
        .toggle-switch {
            width: 40px;
            height: 20px;
            background: var(--border-color);
            border-radius: 10px;
            cursor: pointer;
            position: relative;
            transition: background 0.2s;
        }
        
        .toggle-switch.active {
            background: var(--accent-blue);
        }
        
        .toggle-switch::after {
            content: '';
            width: 16px;
            height: 16px;
            background: white;
            border-radius: 50%;
            position: absolute;
            top: 2px;
            left: 2px;
            transition: left 0.2s;
        }
        
        .toggle-switch.active::after {
            left: 22px;
        }
        
        /* Keyboard hints */
        .kbd {
            padding: 2px 6px;
            background: var(--bg-tertiary);
            border: 1px solid var(--border-color);
            border-radius: 4px;
            font-family: 'JetBrains Mono', monospace;
            font-size: 11px;
        }
    </style>
</head>
<body>
    <div class="ide-container">
        <!-- Header -->
        <header class="header">
            <div class="logo">
                <span class="logo-braille">⠎⠁⠇</span>
                <span>SAL 8-Dot Braille IDE</span>
            </div>
            
            <div class="menu-bar">
                <div class="menu-item" onclick="executeCommand('new')">
                    <span class="menu-braille">⠁</span>
                    <span>New</span>
                </div>
                <div class="menu-item" onclick="createFile()">
                    <span class="menu-braille">⠉</span>
                    <span>File</span>
                </div>
                <div class="menu-item" onclick="saveProject()">
                    <span class="menu-braille">⠑</span>
                    <span>Save</span>
                </div>
                <div class="menu-item" onclick="runCode()">
                    <span class="menu-braille">⠕</span>
                    <span>Run</span>
                </div>
                <div class="menu-item" onclick="toggleCommandPalette()">
                    <span class="menu-braille">⠒</span>
                    <span>Commands</span>
                    <span class="kbd">⌘K</span>
                </div>
            </div>
            
            <div style="flex: 1;"></div>
            
            <div class="braille-toggle">
                <span>Braille Mode</span>
                <div class="toggle-switch active" id="brailleToggle" onclick="toggleBrailleMode()"></div>
            </div>
            
            <select class="language-selector" id="languageSelect" onchange="changeLanguage()">
                <option value="python">Python</option>
                <option value="rust">Rust</option>
                <option value="go">Go</option>
                <option value="javascript">JavaScript</option>
                <option value="typescript">TypeScript</option>
                <option value="sql">SQL</option>
                <option value="java">Java</option>
            </select>
        </header>
        
        <!-- Main Content -->
        <main class="main-content">
            <!-- Sidebar - File Browser -->
            <aside class="sidebar">
                <!-- Quick Access -->
                <div class="sidebar-header" style="display: flex; justify-content: space-between; align-items: center;">
                    <span>📁 Files</span>
                    <button class="btn" onclick="goToParent()" style="padding: 2px 6px; font-size: 10px;">↑</button>
                </div>
                
                <!-- Current Path -->
                <div id="currentPath" style="padding: 4px 12px; font-size: 10px; color: var(--text-secondary); border-bottom: 1px solid var(--border-color); white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">
                    ~
                </div>
                
                <!-- Quick Access Buttons -->
                <div id="quickAccess" style="padding: 8px; border-bottom: 1px solid var(--border-color); display: flex; flex-wrap: wrap; gap: 4px;">
                    <button class="btn" onclick="browsePath('~')" style="padding: 2px 6px; font-size: 10px;">🏠 Home</button>
                    <button class="btn" onclick="browsePath('~/sal-voice')" style="padding: 2px 6px; font-size: 10px;">⠎ sal-voice</button>
                    <button class="btn" onclick="browsePath('~/CascadeProjects')" style="padding: 2px 6px; font-size: 10px;">📂 Projects</button>
                </div>
                
                <!-- File Tree -->
                <div class="file-tree" id="fileTree" style="flex: 1; overflow-y: auto;">
                    <!-- Files populated dynamically -->
                </div>
                
                <!-- Actions -->
                <div style="padding: 8px; border-top: 1px solid var(--border-color);">
                    <button class="btn" onclick="createFile()" style="width: 100%; margin-bottom: 4px;">
                        <span>⠉</span> New File
                    </button>
                    <button class="btn" onclick="saveFileToDisk()" style="width: 100%;">
                        <span>💾</span> Save to Disk
                    </button>
                </div>
            </aside>
            
            <!-- Editor -->
            <section class="editor-area">
                <div class="editor-tabs" id="editorTabs">
                    <!-- Tabs populated dynamically -->
                </div>
                
                <div class="editor-content">
                    <div class="code-editor">
                        <div class="line-numbers" id="lineNumbers">1</div>
                        <div class="code-area">
                            <textarea class="code-input" id="codeInput" 
                                      placeholder="Start typing code..." 
                                      spellcheck="false"
                                      oninput="handleInput()"
                                      onkeydown="handleKeyDown(event)"
                                      role="textbox"
                                      aria-multiline="true"
                                      aria-label="Code editor. Press Control+Slash to hear current line. Press F6 to navigate panels."></textarea>
                        </div>
                    </div>
                    
                    <!-- Braille Display -->
                    <div style="padding: 8px;">
                        <div class="braille-display" id="brailleDisplay">
                            ⠎⠁⠇ ⠠⠃⠗⠁⠊⠇⠇⠑ ⠠⠊⠙⠑ - Type code to see braille representation
                        </div>
                    </div>
                    
                    <!-- Output Panel -->
                    <div class="output-panel">
                        <div class="output-header">
                            <span>⠕</span> Output
                            <span style="flex:1"></span>
                            <button class="btn" onclick="clearOutput()" style="padding: 4px 8px; font-size: 11px;">Clear</button>
                        </div>
                        <div class="output-content" id="outputContent">
                            <div class="output-line system">⠎⠁⠇ SAL Braille IDE ready. Type 'help' for commands.</div>
                        </div>
                    </div>
                </div>
            </section>
            
            <!-- Right Panel - SAL Cascade (Autonomous Coding) -->
            <aside class="right-panel">
                <!-- Cascade Mode Toggle -->
                <div class="panel-section" style="padding: 8px 12px; background: linear-gradient(135deg, rgba(163,113,247,0.15), rgba(88,166,255,0.15));">
                    <div style="display: flex; align-items: center; justify-content: space-between;">
                        <div>
                            <div style="font-weight: 600; font-size: 14px;">⠎⠁⠇ SAL Cascade</div>
                            <div style="font-size: 10px; color: var(--text-secondary);">Autonomous Coding Mode</div>
                        </div>
                        <div class="toggle-switch active" id="cascadeToggle" onclick="toggleCascadeMode()" title="SAL writes all code"></div>
                    </div>
                    <div id="cascadeStatus" style="margin-top: 8px; font-size: 11px; color: var(--accent-green);">
                        ● SAL is the coder. Describe what you want.
                    </div>
                </div>
                
                <!-- SAL Cascade Chat -->
                <div class="panel-section" style="flex: 2; display: flex; flex-direction: column;">
                    <div class="panel-header">
                        <span>💬 Tell SAL What to Build</span>
                        <span id="salStatus" style="font-size: 10px; color: var(--accent-green);">● Online</span>
                    </div>
                    <div class="panel-content" style="flex: 1; display: flex; flex-direction: column; padding: 0;">
                        <div id="salChat" style="flex: 1; overflow-y: auto; padding: 12px; font-size: 13px; max-height: 300px;">
                            <div class="sal-message sal" style="background: rgba(63, 185, 80, 0.1); padding: 10px; border-radius: 8px; margin-bottom: 8px;">
                                <div style="color: var(--accent-green); margin-bottom: 4px; font-size: 11px;">⠎⠁⠇ SAL Cascade</div>
                                <div>⠎⠁⠇_⠉⠁⠎⠉⠁⠙⠑_⠁⠉⠞⠊⠧⠑
                                    <br><br>I am SAL Cascade. <strong>I write ALL the code.</strong>
                                    <br><br>Tell me what you want to build:
                                    <br>• "Create a web scraper for news sites"
                                    <br>• "Build a REST API with user auth"
                                    <br>• "Make a data visualization dashboard"
                                    <br><br>I'll understand → plan → code → verify.
                                    <br><br><em style="color: var(--text-secondary);">Human code is messy. I keep it clean.</em></div>
                            </div>
                        </div>
                        <div style="padding: 8px; border-top: 1px solid var(--border-color);">
                            <textarea id="cascadeInput" placeholder="Describe what you want to build... (SAL writes the code)" 
                                   style="width: 100%; padding: 10px; background: var(--bg-tertiary); border: 1px solid var(--border-color); border-radius: 6px; color: var(--text-primary); font-size: 13px; resize: none; min-height: 60px;"
                                   onkeydown="if(event.key==='Enter' && !event.shiftKey){event.preventDefault();sendCascadeIntent();}"></textarea>
                            <div style="display: flex; gap: 8px; margin-top: 8px;">
                                <button class="btn btn-primary" onclick="sendCascadeIntent()" style="flex: 1;">
                                    ⠎⠁⠇ Build It
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
                
                <!-- Current Task Status -->
                <div class="panel-section" id="taskPanel" style="display: none;">
                    <div class="panel-header">
                        <span>📋 Current Task</span>
                    </div>
                    <div class="panel-content" id="taskStatus" style="font-size: 12px;">
                    </div>
                </div>
                
                <!-- Quick Help -->
                <div class="panel-section">
                    <div class="panel-header">
                        <span>⠓ How It Works</span>
                    </div>
                    <div class="panel-content" style="font-size: 11px;">
                        <div style="display: grid; gap: 4px; color: var(--text-secondary);">
                            <div>1. You describe what you want</div>
                            <div>2. SAL understands your intent</div>
                            <div>3. SAL creates a plan</div>
                            <div>4. SAL writes clean code</div>
                            <div>5. SAL verifies it works</div>
                        </div>
                        <div style="margin-top: 8px; padding-top: 8px; border-top: 1px solid var(--border-color); color: var(--accent-purple);">
                            ⚡ The editor is read-only. SAL codes.
                        </div>
                    </div>
                </div>
            </aside>
        </main>
        
        <!-- Status Bar -->
        <footer class="status-bar">
            <div class="status-item">
                <span class="status-braille">⠇</span>
                <span>Ln <span id="cursorLine">1</span>, Col <span id="cursorCol">1</span></span>
            </div>
            <div class="status-item">
                <span class="status-braille">⠏⠽</span>
                <span id="currentLanguage">Python</span>
            </div>
            <div class="status-item">
                <span class="status-braille">⠎⠁⠧</span>
                <span id="saveStatus">Saved</span>
            </div>
            <div style="flex: 1;"></div>
            <div class="status-item">
                <span>⠎⠁⠇ SAL Braille IDE v1.0</span>
            </div>
        </footer>
    </div>
    
    <!-- Command Palette -->
    <div class="command-palette" id="commandPalette">
        <input type="text" class="command-input" id="commandInput" 
               placeholder="⠒ Type a command or search..." 
               oninput="searchCommands()">
        <div class="command-results" id="commandResults">
            <!-- Results populated dynamically -->
        </div>
    </div>
    
    <script>
        // State
        let brailleMode = true;
        let currentLanguage = 'python';
        let projectId = null;
        let activeFileId = null;
        let completionIndex = 0;
        
        // Initialize
        document.addEventListener('DOMContentLoaded', async () => {
            await initializeIDE();
            setupKeyboardShortcuts();
        });
        
        async function initializeIDE() {
            // Create default project if needed
            try {
                const response = await fetch('/api/status');
                const data = await response.json();
                
                if (!data.project) {
                    await fetch('/api/command', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({command: 'new Default Project'})
                    });
                }
                
                await refreshState();
            } catch (e) {
                console.error('Init error:', e);
                addOutput('Failed to initialize IDE', 'error');
            }
        }
        
        async function refreshState() {
            const response = await fetch('/api/status');
            const data = await response.json();
            
            if (data.project) {
                projectId = data.project.id;
                updateFileTree(data.project.files || {});
            }
            
            if (data.file) {
                activeFileId = data.file.id;
                document.getElementById('codeInput').value = data.file.content_text || '';
                updateBrailleDisplay(data.file.content_text || '');
                updateLineNumbers();
                document.getElementById('currentLanguage').textContent = data.file.language || 'Python';
            }
        }
        
        function updateFileTree(files) {
            const tree = document.getElementById('fileTree');
            tree.innerHTML = '';
            
            for (const [id, file] of Object.entries(files)) {
                const item = document.createElement('div');
                item.className = 'file-item' + (id === activeFileId ? ' active' : '');
                item.innerHTML = `
                    <span class="file-icon">${getFileIcon(file.name)}</span>
                    <span>${file.name}</span>
                `;
                item.onclick = () => openFile(id);
                tree.appendChild(item);
            }
        }
        
        function getFileIcon(filename) {
            const icons = {
                '.py': '⠏⠽', '.rs': '⠗⠎', '.go': '⠛⠕',
                '.js': '⠚⠎', '.ts': '⠞⠎', '.java': '⠚⠧',
                '.sql': '⠎⠟', '.c': '⠉', '.cpp': '⠉⠏'
            };
            for (const [ext, icon] of Object.entries(icons)) {
                if (filename.endsWith(ext)) return icon;
            }
            return '⠶';
        }
        
        async function openFile(fileId) {
            const response = await fetch('/api/open-file', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({file_id: fileId})
            });
            await refreshState();
        }
        
        async function createFile() {
            const name = prompt('File name:', 'untitled.py');
            if (name) {
                const response = await fetch('/api/command', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({command: `create ${name}`})
                });
                const data = await response.json();
                addOutput(data.result_text || 'File created', 'success');
                await refreshState();
            }
        }
        
        async function saveProject() {
            const content = document.getElementById('codeInput').value;
            await fetch('/api/update-content', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({content: content})
            });
            
            await fetch('/api/command', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({command: 'save'})
            });
            
            document.getElementById('saveStatus').textContent = 'Saved';
            addOutput('⠎⠁⠧ Project saved', 'success');
        }
        
        async function runCode() {
            const content = document.getElementById('codeInput').value;
            const language = document.getElementById('languageSelect').value;
            
            addOutput('⠗⠥⠝ Running code...', 'system');
            
            const response = await fetch('/api/run', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({code: content, language: language})
            });
            
            const data = await response.json();
            
            if (data.stdout) {
                data.stdout.split('\\n').forEach(line => addOutput(line, 'stdout'));
            }
            if (data.stderr) {
                data.stderr.split('\\n').forEach(line => addOutput(line, 'error'));
            }
            
            addOutput(data.success ? '⠎⠥⠉ Completed' : '⠑⠗⠗ Failed', data.success ? 'success' : 'error');
        }
        
        async function handleInput() {
            const code = document.getElementById('codeInput').value;
            
            // Update braille display
            updateBrailleDisplay(code);
            
            // Update line numbers
            updateLineNumbers();
            
            // Mark as modified
            document.getElementById('saveStatus').textContent = 'Modified';
            
            // Get completions
            await getCompletions();
        }
        
        function updateBrailleDisplay(text) {
            if (!brailleMode) {
                document.getElementById('brailleDisplay').textContent = text;
                return;
            }
            
            fetch('/api/to-braille', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({text: text})
            })
            .then(r => r.json())
            .then(data => {
                document.getElementById('brailleDisplay').textContent = data.braille || '⠀';
            });
        }
        
        function updateLineNumbers() {
            const code = document.getElementById('codeInput').value;
            const lines = code.split('\\n').length;
            const lineNums = Array.from({length: lines}, (_, i) => i + 1).join('\\n');
            document.getElementById('lineNumbers').textContent = lineNums;
        }
        
        async function getCompletions() {
            const code = document.getElementById('codeInput').value;
            const textarea = document.getElementById('codeInput');
            const pos = textarea.selectionStart;
            const language = document.getElementById('languageSelect').value;
            
            // Get current line and column
            const beforeCursor = code.substring(0, pos);
            const lines = beforeCursor.split('\\n');
            const currentLine = lines[lines.length - 1];
            const col = currentLine.length;
            
            const response = await fetch('/api/completions', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    line: currentLine,
                    col: col,
                    language: language,
                    file_content: code
                })
            });
            
            const data = await response.json();
            renderCompletions(data.completions || []);
        }
        
        function renderCompletions(completions) {
            const list = document.getElementById('completionList');
            list.innerHTML = '';
            
            completions.slice(0, 8).forEach((comp, i) => {
                const item = document.createElement('div');
                item.className = 'completion-item' + (i === completionIndex ? ' selected' : '');
                
                const iconClass = {
                    'keyword': 'keyword',
                    'function': 'function',
                    'type': 'type',
                    'snippet': 'snippet'
                }[comp.kind] || '';
                
                item.innerHTML = `
                    <span class="completion-icon ${iconClass}">${comp.braille_icon}</span>
                    <span>${comp.label}</span>
                    <span style="color: var(--text-secondary); font-size: 11px;">${comp.braille}</span>
                `;
                item.onclick = () => applyCompletion(comp);
                list.appendChild(item);
            });
        }
        
        function applyCompletion(comp) {
            const textarea = document.getElementById('codeInput');
            const pos = textarea.selectionStart;
            const code = textarea.value;
            
            // Find word start
            let start = pos;
            while (start > 0 && /\\w/.test(code[start-1])) start--;
            
            const insertText = comp.insert_text || comp.label;
            const newCode = code.substring(0, start) + insertText + code.substring(pos);
            textarea.value = newCode;
            textarea.selectionStart = textarea.selectionEnd = start + insertText.length;
            
            handleInput();
        }
        
        function handleKeyDown(event) {
            // Update cursor position
            setTimeout(() => {
                const textarea = document.getElementById('codeInput');
                const pos = textarea.selectionStart;
                const beforeCursor = textarea.value.substring(0, pos);
                const lines = beforeCursor.split('\\n');
                
                document.getElementById('cursorLine').textContent = lines.length;
                document.getElementById('cursorCol').textContent = lines[lines.length-1].length + 1;
            }, 0);
            
            // Tab key for completion
            if (event.key === 'Tab' && document.getElementById('completionList').children.length > 0) {
                event.preventDefault();
                const items = document.getElementById('completionList').querySelectorAll('.completion-item');
                if (items[completionIndex]) {
                    items[completionIndex].click();
                }
            }
        }
        
        function setupKeyboardShortcuts() {
            document.addEventListener('keydown', async (e) => {
                // Command palette
                if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
                    e.preventDefault();
                    toggleCommandPalette();
                }
                
                // Save
                if ((e.metaKey || e.ctrlKey) && e.key === 's') {
                    e.preventDefault();
                    await saveProject();
                }
                
                // Run
                if ((e.metaKey || e.ctrlKey) && e.key === 'Enter') {
                    e.preventDefault();
                    await runCode();
                }
                
                // Escape to close palette
                if (e.key === 'Escape') {
                    document.getElementById('commandPalette').classList.remove('active');
                }
            });
        }
        
        function toggleCommandPalette() {
            const palette = document.getElementById('commandPalette');
            palette.classList.toggle('active');
            if (palette.classList.contains('active')) {
                document.getElementById('commandInput').focus();
                searchCommands();
            }
        }
        
        async function searchCommands() {
            const query = document.getElementById('commandInput').value;
            
            const response = await fetch('/api/commands');
            const data = await response.json();
            
            const filtered = data.commands.filter(cmd => 
                cmd.text_label.toLowerCase().includes(query.toLowerCase()) ||
                cmd.braille_icon.includes(query)
            );
            
            const results = document.getElementById('commandResults');
            results.innerHTML = '';
            
            filtered.slice(0, 10).forEach(cmd => {
                const item = document.createElement('div');
                item.className = 'command-item';
                item.innerHTML = `
                    <span style="font-size: 18px;">${cmd.braille_icon}</span>
                    <span>${cmd.text_label}</span>
                    <span style="flex:1"></span>
                    <span class="kbd">${cmd.shortcut || ''}</span>
                `;
                item.onclick = () => {
                    executeCommand(cmd.id);
                    toggleCommandPalette();
                };
                results.appendChild(item);
            });
        }
        
        async function executeCommand(cmdId) {
            const response = await fetch('/api/command', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({command: cmdId})
            });
            
            const data = await response.json();
            addOutput(data.result_text || cmdId, 'system');
            await refreshState();
        }
        
        function toggleBrailleMode() {
            brailleMode = !brailleMode;
            document.getElementById('brailleToggle').classList.toggle('active', brailleMode);
            handleInput();
        }
        
        function changeLanguage() {
            currentLanguage = document.getElementById('languageSelect').value;
            document.getElementById('currentLanguage').textContent = 
                currentLanguage.charAt(0).toUpperCase() + currentLanguage.slice(1);
            getCompletions();
        }
        
        function addOutput(text, type = 'stdout') {
            const content = document.getElementById('outputContent');
            const line = document.createElement('div');
            line.className = 'output-line ' + type;
            line.textContent = text;
            content.appendChild(line);
            content.scrollTop = content.scrollHeight;
        }
        
        function clearOutput() {
            document.getElementById('outputContent').innerHTML = 
                '<div class="output-line system">⠎⠁⠇ Output cleared</div>';
        }
        
        // ============================================
        // SAL AI Assistant Functions
        // ============================================
        
        let salThinking = false;
        
        async function checkSalStatus() {
            try {
                const response = await fetch('/api/sal/status');
                const data = await response.json();
                const statusEl = document.getElementById('salStatus');
                if (data.available) {
                    statusEl.textContent = '● Online';
                    statusEl.style.color = 'var(--accent-green)';
                } else {
                    statusEl.textContent = '○ Offline';
                    statusEl.style.color = 'var(--text-secondary)';
                }
            } catch (e) {
                document.getElementById('salStatus').textContent = '○ Offline';
            }
        }
        
        async function sendToSal() {
            const input = document.getElementById('salInput');
            const message = input.value.trim();
            if (!message || salThinking) return;
            
            input.value = '';
            addSalMessage('user', message);
            
            salThinking = true;
            addSalMessage('thinking', '⠎⠁⠇ is thinking in braille...');
            
            try {
                const response = await fetch('/api/sal/chat', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        message: message,
                        include_file: true
                    })
                });
                
                const data = await response.json();
                
                // Remove thinking indicator
                removeSalThinking();
                
                // Add SAL response
                addSalMessage('sal', data.text, data.code_blocks);
                
            } catch (e) {
                removeSalThinking();
                addSalMessage('sal', '⠑⠗⠗ Error connecting to SAL. Is Ollama running?');
            }
            
            salThinking = false;
        }
        
        function addSalMessage(role, content, codeBlocks = []) {
            const chat = document.getElementById('salChat');
            const div = document.createElement('div');
            div.className = 'sal-message ' + role;
            div.style.marginBottom = '12px';
            div.style.padding = '8px';
            div.style.borderRadius = '8px';
            
            if (role === 'user') {
                div.style.background = 'rgba(88, 166, 255, 0.1)';
                div.style.marginLeft = '20px';
                div.innerHTML = `
                    <div style="color: var(--accent-blue); margin-bottom: 4px; font-size: 11px;">You</div>
                    <div>${content}</div>
                `;
            } else if (role === 'thinking') {
                div.id = 'salThinking';
                div.style.color = 'var(--text-secondary)';
                div.style.fontStyle = 'italic';
                div.innerHTML = content;
            } else {
                div.style.background = 'rgba(63, 185, 80, 0.1)';
                
                // Format code blocks
                let formatted = content
                    .replace(/```(\\w*)\\n([\\s\\S]*?)```/g, '<pre style="background: var(--bg-primary); padding: 8px; border-radius: 4px; margin: 8px 0; overflow-x: auto;"><code>$2</code></pre>')
                    .replace(/`([^`]+)`/g, '<code style="background: var(--bg-primary); padding: 2px 4px; border-radius: 2px;">$1</code>')
                    .replace(/\\n/g, '<br>');
                
                div.innerHTML = `
                    <div style="color: var(--accent-green); margin-bottom: 4px; font-size: 11px;">⠎⠁⠇ SAL</div>
                    <div>${formatted}</div>
                `;
                
                // Add code blocks with insert button
                if (codeBlocks && codeBlocks.length > 0) {
                    codeBlocks.forEach((block, i) => {
                        const codeDiv = document.createElement('div');
                        codeDiv.style.marginTop = '8px';
                        codeDiv.innerHTML = `
                            <button class="btn" onclick="insertCode(\`${block.code.replace(/`/g, '\\`')}\`)" 
                                    style="font-size: 10px; padding: 2px 8px;">Insert Code</button>
                        `;
                        div.appendChild(codeDiv);
                    });
                }
            }
            
            chat.appendChild(div);
            chat.scrollTop = chat.scrollHeight;
        }
        
        function removeSalThinking() {
            const thinking = document.getElementById('salThinking');
            if (thinking) thinking.remove();
        }
        
        function insertCode(code) {
            const textarea = document.getElementById('codeInput');
            const pos = textarea.selectionStart;
            const before = textarea.value.substring(0, pos);
            const after = textarea.value.substring(pos);
            textarea.value = before + code + after;
            textarea.selectionStart = textarea.selectionEnd = pos + code.length;
            handleInput();
            addOutput('⠉ Code inserted from SAL', 'success');
        }
        
        async function salGenerate() {
            const instruction = prompt('What code should SAL generate?');
            if (!instruction) return;
            
            addSalMessage('user', `Generate: ${instruction}`);
            salThinking = true;
            addSalMessage('thinking', '⠎⠁⠇ is generating code...');
            
            try {
                const response = await fetch('/api/sal/generate', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        instruction: instruction,
                        language: currentLanguage
                    })
                });
                
                const data = await response.json();
                removeSalThinking();
                addSalMessage('sal', data.text, data.code_blocks);
                
            } catch (e) {
                removeSalThinking();
                addSalMessage('sal', '⠑⠗⠗ Error generating code');
            }
            
            salThinking = false;
        }
        
        async function salExplain() {
            const code = document.getElementById('codeInput').value;
            if (!code.trim()) {
                addSalMessage('sal', 'No code to explain. Write some code first!');
                return;
            }
            
            addSalMessage('user', 'Explain this code');
            salThinking = true;
            addSalMessage('thinking', '⠎⠁⠇ is analyzing code...');
            
            try {
                const response = await fetch('/api/sal/explain', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        code: code,
                        language: currentLanguage
                    })
                });
                
                const data = await response.json();
                removeSalThinking();
                addSalMessage('sal', data.text);
                
            } catch (e) {
                removeSalThinking();
                addSalMessage('sal', '⠑⠗⠗ Error explaining code');
            }
            
            salThinking = false;
        }
        
        async function salDebug() {
            const code = document.getElementById('codeInput').value;
            if (!code.trim()) {
                addSalMessage('sal', 'No code to debug. Write some code first!');
                return;
            }
            
            const error = prompt('Paste any error message (or leave empty):') || '';
            
            addSalMessage('user', 'Debug this code' + (error ? `: ${error}` : ''));
            salThinking = true;
            addSalMessage('thinking', '⠎⠁⠇ is debugging...');
            
            try {
                const response = await fetch('/api/sal/debug', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        code: code,
                        error: error,
                        language: currentLanguage
                    })
                });
                
                const data = await response.json();
                removeSalThinking();
                addSalMessage('sal', data.text, data.code_blocks);
                
            } catch (e) {
                removeSalThinking();
                addSalMessage('sal', '⠑⠗⠗ Error debugging code');
            }
            
            salThinking = false;
        }
        
        // Check SAL status on load
        checkSalStatus();
        setInterval(checkSalStatus, 30000); // Check every 30s
        
        // ============================================
        // SAL Cascade - Autonomous Coding Mode
        // ============================================
        
        let cascadeMode = true; // SAL writes all code by default
        let cascadeThinking = false;
        
        function toggleCascadeMode() {
            cascadeMode = !cascadeMode;
            document.getElementById('cascadeToggle').classList.toggle('active', cascadeMode);
            
            const statusEl = document.getElementById('cascadeStatus');
            const codeInput = document.getElementById('codeInput');
            
            if (cascadeMode) {
                statusEl.textContent = '● SAL is the coder. Describe what you want.';
                statusEl.style.color = 'var(--accent-green)';
                codeInput.readOnly = true;
                codeInput.style.opacity = '0.7';
                codeInput.placeholder = '⠎⠁⠇ SAL writes code here. Use the panel to describe what you want.';
            } else {
                statusEl.textContent = '○ Manual mode. You can edit code.';
                statusEl.style.color = 'var(--text-secondary)';
                codeInput.readOnly = false;
                codeInput.style.opacity = '1';
                codeInput.placeholder = 'Start typing code...';
            }
        }
        
        // Initialize cascade mode on load
        document.addEventListener('DOMContentLoaded', () => {
            if (cascadeMode) {
                const codeInput = document.getElementById('codeInput');
                codeInput.readOnly = true;
                codeInput.style.opacity = '0.7';
                codeInput.placeholder = '⠎⠁⠇ SAL writes code here. Use the panel to describe what you want.';
            }
        });
        
        async function sendCascadeIntent() {
            const input = document.getElementById('cascadeInput');
            const intent = input.value.trim();
            if (!intent || cascadeThinking) return;
            
            input.value = '';
            addCascadeMessage('user', intent);
            
            cascadeThinking = true;
            showTaskPanel('understanding', 'Understanding your intent...');
            
            // Create streaming message element with token counter
            const streamDiv = document.createElement('div');
            streamDiv.id = 'cascadeStream';
            streamDiv.style.cssText = 'background: rgba(63, 185, 80, 0.1); padding: 10px; border-radius: 8px; margin-bottom: 10px;';
            streamDiv.innerHTML = `
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px;">
                    <span style="color: var(--accent-green); font-size: 11px;">⠎⠁⠇ SAL Cascade</span>
                    <span id="tokenCounter" style="font-size: 10px; color: var(--accent-purple);">↓ 0 tokens</span>
                </div>
                <div id="streamContent">⠎⠁⠇ is thinking...</div>
            `;
            document.getElementById('salChat').appendChild(streamDiv);
            document.getElementById('salChat').scrollTop = document.getElementById('salChat').scrollHeight;
            
            let totalTokens = 0;
            
            try {
                // Use streaming endpoint
                const response = await fetch('/api/cascade/stream', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ intent: intent })
                });
                
                const reader = response.body.getReader();
                const decoder = new TextDecoder();
                let buffer = '';
                
                while (true) {
                    const {value, done} = await reader.read();
                    if (done) break;
                    
                    buffer += decoder.decode(value, {stream: true});
                    const lines = buffer.split('\\n');
                    buffer = lines.pop();
                    
                    for (const line of lines) {
                        if (line.startsWith('data: ')) {
                            try {
                                const data = JSON.parse(line.slice(6));
                                
                                // Update token counter
                                if (data.tokens !== undefined) {
                                    totalTokens = data.tokens;
                                    const counter = document.getElementById('tokenCounter');
                                    if (counter) {
                                        counter.textContent = `↓ ${totalTokens} tokens`;
                                    }
                                }
                                
                                if (data.status) {
                                    showTaskPanel(data.status, data.message || data.status);
                                    document.getElementById('streamContent').textContent = data.message || data.status;
                                }
                                
                                if (data.status === 'completed' && data.result) {
                                    // Show final token count
                                    const finalTokens = data.result.tokens_used || totalTokens;
                                    const elapsed = data.result.elapsed_time || 0;
                                    
                                    // Remove stream div, show completed with token info
                                    document.getElementById('cascadeStream')?.remove();
                                    showTaskCompleted(data.result, finalTokens, elapsed);
                                    
                                    if (data.result.code) {
                                        const code = Object.values(data.result.code)[0] || '';
                                        document.getElementById('codeInput').value = code;
                                        handleInput();
                                        addOutput(`⠎⠁⠇ Code generated (${finalTokens} tokens, ${elapsed}s)`, 'success');
                                    }
                                }
                                
                                if (data.status === 'clarification_needed') {
                                    document.getElementById('cascadeStream')?.remove();
                                    showClarificationRequest(data.clarification);
                                }
                                
                                if (data.status === 'error') {
                                    document.getElementById('streamContent').textContent = '⠑⠗⠗ ' + data.error;
                                }
                                
                            } catch (e) {}
                        }
                    }
                }
                
            } catch (e) {
                document.getElementById('cascadeStream')?.remove();
                addCascadeMessage('sal', '⠑⠗⠗ Error connecting to SAL Cascade: ' + e);
            }
            
            cascadeThinking = false;
        }
        
        function addCascadeMessage(role, content) {
            const chat = document.getElementById('salChat');
            const div = document.createElement('div');
            div.style.marginBottom = '10px';
            div.style.padding = '10px';
            div.style.borderRadius = '8px';
            div.style.fontSize = '13px';
            
            if (role === 'user') {
                div.style.background = 'rgba(88, 166, 255, 0.1)';
                div.style.marginLeft = '20px';
                div.innerHTML = `<div style="color: var(--accent-blue); font-size: 11px; margin-bottom: 4px;">You</div><div>${content}</div>`;
            } else if (role === 'thinking') {
                div.id = 'cascadeThinking';
                div.style.color = 'var(--accent-purple)';
                div.style.fontStyle = 'italic';
                div.innerHTML = `<div style="display: flex; align-items: center; gap: 8px;">
                    <div class="typing-dots" style="display: flex; gap: 3px;">
                        <div style="width: 6px; height: 6px; background: var(--accent-purple); border-radius: 50%; animation: bounce 1s infinite;"></div>
                        <div style="width: 6px; height: 6px; background: var(--accent-purple); border-radius: 50%; animation: bounce 1s infinite 0.2s;"></div>
                        <div style="width: 6px; height: 6px; background: var(--accent-purple); border-radius: 50%; animation: bounce 1s infinite 0.4s;"></div>
                    </div>
                    ${content}
                </div>`;
            } else {
                div.style.background = 'rgba(63, 185, 80, 0.1)';
                div.innerHTML = `<div style="color: var(--accent-green); font-size: 11px; margin-bottom: 4px;">⠎⠁⠇ SAL Cascade</div><div>${content.replace(/\\n/g, '<br>')}</div>`;
            }
            
            chat.appendChild(div);
            chat.scrollTop = chat.scrollHeight;
        }
        
        function removeCascadeThinking() {
            const el = document.getElementById('cascadeThinking');
            if (el) el.remove();
        }
        
        function showTaskPanel(status, message) {
            const panel = document.getElementById('taskPanel');
            const content = document.getElementById('taskStatus');
            panel.style.display = 'block';
            
            const statusColors = {
                'understanding': 'var(--accent-blue)',
                'planning': 'var(--accent-purple)',
                'coding': 'var(--accent-orange)',
                'verifying': 'var(--accent-green)',
                'completed': 'var(--accent-green)',
                'clarification_needed': 'var(--accent-orange)'
            };
            
            content.innerHTML = `
                <div style="color: ${statusColors[status] || 'var(--text-secondary)'}; margin-bottom: 8px;">
                    <strong>${status.toUpperCase().replace('_', ' ')}</strong>
                </div>
                <div>${message}</div>
            `;
        }
        
        function showClarificationRequest(clarification) {
            const chat = document.getElementById('salChat');
            const div = document.createElement('div');
            div.style.background = 'rgba(210, 153, 34, 0.15)';
            div.style.padding = '12px';
            div.style.borderRadius = '8px';
            div.style.marginBottom = '10px';
            div.style.border = '1px solid rgba(210, 153, 34, 0.3)';
            
            let suggestionsHtml = '';
            if (clarification.suggestions && clarification.suggestions.length > 0) {
                suggestionsHtml = '<div style="margin-top: 8px;"><strong>Suggestions:</strong><ul style="margin: 4px 0 0 16px;">';
                clarification.suggestions.forEach(s => {
                    suggestionsHtml += `<li style="margin: 2px 0;">${s}</li>`;
                });
                suggestionsHtml += '</ul></div>';
            }
            
            div.innerHTML = `
                <div style="color: var(--accent-orange); font-size: 11px; margin-bottom: 4px;">⠒ SAL needs clarification</div>
                <div>${clarification.message}</div>
                ${suggestionsHtml}
                <div style="margin-top: 10px;">
                    <input type="text" id="clarificationInput" placeholder="Provide clarification..." 
                           style="width: 100%; padding: 8px; background: var(--bg-primary); border: 1px solid var(--border-color); border-radius: 4px; color: var(--text-primary);"
                           onkeydown="if(event.key==='Enter')sendClarification()">
                    <button class="btn" onclick="sendClarification()" style="margin-top: 8px; width: 100%;">Clarify</button>
                </div>
            `;
            
            chat.appendChild(div);
            chat.scrollTop = chat.scrollHeight;
            
            showTaskPanel('clarification_needed', 'Waiting for your clarification...');
        }
        
        async function sendClarification() {
            const input = document.getElementById('clarificationInput');
            const clarification = input.value.trim();
            if (!clarification) return;
            
            addCascadeMessage('user', clarification);
            cascadeThinking = true;
            addCascadeMessage('thinking', '⠎⠁⠇ is processing your clarification...');
            
            try {
                const response = await fetch('/api/cascade/clarify', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ clarification: clarification })
                });
                
                const data = await response.json();
                removeCascadeThinking();
                
                if (data.status === 'completed') {
                    showTaskCompleted(data);
                    if (data.code) {
                        const code = Object.values(data.code)[0] || '';
                        document.getElementById('codeInput').value = code;
                        handleInput();
                    }
                } else if (data.status === 'clarification_needed') {
                    showClarificationRequest(data.clarification);
                }
                
            } catch (e) {
                removeCascadeThinking();
                addCascadeMessage('sal', '⠑⠗⠗ Error processing clarification');
            }
            
            cascadeThinking = false;
        }
        
        function showTaskCompleted(data, tokens = 0, elapsed = 0) {
            const tokenInfo = tokens ? ` (${tokens} tokens, ${elapsed}s)` : '';
            showTaskPanel('completed', `Task completed!${tokenInfo} Generated ${Object.keys(data.code || {}).length} file(s).`);
            
            // Show plan
            let planHtml = '<div style="margin-top: 8px;"><strong>Plan executed:</strong><ul style="margin: 4px 0 0 16px;">';
            (data.plan || []).forEach((step, i) => {
                planHtml += `<li style="margin: 2px 0; color: var(--accent-green);">✓ ${step.step}</li>`;
            });
            planHtml += '</ul></div>';
            
            addCascadeMessage('sal', `✅ <strong>Task Complete!</strong>
                <br><br><strong>Understanding:</strong> ${data.understanding || 'N/A'}
                ${planHtml}
                <br><strong>Verification:</strong> ${(data.verification || 'Code generated successfully').substring(0, 200)}...`);
        }
        
        // Block human code in cascade mode
        document.getElementById('codeInput').addEventListener('input', async function(e) {
            if (!cascadeMode) return;
            
            const code = e.target.value;
            if (code.length > 50) {
                const response = await fetch('/api/cascade/reject-code', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ code: code })
                });
                
                const data = await response.json();
                if (data.rejected) {
                    addCascadeMessage('sal', data.message);
                    e.target.value = '';
                }
            }
        });
        
        // ============================================
        // File Browser (Like Jupyter)
        // ============================================
        
        let currentBrowsePath = '~';
        let currentFilePath = null;
        
        async function browsePath(path) {
            try {
                const response = await fetch(`/api/fs/list?path=${encodeURIComponent(path)}`);
                const data = await response.json();
                
                if (data.error) {
                    addOutput(`⠑⠗⠗ ${data.error}`, 'error');
                    return;
                }
                
                currentBrowsePath = data.path;
                document.getElementById('currentPath').textContent = data.path.replace(/^\/Users\/\\w+/, '~');
                
                const tree = document.getElementById('fileTree');
                tree.innerHTML = '';
                
                // Add items
                data.items.forEach(item => {
                    const div = document.createElement('div');
                    div.className = 'file-item';
                    div.style.cursor = 'pointer';
                    
                    const icon = item.is_dir ? '📁' : getFileIconEmoji(item.name);
                    const size = item.size ? `${Math.round(item.size/1024)}KB` : '';
                    
                    div.innerHTML = `
                        <span style="margin-right: 6px;">${icon}</span>
                        <span style="flex: 1; overflow: hidden; text-overflow: ellipsis;">${item.name}</span>
                        <span style="font-size: 10px; color: var(--text-secondary);">${size}</span>
                    `;
                    
                    div.onclick = () => {
                        if (item.is_dir) {
                            browsePath(item.path);
                        } else {
                            openFileFromDisk(item.path);
                        }
                    };
                    
                    tree.appendChild(div);
                });
                
                if (data.items.length === 0) {
                    tree.innerHTML = '<div style="padding: 12px; color: var(--text-secondary); font-size: 12px;">Empty directory</div>';
                }
                
            } catch (e) {
                addOutput(`⠑⠗⠗ Failed to browse: ${e}`, 'error');
            }
        }
        
        function getFileIconEmoji(name) {
            if (name.endsWith('.py')) return '🐍';
            if (name.endsWith('.js') || name.endsWith('.ts')) return '📜';
            if (name.endsWith('.json')) return '📋';
            if (name.endsWith('.md')) return '📝';
            if (name.endsWith('.html')) return '🌐';
            if (name.endsWith('.css')) return '🎨';
            if (name.endsWith('.go')) return '🔵';
            if (name.endsWith('.rs')) return '🦀';
            return '📄';
        }
        
        function goToParent() {
            const parent = currentBrowsePath.split('/').slice(0, -1).join('/') || '/';
            browsePath(parent);
        }
        
        async function openFileFromDisk(path) {
            try {
                const response = await fetch('/api/fs/open', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ path: path })
                });
                
                const data = await response.json();
                
                if (data.error) {
                    addOutput(`⠑⠗⠗ ${data.error}`, 'error');
                    return;
                }
                
                // Update editor
                document.getElementById('codeInput').value = data.content;
                currentFilePath = data.path;
                
                // Update language selector
                if (data.language) {
                    document.getElementById('languageSelect').value = data.language;
                    currentLanguage = data.language;
                    document.getElementById('currentLanguage').textContent = 
                        data.language.charAt(0).toUpperCase() + data.language.slice(1);
                }
                
                handleInput();
                addOutput(`⠕⠏⠑⠝ Opened: ${data.name} (${data.lines} lines)`, 'success');
                
                // Disable cascade mode for editing real files
                if (cascadeMode) {
                    document.getElementById('codeInput').readOnly = false;
                    document.getElementById('codeInput').style.opacity = '1';
                }
                
            } catch (e) {
                addOutput(`⠑⠗⠗ Failed to open file: ${e}`, 'error');
            }
        }
        
        async function saveFileToDisk() {
            const content = document.getElementById('codeInput').value;
            
            let path = currentFilePath;
            if (!path) {
                path = prompt('Save as (full path):', '~/untitled.py');
                if (!path) return;
            }
            
            try {
                const response = await fetch('/api/fs/write', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ path: path, content: content })
                });
                
                const data = await response.json();
                
                if (data.error) {
                    addOutput(`⠑⠗⠗ ${data.error}`, 'error');
                    return;
                }
                
                currentFilePath = data.path;
                document.getElementById('saveStatus').textContent = 'Saved';
                addOutput(`⠎⠁⠧ Saved: ${data.path} (${data.size} bytes)`, 'success');
                
                // Refresh file tree if we're in the same directory
                if (data.path.startsWith(currentBrowsePath)) {
                    browsePath(currentBrowsePath);
                }
                
            } catch (e) {
                addOutput(`⠑⠗⠗ Failed to save: ${e}`, 'error');
            }
        }
        
        // Initialize file browser on load
        document.addEventListener('DOMContentLoaded', () => {
            browsePath('~');
        });
    </script>
</body>
</html>
'''


@app.route('/')
def index():
    """Serve the main IDE interface"""
    return render_template_string(HTML_TEMPLATE)


@app.route('/api/status')
def get_status():
    """Get current IDE status"""
    project = ide.get_active_project()
    file = ide.get_active_file()
    
    return jsonify({
        'project': project.to_dict() if project else None,
        'file': {
            'id': file.id,
            'name': file.name,
            'language': file.language.value,
            'content_text': file.text_content,
            'content_braille': file.braille_content,
            'cursor_line': file.cursor_line,
            'cursor_col': file.cursor_col,
            'line_count': file.line_count,
        } if file else None,
    })


@app.route('/api/command', methods=['POST'])
def execute_command():
    """Execute an IDE command"""
    data = request.get_json()
    command = data.get('command', '')
    
    result = ide.execute_command(command)
    result_text = ide.encoder.decode(result)
    
    return jsonify({
        'result_braille': result,
        'result_text': result_text,
    })


@app.route('/api/to-braille', methods=['POST'])
def to_braille():
    """Convert text to braille"""
    data = request.get_json()
    text = data.get('text', '')
    
    braille = ide.code_encoder.encode(text)
    
    return jsonify({
        'braille': braille,
        'text': text,
    })


@app.route('/api/from-braille', methods=['POST'])
def from_braille():
    """Convert braille to text"""
    data = request.get_json()
    braille = data.get('braille', '')
    
    text = ide.code_encoder.decode(braille)
    
    return jsonify({
        'text': text,
        'braille': braille,
    })


@app.route('/api/open-file', methods=['POST'])
def open_file():
    """Open a file"""
    data = request.get_json()
    file_id = data.get('file_id', '')
    
    project = ide.get_active_project()
    if project:
        project.set_active_file(file_id)
        ide.save_projects()
        
    return jsonify({'success': True})


@app.route('/api/update-content', methods=['POST'])
def update_content():
    """Update file content"""
    data = request.get_json()
    content = data.get('content', '')
    
    file = ide.get_active_file()
    if file:
        file.text_content = content
        ide.save_projects()
        
    return jsonify({'success': True})


@app.route('/api/completions', methods=['POST'])
def get_completions():
    """Get code completions"""
    data = request.get_json()
    line = data.get('line', '')
    col = data.get('col', 0)
    language_str = data.get('language', 'python')
    file_content = data.get('file_content', '')
    
    try:
        language = Language(language_str.lower())
    except:
        language = Language.PYTHON
    
    context = CompletionContext(
        line=line,
        col=col,
        prefix=completion_engine.get_context_from_line(line, col, language).prefix,
        language=language,
        file_content=file_content
    )
    
    completions = completion_engine.get_completions(context)
    
    return jsonify({
        'completions': [
            {
                'label': c.label,
                'braille': c.braille,
                'braille_icon': c.braille_icon,
                'kind': c.kind.value,
                'detail': c.detail,
                'insert_text': c.insert_text,
            }
            for c in completions
        ]
    })


@app.route('/api/highlight', methods=['POST'])
def highlight_code():
    """Syntax highlight code"""
    data = request.get_json()
    code = data.get('code', '')
    language_str = data.get('language', 'python')
    
    try:
        language = Language(language_str.lower())
    except:
        language = Language.PYTHON
        
    highlighted = highlighter.highlight_code(code, language)
    
    return jsonify({
        'highlighted_braille': highlighted,
        'original': code,
    })


@app.route('/api/run', methods=['POST'])
def run_code():
    """Run code"""
    data = request.get_json()
    code = data.get('code', '')
    language_str = data.get('language', 'python')
    
    try:
        language = Language(language_str.lower())
    except:
        language = Language.PYTHON
        
    success, stdout, stderr = output_renderer.execute_code(code, language)
    
    return jsonify({
        'success': success,
        'stdout': stdout,
        'stderr': stderr,
    })


@app.route('/api/commands')
def get_commands():
    """Get all available commands"""
    commands = interface.get_command_palette()
    return jsonify({'commands': commands})


@app.route('/api/menu')
def get_menu():
    """Get menu structure"""
    return jsonify({
        'menu_braille': interface.render_menu(),
        'menu_text': interface.render_menu_text(),
    })


# ============================================
# SAL AI Integration Endpoints
# ============================================

@app.route('/api/sal/status')
def sal_status():
    """Check if SAL is available"""
    available = run_async(check_sal_available())
    return jsonify({
        'available': available,
        'model': 'sal',
        'braille_status': '⠎⠁⠇_⠁⠉⠞⠊⠧⠑' if available else '⠎⠁⠇_⠕⠋⠋⠇⠊⠝⠑'
    })


@app.route('/api/sal/chat', methods=['POST'])
def sal_chat():
    """Chat with SAL AI"""
    data = request.get_json()
    message = data.get('message', '')
    include_file = data.get('include_file', True)
    
    # Update SAL context
    file = ide.get_active_file()
    if file:
        sal_client.set_context(
            language=file.language.value,
            filename=file.name,
            cursor_line=file.cursor_line,
            file_content=file.text_content if include_file else ""
        )
    
    response = run_async(sal_client.chat(message, include_file))
    
    return jsonify({
        'text': response.text,
        'braille': response.braille,
        'code_blocks': response.code_blocks,
        'tokens_used': response.tokens_used,
        'thinking_time': response.thinking_time,
    })


@app.route('/api/sal/generate', methods=['POST'])
def sal_generate():
    """Generate code with SAL"""
    data = request.get_json()
    instruction = data.get('instruction', '')
    language = data.get('language', 'python')
    
    response = run_async(sal_client.generate_code(instruction, language))
    
    return jsonify({
        'text': response.text,
        'braille': response.braille,
        'code_blocks': response.code_blocks,
    })


@app.route('/api/sal/stream', methods=['POST'])
def sal_stream():
    """Stream SAL response token by token with token counts"""
    data = request.get_json()
    message = data.get('message', '')
    
    def generate():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        async def collect():
            chunks = []
            token_count = 0
            async for data in sal_client.stream_chat(message, include_file=False):
                token = data.get('token', '')
                chunks.append(token)
                token_count = data.get('token_count', token_count + 1)
                
                yield f"data: {json.dumps({'token': token, 'tokens': token_count})}\n\n"
                
                if data.get('done'):
                    yield f"data: {json.dumps({'done': True, 'tokens': data.get('eval_count', token_count), 'prompt_tokens': data.get('prompt_eval_count', 0)})}\n\n"
        
        for chunk in loop.run_until_complete(list_async_gen(collect())):
            yield chunk
        loop.close()
    
    return Response(generate(), mimetype='text/event-stream')


async def list_async_gen(agen):
    """Convert async generator to list"""
    result = []
    async for item in agen:
        result.append(item)
    return result


@app.route('/api/cascade/stream', methods=['POST'])
def cascade_stream():
    """Stream SAL Cascade intent processing with token counting"""
    data = request.get_json()
    intent = data.get('intent', '')
    
    def generate():
        import time
        import threading
        import json as json_lib  # Import json inside generator
        
        start_time = time.time()
        token_count = [0]  # Use list for mutable closure
        
        # Send initial status
        yield f"data: {json_lib.dumps({'status': 'understanding', 'message': 'Connecting to SAL...', 'tokens': 0})}\n\n"
        
        # Process in background thread to allow streaming
        result_holder = [None]
        error_holder = [None]
        
        def process():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                result_holder[0] = loop.run_until_complete(sal_cascade.process_intent(intent))
            except Exception as e:
                error_holder[0] = str(e)
            finally:
                loop.close()
        
        # Start processing in thread
        thread = threading.Thread(target=process)
        thread.start()
        
        # Stream progress updates while waiting
        phases = [
            ('understanding', 'Understanding your intent...'),
            ('planning', 'Creating plan...'),
            ('coding', 'Writing code...'),
        ]
        
        phase_idx = 0
        while thread.is_alive():
            time.sleep(0.5)
            token_count[0] += 15  # Estimate ~30 tokens/sec
            
            # Cycle through phases
            if token_count[0] > 50 and phase_idx == 0:
                phase_idx = 1
            if token_count[0] > 150 and phase_idx == 1:
                phase_idx = 2
                
            phase, msg = phases[min(phase_idx, len(phases)-1)]
            yield f"data: {json_lib.dumps({'status': phase, 'message': msg, 'tokens': token_count[0]})}\n\n"
        
        thread.join()
        elapsed = time.time() - start_time
        
        if error_holder[0]:
            yield f"data: {json_lib.dumps({'status': 'error', 'error': error_holder[0], 'tokens': token_count[0]})}\n\n"
        else:
            result = result_holder[0]
            
            # Calculate actual tokens from response
            if result and result.get('code'):
                for code in result['code'].values():
                    token_count[0] += len(code) // 4
            
            if result and result.get('status') == 'completed':
                result['tokens_used'] = token_count[0]
                result['elapsed_time'] = round(elapsed, 2)
                
                yield f"data: {json_lib.dumps({'status': 'completed', 'result': result, 'tokens': token_count[0]})}\n\n"
                
                # Update file in IDE
                if result.get('code'):
                    file = ide.get_active_file()
                    if file:
                        code = list(result['code'].values())[0] if result['code'] else ""
                        file.text_content = code
                        ide.save_projects()
                        
            elif result and result.get('status') == 'clarification_needed':
                yield f"data: {json_lib.dumps({'status': 'clarification_needed', 'clarification': result.get('clarification'), 'tokens': token_count[0]})}\n\n"
            else:
                yield f"data: {json_lib.dumps({'status': 'error', 'error': 'Unknown error', 'tokens': token_count[0]})}\n\n"
        
        yield f"data: {json_lib.dumps({'done': True, 'total_tokens': token_count[0]})}\n\n"
    
    return Response(generate(), mimetype='text/event-stream')


@app.route('/api/sal/explain', methods=['POST'])
def sal_explain():
    """Explain code with SAL"""
    data = request.get_json()
    code = data.get('code', '')
    language = data.get('language', 'python')
    
    response = run_async(sal_client.explain_code(code, language))
    
    return jsonify({
        'text': response.text,
        'braille': response.braille,
    })


@app.route('/api/sal/debug', methods=['POST'])
def sal_debug():
    """Debug code with SAL"""
    data = request.get_json()
    code = data.get('code', '')
    error = data.get('error', '')
    language = data.get('language', 'python')
    
    response = run_async(sal_client.debug_code(code, error, language))
    
    return jsonify({
        'text': response.text,
        'braille': response.braille,
        'code_blocks': response.code_blocks,
    })


@app.route('/api/sal/complete', methods=['POST'])
def sal_complete():
    """AI-powered code completion with SAL"""
    data = request.get_json()
    code_before = data.get('code_before', '')
    code_after = data.get('code_after', '')
    language = data.get('language', 'python')
    
    response = run_async(sal_client.complete_code(code_before, code_after, language))
    
    return jsonify({
        'completion': response.text,
        'braille': response.braille,
    })


@app.route('/api/sal/refactor', methods=['POST'])
def sal_refactor():
    """Refactor code with SAL"""
    data = request.get_json()
    code = data.get('code', '')
    instruction = data.get('instruction', '')
    language = data.get('language', 'python')
    
    response = run_async(sal_client.refactor_code(code, instruction, language))
    
    return jsonify({
        'text': response.text,
        'braille': response.braille,
        'code_blocks': response.code_blocks,
    })


@app.route('/api/sal/history')
def sal_history():
    """Get SAL conversation history"""
    return jsonify({
        'history': sal_client.get_history()
    })


@app.route('/api/sal/clear', methods=['POST'])
def sal_clear():
    """Clear SAL conversation history"""
    sal_client.clear_history()
    return jsonify({'success': True})


# ============================================
# SAL Cascade - Autonomous Coding Endpoints
# ============================================

@app.route('/api/cascade/intent', methods=['POST'])
def cascade_intent():
    """Send intent to SAL Cascade - SAL writes all code"""
    data = request.get_json()
    intent = data.get('intent', '')
    
    if not intent:
        return jsonify({'error': 'No intent provided'})
    
    result = run_async(sal_cascade.process_intent(intent))
    
    # If SAL wrote code, update the active file
    if result.get('status') == 'completed' and result.get('code'):
        file = ide.get_active_file()
        if file:
            # Get the first file's code
            code = list(result['code'].values())[0] if result['code'] else ""
            file.text_content = code
            ide.save_projects()
    
    return jsonify(result)


@app.route('/api/cascade/clarify', methods=['POST'])
def cascade_clarify():
    """Provide clarification to SAL Cascade"""
    data = request.get_json()
    clarification = data.get('clarification', '')
    
    result = run_async(sal_cascade.provide_clarification(clarification))
    
    # If SAL wrote code, update the active file
    if result.get('status') == 'completed' and result.get('code'):
        file = ide.get_active_file()
        if file:
            code = list(result['code'].values())[0] if result['code'] else ""
            file.text_content = code
            ide.save_projects()
    
    return jsonify(result)


@app.route('/api/cascade/status')
def cascade_status():
    """Get SAL Cascade status"""
    return jsonify(sal_cascade.get_status())


@app.route('/api/cascade/reject-code', methods=['POST'])
def cascade_reject_code():
    """Check if human is trying to type code (rejected in autonomous mode)"""
    data = request.get_json()
    code = data.get('code', '')
    
    return jsonify(sal_cascade.reject_human_code(code))


# ============================================
# Graph Database Endpoints
# ============================================

@app.route('/api/graph/stats')
def graph_stats():
    """Get graph database statistics"""
    return jsonify(graph_store.get_stats())


@app.route('/api/graph/nodes', methods=['GET'])
def graph_nodes():
    """Query nodes from graph"""
    node_type = request.args.get('type')
    
    if node_type:
        try:
            nt = NodeType(node_type)
            nodes = graph_store.query_nodes(node_type=nt)
        except ValueError:
            nodes = graph_store.query_nodes()
    else:
        nodes = graph_store.query_nodes()
    
    return jsonify({
        'nodes': [n.to_dict() for n in nodes],
        'count': len(nodes)
    })


@app.route('/api/graph/node/<node_id>', methods=['GET'])
def graph_get_node(node_id):
    """Get a specific node"""
    node = graph_store.get_node(node_id)
    if node:
        rels = graph_store.get_relationships(node_id)
        return jsonify({
            'node': node.to_dict(),
            'relationships': [r.to_dict() for r in rels]
        })
    return jsonify({'error': 'Node not found'}), 404


@app.route('/api/graph/node', methods=['POST'])
def graph_create_node():
    """Create a new node"""
    data = request.get_json()
    
    node = Node(
        id=data.get('id', f"node_{len(graph_store.query_nodes())}"),
        type=NodeType(data.get('type', 'File')),
        properties=data.get('properties', {})
    )
    
    created = graph_store.create_node(node)
    return jsonify({'node': created.to_dict()})


@app.route('/api/graph/node/<node_id>', methods=['DELETE'])
def graph_delete_node(node_id):
    """Delete a node"""
    success = graph_store.delete_node(node_id)
    return jsonify({'success': success})


@app.route('/api/graph/relationship', methods=['POST'])
def graph_create_relationship():
    """Create a relationship between nodes"""
    data = request.get_json()
    
    rel = Relationship(
        id=data.get('id', f"rel_{data['source_id']}_{data['target_id']}"),
        type=RelationType(data.get('type', 'CONTAINS')),
        source_id=data['source_id'],
        target_id=data['target_id'],
        properties=data.get('properties', {})
    )
    
    try:
        created = graph_store.create_relationship(rel)
        return jsonify({'relationship': created.to_dict()})
    except ValueError as e:
        return jsonify({'error': str(e)}), 400


@app.route('/api/graph/traverse/<start_id>', methods=['GET'])
def graph_traverse(start_id):
    """Traverse graph from a starting node"""
    max_depth = int(request.args.get('depth', 3))
    rel_types = request.args.get('types')
    
    types = None
    if rel_types:
        types = [RelationType(t) for t in rel_types.split(',')]
    
    results = graph_store.traverse(start_id, rel_types=types, max_depth=max_depth)
    
    return jsonify({
        'paths': [
            {
                'node': node.to_dict(),
                'path': [r.to_dict() for r in path]
            }
            for node, path in results
        ],
        'count': len(results)
    })


@app.route('/api/graph/sync', methods=['POST'])
def graph_sync_project():
    """Sync current project to graph database"""
    project = ide.get_active_project()
    if not project:
        return jsonify({'error': 'No active project'})
    
    # Create project node
    project_node = create_project_node(graph_store, project.id, project.name)
    
    # Create file nodes
    file_nodes = []
    for file_id, file in project.files.items():
        file_node = create_file_node(
            graph_store,
            file_id,
            file.name,
            file.language.value,
            file.text_content,
            project.id
        )
        file_nodes.append(file_node)
    
    return jsonify({
        'synced': True,
        'project': project_node.to_dict(),
        'files': [f.to_dict() for f in file_nodes],
        'braille_status': '⠛⠗⠁⠏⠓_⠎⠽⠝⠉⠑⠙'
    })


# ============================================
# Filesystem Access (Like Jupyter)
# ============================================

@app.route('/api/fs/list')
def fs_list():
    """List directory contents"""
    path = request.args.get('path', os.path.expanduser('~'))
    
    try:
        path = os.path.abspath(os.path.expanduser(path))
        
        if not os.path.exists(path):
            return jsonify({'error': 'Path not found'}), 404
            
        if not os.path.isdir(path):
            return jsonify({'error': 'Not a directory'}), 400
            
        items = []
        for name in sorted(os.listdir(path)):
            if name.startswith('.'):
                continue  # Skip hidden files by default
                
            full_path = os.path.join(path, name)
            is_dir = os.path.isdir(full_path)
            
            # Get file info
            try:
                stat = os.stat(full_path)
                size = stat.st_size if not is_dir else None
                modified = stat.st_mtime
            except:
                size = None
                modified = None
                
            # Detect language for files
            language = None
            if not is_dir:
                ext_map = {
                    '.py': 'python', '.js': 'javascript', '.ts': 'typescript',
                    '.jsx': 'javascript', '.tsx': 'typescript', '.go': 'go',
                    '.rs': 'rust', '.java': 'java', '.sql': 'sql',
                    '.c': 'c', '.cpp': 'cpp', '.h': 'c', '.md': 'markdown',
                    '.json': 'json', '.yaml': 'yaml', '.yml': 'yaml',
                    '.html': 'html', '.css': 'css', '.sh': 'shell'
                }
                for ext, lang in ext_map.items():
                    if name.endswith(ext):
                        language = lang
                        break
                        
            items.append({
                'name': name,
                'path': full_path,
                'is_dir': is_dir,
                'size': size,
                'modified': modified,
                'language': language
            })
            
        return jsonify({
            'path': path,
            'parent': os.path.dirname(path),
            'items': items,
            'count': len(items)
        })
        
    except PermissionError:
        return jsonify({'error': 'Permission denied'}), 403
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/fs/read')
def fs_read():
    """Read a file from disk"""
    path = request.args.get('path')
    
    if not path:
        return jsonify({'error': 'No path provided'}), 400
        
    try:
        path = os.path.abspath(os.path.expanduser(path))
        
        if not os.path.exists(path):
            return jsonify({'error': 'File not found'}), 404
            
        if os.path.isdir(path):
            return jsonify({'error': 'Path is a directory'}), 400
            
        # Check file size (limit to 1MB)
        if os.path.getsize(path) > 1024 * 1024:
            return jsonify({'error': 'File too large (>1MB)'}), 400
            
        with open(path, 'r', encoding='utf-8', errors='replace') as f:
            content = f.read()
            
        # Convert to braille
        braille_content = ide.encoder.encode(content[:1000])
        
        return jsonify({
            'path': path,
            'name': os.path.basename(path),
            'content': content,
            'braille_preview': braille_content,
            'size': len(content),
            'lines': content.count('\n') + 1
        })
        
    except PermissionError:
        return jsonify({'error': 'Permission denied'}), 403
    except UnicodeDecodeError:
        return jsonify({'error': 'Binary file cannot be read as text'}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/fs/write', methods=['POST'])
def fs_write():
    """Write a file to disk"""
    data = request.get_json()
    path = data.get('path')
    content = data.get('content', '')
    
    if not path:
        return jsonify({'error': 'No path provided'}), 400
        
    try:
        path = os.path.abspath(os.path.expanduser(path))
        
        # Create directory if needed
        os.makedirs(os.path.dirname(path), exist_ok=True)
        
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
            
        return jsonify({
            'success': True,
            'path': path,
            'size': len(content),
            'braille_status': '⠎⠁⠧⠑⠙'
        })
        
    except PermissionError:
        return jsonify({'error': 'Permission denied'}), 403
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/fs/open', methods=['POST'])
def fs_open_in_ide():
    """Open a file in the IDE editor"""
    data = request.get_json()
    path = data.get('path')
    
    if not path:
        return jsonify({'error': 'No path provided'}), 400
        
    try:
        path = os.path.abspath(os.path.expanduser(path))
        
        if not os.path.exists(path):
            return jsonify({'error': 'File not found'}), 404
            
        with open(path, 'r', encoding='utf-8', errors='replace') as f:
            content = f.read()
            
        # Detect language
        ext_map = {
            '.py': 'python', '.js': 'javascript', '.ts': 'typescript',
            '.go': 'go', '.rs': 'rust', '.java': 'java', '.sql': 'sql'
        }
        language = 'python'
        for ext, lang in ext_map.items():
            if path.endswith(ext):
                language = lang
                break
                
        # Update active file in IDE
        file = ide.get_active_file()
        if file:
            file.name = os.path.basename(path)
            file.text_content = content
            try:
                file.language = Language(language)
            except:
                pass
            file._real_path = path  # Track real path
            ide.save_projects()
            
        return jsonify({
            'success': True,
            'path': path,
            'name': os.path.basename(path),
            'content': content,
            'language': language,
            'lines': content.count('\n') + 1,
            'braille_status': '⠕⠏⠑⠝⠑⠙'
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/fs/recent')
def fs_recent():
    """Get recently accessed paths (for quick access)"""
    # Common project locations
    home = os.path.expanduser('~')
    recent = [
        {'name': 'Home', 'path': home},
        {'name': 'Desktop', 'path': os.path.join(home, 'Desktop')},
        {'name': 'Documents', 'path': os.path.join(home, 'Documents')},
        {'name': 'CascadeProjects', 'path': os.path.join(home, 'CascadeProjects')},
        {'name': 'sal-voice', 'path': os.path.join(home, 'sal-voice')},
        {'name': 'sal-llm', 'path': os.path.join(home, 'sal-llm')},
    ]
    
    # Filter to only existing paths
    recent = [r for r in recent if os.path.exists(r['path'])]
    
    return jsonify({'recent': recent})


# ============================================
# File Management (SAL can organize files)
# ============================================

import shutil

@app.route('/api/fs/move', methods=['POST'])
def fs_move():
    """Move/rename a file or directory"""
    data = request.get_json()
    source = data.get('source')
    destination = data.get('destination')
    
    if not source or not destination:
        return jsonify({'error': 'Source and destination required'}), 400
        
    try:
        source = os.path.abspath(os.path.expanduser(source))
        destination = os.path.abspath(os.path.expanduser(destination))
        
        if not os.path.exists(source):
            return jsonify({'error': 'Source not found'}), 404
            
        # Create destination directory if needed
        os.makedirs(os.path.dirname(destination), exist_ok=True)
        
        shutil.move(source, destination)
        
        return jsonify({
            'success': True,
            'source': source,
            'destination': destination,
            'braille_status': '⠍⠕⠧⠑⠙'
        })
        
    except PermissionError:
        return jsonify({'error': 'Permission denied'}), 403
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/fs/copy', methods=['POST'])
def fs_copy():
    """Copy a file or directory"""
    data = request.get_json()
    source = data.get('source')
    destination = data.get('destination')
    
    if not source or not destination:
        return jsonify({'error': 'Source and destination required'}), 400
        
    try:
        source = os.path.abspath(os.path.expanduser(source))
        destination = os.path.abspath(os.path.expanduser(destination))
        
        if not os.path.exists(source):
            return jsonify({'error': 'Source not found'}), 404
            
        os.makedirs(os.path.dirname(destination), exist_ok=True)
        
        if os.path.isdir(source):
            shutil.copytree(source, destination)
        else:
            shutil.copy2(source, destination)
        
        return jsonify({
            'success': True,
            'source': source,
            'destination': destination,
            'braille_status': '⠉⠕⠏⠊⠑⠙'
        })
        
    except PermissionError:
        return jsonify({'error': 'Permission denied'}), 403
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/fs/delete', methods=['POST'])
def fs_delete():
    """Delete a file or directory (moves to trash conceptually)"""
    data = request.get_json()
    path = data.get('path')
    confirm = data.get('confirm', False)
    
    if not path:
        return jsonify({'error': 'Path required'}), 400
        
    if not confirm:
        return jsonify({'error': 'Deletion requires confirm=true'}), 400
        
    try:
        path = os.path.abspath(os.path.expanduser(path))
        
        if not os.path.exists(path):
            return jsonify({'error': 'Path not found'}), 404
            
        # Safety: Don't delete important directories
        protected = [os.path.expanduser('~'), '/', '/Users', '/home']
        if path in protected:
            return jsonify({'error': 'Cannot delete protected path'}), 403
            
        if os.path.isdir(path):
            shutil.rmtree(path)
        else:
            os.remove(path)
        
        return jsonify({
            'success': True,
            'deleted': path,
            'braille_status': '⠙⠑⠇⠑⠞⠑⠙'
        })
        
    except PermissionError:
        return jsonify({'error': 'Permission denied'}), 403
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/fs/mkdir', methods=['POST'])
def fs_mkdir():
    """Create a directory"""
    data = request.get_json()
    path = data.get('path')
    
    if not path:
        return jsonify({'error': 'Path required'}), 400
        
    try:
        path = os.path.abspath(os.path.expanduser(path))
        os.makedirs(path, exist_ok=True)
        
        return jsonify({
            'success': True,
            'path': path,
            'braille_status': '⠉⠗⠑⠁⠞⠑⠙'
        })
        
    except PermissionError:
        return jsonify({'error': 'Permission denied'}), 403
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/fs/organize', methods=['POST'])
def fs_organize():
    """SAL organizes files in a directory based on intent"""
    data = request.get_json()
    path = data.get('path')
    intent = data.get('intent', 'organize by type')
    
    if not path:
        return jsonify({'error': 'Path required'}), 400
        
    try:
        path = os.path.abspath(os.path.expanduser(path))
        
        if not os.path.exists(path):
            return jsonify({'error': 'Path not found'}), 404
            
        if not os.path.isdir(path):
            return jsonify({'error': 'Path must be a directory'}), 400
        
        # Ask SAL to plan the organization
        result = run_async(sal_cascade.process_intent(
            f"Organize the files in {path}. Intent: {intent}. "
            f"List current files and suggest how to reorganize them. "
            f"Create a plan but don't execute yet - just return the plan."
        ))
        
        return jsonify({
            'path': path,
            'intent': intent,
            'sal_plan': result,
            'braille_status': '⠕⠗⠛⠁⠝⠊⠵⠑'
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/sal/edit-file', methods=['POST'])
def sal_edit_file():
    """SAL edits a file based on instruction"""
    data = request.get_json()
    path = data.get('path')
    instruction = data.get('instruction')
    
    if not path or not instruction:
        return jsonify({'error': 'Path and instruction required'}), 400
        
    try:
        path = os.path.abspath(os.path.expanduser(path))
        
        if not os.path.exists(path):
            return jsonify({'error': 'File not found'}), 404
            
        # Read current content
        with open(path, 'r', encoding='utf-8', errors='replace') as f:
            current_content = f.read()
        
        # Ask SAL to edit
        result = run_async(sal_client.chat(
            f"Edit this file according to the instruction.\n\n"
            f"File: {path}\n"
            f"Instruction: {instruction}\n\n"
            f"Current content:\n```\n{current_content[:3000]}\n```\n\n"
            f"Return the complete edited file content in a code block."
        ))
        
        # Extract code from response
        new_content = current_content  # Default to original
        if result.code_blocks:
            new_content = result.code_blocks[0].get('code', current_content)
        
        # Write back
        with open(path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        
        return jsonify({
            'success': True,
            'path': path,
            'instruction': instruction,
            'original_size': len(current_content),
            'new_size': len(new_content),
            'sal_response': result.text[:500],
            'braille_status': '⠑⠙⠊⠞⠑⠙'
        })
        
    except PermissionError:
        return jsonify({'error': 'Permission denied'}), 403
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/sal/refactor-file', methods=['POST'])
def sal_refactor_file():
    """SAL refactors a file"""
    data = request.get_json()
    path = data.get('path')
    instruction = data.get('instruction', 'Clean up and improve code quality')
    
    if not path:
        return jsonify({'error': 'Path required'}), 400
        
    try:
        path = os.path.abspath(os.path.expanduser(path))
        
        if not os.path.exists(path):
            return jsonify({'error': 'File not found'}), 404
            
        # Read current content
        with open(path, 'r', encoding='utf-8', errors='replace') as f:
            current_content = f.read()
        
        # Detect language
        lang = 'python'
        for ext, l in {'.py': 'python', '.js': 'javascript', '.ts': 'typescript', '.go': 'go', '.rs': 'rust'}.items():
            if path.endswith(ext):
                lang = l
                break
        
        # Ask SAL to refactor
        result = run_async(sal_client.refactor_code(current_content, instruction, lang))
        
        # Extract refactored code
        new_content = current_content
        if result.code_blocks:
            new_content = result.code_blocks[0].get('code', current_content)
        
        # Write back
        with open(path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        
        return jsonify({
            'success': True,
            'path': path,
            'instruction': instruction,
            'original_size': len(current_content),
            'new_size': len(new_content),
            'sal_response': result.text[:500],
            'braille_status': '⠗⠑⠋⠁⠉⠞⠕⠗⠑⠙'
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


def run_ide(host='127.0.0.1', port=8888, debug=True):
    """Run the Braille IDE web server"""
    print(f"""
╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║   ⠎⠁⠇  SAL 8-Dot Braille IDE                                ║
║                                                              ║
║   Running at: http://{host}:{port}                          ║
║                                                              ║
║   Braille Menu Icons:                                        ║
║   ⠁ New Project    ⠃ Open Project    ⠉ Create File          ║
║   ⠑ Save Changes   ⠕ Run Code        ⠓ Help                 ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
    """)
    app.run(host=host, port=port, debug=debug)


if __name__ == '__main__':
    run_ide()
