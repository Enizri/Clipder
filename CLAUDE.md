# Claude Code

This repository uses **[AGENTS.md](./AGENTS.md)** as the single source of truth for coding agents.

Before writing or changing code:

1. Read `AGENTS.md` in full.
2. Follow its constraints (`uv` only, never expose `.env`, treat `backend/engine.py` as a legacy engine).
3. Prefer the layout, API prefixes, and gaps listed there.

When architecture, endpoints, models, or conventions change, update `AGENTS.md` in the same change. **Do not duplicate project rules in this file.**
