import pytest
from sqlalchemy import select

from backend.models import Clip
from backend.core.state import AppState


@pytest.mark.integration
async def test_get_clips_persists_fetched_clips(test_client, test_db, monkeypatch):
    # Stub Twitch fetch to avoid network + keep deterministic
    async def _fake_get_instance(cls):
        # Use the normal singleton instance
        return await AppState.get_instance()

    def _fake_fetch(_self, category_name: str):
        return [
            {
                "id": "SomeSlug-abc123",
                "title": "A Clip",
                "url": "https://clips.twitch.tv/SomeSlug-abc123",
                "thumbnail_url": "https://example.com/thumb.webp",
                "view_count": 42,
                "creator_name": "Creator",
                "duration": 12.3,
                "created_at": "2025-01-01T00:00:00Z",
                "channel": "tester",
            }
        ]

    # Patch the sync fetcher used by fetch_clips
    monkeypatch.setattr(AppState, "_fetch_clips_for_category", _fake_fetch, raising=True)

    resp = test_client.get("/api/clips", params={"category": "My Streamers"})
    assert resp.status_code == 200

    # Assert DB has the clip persisted by twitch_clip_id
    result = await test_db.execute(select(Clip).where(Clip.twitch_clip_id == "SomeSlug-abc123"))
    clip = result.scalar_one_or_none()
    assert clip is not None
    assert clip.url
