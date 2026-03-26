import type {
  ClipsResponse,
  VideoUrlResponse,
  ClipActionResponse,
  Comment,
  LeaderboardClip,
  AdminClip,
  QueueStatusResponse,
  ProcessStatusResponse,
  EmoteResponse,
  GifResponse,
} from '../types';

const API_BASE = '/api';
const WS_BASE = `ws://${window.location.host}`;

async function fetchJson<T>(url: string, options?: RequestInit): Promise<T> {
  const token = localStorage.getItem('token');
  const response = await fetch(url, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...options?.headers,
    },
  });
  if (!response.ok) {
    throw new Error(`API Error: ${response.status}`);
  }
  return response.json();
}

export const api = {
  // Auth
  login: (email: string, password: string): Promise<{ access_token: string; user: any }> =>
    fetchJson('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    }),

  register: (username: string, email: string, password: string): Promise<{ access_token: string; user: any }> =>
    fetchJson('/auth/register', {
      method: 'POST',
      body: JSON.stringify({ username, email, password }),
    }),

  getMe: (): Promise<any> => fetchJson('/auth/me'),

  // Twitch OAuth
  getTwitchLoginUrl: (): Promise<{ authorization_url: string }> =>
    fetchJson('/auth/twitch/login'),

  linkTwitch: (code: string): Promise<any> =>
    fetchJson('/auth/twitch/link', {
      method: 'POST',
      body: JSON.stringify({ code }),
    }),

  unlinkTwitch: (): Promise<any> =>
    fetchJson('/auth/twitch/unlink', { method: 'DELETE' }),

  // Following
  getFollowing: (): Promise<any[]> => fetchJson('/api/following'),

  addFollowing: (streamer_name: string, streamer_id: string): Promise<any> =>
    fetchJson('/api/following', {
      method: 'POST',
      body: JSON.stringify({ streamer_name, streamer_id }),
    }),

  removeFollowing: (streamer_id: string): Promise<any> =>
    fetchJson(`/api/following/${streamer_id}`, { method: 'DELETE' }),

  getTwitchFollows: (): Promise<any[]> => fetchJson('/api/following/twitch/follows'),

  searchChannels: (query: string): Promise<any[]> =>
    fetchJson(`/api/following/search?q=${encodeURIComponent(query)}`),

  syncFollows: (): Promise<any> =>
    fetchJson('/api/following/sync', { method: 'POST' }),

  // Clips
  getClips: (category: string = 'My Streamers'): Promise<ClipsResponse> =>
    fetchJson<ClipsResponse>(`${API_BASE}/clips?category=${encodeURIComponent(category)}`),

  getCategories: (): Promise<{ categories: string[] }> =>
    fetchJson(`${API_BASE}/categories`),

  getVideoUrl: (clipId: string): Promise<VideoUrlResponse> =>
    fetchJson<VideoUrlResponse>(`${API_BASE}/clip/${clipId}/video-url`),

  // Votes (authenticated)
  likeClip: (clipId: string): Promise<ClipActionResponse> =>
    fetchJson<ClipActionResponse>(`${API_BASE}/votes/clip/${clipId}/vote?vote_type=like`, {
      method: 'POST',
    }),

  dislikeClip: (clipId: string): Promise<ClipActionResponse> =>
    fetchJson<ClipActionResponse>(`${API_BASE}/votes/clip/${clipId}/vote?vote_type=dislike`, {
      method: 'POST',
    }),

  getClipVotes: (clipId: string): Promise<{ likes: number; dislikes: number }> =>
    fetchJson(`${API_BASE}/votes/clip/${clipId}/votes`),

  // Legacy endpoints (still work without auth)
  legacyLikeClip: (clipId: string): Promise<ClipActionResponse> =>
    fetchJson<ClipActionResponse>(`${API_BASE}/clip/${clipId}/action`, {
      method: 'POST',
      body: JSON.stringify({ action: 'like' }),
    }),

  legacyDislikeClip: (clipId: string): Promise<ClipActionResponse> =>
    fetchJson<ClipActionResponse>(`${API_BASE}/clip/${clipId}/action`, {
      method: 'POST',
      body: JSON.stringify({ action: 'dislike' }),
    }),

  getComments: (clipId: string): Promise<Comment[]> =>
    fetchJson<Comment[]>(`${API_BASE}/clip/${clipId}/comments`),

  postComment: (clipId: string, text: string): Promise<{ status: string; comment: Comment }> =>
    fetchJson(`${API_BASE}/clip/${clipId}/comments`, {
      method: 'POST',
      body: JSON.stringify({ text }),
    }),

  getLeaderboard: (): Promise<LeaderboardClip[]> =>
    fetchJson<LeaderboardClip[]>(`${API_BASE}/leaderboard`),

  addToQueue: (clipId: string): Promise<QueueStatusResponse> =>
    fetchJson<QueueStatusResponse>(`${API_BASE}/admin/queue`, {
      method: 'POST',
      body: JSON.stringify({ clip_id: clipId }),
    }),

  removeFromQueue: (clipId: string): Promise<QueueStatusResponse> =>
    fetchJson<QueueStatusResponse>(`${API_BASE}/admin/remove`, {
      method: 'POST',
      body: JSON.stringify({ clip_id: clipId }),
    }),

  getAcceptedClips: (): Promise<AdminClip[]> =>
    fetchJson<AdminClip[]>(`${API_BASE}/accepted`),

  processClips: (clipIds: string[]): Promise<ProcessStatusResponse> =>
    fetchJson<ProcessStatusResponse>(`${API_BASE}/process`, {
      method: 'POST',
      body: JSON.stringify({ clip_ids: clipIds }),
    }),

  getEmotes: (channel?: string): Promise<EmoteResponse> =>
    fetchJson<EmoteResponse>(`${API_BASE}/emotes${channel ? `?channel=${encodeURIComponent(channel)}` : ''}`),

  searchGifs: (query: string, limit?: number): Promise<GifResponse> =>
    fetchJson<GifResponse>(`${API_BASE}/gifs?q=${encodeURIComponent(query)}${limit ? `&limit=${limit}` : ''}`),

  // AI Editor clip history (PRO only)
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
  }) =>
    fetchJson(`${API_BASE}/v1/ai-editor/history/save`, {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  getUserClipHistory: (): Promise<any> =>
    fetchJson(`${API_BASE}/v1/ai-editor/history`),

  deleteClipFromHistory: (clipId: string): Promise<any> =>
    fetchJson(`${API_BASE}/v1/ai-editor/history/clip/${clipId}`, {
      method: 'DELETE',
    }),

  clearAllHistory: (): Promise<any> =>
    fetchJson(`${API_BASE}/v1/ai-editor/history/clear-all`, {
      method: 'DELETE',
    }),
};

// WebSocket for live leaderboard updates
export function createLeaderboardSocket(onUpdate: (clips: LeaderboardClip[]) => void, onConnect?: () => void) {
  const ws = new WebSocket(`${WS_BASE}/ws/leaderboard`);
  
  ws.onopen = () => {
    console.log('WebSocket connected');
    if (onConnect) {
      onConnect();
    }
  };

  ws.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data);
      if (data.type === 'leaderboard_update') {
        onUpdate(data.data);
      }
    } catch (e) {
      console.error('Failed to parse WebSocket message:', e);
    }
  };

  ws.onerror = (error) => {
    console.error('WebSocket error:', error);
  };

  ws.onclose = () => {
    console.log('WebSocket disconnected');
  };

  return ws;
}
