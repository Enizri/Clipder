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

const getConfiguredApiOrigin = (): string | null => {
  const raw = (import.meta as any).env?.VITE_API_ORIGIN as string | undefined;
  const value = (raw || '').trim();
  return value ? value.replace(/\/$/, '') : null;
};

// If VITE_API_ORIGIN is set (e.g. http://127.0.0.1:8001), use it.
// Otherwise default to same-origin (works when you serve frontend through backend/proxy).
const API_ORIGIN = getConfiguredApiOrigin();
const API_BASE = API_ORIGIN ? `${API_ORIGIN}/api` : '/api';

const WS_BASE = (() => {
  if (API_ORIGIN) {
    return API_ORIGIN.replace(/^http:/, 'ws:').replace(/^https:/, 'wss:');
  }
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  return `${protocol}//${window.location.host}`;
})();

async function fetchJson<T>(url: string, options?: RequestInit): Promise<T> {
  // Build full URL.
  // - If caller passes an absolute URL, use it as-is.
  // - Otherwise treat it as an API path under API_BASE.
  const fullUrl = url.startsWith('http') ? url : `${API_BASE}${url}`;
  
  const token = localStorage.getItem('token');
  
  // Only add auth header if token exists AND endpoint requires it
  // Most public endpoints don't need auth
  const headers: any = {
    'Content-Type': 'application/json',
    ...options?.headers,
  };
  
  // Only add token for endpoints that need auth (votes, following, admin, ai_chat, ai_editor, auth/me)
  const requiresAuth = ['/votes', '/following', '/admin', '/ai', '/auth/me'].some(path => fullUrl.includes(path));
  if (token && requiresAuth) {
    headers['Authorization'] = `Bearer ${token}`;
  }
  
  const response = await fetch(fullUrl, {
    ...options,
    headers,
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
  getFollowing: (): Promise<any[]> => fetchJson('/following'),

  addFollowing: (streamer_name: string, streamer_id: string): Promise<any> =>
    fetchJson('/following', {
      method: 'POST',
      body: JSON.stringify({ streamer_name, streamer_id }),
    }),

  removeFollowing: (streamer_id: string): Promise<any> =>
    fetchJson(`/following/${streamer_id}`, { method: 'DELETE' }),

  getTwitchFollows: (): Promise<any[]> => fetchJson('/following/twitch/follows'),

  searchChannels: (query: string): Promise<any[]> =>
    fetchJson(`/following/search?q=${encodeURIComponent(query)}`),

  syncFollows: (): Promise<any> =>
    fetchJson('/following/sync', { method: 'POST' }),

  // Clips
  getClips: (category: string = 'My Streamers'): Promise<ClipsResponse> =>
    fetchJson<ClipsResponse>(`/clips?category=${encodeURIComponent(category)}`),

  getCategories: (): Promise<{ categories: string[] }> =>
    fetchJson('/categories'),

  getVideoUrl: (clipId: string): Promise<VideoUrlResponse> =>
    fetchJson<VideoUrlResponse>(`/clip/${clipId}/video-url`),

  // Votes (authenticated)
  likeClip: (clipId: string): Promise<ClipActionResponse> =>
    fetchJson<ClipActionResponse>(`/votes/clip/${clipId}/vote?vote_type=like`, {
      method: 'POST',
    }),

  dislikeClip: (clipId: string): Promise<ClipActionResponse> =>
    fetchJson<ClipActionResponse>(`/votes/clip/${clipId}/vote?vote_type=dislike`, {
      method: 'POST',
    }),

  getClipVotes: (clipId: string): Promise<{ likes: number; dislikes: number }> =>
    fetchJson(`/votes/clip/${clipId}/votes`),

  // Legacy endpoints (still work without auth)
  legacyLikeClip: (clipId: string): Promise<ClipActionResponse> =>
    fetchJson<ClipActionResponse>(`/clip/${clipId}/action`, {
      method: 'POST',
      body: JSON.stringify({ action: 'like' }),
    }),

  legacyDislikeClip: (clipId: string): Promise<ClipActionResponse> =>
    fetchJson<ClipActionResponse>(`/clip/${clipId}/action`, {
      method: 'POST',
      body: JSON.stringify({ action: 'dislike' }),
    }),

  getComments: (clipId: string): Promise<Comment[]> =>
    fetchJson<Comment[]>(`/clip/${clipId}/comments`),

  postComment: (clipId: string, text: string): Promise<{ status: string; comment: Comment }> =>
    fetchJson(`/clip/${clipId}/comments`, {
      method: 'POST',
      body: JSON.stringify({ text }),
    }),

  getLeaderboard: (): Promise<LeaderboardClip[]> =>
    fetchJson<LeaderboardClip[]>(`/leaderboard`),

  addToQueue: (clipId: string): Promise<QueueStatusResponse> =>
    fetchJson<QueueStatusResponse>(`/admin/queue`, {
      method: 'POST',
      body: JSON.stringify({ clip_id: clipId }),
    }),

  removeFromQueue: (clipId: string): Promise<QueueStatusResponse> =>
    fetchJson<QueueStatusResponse>(`/admin/remove`, {
      method: 'POST',
      body: JSON.stringify({ clip_id: clipId }),
    }),

  getAcceptedClips: (): Promise<AdminClip[]> =>
    fetchJson<AdminClip[]>(`/accepted`),

  processClips: (clipIds: string[]): Promise<ProcessStatusResponse> =>
    fetchJson<ProcessStatusResponse>(`/process`, {
      method: 'POST',
      body: JSON.stringify({ clip_ids: clipIds }),
    }),

  getEmotes: (channel?: string): Promise<EmoteResponse> =>
    fetchJson<EmoteResponse>(`/emotes${channel ? `?channel=${encodeURIComponent(channel)}` : ''}`),

  searchGifs: (query: string, limit?: number): Promise<GifResponse> =>
    fetchJson<GifResponse>(`/gifs?q=${encodeURIComponent(query)}${limit ? `&limit=${limit}` : ''}`),

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
    fetchJson('/v1/ai-editor/history/save', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  getUserClipHistory: (): Promise<any> =>
    fetchJson('/v1/ai-editor/history'),

  deleteClipFromHistory: (clipId: string): Promise<any> =>
    fetchJson(`/v1/ai-editor/history/clip/${clipId}`, {
      method: 'DELETE',
    }),

  clearAllHistory: (): Promise<any> =>
    fetchJson('/v1/ai-editor/history/clear-all', {
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
