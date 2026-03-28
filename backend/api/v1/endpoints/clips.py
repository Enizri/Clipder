import asyncio
import logging
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
import httpx

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

_clips_logger = logging.getLogger(__name__)

from backend.core.state import AppState, get_state
from backend.core.database import get_db
from backend.models import Clip
from backend.schemas.clip import (
    ClipResponse,
    ClipsResponse,
    VideoUrlResponse,
    Comment,
    CommentResponse,
    CategoryResponse,
    EmoteResponse,
)

router = APIRouter(prefix="/api/v1", tags=["clips"])

# think of moving these to somewhere else
BTTV_GLOBAL_EMOTES = [
    {
        "code": "PepePls",
        "id": "6033f6bc671912p",
        "type": "png",
        "url": "https://cdn.betterttv.net/emote/6033f6bc671912p/1x",
    },
    {
        "code": "PepeHands",
        "id": "544c694cp",
        "type": "png",
        "url": "https://cdn.betterttv.net/emote/544c694cp/1x",
    },
    {
        "code": "FeelsOkayMan",
        "id": "566c6fc8e564e5a9774e4a74",
        "type": "png",
        "url": "https://cdn.betterttv.net/emote/566c6fc8e564e5a9774e4a74/1x",
    },
    {
        "code": "FeelsBadMan",
        "id": "566c6fc8e564e5a9774e4a75",
        "type": "png",
        "url": "https://cdn.betterttv.net/emote/566c6fc8e564e5a9774e4a75/1x",
    },
    {
        "code": "FeelsBirthdayMan",
        "id": "566c6fc8e564e5a9774e4a76",
        "type": "png",
        "url": "https://cdn.betterttv.net/emote/566c6fc8e564e5a9774e4a76/1x",
    },
    {
        "code": "FeelsStrongMan",
        "id": "566c6fc8e564e5a9774e4a77",
        "type": "png",
        "url": "https://cdn.betterttv.net/emote/566c6fc8e564e5a9774e4a77/1x",
    },
    {
        "code": "FeelsWeirdMan",
        "id": "566c6fc8e564e5a9774e4a78",
        "type": "png",
        "url": "https://cdn.betterttv.net/emote/566c6fc8e564e5a9774e4a78/1x",
    },
    {
        "code": "WeirdChamp",
        "id": "57721810e564e5a9774e4a79",
        "type": "png",
        "url": "https://cdn.betterttv.net/emote/57721810e564e5a9774e4a79/1x",
    },
    {
        "code": "PepeLaugh",
        "id": "5c1f4d04e564e5a9774e4a7a",
        "type": "png",
        "url": "https://cdn.betterttv.net/emote/5c1f4d04e564e5a9774e4a7a/1x",
    },
    {
        "code": "Pepega",
        "id": "5c1f4d04e564e5a9774e4a7b",
        "type": "png",
        "url": "https://cdn.betterttv.net/emote/5c1f4d04e564e5a9774e4a7b/1x",
    },
    {
        "code": "BasedGod",
        "id": "5c1f4d04e564e5a9774e4a7c",
        "type": "png",
        "url": "https://cdn.betterttv.net/emote/5c1f4d04e564e5a9774e4a7c/1x",
    },
    {
        "code": "Clap",
        "id": "5c1f4d04e564e5a9774e4a7d",
        "type": "png",
        "url": "https://cdn.betterttv.net/emote/5c1f4d04e564e5a9774e4a7d/1x",
    },
    {
        "code": "OkayChamp",
        "id": "5c1f4d04e564e5a9774e4a7e",
        "type": "png",
        "url": "https://cdn.betterttv.net/emote/5c1f4d04e564e5a9774e4a7e/1x",
    },
    {
        "code": "Racc",
        "id": "5e9c6c18fd09b400e181a0e0",
        "type": "png",
        "url": "https://cdn.betterttv.net/emote/5e9c6c18fd09b400e181a0e0/1x",
    },
    {
        "code": "R verbatim",
        "id": "5e9c6c18fd09b400e181a0e1",
        "type": "png",
        "url": "https://cdn.betterttv.net/emote/5e9c6c18fd09b400e181a0e1/1x",
    },
]

