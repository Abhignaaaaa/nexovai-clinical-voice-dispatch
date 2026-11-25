import os
import json
import uuid
import logging
from typing import Dict, Any
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from dotenv import load_dotenv

load_dotenv()

from .database import (
    init_db,
    seed_db,
    reset_db,
    get_doctors_with_slots,
    get_all_appointments,
    get_dates
)
from .events import events_bus
from .bot import ClinicalVoiceSession, get_api_keys

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(name)s: %(message)s')
logger = logging.getLogger("clinical_dispatch.server")

# Ensure database is seeded at boot
seed_db()

app = FastAPI(
    title="NexoVAI Clinical Voice Dispatch",
    description="Real-time Voice AI Doctor Appointment Booking System using Pipecat, Gemini 2.5 Flash, and ElevenLabs.",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

active_voice_sessions: Dict[str, ClinicalVoiceSession] = {}

@app.get("/")
@app.get("/health")
@app.get("/api/health")
async def health_check():
    return {
        "status": "ok",
        "service": "NexoVAI Clinical Voice Dispatch",
        "system": "Production Dispatch AI",
        "dates": get_dates()
    }

@app.get("/config-status")
@app.get("/api/config-status")
async def config_status():
    keys = get_api_keys()
    return {
        "gemini": bool(keys["gemini_key"]),
        "elevenlabs": bool(keys["eleven_key"]),
        "voice_id": keys["voice_id"],
        "mode": "production (live api)" if keys["has_real_keys"] else "simulation / fallback mode"
    }

@app.get("/doctors")
@app.get("/api/doctors")
async def get_doctors():
    doctors = get_doctors_with_slots()
    return {"doctors": doctors, "dates": get_dates()}

@app.get("/appointments")
@app.get("/api/appointments")
async def get_appointments():
    appointments = get_all_appointments()
    return {"appointments": appointments}

@app.post("/reset")
@app.post("/api/reset")
async def reset_demo():
    reset_db()
    doctors = get_doctors_with_slots()
    appointments = get_all_appointments()
    
    # Broadcast reset to all listening frontend clients
    await events_bus.broadcast({
        "type": "DEMO_RESET",
        "doctors": doctors,
        "appointments": appointments
    })
    return {"status": "reset_successful", "doctors": doctors, "appointments": appointments}

@app.post("/message")
@app.post("/api/message")
async def post_message(payload: Dict[str, Any]):
    session_id = payload.get("session_id", "default")
    text = payload.get("text", "")
    if session_id not in active_voice_sessions:
        active_voice_sessions[session_id] = ClinicalVoiceSession(session_id)
    
    session = active_voice_sessions[session_id]
    response_text = await session.handle_user_utterance(text)
    return {"response": response_text}

@app.websocket("/ws/events")
@app.websocket("/api/ws/events")
async def websocket_events_endpoint(websocket: WebSocket):
    await events_bus.connect(websocket)
    try:
        # Send initial state immediately
        initial_doctors = get_doctors_with_slots()
        initial_appointments = get_all_appointments()
        await websocket.send_text(json.dumps({
            "type": "INITIAL_STATE",
            "doctors": initial_doctors,
            "appointments": initial_appointments,
            "dates": get_dates()
        }))

        while True:
            data = await websocket.receive_text()
            # Heartbeat / ping handling
            if data == "ping":
                await websocket.send_text(json.dumps({"type": "pong"}))
    except WebSocketDisconnect:
        await events_bus.disconnect(websocket)
    except Exception as e:
        logger.warning(f"Events WS exception: {e}")
        await events_bus.disconnect(websocket)

@app.websocket("/ws/voice")
@app.websocket("/api/ws/voice")
async def websocket_voice_endpoint(websocket: WebSocket):
    await websocket.accept()
    session_id = str(uuid.uuid4())
    session = ClinicalVoiceSession(session_id)
    active_voice_sessions[session_id] = session
    logger.info(f"Voice call connected: session {session_id}")

    try:
        # Notify clients that call is connected
        await events_bus.broadcast({
            "type": "CALL_STATE",
            "state": "CONNECTED",
            "session_id": session_id
        })

        # Send initial greeting (no 'cancel' word to avoid false-trigger echo)
        greeting = "Thank you for calling NexoVAI Clinical Dispatch. How may I assist you with your appointment today?"
        await websocket.send_text(json.dumps({
            "type": "AGENT_MESSAGE",
            "text": greeting,
            "session_id": session_id
        }))
        await events_bus.broadcast({
            "type": "TRANSCRIPT_UPDATE",
            "speaker": "AGENT",
            "text": greeting,
            "is_final": True
        })

        while True:
            message = await websocket.receive()
            if "text" in message and message["text"]:
                try:
                    payload = json.loads(message["text"])
                    msg_type = payload.get("type")
                    
                    if msg_type == "CALLER_SPEECH":
                        transcript = payload.get("text", "")
                        response = await session.handle_user_utterance(transcript)
                        await websocket.send_text(json.dumps({
                            "type": "AGENT_MESSAGE",
                            "text": response,
                            "session_id": session_id
                        }))
                    elif msg_type == "END_CALL":
                        break
                    elif msg_type == "PING":
                        await websocket.send_text(json.dumps({"type": "PONG"}))
                except json.JSONDecodeError:
                    pass
            elif "bytes" in message and message["bytes"]:
                # Raw audio chunk (PCM 16kHz)
                pass

    except WebSocketDisconnect:
        logger.info(f"Voice call disconnected: session {session_id}")
    finally:
        active_voice_sessions.pop(session_id, None)
        await events_bus.broadcast({
            "type": "CALL_STATE",
            "state": "DISCONNECTED",
            "session_id": session_id
        })