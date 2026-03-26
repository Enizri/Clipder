from http.client import HTTPException
import os
import json
import requests
import pickle
import sys
import subprocess
import time
from pathlib import Path
from typing import Dict, List, Set, Optional
from dataclasses import dataclass
import logging
import dotenv
import numpy as np
from moviepy import VideoFileClip, CompositeVideoClip
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import yt_dlp

# ==============================================================================
# FIX WINDOWS CONSOLE ENCODING FOR EMOJIS
# ==============================================================================
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except AttributeError:
        import codecs
        sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
        sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

# ==============================================================================
# CONFIGURATION & LOGGING
# ==============================================================================
dotenv.load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler('clip_bot.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

@dataclass
class Config:
    """Configuration"""
    twitch_client_id: str
    twitch_client_secret: str
    groq_api_key: str
    twitch_channels: List[str]
    twitch_categories: List[str]  # NEW: For Category Tabs
    base_dir: Path
    client_secrets_file: Path
    token_pickle: Path
    uploaded_json: Path
    download_folder: Path
    processed_folder: Path
    
    opus_clip_api_key: Optional[str] = None
    use_opus_clip: bool = False
    add_captions: bool = True
    caption_style: str = "tiktok"
    target_duration: int = 45
    viral_threshold: float = 0.6
    groq_transcription_model: str = "whisper-large-v3-turbo"
    groq_chat_model: str = "llama-3.3-70b-versatile"
    youtube_category: str = "20"
    youtube_privacy: str = "public"
    api_timeout: int = 30

    @classmethod
    def from_env(cls) -> 'Config':
        base_dir = Path(__file__).parent
        required = ["TWITCH_CLIENT_ID", "TWITCH_CLIENT_SECRET", "GROQ_API_KEY"]
        missing = [v for v in required if not os.getenv(v)]
        if missing:
            raise ValueError(f"Missing: {', '.join(missing)}")
        
        channels = [ch.strip() for ch in os.getenv("TWITCH_CHANNELS", "").split(",") if ch.strip()]
        if not channels:
            raise ValueError("No channels in TWITCH_CHANNELS")
            
        # Parse Categories
        categories = [c.strip() for c in os.getenv("TWITCH_CATEGORIES", "Just Chatting, Grand Theft Auto V, VALORANT, League of Legends").split(",") if c.strip()]
        
        opus_key = os.getenv("OPUS_CLIP_API_KEY")
        use_opus = opus_key is not None and len(opus_key) > 0
        
        return cls(
            twitch_client_id=os.getenv("TWITCH_CLIENT_ID"),
            twitch_client_secret=os.getenv("TWITCH_CLIENT_SECRET"),
            groq_api_key=os.getenv("GROQ_API_KEY"),
            opus_clip_api_key=opus_key,
            use_opus_clip=use_opus,
            twitch_channels=channels,
            twitch_categories=categories,
            base_dir=base_dir,
            client_secrets_file=base_dir / "client_secrets.json",
            token_pickle=base_dir / "token.pickle",
            uploaded_json=base_dir / "uploaded_clips.json",
            download_folder=base_dir / "clips_to_process",
            processed_folder=base_dir / "processed_clips"
        )

# ==============================================================================
# TWITCH CLIENT
# ==============================================================================
class TwitchClient:
    def __init__(self, config: Config):
        self.config = config
        self._token = None
    
    @property
    def headers(self) -> Dict[str, str]:
        if not self._token:
            self._refresh_token()
        return {
            "Client-ID": self.config.twitch_client_id,
            "Authorization": f"Bearer {self._token}"
        }
    
    def _refresh_token(self):
        url = "https://id.twitch.tv/oauth2/token"
        data = {
            "client_id": self.config.twitch_client_id,
            "client_secret": self.config.twitch_client_secret,
            "grant_type": "client_credentials"
        }
        try:
            response = requests.post(url, data=data, timeout=10)
            response.raise_for_status()
            self._token = response.json()["access_token"]
        except requests.exceptions.HTTPError as e:
            print(f"Twitch Auth Failed: {e.response.text}")
            raise HTTPException(status_code=401, detail="Twitch credentials invalid")

    def get_broadcaster_id(self, username: str) -> Optional[str]:
        url = f"https://api.twitch.tv/helix/users?login={username}"
        response = requests.get(url, headers=self.headers, timeout=10)
        response.raise_for_status()
        data = response.json().get("data", [])
        return data[0]["id"] if data else None

    # NEW: Find a Game/Category ID from Twitch
    def get_game_id(self, game_name: str) -> Optional[str]:
        url = f"https://api.twitch.tv/helix/games?name={game_name}"
        try:
            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()
            data = response.json().get("data", [])
            return data[0]["id"] if data else None
        except Exception as e:
            logger.error(f"Error fetching game ID for {game_name}: {e}")
            return None
    
    def get_recent_clips(self, broadcaster_id: str, hours_back: int = 24, fetch_count: int = 100) -> List[Dict]:
        import datetime
        start_time = (
            datetime.datetime.now(datetime.timezone.utc) - 
            datetime.timedelta(hours=hours_back)
        ).isoformat().split('.')[0] + 'Z'
        url = f"https://api.twitch.tv/helix/clips?broadcaster_id={broadcaster_id}&first={fetch_count}&started_at={start_time}"
        try:
            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()
            return response.json().get("data", [])
        except Exception as e:
            logger.error(f"Error fetching clips: {e}")
            return []

    # NEW: Fetch clips specifically by the Game/Category ID
    def get_recent_clips_by_game(self, game_id: str, hours_back: int = 72, fetch_count: int = 100) -> List[Dict]:
        import datetime
        start_time = (
            datetime.datetime.now(datetime.timezone.utc) - 
            datetime.timedelta(hours=hours_back)
        ).isoformat().split('.')[0] + 'Z'
        url = f"https://api.twitch.tv/helix/clips?game_id={game_id}&first={fetch_count}&started_at={start_time}"
        try:
            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()
            return response.json().get("data", [])
        except Exception as e:
            logger.error(f"Error fetching clips by game: {e}")
            return []

# ==============================================================================
# CAPTION GENERATOR
# ==============================================================================
class CaptionGenerator:
    def __init__(self, config: Config):
        self.config = config
        self.groq_headers = {"Authorization": f"Bearer {config.groq_api_key}"}
    
    def transcribe_with_timestamps(self, audio_path: Path) -> Dict:
        try:
            url = "https://api.groq.com/openai/v1/audio/transcriptions"
            with open(audio_path, "rb") as f:
                response = requests.post(
                    url, headers=self.groq_headers,
                    files={"file": (audio_path.name, f, "audio/mpeg")},
                    data={"model": self.config.groq_transcription_model, "response_format": "verbose_json", "timestamp_granularities": ["word"]},
                    timeout=self.config.api_timeout
                )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            return {}
    
    def create_subtitle_file(self, transcript_data: Dict, output_path: Path) -> bool:
        try:
            words = transcript_data.get("words", [])
            if not words: return False
            ass_content = """[Script Info]\nTitle: TikTok Style\nScriptType: v4.00+\nPlayResX: 1080\nPlayResY: 1920\n\n[V4+ Styles]\nFormat: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\nStyle: Default,Arial,70,&H00FFFFFF,&H000000FF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,3,2,2,30,30,250,1\n\n[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"""
            chunk_size = 4
            for i in range(0, len(words), chunk_size):
                chunk = words[i:i+chunk_size]
                text = " ".join([w["word"] for w in chunk]).upper()
                ass_content += f"Dialogue: 0,{self._sec_to_ass(chunk[0]['start'])},{self._sec_to_ass(chunk[-1]['end'])},Default,,0,0,0,,{text}\n"
            with open(output_path, "w", encoding="utf-8") as f: f.write(ass_content)
            return True
        except Exception as e:
            return False
    
    def _sec_to_ass(self, seconds: float) -> str:
        hours, minutes, secs = int(seconds // 3600), int((seconds % 3600) // 60), seconds % 60
        return f"{hours}:{minutes:02d}:{secs:05.2f}"

# ==============================================================================
# OTHER CLIENTS (Video, Groq, YT, TikTok, DB)
# ==============================================================================
class OpusClipClient:
    def __init__(self, config: Config):
        self.config = config; self.api_key = config.opus_clip_api_key; self.base_url = "https://api.opus.pro/api/v1"
    def upload_and_process(self, video_path: Path, title: str) -> Optional[Dict]: return None
    def download_clip(self, opus_data: Dict, output_path: Path) -> bool: return False

class GroqClient:
    def __init__(self, config: Config):
        self.config = config; self.headers = {"Authorization": f"Bearer {config.groq_api_key}"}
    def transcribe_audio(self, file_path: Path) -> str:
        try:
            with open(file_path, "rb") as f:
                response = requests.post("https://api.groq.com/openai/v1/audio/transcriptions", headers=self.headers, files={"file": (file_path.name, f, "audio/mpeg")}, data={"model": self.config.groq_transcription_model}, timeout=30)
            return response.json().get("text", "")
        except: return ""
    def analyze_clip(self, transcript: str, title: str, view_count: int) -> Dict:
        try:
            prompt = f"Analyze clip.\nTitle: {title}\nViews: {view_count}\nTranscript: {transcript}\nReturn ONLY JSON: {{\"score\": 0.0, \"title\": \"...\", \"description\": \"...\"}}"
            response = requests.post("https://api.groq.com/openai/v1/chat/completions", headers={**self.headers, "Content-Type": "application/json"}, json={"model": self.config.groq_chat_model, "messages": [{"role": "user", "content": prompt}], "response_format": {"type": "json_object"}}, timeout=30)
            meta = json.loads(response.json()["choices"][0]["message"]["content"])
            meta["score"] = float(meta.get("score", 0.0))
            return meta
        except: return {"score": 0.0, "title": title, "description": f"{title} #gaming"}

class VideoProcessor:
    def __init__(self, config: Config):
        self.config = config; self.opus_clip = OpusClipClient(config) if config.use_opus_clip else None; self.caption_gen = CaptionGenerator(config)
    def download_clip(self, clip_url: str, clip_id: str) -> Optional[Path]:
        try:
            output = self.config.download_folder / f"{clip_id}.mp4"
            with yt_dlp.YoutubeDL({'outtmpl': str(output), 'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best', 'quiet': True, 'merge_output_format': 'mp4'}) as ydl:
                ydl.download([clip_url])
            return output if output.exists() else None
        except: return None
    def create_tiktok_style_video(self, source_path: Path, clip_id: str, title: str = "", description: str = "") -> Optional[Path]: return source_path

class YouTubeUploader:
    def __init__(self, config: Config): self.config = config; self._service = None
    def upload(self, file_path: Path, title: str, description: str) -> Optional[str]: return "yt_id_mock"

class TikTokUploader:
    def __init__(self, config: Config): self.config = config; self.cookies_file = config.base_dir / "tiktok.com_cookies.txt"
    def upload(self, file_path: Path, title: str, description: str) -> bool: return True

class StateManager:
    def __init__(self, config: Config):
        self.config = config; self.db_file = config.base_dir / "clipder_db.json"; self._db = {"clips": {}}
        if self.db_file.exists():
            with open(self.db_file, "r", encoding="utf-8") as f: self._db = json.load(f)
    def _save(self):
        with open(self.db_file, "w", encoding="utf-8") as f: json.dump(self._db, f, indent=2)
    def is_processed(self, clip_id: str) -> bool: return self._db["clips"].get(clip_id, {}).get("status") in ["uploaded", "rejected"]
    def mark_processed(self, clip_id: str):
        if clip_id not in self._db["clips"]: self._db["clips"][clip_id] = {}
        self._db["clips"][clip_id]["status"] = "uploaded"
        self._save()

class ClipBot:
    def __init__(self): self.config = Config.from_env()
    def run(self): pass

if __name__ == "__main__":
    pass