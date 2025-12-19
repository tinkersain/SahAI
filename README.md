# 🇮🇳 SahAI - Voice-First Hindi Government Scheme Assistant

A **voice-first, agentic AI system** that helps users identify and apply for Indian government welfare schemes. The system operates **end-to-end in Hindi** with a true **Planner-Executor-Evaluator** agentic workflow.

## ✨ Key Features Matching Requirements

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
│              AGENTIC STATE MACHINE                   │
├─────────────────────────────────────────────────────┤
│                                                      │
│  ┌──────────────────────────────────────────────┐   │
│  │              PLANNER PHASE                    │   │
│  │  • Analyze user intent                        │   │
│  │  • Extract user data from input              │   │
│  │  • Select appropriate tools                  │   │
│  │  • Create execution plan                     │   │
│  └─────────────────┬────────────────────────────┘   │
│                    ▼                                 │
│  ┌──────────────────────────────────────────────┐   │
│  │              EXECUTOR PHASE                   │   │
│  │  • Execute selected tools                    │   │
│  │  • Eligibility Engine                        │   │
│  │  • Scheme Retrieval                          │   │
│  │  • Document Checker                          │   │
│  │  • Application Status (Mock API)             │   │
│  └─────────────────┬────────────────────────────┘   │
│                    ▼                                 │
│  ┌──────────────────────────────────────────────┐   │
│  │              EVALUATOR PHASE                  │   │
│  │  • Check execution completeness              │   │
│  │  • Detect contradictions                     │   │
│  │  • Decide: respond / re-execute / clarify    │   │
│  │  • Quality score assessment                  │   │
│  └──────────────────────────────────────────────┘   │
│                                                      │
└─────────────────────────────────────────────────────┘
```

### ✅ Tool Usage (At Least 2 Tools)

1. **Eligibility Engine Tool**:

   - Checks user eligibility against scheme criteria
   - Uses age, income, gender, category, BPL status
   - Returns eligible, partially eligible, and not eligible schemes

2. **Scheme Retrieval Tool**:

   - Searches and retrieves scheme information
   - Supports query-based search
   - Returns scheme details, benefits, helplines

3. **Document Checker Tool**:

   - Lists required documents for each scheme
   - Provides document descriptions in Hindi

4. **Application Status Tool (Mock API)**:

   - Simulates checking application status
   - Returns status, stage, next steps

5. **User Data Extractor Tool**:
   - Extracts structured data from Hindi text
   - Handles age, income, gender, category patterns

### ✅ Conversation Memory Across Turns

- **Session-based memory**: Tracks user data across conversation
- **Field history tracking**: Remembers what user said and when
- **Contradiction detection**: Identifies when user provides conflicting info
- **Confirmation tracking**: Marks which data is confirmed

### ✅ Failure Handling

- **STT Error Recovery**:

  - No audio detection
  - Unclear speech handling
  - Partial transcription handling
  - Language error recovery

- **Missing Information Handling**:

  - Graceful prompts for required data
  - Explains why information is needed

- **Contradiction Resolution**:

  - Detects conflicting user statements
  - Asks for clarification
  - Allows user to confirm correct value

- **System Error Recovery**:
  - Graceful degradation
  - Fallback responses
  - Escalation to helpline when needed

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

## 📁 Project Structure

```
SahAI/
├── app.py                    # FastAPI app with voice endpoints
├── requirements.txt          # Python dependencies
├── .env                      # Environment variables (GEMINI_API_KEY)
│
├── agent/
│   ├── __init__.py          # Module exports
│   ├── agent.py             # Original simple agent (backward compat)
│   ├── agentic_agent.py     # NEW: Planner-Executor-Evaluator agent
│   ├── state_machine.py     # NEW: Agentic state machine
│   ├── tools.py             # NEW: Tool system (5 tools)
│   ├── memory.py            # Enhanced memory with contradictions
│   └── failure_handler.py   # NEW: Failure recovery system
│
├── audio/
│   ├── stt.py               # Speech-to-Text (Gemini)
│   └── tts.py               # Text-to-Speech (gTTS)
│
├── services/
│   └── ai_service.py        # Gemini LLM integration
│
├── data/
│   ├── scheme_database.py   # Scheme data management
│   └── schemes.json         # Government schemes data (10+ schemes)
│
├── config/
│   └── settings.py          # Application settings
│
├── audio_output/            # Generated TTS audio files
└── logs/                    # Application logs
```

## 🚀 Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Set Environment Variables

Create a `.env` file:

```env
GEMINI_API_KEY=your_gemini_api_key
GEMINI_MODEL=gemini-2.0-flash
```

### 3. Run the Server

```bash
python app.py
# or
uvicorn app:app --reload --port 8000
```

### 4. Access the Interface

Open `http://localhost:8000` in your browser.

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

## 📊 API Endpoints

| Endpoint             | Method | Description                    |
| -------------------- | ------ | ------------------------------ |
| `/`                  | GET    | Web UI (voice-first interface) |
| `/voice`             | POST   | Voice input (Hindi audio)      |
| `/chat`              | POST   | Text input (Hindi text)        |
| `/audio/{filename}`  | GET    | Serve generated audio          |
| `/health`            | GET    | Health check                   |
| `/session/{id}`      | GET    | Get session info               |
| `/debug/memory/{id}` | GET    | Debug memory state             |

## 🔧 Configuration

### Environment Variables

| Variable           | Description                   | Default            |
| ------------------ | ----------------------------- | ------------------ |
| `GEMINI_API_KEY`   | Google Gemini API key         | Required           |
| `GEMINI_MODEL`     | Gemini model name             | `gemini-2.0-flash` |
| `WHISPER_MODEL`    | Whisper model size (fallback) | `base`             |
| `AUDIO_OUTPUT_DIR` | TTS output directory          | `audio_output`     |

## 📝 Schemes Supported

1. **PM-KISAN** - किसान सम्मान निधि
2. **PM Awas (Gramin)** - ग्रामीण आवास योजना
3. **PM Awas (Urban)** - शहरी आवास योजना
4. **Old Age Pension** - वृद्धावस्था पेंशन
5. **Widow Pension** - विधवा पेंशन
6. **Disability Pension** - विकलांगता पेंशन
7. **Jan Dhan** - जन धन योजना
8. **Ayushman Bharat** - आयुष्मान भारत
9. **Sukanya Samriddhi** - सुकन्या समृद्धि
10. **PM Ujjwala** - उज्ज्वला योजना

## 🔒 Security Notes

- Never commit `.env` file
- API keys should be environment variables
- Session data is stored in memory (not persistent)

## 📄 License

MIT License
