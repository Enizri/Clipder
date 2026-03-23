"""
Clipder Pro - Twitch clip discovery
Features: No cropping, clean professional design, proper spacing, 100% full-frame video, timeline scrubber, flawless drag physics
"""

import threading
from flask import Flask, jsonify, request
from pathlib import Path
import json
import sys

sys.path.insert(0, str(Path(__file__).parent))

try:
    from test import (
        Config, TwitchClient, StateManager, GroqClient, 
        VideoProcessor, YouTubeUploader, TikTokUploader
    )
    config = Config.from_env()
    twitch_client = TwitchClient(config)
    state_manager = StateManager(config)
    groq_client = GroqClient(config)
    video_processor = VideoProcessor(config)
    youtube = YouTubeUploader(config)
    tiktok = TikTokUploader(config)
    bot_initialized = True
except Exception as e:
    print(f"⚠️  Bot components not initialized: {e}")
    bot_initialized = False

app = Flask(__name__)
clips_queue = []

def fetch_clips():
    global clips_queue
    clips_queue = []
    
    if not bot_initialized:
        return 0
    
    clips_by_channel = {}
    
    for channel in config.twitch_channels:
        broadcaster_id = twitch_client.get_broadcaster_id(channel)
        if broadcaster_id:
            all_clips = twitch_client.get_recent_clips(broadcaster_id, hours_back=72, fetch_count=100)
            
            channel_clips = []
            for clip in all_clips:
                if not state_manager.is_processed(clip["id"]):
                    channel_clips.append({
                        'id': clip['id'],
                        'title': clip['title'],
                        'url': clip['url'],
                        'thumbnail_url': clip['thumbnail_url'],
                        'view_count': clip['view_count'],
                        'creator_name': clip['creator_name'],
                        'duration': clip['duration'],
                        'created_at': clip['created_at'],
                        'channel': channel
                    })
            
            channel_clips.sort(key=lambda x: x['view_count'], reverse=True)
            clips_by_channel[channel] = channel_clips
    
    mixed_clips = []
    max_per_channel = 10
    
    for channel, channel_clips in clips_by_channel.items():
        for clip in channel_clips[:max_per_channel]:
            mixed_clips.append(clip)
    
    mixed_clips.sort(key=lambda x: x['view_count'], reverse=True)
    
    final_queue = []
    channel_queues = {ch: clips[:max_per_channel] for ch, clips in clips_by_channel.items()}
    
    while any(channel_queues.values()):
        for channel in config.twitch_channels:
            if channel in channel_queues and channel_queues[channel]:
                final_queue.append(channel_queues[channel].pop(0))
    
    clips_queue = final_queue
    return len(clips_queue)


