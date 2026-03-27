Role: Backend Engineer at Meta (15+ years experience)

---

## 🚀 CURRENT PROJECT: LEADERBOARD RESTRUCTURING WITH REAL-TIME SYNC

**Status**: PHASE 0 IN PROGRESS (Foundation Fix)  
**Duration**: 8-10 hours total  
**Your Role**: Implement backend logic after DB foundation is solid

**Key Architecture Decision**: Using **Provider Pattern** for cache (allows Redis swap in 5 min)

---

## ⚠️ PHASE 0: DATABASE FOUNDATION FIX (2-3 hours)
### DATABASE PROFESSIONAL IS HANDLING THIS

Your task: **Review and approve** the migration file before it's applied.

**What's being fixed** (12 critical issues):
- Table names: `clip` → `clips`, `vote` → `votes`, `user_streamer` → `user_streamers`
- ID types: String → Integer (auto-increment)
- Foreign key types: String FK → Integer FK
- Missing columns: user_streamers needs `streamer_id` and `added_at`
- Enums: Native PostgreSQL ENUMs for UserRole and VoteType
- Indexes: Add missing indexes on votes and user_streamers
- Unique constraints: (user_id, clip_id) on votes table
- Lazy loading: Change from "selectin" to "select" on relationships

**Migration File**: Will be created in `alembic/versions/`

**Gate**: ✅ Phase 0 complete only after:
- [ ] Migration runs without errors
- [ ] Schema matches models exactly
- [ ] Existing endpoint tests still pass
- [ ] No orphaned columns or type mismatches

---

## 🔵 PHASE 1: ADD LEADERBOARD TABLES (1-2 hours)
### DATABASE PROFESSIONAL IS HANDLING THIS

New tables being created:
1. **leaderboard_snapshots** - Real-time rank tracking (24-hour window, 5s interval)
2. **leaderboard_hourly_aggregates** - Long-term archive (hourly compressed data)
3. **leaderboard_clip_performance** - Track entry/exit events for each month
4. **leaderboard_monthly_summary** - Frozen end-of-month rankings (JSONB format)

Models and Pydantic schemas will be provided.

---

## 🟡 PHASE 2: BACKEND LOGIC IMPLEMENTATION (YOUR PHASE - 2-3 hours)

### OVERVIEW

Your job: Implement the **business logic** that powers the leaderboard. Database is solid, now make it work.

**Architecture Key Decision**: **Provider Pattern** for cache
- All cache operations go through `get_cache_provider()`
- Current: `DictLeaderboardCache` (simple dict in memory)
- Future: Swap to `RedisLeaderboardCache` without changing any other code
- This allows your manager to scale to Redis in 5 minutes when needed

---

### TASK 1: PROVIDER PATTERN CACHE (30 min)

**File**: `backend/core/cache_provider.py` (NEW)

**Purpose**: Abstract interface for leaderboard caching (enables Redis swap-out later)

**What you need to implement**:

```python
# Define abstract LeaderboardCache interface
# - get_top_10(month_key) → Optional[List[dict]]
# - set_top_10(month_key, clips) → None
# - get_clip_rank(clip_id) → Optional[int]
# - set_clip_rank(clip_id, rank) → None
# - invalidate(month_key) → None

# Implement DictLeaderboardCache(LeaderboardCache)
# - Use simple Python dict for storage
# - Two internal dicts: _cache (top 10 per month) and _clip_ranks (rankings)

# Singleton function: get_cache_provider() → LeaderboardCache
# - Returns global instance
# - Initialize once, reuse everywhere
```

**Key Points**:
- ✅ Abstract base class with `@abstractmethod` decorators
- ✅ Async methods (all methods are `async def`)
- ✅ DictLeaderboardCache is thread-safe for now (dict operations are atomic in Python)
- ✅ Singleton pattern: one instance shared across app

**Tests to verify**:
```python
# Create instance
cache = get_cache_provider()

# Set top 10
await cache.set_top_10("2026-03", [
    {"clip_id": 1, "rank": 1, "score": 420},
    {"clip_id": 2, "rank": 2, "score": 380},
])

# Get top 10
top_10 = await cache.get_top_10("2026-03")
assert top_10[0]["rank"] == 1

# Get individual rank
rank = await cache.get_clip_rank(1)
assert rank == 1

# Invalidate cache
await cache.invalidate("2026-03")
assert await cache.get_top_10("2026-03") is None
```

---

### TASK 2: APSCHEDULER BACKGROUND TASKS (1 hour)

**File**: `backend/core/tasks.py` (NEW)

