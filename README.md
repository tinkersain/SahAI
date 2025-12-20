---
title: SahAI
emoji: 🇮🇳
colorFrom: orange
colorTo: green
sdk: docker
pinned: false
license: mit
app_port: 7860
---

# 🇮🇳 SahAI - Voice-First Hindi Government Scheme Assistant

<p align="center">
  <img src="static/favicon.svg" alt="SahAI Logo" width="120" height="120">
</p>

<p align="center">
  <strong>A voice-first, agentic AI system that helps users identify and apply for Indian government welfare schemes.</strong>
</p>

<p align="center">
  The system operates <strong>end-to-end in Hindi</strong> with a true <strong>Planner-Executor-Evaluator</strong> agentic workflow.
</p>

---

## 📋 Table of Contents

- [Features](#-key-features)
- [System Architecture](#-system-architecture)
- [Project Structure](#-project-structure)
- [Installation](#-installation)
- [Configuration](#-configuration)
- [Running the Application](#-running-the-application)
- [API Endpoints](#-api-endpoints)
- [Example Interactions](#-example-interactions)
- [Supported Schemes](#-schemes-supported)
- [Troubleshooting](#-troubleshooting)
- [License](#-license)

---

## ✨ Key Features

### ✅ Voice-First Interaction (MANDATORY)

- **Primary**: Hindi voice input and voice output using Gemini STT + gTTS
- **Secondary**: Text input support (also in Hindi)
- Complete STT → LLM → TTS pipeline in Hindi

### ✅ Native Language Support (Non-English)

- End-to-end Hindi language processing
- Hindi STT (Speech-to-Text) using Gemini
- Hindi LLM reasoning using Gemini
- Hindi TTS (Text-to-Speech) using gTTS

### ✅ True Agentic Workflow (Planner-Executor-Evaluator Loop)

```
┌─────────────────────────────────────────────────────┐
│              AGENTIC STATE MACHINE                  │
├─────────────────────────────────────────────────────┤
│                                                     │
│  ┌──────────────────────────────────────────────┐   │
│  │              PLANNER PHASE                   │   │
│  │  • Analyze user intent                       │   │
│  │  • Extract user data from input              │   │
│  │  • Select appropriate tools                  │   │
│  │  • Create execution plan                     │   │
│  └─────────────────┬────────────────────────────┘   │
│                    ▼                                │
│  ┌──────────────────────────────────────────────┐   │
│  │              EXECUTOR PHASE                  │   │
│  │  • Execute selected tools                    │   │
│  │  • Eligibility Engine                        │   │
│  │  • Scheme Retrieval                          │   │
│  │  • Document Checker                          │   │
│  │  • Application Status (Mock API)             │   │
│  └─────────────────┬────────────────────────────┘   │
│                    ▼                                │
│  ┌──────────────────────────────────────────────┐   │
│  │              EVALUATOR PHASE                 │   │
│  │  • Check execution completeness              │   │
│  │  • Detect contradictions                     │   │
│  │  • Decide: respond / re-execute / clarify    │   │
│  │  • Quality score assessment                  │   │
│  └──────────────────────────────────────────────┘   │
│                                                     │
└─────────────────────────────────────────────────────┘
```

### ✅ Tool Usage (5 Tools Available)

| Tool                    | Description                                                                                     |
| ----------------------- | ----------------------------------------------------------------------------------------------- |
| **Eligibility Engine**  | Checks user eligibility against scheme criteria using age, income, gender, category, BPL status |
| **Scheme Retrieval**    | Searches and retrieves scheme information with query-based search                               |
| **Document Checker**    | Lists required documents for each scheme with Hindi descriptions                                |
| **Application Status**  | Simulates checking application status (Mock API)                                                |
| **User Data Extractor** | Extracts structured data from Hindi text (age, income, gender patterns)                         |

### ✅ Conversation Memory Across Turns

- **Session-based memory**: Tracks user data across conversation
- **Field history tracking**: Remembers what user said and when
- **Contradiction detection**: Identifies when user provides conflicting info
- **Confirmation tracking**: Marks which data is confirmed

### ✅ Comprehensive Failure Handling

- **STT Error Recovery**: No audio detection, unclear speech, partial transcription, language errors
- **Missing Information Handling**: Graceful prompts for required data
- **Contradiction Resolution**: Detects conflicting statements and asks for clarification
- **System Error Recovery**: Graceful degradation and fallback responses

---

## 🏗️ System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        SahAI System v3.0                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────┐     ┌────────────────────────────────────────┐    │
│  │  🎤 Voice │────▶│      STT (Gemini Hindi)               │    │
│  │  Input   │     │    Audio → Hindi Text + Confidence     │    │
│  └──────────┘     └──────────────────┬─────────────────────┘    │
│                                      │                           │
│                                      ▼                           │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │                  AGENTIC AGENT                             │  │
│  │  ┌─────────────────────────────────────────────────────┐  │  │
│  │  │                 STATE MACHINE                        │  │  │
│  │  │  IDLE → RECEIVING → PLANNING → EXECUTING →          │  │  │
│  │  │  EVALUATING → GENERATING_RESPONSE → COMPLETE        │  │  │
│  │  └─────────────────────────────────────────────────────┘  │  │
│  │                                                            │  │
│  │  ┌───────────┐    ┌───────────┐    ┌───────────┐         │  │
│  │  │  PLANNER  │───▶│ EXECUTOR  │───▶│ EVALUATOR │         │  │
│  │  └───────────┘    └─────┬─────┘    └───────────┘         │  │
│  │                         │                                  │  │
│  │         ┌───────────────┼───────────────┐                 │  │
│  │         ▼               ▼               ▼                 │  │
│  │  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐      │  │
│  │  │ Eligibility  │ │   Scheme     │ │  Document    │      │  │
│  │  │   Engine     │ │  Retrieval   │ │   Checker    │      │  │
│  │  └──────────────┘ └──────────────┘ └──────────────┘      │  │
│  │         │               │               │                 │  │
│  │         └───────────────┼───────────────┘                 │  │
│  │                         ▼                                  │  │
│  │  ┌─────────────────────────────────────────────────────┐  │  │
│  │  │                    MEMORY                            │  │  │
│  │  │  • User Data (age, income, gender, category)        │  │  │
│  │  │  • Conversation History (20 turns)                  │  │  │
│  │  │  • Contradiction Tracking                           │  │  │
│  │  │  • Failure Context                                  │  │  │
│  │  └─────────────────────────────────────────────────────┘  │  │
│  │                                                            │  │
│  │  ┌─────────────────────────────────────────────────────┐  │  │
│  │  │               FAILURE HANDLER                        │  │  │
│  │  │  • STT Error Recovery                                │  │  │
│  │  │  • Missing Info Prompts                              │  │  │
│  │  │  • Contradiction Resolution                          │  │  │
│  │  │  • Escalation Logic                                  │  │  │
│  │  └─────────────────────────────────────────────────────┘  │  │
│  └───────────────────────────────────────────────────────────┘  │
│                                      │                           │
│                                      ▼                           │
│  ┌──────────┐     ┌────────────────────────────────────────┐    │
│  │  🔊 Voice │◀────│      TTS (gTTS Hindi)                 │    │
│  │  Output  │     │    Hindi Text → Audio                  │    │
│  └──────────┘     └────────────────────────────────────────┘    │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 📁 Project Structure

```
SahAI/
├── app.py                    # FastAPI app with voice endpoints
├── requirements.txt          # Python dependencies
├── .env                      # Environment variables (GEMINI_API_KEY)
├── .env.example              # Example environment file
├── README.md                 # This file
│
├── agent/
│   ├── __init__.py          # Module exports
│   ├── agent.py             # Original simple agent (backward compat)
│   ├── agentic_agent.py     # Planner-Executor-Evaluator agent
│   ├── state_machine.py     # Agentic state machine
│   ├── tools.py             # Tool system (5 tools)
│   ├── memory.py            # Enhanced memory with contradictions
│   └── failure_handler.py   # Failure recovery system
│
├── audio/
│   ├── __init__.py          # Module exports
│   ├── stt.py               # Speech-to-Text (Gemini)
│   └── tts.py               # Text-to-Speech (gTTS)
│
├── services/
│   ├── __init__.py          # Module exports
│   └── ai_service.py        # Gemini LLM integration
│
├── data/
│   ├── __init__.py          # Module exports
│   ├── scheme_database.py   # Scheme data management
│   └── schemes.json         # Government schemes data (10+ schemes)
│
├── config/
│   ├── __init__.py          # Module exports
│   └── settings.py          # Application settings
│
├── static/
│   └── favicon.svg          # Application favicon
│
├── audio_output/            # Generated TTS audio files
└── logs/                    # Application logs
```

---

## 🛠️ Installation

### Prerequisites

- **Python 3.10+** (Recommended: Python 3.11 or 3.12)
- **pip** (Python package manager)
- **Git** (for cloning the repository)
- **Google Gemini API Key** (Get one from [Google AI Studio](https://aistudio.google.com/))

### Step 1: Clone the Repository

```bash
git clone https://github.com/yourusername/SahAI.git
cd SahAI
```

### Step 2: Create a Virtual Environment

#### On Windows (Command Prompt)

```cmd
python -m venv venv
venv\Scripts\activate
```

#### On Windows (PowerShell)

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

> **Note**: If you get an execution policy error in PowerShell, run:
>
> ```powershell
> Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
> ```

#### On macOS/Linux

```bash
python3 -m venv venv
source venv/bin/activate
```

### Step 3: Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 4: Verify Installation

```bash
pip list
```

You should see packages like `fastapi`, `uvicorn`, `google-genai`, `gtts`, etc.

---

## ⚙️ Configuration

### Step 1: Create Environment File

Copy the example environment file:

```bash
# On Windows
copy .env.example .env

# On macOS/Linux
cp .env.example .env
```

Or create a new `.env` file manually:

```env
# Required: Google Gemini API Key
GEMINI_API_KEY=your_gemini_api_key_here

# Optional: Model Configuration
GEMINI_MODEL=gemini-2.0-flash

# Optional: Whisper model (fallback STT)
WHISPER_MODEL=base

# Optional: Audio output directory
AUDIO_OUTPUT_DIR=audio_output
```

### Step 2: Get Your Gemini API Key

1. Go to [Google AI Studio](https://aistudio.google.com/)
2. Sign in with your Google account
3. Click on "Get API Key" or navigate to API Keys section
4. Create a new API key
5. Copy the key and paste it in your `.env` file

### Environment Variables Reference

| Variable           | Description                   | Required | Default            |
| ------------------ | ----------------------------- | -------- | ------------------ |
| `GEMINI_API_KEY`   | Google Gemini API key         | ✅ Yes   | -                  |
| `GEMINI_MODEL`     | Gemini model name             | No       | `gemini-2.0-flash` |
| `WHISPER_MODEL`    | Whisper model size (fallback) | No       | `base`             |
| `AUDIO_OUTPUT_DIR` | TTS output directory          | No       | `audio_output`     |

---

## 🚀 Running the Application

### Development Mode (with auto-reload)

```bash
# Make sure your virtual environment is activated
uvicorn app:app --reload --host localhost --port 8000
```

### Production Mode

```bash
uvicorn app:app --host 0.0.0.0 --port 8000 --workers 4
```

### Using Python directly

```bash
python app.py
```

### Access the Application

Open your browser and navigate to:

- **Web Interface**: [http://localhost:8000](http://localhost:8000)
- **API Documentation**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **Alternative API Docs**: [http://localhost:8000/redoc](http://localhost:8000/redoc)

---

## 📊 API Endpoints

| Endpoint             | Method | Description                    |
| -------------------- | ------ | ------------------------------ |
| `/`                  | GET    | Web UI (voice-first interface) |
| `/voice`             | POST   | Voice input (Hindi audio file) |
| `/chat`              | POST   | Text input (Hindi text)        |
| `/audio/{filename}`  | GET    | Serve generated audio files    |
| `/health`            | GET    | Health check endpoint          |
| `/session/{id}`      | GET    | Get session information        |
| `/debug/memory/{id}` | GET    | Debug memory state             |
| `/docs`              | GET    | Swagger API documentation      |
| `/redoc`             | GET    | ReDoc API documentation        |

### Example API Usage

#### Text Chat

```bash
curl -X POST "http://localhost:8000/chat" \
     -H "Content-Type: application/json" \
     -d '{"text": "मेरी उम्र 65 साल है", "session_id": null}'
```

#### Voice Input

```bash
curl -X POST "http://localhost:8000/voice" \
     -F "audio=@voice_recording.wav" \
     -F "session_id="
```

---

## 🎯 Example Interactions

### Eligibility Check Flow

```
User (Voice): "मेरी उम्र 65 साल है और आय 1 लाख है, कौन सी योजना मिल सकती है?"

Agent Processing:
1. PLANNER: Intent=eligibility_check, Tools=[eligibility_engine, scheme_retrieval]
2. EXECUTOR:
   - user_data_extractor → age=65, income=100000
   - eligibility_engine → [old-age-pension: eligible, ayushman: eligible]
3. EVALUATOR: Complete, quality=0.95
4. RESPONSE: "आप वृद्धावस्था पेंशन योजना और आयुष्मान भारत के लिए पात्र हैं..."

Agent (Voice): "आप 2 योजनाओं के लिए पात्र हैं:
1. राष्ट्रीय वृद्धावस्था पेंशन - ₹500/माह
2. आयुष्मान भारत - ₹5 लाख स्वास्थ्य बीमा
हेल्पलाइन: 1800-111-555"
```

### Contradiction Handling Flow

```
User: "मेरी उम्र 45 साल है"
Agent: "ठीक है, आपकी उम्र 45 साल नोट कर ली।"

User: "मेरी उम्र 55 साल है"
Agent: "आपने पहले उम्र 45 साल बताई थी, अब 55 साल बता रहे हैं। कौन सी सही है?"

User: "55 सही है"
Agent: "ठीक है, मैंने उम्र 55 साल अपडेट किया है।"
```

### STT Error Recovery Flow

```
[Unclear audio detected]
Agent: "समझ नहीं आया। कृपया धीरे और साफ़ बोलें।"

[Still unclear]
Agent: "कृपया दूसरे शब्दों में बताएं।"

[Third attempt unclear]
Agent: "आप चाहें तो लिखकर भी बता सकते हैं।"
```

---

## 📝 Schemes Supported

| #   | Scheme Name        | Hindi Name         | Key Benefit                |
| --- | ------------------ | ------------------ | -------------------------- |
| 1   | PM-KISAN           | किसान सम्मान निधि  | ₹6000/year for farmers     |
| 2   | PM Awas (Gramin)   | ग्रामीण आवास योजना | Housing assistance (Rural) |
| 3   | PM Awas (Urban)    | शहरी आवास योजना    | Housing assistance (Urban) |
| 4   | Old Age Pension    | वृद्धावस्था पेंशन  | ₹500/month for elderly     |
| 5   | Widow Pension      | विधवा पेंशन        | Pension for widows         |
| 6   | Disability Pension | विकलांगता पेंशन    | Pension for disabled       |
| 7   | Jan Dhan           | जन धन योजना        | Zero-balance bank account  |
| 8   | Ayushman Bharat    | आयुष्मान भारत      | ₹5 lakh health insurance   |
| 9   | Sukanya Samriddhi  | सुकन्या समृद्धि    | Girl child savings scheme  |
| 10  | PM Ujjwala         | उज्ज्वला योजना     | Free LPG connection        |

---

## 🔧 Troubleshooting

### Common Issues

#### 1. Virtual Environment Not Activating (Windows PowerShell)

```powershell
# Run this command first
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

# Then try activating again
.\venv\Scripts\Activate.ps1
```

#### 2. Module Not Found Error

```bash
# Make sure virtual environment is activated
# You should see (venv) in your terminal prompt

# Reinstall dependencies
pip install -r requirements.txt
```

#### 3. Gemini API Key Error

- Ensure your `.env` file exists in the project root
- Check that `GEMINI_API_KEY` is set correctly (no quotes needed)
- Verify your API key is valid at [Google AI Studio](https://aistudio.google.com/)

#### 4. Port Already in Use

```bash
# Use a different port
uvicorn app:app --reload --host localhost --port 8001
```

#### 5. Audio Not Working

- Check that your microphone is properly connected
- Allow browser access to microphone when prompted
- Ensure `audio_output` directory exists and is writable

### Getting Help

If you encounter any issues:

1. Check the console/terminal for error messages
2. Review the logs in the `logs/` directory
3. Open an issue on the GitHub repository

---

## 🔒 Security Notes

- ⚠️ **Never commit your `.env` file** to version control
- ⚠️ Keep your API keys secure and rotate them periodically
- ⚠️ Session data is stored in memory (not persistent across restarts)
- ⚠️ For production, use proper authentication and HTTPS

---

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- [Google Gemini](https://ai.google.dev/) for AI/LLM capabilities
- [FastAPI](https://fastapi.tiangolo.com/) for the web framework
- [gTTS](https://gtts.readthedocs.io/) for Hindi text-to-speech
- Indian Government for welfare scheme information

---

<p align="center">
  Made with ❤️ for India 🇮🇳
</p>
