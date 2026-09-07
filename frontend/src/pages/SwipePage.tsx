import React, { useState, useEffect, useRef, useCallback, useMemo, useTransition, useDeferredValue } from 'react';
import { api } from '../api/client';
import { ClipPreview } from '../components/ClipPreview';
import { CombinedFeedSearch } from '../components/CombinedFeedSearch';
import { TwitchAuthWall } from '../components/TwitchAuthWall';
import { videoUrlCache } from '../utils/videoCache';
import { filterFollowedStreamersByPrefix, normalizeFollowSearchQuery } from '../utils/followSearch';
import { TheaterMode } from '../components/TheaterMode';
import type { Clip, User, Streamer } from '../types';
import { DEMO_CLIPS, isDemoMode, pushDemoQueue } from '../demo/demoClips';

const GUEST_SWIPE_LIMIT = 15;

const isViteDev = (): boolean =>
  Boolean((import.meta as { env?: { DEV?: boolean } }).env?.DEV);

const getGuestSwipeCount = (): number => {
  try {
    return parseInt(localStorage.getItem('guestSwipeCount') || '0', 10);
  } catch {
    return 0;
  }
};

const incrementGuestSwipeCount = (): number => {
  const next = getGuestSwipeCount() + 1;
  localStorage.setItem('guestSwipeCount', String(next));
  return next;
};

// ==============================================================================
// SEEN CLIP PERSISTENCE
// ==============================================================================

const getSeenClipIds = (): Set<string> => {
  try {
    const stored = localStorage.getItem('seenClipIds');
    if (!stored) return new Set();
    const parsed = JSON.parse(stored);
    if (!Array.isArray(parsed)) {
      localStorage.removeItem('seenClipIds');
      return new Set();
    }
    return new Set(parsed);
  } catch {
    localStorage.removeItem('seenClipIds');
    return new Set();
  }
};

const addSeenClipId = (clipId: string) => {
  const seen = getSeenClipIds();
  seen.add(clipId);
  localStorage.setItem('seenClipIds', JSON.stringify([...seen]));
};

// ==============================================================================
// COMPONENT
// ==============================================================================

interface SwipePageProps {
  user: User | null;
  onOpenComments: (clipId: string, title: string) => void;
}

