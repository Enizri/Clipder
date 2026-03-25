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

export interface Comment {
  user: string;
  text: string;
  timestamp: string;
}

export interface LeaderboardClip extends Clip {}

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

export interface QueueStatusResponse {
  status: string;
}

export interface ProcessStatusResponse {
  status: string;
}

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

export interface GifItem {
  id: string;
  title: string;
  url: string;
  preview: string;
  width: string;
  height: string;
}

export interface GifResponse {
  gifs: GifItem[];
}

// Auth types
export interface User {
  id: number;
  username: string;
  email: string;
  role: string;
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
