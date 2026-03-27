import React, { useRef, useState } from 'react';
import { useLeaderboard } from '../hooks/useLeaderboard';

interface LeaderboardClip {
    rank: number;
    clip_id: number;
    score: number;
    likes: number;
    title: string;
    creator: string;
    thumbnail_url: string;
}

export const Leaderboard: React.FC = () => {
    const { leaderboard, error } = useLeaderboard();

    if (error) return <div className="empty-msg" style={{ color: '#ff6b9d' }}>Error: {error}</div>;

    return (
        <div className="list-container">
            <h2 className="section-title">🏆 Top Viral Clips</h2>
            <div className="section-subtitle">Ranked by your swipes. Hover to preview!</div>

            {leaderboard.length === 0 ? (
                <div className="empty-msg">No clips have been liked yet!<br />Go swipe right to build the leaderboard.</div>
            ) : (
                leaderboard.map((clip) => (
                    <MemoizedLeaderboardRow key={clip.clip_id} clip={clip} />
                ))
            )}
        </div>
    );
};

interface LeaderboardRowProps {
    clip: LeaderboardClip;
}

const LeaderboardRow: React.FC<LeaderboardRowProps> = ({ clip }) => {
    const [isLoading, setIsLoading] = useState(false);
    const [videoSrc, setVideoSrc] = useState<string | null>(null);
    const [isPlaying, setIsPlaying] = useState(false);
    const [isMuted, setIsMuted] = useState(false);
    const [volume, setVolume] = useState(50);
    const videoRef = useRef<HTMLVideoElement>(null);
    const fetchedRef = useRef(false);

    const handleMouseEnter = async () => {
        const video = videoRef.current;
        if (!video) return;

        if (fetchedRef.current && videoSrc) {
            video.volume = volume / 100;
            video.muted = isMuted || volume === 0;
            video.play().then(() => setIsPlaying(true)).catch(() => {});
            return;
        }

        if (fetchedRef.current) return;
        fetchedRef.current = true;

        // Try to fetch video URL from API
        setIsLoading(true);
        try {
            const response = await fetch(
                window.location.port === '3000'
                    ? `http://localhost:8000/api/v1/clips/${clip.clip_id}/video`
                    : `/api/v1/clips/${clip.clip_id}/video`
            );
            if (response.ok) {
                const data = await response.json();
                if (data.video_url) {
                    const vid = videoRef.current;
                    if (vid) {
                        vid.src = data.video_url;
                        setVideoSrc(data.video_url);
                        vid.volume = volume / 100;
                        vid.muted = isMuted || volume === 0;
                        vid.play().then(() => setIsPlaying(true)).catch(() => {});
                    }
                }
            }
        } catch (e) {
            console.error('Failed to fetch video:', e);
        } finally {
            setIsLoading(false);
        }
    };

    const handleMouseLeave = () => {
        const video = videoRef.current;
        if (video) {
            video.pause();
            video.currentTime = 0;
        }
        setIsPlaying(false);
    };

    const handlePlayPause = (e: React.MouseEvent) => {
        e.stopPropagation();
        const video = videoRef.current;
        if (!video || !videoSrc) return;
        if (isPlaying) {
            video.pause();
        } else {
            video.play().catch(() => {});
        }
        setIsPlaying(!isPlaying);
    };

    const handleVolumeChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        const val = parseInt(e.target.value);
        setVolume(val);
        if (videoRef.current) {
            videoRef.current.volume = val / 100;
        }
    };

    const handleMuteToggle = (e: React.MouseEvent) => {
        e.stopPropagation();
        const newMuted = !isMuted;
        setIsMuted(newMuted);
        if (videoRef.current) {
            videoRef.current.muted = newMuted;
        }
    };

    return (
        <div className="list-item">
            <div style={{ fontSize: '1.2em', fontWeight: 900, color: '#888', width: '40px', textAlign: 'center' }}>
                #{clip.rank}
            </div>

            <div className="thumb-wrapper">
                <div
                    className="thumb-container"
                    onMouseEnter={handleMouseEnter}
                    onMouseLeave={handleMouseLeave}
                >
                    <img
                        src={clip.thumbnail_url}
                        alt={clip.title}
                        onError={(e) => {
                            (e.target as HTMLImageElement).src =
                                'https://via.placeholder.com/140x79?text=Thumbnail';
                        }}
                    />
                    <video ref={videoRef} onEnded={() => setIsPlaying(false)} />

                    <div className="mini-controls">
                        <button
                            className="mini-btn"
                            onClick={handlePlayPause}
                            title={isPlaying ? 'Pause' : 'Play'}
                        >
                            {isPlaying ? '⏸' : '▶'}
                        </button>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                            <button
                                className="mini-btn"
                                onClick={handleMuteToggle}
                                title={isMuted ? 'Unmute' : 'Mute'}
                            >
                                {isMuted ? '🔇' : '🔊'}
                            </button>
                            <input
                                type="range"
                                min="0"
                                max="100"
                                value={volume}
                                onChange={handleVolumeChange}
                                className="mini-volume"
                            />
                        </div>
                    </div>

                    {isLoading && (
                        <div className="mini-spinner"></div>
                    )}
                </div>
            </div>

            <div className="item-details">
                <div className="item-title">{clip.title}</div>
                <div className="item-stats">
                    <span>♥ {clip.likes} Likes</span>
                    <span>{clip.creator}</span>
                    <span>Score: {clip.score.toFixed(0)}</span>
                </div>
            </div>
        </div>
    );
};

// Memoize to prevent unnecessary re-renders when parent updates
export const MemoizedLeaderboardRow = React.memo(LeaderboardRow, (prev, next) => {
    // Return true if props are equal (skip re-render)
    return (
        prev.clip.clip_id === next.clip.clip_id &&
        prev.clip.rank === next.clip.rank &&
        prev.clip.score === next.clip.score &&
        prev.clip.likes === next.clip.likes
    );
});
