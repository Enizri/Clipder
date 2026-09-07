# Clipder

A Twitch clip discovery app. Browse clips from your favorite streamers, swipe
to vote, and collect the ones worth keeping. Saved clips land in the Playground,
where you can review them and prepare titles and descriptions for short-form
platforms.

![Clipder demo: swipe a Twitch clip, open the Playground queue, analyze, and mark it for export](docs/screenshots/clipder-demo.gif)

## What it does

- **Swipe to curate** — a Tinder-style feed of Twitch clips, filtered by game category or by the channels you follow. Preview inline or open theater mode.
- **Community leaderboard** — monthly rankings that update live over WebSockets, with historical standings and analytics dashboards.
- **Playground** — liked clips land in a personal queue where an LLM drafts titles, descriptions and hooks for short-form platforms, then marks clips for export.
- **Discussion** — per-clip comments with Twitch emote rendering.
- **Twitch OAuth** — sign in with Twitch to sync followed channels and persist your votes.

## Built with

| | |
|---|---|
| Backend | FastAPI, async SQLAlchemy 2.0, PostgreSQL, Alembic, APScheduler |
| Frontend | React 18, TypeScript, Vite, Recharts |
| Realtime | WebSockets for live leaderboard updates |
| Auth | Twitch OAuth + JWT |
| AI | Groq (Llama 3.3 70B) |

## Requirements

- Python 3.12+ and [uv](https://docs.astral.sh/uv/getting-started/installation/)
- Node.js 22+
- PostgreSQL
- A [Twitch developer app](https://dev.twitch.tv/console/apps) for API credentials

## Setup

```bash
git clone https://github.com/Enizri/Clipder.git
cd Clipder
cp .env.example .env
```

Fill in `.env` — see the comments in [.env.example](.env.example) for what each
value does. At minimum you need a database URL, a JWT secret, and Twitch
credentials.

Install dependencies and create the tables:

```bash
uv sync --locked
uv run alembic upgrade head
cd frontend && npm ci && cd ..
```

## Running

Backend, from the project root:

```bash
uv run uvicorn main:app --reload --port 8000
```

Frontend, in a second terminal:

```bash
cd frontend
npm run dev
```

Open <http://localhost:3000>. The dev server proxies API and WebSocket requests
to the backend automatically.

To look around without signing in, open <http://localhost:3000/?demo=1> for the
walkthrough shown above.

## Development

```bash
uv run ruff check .
uv run pytest
```

Frontend checks run from `frontend/` with `npm run lint` and `npm run build`.

For a production frontend build, run `npm ci` followed by `npm run build` in
`frontend/` using Node.js 22+. Output is generated in `frontend/dist/` and is
ignored by Git. CI checks frontend builds on pushes and pull requests to `main`;
it does not commit generated files.

## License

MIT — see [LICENSE](LICENSE).
