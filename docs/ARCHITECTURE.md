# Architecture

What the app is, how the pieces fit, and the one idea the whole thing is built
around.

## The idea

National fantasy sites answer one question well: *how do I win my matchup?*
Every tool they own optimises a single roster, and none of them has a social
surface. This app knows the **whole league** — all twelve rosters, who owns
them, what happened between them, and how the group talks — and spends that
knowledge on the things a national site structurally cannot do:

- a news wire filtered to players *somebody in your league* rosters, saying whose problem each story is
- a Sunday view that ranks NFL games by how much each one swings *your* matchup, because it knows both starting lineups
- a cross-league view that spots the player you are rooting for *and* against this week
- an assistant that answers about the league, not just your team
- generated content that sounds like your league, because it learns from your league

## Shape

```
React SPA (Vite)                 FastAPI                    Postgres (Supabase)
─────────────────                ───────────                ───────────────────
pages/      screens              api/       routers         users, leagues, teams
components/ UI                   services/  logic           players, matchups
hooks/      react-query   ──►    core/      auth, config    board_posts, comments
services/   axios                db/        SQLAlchemy      board_reactions
                                                            voice_samples
                                    │
                                    ▼
                         ESPN · Sleeper · Groq
                     (all optional; each degrades)
```

There is no WebSocket layer, no Redis, no background worker, and no alert
daemon. Requests are synchronous; anything slow is cached in-process with a TTL.
Earlier drafts of this document described those things aspirationally — they do
not exist, and the app does not need them at its current size.

## Request path

1. The SPA calls `/api/...` with a bearer token.
2. `core/observability` tags the request with an id and starts the clock.
3. `core/auth` resolves the token to a `User`.
4. A router in `api/` validates input against a schema in `schemas/`.
5. It loads the league and **checks ownership** — every league-scoped endpoint does this, so a URL with someone else's league id returns 404 rather than data.
6. Work happens in `services/`; the database is reached through SQLAlchemy's async session.
7. One structured log line records method, path, status and duration.

## The voice loop

This is the part worth understanding, because it is why the board exists.

```
  someone posts ──► the league reacts ──► score = Σ(weight × reactions) + 2×comments
                                                        │
                         board_service.refresh_voice_samples
                                                        │
                                                        ▼
                                                  voice_samples
                                                        │
                       api/content._generation_profile() merges them
                                                        │
                                                        ▼
                    content_service._voice_block() → the model's prompt
                                                        │
                                                        ▼
                      generated recap ──► posts back to the board ──┐
                            ▲                                        │
                            └────────────── rated like any post ◄────┘
```

`LeagueContentProfile` has always had a `humor_examples` field, but filling it
meant typing past write-ups into a settings form, so nobody ever did. The board
fills it from what the league actually laughed at.

Design decisions that carry weight:

- **Typed reactions, not a binary.** `savage`/`funny`/`brutal`/`smart`/`cold` record *how* a post landed. A thumbs-up only records *that* it did, which a voice profile cannot learn from.
- **Replies weigh most** (+2). Bothering to answer is the strongest evidence anything landed.
- **`cold` is negative** (−2), so a flat post falls back out of the corpus on its own.
- **The AI's output is rated too.** Without that the loop has no feedback edge.
- **`allow_training` on every post.** One boolean now; an unpleasant retrofit after a season.

Constants live in `services/board_service.py` — threshold, weights, corpus size.

## Shared league helpers

`services/league_context.py` owns the operations every league-scoped router
needs: load the league and prove the caller belongs to it, decrypt ESPN
cookies, find the caller's team, pull a roster, resolve this week's opponent.
Platform branching (ESPN vs Sleeper) is resolved there once. Routers that skip
it end up re-implementing the access check, which is the one thing that must
not vary.

## Who is in a league

One platform league is **one row** in `leagues`, shared by every manager in it.
That has to be true for the board to work at all: a league's managers only see
each other's posts if they resolve to the same `league_id`.

`services/league_access.py` holds the single definition of who may see a
league, `visible_to(user_id)`, and every router imports it rather than
comparing `owner_user_id` itself:

| | Where it lives | Notes |
| --- | --- | --- |
| Access | `leagues.owner_user_id` OR a row in `league_members` | `visible_to` |
| Their team | `league_members.team_id` | co-owners each keep their own claim |
| Their Sleeper account | `league_members.sleeper_user_id` | `leagues.sleeper_user_id` is the owner's |

Connecting a league that already exists adds the caller as a member. It does
**not** reassign `owner_user_id`, and claiming a team does not take it from
whoever claimed it before: doing either of those locked a real user out of
their own league and made their roster vanish, because both facts used to live
in a single column that the second manager simply overwrote.

## Platform parity

ESPN and Sleeper are meant to be interchangeable to everything above the
service layer. `tests/test_platform_parity.py` enforces that by running the
*same* assertions against a league of each kind rather than testing them
separately — a shape that drifts on one side fails immediately.

