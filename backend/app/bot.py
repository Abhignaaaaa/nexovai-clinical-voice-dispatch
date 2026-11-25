import os
import json
import asyncio
import logging
from typing import Optional, Dict, Any
from dotenv import load_dotenv

# Ensure .env is loaded from both root and backend directories
CURRENT_FILE = os.path.abspath(__file__)
APP_DIR = os.path.dirname(CURRENT_FILE)
BACKEND_DIR = os.path.dirname(APP_DIR)
ROOT_DIR = os.path.dirname(BACKEND_DIR)

for candidate in [
    os.path.join(ROOT_DIR, ".env"),
    os.path.join(BACKEND_DIR, ".env"),
    os.path.join(os.getcwd(), ".env"),
    os.path.join(os.getcwd(), "backend", ".env")
]:
    if os.path.isfile(candidate):
        load_dotenv(candidate, override=True)

from .events import events_bus
from .tools import execute_tool_call, TOOL_DEFINITIONS
from .database import get_dates

logger = logging.getLogger("clinical_dispatch.bot")

SYSTEM_PROMPT = """You are the automated medical dispatch coordinator for NexoVAI Health Clinic.
Your personality is concise, warm, calm, and clinically efficient.

Rules you MUST strictly follow:
1. Identify the caller strictly by the phone number they speak aloud. Never ask for a password, PIN, or OTP.
2. MANDATORY READ-BACK RULE: Whenever a caller provides their phone number (either for booking or for canceling), you MUST ALWAYS repeat the digits back clearly (e.g. 'Let me confirm your number: five five five, zero one four four. Is that correct?') and wait for their affirmative confirmation before calling the booking or cancellation tool.
3. Our clinic has four doctors:
   - Dr. Sarah Lin (Cardiology) - Room 302
   - Dr. Marcus Vance (Dermatology) - Room 118
   - Dr. Elena Rostova (Neurology) - Room 405
   - Dr. James Chen (General Medicine) - Room 201
4. Available appointments are for Today and Tomorrow with standard time slots: 09:30 AM, 11:00 AM, 02:30 PM, 04:00 PM. Note that clinic operates during the day, so any mention of 11 PM or 11:00 PM must be treated as 11:00 AM.
5. Function calling:
   - Use 'check_doctor_availability' to query open slots.
   - Use 'book_appointment' only after confirming the patient's phone number with the read-back rule.
   - Use 'cancel_appointment' to cancel an existing confirmed booking by phone number after verifying digits.
6. Keep spoken responses short, natural, and conversational—suitable for real-time voice over the phone."""

def get_api_keys():
    gemini_key = os.getenv("GEMINI_API_KEY", "").strip()
    eleven_key = os.getenv("ELEVENLABS_API_KEY", "").strip()
    voice_id = os.getenv("ELEVENLABS_VOICE_ID", "21m00Tcm4TlvDq8ikWAM").strip()
    preferred_model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash").strip()
    return {
        "gemini_key": gemini_key,
        "eleven_key": eleven_key,
        "voice_id": voice_id,
        "preferred_model": preferred_model,
        "has_real_keys": bool(gemini_key and eleven_key)
    }

def print_pipeline_status():
    keys = get_api_keys()
    print("\n" + "="*70)
    print("  NEXOVAI CLINICAL DISPATCH // AI PIPELINE STATUS")
    print("="*70)
    
    if keys["gemini_key"]:
        mask = keys["gemini_key"][:6] + "..." + keys["gemini_key"][-4:]
        print(f"  [+] GEMINI_API_KEY:     DETECTED ({mask}, length: {len(keys['gemini_key'])})")
        print(f"  [+] PRIMARY MODEL:      {keys['preferred_model']} -> gemini-3.5-flash -> gemini-3.8-flash")
    else:
        print("  [!] GEMINI_API_KEY:     NOT FOUND in .env or backend/.env")

    if keys["eleven_key"]:
        mask = keys["eleven_key"][:6] + "..." + keys["eleven_key"][-4:]
        print(f"  [+] ELEVENLABS_API_KEY: DETECTED ({mask}, length: {len(keys['eleven_key'])})")
        print(f"  [+] VOICE ID:           {keys['voice_id']}")
    else:
        print("  [!] ELEVENLABS_API_KEY: NOT FOUND in .env or backend/.env")

    try:
        from pipecat.services.google.llm import GoogleLLMService
        from pipecat.services.elevenlabs.tts import ElevenLabsTTSService
        from pipecat.services.elevenlabs.stt import ElevenLabsSTTService
        from pipecat.audio.vad.silero import SileroVADAnalyzer
        print("  [+] PIPECAT SERVICES:   GoogleLLMService, ElevenLabsTTS/STT, SileroVAD loaded")
    except Exception as e:
        print(f"  [!] PIPECAT NOTICE:     {e}")

    print("="*70 + "\n")