export const SwipePage: React.FC<SwipePageProps> = ({ user, onOpenComments }) => {
  const [clips, setClips] = useState<Clip[]>([]);
  const [currentIndex, setCurrentIndex] = useState(0);
  // Tracks whether the guest hit the swipe wall (shown as hard block)
  const [showAuthWall, setShowAuthWall] = useState(false);
  const [categories, setCategories] = useState<string[]>(['My Streamers', 'For You']);
  const [currentCategory, setCurrentCategory] = useState('My Streamers');
  const [followedStreamers, setFollowedStreamers] = useState<Streamer[]>([]);
  /** Twitch game name for My Streamers (explore) mode. */
  const [exploreGame, setExploreGame] = useState<string>('');
  const [forYouPrefsVersion, setForYouPrefsVersion] = useState(0);
  const [forYouSaving, setForYouSaving] = useState(false);
  const [loading, setLoading] = useState(true);
  const [feedSearch, setFeedSearch] = useState('');
  const [, startFeedTransition] = useTransition();
  const [rejectHighlight, setRejectHighlight] = useState(false);
  const [acceptHighlight, setAcceptHighlight] = useState(false);
  const [swipeDirection, setSwipeDirection] = useState<'left' | 'right' | null>(null);
  const [leavingDirection, setLeavingDirection] = useState<'left' | 'right' | null>(null);
  const [theaterSrc, setTheaterSrc] = useState<string | null>(null);
  const [theaterLoading, setTheaterLoading] = useState(false);

  const cardRef = useRef<HTMLDivElement>(null);
  /** Tracks feed identity (category + explore game) to avoid full-page loading on For You checkbox-only saves. */
  const prevClipOptsKeyRef = useRef<string | null>(null);
  const isDragging = useRef(false);
  const startX = useRef(0);
  const currentX = useRef(0);
  const isSwiping = useRef(false);

  // ---------------------------------------------------------------------------
  // Data loading
  // ---------------------------------------------------------------------------

  useEffect(() => {
    api
      .getCategories()
      .then((data) => {
        const rest = Array.isArray(data.categories) ? data.categories : [];
        setCategories(['My Streamers', 'For You', ...rest]);
      })
      .catch(() => {
        // Categories failed — default stays in place
      });
  }, []);

  useEffect(() => {
    if (!user) {
      setFollowedStreamers([]);
      return;
    }
    api
      .getFollowing()
      .then((rows) => setFollowedStreamers(Array.isArray(rows) ? rows : []))
      .catch((err) => {
        if (isViteDev()) console.warn('Could not load followed streamers', err);
      });
  }, [user]);

  const gameCategories = useMemo(
    () => categories.filter((c) => c !== 'My Streamers' && c !== 'For You'),
    [categories]
  );

  useEffect(() => {
    if (gameCategories.length === 0) return;
    setExploreGame((prev) => (prev && gameCategories.includes(prev) ? prev : gameCategories[0]));
  }, [gameCategories]);

  const clipRequestOpts = useMemo(() => {
    if (currentCategory === 'My Streamers') {
      return {
        category: 'My Streamers' as const,
        exploreCategory: exploreGame || undefined,
      };
    }
    return { category: currentCategory };
  }, [currentCategory, exploreGame]);

  /**
   * Persist For You checkbox set. Use `silent: true` for single toggles so the list stays
   * interactive and the swipe stack does not show the full loading screen.
   */
  const persistForYouIds = async (ids: string[], opts?: { silent?: boolean }) => {
    if (!user) return;
    const silent = Boolean(opts?.silent);
    const idSet = new Set(ids);
    if (silent) {
      setFollowedStreamers((prev) =>
        prev.map((row) => ({ ...row, include_in_for_you: idSet.has(row.streamer_id) })),
      );
    } else {
      setForYouSaving(true);
    }
    try {
      await api.setForYouStreamers(ids);
      const rows = await api.getFollowing();
      setFollowedStreamers(Array.isArray(rows) ? rows : []);
      setForYouPrefsVersion((v) => v + 1);
    } catch (err) {
      if (isViteDev()) console.warn('For You preferences failed', err);
      try {
        const rows = await api.getFollowing();
        setFollowedStreamers(Array.isArray(rows) ? rows : []);
      } catch {
        /* leave optimistic state if refresh fails */
      }
    } finally {
      if (!silent) setForYouSaving(false);
    }
  };

  /** Merge IDs into For You after a fresh GET — avoids stale state after POST /following. */
  const mergeForYouInclude = async (idsToInclude: string[]) => {
    if (!user) return;
    setForYouSaving(true);
    try {
      const rows = await api.getFollowing();
      const list = Array.isArray(rows) ? rows : [];
      const base = new Set(list.filter((x) => x.include_in_for_you).map((x) => x.streamer_id));
      idsToInclude.forEach((id) => base.add(id));
      await api.setForYouStreamers([...base]);
      const rows2 = await api.getFollowing();
      setFollowedStreamers(Array.isArray(rows2) ? rows2 : []);
      setForYouPrefsVersion((v) => v + 1);
    } catch (err) {
      if (isViteDev()) console.warn('For You merge failed', err);
    } finally {
      setForYouSaving(false);
    }
  };

  const refreshFollowingOnly = async () => {
    const rows = await api.getFollowing();
    setFollowedStreamers(Array.isArray(rows) ? rows : []);
  };

  const stopAllVideos = useCallback(() => {
    document.querySelectorAll<HTMLVideoElement>('.clip-preview video').forEach((v) => {
      v.pause();
      v.currentTime = 0;
    });
  }, []);

  const deferredFeedSearch = useDeferredValue(feedSearch);
  const filteredFeedCategories = useMemo(() => {
    const q = normalizeFollowSearchQuery(deferredFeedSearch);
    if (!q) return categories;
    return categories.filter((c) => c.toLowerCase().includes(q));
  }, [categories, deferredFeedSearch]);

  const forYouFiltered = useMemo(
    () => filterFollowedStreamersByPrefix(followedStreamers, deferredFeedSearch),
    [followedStreamers, deferredFeedSearch],
  );

  const handleSelectFeedFromSearch = useCallback(
    (feedName: string) => {
      if (feedName === currentCategory) return;
      stopAllVideos();
      startFeedTransition(() => {
        setClips([]);
        setCurrentIndex(0);
        setCurrentCategory(feedName);
      });
    },
    [currentCategory, stopAllVideos, startFeedTransition],
  );

  useEffect(() => {
    if (isDemoMode()) {
      setClips(DEMO_CLIPS);
      setCurrentIndex(0);
      setLoading(false);
      return;
    }

    const optsKey = JSON.stringify(clipRequestOpts);
    const isFirst = prevClipOptsKeyRef.current === null;
    const categoryOrExploreChanged = isFirst || prevClipOptsKeyRef.current !== optsKey;
    prevClipOptsKeyRef.current = optsKey;

    if (categoryOrExploreChanged) {
      setLoading(true);
    }

    const excludeClipIds = [...getSeenClipIds()];
    let cancelled = false;
    api
      .getClips({ ...clipRequestOpts, excludeClipIds })
      .then((data) => {
        if (cancelled) return;
        const apply = () => {
          if (!data?.clips || !Array.isArray(data.clips)) {
            setClips([]);
            return;
          }
          setClips(data.clips);
          setCurrentIndex(0);
        };
        if (categoryOrExploreChanged) {
          apply();
        } else {
          startFeedTransition(apply);
        }
      })
      .catch((err) => {
        if (cancelled) return;
        if (isViteDev()) console.warn('getClips failed', err);
        setClips([]);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [clipRequestOpts, forYouPrefsVersion]);

  // ---------------------------------------------------------------------------
  // Helpers
  // ---------------------------------------------------------------------------

  const formatViews = (views: number) =>
    views >= 1000 ? `${(views / 1000).toFixed(1)}K` : String(views);

  // ---------------------------------------------------------------------------
  // Theater mode
  // ---------------------------------------------------------------------------

  const openTheaterMode = async (clipId: string) => {
    setTheaterLoading(true);
    try {
      const data = await api.getVideoUrl(clipId);
      if (data.video_url) setTheaterSrc(data.video_url);
    } catch {
      // Theater load failed — user stays on card
    } finally {
      setTheaterLoading(false);
    }
  };

  const closeTheaterMode = () => setTheaterSrc(null);

  // ---------------------------------------------------------------------------
  // Swipe logic
  // ---------------------------------------------------------------------------

  const handleSwipe = useCallback(
    async (direction: 'left' | 'right') => {
      if (isSwiping.current) return;
      const currentClip = clips[currentIndex];
      if (!currentClip) return;

      isSwiping.current = true;
      setLeavingDirection(direction);
      stopAllVideos();

      setTimeout(() => {
        addSeenClipId(currentClip.id);

        // Prefetch next clip's video
        const nextClip = clips[currentIndex + 1];
        if (!isDemoMode() && nextClip && !videoUrlCache[nextClip.id]) {
          api.getVideoUrl(nextClip.id).then((data) => {
            if (data.video_url) videoUrlCache[nextClip.id] = data.video_url;
          }).catch(() => {});
        }

        if (user) {
          if (direction === 'right') {
            if (isDemoMode()) {
              pushDemoQueue(currentClip);
            } else {
              api.likeClip(currentClip.id).catch(() => {});
            }
          } else if (!isDemoMode()) {
            api.dislikeClip(currentClip.id).catch(() => {});
          }
        } else {
          // Guest — ghost swipe (no API call), track count for auth wall
          const count = incrementGuestSwipeCount();
          if (count >= GUEST_SWIPE_LIMIT) {
            setShowAuthWall(true);
          }
        }

        const newIndex = currentIndex + 1;
        if (!isDemoMode() && newIndex >= clips.length - 2) {
          api
            .getClips({ ...clipRequestOpts, excludeClipIds: [...getSeenClipIds()] })
            .then((data) => {
              const seenIds = getSeenClipIds();
              const fresh = data.clips.filter((c) => !seenIds.has(c.id));
              if (fresh.length > 0) {
                setClips((prev) => [...prev.filter((c) => !seenIds.has(c.id)), ...fresh]);
              }
            })
            .catch((err) => {
              if (isViteDev()) console.warn('Prefetch clips failed', err);
            });
        }

        setCurrentIndex(newIndex);
        setLeavingDirection(null);
        setSwipeDirection(null);
        isSwiping.current = false;
      }, 320);
    },
    [clips, currentIndex, stopAllVideos, user, clipRequestOpts]
  );

  // ---------------------------------------------------------------------------
  // Drag (mouse + touch)
  // ---------------------------------------------------------------------------

  const handleMouseDown = (e: React.MouseEvent | React.TouchEvent) => {
    if (isSwiping.current) return;
    const target = e.target as HTMLElement;
    if (
      target.closest(
        '.volume-control, .fullscreen-btn, .play-pause-btn, .progress-container, .clip-info, button, .for-you-panel, .streamer-picker, .combined-feed-search-wrap'
      )
    )
      return;
    isDragging.current = true;
    startX.current = 'touches' in e ? e.touches[0].clientX : e.clientX;
    currentX.current = startX.current;
    cardRef.current?.classList.add('dragging');
    stopAllVideos();
  };

  const handleMouseMove = useCallback(
    (e: MouseEvent | TouchEvent) => {
      if (!isDragging.current || !cardRef.current) return;
      if ('preventDefault' in e) e.preventDefault();
      const clientX = 'touches' in e ? e.touches[0].clientX : e.clientX;
      currentX.current = clientX;
      const deltaX = clientX - startX.current;
      cardRef.current.style.transform = `translate(${deltaX}px,0) rotate(${deltaX * 0.03}deg)`;

      const threshold = 50;
      const getHint = (sel: string) =>
        cardRef.current?.querySelector(`.swipe-hint.${sel}`) as HTMLElement | null;

      if (deltaX < -threshold) {
        setRejectHighlight(true);
        setAcceptHighlight(false);
        const hint = getHint('left');
        if (hint) {
          const p = Math.min(1.5, (Math.abs(deltaX) - threshold) / 100);
          hint.style.transform = `scale(${0.5 + p * 0.7})`;
          hint.style.opacity = String(p);
        }
      } else if (deltaX > threshold) {
        setAcceptHighlight(true);
        setRejectHighlight(false);
        const hint = getHint('right');
        if (hint) {
          const p = Math.min(1.5, (deltaX - threshold) / 100);
          hint.style.transform = `scale(${0.5 + p * 0.7})`;
          hint.style.opacity = String(p);
        }
      } else {
        setRejectHighlight(false);
        setAcceptHighlight(false);
        ['left', 'right'].forEach((side) => {
          const hint = getHint(side);
          if (hint) {
            hint.style.opacity = '0';
            hint.style.transform = 'scale(0.5)';
          }
        });
      }
    },
    []
  );

  const handleMouseUp = useCallback(() => {
    if (!isDragging.current || !cardRef.current) return;
    isDragging.current = false;
    cardRef.current.classList.remove('dragging');

    const deltaX = currentX.current - startX.current;
    setRejectHighlight(false);
    setAcceptHighlight(false);

    ['left', 'right'].forEach((side) => {
      const hint = cardRef.current?.querySelector(`.swipe-hint.${side}`) as HTMLElement | null;
      if (hint) {
        hint.style.opacity = '0';
        hint.style.transform = 'scale(0.5)';
      }
    });

    if (Math.abs(deltaX) > 100) {
      cardRef.current.classList.remove('top-card');
      handleSwipe(deltaX > 0 ? 'right' : 'left');
    } else {
      cardRef.current.style.transform = '';
    }
  }, [handleSwipe]);

  useEffect(() => {
    document.addEventListener('mousemove', handleMouseMove);
    document.addEventListener('mouseup', handleMouseUp);
    document.addEventListener('touchmove', handleMouseMove, { passive: false });
    document.addEventListener('touchend', handleMouseUp);
    return () => {
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
      document.removeEventListener('touchmove', handleMouseMove);
      document.removeEventListener('touchend', handleMouseUp);
    };
  }, [handleMouseMove, handleMouseUp]);

  // ---------------------------------------------------------------------------
  // Render
  // ---------------------------------------------------------------------------

  const visibleClips = useMemo(
    () => clips.slice(currentIndex, Math.min(currentIndex + 3, clips.length)),
    [clips, currentIndex]
  );

  return (
    <>
      {/* Hard auth block after 15 guest swipes */}
      {showAuthWall && <TwitchAuthWall />}

      <TheaterMode src={theaterSrc} loading={theaterLoading} onClose={closeTheaterMode} />

      <div id="swipe" className="view-section active">
        <div className="swipe-layout">
          {/* LEFT SIDEBAR — category picker */}
          <div className="swipe-sidebar">
            <div className="streamers-section">
              <h4>Currently viewing</h4>
              <p className="current-category-label">{currentCategory}</p>

              <CombinedFeedSearch
                value={feedSearch}
                onChange={setFeedSearch}
                filteredFeeds={filteredFeedCategories}
                currentFeed={currentCategory}
                onSelectFeed={handleSelectFeedFromSearch}
                user={user}
                streamers={followedStreamers}
                onMergeForYou={mergeForYouInclude}
                onRefreshFollowing={refreshFollowingOnly}
                mergeBusy={forYouSaving}
              />
              <p className="streamer-picker-hint combined-feed-hint">
                Open the search box to switch feeds or {user ? 'add channels to your list.' : 'browse game tabs.'}
              </p>

              {currentCategory === 'My Streamers' && gameCategories.length > 0 && (
                <label className="streamer-picker">
                  <span className="streamer-picker-label">Explore category</span>
                  <select
                    className="streamer-picker-select"
                    value={exploreGame}
                    onChange={(e) => {
                      stopAllVideos();
                      startFeedTransition(() => {
                        setClips([]);
                        setCurrentIndex(0);
                        setExploreGame(e.target.value);
                      });
                    }}
                  >
                    {gameCategories.map((g) => (
                      <option key={g} value={g}>
                        {g}
                      </option>
                    ))}
                  </select>
                </label>
              )}

              {currentCategory === 'For You' && (
                <div className="for-you-panel">
                  {!user && (
                    <p className="streamer-picker-hint">Sign in to build a For You feed from your Twitch follows.</p>
                  )}
                  {user && (
                    <>
                      <div className="for-you-toolbar for-you-toolbar-compact">
                        <button
                          type="button"
                          className="for-you-select-all"
                          disabled={forYouSaving || followedStreamers.length === 0}
                          onClick={() =>
                            void persistForYouIds(followedStreamers.map((s) => s.streamer_id))
                          }
                        >
                          Select all for For You
                        </button>
                      </div>
                      {forYouSaving && <p className="for-you-saving">Saving selection…</p>}
                      {followedStreamers.length === 0 && (
                        <p className="streamer-picker-hint">
                          Use the search box to find Twitch channels, or sync follows from Profile.
                        </p>
                      )}
                      {followedStreamers.length > 0 && (
                        <>
                          {forYouFiltered.length === 0 && normalizeFollowSearchQuery(feedSearch).length > 0 && (
                            <p className="streamer-picker-hint">
                              No channels match the current search filter — clear the search or pick a name from the dropdown.
                            </p>
                          )}
                          <ul className="for-you-list" aria-label="For You streamers">
                            {forYouFiltered.map((s) => (
                              <li key={s.streamer_id} className="for-you-row">
                                <label className="for-you-check-label">
                                  <input
                                    type="checkbox"
                                    checked={s.include_in_for_you}
                                    onChange={(e) => {
                                      const checked = e.target.checked;
                                      const base = new Set(
                                        followedStreamers
                                          .filter((x) => x.include_in_for_you)
                                          .map((x) => x.streamer_id)
                                      );
                                      if (checked) base.add(s.streamer_id);
                                      else base.delete(s.streamer_id);
                                      void persistForYouIds([...base], { silent: true });
                                    }}
                                  />
                                  <span>{s.streamer_name}</span>
                                </label>
                              </li>
                            ))}
                          </ul>
                        </>
                      )}
                    </>
                  )}
                </div>
              )}
            </div>
          </div>

          {/* MAIN CARD AREA */}
          <div className="swipe-container">
            {/* Skip arrow */}
            <button
              className={`btn-side btn-reject ${rejectHighlight ? 'highlight' : ''}`}
              onClick={() => handleSwipe('left')}
              title="Skip"
            >
              <svg viewBox="0 0 120 160" fill="none">
                <g opacity="0.15">
                  <circle cx="25" cy="80" r="18" fill="currentColor" />
                  <circle cx="60" cy="65" r="8" fill="currentColor" />
                  <circle cx="45" cy="100" r="5" fill="currentColor" />
                </g>
                <path d="M95 78 Q88 78 75 78 L45 78" stroke="currentColor" strokeWidth="14" strokeLinecap="round" opacity="0.9" />
                <path d="M55 55 L25 80 L55 105" stroke="currentColor" strokeWidth="14" strokeLinecap="round" strokeLinejoin="round" fill="none" />
                <text x="60" y="42" fontFamily="'Arial Black', Impact, sans-serif" fontSize="20" fontWeight="900" fill="currentColor" opacity="0.7" letterSpacing="3" transform="rotate(-8, 60, 42)">SKIP</text>
              </svg>
            </button>

            {/* Card stack */}
            <div id="card-stack">
              {loading ? (
                <div id="loading">
                  <div className="video-loading active" style={{ position: 'relative', top: 'auto', left: 'auto', transform: 'none' }} />
                  <p style={{ marginTop: '16px', fontWeight: 600, color: '#888' }}>Loading...</p>
                </div>
              ) : currentIndex >= clips.length ? (
                <div className="empty-msg">
                  <h2>All Caught Up</h2>
                  <p style={{ marginTop: '10px' }}>No more clips to vote on</p>
                </div>
              ) : (
                visibleClips.map((clip, idx) => {
                  let cardStyle: React.CSSProperties = {
                    zIndex: 100 - idx,
                    pointerEvents: idx === 0 ? 'auto' : 'none',
                    transition: 'transform 0.32s cubic-bezier(0.34, 1.56, 0.64, 1), opacity 0.28s',
                  };
                  if (idx === 0 && leavingDirection) {
                    cardStyle = {
                      ...cardStyle,
                      transform: `translate(${leavingDirection === 'right' ? '150%' : '-150%'}, -100px) rotate(${leavingDirection === 'right' ? 32 : -32}deg) scale(0.95)`,
                      opacity: 0,
                    };
                  } else if (idx === 0 && swipeDirection) {
                    cardStyle = {
                      ...cardStyle,
                      transform: `translate(${swipeDirection === 'right' ? '150%' : '-150%'}, -100px) rotate(${swipeDirection === 'right' ? 30 : -30}deg) scale(0.95)`,
                      opacity: 0,
                    };
                  } else if (idx > 0) {
                    cardStyle = {
                      ...cardStyle,
                      transform: `scale(${1 - idx * 0.03}) translateY(${idx * 10}px)`,
                      opacity: 1 - idx * 0.12,
                    };
                  }

                  return (
                    <div
                      key={clip.id}
                      ref={idx === 0 ? cardRef : null}
                      className={`clip-card ${idx === 0 ? 'top-card' : ''}`}
                      style={cardStyle}
                      onMouseDown={idx === 0 ? handleMouseDown : undefined}
                      onTouchStart={idx === 0 ? handleMouseDown : undefined}
                    >
                      <ClipPreview
                        clip={clip}
                        onOpenTheater={() => openTheaterMode(clip.id)}
                        isPreload={idx !== 0}
                      >
                        <div className="clip-info" style={{ pointerEvents: 'none' }}>
                          <div className="clip-title">{clip.title}</div>
                          <div className="creator">
                            {clip.creator_name} • {clip.channel}
                          </div>
                          <div className="clip-meta">
                            <div>
                              <span>👁 {formatViews(clip.view_count)}</span>
                              <span style={{ marginLeft: '8px' }}>⏱ {Math.floor(clip.duration)}s</span>
                            </div>
                            <div className="social-counters">
                              <div className="social-badge">♥ <span>{clip.local_likes}</span></div>
                              <button
                                className="social-btn"
                                onClick={(e) => {
                                  e.stopPropagation();
                                  onOpenComments(clip.id, clip.title);
                                }}
                              >
                                💬 <span>{clip.comment_count}</span>
                              </button>
                            </div>
                          </div>
                        </div>
                      </ClipPreview>

                      <div className="swipe-hint left" style={{ opacity: 0 }}>
                        <div className="aura-strings" />
                        <div className="hint-text-main">NOPE</div>
                        <div className="hint-text-bubbly">I dare you!</div>
                      </div>
                      <div className="swipe-hint right" style={{ opacity: 0 }}>
                        <div className="aura-strings" />
                        <div className="hint-text-main">LIKE</div>
                        <div className="hint-text-bubbly">Shiny! ✨</div>
                      </div>
                    </div>
                  );
                })
              )}
            </div>

            {/* Like arrow */}
            <button
              className={`btn-side btn-accept ${acceptHighlight ? 'highlight' : ''}`}
              data-testid="btn-like"
              onClick={() => handleSwipe('right')}
              title="Like"
            >
              <svg viewBox="0 0 120 160" fill="none">
                <g opacity="0.15">
                  <circle cx="95" cy="80" r="18" fill="currentColor" />
                  <circle cx="60" cy="65" r="8" fill="currentColor" />
                  <circle cx="75" cy="100" r="5" fill="currentColor" />
                </g>
                <path d="M25 78 Q32 78 45 78 L75 78" stroke="currentColor" strokeWidth="14" strokeLinecap="round" opacity="0.9" />
                <path d="M65 55 L95 80 L65 105" stroke="currentColor" strokeWidth="14" strokeLinecap="round" strokeLinejoin="round" fill="none" />
                <text x="60" y="42" fontFamily="'Arial Black', Impact, sans-serif" fontSize="20" fontWeight="900" fill="currentColor" opacity="0.7" letterSpacing="3" textAnchor="middle" transform="rotate(8, 60, 42)">LIKE</text>
              </svg>
            </button>
          </div>
        </div>
      </div>
    </>
  );
};
