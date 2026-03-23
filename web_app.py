import threading
from flask import Flask, jsonify, request
from pathlib import Path
import json
import sys

sys.path.insert(0, str(Path(__file__).parent))

try:
    from core import (
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
    print(f"⚠️ Bot components not initialized: {e}")
    bot_initialized = False

app = Flask(__name__)

# --- GLOBAL STATE ---
clips_queue = []              
clip_metadata_store = {}      
clip_scores = {}              
admin_upload_queue = {}       

def fetch_clips():
    global clips_queue, clip_metadata_store
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
                clip_data = {
                    'id': clip['id'],
                    'title': clip['title'],
                    'url': clip['url'],
                    'thumbnail_url': clip['thumbnail_url'],
                    'view_count': clip['view_count'],
                    'creator_name': clip['creator_name'],
                    'duration': clip['duration'],
                    'created_at': clip['created_at'],
                    'channel': channel
                }
                
                clip_metadata_store[clip['id']] = clip_data
                
                if not state_manager.is_processed(clip["id"]) and clip["id"] not in admin_upload_queue and clip["id"] not in clip_scores:
                    channel_clips.append(clip_data)
            
            channel_clips.sort(key=lambda x: x['view_count'], reverse=True)
            clips_by_channel[channel] = channel_clips
    
    max_per_channel = 10
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
    <title>Clipder Pro</title>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap');
        
        * { margin: 0; padding: 0; box-sizing: border-box; }
        
        body { font-family: 'Inter', sans-serif; background: #0a0a0a; min-height: 100vh; color: #ffffff; position: relative; }
        
        body::before {
            content: ''; position: fixed; top: 0; left: 0; width: 100%; height: 100%;
            background: radial-gradient(circle at 20% 50%, rgba(120, 60, 220, 0.06) 0%, transparent 50%),
                        radial-gradient(circle at 80% 50%, rgba(220, 60, 120, 0.06) 0%, transparent 50%);
            pointer-events: none; z-index: 0;
        }
        
        .app-container { width: 100%; height: 100vh; display: flex; flex-direction: column; position: relative; z-index: 1; }
        
        header { 
            position: fixed; top: 0; left: 0; width: 100%; padding: 15px 5%;
            background: rgba(10, 10, 10, 0.95); backdrop-filter: blur(10px); z-index: 100;
            border-bottom: 1px solid rgba(255, 255, 255, 0.05); display: flex; justify-content: space-between; align-items: center;
        }
        
        header h1 { font-size: 1.6em; font-weight: 900; color: #ffffff; letter-spacing: -0.5px; }
        .logo-accent { background: linear-gradient(135deg, #8b5cf6, #ec4899); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
        
        .nav-tabs { display: flex; gap: 8px; background: rgba(255, 255, 255, 0.05); padding: 5px; border-radius: 12px; }
        .tab-btn { padding: 10px 20px; font-size: 0.9em; font-weight: 600; color: #888; background: transparent; border: none; border-radius: 8px; cursor: pointer; transition: all 0.2s; }
        .tab-btn.active { background: rgba(255, 255, 255, 0.1); color: #fff; box-shadow: 0 2px 8px rgba(0,0,0,0.2); }
        .tab-btn:hover:not(.active) { color: #ddd; }
        
        .view-section { flex: 1; width: 100%; height: 100%; overflow: hidden; display: none; }
        .view-section.active { display: flex; flex-direction: column; align-items: center; }
        
        /* SWIPE VIEW */
        .swipe-container { width: 100%; max-width: 480px; flex: 1; position: relative; padding: 100px 20px 160px 20px; display: flex; align-items: center; justify-content: center; }
        #card-stack { position: relative; width: 100%; max-width: 400px; height: 100%; max-height: 680px; }
        .clip-card { position: absolute; width: 100%; height: 100%; background: #141414; border-radius: 16px; box-shadow: 0 20px 60px rgba(0, 0, 0, 0.6), 0 0 0 1px rgba(255, 255, 255, 0.05); cursor: grab; transform-origin: 50% 50%; transition: transform 0.3s ease-out, opacity 0.3s ease-out; user-select: none; }
        .clip-card.top-card:hover:not(.dragging) { transform: translateY(-2px) !important; box-shadow: 0 25px 70px rgba(0, 0, 0, 0.7), 0 0 0 1px rgba(139, 92, 246, 0.2); z-index: 999 !important; }
        .clip-card.dragging { cursor: grabbing; transition: none !important; }
        .clip-preview { position: relative; width: 100%; aspect-ratio: 9/16; background: #000000; border-radius: 16px 16px 0 0; overflow: hidden; transform-origin: bottom center; transition: transform 0.3s cubic-bezier(0.34, 1.56, 0.64, 1), border-radius 0.3s; z-index: 2; }
        .clip-card.top-card:hover:not(.dragging) .clip-preview { transform: scale(1.25) translateY(-12px); border-radius: 12px; box-shadow: 0 40px 80px rgba(0,0,0,1), 0 0 0 1px rgba(139, 92, 246, 0.4); z-index: 10; }
        .clip-card:not(.top-card) .blur-bg-container { display: none !important; }
        .blur-bg-container { position: absolute; top: -10%; left: -10%; width: 120%; height: 120%; z-index: 0; filter: blur(25px); opacity: 0.4; transition: opacity 0.3s ease; }
        .blur-bg-container img { width: 100%; height: 100%; object-fit: cover; }
        .clip-thumbnail, .video-player { position: absolute; top: 0; left: 0; width: 100%; height: 100%; object-fit: contain !important; z-index: 1; }
        .clip-thumbnail { transition: opacity 0.3s ease; z-index: 2; }
        .video-player { z-index: 1; opacity: 0; transition: opacity 0.3s ease; }
        .video-player.playing { opacity: 1; }
        .video-loading { position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); width: 36px; height: 36px; border: 2px solid rgba(255, 255, 255, 0.1); border-top-color: #8b5cf6; border-radius: 50%; animation: spin 0.7s linear infinite; z-index: 5; opacity: 0; transition: opacity 0.3s; }
        .video-loading.active { opacity: 1; }
        .fullscreen-btn { position: absolute; top: 10px; right: 10px; width: 32px; height: 32px; background: rgba(0, 0, 0, 0.5); backdrop-filter: blur(10px); border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 6px; color: white; font-size: 14px; cursor: pointer; display: flex; align-items: center; justify-content: center; opacity: 0; transition: all 0.2s; z-index: 10; }
        .clip-card.top-card:hover:not(.dragging) .fullscreen-btn { opacity: 1; }
        .volume-control { position: absolute; bottom: 55px; right: 10px; display: flex; align-items: center; gap: 0; background: rgba(0, 0, 0, 0.5); backdrop-filter: blur(10px); padding: 0; border-radius: 50px; border: 1px solid rgba(255, 255, 255, 0.1); opacity: 0; transition: all 0.2s; z-index: 10; overflow: hidden; width: 32px; height: 32px; }
        .clip-card.top-card:hover:not(.dragging) .volume-control { opacity: 1; }
        .volume-control:hover { width: 130px; padding-right: 10px; gap: 8px; background: rgba(0, 0, 0, 0.7); }
        .volume-btn { width: 32px; height: 32px; background: transparent; border: none; color: white; cursor: pointer; display: flex; align-items: center; justify-content: center; flex-shrink: 0; }
        .volume-slider { width: 70px; height: 3px; -webkit-appearance: none; appearance: none; background: rgba(255, 255, 255, 0.15); border-radius: 2px; outline: none; cursor: pointer; opacity: 0; }
        .volume-control:hover .volume-slider { opacity: 1; }
        .volume-slider::-webkit-slider-thumb { -webkit-appearance: none; width: 10px; height: 10px; background: white; border-radius: 50%; }
        .progress-container { position: absolute; bottom: 25px; left: 20px; width: calc(100% - 40px); height: 24px; display: flex; align-items: center; z-index: 15; opacity: 0; transition: opacity 0.2s; }
        .clip-card.top-card:hover:not(.dragging) .progress-container { opacity: 1; }
        .progress-slider { width: 100%; height: 5px; -webkit-appearance: none; appearance: none; background: rgba(255, 255, 255, 0.2); outline: none; cursor: pointer; border-radius: 10px; backdrop-filter: blur(4px); transition: height 0.2s; }
        .progress-container:hover .progress-slider { height: 9px; }
        .progress-slider::-webkit-slider-thumb { -webkit-appearance: none; width: 16px; height: 16px; background: #ffffff; border-radius: 50%; opacity: 0; transition: opacity 0.2s, transform 0.2s; }
        .progress-container:hover .progress-slider::-webkit-slider-thumb { opacity: 1; transform: scale(1.1); }
        .clip-info { position: relative; padding: 18px; background: #141414; border-radius: 0 0 16px 16px; z-index: 1; }
        .clip-title { font-size: 1em; font-weight: 600; margin-bottom: 10px; line-height: 1.4; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }
        .clip-meta { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }
        .views-badge, .duration-badge { display: inline-flex; align-items: center; gap: 4px; background: rgba(255, 255, 255, 0.03); border: 1px solid rgba(255, 255, 255, 0.05); color: #666; padding: 4px 8px; border-radius: 10px; font-weight: 600; font-size: 0.75em; }
        .creator { color: #555; font-size: 0.8em; font-weight: 500; }
        .action-buttons { position: absolute; bottom: 30px; left: 50%; transform: translateX(-50%); width: 100%; display: flex; justify-content: center; align-items: center; gap: 16px; z-index: 100; }
        .btn-reject, .btn-accept { width: 58px; height: 58px; border-radius: 50%; border: 2px solid; cursor: pointer; font-size: 1.4em; display: flex; align-items: center; justify-content: center; transition: all 0.2s; }
        .btn-reject { background: rgba(239, 68, 68, 0.08); border-color: rgba(239, 68, 68, 0.25); color: #ef4444; }
        .btn-accept { background: rgba(16, 185, 129, 0.08); border-color: rgba(16, 185, 129, 0.25); color: #10b981; }
        .btn-reject:hover { transform: scale(1.08); background: rgba(239, 68, 68, 0.15); }
        .btn-accept:hover { transform: scale(1.08); background: rgba(16, 185, 129, 0.15); }
        .swipe-hint { position: absolute; top: 30px; font-size: 2.2em; font-weight: 900; padding: 4px 12px; border-radius: 10px; opacity: 0; transition: opacity 0.2s; pointer-events: none; z-index: 100; }
        .swipe-hint.left { left: 16px; color: #ef4444; background: rgba(239, 68, 68, 0.12); border: 2px solid rgba(239, 68, 68, 0.25); }
        .swipe-hint.right { right: 16px; color: #10b981; background: rgba(16, 185, 129, 0.12); border: 2px solid rgba(16, 185, 129, 0.25); }
        .clip-card.swiping-left .swipe-hint.left, .clip-card.swiping-right .swipe-hint.right { opacity: 1; }

        /* WIDE LIST VIEWS */
        .list-container { width: 100%; max-width: 1000px; padding: 100px 20px 100px 20px; flex: 1; overflow-y: auto; display: flex; flex-direction: column; gap: 16px; }
        .list-container::-webkit-scrollbar { width: 8px; }
        .list-container::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.1); border-radius: 10px; }
        
        .section-title { font-size: 2em; font-weight: 900; margin-bottom: 10px; background: linear-gradient(135deg, #8b5cf6, #ec4899); -webkit-background-clip: text; -webkit-text-fill-color: transparent; letter-spacing: -0.5px;}
        .section-subtitle { color: #888; font-size: 0.9em; margin-bottom: 24px; font-weight: 500; }
        
        .list-item { display: flex; gap: 16px; background: #141414; padding: 16px; border-radius: 16px; border: 1px solid rgba(255,255,255,0.05); align-items: center; transition: transform 0.2s; }
        .list-item:hover { transform: translateY(-2px); border-color: rgba(255,255,255,0.1); }
        
        /* HOVER PREVIEW VIDEO CSS */
        .thumb-container { position: relative; width: 120px; height: 68px; border-radius: 8px; overflow: hidden; background: #000; cursor: pointer; flex-shrink: 0; }
        .thumb-container img { width: 100%; height: 100%; object-fit: cover; transition: opacity 0.3s; }
        .thumb-container video { position: absolute; top: 0; left: 0; width: 100%; height: 100%; object-fit: cover; opacity: 0; transition: opacity 0.3s; pointer-events: none; }
        .thumb-container:hover img { opacity: 0; }
        .thumb-container:hover video.playing { opacity: 1; }
        .mini-spinner { position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); width: 20px; height: 20px; border: 2px solid rgba(255,255,255,0.1); border-top-color: #ec4899; border-radius: 50%; animation: spin 0.7s linear infinite; display: none; z-index: 5; }
        .thumb-container.loading .mini-spinner { display: block; }
        .thumb-container.loading img { opacity: 0.5; }

        .item-details { flex: 1; overflow: hidden; }
        .item-title { font-size: 1.1em; font-weight: 600; color: #fff; margin-bottom: 6px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
        .item-stats { font-size: 0.85em; color: #888; display: flex; gap: 12px; align-items: center;}
        .score-badge { display: inline-flex; align-items: center; gap: 4px; background: rgba(236, 72, 153, 0.15); color: #ec4899; padding: 4px 10px; border-radius: 8px; font-weight: 700; font-size: 0.9em; border: 1px solid rgba(236, 72, 153, 0.3);}
        
        .action-group { display: flex; gap: 8px; }
        .btn-small { padding: 10px 16px; border-radius: 8px; border: none; font-size: 0.9em; font-weight: 600; cursor: pointer; transition: all 0.2s; }
        .btn-primary { background: linear-gradient(135deg, #8b5cf6, #ec4899); color: white; }
        .btn-primary:hover { opacity: 0.9; transform: scale(1.05); }
        .btn-outline { background: transparent; border: 1px solid rgba(255,255,255,0.2); color: #fff; }
        .btn-outline:hover { background: rgba(255,255,255,0.1); }
        .btn-danger { background: rgba(239, 68, 68, 0.1); border: 1px solid rgba(239, 68, 68, 0.3); color: #ef4444; }
        .btn-danger:hover { background: rgba(239, 68, 68, 0.2); transform: scale(1.05); }
        
        .admin-footer { width: 100%; max-width: 1000px; margin-bottom: 20px; padding: 20px; background: rgba(20,20,20,0.9); border-radius: 16px; border: 1px solid rgba(255,255,255,0.05); display: flex; justify-content: space-between; align-items: center; }
        #loading { position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(10, 10, 10, 0.98); backdrop-filter: blur(10px); display: flex; flex-direction: column; align-items: center; justify-content: center; z-index: 9999; }
        @keyframes spin { to { transform: translate(-50%, -50%) rotate(360deg); } }
        .empty-msg { text-align: center; color: #666; font-size: 1.2em; margin-top: 60px; font-weight: 600; }
    </style>
</head>
<body>
    <header>
        <div class="header-content">
            <h1>Clip<span class="logo-accent">der</span> Pro</h1>
        </div>
        <div class="nav-tabs">
            <button class="tab-btn active" onclick="switchTab('swipe')">Swipe & Vote</button>
            <button class="tab-btn" onclick="switchTab('leaderboard')">Leaderboard</button>
            <button class="tab-btn" onclick="switchTab('admin')">Admin Queue (<span id="queue-badge">0</span>)</button>
        </div>
    </header>

    <div class="app-container">
        <div id="swipe" class="view-section active">
            <div class="swipe-container">
                <div id="card-stack"></div>
                <div id="empty-state" class="empty-msg" style="display: none;">
                    <h2>All Caught Up</h2>
                    <p style="margin-top: 10px;">No more clips to vote on</p>
                </div>
            </div>
            <div class="action-buttons" id="action-btns">
                <button class="btn-reject" onclick="swipeLeft()" title="Dislike">✕</button>
                <button class="btn-accept" onclick="swipeRight()" title="Like">♥</button>
            </div>
        </div>

        <div id="leaderboard" class="view-section">
            <div class="list-container">
                <h2 class="section-title">🏆 Top Viral Clips of the Month</h2>
                <div class="section-subtitle">Ranked by your swipes. Hover over a thumbnail to play!</div>
                <div id="leaderboard-list" style="display:flex; flex-direction:column; gap:16px;"></div>
            </div>
        </div>

        <div id="admin" class="view-section">
            <div class="list-container" style="padding-bottom: 20px;">
                <h2 class="section-title">🚀 Ready for Upload</h2>
                <div class="section-subtitle">Clips selected from the leaderboard, waiting to be processed.</div>
                <div id="admin-list" style="display:flex; flex-direction:column; gap:16px;"></div>
            </div>
            <div class="admin-footer" id="admin-footer" style="display: none;">
                <div style="font-size: 1.1em; font-weight: 600;"><span id="admin-count">0</span> clips ready to process</div>
                <button class="btn-small btn-primary" onclick="processAllClips()">Process & Upload All</button>
            </div>
        </div>
    </div>
    
    <div id="loading" style="display: none;">
        <div class="video-loading active" style="position: relative; top: auto; left: auto; transform: none; animation: spin 0.7s linear infinite;"></div>
        <p style="margin-top: 16px; font-weight: 600; color: #888;">Loading...</p>
    </div>

    <script>
        let clips = []; let currentIndex = 0; let isDragging = false; let isSwiping = false; 
        
        document.addEventListener('DOMContentLoaded', () => { loadClips(); refreshAdminQueue(); });
        
        function switchTab(tabId) {
            document.querySelectorAll('.view-section').forEach(el => el.classList.remove('active'));
            document.querySelectorAll('.tab-btn').forEach(el => el.classList.remove('active'));
            document.getElementById(tabId).classList.add('active');
            event.target.classList.add('active');
            
            if (tabId === 'leaderboard') loadLeaderboard();
            if (tabId === 'admin') refreshAdminQueue();
        }

        async function loadClips() {
            showLoading(true);
            try {
                const res = await fetch('/api/clips');
                clips = (await res.json()).clips; currentIndex = 0;
                renderCardStack();
            } catch(e) { console.error(e); } finally { showLoading(false); }
        }
        
        function renderCardStack() {
            const stack = document.getElementById('card-stack'); stack.innerHTML = '';
            if (clips.length - currentIndex <= 0) {
                document.getElementById('empty-state').style.display = 'block'; document.getElementById('action-btns').style.display = 'none'; return;
            }
            document.getElementById('empty-state').style.display = 'none'; document.getElementById('action-btns').style.display = 'flex';
            for (let i = currentIndex; i < Math.min(currentIndex + 3, clips.length); i++) {
                stack.appendChild(createCard(clips[i], i - currentIndex));
            }
            setupTopCard();
        }

        function createCard(clip, stackIndex) {
            const card = document.createElement('div'); card.className = 'clip-card'; card.dataset.clipId = clip.id;
            card.style.zIndex = 100 - stackIndex; card.style.transform = `scale(${1 - stackIndex * 0.03}) translateY(${stackIndex * 10}px)`; card.style.opacity = 1 - stackIndex * 0.12;
            card.innerHTML = `
                <div class="clip-preview">
                    <div class="blur-bg-container"><img src="${clip.thumbnail_url}" draggable="false"></div>
                    <img src="${clip.thumbnail_url}" class="clip-thumbnail" draggable="false">
                    <video class="video-player" preload="metadata" loop playsinline ontimeupdate="updateProgress(this)"></video>
                    <div class="video-loading"></div>
                    <button class="fullscreen-btn" onclick="event.stopPropagation(); openFullscreen(this)">⛶</button>
                    <div class="volume-control"><button class="volume-btn" onclick="event.stopPropagation(); toggleMute(this)"><span class="volume-icon">🔊</span></button><input type="range" class="volume-slider" min="0" max="100" value="30" oninput="event.stopPropagation(); changeVolume(this)"></div>
                    <div class="progress-container"><input type="range" class="progress-slider" min="0" max="100" value="0" step="0.1" oninput="event.stopPropagation(); seekVideo(this)"></div>
                </div>
                <div class="clip-info">
                    <div class="clip-title">${clip.title}</div>
                    <div class="creator">${clip.creator_name} • ${clip.channel}</div>
                    <div class="clip-meta"><span class="views-badge">👁️ ${clip.view_count} views</span><span class="duration-badge">⏱️ ${Math.floor(clip.duration)}s</span></div>
                </div>
                <div class="swipe-hint left">DISLIKE</div><div class="swipe-hint right">LIKE</div>
            `;
            return card;
        }

        function setupTopCard() {
            document.querySelectorAll('#card-stack .clip-card').forEach((card, index) => {
                if (index === 0) {
                    card.classList.add('top-card'); card.style.pointerEvents = 'auto';
                    makeCardSwipeable(card); setupVideoHover(card); preloadVideoUrl(card);
                } else { card.classList.remove('top-card'); card.style.pointerEvents = 'none'; }
            });
        }

        function updateProgress(video) {
            const slider = video.closest('.clip-card').querySelector('.progress-slider');
            if (slider && video.duration) {
                const p = (video.currentTime / video.duration) * 100;
                slider.value = p; slider.style.background = `linear-gradient(to right, #ec4899 ${p}%, rgba(255, 255, 255, 0.2) ${p}%)`;
            }
        }
        function seekVideo(slider) {
            const video = slider.closest('.clip-card').querySelector('.video-player');
            if (video && video.duration) {
                video.currentTime = (slider.value / 100) * video.duration;
                slider.style.background = `linear-gradient(to right, #ec4899 ${slider.value}%, rgba(255, 255, 255, 0.2) ${slider.value}%)`;
            }
        }
        async function preloadVideoUrl(card) {
            if (card.dataset.videoUrlFetched) return;
            const video = card.querySelector('.video-player');
            try {
                const res = await fetch(`/api/clip/${card.dataset.clipId}/video-url`);
                const data = await res.json();
                if (data.video_url) { video.src = data.video_url; video.preload = 'auto'; card.dataset.videoUrlFetched = 'true'; }
            } catch (e) {}
        }
        function setupVideoHover(card) {
            if (card.dataset.hoverSetup === 'true') return; card.dataset.hoverSetup = 'true';
            const preview = card.querySelector('.clip-preview');
            preview.addEventListener('mouseenter', () => { if (!isDragging && !isSwiping) startVideoPlay(card); });
            preview.addEventListener('mouseleave', () => { if (!isDragging) stopVideoPlay(card); });
        }
        async function startVideoPlay(card) {
            if (isDragging || isSwiping) return;
            const video = card.querySelector('.video-player'), loading = card.querySelector('.video-loading'), icon = card.querySelector('.volume-icon');
            const attemptPlay = async () => {
                try { video.muted = false; video.volume = 0.3; await video.play(); icon.textContent = '🔊'; } 
                catch (err) { video.muted = true; try { await video.play(); icon.textContent = '🔇'; } catch (err2) {} }
                video.classList.add('playing'); card.querySelector('.clip-thumbnail').style.opacity = '0'; loading.classList.remove('active');
            };
            if (video.src && video.readyState >= 2) { attemptPlay(); return; }
            loading.classList.add('active');
            try {
                const res = await fetch(`/api/clip/${card.dataset.clipId}/video-url`);
                const data = await res.json();
                if (data.video_url) { video.src = data.video_url; video.addEventListener('loadeddata', attemptPlay, { once: true }); }
            } catch (e) { loading.classList.remove('active'); }
        }
        function stopVideoPlay(card) {
            const video = card.querySelector('.video-player');
            if (video) { video.pause(); video.muted = true; video.classList.remove('playing'); }
            const thumb = card.querySelector('.clip-thumbnail'); if (thumb) thumb.style.opacity = '1';
        }
        function openFullscreen(btn) {
            const video = btn.closest('.clip-card').querySelector('.video-player');
            if (video.requestFullscreen) video.requestFullscreen(); else if (video.webkitRequestFullscreen) video.webkitRequestFullscreen();
        }
        function toggleMute(btn) {
            const card = btn.closest('.clip-card'), video = card.querySelector('.video-player');
            video.muted = !video.muted; btn.querySelector('.volume-icon').textContent = video.muted ? '🔇' : '🔊';
            if(!video.muted && video.volume === 0) { video.volume = 0.3; card.querySelector('.volume-slider').value = 30; }
        }
        function changeVolume(slider) {
            const video = slider.closest('.clip-card').querySelector('.video-player');
            video.volume = slider.value / 100; slider.closest('.clip-card').querySelector('.volume-icon').textContent = slider.value == 0 ? '🔇' : '🔊';
            video.muted = slider.value == 0;
        }

        function makeCardSwipeable(card) {
            if (card.dataset.swipeable === 'true') return; card.dataset.swipeable = 'true';
            let startX = 0, currentX = 0, ticking = false;
            
            const doDrag = (e) => {
                if (!isDragging) return; e.preventDefault(); currentX = (e.type.includes('mouse') ? e : e.touches[0]).clientX;
                if (!ticking) {
                    window.requestAnimationFrame(() => {
                        if (!isDragging) return; const deltaX = currentX - startX; card.style.transform = `translate(${deltaX}px, 0) rotate(${deltaX * 0.03}deg)`;
                        if (deltaX > 70) { card.classList.add('swiping-right'); card.classList.remove('swiping-left'); } 
                        else if (deltaX < -70) { card.classList.add('swiping-left'); card.classList.remove('swiping-right'); } 
                        else { card.classList.remove('swiping-left', 'swiping-right'); }
                        ticking = false;
                    }); ticking = true;
                }
            };
            
            const stopDrag = () => {
                if (!isDragging) return; isDragging = false;
                document.removeEventListener('mousemove', doDrag); document.removeEventListener('mouseup', stopDrag); document.removeEventListener('touchmove', doDrag); document.removeEventListener('touchend', stopDrag);
                card.classList.remove('dragging'); const deltaX = currentX - startX;
                if (Math.abs(deltaX) > 100) { card.classList.remove('top-card'); animateSwipe(card, deltaX > 0 ? 'right' : 'left'); } 
                else { card.style.transform = ''; card.classList.remove('swiping-left', 'swiping-right'); }
            };

            const startDrag = (e) => {
                if (e.target.closest('.volume-control') || e.target.closest('.fullscreen-btn') || e.target.closest('.progress-container')) return;
                if (isSwiping) return; 
                isDragging = true; card.classList.add('dragging'); startX = (e.type.includes('mouse') ? e : e.touches[0]).clientX; currentX = startX;
                stopVideoPlay(card);
                document.addEventListener('mousemove', doDrag); document.addEventListener('mouseup', stopDrag); document.addEventListener('touchmove', doDrag, {passive: false}); document.addEventListener('touchend', stopDrag);
            };
            card.addEventListener('mousedown', startDrag); card.addEventListener('touchstart', startDrag, {passive: false});
        }
        
        function animateSwipe(card, direction) {
            if (isSwiping) return; isSwiping = true;
            try { const v = card.querySelector('.video-player'); if(v){ v.pause(); v.removeAttribute('src'); v.load(); } } catch(e){}
            card.style.transition = 'transform 0.3s ease-out, opacity 0.3s';
            card.style.transform = `translate(${direction === 'right' ? window.innerWidth : -window.innerWidth}px, -100px) rotate(${direction === 'right' ? 30 : -30}deg)`;
            card.style.opacity = '0';
            setTimeout(() => { handleSwipe(card.dataset.clipId, direction); currentIndex++; renderCardStack(); isSwiping = false; }, 300);
        }

        function swipeLeft() { const c = document.querySelector('.clip-card.top-card'); if (c && !isDragging && !isSwiping) { c.classList.remove('top-card'); animateSwipe(c, 'left'); } }
        function swipeRight() { const c = document.querySelector('.clip-card.top-card'); if (c && !isDragging && !isSwiping) { c.classList.remove('top-card'); animateSwipe(c, 'right'); } }
        
        async function handleSwipe(clipId, direction) {
            await fetch(`/api/clip/${clipId}/action`, { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({action: direction === 'right' ? 'like' : 'dislike'}) });
        }

        // --- MINI HOVER VIDEO PREVIEW LOGIC ---
        async function playMiniVideo(container, clipId) {
            const video = container.querySelector('video');
            if (video.src && video.readyState >= 2) {
                video.play(); video.classList.add('playing'); return;
            }
            container.classList.add('loading');
            try {
                const res = await fetch(`/api/clip/${clipId}/video-url`);
                const data = await res.json();
                if (data.video_url) {
                    video.src = data.video_url;
                    video.addEventListener('loadeddata', () => {
                        container.classList.remove('loading');
                        video.play(); video.classList.add('playing');
                    }, { once: true });
                }
            } catch (e) { container.classList.remove('loading'); }
        }
        function stopMiniVideo(container) {
            const video = container.querySelector('video');
            video.pause(); video.classList.remove('playing');
        }

        // --- LEADERBOARD LOGIC ---
        async function loadLeaderboard() {
            const container = document.getElementById('leaderboard-list');
            container.innerHTML = '<div class="empty-msg">Loading top clips...</div>';
            try {
                const res = await fetch('/api/leaderboard'); const topClips = await res.json();
                if (topClips.length === 0) { container.innerHTML = '<div class="empty-msg">No clips have been liked yet!<br>Go swipe right to build the leaderboard.</div>'; return; }
                container.innerHTML = '';
                topClips.forEach((clip, index) => {
                    const div = document.createElement('div'); div.className = 'list-item';
                    div.innerHTML = `
                        <div style="font-size: 1.2em; font-weight: 900; color: #888; width: 40px; text-align: center;">#${index + 1}</div>
                        <div class="thumb-container" onmouseenter="playMiniVideo(this, '${clip.id}')" onmouseleave="stopMiniVideo(this)">
                            <img src="${clip.thumbnail_url}">
                            <div class="mini-spinner"></div>
                            <video loop muted playsinline></video>
                        </div>
                        <div class="item-details">
                            <div class="item-title">${clip.title}</div>
                            <div class="item-stats">
                                <span class="score-badge">♥ ${clip.local_likes} Likes</span> 
                                <span>👁️ ${clip.view_count} Twitch Views</span> • <span>${clip.channel}</span>
                            </div>
                        </div>
                        <button class="btn-small btn-outline" onclick="sendToAdminQueue('${clip.id}')">+ Send to Queue</button>
                    `;
                    container.appendChild(div);
                });
            } catch(e) { console.error(e); }
        }

        async function sendToAdminQueue(clipId) {
            await fetch(`/api/admin/queue`, { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({clip_id: clipId}) });
            refreshAdminQueue(); alert("✅ Sent to Admin Upload Queue!");
        }

        // --- ADMIN QUEUE LOGIC ---
        async function refreshAdminQueue() {
            try {
                const res = await fetch('/api/accepted'); const accepted = await res.json();
                document.getElementById('queue-badge').textContent = accepted.length;
                document.getElementById('admin-count').textContent = accepted.length;
                const container = document.getElementById('admin-list'), footer = document.getElementById('admin-footer');
                
                if (accepted.length === 0) {
                    container.innerHTML = '<div class="empty-msg">Admin queue is empty.<br><br>Add clips from the Leaderboard to process them.</div>';
                    footer.style.display = 'none'; return;
                }
                
                footer.style.display = 'flex'; container.innerHTML = '';
                accepted.forEach(clip => {
                    const div = document.createElement('div'); div.className = 'list-item';
                    div.innerHTML = `
                        <div class="thumb-container" onmouseenter="playMiniVideo(this, '${clip.id}')" onmouseleave="stopMiniVideo(this)">
                            <img src="${clip.thumbnail_url}"><div class="mini-spinner"></div><video loop muted playsinline></video>
                        </div>
                        <div class="item-details">
                            <div class="item-title">${clip.title}</div>
                            <div class="item-stats">Ready for Upload • ${clip.channel}</div>
                        </div>
                        <div class="action-group">
                            <button class="btn-small btn-danger" onclick="removeFromAdminQueue('${clip.id}')">Remove</button>
                            <button class="btn-small btn-primary" onclick="processSingle('${clip.id}')">Upload Now</button>
                        </div>
                    `;
                    container.appendChild(div);
                });
            } catch(e) { console.error(e); }
        }

        async function removeFromAdminQueue(clipId) {
            await fetch('/api/admin/remove', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({clip_id: clipId}) });
            refreshAdminQueue();
        }

        async function processSingle(clipId) {
            showLoading(true);
            try {
                await fetch('/api/process', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({clip_ids: [clipId]}) });
                alert(`Upload started! Check terminal for progress.`); refreshAdminQueue();
            } catch(e) { alert('Error processing clip'); } finally { showLoading(false); }
        }

        async function processAllClips() {
            const res = await fetch('/api/accepted'); const accepted = await res.json();
            if (accepted.length === 0) return;
            if (!confirm(`Process and upload ${accepted.length} clips?`)) return;
            showLoading(true);
            try {
                const ids = accepted.map(c => c.id);
                await fetch('/api/process', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({clip_ids: ids}) });
                alert(`🚀 Processing ${accepted.length} clips in the background!`); refreshAdminQueue();
            } catch(e) { alert('Error processing clips'); } finally { showLoading(false); }
        }

        function showLoading(show) { document.getElementById('loading').style.display = show ? 'flex' : 'none'; }
    </script>
</body>
</html>'''

@app.route('/')
def index():
    return HTML_TEMPLATE

@app.route('/api/clips')
def get_clips():
    if not clips_queue:
        fetch_clips()
    return jsonify({'clips': clips_queue, 'total': len(clips_queue)})

@app.route('/api/clip/<clip_id>/video-url')
def get_clip_video_url(clip_id):
    try:
        clip = clip_metadata_store.get(clip_id)
        if not clip: return jsonify({'error': 'Clip not found'}), 404
        
        import yt_dlp
        ydl_opts = { 'format': 'best[ext=mp4]/best', 'quiet': True, 'no_warnings': True }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(clip['url'], download=False)
            return jsonify({'video_url': info.get('url'), 'title': clip['title']})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/clip/<clip_id>/action', methods=['POST'])
def clip_action(clip_id):
    global clips_queue, clip_scores
    data = request.json
    action = data.get('action')
    
    if action == 'like':
        clip_scores[clip_id] = clip_scores.get(clip_id, 0) + 1
        
    clips_queue = [c for c in clips_queue if c['id'] != clip_id]
    return jsonify({'status': 'voted', 'current_score': clip_scores.get(clip_id, 0)})

@app.route('/api/leaderboard')
def get_leaderboard():
    ranked_clips = []
    for cid, likes in clip_scores.items():
        if cid in clip_metadata_store:
            clip_info = clip_metadata_store[cid].copy()
            clip_info['local_likes'] = likes
            ranked_clips.append(clip_info)
            
    ranked_clips.sort(key=lambda x: x['local_likes'], reverse=True)
    return jsonify(ranked_clips)

@app.route('/api/admin/queue', methods=['POST'])
def add_to_admin_queue():
    global admin_upload_queue
    clip_id = request.json.get('clip_id')
    if clip_id in clip_metadata_store:
        admin_upload_queue[clip_id] = clip_metadata_store[clip_id]
        return jsonify({'status': 'added'})
    return jsonify({'status': 'failed'}), 404

@app.route('/api/admin/remove', methods=['POST'])
def remove_from_admin_queue():
    """NEW: Deletes a clip from the admin queue without uploading"""
    global admin_upload_queue
    clip_id = request.json.get('clip_id')
    if clip_id in admin_upload_queue:
        del admin_upload_queue[clip_id]
        return jsonify({'status': 'removed'})
    return jsonify({'status': 'failed'}), 404

@app.route('/api/accepted')
def get_accepted_clips():
    return jsonify(list(admin_upload_queue.values()))

def background_processor(clip_ids):
    global admin_upload_queue
    print(f"\n🚀 Processing {len(clip_ids)} clips...")
    
    for idx, c_id in enumerate(clip_ids, 1):
        if c_id not in admin_upload_queue: continue
        clip = admin_upload_queue[c_id]
        print(f"\n[{idx}/{len(clip_ids)}] 🎬 {clip['title']}")
        
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
                
                if download_path: Path(download_path).unlink(missing_ok=True)
                if processed_path: Path(processed_path).unlink(missing_ok=True)
                del admin_upload_queue[c_id]
                
        except Exception as e: print(f" ❌ Error processing {c_id}: {e}")
    print("\n🎉 Done processing batch!")

@app.route('/api/process', methods=['POST'])
def process_clips():
    data = request.json
    accepted_ids = data.get('clip_ids', [])
    if not accepted_ids: return jsonify({'status': 'empty'})
        
    thread = threading.Thread(target=background_processor, args=(accepted_ids,))
    thread.daemon = True
    thread.start()
    return jsonify({'status': 'processing'})

if __name__ == '__main__':
    print("\n" + "="*60)
    print("🔥 Clipder Pro - Full Edition Restored")
    print("="*60)
    print(f"Status: {bot_initialized}")
    print("✅ Hover-to-Play logic integrated in Leaderboard")
    print("✅ Remove button added to Queue Admin")
    print("Open: http://localhost:5000")
    print("="*60 + "\n")
    app.run(debug=True, host='0.0.0.0', port=5000)