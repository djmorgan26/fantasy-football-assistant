import asyncio
import os
from typing import AsyncGenerator

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool

# Pin a deterministic test environment BEFORE the app (and its module-level
# Settings singleton) is imported. Tests exercise real (non-mock) code paths
# with external HTTP mocked via respx; TrustedHost must accept "testserver".
os.environ["MOCK_MODE"] = "false"
os.environ["DEBUG"] = "false"
os.environ["ALLOWED_HOSTS"] = "testserver,localhost,127.0.0.1"
os.environ["DATABASE_URL"] = "sqlite+aiosqlite://"
os.environ["GROQ_API_KEY"] = ""

from app.main import app  # noqa: E402
from app.db.database import get_database, Base  # noqa: E402

# In-memory SQLite shared across connections via StaticPool so the
# schema created in setup is visible to every test session.
TEST_DATABASE_URL = "sqlite+aiosqlite://"

test_engine = create_async_engine(
    TEST_DATABASE_URL,
    echo=False,
    poolclass=StaticPool,
    connect_args={"check_same_thread": False},
)

TestingSessionLocal = async_sessionmaker(
    test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    # Fresh schema per test: no state leaks between tests even though
    # endpoints commit.
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with TestingSessionLocal() as session:
        yield session
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    async def override_get_database():
        yield db_session

    app.dependency_overrides[get_database] = override_get_database

    async with AsyncClient(app=app, base_url="http://testserver") as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest.fixture
async def auth_headers(client: AsyncClient) -> dict:
    """Register a fresh user and return Authorization headers."""
    response = await client.post(
        "/api/auth/register",
        json={
            "email": "fixture-user@example.com",
            "password": "testpassword123",
            "full_name": "Fixture User",
        },
    )
    assert response.status_code == 200, response.text
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(autouse=True)
def reset_service_caches():
    """Keep the singleton draft service cache from leaking between tests.

    Mock-mode tests fill it with mock players; real-mode (respx) tests must
    not be served those cached payloads, and vice versa.
    """
    from app.services.draft_service import draft_service

    draft_service._players_cache = None
    draft_service._players_cached_at = None
    draft_service._proj_cache = {}
    draft_service._board_cache = {}
    yield
    draft_service._players_cache = None
    draft_service._players_cached_at = None
    draft_service._proj_cache = {}
    draft_service._board_cache = {}


@pytest.fixture
def mock_mode():
    """Flip the app into MOCK_MODE for the duration of one test.

    Services check settings.mock_mode at call time, so toggling the singleton
    short-circuits ESPN/Sleeper/Groq to canned data exactly like the demo.
    """
    from app.core.config import settings

    settings.mock_mode = True
    yield settings
    settings.mock_mode = False


@pytest.fixture
async def espn_league(client: AsyncClient, auth_headers: dict, mock_mode) -> dict:
    """Connect the canned mock ESPN league through the real connect endpoint.

    Returns {"league": <LeagueResponse dict>, "teams": [TeamResponse dicts]}.
    """
    from app.services import mock_data

    resp = await client.post(
        "/api/leagues/connect",
        json={"league_id": mock_data.MOCK_ESPN_LEAGUE_ID},
        headers=auth_headers,
    )
    assert resp.status_code == 200, resp.text
    league = resp.json()["league"]
    teams_resp = await client.get(
        f"/api/teams/league/{league['id']}", headers=auth_headers
    )
    assert teams_resp.status_code == 200, teams_resp.text
    return {"league": league, "teams": teams_resp.json()}


@pytest.fixture
async def sleeper_league(client: AsyncClient, auth_headers: dict, mock_mode) -> dict:
    """Connect the canned mock Sleeper league through the real connect endpoint."""
    from app.services import mock_data

    resp = await client.post(
        "/api/sleeper/connect",
        json={
            "league_id": mock_data.MOCK_SLEEPER_LEAGUE_ID,
            "sleeper_user_id": mock_data.MOCK_SLEEPER_USER_ID,
        },
        headers=auth_headers,
    )
    assert resp.status_code == 200, resp.text
    league_id = resp.json()["league_id"]
    league_resp = await client.get(f"/api/leagues/{league_id}", headers=auth_headers)
    assert league_resp.status_code == 200, league_resp.text
    teams_resp = await client.get(
        f"/api/teams/league/{league_id}", headers=auth_headers
    )
    assert teams_resp.status_code == 200, teams_resp.text
    return {"league": league_resp.json(), "teams": teams_resp.json()}
