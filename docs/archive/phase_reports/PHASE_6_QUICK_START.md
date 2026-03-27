# PHASE 6: QUICK START CHECKLIST

**Status**: 🟡 IN PROGRESS  
**Estimated Time**: 2 hours  
**Goal**: Deploy to PC-2 with Supabase + verify real-time sync

---

## ✅ PREREQUISITES (Do These First)

### Step 1: Get Supabase Credentials (5 min)

1. **Go to**: https://supabase.com/dashboard
2. **Select Your Project** (or create one)
3. **Go to**: Settings → Database → Connection String
4. **Select**: "Connection pooler" (better for FastAPI)
5. **Copy** the full connection string

**Format**: 
```
postgresql+asyncpg://postgres.xxxxx:password@xxxxx.pooler.supabase.com:6543/postgres
```

**Keep this safe** ⚠️ This is your database credential!

---

### Step 2: Create .env File (3 min)

1. **Copy template**:
   ```bash
   cp E:\projects\ClipApp\.env.phase6 E:\projects\ClipApp\.env
   ```

2. **Edit `.env`** and fill in:
   ```
   DATABASE_URL=postgresql+asyncpg://postgres.your_project:your_pass@your_host.pooler.supabase.com:6543/postgres
   TEST_DATABASE_URL=(same as above)
   TWITCH_CLIENT_ID=your_value
   TWITCH_CLIENT_SECRET=your_value
   SECRET_KEY=generate_random_key
   ```

3. **Generate random SECRET_KEY**:
   ```bash
   python -c "import secrets; print(secrets.token_urlsafe(32))"
   # Paste the output into SECRET_KEY=
   ```

4. **Verify .env exists**:
   ```bash
   ls -la E:\projects\ClipApp\.env
   # Should show the file
   ```

---

### Step 3: Test Database Connection (2 min)

```bash
cd E:\projects\ClipApp

python -c "
import os
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import create_async_engine
import asyncio

load_dotenv()

async def test():
    db_url = os.getenv('DATABASE_URL')
    if not db_url:
        print('❌ DATABASE_URL not found in .env')
        return
    
    print(f'📍 Connecting to: {db_url[:50]}...')
    
    try:
        engine = create_async_engine(db_url, echo=False)
        async with engine.connect() as conn:
            result = await conn.execute('SELECT 1')
            print('✅ Database connection successful!')
        await engine.dispose()
    except Exception as e:
        print(f'❌ Connection failed: {e}')

asyncio.run(test())
"
```

**Expected Output**:
```
📍 Connecting to: postgresql+asyncpg://postgres.xxxxx...
✅ Database connection successful!
```

---

## 🚀 STEP BY STEP DEPLOYMENT

### STEP 1: Apply Database Migrations (2 min)

```bash
cd E:\projects\ClipApp

# Run all migrations
alembic upgrade head

# Expected:
# INFO  [alembic.runtime.migration] Running upgrade  -> 20260327_145359_fix_schema_foundation
# INFO  [alembic.runtime.migration] Running upgrade 20260327_145359_fix_schema_foundation -> 20260327_160000_add_leaderboard_tables
```

✅ **Check**: 9 tables should exist in Supabase now

---

### STEP 2: Run Full Test Suite (10 min) ⭐ CRITICAL

```bash
cd E:\projects\ClipApp

pytest tests/integration/ -v

# Expected: 24 passed
```

**If tests fail**:
- Check DATABASE_URL in .env is correct
- Run `pytest tests/integration/test_vote_endpoint.py::test_vote_like_increments_counter -v --tb=long`
- See TROUBLESHOOTING in Phase 6 guide

✅ **Success Criteria**: **All 24 tests PASS**

---

### STEP 3: Start Backend on PC-1 (Continuous)

**Terminal 1** on PC-1:
```bash
cd E:\projects\ClipApp

# Start FastAPI
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Expected:
# INFO:     Uvicorn running on http://0.0.0.0:8000
# INFO:     Application startup complete
```

✅ **Check**: `curl http://localhost:8000/api/v1/health`

---

### STEP 4: Start Frontend on PC-1 (Continuous)

**Terminal 2** on PC-1:
```bash
cd E:\projects\ClipApp\frontend

npm run dev

# Expected:
# ➜  Local:   http://localhost:5173/
```

✅ **Check**: http://localhost:5173 opens in browser

---

### STEP 5: Deploy to PC-2 (15 min)

**On PC-2**:

```bash
# 1. Clone repo (or get copy from PC-1)
git clone https://github.com/your-repo/ClipApp.git
cd ClipApp

# 2. Copy .env from PC-1 to PC-2 (SAME database URL)
# PC-1 → PC-2: Copy .env file

# 3. Install dependencies
uv sync
cd frontend && npm install && cd ..

# 4. Start backend on different port
uvicorn main:app --reload --host 0.0.0.0 --port 8001

# 5. In new terminal on PC-2, start frontend
cd frontend
npm run dev -- --port 5174
```

