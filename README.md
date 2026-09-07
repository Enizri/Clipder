# Clipder

Clipder is a Twitch clip discovery and curation app. Browse moments from your
favorite streamers and game categories, swipe to vote, and save the clips you
want to work with. A monthly leaderboard tracks community favorites, while the
Playground helps you review saved clips and prepare titles and descriptions
for YouTube Shorts and TikTok.

![Clipder demo: swipe a Twitch clip, open the Playground queue, analyze, and mark it for export](docs/screenshots/clipder-demo.gif)

![Python](https://img.shields.io/badge/Python-3.12+-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.135+-green.svg)
![React](https://img.shields.io/badge/React-18-61dafb.svg)
![TypeScript](https://img.shields.io/badge/TypeScript-5-blue.svg)

## The clip workflow

1. **Discover** — Browse Twitch clips by category or choose followed channels for your For You feed.
2. **Watch and vote** — Preview a clip, open theater mode, and swipe right to like it or left to pass. Sign in with Twitch to save votes and liked clips.
3. **Review your queue** — Open the Playground to revisit saved clips and select one for analysis or chat.
4. **Prepare a post** — Generate a recap, a suggested score, and a title and description using Groq.
5. **Mark for export** — Record a clip for YouTube Shorts and TikTok in your queue.

## Current functionality

- **Clip discovery** — Swipe feed, category search, followed-channel selection, video previews, and theater mode.
- **Community ranking** — Monthly leaderboard with WebSocket updates, historical rankings, and analytics dashboards.
- **Clip discussion** — Comments with Twitch emote support.
- **Personal queue** — Saved clip history, Playground analysis, and AI chat.
- **Accounts** — Twitch OAuth sign-in and followed-channel sync.
- **Administration** — Separate admin-only queue and processing endpoints.

### AI and export status

The Playground currently sends the clip's title, channel, and existing
description to Groq. Its `transcript` output is a generated recap based on that
metadata, not a transcription of the clip's audio. If the Groq key is missing
or the request fails, analysis falls back to generated sample content.

YouTube Shorts and TikTok actions currently **record an export request**.
Live publishing adapters are not connected; the UI's upload action does not
publish a video to either platform.

### Try the demo

With the frontend running, open **http://localhost:3000/?demo=1** to try the
swipe → queue → analyze → export flow without signing in. This walkthrough
uses a fixed set of public Twitch clip references, a browser-session queue,
and simulated analysis and export actions. Video playback requires fresh clip
URLs; otherwise the demo shows thumbnails. The GIF above shows the recorded
walkthrough.

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | FastAPI + Uvicorn (async), Python 3.12+ |
| Database | PostgreSQL via SQLAlchemy 2.0 async + asyncpg |
| Migrations | Alembic (async mode) |
| Auth | JWT (HS256) + Bcrypt, Twitch OAuth |
| Scheduling | APScheduler (AsyncIOScheduler) |
| Frontend | React 18 + TypeScript + Vite |
| Charting | Recharts |
| Routing | react-router-dom |
| Package Mgr | uv (Python), npm (Frontend) |

---

## Prerequisites

- **Python 3.12+**
- **Node.js 22+** (with npm; the locked frontend dependencies require Node 20 or newer)
- **uv** — Python package manager ([install guide](https://docs.astral.sh/uv/getting-started/installation/))
- **PostgreSQL** — local instance or hosted (e.g. Supabase)
- **Twitch Developer App** — for API credentials ([dev.twitch.tv](https://dev.twitch.tv/console/apps))

---

## Getting Started

### 1. Clone the repository

```bash
git clone https://github.com/Enizri/Clipder.git
cd Clipder
```

### 2. Configure environment variables

```bash
cp .env.example .env
```

Open `.env` and fill in your credentials and content settings:

| Variable | Description |
|----------|-------------|
| `DATABASE_URL` | PostgreSQL connection string, e.g. `postgresql+asyncpg://user:pass@localhost:5432/clipder` |
| `SECRET_KEY` | A strong random string for JWT signing (the app refuses to start without it) |
| `TWITCH_CLIENT_ID` | From your Twitch Developer Console app |
| `TWITCH_CLIENT_SECRET` | From your Twitch Developer Console app |
| `GROQ_API_KEY` | From [console.groq.com](https://console.groq.com) — used for AI transcription/chat |
| `TWITCH_CHANNELS` | Comma-separated Twitch channel names to fetch clips from |
| `TWITCH_CATEGORIES` | Optional category list (e.g. `Just Chatting,VALORANT`); the template provides a starting selection |

Set `TWITCH_REDIRECT_URI` to
`http://localhost:3000/api/v1/auth/twitch/callback` for local development, and
register that exact URL in your Twitch Developer Console app. The callback
passes through the Vite proxy to the backend.

See [.env.example](.env.example) for the configuration template. The core
engine currently requires `GROQ_API_KEY` as well as Twitch credentials and at
least one `TWITCH_CHANNELS` entry to initialize, even though Playground
analysis has a fallback.

### 3. Install Python dependencies

```bash
uv sync --locked
```

This installs the Python dependencies using the committed `uv.lock`.

### 4. Run database migrations

Make sure your PostgreSQL database exists and `DATABASE_URL` in `.env` points to it, then:

```bash
uv run alembic upgrade head
```

This creates all the tables (users, clips, votes, leaderboard, etc.).

### 5. Install frontend dependencies

```bash
cd frontend
npm ci
cd ..
```

`npm ci` installs the frontend dependencies from the committed `package-lock.json`.

### 6. Start the application

**Backend** (from project root):

```bash
uv run uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

**Frontend** (from `frontend/`):

```bash
cd frontend
npm run dev
```

The Vite dev server starts on **http://localhost:3000** and automatically
proxies `/api/*` and `/ws/*` requests to the backend at `localhost:8000`
(configured in `vite.config.ts`). Open **http://localhost:3000** in your
browser.

Interactive API documentation is available at **http://localhost:8000/docs**.

---

## Project Structure

```
Clipder/
├── main.py                    # FastAPI entry point, router mounting, WebSocket, lifespan
├── pyproject.toml             # Python deps (managed with uv)
├── uv.lock                    # Locked Python dependency versions
├── alembic.ini                # Migration config
├── .env.example               # Required env vars template
├── CLAUDE.md                  # Points Claude Code to AGENTS.md
├── AGENTS.md                  # Canonical coding-agent guidelines
│
├── alembic/
│   ├── env.py                 # Async migration runner
│   └── versions/              # Migration scripts
│
├── backend/
│   ├── engine.py              # Core engine (TwitchClient, VideoProcessor, etc.)
│   ├── api/v1/
│   │   ├── deps.py            # DI: get_db, get_current_user, check_admin
│   │   └── endpoints/
│   │       ├── admin.py       # /api/v1/admin/*
│   │       ├── ai_chat.py     # /api/v1/ai/*
│   │       ├── ai_editor.py   # /api/v1/ai-editor/*
│   │       ├── auth.py        # /api/v1/auth/*
│   │       ├── clips.py       # /api/v1/clips, /clip/*, /categories, /emotes
│   │       ├── following.py   # /api/v1/following/*
│   │       ├── health.py      # /api/v1/health/*
│   │       ├── leaderboard.py # /api/v1/leaderboard/*
│   │       └── votes.py       # /api/v1/votes/*
│   ├── core/
│   │   ├── config.py          # Pydantic Settings (all env vars)
│   │   ├── security.py        # JWT + Bcrypt
│   │   ├── database.py        # Async engine + session factory
│   │   ├── state.py           # ConnectionManager (WebSocket)
│   │   ├── tasks.py           # APScheduler background jobs
│   │   ├── cache_provider.py  # Leaderboard cache
│   │   ├── twitch_oauth.py    # Twitch OAuth helpers (httpx)
│   │   └── logger.py          # Logging config
│   ├── models/                # SQLAlchemy ORM models
│   └── schemas/               # Pydantic request/response schemas
│
├── frontend/
│   ├── index.html
│   ├── package.json
│   ├── package-lock.json      # Locked frontend deps for reproducible installs
│   ├── tsconfig.json
│   ├── vite.config.ts         # Dev server + proxy config
│   ├── eslint.config.js
│   ├── .env.example           # Frontend env var template
│   └── src/
│       ├── main.tsx           # React entry point
│       ├── App.tsx            # BrowserRouter + layout + routes
│       ├── index.css          # Global styles
│       ├── types.ts           # Shared TypeScript interfaces
│       ├── api/client.ts      # Typed API client (all /api/v1/* calls)
│       ├── pages/             # Route-level page components
│       ├── components/        # Reusable UI components
│       └── hooks/             # Custom React hooks
│
├── docs/screenshots/          # README demo GIF
├── tests/                     # Integration tests and manual checks
└── scripts/                   # DB utilities and demo GIF recorder
```

---

## API Endpoints

All routes live under `/api/v1/`. The backend exposes these router groups:

| Router | Routes | Auth |
|--------|--------|------|
| auth | `/api/v1/auth/*` | Public (Twitch OAuth), JWT (`/me`) |
| clips | `/api/v1/clips`, `/api/v1/categories`, `/api/v1/clip/{clip_id}/*`, `/api/v1/emotes` | Public; optional JWT personalizes the feed |
| votes | `/api/v1/votes/clip/{clip_id}/vote`, `/api/v1/votes/clip/{clip_id}/votes` | JWT to vote; public vote totals |
| leaderboard | `/api/v1/leaderboard/*` | Public |
| following | `/api/v1/following`, `/api/v1/following/*` | JWT required |
| admin | `/api/v1/admin/*` | JWT + ADMIN role |
| ai_chat | `/api/v1/ai/chat` | JWT required |
| ai_editor | `/api/v1/ai-editor/history/*`, `/api/v1/ai-editor/history` | JWT required |
| health | `/api/v1/health`, `/api/v1/health/*` | Public |

**WebSocket:** `ws://localhost:8000/ws/leaderboard` — real-time leaderboard updates.

---

## Environment Variables Reference

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `DATABASE_URL` | **Yes** | — | `postgresql+asyncpg://user:pass@host:5432/dbname` |
| `SECRET_KEY` | **Yes** | — | Strong random string for JWT signing |
| `TWITCH_CLIENT_ID` | **Yes** | — | Twitch OAuth client ID |
| `TWITCH_CLIENT_SECRET` | **Yes** | — | Twitch OAuth client secret |
| `GROQ_API_KEY` | **Yes** | — | Groq API key for AI features |
| `GROQ_CHAT_MODEL` | No | `llama-3.3-70b-versatile` | Groq cloud chat model (playground). Not a local LLM. |
| `TWITCH_CHANNELS` | **Yes** | — | Comma-separated channel names |
| `TWITCH_CATEGORIES` | No | `Just Chatting,Grand Theft Auto V,VALORANT,League of Legends` | Comma-separated category names; `.env.example` supplies a shorter list |
| `FRONTEND_URL` | No | `http://localhost:3000` | CORS allowed origin |
| `TWITCH_REDIRECT_URI` | No | `http://localhost:3000/api/v1/auth/twitch/callback` | Must match the callback registered with Twitch |
| `ALGORITHM` | No | `HS256` | JWT algorithm |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | No | `10080` | JWT TTL (7 days) |
| `SUPABASE_URL` | No | — | Supabase project URL |
| `SUPABASE_ANON_KEY` | No | — | Supabase anonymous key |
| `OPUS_CLIP_API_KEY` | No | — | Optional core-engine configuration |

The frontend has one optional variable in `frontend/.env`:

| Variable | Description |
|----------|-------------|
| `VITE_API_ORIGIN` | Set only if the backend runs on a different host. Leave empty for local dev (Vite proxy handles it). |

---

## Development

```bash
# Lint Python
uv run ruff check .

# Run tests
uv run pytest
```

Run frontend checks from `frontend/`:

```bash
npm run lint
npm run build
```

The build runs TypeScript checks before producing the Vite bundle.
Database integration tests use `TEST_DATABASE_URL`, defaulting to
`postgresql+asyncpg://postgres:password@localhost:5432/clipder_test`. Use a
dedicated test database: the fixtures create and drop tables. Tests also load
the application settings, including `SECRET_KEY`.

---

## License

MIT License — see [LICENSE](LICENSE) for details.
