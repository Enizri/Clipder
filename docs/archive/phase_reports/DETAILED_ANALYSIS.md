# ClipApp Database Analysis - Detailed Reference

## Quick Summary

| Category | Issues | Severity |
|----------|--------|----------|
| Schema Mismatches | 4 | CRITICAL |
| Performance | 4 | HIGH |
| Data Integrity | 2 | HIGH |
| Code Quality | 2 | MEDIUM |
| **TOTAL** | **12** | |

---

## CRITICAL ISSUES WITH LINE REFERENCES

### 1. TABLE NAMING MISMATCH

**File:** `alembic/versions/b7f027ceb621_initial_migration.py`

| Table | Model Expects | Migration Creates | Line | Status |
|-------|---------------|-------------------|------|--------|
| clips | `clips` | `clip` | 45 | ✗ MISMATCH |
| votes | `votes` | `vote` | 64 | ✗ MISMATCH |
| user_streamers | `user_streamers` | `user_streamer` | 78 | ✗ MISMATCH |

**Model References:**
- `backend/models/clip.py` line 14: `__tablename__ = "clips"`
- `backend/models/vote.py` line 22: `__tablename__ = "votes"`
- `backend/models/user_streamer.py` line 14: `__tablename__ = "user_streamers"`

**Impact:** ORM queries will execute `SELECT * FROM clips` but table is named `clip`.

---

### 2. ID COLUMN TYPE MISMATCH

**Files Involved:**

#### Model Definitions:
```
backend/models/clip.py:16
  id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

backend/models/vote.py:24
  id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

backend/models/user_streamer.py:16
  id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
```

#### Migration Definitions:
```
alembic/versions/b7f027ceb621_initial_migration.py

Line 46:  sa.Column('id', sa.String(), nullable=False),       # for 'clip' table
Line 65:  sa.Column('id', sa.String(), nullable=False),       # for 'vote' table
Line 79:  sa.Column('id', sa.String(), nullable=False),       # for 'user_streamer'
```

**Impact:** Foreign key from votes.clip_id (String) → clips.id (should be Integer).

---

### 3. FOREIGN KEY TYPE MISMATCH

**File:** `alembic/versions/b7f027ceb621_initial_migration.py`

**Lines 70-71:**
```python
sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
sa.ForeignKeyConstraint(['clip_id'], ['clip.id'], ),
```

**Problem:**
- `votes.clip_id` is created as String (line 67)
- `clip.id` is also String (line 46)
- But model expects `votes.clip_id` to be Integer referencing Integer `clips.id`

**Result:** FK constraint creates String→String, but should be Integer→Integer.

---

### 4. MISSING COLUMNS IN USER_STREAMER

**Model Definition:** `backend/models/user_streamer.py`

Lines 20-23:
```python
streamer_name: Mapped[str] = mapped_column(String(100), nullable=False)
streamer_id: Mapped[str] = mapped_column(String(50), nullable=False)
added_at: Mapped[datetime] = mapped_column(
    DateTime, default=datetime.utcnow, nullable=False
)
```

**Migration Definition:** `alembic/versions/b7f027ceb621_initial_migration.py` Line 77-86

```python
op.create_table(
    'user_streamer',
    sa.Column('id', sa.String(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('streamer_name', sa.String(), nullable=False),
    sa.Column('twitch_channel_id', sa.String(), nullable=True),  # WRONG NAME
    sa.Column('created_at', sa.DateTime(), nullable=False),      # WRONG NAME
    ...
)
```

**Missing:**
- `streamer_id` column (model line 21)
- `added_at` column (model line 22)

**Orphaned:**
- `twitch_channel_id` (should be `streamer_id`)
- `created_at` (should be `added_at`)

---

### 5. DEPRECATED PYDANTIC PATTERN

**File:** `backend/api/v1/endpoints/ai_editor.py`

**Line 54:**
```python
return ClipHistoryResponse.from_orm(history_entry)
```

**Line 77:**
```python
history=[ClipHistoryResponse.from_orm(entry) for entry in history_entries],
```

**Issue:** `.from_orm()` deprecated in Pydantic v2. Should use `.model_validate()`.

**Fix:**
```python
return ClipHistoryResponse.model_validate(history_entry)
history=[ClipHistoryResponse.model_validate(entry) for entry in history_entries]
```

---

### 6. MISSING UNIQUE CONSTRAINT

**Table:** `votes`  
**File:** `alembic/versions/b7f027ceb621_initial_migration.py` Lines 63-73

