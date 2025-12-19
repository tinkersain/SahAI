# 🇮🇳 SahAI - Voice-First Hindi Government Scheme Assistant

A **voice-first, agentic AI system** that helps users identify and apply for Indian government welfare schemes. The system operates **end-to-end in Hindi** with true agentic workflow (Planner-Executor-Evaluator loop).

## ✨ Key Features

### Voice-First Interaction

- **Primary**: Hindi voice input and voice output
- **Secondary**: Text input support (also in Hindi)
- Complete STT → LLM → TTS pipeline in Hindi

### True Agentic Workflow

- **Planner**: Analyzes user intent and plans next action
- **Executor**: Executes actions using tools (eligibility check, scheme lookup)
- **Evaluator**: Evaluates results and decides continuation

### Tools Used

1. **Eligibility Engine**: Checks user eligibility against scheme criteria
2. **Scheme Database**: Retrieves scheme information (mock API)
3. **AI Service** (Gemini): Smart clarifications and responses

### Memory & Conversation

- Session-based conversation memory across turns
- Handles contradictions in user information
- Context-aware responses

### Failure Handling

- STT failure recovery with fallback
- TTS fallback (gTTS → browser TTS)
- Graceful error messages in Hindi

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      SahAI System                           │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────┐     ┌──────────────────────────────────────┐ │
│  │  Voice   │────▶│           STT (Whisper)              │ │
│  │  Input   │     │         Hindi → Text                  │ │
│  └──────────┘     └───────────────┬──────────────────────┘ │
│                                   │                         │
│                                   ▼                         │
│  ┌────────────────────────────────────────────────────────┐│
│  │                    AGENT LOOP                          ││
│  │  ┌──────────┐   ┌──────────┐   ┌──────────┐           ││
│  │  │ PLANNER  │──▶│ EXECUTOR │──▶│EVALUATOR │           ││
│  │  │          │   │          │   │          │           ││
│  │  │ - Intent │   │ - Tools  │   │ - Check  │           ││
│  │  │ - State  │   │ - Action │   │ - Decide │           ││
│  │  └──────────┘   └────┬─────┘   └──────────┘           ││
│  │                      │                                 ││
│  │         ┌────────────┼────────────┐                   ││
│  │         ▼            ▼            ▼                   ││
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐              ││
│  │  │Eligibility│ │ Scheme  │ │    AI    │              ││
│  │  │  Engine  │ │Database │ │ Service  │              ││
│  │  │  (Tool)  │ │ (Tool)  │ │ (Gemini) │              ││
│  │  └──────────┘ └──────────┘ └──────────┘              ││
│  │                                                       ││
│  │  ┌──────────────────────────────────────────────────┐││
│  │  │               MEMORY                             │││
│  │  │  - User Data (age, income, etc.)                 │││
│  │  │  - Conversation History                          │││
│  │  │  - Current Context                               │││
│  │  └──────────────────────────────────────────────────┘││
│  └────────────────────────────────────────────────────────┘│
│                                   │                         │
│                                   ▼                         │
│  ┌──────────┐     ┌──────────────────────────────────────┐ │
│  │  Voice   │◀────│            TTS (gTTS)                │ │
│  │  Output  │     │          Text → Hindi                 │ │
│  └──────────┘     └──────────────────────────────────────┘ │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## 📁 Project Structure

```
SahAI/
├── app.py                 # FastAPI application (voice-first)
├── requirements.txt       # Python dependencies
├── .env                   # Environment variables (create this)
│
├── agent/
│   ├── agent.py          # Planner-Executor-Evaluator loop
│   └── memory.py         # Conversation memory management
│
├── audio/
│   ├── stt.py            # Speech-to-Text (Whisper/Google)
│   └── tts.py            # Text-to-Speech (gTTS)
│
├── services/
│   ├── ai_service.py     # Gemini AI integration
│   └── eligibility_service.py  # Eligibility checking tool
│
├── data/
│   ├── scheme_database.py # Scheme data management
│   └── schemes.json       # Government schemes data
│
├── config/
│   └── settings.py       # Application configuration
│
└── audio_output/         # Generated TTS audio files
```

## 🚀 Quick Start

### 1. Prerequisites

- Python 3.10+
- ffmpeg (for audio processing)
- Microphone access (for voice input)

### 2. Installation

```bash
# Clone repository
git clone https://github.com/tinkersain/SahAI.git
cd SahAI

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# OR
.\venv\Scripts\activate   # Windows

# Install dependencies
pip install -r requirements.txt
```

### 3. Configuration

Create `.env` file:

```env
GEMINI_API_KEY=your_gemini_api_key
WHISPER_MODEL=base
```

### 4. Run

```bash
uvicorn app:app --reload --host localhost --port 8000
```

Open http://localhost:8000 in browser.

## 🎤 Usage

### Voice Interaction (Primary)

1. Click the microphone button 🎤
2. Speak in Hindi: "मुझे पेंशन योजना के बारे में बताओ"
3. Click again to stop
4. Listen to the Hindi response

### Text Interaction (Secondary)

Type in Hindi in the text box and press Enter.

### Example Conversations

**User**: "नमस्ते"
**SahAI**: "नमस्ते! मैं सहाई हूं, आपका सरकारी योजना सहायक..."

**User**: "मैं 65 साल का हूं, पेंशन योजना के बारे में बताओ"
**SahAI**: "वृद्धावस्था पेंशन योजना के बारे में जानकारी..."

**User**: "क्या मैं इसके लिए पात्र हूं?"
**SahAI**: "आपकी वार्षिक आय क्या है?"

**User**: "2 लाख"
**SahAI**: "बधाई हो! आप वृद्धावस्था पेंशन योजना के लिए पात्र हैं..."

## 🔧 Technical Details

### Agent States

- `GREETING` - Initial welcome state
- `COLLECTING_INFO` - Gathering user information
- `CHECKING_ELIGIBILITY` - Checking scheme eligibility
- `SHOWING_RESULTS` - Displaying results
- `ERROR_RECOVERY` - Handling unclear inputs

### Tools

1. **EligibilityService.check_eligibility()** - Checks eligibility rules
2. **SchemeDatabase.get_scheme_by_id()** - Fetches scheme info
3. **AIService.generate_clarification()** - Smart Hindi responses

### Supported Schemes (Sample)

- वृद्धावस्था पेंशन (Old Age Pension)
- विधवा पेंशन (Widow Pension)
- PM आवास योजना (PM Awas Yojana)
- PM किसान (PM-KISAN)
- आयुष्मान भारत (Ayushman Bharat)
- और 20+ योजनाएं...

## 📝 API Endpoints

| Endpoint            | Method | Description              |
| ------------------- | ------ | ------------------------ |
| `/`                 | GET    | Web interface            |
| `/voice`            | POST   | Voice input (audio file) |
| `/chat`             | POST   | Text input               |
| `/audio/{filename}` | GET    | Serve TTS audio          |
| `/health`           | GET    | Health check             |
| `/session/{id}`     | GET    | Get session info         |

## 🤝 Contributing

1. Fork the repository
2. Create feature branch
3. Make changes
4. Submit pull request

## 📄 License

MIT License

---

**Built for accessible government scheme assistance in Hindi** 🇮🇳
