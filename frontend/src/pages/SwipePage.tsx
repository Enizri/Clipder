import React, { useState, useEffect, useRef, useCallback, useMemo } from 'react';
import { api } from '../api/client';
import { ClipPreview } from '../components/ClipPreview';
import { TwitchAuthWall } from '../components/TwitchAuthWall';
import { videoUrlCache } from '../utils/videoCache';
import { TheaterMode } from '../components/TheaterMode';
import type { Clip, User } from '../types';

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
  const [followedStreamers, setFollowedStreamers] = useState<
    { id: number; streamer_name: string; streamer_id: string }[]
  >([]);
  const [selectedStreamerId, setSelectedStreamerId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [showCategoriesMenu, setShowCategoriesMenu] = useState(false);
  const [rejectHighlight, setRejectHighlight] = useState(false);
  const [acceptHighlight, setAcceptHighlight] = useState(false);
  const [swipeDirection, setSwipeDirection] = useState<'left' | 'right' | null>(null);
  const [leavingDirection, setLeavingDirection] = useState<'left' | 'right' | null>(null);
  const [theaterSrc, setTheaterSrc] = useState<string | null>(null);
  const [theaterLoading, setTheaterLoading] = useState(false);

  const cardRef = useRef<HTMLDivElement>(null);
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
      setSelectedStreamerId(null);
      return;
    }
    api
      .getFollowing()
      .then((rows) => setFollowedStreamers(Array.isArray(rows) ? rows : []))
      .catch((err) => {
        if (isViteDev()) console.warn('Could not load followed streamers', err);
      });
  }, [user]);

  const clipQueryStreamerId =
    user && currentCategory === 'My Streamers' && selectedStreamerId
      ? selectedStreamerId
      : undefined;

  useEffect(() => {
    setLoading(true);
    api
      .getClips(currentCategory, clipQueryStreamerId)
      .then((data) => {
        if (!data?.clips || !Array.isArray(data.clips)) {
          setClips([]);
          return;
        }
        setClips(data.clips);
        setCurrentIndex(0);
      })
      .catch((err) => {
        if (isViteDev()) console.warn('getClips failed', err);
        setClips([]);
      })
      .finally(() => setLoading(false));
  }, [currentCategory, clipQueryStreamerId]);

  // ---------------------------------------------------------------------------
  // Helpers
  // ---------------------------------------------------------------------------

  const stopAllVideos = useCallback(() => {
    document.querySelectorAll<HTMLVideoElement>('.clip-preview video').forEach((v) => {
      v.pause();
      v.currentTime = 0;
    });
  }, []);

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
        if (nextClip && !videoUrlCache[nextClip.id]) {
          api.getVideoUrl(nextClip.id).then((data) => {
            if (data.video_url) videoUrlCache[nextClip.id] = data.video_url;
          }).catch(() => {});
        }

        if (user) {
          // Authenticated — votes always count
          if (direction === 'right') {
            api.likeClip(currentClip.id).catch(() => {});
          } else {
            api.dislikeClip(currentClip.id).catch(() => {});
          }
        } else {
          // Guest — ghost swipe (no API call), track count for auth wall
          const count = incrementGuestSwipeCount();
          if (count >= GUEST_SWIPE_LIMIT) {
            setShowAuthWall(true);
          }
        }

        // Fetch more clips before running out
        const newIndex = currentIndex + 1;
        if (newIndex >= clips.length - 2) {
          api
            .getClips(currentCategory, clipQueryStreamerId)
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
    [clips, currentIndex, stopAllVideos, user, currentCategory, clipQueryStreamerId]
  );

  // ---------------------------------------------------------------------------
  // Drag (mouse + touch)
  // ---------------------------------------------------------------------------

  const handleMouseDown = (e: React.MouseEvent | React.TouchEvent) => {
    if (isSwiping.current) return;
    const target = e.target as HTMLElement;
    if (
      target.closest(
        '.volume-control, .fullscreen-btn, .play-pause-btn, .progress-container, .clip-info, button'
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
              {user && currentCategory === 'My Streamers' && followedStreamers.length > 0 && (
                <label className="streamer-picker">
                  <span className="streamer-picker-label">Your streamers</span>
                  <select
                    className="streamer-picker-select"
                    value={selectedStreamerId ?? ''}
                    onChange={(e) => {
                      const v = e.target.value;
                      setSelectedStreamerId(v === '' ? null : v);
                      stopAllVideos();
                      setClips([]);
                      setCurrentIndex(0);
                    }}
                  >
                    <option value="">All followed</option>
                    {followedStreamers.map((s) => (
                      <option key={s.streamer_id} value={s.streamer_id}>
                        {s.streamer_name}
                      </option>
                    ))}
                  </select>
                </label>
              )}
              {user && currentCategory === 'My Streamers' && followedStreamers.length === 0 && !loading && (
                <p className="streamer-picker-hint">
                  Add streamers in your profile to see them here.
                </p>
              )}
            </div>

            <button
              className={`categories-toggle ${showCategoriesMenu ? 'open' : ''}`}
              onClick={() => setShowCategoriesMenu((s) => !s)}
              title="Browse categories"
            >
              <span>All Categories</span>
              <span className="hamburger-icon">☰</span>
            </button>

            <div className={`categories-dropdown ${showCategoriesMenu ? 'open' : ''}`}>
              <div className="categories-list">
                {categories.map((cat) => (
                  <button
                    key={cat}
                    className={`category-item ${currentCategory === cat ? 'active' : ''}`}
                    onClick={() => {
                      if (cat === currentCategory) return;
                      stopAllVideos();
                      setClips([]);
                      setCurrentIndex(0);
                      setCurrentCategory(cat);
                      setShowCategoriesMenu(false);
                    }}
                  >
                    {cat}
                  </button>
                ))}
              </div>
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
