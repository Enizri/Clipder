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

async function fetchJson<T>(url: string, options?: RequestInit): Promise<T> {
  const response = await fetch(url, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
  });
  if (!response.ok) {
    throw new Error(`API Error: ${response.status}`);
  }
  return response.json();
}

export const api = {
  getClips: (category: string = 'My Streamers'): Promise<ClipsResponse> =>
    fetchJson<ClipsResponse>(`${API_BASE}/clips?category=${encodeURIComponent(category)}`),

  getCategories: (): Promise<{ categories: string[] }> =>
    fetchJson(`${API_BASE}/categories`),

  getVideoUrl: (clipId: string): Promise<VideoUrlResponse> =>
    fetchJson<VideoUrlResponse>(`${API_BASE}/clip/${clipId}/video-url`),

  likeClip: (clipId: string): Promise<ClipActionResponse> =>
    fetchJson<ClipActionResponse>(`${API_BASE}/clip/${clipId}/action`, {
      method: 'POST',
      body: JSON.stringify({ action: 'like' }),
    }),

  dislikeClip: (clipId: string): Promise<ClipActionResponse> =>
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
};