✅ **Check**: 
- PC-1: http://localhost:5173 (Backend: :8000)
- PC-2: http://localhost:5174 (Backend: :8001)

---

### STEP 6: Test Real-Time Sync (5 min) ⭐ CRITICAL

**Test 1: Vote on PC-1, See Update on PC-2**

1. **Open both browsers**:
   - PC-1: http://localhost:5173
   - PC-2: http://localhost:5174

2. **Submit vote on PC-1**: Click "Like" on top clip

3. **Watch PC-2**: Should see like counter increment in < 1 second

4. **Both should show same top 10** within 5 seconds

**Test 2: Five Concurrent Votes** ⭐ MOST CRITICAL

```bash
# On PC-1, run this while watching both UIs
for i in {1..5}; do
  curl -X POST http://localhost:8000/api/v1/votes/like/1
  echo "Vote $i sent"
done

# PC-2 should show like counter increment by 5
# Check database: Should have exactly 5 votes
```

✅ **Success**: 
- Both PCs show same data
- Vote count matches (5 votes = 5 increments)
- No race conditions

---

### STEP 7: Validate Health Checks (2 min)

```bash
# PC-1
curl http://localhost:8000/api/v1/health | python -m json.tool

# PC-2
curl http://localhost:8001/api/v1/health | python -m json.tool

# Expected: status = "ok"
```

---

## ✅ GO/NO-GO DECISION MATRIX

### GO (Proceed to Phase 7):
- [ ] ✅ All 24 tests PASS
- [ ] ✅ Both PCs showing real-time updates
- [ ] ✅ 5 concurrent votes test passes
- [ ] ✅ Health checks returning "ok"
- [ ] ✅ WebSocket connected on both PCs
- [ ] ✅ No database errors in logs

### NO-GO (Debug and Retry):
- [ ] ❌ Any test fails
- [ ] ❌ Real-time sync broken
- [ ] ❌ Concurrent votes race condition detected
- [ ] ❌ Health checks failing
- [ ] ❌ WebSocket errors in console

---

## 📋 QUICK REFERENCE

### Environment Variables Needed
```bash
DATABASE_URL        # Supabase connection string (REQUIRED)
TWITCH_CLIENT_ID    # For social login (optional for Phase 6)
SECRET_KEY          # Random 256-bit key (REQUIRED)
```

### Key Endpoints to Test
```bash
# Health checks
curl http://localhost:8000/api/v1/health
curl http://localhost:8001/api/v1/health

# Leaderboard
curl http://localhost:8000/api/v1/leaderboard/current

# Vote
curl -X POST http://localhost:8000/api/v1/votes/like/1
```

### WebSocket URLs
```
PC-1: ws://localhost:8000/ws/leaderboard
PC-2: ws://localhost:8001/ws/leaderboard
```

### Important Files
- `.env` - Configuration (KEEP PRIVATE)
- `main.py` - FastAPI entry point
- `alembic/versions/` - Database migrations
- `tests/integration/` - Test suite
- `PHASE_6_DEPLOYMENT_GUIDE.md` - Full guide

---

## 🆘 COMMON ISSUES

| Issue | Solution |
|-------|----------|
| `DATABASE_URL not found` | Copy `.env.phase6` to `.env` and fill in values |
| `connection timeout` | Check Supabase credentials, verify firewall allows port 6543 |
| Tests fail with no data | Run migrations: `alembic upgrade head` |
| Real-time sync not working | Check WebSocket connection in browser dev tools |
| Both PCs showing different data | Verify both use SAME DATABASE_URL |
| 5 concurrent votes fails | Check for race conditions in database logs |

---

## 🎯 SUCCESS METRICS

When Phase 6 is complete:

✅ **All 24 tests pass** (0 failures)  
✅ **Real-time leaderboard sync works** (< 1s latency)  
✅ **5 concurrent votes test passes** (no data loss)  
✅ **Health checks operational** (both PCs healthy)  
✅ **Cross-PC data consistency** (same top 10 on both)  

---

## Next Steps After Phase 6

Once GO criteria met:
1. Document final test results
2. Get stakeholder sign-off
3. Proceed to Phase 7: Production Go/No-Go
4. Deploy to production servers

---

**Ready to start? Begin with Prerequisites Step 1 above.**  
**Questions? Check PHASE_6_DEPLOYMENT_GUIDE.md for detailed instructions.**

**Phase 6 Status**: IN PROGRESS - Expected completion: 2 hours
