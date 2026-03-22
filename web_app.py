"""
Twitch Clip Bot - Standalone card-swipe Web Interface
All-in-one file - no external templates needed!
"""

import threading
from flask import Flask, jsonify, request
from pathlib import Path
import json
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

try:
    # THE FIX IS HERE: Correctly importing from your engine file!
    from test import (
        Config, TwitchClient, StateManager, GroqClient, 
        VideoProcessor, YouTubeUploader, TikTokUploader
    )
    config = Config.from_env()
    twitch_client = TwitchClient(config)
    state_manager = StateManager(config)
    
    # Initialize the rest of your engine
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
    
    # Fetch clips from all channels
    clips_by_channel = {}
    
    for channel in config.twitch_channels:
        broadcaster_id = twitch_client.get_broadcaster_id(channel)
        if broadcaster_id:
            all_clips = twitch_client.get_recent_clips(broadcaster_id, hours_back=72, fetch_count=100)
            
            # Filter unprocessed and store by channel
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
            
            # Sort channel clips by views
            channel_clips.sort(key=lambda x: x['view_count'], reverse=True)
            clips_by_channel[channel] = channel_clips
    
    # SMART MIXING ALGORITHM
    mixed_clips = []
    max_per_channel = 10  # Take top 10 from each channel
    
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
    <title>Clip Swiper</title>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
        
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Inter', sans-serif;
            background: #0f172a; 
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            overflow: hidden;
            color: #f8fafc;
        }
        
        img { -webkit-user-drag: none; user-select: none; }
        
        .app-container {
            width: 100%;
            max-width: 420px;
            height: 90vh;
            display: flex;
            flex-direction: column;
            padding: 10px 20px;
        }
        header { text-align: center; margin-bottom: 20px; }
        header h1 { font-size: 1.6em; margin-bottom: 6px; font-weight: 700; }
        .stats { display: flex; justify-content: center; gap: 15px; font-size: 0.85em; color: #94a3b8; font-weight: 500; }
        
        .swipe-container { 
            flex: 1; 
            position: relative; 
            margin-bottom: 25px;
            perspective: 1000px;
        }
        #card-stack { position: relative; width: 100%; height: 100%; }
        
        .clip-card {
            position: absolute;
            width: 100%;
            height: 100%;
            background: #ffffff;
            border-radius: 20px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.3);
            cursor: grab;
            overflow: hidden;
            transform-origin: 50% 100%;
            transition: transform 0.4s cubic-bezier(0.2, 0.8, 0.2, 1), box-shadow 0.4s ease, opacity 0.4s ease;
            user-select: none;
        }
        .clip-card.dragging {
            transition: none !important; 
            cursor: grabbing;
            box-shadow: 0 20px 50px rgba(0,0,0,0.5);
        }

        .clip-preview {
            position: relative;
            width: 100%;
            height: 60%;
            background: #000;
            overflow: hidden;
        }
        .clip-thumbnail {
            position: absolute;
            top: 0; left: 0;
            width: 100%;
            height: 100%;
            object-fit: cover;
            pointer-events: none; 
            transition: opacity 0.3s ease;
            z-index: 2;
        }
        .play-indicator {
            position: absolute;
            top: 50%; left: 50%;
            transform: translate(-50%, -50%);
            width: 60px; height: 60px;
            background: rgba(255, 255, 255, 0.9);
            border-radius: 50%;
            display: flex; align-items: center; justify-content: center;
            font-size: 24px; color: #000;
            pointer-events: none;
            box-shadow: 0 4px 15px rgba(0,0,0,0.2);
            transition: opacity 0.3s ease;
            z-index: 3;
        }
        
        .iframe-container {
            position: absolute;
            top: 0; left: 0;
            width: 100%; height: 100%;
            z-index: 1;
        }
        
        .iframe-container iframe {
            pointer-events: none !important; 
        }

        .clip-info { 
            padding: 20px;
            background: white;
            height: 40%;
            display: flex;
            flex-direction: column;
        }
        .clip-title { 
            font-size: 1.1em; font-weight: 700; margin-bottom: 10px;
            color: #1e293b; line-height: 1.4;
            display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden;
        }
        .clip-meta { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; margin-top: auto; }
        .views-badge, .duration-badge { 
            display: inline-flex; align-items: center; gap: 4px;
            background: #f1f5f9; color: #475569; padding: 4px 10px; border-radius: 12px; font-weight: 600; font-size: 0.8em;
        }
        .creator { color: #64748b; font-size: 0.85em; font-weight: 500; }
        
        .action-buttons { display: flex; justify-content: center; gap: 20px; margin-bottom: 20px; }
        .btn-reject, .btn-accept {
            width: 60px; height: 60px; border-radius: 50%; border: none; cursor: pointer;
            font-size: 1.5em; display: flex; align-items: center; justify-content: center;
            transition: transform 0.2s ease, box-shadow 0.2s ease; box-shadow: 0 4px 15px rgba(0,0,0,0.2);
        }
        .btn-reject { background: #fff; color: #ef4444; border: 2px solid #fee2e2; }
        .btn-accept { background: #fff; color: #10b981; border: 2px solid #d1fae5; }
        .btn-reject:hover { transform: scale(1.1); box-shadow: 0 6px 20px rgba(239, 68, 68, 0.3); }
        .btn-accept:hover { transform: scale(1.1); box-shadow: 0 6px 20px rgba(16, 185, 129, 0.3); }
        .btn-reject:active, .btn-accept:active { transform: scale(0.95); }
        
        .btn-process {
            background: #6366f1; color: white; border: none; padding: 12px 30px; border-radius: 25px;
            font-size: 0.95em; font-weight: 600; cursor: pointer; box-shadow: 0 4px 15px rgba(99, 102, 241, 0.4);
            transition: background 0.2s, transform 0.2s; width: 100%; max-width: 250px; margin: 0 auto; display: block;
        }
        .btn-process:hover { background: #4f46e5; transform: translateY(-2px); }
        
        .hidden { display: none !important; }
        
        #loading {
            position: fixed; top: 0; left: 0; width: 100%; height: 100%;
            background: rgba(15, 23, 42, 0.9); backdrop-filter: blur(5px);
            display: flex; flex-direction: column; align-items: center; justify-content: center; z-index: 9999;
        }
        .spinner {
            width: 40px; height: 40px; border: 3px solid rgba(255,255,255,0.1); border-top-color: #6366f1;
            border-radius: 50%; animation: spin 0.8s linear infinite;
        }
        @keyframes spin { to { transform: rotate(360deg); } }
        
        #empty-state { text-align: center; padding: 60px 20px; }
        #empty-state h2 { font-size: 1.8em; margin-bottom: 10px; }
        #empty-state p { color: #94a3b8; margin-bottom: 20px; }
        .refresh-btn {
            background: #334155; color: white; border: none; padding: 10px 25px;
            border-radius: 20px; font-weight: 600; cursor: pointer; transition: 0.2s;
        }
        .refresh-btn:hover { background: #475569; }
        
        .swipe-hint {
            position: absolute; top: 40px; font-size: 2.5em; font-weight: 800; padding: 5px 15px;
            border-radius: 10px; border: 4px solid; opacity: 0; transition: opacity 0.2s;
            pointer-events: none; z-index: 100;
        }
        .swipe-hint.left { left: 20px; color: #ef4444; border-color: #ef4444; transform: rotate(-15deg); }
        .swipe-hint.right { right: 20px; color: #10b981; border-color: #10b981; transform: rotate(15deg); }
        .clip-card.swiping-left .swipe-hint.left, .clip-card.swiping-right .swipe-hint.right { opacity: 1; }
    </style>
</head>
<body>
    <div class="app-container">
        <header>
            <h1>🎬 Clip Swiper</h1>
            <div class="stats">
                <span id="queue-count">0 clips</span>
                <span>•</span>
                <span id="accepted-count" style="color: #10b981;">0 accepted</span>
            </div>
        </header>
        
        <div class="swipe-container">
            <div id="card-stack"></div>
            <div id="empty-state" class="hidden">
                <h2>🎉 All Caught Up!</h2>
                <p>No more clips to review right now.</p>
                <button onclick="location.reload()" class="refresh-btn">Check Again</button>
            </div>
        </div>
        
        <div class="action-buttons">
            <button class="btn-reject" onclick="swipeLeft()">✕</button>
            <button class="btn-accept" onclick="swipeRight()">♥</button>
        </div>
        
        <div>
            <button id="process-btn" class="btn-process hidden" onclick="processAccepted()">
                Process <span id="process-count">0</span> Clips
            </button>
        </div>
    </div>
    
    <div id="loading" class="hidden">
        <div class="spinner"></div>
        <p style="margin-top: 15px; font-weight: 500;">Fetching clips...</p>
    </div>

    <script>
        let clips = [];
        let currentIndex = 0;
        let acceptedClips = [];
        let hoverTimer = null;
        
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
                alert('Failed to load clips. Is the server running?');
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
            if (topCard) makeCardSwipeable(topCard);
        }
        
        function createCard(clip, stackIndex) {
            const card = document.createElement('div');
            card.className = 'clip-card';
            card.dataset.clipId = clip.id;
            
            card.style.zIndex = 100 - stackIndex;
            card.style.transform = `scale(${1 - stackIndex * 0.05}) translateY(${stackIndex * 15}px)`;
            card.style.opacity = 1 - stackIndex * 0.2;
            
            const views = clip.view_count >= 1000 ? (clip.view_count/1000).toFixed(1) + 'K' : clip.view_count;
            
            card.innerHTML = `
                <div class="clip-preview" onmouseenter="startHoverPlay(this, '${clip.id}')" onmouseleave="stopHoverPlay(this)">
                    <div class="iframe-container"></div>
                    <img src="${clip.thumbnail_url}" class="clip-thumbnail" alt="Thumbnail" draggable="false">
                    <div class="play-indicator">▶</div>
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
                <div class="swipe-hint right">KEEP</div>
            `;
            
            return card;
        }

        function startHoverPlay(previewEl, clipId) {
            hoverTimer = setTimeout(() => {
                const parentDomain = window.location.hostname || 'localhost';
                const iframeContainer = previewEl.querySelector('.iframe-container');
                const thumbnail = previewEl.querySelector('.clip-thumbnail');
                const indicator = previewEl.querySelector('.play-indicator');
                
                iframeContainer.innerHTML = `<iframe src="https://clips.twitch.tv/embed?clip=${clipId}&parent=${parentDomain}&autoplay=true&muted=false" width="100%" height="100%" frameborder="0" scrolling="no" allowfullscreen="true"></iframe>`;
                
                thumbnail.style.opacity = '0';
                indicator.style.opacity = '0';
            }, 300);
        }

        function stopHoverPlay(previewEl) {
            clearTimeout(hoverTimer);
            const iframeContainer = previewEl.querySelector('.iframe-container');
            const thumbnail = previewEl.querySelector('.clip-thumbnail');
            const indicator = previewEl.querySelector('.play-indicator');
            
            iframeContainer.innerHTML = '';
            
            thumbnail.style.opacity = '1';
            indicator.style.opacity = '1';
        }
        
        function makeCardSwipeable(card) {
            let startX = 0, currentX = 0, isDragging = false;
            
            const startDrag = (e) => {
                if (e.target.tagName === 'BUTTON') return;
                isDragging = true;
                card.classList.add('dragging'); 
                startX = e.type.includes('mouse') ? e.clientX : e.touches[0].clientX;
            };
            
            const doDrag = (e) => {
                if (!isDragging) return;
                e.preventDefault(); 
                currentX = e.type.includes('mouse') ? e.clientX : e.touches[0].clientX;
                const deltaX = currentX - startX;
                const rotation = deltaX * 0.05; 
                
                card.style.transform = `translate3d(${deltaX}px, 0, 0) rotate(${rotation}deg)`;
                
                if (deltaX > 60) {
                    card.classList.add('swiping-right');
                    card.classList.remove('swiping-left');
                } else if (deltaX < -60) {
                    card.classList.add('swiping-left');
                    card.classList.remove('swiping-right');
                } else {
                    card.classList.remove('swiping-left', 'swiping-right');
                }
            };
            
            const stopDrag = () => {
                if (!isDragging) return;
                isDragging = false;
                card.classList.remove('dragging'); 
                
                const deltaX = currentX - startX;
                
                if (deltaX > 100) animateSwipe(card, 'right');
                else if (deltaX < -100) animateSwipe(card, 'left');
                else {
                    card.style.transform = '';
                    card.classList.remove('swiping-left', 'swiping-right');
                }
                
                startX = 0; currentX = 0;
            };

            card.addEventListener('mousedown', startDrag);
            document.addEventListener('mousemove', doDrag);
            document.addEventListener('mouseup', stopDrag);
            
            card.addEventListener('touchstart', startDrag, {passive: false});
            document.addEventListener('touchmove', doDrag, {passive: false});
            document.addEventListener('touchend', stopDrag);
        }
        
        function animateSwipe(card, direction) {
            const distance = direction === 'right' ? window.innerWidth : -window.innerWidth;
            const rotation = direction === 'right' ? 30 : -30;
            
            stopHoverPlay(card.querySelector('.clip-preview'));
            
            card.classList.remove('dragging'); 
            card.style.transform = `translate3d(${distance}px, 0, 0) rotate(${rotation}deg)`;
            card.style.opacity = '0';
            
            setTimeout(() => {
                handleSwipe(card.dataset.clipId, direction);
                currentIndex++;
                renderCards();
                updateStats();
            }, 300); 
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
            if (card) animateSwipe(card, 'left');
        }
        function swipeRight() {
            const card = document.querySelector('.clip-card');
            if (card) animateSwipe(card, 'right');
        }
        
        function updateStats() {
            document.getElementById('queue-count').textContent = `${clips.length - currentIndex} clips left`;
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
                alert(`✅ Successfully sent ${acceptedClips.length} clips for processing!`);
                acceptedClips = [];
                updateProcessButton();
            } catch(e) {
                alert('Error processing clips.');
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

@app.route('/api/clip/<clip_id>/action', methods=['POST'])
def clip_action(clip_id):
    data = request.json
    action = data.get('action')
    clip = next((c for c in clips_queue if c['id'] == clip_id), None)
    
    if not clip:
        return jsonify({'error': 'Clip not found'}), 404
    
    if action == 'accept':
        return jsonify({'status': 'accepted', 'clip_id': clip_id})
    else:
        if bot_initialized:
            state_manager.mark_processed(clip_id)
        return jsonify({'status': 'rejected', 'clip_id': clip_id})


def background_processor(clip_ids):
    """Runs your FFmpeg and Upload engine silently in the background"""
    print(f"\n🚀 Starting background processing for {len(clip_ids)} clips...")
    
    # Find the full clip data for the IDs we accepted
    clips_to_process = [c for c in clips_queue if c['id'] in clip_ids]
    
    for idx, clip in enumerate(clips_to_process, 1):
        clip_id = clip["id"]
        clip_title = clip["title"]
        clip_url = clip["url"]
        view_count = clip.get("view_count", 0)
        
        print(f"\n[{idx}/{len(clips_to_process)}] 🎬 PROCESSING: {clip_title}")
        download_path = None
        processed_path = None
        
        try:
            # 1. Download
            download_path = video_processor.download_clip(clip_url, clip_id)
            if not download_path: continue
            
            # 2. Transcribe & AI Analysis
            print(" 🎤 Transcribing & Analyzing...")
            transcript = groq_client.transcribe_audio(download_path)
            metadata = groq_client.analyze_clip(transcript, clip_title, view_count)
            
            # 3. Create TikTok Style Video
            print(" 🎨 Rendering Video...")
            processed_path = video_processor.create_tiktok_style_video(
                download_path, clip_id, clip_title, metadata['description']
            )
            
            if processed_path:
                # 4. Auto-Upload
                print(" 📤 Uploading to YouTube...")
                youtube.upload(processed_path, metadata['title'], metadata['description'])
                
                print(" 📱 Uploading to TikTok...")
                tiktok.upload(processed_path, metadata['title'], metadata['description'])
                
                # Mark as processed so it doesn't show up again
                state_manager.mark_processed(clip_id)
                print(" ✅ Upload Complete!")
                
        except Exception as e:
            print(f" ❌ Error processing {clip_id}: {e}")
            
        finally:
            # Cleanup files
            if download_path and download_path.exists():
                download_path.unlink()
            if processed_path and processed_path.exists():
                processed_path.unlink()

    print("\n🎉 ALL BACKGROUND PROCESSING FINISHED!")


@app.route('/api/process', methods=['POST'])
def process_clips():
    data = request.json
    accepted = data.get('clip_ids', [])
    
    if not accepted:
        return jsonify({'status': 'empty'})
        
    # Start the engine in a background thread so the web UI doesn't freeze
    thread = threading.Thread(target=background_processor, args=(accepted,))
    thread.daemon = True
    thread.start()
    
    return jsonify({'status': 'processing', 'count': len(accepted)})

if __name__ == '__main__':
    print("\n" + "="*60)
    print("🎬 Clip Swiper - Standalone Web App")
    print("="*60)
    print(f"Bot initialized: {bot_initialized}")
    print("Open: http://localhost:5000")
    print("="*60 + "\n")
    app.run(debug=True, host='0.0.0.0', port=5000)