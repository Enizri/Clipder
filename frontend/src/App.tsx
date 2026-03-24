import { useState, useEffect, useRef, useCallback, useMemo } from 'react';
import { api } from './api/client';
import type { Clip, LeaderboardClip, AdminClip, Comment, EmoteResponse, GifResponse } from './types';

type Tab = 'swipe' | 'leaderboard' | 'admin';
type EmoteTab = 'twitch' | 'bttv' | '7tv' | 'gifs';

function ClipPreview({ clip, onOpenTheater, children }: { clip: Clip; onOpenTheater: () => void; children?: React.ReactNode }) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const [videoSrc, setVideoSrc] = useState<string | null>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [isMuted, setIsMuted] = useState(false);
  const [volume, setVolume] = useState(5);
  const [progress, setProgress] = useState(0);
  const [isHovering, setIsHovering] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  const fetchVideoUrl = useCallback(async () => {
    if (videoSrc) return;
    setIsLoading(true);
    try {
      const data = await api.getVideoUrl(clip.id);
      if (data.video_url) {
        setVideoSrc(data.video_url);
      }
    } catch (e) {
      console.error('Failed to fetch video:', e);
    } finally {
      setIsLoading(false);
    }
  }, [clip.id, videoSrc]);

  useEffect(() => {
    if (isHovering && videoSrc) {
      const video = videoRef.current;
      if (video && video.readyState >= 2) {
        video.volume = volume / 100;
        video.muted = isMuted || volume === 0;
        video.play().catch(() => {});
        setIsPlaying(true);
      } else if (video && videoSrc) {
        setIsLoading(true);
        video.addEventListener('loadeddata', () => {
          setIsLoading(false);
          video.volume = volume / 100;
          video.muted = isMuted || volume === 0;
          video.play().catch(() => {});
          setIsPlaying(true);
        }, { once: true });
      }
    } else {
      const video = videoRef.current;
      if (video) {
        video.pause();
      }
      setIsPlaying(false);
    }
  }, [isHovering, videoSrc, volume, isMuted]);

  const handleMouseEnter = () => {
    setIsHovering(true);
    fetchVideoUrl();
  };

  const handleMouseLeave = () => {
    setIsHovering(false);
  };

  const handlePlayPause = (e: React.MouseEvent) => {
    e.stopPropagation();
    const video = videoRef.current;
    if (!video || !videoSrc) return;
    if (isPlaying) {
      video.pause();
    } else {
      video.play().catch(() => {});
    }
    setIsPlaying(!isPlaying);
  };

  const handleFullscreen = (e: React.MouseEvent) => {
    e.stopPropagation();
    onOpenTheater();
  };

  const toggleMute = (e: React.MouseEvent) => {
    e.stopPropagation();
    const newMuted = !isMuted;
    setIsMuted(newMuted);
    if (videoRef.current) {
      videoRef.current.muted = newMuted;
    }
  };

  const handleVolumeChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    e.stopPropagation();
    const vol = parseInt(e.target.value);
    setVolume(vol);
    if (videoRef.current) {
      videoRef.current.volume = vol / 100;
      if (vol === 0) {
        setIsMuted(true);
        videoRef.current.muted = true;
      } else if (isMuted && vol > 0) {
        setIsMuted(false);
        videoRef.current.muted = false;
      }
    }
  };

  const handleProgressChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    e.stopPropagation();
    const video = videoRef.current;
    if (!video) return;
    const val = parseFloat(e.target.value);
    video.currentTime = (val / 100) * video.duration;
    setProgress(val);
  };

  const handleTimeUpdate = () => {
    const video = videoRef.current;
    if (video && video.duration) {
      const val = (video.currentTime / video.duration) * 100;
      setProgress(val);
    }
  };

  return (
    <div
      ref={containerRef}
      className="clip-preview"
      onMouseEnter={handleMouseEnter}
      onMouseLeave={handleMouseLeave}
    >
      <div className="blur-bg-container">
        <img src={clip.thumbnail_url} alt="" draggable={false} />
      </div>
      <img src={clip.thumbnail_url} className="clip-thumbnail" alt={clip.title} draggable={false} 
           style={{ opacity: isPlaying ? 0 : 1 }} />
      
      {videoSrc && (
        <video
          ref={videoRef}
          className={`video-player ${isPlaying ? 'playing' : ''}`}
          src={videoSrc}
          loop
          muted={isMuted || volume === 0}
          playsInline
          onTimeUpdate={handleTimeUpdate}
        />
      )}
      
      <div className={`video-loading ${isLoading ? 'active' : ''}`}></div>
      
      <button className="fullscreen-btn" onClick={handleFullscreen} title="Theater Mode">⛶</button>
      <button className="play-pause-btn" onClick={handlePlayPause} title="Play/Pause">
        {isPlaying ? '⏸' : '▶'}
      </button>
      
      <div className="volume-control">
        <button className="volume-btn" onClick={toggleMute}><span>{volume === 0 ? '🔇' : '🔊'}</span></button>
        <input type="range" className="volume-slider" min="0" max="100" value={volume} onChange={handleVolumeChange} />
      </div>
      
      <div className="progress-container">
        <input
          type="range"
          className="progress-slider"
          min="0"
          max="100"
          step="0.1"
          value={progress}
          onChange={handleProgressChange}
          style={{ background: `linear-gradient(to right, #ec4899 ${progress}%, rgba(255, 255, 255, 0.2) ${progress}%)` }}
        />
      </div>
      
      {children}
    </div>
  );
}

