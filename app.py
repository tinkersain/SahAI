"""
SahAI - Voice-First Hindi Government Scheme Assistant
Voice-based AI for Indian government welfare schemes
Everything is processed by Gemini LLM
"""
import os
import uuid
import tempfile
from pathlib import Path
from typing import Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, UploadFile, File, HTTPException, Form
from fastapi.responses import JSONResponse, FileResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from config.settings import settings
from agent.agent import Agent
from agent.memory import Memory, SessionManager
from audio.stt import SpeechToText
from audio.tts import TextToSpeech
from services.ai_service import AIService
from data.scheme_database import SchemeDatabase

# Ensure directories exist
Path("audio_output").mkdir(exist_ok=True)
Path("logs").mkdir(exist_ok=True)

# Initialize services
stt = SpeechToText()
tts = TextToSpeech()
ai_service = AIService()
scheme_db = SchemeDatabase()
session_manager = SessionManager()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup/shutdown"""
    print(f"🚀 SahAI शुरू हो रहा है... ({len(scheme_db.schemes)} योजनाएं लोड की गईं)")
    yield
    print("👋 SahAI बंद हो रहा है...")
    tts.cleanup()
    session_manager.cleanup_expired()


app = FastAPI(
    title="SahAI - सरकारी योजना सहायक",
    description="Voice-first Hindi AI assistant for government schemes",
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


# Request/Response Models
class TextRequest(BaseModel):
    text: str
    session_id: Optional[str] = None


class ChatResponse(BaseModel):
    text: str
    audio_url: Optional[str] = None
    session_id: str
    user_data: Optional[dict] = None


# Exception handlers
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    error_msg = "क्षमा करें, कुछ समस्या हुई। कृपया दोबारा प्रयास करें।"
    print(f"Error: {exc}")
    return JSONResponse(
        status_code=500,
        content={"error": str(exc), "message": error_msg}
    )


def get_or_create_session(session_id: Optional[str]) -> tuple[Memory, Agent]:
    """Get existing session or create new one"""
    if session_id:
        memory = session_manager.get(session_id)
        if memory:
            return memory, Agent(memory, ai_service, scheme_db)
    
    memory = Memory()
    session_manager.add(memory)
    agent = Agent(memory, ai_service, scheme_db)
    return memory, agent


def generate_audio_response(text: str) -> Optional[str]:
    """Generate TTS audio and return URL"""
    try:
        audio_path = tts.synthesize(text)
        if audio_path:
            return f"/audio/{Path(audio_path).name}"
    except Exception as e:
        print(f"TTS error: {e}")
    return None


# ==================== API ENDPOINTS ====================

@app.get("/", response_class=HTMLResponse)
async def home():
    """Voice-first Hindi interface"""
    return """
