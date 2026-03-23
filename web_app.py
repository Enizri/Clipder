"""
Clipder - Swipe through Twitch clips
All bugs fixed + Fullscreen feature
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
    <title>Clipder - Swipe for Clips</title>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@400;500;600;700;800&display=swap');
        
        * { margin: 0; padding: 0; box-sizing: border-box; }
        
        body {
            font-family: 'Outfit', sans-serif;
            background: radial-gradient(ellipse at top, #1e1b4b, #0f172a);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            overflow: hidden;
            color: #f8fafc;
            position: relative;
        }
        
        body::before {
            content: '';
            position: fixed;
            top: -50%; left: -50%;
            width: 200%; height: 200%;
            background: radial-gradient(circle, rgba(99, 102, 241, 0.1) 0%, transparent 70%);
            animation: rotate 20s linear infinite;
            pointer-events: none;
        }
        
        @keyframes rotate {
            from { transform: rotate(0deg); }
            to { transform: rotate(360deg); }
        }
        
        .app-container {
            width: 100%;
            max-width: 440px;
            height: 95vh;
            display: flex;
            flex-direction: column;
            padding: 20px;
            position: relative;
            z-index: 1;
        }
        
        header { 
            text-align: center; 
            margin-bottom: 25px;
            animation: fadeInDown 0.6s ease;
        }
        
        @keyframes fadeInDown {
            from { opacity: 0; transform: translateY(-20px); }
            to { opacity: 1; transform: translateY(0); }
        }
        
        header h1 { 
            font-size: 2.2em; 
            margin-bottom: 8px; 
            font-weight: 800;
            background: linear-gradient(135deg, #a78bfa, #ec4899);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            letter-spacing: -1px;
        }
        
        .stats { 
            display: flex; 
            justify-content: center; 
            gap: 20px; 
            font-size: 0.9em; 
            color: #cbd5e1;
            font-weight: 600;
        }
        
        .stat-item {
            display: flex;
            align-items: center;
            gap: 6px;
            padding: 6px 14px;
            background: rgba(255, 255, 255, 0.05);
            border-radius: 20px;
            backdrop-filter: blur(10px);
        }
        
        .swipe-container { 
            flex: 1; 
            position: relative; 
            margin-bottom: 30px;
            perspective: 1500px;
        }
        
        #card-stack { 
            position: relative; 
            width: 100%; 
            height: 100%;
        }
        
        .clip-card {
            position: absolute;
            width: 100%;
            height: 100%;
            background: linear-gradient(145deg, #1e293b, #0f172a);
            border-radius: 24px;
            box-shadow: 
                0 20px 60px rgba(0, 0, 0, 0.5),
                inset 0 1px 0 rgba(255, 255, 255, 0.1);
            cursor: grab;
            overflow: hidden;
            transform-origin: 50% 50%;
            transition: transform 0.6s cubic-bezier(0.34, 1.56, 0.64, 1), 
                        box-shadow 0.6s ease;
            user-select: none;
            border: 1px solid rgba(255, 255, 255, 0.1);
        }
        
        /* SMOOTH HOVER - AESTHETIC POP */
        .clip-card:hover:not(.dragging) {
            transform: scale(1.05) translateY(-10px) !important;
            box-shadow: 
                0 30px 80px rgba(99, 102, 241, 0.3),
                0 0 60px rgba(236, 72, 153, 0.2),
                inset 0 1px 0 rgba(255, 255, 255, 0.2);
            z-index: 1000 !important;
            border-color: rgba(167, 139, 250, 0.4);
        }
        
        .clip-card.dragging {
            cursor: grabbing;
            transition: none !important;
        }

        .clip-preview {
            position: relative;
            width: 100%;
            height: 65%;
            background: #000;
            border-radius: 24px 24px 0 0;
            overflow: hidden;
        }
        
        .clip-thumbnail {
            position: absolute;
            top: 0; left: 0;
            width: 100%;
            height: 100%;
            object-fit: cover;
            transition: transform 0.6s ease, opacity 0.4s ease;
            z-index: 2;
        }
        
        .clip-card:hover:not(.dragging) .clip-thumbnail {
            transform: scale(1.05);
        }
        
        .video-player {
            position: absolute;
            top: 0; left: 0;
            width: 100%; height: 100%;
            object-fit: cover;
            z-index: 1;
            opacity: 0;
            transition: opacity 0.4s ease;
        }
        
        .video-player.playing {
            opacity: 1;
        }
        
        .play-overlay {
            position: absolute;
            top: 50%; left: 50%;
            transform: translate(-50%, -50%);
            width: 70px; height: 70px;
            background: rgba(255, 255, 255, 0.95);
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 28px;
            color: #000;
            pointer-events: none;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
            transition: all 0.4s cubic-bezier(0.34, 1.56, 0.64, 1);
            z-index: 3;
        }
        
        .clip-card:hover:not(.dragging) .play-overlay {
            transform: translate(-50%, -50%) scale(1.2);
            background: linear-gradient(135deg, #a78bfa, #ec4899);
            color: white;
        }
        
        .video-loading {
            position: absolute;
            top: 50%; left: 50%;
            transform: translate(-50%, -50%);
            width: 40px; height: 40px;
            border: 3px solid rgba(255, 255, 255, 0.2);
            border-top-color: #a78bfa;
            border-radius: 50%;
            animation: spin 0.8s linear infinite;
            z-index: 5;
            opacity: 0;
            transition: opacity 0.3s;
        }
        
        .video-loading.active { opacity: 1; }
        
        @keyframes spin {
            to { transform: translate(-50%, -50%) rotate(360deg); }
        }
        
        /* FULLSCREEN BUTTON */
        .fullscreen-btn {
            position: absolute;
            top: 15px; right: 15px;
            width: 40px; height: 40px;
            background: rgba(15, 23, 42, 0.9);
            backdrop-filter: blur(20px);
            border: 1px solid rgba(255, 255, 255, 0.2);
            border-radius: 12px;
            color: white;
            font-size: 18px;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            opacity: 0;
            transform: translateY(-10px);
            transition: all 0.4s cubic-bezier(0.34, 1.56, 0.64, 1);
            z-index: 10;
        }
        
        .clip-card:hover:not(.dragging) .fullscreen-btn {
            opacity: 1;
            transform: translateY(0);
        }
        
        .fullscreen-btn:hover {
            background: linear-gradient(135deg, #6366f1, #8b5cf6);
            transform: scale(1.1);
            box-shadow: 0 4px 16px rgba(99, 102, 241, 0.5);
        }
        
        /* VOLUME CONTROL */
        .volume-control {
            position: absolute;
            bottom: 15px; right: 15px;
            display: flex;
            align-items: center;
            gap: 12px;
            background: rgba(15, 23, 42, 0.9);
            backdrop-filter: blur(20px);
            padding: 10px 16px;
            border-radius: 50px;
            border: 1px solid rgba(255, 255, 255, 0.1);
            opacity: 0;
            transform: translateY(10px);
            transition: all 0.4s cubic-bezier(0.34, 1.56, 0.64, 1);
            z-index: 10;
        }
        
        .clip-card:hover:not(.dragging) .volume-control {
            opacity: 1;
            transform: translateY(0);
        }
        
        .volume-btn {
            width: 36px; height: 36px;
            background: linear-gradient(135deg, #6366f1, #8b5cf6);
            border: none;
            color: white;
            font-size: 18px;
            cursor: pointer;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            transition: transform 0.2s, box-shadow 0.2s;
            box-shadow: 0 4px 12px rgba(99, 102, 241, 0.4);
        }
        
        .volume-btn:hover {
            transform: scale(1.15);
        }
        
        .volume-slider {
            width: 90px; height: 6px;
            -webkit-appearance: none;
            appearance: none;
            background: rgba(255, 255, 255, 0.2);
            border-radius: 3px;
            outline: none;
            cursor: pointer;
        }
        
        .volume-slider::-webkit-slider-thumb {
            -webkit-appearance: none;
            appearance: none;
            width: 18px; height: 18px;
            background: linear-gradient(135deg, #a78bfa, #ec4899);
            border-radius: 50%;
            cursor: pointer;
            box-shadow: 0 3px 8px rgba(167, 139, 250, 0.5);
        }
        
        .volume-slider::-moz-range-thumb {
            width: 18px; height: 18px;
            background: linear-gradient(135deg, #a78bfa, #ec4899);
            border-radius: 50%;
            cursor: pointer;
            border: none;
            box-shadow: 0 3px 8px rgba(167, 139, 250, 0.5);
        }

        .clip-info { 
            padding: 24px;
            background: linear-gradient(to bottom, transparent, rgba(0, 0, 0, 0.3));
        }
        
        .clip-title { 
            font-size: 1.15em; 
            font-weight: 700; 
            margin-bottom: 12px;
            color: #f8fafc;
            line-height: 1.4;
            display: -webkit-box; 
            -webkit-line-clamp: 2; 
            -webkit-box-orient: vertical; 
            overflow: hidden;
        }
        
        .clip-meta { 
            display: flex; 
            justify-content: space-between; 
            align-items: center; 
            margin-bottom: 12px;
        }
        
        .views-badge, .duration-badge { 
            display: inline-flex; 
            align-items: center; 
            gap: 6px;
            background: rgba(99, 102, 241, 0.2);
            border: 1px solid rgba(99, 102, 241, 0.3);
            color: #c7d2fe;
            padding: 6px 12px; 
            border-radius: 16px; 
            font-weight: 600; 
            font-size: 0.85em;
        }
        
        .creator { 
            color: #94a3b8; 
            font-size: 0.9em; 
            font-weight: 500;
        }
        
        .action-buttons { 
            display: flex; 
            justify-content: center; 
            gap: 25px; 
            margin-bottom: 25px;
            animation: fadeInUp 0.6s ease 0.2s both;
        }
        
        @keyframes fadeInUp {
            from { opacity: 0; transform: translateY(20px); }
            to { opacity: 1; transform: translateY(0); }
        }
        
        .btn-reject, .btn-accept {
            width: 70px; height: 70px; 
            border-radius: 50%; 
            border: none; 
            cursor: pointer;
            font-size: 1.8em; 
            display: flex; 
            align-items: center; 
            justify-content: center;
            transition: all 0.3s cubic-bezier(0.34, 1.56, 0.64, 1);
        }
        
        .btn-reject {
            background: linear-gradient(135deg, #ef4444, #dc2626);
            color: white;
            box-shadow: 0 8px 24px rgba(239, 68, 68, 0.4);
        }
        
        .btn-accept {
            background: linear-gradient(135deg, #10b981, #059669);
            color: white;
            box-shadow: 0 8px 24px rgba(16, 185, 129, 0.4);
        }
        
        .btn-reject:hover, .btn-accept:hover { 
            transform: scale(1.15) translateY(-3px);
        }
        
        .btn-reject:active, .btn-accept:active { 
            transform: scale(0.95); 
        }
        
        .btn-process {
            background: linear-gradient(135deg, #6366f1, #8b5cf6);
            color: white; 
            border: none; 
            padding: 16px 36px; 
            border-radius: 30px;
            font-size: 1em; 
            font-weight: 700; 
            cursor: pointer; 
            box-shadow: 0 8px 24px rgba(99, 102, 241, 0.4);
            transition: all 0.3s;
            width: 100%; 
            max-width: 280px; 
            margin: 0 auto; 
            display: block;
        }
        
        .btn-process:hover { 
            transform: translateY(-3px);
            box-shadow: 0 12px 32px rgba(99, 102, 241, 0.5);
        }
        
        .hidden { display: none !important; }
        
        #loading {
            position: fixed; 
            top: 0; left: 0; 
            width: 100%; height: 100%;
            background: rgba(15, 23, 42, 0.95); 
            backdrop-filter: blur(10px);
            display: flex; 
            flex-direction: column; 
            align-items: center; 
            justify-content: center; 
            z-index: 9999;
        }
        
        .spinner {
            width: 50px; height: 50px; 
            border: 4px solid rgba(255,255,255,0.1); 
            border-top-color: #a78bfa;
            border-radius: 50%; 
            animation: spin 0.8s linear infinite;
        }
        
        #empty-state { 
            text-align: center; 
            padding: 60px 20px;
        }
        
        #empty-state h2 { 
            font-size: 2em; 
            margin-bottom: 15px;
            background: linear-gradient(135deg, #a78bfa, #ec4899);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        
        .refresh-btn {
            background: linear-gradient(135deg, #6366f1, #8b5cf6);
            color: white; 
            border: none; 
            padding: 14px 32px;
            border-radius: 25px; 
            font-weight: 600; 
            cursor: pointer; 
            transition: all 0.3s;
            box-shadow: 0 8px 24px rgba(99, 102, 241, 0.4);
        }
        
        .refresh-btn:hover { 
            transform: translateY(-3px);
        }
        
        .swipe-hint {
            position: absolute; 
            top: 50px; 
            font-size: 2.8em; 
            font-weight: 900; 
            padding: 8px 20px;
            border-radius: 16px; 
            opacity: 0; 
            transition: opacity 0.3s;
            pointer-events: none; 
            z-index: 100;
            text-shadow: 0 4px 12px rgba(0, 0, 0, 0.5);
        }
        
        .swipe-hint.left { 
            left: 30px; 
            color: #ef4444;
            background: rgba(239, 68, 68, 0.2);
            border: 2px solid #ef4444;
        }
        
        .swipe-hint.right { 
            right: 30px; 
            color: #10b981;
            background: rgba(16, 185, 129, 0.2);
            border: 2px solid #10b981;
        }
        
        .clip-card.swiping-left .swipe-hint.left,
        .clip-card.swiping-right .swipe-hint.right { 
            opacity: 1; 
        }
    </style>
</head>
<body>
    <div class="app-container">
        <header>
            <h1>🔥 Clipder</h1>
            <div class="stats">
                <div class="stat-item">
                    <span>📊</span>
                    <span id="queue-count">0 clips</span>
                </div>
                <div class="stat-item" style="color: #10b981;">
                    <span>✨</span>
                    <span id="accepted-count">0 selected</span>
                </div>
            </div>
        </header>
        
        <div class="swipe-container">
            <div id="card-stack"></div>
            <div id="empty-state" class="hidden">
                <h2>🎉 All Done!</h2>
                <p>No more clips to review</p>
                <button onclick="location.reload()" class="refresh-btn">🔄 Refresh Clips</button>
            </div>
        </div>
        
        <div class="action-buttons">
            <button class="btn-reject" onclick="swipeLeft()">✕</button>
            <button class="btn-accept" onclick="swipeRight()">♥</button>
        </div>
        
        <div>
            <button id="process-btn" class="btn-process hidden" onclick="processAccepted()">
                🚀 Process <span id="process-count">0</span> Clips
            </button>
        </div>
    </div>
    
    <div id="loading" class="hidden">
        <div class="spinner"></div>
        <p style="margin-top: 20px; font-weight: 600; font-size: 1.1em;">Loading clips...</p>
    </div>

    <script>
        let clips = [];
        let currentIndex = 0;
        let acceptedClips = [];
        let isDragging = false;
        
        document.addEventListener('DOMContentLoaded', loadClips);
        
        async function loadClips() {
            showLoading(true);
            try {
                const res = await fetch('/api/clips');
                const data = await res.json();
                clips = data.clips;
                currentIndex = 0;
                updateStats();
                renderCards();
            } catch(e) {
                console.error(e);
                alert('Failed to load clips');
            } finally {
                showLoading(false);
            }
        }
        
        function renderCards() {
            const stack = document.getElementById('card-stack');
            stack.innerHTML = '';
            
            if (currentIndex >= clips.length) {
                showEmptyState();
                return;
            }
            
            for (let i = currentIndex; i < Math.min(currentIndex + 3, clips.length); i++) {
                const card = createCard(clips[i], i - currentIndex);
                stack.appendChild(card);
            }
            
            const topCard = stack.querySelector('.clip-card');
            if (topCard) {
                makeCardSwipeable(topCard);
                setupVideoHover(topCard);
            }
        }
        
        function createCard(clip, stackIndex) {
            const card = document.createElement('div');
            card.className = 'clip-card';
            card.dataset.clipId = clip.id;
            card.dataset.clipUrl = clip.url;
            
            card.style.zIndex = 100 - stackIndex;
            card.style.transform = `scale(${1 - stackIndex * 0.04}) translateY(${stackIndex * 12}px)`;
            card.style.opacity = 1 - stackIndex * 0.15;
            
            const views = clip.view_count >= 1000 ? (clip.view_count/1000).toFixed(1) + 'K' : clip.view_count;
            
            card.innerHTML = `
                <div class="clip-preview">
                    <img src="${clip.thumbnail_url}" class="clip-thumbnail" draggable="false">
                    <video class="video-player" preload="metadata" loop playsinline muted></video>
                    <div class="video-loading"></div>
                    <div class="play-overlay">▶</div>
                    <button class="fullscreen-btn" onclick="event.stopPropagation(); openFullscreen(this)" title="Fullscreen">⛶</button>
                    <div class="volume-control">
                        <button class="volume-btn" onclick="event.stopPropagation(); toggleMute(this)">
                            <span class="volume-icon">🔊</span>
                        </button>
                        <input type="range" class="volume-slider" min="0" max="100" value="70" 
                               onclick="event.stopPropagation()" 
                               oninput="event.stopPropagation(); changeVolume(this)">
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
        
        function setupVideoHover(card) {
            const preview = card.querySelector('.clip-preview');
            let hoverTimer = null;
            
            preview.addEventListener('mouseenter', () => {
                if (isDragging) return;
                hoverTimer = setTimeout(() => startVideoPlay(card), 150);
            });
            
            preview.addEventListener('mouseleave', () => {
                clearTimeout(hoverTimer);
                if (!isDragging) stopVideoPlay(card);
            });
        }

        async function startVideoPlay(card) {
            if (isDragging) return;
            
            const video = card.querySelector('.video-player');
            const thumbnail = card.querySelector('.clip-thumbnail');
            const playOverlay = card.querySelector('.play-overlay');
            const loading = card.querySelector('.video-loading');
            
            // If video already loaded, just play
            if (video.src && video.readyState >= 2) {
                video.muted = false; // FIX: Unmute when playing
                video.play().then(() => {
                    video.classList.add('playing');
                    thumbnail.style.opacity = '0';
                    playOverlay.style.opacity = '0';
                }).catch(e => console.log('Play prevented:', e));
                return;
            }
            
            loading.classList.add('active');
            
            try {
                const response = await fetch(`/api/clip/${card.dataset.clipId}/video-url`);
                const data = await response.json();
                
                if (data.video_url) {
                    video.src = data.video_url;
                    video.volume = 0.7;
                    video.muted = false; // FIX: Start unmuted
                    
                    video.addEventListener('loadeddata', () => {
                        loading.classList.remove('active');
                        video.play().then(() => {
                            video.classList.add('playing');
                            thumbnail.style.opacity = '0';
                            playOverlay.style.opacity = '0';
                        }).catch(e => {
                            console.log('Autoplay prevented');
                            loading.classList.remove('active');
                        });
                    }, { once: true });
                    
                    video.addEventListener('error', () => {
                        loading.classList.remove('active');
                        console.error('Video error');
                    }, { once: true });
                }
            } catch (e) {
                console.error('Failed to fetch video:', e);
                loading.classList.remove('active');
            }
        }

        function stopVideoPlay(card) {
            const video = card.querySelector('.video-player');
            const thumbnail = card.querySelector('.clip-thumbnail');
            const playOverlay = card.querySelector('.play-overlay');
            
            video.pause();
            video.classList.remove('playing');
            
            thumbnail.style.opacity = '1';
            playOverlay.style.opacity = '1';
        }
        
        function openFullscreen(btn) {
            const card = btn.closest('.clip-card');
            const video = card.querySelector('.video-player');
            
            if (video.requestFullscreen) {
                video.requestFullscreen();
            } else if (video.webkitRequestFullscreen) {
                video.webkitRequestFullscreen();
            } else if (video.msRequestFullscreen) {
                video.msRequestFullscreen();
            }
        }
        
        function toggleMute(btn) {
            const card = btn.closest('.clip-card');
            const video = card.querySelector('.video-player');
            const icon = btn.querySelector('.volume-icon');
            
            video.muted = !video.muted;
            icon.textContent = video.muted ? '🔇' : '🔊';
        }
        
        function changeVolume(slider) {
            const card = slider.closest('.clip-card');
            const video = card.querySelector('.video-player');
            const icon = card.querySelector('.volume-icon');
            
            video.volume = slider.value / 100;
            
            if (slider.value == 0) {
                icon.textContent = '🔇';
                video.muted = true;
            } else {
                icon.textContent = '🔊';
                video.muted = false;
            }
        }
        
        function makeCardSwipeable(card) {
            let startX = 0, currentX = 0;
            let startTime = 0;
            
            const startDrag = (e) => {
                if (e.target.closest('.volume-control') || e.target.closest('.fullscreen-btn')) return;
                
                isDragging = true;
                startTime = Date.now();
                card.classList.add('dragging');
                
                const point = e.type.includes('mouse') ? e : e.touches[0];
                startX = point.clientX;
                currentX = startX;
                
                stopVideoPlay(card);
            };
            
            const doDrag = (e) => {
                if (!isDragging) return;
                e.preventDefault();
                
                const point = e.type.includes('mouse') ? e : e.touches[0];
                currentX = point.clientX;
                const deltaX = currentX - startX;
                const rotation = deltaX * 0.03;
                
                card.style.transition = 'none';
                card.style.transform = `translate(${deltaX}px, 0) rotate(${rotation}deg)`;
                
                if (deltaX > 70) {
                    card.classList.add('swiping-right');
                    card.classList.remove('swiping-left');
                } else if (deltaX < -70) {
                    card.classList.add('swiping-left');
                    card.classList.remove('swiping-right');
                } else {
                    card.classList.remove('swiping-left', 'swiping-right');
                }
            };
            
            const stopDrag = () => {
                if (!isDragging) return;
                
                const deltaX = currentX - startX;
                const duration = Date.now() - startTime;
                const velocity = Math.abs(deltaX) / duration;
                
                isDragging = false;
                card.classList.remove('dragging');
                
                // FIX: Proper swipe detection
                if (Math.abs(deltaX) > 100 || velocity > 0.5) {
                    // Swipe detected!
                    animateSwipe(card, deltaX > 0 ? 'right' : 'left');
                } else {
                    // Snap back
                    card.style.transition = 'transform 0.4s cubic-bezier(0.34, 1.56, 0.64, 1)';
                    card.style.transform = '';
                    card.classList.remove('swiping-left', 'swiping-right');
                    setTimeout(() => { card.style.transition = ''; }, 400);
                }
            };

            card.addEventListener('mousedown', startDrag);
            document.addEventListener('mousemove', doDrag);
            document.addEventListener('mouseup', stopDrag);
            
            card.addEventListener('touchstart', startDrag, {passive: false});
            document.addEventListener('touchmove', doDrag, {passive: false});
            document.addEventListener('touchend', stopDrag);
        }
        
        function animateSwipe(card, direction) {
            const distance = direction === 'right' ? 1500 : -1500;
            const rotation = direction === 'right' ? 35 : -35;
            
            card.style.transition = 'transform 0.5s cubic-bezier(0.4, 0, 0.2, 1), opacity 0.5s';
            card.style.transform = `translate(${distance}px, -100px) rotate(${rotation}deg)`;
            card.style.opacity = '0';
            
            setTimeout(() => {
                handleSwipe(card.dataset.clipId, direction);
                currentIndex++;
                renderCards();
                updateStats();
            }, 500);
        }
        
        async function handleSwipe(clipId, direction) {
            const action = direction === 'right' ? 'accept' : 'reject';
            await fetch(`/api/clip/${clipId}/action`, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({action})
            });
            if (action === 'accept') {
                acceptedClips.push(clipId);
                updateProcessButton();
            }
        }
        
        function swipeLeft() {
            const card = document.querySelector('.clip-card');
            if (card && !isDragging) animateSwipe(card, 'left');
        }
        
        function swipeRight() {
            const card = document.querySelector('.clip-card');
            if (card && !isDragging) animateSwipe(card, 'right');
        }
        
        function updateStats() {
            document.getElementById('queue-count').textContent = `${clips.length - currentIndex} clips`;
            document.getElementById('accepted-count').textContent = `${acceptedClips.length} selected`;
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
        
        function showLoading(show) {
            document.getElementById('loading').classList.toggle('hidden', !show);
        }
        
        async function processAccepted() {
            if (!acceptedClips.length) return;
            showLoading(true);
            try {
                await fetch('/api/process', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({clip_ids: acceptedClips})
                });
                alert(`✅ Processing ${acceptedClips.length} clips!`);
                acceptedClips = [];
                updateProcessButton();
            } catch(e) {
                alert('Error processing clips');
            } finally {
                showLoading(false);
            }
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
    print("🔥 Clipder - Swipe through Twitch clips")
    print("="*60)
    print(f"Status: {bot_initialized}")
    print("✅ Video with audio working")
    print("✅ Smooth swiping fixed")
    print("✅ Aesthetic hover pop-out")
    print("✅ Fullscreen feature added")
    print("Open: http://localhost:5000")
    print("="*60 + "\n")
    app.run(debug=True, host='0.0.0.0', port=5000)