Where they genuinely differ, the difference is resolved once:

| | ESPN | Sleeper | Resolved in |
| --- | --- | --- | --- |
| Roster | normalized entries | arrays of player ids | `build_team_roster_entries` |
| Matchup | home/away on one row | two rows sharing a `matchup_id` | `league_context.opponent_this_week` |
| Player id | integer | string; a defense is its team abbreviation | joins go through normalized names |
| Scoring label | named on the league | derived from points-per-reception | `sleeper_sync.scoring_type_from` |
| Current week | on the league | authoritative at `/v1/state/nfl` | `sleeper_sync.current_week` |
| FAAB | on the team | split across league, roster and transactions | `sleeper_service.get_waiver_budgets` |
| Sync | `/leagues/{id}/sync` | same endpoint, `sleeper_sync.refresh_league` | `api/leagues.py` |
| Pending trades | `view=mPendingTransactions`, public | GraphQL only, needs a user token | `trade_feed.fetch_trades` |
| Player news / depth chart | wire articles carry athlete tags | player index carries role and injury detail | `player_intel.gather` |

Sleeper needs no credentials at all — the whole API is public and read-only, so
connecting a league needs only a username. The one exception is pending trade
offers, which the public API does not carry at all; see below.

### Yahoo is a third of a platform, on purpose

Yahoo is **not** interchangeable with the other two yet, and
`test_platform_parity.py` deliberately does not cover it. What works today is
OAuth, league discovery, standings and re-sync. What does not:

| | State | Where |
| --- | --- | --- |
| Roster | 501 | `api/teams.py` `get_team_roster` |
| Matchups | 501 | `api/leagues.py` `get_league_matchups` |
| Waiver budgets | 501 | `api/leagues.py` `get_league_waiver_budgets` |
| Points against | always `0.0` | `yahoo_service.league_and_teams` |

The 501s are honest. The trap is `league_context.roster_for`, which fails soft
by design and has no Yahoo branch, so it returns `[]` rather than raising.
Every feature built on a roster — Game Plan, Game Day, the assistant, the news
feed, the cross-league view — therefore renders a Yahoo team as a team with
nobody on it rather than saying it cannot load one. That reads as a bug and is
the first thing to fix when the Yahoo roster adapter lands.

Yahoo also needs an approved developer app: every Fantasy API resource returns
401 without OAuth, credentials are not self-serve, and Yahoo reviews the
application before issuing them.

## Trades

The one feature where a platform's public API is not enough.

### Seeing a trade at all

A trade offer sitting in your inbox is a different thing from a completed
transaction, and the two platforms disagree about whether you may read it:

- **ESPN** answers `?view=mPendingTransactions` for a public league with no
  credentials, alongside `mTransactions2` for history.
- **Sleeper's** public `/v1/league/{id}/transactions/{week}` returns **completed
  transactions only**. A proposed trade is absent from it entirely. Pending
  offers live behind `sleeper.com/graphql`, which requires the manager's own
  bearer token, stored Fernet-encrypted in `leagues.sleeper_token_encrypted`
  and optional: without it the Offers tab degrades to trade history and says
  why.

Two details about Sleeper's GraphQL cost real time to find and are easy to
re-lose:

1. A pending trade's status is **`"proposed"`**, not `"pending"`. Querying the
   obvious spelling returns an empty list rather than an error.
2. `consenter_ids` holds the *roster ids* that have agreed so far, and the
   proposer is always among them. A roster in the trade but absent from that
   list is the one being asked, which is how `trade_feed._direction`
   distinguishes an incoming offer from an outgoing one.

`trade_feed` flattens both platforms into one `NormalizedTrade`, so nothing
above the service layer branches on platform.

### Deciding whether to accept

`trade_engine` is pure (no I/O, no database, no network), so the whole model is
unit-testable from plain dicts (`tests/test_trade_engine.py`). Three ideas:

| Idea | Function | Why it exists |
| --- | --- | --- |
| Value over replacement | `replacement_levels`, `value_over_replacement` | 12 points a week is a great TE and a bad RB. What matters is the margin over the last startable player at that position, which depends on league size and slots. |
| Lineup impact | `optimal_lineup`, `evaluate_side` | Value is theoretical; points scored come from the best *legal* lineup. This is what notices that a third good RB adds nothing when you start two. |
| Playoff odds | `simulate_season` | The number a manager actually wants. Monte Carlo over the **real** remaining schedule, both platforms publishing it up front (`trade_feed.remaining_schedule`). |

The odds are run twice, before and after, under the **same seed**, so the
delta is the trade rather than simulation noise. That matters when the true
effect is under a point.

`find_opportunities` inverts the usual framing: it ranks swaps where *both*
starting lineups improve, because a trade only happens if the other manager
says yes. Ranking by your own gain alone surfaces offers nobody accepts.