function MiniThumb({ clip, onOpenTheater }: { clip: LeaderboardClip | AdminClip; onOpenTheater: () => void }) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const [videoSrc, setVideoSrc] = useState<string | null>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [isMuted, setIsMuted] = useState(false);
  const [volume, setVolume] = useState(5);

  const fetchVideoUrl = useCallback(async () => {
    if (videoSrc) return videoSrc;
    setIsLoading(true);
    try {
      const data = await api.getVideoUrl(clip.id);
      if (data.video_url) {
        setVideoSrc(data.video_url);
        return data.video_url;
      }
    } catch (e) {
      console.error('Failed to fetch video:', e);
    } finally {
      setIsLoading(false);
    }
    return null;
  }, [clip.id, videoSrc]);

  const handleMouseEnter = async () => {
    const src = await fetchVideoUrl();
    if (src && videoRef.current) {
      videoRef.current.src = src;
      videoRef.current.volume = volume / 100;
      videoRef.current.muted = isMuted || volume === 0;
      videoRef.current.play().catch(() => {});
      setIsPlaying(true);
    }
  };

  const handleMouseLeave = () => {
    if (videoRef.current) {
      videoRef.current.pause();
      videoRef.current.currentTime = 0;
    }
    setIsPlaying(false);
  };

  const togglePlay = (e: React.MouseEvent) => {
    e.stopPropagation();
    const video = videoRef.current;
    if (!video || !videoSrc) return;
    if (isPlaying) {
      video.pause();
    } else {
      video.play().catch(() => {});
    }
    setIsPlaying(!isPlaying);
  };

  const toggleMute = (e: React.MouseEvent) => {
    e.stopPropagation();
    const newMuted = !isMuted;
    setIsMuted(newMuted);
    if (videoRef.current) {
      videoRef.current.muted = newMuted;
    }
  };

  const handleVolumeChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    e.stopPropagation();
    const vol = parseInt(e.target.value);
    setVolume(vol);
    if (videoRef.current) {
      videoRef.current.volume = vol / 100;
      if (vol === 0) {
        setIsMuted(true);
        videoRef.current.muted = true;
      } else if (isMuted && vol > 0) {
        setIsMuted(false);
        videoRef.current.muted = false;
      }
    }
  };

  return (
    <div
      className={`thumb-container ${isLoading ? 'loading' : ''}`}
      onMouseEnter={handleMouseEnter}
      onMouseLeave={handleMouseLeave}
    >
      <img src={clip.thumbnail_url} alt={clip.title} />
      <div className="mini-spinner"></div>
      <video ref={videoRef} className={isPlaying ? 'playing' : ''} loop muted playsInline></video>
      <div className="mini-controls">
        <div style={{ display: 'flex', gap: '4px', alignItems: 'center' }}>
          <button className="mini-btn" onClick={togglePlay}>{isPlaying ? '⏸' : '▶'}</button>
          <button className="mini-btn" onClick={toggleMute}>{volume === 0 ? '🔇' : '🔊'}</button>
          <input 
            type="range" 
            className="mini-volume" 
            min="0" 
            max="100" 
            value={volume} 
            onChange={handleVolumeChange}
            onClick={(e) => e.stopPropagation()}
          />
        </div>
        <button className="mini-btn" onClick={onOpenTheater}>⛶</button>
      </div>
    </div>
  );
}

