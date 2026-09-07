import React, { useCallback, useEffect, useLayoutEffect, useMemo, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import { api } from '../api/client';
import type { SearchChannel, Streamer } from '../types';
import { normalizeFollowSearchQuery, suggestFollowedByPrefix } from '../utils/followSearch';

const DEBOUNCE_MS = 320;
const TWITCH_QUERY_MIN_LEN = 2;

const isViteDev = (): boolean =>
  Boolean((import.meta as { env?: { DEV?: boolean } }).env?.DEV);

function isAlreadyInList(streamerId: string, streamers: Streamer[]): boolean {
  return streamers.some((s) => s.streamer_id === streamerId);
}

export type ForYouChannelPickerProps = {
  value: string;
  onChange: (next: string) => void;
  streamers: Streamer[];
  /**
   * Merge IDs into the user's For You selection using fresh /following data
   * (pages implement this with GET then PUT /following/for-you).
   */
  onMergeForYou: (streamerIds: string[]) => Promise<void>;
  /** Reload follows from the server after POST /following (new Twitch pick). */
  onRefreshFollowing?: () => Promise<void>;
  disabled?: boolean;
  busy?: boolean;
  placeholder?: string;
  ariaLabel?: string;
};

/**
 / Combined typeahead: local follows (prefix) + Twitch Helix search (debounced),
 * rendered in a fixed portal so parent overflow cannot clip the menu.
 */
export const ForYouChannelPicker: React.FC<ForYouChannelPickerProps> = ({
  value,
  onChange,
  streamers,
  onMergeForYou,
  onRefreshFollowing,
  disabled = false,
  busy = false,
  placeholder = 'Type a channel name…',
  ariaLabel = 'Search channels for For You',
}) => {
  const wrapperRef = useRef<HTMLDivElement>(null);
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
    const sorted = [...suggestFollowedByPrefix(streamers, value)].sort((a, b) =>
      a.streamer_name.localeCompare(b.streamer_name, undefined, { sensitivity: 'base' }),
    );
    return sorted.slice(0, 12);
  }, [streamers, value]);

  const updatePanelPosition = useCallback(() => {
    const el = wrapperRef.current;
    if (!el) return;
    const r = el.getBoundingClientRect();
    const width = Math.max(r.width, Math.min(320, window.innerWidth - 16));
    const left = Math.min(r.left, window.innerWidth - width - 8);
    setPanelRect({ top: r.bottom + 6, left: Math.max(8, left), width });
  }, []);

  useLayoutEffect(() => {
    if (!open || qNorm.length < 1 || disabled) return;
    updatePanelPosition();
  }, [open, qNorm.length, disabled, value, updatePanelPosition]);

  useEffect(() => {
    if (!open || qNorm.length < 1) return;
    updatePanelPosition();
    const onReposition = () => updatePanelPosition();
    window.addEventListener('scroll', onReposition, true);
    window.addEventListener('resize', onReposition);
    return () => {
      window.removeEventListener('scroll', onReposition, true);
      window.removeEventListener('resize', onReposition);
    };
  }, [open, qNorm.length, updatePanelPosition]);

  useEffect(() => {
    if (searchTimer.current) clearTimeout(searchTimer.current);
    if (qNorm.length < TWITCH_QUERY_MIN_LEN) {
      setTwitchResults([]);
      setTwitchLoading(false);
      setTwitchError(null);
      return;
    }
    setTwitchLoading(true);
    setTwitchError(null);
    searchTimer.current = setTimeout(() => {
      void (async () => {
        try {
          const rows = await api.searchChannels(qNorm);
          const list = Array.isArray(rows) ? rows : [];
          const fresh = list.filter((ch) => !isAlreadyInList(ch.id, streamers));
          setTwitchResults(fresh.slice(0, 15));
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
  }, [qNorm, streamers]);

  useEffect(() => {
    return () => {
      if (blurTimer.current) clearTimeout(blurTimer.current);
      if (searchTimer.current) clearTimeout(searchTimer.current);
    };
  }, []);

  const pickLocal = async (s: Streamer) => {
    if (pickBusy || busy || disabled) return;
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
    if (pickBusy || busy || disabled) return;
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
      onChange(ch.name);
      setOpen(false);
    } catch (err) {
      setTwitchError(err instanceof Error ? err.message : 'Could not add channel');
      if (isViteDev()) console.warn('addFollowing failed', err);
    } finally {
      setPickBusy(false);
    }
  };

  const showFloating = open && !disabled && qNorm.length >= 1;
  const showTwitchHint = qNorm.length === 1;

  const floating = showFloating && (
    <div
      className="for-you-picker-floating"
      style={{
        position: 'fixed',
        top: panelRect.top,
        left: panelRect.left,
        width: panelRect.width,
      }}
      role="presentation"
      onMouseDown={(e) => e.preventDefault()}
    >
      <div className="for-you-picker-inner">
        {localSuggestions.length > 0 && (
          <section className="for-you-picker-section" aria-label="Your follows">
            <div className="for-you-picker-section-title">Your follows</div>
            <ul className="for-you-picker-ul">
              {localSuggestions.map((s) => (
                <li key={s.streamer_id}>
                  <button
                    type="button"
                    className="for-you-picker-row for-you-picker-row-local"
                    disabled={pickBusy || busy}
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

        {qNorm.length >= TWITCH_QUERY_MIN_LEN && (
          <section className="for-you-picker-section" aria-label="Twitch search">
            <div className="for-you-picker-section-title">Add from Twitch</div>
            {twitchLoading && <p className="for-you-picker-muted">Searching…</p>}
            {!twitchLoading && twitchError && (
              <p className="for-you-picker-error">{twitchError}</p>
            )}
            {!twitchLoading && !twitchError && twitchResults.length === 0 && (
              <p className="for-you-picker-muted">No channels found (or already in your list).</p>
            )}
            {!twitchLoading && twitchResults.length > 0 && (
              <ul className="for-you-picker-ul">
                {twitchResults.map((ch) => (
                  <li key={ch.id}>
                    <button
                      type="button"
                      className="for-you-picker-row for-you-picker-row-twitch"
                      disabled={pickBusy || busy}
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
                        {ch.game_name ? `${ch.game_name} · ` : ''}Add to your list and For You
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
            No saved follow starts with that. Type one more letter to search Twitch.
          </p>
        )}

        {showTwitchHint && streamers.length === 0 && (
          <p className="for-you-picker-muted for-you-picker-hint-only">
            Type {TWITCH_QUERY_MIN_LEN}+ letters to search Twitch and add channels to your account.
          </p>
        )}

      </div>
    </div>
  );

  return (
    <>
      <div className="follow-search-combo for-you-channel-picker" ref={wrapperRef}>
        <input
          type="text"
          inputMode="search"
          enterKeyHint="search"
          autoComplete="off"
          className="for-you-search"
          placeholder={placeholder}
          value={value}
          disabled={disabled || busy}
          aria-label={ariaLabel}
          aria-expanded={showFloating}
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
          onBlur={() => {
            blurTimer.current = setTimeout(() => setOpen(false), 220);
          }}
        />
        {(pickBusy || busy) && <span className="for-you-picker-input-busy" aria-hidden />}
      </div>
      {typeof document !== 'undefined' && floating ? createPortal(floating, document.body) : null}
    </>
  );
};
