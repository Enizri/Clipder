import { useEffect, useState } from 'react';

interface LeaderboardClip {
    rank: number;
    clip_id: number;
    score: number;
    likes: number;
    title: string;
    creator: string;
    thumbnail_url: string;
}

interface LeaderboardUpdate {
    clips_entered: LeaderboardClip[];
    clips_exited: Array<{ clip_id: number }>;
    position_changes: Array<{
        clip_id: number;
        old_rank: number;
        new_rank: number;
        score: number;
    }>;
    top_10: LeaderboardClip[];
}

// Get WebSocket URL dynamically from current location
const getWebSocketUrl = (): string => {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    return `${protocol}//${window.location.host}/ws/leaderboard`;
};

export const useLeaderboard = () => {
    const [leaderboard, setLeaderboard] = useState<LeaderboardClip[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        // 1. Fetch initial leaderboard
        const fetchInitial = async () => {
            try {
                const response = await fetch('/api/v1/leaderboard/current');
                if (!response.ok) throw new Error('Failed to fetch');
                const data = await response.json();
                setLeaderboard(data.clips || []);
                setLoading(false);
            } catch (err) {
                console.error('Leaderboard fetch error:', err);
                setError('Failed to load leaderboard');
                setLoading(false);
            }
        };

        fetchInitial();

        // 2. Connect to WebSocket with dynamic URL
        const wsUrl = getWebSocketUrl();
        console.log('Connecting to WebSocket:', wsUrl);
        
        const ws = new WebSocket(wsUrl);

        ws.onopen = () => {
            console.log('✅ WebSocket connected to leaderboard');
        };

        ws.onmessage = (event) => {
            try {
                const message = JSON.parse(event.data);

                if (message.type === 'leaderboard_update') {
                    const { changes } = message as { changes: LeaderboardUpdate };
                    console.log('📊 Leaderboard update received:', changes);

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
            console.log('🔌 WebSocket disconnected');
        };

        return () => {
            ws.close();
        };
    }, []);

    return { leaderboard, loading, error };
};
