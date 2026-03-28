import type {
  ClipsResponse,
  VideoUrlResponse,
  VoteResponse,
  Comment,
  LeaderboardEntry,
  AdminClip,
  QueueStatusResponse,
  ProcessStatusResponse,
  EmoteResponse,
  User,
} from '../types';

const getConfiguredApiOrigin = (): string | null => {
  const raw = (import.meta as any).env?.VITE_API_ORIGIN as string | undefined;
  const value = (raw || '').trim();
  return value ? value.replace(/\/$/, '') : null;
};

// If VITE_API_ORIGIN is set use it; otherwise fall back to same-origin (proxy mode).
const API_ORIGIN = getConfiguredApiOrigin();
const API_BASE = API_ORIGIN ? `${API_ORIGIN}/api/v1` : '/api/v1';

async function fetchJson<T>(url: string, options?: RequestInit): Promise<T> {
  const fullUrl = url.startsWith('http') ? url : `${API_BASE}${url}`;

  const token = localStorage.getItem('token');
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options?.headers as Record<string, string>),
  };

  // Add auth header only for routes that require authentication
  const requiresAuth = [
    '/votes',
    '/following',
    '/admin',
    '/ai',
    '/ai-editor',
    '/auth/me',
  ].some((p) => fullUrl.includes(p));
  if (token && requiresAuth) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const response = await fetch(fullUrl, { ...options, headers });

  if (!response.ok) {
    const text = await response.text().catch(() => '');
    let detail = `HTTP ${response.status}`;
    try {
      const json = JSON.parse(text);
      detail = json.detail ?? json.message ?? detail;
    } catch {
      // response body was not JSON — use the status text
    }
    throw new Error(detail);
  }

  return response.json() as Promise<T>;
}

export const api = {
  // ===========================================================================
  // AUTH — Twitch only
  // ===========================================================================

  getMe: (): Promise<User> => fetchJson('/auth/me'),

  /** Returns Twitch OAuth URL — no token required. */
  getTwitchLoginUrl: (): Promise<{ authorization_url: string }> =>
    fetchJson('/auth/twitch/login'),

  // ===========================================================================
  // FOLLOWING
  // ===========================================================================

  getFollowing: (): Promise<{ id: number; streamer_name: string; streamer_id: string }[]> =>
    fetchJson('/following'),

  addFollowing: (streamer_name: string, streamer_id: string): Promise<unknown> =>
    fetchJson('/following', { method: 'POST', body: JSON.stringify({ streamer_name, streamer_id }) }),

  removeFollowing: (streamer_id: string): Promise<unknown> =>
    fetchJson(`/following/${streamer_id}`, { method: 'DELETE' }),

  getTwitchFollows: (): Promise<unknown[]> => fetchJson('/following/twitch/follows'),

  searchChannels: (query: string): Promise<unknown[]> =>
    fetchJson(`/following/search?q=${encodeURIComponent(query)}`),

  syncFollows: (): Promise<unknown> => fetchJson('/following/sync', { method: 'POST' }),

  // ===========================================================================
  // CLIPS
  // ===========================================================================

  getClips: (category = 'My Streamers'): Promise<ClipsResponse> =>
    fetchJson<ClipsResponse>(`/clips?category=${encodeURIComponent(category)}`),

  getCategories: (): Promise<{ categories: string[] }> => fetchJson('/categories'),

  getVideoUrl: (clipId: string): Promise<VideoUrlResponse> =>
    fetchJson<VideoUrlResponse>(`/clip/${clipId}/video-url`),

  // ===========================================================================
  // VOTES (authenticated users only)
  // ===========================================================================

  likeClip: (clipId: string): Promise<VoteResponse> =>
    fetchJson<VoteResponse>(`/votes/clip/${clipId}/vote?vote_type=like`, { method: 'POST' }),

  dislikeClip: (clipId: string): Promise<VoteResponse> =>
    fetchJson<VoteResponse>(`/votes/clip/${clipId}/vote?vote_type=dislike`, { method: 'POST' }),

  getClipVotes: (clipId: string): Promise<{ likes: number; dislikes: number }> =>
    fetchJson(`/votes/clip/${clipId}/votes`),

  // ===========================================================================
  // COMMENTS
  // ===========================================================================

  getComments: (clipId: string): Promise<Comment[]> =>
    fetchJson<Comment[]>(`/clip/${clipId}/comments`),

  postComment: (clipId: string, text: string): Promise<{ status: string; comment: Comment }> =>
    fetchJson(`/clip/${clipId}/comments`, { method: 'POST', body: JSON.stringify({ text }) }),

  // ===========================================================================
  // LEADERBOARD
  // ===========================================================================

  getLeaderboard: (): Promise<{ month_key: string; clips: LeaderboardEntry[] }> =>
    fetchJson<{ month_key: string; clips: LeaderboardEntry[] }>('/leaderboard/current'),

  // ===========================================================================
  // ADMIN
  // ===========================================================================

  addToQueue: (clipId: string): Promise<QueueStatusResponse> =>
    fetchJson<QueueStatusResponse>('/admin/queue', {
      method: 'POST',
      body: JSON.stringify({ clip_id: clipId }),
    }),

  removeFromQueue: (clipId: string): Promise<QueueStatusResponse> =>
    fetchJson<QueueStatusResponse>('/admin/remove', {
      method: 'POST',
      body: JSON.stringify({ clip_id: clipId }),
    }),

  getAcceptedClips: (): Promise<AdminClip[]> => fetchJson<AdminClip[]>('/admin/accepted'),

  processClips: (clipIds: string[]): Promise<ProcessStatusResponse> =>
    fetchJson<ProcessStatusResponse>('/admin/process', {
      method: 'POST',
      body: JSON.stringify({ clip_ids: clipIds }),
    }),

  // ===========================================================================
  // EMOTES
  // ===========================================================================

  getEmotes: (channel?: string): Promise<EmoteResponse> =>
    fetchJson<EmoteResponse>(`/emotes${channel ? `?channel=${encodeURIComponent(channel)}` : ''}`),

  // ===========================================================================
  // AI EDITOR HISTORY (PRO)
  // ===========================================================================

  saveClipToHistory: (data: {
    clip_id: string;
    clip_title: string;
    clip_url: string;
    clip_channel: string;
    thumbnail_url?: string;
    clip_description?: string;
    clip_tags?: string[];
    edited_title?: string;
    chat_messages?: Array<{ role: string; content: string; timestamp: string }>;
    edit_history?: Array<{ action: string; timestamp: string; before?: string; after?: string }>;
  }): Promise<unknown> =>
    fetchJson('/ai-editor/history/save', { method: 'POST', body: JSON.stringify(data) }),

  getUserClipHistory: (): Promise<{ history: any[] }> => fetchJson('/ai-editor/history'),

  deleteClipFromHistory: (clipId: string): Promise<unknown> =>
    fetchJson(`/ai-editor/history/clip/${clipId}`, { method: 'DELETE' }),

  clearAllHistory: (): Promise<unknown> =>
    fetchJson('/ai-editor/history/clear-all', { method: 'DELETE' }),
};
