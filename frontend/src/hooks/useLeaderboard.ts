import { useEffect, useState, useRef } from 'react';
import type { LeaderboardEntry } from '../types';

const getWebSocketUrl = (): string => {
  const apiOrigin = (import.meta as any).env?.VITE_API_ORIGIN as string | undefined;
  const origin = (apiOrigin || '').trim().replace(/\/$/, '');
  if (origin) {
    const wsOrigin = origin.replace(/^http:/, 'ws:').replace(/^https:/, 'wss:');
    return `${wsOrigin}/ws/leaderboard`;
  }
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  return `${protocol}//${window.location.host}/ws/leaderboard`;
};

const getRestUrl = (): string => {
  const apiOrigin = (import.meta as any).env?.VITE_API_ORIGIN as string | undefined;
  const origin = (apiOrigin || '').trim().replace(/\/$/, '');
  return origin ? `${origin}/api/v1/leaderboard/current` : '/api/v1/leaderboard/current';
};

export const useLeaderboard = () => {
  const [leaderboard, setLeaderboard] = useState<LeaderboardEntry[]>([]);
  const [error, setError] = useState<string | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    let cancelled = false;

    // Seed initial data from REST while WS is connecting
    fetch(getRestUrl())
      .then((r) => (r.ok ? r.json() : null))
      .then((data) => {
        if (!cancelled && data?.clips && Array.isArray(data.clips)) {
          setLeaderboard(data.clips);
        }
      })
      .catch(() => {
        // Non-fatal — WS will provide data when it connects
      });

    const connect = () => {
      if (cancelled) return;

      const ws = new WebSocket(getWebSocketUrl());
      wsRef.current = ws;

      ws.onopen = () => {
        if (reconnectTimeoutRef.current) {
          clearTimeout(reconnectTimeoutRef.current);
          reconnectTimeoutRef.current = null;
        }
      };

      ws.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data as string);
          if (message.type !== 'leaderboard_update') return;

          const payload = message.changes ?? message.data;
          if (!payload) return;

          // When backend sends a full top_10 snapshot, replace state outright.
          // This avoids drift from missed delta messages (e.g. reconnects).
          if (payload.top_10 && Array.isArray(payload.top_10)) {
            setLeaderboard(payload.top_10);
            return;
          }

          // Fallback: apply deltas if top_10 not present (should not happen normally)
          if (Array.isArray(payload)) {
            setLeaderboard(payload);
          }
        } catch {
          // Malformed WS message — ignore
        }
      };

      ws.onerror = () => {
        setError('WebSocket connection error');
      };

      ws.onclose = () => {
        if (!cancelled) {
          reconnectTimeoutRef.current = setTimeout(connect, 3000);
        }
      };
    };

    // Defer by one event-loop tick so React StrictMode's synchronous
    // unmount/remount cycle can cancel this timer before the socket is
    // ever opened — eliminating the "closed before established" warning.
    const initialTimer = setTimeout(connect, 0);

    return () => {
      cancelled = true;
      clearTimeout(initialTimer);
      if (reconnectTimeoutRef.current) clearTimeout(reconnectTimeoutRef.current);
      // Only close if fully open — avoids closing a half-open socket
      if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
        wsRef.current.close();
      }
      wsRef.current = null;
    };
  }, []);

  return { leaderboard, error };
};
