import json
import logging
from typing import Dict, Any, Optional
from .database import (
    check_availability,
    book_appointment_db,
    cancel_appointment_db,
    get_doctors_with_slots,
    get_all_appointments
)
from .events import events_bus

logger = logging.getLogger("clinical_dispatch.tools")

# Schema definitions for Gemini Function Calling
TOOL_DEFINITIONS = [
    {
        "name": "check_doctor_availability",
        "description": "Query available open appointment slots for clinic doctors by name, medical specialty, or date (e.g. 'today' or 'tomorrow').",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "doctor_name": {
                    "type": "STRING",
                    "description": "Optional name of the doctor (e.g. 'Dr. Sarah Lin', 'Marcus Vance', 'Elena Rostova', 'James Chen')."
                },
                "specialty": {
                    "type": "STRING",
                    "description": "Optional medical specialty (e.g. 'Cardiology', 'Dermatology', 'Neurology', 'General Medicine')."
                },
                "date": {
                    "type": "STRING",
                    "description": "Optional date filter, such as 'today' or 'tomorrow', or a specific YYYY-MM-DD string."
                }
            }
        }
    },
    {
        "name": "book_appointment",
        "description": "Book a confirmed medical appointment for a patient after confirming their phone number with the mandatory read-back rule.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "patient_phone": {
                    "type": "STRING",
                    "description": "The patient's phone number as spoken aloud and verified (e.g. '555-0199' or '415-555-2671')."
                },
                "doctor_name": {
                    "type": "STRING",
                    "description": "Full or partial name of the physician (e.g. 'Dr. Sarah Lin', 'Dr. Marcus Vance', 'Dr. Elena Rostova', 'Dr. James Chen')."
                },
                "date": {
                    "type": "STRING",
                    "description": "Date of appointment, typically 'today' or 'tomorrow'."
                },
                "time_slot": {
                    "type": "STRING",
                    "description": "The time slot to book (e.g. '09:30 AM', '11:00 AM', '02:30 PM', '04:00 PM')."
                }
            },
            "required": ["patient_phone", "doctor_name", "date", "time_slot"]
        }
    },
    {
        "name": "cancel_appointment",
        "description": "Cancel an existing confirmed medical appointment associated with the patient's phone number and release the slot.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "patient_phone": {
                    "type": "STRING",
                    "description": "The patient's phone number spoken aloud and verified with the caller."
                }
            },
            "required": ["patient_phone"]
        }
    }
]

async def handle_check_doctor_availability(doctor_name: Optional[str] = None, specialty: Optional[str] = None, date: Optional[str] = None) -> Dict[str, Any]:
    res = check_availability(doctor_name, specialty, date)
    
    # Broadcast telemetry card to frontend
    await events_bus.broadcast({
        "type": "TOOL_CALL",
        "tool_name": "check_doctor_availability",
        "args": {"doctor_name": doctor_name, "specialty": specialty, "date": date},
        "result": res,
        "receipt": {
            "type": "AVAILABILITY_QUERY",
            "title": "Doctor Availability Query",
            "count": res["count"],
            "slots": res["available_slots"][:4]  # summary
        }
    })
    return res

async def handle_book_appointment(patient_phone: str, doctor_name: str, date: str, time_slot: str) -> Dict[str, Any]:
    res = book_appointment_db(patient_phone, doctor_name, date, time_slot)
    
    if res["status"] == "success":
        # Broadcast state mutation & receipt to ledger and drawer
        updated_doctors = get_doctors_with_slots()
        updated_appointments = get_all_appointments()
        
        await events_bus.broadcast({
            "type": "APPOINTMENT_BOOKED",
            "appointment": res,
            "doctors": updated_doctors,
            "appointments": updated_appointments
        })
        
        await events_bus.broadcast({
            "type": "TOOL_CALL",
            "tool_name": "book_appointment",
            "args": {"patient_phone": patient_phone, "doctor_name": doctor_name, "date": date, "time_slot": time_slot},
            "result": res,
            "receipt": {
                "type": "BOOKING_CONFIRMATION",
                "title": "Appointment Confirmed",
                "appointment_id": res["appointment_id"],
                "doctor_name": res["doctor_name"],
                "specialty": res["specialty"],
                "date": res["date"],
                "date_label": res["date_label"],
                "time_slot": res["time_slot"],
                "patient_phone": res["patient_phone"],
                "status": "confirmed"
            }
        })
    else:
        await events_bus.broadcast({
            "type": "TOOL_CALL",
            "tool_name": "book_appointment",
            "args": {"patient_phone": patient_phone, "doctor_name": doctor_name, "date": date, "time_slot": time_slot},
            "result": res,
            "receipt": {
                "type": "BOOKING_ERROR",
                "title": "Booking Failed",
                "message": res["message"]
            }
        })

    return res

async def handle_cancel_appointment(patient_phone: str) -> Dict[str, Any]:
    res = cancel_appointment_db(patient_phone)
    
    if res["status"] == "success":
        updated_doctors = get_doctors_with_slots()
        updated_appointments = get_all_appointments()
        
        await events_bus.broadcast({
            "type": "APPOINTMENT_CANCELED",
            "cancellation": res,
            "doctors": updated_doctors,
            "appointments": updated_appointments
        })
        
        await events_bus.broadcast({
            "type": "TOOL_CALL",
            "tool_name": "cancel_appointment",
            "args": {"patient_phone": patient_phone},
            "result": res,
            "receipt": {
                "type": "CANCELLATION_CONFIRMATION",
                "title": "Appointment Canceled",
                "appointment_id": res["appointment_id"],
                "doctor_name": res["doctor_name"],
                "patient_phone": res["patient_phone"],
                "released_slot": f"{res['date']} at {res['time_slot']}",
                "status": "canceled"
            }
        })
    else:
        await events_bus.broadcast({
            "type": "TOOL_CALL",
            "tool_name": "cancel_appointment",
            "args": {"patient_phone": patient_phone},
            "result": res,
            "receipt": {
                "type": "CANCELLATION_ERROR",
                "title": "Cancellation Failed",
                "message": res["message"]
            }
        })

    return res

async def execute_tool_call(tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    logger.info(f"Executing tool call '{tool_name}' with args {arguments}")
    if tool_name == "check_doctor_availability":
        return await handle_check_doctor_availability(
            doctor_name=arguments.get("doctor_name"),
            specialty=arguments.get("specialty"),
            date=arguments.get("date")
        )
    elif tool_name == "book_appointment":
        return await handle_book_appointment(
            patient_phone=str(arguments.get("patient_phone", "")),
            doctor_name=arguments.get("doctor_name", ""),
            date=arguments.get("date", "today"),
            time_slot=arguments.get("time_slot", "")
        )
    elif tool_name == "cancel_appointment":
        return await handle_cancel_appointment(
            patient_phone=str(arguments.get("patient_phone", ""))
        )
    else:
        return {"status": "error", "message": f"Unknown tool: {tool_name}"}