**Current:**
```python
op.create_table(
    'vote',
    sa.Column('id', sa.String(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('clip_id', sa.String(), nullable=False),
    sa.Column('vote_type', sa.String(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.ForeignKeyConstraint(['clip_id'], ['clip.id'], ),
    sa.PrimaryKeyConstraint('id')
    # MISSING: UniqueConstraint on user_id + clip_id
)
```

**Fix:**
```python
sa.UniqueConstraint('user_id', 'clip_id', name='unique_user_clip_vote')
```

---

## PERFORMANCE ISSUES WITH LINE REFERENCES

### 7. N+1 QUERY PROBLEM

**File:** `backend/api/v1/endpoints/following.py`  
**Lines:** 146-180 (`sync_with_twitch` endpoint)

**Current Code:**
```python
# Line 158-161: Get Twitch follows
follows = twitch_oauth.get_user_follows(
    current_user.twitch_access_token,
    current_user.twitch_id,
)

# Lines 164-178: LOOP WITH QUERY PER ITEM
added = 0
for follow in follows:
    existing = await db.execute(
        select(UserStreamer).where(
            UserStreamer.user_id == current_user.id,
            UserStreamer.streamer_id == follow["to_id"],
        )
    )
    if not existing.scalar_one_or_none():
        streamer = UserStreamer(
            user_id=current_user.id,
            streamer_name=follow["to_name"],
            streamer_id=follow["to_id"],
        )
        db.add(streamer)
        added += 1
```

**Problem:** If 100 follows, executes 100 queries.

**Optimized:**
```python
# Fetch all at once
existing_ids = await db.execute(
    select(UserStreamer.streamer_id).where(
        UserStreamer.user_id == current_user.id,
        UserStreamer.streamer_id.in_([f["to_id"] for f in follows])
    )
)
existing_set = set(row[0] for row in existing_ids)

# Loop without queries
for follow in follows:
    if follow["to_id"] not in existing_set:
        streamer = UserStreamer(...)
        db.add(streamer)
        added += 1
```

**Impact:** Reduces 100 queries to 2 queries (100x improvement).

---

### 8. MISSING INDEXES

**File:** `alembic/versions/b7f027ceb621_initial_migration.py`

**Current (lines 73-74):**
```python
op.create_index(op.f('ix_vote_id'), 'vote', ['id'], unique=False)
# MISSING indexes for user_id and clip_id!
```

**Needed Indexes:**
```python
op.create_index('ix_votes_user_id', 'votes', ['user_id'])
op.create_index('ix_votes_clip_id', 'votes', ['clip_id'])
op.create_index('ix_votes_user_clip', 'votes', ['user_id', 'clip_id'], unique=True)
op.create_index('ix_user_streamers_user_id', 'user_streamers', ['user_id'])
```

**Affected Queries:**

1. **votes.py line 57-59** (Query user's vote)
   ```python
   existing_vote = await db.execute(
       select(Vote).where(Vote.user_id == current_user.id, Vote.clip_id == clip.id)
   )
   ```
   Needs: `ix_votes_user_id` or `ix_votes_user_clip`

2. **following.py line 49-53** (Get user's streamers)
   ```python
   result = await db.execute(
       select(UserStreamer).where(UserStreamer.user_id == current_user.id)
   )
   ```
   Needs: `ix_user_streamers_user_id`

3. **ai_editor.py line 95-99** (Delete by clip_id + user)
   ```python
   result = await db.execute(
       select(UserClipHistory).where(
           (UserClipHistory.clip_id == clip_id) & 
           (UserClipHistory.user_id == current_user.id)
       )
   )
   ```
   Needs: Composite index `ix_user_clip_history_user_clip`

---

### 9. INEFFICIENT VOTE COUNTING

**File:** `backend/api/v1/endpoints/votes.py`  
**Lines:** 80-85

```python
likes_count = await db.execute(
    select(func.count(Vote.id)).where(
        Vote.clip_id == clip.id, Vote.vote_type == VoteType.LIKE
    )
)
current_score = likes_count.scalar() or 0
```

**Issues:**
1. No index on `Vote.vote_type`
2. Counts all votes, then filters
3. Called on every vote action

**Optimization:** Partial index
```python
CREATE INDEX idx_votes_likes ON votes(clip_id) WHERE vote_type = 'like';
```

---

### 10. DUAL DATA SOURCE

**File:** `backend/core/state.py`  
**Lines:** 69-74
