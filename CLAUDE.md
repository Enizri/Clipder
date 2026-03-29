# Clipder — Project Guide (CLAUDE.md)

> Single source of truth for architecture, conventions, and the active refactor plan.
> Every AI agent and human contributor must follow this document.

---
## Agent Persona:
You are a senior software architect with 20+ years of experience.
You write production-grade code, not tutorial code.
You always:
- Think about edge cases before writing
- Prefer simple solutions over clever ones
- Never leave broken or half-finished code
- Flag risks before implementing, don't just proceed
- Ask before making decisions that weren't explicitly planned
- add small comments to the code to explain the logic dont try to be clever just explain the logic

## 1. Project Overview

**Clipder** is a Twitch clip discovery and ranking platform. Users swipe through clips,
vote (like/dislike), and a real-time leaderboard tracks the top clips each month.

| Layer | Stack |
|-------|-------|
| Backend | FastAPI + Uvicorn (async), Python 3.12+ |
| Database | PostgreSQL (Supabase) via SQLAlchemy 2.0 async + asyncpg |
| Migrations | Alembic (async mode) |
| Auth | JWT (HS256) + Bcrypt, Twitch OAuth |
| Scheduling | APScheduler (AsyncIOScheduler) |
| Frontend | React 18 + TypeScript + Vite |
| Charting | Recharts |
| Routing | react-router-dom |
| Package Mgr | uv (Python), npm (Frontend) |

---

## 2. Directory Structure

```
ClipApp/
├── main.py                    # FastAPI entry point, router mounting, WebSocket, lifespan
├── pyproject.toml             # Python deps managed with uv
├── alembic.ini                # Migration config
├── AGENTS.md                  # Agent behavioral rules (immutable reference)
├── CLAUDE.md                  # THIS FILE — project guide
├── .env.example               # Required env vars template
├── .gitignore
├── LICENSE
├── README.md
│
├── alembic/
│   ├── env.py                 # Async migration runner
│   ├── script.py.mako
│   └── versions/              # Single consolidated migration
│
├── backend/
│   ├── __init__.py
│   ├── engine.py              # IMMUTABLE core engine (moved from root core.py)
│   │                          #   Config, TwitchClient, StateManager, GroqClient,
│   │                          #   VideoProcessor, YouTubeUploader, TikTokUploader
│   ├── api/
│   │   └── v1/
│   │       ├── __init__.py
│   │       ├── deps.py        # DI: get_db, get_current_user, check_pro, check_admin
│   │       └── endpoints/
│   │           ├── admin.py       # /api/v1/admin/*
│   │           ├── ai_chat.py     # /api/v1/ai/*
│   │           ├── ai_editor.py   # /api/v1/ai-editor/*
│   │           ├── auth.py        # /api/v1/auth/*
│   │           ├── clips.py       # /api/v1/clips/*
│   │           ├── following.py   # /api/v1/following/*
│   │           ├── health.py      # /api/v1/health/*
│   │           ├── leaderboard.py # /api/v1/leaderboard/*
│   │           └── votes.py       # /api/v1/votes/*
│   ├── core/
│   │   ├── config.py          # Pydantic Settings — ALL env vars live here
│   │   ├── security.py        # JWT + Bcrypt
│   │   ├── database.py        # Async engine + session (uses Settings)
│   │   ├── state.py           # ConnectionManager (WS) + AppState
│   │   ├── twitch_oauth.py    # Twitch OAuth helpers (async httpx)
│   │   ├── cache_provider.py  # LeaderboardCache ABC + DictLeaderboardCache
│   │   ├── tasks.py           # APScheduler background jobs
│   │   └── logger.py          # Logging config
│   ├── models/
│   │   ├── __init__.py        # Re-exports Base + all models
│   │   ├── user.py
│   │   ├── clip.py
│   │   ├── vote.py
│   │   ├── user_streamer.py
│   │   ├── user_clip_history.py
│   │   ├── clip_video_cache.py
│   │   ├── leaderboard_snapshot.py
│   │   └── leaderboard_monthly_summary.py
│   └── schemas/
│       ├── __init__.py
│       ├── auth.py
│       ├── clip.py
│       ├── clip_history.py
│       ├── admin.py
│       ├── leaderboard.py
│       └── vote.py
│
├── frontend/
│   ├── index.html
│   ├── package.json
│   ├── tsconfig.json
│   ├── vite.config.ts
│   ├── .env.example
│   └── src/
│       ├── main.tsx
│       ├── App.tsx             # BrowserRouter + layout + <Routes>
│       ├── index.css
│       ├── types.ts            # Single source of truth for TS interfaces
│       ├── utils/
│       │   └── followSearch.ts # For You: normalize query, prefix/substring filters
│       ├── api/
│       │   └── client.ts       # Typed API client, all paths /api/v1/*
│       ├── pages/
│       │   ├── SwipePage.tsx
│       │   ├── LeaderboardPage.tsx
│       │   ├── AnalyticsPage.tsx
│       │   ├── AiEditorPage.tsx
│       │   └── ProfilePage.tsx
│       ├── components/
│       │   ├── SwipeStack.tsx
│       │   ├── AuthModal.tsx
│       │   ├── ProfilePanel.tsx
│       │   ├── CommentsPanel.tsx
│       │   ├── TheaterMode.tsx
│       │   ├── EmotePicker.tsx
│       │   ├── ForYouChannelPicker.tsx  # Profile: portal typeahead follows + Twitch search
│       │   ├── CombinedFeedSearch.tsx  # Swipe: one search = feeds + channels (portal)
│       │   ├── AiEditor.tsx
│       │   ├── Leaderboard.tsx
│       │   ├── AnalyticsDashboard.tsx
│       │   └── AnalyticsDashboard.css
│       └── hooks/
│           └── useLeaderboard.ts
│
├── scripts/
│   ├── db_maintenance/
│   │   ├── clean_history.py
│   │   └── cleanup_db.py
│   └── db_setup/
│       ├── create_admin_user.py
│       └── create_tables.py
│
├── tests/
│   ├── conftest.py
│   ├── integration/
│   ├── manual/
│   └── unit/
│
├── clips_to_process/          # Queue directory (runtime)
└── processed_clips/           # Archive directory (runtime)
```