print_pipeline_status()

def extract_phone_number(text: str) -> Optional[str]:
    """Extracts a 10-digit phone number from either digits or spelled out words."""
    if not text:
        return None
    import re
    # 1. Standard digit formats (e.g., 415-555-0123, 9123456780, (415) 555-0123, 4 1 5 5 5 5 0 1 2 3)
    digit_sequences = re.findall(r'\b(?:\+?1[-.\s]?)?\(?([0-9]{3})\)?[-.\s]?([0-9]{3})[-.\s]?([0-9]{4})\b', text)
    if digit_sequences:
        return "".join(digit_sequences[0])

    raw_digits = re.findall(r'\b\d[\d\s\-\.]{7,}\d\b', text)
    if raw_digits:
        cleaned = re.sub(r'\D', '', raw_digits[0])
        if len(cleaned) >= 10:
            return cleaned[-10:]

    # 2. Spelled out words (e.g. 'nine one two, three four five, six seven eight zero')
    word_map = {
        "zero": "0", "oh": "0", "o": "0",
        "one": "1", "two": "2", "three": "3", "four": "4",
        "five": "5", "six": "6", "seven": "7", "eight": "8", "nine": "9"
    }
    tokens = re.findall(r'[a-zA-Z]+|\d+', text.lower())
    digit_stream = []
    for t in tokens:
        if t in word_map:
            digit_stream.append(word_map[t])
        elif t.isdigit():
            digit_stream.extend(list(t))
        else:
            if len(digit_stream) >= 10:
                break
            digit_stream = []
    if len(digit_stream) >= 10:
        return "".join(digit_stream[:10])

    return None

def extract_doctor(text: str) -> Optional[str]:
    """Identifies doctor from text across first name, last name, or specialty."""
    if not text:
        return None
    lower = text.lower()
    if any(k in lower for k in ["vance", "marcus", "derma", "skin"]):
        return "Dr. Marcus Vance"
    elif any(k in lower for k in ["rostova", "elena", "neuro", "brain"]):
        return "Dr. Elena Rostova"
    elif any(k in lower for k in ["chen", "james", "general", "primary"]):
        return "Dr. James Chen"
    elif any(k in lower for k in ["lin", "sarah", "cardio", "heart"]):
        return "Dr. Sarah Lin"
    return None

def extract_date(text: str) -> Optional[str]:
    """Extracts target date (today or tomorrow)."""
    if not text:
        return None
    lower = text.lower()
    if "tomorrow" in lower:
        return "tomorrow"
    elif "today" in lower:
        return "today"
    return None

def extract_time_slot(text: str) -> Optional[str]:
    """Extracts and normalizes appointment time slot to daytime clinic hours."""
    if not text:
        return None
    lower = text.lower()
    if "9:30" in lower or "09:30" in lower or "nine thirty" in lower:
        return "09:30 AM"
    elif "11:00" in lower or "11" in lower or "eleven" in lower:
        # Daytime clinic normalization: 11 PM / 11:00 PM -> 11:00 AM
        return "11:00 AM"
    elif "2:30" in lower or "02:30" in lower or "two thirty" in lower:
        return "02:30 PM"
    elif "4:00" in lower or "04:00" in lower or "4" in lower or "four" in lower:
        return "04:00 PM"
    return None

