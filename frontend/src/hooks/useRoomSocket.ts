import { useCallback, useEffect, useRef, useState } from 'react';
import type {
  ClientRole,
  DecisionResultPayload,
  FeedEventPayload,
  MatchDebriefPayload,
  RoomStatePayload,
  SessionReadyPayload,
  WsEnvelope,
} from '../contracts/types';

export interface JoinOptions {
  roomCode: string;
  role: ClientRole;
  teamId?: string;
  nickname?: string;
  avatarId?: string;
  adminToken?: string;
}

interface StoredSession {
  session_token: string;
  team_id: string;
  nickname: string;
  avatar_id: string;
}

export function getStoredSession(roomCode: string): StoredSession | null {
  try {
    const raw = sessionStorage.getItem(`bz_session_${roomCode.toUpperCase()}`);
    return raw ? (JSON.parse(raw) as StoredSession) : null;
  } catch {
    return null;
  }
}

export function saveStoredSession(roomCode: string, data: StoredSession): void {
  try {
    sessionStorage.setItem(`bz_session_${roomCode.toUpperCase()}`, JSON.stringify(data));
  } catch {
    // Ignore storage quota errors
  }
}

export function useRoomSocket() {
  const wsRef = useRef<WebSocket | null>(null);
  const closeFnRef = useRef<(() => void) | null>(null);
  const [connected, setConnected] = useState(false);
  const [session, setSession] = useState<SessionReadyPayload | null>(null);
  const [roomState, setRoomState] = useState<RoomStatePayload | null>(null);
  const [feedEvents, setFeedEvents] = useState<FeedEventPayload[]>([]);
  const [lastDecision, setLastDecision] = useState<DecisionResultPayload | null>(null);
  const [debrief, setDebrief] = useState<MatchDebriefPayload | null>(null);
  const [lastError, setLastError] = useState<string | null>(null);

  const disconnect = useCallback(() => {
    if (closeFnRef.current) {
      closeFnRef.current();
      closeFnRef.current = null;
    }
    wsRef.current = null;
    setConnected(false);
  }, []);

  useEffect(() => {
    return () => {
      if (closeFnRef.current) {
        closeFnRef.current();
        closeFnRef.current = null;
      }
      wsRef.current = null;
    };
  }, []);

  const connect = useCallback((opts: JoinOptions) => {
    if (closeFnRef.current) {
      closeFnRef.current();
      closeFnRef.current = null;
    }
    const cleanCode = opts.roomCode.trim().toUpperCase();
    const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${wsProtocol}//${window.location.host}/ws/room/${cleanCode}`;
    const ws = new WebSocket(wsUrl);
    let closedIntentionally = false;
    wsRef.current = ws;
    closeFnRef.current = () => {
      closedIntentionally = true;
      if (ws.readyState === WebSocket.OPEN) {
        ws.close();
      }
    };
    setLastError(null);

    ws.onopen = () => {
      if (closedIntentionally || wsRef.current !== ws) {
        ws.close();
        return;
      }
      setConnected(true);
      const stored = opts.role === 'PLAYER' ? getStoredSession(cleanCode) : null;
      ws.send(
        JSON.stringify({
          type: 'JOIN_ROOM',
          request_id: `join_${Date.now()}`,
          timestamp: new Date().toISOString(),
          payload: {
            room_code: cleanCode,
            role: opts.role,
            team_id: stored?.team_id ?? opts.teamId,
            nickname: stored?.nickname ?? opts.nickname,
            avatar_id: stored?.avatar_id ?? opts.avatarId ?? 'analyst-ali',
            session_token: stored?.session_token ?? null,
            admin_token: opts.adminToken ?? null,
          },
        }),
      );
    };

    ws.onmessage = (evt) => {
      if (closedIntentionally || wsRef.current !== ws) return;
      const msg = JSON.parse(evt.data) as WsEnvelope<Record<string, unknown>>;
      if (msg.type === 'SESSION_READY') {
        const ready = msg.payload as unknown as SessionReadyPayload;
        setSession(ready);
        if (ready.role === 'PLAYER' && ready.session_token && ready.team_id) {
          saveStoredSession(cleanCode, {
            session_token: ready.session_token,
            team_id: ready.team_id,
            nickname: opts.nickname || 'Analist',
            avatar_id: opts.avatarId || 'analyst-ali',
          });
        }
      } else if (msg.type === 'ROOM_STATE_UPDATE') {
        setRoomState(msg.payload as unknown as RoomStatePayload);
      } else if (msg.type === 'FEED_EVENT') {
        const item = msg.payload as unknown as FeedEventPayload;
        setFeedEvents((prev) => [item, ...prev].slice(0, 30));
      } else if (msg.type === 'DECISION_RESULT') {
        setLastDecision(msg.payload as unknown as DecisionResultPayload);
      } else if (msg.type === 'MATCH_DEBRIEF') {
        setDebrief(msg.payload as unknown as MatchDebriefPayload);
      } else if (msg.type === 'ERROR') {
        const errPayload = msg.payload as { code?: string; message?: string };
        setLastError(`${errPayload.code || 'HATA'}: ${errPayload.message || 'İşlem başarısız'}`);
      }
    };

    ws.onclose = () => {
      if (closedIntentionally || wsRef.current !== ws) return;
      setConnected(false);
    };

    ws.onerror = () => {
      if (closedIntentionally || wsRef.current !== ws) return;
      setLastError('WebSocket bağlantı hatası oluştu.');
    };
  }, []);

  const sendAction = useCallback((type: string, payload: Record<string, unknown> = {}) => {
    const ws = wsRef.current;
    if (!ws || ws.readyState !== WebSocket.OPEN) {
      setLastError('Sunucu bağlantısı açık değil.');
      return;
    }
    setLastError(null);
    ws.send(
      JSON.stringify({
        type,
        request_id: `req_${Date.now()}`,
        timestamp: new Date().toISOString(),
        payload,
      }),
    );
  }, []);

  return {
    connected,
    session,
    roomState,
    feedEvents,
    lastDecision,
    debrief,
    lastError,
    clearError: () => setLastError(null),
    connect,
    disconnect,
    sendAction,
  };
}
