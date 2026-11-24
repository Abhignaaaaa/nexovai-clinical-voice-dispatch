import React from 'react';
import { ClipboardList, Phone, Calendar, Clock, CheckCircle2, XCircle } from 'lucide-react';

export default function AppointmentLedger({ appointments, flashedRowId, flashType }) {
  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between border-b border-hairline pb-2">
        <div className="flex items-center gap-2">
          <ClipboardList className="w-4 h-4 text-burnt-orange" />
          <h2 className="font-mono text-xs font-bold uppercase tracking-wider text-carbon-ink">
            LIVE APPOINTMENT LEDGER
          </h2>
        </div>
        <div className="font-mono text-[10px] uppercase tracking-wider text-slate-label flex items-center gap-2">
          <span>ACTIVE ENTRIES:</span>
          <span className="font-bold text-carbon-ink tabular-nums">{appointments.length}</span>
        </div>
      </div>

      <div className="bg-white rounded-lg border border-hairline shadow-tactile overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="bg-[#F7F7F5] border-b border-hairline text-slate-label font-mono text-[10px] uppercase tracking-wider">
                <th className="py-2.5 px-4">TICKET ID</th>
                <th className="py-2.5 px-4">CALLER PHONE</th>
                <th className="py-2.5 px-4">PHYSICIAN / SPECIALTY</th>
                <th className="py-2.5 px-4">DATE & TIME</th>
                <th className="py-2.5 px-4">STATUS</th>
                <th className="py-2.5 px-4 text-right">LOGGED AT</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-hairline">
              {appointments.length === 0 ? (
                <tr>
                  <td colSpan={6} className="py-8 text-center text-slate-label font-mono text-xs">
                    NO APPOINTMENTS LOGGED YET. USE 'TRY CALL' TO TEST VOICE BOOKING.
                  </td>
                </tr>
              ) : (
                appointments.map((apt) => {
                  const isFlashed = flashedRowId === apt.id;
                  const flashClass = isFlashed
                    ? (flashType === 'amber' ? 'animate-flash-amber' : 'animate-flash-emerald')
                    : '';

                  return (
                    <tr
                      key={apt.id}
                      className={"transition-colors hover:bg-[#FBFBFA] " + flashClass}
                    >
                      {/* Ticket ID */}
                      <td className="py-3 px-4 font-mono font-medium text-carbon-ink">
                        {apt.id}
                      </td>

                      {/* Phone */}
                      <td className="py-3 px-4 font-mono text-carbon-ink tabular-nums">
                        <span className="inline-flex items-center gap-1.5 font-semibold">
                          <Phone className="w-3 h-3 text-slate-400" />
                          {apt.patient_phone}
                        </span>
                      </td>

                      {/* Doctor & Specialty */}
                      <td className="py-3 px-4">
                        <div className="font-medium text-carbon-ink">{apt.doctor_name}</div>
                        <div className="text-[10px] font-mono text-slate-label">{apt.specialty}</div>
                      </td>

                      {/* Date & Time */}
                      <td className="py-3 px-4 font-mono">
                        <div className="text-carbon-ink font-medium">{apt.date}</div>
                        <div className="text-[10px] text-slate-label tabular-nums">{apt.time_slot}</div>
                      </td>

                      {/* Status */}
                      <td className="py-3 px-4">
                        <span className={"inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-mono font-bold uppercase tracking-tight " + (
                          apt.status === 'confirmed'
                            ? "bg-emerald-subtle text-emerald-booked border border-emerald-200"
                            : "bg-amber-subtle text-amber-700 border border-amber-200"
                        )}>
                          {apt.status === 'confirmed' ? (
                            <CheckCircle2 className="w-3 h-3" />
                          ) : (
                            <XCircle className="w-3 h-3" />
                          )}
                          <span>{apt.status}</span>
                        </span>
                      </td>

                      {/* Timestamp */}
                      <td className="py-3 px-4 text-right font-mono text-[10px] text-slate-label tabular-nums">
                        {apt.created_at || 'Just now'}
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}