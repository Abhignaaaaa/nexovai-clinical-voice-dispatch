import React, { useState, useRef, useEffect } from 'react';
import { X, Mic, MicOff, PhoneOff, PhoneCall, Send, Activity, Sparkles, Volume2 } from 'lucide-react';
import AudioVisualizer from './AudioVisualizer';
import ReceiptCard from './ReceiptCard';

export default function PhoneDrawer({
  isOpen,
  onClose,
  voiceCall,
  transcripts,
  receiptCards
}) {
  const [inputText, setInputText] = useState('');
  const transcriptEndRef = useRef(null);

  const {
    callState,
    isMuted,
    callDuration,
    audioData,
    startCall,
    endCall,
    toggleMute,
    sendUserSpeech
  } = voiceCall;

  // Auto-scroll transcript to bottom
  useEffect(() => {
    if (transcriptEndRef.current) {
      transcriptEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [transcripts, receiptCards]);

  const handleSendText = (e) => {
    e.preventDefault();
    if (!inputText.trim()) return;
    sendUserSpeech(inputText);
    setInputText('');
  };

  const formatTimer = (seconds) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return String(mins).padStart(2, '0') + ':' + String(secs).padStart(2, '0');
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-carbon-ink/20 backdrop-blur-[2px] transition-opacity duration-300">
      {/* Backdrop click to close */}
      <div className="absolute inset-0" onClick={onClose} />

      {/* Hardware Device Casing */}
      <div className="relative w-full max-w-md h-full bg-[#EBEBE8] border-l border-hairline shadow-drawer flex flex-col justify-between overflow-hidden animate-in slide-in-from-right duration-300 font-sans">
        {/* Hardware Top Chassis / Header */}
        <div className="px-4 py-3 bg-[#E2E2DF] border-b border-[#D4D4D0] flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="w-2 h-2 rounded-full bg-burnt-orange shadow-sm animate-pulse-subtle" />
            <div className="font-mono text-xs font-semibold uppercase tracking-wider text-carbon-ink">
              DISPATCH_COMM // HW-01
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded text-slate-label hover:text-carbon-ink hover:bg-[#D4D4D0] transition-colors"
            title="Close Console"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* OLED Screen Enclosure */}
        <div className="flex-1 p-3 flex flex-col gap-2 min-h-0 bg-[#141413] m-3 rounded-lg border border-[#2B2B28] shadow-inner text-[#E0E0DC]">
          {/* Top Status & Telemetry Bar */}
          <div className="flex items-center justify-between border-b border-[#2B2B28] pb-2 text-[10px] font-mono">
            <div className="flex items-center gap-2">
              <span className={"px-1.5 py-0.5 rounded text-[9px] font-bold uppercase tracking-wider " + (
                callState === 'CONNECTED'
                  ? "bg-burnt-orange/20 text-burnt-orange border border-burnt-orange/40"
                  : callState === 'DIALING'
                  ? "bg-amber-500/20 text-amber-400 border border-amber-500/40 animate-pulse"
                  : "bg-[#2A2A28] text-slate-400"
              )}>
                {callState === 'CONNECTED' ? 'LIVE // CONNECTED' : callState === 'DIALING' ? 'DIALING (440+480HZ)...' : 'CALL ENDED'}
              </span>
              <span className="text-[#888884] hidden sm:inline">VOICE AI (GEMINI 2.5)</span>
            </div>

            {/* MONOSPACE CALL TIMER */}
            <div className="font-mono font-bold text-sm tracking-wider tabular-nums text-white">
              {formatTimer(callDuration)}
            </div>
          </div>

          {/* Real-time Reactive Waveform */}
          <div className="my-1">
            <AudioVisualizer
              audioData={audioData}
              isCalling={callState === 'CONNECTED'}
              isMuted={isMuted}
            />
          </div>

          {/* Live Transcript & Inline Receipt Screen */}
          <div className="flex-1 overflow-y-auto pr-1 space-y-2.5 font-sans text-xs scrollbar-thin">
            {transcripts.length === 0 && (
              <div className="h-full flex flex-col items-center justify-center text-center p-4 text-[#888884] space-y-2">
                <Activity className="w-6 h-6 text-[#555552] animate-bounce" />
                <p className="font-mono text-[11px] uppercase tracking-wider">
                  Awaiting Dispatch Connection...
                </p>
                <p className="text-[11px] text-[#70706C] max-w-xs">
                  Speak clearly into your microphone, or use the quick dialer below to test booking and cancellation flows.
                </p>
              </div>
            )}

            {transcripts
              .filter((t, idx, arr) => {
                if (idx === 0) return true;
                const prev = arr[idx - 1];
                return !(prev.speaker === t.speaker && prev.text.trim().toLowerCase() === t.text.trim().toLowerCase());
              })
              .map((t, idx) => (
              <div
                key={t.id || idx}
                className={"flex flex-col " + (t.speaker === 'CALLER' ? 'items-start' : 'items-end')}
              >
                <span className="font-mono text-[9px] uppercase tracking-wider text-[#888884] mb-0.5 px-1">
                  {(t.speaker === 'CALLER' ? '// CALLER (YOU)' : '// DISPATCH AGENT') + ' · ' + (t.timestamp || '')}
                </span>
                <div
                  className={"max-w-[85%] rounded px-3 py-2 text-xs leading-relaxed " + (
                    t.speaker === 'CALLER'
                      ? "bg-[#262624] text-[#F0F0EC] border border-[#3A3A38]"
                      : "bg-[#1C1C1A] text-white border border-burnt-orange/30 shadow-sm"
                  )}
                >
                  {t.text}
                </div>
              </div>
            ))}

            {/* Inline Confirmation Receipt Cards */}
            {receiptCards.map((receipt, idx) => (
              <ReceiptCard key={idx} receipt={receipt} />
            ))}

            <div ref={transcriptEndRef} />
          </div>

          {/* Quick Speech / Text Input Fallback Bar */}
          <form onSubmit={handleSendText} className="mt-2 flex gap-1.5 pt-2 border-t border-[#2B2B28]">
            <input
              type="text"
              value={inputText}
              onChange={(e) => setInputText(e.target.value)}
              placeholder="Speak or type (e.g. 'Book Dr. Lin today 2:30 PM, phone 555-0199')..."
              className="flex-1 bg-[#1E1E1C] border border-[#383834] rounded px-2.5 py-1.5 text-xs text-white placeholder-[#686864] focus:outline-none focus:border-burnt-orange font-mono"
            />
            <button
              type="submit"
              disabled={!inputText.trim()}
              className="px-3 py-1.5 bg-[#2A2A28] hover:bg-burnt-orange hover:text-white disabled:opacity-40 disabled:hover:bg-[#2A2A28] rounded text-xs font-mono font-medium transition-colors flex items-center justify-center"
            >
              <Send className="w-3 h-3" />
            </button>
          </form>
        </div>

        {/* Tactile Hardware Controls Bottom Bar */}
        <div className="p-3 bg-[#E2E2DF] border-t border-[#D4D4D0] flex items-center justify-between gap-3">
          {/* Mute Button */}
          <button
            onClick={toggleMute}
            disabled={callState !== 'CONNECTED'}
            className={"flex-1 py-2.5 px-3 rounded flex items-center justify-center gap-2 font-mono text-xs font-semibold uppercase tracking-wider transition-all shadow-tactile " + (
              isMuted
                ? "bg-amber-100 border border-amber-400 text-amber-800"
                : "bg-white border border-[#D4D4D0] text-carbon-ink hover:bg-[#F7F7F5]"
            ) + " disabled:opacity-40"}
          >
            {isMuted ? <MicOff className="w-4 h-4 text-amber-600" /> : <Mic className="w-4 h-4 text-slate-label" />}
            <span>{isMuted ? 'UNMUTE' : 'MUTE MIC'}</span>
          </button>

          {/* End Call / Dial Call Button */}
          {callState === 'CONNECTED' || callState === 'DIALING' ? (
            <button
              onClick={endCall}
              className="flex-1 py-2.5 px-3 rounded bg-burnt-orange hover:bg-[#E04500] text-white flex items-center justify-center gap-2 font-mono text-xs font-bold uppercase tracking-wider transition-all shadow-tactile"
            >
              <PhoneOff className="w-4 h-4" />
              <span>END CALL</span>
            </button>
          ) : (
            <button
              onClick={startCall}
              className="flex-1 py-2.5 px-3 rounded bg-carbon-ink hover:bg-black text-white flex items-center justify-center gap-2 font-mono text-xs font-bold uppercase tracking-wider transition-all shadow-tactile"
            >
              <PhoneCall className="w-4 h-4 text-burnt-orange" />
              <span>REDIAL</span>
            </button>
          )}
        </div>
      </div>
    </div>
  );
}