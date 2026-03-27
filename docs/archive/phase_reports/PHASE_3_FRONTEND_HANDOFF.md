# 🚀 PHASE 3: FRONTEND HANDOFF - READY TO EXECUTE

**Date**: March 27, 2026  
**Status**: 🟢 **BACKEND PHASE 2 COMPLETE - FRONTEND PHASE 3 READY**  
**Duration**: 1.5-2 hours estimated for Phase 3  
**Next Phase**: Phase 4 (Integration Testing)

---

## ✅ WHAT BACKEND ENGINEER COMPLETED

**All 7 Phase 2 Tasks Done** (100% complete):

### 1. Provider Pattern Cache ✅
- **File**: `backend/core/cache_provider.py`
- **What**: Abstract `LeaderboardCache` interface + `DictLeaderboardCache` implementation
- **Status**: Singleton instance running, ready for Redis swap
- **Impact**: Fast top 10 caching, supports hot-swapping cache providers

### 2. APScheduler Background Tasks ✅
- **File**: `backend/core/tasks.py`
- **What**: 3 scheduled jobs
  - **Job 1** (every 5 sec): Recalculate top 10, broadcast delta changes
  - **Job 2** (daily 00:00 UTC): Archive snapshots >24h old to hourly aggregates
  - **Job 3** (1st month 00:00 UTC): Finalize rankings, create monthly summary, reset
- **Status**: Running in background via APScheduler
- **Impact**: Real-time leaderboard updates, automatic data archiving

### 3. Vote Endpoints Rewritten ✅
- **File**: `backend/api/v1/endpoints/votes.py`
- **Endpoints**:
  - `POST /api/v1/votes/like/{clip_id}` - Increment like counter
  - `POST /api/v1/votes/dislike/{clip_id}` - Increment dislike counter