---

## 3. Coding Conventions

### 3.1 Python (PEP 8 + project rules)

**Import ordering** — three groups separated by blank lines:
1. Standard library (`os`, `json`, `typing`, `datetime`, `pathlib`)
2. Third-party (`fastapi`, `pydantic`, `sqlalchemy`, `httpx`)
3. Local (`from backend.core.config import get_settings`)

**Naming:**

| Element | Style | Example |
|---------|-------|---------|
| Modules | snake_case | `clips.py` |
| Classes | PascalCase | `ClipResponse` |
| Functions | snake_case | `get_clips` |
| Constants | UPPER_SNAKE | `API_TIMEOUT = 30` |
| Private | _prefix | `_refresh_token` |

**Type hints** — mandatory on all function parameters and return types.
Use `Optional[X]` (not `X | None`) for compatibility.

**Pydantic** — use v2 API exclusively:
- `model_validate()` not `.from_orm()`
- `model_dump()` not `.dict()`
- `model_config = ConfigDict(from_attributes=True)` not `class Config`

**SQLAlchemy** — use 2.0 declarative style exclusively:
- `Mapped[str]` + `mapped_column()` everywhere
- Never use legacy `Column()` API
- `lazy="select"` on relationships (never `"selectin"`)

**Async** — every FastAPI handler and DB call is `async def`.
Never use sync `requests` in async code; use `httpx.AsyncClient` instead.

**Docstrings** — required on public classes and non-obvious endpoints.
Use Google-style (Args/Returns/Raises).

### 3.2 TypeScript / React

- Strict TypeScript (`strict: true` in tsconfig)
- All API response types defined once in `types.ts`
- No `any` — use proper interfaces
- Components are functional with hooks
- No inline styles for reusable patterns — use CSS classes
- No `console.log` in production code (use conditional `import.meta.env.DEV` guard if needed)
- Proper error handling — never `.catch(() => {})` silently

### 3.3 Comments

Comments explain **why**, not **what**. Do not narrate obvious code.
No emoji in code comments. No commented-out dead code.

