import sys
from pathlib import Path
from typing import Dict, List, Optional, Any, Set
import asyncio
import logging
from fastapi import WebSocket

sys.path.insert(0, str(Path(__file__).parent.parent.parent))


class ConnectionManager:
    _instance: Optional["ConnectionManager"] = None

    def __init__(self):
        self.active_connections: Set[WebSocket] = set()

    @classmethod
    def get_instance(cls) -> "ConnectionManager":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.add(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.discard(websocket)

    async def broadcast(self, message: dict):
        disconnected = set()
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                disconnected.add(connection)
        for conn in disconnected:
            self.active_connections.discard(conn)


from core import (
    Config,
    TwitchClient,
    StateManager as CoreStateManager,
    GroqClient,
    VideoProcessor,
    YouTubeUploader,
    TikTokUploader,
)

logger = logging.getLogger(__name__)


class AppState:
    _instance: Optional["AppState"] = None
    _lock = asyncio.Lock()

    def __init__(self):
        self.config: Config = Config.from_env()
        self.twitch_client: TwitchClient = TwitchClient(self.config)
        self.core_state_manager: CoreStateManager = CoreStateManager(self.config)
        self.groq_client: GroqClient = GroqClient(self.config)
        self.video_processor: VideoProcessor = VideoProcessor(self.config)
        self.youtube: YouTubeUploader = YouTubeUploader(self.config)
        self.tiktok: TikTokUploader = TikTokUploader(self.config)

        self.ws_manager: ConnectionManager = ConnectionManager.get_instance()

        self.category_queues: Dict[str, List[Dict[str, Any]]] = {}
        self.clip_metadata_store: Dict[str, Dict[str, Any]] = {}
        self.clip_scores: Dict[str, int] = {}
        self.clip_comments: Dict[str, List[Dict[str, str]]] = {}
        self.admin_upload_queue: Dict[str, Dict[str, Any]] = {}

        self.bot_initialized = True

    @classmethod
    async def get_instance(cls) -> "AppState":
        if cls._instance is None:
            async with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def _fetch_clips_for_category(self, category_name: str) -> List[Dict[str, Any]]:
        if not self.bot_initialized:
            return []

        if category_name == "My Streamers":
            clips_by_channel: Dict[str, List[Dict[str, Any]]] = {}
            for channel in self.config.twitch_channels:
                broadcaster_id = self.twitch_client.get_broadcaster_id(channel)
                if broadcaster_id:
                    all_clips = self.twitch_client.get_recent_clips(
                        broadcaster_id, hours_back=72, fetch_count=100
                    )
                    channel_clips: List[Dict[str, Any]] = []
                    for clip in all_clips:
                        clip_data: Dict[str, Any] = {
                            "id": clip["id"],
                            "title": clip["title"],
                            "url": clip["url"],
                            "thumbnail_url": clip["thumbnail_url"],
                            "view_count": clip["view_count"],
                            "creator_name": clip["creator_name"],
                            "duration": clip["duration"],
                            "created_at": clip["created_at"],
                            "channel": channel,
                        }
                        self.clip_metadata_store[clip["id"]] = clip_data
                        if (
                            not self.core_state_manager.is_processed(clip["id"])
                            and clip["id"] not in self.admin_upload_queue
                            and clip["id"] not in self.clip_scores
                        ):
                            channel_clips.append(clip_data)
                    channel_clips.sort(key=lambda x: x["view_count"], reverse=True)
                    clips_by_channel[channel] = channel_clips

            max_per_channel = 10
            final_queue: List[Dict[str, Any]] = []
            channel_queues = {
                ch: clips[:max_per_channel] for ch, clips in clips_by_channel.items()
            }
            while any(channel_queues.values()):
                for channel in self.config.twitch_channels:
                    if channel in channel_queues and channel_queues[channel]:
                        final_queue.append(channel_queues[channel].pop(0))
            return final_queue

        else:
            if not hasattr(self.twitch_client, "get_game_id"):
                logger.warning(
                    f"get_game_id not in core.py yet. Unable to fetch {category_name}"
                )
                return []

            game_id = self.twitch_client.get_game_id(category_name)
            if not game_id:
                return []

            all_clips = self.twitch_client.get_recent_clips_by_game(
                game_id, hours_back=48, fetch_count=100
            )

            valid_clips: List[Dict[str, Any]] = []
            for clip in all_clips:
                clip_data: Dict[str, Any] = {
                    "id": clip["id"],
                    "title": clip["title"],
                    "url": clip["url"],
                    "thumbnail_url": clip["thumbnail_url"],
                    "view_count": clip["view_count"],
                    "creator_name": clip["creator_name"],
                    "duration": clip["duration"],
                    "created_at": clip["created_at"],
                    "channel": clip.get("broadcaster_name", category_name),
                }
                self.clip_metadata_store[clip["id"]] = clip_data
                if (
                    not self.core_state_manager.is_processed(clip["id"])
                    and clip["id"] not in self.admin_upload_queue
                    and clip["id"] not in self.clip_scores
                ):
                    valid_clips.append(clip_data)

            valid_clips.sort(key=lambda x: x["view_count"], reverse=True)
            return valid_clips[:30]

    async def fetch_clips(self, category: str = "My Streamers") -> List[Dict[str, Any]]:
        if category not in self.category_queues or not self.category_queues[category]:
            self.category_queues[category] = self._fetch_clips_for_category(category)

        queue = self.category_queues[category]

        for clip in queue:
            clip["local_likes"] = self.clip_scores.get(clip["id"], 0)
            clip["comment_count"] = len(self.clip_comments.get(clip["id"], []))

        return queue

    async def get_clip(self, clip_id: str) -> Optional[Dict[str, Any]]:
        clip = self.clip_metadata_store.get(clip_id)
        if clip:
            clip["local_likes"] = self.clip_scores.get(clip_id, 0)
            clip["comment_count"] = len(self.clip_comments.get(clip_id, []))
        return clip

    async def get_video_url(self, clip_id: str) -> Dict[str, Any]:
        clip = self.clip_metadata_store.get(clip_id)
        if not clip:
            return {"error": "Clip not found"}

        try:
            import yt_dlp

            ydl_opts: Dict[str, Any] = {
                "format": "best[ext=mp4]/best",
                "quiet": True,
                "no_warnings": True,
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(clip["url"], download=False)

                video_url = info.get("url") if info else None

                if not video_url and info:
                    entries = info.get("entries")
                    if entries:
                        for entry in entries:
                            if entry and "url" in entry:
                                video_url = entry["url"]
                                break

                if video_url:
                    return {
                        "video_url": video_url,
                        "title": clip["title"],
                    }

                return {"error": "No video URL found"}
        except Exception as e:
            return {"error": str(e)}

    async def action_clip(self, clip_id: str, action: str) -> Dict[str, Any]:
        if action == "like":
            self.clip_scores[clip_id] = self.clip_scores.get(clip_id, 0) + 1

            leaderboard = await self.get_leaderboard()
            await self.ws_manager.broadcast(
                {"type": "leaderboard_update", "data": leaderboard[:10]}
            )

        for cat in self.category_queues:
            self.category_queues[cat] = [
                c for c in self.category_queues[cat] if c["id"] != clip_id
            ]

        return {
            "status": "voted",
            "current_score": self.clip_scores.get(clip_id, 0),
        }

    async def get_comments(self, clip_id: str) -> List[Dict[str, str]]:
        return self.clip_comments.get(clip_id, [])

    async def add_comment(self, clip_id: str, text: str) -> Dict[str, Any]:
        if clip_id not in self.clip_comments:
            self.clip_comments[clip_id] = []

        new_comment: Dict[str, str] = {
            "user": "AnonymousGamer",
            "text": text,
            "timestamp": str(asyncio.get_event_loop().time()),
        }
        self.clip_comments[clip_id].append(new_comment)
        return {"status": "success", "comment": new_comment}

    async def get_leaderboard(self) -> List[Dict[str, Any]]:
        ranked_clips: List[Dict[str, Any]] = []
        for cid, likes in self.clip_scores.items():
            if cid in self.clip_metadata_store:
                clip_info = self.clip_metadata_store[cid].copy()
                clip_info["local_likes"] = likes
                clip_info["comment_count"] = len(self.clip_comments.get(cid, []))
                ranked_clips.append(clip_info)

        ranked_clips.sort(key=lambda x: x["local_likes"], reverse=True)
        return ranked_clips

    async def add_to_queue(self, clip_id: str) -> Dict[str, str]:
        if clip_id in self.clip_metadata_store:
            self.admin_upload_queue[clip_id] = self.clip_metadata_store[clip_id]
            return {"status": "added"}
        return {"status": "failed"}

    async def remove_from_queue(self, clip_id: str) -> Dict[str, str]:
        if clip_id in self.admin_upload_queue:
            del self.admin_upload_queue[clip_id]
            return {"status": "removed"}
        return {"status": "failed"}

    async def get_accepted_clips(self) -> List[Dict[str, Any]]:
        return list(self.admin_upload_queue.values())

    def get_categories(self) -> List[str]:
        return getattr(
            self.config,
            "twitch_categories",
            [
                "Just Chatting",
                "League of Legends",
                "VALORANT",
            ],
        )


async def get_state() -> AppState:
    return await AppState.get_instance()