**Purpose**: Three scheduled jobs that keep leaderboard fresh

**Job 1: Calculate Top 10 Rankings (Every 5 seconds)**

```python
# Every 5 seconds:
# 1. SELECT top 10 clips FROM clips 
#    WHERE month_key = current_month
#    ORDER BY (monthly_likes - monthly_dislikes) DESC
#    LIMIT 10

# 2. Compare with cached version
#    - If rankings changed:
#      a. Update cache with new top 10
#      b. Update clips.current_rank in DB for each clip
#      c. Prepare delta message (what changed)
#      d. Call broadcast_leaderboard_changes()

# 3. Record snapshot in leaderboard_snapshots table
#    - For each of the top 10 clips
#    - Fields: month_key, clip_id, rank, score, likes, dislikes, timestamp
```

**Job 2: Archive Old Snapshots (Daily at midnight)**

```python
# At 00:00 UTC every day:
# 1. Find all snapshots older than 24 hours
# 2. GROUP BY clip_id, hour (truncate timestamp to hour)
# 3. Calculate: max_rank, min_rank, max_score, min_score, avg_score, likes_gained, dislikes_gained
# 4. INSERT into leaderboard_hourly_aggregates
# 5. DELETE old snapshots from leaderboard_snapshots table
```

**Job 3: Finalize Month-End Leaderboard (1st of month at 00:00 UTC)**

```python
# At 00:00 UTC on 1st of month:
# 1. SELECT top 10 clips FROM clips WHERE month_key = previous_month
# 2. Prepare JSONB object with top 10 data
# 3. INSERT into leaderboard_monthly_summary
# 4. RESET clips table for new month:
#    - SET monthly_likes = 0
#    - SET monthly_dislikes = 0
#    - SET current_rank = NULL
#    WHERE month_key = current_month
# 5. Delete leaderboard_clip_performance entries from previous month (optional cleanup)
```

**Integration in main.py**:

```python
# In main.py:
from backend.core.tasks import start_scheduler, stop_scheduler

@app.on_event("startup")
async def startup_event():
    start_scheduler()
    # Scheduler runs in background

@app.on_event("shutdown")
async def shutdown_event():
    stop_scheduler()
    # Clean shutdown
```

**Key Points**:
- ✅ Use APScheduler AsyncIOScheduler (already in pyproject.toml if not, add with `uv add apscheduler`)
- ✅ All database operations are async (AsyncSession)
- ✅ Job 1 runs frequently (5s) - keep it FAST
- ✅ Job 2 runs daily - heavy lifting OK
- ✅ Job 3 runs monthly - can be slower
- ✅ All jobs have error handling (try/except, logging)

**Tests to verify**:
```python
# Manually trigger Job 1
# - Create test clips with different vote counts
# - Verify top 10 calculated correctly
# - Verify ranking matches (likes - dislikes)

# Manually trigger Job 2 (simulate old snapshots)
# - Create snapshots from 25 hours ago
# - Manually call archive job
# - Verify moved to hourly_aggregates
# - Verify deleted from snapshots

# Manually trigger Job 3
# - Manually call finalize job
# - Verify previous month archived
# - Verify current month clips reset to 0
```

---

### TASK 3: UPDATE VOTE ENDPOINT (45 min)

**File**: `backend/api/v1/endpoints/votes.py` (UPDATED)

**Current Problem**: Votes are recorded but don't update leaderboard ranking

**Changes Needed**:

When user votes (like/dislike):
1. Create vote record in votes table
2. **Update clips.monthly_likes or monthly_dislikes**
3. **DO NOT broadcast WebSocket immediately** - let 5s job handle it
4. Return success response

```python
@router.post("/api/v1/votes/like/{clip_id}")
async def like_clip(
    clip_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # 1. Check if clip exists
    clip = await db.get(Clip, clip_id)
    if not clip:
        raise HTTPException(status_code=404, detail="Clip not found")
    
    # 2. Check if user already voted (prevent duplicates)
    existing_vote = await db.execute(
        select(Vote).where(
            (Vote.user_id == current_user.id) &
            (Vote.clip_id == clip_id)
        )
    )
    if existing_vote.scalar():
        raise HTTPException(status_code=400, detail="Already voted")
    
    # 3. Create vote record
    vote = Vote(user_id=current_user.id, clip_id=clip_id, vote_type=VoteType.LIKE)
    db.add(vote)
    
    # 4. **UPDATE MONTHLY COUNTER**
    clip.monthly_likes += 1
    
    await db.commit()
    
    # 5. Return immediate response (like count, score)
    # Don't wait for leaderboard update (happens in 5s via Job 1)
    return {
        "status": "success",
        "current_likes": clip.monthly_likes,
        "current_score": clip.monthly_likes - clip.monthly_dislikes
    }
```