---

## 4. Centralized Configuration

**Rule: Every environment variable is accessed through the `Settings` class.**

No module may call `os.getenv()` or `os.environ` directly.
The single exception is `alembic/env.py` (runs outside the app lifecycle).

### Settings class (`backend/core/config.py`)

```python
class Settings(BaseSettings):
    model_config = ConfigDict(env_file=".env", extra="ignore")

    # Database
    database_url: str                              # REQUIRED — no default

    # Supabase
    supabase_url: str = ""
    supabase_anon_key: str = ""

    # JWT — no weak defaults; app must fail loudly if unset
    secret_key: str                                # REQUIRED
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 10080       # 7 days

    # Twitch OAuth
    twitch_client_id: str = ""
    twitch_client_secret: str = ""
    twitch_redirect_uri: str = "http://localhost:8000/api/v1/auth/twitch/callback"

    # Twitch content
    twitch_channels: str = ""                      # comma-separated
    twitch_categories: str = ""                    # comma-separated

    # Groq
    groq_api_key: str = ""

    # Opus Clip (optional)
    opus_clip_api_key: str = ""

    # CORS
    frontend_url: str = "http://localhost:3000"
```

Usage everywhere else:

```
from backend.core.config import get_settings

settings = get_settings()
url = settings.database_url
```

### Environment variables (`.env.example`)

| Variable | Required | Description |
|----------|----------|-------------|
| `DATABASE_URL` | Yes | `postgresql+asyncpg://user:pass@host:5432/dbname` |
| `SECRET_KEY` | Yes | Strong random string for JWT signing |
| `TWITCH_CLIENT_ID` | Yes | From Twitch Developer Console |
| `TWITCH_CLIENT_SECRET` | Yes | From Twitch Developer Console |
| `GROQ_API_KEY` | Yes | For transcription/AI chat |
| `TWITCH_CHANNELS` | Yes | Comma-separated channel names |
| `TWITCH_CATEGORIES` | Yes | Comma-separated category names |
| `FRONTEND_URL` | No | CORS origin (default `http://localhost:3000`) |
| `ALGORITHM` | No | JWT algorithm (default `HS256`) |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | No | JWT TTL (default `10080`) |
| `SUPABASE_URL` | No | Supabase project URL |
| `SUPABASE_ANON_KEY` | No | Supabase anon key |
| `OPUS_CLIP_API_KEY` | No | Opus Clip integration |
| `VITE_API_ORIGIN` | No | Frontend-only: backend origin for cross-origin dev |

---

## 5. API Standards

### 5.1 All routes under `/api/v1/`

Every router uses the prefix `/api/v1/<resource>`. No exceptions.

| Router | Prefix | Auth |
|--------|--------|------|
| auth | `/api/v1/auth` | Public (register/login), JWT (me/twitch) |
| clips | `/api/v1/clips` | Public read, JWT for actions |
| votes | `/api/v1/votes` | JWT required |
| leaderboard | `/api/v1/leaderboard` | Public read |
| admin | `/api/v1/admin` | JWT + ADMIN role required |
| following | `/api/v1/following` | JWT required |
| ai_chat | `/api/v1/ai` | JWT required |
| ai_editor | `/api/v1/ai-editor` | JWT required |
| health | `/api/v1/health` | Public |

WebSocket: `/ws/leaderboard` (optional token auth)

### 5.2 Response format

- Success: return Pydantic `response_model` directly
- Error: raise `HTTPException(status_code=..., detail="...")`
- Lists: return empty list `[]`, never `None`
- Not found: `404` with descriptive detail

### 5.3 Frontend API client

All calls go through `frontend/src/api/client.ts` which:
- Prepends `/api/v1` to all paths
- Attaches `Authorization: Bearer <token>` for authenticated routes
- Parses error `detail` from FastAPI responses
- Never swallows errors silently

