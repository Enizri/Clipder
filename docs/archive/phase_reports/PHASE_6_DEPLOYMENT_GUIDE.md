# PHASE 6: PC-2 DEPLOYMENT & REAL-TIME SYNC VERIFICATION

**Status**: 🟡 IN PROGRESS  
**Duration**: 1.5-2 hours  
**Target**: Full system deployment + cross-PC real-time sync  
**Success Criteria**: All 24 tests PASS + real-time leaderboard sync verified

---

## 🎯 Phase 6 Objectives

1. ✅ Set up PostgreSQL database (Supabase recommended)
2. ✅ Create .env configuration file
3. ✅ Run all 24 integration tests (expect 24/24 PASS)
4. ✅ Deploy to PC-2 (backend + frontend)
5. ✅ Verify real-time sync between PC-1 and PC-2
6. ✅ Test critical scenarios (5 concurrent votes, etc.)
7. ✅ Health check validation on deployed system
8. ✅ Go/no-go decision for Phase 7

---

## STEP 1: Database Setup

### Option A: Supabase (RECOMMENDED)

**1.1 Get Supabase Connection String**

Visit your Supabase project:
1. Go to https://supabase.com → Your Project
2. Settings → Database → Connection String
3. Select "Connection pooler" (better for FastAPI)
4. Copy the full connection string

**Format**: `postgresql+asyncpg://postgres.xxxxx:password@xxxxx.pooler.supabase.com:6543/postgres`

**1.2 Create .env File on PC-1**

Create `E:\projects\ClipApp\.env`:

```bash
# Database URL (Supabase PostgreSQL)
DATABASE_URL=postgresql+asyncpg://postgres.your_project:your_password@your_host.pooler.supabase.com:6543/postgres

# Test Database URL (same as above, or separate test DB)
TEST_DATABASE_URL=postgresql+asyncpg://postgres.your_project:your_password@your_host.pooler.supabase.com:6543/postgres

# Twitch API Credentials
TWITCH_CLIENT_ID=your_twitch_client_id
TWITCH_CLIENT_SECRET=your_twitch_client_secret
TWITCH_REDIRECT_URI=http://localhost:8000/auth/twitch/callback

# Groq API Key
GROQ_API_KEY=your_groq_api_key

# JWT Settings
SECRET_KEY=your_256bit_secret_key_here_make_it_random
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=10080

# Twitch Channels & Categories
TWITCH_CHANNELS=xqc,shroud,ninja
TWITCH_CATEGORIES=Just Chatting,Valorant,Minecraft

# Supabase (optional)
SUPABASE_URL=https://your_project.supabase.co
SUPABASE_ANON_KEY=your_supabase_anon_key
```

**1.3 Verify Connection**

```bash
# On PC-1, test the connection
python -c "
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine

async def test():
    engine = create_async_engine('postgresql+asyncpg://...')
    async with engine.connect() as conn:
        result = await conn.execute('SELECT 1')
        print('✅ Connection successful')
    await engine.dispose()

asyncio.run(test())
"
```

### Option B: Local PostgreSQL (Alternative)

If using local PostgreSQL:

```bash
DATABASE_URL=postgresql+asyncpg://postgres:password@localhost:5432/clipder
TEST_DATABASE_URL=postgresql+asyncpg://postgres:password@localhost:5432/clipder_test
```

---

## STEP 2: Run Database Migrations

**2.1 Apply Alembic Migrations**

```bash
# On PC-1
cd E:\projects\ClipApp

# Initialize database with latest schema
alembic upgrade head
```

**Expected Output**:
```
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
INFO  [alembic.migration] Running upgrade  -> 20260327_145359_fix_schema_foundation
INFO  [alembic.migration] Running upgrade 20260327_145359_fix_schema_foundation -> 20260327_160000_add_leaderboard_tables
INFO  [alembic.migration] Running upgrade 20260327_160000_add_leaderboard_tables -> [current]
```

**2.2 Verify Schema**

```bash
# Check that tables exist
python -c "
from backend.models import Base
from sqlalchemy import inspect, create_engine

engine = create_engine('postgresql://...')
inspector = inspect(engine)
tables = inspector.get_table_names()
print('Tables:', tables)
print('✅ Should see 9 tables (users, clips, votes, ...)')
"
```

---

## STEP 3: Run Full Test Suite

### 3.1 Execute All 24 Tests

```bash
# On PC-1, with .env configured
cd E:\projects\ClipApp

pytest tests/integration/ -v --tb=short
```

