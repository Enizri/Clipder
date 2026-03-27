# Quick Fix Reference Guide

## CRITICAL (Fix Immediately - App Won't Work)

### 1. Models Export (`backend/models/__init__.py`)
```python
from backend.models.user import User, UserRole
from backend.models.clip import Clip
from backend.models.vote import Vote, VoteType
from backend.models.user_streamer import UserStreamer
from backend.models.leaderboard_snapshot import LeaderboardSnapshot
from backend.models.leaderboard_monthly_summary import LeaderboardMonthlySummary
from backend.models.leaderboard_clip_performance import LeaderboardClipPerformance

__all__ = ["User", "UserRole", "Clip", "Vote", "VoteType", "UserStreamer", "LeaderboardSnapshot", "LeaderboardMonthlySummary", "LeaderboardClipPerformance"]
```

### 2. Database Session in Tasks
**Replace in `backend/core/tasks.py` - All three jobs:**
```python
# OLD (WRONG)
engine = create_async_engine(settings.database_url, echo=False)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
async with async_session() as db:
    # ...
await engine.dispose()

# NEW (RIGHT)
from backend.core.database import async_session_maker

async with async_session_maker() as db:
    # ...
```

### 3. Race Condition in Vote Endpoint (`backend/api/v1/endpoints/votes.py`)
**Update lines 51-61 and 119-129:**
```python
from sqlalchemy.dialects.postgresql import insert as pg_insert

# OLD (WRONG)
existing_vote = await db.execute(...)
if existing_vote.scalar_one_or_none():
    raise HTTPException(...)

# NEW (RIGHT)
stmt = pg_insert(Vote).values(
    user_id=current_user.id,
    clip_id=clip_id,
    vote_type=VoteType.LIKE
).on_conflict_do_nothing()

result = await db.execute(stmt)
await db.commit()

if result.rowcount == 0:
    raise HTTPException(status_code=400, detail="Already voted")
```

### 4. WebSocket Broadcast Error Logging (`backend/core/state.py`)
**Update lines 32-40:**
```python
async def broadcast(self, message: dict):
    disconnected = set()
    for connection in self.active_connections:
        try:
            await connection.send_json(message)
        except Exception as e:
            logger.warning(f"Failed to broadcast to client: {e}")  # ⚠️ Log error
            disconnected.add(connection)
    
    for conn in disconnected:
        self.active_connections.discard(conn)
```

### 5. Timezone Mismatch (All Tasks)
**Replace all `datetime.utcnow()` with `datetime.now(timezone.utc)` in `backend/core/tasks.py`**
```python
from datetime import datetime, timezone

# OLD (WRONG)
snapshot_timestamp=datetime.utcnow(),

# NEW (RIGHT)
snapshot_timestamp=datetime.now(timezone.utc),
```

---

## HIGH (Fix Before Deployment)

### 6. Hardcoded Auth Redirect (`backend/api/v1/endpoints/auth.py:178-181`)
```python
from urllib.parse import urlencode
from fastapi.responses import RedirectResponse
import os

@router.get("/auth/twitch/callback")
async def twitch_callback(...):
    # ... auth logic ...
    frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3000")
    params = urlencode({"twitch_linked": "true", "username": user_info['display_name']})
    redirect_url = f"{frontend_url}?{params}"
    
    response = RedirectResponse(url=redirect_url, status_code=302)
    response.set_cookie("auth_token", access_token, httponly=True, secure=True)
    return response
```

### 7. Snapshot Extraction N+1 (`backend/api/v1/endpoints/leaderboard.py:213-279`)
Use PostgreSQL JSONB filtering instead of Python loop:
```python
# OLD (WRONG)
for snapshot in snapshots:
    for clip_data in snapshot.ranking:
        if clip_data["clip_id"] == clip_id:
            # extract

# NEW (RIGHT) - Use PostgreSQL JSON operators
result = await db.execute(
    select(LeaderboardSnapshot)
    .where(
        and_(
            LeaderboardSnapshot.snapshot_timestamp >= cutoff_time,
            LeaderboardSnapshot.ranking.astext.contains(f'"clip_id":{clip_id}')
        )
    )
    .order_by(LeaderboardSnapshot.snapshot_timestamp)
)
```

### 8. Scheduler Double-Start (`backend/core/tasks.py:347-354`)
```python
import asyncio

_scheduler_lock = asyncio.Lock()

async def start_scheduler() -> None:
    global _scheduler
    async with _scheduler_lock:  # ⚠️ Make atomic
        scheduler = get_scheduler()
        if scheduler.running:
            logger.info("Scheduler already running")
            return
        scheduler.start()
```

### 9. Vote Input Validation (`backend/api/v1/endpoints/votes.py`)
```python
@router.post("/like/{clip_id}")
async def like_clip(
    clip_id: int = Query(..., gt=0),  # ⚠️ Positive only
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
```