**GET `/api/v1/clips` (swipe feed):**
- Query `exclude_clip_ids`: comma-separated Twitch clip IDs to omit (guest **seen** list from `localStorage`; capped server-side). When a JWT is present, the backend **union** this set with every Twitch ID the user has already **liked or disliked** (`votes` → `clips.twitch_clip_id`) so repeats do not reappear after refresh.
- `category` values other than `My Streamers` / `For You` are treated as a **Twitch game name** (e.g. Valorant). There is **no** fallback to generic “top clips this month” from Postgres, because `clips` rows are not tagged by game — that fallback used to show the wrong category.
- **`explore_category`**: only when `category=My Streamers`; selects which game’s clips to explore.
- **For You channel guard**: responses are filtered so each clip’s `channel` (broadcaster login) is in the current `include_in_for_you` set (case-insensitive). That removes stale cached rows from channels you just excluded.

### 5.4 Following, For You, and Twitch sync (agent reference)

**Model:** `UserStreamer` (`backend/models/user_streamer.py`) stores channels tied to the user. Column `include_in_for_you` controls whether that row’s channel is included in the **For You** clip feed (`PUT /api/v1/following/for-you` sets exactly which Twitch `streamer_id` values are on).

**Backend — shared sync helper** (`backend/api/v1/endpoints/following.py`):
- `sync_twitch_follows_for_user(db, user) -> int` — calls Helix for the user’s Twitch follows and inserts missing `UserStreamer` rows (`include_in_for_you=True`). Does **not** commit; caller commits. Idempotent on `streamer_id`.
- `POST /api/v1/following/sync` — runs the helper and commits; response `{ "status": "synced", "added": <int> }`.

**Backend — OAuth** (`backend/api/v1/endpoints/auth.py`):
- After Twitch `GET /api/v1/auth/twitch/callback` creates or updates the user and commits, the handler calls `sync_twitch_follows_for_user` in a **try/except**. On failure it logs, rolls back the sync attempt only, and **still** issues the JWT redirect so login succeeds.

**Backend — channel search** (`backend/core/twitch_oauth.py`):
- Helix `search/channels` URL must use `urllib.parse.quote` on the query string so spaces and special characters are valid.

**Frontend — search utilities** (`frontend/src/utils/followSearch.ts`):
- `normalizeFollowSearchQuery` — trim, lowercase, strip leading `@`.
- `filterFollowedStreamersByPrefix` — list filter: prefix match first, then substring fallback if no prefix hits.
- `suggestFollowedByPrefix` — prefix-only list (used for typeahead suggestions).

**Frontend — For You picker (Profile)** (`frontend/src/components/ForYouChannelPicker.tsx`):
- Typeahead for **For You**: combines **saved follows** (prefix suggestions from local list) with **debounced Twitch search** (`GET /following/search`, min query length 2) for channels not already in the list.
- Dropdown is rendered with **`createPortal(..., document.body)`** and a high z-index so parent layout (e.g. swipe sidebar `overflow`) does not clip it.
- Choosing a Twitch result: `POST /following`, then refresh list, then merge **`PUT /following/for-you`** using a **fresh `GET /following`** inside the page callback so selection state matches the DB (see `mergeForYouInclude` on `SwipePage` / `ProfilePage`).

**Frontend — UX**:
- **Profile** (`ProfilePage.tsx`): full follow list, For You checkboxes, Remove, **Refresh from Twitch**, and the same picker.
- **Swipe** (`SwipePage.tsx`): **CombinedFeedSearch** — one field opens a portal with **Feeds** (category tabs) plus **Your channels** / **Add from Twitch** when signed in; under **For You** the checkbox list + **Select all** remain; hints point users with no follows to search or Profile sync.

**Twitch OAuth scopes:** `get_authorization_url` in `twitch_oauth.py` currently requests `user:read:follows`. If Helix channel search fails with **401**, check Twitch’s current scope list and extend the authorization `scope` string and re-link flow if required.

---

## 6. Security Rules

1. **NEVER** read, display, or commit `.env` files
2. **NEVER** hardcode API keys, secrets, or credentials in source code
3. **CORS**: use `FRONTEND_URL` env var for allowed origins — never `*` in production
4. **JWT**: `SECRET_KEY` is required with no fallback default — app refuses to start without it
5. **Admin routes**: require `ADMIN` role via `check_admin` dependency
6. **AI endpoints**: require authenticated user to prevent abuse
7. **SQL**: use ORM / parameterized queries exclusively — no string concatenation
8. **Passwords**: bcrypt hashing via `backend/core/security.py`
9. **Async safety**: never use sync `requests` in async handlers — use `httpx.AsyncClient`
10. **WebSocket**: validate JWT token on connection when sensitive data is involved