SEVENTV_EMOTES = [
    {
        "code": "Pepega",
        "id": "60f7f2c85d3c0a5d97eca78c",
        "url": "https://cdn.7tv.app/emote/60f7f2c85d3c0a5d97eca78c/1x.webp",
    },
    {
        "code": "PepeLaugh",
        "id": "5e73099955eb7c006fb1d9f4",
        "url": "https://cdn.7tv.app/emote/5e73099955eb7c006fb1d9f4/1x.webp",
    },
    {
        "code": "KEKL",
        "id": "60ae6c0c54f32c0001656e1f",
        "url": "https://cdn.7tv.app/emote/60ae6c0c54f32c0001656e1f/1x.webp",
    },
    {
        "code": "KEKW",
        "id": "5e9c6c18fd09b400e181a0e4",
        "url": "https://cdn.7tv.app/emote/5e9c6c18fd09b400e181a0e4/1x.webp",
    },
    {
        "code": "Sadge",
        "id": "5e0fa9d40550d400155b2b06",
        "url": "https://cdn.7tv.app/emote/5e0fa9d40550d400155b2b06/1x.webp",
    },
    {
        "code": "PepeHands",
        "id": "5e0fa9d40550d400155b2b07",
        "url": "https://cdn.7tv.app/emote/5e0fa9d40550d400155b2b07/1x.webp",
    },
    {
        "code": "EZ",
        "id": "5f1b0186cf6d8a4f54d0c327",
        "url": "https://cdn.7tv.app/emote/5f1b0186cf6d8a4f54d0c327/1x.webp",
    },
    {
        "code": "PepeLaugh",
        "id": "5e73099955eb7c006fb1d9f4",
        "url": "https://cdn.7tv.app/emote/5e73099955eb7c006fb1d9f4/1x.webp",
    },
    {
        "code": "modLove",
        "id": "60ae6c0c54f32c0001656e20",
        "url": "https://cdn.7tv.app/emote/60ae6c0c54f32c0001656e20/1x.webp",
    },
    {
        "code": "peepoHappy",
        "id": "5e9c6c18fd09b400e181a0e5",
        "url": "https://cdn.7tv.app/emote/5e9c6c18fd09b400e181a0e5/1x.webp",
    },
    {
        "code": "peepoSad",
        "id": "5e9c6c18fd09b400e181a0e6",
        "url": "https://cdn.7tv.app/emote/5e9c6c18fd09b400e181a0e6/1x.webp",
    },
    {
        "code": "FeelsDankMan",
        "id": "5e9c6c18fd09b400e181a0e7",
        "url": "https://cdn.7tv.app/emote/5e9c6c18fd09b400e181a0e7/1x.webp",
    },
    {
        "code": "YEP",
        "id": "60ae6c0c54f32c0001656e21",
        "url": "https://cdn.7tv.app/emote/60ae6c0c54f32c0001656e21/1x.webp",
    },
    {
        "code": "W",
        "id": "60ae6c0c54f32c0001656e22",
        "url": "https://cdn.7tv.app/emote/60ae6c0c54f32c0001656e22/1x.webp",
    },
    {
        "code": "L",
        "id": "60ae6c0c54f32c0001656e23",
        "url": "https://cdn.7tv.app/emote/60ae6c0c54f32c0001656e23/1x.webp",
    },
]

