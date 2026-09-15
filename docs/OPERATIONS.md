# Operations

## Health endpoints

Three routes, two questions. A load balancer needs both.

| Route | Question | Touches the database | Fails when |
| --- | --- | --- | --- |
| `GET /health/live` | is the process up? | no | never — it has no dependencies |
| `GET /health` | *(alias of `/health/live`)* | no | — |
| `GET /health/ready` | should this instance get traffic? | yes | database unreachable or slow → **503** |

Liveness deliberately does no I/O. A database blip should not get a healthy
container killed and restarted into the same blip.

```bash
curl -s localhost:8000/health/ready | jq
{
  "status": "ready",
  "checks": { "database": { "status": "ok", "latency_ms": 1.84 } },
  "features": { "llm": "configured", "espn": "live", "sleeper": "live" },
  "app": "Fantasy Football Assistant",
  "version": "2.0.0",
  "commit": "eab57cd91f2a",
  "region": "iad1",
  "environment": "production"
}
```

`features` is **reported, not gated**. A missing model key means recaps fall
back to a facts summary; that is not a reason to pull an instance out of
rotation. The database is the only hard dependency, and its check has a 5s
deadline so a wedged connection surfaces as "not ready" rather than a probe
that never returns.

Point uptime monitoring at `/health/ready`. Point container liveness at
`/health/live`.

## Request tracing

Every response carries:

- **`X-Request-ID`** — taken from the incoming header if a proxy already set one, so a trace survives a hop; otherwise generated.
- **`Server-Timing: app;dur=<ms>`** — server-side duration.

Every request produces one structured log line with method, path, status and
duration, keyed by that id. Health checks are excluded so they do not drown the
log.

When a user reports an error, ask for the request id — a 500 response includes
it in the body:

```json
{ "detail": "Something went wrong on our end. Try again in a moment.",
  "request_id": "9f2c1ab4de7c0051" }
```

Internal exception messages never reach the client. They are in the logs under
that id.

## Security headers

Set on every response: `X-Content-Type-Options: nosniff`,
`X-Frame-Options: DENY`, `Referrer-Policy: strict-origin-when-cross-origin`,
`Permissions-Policy` denying geolocation, microphone and camera.

No Content-Security-Policy is set here. The API serves JSON and the built SPA,
and a CSP tight enough to be worth having needs the frontend's asset hashes —
that belongs in the hosting config.

## Configuration

Production environment variables override code defaults, which is both the
point and the hazard: **a stale pin is worse than a missing one**. Prefer
removing a variable so the derived default wins rather than setting a new fixed
value.

| Variable | Required | Notes |
| --- | --- | --- |
| `SECRET_KEY` | **yes** | `openssl rand -hex 32`. Rotating it invalidates every session *and* every stored ESPN credential. |
| `DATABASE_URL` | **yes** | Postgres. Through Supabase's pooler, use port 6543. |
| `ALLOWED_ORIGINS` | yes | comma-separated; the frontend origin |
| `ALLOWED_HOSTS` | yes | comma-separated; supports `*.vercel.app` |
| `GROQ_API_KEY` | no | without it, generated content falls back to facts |
| `LLM_MODEL` | no | **verify it is still live before pinning** — see below |
| `ESPN_SEASON_YEAR` | no | leave unset; the code derives it (March onward = the upcoming season) |
| `MOCK_MODE` | no | `true` only for the demo deployment |
| `YAHOO_CLIENT_ID`, `YAHOO_CLIENT_SECRET` | no | enable Yahoo Fantasy OAuth; the secret must remain server-only |
| `YAHOO_REDIRECT_URI`, `FRONTEND_URL` | with Yahoo | callback registered with Yahoo, and the browser origin to return to after consent |

### Yahoo Fantasy OAuth

Yahoo fails differently from ESPN and Sleeper: the sign-in succeeds and the
league data is what gets refused. Three things must line up in the Yahoo
developer app at <https://developer.yahoo.com/apps/>, and only the third one
announces itself.

