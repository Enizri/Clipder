import React, { useState, useRef, useEffect, useCallback } from 'react';
import { api } from '../api/client';
import { getDemoVideoUrl, isDemoMode } from '../demo/demoClips';
import { videoUrlCache } from '../utils/videoCache';
import type { Clip } from '../types';

interface ClipPreviewProps {
  clip: Clip;
  onOpenTheater: () => void;
  isPreload?: boolean;
  /** Play without waiting for hover — used for the top card of the swipe stack. */
  autoPlay?: boolean;
  children?: React.ReactNode;
}

export const ClipPreview = React.memo(function ClipPreview({
  clip,
  onOpenTheater,
  isPreload,
  autoPlay,
  children,
}: ClipPreviewProps) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [videoSrc, setVideoSrc] = useState<string | null>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [isMuted, setIsMuted] = useState(false);
  const [volume, setVolume] = useState(5);
  const [progress, setProgress] = useState(0);
  const [isHovering, setIsHovering] = useState(false);

  const fetchVideoUrl = useCallback(() => {
    if (videoSrc) return;
    if (isDemoMode()) {
      const demoSrc = getDemoVideoUrl(clip.id);
      if (demoSrc) setVideoSrc(demoSrc);
      return;
    }
    if (videoUrlCache[clip.id]) {
      setVideoSrc(videoUrlCache[clip.id]);
      return;
    }
    setIsLoading(true);
    api
      .getVideoUrl(clip.id)
      .then((data) => {
        if (data.video_url) {
          videoUrlCache[clip.id] = data.video_url;
          setVideoSrc(data.video_url);
        }
      })
      .catch(() => {
        // Video URL fetch failed — card stays with thumbnail
      })
      .finally(() => setIsLoading(false));
  }, [clip.id, videoSrc]);

  // Seed from cache if preloading (next card in stack)
  useEffect(() => {
    if (isPreload && !videoSrc && videoUrlCache[clip.id]) {
      setVideoSrc(videoUrlCache[clip.id]);
    }
  }, [isPreload, videoSrc, clip.id]);

  // Trigger fetch when hovering, preloading, or auto-playing
  useEffect(() => {
    if (isHovering || isPreload || autoPlay) fetchVideoUrl();
  }, [isHovering, isPreload, autoPlay, fetchVideoUrl]);

  const shouldPlay = Boolean(autoPlay) || isHovering;
  // Headless capture and first-paint autoplay both require the muted attribute to stay set.
  // Unmuting on hover is fine in a real browser; in demo mode we never unmute.
  const forceMuted = isDemoMode() || isMuted || (Boolean(autoPlay) && !isHovering);

  // Play once the src lands, either on hover or because this card is the active one
  useEffect(() => {
    if (!videoSrc || !shouldPlay) return;
    const video = videoRef.current;
    if (!video) return;
    const play = () => {
      video.muted = forceMuted;
      if (!forceMuted) video.volume = volume / 100;
      video
        .play()
        .then(() => setIsPlaying(true))
        .catch(() => {
          video.muted = true;
          video.play().then(() => setIsPlaying(true)).catch(() => {});
        });
    };
    if (video.readyState >= 2) {
      play();
    } else {
      video.addEventListener('canplay', play, { once: true });
    }
  }, [shouldPlay, forceMuted, videoSrc, volume]);

  // Pause when the mouse leaves, unless this card is auto-playing
  useEffect(() => {
    if (!shouldPlay && isPlaying) {
      videoRef.current?.pause();
      setIsPlaying(false);
    }
  }, [shouldPlay, isPlaying]);

  // Demo GIF capture: GPU video overlays are invisible to Chrome's screencast, so paint
  // each decoded frame onto a canvas that lives in the regular compositor.
  useEffect(() => {
    if (!isDemoMode() || !isPlaying) return;
    const video = videoRef.current;
    const canvas = canvasRef.current;
    if (!video || !canvas) return;
    const ctx = canvas.getContext('2d', { alpha: false });
    if (!ctx) return;
    let raf = 0;
    let lastW = 0;
    let lastH = 0;
    const draw = () => {
      const vw = video.videoWidth;
      const vh = video.videoHeight;
      const dw = canvas.clientWidth;
      const dh = canvas.clientHeight;
      if (vw > 0 && vh > 0 && dw > 0 && dh > 0) {
        const dpr = window.devicePixelRatio || 1;
        const tw = Math.round(dw * dpr);
        const th = Math.round(dh * dpr);
        if (canvas.width !== tw || canvas.height !== th) {
          canvas.width = tw;
          canvas.height = th;
        }
        if (lastW !== tw || lastH !== th) {
          ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
          lastW = tw;
          lastH = th;
        }
        const scale = Math.max(dw / vw, dh / vh);
        const sw = dw / scale;
        const sh = dh / scale;
        try {
          ctx.drawImage(video, (vw - sw) / 2, (vh - sh) / 2, sw, sh, 0, 0, dw, dh);
        } catch {
          /* tainted frame — keep the loop alive for the next tick */
        }
      }
      raf = requestAnimationFrame(draw);
    };
    draw();
    return () => cancelAnimationFrame(raf);
  }, [isPlaying]);

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

  const toggleMute = (e: React.MouseEvent) => {
    e.stopPropagation();
    const next = !isMuted;
    setIsMuted(next);
    if (videoRef.current) videoRef.current.muted = next;
  };

  const handleVolumeChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    e.stopPropagation();
    const vol = parseInt(e.target.value);
    setVolume(vol);
    if (videoRef.current) {
      videoRef.current.volume = vol / 100;
      const nowMuted = vol === 0;
      setIsMuted(nowMuted);
      videoRef.current.muted = nowMuted;
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
    if (video?.duration) {
      setProgress((video.currentTime / video.duration) * 100);
    }
  };

  return (
    <div
      className={`clip-preview${isDemoMode() ? ' demo-cover' : ''}`}
      onMouseEnter={() => setIsHovering(true)}
      onMouseLeave={() => setIsHovering(false)}
    >
      <div className="blur-bg-container">
        <img src={clip.thumbnail_url} alt="" draggable={false} decoding="async" />
      </div>
      <img
        src={clip.thumbnail_url}
        className="clip-thumbnail"
        alt={clip.title}
        draggable={false}
        decoding="sync"
        fetchPriority="high"
        style={{ opacity: isPlaying ? 0 : 1 }}
      />
      <video
        ref={videoRef}
        src={videoSrc || undefined}
        className={`video-player ${isPlaying ? 'playing' : ''}${isDemoMode() ? ' demo-src' : ''}`}
        loop
        muted={forceMuted}
        autoPlay={Boolean(autoPlay)}
        playsInline
        onTimeUpdate={handleTimeUpdate}
        preload="auto"
      />
      {isDemoMode() && (
        <canvas
          ref={canvasRef}
          className={`video-player demo-canvas ${isPlaying ? 'playing' : ''}`}
        />
      )}
      <div className={`video-loading ${isLoading ? 'active' : ''}`} />

      <button
        className="fullscreen-btn"
        onClick={(e) => {
          e.stopPropagation();
          onOpenTheater();
        }}
        title="Theater Mode"
      >
        ⛶
      </button>
      <button className="play-pause-btn" onClick={handlePlayPause} title="Play/Pause">
        {isPlaying ? '⏸' : '▶'}
      </button>

      <div className="volume-control">
        <button className="volume-btn" onClick={toggleMute}>
          <span>{volume === 0 ? '🔇' : '🔊'}</span>
        </button>
        <input
          type="range"
          className="volume-slider"
          min="0"
          max="100"
          value={volume}
          onChange={handleVolumeChange}
        />
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
          style={{
            background: `linear-gradient(to right, #ec4899 ${progress}%, rgba(255,255,255,0.2) ${progress}%)`,
          }}
        />
      </div>

      {children}
    </div>
  );
});