<!DOCTYPE html>
<html lang="hi">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>सहAI - सरकारी योजना सहायक</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { 
            font-family: 'Segoe UI', Tahoma, sans-serif; 
            background: linear-gradient(135deg, #ff6b35 0%, #f7931e 100%);
            min-height: 100vh; 
            display: flex; 
            flex-direction: column;
            align-items: center;
            padding: 20px;
        }
        .container { max-width: 600px; width: 100%; }
        header { text-align: center; color: white; padding: 30px 0; }
        header h1 { font-size: 2.5em; margin-bottom: 10px; text-shadow: 2px 2px 4px rgba(0,0,0,0.2); }
        header p { font-size: 1.1em; opacity: 0.95; }
        
        .chat-box {
            background: white; 
            border-radius: 25px; 
            padding: 25px;
            box-shadow: 0 15px 50px rgba(0,0,0,0.2);
        }
        
        .messages { 
            height: 350px; 
            overflow-y: auto; 
            padding: 15px;
            background: #f8f9fa; 
            border-radius: 15px; 
            margin-bottom: 20px;
        }
        
        .message { 
            padding: 12px 18px; 
            margin: 10px 0; 
            border-radius: 18px;
            max-width: 85%; 
            line-height: 1.6;
            font-size: 1.05em;
        }
        .message strong { font-weight: 600; }
        .message em { font-style: italic; }
        .message ul, .message ol { 
            margin: 8px 0; 
            padding-left: 20px; 
        }
        .message li { margin: 4px 0; }
        .user { 
            background: linear-gradient(135deg, #ff6b35, #f7931e); 
            color: white; 
            margin-left: auto; 
        }
        .assistant { 
            background: white; 
            border: 2px solid #e0e0e0;
            box-shadow: 0 2px 8px rgba(0,0,0,0.08);
        }
        
        .voice-area {
            display: flex;
            flex-direction: column;
            align-items: center;
            gap: 15px;
        }
        
        .voice-btn {
            width: 100px;
            height: 100px;
            border-radius: 50%;
            border: none;
            background: linear-gradient(135deg, #ff6b35, #f7931e);
            color: white;
            font-size: 2.5em;
            cursor: pointer;
            transition: all 0.3s;
            box-shadow: 0 8px 25px rgba(255,107,53,0.4);
        }
        .voice-btn:hover { transform: scale(1.05); }
        .voice-btn.recording { 
            background: #e53e3e; 
            animation: pulse 1s infinite;
            box-shadow: 0 8px 25px rgba(229,62,62,0.5);
        }
        .voice-btn:disabled { opacity: 0.5; cursor: not-allowed; }
        
        @keyframes pulse { 
            0%, 100% { transform: scale(1); } 
            50% { transform: scale(1.08); } 
        }
        
        .status { 
            font-size: 1.1em; 
            color: #666; 
            min-height: 25px;
            text-align: center;
        }
        
        .text-input-area {
            display: flex;
            gap: 10px;
            margin-top: 15px;
            padding-top: 15px;
            border-top: 1px solid #eee;
        }
        
        input[type="text"] {
            flex: 1;
            padding: 12px 18px;
            border: 2px solid #ddd;
            border-radius: 25px;
            font-size: 1em;
            outline: none;
        }
        input[type="text"]:focus { border-color: #ff6b35; }
        
        .send-btn {
            padding: 12px 25px;
            border: none;
            border-radius: 25px;
            background: linear-gradient(135deg, #ff6b35, #f7931e);
            color: white;
            font-size: 1em;
            cursor: pointer;
        }
        .send-btn:hover { opacity: 0.9; }
        .send-btn:disabled { opacity: 0.5; }
        
        .info-box {
            background: white;
            border-radius: 15px;
            padding: 20px;
            margin-top: 20px;
            font-size: 0.95em;
        }
        .info-box h3 { color: #ff6b35; margin-bottom: 12px; }
        .info-box ul { padding-left: 20px; color: #555; }
        .info-box li { margin: 8px 0; }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>🇮🇳 सहAI</h1>
            <p>आवाज़ से पूछें - सरकारी योजनाओं की जानकारी पाएं</p>
        </header>
        
        <div class="chat-box">
            <div class="messages" id="messages">
                <div class="message assistant">
                    🙏 नमस्ते! मैं <strong>सहाई</strong> हूं।<br><br>
                    मैं आपको सरकारी योजनाओं की जानकारी देने और पात्रता जांचने में मदद करूंगा।<br><br>
                    🎤 <strong>माइक बटन दबाकर बोलें</strong> या नीचे लिखें।
                </div>
            </div>
            
            <div class="voice-area">
                <button class="voice-btn" id="voiceBtn" onclick="toggleVoice()">🎤</button>
                <div class="status" id="status">माइक दबाएं और बोलें</div>
            </div>
            
            <div class="text-input-area">
                <input type="text" id="textInput" placeholder="या यहां लिखें..." 
                       onkeypress="if(event.key==='Enter')sendText()">
                <button class="send-btn" id="sendBtn" onclick="sendText()">भेजें</button>
            </div>
        </div>
        
        <div class="info-box">
            <h3>📋 मैं इनमें मदद कर सकता हूं:</h3>
            <ul>
                <li>पेंशन योजना (वृद्धावस्था, विधवा, विकलांग)</li>
                <li>आवास योजना (ग्रामीण/शहरी)</li>
                <li>किसान योजनाएं (PM-KISAN, फसल बीमा)</li>
                <li>आयुष्मान भारत (स्वास्थ्य बीमा)</li>
                <li>और भी बहुत कुछ...</li>
            </ul>
        </div>
    </div>
    
    <audio id="audio" style="display:none"></audio>
    
    <script>
        let sessionId = localStorage.getItem('sahai_session') || '';
        let isRecording = false;
        let mediaRecorder = null;
        let audioChunks = [];
        let isProcessing = false;
        
        // Get elements after DOM is ready
        let voiceBtn, status, messages, audio;
        
        // Initialize when DOM is ready
        document.addEventListener('DOMContentLoaded', function() {
            voiceBtn = document.getElementById('voiceBtn');
            status = document.getElementById('status');
            messages = document.getElementById('messages');
            audio = document.getElementById('audio');
            
            // Make sure button is enabled
            if (voiceBtn) {
                voiceBtn.disabled = false;
                console.log('Voice button initialized');
            }
            
            // Welcome message after short delay
            setTimeout(() => speak('नमस्ते! माइक बटन दबाकर अपना सवाल बोलें।'), 1000);
        });
        
        // All functions defined globally so onclick can access them
        function speak(text) {
            if ('speechSynthesis' in window) {
                speechSynthesis.cancel();
                const utterance = new SpeechSynthesisUtterance(text);
                utterance.lang = 'hi-IN';
                utterance.rate = 0.9;
                speechSynthesis.speak(utterance);
            }
        }
        
        function stopSpeaking() {
            speechSynthesis.cancel();
            audio.pause();
        }
        
        function formatMarkdown(text) {
            // Convert markdown to HTML
            let html = text;
            
            // Escape HTML first
            html = html.replace(/</g, '&lt;').replace(/>/g, '&gt;');
            
            // Bold: **text** or __text__
            html = html.replace(/[*][*]([^*]+)[*][*]/g, '<strong>$1</strong>');
            html = html.replace(/__([^_]+)__/g, '<strong>$1</strong>');
            
            // Bullet points: lines starting with - or •
            html = html.replace(/^[-•] *(.+)$/gm, '<li>$1</li>');
            
            // Wrap consecutive <li> in <ul>
            html = html.replace(/(<li>[^<]*<[/]li>)+/g, '<ul>$&</ul>');
            
            // Numbered lists: lines starting with 1. 2. etc
            html = html.replace(/^[0-9]+[.] *(.+)$/gm, '<li>$1</li>');
            
            // Newlines to <br>
            html = html.replace(/\\n/g, '<br>');
            
            // Clean up extra <br> around lists
            html = html.replace(/<br><ul>/g, '<ul>');
            html = html.replace(/<[/]ul><br>/g, '</ul>');
            html = html.replace(/<br><li>/g, '<li>');
            html = html.replace(/<[/]li><br>/g, '</li>');
            
            return html;
        }
        
        function addMessage(text, type) {
            const div = document.createElement('div');
            div.className = 'message ' + type;
            div.innerHTML = formatMarkdown(text);
            messages.appendChild(div);
            messages.scrollTop = messages.scrollHeight;
        }
        
        function setStatus(text) {
            status.textContent = text;
        }
        
        function setProcessing(processing) {
            isProcessing = processing;
            if (voiceBtn) voiceBtn.disabled = processing;
            const sendBtn = document.getElementById('sendBtn');
            const textInput = document.getElementById('textInput');
            if (sendBtn) sendBtn.disabled = processing;
            if (textInput) textInput.disabled = processing;
        }
        
        async function toggleVoice() {
            console.log('toggleVoice called, isProcessing:', isProcessing, 'isRecording:', isRecording);
            if (isProcessing) {
                console.log('Button disabled - processing');
                return;
            }
            
            if (isRecording) {
                stopRecording();
            } else {
                startRecording();
            }
        }
        
        async function startRecording() {
            try {
                stopSpeaking();
                console.log('Requesting microphone access...');
                const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
                console.log('Microphone access granted');
                mediaRecorder = new MediaRecorder(stream);
                audioChunks = [];
                
                mediaRecorder.ondataavailable = e => audioChunks.push(e.data);
                mediaRecorder.onstop = () => {
                    stream.getTracks().forEach(t => t.stop());
                    processAudio();
                };
                
                mediaRecorder.start();
                isRecording = true;
                if (voiceBtn) {
                    voiceBtn.classList.add('recording');
                    voiceBtn.textContent = '⏹';
                }
                setStatus('🔴 बोलें... (फिर से दबाएं रोकने के लिए)');
                
                // Auto-stop after 30 seconds
                setTimeout(() => {
                    if (isRecording) stopRecording();
                }, 30000);
                
            } catch (err) {
                console.error('Mic error:', err);
                setStatus('❌ माइक की अनुमति दें');
                speak('कृपया माइक की अनुमति दें');
                setProcessing(false);
            }
        }
        
        function stopRecording() {
            if (mediaRecorder && isRecording) {
                mediaRecorder.stop();
                isRecording = false;
                if (voiceBtn) {
                    voiceBtn.classList.remove('recording');
                    voiceBtn.textContent = '🎤';
                }
                setStatus('⏳ समझ रहा हूं...');
            }
        }
        
        async function processAudio() {
            if (audioChunks.length === 0) {
                setProcessing(false);
                return;
            }
            
            setProcessing(true);
            const blob = new Blob(audioChunks, { type: 'audio/webm' });
            const formData = new FormData();
            formData.append('audio', blob, 'recording.webm');
            formData.append('session_id', sessionId);
            
            try {
                console.log('Sending audio to server...');
                const response = await fetch('/voice', {
                    method: 'POST',
                    body: formData
                });
                const data = await response.json();
                console.log('Server response:', data);
                
                if (data.error) {
                    setStatus('❌ ' + data.message);
                    speak(data.message);
                } else {
                    sessionId = data.session_id;
                    localStorage.setItem('sahai_session', sessionId);
                    
                    if (data.transcription) {
                        addMessage(data.transcription, 'user');
                    }
                    addMessage(data.text, 'assistant');
                    
                    // Play audio response
                    if (data.audio_url) {
                        audio.src = data.audio_url;
                        audio.play().catch(() => speak(data.text));
                    } else {
                        speak(data.text);
                    }
                    setStatus('✅ माइक दबाएं और बोलें');
                }
            } catch (err) {
                console.error('Error:', err);
                const errMsg = 'क्षमा करें, समस्या हुई। दोबारा प्रयास करें।';
                setStatus('❌ त्रुटि');
                speak(errMsg);
                addMessage(errMsg, 'assistant');
            } finally {
                // Always re-enable the button
                setProcessing(false);
            }
        }
        
        async function sendText() {
            const input = document.getElementById('textInput');
            const text = input.value.trim();
            if (!text || isProcessing) return;
            
            input.value = '';
            stopSpeaking();
            addMessage(text, 'user');
            setStatus('⏳ सोच रहा हूं...');
            setProcessing(true);
            
            try {
                const response = await fetch('/chat', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ text, session_id: sessionId })
                });
                const data = await response.json();
                
                sessionId = data.session_id;
                localStorage.setItem('sahai_session', sessionId);
                
                addMessage(data.text, 'assistant');
                
                if (data.audio_url) {
                    audio.src = data.audio_url;
                    audio.play().catch(() => speak(data.text));
                } else {
                    speak(data.text);
                }
                setStatus('✅ माइक दबाएं और बोलें');
            } catch (err) {
                console.error('Error:', err);
                speak('क्षमा करें, समस्या हुई।');
                setStatus('❌ त्रुटि');
            }
            
            setProcessing(false);
        }
    </script>
</body>
</html>
"""


@app.post("/voice")
async def voice_input(
    audio: UploadFile = File(...),
    session_id: Optional[str] = Form(None)
):
    """
    Primary endpoint - Voice input in Hindi
    Handles: Audio → STT → Agent Processing → TTS → Audio Response
    """
    memory, agent = get_or_create_session(session_id)
    
    # Save uploaded audio
    temp_path = None
    try:
        suffix = ".webm" if "webm" in (audio.content_type or "") else ".wav"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as f:
            content = await audio.read()
            f.write(content)
            temp_path = f.name
        
        # Transcribe audio (Hindi)
        transcription = stt.transcribe(temp_path)
        if not transcription or not transcription.strip():
            error_response = "आवाज़ समझ नहीं आई। कृपया फिर से बोलें।"
            return {
                "text": error_response,
                "audio_url": generate_audio_response(error_response),
                "session_id": memory.session_id,
                "transcription": None
            }
        
        # Process through agent (Gemini handles everything)
        response = agent.process(transcription)
        audio_url = generate_audio_response(response)
        
        return {
            "text": response,
            "audio_url": audio_url,
            "session_id": memory.session_id,
            "user_data": memory.user_data,
            "transcription": transcription
        }
        
    finally:
        if temp_path and os.path.exists(temp_path):
            os.unlink(temp_path)


@app.post("/chat")
async def text_input(request: TextRequest):
    """
    Secondary endpoint - Text input (also in Hindi)
    """
    memory, agent = get_or_create_session(request.session_id)
    
    text = request.text.strip()
    if not text:
        return {
            "text": "कृपया कुछ बोलें या लिखें।",
            "session_id": memory.session_id
        }
    
    # Process through agent (Gemini handles everything)
    response = agent.process(text)
    audio_url = generate_audio_response(response)
    
    return {
        "text": response,
        "audio_url": audio_url,
        "session_id": memory.session_id,
        "user_data": memory.user_data
    }


@app.get("/audio/{filename}")
async def serve_audio(filename: str):
    """Serve generated audio files"""
    file_path = Path("audio_output") / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Audio not found")
    return FileResponse(file_path, media_type="audio/mpeg")


@app.get("/health")
async def health():
    """Health check"""
    return {"status": "healthy", "schemes_loaded": len(scheme_db.schemes)}


@app.get("/session/{session_id}")
async def get_session(session_id: str):
    """Get session info for debugging"""
    memory = session_manager.get(session_id)
    if not memory:
        raise HTTPException(status_code=404, detail="Session not found")
    return {
        "session_id": memory.session_id,
        "user_data": memory.get_user_data(),
        "history_length": len(memory.history),
        "current_scheme": memory.current_scheme
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="localhost", port=8000, reload=True)
