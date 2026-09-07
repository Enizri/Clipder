import type { Clip, User } from '../types';

export const DEMO_USER: User = {
  id: 0,
  username: 'demo',
  role: 'USER',
  is_pro: false,
  twitch_id: null,
  twitch_username: 'clipder-demo',
};

const DEMO_FLAG = 'clipder-demo-mode';

export function isDemoMode(): boolean {
  if (typeof window === 'undefined') return false;
  if (new URLSearchParams(window.location.search).get('demo') === '1') {
    sessionStorage.setItem(DEMO_FLAG, '1');
    return true;
  }
  return sessionStorage.getItem(DEMO_FLAG) === '1';
}

const QUEUE_KEY = 'clipder-demo-queue';

declare global {
  interface Window {
    /** clip id -> playable MP4 URL. */
    __clipderDemoVideos?: Record<string, string>;
  }
}

/**
 * Twitch serves clip MP4s from signed CDN URLs that expire within a day, so they cannot be
 * committed here. The GIF recorder resolves fresh ones at capture time and injects them; without
 * that injection the demo simply shows thumbnails.
 */
export function getDemoVideoUrl(clipId: string): string | null {
  if (typeof window === 'undefined') return null;
  return window.__clipderDemoVideos?.[clipId] ?? null;
}

/** Public Twitch clip pages + CDN thumbnails used as the demo feed. */
export const DEMO_CLIPS: Clip[] = [
  {
    id: 'SeductivePerfectClipsdadOneHand-QDHtFh3QBebzcPAV',
    title: 'Clip for Anna',
    url: 'https://clips.twitch.tv/SeductivePerfectClipsdadOneHand-QDHtFh3QBebzcPAV',
    thumbnail_url:
      'https://static-cdn.jtvnw.net/twitch-video-assets/twitch-vap-video-assets-prod-us-west-2/a6e7ed85-74fe-44b9-8b9f-cc1428cb811a/landscape/thumb/thumb-0000000000-1920x1080.jpg',
    view_count: 184200,
    creator_name: 'xAnnaGrace',
    duration: 28,
    created_at: '2024-11-02T18:22:00Z',
    channel: 'xannagrace',
    local_likes: 12,
    comment_count: 4,
  },
  {
    id: 'SpotlessEnthusiasticNeanderthalStoneLightning-aan-npvFhj14Jd-O',
    title: 'holy aim',
    url: 'https://clips.twitch.tv/SpotlessEnthusiasticNeanderthalStoneLightning-aan-npvFhj14Jd-O',
    thumbnail_url:
      'https://static-cdn.jtvnw.net/twitch-video-assets/twitch-vap-video-assets-prod-us-west-2/97cfcf2b-c42f-46e3-bd97-0877c5963a40/landscape/thumb/thumb-0000000000-1920x1080.jpg',
    view_count: 795,
    creator_name: 'aceu',
    duration: 9,
    created_at: '2026-09-04T05:04:52Z',
    channel: 'aceu',
    local_likes: 8,
    comment_count: 2,
  },
  {
    id: 'SourHilariousFishPeteZaroll-c13qZ1aGXTzxWz-e',
    title: 'Stax + Zest INSTANT 2v4 vs FPX',
    url: 'https://clips.twitch.tv/SourHilariousFishPeteZaroll-c13qZ1aGXTzxWz-e',
    thumbnail_url:
      'https://static-cdn.jtvnw.net/twitch-video-assets/twitch-vap-video-assets-prod-us-west-2/bfe6497f-e31b-4d6d-b7f2-af5158552b66/landscape/thumb/thumb-0000000000-1920x1080.jpg',
    view_count: 241000,
    creator_name: 'tarik',
    duration: 34,
    created_at: '2024-09-09T14:11:00Z',
    channel: 'tarik',
    local_likes: 31,
    comment_count: 9,
  },
];

export function readDemoQueue(): Clip[] {
  try {
    const raw = sessionStorage.getItem(QUEUE_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

export function pushDemoQueue(clip: Clip): void {
  const next = [clip, ...readDemoQueue().filter((c) => c.id !== clip.id)];
  sessionStorage.setItem(QUEUE_KEY, JSON.stringify(next));
}

export function removeDemoQueue(clipId: string): void {
  sessionStorage.setItem(
    QUEUE_KEY,
    JSON.stringify(readDemoQueue().filter((c) => c.id !== clipId)),
  );
}
