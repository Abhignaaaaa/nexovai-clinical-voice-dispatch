import asyncio
import os
import sys

# Ensure backend root is in sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.database import (
    reset_db,
    get_doctors_with_slots,
    get_all_appointments,
    check_availability,
    book_appointment_db,
    cancel_appointment_db
)
from app.tools import execute_tool_call
from app.bot import ClinicalVoiceSession

async def run_tests():
    print("=== TEST 1: Database Initialization & Seeding ===")
    reset_db()
    doctors = get_doctors_with_slots()
    assert len(doctors) == 4, f"Expected 4 doctors, got {len(doctors)}"
    for doc in doctors:
        assert len(doc["slots"]) == 8, f"Expected 8 slots (4 today + 4 tomorrow) for {doc['name']}, got {len(doc['slots'])}"
    print(f"Seeded 4 doctors with 8 slots each (Total 32 slots).")

    print("\n=== TEST 2: check_doctor_availability Tool ===")
    avail_all = await execute_tool_call("check_doctor_availability", {})
    assert avail_all["status"] == "success"
    print(f"check_doctor_availability() returned {avail_all['count']} open slots.")

    avail_cardio = await execute_tool_call("check_doctor_availability", {"specialty": "Cardiology", "date": "today"})
    print(f"Dr. Lin Cardiology open slots today: {avail_cardio['count']}")
    assert avail_cardio["count"] > 0

    print("\n=== TEST 3: book_appointment Tool ===")
    test_phone = "555-0199"
    book_res = await execute_tool_call("book_appointment", {
        "patient_phone": test_phone,
        "doctor_name": "Dr. Sarah Lin",
        "date": "today",
        "time_slot": "02:30 PM"
    })
    print(f"Booking result: {book_res['status']} -> {book_res.get('appointment_id')} ({book_res['message']})")
    assert book_res["status"] == "success"
    apt_id = book_res["appointment_id"]

    # Verify slot is marked booked in DB
    updated_doctors = get_doctors_with_slots()
    dr_lin = next(d for d in updated_doctors if "Lin" in d["name"])
    booked_slot = next(s for s in dr_lin["slots"] if s["time_slot"] == "02:30 PM" and s["date_label"] == "Today")
    assert booked_slot["is_booked"] == 1
    assert booked_slot["booked_by_phone"] == test_phone
    print("Slot 02:30 PM successfully locked to patient phone 555-0199.")

    print("\n=== TEST 4: Double-booking Prevention ===")
    dup_res = await execute_tool_call("book_appointment", {
        "patient_phone": "555-9999",
        "doctor_name": "Dr. Sarah Lin",
        "date": "today",
        "time_slot": "02:30 PM"
    })
    print(f"Duplicate booking prevention: {dup_res['status']} -> {dup_res['message']}")
    assert dup_res["status"] == "error"

    print("\n=== TEST 5: cancel_appointment Tool ===")
    cancel_res = await execute_tool_call("cancel_appointment", {"patient_phone": test_phone})
    print(f"Cancel result: {cancel_res['status']} -> {cancel_res['message']}")
    assert cancel_res["status"] == "success"

    # Verify slot is released
    updated_doctors_after_cancel = get_doctors_with_slots()
    dr_lin_after = next(d for d in updated_doctors_after_cancel if "Lin" in d["name"])
    freed_slot = next(s for s in dr_lin_after["slots"] if s["time_slot"] == "02:30 PM" and s["date_label"] == "Today")
    assert freed_slot["is_booked"] == 0
    assert freed_slot["booked_by_phone"] is None
    print("Slot 02:30 PM successfully released back to open status.")

    print("\n=== TEST 6: Conversational Session & Mandatory Read-Back Rule ===")
    session = ClinicalVoiceSession("test-session")
    
    # 6a. Caller asks for booking
    resp1 = await session.handle_user_utterance("I would like to book an appointment with Dr. Elena Rostova tomorrow at 11:00 AM. My number is 415-555-0123.")
    print("Caller: 'I would like to book an appointment with Dr. Elena Rostova tomorrow at 11:00 AM. My number is 415-555-0123.'")
    print(f"Agent: {resp1}")
    assert "confirm your phone number" in resp1 or "verify" in resp1
    assert "4 1 5 5 5 5 0 1 2 3" in resp1 or "415" in resp1
    print("-> Mandatory Read-Back Rule successfully triggered.")

    # 6b. Caller confirms
    resp2 = await session.handle_user_utterance("Yes, that is correct.")
    print("Caller: 'Yes, that is correct.'")
    print(f"Agent: {resp2}")
    assert "confirmed" in resp2.lower()
    print("-> Appointment confirmed upon caller confirmation.")

    print("\nALL AUTOMATED TESTS PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    asyncio.run(run_tests())
