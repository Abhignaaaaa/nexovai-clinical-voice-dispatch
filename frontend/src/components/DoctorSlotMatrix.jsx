import React from 'react';
import { Stethoscope, CheckCircle, Clock, ShieldCheck, MapPin } from 'lucide-react';

export default function DoctorSlotMatrix({ doctors, onSelectSlot }) {
  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between border-b border-hairline pb-2">
        <div className="flex items-center gap-2">
          <Stethoscope className="w-4 h-4 text-burnt-orange" />
          <h2 className="font-mono text-xs font-bold uppercase tracking-wider text-carbon-ink">
            PHYSICIAN & SLOT MATRIX
          </h2>
        </div>
        <span className="font-mono text-[10px] uppercase tracking-wider text-slate-label">
          LIVE SYNCHRONIZED
        </span>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {doctors.map((doctor) => {
          const totalSlots = doctor.slots ? doctor.slots.length : 0;
          const openSlots = doctor.slots ? doctor.slots.filter(s => !s.is_booked).length : 0;
          
          const todaySlots = doctor.slots ? doctor.slots.filter(s => s.date_label === 'Today') : [];
          const tomorrowSlots = doctor.slots ? doctor.slots.filter(s => s.date_label === 'Tomorrow') : [];

          return (
            <div
              key={doctor.id}
              className="bg-white rounded-lg border border-hairline p-4 shadow-tactile hover:shadow-tactile-hover transition-all duration-200"
            >
              {/* Doctor Header */}
              <div className="flex items-start justify-between border-b border-hairline pb-3 mb-3">
                <div>
                  <div className="flex items-center gap-2">
                    <h3 className="font-semibold text-sm text-carbon-ink">
                      {doctor.name}
                    </h3>
                    <span className="inline-block px-2 py-0.5 rounded text-[10px] font-mono font-medium bg-[#F0F0EE] text-slate-label border border-hairline">
                      {doctor.specialty}
                    </span>
                  </div>
                  <div className="flex items-center gap-1 text-[11px] text-slate-label mt-1">
                    <MapPin className="w-3 h-3 text-slate-400" />
                    <span>{doctor.office_room}</span>
                  </div>
                </div>

                {/* Capacity Counter */}
                <div className="text-right">
                  <span className={"inline-flex items-center gap-1 font-mono text-[11px] font-semibold px-2 py-0.5 rounded " + (
                    openSlots > 0 ? "bg-emerald-subtle text-emerald-booked" : "bg-red-50 text-red-600"
                  )}>
                    <span className="w-1.5 h-1.5 rounded-full bg-current"></span>
                    <span className="tabular-nums">{openSlots} / {totalSlots} OPEN</span>
                  </span>
                </div>
              </div>

              {/* Slot Schedule: Today */}
              <div className="mb-3">
                <div className="font-mono text-[10px] uppercase tracking-wider text-slate-label mb-1.5 flex items-center justify-between">
                  <span>TODAY'S SCHEDULE</span>
                  <span className="text-[9px] text-slate-400">09:30 - 16:00</span>
                </div>
                <div className="grid grid-cols-4 gap-1.5">
                  {todaySlots.map((slot) => (
                    <button
                      key={slot.id}
                      onClick={() => onSelectSlot && onSelectSlot(doctor, slot)}
                      title={slot.is_booked ? ("Booked by " + (slot.booked_by_phone || "Patient")) : "Click to test booking"}
                      className={"py-1.5 px-1 rounded text-center font-mono text-[11px] font-medium transition-all duration-200 border " + (
                        slot.is_booked
                          ? "bg-emerald-subtle border-emerald-300 text-emerald-booked cursor-default shadow-sm"
                          : "bg-[#FAFAFA] hover:bg-white hover:border-burnt-orange border-hairline text-carbon-ink shadow-sm"
                      )}
                    >
                      <div className="tabular-nums leading-tight">{slot.time_slot}</div>
                      <div className="text-[8px] uppercase tracking-tighter mt-0.5 font-bold">
                        {slot.is_booked ? "BOOKED" : "OPEN"}
                      </div>
                    </button>
                  ))}
                </div>
              </div>

              {/* Slot Schedule: Tomorrow */}
              <div>
                <div className="font-mono text-[10px] uppercase tracking-wider text-slate-label mb-1.5 flex items-center justify-between">
                  <span>TOMORROW'S SCHEDULE</span>
                  <span className="text-[9px] text-slate-400">NEXT DAY</span>
                </div>
                <div className="grid grid-cols-4 gap-1.5">
                  {tomorrowSlots.map((slot) => (
                    <button
                      key={slot.id}
                      onClick={() => onSelectSlot && onSelectSlot(doctor, slot)}
                      title={slot.is_booked ? ("Booked by " + (slot.booked_by_phone || "Patient")) : "Click to test booking"}
                      className={"py-1.5 px-1 rounded text-center font-mono text-[11px] font-medium transition-all duration-200 border " + (
                        slot.is_booked
                          ? "bg-emerald-subtle border-emerald-300 text-emerald-booked cursor-default shadow-sm"
                          : "bg-[#FAFAFA] hover:bg-white hover:border-burnt-orange border-hairline text-carbon-ink shadow-sm"
                      )}
                    >
                      <div className="tabular-nums leading-tight">{slot.time_slot}</div>
                      <div className="text-[8px] uppercase tracking-tighter mt-0.5 font-bold">
                        {slot.is_booked ? "BOOKED" : "OPEN"}
                      </div>
                    </button>
                  ))}
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}