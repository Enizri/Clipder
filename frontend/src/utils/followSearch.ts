import type { Streamer } from '../types';

/** Trim, lowercase, strip leading @ for matching Twitch-style input. */
export function normalizeFollowSearchQuery(raw: string): string {
  return raw.trim().toLowerCase().replace(/^@+/, '');
}

/**
 * Prefix matches first; if none, fall back to substring so mid-name search still surfaces rows.
 * Empty query returns the full list (same order as input).
 */
export function filterFollowedStreamersByPrefix(streamers: Streamer[], rawQuery: string): Streamer[] {
  const q = normalizeFollowSearchQuery(rawQuery);
  if (!q) return streamers;
  const nameLc = (s: Streamer) => (s.streamer_name ?? '').trim().toLowerCase();
  const byPrefix = streamers.filter((s) => nameLc(s).startsWith(q));
  if (byPrefix.length > 0) return byPrefix;
  return streamers.filter((s) => nameLc(s).includes(q));
}

/** Suggestions: prefix-only (for the dropdown while typing). */
export function suggestFollowedByPrefix(streamers: Streamer[], rawQuery: string): Streamer[] {
  const q = normalizeFollowSearchQuery(rawQuery);
  if (!q) return [];
  return streamers.filter((s) =>
    (s.streamer_name ?? '').trim().toLowerCase().startsWith(q),
  );
}
