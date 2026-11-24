# NexoVAI // Clinical Voice Dispatch System

A production-grade, real-time Voice AI Doctor Appointment Booking System built with **Pipecat**, **Google Gemini 2.5 Flash**, **ElevenLabs STT & TTS**, **Silero VAD**, **FastAPI**, **SQLite**, and a **Swiss-inspired tactile React dispatch console**.

---

## Architecture Overview

```
nexovai-clinical-voice-dispatch/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── database.py       # SQLite schema, doctors, slots, atomic booking/cancellation logic
│   │   ├── tools.py          # Gemini function calling schemas & tool execution
│   │   ├── events.py         # Real-time WebSocket event broadcaster (/ws/events)
│   │   ├── bot.py            # Pipecat voice pipeline (Silero VAD + ElevenLabs + Gemini 2.5 Flash)
│   │   └── server.py         # FastAPI application with REST & WebSockets (/ws/voice, /ws/events)
│   ├── requirements.txt
│   ├── run.py                # Server launcher script
│   └── test_dispatch.py      # Automated verification test suite
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── TopTelemetryBar.jsx     # Telemetry bar with live connection and Try Call trigger
│   │   │   ├── DoctorSlotMatrix.jsx    # Doctor grid with tactile live-updating time-slot pills
│   │   │   ├── AppointmentLedger.jsx   # Live appointment table with real-time flash highlights
│   │   │   ├── PhoneDrawer.jsx         # Swiss hardware-inspired phone drawer (Braun / Teenage Eng.)
│   │   │   ├── AudioVisualizer.jsx     # Real-time reactive <canvas> frequency waveform
│   │   │   └── ReceiptCard.jsx         # Tactile confirmation receipt cards
│   │   ├── hooks/
│   │   │   ├── useVoiceCall.js         # Web Audio API ring tones, mic capture, WebSocket streaming
│   │   │   └── useDispatchEvents.js    # State sync and live ledger mutations over /ws/events
│   │   ├── App.jsx
│   │   ├── index.css                   # Swiss design tokens (Alabaster, carbon ink, burnt orange)
│   │   └── main.jsx
│   ├── package.json
│   ├── tailwind.config.js
│   └── vite.config.js
├── .env.example
├── .gitignore
└── README.md
```

---

## Key Technologies & AI Stack

| Component | Technology | Description |
| :--- | :--- | :--- |
| **Orchestration** | [Pipecat AI](https://github.com/pipecat-ai/pipecat) (`pipecat-ai>=1.17.0`) | Pipeline coordination, audio frame transport, and barge-in management |
| **LLM** | **Google Gemini 2.5 Flash** (`gemini-2.5-flash`) | Low-latency clinical intelligence with native function calling |
| **Speech-to-Text (STT)** | **ElevenLabs STT** (`ElevenLabsSTTService`) | Streaming real-time transcription |
| **Text-to-Speech (TTS)** | **ElevenLabs TTS** (`ElevenLabsTTSService`) | Natural, expressive medical dispatch voice generation |
| **Voice Activity Detection (VAD)** | **Silero VAD** (`SileroVADAnalyzer`) | Millisecond-accurate voice activity detection & natural barge-in interruption |
| **Backend Framework** | **FastAPI** + **Uvicorn** + **SQLite** (`aiosqlite`) | High-concurrency async REST API & bidirectional WebSockets |
| **Frontend** | **React** + **Vite** + **Tailwind CSS** | Swiss tactile design (Braun & Teenage Engineering aesthetic) |
| **Synthesized Audio** | **Browser Web Audio API** | Zero-dependency dual-tone (`440Hz + 480Hz`) ringback tone & soft hang-up tone |

---

## Conversational Dispatch Rules

1. **Voice-Only Identification**: Callers are identified **strictly by the phone number they speak aloud** (no login, no passwords, no OTPs).
2. **Mandatory Read-Back Rule**: Whenever a caller provides their phone number (for booking or canceling), the dispatch AI **must always repeat the digits back clearly** (e.g., *"Let me confirm your number: five five five, zero one four four. Is that correct?"*) and wait for affirmative confirmation before calling `book_appointment` or `cancel_appointment`.
3. **Four Clinical Specialists**:
   - **Dr. Sarah Lin** – *Cardiology* (Room 302 - Heart Center)
   - **Dr. Marcus Vance** – *Dermatology* (Room 118 - Skin Clinic)
   - **Dr. Elena Rostova** – *Neurology* (Room 405 - Neuro Wing)
   - **Dr. James Chen** – *General Medicine* (Room 201 - Primary Care)
4. **Standard Slots**: `09:30 AM`, `11:00 AM`, `02:30 PM`, `04:00 PM` available for **Today** and **Tomorrow**.

---

## Getting Started

### Prerequisites
- **Python 3.11+**
- **Node.js 18+** and **npm**

### 1. Environment Setup

Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```

Edit `.env` with your API keys:
```ini
# Google Gemini API Key
GEMINI_API_KEY=your_gemini_api_key_here

# ElevenLabs API Key & Voice ID
ELEVENLABS_API_KEY=your_elevenlabs_api_key_here
ELEVENLABS_VOICE_ID=21m00Tcm4TlvDq8ikWAM

HOST=0.0.0.0
PORT=8000
```

> [!NOTE]
> If run without API keys, the system automatically runs in **high-fidelity simulation fallback mode**, permitting complete testing of the Web Audio ringing, live reactive canvas waveform, interactive phone drawer, tools, and ledger synchronization without requiring immediate third-party credits.

---

### 2. Backend Setup & Startup

Install backend dependencies:
```bash
pip install -r backend/requirements.txt
```

Run the backend automated verification tests:
```bash
python backend/test_dispatch.py
```

Start the FastAPI backend server:
```bash
python backend/run.py
```
*The backend API will run on `http://localhost:8000` with interactive docs at `http://localhost:8000/docs`.*

---

### 3. Frontend Setup & Startup

In a separate terminal:
```bash
cd frontend
npm install
npm run dev
```
*The dispatch console will be live on `http://localhost:3000`.*

---

## Testing the Voice Dispatch System

1. Open `http://localhost:3000` in your browser.
2. Click the burnt-orange **`TRY CALL`** button in the top telemetry bar:
   - The Swiss hardware phone drawer slides open.
   - Listen to the browser-synthesized **dual-tone ringback (`440Hz + 480Hz`)**.
   - After connection, the live **monospace call timer** begins ticking and the **reactive audio waveform** activates.
   - The AI coordinator greets you: *"Thank you for calling NexoVAI Clinical Dispatch..."*
3. **Voice Booking Walkthrough**:
   - Speak or type: *"I want to book an appointment with Dr. Sarah Lin today at 02:30 PM. My phone number is 555-0199."*
   - Notice the AI triggers the **Mandatory Read-Back Rule**: *"Let me confirm your number: 5 5 5 0 1 9 9. Is that correct?"*
   - Confirm by speaking or typing: *"Yes, that's correct."*
   - Watch the inline **Booking Confirmation Receipt Card** pop into the drawer, while the **02:30 PM slot pill** in the doctor card flips to **BOOKED** and the **Appointment Ledger** flashes emerald as a new row is logged.
4. **Voice Cancellation Walkthrough**:
   - Speak or type: *"Can you cancel my appointment? My number is 555-0199."*
   - Notice the AI confirms the digits again, cancels the booking, pops a **Cancellation Receipt**, and releases the slot back to **OPEN** in real time!
5. **Reset Demo**:
   - Click the tactile **`RESET DEMO`** button in the header at any time to restore the pristine seed state.