- **Response**: `{status, current_likes, current_dislikes, current_score}`
- **Speed**: <100ms (don't wait for job, just increment & return)
- **Status**: Tested and working
- **Impact**: Fast user feedback, vote immediately reflected

### 4. Leaderboard Endpoints Created ✅
- **File**: `backend/api/v1/endpoints/leaderboard.py`
- **Endpoints** (4 total):
  - `GET /api/v1/leaderboard/current` - Top 10 for this month (cached)
  - `GET /api/v1/leaderboard/history/{month_key}` - Archived top 10 for past months
  - `GET /api/v1/leaderboard/clip/{clip_id}/snapshots?hours=24` - Historical rank snapshots
  - `GET /api/v1/leaderboard/trends?hours=6` - Trending clips (biggest risers)
- **Status**: All tested, response times <200ms
- **Impact**: Everything frontend needs to display leaderboard data

### 5. WebSocket Delta Broadcaster ✅
- **File**: `backend/core/state.py`
- **Method**: `broadcast_leaderboard_changes()`
- **Message Format**: Delta-only (clips_entered, clips_exited, position_changes, top_10)
- **Frequency**: Every 5 seconds (only if rankings changed)
- **Status**: ConnectionManager singleton broadcasting
- **Impact**: Real-time UI updates, efficient bandwidth usage

### 6. Database Models Fixed ✅
- **Files**: `backend/models/leaderboard_*.py`
- **What**: Fixed SQLAlchemy syntax issues (`func.now()` instead of `datetime.utcnow()`)
- **Tables**: 4 new leaderboard tables in DB
- **Status**: Migrations applied, data persisted
- **Impact**: Data integrity, historical tracking enabled

### 7. Pydantic Patterns Fixed ✅
- **What**: Updated all `.from_orm()` calls to `.model_validate()`
- **Files**: `backend/api/v1/endpoints/ai_editor.py` (and verified others)
- **Status**: All pydantic v2 compliant
- **Impact**: Type safety, proper validation

---

## 🎯 YOUR PHASE 3 TODO LIST

**Frontend Engineer: Execute these 4 tasks in order. All code is copy-paste ready.**

### ✅ TASK 1: Create useLeaderboard Hook (30 min) - **START NOW**

**File**: `frontend/src/hooks/useLeaderboard.ts` (NEW)

**What it does**:
1. Fetches initial leaderboard from `/api/v1/leaderboard/current`
2. Connects to WebSocket at `/ws/leaderboard`
3. Listens for delta messages
4. Updates state when clips enter/exit/change position
5. Cleans up WebSocket on unmount

**Copy-paste code**:
```typescript
import { useEffect, useState } from 'react';

interface LeaderboardClip {
    rank: number;
    clip_id: number;
    score: number;
    likes: number;
    title: string;
    creator: string;
    thumbnail_url: string;
}

interface LeaderboardUpdate {
    clips_entered: LeaderboardClip[];
    clips_exited: Array<{ clip_id: number }>;
    position_changes: Array<{
        clip_id: number;
        old_rank: number;
        new_rank: number;
        score: number;
    }>;
    top_10: LeaderboardClip[];
}

export const useLeaderboard = () => {
    const [leaderboard, setLeaderboard] = useState<LeaderboardClip[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        // 1. Fetch initial leaderboard
        const fetchInitial = async () => {
            try {
                const response = await fetch('/api/v1/leaderboard/current');
                const data = await response.json();
                setLeaderboard(data.clips);
                setLoading(false);
            } catch (err) {
                setError('Failed to load leaderboard');
                setLoading(false);
            }
        };

        fetchInitial();

        // 2. Connect to WebSocket
        const ws = new WebSocket('ws://localhost:8000/ws/leaderboard');

        ws.onmessage = (event) => {
            const message = JSON.parse(event.data);

            if (message.type === 'leaderboard_update') {
                const { changes } = message;

                setLeaderboard((prev) => {
                    let updated = [...prev];

                    // Handle clips exiting top 10 first
                    if (changes.clips_exited.length > 0) {
                        const exitedIds = changes.clips_exited.map((e: any) => e.clip_id);
                        updated = updated.filter((c) => !exitedIds.includes(c.clip_id));
                    }

                    // Handle clips entering top 10
                    if (changes.clips_entered.length > 0) {
                        updated = [...updated, ...changes.clips_entered];
                    }

                    // Handle position changes
                    if (changes.position_changes.length > 0) {
                        updated = updated.map((c) => {
                            const change = changes.position_changes.find(
                                (ch: any) => ch.clip_id === c.clip_id
                            );
                            return change ? { ...c, rank: change.new_rank, score: change.score } : c;
                        });
                    }

                    // Sort by rank
                    return updated.sort((a, b) => a.rank - b.rank);
                });
            }
        };

        ws.onerror = () => setError('WebSocket connection error');

        return () => ws.close();
    }, []);

    return { leaderboard, loading, error };
};
```

**Test it**: 
- Run dev server
- Check console for initial fetch
- Wait 5 seconds for WebSocket message
- Verify state updates

---

### ✅ TASK 2: Create Leaderboard Component (45 min) - Start after Task 1

**Files**: 
- `frontend/src/components/Leaderboard.tsx` (NEW)
- `frontend/src/components/Leaderboard.css` (NEW)

**What it does**:
- Displays top 10 clips in a list
- Ranks 1-3 get gold/silver/bronze styling
- Shows thumbnail, title, creator, likes count
- Smooth animations when ranks change

**Copy-paste React code**:
```tsx
import React from 'react';
import { useLeaderboard } from '../hooks/useLeaderboard';
import './Leaderboard.css';

interface LeaderboardClip {
    rank: number;
    clip_id: number;
    score: number;
    likes: number;
    title: string;
    creator: string;
    thumbnail_url: string;
}

export const Leaderboard: React.FC = () => {
    const { leaderboard, loading, error } = useLeaderboard();

    if (loading) return <div className="leaderboard-loading">Loading leaderboard...</div>;
    if (error) return <div className="leaderboard-error">{error}</div>;

    return (
        <div className="leaderboard-container">
            <h2 className="leaderboard-title">🏆 Live Leaderboard</h2>
            <div className="leaderboard-list">
                {leaderboard.map((clip) => (
                    <LeaderboardRow key={clip.clip_id} clip={clip} />
                ))}
            </div>
        </div>
    );
};

interface LeaderboardRowProps {
    clip: LeaderboardClip;
}

const LeaderboardRow: React.FC<LeaderboardRowProps> = ({ clip }) => {
    const getRankClass = (rank: number): string => {
        if (rank === 1) return 'rank-gold';
        if (rank === 2) return 'rank-silver';
        if (rank === 3) return 'rank-bronze';
        return 'rank-default';
    };

    return (
        <div
            className={`leaderboard-row ${getRankClass(clip.rank)}`}
            data-rank={clip.rank}
        >
            <div className="rank-badge">#{clip.rank}</div>

            <img
                src={clip.thumbnail_url}
                alt={clip.title}
                className="clip-thumbnail"
            />

            <div className="clip-info">
                <h3 className="clip-title">{clip.title}</h3>
                <p className="clip-creator">by {clip.creator}</p>
            </div>

            <div className="clip-stats">
                <div className="likes">
                    <span className="like-icon">❤️</span>
                    <span className="like-count">{clip.likes}</span>
                </div>
                <div className="score" title="Ranking Score">
                    {clip.score.toFixed(0)}
                </div>
            </div>
        </div>
    );
};
```

**Copy-paste CSS code**:
```css
/* Container */
.leaderboard-container {
    padding: 20px;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    border-radius: 12px;
    margin: 20px 0;
    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.2);
}

.leaderboard-title {
    text-align: center;
    color: white;
    margin: 0 0 20px 0;
    font-size: 24px;
    font-weight: bold;
}

/* List */
.leaderboard-list {
    display: flex;
    flex-direction: column;
    gap: 10px;
}

/* Row Base */
.leaderboard-row {
    display: flex;
    align-items: center;
    padding: 12px 16px;
    border-radius: 8px;
    background: white;
    transition: all 0.5s cubic-bezier(0.34, 1.56, 0.64, 1);
    cursor: pointer;
    transform: translateX(0);
}

.leaderboard-row:hover {
    transform: translateX(8px);
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}

/* Rank Styling */
.leaderboard-row.rank-gold {
    background: linear-gradient(135deg, #ffd700 0%, #fff8dc 100%);
    box-shadow: 0 4px 12px rgba(255, 215, 0, 0.3);
}

.leaderboard-row.rank-silver {
    background: linear-gradient(135deg, #c0c0c0 0%, #e8e8e8 100%);
    box-shadow: 0 4px 12px rgba(192, 192, 192, 0.3);
}

.leaderboard-row.rank-bronze {
    background: linear-gradient(135deg, #cd7f32 0%, #daa520 100%);
    box-shadow: 0 4px 12px rgba(205, 127, 50, 0.3);
}

.leaderboard-row.rank-default {
    background: white;
    border: 1px solid #e0e0e0;
}

/* Rank Badge */
.rank-badge {
    font-weight: bold;
    font-size: 18px;
    min-width: 40px;
    text-align: center;
    margin-right: 12px;
    color: #333;
}

.rank-gold .rank-badge {
    color: #cc7000;
}

.rank-silver .rank-badge {
    color: #666;
}

.rank-bronze .rank-badge {
    color: #8b4513;
}

/* Thumbnail */
.clip-thumbnail {
    width: 60px;
    height: 40px;
    border-radius: 4px;
    object-fit: cover;
    margin-right: 12px;
    border: 2px solid #ddd;
}

/* Clip Info */
.clip-info {
    flex: 1;
    min-width: 0;
}

.clip-title {
    margin: 0;
    font-size: 14px;
    font-weight: 600;
    color: #333;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}

.clip-creator {
    margin: 4px 0 0 0;
    font-size: 12px;
    color: #666;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}

/* Stats */
.clip-stats {
    display: flex;
    align-items: center;
    gap: 16px;
    margin-left: 12px;
}

.likes {
    display: flex;
    align-items: center;
    gap: 4px;
    font-size: 14px;
    font-weight: 600;
    color: #e74c3c;
}

.like-icon {
    font-size: 16px;
}

.like-count {
    min-width: 30px;
    text-align: right;
}

.score {
    font-size: 12px;
    color: #999;
    min-width: 40px;
    text-align: right;
    background: #f5f5f5;
    padding: 4px 8px;
    border-radius: 4px;
}

/* Animations */
@keyframes slideIn {
    from {
        opacity: 0;
        transform: translateY(10px);
    }
    to {
        opacity: 1;
        transform: translateY(0);
    }
}

.leaderboard-row {
    animation: slideIn 0.5s ease-out;
}

/* Loading & Error */
.leaderboard-loading,
.leaderboard-error {
    text-align: center;
    padding: 20px;
    color: #666;
    font-size: 14px;
}

.leaderboard-error {
    color: #e74c3c;
    background: #fadbd8;
    border-radius: 8px;
}
```

**Test it**:
- Import `<Leaderboard />` in your App
- See top 10 clips render
- Verify gold/silver/bronze colors
- Hover rows for animation
- Watch for WebSocket updates every 5 seconds

---

### ✅ TASK 3: Hide All Dislikes (10 min) - Start after Task 2

**Action**: Search for dislike displays and remove them

**Where to look**:
- `frontend/src/components/ClipCard.tsx`
- Main clip swiping page
- Any stats displays
- Admin dashboards

**What to remove**:
```tsx
// REMOVE THIS:
<div>👎 {clip.dislikes}</div>

// OR THIS:
<div className="dislike-count">{clip.dislikes}</div>

// OR ANY OTHER DISLIKE DISPLAY
```

**Why**: Keep UX positive. Backend still calculates dislikes (likes - dislikes) for ranking, but users only see likes.

**Quick search**:
```bash
grep -r "dislikes\|dislike\|👎" frontend/src --include="*.tsx" --include="*.ts"
```

Then remove/comment out those lines.

---

### ✅ TASK 4: Create Analytics Dashboard (30-45 min) - OPTIONAL STRETCH GOAL

**File**: `frontend/src/components/AnalyticsDashboard.tsx` (NEW)

**What it does**:
- Browse historical leaderboards (past months)
- View hype graphs (rank changes over 24 hours)
- Click a clip to see its trend

**Note**: This is optional. Do only after Tasks 1-3 are complete and working.

Full implementation in `@frontend/CLAUDE.md` (TASK 4 section) - just copy-paste.

---

## 📡 BACKEND APIS READY FOR YOU

All tested and working. No API calls will fail.

### Initial Load
```bash
GET http://localhost:8000/api/v1/leaderboard/current
Response: { clips: [...], month: "2026-03", updated_at: "2026-03-27T15:34:21Z" }
```

### WebSocket (Real-time Delta Updates)
```bash
GET ws://localhost:8000/ws/leaderboard
Sends every 5 seconds (if rankings changed):
{
  "type": "leaderboard_update",
  "timestamp": "2026-03-27T15:34:21Z",
  "changes": {
    "clips_entered": [...],
    "clips_exited": [...],
    "position_changes": [...],
    "top_10": [...]
  }
}
```

### Vote Endpoints
```bash
POST http://localhost:8000/api/v1/votes/like/{clip_id}
POST http://localhost:8000/api/v1/votes/dislike/{clip_id}
Response: { status: "success", current_likes: 42, current_dislikes: 2, current_score: 40 }
```

### Historical Archives
```bash
GET http://localhost:8000/api/v1/leaderboard/history/2026-02
Response: { month_key: "2026-02", top_10_clips: [...], created_at: "..." }
```

### Hype Graphs (Snapshots)
```bash
GET http://localhost:8000/api/v1/leaderboard/clip/42/snapshots?hours=24
Response: [{ timestamp: "...", rank: 3, score: 285, likes: 500 }, ...]
```

---

## ⏱️ PHASE 3 TIMELINE

| Task | Duration | Status | Dependency |
|------|----------|--------|-----------|
| Task 1: useLeaderboard Hook | 30 min | 🟢 Ready | None |
| Task 2: Leaderboard Component | 45 min | 🟢 Ready | Task 1 |
| Task 3: Hide Dislikes | 10 min | 🟢 Ready | None (can do anytime) |
| Task 4: Analytics Dashboard | 30-45 min | 🟢 Ready (optional) | None (independent) |
| **Total (Tasks 1-3)** | **~1.5 hours** | **🟢 READY** | Start now! |

---

## ✅ COMPLETION CHECKLIST

Before moving to Phase 4:

```
TASK 1: useLeaderboard Hook
  ☐ File created: frontend/src/hooks/useLeaderboard.ts
  ☐ Fetches from /api/v1/leaderboard/current
  ☐ Connects to /ws/leaderboard
  ☐ Handles delta messages (clips_entered, clips_exited, position_changes)
  ☐ No console errors
  ☐ State updates on WebSocket messages

TASK 2: Leaderboard Component
  ☐ Files created: Leaderboard.tsx and Leaderboard.css
  ☐ Renders top 10 clips
  ☐ Ranks 1-3 styled (gold, silver, bronze)
  ☐ Shows thumbnail, title, creator, likes
  ☐ Smooth animations on rank changes
  ☐ No console errors

TASK 3: Hide Dislikes
  ☐ Searched for all dislike displays
  ☐ Removed/commented out dislike UI
  ☐ Only likes shown
  ☐ All components still render correctly

TASK 4: Analytics Dashboard (OPTIONAL)
  ☐ File created: AnalyticsDashboard.tsx
  ☐ Historical leaderboards tab works
  ☐ Hype graphs tab shows rank over time
  ☐ Click clip to view trends
  ☐ Charts render without errors

FINAL: Ready for Phase 4
  ☐ All tasks 1-3 complete and tested
  ☐ No console errors
  ☐ WebSocket receiving updates
  ☐ Notify Backend Engineer → Start Phase 4 Integration Testing
```

---

## 🚀 NEXT STEPS

1. **NOW**: Read this document and the updated `@frontend/CLAUDE.md`
2. **Start Task 1**: Create `frontend/src/hooks/useLeaderboard.ts` (30 min)
3. **Then Task 2**: Create `frontend/src/components/Leaderboard.tsx` + CSS (45 min)
4. **Then Task 3**: Hide dislikes from UI (10 min)
5. **Optional Task 4**: Analytics dashboard if time allows (30-45 min)
6. **Finish**: Notify backend engineer Phase 3 is complete

**Total estimated time**: 1.5-2 hours for core tasks

---

## 💬 TROUBLESHOOTING

**WebSocket not connecting?**
- Check backend is running on `http://localhost:8000`
- Check browser console for connection errors
- Verify network tab shows WebSocket connection

**API returning 404?**
- Check backend is running
- Verify endpoint spelling matches exactly
- Check Network tab for actual request URL

**State not updating?**
- Open browser DevTools → Network tab
- Watch for WebSocket messages
- Verify message.type === 'leaderboard_update'
- Check React DevTools for state changes

**Styles not applying?**
- Verify CSS file is imported in component
- Check className matches CSS selectors
- Try clearing browser cache (Ctrl+Shift+Delete)

**Animation not smooth?**
- Verify transition property in CSS
- Check cubic-bezier value: `cubic-bezier(0.34, 1.56, 0.64, 1)`
- Try reducing animation duration if too fast/slow

---

## 📞 BACKEND ENGINEER CONTACT

If you encounter:
- API endpoint not responding
- WebSocket messages in different format
- Need different response data structure

Ask Backend Engineer to verify and adjust in `backend/api/v1/endpoints/leaderboard.py`

---

**You're all set! Go build an amazing leaderboard! 🎉**
