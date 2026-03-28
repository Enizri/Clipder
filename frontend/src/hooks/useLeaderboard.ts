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

          if (Array.isArray(payload)) {
            setLeaderboard(payload);
            return;
          }

          setLeaderboard((prev) => {
            let updated = [...prev];

            if (payload.clips_exited?.length) {
              const exitedIds = new Set(payload.clips_exited.map((e: any) => e.clip_id));
              updated = updated.filter((c) => !exitedIds.has(c.clip_id));
            }

            if (payload.clips_entered?.length) {
              updated = [...updated, ...payload.clips_entered];
            }

            if (payload.position_changes?.length) {
              updated = updated.map((c) => {
                const change = payload.position_changes.find((ch: any) => ch.clip_id === c.clip_id);
                return change ? { ...c, rank: change.new_rank, score: change.score } : c;
              });
            }

            return [...updated].sort((a, b) => a.rank - b.rank);
          });
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
