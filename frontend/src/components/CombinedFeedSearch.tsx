import React, { useCallback, useEffect, useLayoutEffect, useMemo, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import { api } from '../api/client';
import type { SearchChannel, Streamer, User } from '../types';
import { normalizeFollowSearchQuery, suggestFollowedByPrefix } from '../utils/followSearch';

const DEBOUNCE_MS = 320;
const TWITCH_QUERY_MIN_LEN = 2;

const isViteDev = (): boolean =>
  Boolean((import.meta as { env?: { DEV?: boolean } }).env?.DEV);

function isAlreadyInList(streamerId: string, streamers: Streamer[]): boolean {
  return streamers.some((s) => s.streamer_id === streamerId);
}

export type CombinedFeedSearchProps = {
  value: string;
  onChange: (next: string) => void;
  /** Feed names to show in the panel (e.g. deferred-filtered categories). */
  filteredFeeds: string[];
  currentFeed: string;
  onSelectFeed: (feedName: string) => void;
  user: User | null;
  streamers: Streamer[];
  onMergeForYou: (streamerIds: string[]) => Promise<void>;
  onRefreshFollowing?: () => Promise<void>;
  mergeBusy: boolean;
};

/**
 * One search field: pick a swipe feed (category) from the list and, when signed in,
 * add/include channels (local follows + debounced Twitch) via the same typeahead portal.
 * Keeps Twitch calls debounced and uses a ref for follow list so refreshes do not reset timers.
 */
export const CombinedFeedSearch: React.FC<CombinedFeedSearchProps> = ({
  value,
  onChange,
  filteredFeeds,
  currentFeed,
  onSelectFeed,
  user,
  streamers,
  onMergeForYou,
  onRefreshFollowing,
  mergeBusy,
}) => {
  const wrapperRef = useRef<HTMLDivElement>(null);
  const streamersRef = useRef(streamers);
  streamersRef.current = streamers;

  const [open, setOpen] = useState(false);
  const blurTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const searchTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const [panelRect, setPanelRect] = useState({ top: 0, left: 0, width: 300 });
  const [twitchResults, setTwitchResults] = useState<SearchChannel[]>([]);
  const [twitchLoading, setTwitchLoading] = useState(false);
  const [twitchError, setTwitchError] = useState<string | null>(null);
  const [pickBusy, setPickBusy] = useState(false);

  const qNorm = normalizeFollowSearchQuery(value);

  const localSuggestions = useMemo(() => {
    if (!user) return [];
    const sorted = [...suggestFollowedByPrefix(streamers, value)].sort((a, b) =>
      a.streamer_name.localeCompare(b.streamer_name, undefined, { sensitivity: 'base' }),
    );
    return sorted.slice(0, 12);
  }, [user, streamers, value]);

  const updatePanelPosition = useCallback(() => {
    const el = wrapperRef.current;
    if (!el) return;
    const r = el.getBoundingClientRect();
    const width = Math.max(r.width, Math.min(340, window.innerWidth - 16));
    const left = Math.min(r.left, window.innerWidth - width - 8);
    setPanelRect({ top: r.bottom + 8, left: Math.max(8, left), width });
  }, []);

  useLayoutEffect(() => {
    if (!open) return;
    updatePanelPosition();
  }, [open, value, updatePanelPosition]);

  useEffect(() => {
    if (!open) return;
    updatePanelPosition();
    const onReposition = () => updatePanelPosition();
    window.addEventListener('scroll', onReposition, true);
    window.addEventListener('resize', onReposition);
    return () => {
      window.removeEventListener('scroll', onReposition, true);
      window.removeEventListener('resize', onReposition);
    };
  }, [open, updatePanelPosition]);

  useEffect(() => {
    if (!user || !open || qNorm.length < TWITCH_QUERY_MIN_LEN) {
      if (searchTimer.current) clearTimeout(searchTimer.current);
      setTwitchResults([]);
      setTwitchLoading(false);
      setTwitchError(null);
      return;
    }
    setTwitchLoading(true);
    setTwitchError(null);
    if (searchTimer.current) clearTimeout(searchTimer.current);
    searchTimer.current = setTimeout(() => {
      void (async () => {
        try {
          const rows = await api.searchChannels(qNorm);
          const list = Array.isArray(rows) ? rows : [];
          const fresh = list.filter((ch) => !isAlreadyInList(ch.id, streamersRef.current));
          setTwitchResults(fresh.slice(0, 12));
        } catch (e) {
          setTwitchResults([]);
          setTwitchError(e instanceof Error ? e.message : 'Search failed');
          if (isViteDev()) console.warn('Twitch channel search failed', e);
        } finally {
          setTwitchLoading(false);
        }
      })();
    }, DEBOUNCE_MS);
    return () => {
      if (searchTimer.current) clearTimeout(searchTimer.current);
    };
  }, [user, open, qNorm]);

  useEffect(() => {
    return () => {
      if (blurTimer.current) clearTimeout(blurTimer.current);
      if (searchTimer.current) clearTimeout(searchTimer.current);
    };
  }, []);

  const closeSoon = useCallback(() => {
    blurTimer.current = setTimeout(() => setOpen(false), 200);
  }, []);

  const pickFeed = (name: string) => {
    if (name === currentFeed) {
      setOpen(false);
      onChange('');
      return;
    }
    onSelectFeed(name);
    onChange('');
    setOpen(false);
  };

  const pickLocal = async (s: Streamer) => {
    if (pickBusy || mergeBusy || !user) return;
    setPickBusy(true);
    try {
      onChange(s.streamer_name);
      await onMergeForYou([s.streamer_id]);
    } catch (e) {
      if (isViteDev()) console.warn('merge For You failed', e);
    } finally {
      setPickBusy(false);
    }
  };

  const pickTwitch = async (ch: SearchChannel) => {
    if (pickBusy || mergeBusy || !user) return;
    setPickBusy(true);
    setTwitchError(null);
    try {
      try {
        await api.addFollowing(ch.name, ch.id);
      } catch (err) {
        const msg = err instanceof Error ? err.message : String(err);
        if (!msg.includes('already')) throw err;
      }
      await onRefreshFollowing?.();
      await onMergeForYou([ch.id]);
      onChange('');
      setOpen(false);
    } catch (err) {
      setTwitchError(err instanceof Error ? err.message : 'Could not add channel');
      if (isViteDev()) console.warn('addFollowing failed', err);
    } finally {
      setPickBusy(false);
    }
  };

  // Keep the portal mounted whenever the field is focused so we can show empty states.
  const showFloating = open;
  const showTwitchHint = user && qNorm.length === 1;

  const floating =
    showFloating &&
    typeof document !== 'undefined' &&
    createPortal(
      <div
        className="combined-feed-floating for-you-picker-floating"
        style={{
          position: 'fixed',
          top: panelRect.top,
          left: panelRect.left,
          width: panelRect.width,
        }}
        role="listbox"
        aria-label="Feeds and channels"
        onMouseDown={(e) => e.preventDefault()}
      >
        <div className="combined-feed-inner for-you-picker-inner">
          <section className="for-you-picker-section" aria-label="Swipe feeds">
            <div className="for-you-picker-section-title">Feeds</div>
            {filteredFeeds.length === 0 ? (
              <p className="for-you-picker-muted combined-feed-empty">No feed matches that text.</p>
            ) : (
              <ul className="for-you-picker-ul combined-feed-feeds-ul">
                {filteredFeeds.map((name) => (
                  <li key={name}>
                    <button
                      type="button"
                      className={`combined-feed-feed-row ${currentFeed === name ? 'is-current' : ''}`}
                      onMouseDown={(e) => {
                        e.preventDefault();
                        pickFeed(name);
                      }}
                    >
                      <span className="for-you-picker-name">{name}</span>
                      {currentFeed === name && (
                        <span className="combined-feed-current-badge">Active</span>
                      )}
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </section>

          {user && qNorm.length >= 1 && localSuggestions.length > 0 && (
            <section className="for-you-picker-section" aria-label="Your follows">
              <div className="for-you-picker-section-title">Your channels</div>
              <ul className="for-you-picker-ul">
                {localSuggestions.map((s) => (
                  <li key={s.streamer_id}>
                    <button
                      type="button"
                      className="for-you-picker-row for-you-picker-row-local"
                      disabled={pickBusy || mergeBusy}
                      onMouseDown={(e) => {
                        e.preventDefault();
                        void pickLocal(s);
                      }}
                    >
                      <span className="for-you-picker-row-main">
                        <span className="for-you-picker-name">{s.streamer_name}</span>
                        {s.include_in_for_you ? (
                          <span className="for-you-picker-pill for-you-picker-pill-on">For You</span>
                        ) : (
                          <span className="for-you-picker-pill for-you-picker-pill-off">Add to For You</span>
                        )}
                      </span>
                    </button>
                  </li>
                ))}
              </ul>
            </section>
          )}

          {user && qNorm.length >= TWITCH_QUERY_MIN_LEN && (
            <section className="for-you-picker-section" aria-label="Twitch search">
              <div className="for-you-picker-section-title">Add from Twitch</div>
              {twitchLoading && <p className="for-you-picker-muted">Searching…</p>}
              {!twitchLoading && twitchError && <p className="for-you-picker-error">{twitchError}</p>}
              {!twitchLoading && !twitchError && twitchResults.length === 0 && (
                <p className="for-you-picker-muted">No channels found (or already saved).</p>
              )}
              {!twitchLoading && twitchResults.length > 0 && (
                <ul className="for-you-picker-ul">
                  {twitchResults.map((ch) => (
                    <li key={ch.id}>
                      <button
                        type="button"
                        className="for-you-picker-row for-you-picker-row-twitch"
                        disabled={pickBusy || mergeBusy}
                        onMouseDown={(e) => {
                          e.preventDefault();
                          void pickTwitch(ch);
                        }}
                      >
                        <span className="for-you-picker-row-main">
                          <span className="for-you-picker-name">{ch.name}</span>
                          {ch.is_live && <span className="for-you-picker-live">LIVE</span>}
                        </span>
                        <span className="for-you-picker-meta">
                          {ch.game_name ? `${ch.game_name} · ` : ''}
                          Save + For You
                        </span>
                      </button>
                    </li>
                  ))}
                </ul>
              )}
            </section>
          )}

          {showTwitchHint && streamers.length > 0 && localSuggestions.length === 0 && (
            <p className="for-you-picker-muted for-you-picker-hint-only">
              No saved channel matches. Type another letter to search Twitch.
            </p>
          )}

          {showTwitchHint && streamers.length === 0 && (
            <p className="for-you-picker-muted for-you-picker-hint-only">
              Type {TWITCH_QUERY_MIN_LEN}+ letters to search Twitch and save a channel.
            </p>
          )}
        </div>
      </div>,
      document.body,
    );

  return (
    <>
      <div className="combined-feed-search-wrap follow-search-combo" ref={wrapperRef}>
        <label className="feed-search-label combined-feed-label" htmlFor="combined-feed-search">
          <span className="streamer-picker-label">Find a feed or channel</span>
          <input
            id="combined-feed-search"
            type="search"
            inputMode="search"
            enterKeyHint="search"
            autoComplete="off"
            className="feed-search-input combined-feed-input"
            placeholder={
              user
                ? 'Feeds, games, or channel name…'
                : 'Search feeds and games…'
            }
            value={value}
            disabled={pickBusy}
            aria-expanded={open}
            aria-controls={undefined}
            onChange={(e) => {
              onChange(e.target.value);
              setOpen(true);
            }}
            onFocus={() => {
              if (blurTimer.current) {
                clearTimeout(blurTimer.current);
                blurTimer.current = null;
              }
              setOpen(true);
            }}
            onBlur={() => closeSoon()}
          />
        </label>
        {(pickBusy || mergeBusy) && <span className="for-you-picker-input-busy" aria-hidden />}
      </div>
      {floating}
    </>
  );
};
