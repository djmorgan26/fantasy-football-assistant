# Fantasy Football Assistant

A comprehensive web application that connects to ESPN Fantasy Football leagues to provide intelligent trade suggestions, waiver wire recommendations, and real-time alerts to optimize your fantasy football experience.

## Features

- **ESPN & Sleeper League Integration**: Seamlessly connect to your fantasy leagues
- **Draft Prep & Live Draft Assistant**: League-scoring-aware value board (VBD rankings,
  tiers, ADP) plus best-available pick recommendations during your draft
- **Trade Analyzer**: Get intelligent trade suggestions based on player valuations and team needs
- **Waiver Wire Assistant**: Receive recommendations for pickup targets and drop candidates
- **Content & Humor Engine**: League-personalized recaps, power rankings, awards, and season
  write-ups built from real weekly data and your league's own voice
- **Real-time Alerts**: Get notified about injuries, breakout performances, and opportunities
- **Team Optimization**: Lineup suggestions and roster management tools
- **Mobile-Responsive UI**: Access your tools on any device

### Draft Tools (ESPN & Sleeper)

The draft endpoints build projections from your league's scoring settings, then
convert them to Value-Based Drafting (VBD) scores so rankings reflect positional
scarcity rather than generic rankings. They work for **both ESPN and Sleeper**
leagues (Sleeper uses exact scoring pulled live; ESPN uses its scoring type,
size, and lineup slots). Projections come from the free Sleeper data set either way:

- `GET /api/draft/rankings?scoring_type=ppr&team_count=12` — generic pre-draft cheat sheet
- `GET /api/draft/value-board/{league_id}` — value board tuned to your league's scoring
- `GET /api/draft/assist/{league_id}` — best-available recommendations + optional AI advice

Live in-draft pick tracking uses Sleeper's public draft feed. ESPN has no
equivalent public feed, so for ESPN leagues the assistant serves a
scoring-adjusted big board of best-available players.

### Content & Humor Engine (ESPN & Sleeper)

Generates league-personalized written content from **real weekly data** plus your
league's own voice. The engine first extracts concrete "story hooks" from the week
(biggest blowout, nail-biters, points left on the bench, the should've-started guy,
lucky/unlucky wins), then writes content in your league's tone using manager personas
and a corpus of past write-ups you provide.

- `GET /api/content/{league_id}/profile` · `PUT .../profile` — manage voice, personas, and past write-ups
- `GET /api/content/{league_id}/narrative/week/{week}` — the data-driven story facts (no AI)
- `POST /api/content/{league_id}/generate` — generate `weekly_recap`, `power_rankings`, `awards`, or `season_recap`

The **Press Box** page (`/leagues/:id/press-box`) drives all of this, including a
Voice Settings panel where you paste previous years' reports — the single biggest
lever on output quality. The engine works before any corpus is added (sensible
default voice) and degrades to a facts-based draft when no AI key is configured.

> **AI provider:** AI features run on **Groq** (single provider) using the
> `LLM_MODEL` configured in `.env` (default `llama-3.3-70b-versatile`).

## Tech Stack

**Frontend**
- React 18 with TypeScript
- Vite for fast development and building
- Tailwind CSS for styling
- React Router for navigation
- Recharts for data visualization
- Headless UI for accessible components

**Backend**
- FastAPI with async/await support
- SQLAlchemy 2.0 with async PostgreSQL
- Pydantic for data validation
- JWT authentication
- Alembic for database migrations

**Database**
- PostgreSQL with asyncpg driver
- Connection pooling for optimal performance

## Installation

### Prerequisites
- Node.js 18+ and npm
- Python 3.11+
- PostgreSQL 14+

### Quick Start

1. **Clone and setup**
   ```bash
   git clone <repository-url>
   cd fantasy-football-assistant
   ```

