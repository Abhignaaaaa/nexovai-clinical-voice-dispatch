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
4. Available appointments are for Today and Tomorrow with standard time slots: 09:30 AM, 11:00 AM, 02:30 PM, 04:00 PM.
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
    
    # 1. Gemini status
    if keys["gemini_key"]:
        mask = keys["gemini_key"][:6] + "..." + keys["gemini_key"][-4:]
        print(f"  [+] GEMINI_API_KEY:     DETECTED ({mask}, length: {len(keys['gemini_key'])})")
        print(f"  [+] PRIMARY MODEL:      {keys['preferred_model']} (fallback: gemini-3.8-flash)")
    else:
        print("  [!] GEMINI_API_KEY:     NOT FOUND in .env or backend/.env")

    # 2. ElevenLabs status
    if keys["eleven_key"]:
        mask = keys["eleven_key"][:6] + "..." + keys["eleven_key"][-4:]
        print(f"  [+] ELEVENLABS_API_KEY: DETECTED ({mask}, length: {len(keys['eleven_key'])})")
        print(f"  [+] VOICE ID:           {keys['voice_id']}")
    else:
        print("  [!] ELEVENLABS_API_KEY: NOT FOUND in .env or backend/.env")

    # 3. Pipecat services test
    try:
        from pipecat.services.google.llm import GoogleLLMService
        from pipecat.services.elevenlabs.tts import ElevenLabsTTSService
        from pipecat.services.elevenlabs.stt import ElevenLabsSTTService
        from pipecat.audio.vad.silero import SileroVADAnalyzer
        print("  [+] PIPECAT SERVICES:   GoogleLLMService, ElevenLabsTTS/STT, SileroVAD loaded")
    except Exception as e:
        print(f"  [!] PIPECAT NOTICE:     {e}")

    print("="*70 + "\n")

# Run status check at module load
print_pipeline_status()