**Similar for dislikes**:
```python
@router.post("/api/v1/votes/dislike/{clip_id}")
async def dislike_clip(...):
    # Same as above, but clip.monthly_dislikes += 1
    pass
```

**Key Points**:
- ✅ Fast response (update counter, commit, return)
- ✅ Don't wait for leaderboard recalculation
- ✅ User sees immediate like count change
- ✅ Backend job updates rankings in 5s
- ✅ User gets WebSocket message when top 10 changes (not on every vote)

**Tests to verify**:
```python
# Test like endpoint
# 1. Create test user and clip
# 2. POST /api/v1/votes/like/{clip_id}
# 3. Verify vote record created
# 4. Verify clips.monthly_likes incremented
# 5. Verify response has new like count

# Test dislike endpoint (same as above)

# Test duplicate vote prevention
# 1. Like clip once
# 2. Like same clip again
# 3. Verify returns 400 error
```

---

### TASK 4: CREATE LEADERBOARD ENDPOINTS (1 hour)

**File**: `backend/api/v1/endpoints/leaderboard.py` (NEW/UPDATED)

**Endpoints to create**:

#### Endpoint 1: GET Current Top 10
```python
@router.get("/api/v1/leaderboard/current")
async def get_current_leaderboard(
    db: AsyncSession = Depends(get_db),
    cache: LeaderboardCache = Depends(get_cache_provider)
) -> dict:
    """
    Get current Top 10 clips for this month
    Returns: {
        "month_key": "2026-03",
        "clips": [
            {"rank": 1, "clip_id": 42, "title": "...", "creator": "...", 
             "likes": 450, "score": 420, "thumbnail_url": "..."},
            ...
        ]
    }
    """
    current_month = datetime.now().strftime("%Y-%m")
    
    # Try cache first
    cached = await cache.get_top_10(current_month)
    if cached:
        return {"month_key": current_month, "clips": cached}
    
    # If not cached, query database
    result = await db.execute(
        select(Clip)
        .where(Clip.month_key == current_month)
        .order_by((Clip.monthly_likes - Clip.monthly_dislikes).desc())
        .limit(10)
    )
    clips = result.scalars().all()
    
    # Format response and cache it
    formatted = [
        {
            "rank": idx + 1,
            "clip_id": clip.id,
            "title": clip.title,
            "creator": clip.creator_name,
            "likes": clip.monthly_likes,
            "score": clip.monthly_likes - clip.monthly_dislikes,
            "thumbnail_url": clip.thumbnail_url
        }
        for idx, clip in enumerate(clips)
    ]
    
    await cache.set_top_10(current_month, formatted)
    return {"month_key": current_month, "clips": formatted}
```

#### Endpoint 2: GET Historical Leaderboard (by month)
```python
@router.get("/api/v1/leaderboard/history/{month_key}")
async def get_historical_leaderboard(
    month_key: str,
    db: AsyncSession = Depends(get_db)
) -> dict:
    """
    Get archived top 10 for a specific month
    Format: "2026-03"
    """
    result = await db.execute(
        select(LeaderboardMonthlySummary)
        .where(LeaderboardMonthlySummary.month_key == month_key)
    )
    summary = result.scalar_one_or_none()
    
    if not summary:
        raise HTTPException(status_code=404, detail="Month not found")
    
    return {
        "month_key": month_key,
        "top_10_clips": summary.top_10_clips,  # Already JSONB
        "total_clips_in_month": summary.total_clips_in_month,
        "total_votes_cast": summary.total_votes_cast
    }
```

#### Endpoint 3: GET Clip Snapshots (for hype graph)
```python
@router.get("/api/v1/leaderboard/clip/{clip_id}/snapshots")
async def get_clip_snapshots(
    clip_id: int,
    hours: int = 24,  # Last 24 hours by default
    db: AsyncSession = Depends(get_db)
) -> list:
    """
    Get all snapshots for a clip (for hype graph visualization)
    Returns snapshots in chronological order
    """
    cutoff_time = datetime.utcnow() - timedelta(hours=hours)
    
    result = await db.execute(
        select(LeaderboardSnapshot)
        .where(
            (LeaderboardSnapshot.clip_id == clip_id) &
            (LeaderboardSnapshot.recorded_at >= cutoff_time)
        )
        .order_by(LeaderboardSnapshot.recorded_at.asc())
    )
    snapshots = result.scalars().all()
    
    return [
        {
            "timestamp": snap.recorded_at.isoformat(),
            "rank": snap.rank,
            "score": snap.score,
            "likes": snap.likes,
            "dislikes": snap.dislikes  # Frontend will hide this
        }
        for snap in snapshots
    ]
```