2. **Backend setup**
   ```bash
   cd backend
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. **Database setup**
   ```bash
   # Create PostgreSQL database
   createdb fantasy_football_db
   
   # Run migrations
   alembic upgrade head
   ```

4. **Environment configuration**
   ```bash
   # Copy and configure environment files
   cp .env.example .env
   # Edit .env with your ESPN credentials and database settings
   ```

5. **Frontend setup**
   ```bash
   cd ../frontend
   npm install
   ```

6. **Start development servers**
   ```bash
   # Terminal 1: Backend (from backend/)
   uvicorn app.main:app --reload
   
   # Terminal 2: Frontend (from frontend/)
   npm run dev
   ```

   > **Entrypoints:** `app.main:app` is the canonical application server for
   > BOTH modes (real and mock) — see "Real mode vs Mock mode" below. The repo
   > also contains two older standalone demo servers from early prototyping
   > (`app.working_main`, `app.demo_main`); these are superseded by `MOCK_MODE`
   > on `app.main` and are kept only for reference.

## Real mode vs Mock mode

The whole app runs in one of two modes, selected by the `MOCK_MODE` environment
variable. Both use the same canonical entrypoint, `app.main:app`.

| | Real mode | Mock mode |
|---|---|---|
| `MOCK_MODE` | `false` | `true` |
| Data | live ESPN + Sleeper + Groq, your credentials | realistic sample data, no external calls |
| Database | PostgreSQL (`DATABASE_URL`) | local SQLite (`fantasy_mock.db`), auto-created |
| Credentials needed | Groq key, ESPN league/cookies, Postgres | none |
| Use for | your real leagues | demos, UI development, offline work |

In mock mode every feature degrades gracefully to coherent sample data: the
Draft Room shows a full value board and an in-progress draft, and the Press Box
shows a seeded league with auto-filled personas. The content engine still uses
its facts-based fallback when no Groq key is set (add a key to `.env.mock` to
exercise real AI writing against the mock data).

### Launch mock mode (zero setup)

```bash
# Backend (from backend/)
./venv/bin/python -m uvicorn app.main:app --reload --env-file ../.env.mock --port 8000
# Frontend (from frontend/)
npm run dev
```

Open http://localhost:3000 and click **Use demo account** on the login page
(credentials: `demo@demo.app` / `demo1234`). A demo user, an ESPN league, and a
Sleeper league are seeded automatically on startup.

### Launch real mode

```bash
# One-time: create .env from .env.example, set DATABASE_URL, SECRET_KEY
#   (openssl rand -hex 32), GROQ_API_KEY, and ESPN_SEASON_YEAR.
# Backend (from backend/) — uvicorn loads .env automatically
./venv/bin/python -m uvicorn app.main:app --reload --port 8000
# Frontend (from frontend/)
npm run dev
```

Register an account, then connect your ESPN or Sleeper league from the dashboard.

7. **Access the application**
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000
   - API Documentation: http://localhost:8000/docs

## ESPN Integration Setup

To connect to your ESPN league, you'll need:

1. **League ID**: Found in your ESPN league URL
2. **ESPN Cookies**: Required for private leagues
   - `espn_s2`: Authentication cookie
   - `SWID`: Session identifier

See [ESPN_API_INTEGRATION.md](docs/ESPN_API_INTEGRATION.md) for detailed setup instructions.

## Development

- **Frontend**: Hot reload enabled with Vite
- **Backend**: Auto-reload enabled with uvicorn
- **Database**: Migrations managed with Alembic
- **Type Safety**: Full TypeScript on frontend, Pydantic validation on backend

## Project Structure

```
fantasy-football-assistant/
├── frontend/           # React frontend application
├── backend/            # FastAPI backend application
├── docs/               # Project documentation
├── scripts/            # Build and deployment scripts
└── docker/             # Docker configuration files
```

## Contributing

1. Follow the development setup in [DEVELOPMENT_SETUP.md](docs/DEVELOPMENT_SETUP.md)
2. Use conventional commits for clear git history
3. Ensure all tests pass before submitting PRs
4. Maintain type safety and add proper validation

## License

MIT License - see LICENSE file for details