import React, { useState } from 'react';
import TopTelemetryBar from './components/TopTelemetryBar';
import DoctorSlotMatrix from './components/DoctorSlotMatrix';
import AppointmentLedger from './components/AppointmentLedger';
import PhoneDrawer from './components/PhoneDrawer';
import { useDispatchEvents } from './hooks/useDispatchEvents';
import { useVoiceCall } from './hooks/useVoiceCall';
import { ShieldCheck, Info, Sparkles, Terminal } from 'lucide-react';

export default function App() {
  const [isDrawerOpen, setIsDrawerOpen] = useState(false);

  const {
    connected: wsConnected,
    doctors,
    appointments,
    transcripts,
    receiptCards,
    flashedRowId,
    flashType,
    apiStatus,
    resetDemoData
  } = useDispatchEvents();

  const voiceCall = useVoiceCall({
    onCallerSpeech: (text) => {
      console.log('Caller uttered:', text);
    },
    onAgentMessage: (text) => {
      console.log('Agent responded:', text);
    },
    onCallEnded: () => {
      console.log('Call session completed');
    }
  });

  const handleOpenDrawer = () => {
    setIsDrawerOpen(true);
    if (voiceCall.callState === 'IDLE' || voiceCall.callState === 'ENDED') {
      voiceCall.startCall();
    }
  };

  const handleSelectSlot = (doctor, slot) => {
    setIsDrawerOpen(true);
    if (voiceCall.callState === 'IDLE' || voiceCall.callState === 'ENDED') {
      voiceCall.startCall();
    }
    // If slot is not booked, suggest booking prompt
    setTimeout(() => {
      if (!slot.is_booked) {
        voiceCall.sendUserSpeech('I want to book an appointment with ' + doctor.name + ' on ' + slot.date_label.toLowerCase() + ' at ' + slot.time_slot + '. My phone is 555-0199.');
      } else {
        voiceCall.sendUserSpeech('Can I cancel the appointment for ' + (slot.booked_by_phone || '555-0144') + '?');
      }
    }, 2500);
  };

  return (
    <div className='min-h-screen bg-canvas text-carbon-ink flex flex-col font-sans selection:bg-burnt-orange selection:text-white'>
      {/* Top Telemetry Header */}
      <TopTelemetryBar
        wsConnected={wsConnected}
        apiStatus={apiStatus}
        onResetDemo={resetDemoData}
        onOpenDrawer={handleOpenDrawer}
        callState={voiceCall.callState}
      />

      {/* Main Console Container */}
      <main className='flex-1 max-w-7xl w-full mx-auto p-4 lg:p-8 space-y-6'>
        {/* Protocol Banner: Swiss Minimalist linework */}
        <div className='bg-white border border-hairline rounded-lg p-3.5 shadow-tactile flex flex-col sm:flex-row sm:items-center justify-between gap-3 font-mono text-xs'>
          <div className='flex items-center gap-2 text-carbon-ink'>
            <ShieldCheck className='w-4 h-4 text-emerald-booked shrink-0' />
            <span className='font-bold uppercase tracking-wider'>
              MANDATORY READ-BACK PROTOCOL:
            </span>
            <span className='text-slate-label font-normal text-[11px]'>
              Caller phone digits are strictly repeated back and verified aloud prior to atomic slot mutation.
            </span>
          </div>

          <div className='flex items-center gap-2 text-[10px] text-slate-label'>
            <span className='w-1.5 h-1.5 rounded-full bg-burnt-orange animate-pulse'></span>
            <span>CLINICAL_DISPATCH // LINE 01</span>
          </div>
        </div>

        {/* Doctor and Slot Grid Matrix */}
        <section>
          <DoctorSlotMatrix
            doctors={doctors}
            onSelectSlot={handleSelectSlot}
          />
        </section>

        {/* Live Appointment Ledger Table */}
        <section>
          <AppointmentLedger
            appointments={appointments}
            flashedRowId={flashedRowId}
            flashType={flashType}
          />
        </section>
      </main>

      {/* Swiss Inspired Tactile Phone Drawer */}
      <PhoneDrawer
        isOpen={isDrawerOpen}
        onClose={() => setIsDrawerOpen(false)}
        voiceCall={voiceCall}
        transcripts={transcripts}
        receiptCards={receiptCards}
      />

      {/* Minimal Footer */}
      <footer className='border-t border-hairline py-3 px-4 text-center font-mono text-[10px] text-slate-label uppercase tracking-widest'>
        NEXOVAI CLINICAL VOICE DISPATCH · HIGH-CONCURRENCY REAL-TIME AI ARCHITECTURE
      </footer>
    </div>
  );
}