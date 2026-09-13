# Fantasy Football Assistant

A companion app for ESPN and Sleeper fantasy leagues that knows your **whole
league**, not just your team — and spends that on the things a national fantasy
site cannot do.

```bash
# Backend (no credentials, no network, no database server)
cd backend && ./venv/bin/python -m uvicorn app.main:app --reload --env-file ../.env.mock --port 8000

# Frontend
cd frontend && npm run dev
```

Then <http://localhost:3000> — sign in with the demo button, or
`demo@demo.app` / `demo1234`. Full setup in [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md).

## What it does

**The board.** Your league posts, comments and reacts. Reactions are typed —
🔥 savage, 😂 funny, 💀 brutal, 🤓 smart, 🧊 cold take — and the posts the league
rates highly become the style anchors the AI writes from. Generated content
lands on the board too and is rated the same way, so a flat recap gets rated
flat and drops back out. This is the loop the rest of the app is arranged
around; see [Architecture](docs/ARCHITECTURE.md#the-voice-loop).

**Across Leagues.** If you play in more than one league, the same player ends
up on your roster in one and on your opponent's in another — every point he
scores helps you and hurts you at once, and most people never notice. This page
names those conflicts, shows which players you are most exposed to across all
your teams, and sorts your weeks with the most precarious first. Players are
matched by name, not id, because ESPN and Sleeper number the same human
differently.

**Game Day.** On a Sunday, the only question is *who do I still have left, and
who do they still have?* This maps both starting lineups onto the live NFL
slate and ranks every game by how much it swings **your** matchup — so the game
where you have two starters against their quarterback sits at the top, not
whichever kicked off first.

**The Commissioner.** A league-aware assistant, docked on every league page. It
answers from standings, your roster, the week's results and live waiver
trends — in your league's voice, not a product's.

**The league wire.** The NFL news feed, filtered to players somebody in your
league rosters, flagged with the team that owns them, and summarised on demand
into one paragraph about what changed *for your league* today.

**Weekly primer.** One card: lineup risk, the single swap that gains the most
points, this week's matchup, and a line of trash talk to paste into the group
chat.

**Draft tools.** Value-Based Drafting rankings built from your league's actual
scoring settings, so they reflect positional scarcity rather than generic
rankings. Live pick tracking for Sleeper; a scoring-adjusted big board for ESPN,
which has no public draft feed.

**Roster, trades, players, waiver budgets** across both platforms, with a
mobile-first interface that works on a 320px screen.

## Stack

React 18 · TypeScript · Vite · Tailwind · react-query
FastAPI · SQLAlchemy 2 (async) · Postgres / SQLite · Alembic
Groq for generation, with deterministic fallbacks everywhere

## API surface

| Area | Routes |
| --- | --- |
| Auth | `/api/auth/*` |
| Leagues & teams | `/api/leagues/*` · `/api/teams/*` · `/api/sleeper/*` |
| Players & trades | `/api/players/*` · `/api/trades/*` |
| Draft | `/api/draft/rankings` · `/api/draft/value-board/{id}` · `/api/draft/assist/{id}` |
| Content | `/api/content/{id}/profile` · `/api/content/{id}/generate` · `/api/content/{id}/narrative/week/{week}` |
| Board | `/api/board/{id}/posts` · `.../reactions` · `.../comments` · `.../voice-samples` |
| News | `/api/news/league/{id}` · `/api/news/digest/{id}` · `/api/news/trending` · `/api/news/wire` |
| Assistant | `/api/assistant/{id}/chat` · `.../suggestions` · `.../primer` |
| Game day | `/api/gameday/{id}` |
| Across leagues | `/api/portfolio` |
| Health | `/health/live` · `/health/ready` |

Interactive docs at `/docs` when running locally.

## Tests

```bash
cd backend  && ./venv/bin/python -m pytest tests/ -q   # 285 tests, 85% covered
cd frontend && npx vitest run                          # 230 tests
```

Both have coverage gates that fail the build. [docs/TESTING.md](docs/TESTING.md)

## Documentation

| | |
| --- | --- |
| [Architecture](docs/ARCHITECTURE.md) | how the pieces fit, and the voice loop |
| [Development](docs/DEVELOPMENT.md) | running it locally, gotchas |
| [Testing](docs/TESTING.md) | the suites, fixtures, and why coverage was lying |
| [Operations](docs/OPERATIONS.md) | health, config, deploy, troubleshooting |
| [ESPN API](docs/ESPN_API_INTEGRATION.md) | the upstream API and its two position id spaces |
| [Design](docs/DESIGN.md) | the Stadium token system |

## Status

`main` deploys to production on push. Work in progress is tracked in
[NEXT_SESSION.md](NEXT_SESSION.md).

## License

MIT — see [LICENSE](LICENSE). Not affiliated with or endorsed by ESPN or
Sleeper; platform names identify league connections only.