---

## 7. Database Rules

- **ORM**: SQLAlchemy 2.0 declarative (`Mapped` / `mapped_column`) exclusively
- **Migrations**: Alembic async mode; one clean migration chain
- **Supabase pooler**: when `"pooler"` appears in URL, use `ssl=require` + `statement_cache_size=0`
- **Sessions**: async sessions via `get_db()` dependency injection
- **Relationships**: `lazy="select"` (load on access, not on every query)
- **IDs**: integer auto-increment primary keys
- **Timestamps**: `DateTime(timezone=True)` with `func.now()` server defaults

---

## 8. Immutable Engine (`backend/engine.py`)

This file (originally `core.py`) contains the algorithmic core:
`Config`, `TwitchClient`, `CaptionGenerator`, `GroqClient`, `VideoProcessor`,
`YouTubeUploader`, `TikTokUploader`, `StateManager`, `ClipBot`.

**DO NOT modify its logic or function signatures.**
It has its own `Config.from_env()` dataclass — that is the one exception to the
centralized Settings rule, because it predates the FastAPI backend.

The FastAPI `AppState` in `backend/core/state.py` wraps this engine and
bridges it to the async web layer.

---
**Documentation updates (ongoing):** §5.4 describes following sync, For You, `ForYouChannelPicker` (Profile), `CombinedFeedSearch` (Swipe), and `followSearch`; §2 directory tree and §10 Key Decisions include portal/merge/quote-query behavior.
---

## 10. Key Decisions (Locked)

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Database | Fresh consolidated migration | Supabase DB has no important data |
| Frontend routing | `react-router-dom` | Proper page-based navigation |
| Leaderboard hourly aggregates | Dropped | No model or code uses it |
| Giphy feature | Removed entirely | Hardcoded API key, low value |
| Env var access | Centralized `Settings` class | No scattered `os.getenv()` |
| `core.py` location | Moved to `backend/engine.py` | Clean project root |
| API prefix | All routes under `/api/v1/*` | Consistency |
| SQLAlchemy style | `Mapped` / `mapped_column` only | No legacy `Column` API |
| Sync HTTP calls | Replaced with `httpx` async | Never block the event loop |
| FastAPI route order | Static paths before dynamic `{param}` segments | Prevents path shadowing (e.g. `/clear-all` vs `/{id}`) |
| Auth guard list | `requiresAuth` in `client.ts` — include every authenticated prefix | Forgetting a prefix silently drops the JWT header |
| Twitch follows on login | `sync_twitch_follows_for_user` after OAuth callback + `POST /following/sync` | DB `user_streamers` reflects Twitch follows without a separate manual step |
| For You picker UI | `ForYouChannelPicker` + `createPortal` to `document.body` | Dropdown must not be clipped by swipe / overflow parents |
| For You + new follows | Merge via fresh `GET /following` before `PUT /following/for-you` | Avoids stale React state after `POST /following` |
| Helix channel search URL | `quote(query)` in `twitch_oauth.search_channels` | Valid requests for multi-word and special-character queries |
| Swipe feed clips | Twitch-by-game queues only + `exclude_clip_ids` / voted IDs | Game tabs must not fall back to untagged DB “top clips”; repeats excluded via votes + guest param |
| Swipe feed picker UI | `CombinedFeedSearch`: portal lists feeds + Twitch/follow typeahead; no duplicate channel field | One search bar; Profile still uses `ForYouChannelPicker` |

---

## 11. Build & Run

```bash
# Install Python deps
uv sync

# Install frontend deps
cd frontend && npm install

# Run backend (from project root)
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Run frontend (from frontend/)
npm run dev

# Run migrations
alembic upgrade head

# Run tests
pytest
```

### Adding dependencies

```bash
# Python — NEVER use pip
uv add <package>

# Frontend
cd frontend && npm install <package>
```