HTML_TEMPLATE = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Clipder</title>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap');
        
        * { margin: 0; padding: 0; box-sizing: border-box; }
        
        body {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
            background: #0a0a0a;
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            overflow: hidden;
            color: #ffffff;
            position: relative;
        }
        
        body::before {
            content: '';
            position: fixed;
            top: 0; left: 0;
            width: 100%; height: 100%;
            background: radial-gradient(circle at 20% 50%, rgba(120, 60, 220, 0.06) 0%, transparent 50%),
                        radial-gradient(circle at 80% 50%, rgba(220, 60, 120, 0.06) 0%, transparent 50%);
            pointer-events: none;
            z-index: 0;
        }
        
        .app-container {
            width: 100%; max-width: 480px; height: 100vh;
            display: flex; flex-direction: column; padding: 0;
            position: relative; z-index: 1;
        }
        
        header { 
            position: fixed; top: 0; left: 50%; transform: translateX(-50%);
            width: 100%; max-width: 480px; padding: 20px 24px;
            background: linear-gradient(to bottom, rgba(10, 10, 10, 0.98) 60%, transparent 100%);
            backdrop-filter: blur(20px); z-index: 100;
            border-bottom: 1px solid rgba(255, 255, 255, 0.03);
        }
        
        .header-content { display: flex; justify-content: space-between; align-items: center; margin-bottom: 14px; }
        header h1 { font-size: 1.6em; font-weight: 900; color: #ffffff; letter-spacing: -0.5px; }
        
        .logo-accent {
            background: linear-gradient(135deg, #8b5cf6, #ec4899);
            -webkit-background-clip: text; -webkit-text-fill-color: transparent;
        }
        
        .stats { display: flex; gap: 10px; font-size: 0.75em; color: #666; font-weight: 600; }
        .stat-item { padding: 4px 10px; background: rgba(255, 255, 255, 0.02); border-radius: 12px; border: 1px solid rgba(255, 255, 255, 0.04); }
        .stat-value { color: #ffffff; margin-left: 4px; }
        
        .swipe-container { 
            flex: 1; position: relative; padding: 100px 20px 160px 20px;
            display: flex; align-items: center; justify-content: center;
        }
        
        #card-stack { position: relative; width: 100%; max-width: 400px; height: 100%; max-height: 680px; }
        
        .clip-card {
            position: absolute; width: 100%; height: 100%;
            background: #141414; border-radius: 16px;
            box-shadow: 0 20px 60px rgba(0, 0, 0, 0.6), 0 0 0 1px rgba(255, 255, 255, 0.05);
            cursor: grab; overflow: visible; transform-origin: 50% 50%;
            transition: transform 0.3s ease-out, opacity 0.3s ease-out;
            will-change: transform, opacity;
            user-select: none;
        }
        
        .clip-card.top-card:hover:not(.dragging) {
            transform: translateY(-2px) !important;
            box-shadow: 0 25px 70px rgba(0, 0, 0, 0.7), 0 0 0 1px rgba(139, 92, 246, 0.2);
            z-index: 999 !important;
        }
        
        .clip-card.dragging { cursor: grabbing; transition: none !important; }

        .clip-preview {
            position: relative; width: 100%; aspect-ratio: 9/16;
            background: #000000; border-radius: 16px 16px 0 0; overflow: hidden;
            transform-origin: bottom center; 
            transition: transform 0.3s cubic-bezier(0.34, 1.56, 0.64, 1), border-radius 0.3s;
            z-index: 2;
        }
        
        .clip-card.top-card:hover:not(.dragging) .clip-preview {
            transform: scale(1.25) translateY(-12px);
            border-radius: 12px;
            box-shadow: 0 40px 80px rgba(0,0,0,1), 0 0 0 1px rgba(139, 92, 246, 0.4);
            z-index: 10;
        }
        
        .clip-card:not(.top-card) .blur-bg-container { display: none !important; }
        
        .blur-bg-container {
            position: absolute; top: -10%; left: -10%; width: 120%; height: 120%;
            z-index: 0; filter: blur(25px); opacity: 0.4; 
            transition: opacity 0.3s ease;
        }
        
        .blur-bg-container img { width: 100%; height: 100%; object-fit: cover; }
        
        .clip-thumbnail, .video-player {
            position: absolute; top: 0; left: 0; width: 100%; height: 100%;
            object-fit: contain !important; 
            z-index: 1;
        }
        
        .clip-thumbnail { transition: opacity 0.3s ease; z-index: 2; }
        
        .video-player { z-index: 1; opacity: 0; transition: opacity 0.3s ease; }
        .video-player.playing { opacity: 1; }
        
        .video-loading {
            position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%);
            width: 36px; height: 36px; border: 2px solid rgba(255, 255, 255, 0.1);
            border-top-color: #8b5cf6; border-radius: 50%;
            animation: spin 0.7s linear infinite; z-index: 5; opacity: 0; transition: opacity 0.3s;
        }
        
        .video-loading.active { opacity: 1; }
        @keyframes spin { to { transform: translate(-50%, -50%) rotate(360deg); } }
        
        .fullscreen-btn {
            position: absolute; top: 10px; right: 10px; width: 32px; height: 32px;
            background: rgba(0, 0, 0, 0.5); backdrop-filter: blur(10px);
            border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 6px;
            color: white; font-size: 14px; cursor: pointer; display: flex;
            align-items: center; justify-content: center; opacity: 0; transition: all 0.2s; z-index: 10;
        }
        
        .clip-card.top-card:hover:not(.dragging) .fullscreen-btn { opacity: 1; }
        .fullscreen-btn:hover { background: rgba(0, 0, 0, 0.7); }
        
        /* VOLUME CONTROL - Moved up so it doesn't hit the timeline */
        .volume-control {
            position: absolute; bottom: 55px; right: 10px; display: flex; align-items: center; gap: 0;
            background: rgba(0, 0, 0, 0.5); backdrop-filter: blur(10px); padding: 0;
            border-radius: 50px; border: 1px solid rgba(255, 255, 255, 0.1); opacity: 0;
            transition: all 0.2s; z-index: 10; overflow: hidden; width: 32px; height: 32px;
        }
        
        .clip-card.top-card:hover:not(.dragging) .volume-control { opacity: 1; }
        .volume-control:hover { width: 130px; padding-right: 10px; gap: 8px; background: rgba(0, 0, 0, 0.7); }
        
        .volume-btn {
            width: 32px; height: 32px; background: transparent; border: none; color: white;
            font-size: 14px; cursor: pointer; display: flex; align-items: center; justify-content: center; flex-shrink: 0;
        }
        
        .volume-slider {
            width: 70px; height: 3px; -webkit-appearance: none; appearance: none;
            background: rgba(255, 255, 255, 0.15); border-radius: 2px; outline: none; cursor: pointer;
            opacity: 0; transition: opacity 0.2s;
        }
        
        .volume-control:hover .volume-slider { opacity: 1; }
        .volume-slider::-webkit-slider-thumb { -webkit-appearance: none; width: 10px; height: 10px; background: white; border-radius: 50%; cursor: pointer; }
        .volume-slider::-moz-range-thumb { width: 10px; height: 10px; background: white; border-radius: 50%; cursor: pointer; border: none; }

        /* JITTER-FREE CUSTOM TIMELINE */
        .progress-container {
            position: absolute; 
            bottom: 25px; /* Moved safely up from the edge! */
            left: 20px; 
            width: calc(100% - 40px); /* Adds nice padding to the sides */
            height: 24px; /* Large invisible hit-box so mouse doesn't slip */
            display: flex; align-items: center; z-index: 15; opacity: 0; 
            transition: opacity 0.2s;
        }
        
        .clip-card.top-card:hover:not(.dragging) .progress-container { opacity: 1; }
        
        .progress-slider {
            width: 100%; height: 5px; -webkit-appearance: none; appearance: none;
            background: rgba(255, 255, 255, 0.2); outline: none; margin: 0; cursor: pointer;
            border-radius: 10px; backdrop-filter: blur(4px);
            transition: height 0.2s;
        }
        
        /* Expands when hovered for easier grabbing */
        .progress-container:hover .progress-slider { height: 9px; }
        
        .progress-slider::-webkit-slider-thumb {
            -webkit-appearance: none; width: 16px; height: 16px; background: #ffffff;
            border-radius: 50%; cursor: pointer; opacity: 0; 
            box-shadow: 0 2px 8px rgba(0,0,0,0.5);
            transition: opacity 0.2s, transform 0.2s;
        }
        
        .progress-container:hover .progress-slider::-webkit-slider-thumb { 
            opacity: 1; transform: scale(1.1); 
        }

        .clip-info { 
            position: relative; padding: 18px; background: #141414; 
            border-radius: 0 0 16px 16px; z-index: 1; 
        }
        .clip-title { font-size: 1em; font-weight: 600; margin-bottom: 10px; color: #ffffff; line-height: 1.4; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }
        .clip-meta { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }
        .views-badge, .duration-badge { display: inline-flex; align-items: center; gap: 4px; background: rgba(255, 255, 255, 0.03); border: 1px solid rgba(255, 255, 255, 0.05); color: #666; padding: 4px 8px; border-radius: 10px; font-weight: 600; font-size: 0.75em; }
        .creator { color: #555; font-size: 0.8em; font-weight: 500; }
        
        .action-buttons { 
            position: fixed; bottom: 0; left: 50%; transform: translateX(-50%); width: 100%; max-width: 480px;
            display: flex; justify-content: center; align-items: center; gap: 16px; padding: 24px 20px 30px 20px;
            background: linear-gradient(to top, rgba(10, 10, 10, 0.98) 60%, transparent 100%);
            backdrop-filter: blur(20px); z-index: 100; border-top: 1px solid rgba(255, 255, 255, 0.03);
        }
        
        .btn-reject, .btn-accept {
            width: 58px; height: 58px; border-radius: 50%; border: 2px solid; cursor: pointer; font-size: 1.4em; 
            display: flex; align-items: center; justify-content: center; transition: all 0.2s;
        }
        .btn-reject { background: rgba(239, 68, 68, 0.08); border-color: rgba(239, 68, 68, 0.25); color: #ef4444; }
        .btn-accept { background: rgba(16, 185, 129, 0.08); border-color: rgba(16, 185, 129, 0.25); color: #10b981; }
        .btn-reject:hover { transform: scale(1.08); background: rgba(239, 68, 68, 0.15); border-color: rgba(239, 68, 68, 0.4); }
        .btn-accept:hover { transform: scale(1.08); background: rgba(16, 185, 129, 0.15); border-color: rgba(16, 185, 129, 0.4); }
        .btn-reject:active, .btn-accept:active { transform: scale(0.96); }
        
        .btn-process {
            background: linear-gradient(135deg, #8b5cf6, #ec4899); color: white; border: none; padding: 14px 28px; 
            border-radius: 14px; font-size: 0.9em; font-weight: 700; cursor: pointer; box-shadow: 0 6px 20px rgba(139, 92, 246, 0.35);
            transition: all 0.2s; width: 100%; max-width: 260px; margin: 12px auto 0 auto; display: block;
        }
        .btn-process:hover { transform: translateY(-2px); box-shadow: 0 8px 28px rgba(139, 92, 246, 0.45); }
        .hidden { display: none !important; }
        
        #loading {
            position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(10, 10, 10, 0.98); 
            backdrop-filter: blur(10px); display: flex; flex-direction: column; align-items: center; justify-content: center; z-index: 9999;
        }
        .spinner { width: 44px; height: 44px; border: 3px solid rgba(255,255,255,0.08); border-top-color: #8b5cf6; border-radius: 50%; animation: spin 0.7s linear infinite; }
        
        #empty-state { text-align: center; padding: 50px 20px; }
        #empty-state h2 { font-size: 1.6em; margin-bottom: 10px; font-weight: 800; color: #ffffff; }
        #empty-state p { color: #555; margin-bottom: 20px; }
        .refresh-btn { background: rgba(255, 255, 255, 0.08); color: white; border: 1px solid rgba(255, 255, 255, 0.15); padding: 12px 24px; border-radius: 10px; font-weight: 600; cursor: pointer; transition: all 0.2s; }
        .refresh-btn:hover { background: rgba(255, 255, 255, 0.12); }
        
        .swipe-hint {
            position: absolute; top: 30px; font-size: 2.2em; font-weight: 900; padding: 4px 12px;
            border-radius: 10px; opacity: 0; transition: opacity 0.2s; pointer-events: none; z-index: 100;
        }
        .swipe-hint.left { left: 16px; color: #ef4444; background: rgba(239, 68, 68, 0.12); border: 2px solid rgba(239, 68, 68, 0.25); }
        .swipe-hint.right { right: 16px; color: #10b981; background: rgba(16, 185, 129, 0.12); border: 2px solid rgba(16, 185, 129, 0.25); }
        .clip-card.swiping-left .swipe-hint.left, .clip-card.swiping-right .swipe-hint.right { opacity: 1; }
    </style>
</head>
<body>
    <div class="app-container">
        <header>
            <div class="header-content">
                <h1>Clip<span class="logo-accent">der</span></h1>
                <div class="stats">
                    <div class="stat-item"><span id="queue-count">0</span></div>
                    <div class="stat-item" style="color: #10b981;"><span id="accepted-count">0</span> ✓</div>
                </div>
            </div>
        </header>
        
        <div class="swipe-container">
            <div id="card-stack"></div>
            <div id="empty-state" class="hidden">
                <h2>All Done</h2>
                <p>No more clips to review</p>
                <button onclick="location.reload()" class="refresh-btn">Refresh</button>
            </div>
        </div>
        
        <div class="action-buttons">
            <button class="btn-reject" onclick="swipeLeft()">✕</button>
            <button class="btn-accept" onclick="swipeRight()">♥</button>
        </div>
        
        <div style="padding: 0 20px;">
            <button id="process-btn" class="btn-process hidden" onclick="processAccepted()">
                Process <span id="process-count">0</span> Clips
            </button>
        </div>
    </div>
    
    <div id="loading" class="hidden">
        <div class="spinner"></div>
        <p style="margin-top: 16px; font-weight: 600; color: #666;">Loading...</p>
    </div>

    <script>
        let clips = [];
        let currentIndex = 0;
        let acceptedClips = [];
        let isDragging = false;
        let isSwiping = false; 
        
        document.addEventListener('DOMContentLoaded', loadClips);
        
        async function loadClips() {
            showLoading(true);
            try {
                const res = await fetch('/api/clips');
                const data = await res.json();
                clips = data.clips;
                currentIndex = 0;
                updateStats();
                
                const stack = document.getElementById('card-stack');
                stack.innerHTML = '';
                if (clips.length === 0) {
                    showEmptyState();
                    return;
                }
                
                for (let i = 0; i < Math.min(3, clips.length); i++) {
                    const card = createCard(clips[i], i);
                    stack.appendChild(card);
                }
                
                setupTopCard();
            } catch(e) {
                console.error(e);
                alert('Failed to load clips');
            } finally {
                showLoading(false);
            }
        }
        
        function createCard(clip, stackIndex) {
            const card = document.createElement('div');
            card.className = 'clip-card';
            card.dataset.clipId = clip.id;
            card.dataset.clipUrl = clip.url;
            
            card.style.zIndex = 100 - stackIndex;
            card.style.transform = `scale(${1 - stackIndex * 0.03}) translateY(${stackIndex * 10}px)`;
            card.style.opacity = 1 - stackIndex * 0.12;
            
            const views = clip.view_count >= 1000 ? (clip.view_count/1000).toFixed(1) + 'K' : clip.view_count;
            
            card.innerHTML = `
                <div class="clip-preview">
                    <div class="blur-bg-container">
                        <img src="${clip.thumbnail_url}" draggable="false">
                    </div>
                    <img src="${clip.thumbnail_url}" class="clip-thumbnail" draggable="false">
                    <video class="video-player" preload="metadata" loop playsinline ontimeupdate="updateProgress(this)"></video>
                    <div class="video-loading"></div>
                    <button class="fullscreen-btn" onclick="event.stopPropagation(); openFullscreen(this)" title="Fullscreen">⛶</button>
                    <div class="volume-control">
                        <button class="volume-btn" onclick="event.stopPropagation(); toggleMute(this)">
                            <span class="volume-icon">🔊</span>
                        </button>
                        <input type="range" class="volume-slider" min="0" max="100" value="30" 
                               oninput="event.stopPropagation(); changeVolume(this)">
                    </div>
                    <div class="progress-container">
                        <input type="range" class="progress-slider" min="0" max="100" value="0" step="0.1" 
                               oninput="event.stopPropagation(); seekVideo(this)">
                    </div>
                </div>
                <div class="clip-info">
                    <div class="clip-title">${clip.title}</div>
                    <div class="creator">${clip.creator_name} • ${clip.channel}</div>
                    <div class="clip-meta">
                        <span class="views-badge">👁️ ${views}</span>
                        <span class="duration-badge">⏱️ ${Math.floor(clip.duration)}s</span>
                    </div>
                </div>
                <div class="swipe-hint left">NOPE</div>
                <div class="swipe-hint right">LIKE</div>
            `;
            return card;
        }

        // Dynamic Color Fill for Custom Timeline
        function updateProgress(video) {
            const card = video.closest('.clip-card');
            if (!card) return;
            const slider = card.querySelector('.progress-slider');
            if (slider && video.duration) {
                const percent = (video.currentTime / video.duration) * 100;
                slider.value = percent;
                // Vibrant Pink/Purple Gradient Fill
                slider.style.background = `linear-gradient(to right, #ec4899 ${percent}%, rgba(255, 255, 255, 0.2) ${percent}%)`;
            }
        }

        function seekVideo(slider) {
            const card = slider.closest('.clip-card');
            const video = card.querySelector('.video-player');
            if (video && video.duration) {
                const seekTime = (slider.value / 100) * video.duration;
                video.currentTime = seekTime;
                slider.style.background = `linear-gradient(to right, #ec4899 ${slider.value}%, rgba(255, 255, 255, 0.2) ${slider.value}%)`;
            }
        }

        function setupTopCard() {
            const stack = document.getElementById('card-stack');
            const allCards = stack.querySelectorAll('.clip-card');
            
            allCards.forEach((card, index) => {
                if (index === 0) {
                    card.classList.add('top-card'); 
                    card.style.pointerEvents = 'auto';
                    makeCardSwipeable(card);
                    setupVideoHover(card);
                    preloadVideoUrl(card);
                } else {
                    card.classList.remove('top-card');
                    card.style.pointerEvents = 'none';
                }
            });
        }

        function advanceQueue(removedCard) {
            const stack = document.getElementById('card-stack');
            if (removedCard) {
                removedCard.remove();
            }
            
            currentIndex++;
            updateStats();
            
            const nextIndex = currentIndex + 2; 
            if (nextIndex < clips.length) {
                const newCard = createCard(clips[nextIndex], 2);
                newCard.style.pointerEvents = 'none';
                stack.appendChild(newCard);
            }
            
            const remainingCards = stack.querySelectorAll('.clip-card');
            if (remainingCards.length === 0) {
                showEmptyState();
                return;
            }
            
            remainingCards.forEach((card, index) => {
                card.style.zIndex = 100 - index;
                card.style.transform = `scale(${1 - index * 0.03}) translateY(${index * 10}px)`;
                card.style.opacity = 1 - index * 0.12;
            });
            
            setTimeout(() => { 
                setupTopCard(); 
                isSwiping = false; 
            }, 50);
        }

        async function preloadVideoUrl(card) {
            if (card.dataset.videoUrlFetched) return;
            const video = card.querySelector('.video-player');
            try {
                const response = await fetch(`/api/clip/${card.dataset.clipId}/video-url`);
                const data = await response.json();
                if (data.video_url) {
                    video.src = data.video_url;
                    video.preload = 'auto';
                    card.dataset.videoUrlFetched = 'true';
                }
            } catch (e) { console.error('Preload failed', e); }
        }
        
        function setupVideoHover(card) {
            if (card.dataset.hoverSetup === 'true') return;
            card.dataset.hoverSetup = 'true';
            
            const preview = card.querySelector('.clip-preview');
            preview.addEventListener('mouseenter', () => {
                if (isDragging || isSwiping) return;
                startVideoPlay(card);
            });
            preview.addEventListener('mouseleave', () => {
                if (!isDragging) stopVideoPlay(card);
            });
        }

        async function startVideoPlay(card) {
            if (isDragging || isSwiping) return;
            
            const video = card.querySelector('.video-player');
            const thumbnail = card.querySelector('.clip-thumbnail');
            const loading = card.querySelector('.video-loading');
            const icon = card.querySelector('.volume-icon');
            
            const attemptPlay = async () => {
                try {
                    video.muted = false;
                    video.volume = 0.3;
                    await video.play();
                    icon.textContent = '🔊';
                } catch (err) {
                    video.muted = true;
                    try {
                        await video.play();
                        icon.textContent = '🔇';
                    } catch (err2) { console.log("All autoplay blocked"); }
                }
                video.classList.add('playing');
                thumbnail.style.opacity = '0';
                loading.classList.remove('active');
            };

            if (video.src && video.readyState >= 2) {
                attemptPlay();
                return;
            }
            
            loading.classList.add('active');
            try {
                const response = await fetch(`/api/clip/${card.dataset.clipId}/video-url`);
                const data = await response.json();
                if (data.video_url) {
                    video.src = data.video_url;
                    video.addEventListener('loadeddata', attemptPlay, { once: true });
                }
            } catch (e) { loading.classList.remove('active'); }
        }

        function stopVideoPlay(card) {
            const video = card.querySelector('.video-player');
            const thumbnail = card.querySelector('.clip-thumbnail');
            if (video) {
                video.pause();
                video.muted = true;
                video.classList.remove('playing');
            }
            if (thumbnail) thumbnail.style.opacity = '1';
        }
        
        function openFullscreen(btn) {
            const card = btn.closest('.clip-card');
            const video = card.querySelector('.video-player');
            if (video.requestFullscreen) { video.requestFullscreen(); } 
            else if (video.webkitRequestFullscreen) { video.webkitRequestFullscreen(); } 
            else if (video.msRequestFullscreen) { video.msRequestFullscreen(); }
        }
        
        function toggleMute(btn) {
            const card = btn.closest('.clip-card');
            const video = card.querySelector('.video-player');
            const icon = btn.querySelector('.volume-icon');
            const slider = card.querySelector('.volume-slider');
            
            video.muted = !video.muted;
            icon.textContent = video.muted ? '🔇' : '🔊';
            if(!video.muted && video.volume === 0) {
                video.volume = 0.3;
                slider.value = 30;
            }
        }
        
        function changeVolume(slider) {
            const card = slider.closest('.clip-card');
            const video = card.querySelector('.video-player');
            const icon = card.querySelector('.volume-icon');
            video.volume = slider.value / 100;
            if (slider.value == 0) {
                icon.textContent = '🔇'; video.muted = true;
            } else {
                icon.textContent = '🔊'; video.muted = false;
            }
        }
        
        function makeCardSwipeable(card) {
            if (card.dataset.swipeable === 'true') return;
            card.dataset.swipeable = 'true';
            
            let startX = 0, currentX = 0; let startTime = 0;
            let ticking = false; 
            
            const doDrag = (e) => {
                if (!isDragging) return;
                e.preventDefault();
                const point = e.type.includes('mouse') ? e : e.touches[0];
                currentX = point.clientX;
                
                if (!ticking) {
                    window.requestAnimationFrame(() => {
                        if (!isDragging) return;
                        const deltaX = currentX - startX; const rotation = deltaX * 0.03;
                        card.style.transform = `translate(${deltaX}px, 0) rotate(${rotation}deg)`;
                        if (deltaX > 70) { card.classList.add('swiping-right'); card.classList.remove('swiping-left'); } 
                        else if (deltaX < -70) { card.classList.add('swiping-left'); card.classList.remove('swiping-right'); } 
                        else { card.classList.remove('swiping-left', 'swiping-right'); }
                        ticking = false;
                    });
                    ticking = true;
                }
            };
            
            const stopDrag = () => {
                if (!isDragging) return;
                isDragging = false; 
                
                document.removeEventListener('mousemove', doDrag); 
                document.removeEventListener('mouseup', stopDrag);
                document.removeEventListener('touchmove', doDrag); 
                document.removeEventListener('touchend', stopDrag);
                
                card.classList.remove('dragging');
                
                const deltaX = currentX - startX; const duration = Date.now() - startTime; const velocity = Math.abs(deltaX) / duration;
                
                if (Math.abs(deltaX) > 100 || velocity > 0.5) { 
                    card.classList.remove('top-card');
                    animateSwipe(card, deltaX > 0 ? 'right' : 'left'); 
                } else {
                    card.style.transform = ''; 
                    card.classList.remove('swiping-left', 'swiping-right');
                }
            };

            const startDrag = (e) => {
                if (e.target.closest('.volume-control') || e.target.closest('.fullscreen-btn') || e.target.closest('.progress-container')) return;
                if (isSwiping) return; 
                
                isDragging = true; startTime = Date.now(); card.classList.add('dragging');
                const point = e.type.includes('mouse') ? e : e.touches[0];
                startX = point.clientX; currentX = startX;
                stopVideoPlay(card);
                
                document.addEventListener('mousemove', doDrag); 
                document.addEventListener('mouseup', stopDrag);
                document.addEventListener('touchmove', doDrag, {passive: false}); 
                document.addEventListener('touchend', stopDrag);
            };
            
            card.addEventListener('mousedown', startDrag); 
            card.addEventListener('touchstart', startDrag, {passive: false}); 
        }
        
        function animateSwipe(card, direction) {
            if (isSwiping) return;
            isSwiping = true; 

            try {
                const video = card.querySelector('.video-player');
                if (video) {
                    video.pause();
                    video.muted = true;
                    video.removeAttribute('src'); 
                    video.load(); 
                }
            } catch(e) {}

            const distance = direction === 'right' ? window.innerWidth : -window.innerWidth; 
            const rotation = direction === 'right' ? 30 : -30;
            
            card.style.transition = 'transform 0.3s cubic-bezier(0.25, 0.46, 0.45, 0.94), opacity 0.3s';
            card.style.transform = `translate(${distance}px, -100px) rotate(${rotation}deg)`;
            card.style.opacity = '0';
            card.classList.remove('top-card'); 
            
            setTimeout(() => {
                advanceQueue(card); 
                handleSwipe(card.dataset.clipId, direction);
            }, 300);
        }
        
        async function handleSwipe(clipId, direction) {
            const action = direction === 'right' ? 'accept' : 'reject';
            await fetch(`/api/clip/${clipId}/action`, {
                method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({action})
            });
            if (action === 'accept') { acceptedClips.push(clipId); updateProcessButton(); }
        }
        
        function swipeLeft() { 
            const card = document.querySelector('.clip-card.top-card'); 
            if (card && !isDragging && !isSwiping) {
                card.classList.remove('top-card'); 
                animateSwipe(card, 'left'); 
            }
        }
        function swipeRight() { 
            const card = document.querySelector('.clip-card.top-card'); 
            if (card && !isDragging && !isSwiping) {
                card.classList.remove('top-card'); 
                animateSwipe(card, 'right'); 
            }
        }
        
        function updateStats() {
            document.getElementById('queue-count').textContent = clips.length - currentIndex;
            document.getElementById('accepted-count').textContent = acceptedClips.length;
        }
        
        function updateProcessButton() {
            const btn = document.getElementById('process-btn');
            document.getElementById('process-count').textContent = acceptedClips.length;
            btn.classList.toggle('hidden', acceptedClips.length === 0);
        }
        
        function showEmptyState() {
            document.getElementById('card-stack').classList.add('hidden');
            document.querySelector('.action-buttons').classList.add('hidden');
            document.getElementById('empty-state').classList.remove('hidden');
        }
        
        function showLoading(show) { document.getElementById('loading').classList.toggle('hidden', !show); }
        
        async function processAccepted() {
            if (!acceptedClips.length) return;
            showLoading(true);
            try {
                await fetch('/api/process', {
                    method: 'POST', headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({clip_ids: acceptedClips})
                });
                alert(`✅ Processing ${acceptedClips.length} clips!`);
                acceptedClips = []; updateProcessButton();
            } catch(e) { alert('Error processing clips'); } 
            finally { showLoading(false); }
        }
        
        document.addEventListener('keydown', e => {
            if (e.key === 'ArrowLeft') swipeLeft();
            if (e.key === 'ArrowRight') swipeRight();
        });
    </script>
</body>
</html>'''
@app.route('/')
def index():
    fetch_clips()
    return HTML_TEMPLATE

@app.route('/api/clips')
def get_clips():
    return jsonify({'clips': clips_queue, 'total': len(clips_queue)})

@app.route('/api/clip/<clip_id>/video-url')
def get_clip_video_url(clip_id):
    """Get direct video URL"""
    try:
        clip = next((c for c in clips_queue if c['id'] == clip_id), None)
        if not clip:
            return jsonify({'error': 'Clip not found'}), 404
        
        import yt_dlp
        
        ydl_opts = {
            'format': 'best[ext=mp4]/best',
            'quiet': True,
            'no_warnings': True,
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(clip['url'], download=False)
            video_url = info.get('url')
            
            return jsonify({'video_url': video_url, 'title': clip['title']})
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/clip/<clip_id>/action', methods=['POST'])
def clip_action(clip_id):
    data = request.json
    action = data.get('action')
    
    if action == 'accept':
        return jsonify({'status': 'accepted', 'clip_id': clip_id})
    else:
        if bot_initialized:
            state_manager.mark_processed(clip_id)
        return jsonify({'status': 'rejected', 'clip_id': clip_id})

def background_processor(clip_ids):
    print(f"\n🚀 Processing {len(clip_ids)} clips...")
    clips_to_process = [c for c in clips_queue if c['id'] in clip_ids]
    
    for idx, clip in enumerate(clips_to_process, 1):
        print(f"\n[{idx}/{len(clips_to_process)}] 🎬 {clip['title']}")
        
        try:
            download_path = video_processor.download_clip(clip['url'], clip['id'])
            if not download_path: continue
            
            transcript = groq_client.transcribe_audio(download_path)
            metadata = groq_client.analyze_clip(transcript, clip['title'], clip['view_count'])
            
            processed_path = video_processor.create_tiktok_style_video(
                download_path, clip['id'], clip['title'], metadata['description']
            )
            
            if processed_path:
                youtube.upload(processed_path, metadata['title'], metadata['description'])
                tiktok.upload(processed_path, metadata['title'], metadata['description'])
                state_manager.mark_processed(clip['id'])
                
                if download_path.exists(): download_path.unlink()
                if processed_path.exists(): processed_path.unlink()
        except Exception as e:
            print(f" ❌ Error: {e}")
    
    print("\n🎉 Done!")

@app.route('/api/process', methods=['POST'])
def process_clips():
    data = request.json
    accepted = data.get('clip_ids', [])
    
    if not accepted:
        return jsonify({'status': 'empty'})
        
    thread = threading.Thread(target=background_processor, args=(accepted,))
    thread.daemon = True
    thread.start()
    
    return jsonify({'status': 'processing', 'count': len(accepted)})

if __name__ == '__main__':
    print("\n" + "="*60)
    print("🔥 Clipder Pro - Professional Edition")
    print("="*60)
    print(f"Status: {bot_initialized}")
    print("✅ No video cropping - full aspect ratio")
    print("✅ Clean professional design")
    print("✅ Fixed header & footer - no overlap")
    print("✅ Instant video playback")
    print("Open: http://localhost:5000")
    print("="*60 + "\n")
    app.run(debug=True, host='0.0.0.0', port=5000)