import { useEffect, useState, useRef } from 'react';

interface LeaderboardClip {
    rank: number;
    clip_id: number;
    score: number;
    likes: number;
    title: string;
    creator: string;
    thumbnail_url: string;
}

// Get WebSocket URL dynamically from current location
const getWebSocketUrl = (): string => {
    if (window.location.port === '3000') {
        return 'ws://localhost:8000/ws/leaderboard';
    }
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    return `${protocol}//${window.location.host}/ws/leaderboard`;
};

export const useLeaderboard = () => {
    const [leaderboard, setLeaderboard] = useState<LeaderboardClip[]>([]);
    const [loading, setLoading] = useState(false); // Start with false - no initial load
    const [error, setError] = useState<string | null>(null);
    const wsRef = useRef<WebSocket | null>(null);
    const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

    useEffect(() => {
        // Don't fetch initial leaderboard - start empty and wait for first vote to populate
        setLoading(false);

        // Connect to WebSocket to listen for updates
        const connectWebSocket = () => {
            // Close any existing connection first
            if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
                wsRef.current.close();
            }

            const wsUrl = getWebSocketUrl();
            console.log('Connecting to WebSocket:', wsUrl);
            
            const ws = new WebSocket(wsUrl);
            wsRef.current = ws;

            ws.onopen = () => {
                console.log('✅ WebSocket connected to leaderboard');
                // Clear any pending reconnect attempts
                if (reconnectTimeoutRef.current) {
                    clearTimeout(reconnectTimeoutRef.current);
                    reconnectTimeoutRef.current = null;
                }
            };

            ws.onmessage = (event) => {
                try {
                    const message = JSON.parse(event.data);

                    if (message.type === 'leaderboard_update') {
                        console.log('📊 Leaderboard update received:', message);
                        
                        // Handle both message formats:
                        // Format 1: { type: 'leaderboard_update', changes: {...} } (delta updates)
                        // Format 2: { type: 'leaderboard_update', data: [...] } (full list)
                        
                        const changes = message.changes || message.data;
                        if (!changes) {
                            console.warn('⚠️ No changes or data in leaderboard update', message);
                            return;
                        }

                        // If it's an array (full leaderboard), replace it
                        if (Array.isArray(changes)) {
                            console.log('📋 Replacing leaderboard with:', changes);
                            setLeaderboard(changes);
                            return;
                        }

                        // Otherwise handle delta updates
                        setLeaderboard((prev) => {
                            let updated = [...prev];

                            // Handle clips exiting top 10 first
                            if (changes.clips_exited && changes.clips_exited.length > 0) {
                                const exitedIds = changes.clips_exited.map((e: any) => e.clip_id);
                                updated = updated.filter((c) => !exitedIds.includes(c.clip_id));
                                console.log(`⬇️ Removed ${exitedIds.length} clips that exited top 10`);
                            }

                            // Handle clips entering top 10
                            if (changes.clips_entered && changes.clips_entered.length > 0) {
                                updated = [...updated, ...changes.clips_entered];
                                console.log(`⬆️ Added ${changes.clips_entered.length} clips that entered top 10`);
                            }

                            // Handle position changes
                            if (changes.position_changes && changes.position_changes.length > 0) {
                                updated = updated.map((c) => {
                                    const change = changes.position_changes.find(
                                        (ch: any) => ch.clip_id === c.clip_id
                                    );
                                    if (change) {
                                        console.log(
                                            `🔄 Clip ${c.clip_id} moved from rank ${change.old_rank} to ${change.new_rank}`
                                        );
                                        return {
                                            ...c,
                                            rank: change.new_rank,
                                            score: change.score,
                                        };
                                    }
                                    return c;
                                });
                            }

                            // Sort by rank
                            const sorted = updated.sort((a, b) => a.rank - b.rank);
                            console.log('📋 Leaderboard updated:', sorted);
                            return sorted;
                        });
                    }
                } catch (err) {
                    console.error('❌ Error processing WebSocket message:', err);
                }
            };

            ws.onerror = (event) => {
                console.error('❌ WebSocket error:', event);
                setError('WebSocket connection error');
            };

            ws.onclose = () => {
                console.log('🔌 WebSocket disconnected - attempting reconnect in 3s');
                // Attempt reconnect after 3 seconds
                reconnectTimeoutRef.current = setTimeout(() => {
                    console.log('🔄 Reconnecting WebSocket...');
                    connectWebSocket();
                }, 3000);
            };
        };

        connectWebSocket();

        return () => {
            // Cleanup: close WebSocket and clear timeouts
            if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
                wsRef.current.close();
            }
            if (reconnectTimeoutRef.current) {
                clearTimeout(reconnectTimeoutRef.current);
            }
        };
    }, []);

    return { leaderboard, loading, error };
};
