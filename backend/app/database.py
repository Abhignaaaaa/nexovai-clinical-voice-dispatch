import sqlite3
import datetime
import os
from typing import List, Dict, Any, Optional

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "clinical_dispatch.db")

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def get_dates():
    today = datetime.date.today()
    tomorrow = today + datetime.timedelta(days=1)
    return {
        "today_iso": today.isoformat(),
        "today_label": f"{today.strftime('%b %d')} (Today)",
        "tomorrow_iso": tomorrow.isoformat(),
        "tomorrow_label": f"{tomorrow.strftime('%b %d')} (Tomorrow)"
    }

def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS doctors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            specialty TEXT NOT NULL,
            office_room TEXT NOT NULL
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS slots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            doctor_id INTEGER NOT NULL,
            date_iso TEXT NOT NULL,
            date_label TEXT NOT NULL,
            time_slot TEXT NOT NULL,
            is_booked INTEGER DEFAULT 0,
            booked_by_phone TEXT DEFAULT NULL,
            FOREIGN KEY (doctor_id) REFERENCES doctors(id)
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS appointments (
            id TEXT PRIMARY KEY,
            patient_phone TEXT NOT NULL,
            doctor_id INTEGER NOT NULL,
            doctor_name TEXT NOT NULL,
            specialty TEXT NOT NULL,
            date TEXT NOT NULL,
            time_slot TEXT NOT NULL,
            status TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (doctor_id) REFERENCES doctors(id)
        )
    """)
    conn.commit()
    conn.close()

def seed_db():
    init_db()
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) as cnt FROM doctors")
    if cursor.fetchone()["cnt"] > 0:
        conn.close()
        return

    doctors = [
        ("Dr. Sarah Lin", "Cardiology", "Room 302 - Heart Center"),
        ("Dr. Marcus Vance", "Dermatology", "Room 118 - Skin Clinic"),
        ("Dr. Elena Rostova", "Neurology", "Room 405 - Neuro Wing"),
        ("Dr. James Chen", "General Medicine", "Room 201 - Primary Care")
    ]
    cursor.executemany("INSERT INTO doctors (name, specialty, office_room) VALUES (?, ?, ?)", doctors)
    conn.commit()

    dates = get_dates()
    time_slots = ["09:30 AM", "11:00 AM", "02:30 PM", "04:00 PM"]

    cursor.execute("SELECT id, name FROM doctors")
    doc_rows = cursor.fetchall()

    for doc in doc_rows:
        doc_id = doc["id"]
        # Today's slots
        for ts in time_slots:
            cursor.execute(
                "INSERT INTO slots (doctor_id, date_iso, date_label, time_slot, is_booked) VALUES (?, ?, ?, ?, 0)",
                (doc_id, dates["today_iso"], "Today", ts)
            )
        # Tomorrow's slots
        for ts in time_slots:
            cursor.execute(
                "INSERT INTO slots (doctor_id, date_iso, date_label, time_slot, is_booked) VALUES (?, ?, ?, ?, 0)",
                (doc_id, dates["tomorrow_iso"], "Tomorrow", ts)
            )

    # Seed 1 initial appointment for demo realism
    now_ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("SELECT id FROM slots WHERE time_slot = '09:30 AM' AND date_label = 'Today' LIMIT 1")
    s_row = cursor.fetchone()
    if s_row:
        slot_id = s_row["id"]
        cursor.execute("UPDATE slots SET is_booked = 1, booked_by_phone = '555-0144' WHERE id = ?", (slot_id,))
        cursor.execute("""
            INSERT INTO appointments (id, patient_phone, doctor_id, doctor_name, specialty, date, time_slot, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            "APT-8821", "555-0144", 1, "Dr. Sarah Lin", "Cardiology", dates["today_iso"], "09:30 AM", "confirmed", now_ts
        ))

    conn.commit()
    conn.close()

def reset_db():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DROP TABLE IF EXISTS appointments")
    cursor.execute("DROP TABLE IF EXISTS slots")
    cursor.execute("DROP TABLE IF EXISTS doctors")
    conn.commit()
    conn.close()
    seed_db()

