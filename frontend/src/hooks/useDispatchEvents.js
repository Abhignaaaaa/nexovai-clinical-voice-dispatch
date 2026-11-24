import { useState, useEffect, useRef, useCallback } from 'react';

// Helper to make API requests via proxy with automatic direct 127.0.0.1 fallback
async function safeFetch(path, options = {}) {
  try {
    const res = await fetch(path, options);
    if (res.ok) return res;
    if (!path.startsWith('http')) {
      const directUrl = 'http://127.0.0.1:8000' + path;
      const directRes = await fetch(directUrl, options);
      if (directRes.ok) return directRes;
    }
    return res;
  } catch (err) {
    if (!path.startsWith('http')) {
      const directUrl = 'http://127.0.0.1:8000' + path;
      return await fetch(directUrl, options);
    }
    throw err;
  }
}

export function useDispatchEvents() {
  const [connected, setConnected] = useState(false);
  const [doctors, setDoctors] = useState([]);
  const [appointments, setAppointments] = useState([]);
  const [transcripts, setTranscripts] = useState([]);
  const [receiptCards, setReceiptCards] = useState([]);
  const [lastEvent, setLastEvent] = useState(null);
  const [flashedRowId, setFlashedRowId] = useState(null);
  const [flashType, setFlashType] = useState(null); // 'emerald' | 'amber'
  const [apiStatus, setApiStatus] = useState({ gemini: false, elevenlabs: false, mode: 'checking' });

  const wsRef = useRef(null);
  const reconnectTimeoutRef = useRef(null);
  const useDirectWsRef = useRef(false);
  const isMountedRef = useRef(true);

  // Fetch initial REST data
  const fetchData = useCallback(async () => {
    try {
      const [docsRes, aptsRes, statusRes] = await Promise.all([
        safeFetch('/api/doctors'),
        safeFetch('/api/appointments'),
        safeFetch('/api/config-status')
      ]);
      if (docsRes.ok) {
        const docsData = await docsRes.json();
        setDoctors(docsData.doctors || []);
      }
      if (aptsRes.ok) {
        const aptsData = await aptsRes.json();
        setAppointments(aptsData.appointments || []);
      }
      if (statusRes.ok) {
        const stData = await statusRes.json();
        setApiStatus(stData);
      }
    } catch (err) {
      console.error('Error fetching initial data:', err);
    }
  }, []);

  // Reset database demo
  const resetDemoData = useCallback(async () => {
    try {
      const res = await safeFetch('/api/reset', { method: 'POST' });
      if (res.ok) {
        const data = await res.json();
        setDoctors(data.doctors || []);
        setAppointments(data.appointments || []);
        setReceiptCards([]);
        setTranscripts([]);
      }
    } catch (err) {
      console.error('Error resetting demo data:', err);
    }
  }, []);

  // Connect WebSocket for events with clean lifecycle management
  const connectWs = useCallback(() => {
    if (!isMountedRef.current) return;

    // Clean up any existing connection
    if (wsRef.current) {
      wsRef.current.onclose = null;
      wsRef.current.onerror = null;
      wsRef.current.close();
      wsRef.current = null;
    }

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    let wsUrl = '';
    if (useDirectWsRef.current || (window.location.port !== '3000' && window.location.port !== '5173')) {
      wsUrl = `${protocol}//127.0.0.1:8000/ws/events`;
    } else {
      wsUrl = `${protocol}//${window.location.host}/ws/events`;
    }

    try {
      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onopen = () => {
        if (!isMountedRef.current) {
          ws.close();
          return;
        }
        setConnected(true);
        console.log(`Events WebSocket connected to ${wsUrl}`);
      };

      ws.onmessage = (event) => {
        if (!isMountedRef.current) return;
        try {
          const data = JSON.parse(event.data);
          setLastEvent(data);

          switch (data.type) {
            case 'INITIAL_STATE':
              if (data.doctors) setDoctors(data.doctors);
              if (data.appointments) setAppointments(data.appointments);
              break;

            case 'APPOINTMENT_BOOKED':
              if (data.doctors) setDoctors(data.doctors);
              if (data.appointments) setAppointments(data.appointments);
              if (data.appointment?.appointment_id) {
                setFlashedRowId(data.appointment.appointment_id);
                setFlashType('emerald');
                setTimeout(() => setFlashedRowId(null), 3000);
              }
              break;

            case 'APPOINTMENT_CANCELED':
              if (data.doctors) setDoctors(data.doctors);
              if (data.appointments) setAppointments(data.appointments);
              if (data.cancellation?.appointment_id) {
                setFlashedRowId(data.cancellation.appointment_id);
                setFlashType('amber');
                setTimeout(() => setFlashedRowId(null), 3000);
              }
              break;

            case 'TOOL_CALL':
              if (data.receipt) {
                setReceiptCards((prev) => {
                  // Deduplicate receipts by appointment_id or type
                  const isDup = prev.some(r => 
                    r.appointment_id && r.appointment_id === data.receipt.appointment_id
                  );
                  if (isDup) return prev;
                  return [...prev, { ...data.receipt, timestamp: new Date().toLocaleTimeString() }];
                });
              }
              break;

            case 'TRANSCRIPT_UPDATE':
              setTranscripts((prev) => {
                const now = Date.now();
                const newText = (data.text || '').trim();
                if (!newText) return prev;

                // Deduplicate incoming transcript events by role + text within 3.5s window
                const isDuplicate = prev.slice(-4).some(item => 
                  item.speaker === data.speaker && 
                  item.text.trim().toLowerCase() === newText.toLowerCase() &&
                  Math.abs(now - (item.rawTimestamp || 0)) < 3500
                );

                if (isDuplicate) {
                  return prev;
                }

                return [
                  ...prev,
                  {
                    id: data.id || (now + Math.random()),
                    rawTimestamp: now,
                    speaker: data.speaker,
                    text: newText,
                    timestamp: data.timestamp || new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }),
                    is_final: data.is_final ?? true
                  }
                ];
              });
              break;

            case 'DEMO_RESET':
              if (data.doctors) setDoctors(data.doctors);
              if (data.appointments) setAppointments(data.appointments);
              setReceiptCards([]);
              setTranscripts([]);
              break;

            default:
              break;
          }
        } catch (e) {
          console.error('Failed to parse WS message:', e);
        }
      };

      ws.onclose = () => {
        if (!isMountedRef.current) return;
        setConnected(false);
        if (!useDirectWsRef.current) {
          useDirectWsRef.current = true;
        }
        reconnectTimeoutRef.current = setTimeout(connectWs, 2000);
      };

      ws.onerror = (err) => {
        if (!isMountedRef.current) return;
        console.warn('Events WebSocket error on', wsUrl, err);
        ws.close();
      };
    } catch (err) {
      if (!isMountedRef.current) return;
      console.warn('WebSocket init exception:', err);
      useDirectWsRef.current = true;
      reconnectTimeoutRef.current = setTimeout(connectWs, 2000);
    }
  }, []);

  useEffect(() => {
    isMountedRef.current = true;
    fetchData();
    connectWs();

    return () => {
      isMountedRef.current = false;
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
        reconnectTimeoutRef.current = null;
      }
      if (wsRef.current) {
        wsRef.current.onclose = null;
        wsRef.current.onerror = null;
        wsRef.current.close();
        wsRef.current = null;
      }
    };
  }, [fetchData, connectWs]);

  const clearTranscripts = useCallback(() => {
    setTranscripts([]);
    setReceiptCards([]);
  }, []);

  return {
    connected,
    doctors,
    appointments,
    transcripts,
    receiptCards,
    lastEvent,
    flashedRowId,
    flashType,
    apiStatus,
    resetDemoData,
    fetchData,
    clearTranscripts
  };
}