1. **API permission must include Fantasy Sports, Read.** This is the one that
   bites. An app registered with only OpenID Connect permissions still issues
   working access tokens, so the connection looks fine — and then every league
   call comes back `401`. The app requests `scope=fspt-r`; if the registered
   app cannot grant it, Yahoo refuses at the consent screen and the reason now
   lands on the connect page instead of being swallowed.
2. **Redirect URI must match `YAHOO_REDIRECT_URI` exactly**, including scheme
   and trailing path — `https://<domain>/api/yahoo/callback`. Yahoo rejects
   `http://` and bare `localhost` for OAuth2 apps, so local Yahoo work needs a
   tunnel (or use the deployed callback).
3. **`FRONTEND_URL`** is only the fallback origin. The browser origin that
   started the flow is signed into the OAuth state and wins, so a stale value
   here no longer strands anyone on the wrong deployment.

To see where a failed attempt actually stopped, look for `Yahoo token exchange
failed`, `Yahoo denied a fantasy request`, or `Yahoo callback did not carry an
authorization code` in the server logs — each carries Yahoo's own status and
error text.

### The model pin

Groq retires models regularly. A retired id returns `404 model_not_found` and
every generated feature silently falls back to its facts summary — the app
keeps working, which is exactly why this goes unnoticed. `ESPN_SEASON_YEAR` has
the same failure shape: a pin from a previous season keeps the app on that
season through kickoff.

```bash
curl -s https://api.groq.com/openai/v1/models \
  -H "Authorization: Bearer $GROQ_API_KEY" | jq '.data[].id'
```

`/health/ready` reports whether a key is configured, not whether the model id is
valid. If recaps go flat, check this first.

## Serverless notes

The app runs on Vercel functions against Supabase Postgres.

- **Pooler compatibility.** Supavisor's transaction mode does not support asyncpg's server-side prepared statements, and disabling the statement cache alone is not enough — the prepared-statement *names* still collide across pooled connections. `db/database.py` disables both caches and gives every statement a unique name, and uses `NullPool` so each invocation gets a fresh connection.
- **Cold starts.** The Sleeper player index (14MB upstream, ~150KB trimmed) is cached to the tmp directory so a cold instance reuses the previous one's work instead of re-downloading.

## Deploying

`main` is production. Pushing to it deploys to the `fantasy-football-real`
Vercel project; a PR into `main` deploys a preview.

Ship a production fix as a small commit off `main` rather than pushing a
working tree:

```bash
git push origin <branch>:main
```

### After a deploy

1. `curl -s <host>/health/ready | jq` — expect `"status": "ready"` and the new `commit`.
2. Generate a recap. If `generated_by` comes back `"fallback"`, the model pin is stale.
3. Load a league page and confirm rosters render.

## Database migrations

Two mechanisms, deliberately separate:

- **Alembic** (`backend/alembic/versions/`) — tables and columns. The app also calls `create_all` on startup, so new tables appear without a migration; the revisions exist so Postgres has a reproducible history. Alembic resolves its URL from `DATABASE_URL`, not from `alembic.ini`.
  - **First run against an existing database: `alembic stamp head`, once.** Production's schema was built by `create_all`, so `upgrade head` would try to create tables that already exist.
- **Supabase SQL** (`supabase/migrations/`) — row-level security, Realtime publications, Storage buckets. Alembic does not manage these. They are written idempotently, so re-running after `create_all` has already made the tables is safe.

## When something is wrong

| Symptom | Look at |
| --- | --- |
| 503 from `/health/ready` | `checks.database` — `timeout` means slow, `error` means unreachable |
| Recaps read like bullet lists | `generated_by: "fallback"` → model pin or missing key |
| Wrong season's data | `ESPN_SEASON_YEAR` pinned to a past year; remove it |
| `prepared statement ... already exists` | pooler settings in `db/database.py` |
| A user's private league stops loading | their ESPN cookies expired; re-enter in Profile Settings |
| Every WR labelled "RB/WR" | position vs lineup-slot id spaces — [details](ESPN_API_INTEGRATION.md#two-id-spaces-and-the-bug-that-comes-from-mixing-them) |