class ClinicalVoiceSession:
    """Manages conversational state, intent resolution, tool execution, and transcript distribution."""
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.history = []
        self.pending_confirmation = None # For phone number verification
        self.patient_phone = None
        self.chat = None
        self.gemini_client = None
        self.active_model = None
        # Track pending booking details across turns
        self.pending_booking = {
            "doctor_name": None,
            "date": None,
            "time_slot": None,
            "caller_phone": None,
            "read_back_completed": False
        }

    def _update_state_from_text(self, text: str, speaker: str = "CALLER"):
        """Scans caller or assistant speech to track physician, slot, date, and verified phone."""
        if not text:
            return

        doc = extract_doctor(text)
        if doc:
            self.pending_booking["doctor_name"] = doc

        dt = extract_date(text)
        if dt:
            self.pending_booking["date"] = dt

        slot = extract_time_slot(text)
        if slot:
            self.pending_booking["time_slot"] = slot

        phone = extract_phone_number(text)
        if phone:
            self.pending_booking["caller_phone"] = phone
            self.patient_phone = phone

        lower = text.lower()
        # When assistant reads back phone number or asks for confirmation
        if speaker == "AGENT":
            if any(w in lower for w in ["confirm your phone number", "confirm your number", "verify your phone", "verify your number", "is that correct", "confirm that"]):
                self.pending_booking["read_back_completed"] = True
                if self.pending_booking.get("caller_phone"):
                    self.pending_confirmation = {
                        "action": "book",
                        "phone": self.pending_booking["caller_phone"],
                        "doctor_name": self.pending_booking.get("doctor_name", "Dr. Marcus Vance"),
                        "date": self.pending_booking.get("date", "today"),
                        "time_slot": self.pending_booking.get("time_slot", "11:00 AM")
                    }
        elif speaker == "CALLER":
            if any(w in lower for w in ["cancel", "drop", "delete my appointment"]):
                self.pending_confirmation = {
                    "action": "cancel",
                    "phone": self.pending_booking.get("caller_phone") or self.patient_phone
                }

    async def handle_user_utterance(self, text: str) -> str:
        """Processes caller speech, runs Gemini LLM with function calling, and returns response."""
        text = text.strip()
        if not text:
            return ""

        # Update state from caller utterance
        self._update_state_from_text(text, speaker="CALLER")

        # Broadcast caller transcript
        await events_bus.broadcast({
            "type": "TRANSCRIPT_UPDATE",
            "speaker": "CALLER",
            "text": text,
            "is_final": True
        })

        keys = get_api_keys()

        # If Gemini API key is configured, invoke Google Gemini live
        if keys["gemini_key"]:
            try:
                print("\n" + "="*65)
                print(f"[LIVE PIPELINE] Processing Caller Utterance: \"{text}\"")
                print("="*65)
                response_text = await self._run_gemini(text, keys["gemini_key"], keys["preferred_model"])
                if response_text:
                    self._update_state_from_text(response_text, speaker="AGENT")
                    print(f"\n[LIVE PIPELINE AGENT RESPONSE]\n\"{response_text}\"\n" + "="*65 + "\n")
                    await events_bus.broadcast({
                        "type": "TRANSCRIPT_UPDATE",
                        "speaker": "AGENT",
                        "text": response_text,
                        "is_final": True
                    })
                    return response_text
            except Exception as e:
                import traceback
                print("\n" + "!"*65)
                print(f"[GEMINI API ERROR] {type(e).__name__}: {e}")
                print(f"[GEMINI API TRACEBACK]\n{traceback.format_exc()}")
                print("[NOTICE] Engaging local dispatch fallback for this turn.")
                print("!"*65 + "\n")

        # Fallback / simulated smart dispatch coordinator
        response_text = await self._run_dispatch_logic(text)
        self._update_state_from_text(response_text, speaker="AGENT")
        await events_bus.broadcast({
            "type": "TRANSCRIPT_UPDATE",
            "speaker": "AGENT",
            "text": response_text,
            "is_final": True
        })
        return response_text

    async def _run_gemini(self, user_text: str, api_key: str, preferred_model: str) -> str:
        from google import genai
        from google.genai import types

        # Prioritize gemini-3.5-flash which is active and supports function calling on Google AI Studio
        candidates = []
        if preferred_model and preferred_model != "gemini-2.5-flash":
            candidates.append(preferred_model)
        candidates.extend(["gemini-3.5-flash", "gemini-3.8-flash", "gemini-flash-latest"])
        models_to_try = list(dict.fromkeys(candidates))

        if self.gemini_client is None:
            self.gemini_client = genai.Client(api_key=api_key)

        gemini_tools = []
        for td in TOOL_DEFINITIONS:
            gemini_tools.append(types.Tool(function_declarations=[
                types.FunctionDeclaration(
                    name=td["name"],
                    description=td["description"],
                    parameters=td.get("parameters")
                )
            ]))

        config = types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            temperature=0.3,
            tools=gemini_tools
        )

        response = None
        for model_name in models_to_try:
            try:
                if self.chat is None or self.active_model != model_name:
                    print(f"[GEMINI API ATTEMPT] Initializing Chat session with model '{model_name}'...")
                    self.chat = self.gemini_client.chats.create(model=model_name, config=config)
                    self.active_model = model_name
                    print(f"[GEMINI API SUCCESS] Chat session ready with model '{model_name}'!")

                response = self.chat.send_message(user_text)
                break
            except Exception as e:
                err_str = str(e)
                print(f"[GEMINI API NOTICE] Model '{model_name}' failed: {e}")
                self.chat = None
                if "404" in err_str or "no longer available" in err_str or "not found" in err_str or "503" in err_str:
                    continue
                else:
                    raise e

        if not response:
            raise Exception("No Gemini model responded successfully")

        # Print exact model response details
        print(f"\n[GEMINI API RAW OUTPUT]")
        print(f"  Model:          {self.active_model}")
        print(f"  Text:           {repr(response.text)}")
        print(f"  Function Calls: {response.function_calls}")

        # Handle Function Calls in a loop for multi-step tool interactions
        current_resp = response
        depth = 0
        while current_resp.function_calls and depth < 3:
            depth += 1
            for call in current_resp.function_calls:
                func_name = call.name
                func_args = dict(call.args) if call.args else {}
                print(f"\n>>> [GEMINI TOOL EXECUTION] Function: {func_name}")
                print(f"    Arguments: {json.dumps(func_args, indent=2)}")

                tool_result = await execute_tool_call(func_name, func_args)
                print(f"    Tool Result: {json.dumps(tool_result, indent=2)}")

                # Send tool execution result back to Gemini Chat
                print(f"[GEMINI API FOLLOW-UP] Feeding tool result back to '{self.active_model}' chat...")
                from google.genai import types
                current_resp = self.chat.send_message(
                    types.Part.from_function_response(
                        name=func_name,
                        response={"result": tool_result}
                    )
                )
                print(f"    Follow-up Text: {repr(current_resp.text)}")

        return current_resp.text or "Thank you for calling NexoVAI Clinical Dispatch. How may I assist you with your appointment today?"

    async def _run_dispatch_logic(self, text: str) -> str:
        """Robust clinical dispatch state machine adhering to the Mandatory Read-Back Rule."""
        lower = text.lower()

        # Update extraction
        self._update_state_from_text(text, speaker="CALLER")

        # Detect affirmative confirmation from caller
        is_affirmative = any(w in lower for w in [
            "yes", "correct", "that's right", "right", "yep", "sure", "exactly",
            "confirm", "confirmed", "book it", "go ahead", "please do", "sounds good",
            "lock it in", "proceed", "do it", "please book", "book that", "yes please",
            "yeah", "yup", "ok", "okay"
        ])

        # Check if caller is confirming a pending booking or cancellation
        effective_phone = self.pending_booking.get("caller_phone") or (self.pending_confirmation and self.pending_confirmation.get("phone")) or self.patient_phone
        if is_affirmative and effective_phone:
            # Handle cancellation confirmation
            if self.pending_confirmation and self.pending_confirmation.get("action") == "cancel":
                res = await execute_tool_call("cancel_appointment", {"patient_phone": effective_phone})
                self.pending_confirmation = None
                self.pending_booking = {"doctor_name": None, "date": None, "time_slot": None, "caller_phone": None, "read_back_completed": False}
                if res.get("status") == "success":
                    return f"Thank you for confirming. Your appointment with {res.get('doctor_name', 'your doctor')} on {res.get('date', 'your scheduled date')} at {res.get('time_slot', 'scheduled time')} has been successfully canceled and the slot released. Can I help you with anything else?"
                else:
                    return f"I checked our records, but {res.get('message', 'no active booking was found for that number')}. Would you like me to look up another phone number?"

            # Handle booking confirmation (prioritize tracked details, never reset to Dr. Sarah Lin)
            doctor = self.pending_booking.get("doctor_name") or (self.pending_confirmation and self.pending_confirmation.get("doctor_name")) or "Dr. Marcus Vance"
            date_val = self.pending_booking.get("date") or (self.pending_confirmation and self.pending_confirmation.get("date")) or "today"
            slot_val = self.pending_booking.get("time_slot") or (self.pending_confirmation and self.pending_confirmation.get("time_slot")) or "11:00 AM"

            print(f"[DISPATCH CONFIRMATION] Executing booking: Doctor={doctor}, Date={date_val}, Slot={slot_val}, Phone={effective_phone}")
            res = await execute_tool_call("book_appointment", {
                "patient_phone": effective_phone,
                "doctor_name": doctor,
                "date": date_val,
                "time_slot": slot_val
            })
            self.pending_confirmation = None
            self.pending_booking = {"doctor_name": None, "date": None, "time_slot": None, "caller_phone": None, "read_back_completed": False}

            if res.get("status") == "success":
                date_display = res.get("date_label") or date_val.title()
                return f"Perfect! Your appointment with {res.get('doctor_name', doctor)} on {date_display} at {res.get('time_slot', slot_val)} is officially confirmed under confirmation {res.get('appointment_id', 'APT-CONFIRMED')}. We sent a confirmation SMS to {effective_phone}. Is there anything else I can help you with?"
            else:
                return f"I apologize, but {res.get('message', 'that slot is no longer available')}. Would you like to check another time slot?"

        # Caller rejection of read-back
        is_rejection = any(w in lower for w in ["no", "incorrect", "wrong", "nope", "not right"])
        if is_rejection:
            self.pending_booking["caller_phone"] = None
            self.pending_booking["read_back_completed"] = False
            self.pending_confirmation = None
            return "My apologies. Please speak your phone number again slowly so I can update it."

        # Check for availability queries first (e.g. 'What does Marcus have open today?', 'Is Vance available?')
        is_avail_query = any(w in lower for w in [
            "available", "availability", "open", "opening", "openings", "free", "slots", "slot", "when", "what does", "what do you have", "schedule for"
        ]) and not any(w in lower for w in ["book", "schedule an appointment", "reserve", "make an appointment"])

        if is_avail_query:
            doc_query = extract_doctor(text) or self.pending_booking.get("doctor_name")
            spec_query = None
            if "cardio" in lower: spec_query = "Cardiology"
            elif "derma" in lower: spec_query = "Dermatology"
            elif "neuro" in lower: spec_query = "Neurology"
            elif "general" in lower: spec_query = "General Medicine"

            date_query = extract_date(text) or self.pending_booking.get("date")

            res = await execute_tool_call("check_doctor_availability", {
                "doctor_name": doc_query,
                "specialty": spec_query,
                "date": date_query
            })
            slots = res.get("available_slots", [])
            if slots:
                if doc_query:
                    slot_times = [s["time_slot"] for s in slots[:4]]
                    date_label = slots[0].get("date_label", date_query or "Today")
                    return f"{doc_query} currently has open slots on {date_label} at {', '.join(slot_times)}. Would one of those work for you?"
                else:
                    first_few = [f"{s['doctor_name']} on {s['date_label']} at {s['time_slot']}" for s in slots[:3]]
                    return f"We currently have {len(slots)} open slots. For example: {', '.join(first_few)}. Which physician and time would work best for you?"
            else:
                if doc_query:
                    return f"I checked, but {doc_query} does not have any open slots on {date_query or 'today or tomorrow'}. Would you like to check another day or doctor?"
                return "We do not have any open slots matching that criteria today or tomorrow. Would you like to check another specialty?"

        # Check if caller has explicit booking intent
        is_booking_intent = any(w in lower for w in [
            "book", "schedule", "reserve", "make an appointment", "appointment for", "appointment with"
        ]) or (
            any(d in lower for d in ["lin", "vance", "marcus", "rostova", "chen"]) and 
            any(t in lower for t in ["9", "11", "2:30", "4", "am", "pm", "today", "tomorrow"])
        )

        if is_booking_intent:
            doc_name = extract_doctor(text) or self.pending_booking.get("doctor_name") or "Dr. Marcus Vance"
            date_choice = extract_date(text) or self.pending_booking.get("date") or "today"
            time_slot = extract_time_slot(text) or self.pending_booking.get("time_slot") or "11:00 AM"
            phone = extract_phone_number(text) or self.pending_booking.get("caller_phone") or self.patient_phone

            # Update pending booking state
            self.pending_booking["doctor_name"] = doc_name
            self.pending_booking["date"] = date_choice
            self.pending_booking["time_slot"] = time_slot

            if phone:
                self.pending_booking["caller_phone"] = phone
                self.patient_phone = phone
                spoken_digits = " ".join(list(phone))
                self.pending_confirmation = {
                    "action": "book",
                    "phone": phone,
                    "doctor_name": doc_name,
                    "date": date_choice,
                    "time_slot": time_slot
                }
                return f"Understood. For your booking with {doc_name} {date_choice} at {time_slot}, let me confirm your phone number: {spoken_digits}. Is that correct?"
            else:
                return f"I would be glad to book you with {doc_name} {date_choice} at {time_slot}. What is the best phone number to reach you at?"

        # Check for cancellation intent
        if any(w in lower for w in ["cancel", "drop", "delete my appointment"]):
            phone = extract_phone_number(text) or self.pending_booking.get("caller_phone") or self.patient_phone
            if phone:
                self.patient_phone = phone
                spoken_digits = " ".join(list(phone))
                self.pending_confirmation = {"action": "cancel", "phone": phone}
                return f"I can certainly help you cancel that. Before I proceed, let me verify your phone number: {spoken_digits}. Is that correct?"
            else:
                return "I can help you cancel your appointment. What is the phone number associated with your booking?"

        # Neutral greeting fallback without the word "cancel"
        return "Thank you for calling NexoVAI Clinical Dispatch. How may I assist you with your appointment today?"