function EmotePicker({ onSelect, onClose }: { onSelect: (url: string, code: string) => void; onClose: () => void }) {
  const [activeTab, setActiveTab] = useState<EmoteTab>('twitch');
  const [emotes, setEmotes] = useState<EmoteResponse | null>(null);
  const [gifs, setGifs] = useState<GifResponse | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadEmotes();
  }, []);

  const loadEmotes = async () => {
    try {
      const data = await api.getEmotes();
      setEmotes(data);
    } catch (e) {
      console.error('Failed to load emotes:', e);
    } finally {
      setLoading(false);
    }
  };

  const searchGifs = useCallback(async (query: string) => {
    if (!query.trim()) {
      setGifs(null);
      return;
    }
    try {
      const data = await api.searchGifs(query);
      setGifs(data);
    } catch (e) {
      console.error('Failed to search gifs:', e);
    }
  }, []);

  useEffect(() => {
    if (activeTab === 'gifs' && searchQuery) {
      const timer = setTimeout(() => searchGifs(searchQuery), 300);
      return () => clearTimeout(timer);
    }
  }, [searchQuery, activeTab, searchGifs]);

  const handleSelect = (url: string, code: string) => {
    onSelect(url, code);
  };

  const currentEmotes = useMemo(() => {
    if (!emotes) return [];
    switch (activeTab) {
      case 'twitch': return emotes.twitch;
      case 'bttv': return emotes.bttv;
      case '7tv': return emotes.seventv;
      default: return [];
    }
  }, [emotes, activeTab]);

  return (
    <div className="emote-picker-popup">
      <div className="emote-picker-header">
        <div className="emote-tabs">
          <button className={`emote-tab ${activeTab === 'twitch' ? 'active' : ''}`} onClick={() => setActiveTab('twitch')}>Twitch</button>
          <button className={`emote-tab ${activeTab === 'bttv' ? 'active' : ''}`} onClick={() => setActiveTab('bttv')}>BTTV</button>
          <button className={`emote-tab ${activeTab === '7tv' ? 'active' : ''}`} onClick={() => setActiveTab('7tv')}>7TV</button>
          <button className={`emote-tab ${activeTab === 'gifs' ? 'active' : ''}`} onClick={() => setActiveTab('gifs')}>GIFs</button>
        </div>
        <button className="emote-picker-close" onClick={onClose}>✕</button>
      </div>
      
      {activeTab === 'gifs' && (
        <div className="emote-search">
          <input
            type="text"
            placeholder="Search GIFs..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
          />
        </div>
      )}

      <div className="emote-grid">
        {loading ? (
          <div className="emote-loading">
            <div className="spinner"></div>
            <span>Loading emotes...</span>
          </div>
        ) : activeTab === 'gifs' ? (
          gifs?.gifs && gifs.gifs.length > 0 ? (
            gifs.gifs.map((gif) => (
              <div key={gif.id} className="emote-option gif-option" onClick={() => handleSelect(gif.url, gif.title)}>
                <img src={gif.preview || gif.url} alt="" loading="lazy" />
              </div>
            ))
          ) : (
            <div className="emote-empty">Search for GIFs above</div>
          )
        ) : currentEmotes.length > 0 ? (
          currentEmotes.map((emote) => (
            <div key={emote.id} className="emote-option" onClick={() => handleSelect(emote.url, emote.code)} title={emote.code}>
              <img src={emote.url} alt={emote.code} loading="lazy" />
            </div>
          ))
        ) : (
          <div className="emote-empty">No emotes available</div>
        )}
      </div>
    </div>
  );
}