**Expected Output**:
```
tests/integration/test_archive_job.py::test_hourly_aggregates_table_exists PASSED [ 4%]
tests/integration/test_archive_job.py::test_snapshots_archived_after_24h PASSED [ 8%]
tests/integration/test_delta_calculation.py::test_clips_enter_top_10 PASSED [ 12%]
tests/integration/test_delta_calculation.py::test_clips_exit_top_10 PASSED [ 16%]
tests/integration/test_delta_calculation.py::test_position_changes_detected PASSED [ 20%]
tests/integration/test_delta_calculation.py::test_rank_1_vs_rank_2_swap PASSED [ 25%]
tests/integration/test_delta_calculation.py::test_multiple_simultaneous_changes PASSED [ 29%]
tests/integration/test_month_end.py::test_monthly_summary_table_exists PASSED [ 33%]
tests/integration/test_month_end.py::test_month_end_creates_summary PASSED [ 37%]
tests/integration/test_month_end.py::test_monthly_likes_reset_field_exists PASSED [ 41%]
tests/integration/test_month_end.py::test_no_data_loss_during_month_end PASSED [ 45%]
tests/integration/test_snapshot_job.py::test_snapshot_table_exists PASSED [ 50%]
tests/integration/test_snapshot_job.py::test_snapshot_captures_top_10 PASSED [ 54%]
tests/integration/test_snapshot_job.py::test_snapshot_score_calculation PASSED [ 58%]
tests/integration/test_snapshot_job.py::test_snapshot_no_duplicates PASSED [ 62%]
tests/integration/test_vote_endpoint.py::test_vote_like_increments_counter PASSED [ 66%]
tests/integration/test_vote_endpoint.py::test_vote_dislike_increments_counter PASSED [ 70%]
tests/integration/test_five_concurrent_votes PASSED [ 75%]  ⭐ CRITICAL TEST
tests/integration/test_vote_endpoint.py::test_cant_vote_twice_same_clip PASSED [ 79%]
tests/integration/test_vote_endpoint.py::test_vote_returns_correct_score PASSED [ 83%]
tests/integration/test_vote_endpoint.py::test_vote_endpoint_response_time PASSED [ 87%]
tests/integration/test_websocket.py::test_websocket_endpoint_exists PASSED [ 91%]
tests/integration/test_websocket.py::test_websocket_message_format PASSED [ 95%]
tests/integration/test_websocket.py::test_websocket_message_has_required_fields PASSED [100%]

================== 24 passed in 45.23s ====================
```

### 3.2 If Tests Fail

If any test fails, check:

1. **Database connection error?**
   ```bash
   pytest tests/integration/test_vote_endpoint.py::test_vote_like_increments_counter -v --tb=long
   # Look for connection timeout or authentication error
   ```

2. **Schema missing?**
   ```bash
   alembic current  # Check migration status
   alembic upgrade head  # Re-run migrations
   ```

3. **Data integrity issue?**
   ```bash
   pytest tests/integration/test_no_data_loss_during_month_end -v --tb=long
   ```

---

## STEP 4: Create Initial Test Data

**4.1 Create Admin User**

```bash
# On PC-1
python create_admin_user.py
```

**4.2 Create Sample Clips (for testing)**

```bash
# Run manual test workflow to create clips via API
python scripts/manual_test_workflow.py
```

---

## STEP 5: Start Backend on PC-1

```bash
# Terminal 1 on PC-1
cd E:\projects\ClipApp

# Start FastAPI backend
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Expected output:
# INFO:     Uvicorn running on http://0.0.0.0:8000
# INFO:     Application startup complete
```

### 5.1 Verify Backend Health

```bash
# Terminal 2 on PC-1
curl http://localhost:8000/api/v1/health

# Expected response:
{
  "status": "ok",
  "timestamp": "2026-03-27T17:00:21Z",
  "database": "connected",
  "cache": "connected",
  "workers": "running",
  "scheduled_jobs": 3,
  "version": "1.0.0"
}
```

---

## STEP 6: Start Frontend on PC-1

```bash
# Terminal 3 on PC-1
cd E:\projects\ClipApp\frontend

npm run dev

# Expected output:
#   VITE v5.0.0  ready in 234 ms
#   ➜  Local:   http://localhost:5173/
#   ➜  Network: use --host to expose
```

### 6.1 Open in Browser

- Go to `http://localhost:5173`
- Verify UI loads
- Check browser console for WebSocket connection
- Expected: Connected to `/ws/leaderboard`

