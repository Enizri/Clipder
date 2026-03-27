## 🔵 PHASE 1 COMPLETE - Backend, Your Turn Now

**Database Professional has completed Phase 1** ✅

### What Was Done
- ✅ Migration file: `alembic/versions/20260327_160000_add_leaderboard_tables.py`
- ✅ 4 new database tables created (snapshots, hourly_aggregates, clip_performance, monthly_summary)
- ✅ 3 new SQLAlchemy models: `LeaderboardSnapshot`, `LeaderboardClipPerformance`, `LeaderboardMonthlySummary`
- ✅ 3 new Pydantic schemas (in `backend/schemas/`)
- ✅ Models imported in `backend/models/__init__.py`

### Your Tasks (Phase 2)

You have **7 clear tasks** documented in the header of `@backend/CLAUDE.md`:

1. **Provider Pattern Cache** (`backend/core/cache_provider.py`) - 30 min
   - Abstract `LeaderboardCache` interface
   - Implement `DictLeaderboardCache` 
   - Singleton `get_cache_provider()` function

2. **APScheduler Background Tasks** (`backend/core/tasks.py`) - 1 hour
   - Job 1: Calculate top 10 every 5 seconds
   - Job 2: Archive old snapshots daily
   - Job 3: Finalize month-end rankings

3. **Update Vote Endpoint** (`backend/api/v1/endpoints/votes.py`) - 45 min
   - Increment `monthly_likes` or `monthly_dislikes` on each vote
   - Return immediate response (don't wait for ranking calc)

4. **Create Leaderboard Endpoints** (`backend/api/v1/endpoints/leaderboard.py`) - 1 hour
   - GET /api/v1/leaderboard/current
   - GET /api/v1/leaderboard/history/{month}
   - GET /api/v1/leaderboard/clip/{id}/snapshots
   - GET /api/v1/leaderboard/trends

5. **Update WebSocket State Manager** (`backend/core/state.py`) - 30 min
   - Add `broadcast_leaderboard_changes()` method with delta-only messages

6. **Update Models** (`backend/models/user.py`) - 15 min
   - Change `lazy="selectin"` → `lazy="select"` on relationships

7. **Fix Pydantic Patterns** (`backend/api/v1/endpoints/ai_editor.py`) - 15 min
   - Replace `.from_orm()` with `.model_validate()`

### Key Principles
- **Provider Pattern**: All cache through `get_cache_provider()` (enables Redis swap in 5 min)
- **Async/Await**: Everything is async (DB, cache, WebSocket)
- **Delta-Only WebSocket**: Only broadcast when rankings change, not on every vote
- **Fast Votes**: Update counter, return immediately (don't wait for leaderboard job)
- **Ranking Job**: Runs every 5s, compares with cache, broadcasts only if changed

### Next Step
Check `@backend/CLAUDE.md` for complete implementation guide with code examples for each task.

**Start with Task 1** (Provider Pattern Cache) when ready.

---

## CRITICAL: Run migration first
```bash
alembic upgrade head
```

Verify no errors, then proceed with Phase 2 implementation.