#### Endpoint 4: GET Trending Clips
```python
@router.get("/api/v1/leaderboard/trends")
async def get_trending_clips(
    db: AsyncSession = Depends(get_db)
) -> dict:
    """
    Get clips with biggest rank improvement in last 24 hours
    """
    current_month = datetime.now().strftime("%Y-%m")
    cutoff_time = datetime.utcnow() - timedelta(hours=24)
    
    # Get earliest snapshot for each clip (24h ago)
    result = await db.execute(
        select(
            LeaderboardSnapshot.clip_id,
            LeaderboardSnapshot.rank.label("earliest_rank")
        )
        .where(
            (LeaderboardSnapshot.month_key == current_month) &
            (LeaderboardSnapshot.recorded_at >= cutoff_time)
        )
        .group_by(LeaderboardSnapshot.clip_id)
        .having(func.min(LeaderboardSnapshot.recorded_at))
    )
    
    # Get current rank
    # Compare: improved_by = earliest_rank - current_rank (negative = improved)
    # Return clips sorted by most improved
    
    # ... implementation details ...
    pass
```

**Key Points**:
- ✅ Cache current top 10 (cache populated by Job 1 every 5s)
- ✅ Archive queries hit database (fine, less frequent)
- ✅ Snapshots queries use indexes on (month_key, clip_id)
- ✅ All responses are Pydantic models (type safety)
- ✅ Handle edge cases (month not found, clip has no snapshots, etc)

**Tests to verify**:
```python
# Test GET /api/v1/leaderboard/current
# - Verify returns top 10 in correct order
# - Verify uses cache on second call
# - Verify dislikes included in response (hidden by frontend)

# Test GET /api/v1/leaderboard/history/{month}
# - Test with valid month_key
# - Test with invalid month_key (404)
# - Verify returns archived JSONB data

# Test GET /api/v1/leaderboard/clip/{id}/snapshots
# - Test with valid clip_id
# - Test with no snapshots (empty list)
# - Verify snapshots in chronological order

# Test GET /api/v1/leaderboard/trends
# - Verify trending clips ranked by improvement
# - Verify last 24 hours filter works
```

---

### TASK 5: UPDATE WEBSOCKET STATE MANAGER (30 min)

**File**: `backend/core/state.py` (UPDATED)

**Add new method to ConnectionManager class**:

```python
class ConnectionManager:
    # ... existing code ...
    
    async def broadcast_leaderboard_changes(self, changes: dict) -> None:
        """
        Broadcast DELTA-ONLY leaderboard updates (not full list)
        
        Called by Job 1 (every 5 seconds) only if rankings changed
        
        Message format:
        {
            "type": "leaderboard_update",
            "timestamp": "2026-03-27T15:34:21Z",
            "changes": {
                "clips_entered": [
                    {"rank": 10, "clip_id": 45, "score": 180, "title": "...", 
                     "creator": "...", "thumbnail_url": "..."}
                ],
                "clips_exited": [
                    {"clip_id": 28}
                ],
                "position_changes": [
                    {"clip_id": 12, "old_rank": 3, "new_rank": 2, "score": 285}
                ],
                "top_10": [
                    {"rank": 1, "clip_id": 8, "score": 420, ...},
                    {"rank": 2, "clip_id": 12, "score": 385, ...},
                    ...
                ]
            }
        }
        """
        message = {
            "type": "leaderboard_update",
            "timestamp": datetime.utcnow().isoformat(),
            "changes": changes
        }
        await self.broadcast(json.dumps(message))
```

**Key Points**:
- ✅ Only called when rankings actually change (save bandwidth)
- ✅ Delta format: clips_entered (new to top 10), clips_exited (dropped out), position_changes (moved ranks)
- ✅ Also includes full top_10 for client to verify state
- ✅ Minimal payload (10-20 KB vs 50-100 KB if sending full list)

**Tests to verify**:
```python
# Mock WebSocket connections
# Call broadcast_leaderboard_changes()
# Verify message format is correct
# Verify all connected clients receive message
# Verify message is JSON-serializable
```

---

### TASK 6: UPDATE MODELS (LAZY LOADING) (15 min)