### 10. Pydantic v1 Config (All schemas)
```python
# OLD (DEPRECATED)
class Config:
    from_attributes = True

# NEW (Pydantic v2)
from pydantic import ConfigDict

model_config = ConfigDict(from_attributes=True)
```

### 11. Cache Dependency Injection (`backend/api/v1/endpoints/leaderboard.py`)
```python
from backend.core.cache_provider import get_cache_provider, LeaderboardCache

async def get_cache_dependency() -> LeaderboardCache:
    return get_cache_provider()

@router.get("/current")
async def get_current_leaderboard(
    db: AsyncSession = Depends(get_db),
    cache: LeaderboardCache = Depends(get_cache_dependency),  # ⚠️ Fixed
):
```

### 12. Health Check Workers (`backend/api/v1/endpoints/health.py`)
```python
from backend.core.tasks import get_scheduler

@router.get("/health/workers")
async def health_check_workers() -> Dict[str, Any]:
    try:
        scheduler = get_scheduler()
        
        if not scheduler.running:
            return {"status": "error", "error": "Scheduler not running"}
        
        jobs = scheduler.get_jobs()
        return {
            "status": "ok",
            "scheduled_jobs": len(jobs),
            "jobs": [{"id": job.id, "name": job.name, "next_run": job.next_run_time.isoformat()} for job in jobs]
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}
```

### 13. Broadcast After DB Commit (`backend/core/tasks.py:164-169`)
```python
# OLD (WRONG)
await cache.set_top_10(current_month, new_top_10)
# Update clips
await db.commit()  # First commit
# Broadcast

# NEW (RIGHT)
await cache.set_top_10(current_month, new_top_10)

# Update clips
for clip_data in new_top_10:
    clip = await db.get(Clip, clip_data["clip_id"])
    if clip:
        clip.current_rank = clip_data["rank"]

await db.commit()  # ⚠️ Commit rank updates

# Broadcast AFTER all DB changes
connection_manager = ConnectionManager.get_instance()
changes["top_10"] = new_top_10
await connection_manager.broadcast_leaderboard_changes(changes)
```

---

## MEDIUM (Fix in Next Sprint)

### 14. Database Init Fail-Safe (`main.py:45-48`)
```python
try:
    init_database()
    logger.info("Database initialized")
except Exception as e:
    logger.error(f"CRITICAL: Database failed to initialize: {e}")
    raise  # ⚠️ Fail fast
```

### 15. Cache Thread-Safety (`backend/core/cache_provider.py`)
```python
import threading

class DictLeaderboardCache(LeaderboardCache):
    def __init__(self):
        self._cache = {}
        self._clip_ranks = {}
        self._lock = threading.RLock()  # ⚠️ Add lock
    
    async def invalidate(self, month_key: str) -> None:
        with self._lock:  # ⚠️ Atomic
            # existing logic
```

### 16. Add Index on Sort Column (`backend/models/clip.py`)
```python
class Clip(Base):
    monthly_score: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False, index=True  # ⚠️ Indexed
    )
```

### 17. Snapshot Error Logging (`backend/core/tasks.py:180-181`)
```python
except Exception as snap_error:
    logger.error(f"Failed to record snapshot: {snap_error}", exc_info=True)  # ⚠️ ERROR
```

### 18. Month Validation on Vote (`backend/api/v1/endpoints/votes.py`)
```python
current_month = datetime.utcnow().strftime("%Y-%m")

if clip.month_key != current_month:
    raise HTTPException(status_code=400, detail="Cannot vote on old clips")
```

### 19. Soft Delete for Clips (`backend/models/clip.py`)
```python
deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

# In queries
select(Clip).where(
    (Clip.month_key == current_month) &
    (Clip.deleted_at.is_(None))
)
```

### 20. CORS OPTIONS Handler (`main.py`)
```python
@app.options("/{full_path:path}")
async def preflight(full_path: str):
    return Response(status_code=200, headers={
        "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
        "Access-Control-Allow-Headers": "Authorization, Content-Type",
    })
```

---

## LOW (Tech Debt)

### 21. Configurable Cache Provider (`backend/core/config.py`)
```python
class Settings(BaseSettings):
    cache_provider: str = "dict"  # or "redis"
    redis_url: str = "redis://localhost:6379/0"
```

### 22. Add Endpoint Logging
```python
import logging
logger = logging.getLogger(__name__)

@router.get("/current")
async def get_current_leaderboard(...):
    logger.info("GET /api/v1/leaderboard/current")
    # ...
```

---

## Test Verification

After fixes, verify:

```bash
# Check imports work
python -c "from backend.models import User, Clip, Vote; print('✓ Models import')"

# Check type hints
mypy backend/

# Check no syntax errors
python -m py_compile backend/**/*.py

# Run tests
pytest tests/ -v
```

