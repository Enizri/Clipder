from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
import httpx

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.core.state import AppState, get_state
from backend.core.database import get_db
from backend.models import Clip
from backend.schemas.clip import (
    ClipsResponse,
    ClipResponse,
    VideoUrlResponse,
    ClipActionRequest,
    ClipActionResponse,
    Comment,
    CommentResponse,
    CategoryResponse,
    EmoteResponse,
    GifResponse,
)

router = APIRouter(prefix="/api", tags=["clips"])

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


@router.get("/clips", response_model=ClipsResponse)
async def get_clips(
    category: str = "My Streamers",
    state: AppState = Depends(get_state),
    db: AsyncSession = Depends(get_db),
) -> ClipsResponse:
    clips = await state.fetch_clips(category)
    # Best-effort persist so other endpoints can resolve these clips by slug.
    try:
        await state._upsert_clips(db, clips)
    except Exception:
        pass
    return ClipsResponse(clips=clips, total=len(clips))


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
    """Fast video URL endpoint with caching to avoid yt-dlp slowness."""
    import logging

    try:
        clip_pk = int(clip_id)
    except ValueError:
        clip_pk = None

    clip = None

    # Strategy 1: Try numeric DB lookup
    if clip_pk is not None:
        clip = await db.get(Clip, clip_pk)

    # Strategy 2: Try Twitch clip slug lookup if numeric failed
    if not clip:
        result = await db.execute(select(Clip).where(Clip.twitch_clip_id == clip_id))
        clip = result.scalar_one_or_none()

    # If found in DB, check cache first
    if clip:
        from backend.models.clip_video_cache import ClipVideoCache

        # Try to get from cache
        cache_result = await db.execute(
            select(ClipVideoCache).where(ClipVideoCache.clip_id == clip.id)
        )
        cached = cache_result.scalar_one_or_none()

        if cached:
            logging.info(f"Video URL cache hit for clip {clip_id}")
            # Return backend proxy URL instead of direct URL to bypass CORS
            proxy_url = f"/api/clip/{clip.id}/video-stream"
            return VideoUrlResponse(
                video_url=proxy_url, title=cached.title or clip.title
            )

        # Cache miss - extract using yt-dlp (background task would pre-populate this)
        logging.info(f"Video URL cache miss for clip {clip_id}, extracting...")
        try:
            import yt_dlp

            ydl_opts: Dict[str, Any] = {
                "format": "best[ext=mp4]/best",
                "quiet": True,
                "no_warnings": True,
                "socket_timeout": 5,  # 5 second timeout
            }

            video_url = None
            try:
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
            except Exception as ydl_error:
                logging.warning(f"yt-dlp extraction failed for {clip.url}: {ydl_error}")
                # Fallback to direct URL
                video_url = clip.url

            if video_url:
                # Cache it for next time
                try:
                    new_cache = ClipVideoCache(
                        clip_id=clip.id, video_url=video_url, title=clip.title
                    )
                    db.add(new_cache)
                    await db.commit()
                except Exception as cache_err:
                    logging.debug(f"Failed to cache video URL: {cache_err}")
                    # Don't fail the request if caching fails
                    pass

                # Return backend proxy URL instead of direct URL to bypass CORS
                proxy_url = f"/api/clip/{clip.id}/video-stream"
                return VideoUrlResponse(video_url=proxy_url, title=clip.title)

            raise HTTPException(status_code=404, detail="No video URL found for clip")

        except HTTPException:
            raise
        except Exception as e:
            logging.error(f"Error processing clip {clip_id}: {e}")
            raise HTTPException(status_code=500, detail="Failed to process clip")

    # Strategy 3: Fall back to legacy AppState cache/metadata store
    result = await state.get_video_url(clip_id)
    if "error" not in result:
        return VideoUrlResponse(**result)

    # All strategies exhausted
    raise HTTPException(
        status_code=404, detail="Could not resolve video URL for this clip"
    )


@router.post("/clip/{clip_id}/action", response_model=ClipActionResponse)
async def clip_action(
    clip_id: str,
    action_data: ClipActionRequest,
    state: AppState = Depends(get_state),
) -> ClipActionResponse:
    result = await state.action_clip(clip_id, action_data.action)
    return ClipActionResponse(**result)


@router.get("/clip/{clip_id}/comments", response_model=List[Comment])
async def get_comments(
    clip_id: str,
    state: AppState = Depends(get_state),
) -> List[Comment]:
    comments = await state.get_comments(clip_id)
    return comments


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
    emotes = {
        "twitch": TWITCH_GLOBAL_EMOTES,
        "bttv": BTTV_GLOBAL_EMOTES,
        "7tv": SEVENTV_EMOTES,
    }

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


@router.get("/gifs", response_model=GifResponse)
async def search_gifs(
    q: str = Query(default="", min_length=1), limit: int = Query(default=20, le=50)
) -> GifResponse:
    gifs: List[Dict[str, Any]] = []

    if q:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    "https://api.giphy.com/v1/gifs/search",
                    params={
                        "api_key": "dc6zaTOxFJmzC",
                        "q": q,
                        "limit": limit,
                        "rating": "pg-13",
                    },
                )
                if response.status_code == 200:
                    data = response.json()
                    for gif in data.get("data", []):
                        gifs.append(
                            {
                                "id": gif.get("id", ""),
                                "title": gif.get("title", ""),
                                "url": gif.get("images", {})
                                .get("original", {})
                                .get("url", ""),
                                "preview": gif.get("images", {})
                                .get("fixed_height_small", {})
                                .get("url", ""),
                                "width": gif.get("images", {})
                                .get("original", {})
                                .get("width", ""),
                                "height": gif.get("images", {})
                                .get("original", {})
                                .get("height", ""),
                            }
                        )
        except Exception:
            pass

    return GifResponse(gifs=gifs)