class ClinicalVoiceSession:
    """Manages conversational state, intent resolution, tool execution, and transcript distribution."""
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.history = []
        self.pending_confirmation = None # For phone number verification
        self.patient_phone = None

    async def handle_user_utterance(self, text: str) -> str:
        """Processes caller speech, runs Gemini LLM with function calling, and returns response."""
        text = text.strip()
        if not text:
            return ""

        # Broadcast caller transcript
        await events_bus.broadcast({
            "type": "TRANSCRIPT_UPDATE",
            "speaker": "CALLER",
            "text": text,
            "is_final": True
        })

        keys = get_api_keys()

        # If Gemini API key is configured, use Google Gemini with live function calling
        if keys["gemini_key"]:
            try:
                print(f"\n[AI PIPELINE] Caller Utterance: \"{text}\"")
                print(f"[AI PIPELINE] Dispatching to Google Gemini with function calling...")
                response_text = await self._run_gemini(text, keys["gemini_key"], keys["preferred_model"])
                if response_text:
                    print(f"[AI PIPELINE] Gemini Response: \"{response_text[:120]}...\"\n")
                    await events_bus.broadcast({
                        "type": "TRANSCRIPT_UPDATE",
                        "speaker": "AGENT",
                        "text": response_text,
                        "is_final": True
                    })
                    return response_text
            except Exception as e:
                print(f"\n[AI PIPELINE WARNING] Gemini Error: {e}")
                print(f"[AI PIPELINE NOTICE] Falling back to intelligent local dispatch coordinator for this turn.\n")

        # Fallback / simulated smart dispatch coordinator
        response_text = await self._run_dispatch_logic(text)
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

        client = genai.Client(api_key=api_key)

        # Gemini Tools configuration
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

        # Model resolution: try preferred model (e.g. gemini-2.5-flash), fall back to gemini-3.8-flash if deprecated
        models_to_try = [preferred_model, "gemini-3.8-flash", "gemini-flash-latest"]
        last_error = None
        response = None
        active_model = None

        for model_name in models_to_try:
            try:
                response = client.models.generate_content(
                    model=model_name,
                    contents=user_text,
                    config=config
                )
                active_model = model_name
                break
            except Exception as e:
                err_str = str(e)
                last_error = e
                if "404" in err_str or "no longer available" in err_str:
                    print(f"[AI PIPELINE] Model '{model_name}' deprecated/not found for this key. Trying next candidate...")
                    continue
                else:
                    raise e

        if not response:
            raise last_error or Exception("Could not reach Gemini model")

        # Handle Function Calls
        if response.function_calls:
            for call in response.function_calls:
                func_name = call.name
                func_args = dict(call.args) if call.args else {}
                print(f"\n>>> [GEMINI TOOL CALL TRIGGERED] Function: {func_name}")
                print(f"    Arguments: {json.dumps(func_args)}")
                
                tool_result = await execute_tool_call(func_name, func_args)
                print(f"    Result: {json.dumps(tool_result)}")

                # Send tool execution result back to Gemini for natural spoken completion
                follow_up = client.models.generate_content(
                    model=active_model,
                    contents=[
                        user_text,
                        types.Part.from_function_response(
                            name=func_name,
                            response={"result": tool_result}
                        )
                    ],
                    config=types.GenerateContentConfig(system_instruction=SYSTEM_PROMPT)
                )
                return follow_up.text or f"I have completed that for you: {tool_result.get('message', 'Done')}."

        return response.text or "Thank you for calling NexoVAI Clinical Dispatch. How else may I assist you?"

    async def _run_dispatch_logic(self, text: str) -> str:
        """Robust clinical dispatch state machine adhering to the Mandatory Read-Back Rule."""
        lower = text.lower()
        import re

        # Check if caller is confirming a previously read-back phone number
        if self.pending_confirmation:
            if any(w in lower for w in ["yes", "correct", "that's right", "right", "yep", "sure", "exactly"]):
                action = self.pending_confirmation["action"]
                phone = self.pending_confirmation["phone"]
                
                if action == "book":
                    res = await execute_tool_call("book_appointment", {
                        "patient_phone": phone,
                        "doctor_name": self.pending_confirmation.get("doctor_name", "Dr. Sarah Lin"),
                        "date": self.pending_confirmation.get("date", "today"),
                        "time_slot": self.pending_confirmation.get("time_slot", "02:30 PM")
                    })
                    self.pending_confirmation = None
                    if res["status"] == "success":
                        return f"Perfect! Your appointment with {res['doctor_name']} on {res['date_label']} at {res['time_slot']} is officially confirmed under confirmation {res['appointment_id']}. We sent a confirmation SMS to {phone}. Is there anything else I can help you with?"
                    else:
                        return f"I apologize, but {res['message']} Would you like to check another time slot?"

                elif action == "cancel":
                    res = await execute_tool_call("cancel_appointment", {"patient_phone": phone})
                    self.pending_confirmation = None
                    if res["status"] == "success":
                        return f"Thank you for confirming. Your appointment with {res['doctor_name']} on {res['date']} at {res['time_slot']} has been successfully canceled and the slot released. Can I help you with anything else?"
                    else:
                        return f"I checked our records, but {res['message']} Would you like me to look up another phone number?"

            elif any(w in lower for w in ["no", "incorrect", "wrong", "nope"]):
                self.pending_confirmation = None
                return "My apologies. Please speak your phone number again slowly so I can update it."

        # Detect phone numbers spoken in digits
        digits_match = re.findall(r'\b\d[\d\s\-]{5,}\d\b', text)
        found_phone = digits_match[0].replace(" ", "").replace("-", "") if digits_match else None

        # Check for cancellation intent
        if any(w in lower for w in ["cancel", "reschedule", "drop"]):
            if found_phone:
                self.patient_phone = found_phone
                # MANDATORY READ-BACK RULE
                spoken_digits = " ".join(list(found_phone))
                self.pending_confirmation = {"action": "cancel", "phone": found_phone}
                return f"I can certainly help you cancel that. Before I proceed, let me verify your phone number: {spoken_digits}. Is that correct?"
            else:
                return "I can help you cancel your appointment. What is the phone number associated with your booking?"

        # Check for booking intent
        if any(w in lower for w in ["book", "schedule", "reserve", "make an appointment"]):
            doc_name = None
            if "lin" in lower or "cardio" in lower:
                doc_name = "Dr. Sarah Lin"
            elif "vance" in lower or "derma" in lower:
                doc_name = "Dr. Marcus Vance"
            elif "rostova" in lower or "neuro" in lower:
                doc_name = "Dr. Elena Rostova"
            elif "chen" in lower or "general" in lower or "primary" in lower:
                doc_name = "Dr. James Chen"
            else:
                doc_name = "Dr. Sarah Lin"

            date_choice = "tomorrow" if "tomorrow" in lower else "today"
            
            time_slot = "02:30 PM"
            if "9:30" in lower or "9" in lower:
                time_slot = "09:30 AM"
            elif "11" in lower:
                time_slot = "11:00 AM"
            elif "4" in lower or "04" in lower:
                time_slot = "04:00 PM"

            if found_phone:
                self.patient_phone = found_phone
                spoken_digits = " ".join(list(found_phone))
                self.pending_confirmation = {
                    "action": "book",
                    "phone": found_phone,
                    "doctor_name": doc_name,
                    "date": date_choice,
                    "time_slot": time_slot
                }
                return f"Understood. For your booking with {doc_name} {date_choice} at {time_slot}, let me confirm your phone number: {spoken_digits}. Is that correct?"
            else:
                self.pending_target = {"doctor_name": doc_name, "date": date_choice, "time_slot": time_slot}
                return f"I would be glad to book you with {doc_name} {date_choice} at {time_slot}. What is the best phone number to reach you at?"

        # Check for availability queries
        if any(w in lower for w in ["available", "availability", "open", "free", "slots", "when", "see", "doctor", "cardiology", "dermatology", "neurology", "general"]):
            doc_query = None
            spec_query = None
            if "lin" in lower: doc_query = "Dr. Sarah Lin"
            elif "vance" in lower: doc_query = "Dr. Marcus Vance"
            elif "rostova" in lower: doc_query = "Dr. Elena Rostova"
            elif "chen" in lower: doc_query = "Dr. James Chen"

            if "cardio" in lower: spec_query = "Cardiology"
            elif "derma" in lower: spec_query = "Dermatology"
            elif "neuro" in lower: spec_query = "Neurology"
            elif "general" in lower: spec_query = "General Medicine"

            date_query = "tomorrow" if "tomorrow" in lower else ("today" if "today" in lower else None)
            res = await execute_tool_call("check_doctor_availability", {
                "doctor_name": doc_query,
                "specialty": spec_query,
                "date": date_query
            })
            slots = res.get("available_slots", [])
            if slots:
                first_few = [f"{s['doctor_name']} on {s['date_label']} at {s['time_slot']}" for s in slots[:3]]
                return f"We currently have {len(slots)} open slots. For example: {', '.join(first_few)}. Which physician and time would work best for you?"
            else:
                return "We do not have any open slots matching that criteria today or tomorrow. Would you like to check another specialty?"

        # Greeting fallback
        return "Hello! Thank you for calling NexoVAI Clinical Dispatch. I can check physician availability, book a new appointment, or cancel an existing one for you today or tomorrow. How can I assist you today?"