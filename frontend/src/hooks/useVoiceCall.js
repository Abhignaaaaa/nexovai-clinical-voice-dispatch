import { useState, useRef, useEffect, useCallback } from 'react';

export function useVoiceCall({ onCallerSpeech, onAgentMessage, onCallEnded }) {
  const [callState, setCallState] = useState('IDLE'); // 'IDLE' | 'DIALING' | 'CONNECTED' | 'ENDED'
  const [isMuted, setIsMuted] = useState(false);
  const [callDuration, setCallDuration] = useState(0); // in seconds
  const [audioData, setAudioData] = useState(new Uint8Array(64));

  const isMutedRef = useRef(false);
  const isAgentSpeakingRef = useRef(false);
  const wsRef = useRef(null);
  const audioCtxRef = useRef(null);
  const ringOsc1Ref = useRef(null);
  const ringOsc2Ref = useRef(null);
  const ringGainRef = useRef(null);
  const ringIntervalRef = useRef(null);
  const micStreamRef = useRef(null);
  const analyserRef = useRef(null);
  const animFrameRef = useRef(null);
  const timerIntervalRef = useRef(null);
  const recognitionRef = useRef(null);
  const synthRef = useRef(window.speechSynthesis || null);

  // Initialize Web Audio Context
  const getAudioContext = useCallback(() => {
    if (!audioCtxRef.current) {
      const AudioCtx = window.AudioContext || window.webkitAudioContext;
      audioCtxRef.current = new AudioCtx();
    }
    if (audioCtxRef.current.state === 'suspended') {
      audioCtxRef.current.resume();
    }
    return audioCtxRef.current;
  }, []);

  // Web Audio Ringback tone: Dual-frequency (440Hz + 480Hz) North American ringback standard
  const startRingbackTone = useCallback(() => {
    try {
      const ctx = getAudioContext();
      const osc1 = ctx.createOscillator();
      const osc2 = ctx.createOscillator();
      const gain = ctx.createGain();

      osc1.type = 'sine';
      osc2.type = 'sine';
      osc1.frequency.setValueAtTime(440, ctx.currentTime);
      osc2.frequency.setValueAtTime(480, ctx.currentTime);

      gain.gain.setValueAtTime(0, ctx.currentTime);
      osc1.connect(gain);
      osc2.connect(gain);
      gain.connect(ctx.destination);

      osc1.start();
      osc2.start();

      ringOsc1Ref.current = osc1;
      ringOsc2Ref.current = osc2;
      ringGainRef.current = gain;

      // Cadence: 1.5s tone, 2s silence
      let isBeeping = true;
      gain.gain.setValueAtTime(0.08, ctx.currentTime);

      ringIntervalRef.current = setInterval(() => {
        if (!ringGainRef.current) return;
        isBeeping = !isBeeping;
        const now = ctx.currentTime;
        ringGainRef.current.gain.cancelScheduledValues(now);
        ringGainRef.current.gain.setValueAtTime(isBeeping ? 0.08 : 0, now);
      }, 1500);
    } catch (e) {
      console.warn('AudioContext ringtone error:', e);
    }
  }, [getAudioContext]);

  const stopRingbackTone = useCallback(() => {
    if (ringIntervalRef.current) {
      clearInterval(ringIntervalRef.current);
      ringIntervalRef.current = null;
    }
    if (ringGainRef.current && audioCtxRef.current) {
      try {
        ringGainRef.current.gain.setValueAtTime(0, audioCtxRef.current.currentTime);
      } catch (e) {}
    }
    if (ringOsc1Ref.current) {
      try { ringOsc1Ref.current.stop(); } catch (e) {}
      ringOsc1Ref.current = null;
    }
    if (ringOsc2Ref.current) {
      try { ringOsc2Ref.current.stop(); } catch (e) {}
      ringOsc2Ref.current = null;
    }
    ringGainRef.current = null;
  }, []);

  // Synthesized soft hangup tone (480Hz + 620Hz quick chirp)
  const playHangupTone = useCallback(() => {
    try {
      const ctx = getAudioContext();
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      osc.type = 'triangle';
      osc.frequency.setValueAtTime(480, ctx.currentTime);
      osc.frequency.exponentialRampToValueAtTime(300, ctx.currentTime + 0.25);
      gain.gain.setValueAtTime(0.12, ctx.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.25);
      osc.connect(gain);
      gain.connect(ctx.destination);
      osc.start();
      osc.stop(ctx.currentTime + 0.26);
    } catch (e) {}
  }, [getAudioContext]);

  // Real-time audio waveform loop
  const updateWaveform = useCallback(() => {
    if (analyserRef.current) {
      const buffer = new Uint8Array(analyserRef.current.frequencyBinCount);
      analyserRef.current.getByteFrequencyData(buffer);
      setAudioData(buffer.slice(0, 48));
    }
    animFrameRef.current = requestAnimationFrame(updateWaveform);
  }, []);

  // Speak agent message aloud with mic gating & echo suppression
  const speakAgentMessage = useCallback((text) => {
    if (!synthRef.current || !text) return;
    try {
      synthRef.current.cancel();

      // Mute outgoing mic tracks during agent speech
      isAgentSpeakingRef.current = true;
      if (micStreamRef.current) {
        micStreamRef.current.getAudioTracks().forEach(track => {
          track.enabled = false;
        });
      }

      const utterance = new SpeechSynthesisUtterance(text);
      utterance.rate = 1.05;
      utterance.pitch = 1.0;
      
      const voices = synthRef.current.getVoices();
      const preferred = voices.find(v => v.lang.startsWith('en') && (v.name.includes('Natural') || v.name.includes('Google') || v.name.includes('Samantha')));
      if (preferred) utterance.voice = preferred;

      // Re-enable mic after agent speech ends with 350ms acoustic decay buffer
      const restoreMic = () => {
        setTimeout(() => {
          isAgentSpeakingRef.current = false;
          if (micStreamRef.current && !isMutedRef.current) {
            micStreamRef.current.getAudioTracks().forEach(track => {
              track.enabled = true;
            });
          }
        }, 350);
      };

      utterance.onend = restoreMic;
      utterance.onerror = restoreMic;

      synthRef.current.speak(utterance);
    } catch (e) {
      console.warn('Speech synthesis error:', e);
      isAgentSpeakingRef.current = false;
    }
  }, []);

  // Send user utterance to agent
  const sendUserSpeech = useCallback((text) => {
    if (!text || !text.trim()) return;
    // Prevent self-loop if agent is currently speaking
    if (isAgentSpeakingRef.current) {
      console.log('Suppressed self-echo input while agent was speaking');
      return;
    }

    if (onCallerSpeech) onCallerSpeech(text);

    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({
        type: 'CALLER_SPEECH',
        text: text.trim()
      }));
    } else {
      // Fallback to REST /api/message
      const sendPost = (url) => {
        return fetch(url, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ text: text.trim() })
        });
      };

      sendPost('/api/message')
        .catch(() => sendPost('http://127.0.0.1:8000/api/message'))
        .then(res => res.json())
        .then(data => {
          if (data && data.response) {
            speakAgentMessage(data.response);
            if (onAgentMessage) onAgentMessage(data.response);
          }
        })
        .catch(err => console.error('Error sending fallback utterance:', err));
    }
  }, [onCallerSpeech, onAgentMessage, speakAgentMessage]);

  // Browser speech recognition (SpeechRecognition API) with echo gating
  const startSpeechRecognition = useCallback(() => {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
      console.log('Web SpeechRecognition not supported in this browser, text input available.');
      return;
    }

    try {
      const recognition = new SpeechRecognition();
      recognition.continuous = true;
      recognition.interimResults = true;
      recognition.lang = 'en-US';

      recognition.onresult = (event) => {
        // Echo gate: if agent TTS is playing, discard mic audio
        if (isAgentSpeakingRef.current) {
          return;
        }

        let finalTranscript = '';
        for (let i = event.resultIndex; i < event.results.length; ++i) {
          if (event.results[i].isFinal) {
            finalTranscript += event.results[i][0].transcript;
          }
        }
        if (finalTranscript.trim()) {
          console.log('Spoken transcript:', finalTranscript);
          sendUserSpeech(finalTranscript);
        }
      };

      recognition.onerror = (e) => {
        console.warn('Speech recognition notice:', e.error);
      };

      recognition.start();
      recognitionRef.current = recognition;
    } catch (e) {
      console.warn('Speech recognition init error:', e);
    }
  }, [sendUserSpeech]);

  const stopSpeechRecognition = useCallback(() => {
    if (recognitionRef.current) {
      try { recognitionRef.current.stop(); } catch (e) {}
      recognitionRef.current = null;
    }
    if (synthRef.current) {
      try { synthRef.current.cancel(); } catch (e) {}
    }
    isAgentSpeakingRef.current = false;
  }, []);

  // Start Call workflow
  const startCall = useCallback(async () => {
    setCallState('DIALING');
    setCallDuration(0);
    startRingbackTone();

    // Setup microphone with hardware Echo Cancellation & Noise Suppression
    try {
      const ctx = getAudioContext();
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
          channelCount: 1,
          sampleRate: 16000
        }
      });
      micStreamRef.current = stream;

      const source = ctx.createMediaStreamSource(stream);
      const analyser = ctx.createAnalyser();
      analyser.fftSize = 128;
      source.connect(analyser);
      analyserRef.current = analyser;
      updateWaveform();
    } catch (err) {
      console.warn('Microphone permission not granted or available, running in tactile voice simulation mode:', err);
    }

    // Connect /ws/voice after realistic 2-second dialing ringback
    setTimeout(() => {
      stopRingbackTone();
      setCallState('CONNECTED');

      // Start call timer
      timerIntervalRef.current = setInterval(() => {
        setCallDuration((prev) => prev + 1);
      }, 1000);

      // Open Voice WebSocket with proxy and 127.0.0.1 fallback
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      const isDev = window.location.port === '3000' || window.location.port === '5173';
      const wsUrl = isDev ? (protocol + '//' + window.location.host + '/ws/voice') : (protocol + '//127.0.0.1:8000/ws/voice');
      
      let ws;
      try {
        ws = new WebSocket(wsUrl);
      } catch (e) {
        ws = new WebSocket(protocol + '//127.0.0.1:8000/ws/voice');
      }
      wsRef.current = ws;

      ws.onopen = () => {
        console.log('Voice WebSocket connected to ' + ws.url);
        startSpeechRecognition();
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (data.type === 'AGENT_MESSAGE') {
            speakAgentMessage(data.text);
            if (onAgentMessage) onAgentMessage(data.text);
          }
        } catch (e) {}
      };

      ws.onclose = () => {
        console.log('Voice WebSocket closed');
      };
    }, 2200);
  }, [getAudioContext, startRingbackTone, stopRingbackTone, updateWaveform, startSpeechRecognition, speakAgentMessage, onAgentMessage]);

  // End Call workflow
  const endCall = useCallback(() => {
    stopRingbackTone();
    playHangupTone();
    stopSpeechRecognition();

    if (timerIntervalRef.current) {
      clearInterval(timerIntervalRef.current);
      timerIntervalRef.current = null;
    }

    if (animFrameRef.current) {
      cancelAnimationFrame(animFrameRef.current);
      animFrameRef.current = null;
    }

    if (micStreamRef.current) {
      micStreamRef.current.getTracks().forEach((t) => t.stop());
      micStreamRef.current = null;
    }

    if (wsRef.current) {
      try {
        wsRef.current.send(JSON.stringify({ type: 'END_CALL' }));
        wsRef.current.close();
      } catch (e) {}
      wsRef.current = null;
    }

    setCallState('ENDED');
    if (onCallEnded) onCallEnded();

    setTimeout(() => {
      setCallState('IDLE');
      setCallDuration(0);
      setAudioData(new Uint8Array(64));
    }, 2500);
  }, [stopRingbackTone, playHangupTone, stopSpeechRecognition, onCallEnded]);

  // Toggle Mute
  const toggleMute = useCallback(() => {
    setIsMuted((prev) => {
      const next = !prev;
      isMutedRef.current = next;
      if (micStreamRef.current) {
        micStreamRef.current.getAudioTracks().forEach((track) => {
          track.enabled = !next;
        });
      }
      return next;
    });
  }, []);

  useEffect(() => {
    return () => {
      stopRingbackTone();
      stopSpeechRecognition();
      if (timerIntervalRef.current) clearInterval(timerIntervalRef.current);
      if (animFrameRef.current) cancelAnimationFrame(animFrameRef.current);
      if (micStreamRef.current) micStreamRef.current.getTracks().forEach(t => t.stop());
      if (wsRef.current) wsRef.current.close();
    };
  }, [stopRingbackTone, stopSpeechRecognition]);

  return {
    callState,
    isMuted,
    callDuration,
    audioData,
    startCall,
    endCall,
    toggleMute,
    sendUserSpeech
  };
}