import React from 'react';
import { PhoneCall, RotateCcw, Activity, ShieldAlert, Cpu } from 'lucide-react';

export default function TopTelemetryBar({
  wsConnected,
  apiStatus,
  onResetDemo,
  onOpenDrawer,
  callState
}) {
  const isCalling = callState === 'CONNECTED' || callState === 'DIALING';

  return (
    <header className="bg-white border-b border-hairline sticky top-0 z-40 px-4 lg:px-8 py-3 shadow-sm">
      <div className="max-w-7xl mx-auto flex items-center justify-between gap-4">
        {/* Brand & Monospace Subtitle */}
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded bg-carbon-ink flex items-center justify-center text-white shadow-tactile">
            <Activity className="w-4 h-4 text-burnt-orange" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="font-bold text-sm tracking-tight text-carbon-ink font-mono">
                NEXOVAI // CLINICAL DISPATCH
              </h1>
              <span className="hidden sm:inline-block px-1.5 py-0.2 rounded text-[9px] font-mono uppercase bg-[#EEEEEC] text-slate-label border border-hairline">
                v1.0-STABLE
              </span>
            </div>
            <p className="text-[10px] font-mono text-slate-label tracking-wide">
              REAL-TIME VOICE AI · GEMINI 2.5 FLASH · PIPECAT · SILERO VAD
            </p>
          </div>
        </div>

        {/* Telemetry & Action Buttons */}
        <div className="flex items-center gap-3">
          {/* Real-time WebSocket connection status */}
          <div className="hidden md:flex items-center gap-1.5 px-2.5 py-1 rounded bg-[#F7F7F5] border border-hairline font-mono text-[11px] text-slate-label">
            <span className={"w-2 h-2 rounded-full " + (wsConnected ? "bg-[#15803D] animate-pulse" : "bg-amber-500")} />
            <span>{wsConnected ? "TELEMETRY // LIVE" : "CONNECTING..."}</span>
          </div>

          {/* AI Mode badge */}
          <div className="hidden lg:flex items-center gap-1.5 px-2.5 py-1 rounded bg-[#F7F7F5] border border-hairline font-mono text-[11px] text-slate-label">
            <Cpu className="w-3.5 h-3.5 text-slate-label" />
            <span>{apiStatus?.gemini ? "GEMINI 2.5 FLASH" : "DISPATCH AGENT"}</span>
          </div>

          {/* Reset Demo Button */}
          <button
            onClick={onResetDemo}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded bg-white hover:bg-[#F7F7F5] border border-hairline text-carbon-ink text-xs font-mono font-medium shadow-tactile hover:shadow-tactile-hover active:shadow-tactile-pressed transition-all"
            title="Reset sample database and demo slots"
          >
            <RotateCcw className="w-3.5 h-3.5 text-slate-label" />
            <span className="hidden sm:inline">RESET DEMO</span>
          </button>

          {/* Prominent Try Call Button */}
          <button
            onClick={onOpenDrawer}
            className={"flex items-center gap-2 px-4 py-1.5 rounded font-mono text-xs font-bold uppercase tracking-wider transition-all shadow-tactile " + (
              isCalling
                ? "bg-burnt-orange text-white animate-pulse-subtle"
                : "bg-burnt-orange hover:bg-[#E04500] text-white shadow-tactile-hover"
            )}
          >
            <PhoneCall className="w-3.5 h-3.5" />
            <span>{isCalling ? "CALL IN PROGRESS" : "TRY CALL"}</span>
          </button>
        </div>
      </div>
    </header>
  );
}