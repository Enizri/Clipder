import React from 'react';
import { Leaderboard } from '../components/Leaderboard';

interface LeaderboardPageProps {
  onOpenComments: (clipId: string, title: string) => void;
}

export const LeaderboardPage: React.FC<LeaderboardPageProps> = ({ onOpenComments }) => {
  return (
    <div id="leaderboard" className="view-section active">
      <div className="list-container">
        <Leaderboard
          onOpenComments={(clipId: number, title: string) =>
            onOpenComments(clipId.toString(), title)
          }
        />
      </div>
    </div>
  );
};