TWITCH_GLOBAL_EMOTES = [
    {
        "code": "Kappa",
        "id": "25",
        "url": "https://static-cdn.jtvnw.net/emoticons/v2/25/default/dark/1.0",
    },
    {
        "code": "LUL",
        "id": "425618",
        "url": "https://static-cdn.jtvnw.net/emoticons/v2/425618/default/dark/1.0",
    },
    {
        "code": "PogChamp",
        "id": "305954156",
        "url": "https://static-cdn.jtvnw.net/emoticons/v2/305954156/default/dark/1.0",
    },
    {
        "code": "Kreygasm",
        "id": "1902",
        "url": "https://static-cdn.jtvnw.net/emoticons/v2/1902/default/dark/1.0",
    },
    {
        "code": "4Head",
        "id": "354",
        "url": "https://static-cdn.jtvnw.net/emoticons/v2/354/default/dark/1.0",
    },
    {
        "code": "DatSheffy",
        "id": "1904",
        "url": "https://static-cdn.jtvnw.net/emoticons/v2/1904/default/dark/1.0",
    },
    {
        "code": "TinyFace",
        "id": "1905",
        "url": "https://static-cdn.jtvnw.net/emoticons/v2/1905/default/dark/1.0",
    },
    {
        "code": "ResidentSleeper",
        "id": "1903",
        "url": "https://static-cdn.jtvnw.net/emoticons/v2/1903/default/dark/1.0",
    },
    {
        "code": "CoolStoryBob",
        "id": "89925",
        "url": "https://static-cdn.jtvnw.net/emoticons/v2/89925/default/dark/1.0",
    },
    {
        "code": "SeemsGood",
        "id": "64138",
        "url": "https://static-cdn.jtvnw.net/emoticons/v2/64138/default/dark/1.0",
    },
    {
        "code": "NotLikeThis",
        "id": "73111",
        "url": "https://static-cdn.jtvnw.net/emoticons/v2/73111/default/dark/1.0",
    },
    {
        "code": "PermaSmug",
        "id": "106741",
        "url": "https://static-cdn.jtvnw.net/emoticons/v2/106741/default/dark/1.0",
    },
    {
        "code": "VoHiYo",
        "id": "81273",
        "url": "https://static-cdn.jtvnw.net/emoticons/v2/81273/default/dark/1.0",
    },
    {
        "code": "WidePeepoSad",
        "id": "254142",
        "url": "https://static-cdn.jtvnw.net/emoticons/v2/254142/default/dark/1.0",
    },
    {
        "code": "CatJam",
        "id": "306627849",
        "url": "https://static-cdn.jtvnw.net/emoticons/v2/306627849/default/dark/1.0",
    },
    {
        "code": "PauseChamp",
        "id": "211365",
        "url": "https://static-cdn.jtvnw.net/emoticons/v2/211365/default/dark/1.0",
    },
    {
        "code": "Clueless",
        "id": "121555",
        "url": "https://static-cdn.jtvnw.net/emoticons/v2/121555/default/dark/1.0",
    },
    {
        "code": "Pepega",
        "id": "310041459",
        "url": "https://static-cdn.jtvnw.net/emoticons/v2/310041459/default/dark/1.0",
    },
    {
        "code": "F",
        "id": "295491",
        "url": "https://static-cdn.jtvnw.net/emoticons/v2/295491/default/dark/1.0",
    },
    {
        "code": "Hastad",
        "id": "188170",
        "url": "https://static-cdn.jtvnw.net/emoticons/v2/188170/default/dark/1.0",
    },
    {
        "code": "KappaCool",
        "id": "407",
        "url": "https://static-cdn.jtvnw.net/emoticons/v2/407/default/dark/1.0",
    },
    {
        "code": "MrDestructoid",
        "id": "28",
        "url": "https://static-cdn.jtvnw.net/emoticons/v2/28/default/dark/1.0",
    },
    {
        "code": "WutFace",
        "id": "100952",
        "url": "https://static-cdn.jtvnw.net/emoticons/v2/100952/default/dark/1.0",
    },
    {
        "code": "TriHard",
        "id": "120232",
        "url": "https://static-cdn.jtvnw.net/emoticons/v2/120232/default/dark/1.0",
    },
    {
        "code": "PogU",
        "id": "3649099",
        "url": "https://static-cdn.jtvnw.net/emoticons/v2/3649099/default/dark/1.0",
    },
]


