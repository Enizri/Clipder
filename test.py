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
    # Required
    twitch_client_id: str
    twitch_client_secret: str
    groq_api_key: str
    twitch_channels: List[str]
    base_dir: Path
    client_secrets_file: Path
    token_pickle: Path
    uploaded_json: Path
    download_folder: Path
    processed_folder: Path
    
    # Optional
    opus_clip_api_key: Optional[str] = None  # NEW: Opus Clip API key
    use_opus_clip: bool = False  # NEW: Enable/disable Opus Clip
    add_captions: bool = True  # NEW: Add TikTok-style captions
    caption_style: str = "tiktok"  # NEW: Caption style (tiktok, minimal, bold)
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
        
        # Check for Opus Clip API key
        opus_key = os.getenv("OPUS_CLIP_API_KEY")
        use_opus = opus_key is not None and len(opus_key) > 0
        
        if use_opus:
            logger.info("✓ Opus Clip integration ENABLED")
        else:
            logger.info("ℹ️  Opus Clip integration disabled (no API key)")
        
        return cls(
            twitch_client_id=os.getenv("TWITCH_CLIENT_ID"),
            twitch_client_secret=os.getenv("TWITCH_CLIENT_SECRET"),
            groq_api_key=os.getenv("GROQ_API_KEY"),
            opus_clip_api_key=opus_key,
            use_opus_clip=use_opus,
            twitch_channels=channels,
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
        response = requests.post(url, data=data, timeout=10)
        response.raise_for_status()
        self._token = response.json()["access_token"]
        logger.info("✓ Twitch token obtained")
    
    def get_broadcaster_id(self, username: str) -> Optional[str]:
        url = f"https://api.twitch.tv/helix/users?login={username}"
        response = requests.get(url, headers=self.headers, timeout=10)
        response.raise_for_status()
        data = response.json().get("data", [])
        return data[0]["id"] if data else None
    
    def get_top_clip(self, broadcaster_id: str) -> Optional[Dict]:
        """Get the single best clip from last 24 hours"""
        clips = self.get_recent_clips(broadcaster_id, hours_back=24)
        if not clips:
            return None
        clips.sort(key=lambda x: x.get("view_count", 0), reverse=True)
        return clips[0]
    
    def get_recent_clips(self, broadcaster_id: str, hours_back: int = 24, fetch_count: int = 100) -> List[Dict]:
        """Get recent clips from a broadcaster"""
        import datetime
        start_time = (
            datetime.datetime.now(datetime.timezone.utc) - 
            datetime.timedelta(hours=hours_back)
        ).isoformat().split('.')[0] + 'Z'
        
        url = (
            f"https://api.twitch.tv/helix/clips?"
            f"broadcaster_id={broadcaster_id}&"
            f"first={fetch_count}&"
            f"started_at={start_time}"
        )
        
        try:
            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()
            clips = response.json().get("data", [])
            
            if clips:
                logger.info(f"   Fetched {len(clips)} total clips from Twitch")
            
            return clips
        except Exception as e:
            logger.error(f"Error fetching clips: {e}")
            return []

# ==============================================================================
# CAPTION GENERATOR - TIKTOK STYLE
# ==============================================================================

class CaptionGenerator:
    """Creates TikTok-style animated captions with word-level timing"""
    
    def __init__(self, config: Config):
        self.config = config
        self.groq_headers = {"Authorization": f"Bearer {config.groq_api_key}"}
    
    def transcribe_with_timestamps(self, audio_path: Path) -> Dict:
        """Get word-level timestamps from Whisper"""
        try:
            url = "https://api.groq.com/openai/v1/audio/transcriptions"
            
            with open(audio_path, "rb") as f:
                response = requests.post(
                    url,
                    headers=self.groq_headers,
                    files={"file": (audio_path.name, f, "audio/mpeg")},
                    data={
                        "model": self.config.groq_transcription_model,
                        "response_format": "verbose_json",  # Get timestamps
                        "timestamp_granularities": ["word"]
                    },
                    timeout=self.config.api_timeout
                )
            
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Timestamp transcription failed: {e}")
            return {}
    
    def create_subtitle_file(self, transcript_data: Dict, output_path: Path) -> bool:
        """Create ASS subtitle file with TikTok-style formatting"""
        try:
            words = transcript_data.get("words", [])
            
            if not words:
                logger.warning("No word timestamps available")
                return False
            
            # ASS subtitle format with TikTok styling
            ass_content = """[Script Info]
Title: TikTok Style Captions
ScriptType: v4.00+
WrapStyle: 0
PlayResX: 1080
PlayResY: 1920

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial,70,&H00FFFFFF,&H000000FF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,3,2,2,30,30,250,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
            
            # Group words into chunks of 3-5 words for readability
            chunk_size = 4
            for i in range(0, len(words), chunk_size):
                chunk = words[i:i+chunk_size]
                
                start_time = chunk[0]["start"]
                end_time = chunk[-1]["end"]
                
                text = " ".join([w["word"] for w in chunk])
                
                # Convert seconds to ASS format (0:00:00.00)
                start_ass = self._seconds_to_ass(start_time)
                end_ass = self._seconds_to_ass(end_time)
                
                # Make text uppercase and bold for TikTok style
                text_upper = text.upper()
                
                ass_content += f"Dialogue: 0,{start_ass},{end_ass},Default,,0,0,0,,{text_upper}\n"
            
            # Write to file
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(ass_content)
            
            logger.info(f"   ✓ Created subtitle file with {len(words)} words")
            return True
            
        except Exception as e:
            logger.error(f"Subtitle creation failed: {e}")
            return False
    
    def _seconds_to_ass(self, seconds: float) -> str:
        """Convert seconds to ASS timestamp format"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = seconds % 60
        return f"{hours}:{minutes:02d}:{secs:05.2f}"

# ==============================================================================
# OPUS CLIP CLIENT
# ==============================================================================

class OpusClipClient:
    """Handles Opus Clip AI video editing"""
    
    def __init__(self, config: Config):
        self.config = config
        self.api_key = config.opus_clip_api_key
        self.base_url = "https://api.opus.pro/api/v1"
    
    def upload_and_process(self, video_path: Path, title: str) -> Optional[Dict]:
        """
        Upload video to Opus Clip and get AI-generated best clips
        Returns: Dict with clip data or None if failed
        """
        try:
            logger.info("   🎬 Uploading to Opus Clip for AI editing...")
            
            # Step 1: Upload video
            upload_url = f"{self.base_url}/upload"
            
            with open(video_path, 'rb') as f:
                files = {'file': (video_path.name, f, 'video/mp4')}
                headers = {'Authorization': f'Bearer {self.api_key}'}
                
                response = requests.post(
                    upload_url,
                    files=files,
                    headers=headers,
                    timeout=120  # 2 minute timeout for upload
                )
            
            if response.status_code != 200:
                logger.error(f"   ✗ Opus Clip upload failed: {response.text}")
                return None
            
            upload_data = response.json()
            video_id = upload_data.get('id')
            
            if not video_id:
                logger.error("   ✗ No video ID returned from Opus Clip")
                return None
            
            logger.info(f"   ✓ Uploaded to Opus Clip (ID: {video_id})")
            
            # Step 2: Start AI processing
            logger.info("   🤖 Starting Opus Clip AI processing...")
            
            process_url = f"{self.base_url}/process"
            process_data = {
                'video_id': video_id,
                'title': title,
                'clip_length': 'auto',  # Let AI decide
                'aspect_ratio': '9:16',  # Vertical for TikTok/Shorts
                'auto_captions': True,
                'auto_reframe': True
            }
            
            response = requests.post(
                process_url,
                json=process_data,
                headers=headers,
                timeout=30
            )
            
            if response.status_code != 200:
                logger.error(f"   ✗ Opus Clip processing failed: {response.text}")
                return None
            
            job_data = response.json()
            job_id = job_data.get('job_id')
            
            logger.info(f"   ⏳ Processing... (Job ID: {job_id})")
            
            # Step 3: Wait for processing to complete
            max_wait = 300  # 5 minutes max
            check_interval = 10  # Check every 10 seconds
            elapsed = 0
            
            status_url = f"{self.base_url}/job/{job_id}"
            
            while elapsed < max_wait:
                time.sleep(check_interval)
                elapsed += check_interval
                
                response = requests.get(status_url, headers=headers, timeout=10)
                
                if response.status_code != 200:
                    logger.warning(f"   ⚠️  Status check failed")
                    continue
                
                status_data = response.json()
                status = status_data.get('status')
                
                if status == 'completed':
                    logger.info(f"   ✓ Opus Clip processing complete!")
                    return status_data
                elif status == 'failed':
                    logger.error(f"   ✗ Opus Clip processing failed")
                    return None
                else:
                    logger.info(f"   ⏳ Still processing... ({elapsed}s)")
            
            logger.error(f"   ✗ Opus Clip processing timeout")
            return None
            
        except Exception as e:
            logger.error(f"   ✗ Opus Clip error: {e}")
            return None
    
    def download_clip(self, opus_data: Dict, output_path: Path) -> bool:
        """Download the best clip from Opus Clip results"""
        try:
            clips = opus_data.get('clips', [])
            
            if not clips:
                logger.warning("   ⚠️  No clips generated by Opus Clip")
                return False
            
            # Get the best clip (Opus Clip ranks them)
            best_clip = clips[0]
            download_url = best_clip.get('download_url')
            
            if not download_url:
                logger.error("   ✗ No download URL in Opus Clip result")
                return False
            
            logger.info(f"   📥 Downloading best clip from Opus Clip...")
            
            response = requests.get(download_url, stream=True, timeout=120)
            response.raise_for_status()
            
            with open(output_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            if output_path.exists():
                logger.info(f"   ✓ Downloaded Opus Clip result: {output_path.name}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"   ✗ Download failed: {e}")
            return False

# ==============================================================================
# GROQ CLIENT
# ==============================================================================

class GroqClient:
    def __init__(self, config: Config):
        self.config = config
        self.headers = {"Authorization": f"Bearer {config.groq_api_key}"}
    
    def transcribe_audio(self, file_path: Path) -> str:
        try:
            url = "https://api.groq.com/openai/v1/audio/transcriptions"
            with open(file_path, "rb") as f:
                response = requests.post(
                    url,
                    headers=self.headers,
                    files={"file": (file_path.name, f, "audio/mpeg")},
                    data={"model": self.config.groq_transcription_model},
                    timeout=self.config.api_timeout
                )
            response.raise_for_status()
            return response.json().get("text", "")
        except Exception as e:
            logger.error(f"Transcription failed: {e}")
            return ""
    
    def analyze_clip(self, transcript: str, title: str, view_count: int) -> Dict:
        try:
            url = "https://api.groq.com/openai/v1/chat/completions"
            
            prompt = f"""Analyze this gaming clip for TikTok/YouTube Shorts viral potential.

Title: {title}
Views: {view_count}
Transcript: {transcript}

Rate 0.0-1.0 based on: hype moments, skill plays, humor, shock value, relatability.

Create viral metadata:
- Title: Engaging, emojis, curiosity gap (max 100 chars)
- Description: 2-3 sentences with hashtags

Return ONLY JSON:
{{
  "score": 0.0,
  "title": "Title 🔥",
  "description": "Description #hashtags"
}}"""
            
            data = {
                "model": self.config.groq_chat_model,
                "messages": [{"role": "user", "content": prompt}],
                "response_format": {"type": "json_object"},
                "temperature": 0.8
            }
            
            response = requests.post(
                url,
                headers={**self.headers, "Content-Type": "application/json"},
                json=data,
                timeout=self.config.api_timeout
            )
            response.raise_for_status()
            
            content = response.json()["choices"][0]["message"]["content"]
            metadata = json.loads(content)
            
            metadata["score"] = float(metadata.get("score", 0.0))
            metadata["title"] = str(metadata.get("title", title))[:100]
            metadata["description"] = str(metadata.get("description", ""))
            
            return metadata
            
        except Exception as e:
            logger.error(f"AI analysis failed: {e}")
            return {"score": 0.0, "title": title, "description": f"{title} #gaming"}

# ==============================================================================
# VIDEO PROCESSOR - USING FFMPEG DIRECTLY
# ==============================================================================

class VideoProcessor:
    def __init__(self, config: Config):
        self.config = config
        self.opus_clip = OpusClipClient(config) if config.use_opus_clip else None
        self.caption_gen = CaptionGenerator(config)
    
    def download_clip(self, clip_url: str, clip_id: str) -> Optional[Path]:
        try:
            output_path = self.config.download_folder / f"{clip_id}.mp4"
            
            ydl_opts = {
                'outtmpl': str(output_path),
                'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
                'quiet': True,
                'no_warnings': True,
                'merge_output_format': 'mp4'
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([clip_url])
            
            if output_path.exists():
                logger.info(f"✓ Downloaded: {output_path.name}")
                return output_path
            return None
        except Exception as e:
            logger.error(f"Download failed: {e}")
            return None
    
    def create_tiktok_style_video(
        self, 
        source_path: Path, 
        clip_id: str, 
        title: str = "",
        description: str = ""
    ) -> Optional[Path]:
        """
        Create TikTok-style vertical video with captions and description overlay.
        
        Features:
        1. Opus Clip AI editing (if enabled)
        2. Vertical format with blurred background
        3. Auto-captions from speech (TikTok style)
        4. Description overlay at top (white bg, black text)
        """
        try:
            # === STEP 1: OPUS CLIP AI PROCESSING (if enabled) ===
            if self.config.use_opus_clip and self.opus_clip:
                logger.info("🤖 Using Opus Clip AI to find the best moments...")
                
                opus_result = self.opus_clip.upload_and_process(source_path, title)
                
                if opus_result:
                    opus_output = self.config.processed_folder / f"{clip_id}_opus.mp4"
                    
                    if self.opus_clip.download_clip(opus_result, opus_output):
                        logger.info("   ✓ Opus Clip AI editing complete!")
                        source_for_formatting = opus_output
                    else:
                        logger.warning("   ⚠️  Opus Clip download failed, using original")
                        source_for_formatting = source_path
                else:
                    logger.warning("   ⚠️  Opus Clip processing failed, using original")
                    source_for_formatting = source_path
            else:
                source_for_formatting = source_path
            
            # === STEP 2: GENERATE CAPTIONS ===
            subtitle_file = None
            if self.config.add_captions:
                logger.info("📝 Generating auto-captions...")
                
                transcript_data = self.caption_gen.transcribe_with_timestamps(source_for_formatting)
                
                if transcript_data:
                    subtitle_file = self.config.processed_folder / f"{clip_id}_subs.ass"
                    self.caption_gen.create_subtitle_file(transcript_data, subtitle_file)
            
            # === STEP 3: CREATE VERTICAL VIDEO WITH CAPTIONS ===
            logger.info("🎨 Creating TikTok-style video...")
            
            output_path = self.config.processed_folder / f"{clip_id}_tiktok.mp4"
            
            # Get video info
            video = VideoFileClip(str(source_for_formatting))
            duration = min(video.duration, self.config.target_duration)
            width = video.w
            height = video.h
            video.close()
            
            logger.info(f"   Video: {width}x{height} @ {duration:.1f}s")
            
            # Use title if no description
            overlay_text = description if description else title
            
            # Build FFmpeg filter complex
            filter_complex = (
                # Split input into background and main
                '[0:v]split=2[blur][main];'
                # Blurred background
                '[blur]scale=1080:1920:force_original_aspect_ratio=increase,'
                'crop=1080:1920,'
                'boxblur=20:5,'
                'eq=brightness=-0.3[bg];'
                # Main video centered
                '[main]scale=1080:1920:force_original_aspect_ratio=decrease,'
                'pad=1080:1920:(ow-iw)/2:(oh-ih)/2:black@0[fg];'
                # Overlay main on background
                '[bg][fg]overlay[video_base]'
            )
            
            # Add title overlay at top - TikTok speech bubble style
            if overlay_text:
                # Clean text
                clean_text = overlay_text.replace("'", "").replace('"', '').replace('\\', '').replace(':', '').replace('[', '').replace(']', '').replace(',', '').upper()[:60]
                
                # Detect font path
                if sys.platform == "win32":
                    font_path = "C\\\\:/Windows/Fonts/arialbd.ttf"
                else:
                    font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
                
                # Create clean white rounded box with text (TikTok style)
                filter_complex += (
                    # Add white rounded rectangle background
                    f';[video_base]drawbox=y=80:color=white@1.0:width=950:height=140:t=fill:x=(iw-950)/2,'
                    # Add black text on top
                    f"drawtext=text='{clean_text}':"
                    f"fontfile={font_path}:"
                    "fontsize=42:"
                    "fontcolor=black:"
                    "x=(w-text_w)/2:"
                    "y=120[video_with_title]"
                )
                video_output = 'video_with_title'
            else:
                video_output = 'video_base'
            
            # Add captions/subtitles if available
            if subtitle_file and subtitle_file.exists():
                filter_complex += f';[{video_output}]subtitles={str(subtitle_file).replace("\\", "/")}[video_final]'
                final_output = 'video_final'
                logger.info("   ✓ Adding auto-captions")
            else:
                final_output = video_output
            
            # Build FFmpeg command
            ffmpeg_cmd = [
                'ffmpeg',
                '-i', str(source_for_formatting),
                '-t', str(duration),
                '-filter_complex', filter_complex,
                '-map', f'[{final_output}]',
                '-map', '0:a',
                '-c:v', 'libx264',
                '-preset', 'medium',
                '-crf', '18',
                '-pix_fmt', 'yuv420p',
                '-c:a', 'aac',
                '-b:a', '192k',
                '-y',
                str(output_path)
            ]
            
            logger.info(f"   🎬 Rendering with captions & title overlay...")
            
            result = subprocess.run(
                ffmpeg_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            if result.returncode != 0:
                logger.error(f"FFmpeg error: {result.stderr}")
                
                # Fallback: Try without captions
                logger.info("   Retrying without captions...")
                return self._create_simple_vertical(source_for_formatting, clip_id, duration)
            
            # Cleanup temp files
            if self.config.use_opus_clip and source_for_formatting != source_path:
                try:
                    source_for_formatting.unlink()
                except:
                    pass
            
            if subtitle_file and subtitle_file.exists():
                try:
                    subtitle_file.unlink()
                except:
                    pass
            
            if output_path.exists():
                logger.info(f"   ✅ Complete: {output_path.name}")
                return output_path
            else:
                logger.error("   Output file not created")
                return None
            
        except Exception as e:
            logger.error(f"Video processing failed: {e}", exc_info=True)
            return None
    
    def _create_simple_vertical(self, source_path: Path, clip_id: str, duration: float) -> Optional[Path]:
        """Fallback: Create simple vertical video without captions"""
        try:
            output_path = self.config.processed_folder / f"{clip_id}_tiktok.mp4"
            
            ffmpeg_cmd = [
                'ffmpeg',
                '-i', str(source_path),
                '-t', str(duration),
                '-filter_complex',
                '[0:v]split=2[blur][main];'
                '[blur]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,boxblur=20:5,eq=brightness=-0.3[bg];'
                '[main]scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2:black@0[fg];'
                '[bg][fg]overlay',
                '-c:v', 'libx264',
                '-preset', 'medium',
                '-crf', '18',
                '-pix_fmt', 'yuv420p',
                '-c:a', 'aac',
                '-b:a', '192k',
                '-y',
                str(output_path)
            ]
            
            result = subprocess.run(ffmpeg_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            
            if result.returncode == 0 and output_path.exists():
                return output_path
            return None
            
        except Exception as e:
            logger.error(f"Fallback processing failed: {e}")
            return None

# ==============================================================================
# YOUTUBE UPLOADER
# ==============================================================================

class YouTubeUploader:
    SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
    
    def __init__(self, config: Config):
        self.config = config
        self._service = None
    
    @property
    def service(self):
        if not self._service:
            self._service = self._authenticate()
        return self._service
    
    def _authenticate(self):
        creds = None
        
        if self.config.token_pickle.exists():
            with open(self.config.token_pickle, "rb") as token:
                creds = pickle.load(token)
        
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
            with open(self.config.token_pickle, "wb") as token:
                pickle.dump(creds, token)
        
        if not creds or not creds.valid:
            if not self.config.client_secrets_file.exists():
                raise FileNotFoundError(f"YouTube client_secrets.json not found at {self.config.client_secrets_file}")
            
            flow = InstalledAppFlow.from_client_secrets_file(
                str(self.config.client_secrets_file),
                self.SCOPES
            )
            creds = flow.run_local_server(port=0)
            
            with open(self.config.token_pickle, "wb") as token:
                pickle.dump(creds, token)
        
        logger.info("✓ YouTube authenticated")
        return build("youtube", "v3", credentials=creds)
    
    def upload(self, file_path: Path, title: str, description: str) -> Optional[str]:
        try:
            body = {
                "snippet": {
                    "title": title[:100],
                    "description": description[:5000],
                    "categoryId": self.config.youtube_category,
                    "tags": ["gaming", "twitch", "shorts", "viral"]
                },
                "status": {
                    "privacyStatus": self.config.youtube_privacy,
                    "selfDeclaredMadeForKids": False
                }
            }
            
            media = MediaFileUpload(str(file_path), mimetype="video/mp4", resumable=True, chunksize=1024*1024)
            request = self.service.videos().insert(part="snippet,status", body=body, media_body=media)
            
            response = None
            while response is None:
                status, response = request.next_chunk()
                if status:
                    logger.info(f"      Upload: {int(status.progress() * 100)}%")
            
            video_id = response.get("id")
            logger.info(f"      ✓ YouTube: https://youtube.com/shorts/{video_id}")
            return video_id
            
        except Exception as e:
            logger.error(f"YouTube upload failed: {e}")
            return None

# ==============================================================================
# TIKTOK UPLOADER
# ==============================================================================

class TikTokUploader:
    def __init__(self, config: Config):
        self.config = config
        self.cookies_file = config.base_dir / "tiktok.com_cookies.txt"
    
    def upload(self, file_path: Path, title: str, description: str) -> bool:
        try:
            if not self.cookies_file.exists():
                logger.warning(f"⚠️  TikTok cookies not found, skipping TikTok upload")
                return False
            
            try:
                from tiktok_uploader.upload import upload_video
            except ImportError:
                logger.error("tiktok-uploader not installed. Run: pip install tiktok-uploader")
                return False
            
            caption = f"{title}\n\n{description}"[:150]
            
            upload_video(
                str(file_path),
                description=caption,
                cookies=str(self.cookies_file)
            )
            
            logger.info(f"      ✓ TikTok upload complete")
            return True
            
        except Exception as e:
            logger.error(f"TikTok upload failed: {e}")
            return False

# ==============================================================================
# STATE MANAGER
# ==============================================================================

class StateManager:
    def __init__(self, config: Config):
        self.config = config
        self._processed: Set[str] = set()
        self._load()
    
    def _load(self):
        """Load processed clip IDs from disk"""
        if self.config.uploaded_json.exists():
            try:
                with open(self.config.uploaded_json, "r") as f:
                    self._processed = set(json.load(f))
                logger.info(f"📚 Loaded {len(self._processed)} processed clips from history")
            except Exception as e:
                logger.error(f"Failed to load history: {e}")
                self._processed = set()
        else:
            logger.info("📚 No history file found - starting fresh")
            self._processed = set()
    
    def _save(self):
        try:
            with open(self.config.uploaded_json, "w") as f:
                json.dump(list(self._processed), f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save state: {e}")
    
    def is_processed(self, clip_id: str) -> bool:
        return clip_id in self._processed
    
    def mark_processed(self, clip_id: str):
        self._processed.add(clip_id)
        self._save()

# ==============================================================================
# MAIN BOT
# ==============================================================================

class ClipBot:
    def __init__(self):
        self.config = Config.from_env()
        self._setup()
        
        self.twitch = TwitchClient(self.config)
        self.groq = GroqClient(self.config)
        self.video = VideoProcessor(self.config)
        self.youtube = YouTubeUploader(self.config)
        self.tiktok = TikTokUploader(self.config)
        self.state = StateManager(self.config)
    
    def _setup(self):
        self.config.download_folder.mkdir(exist_ok=True)
        self.config.processed_folder.mkdir(exist_ok=True)
    
    def run(self):
        """Process up to 5 clips per channel"""
        logger.info("\n" + "="*80)
        logger.info("🚀 TWITCH CLIP BOT - MULTI-CLIP MODE")
        logger.info("="*80)
        logger.info(f"Channels: {', '.join(self.config.twitch_channels)}")
        logger.info(f"Clips per channel: Up to 5")
        logger.info(f"Viral threshold: {self.config.viral_threshold:.0%}")
        logger.info("="*80 + "\n")
        
        try:
            total_processed = 0
            
            # Process each channel
            for channel in self.config.twitch_channels:
                logger.info(f"\n{'🔥'*40}")
                logger.info(f"📺 CHANNEL: {channel.upper()}")
                logger.info(f"{'🔥'*40}\n")
                
                clips = self._find_unprocessed_clips(channel, limit=5)
                
                if not clips:
                    logger.info(f"   ⏭️  Skipping {channel}, no new clips to process\n")
                    continue
                
                # Process each clip one by one
                for idx, clip in enumerate(clips, 1):
                    logger.info(f"\n{'─'*80}")
                    logger.info(f"📌 CLIP {idx}/{len(clips)} from {channel}")
                    logger.info(f"{'─'*80}\n")
                    
                    self._process_clip(clip)
                    total_processed += 1
                    
                    # Small pause between clips
                    time.sleep(1)
            
            logger.info(f"\n{'='*80}")
            if total_processed > 0:
                logger.info(f"✅ COMPLETED! Processed {total_processed} total clips")
            else:
                logger.info(f"ℹ️  NO NEW CLIPS - All clips in all channels already processed")
            logger.info(f"{'='*80}\n")
            
        except KeyboardInterrupt:
            logger.info("\n⚠️  Stopped by user")
        except Exception as e:
            logger.error(f"\n💥 Fatal error: {e}", exc_info=True)
    
    def _find_unprocessed_clips(self, channel: str, limit: int = 5) -> List[Dict]:
        """Find up to 'limit' unprocessed clips from a channel, sorted by views"""
        logger.info(f"📺 Scanning: {channel}")
        
        broadcaster_id = self.twitch.get_broadcaster_id(channel)
        if not broadcaster_id:
            logger.warning(f"   ❌ Channel not found")
            return []
        
        logger.info(f"   ✓ Broadcaster ID: {broadcaster_id}")
        
        # Get clips using TwitchClient method (fetch 100 to ensure we get enough unprocessed)
        logger.info(f"   🔍 Fetching clips from Twitch API (last 72 hours)...")
        all_clips = self.twitch.get_recent_clips(broadcaster_id, hours_back=72, fetch_count=100)
        
        if not all_clips:
            logger.warning(f"   ❌ Twitch returned ZERO clips")
            logger.info(f"      Possible reasons:")
            logger.info(f"      - No clips created in last 72 hours")
            logger.info(f"      - Streamer hasn't been live")
            logger.info(f"      - API issue (check broadcaster_id is correct)")
            return []
        
        logger.info(f"   ✓ Twitch returned {len(all_clips)} clips!")
        
        # Show some clip details
        logger.info(f"\n   📋 Sample of clips from Twitch:")
        for i, clip in enumerate(all_clips[:5]):  # Show first 5
            logger.info(f"      {i+1}. \"{clip['title']}\" - {clip['view_count']:,} views - ID: {clip['id'][:30]}...")
        
        if len(all_clips) > 5:
            logger.info(f"      ... and {len(all_clips) - 5} more")
        
        # Check against processed history
        logger.info(f"\n   🔍 Checking against history ({len(self.state._processed)} processed clips)...")
        
        processed_clips = []
        unprocessed = []
        
        for clip in all_clips:
            clip_id = clip["id"]
            if self.state.is_processed(clip_id):
                processed_clips.append(clip)
                logger.debug(f"      ✓ Already processed: {clip['title'][:40]}")
            else:
                unprocessed.append(clip)
                logger.debug(f"      🆕 NEW: {clip['title'][:40]}")
        
        # Show detailed stats
        logger.info(f"\n   📊 Results:")
        logger.info(f"      • Total from Twitch: {len(all_clips)}")
        logger.info(f"      • Already processed: {len(processed_clips)}")
        logger.info(f"      • NEW/Unprocessed: {len(unprocessed)}")
        
        if not unprocessed:
            logger.warning(f"\n   ⚠️  ALL {len(all_clips)} clips are already processed!")
            logger.info(f"      To process them again, run: python {sys.argv[0]} --clear-history")
            return []
        
        # Sort by view count (highest first)
        unprocessed.sort(key=lambda x: x.get("view_count", 0), reverse=True)
        
        # Take top 'limit' clips
        top_clips = unprocessed[:limit]
        
        logger.info(f"\n   🎯 Will process these {len(top_clips)} clips:")
        for idx, clip in enumerate(top_clips, 1):
            title = clip['title'][:45] + "..." if len(clip['title']) > 45 else clip['title']
            logger.info(f"      {idx}. \"{title}\" - {clip['view_count']:,} views")
        
        logger.info("")  # Empty line for spacing
        return top_clips
    
    def _process_clip(self, clip: Dict):
        clip_id = clip["id"]
        clip_title = clip["title"]
        clip_url = clip["url"]
        clip_description = clip.get("description", "")  # Get Twitch description
        view_count = clip.get("view_count", 0)
        
        logger.info(f"\n{'='*80}")
        logger.info(f"🎬 PROCESSING CLIP")
        logger.info(f"{'='*80}")
        logger.info(f"Title: {clip_title}")
        logger.info(f"Views: {view_count:,}")
        logger.info(f"ID: {clip_id}")
        logger.info(f"{'='*80}\n")
        
        download_path = None
        processed_path = None
        
        try:
            logger.info("[1/5] 📥 Downloading...")
            download_path = self.video.download_clip(clip_url, clip_id)
            if not download_path:
                logger.error("   Download failed")
                return
            
            logger.info("\n[2/5] 🎤 Transcribing audio...")
            transcript = self.groq.transcribe_audio(download_path)
            if transcript:
                logger.info(f"   ✓ Transcribed {len(transcript)} characters")
            
            logger.info("\n[3/5] 🤖 AI Analysis...")
            metadata = self.groq.analyze_clip(transcript, clip_title, view_count)
            logger.info(f"   Viral Score: {metadata['score']:.1%}")
            
            if metadata['score'] < self.config.viral_threshold:
                logger.info(f"   ⏭️  Below threshold ({self.config.viral_threshold:.0%}), skipping")
                self.state.mark_processed(clip_id)
                self._cleanup(download_path)
                return
            
            logger.info("\n[4/5] 🎨 Creating TikTok-style video...")
            processed_path = self.video.create_tiktok_style_video(
                download_path, 
                clip_id, 
                clip_title,
                clip_description
            )
            
            if not processed_path:
                logger.error("   Video processing failed")
                return
            
            logger.info("\n[5/5] 👁️  REVIEW REQUIRED")
            self._show_review(clip, metadata, processed_path)
            
            decision = self._get_decision()
            
            if decision == 'quit':
                logger.info("\n👋 Quitting")
                sys.exit(0)
            
            elif decision == 'skip':
                logger.info("\n⏭️  Skipped by user")
                self.state.mark_processed(clip_id)
                self._cleanup(download_path, processed_path)
            
            elif decision == 'upload':
                logger.info("\n📤 UPLOADING...")
                
                logger.info("\n   📺 YouTube Shorts:")
                yt_id = self.youtube.upload(processed_path, metadata['title'], metadata['description'])
                
                logger.info("\n   📱 TikTok:")
                tt_success = self.tiktok.upload(processed_path, metadata['title'], metadata['description'])
                
                self.state.mark_processed(clip_id)
                
                if yt_id or tt_success:
                    logger.info("\n✅ UPLOAD COMPLETE!")
                    self._cleanup(download_path)
                else:
                    logger.error("\n❌ All uploads failed")
                    self._cleanup(download_path, processed_path)
        
        except Exception as e:
            logger.error(f"\n💥 Error: {e}", exc_info=True)
            self._cleanup(download_path, processed_path)
    
    def _show_review(self, clip: Dict, metadata: Dict, video_path: Path):
        print("\n" + "="*80)
        print("📋 CLIP REVIEW")
        print("="*80)
        print(f"\n📊 CLIP INFO:")
        print(f"   Title: {clip['title']}")
        print(f"   Creator: {clip['creator_name']}")
        print(f"   Views: {clip['view_count']:,}")
        print(f"   Duration: {clip['duration']:.1f}s")
        
        print(f"\n🤖 AI ANALYSIS:")
        print(f"   Viral Score: {metadata['score']:.1%}")
        
        print(f"\n✨ OPTIMIZED FOR UPLOAD:")
        print(f"   Title: {metadata['title']}")
        print(f"   Description: {metadata['description']}")
        
        print(f"\n📁 VIDEO FILE:")
        print(f"   {video_path}")
        print(f"   Size: {video_path.stat().st_size / 1024 / 1024:.1f}MB")
        print(f"   Format: 1080x1920 (9:16) with blurred background")
        
        print("\n" + "="*80)
    
    def _get_decision(self) -> str:
        while True:
            print("\n🎯 YOUR DECISION:")
            print("   [Y] Upload to YouTube & TikTok")
            print("   [N] Skip this clip")
            print("   [Q] Quit")
            
            choice = input("\n👉 Choice: ").strip().upper()
            
            if choice == 'Y':
                return 'upload'
            elif choice == 'N':
                return 'skip'
            elif choice == 'Q':
                return 'quit'
            else:
                print("❌ Invalid. Enter Y, N, or Q.")
    
    def _cleanup(self, *paths):
        for path in paths:
            if path and path.exists():
                try:
                    path.unlink()
                except Exception as e:
                    logger.warning(f"Could not delete {path}: {e}")

# ==============================================================================
# ENTRY POINT
# ==============================================================================

def main():
    try:
        # Check for command line arguments
        if len(sys.argv) > 1:
            if sys.argv[1] == '--clear-history':
                config = Config.from_env()
                if config.uploaded_json.exists():
                    with open(config.uploaded_json, "r") as f:
                        old_count = len(json.load(f))
                    config.uploaded_json.unlink()
                    logger.info(f"✅ Cleared {old_count} clips from history")
                else:
                    logger.info("ℹ️  No history file to clear")
                return
            elif sys.argv[1] == '--stats':
                config = Config.from_env()
                if config.uploaded_json.exists():
                    with open(config.uploaded_json, "r") as f:
                        processed = json.load(f)
                    logger.info(f"\n📊 HISTORY STATS:")
                    logger.info(f"   Total processed clips: {len(processed)}")
                    logger.info(f"   History file: {config.uploaded_json}")
                else:
                    logger.info("ℹ️  No history file found")
                return
            elif sys.argv[1] == '--help':
                print("\n🤖 TWITCH CLIP BOT - Usage:")
                print("\n   python script.py                 Run the bot")
                print("   python script.py --clear-history  Clear all processed clips history")
                print("   python script.py --stats          Show history statistics")
                print("   python script.py --help           Show this help\n")
                return
        
        bot = ClipBot()
        bot.run()
    except Exception as e:
        logger.error(f"💥 Fatal: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()