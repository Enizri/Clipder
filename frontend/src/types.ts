// ==============================================================================
// CLIP TYPES
// ==============================================================================

export interface Clip {
  id: string;
  title: string;
  url: string;
  thumbnail_url: string;
  view_count: number;
  creator_name: string;
  duration: number;
  created_at: string;
  channel: string;
  local_likes: number;
  comment_count: number;
}

export interface ClipsResponse {
  clips: Clip[];
  total: number;
}

export interface VideoUrlResponse {
  video_url?: string;
  title?: string;
  error?: string;
}

export interface ClipActionResponse {
  status: string;
  current_score: number;
}

// Clip as stored in the AI editor queue (no duration/channel fields from the swipe feed)
export interface AdminClip {
  id: string;
  title: string;
  url: string;
  thumbnail_url: string;
  view_count: number;
  creator_name: string;
  duration: number;
  created_at: string;
  channel: string;
}

// ==============================================================================
// LEADERBOARD TYPES
// ==============================================================================

// Shape returned by the /leaderboard WebSocket and REST endpoint
export interface LeaderboardEntry {
  rank: number;
  clip_id: number;
  score: number;
  likes: number;
  title: string;
  creator: string;
  thumbnail_url: string;
}

// ==============================================================================
// COMMENT TYPES
// ==============================================================================

export interface Comment {
  user: string;
  text: string;
  timestamp: string;
}

// ==============================================================================
// EMOTE TYPES
// ==============================================================================

export interface EmoteItem {
  code: string;
  id: string;
  url: string;
}

export interface EmoteResponse {
  twitch: EmoteItem[];
  bttv: EmoteItem[];
  seventv: EmoteItem[];
  channel: EmoteItem[];
}

// ==============================================================================
// AUTH TYPES
// ==============================================================================

export interface User {
  id: number;
  username: string;
  email: string;
  role: 'USER' | 'PRO' | 'ADMIN';
  twitch_id: string | null;
  twitch_username: string | null;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  user: User;
}

export interface TwitchLoginResponse {
  authorization_url: string;
}

// ==============================================================================
// FOLLOWING / STREAMER TYPES
// ==============================================================================

export interface Streamer {
  id: number;
  streamer_name: string;
  streamer_id: string;
}

export interface TwitchFollow {
  to_id: string;
  to_name: string;
}

export interface SearchChannel {
  id: string;
  name: string;
  game_name: string;
  is_live: boolean;
}

// ==============================================================================
// MISC
// ==============================================================================

export interface QueueStatusResponse {
  status: string;
}

export interface ProcessStatusResponse {
  status: string;
}