def get_doctors_with_slots() -> List[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM doctors ORDER BY id ASC")
    doctors = [dict(row) for row in cursor.fetchall()]

    for doc in doctors:
        cursor.execute("""
            SELECT id, date_iso, date_label, time_slot, is_booked, booked_by_phone
            FROM slots
            WHERE doctor_id = ?
            ORDER BY date_iso ASC, id ASC
        """, (doc["id"],))
        doc["slots"] = [dict(s) for s in cursor.fetchall()]

    conn.close()
    return doctors

def get_all_appointments() -> List[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM appointments ORDER BY created_at DESC")
    appointments = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return appointments

def check_availability(doctor_name: Optional[str] = None, specialty: Optional[str] = None, date: Optional[str] = None) -> Dict[str, Any]:
    conn = get_connection()
    cursor = conn.cursor()
    dates = get_dates()

    query = """
        SELECT s.id as slot_id, s.date_iso, s.date_label, s.time_slot, d.id as doctor_id, d.name as doctor_name, d.specialty
        FROM slots s
        JOIN doctors d ON s.doctor_id = d.id
        WHERE s.is_booked = 0
    """
    params = []

    if doctor_name:
        clean_name = doctor_name.strip().replace("Dr. ", "").replace("Doctor ", "").lower()
        query += " AND LOWER(d.name) LIKE ?"
        params.append(f"%{clean_name}%")

    if specialty:
        clean_spec = specialty.strip().lower()
        query += " AND LOWER(d.specialty) LIKE ?"
        params.append(f"%{clean_spec}%")

    if date:
        clean_date = date.strip().lower()
        if "today" in clean_date:
            query += " AND (s.date_label = 'Today' OR s.date_iso = ?)"
            params.append(dates["today_iso"])
        elif "tomorrow" in clean_date:
            query += " AND (s.date_label = 'Tomorrow' OR s.date_iso = ?)"
            params.append(dates["tomorrow_iso"])
        else:
            query += " AND (s.date_iso LIKE ? OR s.date_label LIKE ?)"
            params.extend([f"%{clean_date}%", f"%{clean_date}%"])

    query += " ORDER BY s.date_iso ASC, d.id ASC, s.id ASC"
    cursor.execute(query, params)
    available_slots = [dict(row) for row in cursor.fetchall()]
    conn.close()

    return {
        "status": "success",
        "count": len(available_slots),
        "available_slots": available_slots,
        "message": f"Found {len(available_slots)} open appointment slot(s)."
    }

def book_appointment_db(patient_phone: str, doctor_name: str, date: str, time_slot: str) -> Dict[str, Any]:
    conn = get_connection()
    cursor = conn.cursor()
    dates = get_dates()

    # Normalize phone
    clean_phone = patient_phone.strip()
    
    # Normalize doctor
    clean_doc = doctor_name.strip().replace("Dr. ", "").replace("Doctor ", "").lower()
    cursor.execute("SELECT id, name, specialty FROM doctors WHERE LOWER(name) LIKE ? OR LOWER(specialty) LIKE ?", (f"%{clean_doc}%", f"%{clean_doc}%"))
    doctor = cursor.fetchone()
    if not doctor:
        conn.close()
        return {"status": "error", "message": f"Could not find a physician matching '{doctor_name}'."}

    doc_id = doctor["id"]
    doc_real_name = doctor["name"]
    doc_specialty = doctor["specialty"]

    # Normalize date
    clean_date_str = date.strip().lower()
    target_date_iso = dates["today_iso"] if "today" in clean_date_str else dates["tomorrow_iso"]
    target_date_label = "Today" if "today" in clean_date_str else "Tomorrow"
    if "today" not in clean_date_str and "tomorrow" not in clean_date_str:
        if clean_date_str in dates["today_iso"]:
            target_date_iso = dates["today_iso"]
            target_date_label = "Today"
        elif clean_date_str in dates["tomorrow_iso"]:
            target_date_iso = dates["tomorrow_iso"]
            target_date_label = "Tomorrow"

    # Normalize time slot
    clean_ts = time_slot.strip().upper()
    # Normalize variants e.g. "9:30" -> "09:30 AM", "2:30" -> "02:30 PM", "4" -> "04:00 PM"
    if "9:30" in clean_ts:
        clean_ts = "09:30 AM"
    elif "11" in clean_ts:
        clean_ts = "11:00 AM"
    elif "2:30" in clean_ts or "02:30" in clean_ts:
        clean_ts = "02:30 PM"
    elif "4" in clean_ts or "04" in clean_ts:
        clean_ts = "04:00 PM"

    # Look for available slot
    cursor.execute("""
        SELECT id FROM slots
        WHERE doctor_id = ? AND date_iso = ? AND time_slot = ? AND is_booked = 0
    """, (doc_id, target_date_iso, clean_ts))
    slot = cursor.fetchone()

    if not slot:
        # Check if slot exists but is booked
        cursor.execute("""
            SELECT id FROM slots
            WHERE doctor_id = ? AND date_iso = ? AND time_slot = ?
        """, (doc_id, target_date_iso, clean_ts))
        if cursor.fetchone():
            conn.close()
            return {"status": "error", "message": f"The {clean_ts} slot on {target_date_label} for {doc_real_name} is already booked."}
        conn.close()
        return {"status": "error", "message": f"Slot {clean_ts} on {target_date_label} for {doc_real_name} does not exist."}

    slot_id = slot["id"]

    # Generate appointment ID
    import random
    apt_id = f"APT-{random.randint(1000, 9999)}"
    now_ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Mark slot booked
    cursor.execute("UPDATE slots SET is_booked = 1, booked_by_phone = ? WHERE id = ?", (clean_phone, slot_id))

    # Insert appointment
    cursor.execute("""
        INSERT INTO appointments (id, patient_phone, doctor_id, doctor_name, specialty, date, time_slot, status, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, 'confirmed', ?)
    """, (apt_id, clean_phone, doc_id, doc_real_name, doc_specialty, target_date_iso, clean_ts, now_ts))

    conn.commit()
    conn.close()

    return {
        "status": "success",
        "appointment_id": apt_id,
        "patient_phone": clean_phone,
        "doctor_name": doc_real_name,
        "specialty": doc_specialty,
        "date": target_date_iso,
        "date_label": target_date_label,
        "time_slot": clean_ts,
        "created_at": now_ts,
        "message": f"Appointment successfully confirmed for {doc_real_name} on {target_date_label} ({target_date_iso}) at {clean_ts}."
    }

def cancel_appointment_db(patient_phone: str) -> Dict[str, Any]:
    conn = get_connection()
    cursor = conn.cursor()
    clean_phone = patient_phone.strip()

    # Find active appointment
    cursor.execute("""
        SELECT * FROM appointments
        WHERE patient_phone = ? AND status = 'confirmed'
        ORDER BY created_at DESC
        LIMIT 1
    """, (clean_phone,))
    appointment = cursor.fetchone()

    if not appointment:
        conn.close()
        return {
            "status": "error",
            "message": f"No active confirmed appointment found for phone number {clean_phone}."
        }

    apt_id = appointment["id"]
    doc_id = appointment["doctor_id"]
    date_iso = appointment["date"]
    ts = appointment["time_slot"]
    doc_name = appointment["doctor_name"]

    # Mark slot as available
    cursor.execute("""
        UPDATE slots
        SET is_booked = 0, booked_by_phone = NULL
        WHERE doctor_id = ? AND date_iso = ? AND time_slot = ?
    """, (doc_id, date_iso, ts))

    # Update appointment status
    cursor.execute("UPDATE appointments SET status = 'canceled' WHERE id = ?", (apt_id,))

    conn.commit()
    conn.close()

    return {
        "status": "success",
        "appointment_id": apt_id,
        "patient_phone": clean_phone,
        "doctor_name": doc_name,
        "date": date_iso,
        "time_slot": ts,
        "message": f"Appointment {apt_id} with {doc_name} on {date_iso} at {ts} has been canceled and the slot released."
    }

if __name__ == "__main__":
    reset_db()
    print("Database seeded successfully.")
    docs = get_doctors_with_slots()
    print(f"Loaded {len(docs)} doctors.")
    avail = check_availability()
    print(f"Available slots: {avail['count']}")