def _yt_dlp_extract_sync(url: str) -> Optional[str]:
    """Run yt-dlp synchronously — must be called via run_in_executor, never directly in async code."""
    try:
        import yt_dlp

        ydl_opts: Dict[str, Any] = {
            "format": "best[ext=mp4]/best",
            "quiet": True,
            "no_warnings": True,
            "socket_timeout": 10,
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            video_url = info.get("url") if info else None
            if not video_url and info:
                for entry in (info.get("entries") or []):
                    if entry and "url" in entry:
                        return entry["url"]
            return video_url
    except Exception as e:
        _clips_logger.warning("yt-dlp extraction failed for %s: %s", url, e)
        return None


def _db_clip_to_response(clip: Clip) -> ClipResponse:
    """Convert a DB Clip row to a ClipResponse without needing AppState."""
    return ClipResponse(
        id=clip.twitch_clip_id,
        title=clip.title,
        url=clip.url,
        thumbnail_url=clip.thumbnail_url or "",
        view_count=clip.view_count,
        creator_name=clip.creator_name,
        # duration and channel are not stored in DB; provide safe defaults
        duration=0.0,
        created_at=clip.created_at.isoformat() if clip.created_at else "",
        channel=clip.creator_name,
        local_likes=clip.monthly_likes,
        comment_count=0,
    )


async def _background_refresh(category: str) -> None:
    """Fetch fresh clips from Twitch in the background so the next request is fast."""
    try:
        state = await asyncio.wait_for(AppState.get_instance(), timeout=60.0)
        await state.fetch_clips(category)
    except Exception as exc:
        _clips_logger.debug("Background Twitch refresh failed: %s", exc)


@router.get("/clips", response_model=ClipsResponse)
async def get_clips(
    category: str = "My Streamers",
    db: AsyncSession = Depends(get_db),
) -> ClipsResponse:
    """
    Serve clips with a DB-first strategy so the endpoint is never blocked by Twitch API latency.

    Priority order:
    1. AppState in-memory cache — zero latency when warm (subsequent requests)
    2. DB rows — fast async query; covers the cold-start window
    3. Block on Twitch API — only when DB is truly empty (first ever run)
    """
    # --- Fast path: AppState already has a warm cache for this category ---
    if AppState._instance is not None:
        queue = AppState._instance.category_queues.get(category)
        if queue:
            state = AppState._instance
            for clip in queue:
                clip["local_likes"] = state.clip_scores.get(clip["id"], 0)
                clip["comment_count"] = len(state.clip_comments.get(clip["id"], []))
            return ClipsResponse(
                clips=[ClipResponse.model_validate(c) for c in queue],
                total=len(queue),
            )

    # --- DB fallback: serve stored clips while Twitch warms up in background ---
    current_month = datetime.now(timezone.utc).strftime("%Y-%m")
    result = await db.execute(
        select(Clip)
        .where(Clip.month_key == current_month)
        .order_by(Clip.view_count.desc())
        .limit(30)
    )
    db_clips = result.scalars().all()

    if not db_clips:
        # Try any month — covers a server that just had its DB seeded with older data
        result = await db.execute(
            select(Clip).order_by(Clip.view_count.desc()).limit(30)
        )
        db_clips = result.scalars().all()

    if db_clips:
        # Kick off a Twitch refresh in background so the next request hits the fast path
        asyncio.create_task(_background_refresh(category))
        return ClipsResponse(
            clips=[_db_clip_to_response(c) for c in db_clips],
            total=len(db_clips),
        )

    # --- Last resort: DB is empty (first ever run) — wait for Twitch (bounded) ---
    _clips_logger.info("DB empty — waiting for Twitch fetch for category '%s'", category)
    try:
        state = await asyncio.wait_for(AppState.get_instance(), timeout=5.0)
        clips = await asyncio.wait_for(state.fetch_clips(category), timeout=25.0)
    except asyncio.TimeoutError:
        _clips_logger.warning("Timed out waiting for initial Twitch fetch")
        clips = []
    except Exception as exc:
        _clips_logger.warning("Initial Twitch fetch failed: %s", exc)
        clips = []

    return ClipsResponse(
        clips=[ClipResponse.model_validate(c) for c in clips],
        total=len(clips),
    )


@router.get("/categories", response_model=CategoryResponse)
async def get_categories(state: AppState = Depends(get_state)) -> CategoryResponse:
    categories = state.get_categories()
    return CategoryResponse(categories=categories)


@router.get("/clip/{clip_id}/video-stream")
async def get_clip_video_stream(
    clip_id: str,
    state: AppState = Depends(get_state),
    db: AsyncSession = Depends(get_db),
):
    """Stream video file with proper CORS headers to bypass frontend CORS issues."""
    import logging
    from fastapi.responses import StreamingResponse

    logging.info(f"📥 get_clip_video_stream called with clip_id: {clip_id}")

    try:
        clip_pk = int(clip_id)
    except ValueError:
        clip_pk = None

    clip = None
    if clip_pk is not None:
        clip = await db.get(Clip, clip_pk)

    if not clip:
        result = await db.execute(select(Clip).where(Clip.twitch_clip_id == clip_id))
        clip = result.scalar_one_or_none()

    if not clip or not clip.url:
        raise HTTPException(status_code=404, detail="Clip not found")

    # Extract video URL using yt-dlp
    try:
        import yt_dlp

        ydl_opts: Dict[str, Any] = {
            "format": "best[ext=mp4]/best",
            "quiet": True,
            "no_warnings": True,
        }

        video_url = None
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(clip.url, download=False)
            video_url = info.get("url") if info else None
            if not video_url and info:
                entries = info.get("entries")
                if entries:
                    for entry in entries:
                        if entry and "url" in entry:
                            video_url = entry["url"]
                            break

        if not video_url:
            raise HTTPException(status_code=404, detail="Could not extract video URL")

        # Proxy stream from video_url
        async def stream_generator():
            async with httpx.AsyncClient(timeout=None) as client:
                async with client.stream("GET", video_url) as response:
                    async for chunk in response.aiter_bytes():
                        yield chunk

        return StreamingResponse(
            stream_generator(),
            media_type="video/mp4",
            headers={
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "GET, OPTIONS",
                "Access-Control-Allow-Headers": "Content-Type",
            },
        )

    except Exception as e:
        logging.error(f"❌ Failed to stream video: {e}")
        raise HTTPException(status_code=500, detail="Failed to stream video")


@router.get("/clip/{clip_id}/video-url")
async def get_clip_video_url(
    clip_id: str,
    state: AppState = Depends(get_state),
    db: AsyncSession = Depends(get_db),
) -> VideoUrlResponse:
    """
    Return a playable video URL for a clip.

    Resolution order:
    1. DB clip + in-DB URL cache (fastest)
    2. DB clip + yt-dlp extraction via thread-pool (non-blocking)
    3. In-memory AppState cache (legacy fallback)
    """
    from backend.models.clip_video_cache import ClipVideoCache

    # --- Resolve DB clip (PK int or Twitch slug) ---
    clip = None
    try:
        clip = await db.get(Clip, int(clip_id))
    except (ValueError, Exception):
        pass
    if not clip:
        result = await db.execute(select(Clip).where(Clip.twitch_clip_id == clip_id))
        clip = result.scalar_one_or_none()

    if clip:
        # Check DB cache first
        cache_result = await db.execute(
            select(ClipVideoCache).where(ClipVideoCache.clip_id == clip.id)
        )
        cached = cache_result.scalar_one_or_none()
        if cached:
            _clips_logger.debug("Video URL cache hit for clip %s", clip_id)
            return VideoUrlResponse(video_url=cached.video_url, title=cached.title or clip.title)

        # Cache miss — run yt-dlp in a thread pool so the event loop stays free
        _clips_logger.info("Video URL cache miss for clip %s, extracting...", clip_id)
        loop = asyncio.get_event_loop()
        video_url: Optional[str] = await loop.run_in_executor(
            None, _yt_dlp_extract_sync, clip.url
        )

        # Fall back to the Twitch clip page URL if yt-dlp returned nothing
        if not video_url:
            video_url = clip.url

        # Persist to cache (best-effort; don't fail the request if it errors)
        try:
            new_cache = ClipVideoCache(clip_id=clip.id, video_url=video_url, title=clip.title)
            db.add(new_cache)
            await db.commit()
        except Exception as cache_err:
            await db.rollback()
            _clips_logger.debug("Failed to cache video URL for clip %s: %s", clip_id, cache_err)

        return VideoUrlResponse(video_url=video_url, title=clip.title)

    # Clip not in DB yet — try in-memory AppState (handles clips loaded this session)
    legacy = await state.get_video_url(clip_id)
    if "error" not in legacy:
        return VideoUrlResponse(**legacy)

    raise HTTPException(status_code=404, detail="Could not resolve video URL for this clip")


@router.get("/clip/{clip_id}/comments", response_model=List[Comment])
async def get_comments(
    clip_id: str,
    state: AppState = Depends(get_state),
) -> List[Comment]:
    raw = await state.get_comments(clip_id)
    # AppState stores plain dicts; response contract is List[Comment].
    return [Comment.model_validate(c) for c in raw]


class PostCommentRequest(BaseModel):
    text: str


@router.post("/clip/{clip_id}/comments", response_model=CommentResponse)
async def post_comment(
    clip_id: str,
    comment_data: PostCommentRequest,
    state: AppState = Depends(get_state),
) -> CommentResponse:
    text = comment_data.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="empty")

    result = await state.add_comment(clip_id, text)
    return CommentResponse(
        status=result["status"],
        comment=Comment(**result["comment"]) if result.get("comment") else None,
    )


