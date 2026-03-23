import threading
from flask import Flask, jsonify, request
from pathlib import Path
import json
import sys
import datetime

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
clip_comments = {}            
admin_upload_queue = {}       

def fetch_clips():
    global clips_queue, clip_metadata_store
    clips_queue = []
    if not bot_initialized: return 0
    clips_by_channel = {}
    for channel in config.twitch_channels:
        broadcaster_id = twitch_client.get_broadcaster_id(channel)
        if broadcaster_id:
            all_clips = twitch_client.get_recent_clips(broadcaster_id, hours_back=72, fetch_count=100)
            channel_clips = []
            for clip in all_clips:
                clip_data = {'id': clip['id'], 'title': clip['title'], 'url': clip['url'], 'thumbnail_url': clip['thumbnail_url'], 'view_count': clip['view_count'], 'creator_name': clip['creator_name'], 'duration': clip['duration'], 'created_at': clip['created_at'], 'channel': channel}
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
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&family=Fredoka+One&display=swap');
        
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: 'Inter', sans-serif; background: #0a0a0a; min-height: 100vh; color: #ffffff; position: relative; overflow-x: hidden; }
        
        body::before {
            content: ''; position: fixed; top: 0; left: 0; width: 100%; height: 100%;
            background: radial-gradient(circle at 20% 50%, rgba(120, 60, 220, 0.06) 0%, transparent 50%),
                        radial-gradient(circle at 80% 50%, rgba(220, 60, 120, 0.06) 0%, transparent 50%);
            pointer-events: none; z-index: 0;
        }
        
        .app-container { width: 100%; height: 100vh; display: flex; flex-direction: column; position: relative; z-index: 1; transition: width 0.3s cubic-bezier(0.25, 0.46, 0.45, 0.94); }
        body.comments-open .app-container { width: calc(100% - 400px); }
        
        header { 
            position: fixed; top: 0; left: 0; width: 100%; padding: 15px 5%;
            background: rgba(10, 10, 10, 0.95); backdrop-filter: blur(10px); z-index: 100;
            border-bottom: 1px solid rgba(255, 255, 255, 0.05); display: flex; justify-content: space-between; align-items: center;
            transition: width 0.3s cubic-bezier(0.25, 0.46, 0.45, 0.94);
        }
        body.comments-open header { width: calc(100% - 400px); }
        
        header h1 { font-size: 1.6em; font-weight: 900; color: #ffffff; letter-spacing: -0.5px; }
        .logo-accent { background: linear-gradient(135deg, #8b5cf6, #ec4899); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
        
        .nav-tabs { display: flex; gap: 8px; background: rgba(255, 255, 255, 0.05); padding: 5px; border-radius: 12px; }
        .tab-btn { padding: 10px 20px; font-size: 0.9em; font-weight: 600; color: #888; background: transparent; border: none; border-radius: 8px; cursor: pointer; transition: all 0.2s; }
        .tab-btn.active { background: rgba(255, 255, 255, 0.1); color: #fff; box-shadow: 0 2px 8px rgba(0,0,0,0.2); }
        .tab-btn:hover:not(.active) { color: #ddd; }
        
        .view-section { flex: 1; width: 100%; height: 100%; overflow: hidden; display: none; }
        .view-section.active { display: flex; flex-direction: column; align-items: center; }
        
        /* SWIPE VIEW - BIG & PROFESSIONAL */
        .swipe-container { width: 100%; max-width: 900px; flex: 1; position: relative; padding: 100px 20px; display: flex; align-items: center; justify-content: center; }
        #card-stack { position: relative; width: 100%; max-width: 460px; height: 100%; max-height: 750px; z-index: 10; }
        
        .clip-card { 
            position: absolute; width: 100%; height: 100%; background: #141414; border-radius: 16px; 
            box-shadow: 0 25px 60px rgba(0, 0, 0, 0.8), 0 0 0 1px rgba(255, 255, 255, 0.05); 
            cursor: grab; transform-origin: center center; user-select: none; 
            will-change: transform, opacity;
            transition: transform 0.3s cubic-bezier(0.2, 1, 0.3, 1), opacity 0.3s ease-out;
        }
        .clip-card.dragging { transition: none !important; cursor: grabbing; }
        
        .clip-preview { position: relative; width: 100%; aspect-ratio: 9/16; background: #000; border-radius: 16px 16px 0 0; overflow: hidden; transform-origin: bottom center; transition: transform 0.3s cubic-bezier(0.34, 1.56, 0.64, 1), border-radius 0.3s; z-index: 2; }
        .clip-preview:hover { transform: scale(1.02) translateY(-4px); border-radius: 16px; box-shadow: 0 20px 50px rgba(0,0,0,0.8), 0 0 0 1px rgba(139, 92, 246, 0.4); z-index: 10; }
        
        .clip-card:not(.top-card) .blur-bg-container { display: none !important; }
        .blur-bg-container { position: absolute; top: -10%; left: -10%; width: 120%; height: 120%; z-index: 0; filter: blur(25px); opacity: 0.4; transition: opacity 0.3s ease; }
        .blur-bg-container img { width: 100%; height: 100%; object-fit: cover; }
        .clip-thumbnail, .video-player { position: absolute; top: 0; left: 0; width: 100%; height: 100%; object-fit: contain !important; z-index: 1; }
        .clip-thumbnail { transition: opacity 0.3s ease; z-index: 2; }
        .video-player { z-index: 1; opacity: 0; transition: opacity 0.3s ease; }
        .video-player.playing { opacity: 1; }
        .video-loading { position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); width: 36px; height: 36px; border: 2px solid rgba(255, 255, 255, 0.1); border-top-color: #8b5cf6; border-radius: 50%; animation: spin 0.7s linear infinite; z-index: 5; opacity: 0; transition: opacity 0.3s; }
        .video-loading.active { opacity: 1; }
        
        .fullscreen-btn, .play-pause-btn { position: absolute; top: 15px; width: 36px; height: 36px; background: rgba(0, 0, 0, 0.6); backdrop-filter: blur(10px); border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 8px; color: white; font-size: 16px; cursor: pointer; display: flex; align-items: center; justify-content: center; opacity: 0; transition: all 0.2s; z-index: 10; }
        .fullscreen-btn { right: 15px; }
        .play-pause-btn { right: 60px; }
        
        .clip-preview:hover .fullscreen-btn, .clip-preview:hover .play-pause-btn { opacity: 1; }
        .fullscreen-btn:hover, .play-pause-btn:hover { background: rgba(236, 72, 153, 0.8); border-color: transparent; transform: scale(1.05); }
        
        .volume-control { position: absolute; bottom: 55px; right: 15px; display: flex; align-items: center; gap: 0; background: rgba(0, 0, 0, 0.6); backdrop-filter: blur(10px); padding: 0; border-radius: 50px; border: 1px solid rgba(255, 255, 255, 0.1); opacity: 0; transition: all 0.2s; z-index: 10; overflow: hidden; width: 36px; height: 36px; }
        .clip-preview:hover .volume-control { opacity: 1; }
        .volume-control:hover { width: 140px; padding-right: 12px; gap: 8px; background: rgba(0, 0, 0, 0.8); }
        .volume-btn { width: 36px; height: 36px; background: transparent; border: none; color: white; cursor: pointer; display: flex; align-items: center; justify-content: center; flex-shrink: 0; font-size: 16px; }
        .volume-slider { width: 70px; height: 4px; -webkit-appearance: none; appearance: none; background: rgba(255, 255, 255, 0.15); border-radius: 2px; outline: none; cursor: pointer; opacity: 0; }
        .volume-control:hover .volume-slider { opacity: 1; }
        .volume-slider::-webkit-slider-thumb { -webkit-appearance: none; width: 12px; height: 12px; background: white; border-radius: 50%; }
        
        .progress-container { position: absolute; bottom: 25px; left: 20px; width: calc(100% - 40px); height: 24px; display: flex; align-items: center; z-index: 15; opacity: 0; transition: opacity 0.2s; }
        .clip-preview:hover .progress-container { opacity: 1; }
        .progress-slider { width: 100%; height: 5px; -webkit-appearance: none; appearance: none; background: rgba(255, 255, 255, 0.2); outline: none; cursor: pointer; border-radius: 10px; backdrop-filter: blur(4px); transition: height 0.2s; }
        .progress-container:hover .progress-slider { height: 9px; }
        .progress-slider::-webkit-slider-thumb { -webkit-appearance: none; width: 16px; height: 16px; background: #ffffff; border-radius: 50%; opacity: 0; transition: opacity 0.2s, transform 0.2s; box-shadow: 0 2px 8px rgba(0,0,0,0.5); }
        .progress-container:hover .progress-slider::-webkit-slider-thumb { opacity: 1; transform: scale(1.1); }
        
        /* INFO SECTION */
        .clip-info { position: relative; padding: 24px 20px; background: #141414; border-radius: 0 0 16px 16px; z-index: 1; }
        .clip-title { font-size: 1.15em; font-weight: 700; margin-bottom: 8px; line-height: 1.4; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }
        .clip-meta { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }
        .creator { color: #888; font-size: 0.9em; font-weight: 500; margin-bottom: 16px; }
        
        .social-counters { display: flex; gap: 8px; align-items: center; }
        .social-badge { display: inline-flex; align-items: center; gap: 6px; background: rgba(236, 72, 153, 0.08); border: 1px solid rgba(236, 72, 153, 0.2); color: #ec4899; padding: 6px 12px; border-radius: 12px; font-weight: 700; font-size: 0.85em; }
        .social-btn { display: inline-flex; align-items: center; gap: 6px; background: rgba(255, 255, 255, 0.05); border: 1px solid rgba(255, 255, 255, 0.1); color: #fff; padding: 6px 12px; border-radius: 12px; font-weight: 600; font-size: 0.85em; cursor: pointer; transition: all 0.2s; }
        .social-btn:hover { background: rgba(255, 255, 255, 0.15); transform: translateY(-1px); }
        
        /* FLOATING SIDE ARROWS */
        .action-buttons { 
            position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); 
            width: 100%; max-width: 820px; display: flex; justify-content: space-between; align-items: center; z-index: 5; pointer-events: none; 
        }
        .btn-side { 
            pointer-events: auto; width: 85px; height: 85px; border-radius: 50%; border: 2px solid; 
            cursor: pointer; display: flex; align-items: center; justify-content: center; 
            background: rgba(20, 20, 20, 0.7); backdrop-filter: blur(12px); box-shadow: 0 15px 35px rgba(0,0,0,0.5); 
            transition: transform 0.1s ease-out, box-shadow 0.1s ease-out, border-color 0.1s ease-out;
        }
        .btn-reject { border-color: rgba(239, 68, 68, 0.4); color: #ef4444; }
        .btn-accept { border-color: rgba(16, 185, 129, 0.4); color: #10b981; }
        
        /* Highlight states driven by JS Physics */
        .btn-reject.highlight { transform: scale(1.2) translateX(-10px) rotate(-15deg); background: rgba(239, 68, 68, 0.2); box-shadow: 0 0 50px rgba(239, 68, 68, 0.6); border-color: #ef4444; }
        .btn-accept.highlight { transform: scale(1.2) translateX(10px) rotate(15deg); background: rgba(16, 185, 129, 0.2); box-shadow: 0 0 50px rgba(16, 185, 129, 0.6); border-color: #10b981; }
        
        .btn-reject:hover { transform: scale(1.15) translateX(-8px) rotate(-15deg); background: rgba(239, 68, 68, 0.15); box-shadow: 0 0 30px rgba(239, 68, 68, 0.3); border-color: #ef4444; }
        .btn-accept:hover { transform: scale(1.15) translateX(8px) rotate(15deg); background: rgba(16, 185, 129, 0.15); box-shadow: 0 0 30px rgba(16, 185, 129, 0.3); border-color: #10b981; }

        @media (max-width: 850px) {
            .action-buttons { top: auto; bottom: 30px; transform: translateX(-50%); max-width: 360px; z-index: 100;}
            .btn-side { width: 64px; height: 64px; }
            .btn-reject:hover { transform: scale(1.1) rotate(-10deg); }
            .btn-accept:hover { transform: scale(1.1) rotate(10deg); }
            #card-stack { max-height: 600px; }
        }

        /* --- DYNAMIC BUBBLY AURAS --- */
        .swipe-hint { 
            position: absolute; top: 15%; pointer-events: none; z-index: 100; 
            display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 8px;
            opacity: 0; transform: scale(0.5); transition: opacity 0.1s ease, transform 0.1s ease;
        }
        
        .hint-text-main { font-family: 'Fredoka One', cursive; font-size: 3.5em; font-weight: 900; letter-spacing: 2px; }
        .hint-text-bubbly { 
            font-family: 'Fredoka One', cursive; font-size: 1.6em; padding: 6px 20px; 
            background: #fff; border-radius: 50px; color: #000; white-space: nowrap;
            box-shadow: 0 8px 0px rgba(0,0,0,0.2), 0 0 25px rgba(255,255,255,0.6); transform: rotate(-5deg);
        }
        
        .aura-strings {
            position: absolute; width: 250px; height: 250px; top: 50%; left: 50%; transform: translate(-50%, -50%);
            border-radius: 50%; filter: blur(30px); opacity: 0.5; z-index: -1; pointer-events: none; mix-blend-mode: screen;
        }

        .swipe-hint.left { left: -60px; color: #ff3e3e; }
        .swipe-hint.left .hint-text-main { filter: drop-shadow(0 0 15px rgba(255, 62, 62, 0.8)); text-shadow: 2px 2px 0 #000; }
        .swipe-hint.left .aura-strings { background: radial-gradient(circle, #ff3e3e 0%, transparent 70%); }
        
        .swipe-hint.right { right: -60px; color: #2eff8c; }
        .swipe-hint.right .hint-text-main { filter: drop-shadow(0 0 15px rgba(46, 255, 140, 0.8)); text-shadow: 2px 2px 0 #000; }
        .swipe-hint.right .hint-text-bubbly { transform: rotate(5deg); }
        .swipe-hint.right .aura-strings { background: radial-gradient(circle, #2eff8c 0%, transparent 70%); }

        /* WIDE LIST VIEWS (LEADERBOARD/ADMIN) */
        .list-container { width: 100%; max-width: 1000px; padding: 100px 20px 100px 20px; flex: 1; overflow-y: auto; display: flex; flex-direction: column; gap: 16px; }
        .list-container::-webkit-scrollbar { width: 8px; }
        .list-container::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.1); border-radius: 10px; }
        
        .section-title { font-size: 2.2em; font-weight: 900; margin-bottom: 10px; background: linear-gradient(135deg, #8b5cf6, #ec4899); -webkit-background-clip: text; -webkit-text-fill-color: transparent; letter-spacing: -0.5px;}
        .section-subtitle { color: #888; font-size: 0.95em; margin-bottom: 24px; font-weight: 500; }
        
        .list-item { position: relative; display: flex; gap: 16px; background: #141414; padding: 16px; border-radius: 16px; border: 1px solid rgba(255,255,255,0.05); align-items: center; transition: background 0.2s; z-index: 1; }
        .list-item:hover { background: #1a1a1a; z-index: 50; } 
        
        .thumb-wrapper { position: relative; width: 140px; height: 79px; flex-shrink: 0; z-index: 1; }
        .list-item:hover .thumb-wrapper { z-index: 50; }
        .thumb-container { position: absolute; top: 0; left: 0; width: 140px; height: 79px; border-radius: 8px; overflow: hidden; background: #000; cursor: pointer; transition: all 0.3s cubic-bezier(0.34, 1.56, 0.64, 1); transform-origin: center left; }
        .thumb-container img { width: 100%; height: 100%; object-fit: cover; transition: opacity 0.3s; }
        .thumb-container video { position: absolute; top: 0; left: 0; width: 100%; height: 100%; object-fit: cover; opacity: 0; transition: opacity 0.3s; pointer-events: none; }
        .thumb-container:hover { transform: scale(2.6); box-shadow: 0 15px 40px rgba(0,0,0,0.8), 0 0 0 1px rgba(139, 92, 246, 0.4); border-radius: 4px; z-index: 100; }
        .thumb-container:hover img { opacity: 0; }
        .thumb-container:hover video.playing { opacity: 1; }
        
        .mini-controls { position: absolute; bottom: 4px; left: 4px; right: 4px; display: flex; justify-content: space-between; opacity: 0; transition: opacity 0.2s; z-index: 10; pointer-events: none; }
        .thumb-container:hover .mini-controls { opacity: 1; pointer-events: auto; }
        .mini-btn { background: rgba(0,0,0,0.6); color: #fff; border: 1px solid rgba(255,255,255,0.2); border-radius: 3px; width: 18px; height: 18px; font-size: 10px; cursor: pointer; display: flex; align-items: center; justify-content: center; backdrop-filter: blur(4px); }
        .mini-btn:hover { background: rgba(236, 72, 153, 0.8); border-color: transparent; }
        .mini-spinner { position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); width: 24px; height: 24px; border: 2px solid rgba(255,255,255,0.1); border-top-color: #ec4899; border-radius: 50%; animation: spin 0.7s linear infinite; display: none; z-index: 5; }
        .thumb-container.loading .mini-spinner { display: block; }
        .thumb-container.loading img { opacity: 0.5; }

        .item-details { flex: 1; overflow: hidden; }
        .item-title { font-size: 1.1em; font-weight: 600; color: #fff; margin-bottom: 8px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
        .item-stats { font-size: 0.9em; color: #888; display: flex; gap: 12px; align-items: center;}
        
        .action-group { display: flex; gap: 8px; }
        .btn-small { padding: 10px 16px; border-radius: 8px; border: none; font-size: 0.9em; font-weight: 600; cursor: pointer; transition: all 0.2s; }
        .btn-primary { background: linear-gradient(135deg, #8b5cf6, #ec4899); color: white; }
        .btn-primary:hover { opacity: 0.9; transform: scale(1.05); }
        .btn-outline { background: transparent; border: 1px solid rgba(255,255,255,0.2); color: #fff; }
        .btn-outline:hover { background: rgba(255,255,255,0.1); }
        .btn-danger { background: rgba(239, 68, 68, 0.1); border: 1px solid rgba(239, 68, 68, 0.3); color: #ef4444; }
        .btn-danger:hover { background: rgba(239, 68, 68, 0.2); transform: scale(1.05); }
        
        .admin-footer { width: 100%; max-width: 1000px; margin-bottom: 20px; padding: 20px; background: rgba(20,20,20,0.9); border-radius: 16px; border: 1px solid rgba(255,255,255,0.05); display: flex; justify-content: space-between; align-items: center; }
        
        /* --- THEATER MODE MODAL CSS --- */
        #theater-modal { position: fixed; top: 0; left: 0; width: 100%; height: 100%; z-index: 10000; display: flex; align-items: center; justify-content: center; opacity: 0; transition: opacity 0.3s ease; pointer-events: none; }
        #theater-modal.show { opacity: 1; pointer-events: auto; }
        .theater-backdrop { position: absolute; top: 0; left: 0; width: 100%; height: 100%; background: rgba(10, 10, 10, 0.65); backdrop-filter: blur(15px); }
        .theater-content { position: relative; z-index: 10001; width: 90%; max-width: 1200px; height: auto; display: flex; justify-content: center; align-items: center; background: transparent; border-radius: 16px; overflow: hidden; box-shadow: 0 30px 60px rgba(0,0,0,0.6), 0 0 0 1px rgba(255, 255, 255, 0.1); }
        #theater-video { width: 100%; max-height: 85vh; aspect-ratio: 16/9; object-fit: contain; outline: none; background: transparent; border-radius: 16px; }
        .theater-close { position: absolute; top: 20px; right: 20px; width: 44px; height: 44px; border-radius: 50%; background: rgba(0,0,0,0.5); color: #fff; border: 1px solid rgba(255,255,255,0.2); font-size: 20px; cursor: pointer; display: flex; align-items: center; justify-content: center; z-index: 10002; transition: all 0.2s; }
        .theater-close:hover { background: rgba(239, 68, 68, 0.8); transform: scale(1.1); border-color: transparent; }

        /* --- COMMENTS SIDEBAR CSS --- */
        #comments-sidebar { 
            position: fixed; top: 0; right: -400px; width: 100%; max-width: 400px; height: 100vh; 
            background: rgba(15, 15, 15, 0.98); backdrop-filter: blur(20px); border-left: 1px solid rgba(255,255,255,0.1); 
            box-shadow: -10px 0 50px rgba(0,0,0,0.5); display: flex; flex-direction: column; 
            transition: right 0.3s cubic-bezier(0.25, 0.46, 0.45, 0.94); z-index: 1000; 
        }
        #comments-sidebar.show { right: 0; }
        
        .comments-header { padding: 20px; border-bottom: 1px solid rgba(255,255,255,0.05); display: flex; justify-content: space-between; align-items: center; font-weight: 800; font-size: 1.2em; }
        .close-comments { background: transparent; border: none; color: #888; font-size: 1.2em; cursor: pointer; transition: color 0.2s; }
        .close-comments:hover { color: #fff; }
        .comments-list { flex: 1; overflow-y: auto; padding: 20px; display: flex; flex-direction: column; gap: 16px; }
        .comments-list::-webkit-scrollbar { width: 6px; }
        .comments-list::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.1); border-radius: 10px; }
        
        .comment-item { display: flex; flex-direction: column; gap: 4px; background: rgba(255,255,255,0.02); padding: 12px; border-radius: 12px; border: 1px solid rgba(255,255,255,0.02); }
        .comment-user { font-weight: 700; font-size: 0.85em; color: #a78bfa; }
        .comment-text { font-size: 0.95em; color: #ddd; line-height: 1.4; display: flex; align-items: center; flex-wrap: wrap; gap: 4px;}
        .chat-emote { height: 28px; vertical-align: middle; pointer-events: none;}
        
        /* RICH TEXT COMMENT INPUT */
        .comments-input-wrapper { padding: 16px 20px 24px 20px; border-top: 1px solid rgba(255,255,255,0.05); position: relative; display: flex; gap: 8px; background: #141414; align-items: flex-end;}
        
        .comment-input { 
            flex: 1; background: #0a0a0a; border: 1px solid rgba(255,255,255,0.1); border-radius: 20px; 
            padding: 12px 16px; color: #fff; font-family: 'Inter'; outline: none; 
            min-height: 44px; max-height: 120px; overflow-y: auto;
            display: flex; align-items: center; flex-wrap: wrap; align-content: center; line-height: 1.4;
        }
        .comment-input:focus { border-color: #8b5cf6; }
        .comment-input[contenteditable]:empty::before { content: attr(data-placeholder); color: #666; pointer-events: none; display: block; }
        
        .emote-toggle-btn { background: transparent; border: none; font-size: 1.4em; cursor: pointer; color: #888; transition: color 0.2s; height: 44px;}
        .emote-toggle-btn:hover { color: #ec4899; }
        .send-btn { background: #8b5cf6; color: #fff; border: none; border-radius: 20px; padding: 0 16px; font-weight: 600; cursor: pointer; transition: background 0.2s; height: 44px;}
        .send-btn:hover { background: #7c3aed; }
        
        /* Twitch Emote Picker */
        .emote-picker { position: absolute; bottom: 80px; right: 20px; background: #222; border: 1px solid rgba(255,255,255,0.1); border-radius: 12px; padding: 10px; display: none; grid-template-columns: repeat(4, 1fr); gap: 10px; box-shadow: 0 10px 25px rgba(0,0,0,0.5); z-index: 10002; }
        .emote-picker.show { display: grid; }
        .emote-option { cursor: pointer; transition: transform 0.1s; display: flex; justify-content: center; align-items: center; padding: 4px; border-radius: 6px;}
        .emote-option:hover { background: rgba(255,255,255,0.1); transform: scale(1.15); }
        .emote-option img { height: 32px; pointer-events: none;}

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
                <div class="action-buttons" id="action-btns">
                    <button class="btn-side btn-reject" onclick="triggerSwipeAnimation('left')" title="Skip">
                        <svg xmlns="http://www.w3.org/2000/svg" width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><path d="M9 14L4 9l5-5"/><path d="M4 9h10.5a5.5 5.5 0 0 1 5.5 5.5v.5"/></svg>
                    </button>
                    <button class="btn-side btn-accept" onclick="triggerSwipeAnimation('right')" title="Like">
                        <svg xmlns="http://www.w3.org/2000/svg" width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><path d="M15 14l5-5-5-5"/><path d="M20 9H9.5A5.5 5.5 0 0 0 4 14.5v.5"/></svg>
                    </button>
                </div>
                
                <div id="card-stack"></div>
                <div id="empty-state" class="empty-msg" style="display: none;">
                    <h2>All Caught Up</h2>
                    <p style="margin-top: 10px;">No more clips to vote on</p>
                </div>
            </div>
        </div>

        <div id="leaderboard" class="view-section">
            <div class="list-container">
                <h2 class="section-title">🏆 Top Viral Clips</h2>
                <div class="section-subtitle">Ranked by your swipes. Hover to preview, or click expand for Theater Mode!</div>
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
    
    <div id="theater-modal" style="display: none;">
        <div class="theater-backdrop" onclick="closeTheaterMode()"></div>
        <button class="theater-close" onclick="closeTheaterMode()">✕</button>
        <div class="theater-content">
            <video id="theater-video" controls playsinline autoplay></video>
            <div id="theater-loading" class="video-loading" style="display: none; top: auto; left: auto; transform: none; position: absolute;"></div>
        </div>
    </div>

    <div id="comments-sidebar">
        <div class="comments-header">
            <span id="comment-sidebar-title">Comments</span>
            <button class="close-comments" onclick="closeComments()">✕</button>
        </div>
        <div class="comments-list" id="comments-list">
            </div>
        <div class="comments-input-wrapper">
            <div class="emote-picker" id="emote-picker">
                <div class="emote-option" onclick="insertEmote('Kappa')"><img src="https://static-cdn.jtvnw.net/emoticons/v2/25/default/dark/1.0" alt="Kappa"></div>
                <div class="emote-option" onclick="insertEmote('LUL')"><img src="https://static-cdn.jtvnw.net/emoticons/v2/425618/default/dark/1.0" alt="LUL"></div>
                <div class="emote-option" onclick="insertEmote('PogChamp')"><img src="https://static-cdn.jtvnw.net/emoticons/v2/305954156/default/dark/1.0" alt="PogChamp"></div>
                <div class="emote-option" onclick="insertEmote('KEKW')"><img src="https://cdn.7tv.app/emote/5e9c6c18fd09b400e181a0e4/1x.webp" alt="KEKW"></div>
                <div class="emote-option" onclick="insertEmote('PepeLaugh')"><img src="https://cdn.7tv.app/emote/5e73099955eb7c006fb1d9f4/1x.webp" alt="PepeLaugh"></div>
                <div class="emote-option" onclick="insertEmote('Sadge')"><img src="https://cdn.7tv.app/emote/5e0fa9d40550d400155b2b06/1x.webp" alt="Sadge"></div>
                <div class="emote-option" onclick="insertEmote('EZ')"><img src="https://cdn.7tv.app/emote/5f1b0186cf6d8a4f54d0c327/1x.webp" alt="EZ"></div>
                <div class="emote-option" onclick="insertEmote('monkaW')"><img src="https://cdn.7tv.app/emote/5e7b78a9c2981a0076a032ba/1x.webp" alt="monkaW"></div>
            </div>
            <input type="hidden" id="active-comment-clip">
            <div id="comment-input" class="comment-input" contenteditable="true" data-placeholder="Add a comment..." onkeydown="if(event.key === 'Enter' && !event.shiftKey) { event.preventDefault(); postComment(); }"></div>
            <button class="emote-toggle-btn" onclick="toggleEmotePicker()">☺</button>
            <button class="send-btn" onclick="postComment()">Send</button>
        </div>
    </div>

    <div id="loading" style="display: none;">
        <div class="video-loading active" style="position: relative; top: auto; left: auto; transform: none; animation: spin 0.7s linear infinite;"></div>
        <p style="margin-top: 16px; font-weight: 600; color: #888;">Loading...</p>
    </div>

    <script>
        let clips = []; let currentIndex = 0; let isDragging = false; let isSwiping = false; 
        
        const EMOTES = {
            'Kappa': 'https://static-cdn.jtvnw.net/emoticons/v2/25/default/dark/1.0',
            'LUL': 'https://static-cdn.jtvnw.net/emoticons/v2/425618/default/dark/1.0',
            'PogChamp': 'https://static-cdn.jtvnw.net/emoticons/v2/305954156/default/dark/1.0',
            'KEKW': 'https://cdn.7tv.app/emote/5e9c6c18fd09b400e181a0e4/1x.webp',
            'PepeLaugh': 'https://cdn.7tv.app/emote/5e73099955eb7c006fb1d9f4/1x.webp',
            'Sadge': 'https://cdn.7tv.app/emote/5e0fa9d40550d400155b2b06/1x.webp',
            'EZ': 'https://cdn.7tv.app/emote/5f1b0186cf6d8a4f54d0c327/1x.webp',
            'monkaW': 'https://cdn.7tv.app/emote/5e7b78a9c2981a0076a032ba/1x.webp'
        };
        
        let stackRect, rejectBtnRect, acceptBtnRect;

        document.addEventListener('DOMContentLoaded', () => { loadClips(); refreshAdminQueue(); });
        
        function switchTab(tabId) {
            document.querySelectorAll('.view-section').forEach(el => el.classList.remove('active'));
            document.querySelectorAll('.tab-btn').forEach(el => el.classList.remove('active'));
            document.getElementById(tabId).classList.add('active');
            event.target.classList.add('active');
            
            closeComments(); 
            if (tabId === 'leaderboard') loadLeaderboard();
            if (tabId === 'admin') refreshAdminQueue();
        }

        async function loadClips() {
            showLoading(true);
            try {
                const res = await fetch('/api/clips');
                clips = (await res.json()).clips; currentIndex = 0; renderCardStack();
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
            
            const likes = clip.local_likes || 0;
            const commentsCount = clip.comment_count || 0;
            
            card.innerHTML = `
                <div class="clip-preview">
                    <div class="blur-bg-container"><img src="${clip.thumbnail_url}" draggable="false"></div>
                    <img src="${clip.thumbnail_url}" class="clip-thumbnail" draggable="false">
                    <video class="video-player" preload="metadata" loop playsinline ontimeupdate="updateProgress(this)"></video>
                    <div class="video-loading"></div>
                    <button class="fullscreen-btn" onclick="openTheaterMode(event, '${clip.id}')" title="Theater Mode">⛶</button>
                    <button class="play-pause-btn" onclick="toggleMainPlay(event, this)" title="Play/Pause">⏸</button>
                    <div class="volume-control"><button class="volume-btn" onclick="event.stopPropagation(); toggleMute(this)"><span class="volume-icon">🔊</span></button><input type="range" class="volume-slider" min="0" max="100" value="30" oninput="event.stopPropagation(); changeVolume(this)"></div>
                    <div class="progress-container"><input type="range" class="progress-slider" min="0" max="100" value="0" step="0.1" oninput="event.stopPropagation(); seekVideo(this)"></div>
                </div>
                <div class="clip-info" onmousedown="event.stopPropagation()" ontouchstart="event.stopPropagation()">
                    <div class="clip-title">${clip.title}</div>
                    <div class="creator">${clip.creator_name} • ${clip.channel}</div>
                    
                    <div class="clip-meta">
                        <div style="display:flex; gap:8px;">
                            <span class="views-badge">👁️ ${clip.view_count >= 1000 ? (clip.view_count/1000).toFixed(1)+'K' : clip.view_count}</span>
                            <span class="duration-badge">⏱️ ${Math.floor(clip.duration)}s</span>
                        </div>
                        <div class="social-counters">
                            <div class="social-badge" title="Total Likes">♥ <span>${likes}</span></div>
                            <button class="social-btn" onclick="event.stopPropagation(); openComments('${clip.id}', '${clip.title.replace(/'/g, "\\'")}')">💬 <span id="cc-${clip.id}">${commentsCount}</span></button>
                        </div>
                    </div>
                </div>
                
                <div id="nope-hint" class="swipe-hint left">
                    <div class="aura-strings"></div>
                    <div class="hint-text-main">NOPE</div>
                    <div class="hint-text-bubbly">I dare you!</div>
                </div>
                <div id="like-hint" class="swipe-hint right">
                    <div class="aura-strings"></div>
                    <div class="hint-text-main">LIKE</div>
                    <div class="hint-text-bubbly">Shiny! ✨</div>
                </div>
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

        // --- PLAYBACK CONTROLS ---
        function updateProgress(video) {
            const slider = video.closest('.clip-card').querySelector('.progress-slider');
            if (slider && video.duration) {
                const p = (video.currentTime / video.duration) * 100;
                slider.value = p; slider.style.background = `linear-gradient(to right, #ec4899 ${p}%, rgba(255, 255, 255, 0.2) ${p}%)`;
            }
        }
        function seekVideo(slider) {
            const video = slider.closest('.clip-card').querySelector('.video-player');
            if (video && video.duration) { video.currentTime = (slider.value / 100) * video.duration; }
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
            const playBtn = card.querySelector('.play-pause-btn');
            
            const attemptPlay = async () => {
                try { video.muted = false; video.volume = 0.3; await video.play(); icon.textContent = '🔊'; if(playBtn) playBtn.textContent = '⏸'; } 
                catch (err) { video.muted = true; try { await video.play(); icon.textContent = '🔇'; if(playBtn) playBtn.textContent = '⏸'; } catch (err2) {} }
                video.classList.add('playing'); card.querySelector('.clip-thumbnail').style.opacity = '0'; loading.classList.remove('active');
            };
            if (video.src && video.readyState >= 2) { attemptPlay(); return; }
            loading.classList.add('active');
            try {
                const res = await fetch(`/api/clip/${card.dataset.clipId}/video-url`); const data = await res.json();
                if (data.video_url) { video.src = data.video_url; video.addEventListener('loadeddata', attemptPlay, { once: true }); }
            } catch (e) { loading.classList.remove('active'); }
        }
        
        function stopVideoPlay(card) {
            const video = card.querySelector('.video-player');
            const playBtn = card.querySelector('.play-pause-btn');
            if (video) { video.pause(); video.muted = true; video.classList.remove('playing'); if(playBtn) playBtn.textContent = '▶'; }
            const thumb = card.querySelector('.clip-thumbnail'); if (thumb) thumb.style.opacity = '1';
        }
        
        function toggleMainPlay(e, btn) {
            e.stopPropagation(); const video = btn.closest('.clip-card').querySelector('.video-player');
            if (video.paused) { video.play(); btn.textContent = '⏸'; } else { video.pause(); btn.textContent = '▶'; }
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

        // --- DYNAMIC SWIPE LOGIC WITH THE "GENIE" SUCK ANIMATION ---
        function makeCardSwipeable(card) {
            if (card.dataset.swipeable === 'true') return; card.dataset.swipeable = 'true';
            let startX = 0, currentX = 0, ticking = false;
            
            const nopeHint = card.querySelector('#nope-hint');
            const likeHint = card.querySelector('#like-hint');
            
            const rejectBtn = document.querySelector('.btn-reject');
            const acceptBtn = document.querySelector('.btn-accept');
            const stack = document.getElementById('card-stack');

            const doDrag = (e) => {
                if (!isDragging) return; e.preventDefault(); currentX = (e.type.includes('mouse') ? e : e.touches[0]).clientX;
                if (!ticking) {
                    window.requestAnimationFrame(() => {
                        if (!isDragging) return; const deltaX = currentX - startX; 
                        
                        // Calculate Magnetic Sucking Physics
                        const dragDistance = Math.abs(deltaX);
                        const maxDrag = window.innerWidth / 3.5; 
                        const rawProgress = Math.min(1, dragDistance / maxDrag);
                        
                        // Exponential easing for the suck effect
                        const suckEase = Math.pow(rawProgress, 3); 
                        const scale = 1 - (suckEase * 0.9); // Shrinks to 10%
                        const rot = deltaX * 0.05; 
                        
                        let targetX = deltaX;
                        let targetY = Math.abs(deltaX) * -0.05; 
                        
                        const swipeThreshold = 50;
                        
                        if (deltaX < -swipeThreshold) { 
                            card.classList.add('dragging-nope'); card.classList.remove('dragging-like'); 
                            
                            // Magnetic Pull towards Reject Button
                            if (rejectBtnRect && stackRect) {
                                const btnX = (rejectBtnRect.left + rejectBtnRect.width/2) - (stackRect.left + stackRect.width/2);
                                const btnY = (rejectBtnRect.top + rejectBtnRect.height/2) - (stackRect.top + stackRect.height/2);
                                targetX = deltaX + (btnX - deltaX) * suckEase;
                                targetY = targetY + (btnY - targetY) * suckEase;
                            }
                            
                            if(nopeHint) { nopeHint.style.transform = `scale(${0.5 + rawProgress * 0.7})`; nopeHint.style.opacity = rawProgress * 1.5; }
                            if(rejectBtn) { rejectBtn.classList.add('highlight'); }
                            if(acceptBtn) { acceptBtn.classList.remove('highlight'); }
                            
                        } else if (deltaX > swipeThreshold) { 
                            card.classList.add('dragging-like'); card.classList.remove('dragging-nope'); 
                            
                            // Magnetic Pull towards Accept Button
                            if (acceptBtnRect && stackRect) {
                                const btnX = (acceptBtnRect.left + acceptBtnRect.width/2) - (stackRect.left + stackRect.width/2);
                                const btnY = (acceptBtnRect.top + acceptBtnRect.height/2) - (stackRect.top + stackRect.height/2);
                                targetX = deltaX + (btnX - deltaX) * suckEase;
                                targetY = targetY + (btnY - targetY) * suckEase;
                            }
                            
                            if(likeHint) { likeHint.style.transform = `scale(${0.5 + rawProgress * 0.7})`; likeHint.style.opacity = rawProgress * 1.5; }
                            if(acceptBtn) { acceptBtn.classList.add('highlight'); }
                            if(rejectBtn) { rejectBtn.classList.remove('highlight'); }
                            
                        } else { 
                            card.classList.remove('dragging-nope', 'dragging-like'); 
                            if(nopeHint) nopeHint.style.opacity = 0;
                            if(likeHint) likeHint.style.opacity = 0;
                            if(rejectBtn) rejectBtn.classList.remove('highlight');
                            if(acceptBtn) acceptBtn.classList.remove('highlight');
                        }
                        
                        card.style.transformOrigin = 'center center';
                        card.style.transform = `translate(${targetX}px, ${targetY}px) scale(${scale}) rotate(${rot}deg)`;
                        
                        ticking = false;
                    }); ticking = true;
                }
            };
            
            const stopDrag = () => {
                if (!isDragging) return; isDragging = false;
                document.removeEventListener('mousemove', doDrag); document.removeEventListener('mouseup', stopDrag); document.removeEventListener('touchmove', doDrag); document.removeEventListener('touchend', stopDrag);
                
                const deltaX = currentX - startX;
                card.classList.remove('dragging-nope', 'dragging-like');
                if(nopeHint) { nopeHint.style.opacity = 0; nopeHint.style.transform = 'scale(0.5)'; }
                if(likeHint) { likeHint.style.opacity = 0; likeHint.style.transform = 'scale(0.5)'; }
                if(rejectBtn) rejectBtn.classList.remove('highlight');
                if(acceptBtn) acceptBtn.classList.remove('highlight');

                if (Math.abs(deltaX) > 130) { 
                    card.classList.remove('top-card'); 
                    animateSwipe(card, deltaX > 0 ? 'right' : 'left'); 
                } else { 
                    card.style.transition = 'transform 0.4s cubic-bezier(0.2, 1, 0.3, 1)'; 
                    card.style.transform = ''; 
                    setTimeout(() => { card.style.transition = ''; }, 400);
                }
            };

            const startDrag = (e) => {
                if (e.target.closest('.volume-control') || e.target.closest('.fullscreen-btn') || e.target.closest('.play-pause-btn') || e.target.closest('.progress-container') || e.target.closest('.clip-info')) return;
                if (isSwiping) return; 
                
                // Cache Button Rects for real-time physics calculations
                if(rejectBtn) rejectBtnRect = rejectBtn.getBoundingClientRect();
                if(acceptBtn) acceptBtnRect = acceptBtn.getBoundingClientRect();
                if(stack) stackRect = stack.getBoundingClientRect();
                
                isDragging = true; card.classList.add('dragging'); startX = (e.type.includes('mouse') ? e : e.touches[0]).clientX; currentX = startX;
                stopVideoPlay(card);
                document.addEventListener('mousemove', doDrag); document.addEventListener('mouseup', stopDrag); document.addEventListener('touchmove', doDrag, {passive: false}); document.addEventListener('touchend', stopDrag);
            };
            card.addEventListener('mousedown', startDrag); card.addEventListener('touchstart', startDrag, {passive: false});
        }
        
        function animateSwipe(card, direction) {
            if (isSwiping) return; isSwiping = true;
            try { const v = card.querySelector('.video-player'); if(v){ v.pause(); v.removeAttribute('src'); v.load(); } } catch(e){}
            
            card.classList.remove('dragging');
            void card.offsetWidth; // Force CSS Reflow to ensure transition runs
            
            const btnSelector = direction === 'right' ? '.btn-accept' : '.btn-reject';
            const targetBtn = document.querySelector(btnSelector);
            const stack = document.getElementById('card-stack');

            let targetX = direction === 'right' ? window.innerWidth : -window.innerWidth;
            let targetY = 0;

            // Final Apple Genie snap into the actual button center
            if (targetBtn && stack) {
                const btnRect = targetBtn.getBoundingClientRect();
                const stackRect = stack.getBoundingClientRect();
                targetX = (btnRect.left + btnRect.width/2) - (stackRect.left + stackRect.width/2);
                targetY = (btnRect.top + btnRect.height/2) - (stackRect.top + stackRect.height/2);
            }
            
            requestAnimationFrame(() => {
                requestAnimationFrame(() => {
                    // Fast Spring Transition
                    card.style.transition = 'transform 0.35s cubic-bezier(0.4, -0.3, 0.1, 1.2), opacity 0.3s ease-out';
                    card.style.transformOrigin = 'center center';
                    card.style.transform = `translate(${targetX}px, ${targetY}px) scale(0) rotate(${direction === 'right' ? 180 : -180}deg)`;
                    card.style.opacity = '0';
                });
            });
            
            closeComments(); 
            setTimeout(() => { handleSwipe(card.dataset.clipId, direction); currentIndex++; renderCardStack(); isSwiping = false; }, 360);
        }

        // Button clicks trigger the exact same suck animation
        function triggerSwipeAnimation(direction) {
            const card = document.querySelector('.clip-card.top-card');
            if (card && !isDragging && !isSwiping) {
                // 1. Cache button positions FIRST
                const rejectBtn = document.querySelector('.btn-reject');
                const acceptBtn = document.querySelector('.btn-accept');
                const stack = document.getElementById('card-stack');
                
                if(rejectBtn) rejectBtnRect = rejectBtn.getBoundingClientRect();
                if(acceptBtn) acceptBtnRect = acceptBtn.getBoundingClientRect();
                if(stack) stackRect = stack.getBoundingClientRect();
                
                // 2. Highlight the target button
                const targetBtn = direction === 'left' ? rejectBtn : acceptBtn;
                if (targetBtn) {
                    targetBtn.classList.add('highlight');
                    setTimeout(() => targetBtn.classList.remove('highlight'), 400);
                }
                
                // 3. Trigger the same genie animation
                card.classList.remove('top-card');
                animateSwipe(card, direction);
            }
        }
        
        function swipeLeft() { triggerSwipeAnimation('left'); }
        function swipeRight() { triggerSwipeAnimation('right'); }
        
        async function handleSwipe(clipId, direction) {
            await fetch(`/api/clip/${clipId}/action`, { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({action: direction === 'right' ? 'like' : 'dislike'}) });
        }

        // --- SIDEBAR COMMENTS SYSTEM ---
        function openComments(clipId, title) {
            document.getElementById('active-comment-clip').value = clipId;
            document.getElementById('comments-list').innerHTML = '<div style="text-align:center; padding:20px; color:#888;">Loading...</div>';
            document.body.classList.add('comments-open');
            document.getElementById('comments-sidebar').classList.add('show');
            loadCommentsForClip(clipId);
        }
        
        function closeComments() {
            document.body.classList.remove('comments-open');
            document.getElementById('comments-sidebar').classList.remove('show');
            document.getElementById('emote-picker').classList.remove('show');
        }
        
        function toggleEmotePicker() { document.getElementById('emote-picker').classList.toggle('show'); }
        
        function insertEmote(emoteName) {
            const input = document.getElementById('comment-input');
            const emoteUrl = EMOTES[emoteName];
            const imgHtml = `<img src="${emoteUrl}" class="chat-emote" alt="${emoteName}" contenteditable="false" style="margin: 0 4px;">`;
            input.innerHTML += imgHtml + '&nbsp;';
            const range = document.createRange(); const sel = window.getSelection();
            range.selectNodeContents(input); range.collapse(false); sel.removeAllRanges(); sel.addRange(range);
            input.focus(); document.getElementById('emote-picker').classList.remove('show');
        }

        async function loadCommentsForClip(clipId) {
            try {
                const res = await fetch(`/api/clip/${clipId}/comments`); const comments = await res.json();
                const list = document.getElementById('comments-list');
                if (comments.length === 0) { list.innerHTML = '<div style="text-align:center; padding:40px 20px; color:#666;">No comments yet. Be the first!</div>'; return; }
                list.innerHTML = '';
                comments.forEach(c => {
                    const div = document.createElement('div'); div.className = 'comment-item';
                    div.innerHTML = `<div class="comment-user">${c.user}</div><div class="comment-text">${c.text}</div>`;
                    list.appendChild(div);
                });
                list.scrollTop = list.scrollHeight;
                const ccSpan = document.getElementById(`cc-${clipId}`); if (ccSpan) ccSpan.textContent = comments.length;
            } catch(e) { console.error(e); }
        }
        
        async function postComment() {
            const input = document.getElementById('comment-input');
            const text = input.innerHTML.trim(); const clipId = document.getElementById('active-comment-clip').value;
            if (!text || text === '<br>' || !clipId) return;
            input.innerHTML = '';
            try {
                await fetch(`/api/clip/${clipId}/comments`, { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({text: text}) });
                loadCommentsForClip(clipId);
            } catch (e) { alert("Failed to post comment"); }
        }

        // --- MINI LIST HOVER VIDEO PREVIEW LOGIC ---
        async function playMiniVideo(container, clipId) {
            container.dataset.hovered = 'true'; const video = container.querySelector('video');
            if (video.src && video.readyState >= 2) { video.play(); video.classList.add('playing'); return; }
            container.classList.add('loading');
            try {
                const res = await fetch(`/api/clip/${clipId}/video-url`); const data = await res.json();
                if (data.video_url && container.dataset.hovered === 'true') {
                    video.src = data.video_url;
                    video.addEventListener('loadeddata', () => { if (container.dataset.hovered === 'true') { container.classList.remove('loading'); video.play(); video.classList.add('playing'); } }, { once: true });
                }
            } catch (e) { container.classList.remove('loading'); }
        }
        function stopMiniVideo(container) {
            container.dataset.hovered = 'false'; const video = container.querySelector('video');
            video.pause(); video.classList.remove('playing'); container.classList.remove('loading');
            container.querySelector('.play-btn').textContent = '⏸'; container.querySelector('.mute-btn').textContent = '🔇'; video.muted = true;
        }
        function toggleMiniPlay(e, btn) { e.stopPropagation(); const video = btn.closest('.thumb-container').querySelector('video'); if (video.paused) { video.play(); btn.textContent = '⏸'; } else { video.pause(); btn.textContent = '▶'; } }
        function toggleMiniMute(e, btn) { e.stopPropagation(); const video = btn.closest('.thumb-container').querySelector('video'); video.muted = !video.muted; btn.textContent = video.muted ? '🔇' : '🔊'; if (!video.muted && video.volume === 0) video.volume = 0.5; }

        // --- GLOBAL THEATER MODE ---
        async function openTheaterMode(e, clipId) {
            e.stopPropagation();
            const thumbVideo = e.target.closest('.thumb-container')?.querySelector('video'); if (thumbVideo) thumbVideo.pause();
            const mainVideo = e.target.closest('.clip-card')?.querySelector('.video-player');
            if (mainVideo) { mainVideo.pause(); const playBtn = e.target.closest('.clip-card').querySelector('.play-pause-btn'); if (playBtn) playBtn.textContent = '▶'; }

            const modal = document.getElementById('theater-modal'), theaterVideo = document.getElementById('theater-video'), loader = document.getElementById('theater-loading');
            modal.style.display = 'flex'; setTimeout(() => modal.classList.add('show'), 10);
            theaterVideo.src = ''; loader.style.display = 'block';
            
            try {
                const res = await fetch(`/api/clip/${clipId}/video-url`); const data = await res.json();
                if (data.video_url) {
                    theaterVideo.src = data.video_url;
                    theaterVideo.addEventListener('loadeddata', () => { loader.style.display = 'none'; theaterVideo.volume = 0.5; theaterVideo.play(); }, { once: true });
                }
            } catch (err) { loader.style.display = 'none'; alert("Could not load full video."); }
        }
        function closeTheaterMode() {
            const modal = document.getElementById('theater-modal'), theaterVideo = document.getElementById('theater-video');
            theaterVideo.pause(); theaterVideo.src = ''; modal.classList.remove('show'); setTimeout(() => modal.style.display = 'none', 300);
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
                    const commentsCount = clip.comment_count || 0;
                    const div = document.createElement('div'); div.className = 'list-item';
                    div.innerHTML = `
                        <div style="font-size: 1.2em; font-weight: 900; color: #888; width: 40px; text-align: center;">#${index + 1}</div>
                        <div class="thumb-wrapper">
                            <div class="thumb-container" onmouseenter="playMiniVideo(this, '${clip.id}')" onmouseleave="stopMiniVideo(this)">
                                <img src="${clip.thumbnail_url}"><div class="mini-spinner"></div><video loop muted playsinline></video>
                                <div class="mini-controls"><div style="display:flex; gap:4px;"><button class="mini-btn play-btn" onclick="toggleMiniPlay(event, this)">⏸</button><button class="mini-btn mute-btn" onclick="toggleMiniMute(event, this)">🔇</button></div><button class="mini-btn" onclick="openTheaterMode(event, '${clip.id}')">⛶</button></div>
                            </div>
                        </div>
                        <div class="item-details">
                            <div class="item-title">${clip.title}</div>
                            <div class="item-stats">
                                <span class="score-badge">♥ ${clip.local_likes} Likes</span>
                                <button class="social-btn" onclick="openComments('${clip.id}', '${clip.title.replace(/'/g, "\\'")}')" style="padding: 2px 8px; font-size: 1em; background:transparent; border:1px solid rgba(255,255,255,0.1);">💬 <span id="cc-${clip.id}">${commentsCount}</span></button>
                                <span>👁️ ${clip.view_count} views</span> • <span>${clip.channel}</span>
                            </div>
                        </div>
                        <button class="btn-small btn-outline" onclick="sendToAdminQueue('${clip.id}')">+ Send to Queue</button>
                    `;
                    container.appendChild(div);
                });
            } catch(e) { console.error(e); }
        }
        async function sendToAdminQueue(clipId) { await fetch(`/api/admin/queue`, { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({clip_id: clipId}) }); refreshAdminQueue(); alert("✅ Sent to Admin Upload Queue!"); }

        // --- ADMIN QUEUE LOGIC ---
        async function refreshAdminQueue() {
            try {
                const res = await fetch('/api/accepted'); const accepted = await res.json();
                document.getElementById('queue-badge').textContent = accepted.length; document.getElementById('admin-count').textContent = accepted.length;
                const container = document.getElementById('admin-list'), footer = document.getElementById('admin-footer');
                if (accepted.length === 0) { container.innerHTML = '<div class="empty-msg">Admin queue is empty.<br><br>Add clips from the Leaderboard to process them.</div>'; footer.style.display = 'none'; return; }
                footer.style.display = 'flex'; container.innerHTML = '';
                accepted.forEach(clip => {
                    const div = document.createElement('div'); div.className = 'list-item';
                    div.innerHTML = `
                        <div class="thumb-wrapper">
                            <div class="thumb-container" onmouseenter="playMiniVideo(this, '${clip.id}')" onmouseleave="stopMiniVideo(this)">
                                <img src="${clip.thumbnail_url}"><div class="mini-spinner"></div><video loop muted playsinline></video>
                                <div class="mini-controls"><div style="display:flex; gap:4px;"><button class="mini-btn play-btn" onclick="toggleMiniPlay(event, this)">⏸</button><button class="mini-btn mute-btn" onclick="toggleMiniMute(event, this)">🔇</button></div><button class="mini-btn" onclick="openTheaterMode(event, '${clip.id}')">⛶</button></div>
                            </div>
                        </div>
                        <div class="item-details"><div class="item-title">${clip.title}</div><div class="item-stats">Ready for Upload • ${clip.channel}</div></div>
                        <div class="action-group"><button class="btn-small btn-danger" onclick="removeFromAdminQueue('${clip.id}')">Remove</button><button class="btn-small btn-primary" onclick="processSingle('${clip.id}')">Upload Now</button></div>
                    `;
                    container.appendChild(div);
                });
            } catch(e) { console.error(e); }
        }
        async function removeFromAdminQueue(clipId) { await fetch('/api/admin/remove', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({clip_id: clipId}) }); refreshAdminQueue(); }
        async function processSingle(clipId) { showLoading(true); try { await fetch('/api/process', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({clip_ids: [clipId]}) }); alert(`Upload started! Check terminal for progress.`); refreshAdminQueue(); } catch(e) { alert('Error processing clip'); } finally { showLoading(false); } }
        async function processAllClips() {
            const res = await fetch('/api/accepted'); const accepted = await res.json();
            if (accepted.length === 0) return; if (!confirm(`Process and upload ${accepted.length} clips?`)) return;
            showLoading(true); try { const ids = accepted.map(c => c.id); await fetch('/api/process', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({clip_ids: ids}) }); alert(`🚀 Processing ${accepted.length} clips in the background!`); refreshAdminQueue(); } catch(e) { alert('Error processing clips'); } finally { showLoading(false); }
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
        
    for clip in clips_queue:
        clip['local_likes'] = clip_scores.get(clip['id'], 0)
        clip['comment_count'] = len(clip_comments.get(clip['id'], []))
        
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

@app.route('/api/clip/<clip_id>/comments', methods=['GET', 'POST'])
def handle_comments(clip_id):
    global clip_comments
    
    if request.method == 'GET':
        return jsonify(clip_comments.get(clip_id, []))
        
    elif request.method == 'POST':
        data = request.json
        text = data.get('text', '').strip()
        if not text: 
            return jsonify({'error': 'empty'}), 400
            
        if clip_id not in clip_comments:
            clip_comments[clip_id] = []
            
        new_comment = {
            'user': 'AnonymousGamer',
            'text': text,
            'timestamp': str(datetime.datetime.now())
        }
        clip_comments[clip_id].append(new_comment)
        return jsonify({'status': 'success', 'comment': new_comment})

@app.route('/api/leaderboard')
def get_leaderboard():
    ranked_clips = []
    for cid, likes in clip_scores.items():
        if cid in clip_metadata_store:
            clip_info = clip_metadata_store[cid].copy()
            clip_info['local_likes'] = likes
            clip_info['comment_count'] = len(clip_comments.get(cid, []))
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
    print("🔥 Clipder Pro - Full Master Edition")
    print("="*60)
    print(f"Status: {bot_initialized}")
    print("✅ Apple 'Genie' Suck Physics Implemented")
    print("Open: http://localhost:5000")
    print("="*60 + "\n")
    app.run(debug=True, host='0.0.0.0', port=5000)