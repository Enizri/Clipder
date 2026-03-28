// Module-level cache: video URLs persist across re-renders and SPA navigations.
// Keyed by clip ID (string).
export const videoUrlCache: Record<string, string> = {};
