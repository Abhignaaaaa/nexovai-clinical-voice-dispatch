import React from 'react';
import { CheckCircle2, XCircle, Calendar, Clock, User, Phone, Stethoscope } from 'lucide-react';

export default function ReceiptCard({ receipt }) {
  if (!receipt) return null;

  if (receipt.type === 'BOOKING_CONFIRMATION') {
    return (
      <div className='my-2 p-3 bg-white border border-[#15803D]/30 rounded shadow-sm font-mono text-xs text-carbon-ink relative overflow-hidden transition-all duration-300'>
        {/* Top green accent strip */}
        <div className='absolute top-0 left-0 right-0 h-1 bg-[#15803D]' />

        <div className='flex items-center justify-between border-b border-hairline pb-2 mb-2'>
          <div className='flex items-center gap-1.5 text-[#15803D] font-semibold text-[11px] tracking-wider uppercase'>
            <CheckCircle2 className='w-3.5 h-3.5' />
            <span>Booking Confirmed</span>
          </div>
          <span className='bg-emerald-subtle text-[#15803D] px-1.5 py-0.5 rounded text-[10px] font-bold tracking-tight'>
            {receipt.appointment_id}
          </span>
        </div>

        <div className='space-y-1.5 text-[11px]'>
          <div className='flex items-center justify-between'>
            <span className='text-slate-label flex items-center gap-1'>
              <Stethoscope className='w-3 h-3 text-slate-label' /> Physician:
            </span>
            <span className='font-medium text-carbon-ink'>{receipt.doctor_name}</span>
          </div>

          <div className='flex items-center justify-between'>
            <span className='text-slate-label flex items-center gap-1'>
              <Calendar className='w-3 h-3 text-slate-label' /> Date / Slot:
            </span>
            <span className='font-medium text-carbon-ink'>
              {receipt.date_label || receipt.date} · {receipt.time_slot}
            </span>
          </div>

          <div className='flex items-center justify-between border-t border-hairline pt-1.5'>
            <span className='text-slate-label flex items-center gap-1'>
              <Phone className='w-3 h-3 text-slate-label' /> Phone:
            </span>
            <span className='font-semibold tabular-nums text-carbon-ink'>{receipt.patient_phone}</span>
          </div>
        </div>

        {/* Tactile perforated receipt bottom edge */}
        <div className='mt-2.5 pt-1.5 border-t border-dashed border-hairline flex items-center justify-between text-[9px] text-slate-label uppercase tracking-widest'>
          <span>CLINICAL_DISPATCH // TICKET</span>
          <span>{receipt.timestamp || 'CONFIRMED'}</span>
        </div>
      </div>
    );
  }

  if (receipt.type === 'CANCELLATION_CONFIRMATION') {
    return (
      <div className='my-2 p-3 bg-white border border-amber-600/30 rounded shadow-sm font-mono text-xs text-carbon-ink relative overflow-hidden transition-all duration-300'>
        <div className='absolute top-0 left-0 right-0 h-1 bg-[#D97706]' />

        <div className='flex items-center justify-between border-b border-hairline pb-2 mb-2'>
          <div className='flex items-center gap-1.5 text-[#D97706] font-semibold text-[11px] tracking-wider uppercase'>
            <XCircle className='w-3.5 h-3.5' />
            <span>Appointment Canceled</span>
          </div>
          <span className='bg-amber-subtle text-[#D97706] px-1.5 py-0.5 rounded text-[10px] font-bold'>
            RELEASED
          </span>
        </div>

        <div className='space-y-1.5 text-[11px]'>
          <div className='flex items-center justify-between'>
            <span className='text-slate-label'>Physician:</span>
            <span className='font-medium text-carbon-ink'>{receipt.doctor_name}</span>
          </div>
          <div className='flex items-center justify-between'>
            <span className='text-slate-label'>Slot Released:</span>
            <span className='font-medium text-carbon-ink'>{receipt.released_slot}</span>
          </div>
          <div className='flex items-center justify-between border-t border-hairline pt-1.5'>
            <span className='text-slate-label'>Phone:</span>
            <span className='font-semibold tabular-nums text-carbon-ink'>{receipt.patient_phone}</span>
          </div>
        </div>

        <div className='mt-2.5 pt-1.5 border-t border-dashed border-hairline flex items-center justify-between text-[9px] text-slate-label uppercase tracking-widest'>
          <span>CANCELLATION_RECEIPT</span>
          <span>{receipt.timestamp || 'VOIDED'}</span>
        </div>
      </div>
    );
  }

  if (receipt.type === 'AVAILABILITY_QUERY') {
    return (
      <div className='my-2 p-2.5 bg-[#F0F0EE] border border-hairline rounded font-mono text-[11px] text-carbon-ink'>
        <div className='flex items-center justify-between mb-1 text-[10px] uppercase tracking-wider text-slate-label'>
          <span>TELEMETRY // AVAILABILITY</span>
          <span className='font-bold text-carbon-ink'>{receipt.count} SLOTS FOUND</span>
        </div>
        <p className='text-slate-label text-[10px]'>
          Query executed across clinic physicians. Open time slots broadcasted to caller.
        </p>
      </div>
    );
  }

  return null;
}