### Countering

`counter_offers` answers the question the verdict cannot: if not this, then
what? It enumerates small edits to the offer on the table (ask for one more
player, ask for a different one, send a cheaper piece, swap both sides) and
scores each with the same machinery, against two baselines that only exist
because an offer was made:

- `gain_vs_original` is weekly lineup points above simply accepting. A counter
  that does not beat accepting is discarded.
- `cost_to_them` is how much worse the counter is than the deal *they wrote*.

Likelihood is graded on whether their own starting lineup still improves, not
on `cost_to_them` alone. Grading on the gap was wrong in the case that matters
most: when someone lowballs you, their opening ask is worth a great deal to
them, so every fair counter looked "much worse than what they proposed" and the
whole list came back labelled unlikely. A fair trade is not a long shot.

Results sort by plausibility first and gain second, because "ask for their best
player as well" always wins the most points and is never accepted. The endpoint
is separate from the evaluation and runs on demand, whatever the verdict: a
trade worth accepting may still be worth improving.

### What the numbers cannot say

`player_intel` gathers the context a projection has no way to carry, from
sources that state it as fact:

| Fact | Source |
| --- | --- |
| Depth-chart role ("Starting RB" vs "RB2") | Sleeper player index |
| Injury status, body part, practice participation | Sleeper player index |
| Age and experience (it is a keeper league) | Sleeper player index |
| Recent headlines, tagged per athlete | ESPN news wire |

Two traps. ESPN's per-athlete news endpoint (`/athletes/{id}/news`) looks like
the right tool and returns an empty list for every athlete tried, including
players on the wire's front page the same minute; the league-wide wire's
athlete tags are what actually work. And ESPN writes "Aaron Jones Sr" where
Sleeper writes "Aaron Jones", so `player_intel._base_name_key` drops
generational suffixes that `news_service._name_key` keeps.

### Grounding

Every figure on the verdict panel is computed by `trade_engine` before the
model is called. `llm_service.trade_verdict` receives those numbers, plus the
sourced `player_intel` facts, and is told to explain them, not to derive or
contradict them. See [Grounding](#grounding).

## Matching players across platforms

ESPN and Sleeper number the same human differently, so anything that has to
recognise one player in two leagues joins on a **normalized name**
(`news_service._name_key`: lowercase, letters and spaces only). That is what
lets the cross-league view notice you own Josh Allen in an ESPN league while
playing against him in a Sleeper one — an id join would find nothing there.

Sleeper rosters also have to be normalized before anything can read them:
Sleeper returns arrays of player ids with no names, slots or points, so
`build_team_roster_entries` converts one into the ESPN-shaped entries the app
renders. Consumers read `is_starter`, `on_injured_reserve`, `projected_points`
and `applied_points`; an entry missing those does not fail loudly, it renders a
team with nobody on it.

## External services, and what happens when they are down

| Service | Used for | If it fails |
| --- | --- | --- |
| ESPN | leagues, rosters, matchups | that league's data is unavailable; the rest of the app works |
| Sleeper | leagues, rosters, projections, trending adds, player index | same, plus waiver buzz disappears |
| Groq | all generated writing | content falls back to a facts summary; the chat says so plainly |
| ESPN/Sleeper CDNs | player headshots | the avatar falls back to initials |

Nothing here is a hard dependency. The database is the only one, which is why
it is the only thing `/health/ready` gates on.

## Grounding

Every generated thing follows the same rule, and it is not optional:

> Gather real facts first. Hand them to the model. Forbid it from going beyond them.

`content_service` extracts story facts from the week before any prompt is
built; `api/assistant` assembles standings, roster, results and waiver trends
into a context block and tells the model to use nothing else. This is not
stylistic — an early recap invented an entire league, and the digest invented a
manager's name until the prompt was told it does not know anyone's real name.

## Mock mode

`MOCK_MODE=true` short-circuits ESPN, Sleeper and Groq to sample data and forces
SQLite. The whole app runs with no credentials and no network. It is how the
demo is served, how most tests run, and the reason a contributor can get to a
working screen in two commands.

## Key directories

```
backend/app/
  api/         one router per feature; ownership checks live here
  services/    business logic and external clients
  models/      SQLAlchemy tables
  schemas/     pydantic request/response shapes
  core/        config, auth, observability
  db/          engine and session

frontend/src/
  pages/       one per route
  components/  ui/ primitives · layout/ shell · feature folders
  hooks/       react-query wrappers
  services/    axios clients
  types/       shared TypeScript types
```

## Related

- [Development](DEVELOPMENT.md) — running it locally
- [Testing](TESTING.md) — the suite and its gotchas
- [Operations](OPERATIONS.md) — health, config, deploy
- [ESPN API](ESPN_API_INTEGRATION.md) — the upstream API, including the two id spaces
- [Design](DESIGN.md) — tokens and theming
