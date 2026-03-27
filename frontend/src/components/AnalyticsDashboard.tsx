import React, { useEffect, useState, useCallback, useMemo } from 'react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  BarChart,
  Bar,
  Legend,
} from 'recharts';
import './AnalyticsDashboard.css';

interface Snapshot {
  timestamp: string;
  rank: number;
  score: number;
  likes: number;
}

interface HistoricalClip {
  rank: number;
  clip_id: number;
  title: string;
  creator_name: string;
  score: number;
  thumbnail_url: string;
  final_likes?: number;
  final_dislikes?: number;
}

interface HistoricalLeaderboard {
  month_key: string;
  final_ranking: HistoricalClip[];
  total_votes: number;
  total_unique_voters: number;
  top_clip_id: number | null;
  top_clip_score: number | null;
  month_end_date: string | null;
}

interface TrendingClip {
  clip_id: number;
  title: string;
  creator: string;
  current_rank: number;
  previous_rank: number;
  rank_change: number;
  current_score: number;
  thumbnail_url: string;
}

type TabType = 'history' | 'hype' | 'trending' | 'creators';

export const AnalyticsDashboard: React.FC = () => {
  const [activeTab, setActiveTab] = useState<TabType>('history');
  const [monthlyLeaderboards, setMonthlyLeaderboards] = useState<HistoricalLeaderboard[]>([]);
  const [selectedMonth, setSelectedMonth] = useState<string | null>(null);
  const [selectedClipId, setSelectedClipId] = useState<number | null>(null);
  const [snapshotData, setSnapshotData] = useState<Snapshot[]>([]);
  const [trendingClips, setTrendingClips] = useState<TrendingClip[]>([]);
  const [creatorStats, setCreatorStats] = useState<{ creator: string; clip_count: number; avg_score: number }[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [snapshotCache, setSnapshotCache] = useState<Map<number, Snapshot[]>>(new Map());

  // Memoize event handlers to prevent recreation on each render
  const handleMonthChange = useCallback((e: React.ChangeEvent<HTMLSelectElement>) => {
    setSelectedMonth(e.target.value);
  }, []);

  const handleClipSelect = useCallback((clipId: number) => {
    setSelectedClipId(clipId);
    setActiveTab('hype');
  }, []);

  const handleTabChange = useCallback((tab: TabType) => {
    setActiveTab(tab);
  }, []);

  // Memoize month generation to avoid recalculation
  const months = useMemo(() => {
    const now = new Date();
    const result = [];
    for (let i = 0; i < 3; i++) {
      const d = new Date(now.getFullYear(), now.getMonth() - i, 1);
      const year = d.getFullYear();
      const month = String(d.getMonth() + 1).padStart(2, '0');
      result.push(`${year}-${month}`);
    }
    return result;
  }, []);

  // Memoize API URL builder
  const getApiUrl = useCallback((path: string) => {
    const apiOrigin = (import.meta as any).env?.VITE_API_ORIGIN as string | undefined;
    const origin = (apiOrigin || '').trim().replace(/\/$/, '');
    return origin ? `${origin}${path}` : path;
  }, []);

  // Memoize trending calculation
  const calculateTrending = useCallback((leaderboards: HistoricalLeaderboard[]): TrendingClip[] => {
    if (leaderboards.length < 2) return [];

    const currentMonth = leaderboards[0];
    const previousMonth = leaderboards[1];

    const currentClips = new Map(
      currentMonth.final_ranking.map((c) => [c.clip_id, c])
    );
    const previousClips = new Map(
      previousMonth.final_ranking.map((c) => [c.clip_id, c])
    );

    const trending: TrendingClip[] = [];
    currentClips.forEach((clip, clipId) => {
      const prev = previousClips.get(clipId);
      const prevRank = prev?.rank || 11;
      const rankChange = prevRank - clip.rank;

      if (rankChange !== 0) {
        trending.push({
          clip_id: clipId,
          title: clip.title,
          creator: clip.creator_name,
          current_rank: clip.rank,
          previous_rank: prevRank,
          rank_change: rankChange,
          current_score: clip.score,
          thumbnail_url: clip.thumbnail_url,
        });
      }
    });

    return trending.sort((a, b) => Math.abs(b.rank_change) - Math.abs(a.rank_change));
  }, []);

  // Memoize creator stats calculation
  const calculateCreatorStats = useCallback(
    (leaderboards: HistoricalLeaderboard[]) => {
      const creatorMap = new Map<string, { count: number; totalScore: number }>();

      leaderboards.forEach((lb) => {
        lb.final_ranking.forEach((clip) => {
          const existing = creatorMap.get(clip.creator_name) || { count: 0, totalScore: 0 };
          creatorMap.set(clip.creator_name, {
            count: existing.count + 1,
            totalScore: existing.totalScore + clip.score,
          });
        });
      });

      return Array.from(creatorMap.entries())
        .map(([creator, data]) => ({
          creator,
          clip_count: data.count,
          avg_score: data.totalScore / data.count,
        }))
        .sort((a, b) => b.clip_count - a.clip_count);
    },
    []
  );

  // Fetch historical leaderboards on mount
  useEffect(() => {
    const fetchHistorical = async () => {
      try {
        setLoading(true);
        setError(null);

        const data = await Promise.all(
          months.map((month) =>
            fetch(getApiUrl(`/api/v1/leaderboard/history/${month}`))
              .then((r) => {
                if (!r.ok) return null;
                return r.json();
              })
              .catch(() => null)
          )
        );

        const validLeaderboards = data.filter((lb) => lb !== null) as HistoricalLeaderboard[];
        setMonthlyLeaderboards(validLeaderboards);

        if (validLeaderboards.length > 0) {
          setSelectedMonth(validLeaderboards[0].month_key);
        }

        // Calculate trending clips using memoized function
        const trending = calculateTrending(validLeaderboards);
        setTrendingClips(trending);

        // Calculate creator stats using memoized function
        const stats = calculateCreatorStats(validLeaderboards);
        setCreatorStats(stats);

        setLoading(false);
      } catch (err) {
        console.error('Failed to fetch analytics', err);
        setError('Failed to load analytics data');
        setLoading(false);
      }
    };

    fetchHistorical();
  }, [months, getApiUrl, calculateTrending, calculateCreatorStats]);

  // Fetch snapshots when clip selected for hype graph (with caching)
  useEffect(() => {
    if (!selectedClipId) return;

    // Check cache first
    if (snapshotCache.has(selectedClipId)) {
      setSnapshotData(snapshotCache.get(selectedClipId) || []);
      return;
    }

    const fetchSnapshots = async () => {
      try {
        setLoading(true);
        const response = await fetch(
          `/api/v1/leaderboard/clip/${selectedClipId}/snapshots?hours=24`
        );
        if (!response.ok) throw new Error('Failed to fetch snapshots');
        const data = await response.json();
        
        // Update cache
        setSnapshotCache((prev) => {
          const newCache = new Map(prev);
          newCache.set(selectedClipId, data);
          return newCache;
        });
        
        setSnapshotData(data);
        setLoading(false);
      } catch (err) {
        console.error('Failed to fetch snapshots', err);
        setError('Failed to load hype graph data');
        setLoading(false);
      }
    };

    fetchSnapshots();
  }, [selectedClipId, snapshotCache]);

  const renderHistoryTab = () => (
    <div className="analytics-tab">
      <h3>📚 Monthly Leaderboards</h3>
      {monthlyLeaderboards.length === 0 ? (
        <p className="empty-message">No historical data available yet</p>
      ) : (
        <div className="history-container">
          <div className="month-selector">
            <label>Select Month:</label>
            <select
              value={selectedMonth || ''}
              onChange={handleMonthChange}
            >
              {monthlyLeaderboards.map((lb) => (
                <option key={lb.month_key} value={lb.month_key}>
                  {lb.month_key}
                </option>
              ))}
            </select>
          </div>

          {selectedMonth && (
            <div className="history-list">
              {monthlyLeaderboards
                .find((lb) => lb.month_key === selectedMonth)
                ?.final_ranking.map((clip) => (
                  <div
                    key={clip.clip_id}
                    className="history-item"
                    onClick={() => handleClipSelect(clip.clip_id)}
                    title="Click to view hype graph"
                  >
                    <div className="history-rank">#{clip.rank}</div>
                    <img
                      src={clip.thumbnail_url}
                      alt={clip.title}
                      className="history-thumbnail"
                      onError={(e) => {
                        (e.target as HTMLImageElement).src =
                          'data:image/svg+xml,%3Csvg xmlns="http://www.w3.org/2000/svg" width="60" height="40"%3E%3Crect fill="%23ccc" width="60" height="40"/%3E%3C/svg%3E';
                      }}
                    />
                    <div className="history-details">
                      <h4>{clip.title}</h4>
                      <p className="creator-name">by {clip.creator_name}</p>
                    </div>
                    <div className="history-score">{clip.score.toFixed(0)}</div>
                  </div>
                ))}
            </div>
          )}
        </div>
      )}
    </div>
  );

  const renderHypeTab = () => (
    <div className="analytics-tab">
      <h3>📈 Hype Graph (24 Hour Rank History)</h3>
      {monthlyLeaderboards.length === 0 ? (
        <p className="empty-message">No historical data available</p>
      ) : selectedClipId === null ? (
        <p className="empty-message">
          Select a clip from the Monthly Leaderboards tab to view its hype graph
        </p>
      ) : snapshotData.length === 0 ? (
        <p className="empty-message">No snapshot data for this clip</p>
      ) : (
        <div className="hype-graph-container">
          <p className="hype-info">
            📊 Tracking rank changes for clip ID: {selectedClipId} over the last 24 hours
          </p>
          <ResponsiveContainer width="100%" height={350}>
            <LineChart
              data={snapshotData}
              margin={{ top: 5, right: 30, left: 0, bottom: 5 }}
            >
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis
                dataKey="timestamp"
                tick={{ fontSize: 12 }}
                angle={-45}
                textAnchor="end"
                height={80}
                tickFormatter={(value) => {
                  const date = new Date(value);
                  return date.toLocaleTimeString([], {
                    hour: '2-digit',
                    minute: '2-digit',
                  });
                }}
              />
              <YAxis
                type="number"
                domain={[0, 10]}
                reversed
                label={{ value: 'Rank', angle: -90, position: 'insideLeft' }}
              />
              <Tooltip
                formatter={(value: any) => [`Rank #${value}`, 'Rank']}
                labelFormatter={(label: any) =>
                  new Date(label).toLocaleString([], {
                    month: 'short',
                    day: 'numeric',
                    hour: '2-digit',
                    minute: '2-digit',
                  })
                }
              />
              <Line
                type="monotone"
                dataKey="rank"
                stroke="#667eea"
                dot={{ r: 3 }}
                activeDot={{ r: 5 }}
                isAnimationActive={false}
                strokeWidth={2}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  );

  const renderTrendingTab = () => (
    <div className="analytics-tab">
      <h3>🚀 Trending Clips (Last Month)</h3>
      {trendingClips.length === 0 ? (
        <p className="empty-message">No trending data available</p>
      ) : (
        <div className="trending-list">
          {trendingClips.map((clip) => (
            <div key={clip.clip_id} className="trending-item">
              <div className="trending-rank-change">
                <div className={`rank-arrow ${clip.rank_change > 0 ? 'up' : 'down'}`}>
                  {clip.rank_change > 0 ? '📈' : '📉'} {Math.abs(clip.rank_change)}
                </div>
              </div>
              <img
                src={clip.thumbnail_url}
                alt={clip.title}
                className="trending-thumbnail"
                onError={(e) => {
                  (e.target as HTMLImageElement).src =
                    'data:image/svg+xml,%3Csvg xmlns="http://www.w3.org/2000/svg" width="60" height="40"%3E%3Crect fill="%23ccc" width="60" height="40"/%3E%3C/svg%3E';
                }}
              />
              <div className="trending-details">
                <h4>{clip.title}</h4>
                <p className="creator-name">by {clip.creator}</p>
                <div className="rank-transition">
                  Rank: {clip.previous_rank > 10 ? 'New' : `#${clip.previous_rank}`} →{' '}
                  #{clip.current_rank}
                </div>
              </div>
              <div className="trending-score">{clip.current_score.toFixed(0)} pts</div>
            </div>
          ))}
        </div>
      )}
    </div>
  );

  const renderCreatorsTab = () => (
    <div className="analytics-tab">
      <h3>👥 Creator Stats</h3>
      {creatorStats.length === 0 ? (
        <p className="empty-message">No creator data available</p>
      ) : (
        <div className="creators-container">
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={creatorStats} margin={{ top: 20, right: 30, left: 0, bottom: 80 }}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis
                dataKey="creator"
                angle={-45}
                textAnchor="end"
                height={100}
                tick={{ fontSize: 11 }}
              />
              <YAxis yAxisId="left" label={{ value: 'Clips in Top 10', angle: -90, position: 'insideLeft' }} />
              <YAxis yAxisId="right" orientation="right" label={{ value: 'Avg Score', angle: 90, position: 'insideRight' }} />
              <Tooltip />
              <Legend />
              <Bar yAxisId="left" dataKey="clip_count" fill="#667eea" name="Clips" />
              <Bar yAxisId="right" dataKey="avg_score" fill="#764ba2" name="Avg Score" />
            </BarChart>
          </ResponsiveContainer>

          <div className="creators-list">
            {creatorStats.map((creator, idx) => (
              <div key={creator.creator} className="creator-stat-item">
                <div className="creator-rank">#{idx + 1}</div>
                <div className="creator-info">
                  <h4>{creator.creator}</h4>
                  <p>{creator.clip_count} clips • Avg: {creator.avg_score.toFixed(0)} pts</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );

  if (loading && monthlyLeaderboards.length === 0) {
    return (
      <div className="analytics-dashboard">
        <h2>🎯 Leaderboard Analytics</h2>
        <div className="loading-message">Loading analytics data...</div>
      </div>
    );
  }

  if (error && monthlyLeaderboards.length === 0) {
    return (
      <div className="analytics-dashboard">
        <h2>🎯 Leaderboard Analytics</h2>
        <div className="error-message">{error}</div>
      </div>
    );
  }

  return (
    <div className="analytics-dashboard">
      <h2>🎯 Leaderboard Analytics</h2>

      <div className="analytics-tabs">
        <button
          className={`analytics-tab-btn ${activeTab === 'history' ? 'active' : ''}`}
          onClick={() => handleTabChange('history')}
        >
          📚 History
        </button>
        <button
          className={`analytics-tab-btn ${activeTab === 'hype' ? 'active' : ''}`}
          onClick={() => handleTabChange('hype')}
        >
          📈 Hype Graphs
        </button>
        <button
          className={`analytics-tab-btn ${activeTab === 'trending' ? 'active' : ''}`}
          onClick={() => handleTabChange('trending')}
        >
          🚀 Trending
        </button>
        <button
          className={`analytics-tab-btn ${activeTab === 'creators' ? 'active' : ''}`}
          onClick={() => handleTabChange('creators')}
        >
          👥 Creators
        </button>
      </div>

      <div className="analytics-content">
        {activeTab === 'history' && renderHistoryTab()}
        {activeTab === 'hype' && renderHypeTab()}
        {activeTab === 'trending' && renderTrendingTab()}
        {activeTab === 'creators' && renderCreatorsTab()}
      </div>
    </div>
  );
};