---

## STEP 7: Deploy to PC-2

### 7.1 On PC-2: Clone Repository

```bash
# On PC-2
git clone https://github.com/your-repo/ClipApp.git
cd ClipApp
```

### 7.2 On PC-2: Set Up Environment

```bash
# Copy .env from PC-1
# (Same Supabase database, different machine)
cp .env.example .env

# Edit .env with same database URL as PC-1
# Important: DATABASE_URL must point to SAME Supabase instance
```

### 7.3 On PC-2: Install Dependencies

```bash
cd E:\ClipApp  # or wherever PC-2 has it

# Install Python dependencies
uv sync

# Install frontend dependencies
cd frontend
npm install
```

### 7.4 On PC-2: Start Backend

```bash
# Terminal 1 on PC-2
cd E:\ClipApp

# Start on different port to avoid conflict
uvicorn main:app --reload --host 0.0.0.0 --port 8001
```

### 7.5 On PC-2: Start Frontend

```bash
# Terminal 2 on PC-2
cd E:\ClipApp\frontend

# Start on different port
npm run dev -- --port 5174
```

---

## STEP 8: Test Real-Time Sync Between PCs

### 8.1 Open Both Browsers

- **PC-1**: http://localhost:5173 (Backend: :8000)
- **PC-2**: http://localhost:5174 (Backend: :8001)

### 8.2 Submit Vote on PC-1, Watch PC-2 Update

1. On PC-1 browser: Click "Like" on a clip
2. On PC-2 browser: Watch the leaderboard update in real-time
3. Both should show same top 10 rankings

### 8.3 Test Scenarios

**Scenario 1: Single Vote**
- [ ] PC-1: Submit 1 like
- [ ] PC-2: See like count increment
- [ ] Both: See leaderboard rank change within 5 seconds

**Scenario 2: Five Concurrent Votes** ⭐ CRITICAL
- [ ] PC-1: Submit 5 votes rapidly for same clip
- [ ] PC-2: Watch like counter increment by 5
- [ ] Both: Verify final score correct
- [ ] Database: Confirm 5 votes recorded (no race conditions)

**Scenario 3: Cross-PC Votes**
- [ ] PC-1: Submit vote for Clip A
- [ ] PC-2: Submit vote for Clip B (simultaneously)
- [ ] Both: Verify both clips ranked correctly
- [ ] Both: See correct final top 10

**Scenario 4: Rank Transitions**
- [ ] Find clip at rank #10
- [ ] PC-1: Submit votes to push it into top 5
- [ ] PC-2: Watch it climb ranks in real-time
- [ ] Both: Verify smooth animation

---

## STEP 9: Validate Health Checks

### 9.1 PC-1 Health

```bash
curl http://localhost:8000/api/v1/health
curl http://localhost:8000/api/v1/health/db
curl http://localhost:8000/api/v1/health/cache
curl http://localhost:8000/api/v1/health/workers
```

### 9.2 PC-2 Health

```bash
curl http://localhost:8001/api/v1/health
curl http://localhost:8001/api/v1/health/db
curl http://localhost:8001/api/v1/health/cache
curl http://localhost:8001/api/v1/health/workers
```

**Expected**: All health checks return `"status": "ok"`

---

## STEP 10: Verify Snapshot Recording

### 10.1 Check Snapshots Are Created

```bash
# Check leaderboard_snapshots table
psql postgresql://... -c "SELECT COUNT(*) FROM leaderboard_snapshots;"

# Should see snapshots being created every 5 seconds
# Run multiple times and count should increase
```

### 10.2 Verify Month-End Logic

```bash
# Check leaderboard_monthly_summary table
psql postgresql://... -c "SELECT * FROM leaderboard_monthly_summary;"

# Should see frozen rankings if month has ended
```

---

## STEP 11: Performance Testing

### 11.1 Response Time

```bash
# Time a single vote request
time curl -X POST http://localhost:8000/api/v1/votes/like/1

# Expected: < 100ms
```

### 11.2 WebSocket Latency

- Submit vote on PC-1
- Measure time until PC-2 receives update
- Expected: < 1 second

### 11.3 Database Query Speed

```bash
# Get current leaderboard
time curl http://localhost:8000/api/v1/leaderboard/current

# Expected: < 50ms (cached)
```

---

## STEP 12: Final Verification Checklist

