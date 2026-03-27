import React from 'react';
import { useLeaderboard } from '../hooks/useLeaderboard';
import './Leaderboard.css';

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
    const { leaderboard, loading, error } = useLeaderboard();

    if (loading)
        return <div className="leaderboard-loading">Loading leaderboard...</div>;
    if (error) return <div className="leaderboard-error">{error}</div>;

    return (
        <div className="leaderboard-container">
            <h2 className="leaderboard-title">🏆 Live Leaderboard</h2>
            <div className="leaderboard-list">
                {leaderboard.map((clip) => (
                    <MemoizedLeaderboardRow key={clip.clip_id} clip={clip} />
                ))}
            </div>
        </div>
    );
};

interface LeaderboardRowProps {
    clip: LeaderboardClip;
}

const getRankClass = (rank: number): string => {
    if (rank === 1) return 'rank-gold';
    if (rank === 2) return 'rank-silver';
    if (rank === 3) return 'rank-bronze';
    return 'rank-default';
};

const LeaderboardRow: React.FC<LeaderboardRowProps> = ({ clip }) => {
    return (
        <div
            className={`leaderboard-row ${getRankClass(clip.rank)}`}
            data-rank={clip.rank}
        >
            <div className="rank-badge">#{clip.rank}</div>

            <img
                src={clip.thumbnail_url}
                alt={clip.title}
                className="clip-thumbnail"
                onError={(e) => {
                    (e.target as HTMLImageElement).src =
                        'https://via.placeholder.com/60x40?text=Thumbnail';
                }}
            />

            <div className="clip-info">
                <h3 className="clip-title">{clip.title}</h3>
                <p className="clip-creator">by {clip.creator}</p>
            </div>

            <div className="clip-stats">
                <div className="likes">
                    <span className="like-icon">❤️</span>
                    <span className="like-count">{clip.likes}</span>
                </div>
                <div className="score" title="Ranking Score">
                    {clip.score.toFixed(0)}
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
