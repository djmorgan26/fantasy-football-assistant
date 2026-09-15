# Development

## Prerequisites

- **Python 3.11+**
- **Node 18+**

That is the whole list. Mock mode uses SQLite and needs no database server, no
API keys and no accounts. Postgres is only needed if you want to run against
production-shaped data locally, which most work does not.

## Running it

Two terminals. The first time, create the backend virtualenv:

```bash
cd backend
python -m venv venv
./venv/bin/pip install -r requirements.txt
```

**Backend** (mock mode — no credentials, no network):

```bash
cd backend
./venv/bin/python -m uvicorn app.main:app --reload --env-file ../.env.mock --port 8000
```

**Frontend**:

```bash
cd frontend
npm install
npm run dev
```

Open <http://localhost:3000> and sign in with the button on the login page, or:

```
email:    demo@demo.app
password: demo1234
```

The seeded demo league has ten teams, full rosters, matchups and waiver budgets.

Interactive API docs: <http://localhost:8000/docs>

## Working against real data

Copy `.env.example` to `backend/.env` and fill in what you need. Everything is
optional and degrades independently:

| Variable | Needed for | Without it |
| --- | --- | --- |
| `SECRET_KEY` | signing tokens | a dev default is used — fine locally, never in production |
| `DATABASE_URL` | Postgres instead of SQLite | SQLite file in `backend/` |
| `GROQ_API_KEY` | all generated writing | content falls back to a facts summary |
| `LLM_MODEL` | which model to use | the code default |
| `YAHOO_CLIENT_ID`, `YAHOO_CLIENT_SECRET` | Yahoo Fantasy connection | Yahoo stays visibly unavailable; ESPN and Sleeper continue to work |

**Sleeper needs nothing at all.** Its API is public and read-only; connecting a
league takes a username, and the app looks up which leagues that username is in.

Private ESPN leagues need the `espn_s2` and `SWID` cookies, entered per-user in
Profile Settings and stored encrypted — see
[ESPN API](ESPN_API_INTEGRATION.md).

Yahoo Fantasy uses server-side OAuth, not copied browser cookies. Register the
exact `YAHOO_REDIRECT_URI` with Yahoo, set the client id/secret plus
`FRONTEND_URL`, and use the Yahoo option on Connect League. Access and refresh
tokens are encrypted at rest and refresh automatically before a sync. Fantasy
Hub's Google login and Yahoo account are intentionally independent: Yahoo is
always asked to authenticate, so a user can choose an account with a different
email. The resulting connection is saved against the currently signed-in
Fantasy Hub user for future Gmail sign-ins.

> **Groq retires models regularly.** A retired model id returns
> `404 model_not_found` and every generated feature silently falls back. Check
> what is live before pinning one:
> ```bash
> curl -s https://api.groq.com/openai/v1/models \
>   -H "Authorization: Bearer $GROQ_API_KEY" | jq '.data[].id'
> ```

## Common tasks

```bash
# Backend
./venv/bin/python -m pytest tests/ -q           # tests + coverage gate
./venv/bin/python -m pytest tests/ -q -m unit   # fast, no database

# Frontend
npm run type-check
npm run lint
npm test                                        # vitest, watch mode
npm run test:coverage
npm run build
```

See [Testing](TESTING.md) for how the suite is organised.

## Database changes

The app calls `create_all` on startup, so new tables appear automatically. For
Postgres, add an Alembic revision as well so the schema has a reproducible
history:

```bash
cd backend
DATABASE_URL=... ./venv/bin/alembic revision --autogenerate -m "describe the change"
DATABASE_URL=... ./venv/bin/alembic upgrade head
```

Alembic reads `DATABASE_URL` from the environment — the same source the app
reads. The `sqlalchemy.url` in `alembic.ini` is an unused placeholder.

> **On a database that already has the schema, run `alembic stamp head`, not
> `upgrade head`.** Every existing deployment was built by `create_all`, so an
> upgrade would try to create tables that already exist. `stamp` records the
> baseline as applied without touching anything.

To check a revision against the models, autogenerate a second one: if it detects
nothing, the migration and the models agree.

Supabase-specific DDL (row-level security, Realtime, Storage buckets) lives in
`supabase/migrations/` and is applied separately — Alembic does not manage it.

## Resetting the demo database

Mock mode seeds on startup and keeps a SQLite file. If it drifts:

```bash
rm backend/fantasy_mock.db   # recreated and reseeded on next boot
```

## Gotchas worth knowing before you hit them

- **ESPN has two position id spaces.** `defaultPositionId` says what a player *is*; `lineupSlotId` says where he *lines up*. Mixing them labelled every WR "RB/WR" in production. [Details](ESPN_API_INTEGRATION.md#two-id-spaces-and-the-bug-that-comes-from-mixing-them).
- **Slot names are uppercase.** Compare against `"BENCH"`, not `"Bench"`.
- **Groq bills reasoning against `max_tokens`.** A tight ceiling does not shorten the answer, it returns nothing. Budgets are deliberately generous.
- **Coverage needs greenlet tracking.** See [Testing](TESTING.md#why-coverage-was-lying).