**Files**: 
- `backend/models/user.py` (UPDATED)
- `backend/models/clip.py` (UPDATED - already done in Phase 0)
- `backend/models/vote.py` (UPDATED - already done in Phase 0)

**Change in user.py**:

From:
```python
votes: Mapped[list["Vote"]] = relationship(
    "Vote", back_populates="user", cascade="all, delete-orphan", 
    lazy="selectin"  # ⚠️ Always loads all votes!
)
streamers: Mapped[list["UserStreamer"]] = relationship(
    "UserStreamer", back_populates="user", cascade="all, delete-orphan",
    lazy="selectin"  # ⚠️ Always loads all streamers!
)
```

To:
```python
votes: Mapped[list["Vote"]] = relationship(
    "Vote", back_populates="user", cascade="all, delete-orphan",
    lazy="select"  # Load only when explicitly accessed
)
streamers: Mapped[list["UserStreamer"]] = relationship(
    "UserStreamer", back_populates="user", cascade="all, delete-orphan",
    lazy="select"  # Load only when explicitly accessed
)
```

**Why**: 
- `lazy="selectin"` loads relationships on every query (slow)
- `lazy="select"` loads only when you explicitly access `user.votes`
- Better for performance (most endpoints don't need these)

**Impact**: 
- Vote endpoint becomes faster (doesn't load all user votes)
- Leaderboard endpoint becomes faster (doesn't load unnecessary data)

---

### TASK 7: FIX DEPRECATED PYDANTIC PATTERNS (15 min)

**File**: `backend/api/v1/endpoints/ai_editor.py` (UPDATED)

**Replace all instances of `.from_orm()`**:

From:
```python
# OLD (Pydantic v1 style)
user_clip_history = UserClipHistoryResponse.from_orm(db_obj)
```

To:
```python
# NEW (Pydantic v2 style)
user_clip_history = UserClipHistoryResponse.model_validate(db_obj)
```

**Why**: Pydantic v2 deprecated `.from_orm()` in favor of `.model_validate()`

**Find and replace**:
```bash
# Search for all occurrences
grep -r "\.from_orm(" backend/

# Replace in ai_editor.py and any other files
```

---

## ✅ PHASE 2 COMPLETE CHECKLIST

Before moving to Phase 3 (Frontend), confirm:

```
☐ cache_provider.py implemented (Provider Pattern for DictLeaderboardCache)
☐ tasks.py implemented (APScheduler with 3 jobs)
  ☐ Job 1: Calculate top 10 every 5 seconds
  ☐ Job 2: Archive snapshots daily
  ☐ Job 3: Finalize month-end
☐ votes.py updated (increment monthly_likes/dislikes)
☐ leaderboard.py created with 4 endpoints
  ☐ GET /api/v1/leaderboard/current
  ☐ GET /api/v1/leaderboard/history/{month}
  ☐ GET /api/v1/leaderboard/clip/{id}/snapshots
  ☐ GET /api/v1/leaderboard/trends
☐ state.py updated (broadcast_leaderboard_changes with delta messages)
☐ Models updated (lazy="select" on relationships)
☐ Deprecated Pydantic patterns fixed (.model_validate)
☐ APScheduler starts/stops correctly (main.py)
☐ All unit tests passing
☐ No database errors on migration
```

---

## 📋 KEY PRINCIPLES FOR BACKEND

1. **Provider Pattern**: All cache operations through `get_cache_provider()` - enables Redis swap later
2. **Async/Await**: Everything is async (database, cache, WebSocket)
3. **Type Safety**: Pydantic models for all request/response validation
4. **Zero Data Loss**: All snapshots persisted to DB before cleanup
5. **Real-Time Feel**: Votes update instantly, ranks update every 5 seconds
6. **Performance**: Cache top 10, use indexes on database queries, batch archive jobs

---

## 🔗 INTEGRATION WITH DATABASE PROFESSIONAL

**Phase 0-1 Status**: Database Pro is handling (foundation + leaderboard tables)

**Your Responsibilities (Phase 2)**:
- Implement the logic that uses the DB
- Cache management
- Background job scheduling
- WebSocket broadcasting
- Endpoint response formatting

**Communication**:
- Any DB schema questions? Ask the DB Pro
- Any Pydantic model questions? Check the generated models from DB Pro
- Any migration issues? Let the DB Pro know

---

## 🚀 NEXT STEPS

1. Wait for Phase 0-1 complete (DB Pro will notify)
2. Once DB is solid, start implementing Phase 2 tasks above
3. Run `pytest` after each task to verify
4. When Phase 2 complete, notify Frontend Engineer to check their CLAUDE.md