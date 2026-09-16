# Testing

Two suites, both with coverage gates that fail the build.

| | Backend | Frontend |
| --- | --- | --- |
| Runner | pytest + pytest-asyncio | vitest + Testing Library |
| Tests | 519 | 317 |
| Coverage | 83% (gate: 80%) | 54% statements, 77% branches (gate: 37 / 74) |

## Running

```bash
# Backend
cd backend
./venv/bin/python -m pytest tests/ -q            # everything, with the gate
./venv/bin/python -m pytest tests/ -q -m unit    # fast: no database, no app
./venv/bin/python -m pytest tests/test_board.py -q --no-cov
./venv/bin/python -m pytest tests/ -q --cov-report=term-missing

# Frontend
cd frontend
npm test                      # watch
npx vitest run                # once
npm run test:coverage
```

## How the backend suite is organised

Markers, declared in `pytest.ini`:

- **`unit`** — pure logic. No database, no HTTP, no app fixtures. `test_core`, `test_llm_service`, `test_encryption`.
- **`integration`** — drives the app through its API against a real (in-memory SQLite) database. Everything else.

Fixtures, in `conftest.py`:

| Fixture | Gives you |
| --- | --- |
| `client` | `AsyncClient` bound to the app via `ASGITransport`, with the database dependency overridden |
| `auth_headers` | a registered user's bearer token |
| `espn_league` | the canned mock ESPN league connected through the real endpoint, plus its teams |
| `mock_mode` | flips `settings.mock_mode` for one test, short-circuiting ESPN/Sleeper/Groq |
| `reset_service_caches` | *autouse* — empties every module-level cache around each test |

`reset_service_caches` matters more than it looks. The draft service and the
Sleeper player index are module-level singletons that outlive a test. The
player index additionally remembers when it last *attempted* a fetch, so a test
that simulates Sleeper being down leaves a cooldown that would silently skip
the next test's fetch.

External HTTP is mocked with `respx`. Nothing in the suite reaches the network.

## Why coverage was lying

Coverage sat at a reported 67% while the real figure was 79%, and individual
files were wildly wrong — `api/board.py` read 37% while its tests exercised
86% of it.

SQLAlchemy's async layer runs database work inside **greenlets**, and
coverage.py cannot see into a greenlet unless told to. Every endpoint body that
touched the database read as unexecuted. The fix is one line in `.coveragerc`:

```ini
[run]
concurrency = greenlet,thread
```

If a file you know is covered reports near-zero, check that this is still set
before writing tests that already exist.

## What is deliberately not tested

Both gates are **ratchets set just under actual coverage**, not targets. Raise
them as coverage grows.

The frontend statement number is low because a large share of the tree is page
and hook wiring inherited from before the suite existed. The branch figure
(75%) is the more meaningful one: the logic that *is* covered is covered
through its cases rather than executed once. Untested areas, in rough priority
order: `App.tsx` routing, the older pages (Dashboard, Leagues, Profile, Trade
Analyzer, Player Search), and the thin react-query hooks around them.

Three modules — `core/exceptions.py`, `core/logging.py`, `core/middleware.py` —
were deleted rather than tested. They shipped with the repo, were imported by
nothing, and had never run. Their real replacements live in
`core/observability.py`, wired into the app and covered at 100%.

## Platform parity

`test_platform_parity.py` runs one set of assertions against both an ESPN and a
Sleeper league, parametrized on platform. Write new platform-facing tests there
rather than in a per-platform file: a gap between the two does not fail loudly,
it renders an empty roster or a zero score, and only a shared assertion catches
that.

## Environment gaps that look like bugs

jsdom does not implement `ResizeObserver`, `IntersectionObserver`,
`matchMedia` or `scrollIntoView`. Headless UI's `Dialog` needs the first, so
without the polyfills in `src/test/setup.ts` every modal, drawer and slide-over
throws on mount and renders nothing — which presents as *"unable to find
element"*, not as a missing polyfill.

`src/test/render.tsx` provides `renderWithProviders`, which wraps a component in
a `QueryClientProvider` and a `MemoryRouter`. Use it rather than bare `render`
for anything that uses routing or react-query. Note that it deliberately does
**not** set `cacheTime: 0` — that garbage-collects anything seeded with
`setQueryData` before a component subscribes to it.

Vitest 0.34 reads coverage thresholds **flat** on the coverage config
(`statements`, `branches`, `functions`, `lines`). A nested `thresholds: {}`
object is 1.x syntax and is silently ignored, which is how a threshold of 55
once sat in the config passing at 34%.

## Writing tests here

- Name the behaviour, not the function: `test_cold_reactions_drop_it_back_out`, not `test_refresh_voice_samples_2`.
- Assert on what a user or caller would notice. For generated content that means asserting on the **prompt** the model was handed, not on whatever it replied — see `captured_llm` in `test_assistant.py`.
- Put a comment above any assertion whose reason is not obvious, especially where it pins a past bug.
- Prefer one fixture in `conftest.py` over the same setup repeated in five files.