@router.get("/emotes", response_model=EmoteResponse)
async def get_emotes(channel: str = Query(default="")) -> EmoteResponse:
    channel_emotes: List[Dict[str, str]] = []
    if channel:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                bttv_resp = await client.get(
                    f"https://api.betterttv.net/3/casters/{channel}/emotes"
                )
                if bttv_resp.status_code == 200:
                    bttv_data = bttv_resp.json()
                    for emote in bttv_data.get("emotes", []):
                        channel_emotes.append(
                            {
                                "code": emote.get("code", ""),
                                "id": emote.get("id", ""),
                                "url": f"https://cdn.betterttv.net/emote/{emote['id']}/1x",
                            }
                        )
        except Exception:
            pass

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                seventv_resp = await client.get(
                    f"https://7tv.io/v3/users/twitch/{channel}"
                )
                if seventv_resp.status_code == 200:
                    seventv_data = seventv_resp.json()
                    for emote in seventv_data.get("emote_set", {}).get("emotes", []):
                        channel_emotes.append(
                            {
                                "code": emote.get("name", ""),
                                "id": emote.get("id", ""),
                                "url": f"https://cdn.7tv.app/emote/{emote['id']}/1x.webp",
                            }
                        )
        except Exception:
            pass

    return EmoteResponse(
        twitch=TWITCH_GLOBAL_EMOTES,
        bttv=BTTV_GLOBAL_EMOTES,
        seventv=SEVENTV_EMOTES,
        channel=channel_emotes,
    )