```
Database:
[ ] ✅ Supabase connected and accessible
[ ] ✅ All migrations applied (9 tables exist)
[ ] ✅ No connection timeouts

Tests:
[ ] ✅ All 24 tests PASS
[ ] ✅ Vote endpoint tests PASS (6 tests)
[ ] ✅ Snapshot tests PASS (4 tests)
[ ] ✅ WebSocket tests PASS (3 tests)
[ ] ✅ 5 concurrent votes test PASS ⭐

Backend:
[ ] ✅ PC-1 backend running on :8000
[ ] ✅ PC-2 backend running on :8001
[ ] ✅ Both connected to same database
[ ] ✅ Health checks passing on both

Frontend:
[ ] ✅ PC-1 frontend running on :5173
[ ] ✅ PC-2 frontend running on :5174
[ ] ✅ Both WebSocket connected
[ ] ✅ Both showing same data

Real-Time Sync:
[ ] ✅ Vote on PC-1 → PC-2 updates
[ ] ✅ Vote on PC-2 → PC-1 updates
[ ] ✅ Rankings synchronized
[ ] ✅ Timestamps aligned

Performance:
[ ] ✅ Vote response < 100ms
[ ] ✅ WebSocket update < 1s
[ ] ✅ Leaderboard fetch < 50ms
[ ] ✅ No memory leaks
[ ] ✅ No CPU spikes

Data Integrity:
[ ] ✅ No lost votes
[ ] ✅ Ranking scores correct
[ ] ✅ Vote counts accurate
[ ] ✅ Snapshots recorded
```

---

## TROUBLESHOOTING

### Database Connection Issues

**Problem**: `psycopg2.OperationalError: connection timeout`

**Solution**:
1. Verify DATABASE_URL is correct
2. Check firewall allows PostgreSQL (port 5432 for Supabase pooler, 6543)
3. Try direct psql connection: `psql "your_connection_string"`

### Migration Failures

**Problem**: `alembic.exc.CommandError: Can't locate revision...`

**Solution**:
```bash
alembic history  # See all migrations
alembic current  # Check current state
alembic upgrade head  # Apply all pending
```

### Tests Fail with "No clips found"

**Problem**: Tests expect sample data

**Solution**:
```bash
# Create sample clips
python create_sample_data.py
# Or run manual test workflow
python scripts/manual_test_workflow.py
```

### WebSocket Not Connecting

**Problem**: Browser console shows connection refused

**Solution**:
1. Verify backend is running: `curl http://localhost:8000/api/v1/health`
2. Check WebSocket URL in browser: Should be `ws://localhost:8000/ws/leaderboard`
3. Check frontend environment: May have hardcoded dev server URL

### Cross-PC Communication Issues

**Problem**: PC-2 can't see updates from PC-1

**Solution**:
1. Verify both use SAME database (DATABASE_URL identical)
2. Verify both WebSockets connected: Check browser dev tools on both PCs
3. Check network firewall allows traffic between PCs

---

## Success Criteria: GO/NO-GO Decision

### GO CONDITIONS (Proceed to Phase 7):
✅ All 24 tests PASS  
✅ Real-time sync works (vote on PC-1, update on PC-2 within 1s)  
✅ 5 concurrent votes test PASS (no race conditions)  
✅ Health checks passing on both PCs  
✅ WebSocket connected and receiving deltas  
✅ Database consistent across both machines  

### NO-GO CONDITIONS (Debug and Retry):
❌ Tests failing (> 0 failures)  
❌ Real-time sync broken (PC-2 not receiving updates)  
❌ 5 concurrent votes test fails  
❌ Health checks failing  
❌ WebSocket disconnections  
❌ Data inconsistency across PCs  

---

## Phase 6 Exit Criteria

When all the following are satisfied, Phase 6 is COMPLETE:

```
[REQUIRED]
✅ All 24 integration tests PASS on deployed system
✅ Real-time leaderboard sync verified between PC-1 and PC-2
✅ 5 concurrent votes scenario tested successfully
✅ Health checks responding correctly on both PCs
✅ WebSocket communication confirmed working

[DESIRED]
✅ Database backups taken
✅ Performance metrics documented
✅ No memory leaks observed
✅ No CPU throttling issues
```

---

## Next: Phase 7

Once Phase 6 is complete and all success criteria met:

**Phase 7: Go/No-Go Decision**
- Final system validation
- Stakeholder review
- Production sign-off
- Launch decision

---

**Phase 6 Start Time**: 2026-03-27 17:00:00 UTC  
**Estimated Completion**: 2026-03-27 19:00:00 UTC  
**Status**: IN PROGRESS
