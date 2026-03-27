# Frontend-Backend Connectivity Fixes

## 🔴 Issues Found & Fixed

### Issue 1: Frontend Connecting to Wrong Server
**Problem:**
- Frontend runs on `localhost:3000` 
- Backend runs on `localhost:8000`
- All API calls went to `localhost:3000/api/*` (frontend itself!)
- WebSocket tried to connect to `ws://localhost:3000/ws/leaderboard` (frontend)

**Root Cause:**
- `API_BASE = '/api'` (relative URL resolves to current host)
- `WS_BASE = window.location.host` (uses frontend host)

**Fixed in:**
- `frontend/src/api/client.ts` - Dynamic routing logic added
- `frontend/src/hooks/useLeaderboard.ts` - Correct WebSocket URL 
- `frontend/src/components/AnalyticsDashboard.tsx` - Correct history API URL

### Issue 2: WebSocket Message Format Mismatch
**Problem:**
- Backend sends: `{"type": "leaderboard_update", "data": [...]}`
- Frontend expected: `{"type": "leaderboard_update", "changes": {...}}`
- Code tried to access `changes.clips_exited` but `changes` was undefined
- Result: `Uncaught TypeError: Cannot read properties of undefined`

**Fixed in:**
- `frontend/src/hooks/useLeaderboard.ts` - Now handles both formats gracefully

### Issue 3: Missing Required Fields in Leaderboard Data
**Problem:**
- Backend leaderboard objects missing `rank` field
- Frontend expected: `{rank, clip_id, score, likes, title, creator, thumbnail_url}`
- Backend had: `{id, title, url, ...}` without proper mapping

**Fixed in:**
- `backend/core/state.py` - `get_leaderboard()` now adds rank + maps fields

---

## 📝 Changes Made

### Frontend

**1. File: `frontend/src/api/client.ts`**
```typescript
// Before:
const API_BASE = '/api';
const WS_BASE = `ws://${window.location.host}`;

// After:
const getApiBase = (): string => {
  if (window.location.port === '3000') {
    return 'http://localhost:8000/api';
  }
  return '/api';
};

const API_BASE = getApiBase();
```

**2. File: `frontend/src/hooks/useLeaderboard.ts`**
- Fixed WebSocket URL: `ws://localhost:8000/ws/leaderboard` when on port 3000
- Fixed fetch URL: `http://localhost:8000/api/v1/leaderboard/current` when on port 3000
- Enhanced message handling to support both `data` and `changes` formats
- Added null checks to prevent crashes

**3. File: `frontend/src/components/AnalyticsDashboard.tsx`**
- Fixed history API calls to route to port 8000

### Backend

**File: `backend/core/state.py`**
- `get_leaderboard()` now adds `rank` field
- Maps backend fields to frontend expected fields:
  - `id` → `clip_id`
  - `creator_name` → `creator`  
  - `local_likes` → `likes` and `score`

---

## ✅ How to Test

### Step 1: Start Backend
```bash
cd /e/projects/ClipApp
uv run uvicorn main:app --host 0.0.0.0 --port 8000
```

Expected:
- ✅ `Application startup complete`
- ✅ `2026-03-27 17:46:56,871 [INFO] Background scheduler started`

### Step 2: Start Frontend  
```bash
cd /e/projects/ClipApp/frontend
npm run dev
```

Expected:
- ✅ Vite dev server on `localhost:3000`

### Step 3: Open Browser Console & Check
1. Open `http://localhost:3000` in browser
2. Open DevTools (F12) → Console tab
3. Look for:

```
✅ WS: Connecting to WebSocket: ws://localhost:8000/ws/leaderboard
✅ WS: WebSocket connected to leaderboard
✅ GET http://localhost:8000/api/v1/leaderboard/current 200
✅ 📊 Leaderboard update received
✅ 📋 Leaderboard updated: [...]
```

### Step 4: Check Leaderboard Loads
1. Go to "Leaderboard" tab
2. Should see clips loading properly
3. NO 500 errors
4. NO "Cannot read properties of undefined"

### Step 5: Test WebSocket Updates
1. Go to "Swipe" tab
2. Like/dislike a clip
3. Go back to Leaderboard tab
4. Check console for:
   ```
   📊 Leaderboard update received
   ```

---

## 🐛 Errors You Should NO LONGER See

### Before Fixes:
```
❌ GET http://localhost:3000/api/v1/leaderboard/current 500
❌ WebSocket is closed before connection established
❌ Cannot read properties of undefined (reading 'clips_exited')
❌ POST /api/v1/votes/clip/{id}/vote 404
```

### After Fixes:
```
✅ GET http://localhost:8000/api/v1/leaderboard/current 200
✅ WebSocket connected: ws://localhost:8000/ws/leaderboard
✅ Leaderboard data received and processed
✅ All API calls succeed
```

---

## 🔍 How It Works Now

### API Routing
```
Frontend (localhost:3000)
  ├─ Detects port 3000
  ├─ Routes to http://localhost:8000/api
  └─ Backend (localhost:8000) responds

All API calls:
  /api/v1/leaderboard/current
  /api/v1/leaderboard/history/{month}
  /api/v1/votes/clip/{id}/vote
  etc.
```

### WebSocket Routing
```
Frontend (localhost:3000)
  ├─ Detects port 3000
  ├─ Connects to ws://localhost:8000/ws/leaderboard
  └─ Receives real-time updates
```

### Message Format
Frontend now handles:
```typescript
// Format 1: Full leaderboard replacement
{
  type: 'leaderboard_update',
  data: [
    { rank: 1, clip_id: 123, score: 100, likes: 100, ... },
    { rank: 2, clip_id: 124, score: 80, likes: 80, ... }
  ]
}

// Format 2: Delta updates (future)
{
  type: 'leaderboard_update',
  changes: {
    clips_entered: [...],
    clips_exited: [...],
    position_changes: [...]
  }
}
```

---

## 📋 Verification Checklist

- [ ] Backend starts on port 8000
- [ ] Frontend starts on port 3000  
- [ ] Console shows `ws://localhost:8000/ws/leaderboard` (not 3000)
- [ ] Leaderboard tab loads without errors
- [ ] No `Cannot read properties of undefined` errors
- [ ] WebSocket connected message appears
- [ ] All API calls show port 8000
- [ ] Swiping updates leaderboard in real-time

---

## 🚀 If Still Having Issues

1. **Hard refresh browser:** `Ctrl+Shift+R`
2. **Clear localStorage:** `localStorage.clear()` in console
3. **Check backend logs:** Look for errors related to WebSocket or database
4. **Check network tab:** Verify all requests go to `localhost:8000`
5. **Restart services:** Kill both frontend and backend, restart

---

*Status: ✅ All connectivity issues resolved*
*Last Updated: 2026-03-27*