function App() {
  const [activeTab, setActiveTab] = useState<Tab>('swipe');
  const [clips, setClips] = useState<Clip[]>([]);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [categories, setCategories] = useState<string[]>(['My Streamers']);
  const [currentCategory, setCurrentCategory] = useState('My Streamers');
  const [loading, setLoading] = useState(true);
  const [leaderboard, setLeaderboard] = useState<LeaderboardClip[]>([]);
  const [adminQueue, setAdminQueue] = useState<AdminClip[]>([]);
  const [showComments, setShowComments] = useState(false);
  const [activeCommentClip, setActiveCommentClip] = useState<{ id: string; title: string } | null>(null);
  const [comments, setComments] = useState<Comment[]>([]);
  const [theaterVideo, setTheaterVideo] = useState<{ clipId: string; src: string } | null>(null);
  const [rejectHighlight, setRejectHighlight] = useState(false);
  const [acceptHighlight, setAcceptHighlight] = useState(false);
  const [swipeDirection, setSwipeDirection] = useState<'left' | 'right' | null>(null);
  const [showEmotePicker, setShowEmotePicker] = useState(false);

  const cardRef = useRef<HTMLDivElement>(null);
  const theaterVideoRef = useRef<HTMLVideoElement>(null);
  const isDragging = useRef(false);
  const startX = useRef(0);
  const currentX = useRef(0);
  const isSwiping = useRef(false);
  const commentInputRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    loadCategories();
  }, []);

  useEffect(() => {
    if (activeTab === 'swipe') {
      loadClips();
    } else if (activeTab === 'leaderboard') {
      loadLeaderboard();
    } else if (activeTab === 'admin') {
      loadAdminQueue();
    }
  }, [activeTab, currentCategory]);

  useEffect(() => {
    if (theaterVideo && theaterVideoRef.current) {
      theaterVideoRef.current.volume = 0.05;
    }
  }, [theaterVideo]);

  const loadCategories = async () => {
    try {
      const data = await api.getCategories();
      setCategories(['My Streamers', ...data.categories]);
    } catch (err) {
      console.error('Failed to load categories:', err);
    }
  };

  const loadClips = async () => {
    setLoading(true);
    try {
      const data = await api.getClips(currentCategory);
      setClips(data.clips);
      setCurrentIndex(0);
    } catch (err) {
      console.error('Failed to load clips:', err);
    } finally {
      setLoading(false);
    }
  };

  const loadLeaderboard = async () => {
    try {
      const data = await api.getLeaderboard();
      setLeaderboard(data);
    } catch (err) {
      console.error('Failed to load leaderboard:', err);
    }
  };

  const loadAdminQueue = async () => {
    try {
      const data = await api.getAcceptedClips();
      setAdminQueue(data);
    } catch (err) {
      console.error('Failed to load admin queue:', err);
    }
  };

  const loadComments = async (clipId: string) => {
    try {
      const data = await api.getComments(clipId);
      setComments(data);
    } catch (err) {
      console.error('Failed to load comments:', err);
    }
  };

  const handleSwipe = useCallback(async (direction: 'left' | 'right') => {
    if (isSwiping.current) return;
    const currentClip = clips[currentIndex];
    if (!currentClip) return;

    isSwiping.current = true;
    setSwipeDirection(direction);

    try {
      if (direction === 'right') {
        await api.likeClip(currentClip.id);
      } else {
        await api.dislikeClip(currentClip.id);
      }
    } catch (err) {
      console.error('Failed to record swipe:', err);
    }

    setTimeout(() => {
      setCurrentIndex((prev) => prev + 1);
      setSwipeDirection(null);
      isSwiping.current = false;
    }, 300);
  }, [clips, currentIndex]);

  const handleMouseDown = (e: React.MouseEvent | React.TouchEvent) => {
    if (isSwiping.current) return;
    const target = e.target as HTMLElement;
    if (target.closest('.volume-control, .fullscreen-btn, .play-pause-btn, .progress-container, .clip-info, button')) return;

    isDragging.current = true;
    startX.current = 'touches' in e ? e.touches[0].clientX : e.clientX;
    currentX.current = startX.current;
    cardRef.current?.classList.add('dragging');
  };

  const handleMouseMove = useCallback((e: MouseEvent | TouchEvent) => {
    if (!isDragging.current || !cardRef.current) return;
    if ('preventDefault' in e) e.preventDefault();

    const clientX = 'touches' in e ? e.touches[0].clientX : e.clientX;
    currentX.current = clientX;

    const deltaX = clientX - startX.current;
    cardRef.current.style.transform = `translate(${deltaX}px, 0) rotate(${deltaX * 0.03}deg)`;

    const swipeThreshold = 50;

    if (deltaX < -swipeThreshold) {
      setRejectHighlight(true);
      setAcceptHighlight(false);
      const nopeHint = cardRef.current.querySelector('.swipe-hint.left') as HTMLElement;
      if (nopeHint) {
        const progress = Math.min(1.5, (Math.abs(deltaX) - swipeThreshold) / 100);
        nopeHint.style.transform = `scale(${0.5 + progress * 0.7})`;
        nopeHint.style.opacity = String(progress);
      }
    } else if (deltaX > swipeThreshold) {
      setAcceptHighlight(true);
      setRejectHighlight(false);
      const likeHint = cardRef.current.querySelector('.swipe-hint.right') as HTMLElement;
      if (likeHint) {
        const progress = Math.min(1.5, (deltaX - swipeThreshold) / 100);
        likeHint.style.transform = `scale(${0.5 + progress * 0.7})`;
        likeHint.style.opacity = String(progress);
      }
    } else {
      setRejectHighlight(false);
      setAcceptHighlight(false);
      const nopeHint = cardRef.current.querySelector('.swipe-hint.left') as HTMLElement;
      const likeHint = cardRef.current.querySelector('.swipe-hint.right') as HTMLElement;
      if (nopeHint) { nopeHint.style.opacity = '0'; nopeHint.style.transform = 'scale(0.5)'; }
      if (likeHint) { likeHint.style.opacity = '0'; likeHint.style.transform = 'scale(0.5)'; }
    }
  }, []);

  const handleMouseUp = useCallback(() => {
    if (!isDragging.current || !cardRef.current) return;
    isDragging.current = false;
    cardRef.current.classList.remove('dragging');

    const deltaX = currentX.current - startX.current;
    setRejectHighlight(false);
    setAcceptHighlight(false);

    const nopeHint = cardRef.current.querySelector('.swipe-hint.left') as HTMLElement;
    const likeHint = cardRef.current.querySelector('.swipe-hint.right') as HTMLElement;
    if (nopeHint) { nopeHint.style.opacity = '0'; nopeHint.style.transform = 'scale(0.5)'; }
    if (likeHint) { likeHint.style.opacity = '0'; likeHint.style.transform = 'scale(0.5)'; }

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

  const openComments = (clipId: string, title: string) => {
    setActiveCommentClip({ id: clipId, title });
    loadComments(clipId);
    setShowComments(true);
  };

  const closeComments = () => {
    setShowComments(false);
    setActiveCommentClip(null);
  };

  const postComment = async () => {
    if (!activeCommentClip || !commentInputRef.current) return;
    const text = commentInputRef.current.innerHTML.trim();
    if (!text || text === '<br>') return;

    commentInputRef.current.innerHTML = '';
    try {
      await api.postComment(activeCommentClip.id, text);
      loadComments(activeCommentClip.id);
    } catch (err) {
      alert('Failed to post comment');
    }
  };

  const openTheaterMode = async (clipId: string) => {
    try {
      const data = await api.getVideoUrl(clipId);
      if (data.video_url) {
        setTheaterVideo({ clipId, src: data.video_url });
      }
    } catch (err) {
      alert('Could not load full video.');
    }
  };

  const closeTheaterMode = () => {
    setTheaterVideo(null);
  };

  const formatViews = (views: number) => {
    if (views >= 1000) return `${(views / 1000).toFixed(1)}K`;
    return views.toString();
  };

  const handleCategoryChange = async (cat: string, e: React.MouseEvent<HTMLButtonElement>) => {
    if (cat === currentCategory) return;
    
    document.querySelectorAll('.cat-pill').forEach(el => el.classList.remove('active'));
    e.currentTarget.classList.add('active');
    
    setClips([]);
    setCurrentIndex(0);
    setLoading(true);
    setCurrentCategory(cat);
  };

  const handleAddToQueue = async (clipId: string) => {
    await api.addToQueue(clipId);
    loadAdminQueue();
    alert('✅ Sent to Admin Upload Queue!');
  };

  const handleRemoveFromQueue = async (clipId: string) => {
    await api.removeFromQueue(clipId);
    loadAdminQueue();
  };

  const visibleClips = useMemo(() => clips.slice(currentIndex, Math.min(currentIndex + 3, clips.length)), [clips, currentIndex]);

  return (
    <>
      <header>
        <h1>Clip<span className="logo-accent">der</span> Pro</h1>
        <nav className="nav-tabs">
          <button className={`tab-btn ${activeTab === 'swipe' ? 'active' : ''}`} onClick={() => { setActiveTab('swipe'); closeComments(); }}>Swipe & Vote</button>
          <button className={`tab-btn ${activeTab === 'leaderboard' ? 'active' : ''}`} onClick={() => { setActiveTab('leaderboard'); closeComments(); loadLeaderboard(); }}>Leaderboard</button>
          <button className={`tab-btn ${activeTab === 'admin' ? 'active' : ''}`} onClick={() => { setActiveTab('admin'); closeComments(); loadAdminQueue(); }}>Admin Queue ({adminQueue.length})</button>
        </nav>
      </header>

      <div className="app-container">
        <div id="swipe" className={`view-section ${activeTab === 'swipe' ? 'active' : ''}`}>
          <div className="category-menu">
            {categories.map((cat) => (
              <button key={cat} className={`cat-pill ${currentCategory === cat ? 'active' : ''}`} onClick={(e) => handleCategoryChange(cat, e)}>
                {cat}
              </button>
            ))}
          </div>

          <div className="swipe-container">
            <div className="action-buttons">
              <button className={`btn-side btn-reject ${rejectHighlight ? 'highlight' : ''}`} onClick={() => handleSwipe('left')} title="Skip">
                <svg viewBox="0 0 120 160" fill="none">
                  <g opacity="0.15"><circle cx="25" cy="80" r="18" fill="currentColor"/><circle cx="60" cy="65" r="8" fill="currentColor"/><circle cx="45" cy="100" r="5" fill="currentColor"/><circle cx="80" cy="75" r="3" fill="currentColor"/><circle cx="35" cy="55" r="4" fill="currentColor"/><circle cx="55" cy="110" r="3" fill="currentColor"/></g>
                  <path d="M95 78 Q88 78 75 78 L45 78" stroke="currentColor" strokeWidth="14" strokeLinecap="round" opacity="0.9"/>
                  <path d="M55 55 L25 80 L55 105" stroke="currentColor" strokeWidth="14" strokeLinecap="round" strokeLinejoin="round" fill="none"/>
                  <path d="M30 95 Q30 115 32 125" stroke="currentColor" strokeWidth="3" strokeLinecap="round" opacity="0.5"/>
                  <path d="M50 105 Q49 118 50 122" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" opacity="0.4"/>
                  <path d="M70 83 Q70 95 71 100" stroke="currentColor" strokeWidth="2" strokeLinecap="round" opacity="0.3"/>
                  <text x="60" y="42" fontFamily="'Arial Black', Impact, sans-serif" fontSize="20" fontWeight="900" fill="currentColor" opacity="0.7" letterSpacing="3" transform="rotate(-8, 60, 42)">SKIP</text>
                </svg>
              </button>
              <button className={`btn-side btn-accept ${acceptHighlight ? 'highlight' : ''}`} onClick={() => handleSwipe('right')} title="Like">
                <svg viewBox="0 0 120 160" fill="none">
                  <g opacity="0.15"><circle cx="95" cy="80" r="18" fill="currentColor"/><circle cx="60" cy="65" r="8" fill="currentColor"/><circle cx="75" cy="100" r="5" fill="currentColor"/><circle cx="40" cy="75" r="3" fill="currentColor"/><circle cx="85" cy="55" r="4" fill="currentColor"/><circle cx="65" cy="110" r="3" fill="currentColor"/></g>
                  <path d="M25 78 Q32 78 45 78 L75 78" stroke="currentColor" strokeWidth="14" strokeLinecap="round" opacity="0.9"/>
                  <path d="M65 55 L95 80 L65 105" stroke="currentColor" strokeWidth="14" strokeLinecap="round" strokeLinejoin="round" fill="none"/>
                  <path d="M90 95 Q90 115 88 125" stroke="currentColor" strokeWidth="3" strokeLinecap="round" opacity="0.5"/>
                  <path d="M70 105 Q71 118 70 122" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" opacity="0.4"/>
                  <path d="M50 83 Q50 95 49 100" stroke="currentColor" strokeWidth="2" strokeLinecap="round" opacity="0.3"/>
                  <text x="60" y="42" fontFamily="'Arial Black', Impact, sans-serif" fontSize="20" fontWeight="900" fill="currentColor" opacity="0.7" letterSpacing="3" textAnchor="middle" transform="rotate(8, 60, 42)">LIKE</text>
                </svg>
              </button>
            </div>

            <div id="card-stack">
              {loading ? (
                <div id="loading">
                  <div className="video-loading active" style={{ position: 'relative', top: 'auto', left: 'auto', transform: 'none' }}></div>
                  <p style={{ marginTop: '16px', fontWeight: 600, color: '#888' }}>Loading...</p>
                </div>
              ) : currentIndex >= clips.length ? (
                <div className="empty-msg">
                  <h2>All Caught Up</h2>
                  <p style={{ marginTop: '10px' }}>No more clips to vote on</p>
                </div>
              ) : (
                visibleClips.map((clip, idx) => (
                  <div
                    key={clip.id}
                    ref={idx === 0 ? cardRef : null}
                    className={`clip-card ${idx === 0 ? 'top-card' : ''}`}
                    style={{
                      zIndex: 100 - idx,
                      transform: idx === 0 && swipeDirection
                        ? `translate(${swipeDirection === 'right' ? '150%' : '-150%'}, -100px) rotate(${swipeDirection === 'right' ? 30 : -30}deg)`
                        : idx > 0
                        ? `scale(${1 - idx * 0.03}) translateY(${idx * 10}px)`
                        : undefined,
                      opacity: idx === 0 && swipeDirection ? 0 : idx > 0 ? 1 - idx * 0.12 : 1,
                      pointerEvents: idx === 0 ? 'auto' : 'none',
                      transition: swipeDirection ? 'transform 0.3s ease-out, opacity 0.3s' : 'transform 0.3s cubic-bezier(0.2, 1, 0.3, 1), opacity 0.3s ease-out'
                    }}
                    onMouseDown={idx === 0 ? handleMouseDown : undefined}
                    onTouchStart={idx === 0 ? handleMouseDown : undefined}
                  >
                    <ClipPreview
                      clip={clip}
                      onOpenTheater={() => openTheaterMode(clip.id)}
                    >
                      <div className="clip-info" style={{ pointerEvents: 'none' }}>
                        <div className="clip-title">{clip.title}</div>
                        <div className="creator">{clip.creator_name} • {clip.channel}</div>
                        <div className="clip-meta">
                          <div>
                            <span>👁 {formatViews(clip.view_count)}</span>
                            <span style={{ marginLeft: '8px' }}>⏱ {Math.floor(clip.duration)}s</span>
                          </div>
                          <div className="social-counters">
                            <div className="social-badge">♥ <span>{clip.local_likes}</span></div>
                            <button className="social-btn" onClick={(e) => { e.stopPropagation(); openComments(clip.id, clip.title); }}>💬 <span>{clip.comment_count}</span></button>
                          </div>
                        </div>
                      </div>
                    </ClipPreview>
                    <div className="swipe-hint left" style={{ opacity: 0 }}>
                      <div className="aura-strings"></div>
                      <div className="hint-text-main">NOPE</div>
                      <div className="hint-text-bubbly">I dare you!</div>
                    </div>
                    <div className="swipe-hint right" style={{ opacity: 0 }}>
                      <div className="aura-strings"></div>
                      <div className="hint-text-main">LIKE</div>
                      <div className="hint-text-bubbly">Shiny! ✨</div>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>

        <div id="leaderboard" className={`view-section ${activeTab === 'leaderboard' ? 'active' : ''}`}>
          <div className="list-container">
            <h2 className="section-title">🏆 Top Viral Clips</h2>
            <div className="section-subtitle">Ranked by your swipes. Hover to preview, or click expand for Theater Mode!</div>

            {leaderboard.length === 0 ? (
              <div className="empty-msg">No clips have been liked yet!<br />Go swipe right to build the leaderboard.</div>
            ) : (
              leaderboard.map((clip, index) => (
                <div key={clip.id} className="list-item">
                  <div style={{ fontSize: '1.2em', fontWeight: 900, color: '#888', width: '40px', textAlign: 'center' }}>#{index + 1}</div>
                  <div className="thumb-wrapper">
                    <MiniThumb clip={clip} onOpenTheater={() => openTheaterMode(clip.id)} />
                  </div>
                  <div className="item-details">
                    <div className="item-title">{clip.title}</div>
                    <div className="item-stats">
                      <span>♥ {clip.local_likes} Likes</span>
                      <button className="social-btn" style={{ padding: '2px 8px', fontSize: '1em', background: 'transparent', border: '1px solid rgba(255,255,255,0.1)' }} onClick={() => openComments(clip.id, clip.title)}>💬 {clip.comment_count}</button>
                      <span>👁 {formatViews(clip.view_count)} views</span>
                      <span>{clip.channel}</span>
                    </div>
                  </div>
                  <button className="btn-small btn-outline" onClick={() => handleAddToQueue(clip.id)}>+ Send to Queue</button>
                </div>
              ))
            )}
          </div>
        </div>

        <div id="admin" className={`view-section ${activeTab === 'admin' ? 'active' : ''}`}>
          <div className="list-container" style={{ paddingBottom: '20px' }}>
            <h2 className="section-title">🚀 Ready for Upload</h2>
            <div className="section-subtitle">Clips selected from the leaderboard, waiting to be processed.</div>

            {adminQueue.length === 0 ? (
              <div className="empty-msg">Admin queue is empty.<br /><br />Add clips from the Leaderboard to process them.</div>
            ) : (
              adminQueue.map((clip) => (
                <div key={clip.id} className="list-item">
                  <div className="thumb-wrapper">
                    <MiniThumb clip={clip} onOpenTheater={() => openTheaterMode(clip.id)} />
                  </div>
                  <div className="item-details">
                    <div className="item-title">{clip.title}</div>
                    <div className="item-stats">Ready for Upload • {clip.channel}</div>
                  </div>
                  <div className="action-group">
                    <button className="btn-small btn-danger" onClick={() => handleRemoveFromQueue(clip.id)}>Remove</button>
                    <button className="btn-small btn-primary">Upload Now</button>
                  </div>
                </div>
              ))
            )}
          </div>
          {adminQueue.length > 0 && (
            <div className="admin-footer">
              <div style={{ fontSize: '1.1em', fontWeight: 600 }}>{adminQueue.length} clips ready to process</div>
              <button className="btn-small btn-primary">Process & Upload All</button>
            </div>
          )}
        </div>
      </div>

      <div id="theater-modal" className={theaterVideo ? 'show' : ''} style={{ display: theaterVideo ? 'flex' : 'none' }}>
        <div className="theater-backdrop" onClick={closeTheaterMode}></div>
        <button className="theater-close" onClick={closeTheaterMode}>✕</button>
        <div className="theater-content">
          <div className="theater-video-wrapper">
            {theaterVideo && <video id="theater-video" ref={theaterVideoRef} controls autoPlay src={theaterVideo.src}></video>}
          </div>
        </div>
      </div>

      <div id="comments-sidebar" className={showComments ? 'show' : ''}>
        <div className="comments-header">
          <span>{activeCommentClip?.title || 'Comments'}</span>
          <button className="close-comments" onClick={closeComments}>✕</button>
        </div>
        <div className="comments-list">
          {comments.length === 0 ? (
            <div style={{ textAlign: 'center', padding: '40px 20px', color: '#666' }}>No comments yet. Be the first!</div>
          ) : (
            comments.map((c) => (
              <div key={c.timestamp} className="comment-item">
                <div className="comment-user">{c.user}</div>
                <div className="comment-text" dangerouslySetInnerHTML={{ __html: c.text }} />
              </div>
            ))
          )}
        </div>
        <div className="comments-input-wrapper">
          {showEmotePicker && (
            <EmotePicker
              onSelect={(url, code) => {
                if (commentInputRef.current) {
                  const img = document.createElement('img');
                  img.src = url;
                  img.className = 'chat-emote';
                  img.alt = code;
                  commentInputRef.current.appendChild(img);
                  commentInputRef.current.appendChild(document.createTextNode('\u00A0'));
                  commentInputRef.current.focus();
                }
              }}
              onClose={() => setShowEmotePicker(false)}
            />
          )}
          <div
            ref={commentInputRef}
            className="comment-input"
            contentEditable
            suppressContentEditableWarning
            data-placeholder="Add a comment..."
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                postComment();
              }
            }}
          ></div>
          <button className="emote-toggle-btn" onClick={() => setShowEmotePicker(!showEmotePicker)}>☺</button>
          <button className="send-btn" onClick={postComment}>Send</button>
        </div>
      </div>
    </>
  );
}

export default App;
