# 🎓 Vidya — AI Literacy Teaching Bot
### Phase 1: Basic Voice Bot

Vidya is an AI-powered voice teacher for uneducated adults and children.
It speaks in the user's native Indian language, adapts to their level,
and teaches with patience and warmth.

---

## Phase 1 — What's Built

- ✅ Pipecat voice pipeline (STT → LLM → TTS)
- ✅ Sarvam Saarika STT — auto-detects Indian languages
- ✅ OpenAI GPT-4o — patient teacher persona
- ✅ Sarvam Bulbul TTS — slow, clear voice (pace=0.8)
- ✅ Provider abstraction layer (providers.py)
- ✅ FastAPI backend + Daily.co room creation
- ✅ Browser frontend with image card area reserved

---

## Project Structure

```
vidya/
├── providers.py        ← THE ONLY FILE THAT KNOWS WHICH SERVICES ARE USED
├── agent.py            ← Pipecat pipeline (never imports services directly)
├── backend.py          ← FastAPI server + Daily room creation
├── requirements.txt
├── .env.example        ← Copy to .env and add your keys
└── frontend/
    └── index.html      ← Browser UI (mic button + image card area)
```

---

## Setup

### Step 1 — Get API Keys

| Service | Where to get it | Used for |
|---------|----------------|----------|
| Sarvam AI | dashboard.sarvam.ai | STT + TTS |
| OpenAI | platform.openai.com/api-keys | GPT-4o |
| Daily.co | dashboard.daily.co/developers | WebRTC transport |

### Step 2 — Clone and install

```bash
git clone <your-repo>
cd vidya
pip install -r requirements.txt
```

### Step 3 — Configure API keys

```bash
cp .env.example .env
# Open .env and fill in your three API keys
```

### Step 4 — Run the backend

```bash
uvicorn backend:app --reload --port 8000
```

Visit http://localhost:8000/api/health — you should see all three keys confirmed.

### Step 5 — Run the Vidya agent (in a second terminal)

```bash
python agent.py
```

The agent will start and wait for a student to connect via Daily.co.

### Step 6 — Open the browser

Visit **http://localhost:8000** and click **"Start Learning with Vidya"**.

Vidya will greet you, ask your name, and begin the conversation.

---

## How to Swap a Provider (Future-Proofing)

Open `providers.py` and change the relevant function.
That's the **only file you ever need to change.**

| What you want to swap | Function to change |
|----------------------|-------------------|
| GPT-4o → Claude / Gemini / Mistral | `get_llm()` |
| Sarvam STT → Whisper / Deepgram | `get_stt()` |
| Sarvam TTS → ElevenLabs / Azure | `get_tts()` |
| Daily.co → LiveKit / Twilio | `get_transport_params()` |

---

## Troubleshooting

**"DAILY_API_KEY not set"** → Make sure `.env` exists and has your Daily key.

**"Module not found: pipecat"** → Run `pip install -r requirements.txt` again.

**Bot doesn't respond** → Check that both `agent.py` AND `uvicorn backend:app` are running simultaneously.

**Poor transcription** → Sarvam auto-detects language. Speak clearly. Works best with Hindi, Telugu, Tamil, Kannada, Bengali.

**Bot speaks too fast** → `pace` is set to 0.8 in `providers.py`. Lower it further (e.g. 0.6) if needed.

---

## What's Coming in Phase 2

- 7-question voice onboarding to profile each student
- SQLite database for user profiles and learning progress
- Custom learning path assigned after onboarding
- Session save and reload — students resume where they left off

---

*Build Vidya. Teach India. One voice at a time.* 🎓
